#!/usr/bin/env python3
"""Independent robust MU-MIMO fuzzy margin pilot. No trained/test leakage."""
import argparse,csv,hashlib,json,os,time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.stats import norm

METHODS=('gaussian','fixed','threshold','sugeno')

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def atomic_json(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
 with open(tmp,'w',encoding='utf8') as f:json.dump(data,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def atomic_csv(path,rows,cols):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
 with open(tmp,'w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def load_data(path,M,K):
 d=np.load(path,allow_pickle=False)
 if 'H' not in d:raise ValueError('NPZ must contain H')
 H=d['H']
 if H.ndim!=3 or H.shape[1:]!=(M,K):raise ValueError(f'H must have shape (N,{M},{K}), got {H.shape}')
 if not np.iscomplexobj(H) or not np.isfinite(H).all():raise ValueError('H needs finite complex samples')
 if 'groups' not in d:raise ValueError('groups is mandatory for disjoint site/scenario split')
 groups=d['groups']
 if len(groups)!=len(H):raise ValueError('groups length differs')
 if len(np.unique(groups))<3:raise ValueError('at least 3 distinct groups required')
 return H,groups

def grouped_split(groups,seed):
 uniq=np.unique(groups);rng=np.random.default_rng(seed);u=rng.permutation(uniq)
 a=max(1,int(.6*len(u)));b=max(a+1,int(.8*len(u)));b=min(b,len(u)-1)
 if b<=a:raise ValueError('need >=5 groups for train val test')
 masks=[np.isin(groups,u[lo:hi]) for lo,hi in ((0,a),(a,b),(b,len(u)))]
 if any(not x.any() for x in masks):raise ValueError('empty grouped split')
 return masks

def rzf(H,reg=.05):
 M,K=H.shape
 try:V=H@np.linalg.solve(H.conj().T@H+reg*np.trace(H.conj().T@H).real/K*np.eye(K)+1e-12*np.eye(K),np.eye(K))
 except np.linalg.LinAlgError:return None
 norms=np.linalg.norm(V,axis=0)
 return V/np.maximum(norms,1e-30)

def coupling(H,V,q,sigma_rel,sinr,noise):
 M,K=H.shape
 # conservative simultaneous bound for each channel vector perturbation norm.
 # For each k: |(h+e)^H v_j| in [|h^H v_j|-||e|| ||v_j||, ...].
 gains=np.abs(H.conj().T@V)
 radii=q*sigma_rel*np.linalg.norm(H,axis=0)/np.sqrt(M) # normalized radial design parameter, NOT Gaussian joint guarantee
 diag=np.maximum(gains.diagonal()-radii,0)**2
 if np.min(diag)<=1e-24:return None
 upper=(gains+radii[:,None])**2
 K=len(diag);F=np.zeros((K,K));u=np.zeros(K)
 for k in range(K):
  for j in range(K):
   if j!=k:F[k,j]=sinr*upper[k,j]/diag[k]
  u[k]=sinr*noise/diag[k]
 return F,u

def power_lp(H,V,q,cfg):
 val=coupling(H,V,q,cfg['sigma_rel'],cfg['sinr'],cfg['noise'])
 if val is None:return None,np.inf
 F,u=val;rho=max(abs(np.linalg.eigvals(F)))
 if rho>=1-1e-10:return None,float(rho)
 try:p=np.linalg.solve(np.eye(len(u))-F,u)
 except np.linalg.LinAlgError:return None,float(rho)
 if not np.all(np.isfinite(p)) or np.min(p)<-1e-10 or np.sum(p)>cfg['pmax']*(1+1e-8):return None,float(rho)
 # Direct audit of conservative inequalities (LP solved analytically for M matrix).
 if np.min(p-F@p-u)<-1e-8*max(np.max(u),1e-12):return None,float(rho)
 return np.maximum(p,0),float(rho)

def features(H,V,cfg,qref):
 G=H.conj().T@H;sv=np.linalg.svd(G,compute_uv=False);cond=float(sv[0]/max(sv[-1],1e-14))
 tmp=coupling(H,V,qref,cfg['sigma_rel'],cfg['sinr'],cfg['noise'])
 rho=float(max(abs(np.linalg.eigvals(tmp[0])))) if tmp is not None else 10.
 return np.array([np.clip(np.log10(max(cond,1)),0,8)/8,np.clip(rho/2,0,1)])

def triangle(x,c,w):return max(0.,1-abs(x-c)/w)

def fuzzy_q(z,constants):
 # Two inputs, 3 fuzzy sets each, 9 zero-order Sugeno rules.
 weights=np.array([triangle(z[0],c,.55)*triangle(z[1],d,.55) for c in (0,.5,1) for d in (0,.5,1)])
 if weights.sum()<1e-15:return float(np.mean(constants))
 return float(np.dot(weights,constants)/weights.sum())

def choose_q(method,z,param):
 if method=='gaussian':return param['qgauss']
 if method=='fixed':return param['qfixed']
 if method=='threshold':return param['qlo'] if z[1]>.5 else param['qhi']
 return fuzzy_q(z,param['rules'])

def evaluate_batch(H,indices,params,cfg,n_mc,seed,tag):
 out=[]
 for ii in indices:
  actual=H[ii];rng=np.random.default_rng(np.random.SeedSequence([seed,int(ii),227]))
  # shared error distribution and samples per channel, no real CSI used in policy.
  err=(rng.normal(size=actual.shape)+1j*rng.normal(size=actual.shape))/np.sqrt(2*actual.shape[0]);scale=cfg['sigma_rel']
  est=actual+scale*np.linalg.norm(actual,axis=0)[None,:]*err
  V=rzf(est)
  if V is None:continue
  z=features(est,V,cfg,params['qgauss'])
  # Monte Carlo true channel conditional on estimated channel using SIMULATED error law, not original actual.
  rmc=np.random.default_rng(np.random.SeedSequence([seed,int(ii),921]))
  innovations=(rmc.normal(size=(n_mc,*est.shape))+1j*rmc.normal(size=(n_mc,*est.shape)))/np.sqrt(2*est.shape[0])
  true=est[None,:,:]+scale*np.linalg.norm(est,axis=0)[None,None,:]*innovations
  for method in METHODS:
   q=choose_q(method,z,params);tic=time.perf_counter();p,rho=power_lp(est,V,q,cfg);runtime=time.perf_counter()-tic
   if p is None:out.append(dict(index=int(ii),cohort=tag,method=method,feasible=0,q=q,power_w='',rho=rho,n_mc=0,failures=0,outage='',runtime_s=runtime,z1=z[0],z2=z[1]));continue
   gain=np.abs(np.einsum('nmk,mj->nkj',true.conj(),V))**2
   desired=p[None,:]*np.diagonal(gain,axis1=1,axis2=2)
   interf=np.einsum('nkj,j->nk',gain,p)-desired+cfg['noise']
   fail=int(np.sum(np.any(desired/interf<cfg['sinr'],axis=1)))
   out.append(dict(index=int(ii),cohort=tag,method=method,feasible=1,q=q,power_w=float(np.sum(p)),rho=rho,n_mc=n_mc,failures=fail,outage=fail/n_mc,runtime_s=runtime,z1=z[0],z2=z[1]))
 return out

def summarize(rows):
 ans=[]
 for tag in sorted(set(r['cohort'] for r in rows)):
  for method in METHODS:
   rr=[r for r in rows if r['cohort']==tag and r['method']==method];valid=[r for r in rr if r['feasible']]
   eff=np.mean([float(r['outage']) if r['feasible'] else 1 for r in rr]);out=np.mean([float(r['outage']) for r in valid]) if valid else np.nan
   ans.append(dict(cohort=tag,method=method,n=len(rr),feasible=len(valid),conditional_outage=out,effective_failure=eff,mean_feasible_power_w=np.mean([r['power_w'] for r in valid]) if valid else np.nan))
 return ans

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['preflight','develop','freeze','test','report','all'],required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--run-id',required=True);ap.add_argument('--out-root',default='outputs');ap.add_argument('--M',type=int,default=8);ap.add_argument('--K',type=int,default=4);ap.add_argument('--sigma-rel',type=float,default=.04);ap.add_argument('--sinr-db',type=float,default=6);ap.add_argument('--noise',type=float,default=1e-9);ap.add_argument('--pmax',type=float,default=1.);ap.add_argument('--seed',type=int,default=20261019);ap.add_argument('--n-mc',type=int,default=300);ap.add_argument('--limit',type=int,default=0);ap.add_argument('--frozen-from',default='')
 a=ap.parse_args();dataset=Path(a.dataset).resolve();H,groups=load_data(dataset,a.M,a.K)
 masks=grouped_split(groups,a.seed);config=dict(sigma_rel=a.sigma_rel,sinr=10**(a.sinr_db/10),noise=a.noise,pmax=a.pmax)
 if not (0<a.sigma_rel<1 and a.noise>0 and a.pmax>0 and a.n_mc>=1):ap.error('invalid physical or MC arguments')
 root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
 sigdata=dict(code_sha256=sha(__file__),dataset_sha256=sha(dataset),settings={k:v for k,v in vars(a).items() if k not in ('stage','out_root','run_id')},n=len(H),group_counts=[int(m.sum()) for m in masks]);signature=hashlib.sha256(json.dumps(sigdata,sort_keys=True).encode()).hexdigest()
 manifest=root/'cp00_manifest.json'
 if manifest.exists():
  if json.loads(manifest.read_text())['signature']!=signature:raise RuntimeError('Manifest signature mismatch: use a new run-id')
 else:atomic_json(manifest,dict(signature=signature,**sigdata))
 if a.stage=='preflight':print('PASS grouped split:',sigdata['group_counts']);return
 params=dict(qgauss=float(np.sqrt(-2*np.log(.05/(a.K)))),qfixed=1.0,qlo=.55,qhi=1.45,rules=np.ones(9).tolist())
 idx=np.flatnonzero(masks[1]);testidx=np.flatnonzero(masks[2]);idx=idx[:a.limit] if a.limit else idx;testidx=testidx[:a.limit] if a.limit else testidx
 dev=root/'tasks'/'validation';test=root/'tasks'/'test'
 def tasks(dest,indices,par,tag):
  for i in indices:
   fp=dest/f'{i:07d}.json'
   if fp.exists():
    o=json.loads(fp.read_text());
    if o['signature']==signature and o['complete']:continue
    raise RuntimeError('Task signature mismatch')
   rows=evaluate_batch(H,[i],par,config,a.n_mc,a.seed,tag);atomic_json(fp,dict(signature=signature,complete=True,rows=rows))
 def load_tasks(dest,indices):
  vals=[]
  for i in indices:
   p=dest/f'{i:07d}.json'
   if not p.exists():raise RuntimeError(f'Missing checkpoint: {p}')
   x=json.loads(p.read_text());assert x['signature']==signature and x['complete'];vals.extend(x['rows'])
  return vals
 if a.stage in ('develop','all'):
  # validation compares fixed and fuzzy on same data, selection NOT via test.
  # Simple interpretable candidates, no overparameterized training.
  candidates=[]
  for j,qsmall in enumerate((.45,.65,.85)):
   p=dict(params);p['qfixed']=qsmall;p['qlo']=qsmall;p['qhi']=min(qsmall+.7,1.8);p['rules']=[max(.3,min(1.8,qsmall+.2*(x//3)+.1*(x%3))) for x in range(9)]
   vals=evaluate_batch(H,idx,p,config,min(a.n_mc,300),a.seed+501,'validation');s=summarize(vals)
   chosen=[r for r in s if r['method']=='sugeno'][0];candidates.append(dict(candidate=j,params=p,eff=chosen['effective_failure'],power=chosen['mean_feasible_power_w'],feasible=chosen['feasible']))
  atomic_json(root/'cp01_candidates.json',candidates)
 if a.stage in ('freeze','all'):
  candidates=json.loads((root/'cp01_candidates.json').read_text())
  # objective: first reliability <= 10%, then minimum power; fallback most reliable.
  eligible=[x for x in candidates if x['eff']<=.10]
  best=min(eligible,key=lambda x:x['power']) if eligible else min(candidates,key=lambda x:x['eff'])
  atomic_json(root/'cp02_frozen.json',dict(signature=signature,selected=best,criterion='validation effective failure <= 0.10 then minimum mean power; fallback min effective failure',eligible=bool(eligible)))
 if a.stage in ('test','all'):
  if a.frozen_from:
   f=json.loads(Path(a.frozen_from).read_text())
   if 'selected' not in f:raise RuntimeError('External frozen file lacks selected parameters')
   atomic_json(root/'cp02_frozen.json',dict(signature=signature,selected=f['selected'],transferred_from=str(Path(a.frozen_from).resolve()),criterion='external frozen transfer: no 3GPP tuning'))
  else:
   f=json.loads((root/'cp02_frozen.json').read_text());assert f['signature']==signature
  tasks(test,testidx,f['selected']['params'],'test')
 if a.stage in ('report','all'):
  f=json.loads((root/'cp02_frozen.json').read_text());rows=load_tasks(test,testidx)
  atomic_csv(root/'cp03_test_geometry.csv',rows,list(rows[0]));summary=summarize(rows);atomic_csv(root/'cp04_test_summary.csv',summary,list(summary[0]));
  eff={r['method']:r for r in summary};atomic_json(root/'cp05_scope.json',dict(signature=signature,test_groups=int(len(np.unique(groups[masks[2]]))),test_geometries=len(testidx),frozen=f,limitations=['synthetic CSI observation error conditional on estimated channel','no formal outage guarantee','DeepMIMO grouped splitting needs spatially meaningful groups','3GPP-inspired generator is not a full TR 38.901 channel simulator']))
  print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
