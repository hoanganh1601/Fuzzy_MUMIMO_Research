#!/usr/bin/env python3
"""Deterministic near-boundary tests for finite candidate robust SINR screening.

Tests algebraic power-control boundaries separately from beam-generation rounding.
Also tests actual CSI->ZF/RZF->F,u near the power-budget boundary.
"""
import argparse, csv, hashlib, json, math, time
from pathlib import Path
import numpy as np
import mpmath as mp
from reference_model import load, get_beam, solve, digest, jwrite, cwrite
from ablation_certified import robust_screen, build_Fu
from ablation_audit import RULES


def power_reference(F,u,pmax,dps=100):
    """High precision feasibility from decimal encodings of F and u (not interval arithmetic)."""
    mp.mp.dps=dps
    FM=mp.matrix([[mp.mpf(str(float(v))) for v in row] for row in F])
    U=mp.matrix([mp.mpf(str(float(v))) for v in u])
    power=mp.mpf(str(float(pmax)))
    if len(u)==1:
        rho=mp.mpf('0')
    elif len(u)==2:
        rho=mp.sqrt(FM[0,1]*FM[1,0])
    else:
        rho=mp.mpf(str(float(max(abs(np.linalg.eigvals(F))))))
    if rho>=1:
        return dict(status='COUPLING',rho=str(rho),p_req='')
    try:
        p=mp.lu_solve(mp.eye(len(u))-FM,U)
        req=sum(p)
        return dict(status='FEASIBLE' if req<=power else 'POWER_BUDGET',rho=str(rho),p_req=str(req))
    except (ZeroDivisionError, ValueError):
        return dict(status='NUMERICAL_UNDETERMINED',rho=str(rho),p_req='')


def algebraic_screen(F,u,pmax,guard=1e-5,orders=4):
    """Same sufficient Neumann and 2-cycle criteria, conservative at boundaries."""
    partial=np.array(u,dtype=float).copy();term=partial.copy()
    for _ in range(orders):
        term=F@term;partial+=term
    neumann=float(partial.sum())
    cycles=[float(F[i,j]*F[j,i]) for i in range(len(u)) for j in range(i+1,len(u))]
    cycle=max(cycles,default=0.)
    tests=[('NEUMANN',neumann/pmax-1.),('TWO_CYCLE',cycle-1.)]
    valid=[(r,v) for r,v in tests if v>1e-8]
    if not valid:return dict(decision='SURVIVE',reason='',slack=0.,near=False)
    reason,slack=valid[0]
    if slack<=guard:return dict(decision='FAIL_OPEN',reason=reason,slack=slack,near=True)
    return dict(decision='PRUNE',reason=reason,slack=slack,near=False)


def algebraic_rows(deltas,guard):
    out=[]
    # Construct exactly controlled rho and power boundaries without inferring from rounded beams.
    for boundary in ('COUPLING','POWER'):
        for sign in (-1,1):
            for delta in deltas:
                if boundary=='COUPLING':
                    F=np.array([[0.,1.+sign*delta],[1.,0.]],float); u=np.array([.01,.01]); pmax=5.
                else:
                    F=np.array([[0.,.2],[.2,0.]],float);u=np.array([.01,.01]);
                    p_base=float(np.linalg.solve(np.eye(2)-F,u).sum())
                    pmax=p_base/(1+sign*delta)
                mp_truth=power_reference(F,u,pmax)
                s=algebraic_screen(F,u,pmax,guard)
                bad=int(s['decision']=='PRUNE' and mp_truth['status']=='FEASIBLE')
                out.append(dict(source='algebraic',boundary=boundary,delta=delta,sign=sign,
                                pmax=pmax,mp_truth=mp_truth['status'],mp_rho=mp_truth['rho'],
                                mp_p_req=mp_truth['p_req'],decision=s['decision'],reason=s['reason'],
                                relative_slack=s['slack'],near=int(s['near']),false_prune=bad))
    return out


def channel_rows(H, alphas, cfg, deltas, guard, limit):
    rows=[]
    for geom,h in enumerate(H[:limit]):
        # A singleton channel gives a well-conditioned power-boundary stress case.
        sub=(0,)
        for alpha in alphas[:2]:
            comp=build_Fu(h,sub,alpha,cfg)
            if comp is None or comp.get('zero'):continue
            req=float(np.asarray(comp['u']).sum())
            if not np.isfinite(req) or req<=0:continue
            for sign in (-1,1):
                for delta in deltas:
                    test_cfg=dict(cfg,pmax=req/(1+sign*delta))
                    prune, rec=robust_screen(h,sub,alpha,test_cfg,set(RULES),guard)
                    mp_truth=power_reference(np.asarray(comp['F']),np.asarray(comp['u']),test_cfg['pmax'])
                    # This audit compares pruning to high-precision solution of derived double coefficients.
                    false=int(prune and mp_truth['status']=='FEASIBLE')
                    rows.append(dict(source='channel',geometry=geom,subset='0',alpha=alpha,
                                     boundary='POWER',delta=delta,sign=sign,pmax=test_cfg['pmax'],
                                     decision='PRUNE' if prune else ('FAIL_OPEN' if rec['fail_open'] else 'SURVIVE'),
                                     reason=rec['reason'],near=int(rec['near_threshold']),
                                     mp_checked=int(rec['mp_checked']),mp_truth=mp_truth['status'],
                                     mp_rho=mp_truth['rho'],mp_p_req=mp_truth['p_req'],false_prune=false))
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--stage',choices=['scan','report','all'],required=True)
    ap.add_argument('--run-id',required=True);ap.add_argument('--out-root',default='outputs')
    ap.add_argument('--dataset',default='');ap.add_argument('--limit',type=int,default=4)
    ap.add_argument('--delta-list',default='1e-3,1e-5,1e-7,1e-9,1e-11')
    ap.add_argument('--guard',type=float,default=1e-5)
    ap.add_argument('--q',type=float,default=2.960414);ap.add_argument('--sigma-rel',type=float,default=.04)
    ap.add_argument('--sinr-db',type=float,default=6.);ap.add_argument('--noise',type=float,default=2e-13)
    a=ap.parse_args(); ds=[float(s) for s in a.delta_list.split(',')]
    if not ds or any(not 0<x<.1 for x in ds):raise ValueError('delta must be in (0,0.1)')
    config={k:v for k,v in vars(a).items() if k not in ('stage','run_id','out_root')}
    config['dataset_sha']=digest(a.dataset) if a.dataset else None
    config['code_sha']=digest(__file__)
    signature=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    root=Path(a.out_root)/a.run_id;root.mkdir(parents=True,exist_ok=True)
    mpath=root/'CP00_manifest.json'
    if mpath.exists():
        if json.loads(mpath.read_text())['signature']!=signature:raise RuntimeError('checkpoint signature mismatch; use new run-id')
    else:jwrite(mpath,dict(signature=signature,config=config,scope='stress, not field reliability'))
    if a.stage in ('scan','all'):
        tasks=[('algebraic',None)]
        if a.dataset:
            H,groups,meta=load(a.dataset)
            tasks += [(f'channel_{i}', H[i:i+1]) for i in range(min(a.limit,len(H)))]
        for key, h in tasks:
            f=root/'tasks'/f'{key}.json'
            if f.exists():
                ck=json.loads(f.read_text())
                if ck.get('signature')!=signature:raise RuntimeError('bad checkpoint')
                continue
            if h is None:rows=algebraic_rows(ds,a.guard)
            else:
                cfg=dict(q=a.q,sigma=a.sigma_rel,gamma=10**(a.sinr_db/10),noise=a.noise,pmax=1.)
                rows=channel_rows(h,[0.,.01],cfg,ds,a.guard,1)
                for r in rows:r['geometry']=int(key.split('_')[1])
            jwrite(f,dict(signature=signature,rows=rows))
    if a.stage in ('report','all'):
        files=[root/'tasks'/'algebraic.json']
        if a.dataset:
            H,_,_=load(a.dataset);files += [root/'tasks'/f'channel_{i}.json' for i in range(min(a.limit,len(H)))]
        rows=[]
        for f in files:
            t=json.loads(f.read_text());assert t['signature']==signature
            rows+=t['rows']
        headers=sorted(set().union(*(set(r) for r in rows)))
        cwrite(root/'CP01_boundary_cases.csv',rows,headers)
        failures=sum(int(r['false_prune']) for r in rows)
        dec=dict(n_cases=len(rows),false_prunes=failures,fail_open_cases=sum(r['decision']=='FAIL_OPEN' for r in rows),
                 outcome='PASS' if failures==0 else 'FAIL',
                 scope='Positive-F,u algebraic boundary and single-user CSI-derived power boundary; not interval guarantee for beam generation.')
        jwrite(root/'CP02_boundary_decision.json',dec)
        cwrite(root/'CP03_sha256.csv',[{'file':p.name,'sha256':digest(p)} for p in (mpath,root/'CP01_boundary_cases.csv',root/'CP02_boundary_decision.json')],['file','sha256'])
        print(json.dumps(dec,indent=2))

if __name__=='__main__':main()
