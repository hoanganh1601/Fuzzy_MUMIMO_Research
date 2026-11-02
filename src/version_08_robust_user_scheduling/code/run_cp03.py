#!/usr/bin/env python3
"""Export CP03 only: compare greedy/exhaustive on the same geometry."""
import argparse
import json
import sys

import numpy as np

import admission_beam as engine
import report_inputs


FIELDS = [
    "geometry", "group", "method", "oracle_cardinality", "greedy_cardinality",
    "cardinality_gap", "same_cardinality", "power_ratio_if_same_cardinality",
    "oracle_calls", "greedy_calls",
]


def build_comparisons(tasks, alphas):
    comparisons = []
    for task in tasks:
        oracle = task["oracle"]
        oracle_cardinality = oracle["cardinality"] if oracle else 0
        for greedy in task["greedy"]:
            choice = greedy["choice"]
            card = choice["cardinality"] if choice else 0
            gap = oracle_cardinality - card
            if gap < 0:
                raise ValueError("Greedy cardinality exceeds the exhaustive reference")
            same_positive = bool(oracle is not None and card == oracle_cardinality)
            ratio = ""
            if same_positive:
                if choice is None or min(oracle["p_req_w"], choice["p_req_w"]) <= 0:
                    raise ValueError("Invalid power in a same-cardinality comparison")
                ratio = choice["p_req_w"] / oracle["p_req_w"]
                if not np.isfinite(ratio) or ratio < 1 - 1e-8:
                    raise ValueError("Greedy power contradicts the exhaustive minimum")
            comparisons.append({
                "geometry": task["geometry"], "group": task["group"],
                "method": greedy["method"], "oracle_cardinality": oracle_cardinality,
                "greedy_cardinality": card, "cardinality_gap": gap,
                # Preserve upstream semantics: no power comparison if both serve zero.
                "same_cardinality": int(same_positive),
                "power_ratio_if_same_cardinality": ratio,
                "oracle_calls": 15 * len(alphas), "greedy_calls": greedy["calls"],
            })
    return comparisons


def run(run_dir):
    root, manifest, tasks, alphas, audit = report_inputs.load_cp02(run_dir)
    comparisons = build_comparisons(tasks, alphas)
    if len(comparisons) != 2 * manifest["N"]:
        raise ValueError("Unexpected number of CP03 pairs")
    for method in ("forward", "backward"):
        selected = [r for r in comparisons if r["method"] == method]
        if len(selected) != manifest["N"] or len({r["geometry"] for r in selected}) != manifest["N"]:
            raise ValueError(f"Missing or duplicate geometry pairs for {method}")
    audit.update({
        "stage": "CP03", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(__file__),
        "report_inputs_sha256": engine.digest(report_inputs.__file__),
    })
    target = root / "CP03_paired_comparison.csv"
    receipt_path = root / "runner_CP03_provenance.json"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf8"))
        output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP03 input, runner or environment changed; use a new run-id")
        if not target.exists() or engine.digest(target) != output_sha:
            raise ValueError("CP03 output differs from its recorded checksum")
    engine.cwrite(target, comparisons, FIELDS)
    engine.jwrite(receipt_path, {**audit, "output_sha256": engine.digest(target)})
    print(f"CP03 PAIRED ROWS: {len(comparisons)}")
    print(f"GEOMETRIES PER GREEDY METHOD: {manifest['N']}")
    print("METHOD     CARD_MATCH  MAX_USER_GAP  POWER_PAIRS  MEAN_POWER_RATIO  MEAN_CALL_RATIO")
    for method in ("forward", "backward"):
        selected = [r for r in comparisons if r["method"] == method]
        matches = sum(r["cardinality_gap"] == 0 for r in selected)
        ratios = [r["power_ratio_if_same_cardinality"] for r in selected if r["same_cardinality"]]
        power = f"{float(np.mean(ratios)):.6g}" if ratios else "NA"
        calls = float(np.mean([r["greedy_calls"] / r["oracle_calls"] for r in selected]))
        max_gap = max(r["cardinality_gap"] for r in selected)
        print(f"{method:<10} {matches:>10} {max_gap:>13} {len(ratios):>12} {power:>17} {calls:>16.6g}")
    print("Power ratios use only equal positive user counts; call ratios are greedy/exhaustive.")
    print("Runtime measurements are retained in CP02; method summaries belong to CP04.")
    print(f"CSV: {target}")
    print("CP03 PASS (paired comparison checks; not an independent improvement claim)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f"CP03 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
