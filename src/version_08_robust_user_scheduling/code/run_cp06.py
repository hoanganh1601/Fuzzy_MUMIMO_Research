#!/usr/bin/env python3
"""Seal CP00--CP05 and provenance, or verify an existing result bundle."""
import argparse
import csv
import json
from pathlib import Path
import sys

import admission_beam as engine
import report_inputs
import run_cp05


ARTIFACTS = sorted([
    "CP00_manifest.json", "CP01_all_subset_beam.csv",
    "CP02_oracle_greedy_decisions.csv", "CP03_paired_comparison.csv",
    "CP04_summary.csv", "CP05_scope.json",
    *[f"runner_CP{i:02d}_provenance.json" for i in range(1, 6)],
])


def source_hashes():
    folder = Path(__file__).resolve().parent
    paths = sorted([*folder.glob("*.py"), folder / "requirements.txt"])
    return {p.name: engine.digest(p) for p in paths}


def verified_cp05(run_dir):
    root, manifest, comparisons, stats, audit = run_cp05.verified_cp04(run_dir)
    target = root / "CP05_scope.json"
    receipt_path = root / "runner_CP05_provenance.json"
    scope = run_cp05.build_scope(manifest)
    evidence = run_cp05.build_evidence(manifest, comparisons, stats)
    expected = {
        **audit, "stage": "CP05", "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(run_cp05.__file__),
        "report_inputs_sha256": engine.digest(report_inputs.__file__),
        "evaluation_evidence": evidence, "output_sha256": engine.digest(target),
    }
    if json.loads(receipt_path.read_text(encoding="utf8")) != expected:
        raise ValueError("CP05 source, output, scope evidence or provenance mismatch")
    if json.loads(target.read_text(encoding="utf8")) != scope:
        raise ValueError("CP05 scope differs from the locked run and original guide")
    audit.update({"cp05_sha256": engine.digest(target),
                  "cp05_provenance_sha256": engine.digest(receipt_path)})
    return root, manifest, audit


def checksum_rows(root):
    return [{"file": name, "sha256": engine.digest(root / name)} for name in ARTIFACTS]


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
    # Portable verification does not read channel NPZ, task caches, or compare
    # the archived executable path with the current Python environment.
    rows = read_checksums(root)
    if sorted(rows, key=lambda r: r["file"]) != checksum_rows(root):
        raise ValueError("CP06 checksum mismatch: a sealed input artifact changed")
    receipt = json.loads((root / "runner_CP06_provenance.json").read_text(encoding="utf8"))
    if receipt["output_sha256"] != engine.digest(root / "CP06_sha256.csv"):
        raise ValueError("CP06 table differs from its recorded checksum")
    if receipt["code_files_sha256"] != source_hashes():
        raise ValueError("Source files differ from the CP06 code snapshot")
    if receipt["artifact_files"] != ARTIFACTS or receipt["status"] != "EXPLORATORY_EVALUATION":
        raise ValueError("Invalid CP06 artifact scope")
    return len(rows)


def run(run_dir, verify_only=False):
    root = Path(run_dir).resolve()
    if not verify_only:
        root, manifest, audit = verified_cp05(root)
        checksums = checksum_rows(root)
        receipt = {
            "status": "EXPLORATORY_EVALUATION",
            "n_geometries": manifest["N"],
            "input_audit": audit,
            "code_files_sha256": source_hashes(),
            "artifact_files": ARTIFACTS,
        }
        target = root / "CP06_sha256.csv"
        receipt_path = root / "runner_CP06_provenance.json"
        if receipt_path.exists():
            verify_bundle(root)
            previous = json.loads(receipt_path.read_text(encoding="utf8"))
            previous.pop("output_sha256")
            if previous != receipt:
                raise ValueError("CP06 input, code or environment changed; use a new run-id")
        else:
            # Recover if a previous process stopped between the atomic writes.
            if target.exists() and read_checksums(root) != checksums:
                raise ValueError("Existing CP06 table differs from verified inputs")
            engine.cwrite(target, checksums, ["file", "sha256"])
            engine.jwrite(receipt_path, {**receipt, "output_sha256": engine.digest(target)})
        print(f"CP06 FILES HASHED: {len(checksums)}")
    count = verify_bundle(root)
    print(f"CP06 CHECKSUMS VERIFIED: {count}")
    print("CP06 STATUS: EXPLORATORY_EVALUATION")
    print(f"CSV: {root / 'CP06_sha256.csv'}")
    print(f"PROVENANCE: {root / 'runner_CP06_provenance.json'}")
    print("CP06 PASS (artifact integrity checks; not independent validation)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify sealed files/code without requiring dataset or tasks")
    args = parser.parse_args()
    try:
        return run(args.run_dir, args.verify_only)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f"CP06 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
