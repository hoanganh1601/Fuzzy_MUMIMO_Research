#!/usr/bin/env python3
"""Export CP02 only from verified CP01 rows, without running any solver."""
import argparse
import json
import sys

import numpy as np

import beam_feasibility as engine
import checkpoint_io


def summarize(rows, alphas, budgets):
    summary = []
    for alpha in alphas:
        for factor in budgets:
            selected = [r for r in rows if r["alpha"] == alpha and r["budget_factor"] == factor]
            feasible = [r for r in selected if r["feasible"]]
            item = {
                "alpha": alpha,
                "beam": selected[0]["beam"],
                "budget_factor": factor,
                "n": len(selected),
                "feasible": len(feasible),
                "feasible_fraction": len(feasible) / len(selected),
                "mean_feasible_power_w": np.mean([r["p_constrained_w"] for r in feasible]) if feasible else "",
                "mean_runtime_ms": np.mean([r["runtime_ms"] for r in selected]),
            }
            statuses = ("COUPLING_RHO_GE_ONE", "ZERO_ROBUST_DIRECT_GAIN", "POWER_BUDGET", "FEASIBLE")
            for status in statuses:
                item["n_" + status.lower()] = sum(r["status"] == status for r in selected)
            item["n_other"] = len(selected) - sum(item["n_" + s.lower()] for s in statuses)
            summary.append(item)
    return summary


def run(run_dir):
    root, manifest, rows, alphas, budgets, audit = checkpoint_io.load_cp01(run_dir)
    summary = summarize(rows, alphas, budgets)
    if len(summary) != len(alphas) * len(budgets) or any(r["n"] != manifest["N"] for r in summary):
        raise ValueError("Unexpected number of geometry/beam/budget cases")
    audit.update({
        "runner_sha256": engine.sha(__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
    })
    provenance_path = root / "runner_CP02_provenance.json"
    target = root / "CP02_beam_budget_summary.csv"
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text(encoding="utf8"))
        previous_output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP02 inputs, runner, or environment changed; use a new run-id")
        if not target.exists() or engine.sha(target) != previous_output_sha:
            raise ValueError("Existing CP02 output differs from its recorded checksum")
    engine.write_csv(target, summary, list(summary[0]))
    engine.write_json(provenance_path, {**audit, "output_sha256": engine.sha(target)})
    print(f"CP02 SUMMARY ROWS: {len(summary)}")
    print(f"GEOMETRIES PER ROW: {manifest['N']}")
    print(f"TOTAL OTHER STATUSES: {sum(r['n_other'] for r in summary)}")
    if 1.0 in budgets:
        print(f"BASELINE BUDGET: {manifest['config']['pmax']:g} W (factor=1)")
        print("BEAM         FEASIBLE/N   RATE      RHO_FAIL  ZERO_GAIN  BUDGET_FAIL")
        for r in summary:
            if r["budget_factor"] == 1.0:
                ratio = f"{r['feasible']}/{r['n']}"
                print(f"{r['beam']:<12} {ratio:<12} {r['feasible_fraction']:>7.2%}"
                      f" {r['n_coupling_rho_ge_one']:>9} {r['n_zero_robust_direct_gain']:>10}"
                      f" {r['n_power_budget']:>12}")
    print(f"CSV: {target}")
    print("CP02 PASS (summary checks; not a certificate)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"CP02 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
