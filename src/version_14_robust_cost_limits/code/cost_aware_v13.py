#!/usr/bin/env python3
"""V13: development-locked, cost-aware early feasibility screening.

Exact finite-codebook objective, unchanged robust SINR coefficients, 4 users.
Policies: CARD (baseline), EARLY (CSI-only necessary bound), CACHED (reuse beam
and robust F,u for screening and power solve), HYBRID (EARLY+CACHED).
Selection uses *development only* and a conservative paired group-bootstrap gate.
Test never changes the policy. Non-strict or numerically ambiguous comparisons
fail open. Numerical oracle is independent exhaustive reference_model.solve.
"""
import argparse, csv, hashlib, itertools, json, math, os, time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from reference_model import load, exhaustive, oracle, solve, digest, jwrite, cwrite
from ablation_certified import build_Fu
from ablation_audit import same

POLICIES=('CARD','EARLY','CACHED','HYBRID')
CODE_FILES=('cost_aware_v13.py','reference_model.py','ablation_certified.py','ablation_audit.py')
ALPHAS=(0.,.001,.01,.05,.1,.3,1.)

def group_ci(x, groups, repeats=2000, seed=7321):
    mp={}
    for value,g in zip(x,groups):mp.setdefault(str(g),[]).append(float(value))
    if len(mp)<3:return (None,None)
    keys=sorted(mp);rng=np.random.default_rng(seed);means=[]
    for _ in range(repeats):
        draw=rng.integers(len(keys),size=len(keys))
        arr=[v for j in draw for v in mp[keys[int(j)]]]
        means.append(float(np.mean(arr)))
    return tuple(float(z) for z in np.quantile(means,[.025,.975]))

def cfg_of(a):
    return {'q':a.q,'sigma':a.sigma_rel,'gamma':10**(a.sinr_db/10),
            'noise':a.noise,'pmax':a.pmax}

def early_bound(h, sub, cfg, guard):
    """Necessary CSI-only bound: p_k >= gamma*noise/||hhat_k||^2.

    Robust error region contains e=0; every normalized beam satisfies
    |h_k^H w_k|^2 <= ||h_k||^2. Interference is nonnegative. Thus this bound
    is valid for ANY candidate beam, provided robust model contains zero error.
    """
    sq=np.sum(np.abs(h[:,list(sub)])**2,axis=0)
    if np.any(sq<=1e-25):return False,'EARLY_UNCERTAIN_ZERO',True,math.nan
    lb=float(np.sum(cfg['gamma']*cfg['noise']/sq))
    excess=lb/cfg['pmax']-1
    if not np.isfinite(excess):return False,'EARLY_NONFINITE',True,lb
    if excess>guard:return True,'EARLY_NORM_BOUND',False,lb
    if abs(excess)<=guard:return False,'EARLY_FAIL_OPEN',True,lb
    return False,'EARLY_PASS',False,lb

def post_bound(comp, cfg, guard):
    """Sufficient infeasibility checks on coefficients already computed once."""
    if comp is None:return False,'BEAM_UNDEFINED',True
    if comp['zero']:
        margins=np.asarray(comp['direct_margin'],dtype=float)
        den=np.maximum(np.asarray(comp['norms']),1e-25)
        if min(margins/den)<-guard:return True,'ZERO_GAIN',False
        return False,'ZERO_FAIL_OPEN',True
    F=np.asarray(comp['F']);u=np.asarray(comp['u'])
    if not np.isfinite(F).all() or not np.isfinite(u).all():return False,'NONFINITE',True
    checks=[('NOISE',float(sum(u))/cfg['pmax']-1)]
    if len(u)>1:
        checks.append(('CYCLE',max(float(F[i,j]*F[j,i]-1) for i in range(len(u)) for j in range(i+1,len(u)))))
    term=u.copy();partial=u.copy()
    for _ in range(4):
        term=F@term;partial=partial+term
        checks.append(('NEUMANN',float(sum(partial))/cfg['pmax']-1))
    if any(abs(s)<=guard for _,s in checks if math.isfinite(s)):
        return False,'POST_FAIL_OPEN',True
    for name,slack in checks:
        if math.isfinite(slack) and slack>guard:return True,name,False
    return False,'POST_PASS',False

def from_comp(comp,cfg):
    """Same F,u power calculation and LP audit as reference_model.solve,
    but avoid building the beam and coefficients a second time."""
    if comp is None:return {'status':'BEAM_RANK_OR_NUMERICAL','p_req_w':None}
    if comp['zero']:return {'status':'ZERO_ROBUST_DIRECT_GAIN','p_req_w':None}
    F=comp['F'];u=comp['u'];S=len(u)
    rho=float(max(abs(np.linalg.eigvals(F))))
    if rho>=1-1e-10:return {'status':'COUPLING_RHO_GE_ONE','p_req_w':None}
    try:p=np.linalg.solve(np.eye(S)-F,u)
    except np.linalg.LinAlgError:return {'status':'SINGULAR_MATRIX','p_req_w':None}
    if not np.isfinite(p).all() or min(p)<0:return {'status':'INVALID_POWER','p_req_w':None}
    req=float(sum(p));residual=float(min(p-F@p-u))
    if req>cfg['pmax']*(1+1e-9):return {'status':'POWER_BUDGET','p_req_w':req}
    scale=max(float(np.max(u)),1e-20)
    lp=linprog(np.ones(S),A_ub=F-np.eye(S),b_ub=-u/scale,bounds=(0,None),method='highs')
    if not lp.success:return {'status':'LP_FAILURE','p_req_w':req}
    gap=abs(float(sum(lp.x))*scale-req)/max(req,1e-30)
    if gap>1e-5 or residual< -1e-7*max(float(np.max(u)),1e-20):
        return {'status':'LP_MISMATCH','p_req_w':req}
    return {'status':'FEASIBLE','p_req_w':req}

def search(h,cfg,policy,guard):
    card=policy=='CARD';early=policy in ('EARLY','HYBRID');cache=policy in ('CACHED','HYBRID')
    met={'full_calls':0,'early_rejects':0,'post_rejects':0,'fail_open':0,'candidates_seen':0,
         'early_ms':0.,'beam_ms':0.,'screen_ms':0.,'solve_ms':0.}
    for size in range(4,0,-1):
        feasible=[]
        for sub in itertools.combinations(range(4),size):
            # For early screening, the bound is shared across all beams of the subset.
            skip=False
            if early:
                t=time.perf_counter();skip,why,uncertain,lb=early_bound(h,sub,cfg,guard)
                met['early_ms']+=(time.perf_counter()-t)*1e3
                met['fail_open']+=int(uncertain)
            for alpha in ALPHAS:
                met['candidates_seen']+=1
                if skip:
                    met['early_rejects']+=1;continue
                if cache:
                    t=time.perf_counter();comp=build_Fu(h,sub,alpha,cfg)
                    met['beam_ms']+=(time.perf_counter()-t)*1e3
                    t=time.perf_counter();drop,reason,uncertain=post_bound(comp,cfg,guard)
                    met['screen_ms']+=(time.perf_counter()-t)*1e3
                    met['fail_open']+=int(uncertain)
                    if drop:met['post_rejects']+=1;continue
                    t=time.perf_counter();result=from_comp(comp,cfg)
                else:
                    t=time.perf_counter();result=solve(h,list(sub),alpha,cfg)
                met['solve_ms']+=(time.perf_counter()-t)*1e3
                met['full_calls']+=1
                if result['status']=='FEASIBLE':
                    feasible.append({'subset':''.join(map(str,sub)),'cardinality':size,
                                     'alpha':alpha,'p_req_w':result['p_req_w']})
        if feasible:
            return min(feasible,key=lambda x:(x['p_req_w'],x['alpha'],x['subset'])),met
    return None,met

def code_hashes():return {s:digest(Path(__file__).parent/s) for s in CODE_FILES}

def settings(a):
    if a.q<0 or a.sigma_rel<=0 or a.pmax<=0 or a.noise<=0 or a.repeats<2 or a.bootstrap<100 or a.guard<=0:
        raise ValueError('Invalid physical/statistical parameters')
    return {'cfg':cfg_of(a),'alphas':ALPHAS,'guard':a.guard,'repeats':a.repeats,
            'bootstrap':a.bootstrap,'min_gain_ms':a.min_gain_ms,'code_hashes':code_hashes()}

def dataset(a,path,split):
    if not path:raise ValueError('Missing '+split+' dataset')
    H,groups,meta=load(path)
    if len(H)<a.min_n and not a.smoke:raise ValueError('Too few geometries: '+split)
    if len(set(map(str,groups)))<a.min_groups and not a.smoke:raise ValueError('Too few groups: '+split)
    return H,groups,meta

def frozen(a,root):
    path=root/'CP02_policy_lock.json'
    if not path.exists():raise RuntimeError('Run --stage develop before test')
    obj=json.loads(path.read_text());current=settings(a)
    if obj['settings']!=json.loads(json.dumps(current)) or obj['dev_sha256']!=digest(a.dev_dataset):
        raise RuntimeError('Source, parameters or development data changed; new run-id required')
    return obj

def run_repeated(h,grp,i,policies,cfg,guard,repeats,oracle_check=True):
    refrows=exhaustive(h,ALPHAS,cfg) if oracle_check else []
    ref=oracle(refrows) if oracle_check else None
    rows=[]
    for r in range(repeats):
        order=list(policies);np.random.default_rng(98231+i*19+r).shuffle(order)
        for policy in order:
            t=time.perf_counter();v,m=search(h,cfg,policy,guard);total=(time.perf_counter()-t)*1000
            if oracle_check and not same(v,ref):
                raise AssertionError(f'Oracle mismatch geometry={i} policy={policy} oracle={ref} result={v}')
            rows.append({'geometry':i,'group':str(grp),'rep':r,'policy':policy,
                         'runtime_ms':total,'oracle_match':1 if oracle_check else '',
                         'cardinality':v['cardinality'] if v else 0,
                         'subset':v['subset'] if v else '', 'alpha':v['alpha'] if v else '',
                         'power_w':v['p_req_w'] if v else '',**m})
    audits=[]
    if oracle_check:
        lookup={(r['subset'],float(r['alpha'])):r for r in refrows}
        for size in range(4,0,-1):
            for sub in itertools.combinations(range(4),size):
                bskip,bwhy,bunc,lb=early_bound(h,sub,cfg,guard)
                for alpha in ALPHAS:
                    comp=build_Fu(h,sub,alpha,cfg)
                    pskip,pwhy,punc=post_bound(comp,cfg,guard)
                    truth=lookup[(''.join(map(str,sub)),float(alpha))]['status']=='FEASIBLE'
                    if truth and (bskip or pskip):raise AssertionError(f'False certificate {i}, {sub}, {alpha}')
                    audits.append({'geometry':i,'group':str(grp),'subset':''.join(map(str,sub)),
                                   'alpha':alpha,'oracle_feasible':int(truth),'early_reject':int(bskip),
                                   'post_reject':int(pskip),'early_reason':bwhy,'post_reason':pwhy,
                                   'fail_open':int(bunc or punc),'false_reject':0})
    return rows,audits

def paired(rows,other):
    ids=sorted(set(int(x['geometry']) for x in rows));out=[]
    for i in ids:
        rs=[r for r in rows if int(r['geometry'])==i]
        by={p:np.median([float(z['runtime_ms']) for z in rs if z['policy']==p]) for p in ('CARD',other)}
        out.append({'geometry':i,'group':rs[0]['group'],'card_ms':float(by['CARD']),
                    'selected_ms':float(by[other]),'saved_ms':float(by['CARD']-by[other]),
                    'card_calls':float(np.mean([z['full_calls'] for z in rs if z['policy']=='CARD'])),
                    'selected_calls':float(np.mean([z['full_calls'] for z in rs if z['policy']==other]))})
    return out

def write_report(root,rows,selected,boot,smoke):
    cwrite(root/'CP04_runtime_repetitions.csv',rows,list(rows[0]))
    p=paired(rows,selected);cwrite(root/'CP05_paired_geometry.csv',p,list(p[0]))
    ci=group_ci([z['saved_ms'] for z in p],[z['group'] for z in p],boot)
    mean=float(np.mean([z['saved_ms'] for z in p]));speed=float(np.mean([z['card_ms'] for z in p]))/max(float(np.mean([z['selected_ms'] for z in p])),1e-12)
    status=('SMOKE_ONLY' if smoke else ('GO_RUNTIME' if selected!='CARD' and ci[0] is not None and ci[0]>0 else 'STOP_NO_RUNTIME_GAIN'))
    result={'status':status,'policy':selected,'n':len(p),'groups':len(set(x['group'] for x in p)),
            'mean_saved_ms':mean,'ci95_saved_ms':ci,'ratio_mean_runtime':speed,
            'mean_calls_saved':float(np.mean([x['card_calls']-x['selected_calls'] for x in p])),
            'oracle_mismatch':sum(1 for r in rows if r['oracle_match']!=1),
            'scope':'exact finite ZF/RZF set only; statistical independence requires provenance',
            'no_retraining_on_test':True}
    jwrite(root/'CP06_decision.json',result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True,choices=['develop','preflight','scan','report','all'])
    parser.add_argument('--dev-dataset',required=True);parser.add_argument('--test-dataset',default='')
    parser.add_argument('--dev-provenance',default='');parser.add_argument('--test-provenance',default='')
    parser.add_argument('--run-id',required=True);parser.add_argument('--out-root',default='outputs')
    parser.add_argument('--q',type=float,default=2.960414);parser.add_argument('--sigma-rel',type=float,default=.04)
    parser.add_argument('--sinr-db',type=float,default=6.);parser.add_argument('--noise',type=float,default=2e-13)
    parser.add_argument('--pmax',type=float,default=1.);parser.add_argument('--guard',type=float,default=1e-5)
    parser.add_argument('--repeats',type=int,default=7);parser.add_argument('--bootstrap',type=int,default=2000)
    parser.add_argument('--min-gain-ms',type=float,default=.1)
    parser.add_argument('--min-groups',type=int,default=20);parser.add_argument('--min-n',type=int,default=50)
    parser.add_argument('--smoke',action='store_true');parser.add_argument('--limit',type=int,default=0)
    a=parser.parse_args();settings(a)
    if not a.smoke and a.min_gain_ms<0:raise ValueError('Official min-gain-ms must be nonnegative')
    root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    devH,devG,_=dataset(a,a.dev_dataset,'development')
    if a.stage=='develop':
        if (root/'CP02_policy_lock.json').exists():raise RuntimeError('Already locked: use a new run-id to retrain')
        if a.limit:devH,devG=devH[:a.limit],devG[:a.limit]
        rows=[]
        for i,h in enumerate(devH):
            rec,_=run_repeated(h,devG[i],i,POLICIES,cfg_of(a),a.guard,a.repeats);rows+=rec
        cwrite(root/'CP01_development_runtime.csv',rows,list(rows[0]))
        summary=[]
        for policy in POLICIES[1:]:
            pairs=paired(rows,policy);ci=group_ci([r['saved_ms'] for r in pairs],[r['group'] for r in pairs],a.bootstrap)
            summary.append({'policy':policy,'mean_saved_ms':float(np.mean([x['saved_ms'] for x in pairs])),
                            'ci_lo':ci[0],'ci_hi':ci[1],
                            'passes':ci[0] is not None and ci[0]>a.min_gain_ms})
        cwrite(root/'CP01_policy_candidates.csv',summary,list(summary[0]))
        eligible=[r for r in summary if r['passes']]
        chosen=max(eligible,key=lambda r:(r['mean_saved_ms'],r['policy']))['policy'] if eligible else 'CARD'
        obj={'settings':settings(a),'dev_sha256':digest(a.dev_dataset),'development_groups':sorted(set(map(str,devG))),
             'development_geometry_hashes':sorted(hashlib.sha256(np.ascontiguousarray(h).tobytes()).hexdigest() for h in devH),
             'selected_policy':chosen,'candidate_results':summary,'scope':'selection from development only'}
        jwrite(root/'CP02_policy_lock.json',obj)
        print('FROZEN',chosen,'; development candidates:',summary);return
    lock=frozen(a,root)
    if not a.test_dataset:raise ValueError('Test dataset required')
    if not a.smoke and (not a.dev_provenance or not a.test_provenance):
        raise ValueError('Both provenance files required for official independent evaluation')
    H,G,_=dataset(a,a.test_dataset,'test')
    if a.limit:
        if not a.smoke:raise ValueError('--limit allowed only in smoke')
        H,G=H[:a.limit],G[:a.limit]
    if digest(a.dev_dataset)==digest(a.test_dataset):raise ValueError('Same development and test bytes')
    overlap=set(map(str,G)) & set(lock['development_groups'])
    if overlap:raise ValueError(f'Development/test group overlap, example {sorted(overlap)[:3]}')
    shared=set(lock['development_geometry_hashes']) & {hashlib.sha256(np.ascontiguousarray(h).tobytes()).hexdigest() for h in H}
    if shared:raise ValueError('Exact channel overlap with development')
    provenance={}
    for part,name in [(a.dev_provenance,'development'),(a.test_provenance,'test')]:
        if part:
            p=json.loads(Path(part).read_text())
            if not p.get('source') or not p.get('scenario') or not p.get('group_definition') or not p.get('independence_basis'):
                raise ValueError('Missing provenance: '+name)
            provenance[name]=p
    if not a.smoke and provenance['test'].get('prior_use') not in ('never_seen','sealed_before_development'):
        raise ValueError('Test provenance must declare never_seen or sealed_before_development')
    meta={'dev_sha256':lock['dev_sha256'],'test_sha256':digest(a.test_dataset),
          'n_test':len(H),'groups':len(set(map(str,G))), 'group_overlap':0,'exact_channel_overlap':0,
          'test_provenance':provenance,'independence_not_proven_by_group_ids':True,
          'selected_policy':lock['selected_policy']}
    file=root/'CP03_test_preflight.json'
    if file.exists() and json.loads(file.read_text())!=meta:raise RuntimeError('Dataset or provenance changed; use new run-id')
    if not file.exists():jwrite(file,meta)
    if a.stage=='preflight':print('PASS PREFLIGHT',meta);return
    signature=hashlib.sha256(json.dumps({'lock':lock,'meta':meta},sort_keys=True).encode()).hexdigest()
    selected=lock['selected_policy']
    if a.stage in ('scan','all'):
        for i,h in enumerate(H):
            f=root/'tasks'/f'{i:07d}.json'
            if f.exists():
                old=json.loads(f.read_text())
                if old.get('signature')!=signature or not old.get('complete'):raise RuntimeError('Corrupt checkpoint '+str(f))
                continue
            rows,audits=run_repeated(h,G[i],i,('CARD',) if selected=='CARD' else ('CARD',selected),cfg_of(a),a.guard,a.repeats)
            jwrite(f,{'signature':signature,'complete':True,'rows':rows,'audit':audits})
            if (i+1)%20==0:print('DONE',i+1,'/',len(H),flush=True)
    if a.stage in ('report','all'):
        rows=[];audits=[]
        for i in range(len(H)):
            f=root/'tasks'/f'{i:07d}.json'
            if not f.exists():raise RuntimeError('Missing '+str(f))
            d=json.loads(f.read_text())
            if d['signature']!=signature or not d['complete']:raise RuntimeError('Invalid task '+str(f))
            rows+=d['rows'];audits+=d['audit']
        cwrite(root/'CP08_candidate_certificate_audit.csv',audits,list(audits[0]))
        if selected=='CARD':
            # No manufactured speedup when fallback is the baseline.
            selected_rows=[dict(r,policy='SELECTED_CARD') for r in rows]
            rows+=selected_rows
            # paired helper expects selected policy key
            selected='SELECTED_CARD'
        outcome=write_report(root,rows,selected,a.bootstrap,a.smoke)
        hashes=[{'file':f.name,'sha256':digest(f)} for f in sorted(root.glob('CP0*')) if f.name!='CP07_SHA256.csv']
        cwrite(root/'CP07_SHA256.csv',hashes,['file','sha256'])
        print(json.dumps(outcome,indent=2))
if __name__=='__main__':main()
