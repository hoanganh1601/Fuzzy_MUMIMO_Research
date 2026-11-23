"""V16.3 tests: frozen scenario spec, pool validation and the natural-run comparison."""
import sys, json, tempfile, subprocess, unittest
from pathlib import Path
import numpy as np
CODE = Path(__file__).resolve().parents[1] / 'code'
sys.path.insert(0, str(CODE))
from natural_prevalence import newcombe, wilson
import scenario_spec as ss


def run(*args):
    return subprocess.run([sys.executable, str(CODE / 'scenario_spec.py'), *args], capture_output=True, text=True)


class Spec(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp()); r = run('--stage', 'freeze', '--run-id', 'NS', '--out-root', str(self.d), '--set', 'pool_drops=12', '--set', 'sample_groups=5')
        self.assertEqual(r.returncode, 0, r.stderr); self.spec = self.d / 'NS' / ss.SPEC_FILE; s = json.loads(self.spec.read_text())
        rng = np.random.default_rng(0)
        H = ((rng.standard_normal((12, 16, 8)) + 1j * rng.standard_normal((12, 16, 8))) * 1e-6).astype(np.complex64)
        self.pool = self.d / 'p.npz'; np.savez(self.pool, H=H, groups=np.array([f'g{i}' for i in range(12)]), ut_distance_m=np.full((12, 8), 100.))
        prov = {k: s[k] for k in ss.MUST_MATCH}; prov.update(seed=s['pool_seed'], scenario_spec_sha256=ss.sha(self.spec), prior_use='never_seen')
        self.prov = self.d / 'p.json'; self.prov.write_text(json.dumps(prov)); self.p = prov

    def test_accepts_conforming_pool(self):
        r = run('--stage', 'validate', '--run-id', 'NS', '--out-root', str(self.d), '--pool', str(self.pool), '--provenance', str(self.prov))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn('POOL ACCEPTED', r.stdout)

    def test_rejects_changed_deployment_or_spec(self):
        for k, v in (('inter_site_distance_m', 200.0), ('indoor_probability', 0.0), ('scenario_spec_sha256', 'x'), ('seed', 1)):
            bad = dict(self.p); bad[k] = v; f = self.d / 'bad.json'; f.write_text(json.dumps(bad))
            r = run('--stage', 'validate', '--run-id', 'NS', '--out-root', str(self.d), '--pool', str(self.pool), '--provenance', str(f))
            self.assertNotEqual(r.returncode, 0, k)

    def test_refreeze_with_other_content_is_refused(self):
        r = run('--stage', 'freeze', '--run-id', 'NS', '--out-root', str(self.d), '--set', 'pool_drops=13', '--set', 'sample_groups=5')
        self.assertNotEqual(r.returncode, 0)


class Compare(unittest.TestCase):
    def test_newcombe_contains_difference_and_zero_when_equal(self):
        lo, hi = newcombe(1, 100, 30, 100); self.assertTrue(lo < 0.29 < hi and lo > 0)
        lo, hi = newcombe(10, 100, 10, 100); self.assertTrue(lo < 0 < hi)


if __name__ == '__main__': unittest.main()
