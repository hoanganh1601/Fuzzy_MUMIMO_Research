"""V15.1 tests: safety of the robust pre-beam bound, oracle agreement, cells, decision logic."""
import sys, unittest, itertools, json, tempfile, types
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from run_experiment import (search, choose_policy, channel_features, split_groups, same_choice, pick,
                            hypothesis_tests, policy_results, bin_label, rjson)
from screening_policy import early_bound
from robust_model import solve, jwrite
from make_synthetic import drop

CFG = {'q': 2.960414, 'sigma': .04, 'gamma': 10**.6, 'noise': 2e-13, 'pmax': 1.}


class Safety(unittest.TestCase):
    def test_robust_early_never_rejects_feasible(self):
        rng = np.random.default_rng(5)
        for t in range(6):
            h = drop(rng, 16, 8, 40, 1200)
            for size in (1, 2, 3):
                for sub in itertools.combinations(range(8), size):
                    for robust in (True, False):
                        for pmax in (1e-3, 1e-1, 1., 10.):
                            c = dict(CFG, pmax=pmax)
                            rej = early_bound(h, sub, c, 1e-5, robust)[0]
                            if rej:
                                for a in (0., .01, 1.):
                                    self.assertNotEqual(solve(h, list(sub), a, c)['status'], 'FEASIBLE')

    def test_robust_bound_tighter_than_nominal(self):
        h = drop(np.random.default_rng(1), 16, 8, 600, 1200)
        lr = early_bound(h, (0, 1), CFG, 1e-5, True)[3]; ln = early_bound(h, (0, 1), CFG, 1e-5, False)[3]
        self.assertGreater(lr, ln)

    def test_boundary_fail_open(self):
        h = drop(np.random.default_rng(2), 16, 8, 300, 600)
        lb = early_bound(h, (0,), CFG, 1e-5, True)[3]
        for d, expect in ((1e-3, True), (5e-6, False), (1e-9, False)):
            self.assertEqual(early_bound(h, (0,), dict(CFG, pmax=lb / (1 + d)), 1e-5, True)[0], expect)


class Oracle(unittest.TestCase):
    def test_all_policies_match_card_k4_k6_k8(self):
        rng = np.random.default_rng(31)
        for lo, hi in ((40, 250), (400, 1200)):
            h = drop(rng, 16, 8, lo, hi)
            for k in (4, 6, 8):
                ref, _, _ = search(h[:, :k], (0., .01), CFG, 'CARD', 1e-5)
                for pol in ('EARLY', 'CACHED', 'HYBRID'):
                    self.assertTrue(same_choice(search(h[:, :k], (0., .01), CFG, pol, 1e-5)[0], ref), (k, pol))

    def test_pick_tie_rule(self):
        c = lambda s, k, a, p: dict(subset=s, cardinality=k, alpha=a, p_req_w=p)
        self.assertEqual(pick([c('01', 2, .1, 1.), c('02', 2, 0., 1. + 5e-10), c('0123', 4, 1., 9.)])['subset'], '0123')
        self.assertEqual(pick([c('01', 2, .1, 1.), c('02', 2, 0., 1. + 5e-10)])['subset'], '02')


class Cells(unittest.TestCase):
    def test_bins(self):
        self.assertEqual([bin_label(x, (.1, 1.)) for x in (.05, .1, .5, 1., 9.)], ['ER0', 'ER1', 'ER1', 'ER2', 'ER2'])

    def test_feature_separates_conditions(self):
        near = channel_features(drop(np.random.default_rng(3), 16, 8, 40, 100), CFG, True, (.1, 1.))
        far = channel_features(drop(np.random.default_rng(3), 16, 8, 1000, 1200), CFG, True, (.1, 1.))
        self.assertLess(near['early_ratio'], far['early_ratio']); self.assertEqual(far['cell'], 'ER2')

    def test_small_cell_fallback(self):
        rows = [{'K': 4, 'L': 3, 'cell': 'ER2', 'group': 'A', 'policy': 'EARLY', 'saving_ms': 1.},
                {'K': 4, 'L': 3, 'cell': 'ER2', 'group': 'B', 'policy': 'EARLY', 'saving_ms': 2.}]
        lock, _ = choose_policy(rows, {'A'}, {'B'}, 100, .1, 5)
        self.assertEqual(lock['K4_L3_ER2'], 'CARD')

    def test_group_split(self):
        a, b = split_groups(['a', 'b', 'c', 'd', 'e', 'f'], 12)
        self.assertFalse(a & b); self.assertEqual(len(a | b), 6)


class Decision(unittest.TestCase):
    def _rows(self, gain8, gain4, n=12):
        paired = []
        for g in range(n):
            for k, gain in ((4, gain4), (8, gain8)):
                for pol in ('EARLY', 'CACHED', 'HYBRID'):
                    paired.append({'geometry': g, 'group': f'G{g}', 'K': k, 'L': 3, 'cell': 'ER2', 'early_ratio': 5.,
                                   'policy': pol, 'card_ms': 100., 'policy_ms': 100. - gain * (1 + .05 * (g % 3)), 'feature_ms': 0.,
                                   'saving_ms': gain * (1 + .05 * (g % 3)), 'calls_saved': 1})
        return paired

    def test_go_when_trend_and_break_even(self):
        a = types.SimpleNamespace(bootstrap=300, seed=1, min_rel_gain=.02, min_gain_ms=.1)
        sel, _ = policy_results(self._rows(20., 2.), {'K4_L3_ER2': 'EARLY', 'K8_L3_ER2': 'EARLY'}, 300, 1, .1)
        self.assertEqual(hypothesis_tests(sel, a, 0)['status'], 'GO_BREAK_EVEN')

    def test_stop_without_trend(self):
        a = types.SimpleNamespace(bootstrap=300, seed=1, min_rel_gain=.02, min_gain_ms=.1)
        sel, _ = policy_results(self._rows(5., 20.), {'K4_L3_ER2': 'EARLY', 'K8_L3_ER2': 'EARLY'}, 300, 1, .1)
        r = hypothesis_tests(sel, a, 0)
        self.assertEqual(r['status'], 'STOP_NO_PREDICTABLE_BREAK_EVEN'); self.assertIn('E2_no_increasing_trend_in_K', r['fail_reasons'])

    def test_stop_when_nothing_activated(self):
        a = types.SimpleNamespace(bootstrap=300, seed=1, min_rel_gain=.02, min_gain_ms=.1)
        sel, _ = policy_results(self._rows(20., 2.), {'K4_L3_ER2': 'CARD', 'K8_L3_ER2': 'CARD'}, 300, 1, .1)
        r = hypothesis_tests(sel, a, 0)
        self.assertEqual(r['status'], 'STOP_NO_PREDICTABLE_BREAK_EVEN'); self.assertFalse(r['endpoints']['E4_predictability'])

    def test_card_routing_pays_feature_cost(self):
        rows = self._rows(5., 5.)
        for r in rows: r['feature_ms'] = .2
        sel, _ = policy_results(rows, {'K4_L3_ER2': 'CARD', 'K8_L3_ER2': 'EARLY', 'K4_L3_ER0': 'EARLY'}, 300, 1, .1)
        self.assertTrue(all(abs(r['saved_ms'] + .2) < 1e-12 for r in sel if r['K'] == 4))


class Encoding(unittest.TestCase):
    def test_utf8_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.json'; jwrite(p, {'scenario': 'Tòa nhà – Hà Nội'})
            self.assertEqual(rjson(p)['scenario'], 'Tòa nhà – Hà Nội')


if __name__ == '__main__': unittest.main()
