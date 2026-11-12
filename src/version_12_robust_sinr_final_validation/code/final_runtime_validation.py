#!/usr/bin/env python3
"""Frozen K=4 finite-codebook verification, fast screening vs strongest baseline.

All test decisions are verified against independent exhaustive oracle. The benchmark
is a paired, randomized, repeated wall-time comparison including all preprocessing.
No tuning allowed on test. No claim of complete interval-arithmetic certification.
"""
import argparse, csv, hashlib, itertools, json, math, os, time
from pathlib import Path
from collections import defaultdict
import numpy as np
from reference_model import load, solve, exhaustive, oracle, digest, jwrite, cwrite
from ablation_audit import same
from ablation_certified import build_Fu

SOURCES=('DeepMIMO','Sionna_3GPP')
RULESETS={'FAST':('ZERO_GAIN','NOISE','TWO_CYCLE','NEUMANN'),
          'LITE':('ZERO_GAIN','NOISE','TWO_CYCLE'),
          'CARDINALITY_ONLY':()}


def subsets():
    for s in range(4,0,-1):
        for sub in itertools.combinations(range(4),s): yield s,sub


def safe_prune(comp,cfg,rules,guard):
    """Only strict sufficient tests, with fail-open within relative numerical guard."""
    if comp is None:return False,'BEAM_UNDEFINED',False
    if comp['zero']:
        # Ambiguous direct-gain margin is kept, not rejected.
        nn=np.asarray(comp['norms']); mm=np.asarray(comp['direct_margin'])
        margin=float(np.min(mm/np.maximum(nn,1e-30)))
        if 'ZERO_GAIN' not in rules:return False,'NONE',False
        if margin < -guard:return True,'ZERO_GAIN',False
        return False,'ZERO_GAIN_BOUNDARY',True
    F,u=comp['F'],comp['u'];pmax=cfg['pmax']
    if 'NOISE' in rules:
        bound=float(np.sum(u));slack=bound/pmax-1
        if slack>guard:return True,'NOISE',False
        if abs(slack)<=guard:return False,'NOISE_BOUNDARY',True
    if 'TWO_CYCLE' in rules:
        for i in range(len(u)):
            for j in range(i+1,len(u)):
                c=float(F[i,j]*F[j,i]); slack=c-1
                if slack>guard:return True,'TWO_CYCLE',False
                if abs(slack)<=guard:return False,'CYCLE_BOUNDARY',True
    if 'NEUMANN' in rules:
        total=u.copy();term=u.copy()
        for _ in range(4):
            term=F@term;total+=term
            slack=float(np.sum(total)/pmax-1)
            if slack>guard:return True,'NEUMANN',False
            if abs(slack)<=guard:return False,'NEUMANN_BOUNDARY',True
    return False,'SURVIVE',False


def search(h,cfg,alphas,variant,guard):
    rules=RULESETS[variant];best=None;calls=0;pruned=0;failopen=0
    t_beam=t_screen=t_solve=0.;tested=0
    for size in range(4,0,-1):
        winners=[]
        for _,sub in (x for x in subsets() if x[0]==size):
            for alpha in alphas:
                tested+=1
                # Strong comparator performs no extra beam assembly or screening.
                if rules:
                    t=time.perf_counter();comp=build_Fu(h,sub,alpha,cfg)
                    t_beam+=time.perf_counter()-t
                    t=time.perf_counter();skip,reason,uncertain=safe_prune(comp,cfg,rules,guard)
                    t_screen+=time.perf_counter()-t
                    failopen+=int(uncertain)
                    if skip:
                        pruned+=1;continue
                t=time.perf_counter();r=solve(h,list(sub),alpha,cfg)
                t_solve+=time.perf_counter()-t;calls+=1
                if r['status']=='FEASIBLE':
                    winners.append(dict(subset=''.join(map(str,sub)),alpha=float(alpha),cardinality=size,**r))
        if winners:
            best=min(winners,key=lambda z:(z['p_req_w'],z['alpha'],z['subset']))
            break
    return best,dict(full_solves=calls,certificate_pruned=pruned,fail_open=failopen,
                     candidates_visited=tested,beam_ms=t_beam*1000,
                     screening_ms=t_screen*1000,solver_ms=t_solve*1000)


def group_bootstrap(deltas,groups,n_boot=2000,seed=1831):
    unique=sorted(set(map(str,groups)));by={g:[] for g in unique}
    for d,g in zip(deltas,groups):by[str(g)].append(float(d))
    if len(unique)<3:return [None,None]
    rng=np.random.default_rng(seed);v=[]
    for _ in range(n_boot):
        ids=rng.integers(0,len(unique),len(unique))
        v.append(float(np.mean([x for i in ids for x in by[unique[int(i)]]])))
    return [float(np.quantile(v,.025)),float(np.quantile(v,.975))]


def settings(args):
    alphas=sorted(set(float(t) for t in args.alphas.split(',')))
    if not alphas or min(alphas)<0 or len(alphas)!=7:raise ValueError('Exactly seven nonnegative beam settings expected')
    if any(not math.isfinite(z) for z in alphas):raise ValueError('alphas nonfinite')
    if args.noise<=0 or args.pmax<=0 or args.sigma_rel<=0 or args.guard<=0:raise ValueError('Invalid physical parameters')
    return dict(q=args.q,sigma=args.sigma_rel,gamma=10**(args.sinr_db/10),noise=args.noise,pmax=args.pmax),alphas


def lock(a,root):
    cfg,alphas=settings(a)
    files=['final_runtime_validation.py','reference_model.py','ablation_certified.py','ablation_audit.py']
    obj=dict(version='V12-frozen',code_hashes={p:digest(Path(__file__).parent/p) for p in files},
             config=cfg,alphas=alphas,guard=a.guard,variants=['CARDINALITY_ONLY','FAST','LITE'],
             objective='lexicographic maximum cardinality then minimum power',
             primary_comparator='CARDINALITY_ONLY', primary_variant='FAST',
             decision_rule='PASS iff exact oracle match, zero false screening, 95pct cluster CI runtime saving >0 on each independent source',
             caveat='No claims about continuous beam directions; data independence requires provenance')
    path=root/'CP00_frozen_protocol.json'
    if path.exists():
        if json.loads(path.read_text())!=obj:raise RuntimeError('Frozen protocol or code changed; NEW run-id required')
    elif a.stage=='lock':jwrite(path,obj)
    else:raise RuntimeError('Run --stage lock BEFORE loading test data')
    return obj


def audit_data(a,root):
    if not a.dataset or not a.provenance:raise ValueError('dataset and provenance required')
    p=json.loads(Path(a.provenance).read_text(encoding='utf8'))
    required=['source','scenario','split','generation_method','independence_basis','group_definition','channel_units','created_before_test']
    if any(not p.get(x) for x in required):raise ValueError('Provenance missing mandatory fields')
    if p['source'] not in SOURCES or p['split']!='new_independent_test' or p['created_before_test'] is not True:raise ValueError('Dataset not labeled independent test')
    if a.source!=p['source']:raise ValueError('Explicit --source must match provenance')
    if a.smoke is False and a.limit:raise ValueError('--limit only allowed for smoke')
    H,groups,meta=load(a.dataset)
    n=min(len(H),a.limit) if a.limit else len(H)
    if len(set(map(str,groups[:n])))<a.min_groups and not a.smoke:raise ValueError('Insufficient groups')
    if a.development_groups:
        dev=set(map(str,json.loads(Path(a.development_groups).read_text(encoding='utf8'))))
        if dev.intersection(set(map(str,groups[:n]))):raise ValueError('Detected development/test group overlap')
    entry=dict(dataset_sha256=digest(a.dataset),provenance_sha256=digest(a.provenance),
               dataset_path=str(Path(a.dataset).resolve()),provenance=p,n=n,
               n_groups=len(set(map(str,groups[:n]))),smoke=a.smoke,
               development_groups_sha=digest(a.development_groups) if a.development_groups else None,
               metadata=list(meta), statistical_independence_verified=False)
    f=root/'CP01_dataset_audit.json'
    if f.exists() and json.loads(f.read_text())!=entry:raise RuntimeError('Dataset changed; NEW run-id required')
    if not f.exists():jwrite(f,entry)
    return H[:n],groups[:n],entry


def evaluate(i,h,group,locked,repeats):
    cfg=locked['config'];alphas=locked['alphas'];guard=locked['guard']
    refrows=exhaustive(h,alphas,cfg);ref=oracle(refrows)
    # balanced interleaving, permuted order per repetition
    executions=[]
    for rep in range(repeats):
        choices=list(locked['variants']);np.random.default_rng(918+rep+i).shuffle(choices)
        for variant in choices:
            t=time.perf_counter();candidate,stats=search(h,cfg,alphas,variant,guard)
            elapsed=(time.perf_counter()-t)*1000
            if not same(candidate,ref):raise AssertionError(f'Oracle mismatch: {i} {variant}')
            executions.append(dict(geometry=i,group=str(group),repetition=rep,variant=variant,
                                   runtime_ms=elapsed,oracle_match=1,**stats))
    # Independently audit every possible FAST certificate against exhaustive table.
    truth={(r['subset'],float(r['alpha'])):r for r in refrows}
    audits=[]
    for size,sub in subsets():
        for alpha in alphas:
            comp=build_Fu(h,sub,alpha,cfg)
            rejected,why,uncertain=safe_prune(comp,cfg,RULESETS['FAST'],guard)
            target=truth[(''.join(map(str,sub)),float(alpha))]
            false=int(rejected and target['status']=='FEASIBLE')
            if false:raise AssertionError(f'False certificate: {i} {sub} {alpha}')
            audits.append(dict(geometry=i,group=str(group),subset=''.join(map(str,sub)),alpha=alpha,
                               rejected=int(rejected),reason=why,fail_open=int(uncertain),
                               oracle_status=target['status'],false_prune=false))
    return dict(repetitions=executions,audit=audits,oracle=None if ref is None else dict(cardinality=ref['cardinality'],subset=ref['subset'],alpha=ref['alpha'],power_w=ref['p_req_w']))


def main():
    aparser=argparse.ArgumentParser(description=__doc__)
    aparser.add_argument('--stage',choices=['lock','preflight','scan','report','all'],required=True)
    aparser.add_argument('--dataset',default='');aparser.add_argument('--provenance',default='');aparser.add_argument('--source',choices=SOURCES,default='DeepMIMO')
    aparser.add_argument('--run-id',required=True);aparser.add_argument('--out-root',default='outputs')
    aparser.add_argument('--development-groups',default='');aparser.add_argument('--smoke',action='store_true')
    aparser.add_argument('--limit',type=int,default=0);aparser.add_argument('--min-groups',type=int,default=20)
    aparser.add_argument('--repeats',type=int,default=7);aparser.add_argument('--bootstrap',type=int,default=2000)
    aparser.add_argument('--q',type=float,default=2.960414);aparser.add_argument('--sigma-rel',type=float,default=.04)
    aparser.add_argument('--sinr-db',type=float,default=6.);aparser.add_argument('--noise',type=float,default=2e-13)
    aparser.add_argument('--pmax',type=float,default=1.);aparser.add_argument('--alphas',default='0,0.001,0.01,0.05,0.1,0.3,1')
    aparser.add_argument('--guard',type=float,default=1e-5)
    a=aparser.parse_args()
    if a.repeats<2 or a.bootstrap<100:raise ValueError('Need >=2 repeats and >=100 bootstrap draws')
    root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    locked=lock(a,root)
    if a.stage=='lock':print('LOCKED',root);return
    H,groups,scope=audit_data(a,root)
    if a.stage=='preflight':print('PREFLIGHT',scope['n'],scope['n_groups']);return
    sig=hashlib.sha256(json.dumps(dict(locked=locked,scope=scope,repeats=a.repeats),sort_keys=True).encode()).hexdigest()
    if a.stage in ('scan','all'):
        for i,h in enumerate(H):
            path=root/'tasks'/f'{i:07d}.json'
            if path.exists():
                ck=json.loads(path.read_text())
                if ck.get('signature')!=sig or not ck.get('complete'):raise RuntimeError(f'Invalid checkpoint {path}')
                continue
            val=evaluate(i,h,groups[i],locked,a.repeats)
            jwrite(path,dict(signature=sig,complete=True,geometry=i,**val))
            if (i+1)%10==0:print('Completed',i+1,'/',len(H),flush=True)
    if a.stage in ('report','all'):
        tasks=[]
        for i in range(len(H)):
            f=root/'tasks'/f'{i:07d}.json'
            if not f.exists():raise RuntimeError(f'Missing checkpoint {f}')
            t=json.loads(f.read_text())
            if t.get('signature')!=sig or not t.get('complete'):raise RuntimeError(f'Corrupt checkpoint {f}')
            tasks.append(t)
        runs=[r for t in tasks for r in t['repetitions']]
        audit=[r for t in tasks for r in t['audit']]
        cwrite(root/'CP02_repeated_runtime.csv',runs,list(runs[0]))
        cwrite(root/'CP03_all_candidate_audit.csv',audit,list(audit[0]))
        pairs=[]
        for i,t in enumerate(tasks):
            d={}
            for v in locked['variants']:
                rows=[r for r in t['repetitions'] if r['variant']==v]
                d[v]=dict(runtime=float(np.median([r['runtime_ms'] for r in rows])),
                          calls=float(np.median([r['full_solves'] for r in rows])),
                          screen=float(np.median([r['screening_ms'] for r in rows])))
            pairs.append(dict(geometry=i,group=str(groups[i]),card_ms=d['CARDINALITY_ONLY']['runtime'],
                              fast_ms=d['FAST']['runtime'],lite_ms=d['LITE']['runtime'],
                              fast_saved_ms=d['CARDINALITY_ONLY']['runtime']-d['FAST']['runtime'],
                              lite_saved_ms=d['CARDINALITY_ONLY']['runtime']-d['LITE']['runtime'],
                              fast_calls_saved=d['CARDINALITY_ONLY']['calls']-d['FAST']['calls'],
                              lite_calls_saved=d['CARDINALITY_ONLY']['calls']-d['LITE']['calls']))
        cwrite(root/'CP04_paired_geometry.csv',pairs,list(pairs[0]))
        summaries=[]
        for v in ['FAST','LITE']:
            ci=group_bootstrap([r[f'{v.lower()}_saved_ms'] for r in pairs],groups,a.bootstrap)
            saves=float(np.mean([r[f'{v.lower()}_saved_ms'] for r in pairs]))
            summaries.append(dict(variant=v,n=len(pairs),groups=scope['n_groups'],
                                  mean_runtime_saved_ms=saves,runtime_ci_lo=ci[0],runtime_ci_hi=ci[1],
                                  mean_calls_saved=float(np.mean([r[f'{v.lower()}_calls_saved'] for r in pairs])),
                                  runtime_go=(not a.smoke and ci[0] is not None and ci[0]>0)))
        cwrite(root/'CP05_comparison_summary.csv',summaries,list(summaries[0]))
        false=sum(int(r['false_prune']) for r in audit)
        result=dict(status='FAIL_FALSE_PRUNE' if false else ('SMOKE_ONLY' if a.smoke else ('GO_FAST_RUNTIME' if summaries[0]['runtime_go'] else 'STOP_NO_FAST_RUNTIME_ADVANTAGE')),
                    source=a.source,n=len(pairs),groups=scope['n_groups'],false_prune=false,
                    all_candidates=len(audit),fail_open=sum(int(r['fail_open']) for r in audit),
                    comparisons=summaries,
                    manuscript_lock='NOT_YET: both DeepMIMO and Sionna_3GPP independently validated with GO and provenance audit',
                    caveat='Group bootstrap descriptive; numerical oracle is finite candidate, floating point; test data never used to tune code')
        jwrite(root/'CP06_decision.json',result)
        hashes=[dict(file=p.name,sha256=digest(p)) for p in sorted(root.glob('CP0*')) if p.name!='CP07_SHA256.csv']
        cwrite(root/'CP07_SHA256.csv',hashes,['file','sha256'])
        print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
