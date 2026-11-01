#!/usr/bin/env python3
"""Run exhaustive candidate evaluation and export CP01 only; defer decisions to CP02."""
import argparse
from collections import Counter
import json
import sys
import time

import admission_beam as engine
import scheduling_checkpoints as checkpoints


def run(run_dir):
    root, manifest, H, groups, alphas, cfg, audit = checkpoints.load_run(run_dir)
    receipt_path = root / "runner_CP01_provenance.json"
    target = root / "CP01_all_subset_beam.csv"
    audit.update({
        "stage": "CP01",
        "protocol": "cp01_candidates_then_cp02_decisions_v1",
        "runner_sha256": engine.digest(__file__),
        "helper_sha256": engine.digest(checkpoints.__file__),
    })
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf8"))
        output_sha = previous.pop("output_sha256")
        if previous != audit:
            raise ValueError("CP01 inputs, runner, or environment changed; use a new run-id")
        if output_sha is not None and (not target.exists() or engine.digest(target) != output_sha):
            raise ValueError("CP01 output differs from its recorded checksum")
    else:
        engine.jwrite(receipt_path, {**audit, "output_sha256": None})

    n = manifest["N"]
    count_per_geometry = 15 * len(alphas)
    print(f"CP01 scan: {n} geometries x 15 subsets x {len(alphas)} beams", flush=True)
    rows = []
    tasks = root / "tasks"
    for i in range(n):
        path = tasks / f"{i:07d}.json"
        if path.exists():
            task = json.loads(path.read_text(encoding="utf8"))
        else:
            started = time.perf_counter()
            candidates = engine.exhaustive(H[i], alphas, cfg)
            elapsed = (time.perf_counter() - started) * 1000
            task = {
                "signature": manifest["signature"],
                "complete": False,
                "cp01_complete": True,
                "geometry": i,
                "group": str(groups[i]),
                "rows": candidates,
                "exhaustive_runtime_ms": elapsed,
            }
            # Oracle/greedy decisions and complete=True belong to CP02.
            engine.jwrite(path, task)
        checked = checkpoints.checked_rows(task, i, groups[i], manifest["signature"], alphas)
        rows.extend(dict(geometry=i, group=str(groups[i]), **row) for row in checked)
        if (i + 1) % 10 == 0 or i + 1 == n:
            print(f"CP01 progress: {i + 1}/{n} geometries", flush=True)
    if len(rows) != n * count_per_geometry:
        raise ValueError("Unexpected total CP01 candidate count")
    engine.cwrite(target, rows, list(rows[0]))
    engine.jwrite(receipt_path, {**audit, "output_sha256": engine.digest(target)})
    statuses = Counter(row["status"] for row in rows)
    print(f"GEOMETRIES: {n}")
    print(f"SUBSETS PER GEOMETRY: 15")
    print(f"CANDIDATES PER GEOMETRY: {count_per_geometry}")
    print(f"CP01 ROWS: {len(rows)}")
    for status, count in sorted(statuses.items()):
        print(f"{status}: {count}")
    print(f"CSV: {target}")
    if set(statuses) - checkpoints.PHYSICAL_STATUSES:
        print("CP01 REVIEW REQUIRED: investigate numerical/rank statuses before CP02")
        return 1
    print("CP01 PASS (candidate/checkpoint checks; not independent validation)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        return run(args.run_dir)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f"CP01 ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
