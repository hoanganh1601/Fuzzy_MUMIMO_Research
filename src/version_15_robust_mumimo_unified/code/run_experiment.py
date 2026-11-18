#!/usr/bin/env python3
"""V15: K=4/6/8 finite-codebook cost break-even experiment.

Physics and oracle: V14 robust_model.solve/get_beam; robust q fixed.
Screening: V14 early_bound/post_bound/build_Fu/from_comp.
No test-based selection; test run uses a cryptographically pinned development lock.
"""
import argparse, csv, hashlib, itertools, json, math, os, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np
from robust_model import solve, get_beam, digest, jwrite, cwrite
from certified_screening import build_Fu
from screening_policy import early_bound, post_bound, from_comp, group_ci

HERE=Path(__file__).resolve().parent
SOURCES=['run_experiment.py','robust_model.py','screening_policy.py','certified_screening.py','screening_bounds.py']
POLICIES=('CARD','EARLY','CACHED','HYBRID')
ALPHAS_DEFAULT=(0.,.001,.01,.05,.1,.3,1.)

def sha_text(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def raw_h(h):return hashlib.sha256(np.ascontiguousarray(h).tobytes()).hexdigest()
def load_any(path):
    with np.load(path,allow_pickle=False) as f:
        H=f['H'];G=f['groups'];meta={z:f[z].tolist() for z in ('scenario',) if z in f.files}
    if H.ndim!=3 or H.shape[0]!=len(G) or H.shape[1]<8 or H.shape[2]<8:raise ValueError('H must be complex (N,M,>=8), M>=8, with groups (N,)')
    if not np.iscomplexobj(H) or not np.isfinite(H).all():raise ValueError('H must be finite complex')
    if len(np.unique(G))<4:raise ValueError('Need >=4 distinct groups')
    return H,G,meta

def cfg(a):return {'q':a.q,'sigma':a.sigma_rel,'gamma':10**(a.sinr_db/10),'noise':a.noise,'pmax':a.pmax}
def configs(a):
    ks=sorted(set(int(v) for v in a.ks.split(',')))
    if any(k not in (4,6,8) for k in ks) or not ks:raise ValueError('K must be subset of 4,6,8')
    alphas=tuple(dict.fromkeys(float(v) for v in a.alphas.split(',')))
    if len(alphas)<max(a.beam_counts) or min(alphas)<0 or alphas[0]!=0.:raise ValueError('alpha-list must begin 0, >=max beam-count, >=0')
    if a.repeats<2 or a.bootstrap<100 or a.q<0 or a.sigma_rel<=0 or a.noise<=0 or a.pmax<=0 or a.guard<=0:raise ValueError('Invalid parameters')
    return [(k,l,alphas[:l]) for k in ks for l in a.beam_counts]

def channel_features(h,c):
    norms=np.sum(abs(h)**2,axis=0)
    v=h/np.maximum(np.linalg.norm(h,axis=0),1e-30)[None,:]
    cr=np.abs(v.conj().T@v);np.fill_diagonal(cr,0.)
    coherence=float(np.max(cr)) if len(h.T)>1 else 0.
    er=float(np.sum(c['gamma']*c['noise']/np.maximum(norms,1e-200))/c['pmax'])
    return {'coherence':coherence,'early_ratio':er,
            'difficulty':'high' if coherence>=.8 else ('medium' if coherence>=.4 else 'low')}

def key(k,l,d):return f'K{k}_L{l}_{d}'

def same_choice(x,y):
    if x is None or y is None:return x is None and y is None
    return (x['cardinality']==y['cardinality'] and x['subset']==y['subset'] and x['alpha']==y['alpha'] and
            abs(x['p_req_w']-y['p_req_w'])<=1e-7*max(1e-18,abs(x['p_req_w']),abs(y['p_req_w'])))

def search(h,alphas,c,policy,guard,profile=False):
    """Cardinality ordered exhaustive remaining candidates; all subset beams recomputed.
    Returns result, cost counters, optional visited candidate trace.
    """
    k=h.shape[1];met=defaultdict(float);trace=[]
    for size in range(k,0,-1):
        feasible=[]
        for subset in itertools.combinations(range(k),size):
            skip=False;early_t=0.;r_early=''
            if policy in ('EARLY','HYBRID'):
                st=time.perf_counter_ns();skip,r_early,unc,lb=early_bound(h,subset,c,guard);early_t=(time.perf_counter_ns()-st)/1e6
                met['early_ms']+=early_t;met['fail_open']+=int(unc)
            for alpha in alphas:
                met['candidates_seen']+=1
                if skip:
                    met['early_rejects']+=1
                    if profile:trace.append({'subset':''.join(map(str,subset)),'alpha':alpha,'reject_stage':'prebeam','solve_ms':0.,'screen_ms':early_t/len(alphas),'reason':r_early})
                    continue
                post_ms=0.;beam_ms=0.;solver_ms=0.;reason=''
                if policy in ('CACHED','HYBRID'):
                    st=time.perf_counter_ns();comp=build_Fu(h,subset,alpha,c);beam_ms=(time.perf_counter_ns()-st)/1e6
                    met['beam_ms']+=beam_ms
                    st=time.perf_counter_ns();drop,reason,unc=post_bound(comp,c,guard);post_ms=(time.perf_counter_ns()-st)/1e6
                    met['screen_ms']+=post_ms;met['fail_open']+=int(unc)
                    if drop:
                        met['post_rejects']+=1
                        if profile:trace.append({'subset':''.join(map(str,subset)),'alpha':alpha,'reject_stage':'postbeam','solve_ms':0.,'screen_ms':post_ms,'reason':reason})
                        continue
                    st=time.perf_counter_ns();r=from_comp(comp,c);solver_ms=(time.perf_counter_ns()-st)/1e6
                else:
                    st=time.perf_counter_ns();r=solve(h,list(subset),alpha,c);solver_ms=(time.perf_counter_ns()-st)/1e6
                met['solve_ms']+=solver_ms;met['full_calls']+=1
                if profile:trace.append({'subset':''.join(map(str,subset)),'alpha':alpha,'reject_stage':'none','solve_ms':solver_ms,'screen_ms':post_ms,'reason':r['status']})
                if r['status']=='FEASIBLE':feasible.append({'subset':''.join(map(str,subset)),'alpha':alpha,'cardinality':size,'p_req_w':float(r['p_req_w'])})
        if feasible:return min(feasible,key=lambda r:(r['p_req_w'],r['alpha'],r['subset'])),dict(met),trace
    return None,dict(met),trace

def independent_oracle(h,alphas,c):
    """Independent all-subsets/all-beams reference; never uses screening decisions."""
    k=h.shape[1];winners=[];ncandidates=0
    for size in range(1,k+1):
        for subset in itertools.combinations(range(k),size):
            for alpha in alphas:
                ncandidates+=1
                r=solve(h,list(subset),alpha,c)
                if r['status']=='FEASIBLE':
                    winners.append({'subset':''.join(map(str,subset)),'alpha':alpha,'cardinality':size,'p_req_w':float(r['p_req_w'])})
    return min(winners,key=lambda r:(-r['cardinality'],r['p_req_w'],r['alpha'],r['subset'])) if winners else None,ncandidates

def process_one(h,group,geometry,k,l,alphas,c,guard,repeats,seed,profile):
    h=h[:,:k];st_feature=time.perf_counter_ns();z=channel_features(h,c)
    feature_ms=(time.perf_counter_ns()-st_feature)/1e6
    rows=[];traces=[]
    # Independent exhaustive oracle: visits every subset and candidate.
    oracle,n_oracle=independent_oracle(h,alphas,c)
    for rep in range(repeats):
        order=list(POLICIES);np.random.default_rng(seed+geometry*71+rep*131+k*37+l).shuffle(order)
        for pol in order:
            st=time.perf_counter_ns();x,met,trace=search(h,alphas,c,pol,guard,profile=profile and rep==0)
            ms=(time.perf_counter_ns()-st)/1e6
            if not same_choice(x,oracle):raise AssertionError(f'Oracle mismatch geometry={geometry}, K={k}, L={l}, policy={pol}')
            rows.append({'geometry':geometry,'group':str(group),'K':k,'L':l,'difficulty':z['difficulty'],
                'coherence':z['coherence'],'early_ratio':z['early_ratio'],'feature_ms':feature_ms,
                'oracle_candidates':n_oracle,'rep':rep,'policy':pol,
                'runtime_ms':ms,'calls':met.get('full_calls',0),'candidates_seen':met.get('candidates_seen',0),
                'early_rejects':met.get('early_rejects',0),'post_rejects':met.get('post_rejects',0),
                'early_ms':met.get('early_ms',0.),'beam_ms':met.get('beam_ms',0.),
                'screen_ms':met.get('screen_ms',0.),'solve_ms':met.get('solve_ms',0.),
                'oracle_match':1,'served':oracle['cardinality'] if oracle else 0})
            if profile and rep==0:
                for t in trace:traces.append({'geometry':geometry,'group':str(group),'K':k,'L':l,'policy':pol,**t})
    if profile:
        # Full candidate-level diagnostic, independent of cardinality-stop. Never used to choose rules on test.
        for size in range(k,0,-1):
            for sub in itertools.combinations(range(k),size):
                st=time.perf_counter_ns();early_drop,early_why,_,_=early_bound(h,sub,c,guard);early_ms=(time.perf_counter_ns()-st)/1e6
                for alpha in alphas:
                    st=time.perf_counter_ns();r=solve(h,list(sub),alpha,c);solver_ms=(time.perf_counter_ns()-st)/1e6
                    st=time.perf_counter_ns();comp=build_Fu(h,sub,alpha,c);beam_ms=(time.perf_counter_ns()-st)/1e6
                    st=time.perf_counter_ns();post_drop,post_why,_=post_bound(comp,c,guard);post_ms=(time.perf_counter_ns()-st)/1e6
                    if r['status']=='FEASIBLE' and (early_drop or post_drop):raise AssertionError('False certificate in full candidate profiling')
                    traces.append({'geometry':geometry,'group':str(group),'K':k,'L':l,'policy':'CANDIDATE_ORACLE',
                        'subset':''.join(map(str,sub)),'alpha':alpha,'oracle_status':r['status'],
                        'reject_stage':'early' if early_drop else ('post' if post_drop else 'none'),
                        'reason':early_why if early_drop else post_why,'early_screen_ms':early_ms,
                        'beam_ms':beam_ms,'post_screen_ms':post_ms,'solve_ms':solver_ms,
                        'conditional_saved_ms':solver_ms-(early_ms+beam_ms+post_ms) if (early_drop or post_drop) else -(early_ms+beam_ms+post_ms),
                        'false_reject':0})
    return rows,traces

def write_rows(path,rows):
    if not rows:raise ValueError('Empty output: '+str(path))
    headers=list(dict.fromkeys(k for row in rows for k in row.keys()))
    cwrite(path,rows,headers)

def summary_from_rows(rows):
    by=defaultdict(list)
    for r in rows:by[(r['geometry'],r['K'],r['L'])].append(r)
    out=[]
    for (geom,k,l),rr in sorted(by.items()):
        base=float(np.median([r['runtime_ms'] for r in rr if r['policy']=='CARD']))
        z=rr[0]
        for pol in POLICIES[1:]:
            pp=[r for r in rr if r['policy']==pol]
            val=float(np.median([r['runtime_ms'] for r in pp]))
            out.append({'geometry':geom,'group':z['group'],'K':k,'L':l,'difficulty':z['difficulty'],
                'coherence':z['coherence'],'policy':pol,'card_ms':base,'policy_ms':val,
                'feature_ms':float(z['feature_ms']),'saving_ms':base-val-float(z['feature_ms']),'calls_saved':next(v['calls'] for v in rr if v['policy']=='CARD')-pp[0]['calls'],
                'active':1})
    return out

def split_groups(G,seed):
    groups=sorted(set(map(str,G)));np.random.default_rng(seed).shuffle(groups)
    n=max(1,int(.6*len(groups)))
    return set(groups[:n]),set(groups[n:])

def group_boot(rows,boot,seed):
    if len(set(r['group'] for r in rows))<3:return (None,None)
    return group_ci([r['saving_ms'] for r in rows],[r['group'] for r in rows],boot,seed=seed)

def choose_policy(per_geometry,train_groups,valid_groups,boot,min_gain,min_cell):
    """Select a CELL policy only when validation passes. All other cells remain CARD.
    No tuning on test. Reports optimistic fit and independent confirmation.
    """
    cells=sorted(set((r['K'],r['L'],r['difficulty']) for r in per_geometry))
    decisions=[];lock={}
    for k,l,d in cells:
        rr=[r for r in per_geometry if (r['K'],r['L'],r['difficulty'])==(k,l,d)]
        fit=[r for r in rr if r['group'] in train_groups]
        valid=[r for r in rr if r['group'] in valid_groups]
        names=sorted(set(r['group'] for r in fit));vnames=sorted(set(r['group'] for r in valid))
        fits=[]
        for pol in POLICIES[1:]:
            samples=[r for r in fit if r['policy']==pol]
            mean=float(np.mean([r['saving_ms'] for r in samples])) if samples else -1e100
            fits.append((mean,pol))
        best=max(fits) if fits else (-1e100,'CARD')
        p=best[1] if best[0]>0 else 'CARD'
        vs=[r for r in valid if r['policy']==p]
        ci=group_boot(vs,boot,1+k*17+l*3) if p!='CARD' else (None,None)
        accepted=(p!='CARD' and len(names)>=min_cell and len(vnames)>=min_cell and ci[0] is not None and ci[0]>min_gain)
        lock[key(k,l,d)]=p if accepted else 'CARD'
        decisions.append({'K':k,'L':l,'difficulty':d,'fit_groups':len(names),'valid_groups':len(vnames),
          'fit_best_policy':p,'fit_best_saved_ms':best[0],'valid_saved_ms':float(np.mean([r['saving_ms'] for r in vs])) if vs else '',
          'valid_ci_lo':ci[0],'valid_ci_hi':ci[1],'accepted':int(accepted),'locked_policy':lock[key(k,l,d)]})
    return lock,decisions

def policy_results(paired,lock,boot,seed,min_gain):
    rows=[]
    grouped=defaultdict(list)
    for r in paired:grouped[(r['geometry'],r['K'],r['L'])].append(r)
    for (g,k,l),rs in grouped.items():
        r=rs[0];pol=lock.get(key(k,l,r['difficulty']),'CARD')
        match=next((x for x in rs if x['policy']==pol),None)
        rows.append({'geometry':g,'group':r['group'],'K':k,'L':l,'difficulty':r['difficulty'],
          'selected_policy':pol,'saved_ms':match['saving_ms'] if match else 0.,
          'calls_saved':match['calls_saved'] if match else 0.,'card_ms':r['card_ms'],
          'selected_ms':match['policy_ms']+match['feature_ms'] if match else r['card_ms']})
    aggregate=[]
    for k,l in sorted(set((r['K'],r['L']) for r in rows)):
        rr=[r for r in rows if r['K']==k and r['L']==l]
        ci=group_ci([r['saved_ms'] for r in rr],[r['group'] for r in rr],boot,seed+100*k+l)
        aggregate.append({'K':k,'L':l,'geometries':len(rr),'groups':len(set(r['group'] for r in rr)),
          'mean_saved_ms':float(np.mean([r['saved_ms'] for r in rr])),
          'ci_lo':ci[0],'ci_hi':ci[1],'mean_calls_saved':float(np.mean([r['calls_saved'] for r in rr])),
          'activated_fraction':float(np.mean([r['selected_policy']!='CARD' for r in rr])),
          'pass_runtime':int(ci[0] is not None and ci[0]>min_gain)})
    return rows,aggregate

def config_signature(a):
    return {'q':a.q,'sigma_rel':a.sigma_rel,'sinr_db':a.sinr_db,'noise':a.noise,'pmax':a.pmax,
      'ks':a.ks,'alphas':a.alphas,'beam_counts':a.beam_counts,'guard':a.guard,'repeats':a.repeats,
      'bootstrap':a.bootstrap,'min_gain_ms':a.min_gain_ms,'min_cell_groups':a.min_cell_groups,
      'smoke':a.smoke,'limit':a.limit,'profile_candidates':a.profile_candidates,
      'seed':a.seed,'dev_hash':digest(a.development),
      'code_hashes':{n:digest(HERE/n) for n in SOURCES}}

def task_signature(manifest,phase,source_hash):return sha_text({'manifest':manifest['signature'],'phase':phase,'source_hash':source_hash})

def run_tasks(a,root,phase,H,G,config,source_hash):
    tdir=root/'tasks'/phase;tdir.mkdir(parents=True,exist_ok=True)
    tsig=task_signature(config,phase,source_hash)
    rows=[];traces=[]
    for i in range(len(H)):
        p=tdir/f'{i:07d}.json'
        if p.exists():
            entry=json.loads(p.read_text())
            if entry.get('signature')!=tsig:raise RuntimeError('Checkpoint mismatch at '+str(p))
        else:
            rr=[];tt=[]
            for k,l,alphas in configs(a):
                rx,tx=process_one(H[i],G[i],i,k,l,alphas,cfg(a),a.guard,a.repeats,a.seed,a.profile_candidates)
                rr.extend(rx);tt.extend(tx)
            entry={'signature':tsig,'complete':True,'rows':rr,'traces':tt}
            jwrite(p,entry)
        if not entry.get('complete'):raise RuntimeError('Incomplete task '+str(p))
        rows.extend(entry['rows']);traces.extend(entry['traces'])
    return rows,traces

def provenance(path,smoke):
    if not path:
        if smoke:return {'source':'synthetic','scenario':'smoke','prior_use':'smoke'}
        raise ValueError('Official run requires provenance JSON')
    d=json.loads(Path(path).read_text())
    for n in ('source','scenario','group_definition','independence_basis','prior_use'):
        if not d.get(n):raise ValueError('Missing provenance '+n)
    return d

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=('preflight','develop','lock','test','report','all'),required=True)
    p.add_argument('--development',required=True);p.add_argument('--test',default='')
    p.add_argument('--dev-provenance',default='');p.add_argument('--test-provenance',default='')
    p.add_argument('--run-id',required=True);p.add_argument('--out-root',default='outputs')
    p.add_argument('--ks',default='4,6,8');p.add_argument('--alphas',default='0,0.001,0.01,0.05,0.1,0.3,1')
    p.add_argument('--beam-counts',default='3,5,7')
    p.add_argument('--q',type=float,default=2.960414);p.add_argument('--sigma-rel',type=float,default=.04)
    p.add_argument('--sinr-db',type=float,default=6.);p.add_argument('--noise',type=float,default=2e-13)
    p.add_argument('--pmax',type=float,default=1.);p.add_argument('--guard',type=float,default=1e-5)
    p.add_argument('--repeats',type=int,default=5);p.add_argument('--bootstrap',type=int,default=1000)
    p.add_argument('--min-gain-ms',type=float,default=.1);p.add_argument('--min-cell-groups',type=int,default=5)
    p.add_argument('--seed',type=int,default=20261117);p.add_argument('--smoke',action='store_true');p.add_argument('--lock-from',default='')
    p.add_argument('--limit',type=int,default=0);p.add_argument('--profile-candidates',action='store_true')
    a=p.parse_args();a.beam_counts=tuple(int(v) for v in a.beam_counts.split(','));configs(a)
    if not a.smoke and a.min_gain_ms<0:raise ValueError('min-gain must be nonnegative')
    H,G,meta=load_any(a.development)
    if a.limit:
        if not a.smoke:raise ValueError('--limit only for smoke')
        H,G=H[:a.limit],G[:a.limit]
    devp=provenance(a.dev_provenance,a.smoke)
    root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    sign=config_signature(a);manifest={'signature':sha_text(sign),'settings':sign,
      'source':devp,'development_n':len(H),'development_groups':len(set(map(str,G))),'scope':'development only'}
    manifest=json.loads(json.dumps(manifest,ensure_ascii=False))
    mp=root/'CP00_manifest.json'
    if mp.exists():
        if json.loads(mp.read_text())!=manifest:raise RuntimeError('Configuration changed; use a new run-id')
    else:jwrite(mp,manifest)
    if a.stage=='preflight':
        print(json.dumps({'stage':'preflight','n_dev':len(H),'n_groups':len(set(map(str,G))),
          'configs':[(k,l) for k,l,_ in configs(a)],'candidates_per_geometry':{f'K{k}_L{l}':l*(2**k-1) for k,l,_ in configs(a)}},indent=2));return
    if a.stage in ('develop','all'):
        dr,trace=run_tasks(a,root,'development',H,G,manifest,digest(a.development))
        write_rows(root/'CP01_development_repeats.csv',dr)
        if trace:write_rows(root/'CP01_candidate_cost.csv',trace)
        paired=summary_from_rows(dr);write_rows(root/'CP02_development_paired.csv',paired)
    if a.stage in ('lock','all'):
        lockfile=root/'CP03_locked_cells.json'
        if lockfile.exists():raise RuntimeError('Already locked: refuse retraining')
        if a.lock_from:raise RuntimeError('Cannot retrain when --lock-from is supplied')
        pth=root/'CP02_development_paired.csv'
        if not pth.exists():raise RuntimeError('Run --stage develop')
        with pth.open() as f: rows=list(csv.DictReader(f))
        for r in rows:
            for x in ('geometry','K','L'):r[x]=int(r[x])
            for x in ('saving_ms','calls_saved','coherence','card_ms','policy_ms','feature_ms'):r[x]=float(r[x])
        fit,valid=split_groups(G,a.seed)
        policies,details=choose_policy(rows,fit,valid,a.bootstrap,a.min_gain_ms,a.min_cell_groups)
        write_rows(root/'CP03_cell_validation.csv',details)
        lock={'policy_cells':policies,'config_signature':manifest['signature'],
              'development_sha256':digest(a.development),'fit_groups':sorted(fit),'valid_groups':sorted(valid),
              'min_gain_ms':a.min_gain_ms,'conditioned_on':'K,L,coherence_bin; no test tuning'}
        jwrite(lockfile,lock)
    if a.stage in ('test','all'):
        lockfile=root/'CP03_locked_cells.json'
        if not lockfile.exists() and a.lock_from:
            imported=json.loads(Path(a.lock_from).read_text(encoding='utf8'))
            if imported['config_signature']!=manifest['signature']:
                raise RuntimeError('External lock and development/configuration hashes differ')
            jwrite(lockfile,imported)
        if not lockfile.exists():raise RuntimeError('Must freeze before test')
        lock=json.loads(lockfile.read_text())
        if lock['config_signature']!=manifest['signature']:raise RuntimeError('Frozen signature mismatch')
        if not a.test:raise ValueError('Need test dataset')
        TH,TG,_=load_any(a.test)
        if a.limit:
            TH,TG=TH[:a.limit],TG[:a.limit]
        tp=provenance(a.test_provenance,a.smoke)
        if not a.smoke and tp['prior_use'] not in ('never_seen','sealed_before_development'):raise ValueError('Test is not sealed')
        if not a.smoke and len(set(map(str,TG)))<10:raise ValueError('At least ten independent-source test groups required for official exploratory claim')
        if not a.smoke and len(set(map(str,G)))<20:raise ValueError('At least twenty development groups required')
        if digest(a.development)==digest(a.test):raise RuntimeError('Same development and test file')
        if set(map(str,G))&set(map(str,TG)):raise RuntimeError('Overlapping group labels')
        if {raw_h(x) for x in H}&{raw_h(x) for x in TH}:raise RuntimeError('Duplicate channels')
        pre={'test_sha256':digest(a.test),'source':tp,'test_n':len(TH),'test_groups':len(set(map(str,TG))),
          'group_overlap':0,'exact_channel_overlap':0,'statistical_independence_requires_source_audit':True}
        pp=root/'CP04_test_preflight.json'
        if pp.exists() and json.loads(pp.read_text())!=pre:raise RuntimeError('Test changed; use new run-id')
        if not pp.exists():jwrite(pp,pre)
        tr,trace=run_tasks(a,root,'test',TH,TG,manifest,digest(a.test))
        write_rows(root/'CP05_test_repeats.csv',tr)
        if trace:write_rows(root/'CP05_candidate_cost.csv',trace)
        paired=summary_from_rows(tr)
        write_rows(root/'CP06_test_paired_all_policies.csv',paired)
        selected,agg=policy_results(paired,lock['policy_cells'],a.bootstrap,a.seed,a.min_gain_ms)
        write_rows(root/'CP07_frozen_policy_geometry.csv',selected)
        write_rows(root/'CP07_break_even_summary.csv',agg)
        # Frozen policy is scored by K,L, across all difficulty cells, not cherry-picked groups.
        nviol=sum(1 for r in tr if r['oracle_match']!=1)
        status='SMOKE_ONLY' if a.smoke else ('GO_RUNTIME_CONFIRMED' if nviol==0 and all(x['pass_runtime'] for x in agg) and any(x['activated_fraction']>0 for x in agg) else 'STOP_NO_GENERAL_RUNTIME_GAIN')
        decision={'status':status,'oracle_mismatch':nviol,'test_source':tp,'per_config':agg,
          'interpretation':'GO requires each predeclared K,L configuration to improve; no selection from test',
          'source_validation':'3GPP must be run as separate untouched test with same frozen lock'}
        jwrite(root/'CP08_decision.json',decision)
    if a.stage in ('report','all'):
        files=sorted([p for p in root.glob('CP*') if p.is_file() and p.name!='CP09_SHA256.csv'] + list((root/'tasks').rglob('*.json')))
        write_rows(root/'CP09_SHA256.csv',[{'file':str(p.relative_to(root)),'sha256':digest(p)} for p in files]);print('REPORT',root)
    if a.stage not in ('report','preflight'):print('STAGE',a.stage,'OK',root)
if __name__=='__main__':main()
