import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import numpy as np
from safe_pruning import select_pruned
from reference_model import exhaustive,oracle

class PruningTests(unittest.TestCase):
 def test_no_false_pruning_random(self):
  alphas=[0.,.001,.01,.1,1.]
  for seed in range(4):
   rng=np.random.default_rng(seed)
   H=(rng.normal(size=(8,4))+1j*rng.normal(size=(8,4)))/np.sqrt(2)
   for budget in (.002,1.):
    cfg=dict(q=2.960414,sigma=.04,gamma=10**(.6),noise=1e-4,pmax=budget)
    p,audit,stats=select_pruned(H,alphas,cfg)
    baseline=exhaustive(H,alphas,cfg);o=oracle(baseline)
    self.assertEqual(p is None,o is None)
    if o:
     self.assertEqual((p['subset'],p['cardinality'],p['alpha']), (o['subset'],o['cardinality'],o['alpha']))
     self.assertAlmostEqual(p['p_req_w'],o['p_req_w'],places=8)
    d={(r['subset'],r['alpha']):r for r in baseline}
    for a in audit:
     if a['pruned']:self.assertNotEqual(d[(a['subset'],a['alpha'])]['status'],'FEASIBLE')
 def test_high_noise_norm_certificate(self):
  rng=np.random.default_rng(42);H=rng.normal(size=(8,4))+1j*rng.normal(size=(8,4))
  cfg=dict(q=2.960414,sigma=.04,gamma=4.,noise=1.,pmax=.01)
  p,audit,stats=select_pruned(H,[0.,.01],cfg)
  self.assertIsNone(p)
  self.assertGreater(stats['pruned_by_certificate'],0)
if __name__=='__main__':unittest.main()
