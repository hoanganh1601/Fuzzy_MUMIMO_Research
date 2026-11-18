#!/usr/bin/env python3
"""Exact K=4 subset/codebook oracle and low-cost greedy. Fixed CSI radius.
All evaluated beams are recomputed for each admitted subset (no full-K submatrix shortcut).
No claims beyond the finite ZF/RZF candidate family. H is estimated channel.
"""
import argparse,csv,hashlib,itertools,json,os,time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def jwrite(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp')
 with t.open('w',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def cwrite(p,rows,headers):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp')
 with t.open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=headers,extrasaction='ignore');w.writeheader();w.writerows(rows);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def load(p):
 with np.load(p,allow_pickle=False) as d:
  H=d['H'];groups=d['groups'];metadata={k:d[k] for k in ('scenario','xyz') if k in d.files}
 if H.ndim!=3 or H.shape[0]!=len(groups) or H.shape[2]!=4 or H.shape[1]<4:raise ValueError('Require H complex shape (N,M,4), M>=4 and groups')
 if not np.iscomplexobj(H) or not np.isfinite(H).all():raise ValueError('H must be finite complex')
 if len(np.unique(groups))<3:raise ValueError('Require at least three nonempty groups')
 return H,groups,metadata

def get_beam(H,alpha):
 M,S=H.shape;gram=H.conj().T@H; scale=max(float(np.trace(gram).real/S),1e-30)
 try:
  if alpha==0:
   if np.linalg.matrix_rank(H)<S:return None
   W=H@np.linalg.solve(gram,np.eye(S))
  else:W=H@np.linalg.solve(gram+alpha*scale*np.eye(S),np.eye(S))
 except np.linalg.LinAlgError:return None
 norms=np.linalg.norm(W,axis=0)
 if np.min(norms)<=1e-30:return None
 return W/norms

def solve(H,users,alpha,cfg):
 h=H[:,users]; W=get_beam(h,alpha)
 if W is None:return {'status':'BEAM_RANK_OR_NUMERICAL','rho':None,'p_req_w':None,'lp_gap':None,'residual':None}
 M,S=h.shape;g=np.abs(h.conj().T@W);radius=cfg['q']*cfg['sigma']*np.linalg.norm(h,axis=0)/np.sqrt(M)
 a=np.maximum(np.diag(g)-radius,0)**2
 if np.any(a<=0):return {'status':'ZERO_ROBUST_DIRECT_GAIN','rho':None,'p_req_w':None,'lp_gap':None,'residual':None}
 upper=(g+radius[:,None])**2;F=cfg['gamma']*upper/a[:,None];np.fill_diagonal(F,0)
 u=cfg['gamma']*cfg['noise']/a
 rho=float(max(abs(np.linalg.eigvals(F))))
 if rho>=1-1e-10:return {'status':'COUPLING_RHO_GE_ONE','rho':rho,'p_req_w':None,'lp_gap':None,'residual':None}
 try:p=np.linalg.solve(np.eye(S)-F,u)
 except np.linalg.LinAlgError:return {'status':'SINGULAR_MATRIX','rho':rho,'p_req_w':None,'lp_gap':None,'residual':None}
 if not np.isfinite(p).all() or min(p)<0:return {'status':'INVALID_POWER','rho':rho,'p_req_w':None,'lp_gap':None,'residual':None}
 req=float(sum(p)); residual=float(min(p-F@p-u))
 if req>cfg['pmax']*(1+1e-9):return {'status':'POWER_BUDGET','rho':rho,'p_req_w':req,'lp_gap':None,'residual':residual}
 # Independent LP audit. Scaling avoids HiGHS feasibility tolerance masking tiny physical units.
 scaler=max(float(np.max(u)),1e-20);res=linprog(np.ones(S),A_ub=F-np.eye(S),b_ub=-u/scaler,bounds=(0,None),method='highs')
 if not res.success:return {'status':'LP_FAILURE','rho':rho,'p_req_w':req,'lp_gap':None,'residual':residual}
 lp=float(sum(res.x)*scaler); gap=abs(lp-req)/max(req,1e-30)
 if gap>1e-5 or residual< -1e-7*max(float(np.max(u)),1e-20):return {'status':'LP_MISMATCH','rho':rho,'p_req_w':req,'lp_gap':gap,'residual':residual}
 return {'status':'FEASIBLE','rho':rho,'p_req_w':req,'lp_gap':gap,'residual':residual}

def exhaustive(H,alphas,cfg):
 rows=[]
 for s in range(1,5):
  for subset in itertools.combinations(range(4),s):
   for alpha in alphas:
    t=time.perf_counter();r=solve(H,list(subset),alpha,cfg)
    rows.append(dict(subset=''.join(map(str,subset)),cardinality=s,alpha=alpha,beam='ZF' if alpha==0 else 'RZF',runtime_ms=(time.perf_counter()-t)*1000,**r))
 return rows

def objective(r):return (-r['cardinality'],r['p_req_w'],r['alpha'],r['subset'])
def oracle(rows):
 feas=[r for r in rows if r['status']=='FEASIBLE'];return min(feas,key=objective) if feas else None

def greedy(H,alphas,cfg,mode):
 # Two candidate-limited greedy baselines: user deletion and forward admission.
 calls=0
 def best(sub):
  nonlocal calls
  rs=[]
  for a in alphas:
   calls+=1;r=solve(H,list(sub),a,cfg)
   if r['status']=='FEASIBLE':rs.append(dict(subset=''.join(map(str,sub)),cardinality=len(sub),alpha=a,**r))
  return min(rs,key=objective) if rs else None
 if mode=='backward':
  current=tuple(range(4))
  while current:
   v=best(current)
   if v is not None:return v,calls
   options=[]
   for sub in itertools.combinations(current,len(current)-1):
    if not sub:continue
    v=best(sub)
    if v is not None:options.append(v)
   if options:return min(options,key=objective),calls
   # deterministic deletion heuristic based on poorest nominal channel strength
   worst=min(current,key=lambda k:(np.linalg.norm(H[:,k]),k))
   current=tuple(k for k in current if k!=worst)
  return None,calls
 else:
  selected=tuple();best_current=None;remaining=set(range(4))
  while remaining:
   candidates=[]
   for k in sorted(remaining):
    sub=tuple(sorted(selected+(k,)));v=best(sub)
    if v is not None:candidates.append((v,sub,k))
   if not candidates:break
   v,selected,k=min(candidates,key=lambda z:objective(z[0]));remaining.remove(k);best_current=v
  return best_current,calls

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--stage',choices=['preflight','scan','report','all'],required=True)
 ap.add_argument('--dataset',required=True);ap.add_argument('--run-id',required=True);ap.add_argument('--out-root',default='outputs')
 ap.add_argument('--q',type=float,default=2.960414);ap.add_argument('--sigma-rel',type=float,default=.04);ap.add_argument('--sinr-db',type=float,default=6.)
 ap.add_argument('--noise',type=float,default=2e-13);ap.add_argument('--pmax',type=float,default=1.)
 ap.add_argument('--alpha-list',default='0,0.001,0.01,0.05,0.1,0.3,1');ap.add_argument('--limit',type=int,default=0)
 a=ap.parse_args();H,groups,meta=load(a.dataset);N=len(H) if not a.limit else min(a.limit,len(H))
 alphas=sorted(set(float(v) for v in a.alpha_list.split(',')))
 if not alphas or min(alphas)<0 or a.q<0 or a.sigma_rel<=0 or a.noise<=0 or a.pmax<=0:raise ValueError('Invalid parameters')
 cfg={'q':a.q,'sigma':a.sigma_rel,'gamma':10**(a.sinr_db/10),'noise':a.noise,'pmax':a.pmax}
 config={k:v for k,v in vars(a).items() if k not in ('stage','out_root','run_id')};config['sha_data']=digest(a.dataset);config['sha_code']=digest(__file__)
 signature=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest();root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
 manifest=root/'CP00_manifest.json'
 if manifest.exists():
  if json.loads(manifest.read_text())['signature']!=signature:raise RuntimeError('Configuration changed. Use a new run-id')
 else:jwrite(manifest,{'signature':signature,'parameters':config,'N':N,'M':H.shape[1],'K':4,'groups':int(len(np.unique(groups[:N]))),'metadata':list(meta)})
 if a.stage=='preflight':print('PASS',N,'geometries,',len(np.unique(groups[:N])),'groups');return
 if a.stage in ('scan','all'):
  for i in range(N):
   file=root/'tasks'/f'{i:07d}.json'
   if file.exists():
    x=json.loads(file.read_text());
    if x.get('signature')==signature and x.get('complete'):continue
    raise RuntimeError('Invalid task '+str(file))
   tic=time.perf_counter();rr=exhaustive(H[i],alphas,cfg);o=oracle(rr);oracletime=(time.perf_counter()-tic)*1000
   gs=[]
   for mode in ('forward','backward'):
    st=time.perf_counter();choice,calls=greedy(H[i],alphas,cfg,mode)
    gs.append({'method':mode,'choice':choice,'calls':calls,'runtime_ms':(time.perf_counter()-st)*1000})
   jwrite(file,{'signature':signature,'complete':True,'geometry':i,'group':str(groups[i]),'rows':rr,'oracle':o,'oracle_runtime_ms':oracletime,'greedy':gs})
 if a.stage in ('report','all'):
  tasks=[]
  for i in range(N):
   path=root/'tasks'/f'{i:07d}.json'
   if not path.exists():raise RuntimeError('Missing task '+str(path))
   x=json.loads(path.read_text());
   if x['signature']!=signature or not x['complete']:raise RuntimeError('Invalid checkpoint')
   tasks.append(x)
  allrows=[];decisions=[];comparisons=[]
  for task in tasks:
   i=task['geometry'];group=task['group'];o=task['oracle']
   for r in task['rows']:allrows.append(dict(geometry=i,group=group,**r))
   decisions.append({'geometry':i,'group':group,'method':'exhaustive','cardinality':o['cardinality'] if o else 0,'subset':o['subset'] if o else '', 'alpha':o['alpha'] if o else '', 'power_w':o['p_req_w'] if o else '', 'calls':15*len(alphas),'runtime_ms':task['oracle_runtime_ms']})
   for g in task['greedy']:
    v=g['choice'];card=v['cardinality'] if v else 0
    decisions.append({'geometry':i,'group':group,'method':g['method'],'cardinality':card,'subset':v['subset'] if v else '','alpha':v['alpha'] if v else '','power_w':v['p_req_w'] if v else '','calls':g['calls'],'runtime_ms':g['runtime_ms']})
    comparisons.append({'geometry':i,'group':group,'method':g['method'],'oracle_cardinality':o['cardinality'] if o else 0,'greedy_cardinality':card,'cardinality_gap':(o['cardinality'] if o else 0)-card,'same_cardinality':int(o is not None and card==o['cardinality']),'power_ratio_if_same_cardinality':v['p_req_w']/o['p_req_w'] if o and v and card==o['cardinality'] and o['p_req_w']>0 else '', 'oracle_calls':15*len(alphas),'greedy_calls':g['calls']})
  cwrite(root/'CP01_all_subset_beam.csv',allrows,list(allrows[0]))
  cwrite(root/'CP02_oracle_greedy_decisions.csv',decisions,list(decisions[0]))
  cwrite(root/'CP03_paired_comparison.csv',comparisons,list(comparisons[0]))
  stats=[]
  for method in ('exhaustive','forward','backward'):
   r=[x for x in decisions if x['method']==method];com=[x for x in comparisons if x['method']==method]
   stats.append({'method':method,'n_geometries':N,'mean_admitted_users':float(np.mean([x['cardinality'] for x in r])),'full_service_fraction':float(np.mean([x['cardinality']==4 for x in r])),'at_least_one_fraction':float(np.mean([x['cardinality']>=1 for x in r])),'mean_calls':float(np.mean([x['calls'] for x in r])),'mean_runtime_ms':float(np.mean([x['runtime_ms'] for x in r])),'oracle_cardinality_match_fraction':float(np.mean([x['same_cardinality'] for x in com])) if com else ''})
  cwrite(root/'CP04_summary.csv',stats,list(stats[0]))
  jwrite(root/'CP05_scope.json',{'status':'EXPLORATORY_EVALUATION','fixed_q':a.q,'objective':'lexicographic max user count, then min transmit power for that count','oracle':'exact across 15 nonempty subsets x enumerated ZF/RZF codebook; not globally optimal beamforming','data_leakage':'Do not tune policies on prior observed geometries and claim independent test','caveats':['Admitted subset recomputes beam and robust coefficients','Outage not certified by finite uncertainty bound','Dropped users are not served, and fairness/throughput not yet evaluated','No statistical independence guaranteed by group names alone']})
  entries=[{'file':p.name,'sha256':digest(p)} for p in sorted(root.glob('CP0*')) if p.name!='CP06_sha256.csv'];cwrite(root/'CP06_sha256.csv',entries,['file','sha256'])
  print('REPORT',root,'records',len(allrows));print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
