"""Exercise the checkpoint CLI against the unmodified engine in temporary runs."""
import csv
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1]


def command(script, run, *extra):
    return subprocess.run(
        [sys.executable, str(PACKAGE / "code" / script), "--run-dir", str(run), *extra],
        cwd=PACKAGE, text=True, capture_output=True,
    )


class CheckpointWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="beam-checkpoints-")
        cls.workspace = Path(cls.temporary.name)
        cls.reference = cls.workspace / "REFERENCE"
        result = subprocess.run(
            [sys.executable, str(PACKAGE / "code/beam_feasibility.py"),
             "--stage", "all", "--dataset", str(PACKAGE / "data/synthetic_diagnostic.npz"),
             "--run-id", cls.reference.name, "--output", str(cls.workspace)],
            cwd=PACKAGE, text=True, capture_output=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.separate = cls.workspace / "SEPARATE"
        cls.separate.mkdir()
        shutil.copy2(cls.reference / "CP00_manifest.json", cls.separate)
        shutil.copytree(cls.reference / "tasks", cls.separate / "tasks")
        cls.step_outputs = []
        for number in range(1, 7):
            result = command(f"run_cp{number:02d}.py", cls.separate)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            later = [p.name for p in cls.separate.glob("CP0*")
                     if int(p.name[2:4]) > number]
            if later:
                raise AssertionError(f"CP{number:02d} produced later checkpoints: {later}")
            cls.step_outputs.append(result.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_separate_reports_match_original_and_seal_provenance(self):
        for number in range(1, 6):
            path = next(self.reference.glob(f"CP{number:02d}_*"))
            self.assertEqual(path.read_bytes(), (self.separate / path.name).read_bytes())
        def checksums(path):
            with path.open(newline="") as file:
                return {r["file"]: r["sha256"] for r in csv.DictReader(file)}
        reference = checksums(self.reference / "CP06_sha256.csv")
        separate = checksums(self.separate / "CP06_sha256.csv")
        self.assertEqual(len(separate), 11)
        for name, digest in reference.items():
            self.assertEqual(separate[name], digest)
        self.assertIn("CHECKSUMS VERIFIED: 11", self.step_outputs[-1])
        result = command("run_cp06.py", self.separate)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_portable_verification_without_tasks(self):
        portable = self.workspace / "PORTABLE"
        portable.mkdir()
        for path in self.separate.iterdir():
            if path.is_file():
                shutil.copy2(path, portable)
        self.assertFalse((portable / "tasks").exists())
        result = command("run_cp06.py", portable, "--verify-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_changed_artifact_blocks_next_cp_and_integrity_check(self):
        changed = self.workspace / "CHANGED"
        shutil.copytree(self.separate, changed)
        path = changed / "CP02_beam_budget_summary.csv"
        path.write_bytes(path.read_bytes() + b"changed\n")
        result = command("run_cp03.py", changed)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CP02 input, output, runner, or provenance mismatch", result.stderr)
        result = command("run_cp06.py", changed, "--verify-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stderr)

    def test_missing_previous_cp_is_rejected(self):
        incomplete = self.workspace / "INCOMPLETE"
        incomplete.mkdir()
        shutil.copy2(self.separate / "CP00_manifest.json", incomplete)
        shutil.copytree(self.separate / "tasks", incomplete / "tasks")
        result = command("run_cp03.py", incomplete)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((incomplete / "CP03_paired_ZF_RZF.csv").exists())


if __name__ == "__main__":
    unittest.main()
