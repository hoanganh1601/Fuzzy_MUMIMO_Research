#!/usr/bin/env python3
"""V14: frozen, out-of-sample cost model for finite-codebook robust MU-MIMO screening.

No novelty/acceleration claim is made by this program. It emits GO/STOP evidence.
Fit set -> select interpretable switch -> confirm on held-out development groups -> lock
-> evaluate on untouched test groups / different channel source. A switch chooses CARD
or one of the existing V13 screening policies. No changes to SINR oracle or CSI radius.
"""
import argparse, csv, hashlib, itertools, json, math, os, sys, time
from pathlib import Path
import numpy as np
from cost_aware_v13 import search, ALPHAS, cfg_of, group_ci, POLICIES, early_bound, post_bound
from ablation_certified import build_Fu
from reference_model import load, exhaustive, oracle, jwrite, cwrite, digest
from ablation_audit import same

SCRIPT=Path(__file__).resolve()
SOURCE_FILES=[SCRIPT]+[SCRIPT.parent/f for f in ('cost_aware_v13.py','reference_model.py','ablation_audit.py','ablation_certified.py')]
POLICIES_COMPARE=('CARD','EARLY','CACHED','HYBRID')
FEATURES=('early_ratio','norm_spread')

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def geometry_hash(h):return sha_bytes(np.ascontiguousarray(h).tobytes())
def feature(h,cfg):
    """Cheap, pre-beam indicators. Measured separately; cost charged for adaptive switch."""
    n=np.sum(np.abs(h)**2,axis=0)
    safe=np.maximum(n,1e-300)
    early=float(np.sum(cfg['gamma']*cfg['noise']/safe)/cfg['pmax'])
    spread=float(np.log10(np.max(safe)/np.min(safe)))
    return {'early_ratio':early,'norm_spread':spread}

def apply_rule(z,rule):
    if rule['policy']=='CARD':return 'CARD'
    f=(0.0 if rule['feature']=='always' else float(z[rule['feature']]));cut=rule['threshold']
    hit=(f>=cut) if rule['direction']=='ge' else (f<=cut)
    return rule['policy'] if hit else 'CARD'

def build_rules(training, min_active):
    rules=[{'policy':'CARD','feature':'','threshold':0.,'direction':''}]
    for pol in POLICIES_COMPARE[1:]:
        # constant policy included to test whether switching is necessary
        rules.append({'policy':pol,'feature':'always','threshold':0.,'direction':'ge'})
        for name in FEATURES:
            values=np.array([float(r[name]) for r in training])
            for q in (.2,.35,.5,.65,.8):
                cut=float(np.quantile(values,q))
                for dr in ('ge','le'):
                    rule={'policy':pol,'feature':name,'threshold':cut,'direction':dr}
                    active=sum(apply_rule(r,rule)==pol for r in training)
                    if active>=min_active and active<len(training):rules.append(rule)
    # stable distinct threshold keys
    result=[];seen=set()
    for r in rules:
        k=json.dumps(r,sort_keys=True)
        if k not in seen:seen.add(k);result.append(r)
    return result

def add_cost(r,rule):
    policy=apply_rule(r,rule)
    # CARD baseline never incurs feature cost. An adaptive switch always does.
    if rule['policy']=='CARD':return float(r['CARD_ms']),policy
    return float(r[policy+'_ms']) + float(r['feature_ms']),policy

def evaluate_rule(rows,rule,n_boot,seed=1357):
    vals=[float(r['CARD_ms'])-add_cost(r,rule)[0] for r in rows]
    groups=[r['group'] for r in rows]
    ci=group_ci(vals,groups,n_boot,seed=seed)
    return {'mean_saved_ms':float(np.mean(vals)),'ci_lo':ci[0],'ci_hi':ci[1],
            'activation_fraction':float(np.mean([apply_rule(r,rule)!='CARD' for r in rows])),
            'median_saved_ms':float(np.median(vals))}

def keys_by_group(G,seed):
    keys=sorted(set(map(str,G)))
    if len(keys)<2:raise ValueError('Need >=2 source groups')
    rng=np.random.default_rng(seed);rng.shuffle(keys)
    split=max(1,min(len(keys)-1,int(round(.60*len(keys)))))
    return set(keys[:split]),set(keys[split:])

def profile_one(h,group,i,cfg,repeats,guard,smoke):
    oracle_rows=exhaustive(h,ALPHAS,cfg)
    ref=oracle(oracle_rows);times={p:[] for p in POLICIES_COMPARE}
    fcost=[];first=None
    for j in range(repeats):
        order=list(POLICIES_COMPARE)
        np.random.default_rng(5100+i*71+j).shuffle(order)
        for pol in order:
            t=time.perf_counter_ns();result,stats=search(h,cfg,pol,guard)
            elapsed=(time.perf_counter_ns()-t)/1e6
            if not same(result,ref):raise AssertionError(f'Oracle mismatch: profile {i} {pol}')
            times[pol].append(elapsed)
            if pol=='CARD' and first is None:first=stats
        t=time.perf_counter_ns();z=feature(h,cfg);fcost.append((time.perf_counter_ns()-t)/1e6)
    out={'geometry':i,'group':str(group),'early_ratio':z['early_ratio'],'norm_spread':z['norm_spread'],
         'feature_ms':float(np.median(fcost)),'oracle_match':1,
         'card_calls':first['full_calls'] if first else ''}
    for p in POLICIES_COMPARE:out[p+'_ms']=float(np.median(times[p]))
    # Candidate-level cost accounting is diagnostic only: never an input to the policy.
    candidate_cost=[]
    for r in oracle_rows:
        sub=tuple(int(v) for v in r['subset'])
        t=time.perf_counter_ns();ed,ew,eo,_=early_bound(h,sub,cfg,guard)
        et=(time.perf_counter_ns()-t)/1e6
        t=time.perf_counter_ns();comp=build_Fu(h,sub,float(r['alpha']),cfg)
        beam_ms=(time.perf_counter_ns()-t)/1e6
        t=time.perf_counter_ns();pd,pw,po=post_bound(comp,cfg,guard)
        ps=(time.perf_counter_ns()-t)/1e6
        candidate_cost.append({'geometry':i,'group':str(group),'subset':r['subset'],'alpha':r['alpha'],
           'oracle_status':r['status'],'oracle_solver_ms':r['runtime_ms'],
           'early_reject':int(ed),'post_reject':int(pd),'early_ms':et,
           'beam_construction_ms':beam_ms,'post_screen_ms':ps,
           'false_certificate':int(r['status']=='FEASIBLE' and (ed or pd))})
    if any(x['false_certificate'] for x in candidate_cost):raise AssertionError('False certificate during development profiling')
    return out,candidate_cost

def validate_provenance(path,needed=True):
    if not path:
        if needed:raise ValueError('Provenance JSON required for official run')
        return {'source':'synthetic_smoke','scenario':'synthetic','prior_use':'smoke'}
    d=json.loads(Path(path).read_text(encoding='utf8'))
    required=('source','scenario','group_definition','independence_basis','prior_use')
    missing=[v for v in required if not d.get(v)]
    if missing:raise ValueError('Missing provenance keys: '+','.join(missing))
    return d

def args_signature(a,include_test=False):
    base={'cfg':cfg_of(a),'repeats':a.repeats,'guard':a.guard,'bootstrap':a.bootstrap,
          'min_gain_ms':a.min_gain_ms,'min_groups':a.min_groups,'seed':a.seed,
          'code_hashes':{p.name:digest(p) for p in SOURCE_FILES},'dev_hash':digest(a.development)}
    if include_test:base['test_hash']=digest(a.test)
    return base

def run_path(a):return Path(a.out)/a.run_id

def assert_unchanged(path,obj):
    if path.exists() and json.loads(path.read_text(encoding='utf8'))!=obj:raise RuntimeError('Checkpoint mismatch; new run-id required: '+str(path))
    if not path.exists():jwrite(path,obj)

def read_or_raise(path):
    if not path.exists():raise RuntimeError('Missing checkpoint '+str(path))
    return json.loads(path.read_text(encoding='utf8'))

def create_and_check_manifest(a,root):
    root.mkdir(parents=True,exist_ok=True)
    manifest={'signature':sha_bytes(json.dumps(args_signature(a),sort_keys=True).encode()),'settings':args_signature(a)}
    assert_unchanged(root/'CP00_manifest.json',manifest)
    return manifest

def preflight(a,root,lock,H,G,prov):
    if digest(a.development)==digest(a.test):raise RuntimeError('Development and test same file')
    devH,devG,_=load(a.development)
    group_overlap=set(map(str,devG))&set(map(str,G))
    exact_overlap={geometry_hash(h) for h in devH}&{geometry_hash(h) for h in H}
    if group_overlap or exact_overlap:raise RuntimeError('Development/test overlap in group or exact channel')
    if not a.smoke and prov['prior_use'] not in ('never_seen','sealed_before_development'):
        raise RuntimeError('Test not sealed: previously used data cannot be independent confirmation')
    if not a.smoke and len(set(map(str,G)))<a.min_groups:raise RuntimeError('Insufficient test groups')
    doc={'lock_hash':digest(root/'CP03_locked_rule.json'),'test_hash':digest(a.test),
         'test_groups':len(set(map(str,G))),'n':len(H),'test_provenance':prov,
         'group_overlap':0,'exact_channel_overlap':0,
         'independence_not_proven_by_group_labels':True}
    assert_unchanged(root/'CP04_preflight.json',doc)
    return doc

def single_repeated(h,g,i,rule,cfg,guard,repeats,hashcode):
    """Per-geometry randomized-order paired timings; all overhead for active rule included."""
    ref=oracle(exhaustive(h,ALPHAS,cfg));rows=[]
    oracle_candidates=exhaustive(h,ALPHAS,cfg)
    # Separate oracle audit of ALL candidates (not timed in either policy).
    cert_errors=0;all_checked=len(oracle_candidates);audits=[]
    for item in oracle_candidates:
        subset=tuple(int(x) for x in item['subset'])
        e_drop,e_why,e_open,_=early_bound(h,subset,cfg,guard)
        comp=build_Fu(h,subset,float(item['alpha']),cfg)
        p_drop,p_why,p_open=post_bound(comp,cfg,guard)
        feasible=item['status']=='FEASIBLE'
        mistake=int(feasible and (e_drop or p_drop))
        cert_errors+=mistake
        audits.append({'geometry':i,'group':str(g),'subset':item['subset'],
                       'alpha':item['alpha'],'oracle_status':item['status'],
                       'early_reject':int(e_drop),'post_reject':int(p_drop),
                       'early_reason':e_why,'post_reason':p_why,
                       'fail_open':int(e_open or p_open),'false_reject':mistake})
    if cert_errors:raise AssertionError(f'Unsafe screening certificates: geometry={i}, false={cert_errors}')
    for rep in range(repeats):
        order=['CARD','ADAPTIVE'];np.random.default_rng(9001+i*73+rep).shuffle(order)
        for mode in order:
            t=time.perf_counter_ns()
            if mode=='CARD':pol='CARD';z=None
            else:
                z=feature(h,cfg) if rule['policy']!='CARD' else None
                pol=apply_rule(z,rule) if z is not None else 'CARD'
            decision,stats=search(h,cfg,pol,guard)
            dur=(time.perf_counter_ns()-t)/1e6
            if not same(decision,ref):raise AssertionError(f'Oracle mismatch {i} {mode} {pol}')
            rows.append({'geometry':i,'group':str(g),'rep':rep,'mode':mode,'executed_policy':pol,
                         'runtime_ms':dur,'full_calls':stats['full_calls'],'oracle_match':1,
                         'screen_ms':stats['screen_ms'],'beam_ms':stats['beam_ms'],
                         'solve_ms':stats['solve_ms'],'early_ms':stats['early_ms'],
                         'cardinality':decision['cardinality'] if decision else 0,
                         'power_w':decision['p_req_w'] if decision else '',
                         'code_signature':hashcode})
    return {'rows':rows,'oracle_candidates':all_checked,'false_certificate':cert_errors,'audits':audits}

def write_csv(path,rows):
    if not rows:raise RuntimeError('Missing output rows: '+str(path))
    cwrite(path,rows,list(rows[0]))

def finish(a,root,H,G,signature,rule,smoke):
    all_rows=[];checks=[];audits=[]
    for i in range(len(H)):
        entry=read_or_raise(root/'tasks'/f'{i:07d}.json')
        if entry.get('signature')!=signature:raise RuntimeError('Task signature mismatch at '+str(i))
        all_rows.extend(entry['rows']);audits.extend(entry['audits'])
        checks.append({'geometry':i,'group':str(G[i]),'oracle_candidates':entry['oracle_candidates'],
                       'false_certificate':entry['false_certificate']})
    write_csv(root/'CP05_runtime_repetitions.csv',all_rows)
    write_csv(root/'CP06_oracle_audit.csv',checks)
    write_csv(root/'CP06_candidate_certificates.csv',audits)
    paired=[]
    for i in range(len(H)):
        rr=[r for r in all_rows if r['geometry']==i]
        card=float(np.median([r['runtime_ms'] for r in rr if r['mode']=='CARD']))
        new=float(np.median([r['runtime_ms'] for r in rr if r['mode']=='ADAPTIVE']))
        pol=next(r['executed_policy'] for r in rr if r['mode']=='ADAPTIVE')
        calls=float(np.mean([r['full_calls'] for r in rr if r['mode']=='CARD']))-float(np.mean([r['full_calls'] for r in rr if r['mode']=='ADAPTIVE']))
        paired.append({'geometry':i,'group':str(G[i]),'selected_policy':pol,
                       'card_ms':card,'adaptive_ms':new,'saved_ms':card-new,'calls_saved':calls})
    write_csv(root/'CP07_paired_geometry.csv',paired)
    save=[r['saved_ms'] for r in paired]
    ci=group_ci(save,[r['group'] for r in paired],a.bootstrap,a.seed+23)
    active=sum(r['selected_policy']!='CARD' for r in paired)
    false=sum(x['false_certificate'] for x in checks)
    decision={'status':'SMOKE_ONLY' if smoke else ('GO_CONDITIONAL_RUNTIME' if rule['policy']!='CARD' and ci[0] is not None and ci[0]>a.min_gain_ms and false==0 else 'STOP_NO_RUNTIME_GAIN'),
              'policy':rule,'n_geometries':len(H),'n_groups':len(set(map(str,G))),
              'activated_geometries':active,'activation_fraction':active/len(H),
              'mean_saved_ms':float(np.mean(save)),'median_saved_ms':float(np.median(save)),
              'ci95_saved_ms':ci,'mean_calls_saved':float(np.mean([r['calls_saved'] for r in paired])),
              'runtime_ratio':float(np.mean([r['card_ms'] for r in paired]))/max(1e-12,float(np.mean([r['adaptive_ms'] for r in paired]))),
              'oracle_mismatch':0,'false_certificate':false,
              'scope':'No claim of exactness outside finite codebook or runtime benefit without independent GO; group independence requires source-level validation'}
    jwrite(root/'CP08_decision.json',decision)
    hashrows=[{'file':p.name,'sha256':digest(p)} for p in sorted(root.glob('CP0*')) if p.name!='CP09_SHA256.csv']
    write_csv(root/'CP09_SHA256.csv',hashrows)
    print(json.dumps(decision,indent=2));return decision

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',required=True,choices=('profile','select','preflight','scan','report','all'))
    p.add_argument('--development',required=True);p.add_argument('--test',default='')
    p.add_argument('--development-provenance',default='');p.add_argument('--test-provenance',default='')
    p.add_argument('--run-id',required=True);p.add_argument('--out',default='outputs')
    p.add_argument('--q',type=float,default=2.960414);p.add_argument('--sigma-rel',type=float,default=.04)
    p.add_argument('--sinr-db',type=float,default=6.);p.add_argument('--pmax',type=float,default=1.)
    p.add_argument('--noise',type=float,default=2e-13);p.add_argument('--guard',type=float,default=1e-5)
    p.add_argument('--repeats',type=int,default=7);p.add_argument('--bootstrap',type=int,default=2000)
    p.add_argument('--min-gain-ms',type=float,default=.1);p.add_argument('--min-groups',type=int,default=20)
    p.add_argument('--seed',type=int,default=217);p.add_argument('--smoke',action='store_true')
    p.add_argument('--limit',type=int,default=0)
    p.add_argument('--lock-from',default='',help='Reuse an existing frozen CP03 rule for a second independent source')
    a=p.parse_args()
    if a.repeats<2 or a.bootstrap<100 or a.pmax<=0 or a.noise<=0 or a.guard<=0:raise ValueError('Bad parameters')
    if not a.smoke and a.limit:raise ValueError('--limit only allowed in smoke')
    root=run_path(a);create_and_check_manifest(a,root)
    H,G,_=load(a.development)
    if a.limit and a.stage in ('profile','select'):H,G=H[:a.limit],G[:a.limit]
    if not a.smoke and len(set(map(str,G)))<a.min_groups*2:raise ValueError('Need >= 2*min_groups distinct development groups')
    cfg=cfg_of(a)
    if a.stage in ('profile','all'):
        prof=[];candidate_costs=[]
        for i,h in enumerate(H):
            f=root/'profile_tasks'/f'{i:07d}.json'
            sig=sha_bytes(json.dumps({'devhash':digest(a.development),'geometry':i,'config':args_signature(a)},sort_keys=True).encode())
            if f.exists():row=read_or_raise(f);assert row['signature']==sig
            else:
                one,costs=profile_one(h,G[i],i,cfg,a.repeats,a.guard,a.smoke)
                row={'signature':sig,'complete':True,'data':one,'candidate_cost':costs}
                jwrite(f,row)
            prof.append(row['data']);candidate_costs.extend(row['candidate_cost'])
        write_csv(root/'CP01_development_profile.csv',prof)
        write_csv(root/'CP01_candidate_cost.csv',candidate_costs)
        if a.stage=='profile':print('Profile done',len(prof));return
    if a.stage in ('select','all'):
        if (root/'CP03_locked_rule.json').exists():raise RuntimeError('Already locked: new run-id required')
        profile= root/'CP01_development_profile.csv'
        if not profile.exists():raise RuntimeError('Run profile first')
        with profile.open(newline='',encoding='utf8') as f:rows=list(csv.DictReader(f))
        fitgroups,valgroups=keys_by_group([r['group'] for r in rows],a.seed)
        fit=[r for r in rows if r['group'] in fitgroups];val=[r for r in rows if r['group'] in valgroups]
        if not a.smoke and (len(fitgroups)<a.min_groups or len(valgroups)<a.min_groups//2):raise RuntimeError('Too few split groups')
        rules=build_rules(fit,max(1,int(.10*len(fit))))
        ranked=[]
        for idx,r in enumerate(rules):
            st=evaluate_rule(fit,r,a.bootstrap,a.seed)
            ranked.append({'rule_index':idx,'rule':r,**st})
        # ONE fit-selected rule, then ONE validation gate. No post-validation tuning.
        eligible=[r for r in ranked if r['rule']['policy']!='CARD' and r['activation_fraction']>=.10]
        winner=max(eligible,key=lambda x:(x['mean_saved_ms'], -x['rule_index'])) if eligible else ranked[0]
        hold=evaluate_rule(val,winner['rule'],a.bootstrap,a.seed+1)
        passed=(winner['rule']['policy']!='CARD' and hold['ci_lo'] is not None and hold['ci_lo']>a.min_gain_ms)
        chosen=winner['rule'] if passed else {'policy':'CARD','feature':'','threshold':0.,'direction':''}
        write_csv(root/'CP02_rule_search.csv',[{'rule_index':z['rule_index'],**z['rule'],
              **{k:v for k,v in z.items() if k not in ('rule','rule_index')}} for z in ranked])
        lock={'selected_rule':chosen,'candidate_rule':winner['rule'],'development_fit':winner,
              'development_validation':hold,'passed_gate':bool(passed),
              'development_sha256':digest(a.development),'profile_sha256':digest(profile),
              'group_counts':{'fit':len(fitgroups),'validation':len(valgroups)},
              'source_code_hashes':args_signature(a)['code_hashes'],'settings':args_signature(a),
              'note':'Rule and threshold locked before test; CARD if holdout fails'}
        jwrite(root/'CP03_locked_rule.json',lock)
        print('LOCKED',chosen,'holdout',hold)
        if a.stage=='select':return
    if a.stage in ('preflight','scan','report','all'):
        if a.lock_from and not (root/'CP03_locked_rule.json').exists():
            external=read_or_raise(Path(a.lock_from))
            if external['settings']!=args_signature(a) or external['development_sha256']!=digest(a.development):
                raise RuntimeError('External lock incompatible with code, settings or development data')
            jwrite(root/'CP03_locked_rule.json',external)
        lock=read_or_raise(root/'CP03_locked_rule.json')
        if lock['settings']!=args_signature(a) or lock['development_sha256']!=digest(a.development):raise RuntimeError('Lock mismatch')
        if not a.test:raise ValueError('Missing --test dataset')
        T,TG,_=load(a.test)
        if a.limit:T,TG=T[:a.limit],TG[:a.limit]
        prov=validate_provenance(a.test_provenance,not a.smoke)
        pre=preflight(a,root,lock,T,TG,prov)
        if a.stage=='preflight':print('PREFLIGHT OK',pre);return
        sig=sha_bytes(json.dumps({'lock':lock,'preflight':pre,'repeats':a.repeats},sort_keys=True).encode())
        rule=lock['selected_rule']
        if a.stage in ('scan','all'):
            for i,h in enumerate(T):
                task=root/'tasks'/f'{i:07d}.json'
                if task.exists():
                    d=read_or_raise(task)
                    if d.get('signature')!=sig or not d.get('complete'):raise RuntimeError('Bad checkpoint '+str(task))
                    continue
                out=single_repeated(h,TG[i],i,rule,cfg,a.guard,a.repeats,sig)
                jwrite(task,{'signature':sig,'complete':True,**out})
                if (i+1)%20==0:print('TEST',i+1,'/',len(T),flush=True)
        if a.stage in ('report','all'):finish(a,root,T,TG,sig,rule,a.smoke)

if __name__=='__main__':main()
