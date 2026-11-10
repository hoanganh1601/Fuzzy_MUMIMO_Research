"""Regression tests for defects fixed in code review R1 (2026-11-06)."""
import sys, unittest, itertools
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
import safe_pruning
from reference_model import solve, POWER_REL_TOL, PRUNE_REL_MARGIN, check_count
from ablation_audit import screening, RULES
from ablation_certified import selection, high_precision_recheck, build_Fu
from boundary_stress import algebraic_rows, power_reference, decide


def channel(seed=321):
    rng = np.random.default_rng(seed)
    return (rng.normal(size=(8, 4)) + 1j * rng.normal(size=(8, 4))) / 4


CFG = dict(q=2.960414, sigma=.04, gamma=10**.6, noise=2e-4, pmax=1.)


class ToleranceConsistency(unittest.TestCase):
    def test_margin_not_tighter_than_solver_tolerance(self):
        self.assertGreaterEqual(PRUNE_REL_MARGIN, POWER_REL_TOL)

    def test_safe_pruning_no_false_prune_inside_solver_tolerance(self):
        # Budget 5e-10 below the requirement: solve() accepts it (tol 1e-9).
        # The former 1e-10 screening margin pruned it -> false prune.
        h = channel()
        for alpha in (0., .01):
            req = solve(h, [0], alpha, CFG)['p_req_w']
            cfg = dict(CFG, pmax=req / (1 + 5e-10))
            self.assertEqual(solve(h, [0], alpha, cfg)['status'], 'FEASIBLE')
            skip, reason, _ = safe_pruning.screening(h, (0,), alpha, cfg)
            self.assertFalse(skip, reason)

    def test_all_screens_safe_on_dense_budget_sweep(self):
        h = channel(5)
        for alpha in (0., .01):
            req = solve(h, [0, 1], alpha, CFG)['p_req_w']
            if req is None: continue
            for rel in (-1e-6, -1e-9, -5e-10, 0., 5e-10, 1e-9, 2e-9, 1e-8, 1e-6):
                cfg = dict(CFG, pmax=req / (1 + rel))
                feasible = solve(h, [0, 1], alpha, cfg)['status'] == 'FEASIBLE'
                if feasible:
                    self.assertFalse(safe_pruning.screening(h, (0, 1), alpha, cfg)[0])
                    self.assertFalse(screening(h, (0, 1), alpha, cfg, set(RULES))[0])


class BaselineFairness(unittest.TestCase):
    def test_cardinality_only_does_no_screening_work(self):
        h = channel()
        _, stats = selection(h, [0., .01], CFG, set(), 1e-5)
        self.assertEqual(stats['screening_ms'], 0.0)
        self.assertEqual(stats['certificate_pruned'], 0)

    def test_lazy_screening_same_decisions(self):
        # Lazy evaluation must not change any decision for any rule subset.
        rng = np.random.default_rng(11)
        for _ in range(3):
            h = (rng.normal(size=(8, 4)) + 1j * rng.normal(size=(8, 4))) / 4
            for k in range(len(RULES) + 1):
                for en in itertools.combinations(RULES, k):
                    for sub in [(0,), (0, 1), (0, 1, 2, 3)]:
                        skip, reason, _, _ = screening(h, sub, .01, dict(CFG, pmax=.02), set(en))
                        if skip:
                            self.assertIn(reason, en)
                            self.assertNotEqual(solve(h, list(sub), .01, dict(CFG, pmax=.02))['status'], 'FEASIBLE')


class ExactReference(unittest.TestCase):
    def test_m_matrix_rule_matches_spectral_radius_3x3(self):
        rng = np.random.default_rng(3)
        for _ in range(50):
            F = rng.uniform(0, .8, size=(3, 3)); np.fill_diagonal(F, 0)
            rho = max(abs(np.linalg.eigvals(F)))
            if abs(rho - 1) < 1e-6: continue
            truth = power_reference(F, np.full(3, .01), 1e9)
            self.assertEqual(truth['status'] == 'COUPLING', rho >= 1)

    def test_recheck_is_exact_rational(self):
        h = channel()
        r = high_precision_recheck(h, (0, 1), .01, CFG, 'NOISE_LOWER_BOUND')
        self.assertTrue(r['checked'])
        u = build_Fu(h, (0, 1), .01, CFG)['u']
        self.assertAlmostEqual(float(r['mp_value']), float(np.sum(u)), places=12)


class BoundaryCoverage(unittest.TestCase):
    def test_every_family_has_feasible_side(self):
        rows = algebraic_rows([1e-3, 1e-5, 1e-7, 1e-9, 1e-11], 1e-5)
        for fam in ('COUPLING', 'POWER', 'POWER_TIGHT'):
            fr = [r for r in rows if r['boundary'] == fam]
            self.assertTrue(all(r['mp_truth'] == 'FEASIBLE' for r in fr if r['sign'] < 0), fam)
            self.assertTrue(all(r['mp_truth'] != 'FEASIBLE' for r in fr if r['sign'] > 0), fam)

    def test_tight_power_boundary_hits_guard(self):
        # delta strictly inside the guard; delta == guard is a rounding knife-edge.
        rows = [r for r in algebraic_rows([1e-3, 5e-6, 1e-9], 1e-5) if r['boundary'] == 'POWER_TIGHT' and r['sign'] > 0]
        self.assertEqual([r['decision'] for r in rows], ['PRUNE', 'FAIL_OPEN', 'SURVIVE'])

    def test_decision_rejects_vacuous_run(self):
        rows = [dict(source='algebraic', boundary='X', mp_truth='POWER_BUDGET', decision='SURVIVE', false_prune=0)]
        self.assertEqual(decide(rows)['outcome'], 'FAIL')


class Validation(unittest.TestCase):
    def test_check_count(self):
        self.assertEqual(check_count(0, 5), 5)
        self.assertEqual(check_count(3, 5), 3)
        with self.assertRaises(ValueError): check_count(-1, 5)
        with self.assertRaises(ValueError): check_count(0, 0)


if __name__ == '__main__': unittest.main()
