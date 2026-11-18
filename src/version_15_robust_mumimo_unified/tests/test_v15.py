import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from run_experiment import search,process_one,choose_policy,channel_features,split_groups,same_choice
class TestV15(unittest.TestCase):
 def setUp(self):
  rng=np.random.default_rng(31)
  self.h=(rng.normal(size=(12,8))+1j*rng.normal(size=(12,8)))*.02
  self.cfg={'q':2.960414,'sigma':.04,'gamma':10**(.6),'noise':2e-13,'pmax':1.}
 def test_oracle_for_k4_k6_k8(self):
  for k in (4,6,8):
   ref,_,_=search(self.h[:,:k],(0.,.01),self.cfg,'CARD',1e-5)
   for policy in ('EARLY','CACHED','HYBRID'):
    x,_,_=search(self.h[:,:k],(0.,.01),self.cfg,policy,1e-5)
    self.assertTrue(same_choice(x,ref),(k,policy))
 def test_features_and_condition(self):
  z=channel_features(self.h,self.cfg)
  self.assertIn(z['difficulty'],('low','medium','high'))
  self.assertTrue(np.isfinite(z['early_ratio']))
 def test_small_cell_fallback(self):
  rows=[{'K':4,'L':3,'difficulty':'high','group':'A','policy':'EARLY','saving_ms':1.},
        {'K':4,'L':3,'difficulty':'high','group':'B','policy':'EARLY','saving_ms':2.}]
  fit={'A'};valid={'B'}
  lock,details=choose_policy(rows,fit,valid,100,.1,5)
  self.assertEqual(lock['K4_L3_high'],'CARD')
 def test_group_split(self):
  a,b=split_groups(['a','b','c','d','e','f'],12)
  self.assertFalse(a&b);self.assertEqual(len(a|b),6)
if __name__=='__main__':unittest.main()
