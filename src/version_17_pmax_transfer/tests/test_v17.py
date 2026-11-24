"""V17 tests: power-budget override and fresh complement sets."""
import sys, json, tempfile, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from make_synthetic import drop
from run_experiment import independent_oracle, same_choice
import pmax_sweep as px
CFG = {'q': 2.960414, 'sigma': .04, 'gamma': 10**.6, 'noise': 2e-13, 'pmax': 1.}
try:
    import native_search as ns; ns.lib(); NATIVE = None
except Exception as e: NATIVE = str(e)


@unittest.skipIf(NATIVE is not None, 'no compiled library')
class Budget(unittest.TestCase):
    def test_early_ratio_scales_and_decisions_match_oracle(self):
        h = drop(np.random.default_rng(8), 16, 8, 300, 1200)
        er30 = ns.Prepared(h, (0., .01), CFG, 1e-5).er()
        for dbm in (35., 46., 49.):
            c = dict(CFG); c['pmax'] = 10 ** ((dbm - 30) / 10)
            self.assertAlmostEqual(ns.Prepared(h, (0., .01), c, 1e-5).er() * c['pmax'], er30, places=9)
            for k in (4, 6):
                ref = independent_oracle(h[:, :k], (0., .01), c)[0]
                for pol in ('CARD', 'EARLY'):
                    self.assertTrue(same_choice(ns.native_search(h[:, :k], (0., .01), c, pol)[0], ref), (dbm, k, pol))


class Complement(unittest.TestCase):
    def test_complement_excludes_sample_and_keeps_rest(self):
        d = Path(tempfile.mkdtemp()); G = np.array([f'g{i}' for i in range(10)])
        H = np.zeros((10, 16, 8), np.complex64); np.savez(d / 'pool.npz', H=H, groups=G)
        np.savez(d / 's.npz', H=H[:4], groups=G[:4]); (d / 'pool.json').write_text(json.dumps({'source': 'x'}))
        n = px.complement(str(d / 'pool.npz'), str(d / 'pool.json'), str(d / 's.npz'), str(d / 'c.npz'))
        self.assertEqual(n, 6)
        with np.load(d / 'c.npz') as f: self.assertEqual(set(f['groups']), set(G[4:]))
        self.assertEqual(json.loads((d / 'c.npz.provenance.json').read_text())['prior_use'], 'never_seen')


if __name__ == '__main__': unittest.main()
