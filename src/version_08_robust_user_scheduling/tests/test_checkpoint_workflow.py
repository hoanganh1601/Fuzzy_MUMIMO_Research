"""Temporary synthetic runs: stage order, upstream equivalence and integrity gates."""
import contextlib
import copy
import csv
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "code"))
import admission_beam as engine
import model_audit
import run_cp02
import run_cp03
import run_cp06
import scheduling_checkpoints as checkpoints


def invoke(script, run, *extra):
    return subprocess.run(
        [sys.executable, str(PACKAGE / "code" / script), "--run-dir", str(run), *extra],
        cwd=PACKAGE, text=True, capture_output=True,
    )


class CheckpointWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="scheduling-workflow-")
        cls.workspace = Path(cls.temporary.name)
        cls.run_dir = cls.workspace / "SEPARATE"
        cls.parameters = [
            "--dataset", str(PACKAGE / "data/smoke.npz"), "--limit", "4",
            "--q", "2.9604143746015965", "--sigma-rel", "0.04", "--sinr-db", "6",
            "--noise", "2e-13", "--pmax", "1", "--alpha-list", "0,0.001,0.01,0.05,0.1,0.3,1",
        ]
        result = subprocess.run(
            [sys.executable, str(PACKAGE / "code/admission_beam.py"), "--stage", "preflight",
             "--run-id", cls.run_dir.name, "--out-root", str(cls.workspace), *cls.parameters],
            cwd=PACKAGE, text=True, capture_output=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        for number in range(1, 7):
            result = invoke(f"run_cp{number:02d}.py", cls.run_dir)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            for path in cls.run_dir.iterdir():
                matched = re.match(r"CP(\d\d)_", path.name)
                if matched and int(matched[1]) > number:
                    raise AssertionError(f"CP{number:02d} created a later checkpoint: {path}")
            if number == 1:
                for path in (cls.run_dir / "tasks").glob("*.json"):
                    task = json.loads(path.read_text())
                    if task["complete"] or "oracle" in task or "greedy" in task:
                        raise AssertionError("CP01 executed CP02 scheduling decisions")

        cls.reference = cls.workspace / "REFERENCE"
        cls.reference.mkdir()
        shutil.copy2(cls.run_dir / "CP00_manifest.json", cls.reference)
        shutil.copytree(cls.run_dir / "tasks", cls.reference / "tasks")
        result = subprocess.run(
            [sys.executable, str(PACKAGE / "code/admission_beam.py"), "--stage", "report",
             "--run-id", cls.reference.name, "--out-root", str(cls.workspace), *cls.parameters],
            cwd=PACKAGE, text=True, capture_output=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_reports_match_upstream_and_all_checksums_verify(self):
        for number in range(1, 6):
            path = next(self.reference.glob(f"CP{number:02d}_*"))
            self.assertEqual(path.read_bytes(), (self.run_dir / path.name).read_bytes())
        def hashes(path):
            with path.open(newline="") as file:
                return {r["file"]: r["sha256"] for r in csv.DictReader(file)}
        upstream = hashes(self.reference / "CP06_sha256.csv")
        separate = hashes(self.run_dir / "CP06_sha256.csv")
        self.assertEqual(len(separate), 11)
        for name, digest in upstream.items():
            self.assertEqual(separate[name], digest)
        result = invoke("run_cp06.py", self.run_dir)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_portable_verification_does_not_read_dataset_or_tasks(self):
        portable = self.workspace / "PORTABLE"
        portable.mkdir()
        for path in self.run_dir.iterdir():
            if path.is_file():
                shutil.copy2(path, portable)
        self.assertFalse((portable / "tasks").exists())
        with mock.patch("numpy.load", side_effect=AssertionError("Dataset must not be read")):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_cp06.run(portable, verify_only=True), 0)

    def test_changed_input_blocks_next_cp_and_integrity_verification(self):
        changed = self.workspace / "CHANGED"
        shutil.copytree(self.run_dir, changed)
        path = changed / "CP02_oracle_greedy_decisions.csv"
        path.write_bytes(path.read_bytes() + b"changed\n")
        result = invoke("run_cp03.py", changed)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provenance mismatch", result.stderr)
        result = invoke("run_cp06.py", changed, "--verify-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stderr)

    def test_missing_predecessor_is_rejected(self):
        missing = self.workspace / "MISSING"
        missing.mkdir()
        shutil.copy2(self.run_dir / "CP00_manifest.json", missing)
        result = invoke("run_cp03.py", missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((missing / "CP03_paired_comparison.csv").exists())

    def test_lexicographic_reference_and_same_cardinality_power_pairing(self):
        rows = [
            dict(status="FEASIBLE", cardinality=1, p_req_w=0.1, subset="0", alpha=0.0),
            dict(status="FEASIBLE", cardinality=2, p_req_w=0.9, subset="01", alpha=0.0),
            dict(status="FEASIBLE", cardinality=2, p_req_w=0.8, subset="02", alpha=0.0),
        ]
        task = {
            "geometry": 0, "group": "fixture", "rows": rows, "oracle": rows[2],
            "oracle_runtime_ms": 1.0,
            "greedy": [dict(method=method, choice=choice, calls=7, runtime_ms=0.1)
                       for method, choice in (("forward", rows[0]), ("backward", rows[1]))],
        }
        run_cp02.validate_choices(task)
        paired = run_cp03.build_comparisons([task], [0.0])
        self.assertEqual(paired[0]["cardinality_gap"], 1)
        self.assertEqual(paired[0]["power_ratio_if_same_cardinality"], "")
        self.assertAlmostEqual(paired[1]["power_ratio_if_same_cardinality"], 1.125)
        for wrong in (rows[0], rows[1]):
            task["oracle"] = wrong
            with self.assertRaisesRegex(ValueError, "lexicographic"):
                run_cp02.validate_choices(task)
        empty = dict(geometry=1, group="empty", oracle=None,
                     greedy=[dict(method=m, choice=None, calls=7) for m in ("forward", "backward")])
        for row in run_cp03.build_comparisons([empty], [0.0]):
            self.assertEqual(row["cardinality_gap"], 0)
            self.assertEqual(row["same_cardinality"], 0)
            self.assertEqual(row["power_ratio_if_same_cardinality"], "")

    def test_g1_rejects_bad_power_and_nonmonotone_budget_behavior(self):
        _, _, H, _, _, cfg, _ = checkpoints.load_run(self.run_dir)
        task = json.loads((self.run_dir / "tasks/0000000.json").read_text())
        one = copy.deepcopy(task)
        one["rows"] = one["rows"][:1]
        bad = copy.deepcopy(one)
        bad["rows"][0]["p_req_w"] *= 2
        with self.assertRaisesRegex(ValueError, "required power mismatch"):
            model_audit.audit_candidates(H, [bad], cfg)
        original_solve = engine.solve
        def nonmonotone(*args, **kwargs):
            result = original_solve(*args, **kwargs)
            result["status"] = "FEASIBLE"
            return result
        with mock.patch.object(engine, "solve", side_effect=nonmonotone):
            with self.assertRaisesRegex(ValueError, "below/above"):
                model_audit.audit_candidates(H, [one], cfg)


if __name__ == "__main__":
    unittest.main()
