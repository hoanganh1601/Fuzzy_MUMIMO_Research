#!/usr/bin/env python3
"""Audit G1, choose exhaustive/greedy schedules, and export CP02 only."""
import argparse
import csv
import json
import sys
import time

import numpy as np

import admission_beam as engine
import model_audit
import run_cp01
import scheduling_checkpoints as checkpoints


def verified_cp01(root, manifest, groups, alphas, audit):
    csv_path = root / "CP01_all_subset_beam.csv"
    receipt_path = root / "runner_CP01_provenance.json"
    expected = {
        **audit, "stage": "CP01", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(run_cp01.__file__),
        "helper_sha256": engine.digest(checkpoints.__file__),
        "output_sha256": engine.digest(csv_path),
    }
    if json.loads(receipt_path.read_text(encoding="utf8")) != expected:
        raise ValueError("CP01 source, environment, output or provenance mismatch")
    tasks, flat = [], []
    for i in range(manifest["N"]):
        task = json.loads((root / "tasks" / f"{i:07d}.json").read_text(encoding="utf8"))
        rows = checkpoints.checked_rows(task, i, groups[i], manifest["signature"], alphas)
        if {r["status"] for r in rows} - checkpoints.PHYSICAL_STATUSES:
            raise ValueError(f"CP01 numerical/rank status requires review in geometry {i}")
        flat.extend(dict(geometry=i, group=str(groups[i]), **r) for r in rows)
        tasks.append(task)
    with csv_path.open(newline="", encoding="utf8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(flat[0]):
            raise ValueError("CP01 CSV schema differs from task rows")
        saved = list(reader)
    serialized = [{k: "" if v is None else str(v) for k, v in row.items()} for row in flat]
    if saved != serialized:
        raise ValueError("CP01 CSV differs from per-geometry task rows")
    return tasks, {"cp01_sha256": engine.digest(csv_path),
                   "cp01_provenance_sha256": engine.digest(receipt_path)}


def validate_choices(task):
    feasible = [r for r in task["rows"] if r["status"] == "FEASIBLE"]
    oracle = task["oracle"]
    if not feasible:
        if oracle is not None:
            raise ValueError("Oracle selected an infeasible candidate")
    else:
        max_cardinality = max(r["cardinality"] for r in feasible)
        minimum_power = min(r["p_req_w"] for r in feasible if r["cardinality"] == max_cardinality)
        if oracle is None or oracle["cardinality"] != max_cardinality or not np.isclose(
                oracle["p_req_w"], minimum_power, rtol=1e-10, atol=0):
            raise ValueError("Oracle violates lexicographic cardinality/power objective")
    if {g["method"] for g in task["greedy"]} != {"forward", "backward"} or len(task["greedy"]) != 2:
        raise ValueError("Missing or duplicate greedy methods")
    choices = [("exhaustive", oracle)] + [(g["method"], g["choice"]) for g in task["greedy"]]
    for method, choice in choices:
        if choice is None:
            continue
        matches = [r for r in feasible if (r["subset"], r["alpha"]) == (choice["subset"], choice["alpha"])]
        if len(matches) != 1 or choice["cardinality"] != matches[0]["cardinality"] or not np.isclose(
                choice["p_req_w"], matches[0]["p_req_w"], rtol=1e-8, atol=0):
            raise ValueError(f"{method} choice does not match a feasible CP01 candidate")
        if oracle is None or choice["cardinality"] > oracle["cardinality"]:
            raise ValueError(f"{method} cardinality exceeds the exhaustive reference")
    for g in task["greedy"]:
        if not isinstance(g["calls"], int) or g["calls"] < 0 or not np.isfinite(g["runtime_ms"]) or g["runtime_ms"] < 0:
            raise ValueError("Invalid greedy runtime/call count")
    if not np.isfinite(task["oracle_runtime_ms"]) or task["oracle_runtime_ms"] < 0:
        raise ValueError("Invalid exhaustive runtime")


def decision_rows(task, alphas):
    choices = [("exhaustive", task["oracle"], 15 * len(alphas), task["oracle_runtime_ms"])]
    choices.extend((g["method"], g["choice"], g["calls"], g["runtime_ms"]) for g in task["greedy"])
    return [{
        "geometry": task["geometry"], "group": task["group"], "method": method,
        "cardinality": choice["cardinality"] if choice else 0,
        "subset": choice["subset"] if choice else "",
        "alpha": choice["alpha"] if choice else "",
        "power_w": choice["p_req_w"] if choice else "",
        "calls": calls, "runtime_ms": runtime,
    } for method, choice, calls, runtime in choices]


def run(run_dir):
    root, manifest, H, groups, alphas, cfg, audit = checkpoints.load_run(run_dir)
    tasks, earlier = verified_cp01(root, manifest, groups, alphas, audit)
    audit.update({
        **earlier, "stage": "CP02", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(__file__),
        "helper_sha256": engine.digest(checkpoints.__file__),
        "model_audit_sha256": engine.digest(model_audit.__file__),
    })
    receipt_path = root / "runner_CP02_provenance.json"
    target = root / "CP02_oracle_greedy_decisions.csv"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf8"))
        output_sha = previous.pop("output_sha256")
        g1 = previous.pop("model_audit")
        if previous != audit or g1.get("gate") != "G1_PASS":
            raise ValueError("CP02 input, runner, audit or environment changed; use a new run-id")
        if output_sha is not None and (not target.exists() or engine.digest(target) != output_sha):
            raise ValueError("CP02 output differs from its recorded checksum")
    else:
        print("G1 model audit before CP02 scheduling decisions", flush=True)
        g1 = model_audit.audit_candidates(H, tasks, cfg, verbose=True)
        engine.jwrite(receipt_path, {**audit, "model_audit": g1, "output_sha256": None})
    print(f"G1 PASS: {g1['candidate_count']} candidates, {g1['lp_checks']} scaled LP checks, "
          f"{g1['budget_monotonicity_checks']} budget monotonicity checks", flush=True)
    rows = []
    for task in tasks:
        i = task["geometry"]
        if task.get("complete") is not True:
            started = time.perf_counter()
            task["oracle"] = engine.oracle(task["rows"])
            task["oracle_runtime_ms"] = task["exhaustive_runtime_ms"] + (time.perf_counter() - started) * 1000
            greedy = []
            for mode in ("forward", "backward"):
                started = time.perf_counter()
                choice, calls = engine.greedy(H[i], alphas, cfg, mode)
                greedy.append({"method": mode, "choice": choice, "calls": calls,
                               "runtime_ms": (time.perf_counter() - started) * 1000})
            task["greedy"] = greedy
            validate_choices(task)
            task["cp02_complete"] = True
            task["complete"] = True
            engine.jwrite(root / "tasks" / f"{i:07d}.json", task)
        else:
            validate_choices(task)
        rows.extend(decision_rows(task, alphas))
        if (i + 1) % 10 == 0 or i + 1 == manifest["N"]:
            print(f"CP02 progress: {i + 1}/{manifest['N']} geometries", flush=True)
    if len(rows) != 3 * manifest["N"]:
        raise ValueError("Unexpected CP02 decision count")
    engine.cwrite(target, rows, list(rows[0]))
    engine.jwrite(receipt_path, {**audit, "model_audit": g1, "output_sha256": engine.digest(target)})
    print(f"GEOMETRIES: {manifest['N']}")
    print("METHODS: exhaustive, forward, backward")
    print(f"CP02 ROWS: {len(rows)}")
    print(f"G2 LEXICOGRAPHIC CHECKS: {manifest['N']}")
    print(f"CSV: {target}")
    print("CP02 PASS (G1 model audit and G2 decision checks; not independent validation)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, np.linalg.LinAlgError) as exc:
        print(f"CP02 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
