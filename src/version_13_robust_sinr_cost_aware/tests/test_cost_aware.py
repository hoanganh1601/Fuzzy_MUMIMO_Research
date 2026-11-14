import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import numpy as np
from cost_aware_v13 import early_bound,post_bound,from_comp,search,ALPHAS,group_ci
from reference_model import solve,exhaustive,oracle
from ablation_certified import build_Fu
from ablation_audit import same
CFG=dict(q=2.960414,sigma=.04,gamma=10**(.6),noise=2e-13,pmax=1.)
class CostAwareTests(unittest.TestCase):
    def test_early_safe_infeasible(self):
        h=np.ones((16,4),complex)*1e-8
        yes,why,_,_=early_bound(h,(0,1,2,3),CFG,1e-5)
        self.assertTrue(yes);self.assertEqual(why,'EARLY_NORM_BOUND')
    def test_early_fail_open(self):
        h=np.ones((16,4),complex)
        self.assertFalse(early_bound(h,(0,1),CFG,1e-5)[0])
    def test_consistent_solver(self):
        rng=np.random.default_rng(7)
        h=(rng.normal(size=(16,4))+1j*rng.normal(size=(16,4)))/np.sqrt(2)
        for sub in ((0,),(0,1),(0,1,2,3)):
            for a in ALPHAS:
                r=solve(h,list(sub),a,CFG)
                x=from_comp(build_Fu(h,sub,a,CFG),CFG)
                self.assertEqual(r['status'],x['status'],(sub,a))
                if r['status']=='FEASIBLE':self.assertAlmostEqual(r['p_req_w'],x['p_req_w'],places=12)
    def test_all_exact(self):
        rng=np.random.default_rng(11)
        for _ in range(3):
            h=(rng.normal(size=(16,4))+1j*rng.normal(size=(16,4)))*.3
            ref=oracle(exhaustive(h,ALPHAS,CFG))
            for p in ('CARD','EARLY','CACHED','HYBRID'):
                x,_=search(h,CFG,p,1e-5)
                self.assertTrue(same(x,ref),p)
    def test_group_bootstrap(self):
        ci=group_ci([1,2,3,4,5,6],[1,1,2,2,3,3],150)
        self.assertEqual(len(ci),2)
        self.assertGreater(ci[1],ci[0])
if __name__=='__main__':unittest.main()
