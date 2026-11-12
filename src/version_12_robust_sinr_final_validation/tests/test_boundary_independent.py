import sys,unittest,tempfile,json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from boundary_stress import algebraic_rows,power_reference,algebraic_screen
from ablation_certified import robust_screen,build_Fu
from ablation_audit import RULES

class BoundaryIndependentTests(unittest.TestCase):
    def test_algebraic_boundaries_have_no_false_prunes(self):
        cases=algebraic_rows([1e-3,1e-5,1e-7,1e-9,1e-11],1e-5)
        self.assertEqual(len(cases),20)
        self.assertEqual(sum(x['false_prune'] for x in cases),0)
        self.assertGreater(sum(x['decision']=='FAIL_OPEN' for x in cases),0)
    def test_cycle_boundary_both_sides(self):
        for d in (1e-4,1e-9):
            for sign in (-1,1):
                F=np.array([[0.,1+sign*d],[1.,0.]])
                truth=power_reference(F,np.array([.01,.01]),100.)
                self.assertEqual(truth['status']=='COUPLING',sign>0)
    def test_power_guard_failopen(self):
        F=np.array([[0.,.2],[.2,0.]])
        u=np.array([.01,.01])
        req=float(np.linalg.solve(np.eye(2)-F,u).sum())
        for d in (1e-7,1e-9):
            s=algebraic_screen(F,u,req/(1+d),1e-5)
            self.assertNotEqual(s['decision'],'PRUNE')

if __name__=='__main__':unittest.main()
