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
from numeric_agreement import agree
from robust_model import solve

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
                    self.assertTrue(agree(ns.native_search(h[:, :k], AL[:3], CFG, pol)[0], ref, h[:, :k], AL[:3], CFG)[0], (t, k, pol))
                    self.assertTrue(same_choice(search(h[:, :k], AL[:3], CFG, pol, 1e-5)[0], ref))

    def test_near_singular_power_agreement(self):
        """V16.1 regression: 1 - rho(F) ~ 1e-8 makes Python and C powers differ by > 1e-7 (field report, geometry 8 K=6 L=3)."""
        rng = np.random.default_rng(0); M = 16
        h1 = rng.standard_normal(M) + 1j * rng.standard_normal(M); v = rng.standard_normal(M) + 1j * rng.standard_normal(M)
        H = lambda e: np.stack([h1, h1 + e * v], 1)
        def rho(e): return solve(H(e), [0, 1], 0., CFG)['rho']
        a, b = 0.02, 0.2
        for _ in range(300):
            m = (a + b) / 2; r = rho(m)
            if r is None or r > 1 - 1e-8: a = m
            else: b = m
        h = H(b); c = dict(CFG); c['noise'] = CFG['noise'] * 0.38 / solve(h, [0, 1], 0., CFG)['p_req_w']
        ref = independent_oracle(h, (0.,), c)[0]; got = ns.native_search(h, (0.,), c, 'CARD')[0]
        self.assertFalse(same_choice(got, ref))                 # the strict V16 test fails, as in the field report
        ok, ev = agree(got, ref, h, (0.,), c)
        self.assertTrue(ok); self.assertEqual(ev['type'], 'POWER_WITHIN_FP_SENSITIVITY')
        well = H(0.2); r0 = independent_oracle(well, (0.,), CFG)[0]; bad = dict(r0); bad['p_req_w'] *= 1 + 1e-5
        self.assertFalse(agree(bad, r0, well, (0.,), CFG)[0])   # a genuine error is still rejected

    def test_single_precision_input(self):
        """V16.2 regression (field report C16_DEV/C16_3GPP): complex64 data make the Python oracle run in single precision.
        After promotion to complex128 the compiled decision and power agree with the strict test."""
        rng = np.random.default_rng(31)
        for t in range(4):
            h32 = drop(rng, 16, 8, *((40, 250) if t % 2 else (300, 1200))).astype(np.complex64)
            h = h32.astype(np.complex128)
            for k in (4, 6):
                ref = independent_oracle(h[:, :k], AL[:3], CFG)[0]
                self.assertTrue(same_choice(ns.native_search(h[:, :k], AL[:3], CFG, 'CARD')[0], ref), (t, k))
                r32 = independent_oracle(h32[:, :k], AL[:3], CFG)[0]
                if ref is not None:
                    self.assertEqual((r32['cardinality'], r32['subset'], r32['alpha']), (ref['cardinality'], ref['subset'], ref['alpha']))

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
