#!/usr/bin/env python3
"""Exact K=4 subset/codebook oracle and low-cost greedy. Fixed CSI radius.
All evaluated beams are recomputed for each admitted subset (no full-K submatrix shortcut).
No claims beyond the finite ZF/RZF candidate family. H is estimated channel.
"""
import argparse,csv,hashlib,itertools,json,os,sys,time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

# Shared numerical tolerances. Every screening module must import these values
# instead of hard-coding its own: a certificate may prune only when the bound
# exceeds the budget by PRUNE_REL_MARGIN, which must be >= POWER_REL_TOL, the
# relative slack that solve() still accepts as FEASIBLE. Otherwise a candidate
# that solve() accepts can be pruned (false prune).
POWER_REL_TOL=1e-9
PRUNE_REL_MARGIN=1e-8
RHO_TOL=1e-10
if PRUNE_REL_MARGIN<POWER_REL_TOL:raise RuntimeError('PRUNE_REL_MARGIN must be >= POWER_REL_TOL')

def check_count(limit,total):
 """Validate --limit and return the number of geometries to process (>=1)."""
 if limit<0:raise ValueError('--limit must be >= 0')
 n=total if limit==0 else min(limit,total)
 if n<1:raise ValueError('No geometry selected')
 return n

def utf8_console():
 """Windows consoles default to cp1252/cp437; print UTF-8 and never crash on a symbol."""
 for s in (sys.stdout,sys.stderr):
  try:s.reconfigure(encoding='utf-8',errors='replace')
  except (AttributeError,ValueError):pass

def _replace(t,p):
 # os.replace can fail transiently on Windows when OneDrive/antivirus holds the file.
 for k in range(20):
  try:os.replace(t,p);return
  except PermissionError:
   if k==19:raise
   time.sleep(0.25)

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def jwrite(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp')
 with t.open('w',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False);f.flush();os.fsync(f.fileno())
 _replace(t,p)
def cwrite(p,rows,headers):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp')
 with t.open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=headers,extrasaction='ignore');w.writeheader();w.writerows(rows);f.flush();os.fsync(f.fileno())
 _replace(t,p)
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

def _result(status,rho=None,req=None,gap=None,residual=None):
 return {'status':status,'rho':rho,'p_req_w':req,'lp_gap':gap,'residual':residual}

def coefficients(H,users,alpha,cfg):
 """Beam generation and robust SINR coefficients of one candidate (S, alpha).

 Computed once per candidate and shared by safe screening and power allocation
 (pipeline: subset -> beam -> screening -> power allocation). Returns a dict with
 'status' None when F and u are defined, otherwise the terminal solver status.
 Arithmetic order is identical to the former monolithic solve().
 """
 h=H[:,users];M,S=h.shape
 norms=np.linalg.norm(h,axis=0);radius=cfg['q']*cfg['sigma']*norms/np.sqrt(M)
 W=get_beam(h,alpha)
 if W is None:return dict(status='BEAM_RANK_OR_NUMERICAL',norms=norms,radius=radius)
 g=np.abs(h.conj().T@W)
 a=np.maximum(np.diag(g)-radius,0)**2
 if np.any(a<=0):return dict(status='ZERO_ROBUST_DIRECT_GAIN',norms=norms,radius=radius,g=g,a=a)
 upper=(g+radius[:,None])**2;F=cfg['gamma']*upper/a[:,None];np.fill_diagonal(F,0)
 u=cfg['gamma']*cfg['noise']/a
 return dict(status=None,norms=norms,radius=radius,g=g,a=a,F=F,u=u)

def power_solve(c,cfg):
 """Full evaluation of p >= F p + u, 1^T p <= pmax for precomputed coefficients."""
 if c['status'] is not None:return _result(c['status'])
 F,u=c['F'],c['u'];S=len(u)
 rho=float(max(abs(np.linalg.eigvals(F))))
 if rho>=1-RHO_TOL:return _result('COUPLING_RHO_GE_ONE',rho)
 try:p=np.linalg.solve(np.eye(S)-F,u)
 except np.linalg.LinAlgError:return _result('SINGULAR_MATRIX',rho)
 if not np.isfinite(p).all() or min(p)<0:return _result('INVALID_POWER',rho)
 req=float(sum(p)); residual=float(min(p-F@p-u))
 if req>cfg['pmax']*(1+POWER_REL_TOL):return _result('POWER_BUDGET',rho,req,None,residual)
 # Independent LP audit. Scaling avoids HiGHS feasibility tolerance masking tiny physical units.
 scaler=max(float(np.max(u)),1e-20);res=linprog(np.ones(S),A_ub=F-np.eye(S),b_ub=-u/scaler,bounds=(0,None),method='highs')
 if not res.success:return _result('LP_FAILURE',rho,req,None,residual)
 lp=float(sum(res.x)*scaler); gap=abs(lp-req)/max(req,1e-30)
 if gap>1e-5 or residual< -1e-7*max(float(np.max(u)),1e-20):return _result('LP_MISMATCH',rho,req,gap,residual)
 return _result('FEASIBLE',rho,req,gap,residual)

def solve(H,users,alpha,cfg):
 return power_solve(coefficients(H,users,alpha,cfg),cfg)

TIE_REL_TOL=1e-9
def select_best(cands):
 """Deterministic lexicographic rule of the manuscript (Section III).

 1) maximum cardinality; 2) minimum total power, where powers within a relative
 TIE_REL_TOL of the minimum are treated as equal; 3) smaller regularization
 alpha (ZF before RZF); 4) lexicographically smallest subset label.
 Every algorithm (exhaustive, greedy, screened) must select through this function.
 """
 if not cands:return None
 cmax=max(c['cardinality'] for c in cands)
 top=[c for c in cands if c['cardinality']==cmax]
 pmin=min(c['p_req_w'] for c in top)
 tied=[c for c in top if c['p_req_w']<=pmin*(1+TIE_REL_TOL)]
 return min(tied,key=lambda c:(c['alpha'],c['subset']))

def exhaustive(H,alphas,cfg):
 rows=[]
 for s in range(1,5):
  for subset in itertools.combinations(range(4),s):
   for alpha in alphas:
    t=time.perf_counter();c=coefficients(H,list(subset),alpha,cfg);t1=time.perf_counter();r=power_solve(c,cfg);t2=time.perf_counter()
    rows.append(dict(subset=''.join(map(str,subset)),cardinality=s,alpha=alpha,beam='ZF' if alpha==0 else 'RZF',runtime_ms=(t2-t)*1000,beam_ms=(t1-t)*1000,power_solve_ms=(t2-t1)*1000,**r))
 return rows

def objective(r):return (-r['cardinality'],r['p_req_w'],r['alpha'],r['subset'])
def oracle(rows):
 return select_best([r for r in rows if r['status']=='FEASIBLE'])

def greedy(H,alphas,cfg,mode):
 # Two candidate-limited greedy baselines: user deletion and forward admission.
 calls=0
 def best(sub):
  nonlocal calls
  rs=[]
  for a in alphas:
   calls+=1;r=solve(H,list(sub),a,cfg)
   if r['status']=='FEASIBLE':rs.append(dict(subset=''.join(map(str,sub)),cardinality=len(sub),alpha=a,**r))
  return select_best(rs)
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
   if options:return select_best(options),calls
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
   v=select_best([z[0] for z in candidates]);_,selected,k=next(z for z in candidates if z[0] is v);remaining.remove(k);best_current=v
  return best_current,calls

def main():
 utf8_console()
 ap=argparse.ArgumentParser()
 ap.add_argument('--stage',choices=['preflight','scan','report','all'],required=True)
 ap.add_argument('--dataset',required=True);ap.add_argument('--run-id',required=True);ap.add_argument('--out-root',default='outputs')
 ap.add_argument('--q',type=float,default=2.960414);ap.add_argument('--sigma-rel',type=float,default=.04);ap.add_argument('--sinr-db',type=float,default=6.)
 ap.add_argument('--noise',type=float,default=2e-13);ap.add_argument('--pmax',type=float,default=1.)
 ap.add_argument('--alpha-list',default='0,0.001,0.01,0.05,0.1,0.3,1');ap.add_argument('--limit',type=int,default=0)
 a=ap.parse_args();H,groups,meta=load(a.dataset);N=check_count(a.limit,len(H))
 alphas=sorted(set(float(v) for v in a.alpha_list.split(',')))
 if not alphas or min(alphas)<0 or a.q<0 or a.sigma_rel<=0 or a.noise<=0 or a.pmax<=0:raise ValueError('Invalid parameters')
 cfg={'q':a.q,'sigma':a.sigma_rel,'gamma':10**(a.sinr_db/10),'noise':a.noise,'pmax':a.pmax}
 config={k:v for k,v in vars(a).items() if k not in ('stage','out_root','run_id')};config['sha_data']=digest(a.dataset);config['sha_code']=digest(__file__)
 signature=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest();root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
 manifest=root/'CP00_manifest.json'
 if manifest.exists():
  if json.loads(manifest.read_text(encoding='utf8'))['signature']!=signature:raise RuntimeError('Configuration changed. Use a new run-id')
 else:jwrite(manifest,{'signature':signature,'parameters':config,'N':N,'M':H.shape[1],'K':4,'groups':int(len(np.unique(groups[:N]))),'metadata':list(meta)})
 if a.stage=='preflight':print('PASS',N,'geometries,',len(np.unique(groups[:N])),'groups');return
 if a.stage in ('scan','all'):
  for i in range(N):
   file=root/'tasks'/f'{i:07d}.json'
   if file.exists():
    x=json.loads(file.read_text(encoding='utf8'));
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
   x=json.loads(path.read_text(encoding='utf8'));
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
