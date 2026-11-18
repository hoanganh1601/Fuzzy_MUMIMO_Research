#!/usr/bin/env python3
"""Ablation + numerical certificate audit for K=4 finite-beam SINR pruning.
Never reads oracle decision inside the screening decision. Exhaustive is solely an auditor.
"""
import argparse, csv, hashlib, itertools, json, math, time
from pathlib import Path
import numpy as np
from reference_model import load,get_beam,solve,exhaustive,oracle,digest,jwrite,cwrite

RULES=('NORM_NOISE_LOWER_BOUND','ZERO_ROBUST_GAIN','NOISE_LOWER_BOUND','NEUMANN_LOWER_BOUND','TWO_CYCLE_COUPLING')

def screening(h,sub,alpha,cfg,enabled):
    """Sufficient tests only. Rounding guard is conservative: never prune at equality."""
    Hs=h[:,list(sub)]; M=Hs.shape[0]; S=len(sub)
    norms=np.linalg.norm(Hs,axis=0)
    r=cfg['q']*cfg['sigma']*norms/np.sqrt(M)
    # Optimistic signal gain bound: |h^H w| <= ||h||; actual robust gain <= (||h||-r)_+^2.
    optimistic=np.maximum(norms-r,0)**2
    if 'NORM_NOISE_LOWER_BOUND' in enabled:
        if np.any(optimistic<=0):
            return True,'NORM_NOISE_LOWER_BOUND',float('inf'),0.0
        bound=float(np.sum(cfg['gamma']*cfg['noise']/optimistic))
        if bound>cfg['pmax']*(1+1e-8):return True,'NORM_NOISE_LOWER_BOUND',bound, bound/cfg['pmax']-1
    W=get_beam(Hs,alpha)
    if W is None:return False,'SURVIVOR',float('nan'),float('nan') # independent solver will determine status
    g=np.abs(Hs.conj().T@W)
    a=np.maximum(np.diag(g)-r,0)**2
    if np.any(a<=0):
        if 'ZERO_ROBUST_GAIN' in enabled:return True,'ZERO_ROBUST_GAIN',float('inf'),0.0
        return False,'SURVIVOR',float('nan'),float('nan')
    u=cfg['gamma']*cfg['noise']/a
    if 'NOISE_LOWER_BOUND' in enabled:
        bound=float(np.sum(u))
        if bound>cfg['pmax']*(1+1e-8):return True,'NOISE_LOWER_BOUND',bound,bound/cfg['pmax']-1
    F=cfg['gamma']*(g+r[:,None])**2/a[:,None];np.fill_diagonal(F,0.)
    if 'NEUMANN_LOWER_BOUND' in enabled:
        term=u.copy();total=u.copy()
        for order in range(1,5):
            term=F@term;total=total+term
            bound=float(np.sum(total))
            if bound>cfg['pmax']*(1+1e-8):return True,'NEUMANN_LOWER_BOUND',bound,bound/cfg['pmax']-1
    if 'TWO_CYCLE_COUPLING' in enabled:
        for i in range(S):
            for j in range(i+1,S):
                cycle=float(F[i,j]*F[j,i])
                if cycle>1+1e-8:return True,'TWO_CYCLE_COUPLING',cycle,cycle-1
    return False,'SURVIVOR',float('nan'),float('nan')

def select(h,alphas,cfg,enabled):
    calls=0; checks=0; pruned=0; hist={r:0 for r in RULES}; chosen=None
    for s in range(4,0,-1):
        winners=[]
        for sub in itertools.combinations(range(4),s):
            for alpha in alphas:
                checks+=1
                skip,reason,_,_=screening(h,sub,alpha,cfg,enabled)
                if skip:pruned+=1;hist[reason]+=1;continue
                calls+=1
                r=solve(h,list(sub),alpha,cfg)
                if r['status']=='FEASIBLE':winners.append(dict(subset=''.join(map(str,sub)),cardinality=s,alpha=alpha,**r))
        if winners:
            chosen=min(winners,key=lambda x:(-x['cardinality'],x['p_req_w'],x['alpha'],x['subset']))
            break
    return chosen,dict(full_solves=calls,certificate_pruned=pruned,cardinality_skipped=15*len(alphas)-checks,screened=checks,**hist)

def same(x,y):
    if x is None or y is None:return x is None and y is None
    if (x['cardinality'],x['subset'],x['alpha'])!=(y['cardinality'],y['subset'],y['alpha']):return False
    return abs(x['p_req_w']-y['p_req_w'])<=1e-7*max(abs(y['p_req_w']),1e-20)

def run_geometry(i,h,group,alphas,cfg,variant_list,signature,near_eps):
    ref=exhaustive(h,alphas,cfg); opt=oracle(ref)
    lookup={(r['subset'],float(r['alpha'])):r for r in ref}
    ablations=[]; certificates=[]
    for variant,enabled in variant_list:
        t=time.perf_counter();choice,stats=select(h,alphas,cfg,enabled);runtime=1000*(time.perf_counter()-t)
        if not same(choice,opt):raise AssertionError(f'NONMATCH geometry={i} variant={variant}')
        ablations.append(dict(geometry=i,group=str(group),variant=variant,exact_match=1,runtime_ms=runtime,**stats))
    for s in range(1,5):
        for sub in itertools.combinations(range(4),s):
            sid=''.join(map(str,sub))
            for alpha in alphas:
                skip,reason,bound,slack=screening(h,sub,alpha,cfg,set(RULES))
                reference=lookup[(sid,float(alpha))]
                if skip and reference['status']=='FEASIBLE':raise AssertionError(f'FALSE_CERTIFICATE geometry={i} subset={sid} alpha={alpha}')
                if skip:
                    certificates.append(dict(geometry=i,group=str(group),subset=sid,alpha=alpha,reason=reason,bound=bound,relative_slack=slack,near_threshold=int(np.isfinite(slack) and abs(slack)<near_eps),reference_status=reference['status'],false_prune=0))
    return dict(signature=signature,complete=True,geometry=i,group=str(group),ablations=ablations,certificates=certificates,oracle=dict(cardinality=opt['cardinality'],subset=opt['subset'],alpha=opt['alpha'],power_w=opt['p_req_w']) if opt else None)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stage',required=True,choices=['preflight','scan','report','all']);ap.add_argument('--dataset',required=True);ap.add_argument('--run-id',required=True);ap.add_argument('--out-root',default='outputs');ap.add_argument('--limit',type=int,default=0)
    ap.add_argument('--q',type=float,default=2.960414);ap.add_argument('--sigma-rel',type=float,default=.04);ap.add_argument('--sinr-db',type=float,default=6.);ap.add_argument('--noise',type=float,default=2e-13);ap.add_argument('--pmax',type=float,default=1.)
    ap.add_argument('--alpha-list',default='0,0.001,0.01,0.05,0.1,0.3,1');ap.add_argument('--near-eps',type=float,default=1e-5)
    a=ap.parse_args();H,groups,meta=load(a.dataset);N=len(H) if a.limit<=0 else min(a.limit,len(H));alphas=sorted(set(map(float,a.alpha_list.split(','))))
    if not alphas or min(alphas)<0 or a.q<0 or a.sigma_rel<=0 or a.noise<=0 or a.pmax<=0 or a.near_eps<=0:raise ValueError('Invalid configuration')
    cfg=dict(q=a.q,sigma=a.sigma_rel,gamma=10**(a.sinr_db/10),noise=a.noise,pmax=a.pmax)
    variants=[('ALL',set(RULES)),('CARDINALITY_ONLY',set())]+[('WITHOUT_'+r,set(RULES)-{r}) for r in RULES]
    config={k:v for k,v in vars(a).items() if k not in ('stage','run_id','out_root')};config.update(data_sha=digest(a.dataset),code_sha=digest(__file__),reference_sha=digest(Path(__file__).parent/'reference_model.py'))
    signature=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest();root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    mp=root/'CP00_manifest.json'
    if mp.exists():
        if json.loads(mp.read_text())['signature']!=signature:raise RuntimeError('Signature mismatch: choose a new run-id')
    else:jwrite(mp,dict(signature=signature,config=config,n=N,groups=int(len(np.unique(groups[:N]))),variants=[v[0] for v in variants],caveat='Group names do not guarantee independence.'))
    if a.stage=='preflight':print('PREFLIGHT PASS',N,'geometries',len(np.unique(groups[:N])),'groups');return
    if a.stage in ('scan','all'):
        for i in range(N):
            p=root/'tasks'/f'{i:07d}.json'
            if p.exists():
                t=json.loads(p.read_text())
                if t.get('signature')==signature and t.get('complete') and t.get('geometry')==i:continue
                raise RuntimeError('Corrupt task checkpoint: '+str(p))
            result=run_geometry(i,H[i],groups[i],alphas,cfg,variants,signature,a.near_eps)
            jwrite(p,result)
            if (i+1)%20==0:print('Completed',i+1,'/',N,flush=True)
    if a.stage in ('report','all'):
        tasks=[]
        for i in range(N):
            p=root/'tasks'/f'{i:07d}.json'
            if not p.exists():raise RuntimeError('Incomplete run '+str(p))
            t=json.loads(p.read_text())
            if t.get('signature')!=signature or not t.get('complete'):raise RuntimeError('Invalid task '+str(p))
            tasks.append(t)
        ar=[r for t in tasks for r in t['ablations']];cr=[r for t in tasks for r in t['certificates']]
        cwrite(root/'CP01_ablation_geometry.csv',ar,list(ar[0]));cwrite(root/'CP02_certificate_audit.csv',cr,list(cr[0]) if cr else ['geometry','group','subset','alpha','reason','bound','relative_slack','near_threshold','reference_status','false_prune'])
        summary=[]
        for variant,_ in variants:
            rs=[r for r in ar if r['variant']==variant]
            summary.append(dict(variant=variant,n=N,exact_match=sum(r['exact_match'] for r in rs),mean_full_solves=float(np.mean([r['full_solves'] for r in rs])),mean_screened=float(np.mean([r['screened'] for r in rs])),mean_certificate_pruned=float(np.mean([r['certificate_pruned'] for r in rs])),mean_runtime_ms=float(np.mean([r['runtime_ms'] for r in rs]))))
        cwrite(root/'CP03_ablation_summary.csv',summary,list(summary[0]));reasonrows=[]
        for rule in RULES:
            vals=[r for r in cr if r['reason']==rule]
            reasonrows.append(dict(rule=rule,n_pruned=len(vals),near_threshold=sum(r['near_threshold'] for r in vals),false_prune=sum(r['false_prune'] for r in vals)))
        cwrite(root/'CP04_numerical_audit_summary.csv',reasonrows,list(reasonrows[0]))
        best={r['variant']:r for r in summary}; allv=best['ALL'];base=best['CARDINALITY_ONLY']
        report=dict(status='PASS' if all(r['exact_match']==N for r in summary) and not any(r['false_prune'] for r in cr) else 'FAIL',n_geometries=N,n_candidates_per_geometry=15*len(alphas),certificate_count=len(cr),false_certificates=0,mean_solver_savings_vs_cardinality_only=base['mean_full_solves']-allv['mean_full_solves'],all_mean_runtime_ms=allv['mean_runtime_ms'],cardinality_only_mean_runtime_ms=base['mean_runtime_ms'],note='Ablation isolated incremental solver calls, not guaranteed speedup. The oracle is exact only in finite candidate codebook. Reused geometries are development, not independent test.' )
        jwrite(root/'CP05_decision.json',report)
        shas=[dict(file=p.name,sha256=digest(p)) for p in sorted(root.glob('CP0*')) if p.name!='CP06_SHA256.csv'];cwrite(root/'CP06_SHA256.csv',shas,['file','sha256'])
        print(json.dumps(report,indent=2))
if __name__=='__main__':main()
