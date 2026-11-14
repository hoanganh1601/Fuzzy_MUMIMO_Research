"""Build the locked DeepMIMO V13 New York test selection.

This script selects channel geometries only. It does not compute channel matrices
and does not inspect any V13 runtime or feasibility outcome.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import deepmimo as dm
import numpy as np


ROOT = Path(__file__).resolve().parent
SCENARIO = "city_0_newyork_3p5"
SEED = 20261113
CELL_SIZE_M = 15.0
GROUPS_REQUIRED = 40
GEOMETRIES_PER_GROUP = 4
USERS_PER_GEOMETRY = 4
MIN_POWER_DBW = -100.0

OUTPUT = ROOT / "deepmimo_v13_selection.npz"
PROTOCOL_OUTPUT = ROOT / "deepmimo_v13_selection_protocol.json"
PARAMS_FILE = ROOT / "deepmimo_scenarios" / SCENARIO / "params.json"
CP02 = ROOT / "locks" / "CP02_policy_lock_DM_ASU35_20261112.json"
EXPECTED_CP02_SHA256 = "ede58de7c0f2791327b54e929e6da4921db17b8d5c870a3dec5bdc9ef1b8b5be"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUTPUT.exists() or PROTOCOL_OUTPUT.exists():
        raise SystemExit("Locked selection output already exists; refusing to overwrite")
    if digest(CP02) != EXPECTED_CP02_SHA256:
        raise SystemExit("CP02 policy-lock hash mismatch")

    dataset = dm.load(
        SCENARIO,
        max_paths=10,
        tx_sets={3: [0]},
        rx_sets={0: "all"},
        matrices=[
            "power",
            "phase",
            "delay",
            "aoa_az",
            "aoa_el",
            "aod_az",
            "aod_el",
            "rx_pos",
            "tx_pos",
        ],
    )

    power = np.asarray(dataset.power, dtype=np.float64)
    xyz = np.asarray(dataset.rx_pos, dtype=np.float64)
    path_power_w = np.where(np.isfinite(power), np.power(10.0, power / 10.0), 0.0)
    total_power_w = path_power_w.sum(axis=1)
    total_power_dbw = np.full(len(total_power_w), -np.inf, dtype=np.float64)
    positive = total_power_w > 0
    total_power_dbw[positive] = 10.0 * np.log10(total_power_w[positive])

    usable_mask = np.isfinite(xyz).all(axis=1) & (total_power_dbw > MIN_POWER_DBW)
    usable_indices = np.flatnonzero(usable_mask)
    origin_xy = xyz[usable_indices, :2].min(axis=0)
    cell_xy = np.floor((xyz[usable_indices, :2] - origin_xy) / CELL_SIZE_M).astype(
        np.int64
    )

    cells: dict[tuple[int, int], list[int]] = {}
    for ue_idx, cell in zip(usable_indices, cell_xy, strict=True):
        key = (int(cell[0]), int(cell[1]))
        cells.setdefault(key, []).append(int(ue_idx))

    required_per_cell = GEOMETRIES_PER_GROUP * USERS_PER_GEOMETRY
    eligible = [
        (cell, np.asarray(indices, dtype=np.int64))
        for cell, indices in cells.items()
        if len(indices) >= required_per_cell
    ]
    if len(eligible) < GROUPS_REQUIRED:
        raise SystemExit(
            f"FAIL: only {len(eligible)} cells contain at least {required_per_cell} usable UEs"
        )

    rng = np.random.default_rng(SEED)
    rng.shuffle(eligible)
    chosen_cells = eligible[:GROUPS_REQUIRED]

    selected_indices: list[np.ndarray] = []
    selected_groups: list[str] = []
    selected_centers: list[np.ndarray] = []
    selected_cells: list[tuple[int, int]] = []
    selected_xyz: list[np.ndarray] = []
    selected_power: list[np.ndarray] = []

    for cell, candidates in chosen_cells:
        chosen = rng.choice(candidates, size=required_per_cell, replace=False).reshape(
            GEOMETRIES_PER_GROUP, USERS_PER_GEOMETRY
        )
        group_name = f"v13_city0_newyork_bs1_cell_{cell[0]}_{cell[1]}"
        for geometry in chosen:
            points = xyz[geometry]
            selected_indices.append(geometry)
            selected_groups.append(group_name)
            selected_centers.append(points.mean(axis=0))
            selected_cells.append(cell)
            selected_xyz.append(points)
            selected_power.append(total_power_dbw[geometry])

    ue_indices = np.asarray(selected_indices, dtype=np.int64)
    groups = np.asarray(selected_groups)
    centers = np.asarray(selected_centers, dtype=np.float64)
    cell_coordinates = np.asarray(selected_cells, dtype=np.int64)
    user_xyz = np.asarray(selected_xyz, dtype=np.float64)
    selected_total_power_dbw = np.asarray(selected_power, dtype=np.float64)

    if ue_indices.shape != (160, 4):
        raise SystemExit(f"FAIL: unexpected selection shape {ue_indices.shape}")
    if len(np.unique(ue_indices)) != 640:
        raise SystemExit("FAIL: UE reuse detected")
    if len(np.unique(groups)) != 40:
        raise SystemExit("FAIL: expected 40 spatial groups")

    pairwise_minima = []
    for points in user_xyz:
        distance = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
        pairwise_minima.append(float(distance[np.triu_indices(USERS_PER_GEOMETRY, 1)].min()))

    np.savez_compressed(
        OUTPUT,
        ue_indices=ue_indices,
        groups=groups,
        centers=centers,
        cell_coordinates=cell_coordinates,
        user_xyz=user_xyz,
        total_path_power_dbw=selected_total_power_dbw,
    )

    protocol = {
        "source": "DeepMIMO",
        "scenario": SCENARIO,
        "deepmimo_version": dm.__version__,
        "transmitter": "BS1",
        "tx_set": 3,
        "tx_index": 0,
        "rx_set": 0,
        "seed": SEED,
        "cell_size_m": CELL_SIZE_M,
        "groups": GROUPS_REQUIRED,
        "geometries_per_group": GEOMETRIES_PER_GROUP,
        "users_per_geometry": USERS_PER_GEOMETRY,
        "minimum_total_path_power_dbw": MIN_POWER_DBW,
        "minimum_user_distance_constraint_m": None,
        "observed_minimum_user_distance_m": min(pairwise_minima),
        "n_geometries": int(len(ue_indices)),
        "unique_ues": int(len(np.unique(ue_indices))),
        "selection_sha256": digest(OUTPUT),
        "scenario_params_sha256": digest(PARAMS_FILE),
        "cp02_policy_lock_sha256": digest(CP02),
        "generation_code_sha256": digest(Path(__file__)),
        "created_after_policy_lock": True,
        "prior_use": "never_seen",
    }
    PROTOCOL_OUTPUT.write_text(json.dumps(protocol, indent=2) + "\n")

    print("DEEPMIMO V13 SELECTION PASS")
    print("Geometries:", len(ue_indices))
    print("Spatial groups:", len(np.unique(groups)))
    print("Unique UEs:", len(np.unique(ue_indices)))
    print("Observed minimum UE distance m:", min(pairwise_minima))
    print("Selection:", OUTPUT)
    print("Selection SHA256:", digest(OUTPUT))
    print("Protocol:", PROTOCOL_OUTPUT)
    print("Protocol SHA256:", digest(PROTOCOL_OUTPUT))
    print("Generation code SHA256:", digest(Path(__file__)))


if __name__ == "__main__":
    main()
