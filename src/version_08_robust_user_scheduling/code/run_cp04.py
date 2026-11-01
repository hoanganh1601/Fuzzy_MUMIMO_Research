#!/usr/bin/env python3
"""Export CP04 only: service level, solver calls and measured algorithm runtime."""
import argparse
import json
import sys

import numpy as np

import admission_beam as engine
import report_inputs
import run_cp02
import run_cp03


def verify_cp03(root, audit, tasks, alphas):
    target = root / "CP03_paired_comparison.csv"
    receipt_path = root / "runner_CP03_provenance.json"
    expected = {
        **audit, "stage": "CP03", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(run_cp03.__file__),
        "report_inputs_sha256": engine.digest(report_inputs.__file__),
        "output_sha256": engine.digest(target),
    }
    if json.loads(receipt_path.read_text(encoding="utf8")) != expected:
        raise ValueError("CP03 source, environment, output or provenance mismatch")
    comparisons = run_cp03.build_comparisons(tasks, alphas)
    report_inputs.verify_csv(target, comparisons)
    return comparisons, {"cp03_sha256": engine.digest(target),
                         "cp03_provenance_sha256": engine.digest(receipt_path)}


def build_summary(decisions, comparisons, n):
    stats = []
    for method in ("exhaustive", "forward", "backward"):
        selected = [r for r in decisions if r["method"] == method]
        paired = [r for r in comparisons if r["method"] == method]
        if len(selected) != n or len({r["geometry"] for r in selected}) != n:
            raise ValueError(f"Incomplete or duplicate decision rows for {method}")
        if method != "exhaustive" and len(paired) != n:
            raise ValueError(f"Incomplete comparison rows for {method}")
        if any(not 0 <= r["cardinality"] <= 4 or r["calls"] < 0 or
               not np.isfinite(r["runtime_ms"]) or r["runtime_ms"] < 0 for r in selected):
            raise ValueError(f"Invalid service/cost measurements for {method}")
        stats.append({
            "method": method,
            "n_geometries": n,
            "mean_admitted_users": float(np.mean([r["cardinality"] for r in selected])),
            "full_service_fraction": float(np.mean([r["cardinality"] == 4 for r in selected])),
            "at_least_one_fraction": float(np.mean([r["cardinality"] >= 1 for r in selected])),
            "mean_calls": float(np.mean([r["calls"] for r in selected])),
            "mean_runtime_ms": float(np.mean([r["runtime_ms"] for r in selected])),
            # Upstream metric excludes both-zero pairs, as does CP03.same_cardinality.
            "oracle_cardinality_match_fraction": float(np.mean([r["same_cardinality"] for r in paired])) if paired else "",
        })
    return stats


def run(run_dir):
    root, manifest, tasks, alphas, audit = report_inputs.load_cp02(run_dir)
    comparisons, earlier = verify_cp03(root, audit, tasks, alphas)
    decisions = [row for task in tasks for row in run_cp02.decision_rows(task, alphas)]
    stats = build_summary(decisions, comparisons, manifest["N"])
    audit.update({
        **earlier, "stage": "CP04", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(__file__),
        "report_inputs_sha256": engine.digest(report_inputs.__file__),
        "runtime_definition": "Exhaustive candidate evaluation in CP01 plus oracle selection in CP02; greedy computation in CP02. G1 audits and artifact I/O excluded from algorithm timings/calls.",
    })
    target = root / "CP04_summary.csv"
    receipt_path = root / "runner_CP04_provenance.json"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf8"))
        output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP04 input, runner or environment changed; use a new run-id")
        if not target.exists() or engine.digest(target) != output_sha:
            raise ValueError("CP04 output differs from its recorded checksum")
    engine.cwrite(target, stats, list(stats[0]))
    engine.jwrite(receipt_path, {**audit, "output_sha256": engine.digest(target)})
    print(f"CP04 SUMMARY ROWS: {len(stats)}")
    print(f"GEOMETRIES PER METHOD: {manifest['N']}")
    print("METHOD      MEAN_USERS  FULL_4_USERS  AT_LEAST_1  MEAN_CALLS  MEAN_MS  CARD_MATCH")
    for r in stats:
        match = f"{r['oracle_cardinality_match_fraction']:.2%}" if r["method"] != "exhaustive" else "NA"
        print(f"{r['method']:<11} {r['mean_admitted_users']:>10.6f}"
              f" {r['full_service_fraction']:>13.2%} {r['at_least_one_fraction']:>11.2%}"
              f" {r['mean_calls']:>11.3f} {r['mean_runtime_ms']:>8.3f} {match:>11}")
    if any(r["oracle_cardinality"] == 0 for r in comparisons):
        print("Upstream CARD_MATCH counts equal positive cardinality; both-zero pairs are excluded.")
    print("Runtime/calls exclude the additional G1 model audit and artifact I/O.")
    print("These are measurements on the supplied dataset, not independent validation.")
    print(f"CSV: {target}")
    print("CP04 PASS (service/cost summary checks; not independent validation)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f"CP04 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
