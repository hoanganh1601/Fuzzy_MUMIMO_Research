#!/usr/bin/env python3
"""Export CP04 only: diagnose each geometry at the locked baseline budget."""
import argparse
from collections import Counter
import json
import sys

import beam_feasibility as engine
import checkpoint_io
import run_cp03


FIELDS = [
    "geometry", "group", "n_feasible_beams", "min_rho", "best_alpha",
    "best_power_w", "all_beams_fail",
]


def verify_cp03(root, audit):
    earlier = run_cp03.verify_cp02(root, audit)
    output = root / "CP03_paired_ZF_RZF.csv"
    provenance = root / "runner_CP03_provenance.json"
    expected = {
        **audit, **earlier,
        "runner_sha256": engine.sha(run_cp03.__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
        "output_sha256": engine.sha(output),
    }
    if json.loads(provenance.read_text(encoding="utf8")) != expected:
        raise ValueError("CP03 input, output, runner, or provenance mismatch")
    return {**earlier, "cp03_sha256": engine.sha(output),
            "cp03_provenance_sha256": engine.sha(provenance)}


def build_diagnosis(rows, n, alphas, budgets):
    if 1.0 not in budgets:
        raise ValueError("CP04 requires baseline budget factor=1 in locked CP00")
    baseline = {i: [] for i in range(n)}
    for row in rows:
        if row["budget_factor"] == 1:
            baseline[row["geometry"]].append(row)
    diagnosis = []
    failed_with_budget_case = 0
    failed_only_coupling_or_zero = 0
    all_beams_coupling = 0
    for i in range(n):
        selected = baseline[i]
        if len(selected) != len(alphas) or {r["alpha"] for r in selected} != set(alphas):
            raise ValueError(f"Incomplete baseline beams for geometry {i}")
        best = min((r for r in selected if r["feasible"]),
                   key=lambda r: r["p_constrained_w"], default=None)
        diagnosis.append({
            "geometry": i,
            "group": str(selected[0]["group"]),
            "n_feasible_beams": sum(r["feasible"] for r in selected),
            "min_rho": min((r["rho"] for r in selected if r["rho"] != ""), default=""),
            "best_alpha": best["alpha"] if best else "",
            "best_power_w": best["p_constrained_w"] if best else "",
            "all_beams_fail": int(best is None),
        })
        if best is None:
            statuses = {r["status"] for r in selected}
            if "POWER_BUDGET" in statuses:
                failed_with_budget_case += 1
            elif statuses <= {"COUPLING_RHO_GE_ONE", "ZERO_ROBUST_DIRECT_GAIN"}:
                failed_only_coupling_or_zero += 1
            else:
                raise ValueError(f"Unclassified failure in geometry {i}: {statuses}")
            if statuses == {"COUPLING_RHO_GE_ONE"}:
                all_beams_coupling += 1
    failed = sum(r["all_beams_fail"] for r in diagnosis)
    if failed != failed_with_budget_case + failed_only_coupling_or_zero:
        raise ValueError("Failure categories do not cover failed geometries")
    statistics = {
        "any_beam_feasible": n - failed,
        "all_beams_fail": failed,
        "failed_with_some_power_budget_case": failed_with_budget_case,
        "failed_only_coupling_or_zero_gain": failed_only_coupling_or_zero,
        "all_beams_coupling": all_beams_coupling,
    }
    return diagnosis, statistics


def run(run_dir):
    root, manifest, rows, alphas, budgets, audit = checkpoint_io.load_cp01(run_dir)
    earlier = verify_cp03(root, audit)
    diagnosis, statistics = build_diagnosis(rows, manifest["N"], alphas, budgets)
    audit.update({
        **earlier,
        "runner_sha256": engine.sha(__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
    })
    provenance_path = root / "runner_CP04_provenance.json"
    target = root / "CP04_geometry_diagnosis.csv"
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text(encoding="utf8"))
        previous_output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP04 inputs, runner, or environment changed; use a new run-id")
        if not target.exists() or engine.sha(target) != previous_output_sha:
            raise ValueError("Existing CP04 output differs from its recorded checksum")
    engine.write_csv(target, diagnosis, FIELDS)
    engine.write_json(provenance_path, {**audit, "output_sha256": engine.sha(target)})
    print(f"CP04 GEOMETRY ROWS: {len(diagnosis)}")
    print(f"BASELINE BUDGET: {manifest['config']['pmax']:g} W (factor=1)")
    print(f"ANY_CANDIDATE_BEAM_FEASIBLE: {statistics['any_beam_feasible']}")
    print(f"ALL_CANDIDATE_BEAMS_FAIL: {statistics['all_beams_fail']}")
    print(f"  WITH_SOME_POWER_BUDGET_CASE: {statistics['failed_with_some_power_budget_case']}")
    print(f"  ONLY_COUPLING_OR_ZERO_GAIN: {statistics['failed_only_coupling_or_zero_gain']}")
    print(f"    ALL_BEAMS_COUPLING_SUBSET: {statistics['all_beams_coupling']}")
    distribution = Counter(r["n_feasible_beams"] for r in diagnosis)
    print("FEASIBLE_BEAMS  GEOMETRIES")
    for count in range(len(alphas) + 1):
        print(f"{count:>14} {distribution[count]:>11}")
    print("best_alpha is a per-geometry diagnostic within the fixed grid, not a validated beam rule.")
    print(f"CSV: {target}")
    print("CP04 PASS (geometry diagnosis checks; not a certificate)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"CP04 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
