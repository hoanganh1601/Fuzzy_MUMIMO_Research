#!/usr/bin/env python3
"""For software smoke testing ONLY. NOT DeepMIMO, NOT 3GPP."""
import argparse,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--n',type=int,default=18)
p.add_argument('--seed',type=int,default=123);p.add_argument('--prefix',default='DEV')
p.add_argument('--m',type=int,default=16);a=p.parse_args()
if a.m<8:raise ValueError('Need M>=8')
rng=np.random.default_rng(a.seed);h=[];grp=[];level=[]
for i in range(a.n):
    difficulty=['low','medium','high'][i%3]
    x=(rng.normal(size=(a.m,8))+1j*rng.normal(size=(a.m,8)))/np.sqrt(2*a.m)
    if difficulty=='medium':
        common=(rng.normal(size=(a.m,1))+1j*rng.normal(size=(a.m,1)))/np.sqrt(2*a.m)
        x=.7*common+.714*x
    if difficulty=='high':
        common=(rng.normal(size=(a.m,1))+1j*rng.normal(size=(a.m,1)))/np.sqrt(2*a.m)
        x=.95*common+.312*x
    # positive scale near powers where feasibility can vary
    x=x*(10**rng.uniform(-2.8,-1.0))
    h.append(x);grp.append(a.prefix+f'_{i:05d}');level.append(difficulty)
Path(a.output).parent.mkdir(parents=True,exist_ok=True)
np.savez_compressed(a.output,H=np.asarray(h),groups=np.asarray(grp),scenario=np.array('synthetic_only'))
Path(a.output+'.provenance.json').write_text(json.dumps({'source':'synthetic_smoke','scenario':'synthetic_only','group_definition':'one independent RNG realization per group','independence_basis':'independent PRNG streams under fixed seed','prior_use':'smoke','difficulty_labels':level},indent=2))
print(a.output,len(h))
