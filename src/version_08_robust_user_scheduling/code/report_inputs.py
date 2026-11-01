"""Read verified CP01/CP02 artifacts for the separate reporting stages."""
import csv
import json

import numpy as np

import admission_beam as engine
import model_audit
import run_cp02
import scheduling_checkpoints as checkpoints


def verify_csv(path, rows):
    with path.open(newline="", encoding="utf8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(rows[0]):
            raise ValueError(f"CSV schema disagrees with checkpoint rows: {path.name}")
        saved = list(reader)
    expected = [{k: "" if v is None else str(v) for k, v in row.items()} for row in rows]
    if saved != expected:
        raise ValueError(f"CSV differs from task checkpoints: {path.name}")


def load_cp02(run_dir):
    root, manifest, _, groups, alphas, _, audit = checkpoints.load_run(run_dir)
    tasks, earlier = run_cp02.verified_cp01(root, manifest, groups, alphas, audit)
    target = root / "CP02_oracle_greedy_decisions.csv"
    receipt_path = root / "runner_CP02_provenance.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf8"))
    g1 = receipt["model_audit"]
    expected = {
        **audit, **earlier,
        "stage": "CP02", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(run_cp02.__file__),
        "helper_sha256": engine.digest(checkpoints.__file__),
        "model_audit_sha256": engine.digest(model_audit.__file__),
        "model_audit": g1, "output_sha256": engine.digest(target),
    }
    if receipt != expected:
        raise ValueError("CP02 source, environment, output or provenance mismatch")
    candidate_count = manifest["N"] * 15 * len(alphas)
    stable = sum(r["status"] in ("FEASIBLE", "POWER_BUDGET") for task in tasks for r in task["rows"])
    if (g1["gate"] != "G1_PASS" or g1["candidate_count"] != candidate_count or
            g1["lp_checks"] != stable or g1["budget_monotonicity_checks"] != candidate_count or
            g1["extra_engine_solve_calls"] != 2 * candidate_count or
            g1["audit_calls_excluded_from_algorithm_calls"] is not True):
        raise ValueError("Incomplete G1 audit in CP02 provenance")
    for key, threshold in (("max_relative_lp_gap", 1e-5),
                           ("max_scaled_analytic_violation", 1e-7),
                           ("max_scaled_lp_violation", 1e-7)):
        if not np.isfinite(g1[key]) or not 0 <= g1[key] <= threshold:
            raise ValueError(f"G1 numerical gate failed: {key}")
    decisions = []
    for task in tasks:
        if task.get("complete") is not True:
            raise ValueError(f"CP02 incomplete for geometry {task['geometry']}")
        run_cp02.validate_choices(task)
        decisions.extend(run_cp02.decision_rows(task, alphas))
    verify_csv(target, decisions)
    audit.update({**earlier, "cp02_sha256": engine.digest(target),
                  "cp02_provenance_sha256": engine.digest(receipt_path)})
    return root, manifest, tasks, alphas, audit
