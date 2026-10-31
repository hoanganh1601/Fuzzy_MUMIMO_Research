"""Verified CP01 inputs shared by the separate reporting checkpoints."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import scipy

import beam_feasibility as engine
import run_cp01


def environment():
    return {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
    }


def load_cp01(run_dir):
    """Check CP00, provenance, dataset, and every CP01 row against its task."""
    root = Path(run_dir).resolve()
    manifest_path = root / "CP00_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    config = manifest["config"]
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    if signature != manifest["signature"]:
        raise ValueError("CP00 configuration/signature mismatch")
    if set(config) != set(run_cp01.OPTIONS) | {"dataset_sha256", "code_sha256"}:
        raise ValueError("Unsupported CP00 configuration keys")
    dataset = Path(config["dataset"])
    if not dataset.is_absolute():
        dataset = run_cp01.PACKAGE_ROOT / dataset
    source_sha = engine.sha(engine.__file__)
    dataset_sha = engine.sha(dataset)
    if source_sha != config["code_sha256"] or dataset_sha != config["dataset_sha256"]:
        raise ValueError("Dataset or engine changed after CP00")
    provenance_path = root / "runner_CP01_provenance.json"
    expected = {
        "manifest_sha256": engine.sha(manifest_path),
        "signature": signature,
        "runner_sha256": engine.sha(run_cp01.__file__),
        "engine_sha256": source_sha,
        "dataset_sha256": dataset_sha,
        **environment(),
    }
    if json.loads(provenance_path.read_text(encoding="utf8")) != expected:
        raise ValueError("CP01 provenance, runner, or environment mismatch")

    H, groups, metadata = engine.load(dataset)
    limit = config["max_geometries"]
    if limit < 0:
        raise ValueError("Invalid geometry limit")
    n = min(len(H), limit) if limit else len(H)
    if n <= 0 or (manifest["N"], manifest["M"], manifest["K"]) != (n, *H.shape[1:]):
        raise ValueError("Dataset dimensions disagree with CP00")
    if manifest["unique_groups"] != len(np.unique(groups[:n])):
        raise ValueError("Group count disagrees with CP00")
    if manifest["data_metadata"] != list(metadata):
        raise ValueError("Metadata disagrees with CP00")
    alphas = sorted(set(float(v) for v in config["alpha_list"].split(",")))
    budgets = sorted(set(float(v) for v in config["budget_list"].split(",")))
    pairs = {(a, b) for a in alphas for b in budgets}
    rows = []
    for i in range(n):
        task_path = root / "tasks" / f"{i:07d}.json"
        task = json.loads(task_path.read_text(encoding="utf8"))
        if task.get("signature") != signature or task.get("complete") is not True:
            raise ValueError(f"Invalid task: {task_path}")
        task_rows = task["rows"]
        if len(task_rows) != len(pairs) or {
            (r["alpha"], r["budget_factor"]) for r in task_rows
        } != pairs:
            raise ValueError(f"Incomplete or duplicate cases: {task_path}")
        for row in task_rows:
            if row["geometry"] != i or row["group"] != str(groups[i]):
                raise ValueError(f"Geometry/group mismatch: {task_path}")
            if row["status"] not in run_cp01.PHYSICAL_STATUSES:
                raise ValueError(f"Numerical/rank status requires review: {row['status']}")
            if row["feasible"] != int(row["status"] == "FEASIBLE"):
                raise ValueError(f"Inconsistent feasibility flag: {task_path}")
        rows.extend(task_rows)

    csv_path = root / "CP01_geometry_beam_budget.csv"
    with csv_path.open(newline="", encoding="utf8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(rows[0]):
            raise ValueError("CP01 CSV columns disagree with task schema")
        saved_rows = list(reader)
    serialized = [{k: str(v) for k, v in row.items()} for row in rows]
    if saved_rows != serialized:
        raise ValueError("CP01 CSV disagrees with geometry task checkpoints")
    audit = {
        "manifest_sha256": engine.sha(manifest_path),
        "cp01_sha256": engine.sha(csv_path),
        "cp01_provenance_sha256": engine.sha(provenance_path),
        "signature": signature,
        "engine_sha256": source_sha,
        "dataset_sha256": dataset_sha,
        **environment(),
    }
    return root, manifest, rows, alphas, budgets, audit
