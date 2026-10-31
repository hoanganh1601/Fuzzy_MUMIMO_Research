import numpy as np
from pathlib import Path
r=np.random.default_rng(20261029);N=36;M=16;K=4
H=(r.normal(size=(N,M,K))+1j*r.normal(size=(N,M,K)))/np.sqrt(2)
H*=np.sqrt(2e-10)
# intentionally correlated user channels for diagnosis
for i in range(0,N,3):H[i,:,1]=0.85*H[i,:,0]+0.15*H[i,:,1]
p=Path('data/synthetic_diagnostic.npz');p.parent.mkdir(parents=True,exist_ok=True)
np.savez_compressed(p,H=H,groups=np.arange(N),scenario=np.array(['synthetic']*N))
print(p)
