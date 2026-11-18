import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import numpy as np
from cost_limits_v14 import feature,apply_rule,build_rules,evaluate_rule,keys_by_group
from reference_model import exhaustive,oracle
from cost_aware_v13 import search,ALPHAS
from ablation_audit import same
CFG={'q':2.960414,'sigma':.04,'gamma':10**.6,'noise':2e-13,'pmax':1.}
class V14Tests(unittest.TestCase):
 def test_features_nonnegative(self):
  x=(np.arange(64).reshape(16,4)+1j).astype(complex)*.01+1
  f=feature(x,CFG);self.assertGreaterEqual(f['early_ratio'],0);self.assertGreaterEqual(f['norm_spread'],0)
 def test_rule_gate(self):
  z={'early_ratio':.5,'norm_spread':2.}
  r={'policy':'EARLY','feature':'early_ratio','threshold':.4,'direction':'ge'}
  self.assertEqual(apply_rule(z,r),'EARLY');r['threshold']=.6;self.assertEqual(apply_rule(z,r),'CARD')
 def test_always_and_card(self):
  z={'early_ratio':.5,'norm_spread':2.}
  self.assertEqual(apply_rule(z,{'policy':'CACHED','feature':'always','threshold':0.,'direction':'ge'}),'CACHED')
  self.assertEqual(apply_rule(z,{'policy':'CARD','feature':'','threshold':0.,'direction':''}),'CARD')
 def test_groups_nonoverlap(self):
  a,b=keys_by_group([str(x) for x in range(40)],217)
  self.assertFalse(a&b);self.assertEqual(len(a|b),40)
 def test_no_false_optimization(self):
  rng=np.random.default_rng(909)
  for _ in range(2):
   H=rng.normal(size=(16,4))+1j*rng.normal(size=(16,4))
   reference=oracle(exhaustive(H,ALPHAS,CFG))
   for p in ('CARD','EARLY','CACHED','HYBRID'):
    actual,_=search(H,CFG,p,1e-5)
    self.assertTrue(same(actual,reference),(p,actual,reference))
 def test_model_uses_feature_charging(self):
  row={'group':'g1','CARD_ms':10.,'EARLY_ms':9.,'feature_ms':2.,'early_ratio':1.,'norm_spread':0.,'CACHED_ms':10.,'HYBRID_ms':10.}
  ev=evaluate_rule([dict(row,group=f'g{i}') for i in range(4)],{'policy':'EARLY','feature':'always','threshold':0.,'direction':'ge'},150)
  self.assertAlmostEqual(ev['mean_saved_ms'],-1.)
if __name__=='__main__':unittest.main()
