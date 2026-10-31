#!/usr/bin/env python3
"""Run scan and export CP01 only, using the configuration locked in CP00.

The original engine and CP00 remain unchanged. No CP02--CP06 is produced.
Relative dataset paths in CP00 are interpreted from this package's root.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import scipy

import beam_feasibility as engine


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
OPTIONS = (
    "dataset", "q", "sigma_rel", "sinr_db", "noise", "pmax",
    "alpha_list", "budget_list", "max_geometries",
)
PHYSICAL_STATUSES = {
    "FEASIBLE", "COUPLING_RHO_GE_ONE", "ZERO_ROBUST_DIRECT_GAIN", "POWER_BUDGET",
}


def run(run_dir):
    root = Path(run_dir).resolve()
    manifest_path = root / "CP00_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    config = manifest["config"]
    signature = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()
    if signature != manifest["signature"]:
        raise ValueError("CP00 configuration/signature mismatch")
    if set(config) != set(OPTIONS) | {"dataset_sha256", "code_sha256"}:
        raise ValueError("Unsupported CP00 configuration keys")
    source = Path(engine.__file__).resolve()
    dataset = Path(config["dataset"])
    if not dataset.is_absolute():
        dataset = PACKAGE_ROOT / dataset
    if engine.sha(source) != config["code_sha256"]:
        raise ValueError("Engine changed after CP00; use a new run-id")
    if engine.sha(dataset) != config["dataset_sha256"]:
        raise ValueError("Dataset changed after CP00; use a new run-id")
    H, groups, metadata = engine.load(dataset)
    limit = config["max_geometries"]
    if limit < 0:
        raise ValueError("max_geometries must be nonnegative")
    n = min(len(H), limit) if limit else len(H)
    if n <= 0 or (manifest["N"], manifest["M"], manifest["K"]) != (n, *H.shape[1:]):
        raise ValueError("Dataset dimensions disagree with CP00")
    if manifest["unique_groups"] != len(np.unique(groups[:n])):
        raise ValueError("Group count disagrees with CP00")
    if manifest["data_metadata"] != list(metadata):
        raise ValueError("Metadata disagrees with CP00")
    alphas = sorted(set(float(v) for v in config["alpha_list"].split(",")))
    budgets = sorted(set(float(v) for v in config["budget_list"].split(",")))
    expected_pairs = {(a, b) for a in alphas for b in budgets}
    provenance_path = root / "runner_CP01_provenance.json"
    provenance = {
        "manifest_sha256": engine.sha(manifest_path),
        "signature": signature,
        "runner_sha256": engine.sha(__file__),
        "engine_sha256": engine.sha(source),
        "dataset_sha256": engine.sha(dataset),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
    }
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text(encoding="utf8"))
        if previous != provenance:
            raise ValueError("CP01 runner or environment changed; use a new run-id")
    else:
        engine.write_json(provenance_path, provenance)

    command = [sys.executable, str(source), "--stage", "scan",
               "--output", str(root.parent), "--run-id", root.name]
    for key in OPTIONS:
        command.extend(["--" + key.replace("_", "-"), str(config[key])])
    print(f"CP01 scan: {n} geometries x {len(expected_pairs)} cases", flush=True)
    subprocess.run(command, cwd=PACKAGE_ROOT, check=True)

    rows = []
    for i in range(n):
        path = root / "tasks" / f"{i:07d}.json"
        task = json.loads(path.read_text(encoding="utf8"))
        if task.get("signature") != signature or task.get("complete") is not True:
            raise ValueError(f"Invalid task: {path}")
        task_rows = task["rows"]
        pairs = {(r["alpha"], r["budget_factor"]) for r in task_rows}
        if len(task_rows) != len(expected_pairs) or pairs != expected_pairs:
            raise ValueError(f"Incomplete or duplicate beam/budget cases: {path}")
        for row in task_rows:
            if row["geometry"] != i or row["group"] != str(groups[i]):
                raise ValueError(f"Geometry/group mismatch: {path}")
            if row["feasible"] != int(row["status"] == "FEASIBLE"):
                raise ValueError(f"Inconsistent feasibility flag: {path}")
        rows.extend(task_rows)
    target = root / "CP01_geometry_beam_budget.csv"
    engine.write_csv(target, rows, list(rows[0]))
    statuses = Counter(r["status"] for r in rows)
    print(f"GEOMETRIES: {n}")
    print(f"TOTAL ROWS: {len(rows)}")
    for status, count in sorted(statuses.items()):
        print(f"{status}: {count}")
    print(f"CSV: {target}")
    if set(statuses) - PHYSICAL_STATUSES:
        print("CP01 REVIEW REQUIRED: investigate numerical/rank statuses before CP02")
        return 1
    print("CP01 PASS (checkpoint and numerical checks; not a certificate)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"CP01 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
