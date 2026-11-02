#!/usr/bin/env python3
"""Export CP05 only: original exploratory scope plus recorded G1--G4 evidence."""
import argparse
import json
import sys

import numpy as np

import admission_beam as engine
import report_inputs
import run_cp02
import run_cp04


RUNTIME_DEFINITION = "Exhaustive candidate evaluation in CP01 plus oracle selection in CP02; greedy computation in CP02. G1 audits and artifact I/O excluded from algorithm timings/calls."


def verified_cp04(run_dir):
    root, manifest, tasks, alphas, audit = report_inputs.load_cp02(run_dir)
    comparisons, earlier = run_cp04.verify_cp03(root, audit, tasks, alphas)
    decisions = [row for task in tasks for row in run_cp02.decision_rows(task, alphas)]
    stats = run_cp04.build_summary(decisions, comparisons, manifest["N"])
    target = root / "CP04_summary.csv"
    receipt_path = root / "runner_CP04_provenance.json"
    expected = {
        **audit, **earlier,
        "stage": "CP04", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(run_cp04.__file__),
        "report_inputs_sha256": engine.digest(report_inputs.__file__),
        "runtime_definition": RUNTIME_DEFINITION,
        "output_sha256": engine.digest(target),
    }
    if json.loads(receipt_path.read_text(encoding="utf8")) != expected:
        raise ValueError("CP04 source, environment, output or provenance mismatch")
    report_inputs.verify_csv(target, stats)
    audit.update({**earlier, "cp04_sha256": engine.digest(target),
                  "cp04_provenance_sha256": engine.digest(receipt_path)})
    return root, manifest, comparisons, stats, audit


def build_scope(manifest):
    # Keep the JSON schema, strings, and key order from admission_beam.py.
    return {
        "status": "EXPLORATORY_EVALUATION",
        "fixed_q": manifest["parameters"]["q"],
        "objective": "lexicographic max user count, then min transmit power for that count",
        "oracle": "exact across 15 nonempty subsets x enumerated ZF/RZF codebook; not globally optimal beamforming",
        "data_leakage": "Do not tune policies on prior observed geometries and claim independent test",
        "caveats": [
            "Admitted subset recomputes beam and robust coefficients",
            "Outage not certified by finite uncertainty bound",
            "Dropped users are not served, and fairness/throughput not yet evaluated",
            "No statistical independence guaranteed by group names alone",
        ],
    }


def build_evidence(manifest, comparisons, stats):
    oracle = next(r for r in stats if r["method"] == "exhaustive")
    paired = []
    for method in ("forward", "backward"):
        selected = [r for r in comparisons if r["method"] == method]
        measured = next(r for r in stats if r["method"] == method)
        powers = [r["power_ratio_if_same_cardinality"] for r in selected if r["same_cardinality"]]
        paired.append({
            "method": method,
            "cardinality_equal_count": sum(r["cardinality_gap"] == 0 for r in selected),
            "max_user_gap": max(r["cardinality_gap"] for r in selected),
            "positive_same_cardinality_power_pairs": len(powers),
            "mean_power_ratio": float(np.mean(powers)) if powers else None,
            "mean_call_ratio": measured["mean_calls"] / oracle["mean_calls"],
            "mean_runtime_ratio": measured["mean_runtime_ms"] / oracle["mean_runtime_ms"] if oracle["mean_runtime_ms"] > 0 else None,
            "observed_no_cardinality_loss": all(r["cardinality_gap"] == 0 for r in selected),
            "observed_mean_call_reduction": measured["mean_calls"] < oracle["mean_calls"],
            "observed_mean_runtime_reduction": measured["mean_runtime_ms"] < oracle["mean_runtime_ms"],
            "independent_improvement_claim_allowed": False,
        })
    return {
        "n_geometries": manifest["N"],
        "fixed_q": manifest["parameters"]["q"],
        "dataset_path": manifest["parameters"]["dataset"],
        "gates": {"G1": "PASSED", "G2": "PASSED",
                  "G3": "MEASUREMENTS_RECORDED", "G4": "NOT_ESTABLISHED"},
        "service_summary": stats,
        "paired_computational_summary": paired,
        "independent_validation_completed": False,
        "statistical_outage_certificate_claim_allowed": False,
        "globally_optimal_beamforming_claim_allowed": False,
        "fairness_throughput_latency_evaluated": False,
        "interpretation": "Observations on the supplied data only; algorithm timings exclude G1 audits and artifact I/O. Timing measurements are not a controlled independent benchmark.",
        "next_gate": "Lock the method before independent DeepMIMO groups or separate 3GPP evaluation; document simulator/CSI/channel units and report group-level uncertainty. Previously viewed DeepMIMO data remain development data.",
    }


def run(run_dir):
    root, manifest, comparisons, stats, audit = verified_cp04(run_dir)
    scope = build_scope(manifest)
    evidence = build_evidence(manifest, comparisons, stats)
    audit.update({
        "stage": "CP05", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(__file__),
        "report_inputs_sha256": engine.digest(report_inputs.__file__),
        "evaluation_evidence": evidence,
    })
    target = root / "CP05_scope.json"
    receipt_path = root / "runner_CP05_provenance.json"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf8"))
        output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP05 input, runner, evidence or environment changed; use a new run-id")
        if not target.exists() or engine.digest(target) != output_sha:
            raise ValueError("CP05 output differs from its recorded checksum")
    engine.jwrite(target, scope)
    engine.jwrite(receipt_path, {**audit, "output_sha256": engine.digest(target)})
    print(f"CP05 STATUS: {scope['status']}")
    print(f"GEOMETRIES: {manifest['N']}")
    print(f"Q_FIXED: {scope['fixed_q']}")
    print("OBJECTIVE: maximize served users, then minimize power at that user count")
    print("G1: PASSED")
    print("G2: PASSED")
    print("G3: MEASUREMENTS_RECORDED")
    print("G4: NOT_ESTABLISHED")
    for result in evidence["paired_computational_summary"]:
        print(f"{result['method']}: max_user_gap={result['max_user_gap']}, "
              f"mean_call_ratio={result['mean_call_ratio']:.6g}, "
              f"observed_mean_runtime_reduction={result['observed_mean_runtime_reduction']}")
    print("INDEPENDENT_VALIDATION_COMPLETED: False")
    print("STATISTICAL_OUTAGE_CERTIFICATE_CLAIM_ALLOWED: False")
    print(f"JSON: {target}")
    print(f"EVIDENCE: {receipt_path}")
    print("CP05 PASS (scope/evidence checks; EXPLORATORY_EVALUATION)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f"CP05 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
