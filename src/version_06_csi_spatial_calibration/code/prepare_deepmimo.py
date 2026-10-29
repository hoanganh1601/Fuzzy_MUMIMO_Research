#!/usr/bin/env python3
"""Prepare a grouped DeepMIMO NPZ for calibration_v2.py in three explicit stages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path

import deepmimo as dm
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    os.replace(temporary, path)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def minimum_separation(points: np.ndarray) -> float:
    delta = points[:, None, :] - points[None, :, :]
    distances = np.linalg.norm(delta, axis=2)
    np.fill_diagonal(distances, np.inf)
    return float(np.min(distances))


def load_selection_view(scenario: str, max_paths: int):
    return dm.load(
        scenario,
        tx_sets={1: [0]},
        rx_sets={0: "all"},
        max_paths=max_paths,
        matrices=["rx_pos", "power", "aoa_az"],
    )


def select_groups(args: argparse.Namespace) -> None:
    selection_path = project_path(args.selection)
    if selection_path.exists() and not args.overwrite:
        raise FileExistsError(f"Selection already exists: {selection_path}; use --overwrite explicitly")

    dataset = load_selection_view(args.scenario, args.max_paths)
    positions = np.asarray(dataset.rx_pos, dtype=np.float64)
    path_power_dbw = np.asarray(dataset.power, dtype=np.float64)
    active = np.asarray(dataset.num_paths) > 0
    total_power_w = np.nansum(np.power(10.0, path_power_dbw / 10.0), axis=1)
    total_power_dbw = 10.0 * np.log10(np.maximum(total_power_w, 1e-300))
    eligible = np.flatnonzero(active & (total_power_dbw >= args.min_total_power_dbw))

    rng = np.random.default_rng(args.seed)
    pool = [int(index) for index in rng.permutation(eligible)]
    used: set[int] = set()
    groups: list[list[int]] = []
    centers: list[np.ndarray] = []

    for anchor in pool:
        if anchor in used:
            continue
        selected = [anchor]
        for candidate in pool:
            if candidate in used or candidate in selected:
                continue
            nearest = min(
                np.linalg.norm(positions[candidate] - positions[member]) for member in selected
            )
            if nearest >= args.min_user_distance_m:
                selected.append(candidate)
                if len(selected) == args.users_per_geometry:
                    break
        if len(selected) != args.users_per_geometry:
            break

        center = positions[selected].mean(axis=0)
        if centers:
            center_distances = np.linalg.norm(np.asarray(centers) - center, axis=1)
            if float(np.min(center_distances)) < args.min_center_distance_m:
                continue

        groups.append(selected)
        centers.append(center)
        used.update(selected)
        if len(groups) == args.groups:
            break

    if len(groups) != args.groups:
        raise RuntimeError(f"Could select only {len(groups)} of {args.groups} requested groups")

    group_array = np.asarray(groups, dtype=np.int64)
    center_array = np.asarray(centers, dtype=np.float64)
    user_xyz = positions[group_array]
    user_power = total_power_dbw[group_array]
    center_min = minimum_separation(center_array)
    if center_min < args.min_center_distance_m:
        raise RuntimeError("Internal error: selected group centers violate the distance threshold")
    if len(np.unique(group_array)) != group_array.size:
        raise RuntimeError("Internal error: a UE was reused across groups")

    atomic_npz(
        selection_path,
        ue_indices=group_array,
        centers=center_array,
        user_xyz=user_xyz,
        total_path_power_dbw=user_power,
    )
    print(f"SELECTION SAVED: {selection_path}")
    print(f"groups={len(group_array)}, users={group_array.size}, eligible_pool={len(eligible)}")
    print(f"minimum_group_center_distance_m={center_min:.6f}")
    print(f"minimum_selected_total_path_power_dbw={float(user_power.min()):.6f}")


def load_selected_dataset(scenario: str, ue_indices: np.ndarray, max_paths: int):
    return dm.load(
        scenario,
        tx_sets={1: [0]},
        rx_sets={0: ue_indices.ravel()},
        max_paths=max_paths,
        matrices=[
            "rx_pos",
            "power",
            "phase",
            "delay",
            "aoa_az",
            "aoa_el",
            "aod_az",
            "aod_el",
        ],
    )


def build_dataset(args: argparse.Namespace) -> None:
    selection_path = project_path(args.selection)
    output_path = project_path(args.output)
    provenance_path = project_path(args.provenance)
    groups_csv_path = project_path(args.groups_csv)
    if not selection_path.exists():
        raise FileNotFoundError(f"Run --stage select first: {selection_path}")
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"Dataset already exists: {output_path}; use --overwrite explicitly")

    with np.load(selection_path, allow_pickle=False) as selected:
        ue_indices = selected["ue_indices"]
        centers = selected["centers"]
        user_xyz = selected["user_xyz"]
        total_path_power_dbw = selected["total_path_power_dbw"]

    dataset = load_selected_dataset(args.scenario, ue_indices, args.max_paths)
    channel_params = dm.ChannelParameters(
        bs_antenna={"shape": [args.antennas, 1]},
        ue_antenna={"shape": [1, 1]},
        num_paths=args.max_paths,
        freq_domain=True,
    )
    channels = np.asarray(dataset.compute_channels(channel_params))
    expected = (ue_indices.size, 1, args.antennas, 1)
    if channels.shape != expected:
        raise ValueError(f"Unexpected DeepMIMO channel shape {channels.shape}; expected {expected}")

    num_groups, users_per_geometry = ue_indices.shape
    H = channels[:, 0, :, 0].reshape(num_groups, users_per_geometry, args.antennas)
    H = np.transpose(H, (0, 2, 1)).astype(np.complex64, copy=False)
    if not np.isfinite(H).all() or np.any(np.linalg.norm(H, axis=1) == 0):
        raise ValueError("Generated channels contain non-finite or zero channel vectors")

    groups = np.asarray(
        [f"{args.scenario}_g{index:04d}" for index in range(num_groups)], dtype="U64"
    )
    scenarios = np.full(num_groups, args.scenario, dtype="U64")
    atomic_npz(output_path, H=H, groups=groups, xyz=centers, scenario=scenarios)

    group_rows: list[dict] = []
    for group_index, group_name in enumerate(groups):
        row: dict[str, object] = {
            "group": str(group_name),
            "center_x_m": float(centers[group_index, 0]),
            "center_y_m": float(centers[group_index, 1]),
            "center_z_m": float(centers[group_index, 2]),
        }
        for user_index in range(users_per_geometry):
            row[f"ue{user_index}_source_index"] = int(ue_indices[group_index, user_index])
            row[f"ue{user_index}_x_m"] = float(user_xyz[group_index, user_index, 0])
            row[f"ue{user_index}_y_m"] = float(user_xyz[group_index, user_index, 1])
            row[f"ue{user_index}_z_m"] = float(user_xyz[group_index, user_index, 2])
            row[f"ue{user_index}_total_path_power_dbw"] = float(
                total_path_power_dbw[group_index, user_index]
            )
        group_rows.append(row)
    atomic_csv(groups_csv_path, group_rows)

    params_path = PROJECT_ROOT / "deepmimo_scenarios" / args.scenario / "params.json"
    provenance = {
        "deepmimo_version": version("deepmimo"),
        "scenario": args.scenario,
        "scenario_params_sha256": sha256(params_path),
        "selection_sha256": sha256(selection_path),
        "dataset_sha256": sha256(output_path),
        "shape": list(H.shape),
        "dtype": str(H.dtype),
        "selection": {
            "seed": args.seed,
            "groups": args.groups,
            "users_per_geometry": args.users_per_geometry,
            "minimum_total_path_power_dbw": args.min_total_power_dbw,
            "minimum_intra_geometry_user_distance_m": args.min_user_distance_m,
            "minimum_group_center_distance_m": args.min_center_distance_m,
            "user_reuse": False,
        },
        "channel": {
            "bs_antenna_shape": [args.antennas, 1],
            "ue_antenna_shape": [1, 1],
            "antenna_spacing_wavelengths": 0.5,
            "max_paths": args.max_paths,
            "domain": "frequency",
            "ofdm_total_subcarriers": 512,
            "selected_subcarrier": 0,
            "bandwidth_hz": 10_000_000.0,
            "normalization": "none; absolute DeepMIMO channel scale retained",
            "matrix_convention": "H[g,:,k] = DeepMIMO channel[user_k,0,:,0]",
        },
        "cautions": [
            "Disjoint UE indices and spatial separation do not prove independent episodes.",
            "All groups come from one ray-tracing scene and may remain correlated.",
            "Noise power must be specified and reported consistently when calibration is run.",
        ],
    }
    atomic_json(provenance_path, provenance)
    print(f"DATASET SAVED: {output_path}")
    print(f"GROUP AUDIT SAVED: {groups_csv_path}")
    print(f"PROVENANCE SAVED: {provenance_path}")
    print(f"H shape={H.shape}, dtype={H.dtype}, sha256={provenance['dataset_sha256']}")


def verify_dataset(args: argparse.Namespace) -> None:
    output_path = project_path(args.output)
    provenance_path = project_path(args.provenance)
    with np.load(output_path, allow_pickle=False) as data:
        if set(data.files) != {"H", "groups", "xyz", "scenario"}:
            raise ValueError(f"Unexpected NPZ fields: {data.files}")
        H = data["H"]
        groups = data["groups"]
        xyz = data["xyz"]
        scenarios = data["scenario"]

    expected_shape = (args.groups, args.antennas, args.users_per_geometry)
    if H.shape != expected_shape or not np.iscomplexobj(H) or not np.isfinite(H).all():
        raise ValueError(f"Invalid H: {H.shape}, {H.dtype}")
    if len(np.unique(groups)) != args.groups:
        raise ValueError("Group IDs are not unique")
    if xyz.shape != (args.groups, 3) or not np.isfinite(xyz).all():
        raise ValueError("Invalid group-center coordinates")
    center_min = minimum_separation(xyz)
    if center_min < args.min_center_distance_m:
        raise ValueError("Group centers do not satisfy the requested separation")
    if set(np.unique(scenarios)) != {args.scenario}:
        raise ValueError("Unexpected scenario labels")

    provenance = json.loads(provenance_path.read_text())
    if provenance["dataset_sha256"] != sha256(output_path):
        raise ValueError("Dataset SHA256 does not match provenance")
    print(f"DEEPMIMO DATASET VALIDATION: PASS")
    print(f"path={output_path}")
    print(f"H={H.shape} {H.dtype}, groups={len(groups)}, center_min_m={center_min:.6f}")
    print(f"sha256={provenance['dataset_sha256']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["select", "build", "verify"], required=True)
    parser.add_argument("--scenario", default="asu_campus_3p5")
    parser.add_argument("--selection", default="data/deepmimo_selection.npz")
    parser.add_argument("--output", default="data/deepmimo.npz")
    parser.add_argument("--provenance", default="data/deepmimo_provenance.json")
    parser.add_argument("--groups-csv", default="data/deepmimo_groups.csv")
    parser.add_argument("--groups", type=int, default=160)
    parser.add_argument("--users-per-geometry", type=int, default=4)
    parser.add_argument("--antennas", type=int, default=16)
    parser.add_argument("--max-paths", type=int, default=10)
    parser.add_argument("--min-total-power-dbw", type=float, default=-100.0)
    parser.add_argument("--min-user-distance-m", type=float, default=20.0)
    parser.add_argument("--min-center-distance-m", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.groups < 118 or args.users_per_geometry < 1 or args.antennas < 1 or args.max_paths < 1:
        parser.error("invalid dataset dimensions; at least 118 groups are required")
    return args


def main() -> None:
    args = parse_args()
    os.chdir(PROJECT_ROOT)
    if args.stage == "select":
        select_groups(args)
    elif args.stage == "build":
        build_dataset(args)
    else:
        verify_dataset(args)


if __name__ == "__main__":
    main()
