#!/usr/bin/env python3
"""Export CP03 only: paired ZF/RZF comparisons on the same geometry/budget."""
import argparse
import json
import sys

import numpy as np

import beam_feasibility as engine
import checkpoint_io
import run_cp02


FIELDS = [
    "geometry", "group", "budget_factor", "alpha", "both_feasible",
    "zf_feasible", "rzf_feasible", "power_ratio_rzf_zf",
]


def verify_cp02(root, audit):
    output = root / "CP02_beam_budget_summary.csv"
    provenance = root / "runner_CP02_provenance.json"
    expected = {
        **audit,
        "runner_sha256": engine.sha(run_cp02.__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
        "output_sha256": engine.sha(output),
    }
    if json.loads(provenance.read_text(encoding="utf8")) != expected:
        raise ValueError("CP02 input, output, runner, or provenance mismatch")
    return {"cp02_sha256": engine.sha(output),
            "cp02_provenance_sha256": engine.sha(provenance)}


def build_pairs(rows, n, alphas, budgets):
    if 0.0 not in alphas or not any(a > 0 for a in alphas):
        raise ValueError("CP03 requires ZF (alpha=0) and at least one RZF beam")
    indexed = {}
    for row in rows:
        indexed.setdefault((row["geometry"], row["budget_factor"]), []).append(row)
    paired = []
    for factor in budgets:
        for i in range(n):
            selected = indexed[(i, factor)]
            zf = next(r for r in selected if r["alpha"] == 0)
            for r in selected:
                if r["alpha"] == 0:
                    continue
                both = bool(r["feasible"] and zf["feasible"])
                ratio = ""
                if both:
                    if zf["p_constrained_w"] <= 0 or r["p_constrained_w"] <= 0:
                        raise ValueError("Nonpositive feasible power; investigate CP01")
                    ratio = r["p_constrained_w"] / zf["p_constrained_w"]
                    if not np.isfinite(ratio):
                        raise ValueError("Nonfinite paired power ratio")
                paired.append({
                    "geometry": i,
                    "group": str(r["group"]),
                    "budget_factor": factor,
                    "alpha": r["alpha"],
                    "both_feasible": int(both),
                    "zf_feasible": zf["feasible"],
                    "rzf_feasible": r["feasible"],
                    "power_ratio_rzf_zf": ratio,
                })
    expected_count = n * (len(alphas) - 1) * len(budgets)
    if len(paired) != expected_count:
        raise ValueError("Unexpected number of paired comparisons")
    return paired


def baseline_summary(paired, alphas, n):
    summary = []
    for alpha in alphas:
        if alpha == 0:
            continue
        selected = [r for r in paired if r["alpha"] == alpha and r["budget_factor"] == 1]
        if len(selected) != n:
            raise ValueError("Incomplete baseline geometry pairs")
        both = sum(r["both_feasible"] for r in selected)
        zf_only = sum(r["zf_feasible"] and not r["rzf_feasible"] for r in selected)
        rzf_only = sum(r["rzf_feasible"] and not r["zf_feasible"] for r in selected)
        neither = sum(not r["zf_feasible"] and not r["rzf_feasible"] for r in selected)
        ratios = [r["power_ratio_rzf_zf"] for r in selected if r["both_feasible"]]
        if both + zf_only + rzf_only + neither != n:
            raise ValueError("Paired feasibility categories do not cover all geometries")
        summary.append({
            "alpha": alpha, "both": both, "zf_only": zf_only,
            "rzf_only": rzf_only, "neither": neither,
            "mean_ratio": float(np.mean(ratios)) if ratios else None,
            "median_ratio": float(np.median(ratios)) if ratios else None,
        })
    return summary


def run(run_dir):
    root, manifest, rows, alphas, budgets, audit = checkpoint_io.load_cp01(run_dir)
    cp02_audit = verify_cp02(root, audit)
    paired = build_pairs(rows, manifest["N"], alphas, budgets)
    baseline = baseline_summary(paired, alphas, manifest["N"]) if 1.0 in budgets else []
    audit.update({
        **cp02_audit,
        "runner_sha256": engine.sha(__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
    })
    provenance_path = root / "runner_CP03_provenance.json"
    target = root / "CP03_paired_ZF_RZF.csv"
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text(encoding="utf8"))
        previous_output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP03 inputs, runner, or environment changed; use a new run-id")
        if not target.exists() or engine.sha(target) != previous_output_sha:
            raise ValueError("Existing CP03 output differs from its recorded checksum")
    engine.write_csv(target, paired, FIELDS)
    engine.write_json(provenance_path, {**audit, "output_sha256": engine.sha(target)})
    print(f"CP03 PAIRED ROWS: {len(paired)}")
    print(f"GEOMETRIES PER RZF/BUDGET: {manifest['N']}")
    if baseline:
        print(f"BASELINE BUDGET: {manifest['config']['pmax']:g} W (factor=1)")
        print("RZF BEAM     BOTH  ZF_ONLY  RZF_ONLY  NEITHER  MEAN_RZF/ZF  MEDIAN_RZF/ZF")
        for item in baseline:
            mean = f"{item['mean_ratio']:.6g}" if item["mean_ratio"] is not None else "NA"
            median = f"{item['median_ratio']:.6g}" if item["median_ratio"] is not None else "NA"
            name = f"RZF_{item['alpha']:g}"
            print(f"{name:<12} {item['both']:>4} {item['zf_only']:>8}"
                  f" {item['rzf_only']:>9} {item['neither']:>8} {mean:>12} {median:>14}")
        print("Power ratios use only BOTH geometries for each RZF/budget.")
    print(f"CSV: {target}")
    print("CP03 PASS (paired comparison checks; not a certificate)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(f"CP03 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
