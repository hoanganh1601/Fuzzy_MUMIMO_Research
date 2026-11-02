"""Validate locked inputs and candidate checkpoints without running later stages."""
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np
import scipy

import admission_beam as engine


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
OPTIONS = {
    "dataset", "q", "sigma_rel", "sinr_db", "noise", "pmax", "alpha_list", "limit",
}
PHYSICAL_STATUSES = {
    "FEASIBLE", "POWER_BUDGET", "COUPLING_RHO_GE_ONE", "ZERO_ROBUST_DIRECT_GAIN",
}


def load_run(run_dir):
    root = Path(run_dir).resolve()
    manifest_path = root / "CP00_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    parameters = manifest["parameters"]
    if set(parameters) != OPTIONS | {"sha_data", "sha_code"}:
        raise ValueError("Unsupported CP00 parameter schema")
    signature = hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
    if manifest["signature"] != signature:
        raise ValueError("CP00 signature does not match its parameters")
    dataset = Path(parameters["dataset"])
    if not dataset.is_absolute():
        dataset = PACKAGE_ROOT / dataset
    if engine.digest(dataset) != parameters["sha_data"]:
        raise ValueError("Dataset changed after CP00; use a new run-id")
    if engine.digest(engine.__file__) != parameters["sha_code"]:
        raise ValueError("Engine changed after CP00; use a new run-id")
    numeric = [parameters[k] for k in ("q", "sigma_rel", "sinr_db", "noise", "pmax")]
    if not np.isfinite(numeric).all():
        raise ValueError("Parameters must be finite")
    if parameters["q"] < 0 or min(parameters[k] for k in ("sigma_rel", "noise", "pmax")) <= 0:
        raise ValueError("Invalid physical parameters")
    limit = parameters["limit"]
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a nonnegative integer")
    H, groups, metadata = engine.load(dataset)
    n = min(limit, len(H)) if limit else len(H)
    if n <= 0 or (manifest["N"], manifest["M"], manifest["K"]) != (n, H.shape[1], 4):
        raise ValueError("Dataset dimensions disagree with CP00")
    if manifest["groups"] != len(np.unique(groups[:n])) or manifest["metadata"] != list(metadata):
        raise ValueError("Dataset groups/metadata disagree with CP00")
    alphas = sorted(set(float(v) for v in parameters["alpha_list"].split(",")))
    if not alphas or not np.isfinite(alphas).all() or min(alphas) < 0:
        raise ValueError("Invalid alpha grid")
    cfg = {"q": parameters["q"], "sigma": parameters["sigma_rel"],
           "gamma": 10 ** (parameters["sinr_db"] / 10),
           "noise": parameters["noise"], "pmax": parameters["pmax"]}
    if not np.isfinite(cfg["gamma"]) or cfg["gamma"] <= 0:
        raise ValueError("Invalid SINR threshold")
    audit = {
        "manifest_sha256": engine.digest(manifest_path),
        "signature": signature,
        "engine_sha256": parameters["sha_code"],
        "dataset_sha256": parameters["sha_data"],
        "python_version": sys.version,
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
    }
    return root, manifest, H, groups, alphas, cfg, audit


def checked_rows(task, geometry, group, signature, alphas):
    if task.get("signature") != signature:
        raise ValueError(f"Task {geometry}: signature mismatch")
    if task.get("cp01_complete") is not True and task.get("complete") is not True:
        raise ValueError(f"Task {geometry}: CP01 is incomplete")
    if task["geometry"] != geometry or task["group"] != str(group):
        raise ValueError(f"Task {geometry}: geometry/group mismatch")
    subsets = {"".join(map(str, s)) for size in range(1, 5)
               for s in itertools.combinations(range(4), size)}
    expected = {(subset, alpha) for subset in subsets for alpha in alphas}
    rows = task["rows"]
    actual = {(r["subset"], r["alpha"]) for r in rows}
    if len(rows) != len(expected) or actual != expected:
        raise ValueError(f"Task {geometry}: missing or duplicate subset/beam candidates")
    for row in rows:
        if row["cardinality"] != len(row["subset"]):
            raise ValueError(f"Task {geometry}: inconsistent subset cardinality")
        expected_beam = "ZF" if row["alpha"] == 0 else "RZF"
        if row["beam"] != expected_beam:
            raise ValueError(f"Task {geometry}: inconsistent beam label")
        if not np.isfinite(row["runtime_ms"]) or row["runtime_ms"] < 0:
            raise ValueError(f"Task {geometry}: invalid runtime")
    return rows
