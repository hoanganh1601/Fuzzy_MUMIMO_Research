#!/usr/bin/env python3
"""Export CP05 only: the original scope decision and audited diagnosis evidence."""
import argparse
import json
import sys

import beam_feasibility as engine
import checkpoint_io
import run_cp04


def verify_cp04(root, audit):
    earlier = run_cp04.verify_cp03(root, audit)
    output = root / "CP04_geometry_diagnosis.csv"
    provenance = root / "runner_CP04_provenance.json"
    expected = {
        **audit, **earlier,
        "runner_sha256": engine.sha(run_cp04.__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
        "output_sha256": engine.sha(output),
    }
    if json.loads(provenance.read_text(encoding="utf8")) != expected:
        raise ValueError("CP04 input, output, runner, or provenance mismatch")
    return {**earlier, "cp04_sha256": engine.sha(output),
            "cp04_provenance_sha256": engine.sha(provenance)}


def build_scope(manifest):
    # Preserve the scope, schema, and wording of the original report exactly.
    return {
        "status": "DIAGNOSTIC_ONLY",
        "n_geometries": manifest["N"],
        "groups": manifest["unique_groups"],
        "q_fixed": manifest["config"]["q"],
        "note": "No adaptive margin or post-test beam selection claim. ZF and RZF are candidate fixed beams. Full channel data and independent validation required. No claim of globally optimal beamforming.",
        "next_gate": "If substantial coupling failures persist for all beams, examine scheduling or multiuser grouping rather than CSI margin.",
    }


def run(run_dir):
    root, manifest, rows, alphas, budgets, audit = checkpoint_io.load_cp01(run_dir)
    earlier = verify_cp04(root, audit)
    _, statistics = run_cp04.build_diagnosis(rows, manifest["N"], alphas, budgets)
    decision = build_scope(manifest)
    evidence = {
        "baseline_budget_w": manifest["config"]["pmax"],
        **statistics,
        "numerical_review_required": False,
        "statistical_certificate_claim_allowed": False,
        "globally_optimal_beamforming_claim_allowed": False,
        "post_test_best_alpha_claim_allowed": False,
        "scope": "Descriptive diagnostics on the supplied dataset; not an independent certification holdout.",
        "next_steps": [
            "For power-limited geometries, inspect channel/noise unit consistency and the predeclared budget sensitivity results.",
            "For coupling or zero-gain failures across the grid, examine scheduling, user grouping, or a broader beam space.",
            "Lock any new beam rule on development data, then evaluate it on independent data before making a validation claim.",
        ],
    }
    audit.update({
        **earlier,
        "runner_sha256": engine.sha(__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
        "diagnostic_evidence": evidence,
    })
    provenance_path = root / "runner_CP05_provenance.json"
    target = root / "CP05_scope_and_decision.json"
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text(encoding="utf8"))
        previous_output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP05 inputs, runner, or environment changed; use a new run-id")
        if not target.exists() or engine.sha(target) != previous_output_sha:
            raise ValueError("Existing CP05 output differs from its recorded checksum")
    engine.write_json(target, decision)
    engine.write_json(provenance_path, {**audit, "output_sha256": engine.sha(target)})
    print(f"CP05 STATUS: {decision['status']}")
    print(f"GEOMETRIES: {manifest['N']}")
    print(f"Q_FIXED: {decision['q_fixed']}")
    print(f"BASELINE BUDGET: {evidence['baseline_budget_w']:g} W (factor=1)")
    print(f"ANY_CANDIDATE_BEAM_FEASIBLE: {statistics['any_beam_feasible']}")
    print(f"ALL_CANDIDATE_BEAMS_FAIL: {statistics['all_beams_fail']}")
    print(f"  WITH_SOME_POWER_BUDGET_CASE: {statistics['failed_with_some_power_budget_case']}")
    print(f"  ONLY_COUPLING_OR_ZERO_GAIN: {statistics['failed_only_coupling_or_zero_gain']}")
    print("STATISTICAL_CERTIFICATE_CLAIM_ALLOWED: False")
    print("GLOBALLY_OPTIMAL_BEAMFORMING_CLAIM_ALLOWED: False")
    for i, next_step in enumerate(evidence["next_steps"], 1):
        print(f"NEXT_STEP_{i}: {next_step}")
    print(f"JSON: {target}")
    print(f"EVIDENCE: {provenance_path}")
    print("CP05 PASS (scope and evidence checks; DIAGNOSTIC_ONLY, not a certificate)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"CP05 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
