#!/usr/bin/env python3
"""Provably safe pruning within fixed finite ZF/RZF candidate family, K=4.
Reference oracle is recomputed by reference_model.exhaustive; no oracle lookup in pruning.
"""
import argparse,csv,hashlib,itertools,json,os,time
from pathlib import Path
import numpy as np
from reference_model import load,get_beam,solve,exhaustive,oracle,digest,jwrite,cwrite

def screening(h, subset, alpha, cfg):
    """Return (skip, reason, certificate). Every skip condition is sufficient for infeasibility.
    Uses a subset-wide optimistic robust signal upper bound, then per-beam necessary bounds.
    """
    m=len(subset); Hs=h[:,list(subset)]; norms=np.linalg.norm(Hs,axis=0)
    r=cfg['q']*cfg['sigma']*norms/np.sqrt(h.shape[0])
    a_max=np.maximum(norms-r,0.)**2
    if np.any(a_max<=0):return True,'NORM_UPPER_GAIN_ZERO',{'min_amax':float(np.min(a_max))}
    noise_lb=float(np.sum(cfg['gamma']*cfg['noise']/a_max))
    if noise_lb>cfg['pmax']*(1+1e-10):return True,'NORM_NOISE_LOWER_BOUND',{'lower_power':noise_lb}
    W=get_beam(Hs,alpha)
    if W is None:return True,'BEAM_UNDEFINED',{}
    g=np.abs(Hs.conj().T@W)
    a=np.maximum(np.diag(g)-r,0.)**2
    if np.any(a<=0):return True,'ZERO_ROBUST_GAIN',{'min_gain':float(np.min(a))}
    u=cfg['gamma']*cfg['noise']/a
    if float(np.sum(u))>cfg['pmax']*(1+1e-10):return True,'NOISE_LOWER_BOUND',{'lower_power':float(np.sum(u))}
    F=cfg['gamma']*(g+r[:,None])**2/a[:,None]
    np.fill_diagonal(F,0.)
    # Every nonnegative feasible vector satisfies p >= sum_{t=0}^T F^t u.
    terms=u.copy(); subtotal=u.copy()
    for t in range(1,5):
        terms=F@terms; subtotal+=terms
        lb=float(np.sum(subtotal))
        if lb>cfg['pmax']*(1+1e-10):return True,'NEUMANN_LOWER_BOUND',{'lower_power':lb,'neumann_order':t}
    # Any nonnegative square submatrix has spectral radius <= rho(F). Two-cycle product >= 1 rules out finite positive power.
    for i in range(m):
        for j in range(i+1,m):
            if F[i,j]*F[j,i]>=1-1e-12:
                return True,'TWO_CYCLE_COUPLING',{'pair':[int(i),int(j)],'product':float(F[i,j]*F[j,i])}
    return False,'SURVIVOR',{'lower_power':float(np.sum(subtotal))}

def select_pruned(H,alphas,cfg):
    audit=[]; calls=0; screened=0; best=None; selected_s=0
    for s in range(4,0,-1):
        candidates=[]
        for sub in itertools.combinations(range(4),s):
            for a in alphas:
                skip,reason,cert=screening(H,sub,a,cfg)
                rec={'subset':''.join(map(str,sub)),'cardinality':s,'alpha':a,'pruned':int(skip),'reason':reason, 'certificate':json.dumps(cert,sort_keys=True)}
                if skip:
                    screened+=1;rec['status']='CERTIFIED_PRUNED';rec['power_w']=''
                else:
                    calls+=1
                    r=solve(H,list(sub),a,cfg)
                    rec['status']=r['status'];rec['power_w']=r['p_req_w'] if r['p_req_w'] is not None else ''
                    if r['status']=='FEASIBLE':candidates.append(dict(subset=rec['subset'],cardinality=s,alpha=a,**r))
                audit.append(rec)
        if candidates:
            best=min(candidates,key=lambda r:(-r['cardinality'],r['p_req_w'],r['alpha'],r['subset']))
            selected_s=s
            break
    return best,audit,{'full_candidates':15*len(alphas),'evaluated':calls,'pruned_by_certificate':screened,'pruned_by_cardinality':15*len(alphas)-len(audit),'cardinality':selected_s}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stage',required=True,choices=['preflight','scan','report','all'])
    ap.add_argument('--dataset',required=True);ap.add_argument('--run-id',required=True);ap.add_argument('--out-root',default='outputs');ap.add_argument('--limit',type=int,default=0)
    ap.add_argument('--q',type=float,default=2.960414);ap.add_argument('--sigma-rel',type=float,default=.04)
    ap.add_argument('--sinr-db',type=float,default=6.);ap.add_argument('--noise',type=float,default=2e-13);ap.add_argument('--pmax',type=float,default=1.)
    ap.add_argument('--alpha-list',default='0,0.001,0.01,0.05,0.1,0.3,1')
    args=ap.parse_args();H,groups,metadata=load(args.dataset);n=len(H) if args.limit<=0 else min(args.limit,len(H))
    alphas=sorted(set(float(x) for x in args.alpha_list.split(',')))
    if not alphas or min(alphas)<0 or args.q<0 or args.sigma_rel<=0 or args.noise<=0 or args.pmax<=0:raise ValueError('Invalid system settings')
    cfg=dict(q=args.q,sigma=args.sigma_rel,gamma=10**(args.sinr_db/10),noise=args.noise,pmax=args.pmax)
    config={k:v for k,v in vars(args).items() if k not in ('stage','run_id','out_root')};config.update(data_sha=digest(args.dataset),code_sha=digest(__file__),reference_sha=digest(Path(__file__).parent/'reference_model.py'))
    signature=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest();root=Path(args.out_root)/args.run_id
    root.mkdir(parents=True,exist_ok=True);manifest=root/'CP00_manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['signature']!=signature:raise RuntimeError('Run signature changed: use another run-id')
    else:jwrite(manifest,dict(signature=signature,config=config,n=n,groups=int(len(np.unique(groups[:n]))),candidate_count=15*len(alphas)))
    if args.stage=='preflight':print('PASS',n,'geometries; groups:',len(np.unique(groups[:n])));return
    if args.stage in ('scan','all'):
        for i in range(n):
            path=root/'tasks'/f'{i:07d}.json'
            if path.exists():
                x=json.loads(path.read_text())
                if x.get('signature')==signature and x.get('complete') and x.get('geometry')==i:continue
                raise RuntimeError('Invalid task checkpoint '+str(path))
            t=time.perf_counter();p,audit,counts=select_pruned(H[i],alphas,cfg);dt=(time.perf_counter()-t)*1000
            t=time.perf_counter();reference_rows=exhaustive(H[i],alphas,cfg);o=oracle(reference_rows);odt=(time.perf_counter()-t)*1000
            def key(v):return None if v is None else [v['cardinality'],v['subset'],v['alpha'],v['p_req_w']]
            matched=(p is None and o is None) or (p is not None and o is not None and key(p)[:3]==key(o)[:3] and abs(p['p_req_w']-o['p_req_w'])<=1e-7*max(o['p_req_w'],1e-20))
            # Audit every certificate against independent exact candidate result, including power infeasibility.
            bykey={(r['subset'],float(r['alpha'])):r for r in reference_rows}
            bad=[r for r in audit if r['pruned'] and bykey[(r['subset'],float(r['alpha']))]['status']=='FEASIBLE']
            if bad or not matched:raise AssertionError(f'UNSAFE_PRUNING geometry={i}, false_skips={len(bad)}, oracle_match={matched}')
            jwrite(path,dict(signature=signature,complete=True,geometry=i,group=str(groups[i]),oracle=key(o),selected=key(p),match=matched,counters=counts,pruned_runtime_ms=dt,oracle_runtime_ms=odt,audit=audit,reference_rows=reference_rows))
            if (i+1)%25==0:print('Completed',i+1,'/',n)
    if args.stage in ('report','all'):
        tasks=[]
        for i in range(n):
            path=root/'tasks'/f'{i:07d}.json'
            if not path.exists():raise RuntimeError('Missing '+str(path))
            t=json.loads(path.read_text())
            if t['signature']!=signature or not t['complete'] or not t['match']:raise RuntimeError('Failed checkpoint '+str(path))
            tasks.append(t)
        rows=[];summary=[];pair=[]
        for t in tasks:
            for r in t['audit']:rows.append(dict(geometry=t['geometry'],group=t['group'],**r))
            c=t['counters'];summary.append(dict(geometry=t['geometry'],group=t['group'],oracle=t['oracle'],pruned=t['selected'],same_solution=int(t['match']),**c,pruned_runtime_ms=t['pruned_runtime_ms'],oracle_runtime_ms=t['oracle_runtime_ms']))
            for r in t['reference_rows']:
                pair.append(dict(geometry=t['geometry'],subset=r['subset'],alpha=r['alpha'],status=r['status'],power_w=r['p_req_w']))
        cwrite(root/'CP01_candidate_screening.csv',rows,list(rows[0]));cwrite(root/'CP02_geometry_paired.csv',summary,list(summary[0]));cwrite(root/'CP03_reference_exhaustive.csv',pair,list(pair[0]))
        reasonlist=sorted(set(r['reason'] for r in rows));reasonrows=[dict(reason=reason,count=sum(r['reason']==reason for r in rows)) for reason in reasonlist]
        cwrite(root/'CP04_screening_reasons.csv',reasonrows,['reason','count'])
        m={'n_geometries':n,'all_oracle_matched':bool(all(t['match'] for t in tasks)),'mean_executed_full_solve_calls':float(np.mean([t['counters']['evaluated'] for t in tasks])),'mean_certificate_pruned':float(np.mean([t['counters']['pruned_by_certificate'] for t in tasks])),'mean_cardinality_pruned':float(np.mean([t['counters']['pruned_by_cardinality'] for t in tasks])),'mean_runtime_oracle_ms':float(np.mean([t['oracle_runtime_ms'] for t in tasks])),'mean_runtime_pruned_ms':float(np.mean([t['pruned_runtime_ms'] for t in tasks])),'scope':'Exact optimum only within 15 user subsets and listed ZF/RZF beams; not global beamforming; no outage or fairness certificate.'}
        jwrite(root/'CP05_decision.json',m)
        files=[{'file':p.name,'sha256':digest(p)} for p in sorted(root.glob('CP0*')) if p.name!='CP06_SHA256.csv']
        cwrite(root/'CP06_SHA256.csv',files,['file','sha256']);print(json.dumps(m,indent=2))
if __name__=='__main__':main()
