#!/usr/bin/env python3
"""Conservative, resumable K=4 certificate ablation and numerical audit.

Scope: finite ZF/RZF beam family, fixed CSI margin; no statistical outage guarantee.
Important: reference exhaustive never enters pruning decisions.
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import time
from collections import Counter
from pathlib import Path

import mpmath as mp
import numpy as np
from reference_model import (load, get_beam, solve, exhaustive, oracle,
                             digest, jwrite, cwrite)
from ablation_audit import RULES, screening, same

BASE_VARIANTS = [('ALL', set(RULES)), ('CARDINALITY_ONLY', set())] + [
    ('WITHOUT_' + rule, set(RULES) - {rule}) for rule in RULES
]


def all_candidates(k=4):
    for size in range(k, 0, -1):
        for subset in itertools.combinations(range(k), size):
            yield size, subset


def build_Fu(h, subset, alpha, cfg):
    """Recompute model coefficients; independent of exhaustive decision."""
    hs = h[:, list(subset)]
    beam = get_beam(hs, alpha)
    if beam is None:
        return None
    norms = np.linalg.norm(hs, axis=0)
    radius = cfg['q'] * cfg['sigma'] * norms / math.sqrt(hs.shape[0])
    g = np.abs(hs.conj().T @ beam)
    a = np.maximum(np.diag(g) - radius, 0.0)**2
    if np.any(a <= 0):
        return dict(zero=True, norms=norms, radius=radius, a=a)
    F = cfg['gamma'] * (g + radius[:, None])**2 / a[:, None]
    np.fill_diagonal(F, 0.0)
    u = cfg['gamma'] * cfg['noise'] / a
    return dict(zero=False, F=F, u=u, norms=norms, radius=radius, a=a)


def high_precision_recheck(h, subset, alpha, cfg, rule, dps=70):
    """Recompute inequality in arbitrary precision from derived double beam/CSI.

    This mitigates reduction-rounding, but is not a formal interval certificate of
    the channel estimate or beam-generation floating-point errors.
    """
    comp = build_Fu(h, subset, alpha, cfg)
    if comp is None:
        return dict(checked=False, mp_value=None, rationale='beam_undefined')
    mp.mp.dps = dps
    D = lambda x: mp.mpf(str(float(x)))
    pmax = D(cfg['pmax']); gamma = D(cfg['gamma']); noise = D(cfg['noise'])
    norms = [D(x) for x in comp['norms']]
    radius = [D(x) for x in comp['radius']]
    if rule == 'NORM_NOISE_LOWER_BOUND':
        den = [max(mp.mpf(0), n-r)**2 for n,r in zip(norms, radius)]
        val = mp.inf if any(x <= 0 for x in den) else sum(gamma*noise/x for x in den)
        return dict(checked=True, mp_value=str(val), mp_excess=str(val-pmax), criterion='power')
    if rule == 'ZERO_ROBUST_GAIN':
        return dict(checked=True, mp_value=str(min(D(v) for v in comp['a'])), criterion='zero_gain')
    if comp.get('zero'):
        return dict(checked=False, mp_value=None, rationale='zero_gain')
    F = [[D(v) for v in row] for row in comp['F']]
    u = [D(v) for v in comp['u']]
    if rule == 'NOISE_LOWER_BOUND':
        val = sum(u)
    elif rule == 'NEUMANN_LOWER_BOUND':
        term = list(u); partial = list(u)
        for _ in range(4):
            term = [sum(F[i][j] * term[j] for j in range(len(term))) for i in range(len(term))]
            partial = [partial[i] + term[i] for i in range(len(term))]
        val = sum(partial)
    elif rule == 'TWO_CYCLE_COUPLING':
        val = max((F[i][j]*F[j][i] for i in range(len(u))
                   for j in range(i+1, len(u))), default=mp.mpf(0))
        return dict(checked=True, mp_value=str(val), mp_excess=str(val-1), criterion='cycle')
    else:
        return dict(checked=False, mp_value=None, rationale='unsupported')
    return dict(checked=True, mp_value=str(val), mp_excess=str(val-pmax), criterion='power')


def robust_screen(h, subset, alpha, cfg, enabled, guard):
    skip, reason, bound, slack = screening(h, subset, alpha, cfg, enabled)
    record = dict(reason=reason, bound=bound if math.isfinite(bound) else None,
                  relative_slack=slack if math.isfinite(slack) else None,
                  near_threshold=False, fail_open=False, mp_checked=False,
                  mp_value='', mp_excess='', mp_criterion='')
    if not skip:
        return False, record
    # Near threshold: use high precision to document, but DO NOT prune. This is
    # conservative even if the high precision recomputation suggests infeasible.
    near = (math.isfinite(slack) and abs(slack) <= guard)
    if reason in ('ZERO_ROBUST_GAIN', 'NORM_NOISE_LOWER_BOUND') and not math.isfinite(bound):
        comp = build_Fu(h, subset, alpha, cfg)
        if comp is not None:
            margins = np.asarray(comp['norms']) - np.asarray(comp['radius'])
            if reason == 'ZERO_ROBUST_GAIN':
                hs = h[:, list(subset)]; W = get_beam(hs, alpha)
                if W is not None:
                    diag = np.abs(np.diag(hs.conj().T @ W))
                    margins = diag - np.asarray(comp['radius'])
            relative = float(np.min(np.abs(margins) / np.maximum(comp['norms'], 1e-30)))
            near = relative <= guard
    if near:
        record['near_threshold'] = True
        record['fail_open'] = True
        mp_result = high_precision_recheck(h, subset, alpha, cfg, reason)
        record['mp_checked'] = bool(mp_result.get('checked'))
        record['mp_value'] = str(mp_result.get('mp_value', ''))
        record['mp_excess'] = str(mp_result.get('mp_excess', ''))
        record['mp_criterion'] = str(mp_result.get('criterion', ''))
        return False, record
    return True, record


def selection(h, alphas, cfg, enabled, guard):
    solves=0; checked=0; cert=0; cardinality=0; near=0; by_rule=Counter()
    best=None; first_card=None; screening_ms=0.0; solver_ms=0.0
    for size in range(4,0,-1):
        winners=[]
        for _, subset in (x for x in all_candidates() if x[0] == size):
            for alpha in alphas:
                checked+=1
                t=time.perf_counter()
                prune, rec=robust_screen(h,subset,alpha,cfg,enabled,guard)
                screening_ms+=(time.perf_counter()-t)*1000
                if rec['fail_open']: near+=1
                if prune:
                    cert+=1;by_rule[rec['reason']]+=1
                    continue
                t=time.perf_counter()
                result=solve(h,list(subset),alpha,cfg)
                solver_ms+=(time.perf_counter()-t)*1000
                solves+=1
                if result['status']=='FEASIBLE':
                    winners.append(dict(subset=''.join(map(str,subset)),cardinality=size,alpha=alpha,**result))
        if winners:
            best=min(winners,key=lambda x:(x['p_req_w'],x['alpha'],x['subset']))
            first_card=size
            cardinality=sum(1 for sz,sub in all_candidates() if sz<size)*len(alphas)
            break
    return best,dict(full_solves=solves,screened=checked,
                     certificate_pruned=cert,cardinality_skipped=cardinality,
                     near_threshold_fail_open=near,screening_ms=screening_ms,
                     solver_ms=solver_ms,**{rule:by_rule[rule] for rule in RULES})


def process_geometry(i,h,group,alphas,cfg,signature,guard):
    t=time.perf_counter(); oracle_rows=exhaustive(h,alphas,cfg)
    oracle_ms=1000*(time.perf_counter()-t)
    ref=oracle(oracle_rows)
    reference={(r['subset'],float(r['alpha'])):r for r in oracle_rows}
    ablations=[]
    for variant, enabled in BASE_VARIANTS:
        start=time.perf_counter()
        choice, stats=selection(h,alphas,cfg,enabled,guard)
        runtime_ms=(time.perf_counter()-start)*1000
        if not same(choice,ref):
            raise AssertionError(f'MISMATCH geometry={i} variant={variant} oracle={ref} selected={choice}')
        ablations.append(dict(geometry=i,group=str(group),variant=variant,exact_match=1,
                              runtime_ms=runtime_ms,**stats))
    cert_rows=[]
    for size,subset in all_candidates():
        subset_id=''.join(map(str,subset))
        for alpha in alphas:
            skip,rec=robust_screen(h,subset,alpha,cfg,set(RULES),guard)
            # Record *all* candidate screening decisions to audit fail-open paths.
            truth=reference[(subset_id,float(alpha))]
            false_prune=int(skip and truth['status']=='FEASIBLE')
            if false_prune:
                raise AssertionError(f'FALSE_PRUNE geometry={i} subset={subset_id} alpha={alpha}')
            cert_rows.append(dict(geometry=i,group=str(group),subset=subset_id,alpha=alpha,
                                  decision='PRUNED' if skip else ('FAIL_OPEN' if rec['fail_open'] else 'SURVIVOR'),
                                  reference_status=truth['status'],false_prune=false_prune,**rec))
    return dict(signature=signature,complete=True,geometry=i,group=str(group),
                ablations=ablations,certificates=cert_rows,
                exhaustive_ms=oracle_ms,
                oracle=dict(cardinality=ref['cardinality'],subset=ref['subset'],
                            alpha=ref['alpha'],power_w=ref['p_req_w']) if ref else None)


def signfile(p):
    return digest(p)


def bootstrap_ci(values,group_ids,seed=1729,n_boot=2000):
    # Paired cluster bootstrap; group count and validity explicitly reported.
    groups=sorted(set(group_ids)); bygroup={g:[] for g in groups}
    for val,g in zip(values,group_ids): bygroup[g].append(float(val))
    if len(groups)<3:return dict(lo=None,hi=None,n_groups=len(groups),note='too_few_groups')
    rng=np.random.default_rng(seed)
    stats=[]
    for _ in range(n_boot):
        sample=rng.choice(len(groups),size=len(groups),replace=True)
        stats.append(np.mean([v for idx in sample for v in bygroup[groups[int(idx)]]]))
    return dict(lo=float(np.quantile(stats,.025)),hi=float(np.quantile(stats,.975)),n_groups=len(groups),note='cluster_bootstrap_descriptive')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True,choices=['preflight','scan','report','all'])
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--out-root',default='outputs')
    parser.add_argument('--limit',type=int,default=0)
    parser.add_argument('--q',type=float,default=2.960414)
    parser.add_argument('--sigma-rel',type=float,default=.04)
    parser.add_argument('--sinr-db',type=float,default=6.)
    parser.add_argument('--noise',type=float,default=2e-13)
    parser.add_argument('--pmax',type=float,default=1.)
    parser.add_argument('--alpha-list',default='0,0.001,0.01,0.05,0.1,0.3,1')
    parser.add_argument('--numeric-guard',type=float,default=1e-5)
    parser.add_argument('--bootstrap',type=int,default=2000)
    a=parser.parse_args()
    H,groups,meta=load(a.dataset)
    N=len(H) if a.limit<=0 else min(a.limit,len(H))
    alphas=sorted(set(float(x) for x in a.alpha_list.split(',')))
    if not alphas or not all(math.isfinite(x) and x>=0 for x in alphas):raise ValueError('alpha list invalid')
    if not (a.q>=0 and a.sigma_rel>0 and a.noise>0 and a.pmax>0 and a.numeric_guard>0 and a.bootstrap>=100):raise ValueError('invalid parameters')
    cfg=dict(q=a.q,sigma=a.sigma_rel,gamma=10**(a.sinr_db/10),noise=a.noise,pmax=a.pmax)
    keys={k:v for k,v in vars(a).items() if k not in ('stage','run_id','out_root')}
    keys.update(dataset_sha=signfile(a.dataset),
                code_sha=signfile(__file__),
                model_sha=signfile(Path(__file__).with_name('reference_model.py')),
                legacy_rules_sha=signfile(Path(__file__).with_name('ablation_audit.py')),
                numpy_version=np.__version__)
    signature=hashlib.sha256(json.dumps(keys,sort_keys=True).encode()).hexdigest()
    root=Path(a.out_root)/a.run_id
    root.mkdir(parents=True,exist_ok=True)
    manifest=root/'CP00_manifest.json'
    if manifest.exists():
        old=json.loads(manifest.read_text(encoding='utf8'))
        if old['signature']!=signature:raise RuntimeError('signature mismatch: new run-id required')
    else:
        jwrite(manifest,dict(signature=signature,config=keys,geometry_count=N,group_count=len(set(map(str,groups[:N]))),
                             n_candidates_per_geometry=15*len(alphas),
                             caveat='Groups are labels, not proof of independent propagation samples.'))
    if a.stage=='preflight':
        print(f'PREFLIGHT PASS: {N} geometries, {len(set(map(str,groups[:N])))} groups, {len(alphas)} beam options')
        return
    if a.stage in ('scan','all'):
        for i in range(N):
            file=root/'tasks'/f'{i:07d}.json'
            if file.exists():
                try: t=json.loads(file.read_text(encoding='utf8'))
                except Exception as exc:raise RuntimeError('Invalid existing task; manual audit required: '+str(file)) from exc
                if t.get('signature')==signature and t.get('complete') and t.get('geometry')==i:continue
                raise RuntimeError('Invalid checkpoint: '+str(file))
            t=process_geometry(i,H[i],groups[i],alphas,cfg,signature,a.numeric_guard)
            jwrite(file,t)
            if (i+1)%10==0:print('completed',i+1,'/',N,flush=True)
    if a.stage in ('report','all'):
        tasks=[]
        for i in range(N):
            file=root/'tasks'/f'{i:07d}.json'
            if not file.exists():raise RuntimeError('incomplete: '+str(file))
            t=json.loads(file.read_text(encoding='utf8'))
            if t.get('signature')!=signature or not t.get('complete') or t.get('geometry')!=i:raise RuntimeError('bad checkpoint')
            tasks.append(t)
        abl=[x for t in tasks for x in t['ablations']]
        cr=[x for t in tasks for x in t['certificates']]
        cwrite(root/'CP01_ablation_geometry.csv',abl,list(abl[0]))
        cwrite(root/'CP02_all_candidate_audit.csv',cr,list(cr[0]))
        sums=[]
        for name,_ in BASE_VARIANTS:
            rows=[r for r in abl if r['variant']==name]
            sums.append(dict(variant=name,n_geometries=N,exact_matches=sum(r['exact_match'] for r in rows),
                             mean_full_solves=float(np.mean([r['full_solves'] for r in rows])),
                             mean_certificate_pruned=float(np.mean([r['certificate_pruned'] for r in rows])),
                             mean_cardinality_skipped=float(np.mean([r['cardinality_skipped'] for r in rows])),
                             mean_fail_open=float(np.mean([r['near_threshold_fail_open'] for r in rows])),
                             mean_runtime_ms=float(np.mean([r['runtime_ms'] for r in rows])),
                             mean_screening_ms=float(np.mean([r['screening_ms'] for r in rows])),
                             mean_solver_ms=float(np.mean([r['solver_ms'] for r in rows]))))
        cwrite(root/'CP03_ablation_summary.csv',sums,list(sums[0]))
        numerical=[]
        for rule in RULES:
            rows=[r for r in cr if r['reason']==rule]
            numerical.append(dict(rule=rule,n_pruned=sum(r['decision']=='PRUNED' for r in rows),
                                  n_fail_open=sum(r['decision']=='FAIL_OPEN' for r in rows),
                                  n_mp_checked=sum(r['mp_checked'] for r in rows),
                                  n_false_pruned=sum(r['false_prune'] for r in rows)))
        cwrite(root/'CP04_numerical_audit.csv',numerical,list(numerical[0]))
        allv={r['geometry']:r for r in abl if r['variant']=='ALL'}
        card={r['geometry']:r for r in abl if r['variant']=='CARDINALITY_ONLY'}
        deltas=[]
        for i in range(N):
            x=allv[i];y=card[i]
            deltas.append(dict(geometry=i,group=x['group'],solver_calls_saved=y['full_solves']-x['full_solves'],
                               runtime_saved_ms=y['runtime_ms']-x['runtime_ms'],
                               screening_ms=x['screening_ms'],
                               all_runtime_ms=x['runtime_ms'],cardinality_only_runtime_ms=y['runtime_ms']))
        cwrite(root/'CP05_paired_incremental.csv',deltas,list(deltas[0]))
        ci_calls=bootstrap_ci([x['solver_calls_saved'] for x in deltas],[x['group'] for x in deltas],n_boot=a.bootstrap)
        ci_time=bootstrap_ci([x['runtime_saved_ms'] for x in deltas],[x['group'] for x in deltas],n_boot=a.bootstrap)
        false_prune=sum(x['false_prune'] for x in cr)
        report=dict(status='PASS_EXACTNESS' if false_prune==0 and all(r['exact_matches']==N for r in sums) else 'FAIL',
                    n_geometries=N,n_groups=len(set(map(str,groups[:N]))),candidate_count=len(cr),
                    false_prunes=false_prune,n_near_fail_open=sum(x['decision']=='FAIL_OPEN' for x in cr),
                    additional_solver_calls_saved_mean=float(np.mean([x['solver_calls_saved'] for x in deltas])),
                    paired_runtime_saved_mean_ms=float(np.mean([x['runtime_saved_ms'] for x in deltas])),
                    solver_calls_ci95=ci_calls,runtime_saved_ci95=ci_time,
                    runtime_advantage_confirmed=(ci_time['lo'] is not None and ci_time['lo']>0),
                    numerical_scope='High precision only re-evaluates derived floating-point coefficients; no formal interval proof.',
                    inference_scope='Finite candidate family only; already-observed geometries are development.')
        jwrite(root/'CP06_decision.json',report)
        manifestrows=[dict(file=p.name,sha256=digest(p)) for p in sorted(root.glob('CP0*')) if p.name!='CP07_sha256.csv']
        cwrite(root/'CP07_sha256.csv',manifestrows,['file','sha256'])
        print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
