#!/usr/bin/env python3
"""Generate a spatially grouped DeepMIMO MU-MIMO dataset."""

import argparse
import json
from pathlib import Path

import deepmimo as dm
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate DeepMIMO H[N,M,K] using spatially "
            "disjoint and balanced groups."
        )
    )
    parser.add_argument(
        "--scenario",
        default="asu_campus_3p5",
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    parser.add_argument(
        "--M",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--K",
        type=int,
        default=4,
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=200.0,
        help="Maximum 2D distance from BS in metres",
    )
    parser.add_argument(
        "--cell-size",
        type=float,
        default=35.0,
        help="Spatial grid-cell size in metres",
    )
    parser.add_argument(
        "--users-per-group",
        type=int,
        default=100,
        help="Exact number of users retained per spatial group",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=31,
    )
    parser.add_argument(
        "--noise-w",
        type=float,
        default=6.324555320336759e-13,
        help="Receiver noise power in watts",
    )
    return parser.parse_args()


def validate_args(args, parser):
    if args.M < args.K:
        parser.error("M must be greater than or equal to K")

    if args.radius <= 0:
        parser.error("--radius must be positive")

    if args.cell_size <= 0:
        parser.error("--cell-size must be positive")

    if args.users_per_group < args.K:
        parser.error("--users-per-group must be at least K")

    if args.users_per_group % args.K != 0:
        parser.error("--users-per-group must be divisible by K")

    if args.noise_w <= 0:
        parser.error("--noise-w must be positive")


def load_metadata(dataset):
    rx = np.asarray(dataset.rx_pos)
    tx = np.asarray(dataset.tx_pos).reshape(-1, 3)[0]
    los = np.asarray(dataset.los)
    pathloss = np.asarray(dataset.pathloss)

    if pathloss.ndim == 2:
        masked = np.where(
            np.isfinite(pathloss),
            pathloss,
            np.nan,
        )
        pathloss = np.nanmin(masked, axis=1)

    if len(rx) != len(los) or len(rx) != len(pathloss):
        raise ValueError(
            "DeepMIMO metadata arrays have inconsistent lengths"
        )

    return rx, tx, los, pathloss


def compute_channel_rows(dataset, M):
    params = dm.ChannelParameters()
    params.bs_antenna.shape = np.array([M, 1])
    params.ue_antenna.shape = np.array([1, 1])

    dataset.compute_channels(params)

    channels = getattr(dataset, "channels", None)

    if channels is None:
        channels = dataset.channel

    channels = np.asarray(channels)

    if channels.ndim != 4:
        raise ValueError(
            f"Expected a four-dimensional channel array, "
            f"got {channels.shape}"
        )

    if channels.shape[1] != 1:
        raise ValueError(
            f"Expected one UE antenna, got shape {channels.shape}"
        )

    if channels.shape[2] != M:
        raise ValueError(
            f"Expected {M} BS antennas, got shape {channels.shape}"
        )

    # DeepMIMO exports row a under y = a*x.
    # The experiment uses y = h^H*x, hence h = conj(a).
    channel_rows = np.conj(channels[:, 0, :, 0])

    return channel_rows


def minimum_pairwise_distance(positions):
    """Minimum horizontal UE separation in every MU-MIMO tuple."""

    xy = positions[:, :, :2]

    delta = xy[:, :, None, :] - xy[:, None, :, :]
    distance = np.linalg.norm(delta, axis=-1)

    K = positions.shape[1]
    diagonal = np.arange(K)
    distance[:, diagonal, diagonal] = np.inf

    return np.min(distance, axis=(1, 2))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    args = parse_args()

    # parse_args creates the real parser, so perform explicit validation.
    if args.M < args.K:
        raise ValueError("M must be greater than or equal to K")
    if args.radius <= 0 or args.cell_size <= 0:
        raise ValueError("radius and cell size must be positive")
    if args.users_per_group < args.K:
        raise ValueError("users-per-group must be at least K")
    if args.users_per_group % args.K != 0:
        raise ValueError("users-per-group must be divisible by K")
    if args.noise_w <= 0:
        raise ValueError("noise-w must be positive")

    print("Loading DeepMIMO scenario:", args.scenario)
    dataset = dm.load(args.scenario)

    rx, tx, los, pathloss = load_metadata(dataset)

    distance_2d = np.linalg.norm(
        rx[:, :2] - tx[None, :2],
        axis=1,
    )

    metadata_valid = (
        (distance_2d <= args.radius)
        & (los != -1)
        & np.isfinite(pathloss)
    )

    print("Computing channel matrices...")
    channel_rows = compute_channel_rows(
        dataset,
        args.M,
    )

    if len(channel_rows) != len(rx):
        raise ValueError(
            "Channel and position arrays have different lengths"
        )

    channel_valid = (
        np.isfinite(channel_rows).all(axis=1)
        & (np.linalg.norm(channel_rows, axis=1) > 1e-15)
    )

    eligible = metadata_valid & channel_valid
    eligible_indices = np.flatnonzero(eligible)

    print("Total UE:", len(rx))
    print("Metadata-eligible UE:", int(np.sum(metadata_valid)))
    print("Channel-valid UE:", int(np.sum(channel_valid)))
    print("Final eligible UE:", len(eligible_indices))

    # Use a fixed origin so cell assignments are reproducible.
    grid_origin = (
        np.floor(np.min(rx[:, :2], axis=0) / 10)
        * 10
    )

    eligible_cells = np.floor(
        (
            rx[eligible_indices, :2]
            - grid_origin[None, :]
        )
        / args.cell_size
    ).astype(np.int64)

    unique_cells, inverse, counts = np.unique(
        eligible_cells,
        axis=0,
        return_inverse=True,
        return_counts=True,
    )

    selected_cell_indices = np.flatnonzero(
        counts >= args.users_per_group
    )

    if len(selected_cell_indices) < 3:
        raise RuntimeError(
            "Fewer than three spatial groups satisfy "
            "--users-per-group"
        )

    rng = np.random.default_rng(args.seed)

    tuple_indices = []
    geometry_groups = []
    geometry_cells = []

    geometries_per_group = (
        args.users_per_group // args.K
    )

    for group_label, cell_index in enumerate(
        selected_cell_indices
    ):
        members = eligible_indices[
            inverse == cell_index
        ].copy()

        rng.shuffle(members)
        members = members[:args.users_per_group]

        tuples = members.reshape(
            geometries_per_group,
            args.K,
        )

        tuple_indices.append(tuples)

        geometry_groups.append(
            np.full(
                geometries_per_group,
                group_label,
                dtype=np.int32,
            )
        )

        geometry_cells.append(
            np.repeat(
                unique_cells[cell_index][None, :],
                geometries_per_group,
                axis=0,
            )
        )

    ue_indices = np.concatenate(
        tuple_indices,
        axis=0,
    )

    groups = np.concatenate(
        geometry_groups,
        axis=0,
    )

    group_cells = np.concatenate(
        geometry_cells,
        axis=0,
    )

    # channel_rows[ue_indices] has shape (N,K,M).
    # The experiment requires H with shape (N,M,K).
    H = channel_rows[ue_indices].transpose(0, 2, 1)

    ue_positions = rx[ue_indices]
    distances_m = distance_2d[ue_indices]
    pathloss_db = pathloss[ue_indices]
    los_labels = los[ue_indices]

    min_separation_m = minimum_pairwise_distance(
        ue_positions
    )

    deepmimo_version = getattr(
        dm,
        "__version__",
        "unknown",
    )

    selection = {
        "source": "DeepMIMO",
        "deepmimo_version": deepmimo_version,
        "scenario": args.scenario,
        "M": args.M,
        "K": args.K,
        "radius_m": args.radius,
        "cell_size_m": args.cell_size,
        "users_per_group": args.users_per_group,
        "geometries_per_group": geometries_per_group,
        "number_of_groups": int(len(selected_cell_indices)),
        "number_of_geometries": int(len(H)),
        "seed": args.seed,
        "noise_w": args.noise_w,
        "channel_frequency_index": 0,
        "grouping": (
            "fixed spatial grid; exact balanced user count "
            "per retained cell; no UE reuse"
        ),
        "eligibility": (
            "within radius, valid path, finite pathloss, "
            "finite nonzero channel"
        ),
        "bs_position": tx.tolist(),
        "grid_origin": grid_origin.tolist(),
    }

    provenance = (
        f"DeepMIMO {args.scenario}; "
        f"version={deepmimo_version}; "
        f"radius={args.radius}m; "
        f"cell={args.cell_size}m; "
        f"users_per_group={args.users_per_group}; "
        f"seed={args.seed}; "
        "spatially grouped without UE reuse"
    )

    output = Path(args.output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.savez_compressed(
        output,
        H=H.astype(np.complex128),
        groups=groups,
        provenance=np.array(provenance),
        noise_w=np.float64(args.noise_w),
        ue_indices=ue_indices.astype(np.int64),
        ue_positions=ue_positions.astype(np.float64),
        distances_m=distances_m.astype(np.float64),
        pathloss_db=pathloss_db.astype(np.float64),
        los=los_labels.astype(np.int8),
        group_cells=group_cells.astype(np.int64),
        min_separation_m=min_separation_m.astype(
            np.float64
        ),
        selection_json=np.array(
            json.dumps(
                selection,
                sort_keys=True,
            )
        ),
    )

    print("\nEXPORT PASS")
    print("Output:", output.resolve())
    print("H shape:", H.shape)
    print("Groups:", len(np.unique(groups)))
    print(
        "Geometries per group:",
        np.unique(
            groups,
            return_counts=True,
        )[1],
    )
    print(
        "Unique UE:",
        len(np.unique(ue_indices)),
        "/",
        ue_indices.size,
    )
    print(
        "Minimum tuple separation percentiles [m]:",
        np.percentile(
            min_separation_m,
            [0, 1, 10, 50, 90, 99, 100],
        ),
    )
    print(
        "Distance percentiles [m]:",
        np.percentile(
            distances_m,
            [0, 1, 10, 50, 90, 99, 100],
        ),
    )
    print(
        "Pathloss percentiles [dB]:",
        np.percentile(
            pathloss_db,
            [0, 1, 10, 50, 90, 99, 100],
        ),
    )
    print(
        "LOS fraction:",
        float(np.mean(los_labels == 1)),
    )
    print("Noise [W]:", args.noise_w)


if __name__ == "__main__":
    main()