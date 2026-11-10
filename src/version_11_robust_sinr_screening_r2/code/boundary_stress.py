#!/usr/bin/env python3
"""Deterministic near-boundary tests for finite candidate robust SINR screening.

Tests algebraic power-control boundaries separately from beam-generation rounding.
Also tests actual CSI->ZF/RZF->F,u near the power-budget boundary.

Reference truth: exact rational arithmetic on the binary64 coefficients F, u, pmax.
For F >= 0, rho(F) < 1  <=>  I-F is a nonsingular M-matrix  <=>  every pivot of
Gaussian elimination without pivoting on I-F is positive (leading principal
minors > 0). This decides the coupling boundary exactly for any size, without a
floating-point eigenvalue. It is not interval arithmetic on beam generation.
"""
import argparse, csv, hashlib, json, math, time
from fractions import Fraction
from pathlib import Path
import numpy as np
from reference_model import utf8_console
from reference_model import load, get_beam, solve, digest, jwrite, cwrite, check_count, PRUNE_REL_MARGIN
from ablation_certified import robust_screen, build_Fu, qstr
from ablation_audit import RULES

DEPENDENCIES = ('reference_model.py', 'ablation_audit.py', 'ablation_certified.py')


def power_reference(F, u, pmax):
    """Exact feasibility of p >= F p + u, p >= 0, 1^T p <= pmax (F >= 0, u > 0)."""
    n = len(u)
    A = [[(Fraction(1) if i == j else Fraction(0)) - Fraction(float(F[i][j])) for j in range(n)] for i in range(n)]
    b = [Fraction(float(x)) for x in u]
    power = Fraction(float(pmax))
    rho_float = 0.0 if n == 1 else float(max(abs(np.linalg.eigvals(np.asarray(F, float)))))
    # Forward elimination without pivoting; a nonpositive pivot means I-F is not a
    # nonsingular M-matrix, i.e. rho(F) >= 1 -> no finite nonnegative solution.
    for k in range(n):
        if A[k][k] <= 0:
            return dict(status='COUPLING', rho=repr(rho_float), p_req='')
        for i in range(k + 1, n):
            f = A[i][k] / A[k][k]
            if f:
                for j in range(k, n):
                    A[i][j] -= f * A[k][j]
                b[i] -= f * b[k]
    p = [Fraction(0)] * n
    for i in range(n - 1, -1, -1):
        p[i] = (b[i] - sum(A[i][j] * p[j] for j in range(i + 1, n))) / A[i][i]
    req = sum(p)
    return dict(status='FEASIBLE' if req <= power else 'POWER_BUDGET', rho=repr(rho_float), p_req=qstr(req))


def algebraic_screen(F, u, pmax, guard=1e-5, orders=4):
    """Same sufficient Neumann and 2-cycle criteria, conservative at boundaries."""
    partial = np.array(u, dtype=float).copy(); term = partial.copy()
    for _ in range(orders):
        term = F @ term; partial += term
    neumann = float(partial.sum())
    cycles = [float(F[i, j] * F[j, i]) for i in range(len(u)) for j in range(i + 1, len(u))]
    cycle = max(cycles, default=0.)
    tests = [('NEUMANN', neumann / pmax - 1.), ('TWO_CYCLE', cycle - 1.)]
    valid = [(r, v) for r, v in tests if v > PRUNE_REL_MARGIN]
    if not valid: return dict(decision='SURVIVE', reason='', slack=0., near=False)
    reason, slack = valid[0]
    if slack <= guard: return dict(decision='FAIL_OPEN', reason=reason, slack=slack, near=True)
    return dict(decision='PRUNE', reason=reason, slack=slack, near=False)


def _p_req(F, u):
    return float(np.linalg.solve(np.eye(len(u)) - F, u).sum())


def algebraic_rows(deltas, guard):
    """Controlled boundaries; every family has a feasible side and an infeasible side.

    COUPLING   : F=[[0,1+s*d],[1,0]]. s=-1 -> rho<1 and pmax=2*p_req, so truth is
                 FEASIBLE (the former fixed pmax=5 made every s=-1 case
                 POWER_BUDGET, so a false prune could never be observed);
                 s=+1 -> rho>1, truth COUPLING.
    POWER      : F=0.2 symmetric, pmax=p_req/(1+s*d). The 4-term Neumann bound is
                 ~3.2e-4 below p_req, so this family only exercises the loose side.
    POWER_TIGHT: nilpotent F=[[0,0.2],[0,0]]; the Neumann bound equals p_req
                 exactly, so the guard and the fail-open path are exercised at the
                 power boundary itself.
    """
    out = []
    u = np.array([.01, .01])
    for boundary in ('COUPLING', 'POWER', 'POWER_TIGHT'):
        for sign in (-1, 1):
            for delta in deltas:
                if boundary == 'COUPLING':
                    F = np.array([[0., 1. + sign * delta], [1., 0.]], float)
                    pmax = 2. * _p_req(F, u) if sign < 0 else 5.
                else:
                    F = (np.array([[0., .2], [.2, 0.]], float) if boundary == 'POWER'
                         else np.array([[0., .2], [0., 0.]], float))
                    pmax = _p_req(F, u) / (1 + sign * delta)
                mp_truth = power_reference(F, u, pmax)
                s = algebraic_screen(F, u, pmax, guard)
                bad = int(s['decision'] == 'PRUNE' and mp_truth['status'] == 'FEASIBLE')
                out.append(dict(source='algebraic', boundary=boundary, delta=delta, sign=sign,
                                pmax=pmax, mp_truth=mp_truth['status'], mp_rho=mp_truth['rho'],
                                mp_p_req=mp_truth['p_req'], decision=s['decision'], reason=s['reason'],
                                relative_slack=s['slack'], near=int(s['near']), false_prune=bad))
    return out


def channel_rows(H, alphas, cfg, deltas, guard, limit):
    rows = []
    for geom, h in enumerate(H[:limit]):
        # A singleton channel gives a well-conditioned power-boundary stress case.
        sub = (0,)
        for alpha in alphas[:2]:
            comp = build_Fu(h, sub, alpha, cfg)
            if comp is None or comp.get('zero'): continue
            req = float(np.asarray(comp['u']).sum())
            if not np.isfinite(req) or req <= 0: continue
            for sign in (-1, 1):
                for delta in deltas:
                    test_cfg = dict(cfg, pmax=req / (1 + sign * delta))
                    prune, rec = robust_screen(h, sub, alpha, test_cfg, set(RULES), guard)
                    mp_truth = power_reference(np.asarray(comp['F']), np.asarray(comp['u']), test_cfg['pmax'])
                    # This audit compares pruning to the exact solution of derived double coefficients.
                    false = int(prune and mp_truth['status'] == 'FEASIBLE')
                    rows.append(dict(source='channel', geometry=geom, subset='0', alpha=alpha,
                                     boundary='POWER', delta=delta, sign=sign, pmax=test_cfg['pmax'],
                                     decision='PRUNE' if prune else ('FAIL_OPEN' if rec['fail_open'] else 'SURVIVE'),
                                     reason=rec['reason'], near=int(rec['near_threshold']),
                                     mp_checked=int(rec['mp_checked']), mp_truth=mp_truth['status'],
                                     mp_rho=mp_truth['rho'], mp_p_req=mp_truth['p_req'], false_prune=false))
    return rows


def decide(rows):
    """A1 PASS needs: no false prune, real fail-open activity, and a feasible side
    actually tested (otherwise 'no false prune' is vacuous), as in the guide."""
    failures = sum(int(r['false_prune']) for r in rows)
    fail_open = sum(r['decision'] == 'FAIL_OPEN' for r in rows)
    feasible = sum(r['mp_truth'] == 'FEASIBLE' for r in rows)
    pruned = sum(r['decision'] == 'PRUNE' for r in rows)
    by = {}
    for r in rows:
        k = f"{r['source']}:{r['boundary']}"
        d = by.setdefault(k, dict(cases=0, feasible_truth=0, prune=0, fail_open=0, false_prune=0))
        d['cases'] += 1; d['feasible_truth'] += r['mp_truth'] == 'FEASIBLE'
        d['prune'] += r['decision'] == 'PRUNE'; d['fail_open'] += r['decision'] == 'FAIL_OPEN'
        d['false_prune'] += int(r['false_prune'])
    reasons = []
    if failures: reasons.append('false_prune')
    if not fail_open: reasons.append('no_fail_open_triggered')
    if not feasible: reasons.append('no_feasible_reference_case')
    return dict(n_cases=len(rows), false_prunes=failures, fail_open_cases=fail_open,
                feasible_reference_cases=feasible, pruned_cases=pruned, by_family=by,
                outcome='PASS' if not reasons else 'FAIL', fail_reasons=reasons,
                scope='Positive-F,u algebraic boundary and single-user CSI-derived power boundary; '
                      'exact rational reference on double coefficients, not interval guarantee for beam generation.')


def main():
    utf8_console()
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', choices=['scan', 'report', 'all'], required=True)
    ap.add_argument('--run-id', required=True); ap.add_argument('--out-root', default='outputs')
    ap.add_argument('--dataset', default=''); ap.add_argument('--limit', type=int, default=4)
    ap.add_argument('--delta-list', default='1e-3,1e-5,1e-7,1e-9,1e-11')
    ap.add_argument('--guard', type=float, default=1e-5)
    ap.add_argument('--q', type=float, default=2.960414); ap.add_argument('--sigma-rel', type=float, default=.04)
    ap.add_argument('--sinr-db', type=float, default=6.); ap.add_argument('--noise', type=float, default=2e-13)
    a = ap.parse_args(); ds = [float(s) for s in a.delta_list.split(',')]
    if not ds or any(not 0 < x < .1 for x in ds): raise ValueError('delta must be in (0,0.1)')
    if not (a.guard > PRUNE_REL_MARGIN): raise ValueError('--guard must exceed PRUNE_REL_MARGIN')
    if a.limit < 0: raise ValueError('--limit must be >= 0')
    config = {k: v for k, v in vars(a).items() if k not in ('stage', 'run_id', 'out_root')}
    config['dataset_sha'] = digest(a.dataset) if a.dataset else None
    config['code_sha'] = digest(__file__)
    # Screening logic and reference model live in the imported modules; a change
    # there must invalidate existing checkpoints too.
    config['dependency_sha'] = {p: digest(Path(__file__).with_name(p)) for p in DEPENDENCIES}
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    root = Path(a.out_root) / a.run_id; root.mkdir(parents=True, exist_ok=True)
    mpath = root / 'CP00_manifest.json'
    if mpath.exists():
        if json.loads(mpath.read_text(encoding='utf8'))['signature'] != signature: raise RuntimeError('checkpoint signature mismatch; use new run-id')
    else: jwrite(mpath, dict(signature=signature, config=config, scope='stress, not field reliability'))
    n_channel = 0
    if a.dataset:
        H, groups, meta = load(a.dataset)
        n_channel = min(a.limit, len(H))
    if a.stage in ('scan', 'all'):
        tasks = [('algebraic', None)]
        if a.dataset:
            tasks += [(f'channel_{i}', H[i:i + 1]) for i in range(n_channel)]
        for key, h in tasks:
            f = root / 'tasks' / f'{key}.json'
            if f.exists():
                ck = json.loads(f.read_text(encoding='utf8'))
                if ck.get('signature') != signature: raise RuntimeError('bad checkpoint ' + str(f))
                continue
            if h is None: rows = algebraic_rows(ds, a.guard)
            else:
                cfg = dict(q=a.q, sigma=a.sigma_rel, gamma=10**(a.sinr_db / 10), noise=a.noise, pmax=1.)
                rows = channel_rows(h, [0., .01], cfg, ds, a.guard, 1)
                for r in rows: r['geometry'] = int(key.split('_')[1])
            jwrite(f, dict(signature=signature, rows=rows))
    if a.stage in ('report', 'all'):
        files = [root / 'tasks' / 'algebraic.json'] + [root / 'tasks' / f'channel_{i}.json' for i in range(n_channel)]
        rows = []
        for f in files:
            if not f.exists(): raise RuntimeError('missing ' + str(f))
            t = json.loads(f.read_text(encoding='utf8'))
            if t.get('signature') != signature: raise RuntimeError('bad checkpoint ' + str(f))
            rows += t['rows']
        headers = sorted(set().union(*(set(r) for r in rows)))
        cwrite(root / 'CP01_boundary_cases.csv', rows, headers)
        dec = decide(rows)
        jwrite(root / 'CP02_boundary_decision.json', dec)
        cwrite(root / 'CP03_sha256.csv', [{'file': p.name, 'sha256': digest(p)} for p in (mpath, root / 'CP01_boundary_cases.csv', root / 'CP02_boundary_decision.json')], ['file', 'sha256'])
        print(json.dumps(dec, indent=2))


if __name__ == '__main__': main()
