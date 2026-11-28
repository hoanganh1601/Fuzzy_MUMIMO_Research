"""V18.3 timing QC and re-timing comparison (no timing, no data files)."""
import math, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_v18 as R  # noqa: E402


def row(routed, lrs, dcs, pbs, card=2):
    return {'set': 'S', 'group': 0, 'K': 4, 'L': 3, 'routed_LRS': routed, 't': {'LRS': lrs, 'DCS': dcs, 'PBS': pbs},
            'card_by': {'DCS': card, 'LRS': card}, 'calls': {'DCS': 10, 'LRS': 10}, 'same': {'LRS': True},
            'p_by': {'DCS': 0.5, 'LRS': 0.5}}


class QC(unittest.TestCase):
    def test_pair_follows_route(self):
        self.assertAlmostEqual(R.identical_pairs(row(0, 2.0, 1.0, 4.0)), 2.0)      # routed to DCS: LRS / DCS
        self.assertAlmostEqual(R.identical_pairs(row(1, 2.0, 1.0, 4.0)), 0.5)      # routed to PBS: LRS / PBS
        self.assertIsNone(R.identical_pairs({'routed_LRS': 0, 't': {}}))         # decisions-only rows carry no timing

    def test_rate_and_threshold(self):
        ok = [row(0, 1.01, 1.0, 9.0) for _ in range(990)] + [row(0, 1.6, 1.0, 9.0) for _ in range(10)]
        q = R.timing_qc(ok); self.assertEqual((q['pairs'], q['discordant']), (1000, 10)); self.assertTrue(q['pass'])
        bad = ok + [row(1, 1.0, 9.0, 1.6)]                                         # 1/1.6 < 1/1.5: discordant
        q = R.timing_qc(bad); self.assertEqual(q['discordant'], 11); self.assertFalse(q['pass'])
        self.assertFalse(abs(math.log(1.49)) > math.log(R.QC_RATIO))               # 1.49x is concordant
        self.assertIsNone(R.timing_qc([])['pass'])

    def test_decisions_identical(self):
        A = {('S', 0, 4, 3): row(0, 1.0, 1.0, 2.0)}
        self.assertTrue(R.decisions_identical(A, {('S', 0, 4, 3): row(0, 7.0, 3.0, 2.0)}))   # timing may differ
        self.assertFalse(R.decisions_identical(A, {('S', 0, 4, 3): row(0, 1.0, 1.0, 2.0, card=3)}))
        b = row(0, 1.0, 1.0, 2.0); b['p_by'] = {'DCS': 0.5, 'LRS': 0.5 * (1 + 1e-6)}
        self.assertFalse(R.decisions_identical(A, {('S', 0, 4, 3): b}))
        self.assertFalse(R.decisions_identical(A, {}))


if __name__ == '__main__':
    unittest.main()
