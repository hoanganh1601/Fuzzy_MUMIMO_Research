#!/usr/bin/env python3
"""Analyze DeepMIMO coverage and candidate spatial grouping."""

import argparse

import deepmimo as dm
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze DeepMIMO coverage and spatial blocks."
    )
    parser.add_argument(
        "--scenario",
        default="asu_campus_3p5",
        help="DeepMIMO scenario name",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=200.0,
        help="Service radius in metres",
    )
    parser.add_argument(
        "--cell-sizes",
        type=float,
        nargs="+",
        default=[20, 25, 30, 35, 40, 45, 50, 60],
        help="Candidate spatial-cell sizes in metres",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    dataset = dm.load(args.scenario)

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

    distance_2d = np.linalg.norm(
        rx[:, :2] - tx[None, :2],
        axis=1,
    )

    finite_path = (
        (los != -1)
        & np.isfinite(pathloss)
    )

    inside = distance_2d <= args.radius
    eligible = inside & finite_path

    n_inside = int(np.sum(inside))
    n_eligible = int(np.sum(eligible))
    n_no_path = int(np.sum(inside & ~finite_path))

    print("Scenario:", args.scenario)
    print("Radius:", args.radius, "m")
    print("BS position:", tx)
    print("All UE inside radius:", n_inside)
    print("Valid-path UE inside:", n_eligible)
    print("No-path UE inside:", n_no_path)

    coverage = 100 * n_eligible / max(n_inside, 1)
    los_rate = (
        100 * np.mean(los[eligible] == 1)
        if n_eligible
        else float("nan")
    )

    print("Coverage rate:", round(coverage, 2), "%")
    print(
        "LOS rate among eligible:",
        round(los_rate, 2),
        "%",
    )

    if n_eligible == 0:
        raise RuntimeError(
            "No eligible users inside the selected radius."
        )

    print("\nEligible-user statistics")

    print("Distance percentiles [m]:")
    print(
        np.percentile(
            distance_2d[eligible],
            [0, 1, 10, 25, 50, 75, 90, 99, 100],
        )
    )

    print("Pathloss percentiles [dB]:")
    print(
        np.percentile(
            pathloss[eligible],
            [0, 1, 10, 25, 50, 75, 90, 99, 100],
        )
    )

    print("\nSpatial block candidates")

    # A fixed grid origin makes group assignment reproducible.
    origin = (
        np.floor(np.min(rx[:, :2], axis=0) / 10)
        * 10
    )
    xy = rx[eligible, :2]

    for cell_size in args.cell_sizes:
        cell_xy = np.floor(
            (xy - origin[None, :]) / cell_size
        ).astype(np.int64)

        _, counts = np.unique(
            cell_xy,
            axis=0,
            return_counts=True,
        )

        usable = counts[counts >= 4]
        geometry_count = int(
            np.sum(usable // 4)
        )
        retained_users = int(
            np.sum((usable // 4) * 4)
        )

        result = {
            "cell_size_m": float(cell_size),
            "occupied_cells": int(len(counts)),
            "cells_ge_4_users": int(
                np.sum(counts >= 4)
            ),
            "cells_ge_40_users": int(
                np.sum(counts >= 40)
            ),
            "cells_ge_100_users": int(
                np.sum(counts >= 100)
            ),
            "min_usable_count": (
                int(np.min(usable))
                if len(usable)
                else 0
            ),
            "median_usable_count": (
                float(np.median(usable))
                if len(usable)
                else 0
            ),
            "max_count": (
                int(np.max(counts))
                if len(counts)
                else 0
            ),
            "disjoint_geometries": geometry_count,
            "retained_users": retained_users,
        }

        print(result)


if __name__ == "__main__":
    main()