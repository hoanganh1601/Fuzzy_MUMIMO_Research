"""V16 tests: compiled solver equivalence, analytical lemmas, model fit, natural-prevalence helpers."""
import sys, unittest, itertools, json, tempfile, types
from math import comb
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from run_experiment import search, same_choice, channel_features, independent_oracle
from make_synthetic import drop
from breakeven_model import rejected_counts, user_x, design
from natural_prevalence import wilson
from scipy.optimize import nnls

CFG = {'q': 2.960414, 'sigma': .04, 'gamma': 10**.6, 'noise': 2e-13, 'pmax': 1.}
AL = (0., .001, .01, .05, .1, .3, 1.)

try:
    import native_search as ns
    ns.lib(); NATIVE = None
except Exception as e:  # no C compiler: native tests are skipped with the reason
    NATIVE = str(e)


@unittest.skipIf(NATIVE is not None, f'compiled library unavailable: {NATIVE}')
class Compiled(unittest.TestCase):
    def test_matches_python_search_and_oracle(self):
        rng = np.random.default_rng(21)
        for t in range(4):
            h = drop(rng, 16, 8, *((40, 250) if t % 2 else (300, 1200)))
            for k in (4, 6):
                ref = independent_oracle(h[:, :k], AL[:3], CFG)[0]
                for pol in ('CARD', 'EARLY'):
                    self.assertTrue(same_choice(ns.native_search(h[:, :k], AL[:3], CFG, pol)[0], ref), (t, k, pol))
                    self.assertTrue(same_choice(search(h[:, :k], AL[:3], CFG, pol, 1e-5)[0], ref))

    def test_counters_and_early_ratio(self):
        h = drop(np.random.default_rng(4), 16, 8, 600, 1200)
        P = ns.Prepared(h, AL, CFG, 1e-5)
        self.assertAlmostEqual(P.er() / channel_features(h, CFG, True, (.1, 1.))['early_ratio'], 1., places=9)
        P.run(1); ch, c = P.result()
        n = rejected_counts(list(user_x(h, CFG)), 1e-5)
        s0 = ch['cardinality'] if ch else 1
        self.assertEqual(sum(c['rejected_subsets_by_size'][s] for s in range(s0, 9)), sum(n[s] for s in range(s0, 9)))

    def test_routed_follows_lock(self):
        h = drop(np.random.default_rng(5), 16, 8, 600, 1200); P = ns.Prepared(h, AL[:3], CFG, 1e-5)
        cell = channel_features(h, CFG, True, (.1, 1.))['cell']
        for active in (set(), {0, 1, 2}, {int(cell[2:])}):
            P.set_routing([.1, 1.], active); P.run_routed()
            self.assertEqual(P.pol.value, int(int(cell[2:]) in active))


class Lemmas(unittest.TestCase):
    def test_lemma1_no_rejection_below_one(self):
        rng = np.random.default_rng(1)
        for _ in range(200):
            x = rng.dirichlet(np.ones(8)) * rng.uniform(0, .999)
            self.assertEqual(sum(rejected_counts(list(x), 1e-5)), 0)

    def test_lemma2_monotone_fraction(self):
        rng = np.random.default_rng(2)
        for _ in range(200):
            K = rng.integers(3, 9); x = list(rng.exponential(rng.uniform(.05, 1.), K)); n = rejected_counts(x, 1e-5)
            f = [n[s] / comb(K, s) for s in range(1, K + 1)]
            self.assertTrue(all(f[i] <= f[i + 1] + 1e-12 for i in range(len(f) - 1)), f)

    def test_full_set_rejected_iff_er_above_one(self):
        x = [.3, .3, .5]; self.assertEqual(rejected_counts(x, 1e-5)[3], 1); self.assertEqual(rejected_counts([.3, .3, .3], 1e-5)[3], 0)


class Model(unittest.TestCase):
    def test_nnls_recovers_costs(self):
        rng = np.random.default_rng(3); theta = np.array([.01, .002, 0., .004, .05]); rows = []
        for _ in range(300):
            r = {'A1': rng.uniform(0, 500), 'N_vis': rng.integers(1, 256)}; r['A2'] = r['A1'] * rng.uniform(1, 8); r['A3'] = r['A2'] * rng.uniform(1, 8)
            rows.append(r)
        y = design(rows) @ theta
        est, _ = nnls(design(rows), y)
        self.assertTrue(np.allclose(est, theta, atol=1e-6), est)


class Natural(unittest.TestCase):
    def test_wilson(self):
        lo, hi = wilson(10, 100); self.assertLess(lo, .1); self.assertGreater(hi, .1)
        self.assertEqual(wilson(0, 0), (None, None))


if __name__ == '__main__': unittest.main()
