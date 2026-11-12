import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import numpy as np
from final_runtime_validation import safe_prune,RULESETS,search
from reference_model import exhaustive,oracle
from ablation_audit import same

class FinalRuntimeChecks(unittest.TestCase):
    def test_strict_noise_certificate(self):
        cfg={'pmax':1.}
        comp=dict(zero=False,F=np.zeros((2,2)),u=np.array([.8,.4]))
        self.assertEqual(safe_prune(comp,cfg,RULESETS['FAST'],1e-5)[0],True)
    def test_near_power_fail_open(self):
        comp=dict(zero=False,F=np.zeros((2,2)),u=np.array([.6,.40000001]))
        prune,reason,flag=safe_prune(comp,{'pmax':1.},RULESETS['FAST'],1e-5)
        self.assertFalse(prune);self.assertTrue(flag)
    def test_two_cycle_prunes(self):
        comp=dict(zero=False,F=np.array([[0.,1.2],[.9,0.]]),u=np.array([.1,.1]))
        prune,reason,flag=safe_prune(comp,{'pmax':1.},RULESETS['LITE'],1e-5)
        self.assertTrue(prune)
    def test_oracle_small_channels(self):
        rng=np.random.default_rng(22)
        cfg=dict(q=2.960414,sigma=.04,gamma=10**(.6),noise=2e-13,pmax=1.)
        for _ in range(3):
            h=rng.normal(size=(16,4))+1j*rng.normal(size=(16,4))
            alpha=[0,0.001,0.01,0.05,0.1,0.3,1.]
            ref=oracle(exhaustive(h,alpha,cfg))
            for variant in RULESETS:
                choice,_=search(h,cfg,alpha,variant,1e-5)
                self.assertTrue(same(choice,ref),variant)
if __name__=='__main__':unittest.main()
