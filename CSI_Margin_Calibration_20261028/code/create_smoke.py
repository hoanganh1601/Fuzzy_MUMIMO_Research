import argparse,numpy as np
p=argparse.ArgumentParser();p.add_argument('--output',default='data/smoke.npz');p.add_argument('--groups',type=int,default=48);p.add_argument('--per-group',type=int,default=2);a=p.parse_args()
r=np.random.default_rng(7206);N=a.groups*a.per_group;H=(r.normal(size=(N,16,4))+1j*r.normal(size=(N,16,4)))/np.sqrt(32)
g=np.repeat(np.arange(a.groups),a.per_group)
from pathlib import Path
Path(a.output).parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(a.output,H=H,groups=g)
print('SYNTHETIC SMOKE DATA ONLY',N)
