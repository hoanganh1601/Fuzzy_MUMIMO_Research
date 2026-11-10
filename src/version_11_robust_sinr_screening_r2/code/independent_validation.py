#!/usr/bin/env python3
"""Locked independent-channel assessment: ALL vs CARDINALITY_ONLY and exhaustive.

Dataset provenance must be documented. The tool cannot prove independence merely
from labels, file names, or dataset checksums. No training/tuning on test sets.
"""
import argparse,csv,hashlib,json,math,time
from pathlib import Path
from collections import defaultdict
import numpy as np
from reference_model import utf8_console
from reference_model import load,exhaustive,oracle,solve,digest,jwrite,cwrite
from ablation_certified import selection,robust_screen,all_candidates,bootstrap_ci
from ablation_audit import RULES,same

LEGACY_SHA='1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50'
ORDER_SEED_BASE=7531
BOOTSTRAP_SEED=1729

def lock_config(a,root):
    paths=['reference_model.py','ablation_audit.py','ablation_certified.py','independent_validation.py']
    code={p:digest(Path(__file__).with_name(p)) for p in paths}
    cfg=dict(q=a.q,sigma=a.sigma_rel,gamma=10**(a.sinr_db/10),noise=a.noise,pmax=a.pmax,
             alphas=sorted(set(float(v) for v in a.alpha_list.split(','))),guard=a.numeric_guard)
    if any(x<0 or not math.isfinite(x) for x in cfg['alphas']):raise ValueError('invalid alphas')
    # Analysis settings are locked too: changing repetitions, bootstrap size,
    # group threshold or seeds after seeing test data would be post-hoc tuning.
    analysis=dict(repeats=a.repeats,bootstrap=a.bootstrap,min_groups=a.min_groups,
                  order_seed_base=ORDER_SEED_BASE,bootstrap_seed=BOOTSTRAP_SEED)
    data=dict(code_hashes=code,cfg=cfg,analysis=analysis,goal='test fixed finite beam-codebook screening, no margin optimization',
              created_without_test='true',legacy_development_dataset_sha=LEGACY_SHA,
              design_note='The full test set must remain unopened before lock; source provenance is mandatory.')
    f=root/'CP00_locked_protocol.json'
    if f.exists():
        if json.loads(f.read_text(encoding='utf8'))!=data:raise RuntimeError('Code or parameters changed after lock; new lock directory required')
    elif a.stage=='lock':jwrite(f,data)
    else:raise RuntimeError('LOCK REQUIRED: run --stage lock before accessing test dataset')
    return data

def validate_data(a,root,locked):
    if not a.dataset or not a.provenance:raise ValueError('both --dataset and --provenance required')
    with open(a.provenance,encoding='utf-8') as f:prov=json.load(f)
    required=('source','scenario','split','generation_method','independence_basis','channel_units','group_definition','created_before_test')
    missing=[k for k in required if not prov.get(k)]
    if missing:raise ValueError('Missing provenance fields: '+','.join(missing))
    if prov['source'] not in ('DeepMIMO','Sionna_3GPP','other_independent'):raise ValueError('source invalid')
    if prov['split']!='new_independent_test':raise ValueError('not locked independent test split')
    if prov['created_before_test'] is not True:raise ValueError('provenance must attest pre-test creation')
    datahash=digest(a.dataset)
    if datahash==LEGACY_SHA:raise ValueError('REUSED legacy development DeepMIMO file: independent test prohibited')
    if a.source!='auto' and a.source!=prov['source']:raise ValueError('source mismatch')
    H,groups,meta=load(a.dataset)
    if a.development_groups:
        dev_ids=json.loads(Path(a.development_groups).read_text(encoding='utf8'))
        if not isinstance(dev_ids,list):raise ValueError('development-groups must be JSON array')
        overlap=set(map(str,groups)) & set(map(str,dev_ids))
        if overlap:raise ValueError(f'DEVELOPMENT GROUP OVERLAP: {len(overlap)} groups')
    if a.limit<0:raise ValueError('--limit must be >= 0')
    if a.limit and not a.smoke:raise ValueError('--limit only allowed with --smoke; not publishable')
    n=min(a.limit,len(H)) if a.limit else len(H)
    if len(set(map(str,groups[:n])))<a.min_groups and not a.smoke:raise ValueError('too few groups for planned analysis')
    if len(set(map(str,groups[:n])))<3:raise ValueError('need at least three groups')
    scope={'dataset_sha':datahash,'dataset_path':str(Path(a.dataset).resolve()),'provenance_sha':digest(a.provenance),
           'provenance':prov,'n':n,'n_groups':len(set(map(str,groups[:n]))),
           'metadata_fields':list(meta.keys()),'smoke':a.smoke,
           'development_groups_sha':digest(a.development_groups) if a.development_groups else None,
           'independence_caveat':'Independence is asserted by data provenance, not verified statistically by this program.'}
    path=root/'CP01_dataset_audit.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf8'))!=scope:raise RuntimeError('dataset/provenance change: new run-id required')
    else:jwrite(path,scope)
    return H[:n],groups[:n],scope

def measure(h,group,i,locked,repeats):
    cfg=locked['cfg'];alphas=cfg['alphas']; guard=cfg['guard']
    oracle_rows=exhaustive(h,alphas,cfg)
    ref=oracle(oracle_rows)
    order=np.random.default_rng(locked['analysis']['order_seed_base']+i).integers(0,2,size=repeats)
    reps=[];choices={};audits=[]
    for rep,flag in enumerate(order):
        for label in (('ALL','CARDINALITY_ONLY') if flag==0 else ('CARDINALITY_ONLY','ALL')):
            enabled=set(RULES) if label=='ALL' else set()
            t=time.perf_counter()
            choice,stat=selection(h,alphas,cfg,enabled,guard)
            runtime=(time.perf_counter()-t)*1000.
            if not same(choice,ref):raise AssertionError(f'ORACLE MISMATCH {i} {label}')
            reps.append(dict(geometry=i,group=str(group),repetition=rep,variant=label,
                             runtime_ms=runtime,beam_ms=stat['beam_ms'],screening_ms=stat['screening_ms'],solver_ms=stat['solver_ms'],beams_built=stat['beams_built'],
                             full_solves=stat['full_solves'],certificate_pruned=stat['certificate_pruned'],
                             near_fail_open=stat['near_threshold_fail_open'],oracle_match=1))
            choices[label]=choice
    # Independently audit ALL certificates for every candidate, not only visited ones.
    refs={(r['subset'],float(r['alpha'])):r for r in oracle_rows}
    for size,sub in all_candidates():
        sid=''.join(map(str,sub))
        for alpha in alphas:
            prune,rec=robust_screen(h,sub,alpha,cfg,set(RULES),guard)
            truth=refs[(sid,float(alpha))]
            false=int(prune and truth['status']=='FEASIBLE')
            if false:raise AssertionError(f'FALSE CERTIFICATE geometry={i}, subset={sid}, alpha={alpha}')
            audits.append(dict(geometry=i,group=str(group),subset=sid,alpha=alpha,
                               decision='PRUNED' if prune else ('FAIL_OPEN' if rec['fail_open'] else 'SURVIVE'),reason=rec['reason'],
                               oracle_status=truth['status'],false_prune=false,
                               near_threshold=rec['near_threshold'],fail_open=rec['fail_open'],
                               mp_checked=rec['mp_checked']))
    return dict(reps=reps,audits=audits,choice=({k:(None if v is None else {'subset':v['subset'],'alpha':v['alpha'],'p_req_w':v['p_req_w'],'cardinality':v['cardinality']}) for k,v in choices.items()}),
                oracle=None if ref is None else {'subset':ref['subset'],'alpha':ref['alpha'],'p_req_w':ref['p_req_w'],'cardinality':ref['cardinality']})

def main():
    utf8_console()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',required=True,choices=['lock','preflight','scan','report','all'])
    ap.add_argument('--dataset',default='');ap.add_argument('--provenance',default='')
    ap.add_argument('--development-groups',default='',help='Optional JSON list of development group IDs for overlap audit')
    ap.add_argument('--source',default='auto',choices=['auto','DeepMIMO','Sionna_3GPP','other_independent'])
    ap.add_argument('--run-id',required=True);ap.add_argument('--out-root',default='outputs');ap.add_argument('--limit',type=int,default=0)
    ap.add_argument('--smoke',action='store_true');ap.add_argument('--min-groups',type=int,default=20)
    ap.add_argument('--repeats',type=int,default=5);ap.add_argument('--bootstrap',type=int,default=2000)
    ap.add_argument('--q',type=float,default=2.960414);ap.add_argument('--sigma-rel',type=float,default=.04)
    ap.add_argument('--sinr-db',type=float,default=6.);ap.add_argument('--noise',type=float,default=2e-13)
    ap.add_argument('--pmax',type=float,default=1.);ap.add_argument('--alpha-list',default='0,0.001,0.01,0.05,0.1,0.3,1')
    ap.add_argument('--numeric-guard',type=float,default=1e-5)
    a=ap.parse_args()
    if a.repeats<1 or a.bootstrap<100 or a.numeric_guard<=0 or a.pmax<=0 or a.noise<=0 or a.sigma_rel<=0:raise ValueError('parameters invalid')
    root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    locked=lock_config(a,root)
    if a.stage=='lock':print('LOCK PASS',root/'CP00_locked_protocol.json');return
    H,groups,scope=validate_data(a,root,locked)
    if a.stage=='preflight':print('PREFLIGHT PASS',scope['n'],scope['n_groups'],scope['dataset_sha']);return
    signature=hashlib.sha256(json.dumps(dict(locked=locked,scope=scope,repeats=a.repeats),sort_keys=True).encode()).hexdigest()
    if a.stage in ('scan','all'):
        for i,h in enumerate(H):
            f=root/'tasks'/f'{i:07d}.json'
            if f.exists():
                ck=json.loads(f.read_text(encoding='utf8'))
                if ck.get('signature')!=signature or not ck.get('complete'):raise RuntimeError('bad checkpoint '+str(f))
                continue
            val=measure(h,groups[i],i,locked,a.repeats)
            jwrite(f,dict(signature=signature,complete=True,geometry=i,**val))
            if (i+1)%10==0:print('completed',i+1,'/',len(H),flush=True)
    if a.stage in ('report','all'):
        tasks=[]
        for i in range(len(H)):
            f=root/'tasks'/f'{i:07d}.json'
            if not f.exists():raise RuntimeError('missing '+str(f))
            t=json.loads(f.read_text(encoding='utf8'))
            if t['signature']!=signature or not t['complete']:raise RuntimeError('bad checkpoint')
            tasks.append(t)
        reps=[r for t in tasks for r in t['reps']]
        audit=[r for t in tasks for r in t['audits']]
        cwrite(root/'CP02_runtime_repetitions.csv',reps,list(reps[0]))
        cwrite(root/'CP03_candidate_audit.csv',audit,list(audit[0]))
        per=[]
        for i,t in enumerate(tasks):
            v={}
            for method in ('ALL','CARDINALITY_ONLY'):
                arows=[r for r in t['reps'] if r['variant']==method]
                v[method]=dict(time=float(np.median([r['runtime_ms'] for r in arows])),
                               calls=float(np.median([r['full_solves'] for r in arows])))
            per.append(dict(geometry=i,group=str(groups[i]),
                            runtime_saved_ms=v['CARDINALITY_ONLY']['time']-v['ALL']['time'],
                            solver_calls_saved=v['CARDINALITY_ONLY']['calls']-v['ALL']['calls'],
                            all_median_ms=v['ALL']['time'],card_median_ms=v['CARDINALITY_ONLY']['time'],
                            cardinality= t['oracle']['cardinality'] if t['oracle'] else 0))
        cwrite(root/'CP04_paired_geometry.csv',per,list(per[0]))
        bs=locked['analysis']
        ci=bootstrap_ci([r['runtime_saved_ms'] for r in per],[r['group'] for r in per],seed=bs['bootstrap_seed'],n_boot=bs['bootstrap'])
        cci=bootstrap_ci([r['solver_calls_saved'] for r in per],[r['group'] for r in per],seed=bs['bootstrap_seed'],n_boot=bs['bootstrap'])
        mean_card=float(np.mean([r['card_median_ms'] for r in per]));mean_all=float(np.mean([r['all_median_ms'] for r in per]))
        result=dict(status='FAIL' if any(r['false_prune'] for r in audit) else ('SMOKE_ONLY' if a.smoke else 'AUDIT_PASS'),
                    n_geometries=len(H),n_groups=scope['n_groups'],n_candidates=len(audit),
                    false_prunes=sum(r['false_prune'] for r in audit),n_fail_open=sum(r['fail_open'] for r in audit),
                    mean_calls_saved=float(np.mean([r['solver_calls_saved'] for r in per])),
                    mean_runtime_saved_ms=float(np.mean([r['runtime_saved_ms'] for r in per])),
                    mean_cardinality_runtime_ms=mean_card,mean_all_runtime_ms=mean_all,
                    runtime_reduction_pct=(mean_card-mean_all)/mean_card*100,
                    runtime_ci95=ci,calls_ci95=cci,
                    observed_runtime_go=(not a.smoke and ci['lo'] is not None and ci['lo']>0 and not any(r['false_prune'] for r in audit)),
                    caveat='Group bootstrap is descriptive; independent-scenario assessment requires credible provenance and channel-source audit. Finite codebook only.')
        jwrite(root/'CP05_independent_decision.json',result)
        checks=[{'file':p.name,'sha256':digest(p)} for p in sorted(root.glob('CP0*')) if p.name!='CP06_sha256.csv']
        cwrite(root/'CP06_sha256.csv',checks,['file','sha256'])
        print(json.dumps(result,indent=2))
if __name__=='__main__':main()
