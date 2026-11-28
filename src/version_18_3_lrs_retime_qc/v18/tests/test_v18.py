import math, sys, unittest
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / 'code'))
import native18 as n18
import v18_stats as S
from make_synthetic import drop

CFG = {'q': 2.960414, 'sigma': .04, 'gamma': 10 ** .6, 'noise': 2e-13, 'pmax': 1.}
AL = (0., .001, .01, .05, .1, .3, 1.)


class TestStats(unittest.TestCase):
    def test_perm_exact(self):
        r = S.perm_paired([1, 2, 3, 4, 5]); self.assertTrue(r['exact']); self.assertAlmostEqual(r['p'], 1 / 32)

    def test_perm_symmetric(self):
        r = S.perm_paired([1, -1, 2, -2, 3, -3], alternative='two'); self.assertGreater(r['p'], .9)

    def test_icc(self):
        v = [1, 2, 3, 1, 2, 3]; s = ['a', 'a', 'a', 'b', 'b', 'b']; self.assertAlmostEqual(S.icc(v, s)['icc'], 0.0)
        v = [0, 0, 0, 10, 10, 10]; self.assertAlmostEqual(S.icc(v, s)['icc'], 1.0)

    def test_break_even(self):
        e = np.r_[np.linspace(.2, .9, 20), np.linspace(1.1, 5, 20)]; y = np.r_[-.05 * np.ones(20), .5 * np.ones(20)]
        r = S.break_even_threshold(e, y, B=200); self.assertEqual(r['acc_rule_1'], 1.0); self.assertTrue(.9 <= r['eta_star'] <= 1.1)

    def test_boot_stratified_constant(self):
        r = S.boot_stratified([.3] * 10, ['a'] * 5 + ['b'] * 5, B=200); self.assertAlmostEqual(r['lo'], .3); self.assertAlmostEqual(r['hi'], .3)


class TestNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls): n18.build(verbose=False)

    def test_exact_schedulers_and_bound(self):
        rng = np.random.default_rng(11)
        for t in range(6):
            h = drop(rng, 16, 8, *((40, 250) if t % 2 else (400, 1500)))
            P = n18.P18(h, AL, CFG); res = {}
            for p in ('DCS', 'PBS', 'CBD', 'CBPBS', 'ACS', 'GREEDY', 'ACSSTOP'):
                P.repeat(1, p); res[p] = P.result()
            for p in ('PBS', 'CBD', 'CBPBS', 'ACS'): self.assertTrue(n18.same(res[p][0], res['DCS'][0]), p)
            card = res['DCS'][0]['cardinality'] if res['DCS'][0] else 0
            self.assertGreaterEqual(P.sbar(), card)
            rej = res['PBS'][1]['rejected_by_size']
            for s in range(P.sbar() + 1, 9): self.assertEqual(rej[s - 1], math.comb(8, s))
            g = res['GREEDY'][0]
            if g is not None: self.assertLessEqual(g['p_req_w'], CFG['pmax'] * (1 + 1e-9)); self.assertLessEqual(g['cardinality'], card)

    def test_timed_build_same_decisions(self):
        rng = np.random.default_rng(3); h = drop(rng, 16, 8, 300, 1200)
        A = n18.P18(h, AL, CFG); B = n18.P18(h, AL, CFG, timed=True)
        for p in ('DCS', 'PBS', 'CBD'):
            A.repeat(1, p); B.repeat(1, p); self.assertTrue(n18.same(A.result()[0], B.result()[0]))
        t, c = B.stages(); self.assertTrue(n18.lib(True).stage_timing_enabled() == 1); self.assertGreater(sum(c), 0)

    def test_routed(self):
        rng = np.random.default_rng(4); h = drop(rng, 16, 8, 400, 1500)
        P = n18.P18(h, AL, CFG, bins=(0.1, 1.0), active_cells=(2,)); P.repeat(1, 'LRS'); r = P.result()
        self.assertEqual(r[1]['routed_policy'], 1 if P.eta() >= 1 else 0)


if __name__ == '__main__':
    unittest.main()
