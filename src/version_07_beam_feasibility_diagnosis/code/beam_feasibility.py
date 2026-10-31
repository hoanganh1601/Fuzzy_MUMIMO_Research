#!/usr/bin/env python3
"""Fixed-margin robust SINR feasibility diagnosis; no margin selection.
NPZ H: (N,M,K) complex estimated channels; groups: (N,) scenario/spatial group IDs.
"""
import argparse,csv,hashlib,json,os,time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def write_json(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp')
 with t.open('w',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def write_csv(p,rows,cols):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp')
 with t.open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def load(p):
 with np.load(p,allow_pickle=False) as d:
  if not {'H','groups'}<=set(d.files):raise ValueError('NPZ requires H and groups')
  H=d['H'];g=d['groups'];meta={k:d[k] for k in ('xyz','scenario') if k in d.files}
 if H.ndim!=3 or H.shape[0]!=len(g) or not np.iscomplexobj(H) or not np.isfinite(H).all():raise ValueError('Invalid H or groups')
 if H.shape[1]<H.shape[2]:raise ValueError('ZF requires M >= K; supply M >= K')
 return H,g,meta
def beam(H,alpha):
 M,K=H.shape; gram=H.conj().T@H; scale=max(float(np.trace(gram).real/K),1e-30)
 try:
  if alpha==0:
   if np.linalg.matrix_rank(H)<K:return None
   V=H@np.linalg.solve(gram,np.eye(K))
  else: V=H@np.linalg.solve(gram+alpha*scale*np.eye(K),np.eye(K))
 except np.linalg.LinAlgError:return None
 n=np.linalg.norm(V,axis=0)
 if np.min(n)<=1e-30:return None
 return V/n
def coefficients(H,V,q,sigma_rel,gamma,noise):
 M,K=H.shape; gain=np.abs(H.conj().T@V)
 rad=q*sigma_rel*np.linalg.norm(H,axis=0)/np.sqrt(M)
 a=np.maximum(np.diag(gain)-rad,0)**2
 if np.min(a)<=0:return None
 upper=(gain+rad[:,None])**2
 F=gamma*upper/a[:,None];np.fill_diagonal(F,0)
 u=gamma*noise/a
 return F,u

def solve(H,alpha,base,scale):
 t=time.perf_counter();V=beam(H,alpha)
 row={'beam':'ZF' if alpha==0 else f'RZF_{alpha:g}','alpha':alpha,'budget_factor':scale,'feasible':0,'rho':'','p_unbounded_w':'','p_constrained_w':'','pmax_w':base['pmax']*scale,'status':'','min_residual':'','runtime_ms':''}
 if V is None:row['status']='BEAM_RANK_OR_NUMERICAL';row['runtime_ms']=1000*(time.perf_counter()-t);return row
 c=coefficients(H,V,base['q'],base['sigma'],base['gamma'],base['noise'])
 if c is None:row['status']='ZERO_ROBUST_DIRECT_GAIN';row['runtime_ms']=1000*(time.perf_counter()-t);return row
 F,u=c;rho=float(np.max(np.abs(np.linalg.eigvals(F))));row['rho']=rho
 if rho>=1-1e-10:row['status']='COUPLING_RHO_GE_ONE';row['runtime_ms']=1000*(time.perf_counter()-t);return row
 # independent LP and analytic candidate enable diagnosing numerical failures.
 try:p=np.linalg.solve(np.eye(len(u))-F,u)
 except np.linalg.LinAlgError:row['status']='SINGULAR_SYSTEM';row['runtime_ms']=1000*(time.perf_counter()-t);return row
 if not np.isfinite(p).all() or np.min(p)<-1e-9:row['status']='INVALID_ANALYTIC_POWER';row['runtime_ms']=1000*(time.perf_counter()-t);return row
 pu=float(np.maximum(p,0).sum());row['p_unbounded_w']=pu
 if pu>base['pmax']*scale*(1+1e-9):row['status']='POWER_BUDGET';row['runtime_ms']=1000*(time.perf_counter()-t);return row
 res=linprog(np.ones(len(u)),A_ub=F-np.eye(len(u)),b_ub=-u,bounds=(0,None),method='highs')
 if not res.success:row['status']='LP_SOLVER_FAILURE_'+str(res.status);row['runtime_ms']=1000*(time.perf_counter()-t);return row
 residual=float(np.min(res.x-F@res.x-u));row['min_residual']=residual
 if residual < -1e-7*max(float(np.max(u)),1e-15):row['status']='LP_RESIDUAL_FAIL'
 elif abs(float(np.sum(res.x))-pu)>1e-5*max(pu,1e-15):row['status']='ANALYTIC_LP_MISMATCH'
 else:row['status']='FEASIBLE';row['feasible']=1;row['p_constrained_w']=float(np.sum(res.x))
 row['runtime_ms']=1000*(time.perf_counter()-t);return row

def main():
 a=argparse.ArgumentParser();a.add_argument('--stage',required=True,choices=('preflight','scan','report','all'));a.add_argument('--dataset',required=True);a.add_argument('--run-id',required=True);a.add_argument('--output',default='outputs');a.add_argument('--q',type=float,default=2.960414);a.add_argument('--sigma-rel',type=float,default=.04);a.add_argument('--sinr-db',type=float,default=6.);a.add_argument('--noise',type=float,default=2e-13);a.add_argument('--pmax',type=float,default=1.);a.add_argument('--alpha-list',default='0,0.001,0.01,0.05,0.1,0.3,1');a.add_argument('--budget-list',default='0.3,0.6,1,2,5');a.add_argument('--max-geometries',type=int,default=0)
 x=a.parse_args();H,groups,meta=load(x.dataset);alphas=sorted(set(float(v) for v in x.alpha_list.split(',')));budgets=sorted(set(float(v) for v in x.budget_list.split(',')))
 if min(alphas)<0 or min(budgets)<=0 or x.q<0 or x.sigma_rel<=0 or x.noise<=0 or x.pmax<=0:raise ValueError('Invalid parameter')
 N=len(H) if not x.max_geometries else min(len(H),x.max_geometries)
 root=Path(x.output)/x.run_id;root.mkdir(parents=True,exist_ok=True)
 config={k:v for k,v in vars(x).items() if k not in ('stage','output','run_id')};config['dataset_sha256']=sha(x.dataset);config['code_sha256']=sha(__file__)
 signature=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest();cp=root/'CP00_manifest.json'
 if cp.exists():
  if json.loads(cp.read_text())['signature']!=signature:raise RuntimeError('Signature mismatch. Use new run-id.')
 else:write_json(cp,{'signature':signature,'config':config,'N':N,'M':H.shape[1],'K':H.shape[2],'unique_groups':len(np.unique(groups[:N])),'data_metadata':list(meta)})
 if x.stage=='preflight':print('PREFLIGHT PASS',N,'geometries',len(np.unique(groups[:N])),'groups');return
 base={'q':x.q,'sigma':x.sigma_rel,'gamma':10**(x.sinr_db/10),'noise':x.noise,'pmax':x.pmax};folder=root/'tasks'
 if x.stage in ('scan','all'):
  for i in range(N):
   target=folder/f'{i:07d}.json'
   if target.exists():
    z=json.loads(target.read_text())
    if z.get('signature')==signature and z.get('complete'):continue
    raise RuntimeError('Checkpoint invalid '+str(target))
   rows=[]
   for alpha in alphas:
    for factor in budgets:
     r=solve(H[i],alpha,base,factor);r.update(geometry=i,group=str(groups[i]));rows.append(r)
   write_json(target,{'signature':signature,'complete':True,'rows':rows})
 if x.stage in ('report','all'):
  rows=[]
  for i in range(N):
   target=folder/f'{i:07d}.json'
   if not target.exists():raise RuntimeError('Missing task '+str(target))
   z=json.loads(target.read_text())
   if z.get('signature')!=signature or not z.get('complete'):raise RuntimeError('Invalid task '+str(target))
   rows.extend(z['rows'])
  write_csv(root/'CP01_geometry_beam_budget.csv',rows,list(rows[0]))
  summ=[]
  for alpha in alphas:
   for factor in budgets:
    r=[v for v in rows if v['alpha']==alpha and v['budget_factor']==factor];ok=[v for v in r if v['feasible']]
    d={'alpha':alpha,'beam':r[0]['beam'],'budget_factor':factor,'n':len(r),'feasible':len(ok),'feasible_fraction':len(ok)/len(r),'mean_feasible_power_w':np.mean([z['p_constrained_w'] for z in ok]) if ok else '', 'mean_runtime_ms':np.mean([z['runtime_ms'] for z in r])}
    for status in ('COUPLING_RHO_GE_ONE','ZERO_ROBUST_DIRECT_GAIN','POWER_BUDGET','FEASIBLE'):
     d['n_'+status.lower()]=sum(v['status']==status for v in r)
    d['n_other']=len(r)-sum(d['n_'+status.lower()] for status in ('COUPLING_RHO_GE_ONE','ZERO_ROBUST_DIRECT_GAIN','POWER_BUDGET','FEASIBLE'))
    summ.append(d)
  write_csv(root/'CP02_beam_budget_summary.csv',summ,list(summ[0]))
  # Same geometry/beam comparison only; no comparison of separately selected feasible subsets.
  paired=[]
  for factor in budgets:
   for i in range(N):
    r=[z for z in rows if z['geometry']==i and z['budget_factor']==factor];zf=next((z for z in r if z['alpha']==0),None)
    if zf is None:continue
    for z in r:
     if z['alpha']==0:continue
     paired.append({'geometry':i,'group':str(groups[i]),'budget_factor':factor,'alpha':z['alpha'],'both_feasible':int(bool(z['feasible'] and zf['feasible'])),'zf_feasible':zf['feasible'],'rzf_feasible':z['feasible'],'power_ratio_rzf_zf':z['p_constrained_w']/zf['p_constrained_w'] if z['feasible'] and zf['feasible'] and zf['p_constrained_w']>0 else ''})
  write_csv(root/'CP03_paired_ZF_RZF.csv',paired,list(paired[0]) if paired else ['geometry','group','budget_factor','alpha','both_feasible','zf_feasible','rzf_feasible','power_ratio_rzf_zf'])
  diag=[]
  for i in range(N):
   rs=[z for z in rows if z['geometry']==i and z['budget_factor']==1];best=min((z for z in rs if z['feasible']),key=lambda z:z['p_constrained_w'],default=None)
   diag.append({'geometry':i,'group':str(groups[i]),'n_feasible_beams':sum(z['feasible'] for z in rs),'min_rho':min((z['rho'] for z in rs if z['rho']!=''),default=''),'best_alpha':best['alpha'] if best else '', 'best_power_w':best['p_constrained_w'] if best else '', 'all_beams_fail':int(best is None)})
  write_csv(root/'CP04_geometry_diagnosis.csv',diag,list(diag[0]))
  write_json(root/'CP05_scope_and_decision.json',{'status':'DIAGNOSTIC_ONLY','n_geometries':N,'groups':len(np.unique(groups[:N])),'q_fixed':x.q,'note':'No adaptive margin or post-test beam selection claim. ZF and RZF are candidate fixed beams. Full channel data and independent validation required. No claim of globally optimal beamforming.', 'next_gate':'If substantial coupling failures persist for all beams, examine scheduling or multiuser grouping rather than CSI margin.'})
  f=[]
  for p in sorted(root.glob('CP0*')):
   if p.name!='CP06_sha256.csv':f.append({'file':p.name,'sha256':sha(p)})
  write_csv(root/'CP06_sha256.csv',f,['file','sha256'])
  print('REPORT PASS',root,'rows',len(rows))
if __name__=='__main__':main()
