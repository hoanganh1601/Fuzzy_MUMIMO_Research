#!/usr/bin/env python3
"""Audit robust feasibility on the grouped training split only."""

import argparse
from collections import Counter
from pathlib import Path

import numpy as np

from experiment import (
    atomic_json,
    channel_context,
    gaussian_q,
    grouped_split,
    load_data,
    power_alloc,
)


def comma_floats(value):
    try:
        result = [float(item) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "expected comma-separated numbers"
        ) from exc
    if not result or not np.all(np.isfinite(result)):
        raise argparse.ArgumentTypeError(
            "values must be finite"
        )
    return result


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--M", type=int, default=8)
    parser.add_argument("--K", type=int, default=4)
    parser.add_argument("--sigma-rel", type=float, default=0.04)
    parser.add_argument("--sinr-db", type=float, default=6.0)
    parser.add_argument("--noise", type=float, default=None)
    parser.add_argument(
        "--pmax-values",
        type=comma_floats,
        default=comma_floats("1,2,4"),
    )
    parser.add_argument(
        "--q-values",
        type=comma_floats,
        default=None,
        help=(
            "Comma-separated margins; default is 1.45,1.8 and "
            "the Gaussian reference margin"
        ),
    )
    parser.add_argument("--eps", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument(
        "--target-feasibility",
        type=float,
        default=0.90,
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.M < args.K or args.K < 1:
        raise ValueError("M must be greater than or equal to K")
    if not 0 < args.sigma_rel < 1:
        raise ValueError("sigma-rel must be between zero and one")
    if not 0 < args.eps < 1:
        raise ValueError("eps must be between zero and one")
    if not 0 < args.target_feasibility <= 1:
        raise ValueError("target-feasibility must be in (0,1]")
    if any(value <= 0 for value in args.pmax_values):
        raise ValueError("all pmax values must be positive")

    dataset = Path(args.dataset).resolve()
    H, groups, dataset_noise = load_data(
        dataset,
        args.M,
        args.K,
    )
    noise = args.noise
    if noise is None:
        if dataset_noise is None:
            raise ValueError(
                "noise is absent from the dataset; pass --noise"
            )
        noise = dataset_noise
    if noise <= 0:
        raise ValueError("noise must be positive")

    masks = grouped_split(groups, args.seed)
    train_indices = np.flatnonzero(masks[0])
    q_reference = gaussian_q(args.eps, args.K)
    q_values = (
        args.q_values
        if args.q_values is not None
        else [1.45, 1.8, q_reference]
    )

    base_cfg = {
        "sigma_rel": args.sigma_rel,
        "sinr": 10 ** (args.sinr_db / 10),
        "noise": noise,
        "pmax": max(args.pmax_values),
    }

    contexts = {}
    for index in train_indices:
        contexts[int(index)] = channel_context(
            H,
            groups,
            int(index),
            base_cfg,
            args.seed + 501,
            1,
            q_reference,
        )

    rows = []
    for q in q_values:
        for pmax in args.pmax_values:
            cfg = dict(base_cfg, pmax=pmax)
            reasons = Counter()
            powers = []

            for index in train_indices:
                context = contexts[int(index)]
                if context["V"] is None:
                    reasons["rzf_failed"] += 1
                    continue
                power, _, reason = power_alloc(
                    context["est"],
                    context["V"],
                    q,
                    cfg,
                )
                reasons[reason] += 1
                if power is not None:
                    powers.append(float(np.sum(power)))

            feasible = reasons["ok"]
            count = len(train_indices)
            rate = feasible / count
            rows.append(
                {
                    "q": q,
                    "pmax_w": pmax,
                    "feasible": feasible,
                    "n_train": count,
                    "feasible_rate": rate,
                    "target_met": rate >= args.target_feasibility,
                    "reasons": dict(sorted(reasons.items())),
                    "power_percentiles_w": (
                        np.percentile(
                            powers,
                            [0, 10, 50, 90, 100],
                        ).tolist()
                        if powers
                        else []
                    ),
                }
            )

    result = {
        "scope": "grouped training split only",
        "dataset": str(dataset),
        "M": args.M,
        "K": args.K,
        "sigma_rel": args.sigma_rel,
        "sinr_db": args.sinr_db,
        "noise_w": noise,
        "eps": args.eps,
        "gaussian_q": q_reference,
        "seed": args.seed,
        "split_counts": [int(mask.sum()) for mask in masks],
        "target_feasibility": args.target_feasibility,
        "rows": rows,
    }
    atomic_json(args.output, result)

    print("TRAIN-ONLY FEASIBILITY AUDIT")
    print("Dataset:", dataset)
    print("Split counts:", result["split_counts"])
    print(
        "q pmax_W feasible rate target reasons"
    )
    for row in rows:
        print(
            f"{row['q']:.9g} {row['pmax_w']:.6g} "
            f"{row['feasible']}/{row['n_train']} "
            f"{row['feasible_rate']:.4f} "
            f"{'PASS' if row['target_met'] else 'FAIL'} "
            f"{row['reasons']}"
        )
    print("Output:", Path(args.output).resolve())


if __name__ == "__main__":
    main()
