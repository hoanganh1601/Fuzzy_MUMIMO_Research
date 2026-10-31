#!/usr/bin/env python3
"""Seal CP00--CP05 and their provenance, or verify an existing result bundle."""
import argparse
import csv
import json
from pathlib import Path
import sys

import beam_feasibility as engine
import checkpoint_io
import run_cp04
import run_cp05


ARTIFACTS = sorted([
    "CP00_manifest.json", "CP01_geometry_beam_budget.csv",
    "CP02_beam_budget_summary.csv", "CP03_paired_ZF_RZF.csv",
    "CP04_geometry_diagnosis.csv", "CP05_scope_and_decision.json",
    *[f"runner_CP{i:02d}_provenance.json" for i in range(1, 6)],
])


def source_hashes():
    folder = Path(__file__).resolve().parent
    paths = sorted([*folder.glob("*.py"), folder / "requirements.txt"])
    return {p.name: engine.sha(p) for p in paths}


def verify_cp05(root, manifest, rows, alphas, budgets, audit):
    earlier = run_cp05.verify_cp04(root, audit)
    output = root / "CP05_scope_and_decision.json"
    provenance = root / "runner_CP05_provenance.json"
    record = json.loads(provenance.read_text(encoding="utf8"))
    evidence = record["diagnostic_evidence"]
    expected = {
        **audit, **earlier,
        "runner_sha256": engine.sha(run_cp05.__file__),
        "checkpoint_io_sha256": engine.sha(checkpoint_io.__file__),
        "diagnostic_evidence": evidence,
        "output_sha256": engine.sha(output),
    }
    if record != expected:
        raise ValueError("CP05 input, output, runner, or provenance mismatch")
    if json.loads(output.read_text(encoding="utf8")) != run_cp05.build_scope(manifest):
        raise ValueError("CP05 scope decision disagrees with locked CP00")
    _, statistics = run_cp04.build_diagnosis(rows, manifest["N"], alphas, budgets)
    if any(evidence[key] != value for key, value in statistics.items()):
        raise ValueError("CP05 diagnostic evidence disagrees with CP04")
    if evidence["baseline_budget_w"] != manifest["config"]["pmax"]:
        raise ValueError("CP05 baseline budget disagrees with CP00")
    for key in ("numerical_review_required", "statistical_certificate_claim_allowed",
                "globally_optimal_beamforming_claim_allowed", "post_test_best_alpha_claim_allowed"):
        if evidence[key] is not False:
            raise ValueError(f"CP05 contains an unsupported scope claim: {key}")
    return {**earlier, "cp05_sha256": engine.sha(output),
            "cp05_provenance_sha256": engine.sha(provenance)}


def checksum_rows(root):
    return [{"file": name, "sha256": engine.sha(root / name)} for name in ARTIFACTS]


def read_checksums(root):
    with (root / "CP06_sha256.csv").open(newline="", encoding="utf8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["file", "sha256"]:
            raise ValueError("Invalid CP06 checksum schema")
        rows = list(reader)
    if len(rows) != len(ARTIFACTS) or sorted(r["file"] for r in rows) != ARTIFACTS:
        raise ValueError("CP06 must list exactly CP00--CP05 and the five provenance files")
    return rows


def verify_bundle(root):
    # This mode verifies portable artifacts and code without needing channel data,
    # per-geometry task caches, or the original absolute Python executable path.
    rows = read_checksums(root)
    if sorted(rows, key=lambda r: r["file"]) != checksum_rows(root):
        raise ValueError("CP06 checksum mismatch: an input artifact was changed")
    receipt = json.loads((root / "runner_CP06_provenance.json").read_text(encoding="utf8"))
    if receipt["output_sha256"] != engine.sha(root / "CP06_sha256.csv"):
        raise ValueError("CP06 table differs from its recorded checksum")
    if receipt["code_files_sha256"] != source_hashes():
        raise ValueError("Source files differ from the CP06 code snapshot")
    if receipt["artifact_files"] != ARTIFACTS or receipt["status"] != "DIAGNOSTIC_ONLY":
        raise ValueError("Invalid CP06 artifact scope")
    return len(rows)


def run(run_dir, verify_only=False):
    root = Path(run_dir).resolve()
    if not verify_only:
        root, manifest, rows, alphas, budgets, audit = checkpoint_io.load_cp01(root)
        earlier = verify_cp05(root, manifest, rows, alphas, budgets, audit)
        checksums = checksum_rows(root)
        receipt = {
            "status": "DIAGNOSTIC_ONLY",
            "input_audit": {**audit, **earlier},
            "code_files_sha256": source_hashes(),
            "artifact_files": ARTIFACTS,
        }
        target = root / "CP06_sha256.csv"
        provenance_path = root / "runner_CP06_provenance.json"
        if provenance_path.exists():
            verify_bundle(root)
            previous = json.loads(provenance_path.read_text(encoding="utf8"))
            previous.pop("output_sha256")
            if previous != receipt:
                raise ValueError("CP06 inputs, source, or environment changed; use a new run-id")
        else:
            # Recover safely if a previous process stopped between the two writes.
            if target.exists() and read_checksums(root) != checksums:
                raise ValueError("Existing CP06 table disagrees with verified inputs")
            engine.write_csv(target, checksums, ["file", "sha256"])
            engine.write_json(provenance_path, {
                **receipt, "output_sha256": engine.sha(target),
            })
        print(f"CP06 FILES HASHED: {len(checksums)}")
    count = verify_bundle(root)
    print(f"CP06 CHECKSUMS VERIFIED: {count}")
    print("CP06 STATUS: DIAGNOSTIC_ONLY")
    print(f"CSV: {root / 'CP06_sha256.csv'}")
    print(f"PROVENANCE: {root / 'runner_CP06_provenance.json'}")
    print("CP06 PASS (artifact integrity checks; not a certificate)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify sealed artifacts and source; do not require dataset/tasks")
    args = parser.parse_args()
    try:
        return run(args.run_dir, args.verify_only)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"CP06 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
