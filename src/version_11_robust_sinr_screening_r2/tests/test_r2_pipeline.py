"""R2 tests: shared beam coefficients, deterministic tie-breaking, one-pass pipeline."""
import sys, unittest, itertools
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from reference_model import solve, coefficients, power_solve, select_best, exhaustive, oracle
from ablation_certified import selection, BASE_VARIANTS
from ablation_audit import same, screening, RULES
from make_synthetic import generate

CFG = dict(q=2.960414, sigma=.04, gamma=10**.6, noise=2e-13, pmax=1.)
ALPHAS = [0, .001, .01, .05, .1, .3, 1]


class SharedCoefficients(unittest.TestCase):
    def test_split_solve_identical(self):
        H, _, _ = generate(2, 2, 16, 4, 7)
        for h in H:
            for s in range(1, 5):
                for sub in itertools.combinations(range(4), s):
                    for a in (0., .01):
                        self.assertEqual(solve(h, list(sub), a, CFG), power_solve(coefficients(h, list(sub), a, CFG), CFG))

    def test_every_variant_matches_exhaustive_and_builds_each_beam_once(self):
        H, _, _ = generate(3, 2, 16, 4, 11)
        for h in H:
            ref = oracle(exhaustive(h, ALPHAS, CFG))
            for name, en in BASE_VARIANTS:
                choice, st = selection(h, ALPHAS, CFG, en, 1e-5)
                self.assertTrue(same(choice, ref), name)
                self.assertLessEqual(st['beams_built'], st['screened'])
                self.assertGreaterEqual(st['beams_built'], st['full_solves'])

    def test_cache_does_not_change_decision(self):
        H, _, _ = generate(2, 2, 16, 4, 13)
        for h in H:
            for sub in [(0, 1), (0, 1, 2, 3)]:
                for a in (0., .1):
                    self.assertEqual(screening(h, sub, a, dict(CFG, pmax=1e-3), set(RULES))[:2],
                                     screening(h, sub, a, dict(CFG, pmax=1e-3), set(RULES), {})[:2])


class TieBreaking(unittest.TestCase):
    def test_rule_order(self):
        c = lambda sub, k, a, p: dict(subset=sub, cardinality=k, alpha=a, p_req_w=p)
        cands = [c('012', 3, .1, 1.0), c('013', 3, 0., 1.0 * (1 + 5e-10)), c('123', 3, 0., 1.0), c('0123', 4, 1., 9.)]
        self.assertEqual(select_best(cands)['subset'], '0123')
        best = select_best(cands[:3])
        self.assertEqual((best['subset'], best['alpha']), ('013', 0.))  # tie within 1e-9 -> ZF, then subset label
        self.assertIsNone(select_best([]))


if __name__ == '__main__': unittest.main()
