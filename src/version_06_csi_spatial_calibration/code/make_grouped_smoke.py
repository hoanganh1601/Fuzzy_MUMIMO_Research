import argparse
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--output',default='data/grouped_smoke.npz');p.add_argument('--groups',type=int,default=140);p.add_argument('--seed',type=int,default=91);a=p.parse_args()
r=np.random.default_rng(a.seed);N=a.groups;M,K=16,4
H=(r.standard_normal((N,M,K))+1j*r.standard_normal((N,M,K)))/np.sqrt(2*M)
# Each synthetic group has one position, 100m apart. Synthetic spatial separation != independence in real data.
xyz=np.stack([np.arange(N)*100.,np.zeros(N),np.zeros(N)],axis=1)
np.savez_compressed(a.output,H=H,groups=np.array([f'g{i:04d}' for i in range(N)]),xyz=xyz,scenario=np.array(['synthetic']*N))
print('Saved',a.output)
