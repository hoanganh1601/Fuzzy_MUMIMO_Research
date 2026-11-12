"""Boundary guard, oracle separation, and conservative certificate tests."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from ablation_certified import robust_screen, selection, build_Fu, high_precision_recheck
from reference_model import exhaustive, oracle


class AuditTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(321)
        self.h=(rng.normal(size=(8,4))+1j*rng.normal(size=(8,4)))/np.sqrt(16)
        self.cfg=dict(q=2.960414,sigma=.04,gamma=10**(.6),noise=2e-4,pmax=1.)

    def test_failopen_near_noise_power_limit(self):
        c=build_Fu(self.h,(0,),0.01,self.cfg)
        self.assertFalse(c['zero'])
        # single-user noise bound exactly matches requirement; make it barely
        # exceed budget (without crossing the hard 1e-8 pruning tolerance).
        self.cfg['pmax']=float(sum(c['u']))/(1+3e-8)
        skip,rec=robust_screen(self.h,(0,),0.01,self.cfg,
                               {'NOISE_LOWER_BOUND'},1e-5)
        self.assertFalse(skip)
        self.assertTrue(rec['fail_open'])
        self.assertTrue(rec['mp_checked'])

    def test_survivor_no_rules_matches_oracle(self):
        alphas=[0.,.001,.01]
        o=oracle(exhaustive(self.h,alphas,self.cfg))
        s,stats=selection(self.h,alphas,self.cfg,set(),1e-5)
        self.assertEqual(s['subset'],o['subset'])
        self.assertAlmostEqual(s['p_req_w'],o['p_req_w'],places=8)
        self.assertEqual(stats['certificate_pruned'],0)

    def test_certificates_no_false_prune(self):
        rng=np.random.default_rng(678)
        alphas=[0.,.001,.01]
        for _ in range(8):
            h=(rng.normal(size=(8,4))+1j*rng.normal(size=(8,4)))/np.sqrt(16)
            for s in range(1,5):
                import itertools
                for sub in itertools.combinations(range(4),s):
                    for a in alphas:
                        skip,_=robust_screen(h,sub,a,self.cfg,
                            {'NORM_NOISE_LOWER_BOUND','ZERO_ROBUST_GAIN',
                             'NOISE_LOWER_BOUND','NEUMANN_LOWER_BOUND',
                             'TWO_CYCLE_COUPLING'},1e-5)
                        if skip:
                            from reference_model import solve
                            self.assertNotEqual(solve(h,list(sub),a,self.cfg)['status'],'FEASIBLE')

if __name__=='__main__': unittest.main()
