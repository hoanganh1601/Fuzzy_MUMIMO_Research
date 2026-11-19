#!/usr/bin/env python3
"""Pack externally extracted DeepMIMO per-user channels and coordinates into 8-user drops.
Does NOT download DeepMIMO or pretend spatial separation proves statistical independence.
Input NPZ: user_channels (U,M) complex, user_positions (U,3) float.
One drop per spatial tile; no same user reused across tiles. Split by tile or scenario externally.
"""
import argparse,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
p.add_argument('--cell-m',type=float,default=50.);p.add_argument('--min-user-distance',type=float,default=2.)
p.add_argument('--max-geometries',type=int,default=1000);p.add_argument('--seed',type=int,default=20261117)
p.add_argument('--prefix',default='DEEP');p.add_argument('--scenario',required=True)
a=p.parse_args();rng=np.random.default_rng(a.seed)
with np.load(a.input,allow_pickle=False) as d:
 h=d['user_channels'];xyz=d['user_positions']
if h.ndim!=2 or not np.iscomplexobj(h) or xyz.shape!=(len(h),3) or h.shape[1]<8:raise ValueError('Required user_channels (U,M>=8) complex and positions (U,3)')
if not np.isfinite(h).all() or not np.isfinite(xyz).all():raise ValueError('Nonfinite channels/positions')
xy=xyz[:,:2];origin=np.min(xy,axis=0);cells=np.floor((xy-origin)/a.cell_m).astype(int)
bins={}
for j,c in enumerate(cells):bins.setdefault(tuple(c),[]).append(j)
drops=[];groups=[];selected=[];excluded=0
for cell,idx in sorted(bins.items()):
 if len(idx)<8:excluded+=1;continue
 idx=list(rng.permutation(idx));taken=[]
 for u in idx:
  if all(np.linalg.norm(xyz[u]-xyz[v])>=a.min_user_distance for v in taken):taken.append(u)
  if len(taken)==8:break
 if len(taken)!=8:excluded+=1;continue
 drops.append(h[np.asarray(taken)].T)
 groups.append(f'{a.prefix}_{cell[0]}_{cell[1]}')
 selected.append(taken)
 if len(drops)>=a.max_geometries:break
if not drops:raise RuntimeError('No cells with eight separated users; change tile size or source')
Path(a.output).parent.mkdir(parents=True,exist_ok=True)
np.savez_compressed(a.output,H=np.stack(drops),groups=np.asarray(groups),scenario=np.array(a.scenario),
                    user_indices=np.asarray(selected),xyz=xyz[np.asarray(selected)])
meta={'source':'DeepMIMO external extraction','scenario':a.scenario,'group_definition':'spatial tile (one 8-user drop per tile)',
 'independence_basis':'spatially disjoint tiles; independence NOT mathematically proven',
 'prior_use':'REPLACE_WITH_NEVER_SEEN_OR_DEVELOPMENT','cell_m':a.cell_m,'min_user_distance':a.min_user_distance,
 'selected_geometries':len(drops),'excluded_tiles':excluded,'seed':a.seed}
Path(a.output+'.provenance.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf8')
print('PACKED',len(drops),'geometries; review provenance before official evaluation')
