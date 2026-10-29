#!/usr/bin/env python3
"""Prespecified fixed CSI margin calibration; no test-time tuning.
Disclaimer: binomial UCB is valid only for independent calibration episodes under
an unchanged error distribution. Grouping and distribution shift invalidate it.
"""
import argparse, hashlib, json, os, csv, time
from pathlib import Path
import numpy as np
from scipy.stats import beta
from engine_original import rzf, power_lp, sha, atomic_json, atomic_csv

Q_GRID=(1.2,1.4,1.6,1.8,2.,2.2,2.401733)

def read(path,M,K):
    d=np.load(path,allow_pickle=False)
    if 'H' not in d or 'groups' not in d: raise ValueError('NPZ needs H and groups')
    H=d['H']; g=d['groups']
    if H.ndim!=3 or H.shape[1:]!=(M,K) or not np.iscomplexobj(H) or not np.isfinite(H).all(): raise ValueError('H must be finite complex (N,M,K)')
    if g.ndim!=1 or len(g)!=len(H):raise ValueError('Invalid groups')
    if len(set(g.tolist()))<12:raise ValueError('Need >=12 genuinely independent spatial groups')
    return H,g

def partition(g,seed):
    v=np.random.default_rng(seed).permutation(np.unique(g));n=len(v)
    div=(0,int(.4*n),int(.6*n),int(.8*n),n)
    return {label:np.flatnonzero(np.isin(g,v[div[i]:div[i+1]])).tolist() for i,label in enumerate(('development','calibration','test','unused'))}

def q_values(qgauss):return sorted(set([1.2,1.4,1.6,1.8,2.,2.2,float(qgauss)]))

def test_one(H,index,q,nsim,seed,cfg):
    h=H[index]; M,K=h.shape
    # CSI observed by BS before policy decision; no true channel in policy.
    rng=np.random.default_rng(np.random.SeedSequence([seed,index,19]))
    obs=(rng.standard_normal(h.shape)+1j*rng.standard_normal(h.shape))/np.sqrt(2*M)
    est=h+cfg['sigma_rel']*np.linalg.norm(h,axis=0)[None,:]*obs
    V=rzf(est)
    if V is None:return dict(feasible=0,power_w='',errors=nsim,trials=nsim,rho='')
    p,rho=power_lp(est,V,q,cfg)
    if p is None:return dict(feasible=0,power_w='',errors=nsim,trials=nsim,rho=float(rho))
    # Fresh, paired conditional-channel perturbations; not empirical measured-channel model.
    r=np.random.default_rng(np.random.SeedSequence([seed,index,31]))
    e=(r.standard_normal((nsim,M,K))+1j*r.standard_normal((nsim,M,K)))/np.sqrt(2*M)
    true=est[None,:,:]+cfg['sigma_rel']*np.linalg.norm(est,axis=0)[None,None,:]*e
    gains=np.abs(np.einsum('nmk,mj->nkj',true.conj(),V))**2
    wanted=p[None,:]*np.diagonal(gains,axis1=1,axis2=2)
    denom=cfg['noise']+np.einsum('nkj,j->nk',gains,p)-wanted
    bad=np.any(wanted/np.maximum(denom,1e-300)<cfg['sinr'],axis=1)
    return dict(feasible=1,power_w=float(np.sum(p)),errors=int(bad.sum()),trials=nsim,rho=float(rho))

def task(H,ids,qs,nsim,a,root,stage,source_name):
    cfg={'sigma_rel':a.sigma_rel,'sinr':10**(a.sinr_db/10),'noise':a.noise,'pmax':a.pmax}
    out=[];folder=root/'tasks'/stage;folder.mkdir(parents=True,exist_ok=True)
    for i in ids:
        name=folder/f'{source_name}_{int(i):08d}.json'
        if name.exists():
            j=json.loads(name.read_text()); assert j['source']==source_name and j['qs']==qs and j['nsim']==nsim
            rows=j['rows']
        else:
            rows=[]
            for q in qs:
                r=test_one(H,int(i),q,nsim,a.seed,cfg)
                rows.append(dict(index=int(i),q=q,**r))
            atomic_json(name,dict(source=source_name,qs=qs,nsim=nsim,rows=rows))
        out+=rows
    return out

def upper(x,n,alpha):
    return 1. if n<=0 else (1. if x>=n else float(beta.ppf(1-alpha,x+1,n-x)))

def aggregate(rows,alpha,episode_level=True):
    qs=sorted({r['q'] for r in rows});out=[]
    for q in qs:
        v=[r for r in rows if r['q']==q];fail=sum((not r['feasible']) or (r['errors']>0) for r in v)
        # Conservative independent geometry-episode indicator: any outage among nsim samples.
        n=len(v); eligible=[float(r['power_w']) for r in v if r['feasible']]
        out.append(dict(q=q,n_geometries=n,n_feasible=len(eligible),failed_geometry_episodes=fail,episode_failure=fail/n,episode_ucb=upper(fail,n,alpha),mean_feasible_power_w=float(np.mean(eligible)) if eligible else '',mc_outage_conditional=float(sum(r['errors'] for r in v if r['feasible'])/max(sum(r['trials'] for r in v if r['feasible']),1))))
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['preflight','develop','calibrate','freeze','test','transfer','report','all'],required=True)
    p.add_argument('--dataset',required=True);p.add_argument('--external-dataset',default='');p.add_argument('--run-id',required=True);p.add_argument('--output-root',default='outputs');p.add_argument('--M',type=int,default=16);p.add_argument('--K',type=int,default=4)
    p.add_argument('--seed',type=int,default=20261023);p.add_argument('--sigma-rel',type=float,default=.04);p.add_argument('--sinr-db',type=float,default=6.);p.add_argument('--noise',type=float,default=1e-9);p.add_argument('--pmax',type=float,default=1.)
    p.add_argument('--epsilon',type=float,default=.05);p.add_argument('--alpha',type=float,default=.05);p.add_argument('--mc',type=int,default=30);p.add_argument('--limit',type=int,default=0)
    a=p.parse_args()
    if not(0<a.epsilon<1 and 0<a.alpha<1 and a.mc>0 and a.noise>0 and a.pmax>0 and a.sigma_rel>0):p.error('Bad settings')
    H,g=read(a.dataset,a.M,a.K);parts=partition(g,a.seed)
    if a.limit:parts={k:v[:a.limit] for k,v in parts.items()}
    qs=q_values(np.sqrt(-2*np.log(a.epsilon/a.K)))
    root=Path(a.output_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    settings={k:v for k,v in vars(a).items() if k not in ('stage','run_id','output_root','external_dataset')}
    payload=dict(code_sha=sha(__file__),engine_sha=sha(Path(__file__).parent/'engine_original.py'),dataset_sha=sha(a.dataset),settings=settings,parts=parts)
    signature=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();man=root/'CP00_manifest.json'
    if man.exists() and json.loads(man.read_text())['signature']!=signature:raise RuntimeError('Changed settings/source/splits: choose a new run-id')
    if not man.exists():atomic_json(man,dict(signature=signature,**payload))
    if a.stage=='preflight':print('PASS', {k:len(v) for k,v in parts.items()},'q',qs);return
    if a.stage in ('develop','all'):
        rows=task(H,parts['development'],qs,a.mc,a,root,'dev','deepmimo')
        atomic_csv(root/'CP01_development.csv',rows,list(rows[0]))
        metrics=aggregate(rows,a.alpha)
        atomic_csv(root/'CP02_development_summary.csv',metrics,list(metrics[0]))
        # minimize conditional power with heuristic dev episode failure penalty;
        # this ranking is NOT an inferential guarantee. Calibration screens one choice.
        valid=[r for r in metrics if r['episode_failure']<=a.epsilon and r['mean_feasible_power_w']!='']
        selected=min(valid,key=lambda z:z['mean_feasible_power_w'])['q'] if valid else qs[-1]
        atomic_json(root/'CP03_development_choice.json',dict(q=float(selected),reason='development point estimate only; no reliability certification',candidate_count=len(qs)))
    if a.stage in ('calibrate','all'):
        chosen=json.loads((root/'CP03_development_choice.json').read_text())['q']
        # One preselected geometry and one independent error realization per group.
        cal_ids=[]
        for group in np.unique(g[parts['calibration']]):
            cal_ids.append(next(i for i in parts['calibration'] if g[i]==group))
        rows=task(H,cal_ids,[chosen],1,a,root,'cal','deepmimo')
        atomic_csv(root/'CP04_calibration.csv',rows,list(rows[0]));m=aggregate(rows,a.alpha)[0]
        eligible=(m['episode_ucb']<=a.epsilon)
        atomic_json(root/'CP05_calibration_decision.json',dict(**m,eligible=eligible,interpretation='UCB applies to independent episodes, not deployment or shifted-channel guarantees'))
    if a.stage in ('freeze','all'):
        m=json.loads((root/'CP05_calibration_decision.json').read_text())
        atomic_json(root/'CP06_frozen.json',dict(q=float(m['q']),certified_under_iid_episode_assumption=bool(m['eligible']),state='CALIBRATION_PASS' if m['eligible'] else 'NO_CERTIFIED_MARGIN',epsilon=a.epsilon,alpha=a.alpha))
    if a.stage in ('test','all'):
        frozen=json.loads((root/'CP06_frozen.json').read_text());selected=frozen['q']
        # Report comparisons for all prespecified q, no test-informed policy update.
        rows=task(H,parts['test'],qs,a.mc,a,root,'test','deepmimo')
        atomic_csv(root/'CP07_test_geometry.csv',rows,list(rows[0]));m=aggregate(rows,a.alpha)
        for r in m:r['selected_before_test']=int(abs(r['q']-selected)<1e-10)
        atomic_csv(root/'CP08_test_summary.csv',m,list(m[0]))
    if a.stage in ('transfer','all') and a.external_dataset:
        extH,extg=read(a.external_dataset,a.M,a.K)
        frozen=json.loads((root/'CP06_frozen.json').read_text())
        external_sig=sha(a.external_dataset); tag=external_sig[:12]
        # The entire external source is held out; group labels must be audited by researcher.
        rows=task(extH,list(range(len(extH))) if not a.limit else list(range(min(a.limit,len(extH)))),sorted(set([frozen['q'],qs[-1]])),a.mc,a,root,'external',tag)
        atomic_csv(root/'CP09_external_geometry.csv',rows,list(rows[0]))
        m=aggregate(rows,a.alpha)
        atomic_csv(root/'CP10_external_summary.csv',m,list(m[0]))
        atomic_json(root/'CP10_external_manifest.json',dict(dataset_sha=external_sig,source='user-supplied independent 3GPP matrix; full compliance not programmatically verified'))
    if a.stage in ('report','all'):
        frozen=json.loads((root/'CP06_frozen.json').read_text())
        testfile=root/'CP08_test_summary.csv'
        if not testfile.exists():raise RuntimeError('Run test before report')
        test=list(csv.DictReader(open(testfile,encoding='utf-8')))
        atomic_json(root/'CP11_conclusion.json',dict(decision='ELIGIBLE_FOR_COMPARISON' if frozen['certified_under_iid_episode_assumption'] else 'STOP_NO_CALIBRATED_MARGIN',note='No claims of out-of-distribution 5% reliability or novelty from fixed margin alone',test_comparison=test,external_available=(root/'CP10_external_summary.csv').exists()))
        records=[]
        for f in sorted(root.glob('CP*')):
            if f.name=='CP12_sha256.csv' or not f.is_file():continue
            records.append(dict(file=f.name,sha256=sha(f)))
        atomic_csv(root/'CP12_sha256.csv',records,['file','sha256'])
        print(json.dumps(json.loads((root/'CP11_conclusion.json').read_text())['decision']))
if __name__=='__main__':main()
