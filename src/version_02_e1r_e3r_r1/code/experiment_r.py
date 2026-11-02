#!/usr/bin/env python3
"""E1-R/E2-R/E3-R: four-way group split, per-method tuning, held-out reliability gate.

Revision R1 (2026-10-21). Main changes against the delivered E1R-E3R script:
  * Built on the R1 engine (experiment.py): Bonferroni slab radius q_G = sqrt(ln(K^2/eps)),
    slab uncertainty set, scale-invariant thresholds, dataset noise_w.
  * The development split (40%) is now used: grids are searched on development, finalists are
    selected on validation, and the selected policy is GATED (not selected) on calibration.
  * Candidate grids are per method. R0 crossed the fixed-margin values with the fuzzy grid, so the
    four "finalists" sent to calibration were one fuzzy configuration repeated four times.
  * Safety floors are kept only when they bind for some rule but not for all; otherwise
    fuzzy_safe degenerates into a constant margin (R0: every rule < 1.7, floors 1.7 and 2.2).
    The fixed grid covers every floor value, so a fuzzy "win" cannot come from grid coverage.
  * Fixed and threshold baselines go through the same develop -> validation -> calibration path.
  * Power is compared on the common feasible set (selection and report).
  * RZF failure is recorded as infeasible instead of aborting the run.
  * Transfer: frozen_from and bootstrap are not part of the run signature, physical settings are
    checked, the transfer test uses every group, task checkpoints are bound to the frozen params.
  * Group (cluster) bootstrap instead of geometry bootstrap; Wilson bounds; total runtime.
Statistical intervals are descriptive, NOT formal deployment guarantees.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from experiment import (load_data, rzf, features, power_alloc, fuzzy_q, gaussian_q, atomic_json, atomic_csv,
                        sha, sha_obj, clean, wilson, group_bootstrap)

METHODS = ('gaussian', 'fixed', 'threshold', 'fuzzy_raw', 'fuzzy_safe')
TUNED = ('fixed', 'threshold', 'fuzzy_raw', 'fuzzy_safe')
ADAPTIVE = ('threshold', 'fuzzy_raw', 'fuzzy_safe')
PHYSICAL = ('M', 'K', 'sigma_rel', 'sinr_db', 'eps')
N_FINALISTS = 4


# ------------------------------------------------------------------ splits & grids
def split(groups, seed):
    g = np.unique(groups)
    if len(g) < 12:
        raise ValueError('At least 12 distinct, spatially meaningful groups required '
                         '(development/validation/calibration/test)')
    g = np.random.default_rng(seed).permutation(g)
    n = len(g)
    cut = [0, int(.4 * n), int(.6 * n), int(.8 * n), n]
    sets = [np.flatnonzero(np.isin(groups, g[cut[i]:cut[i + 1]])) for i in range(4)]
    if min(map(len, sets)) == 0:
        raise ValueError('Empty split')
    return dict(zip(('development', 'validation', 'calibration', 'test'), sets))


def fuzzy_rules(c0, s1, s2, qg):
    """Rule l = 3*i1 + i2 (i1: conditioning set of z1, i2: coupling set of z2)."""
    return [float(np.clip(c0 + s1 * (l // 3 - 1) + s2 * (l % 3 - 1), .7, qg)) for l in range(9)]


def candidate_grids(qg):
    """Per-method grids. The fixed grid contains every floor value and spans the fuzzy outputs."""
    floors = (1.0, 1.4, 1.8)
    fixed = sorted({round(q, 6) for q in np.arange(.8, 2.4 + 1e-9, .2) if q <= qg} | {round(qg, 6)})
    g = dict(gaussian=[dict(q=qg)],
             fixed=[dict(q=float(q)) for q in fixed],
             threshold=[dict(qlo=lo, qhi=float(min(lo + d, qg))) for lo in (1.0, 1.4, 1.8) for d in (.4, .8)],
             fuzzy_raw=[], fuzzy_safe=[])
    for c0 in (1.0, 1.4, 1.8, 2.2):
        for s1 in (-.2, 0., .2):
            for s2 in (-.2, .2):
                rules = fuzzy_rules(c0, s1, s2, qg)
                g['fuzzy_raw'].append(dict(rules=rules, c0=c0, s1=s1, s2=s2))
                for fl in floors:          # keep only floors that bind for some, not all, rules
                    if min(rules) < fl - 1e-9 and fl < max(rules) - 1e-9:
                        g['fuzzy_safe'].append(dict(rules=rules, qfloor=fl, c0=c0, s1=s1, s2=s2))
    return g


def margin(method, z, c):
    if method in ('gaussian', 'fixed'):
        return c['q'], 0
    if method == 'threshold':                        # z2 > .5  <=>  rho(F(q_G)) > 1
        return (c['qlo'] if z[1] > .5 else c['qhi']), 0
    f = fuzzy_q(z, c['rules'])
    if method == 'fuzzy_raw':
        return f, 0
    return max(f, c['qfloor']), int(c['qfloor'] > f)


def fallback_safe(qg):
    """Fail-closed deployment of fuzzy_safe when it does not pass the calibration gate."""
    return dict(rules=[qg] * 9, qfloor=qg, fallback=True)


# ------------------------------------------------------------------- evaluation
def context(H, groups, i, cfg, seed, n_mc, qg):
    h = H[i]
    M = h.shape[0]
    s = cfg['sigma_rel']
    obs = np.random.default_rng(np.random.SeedSequence([seed, int(i), 311]))
    z = (obs.normal(size=h.shape) + 1j * obs.normal(size=h.shape)) / np.sqrt(2 * M)
    est = h + s * np.linalg.norm(h, axis=0)[None, :] * z
    t0 = time.perf_counter()
    V = rzf(est)
    ctx = dict(index=int(i), group=str(groups[i]), est=est, V=V, t_rzf=time.perf_counter() - t0)
    if V is None:
        return ctx
    t0 = time.perf_counter()
    ctx['z'] = features(est, V, cfg, qg)
    ctx['t_feat'] = time.perf_counter() - t0
    rng = np.random.default_rng(np.random.SeedSequence([seed, int(i), 733]))
    w = (rng.normal(size=(n_mc, *h.shape)) + 1j * rng.normal(size=(n_mc, *h.shape))) / np.sqrt(2 * M)
    true = est[None] + s * np.linalg.norm(est, axis=0)[None, None, :] * w
    ctx['g_mc'] = np.abs(np.einsum('nmk,mj->nkj', true.conj(), V)) ** 2     # |h_k^H v_j|^2, shared
    ctx['g_act'] = np.abs(h.conj().T @ V)[None] ** 2
    return ctx


def n_fail(G, p, cfg):
    desired = p[None, :] * np.diagonal(G, axis1=1, axis2=2)
    interf = np.einsum('nkj,j->nk', G, p) - desired + cfg['noise']
    return int(np.sum(np.any(desired < cfg['sinr'] * interf * (1 - 1e-12), axis=1)))


def evaluate(ctx, method, c, cfg, tag, cid=0):
    row = dict(index=ctx['index'], group=ctx['group'], split=tag, method=method, candidate=cid)
    if ctx['V'] is None:
        return dict(row, q=None, floor_active=0, feasible=0, reason='rzf_failed', power_w=None, n_mc=0, n_fail=0,
                    outage=None, effective_failure=1., actual_fail=None, rho=None, runtime_solver_s=None,
                    runtime_total_s=None, z1=None, z2=None)
    t0 = time.perf_counter()
    q, active = margin(method, ctx['z'], c)
    t_inf = time.perf_counter() - t0
    t0 = time.perf_counter()
    p, rho, reason = power_alloc(ctx['est'], ctx['V'], q, cfg)
    t_sol = time.perf_counter() - t0
    row.update(q=float(q), floor_active=active, reason=reason, rho=clean(rho), runtime_solver_s=t_sol,
               runtime_total_s=ctx['t_rzf'] + t_inf + t_sol + (ctx['t_feat'] if method in ADAPTIVE else 0.),
               z1=float(ctx['z'][0]), z2=float(ctx['z'][1]))
    if p is None:
        return dict(row, feasible=0, power_w=None, n_mc=0, n_fail=0, outage=None, effective_failure=1.,
                    actual_fail=None)
    nmc = len(ctx['g_mc'])
    f = n_fail(ctx['g_mc'], p, cfg)
    return dict(row, feasible=1, power_w=float(np.sum(p)), n_mc=nmc, n_fail=f, outage=f / nmc,
                effective_failure=f / nmc, actual_fail=n_fail(ctx['g_act'], p, cfg))


def run_grid(H, groups, ids, grids, cfg, a, qg, tag):
    """rows[method][candidate] -> list of per-geometry rows; one context per channel."""
    rows = {m: [[] for _ in grids[m]] for m in grids}
    for i in ids:
        ctx = context(H, groups, int(i), cfg, a.seed, a.n_mc, qg)
        for m in grids:
            for j, c in enumerate(grids[m]):
                rows[m][j].append(evaluate(ctx, m, c, cfg, tag, j))
    return rows


# ------------------------------------------------------------------- statistics
def metrics(rr, eps=None):
    ok = [r for r in rr if r['feasible']]
    nmc = sum(r['n_mc'] for r in ok)
    nf = sum(r['n_fail'] for r in ok)
    out = dict(n=len(rr), n_feasible=len(ok), feasible_rate=len(ok) / len(rr) if rr else np.nan,
               conditional_outage=nf / nmc if nmc else np.nan,
               conditional_outage_wilson_hi=wilson(nf, nmc)[1],
               effective_failure=float(np.mean([r['effective_failure'] for r in rr])) if rr else np.nan,
               mean_feasible_power_w=float(np.mean([r['power_w'] for r in ok])) if ok else np.nan,
               floor_active_rate=float(np.mean([r['floor_active'] for r in ok])) if ok else np.nan)
    if eps is not None:
        out['gate_pass'] = bool(nmc and out['conditional_outage'] <= eps and out['effective_failure'] <= eps)
    return out


def rank(rows_by_cand, eps):
    """Gate-passing candidates first, ordered by mean power on their common feasible set;
    then failing candidates by effective failure. Returns (order, stats)."""
    st = [metrics(rr, eps) for rr in rows_by_cand]
    passing = [j for j, s in enumerate(st) if s['gate_pass']]
    common = set.intersection(*[{r['index'] for r in rows_by_cand[j] if r['feasible']} for j in passing]) \
        if passing else set()
    for j, s in enumerate(st):
        pw = [r['power_w'] for r in rows_by_cand[j] if r['index'] in common]
        s['power_common_w'] = float(np.mean(pw)) if pw else np.nan
        s['n_common'] = len(common)
    key_pass = lambda j: (st[j]['power_common_w'] if common else st[j]['mean_feasible_power_w'], j)
    fail = [j for j in range(len(st)) if j not in passing]
    key_fail = lambda j: (st[j]['effective_failure'],
                          st[j]['mean_feasible_power_w'] if np.isfinite(st[j]['mean_feasible_power_w']) else np.inf, j)
    return sorted(passing, key=key_pass) + sorted(fail, key=key_fail), st


def paired(rows, method, base, reps, seed):
    aa = {r['index']: r for r in rows if r['method'] == method}
    bb = {r['index']: r for r in rows if r['method'] == base}
    ids = sorted(set(aa) & set(bb))
    common = [i for i in ids if aa[i]['feasible'] and bb[i]['feasible']]
    d = [aa[i]['effective_failure'] - bb[i]['effective_failure'] for i in ids]
    ratio = [aa[i]['power_w'] / bb[i]['power_w'] for i in common]
    db = [10 * np.log10(x) for x in ratio]
    dl, dh = group_bootstrap(d, [aa[i]['group'] for i in ids], reps, seed)
    rl, rh = group_bootstrap(ratio, [aa[i]['group'] for i in common], reps, seed + 1)
    bl, bh = group_bootstrap(db, [aa[i]['group'] for i in common], reps, seed + 2)
    return dict(method=method, baseline=base, n=len(ids), n_common=len(common),
                delta_effective_failure=float(np.mean(d)) if d else np.nan,
                delta_effective_ci_lo=dl, delta_effective_ci_hi=dh,
                mean_common_power_ratio=float(np.mean(ratio)) if ratio else np.nan,
                power_ratio_ci_lo=rl, power_ratio_ci_hi=rh,
                mean_db=float(np.mean(db)) if db else np.nan, db_ci_lo=bl, db_ci_hi=bh)


def jsonable(x):
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return clean(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


# ------------------------------------------------------------------------ main
def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--stage', required=True,
                   choices=['preflight', 'develop', 'calibrate', 'freeze', 'test', 'report', 'all'])
    p.add_argument('--dataset', required=True)
    p.add_argument('--run-id', required=True)
    p.add_argument('--output-root', default='outputs_r')
    p.add_argument('--M', type=int, default=16)
    p.add_argument('--K', type=int, default=4)
    p.add_argument('--seed', type=int, default=20261021)
    p.add_argument('--sigma-rel', type=float, default=.04)
    p.add_argument('--sinr-db', type=float, default=6.)
    p.add_argument('--noise', type=float, default=None,
                   help='receiver noise [W]; default: dataset noise_w if present, else 1e-9')
    p.add_argument('--pmax', type=float, default=1.)
    p.add_argument('--eps', type=float, default=.05)
    p.add_argument('--n-mc', type=int, default=300)
    p.add_argument('--bootstrap', type=int, default=3000, help='group-bootstrap replicates (report only)')
    p.add_argument('--limit', type=int, default=0, help='smoke tests only: first N channels of each split')
    p.add_argument('--frozen-from', default='', help='freeze stage only: transfer a frozen parameter file')
    a = p.parse_args()
    if not (0 < a.eps < 1 and a.n_mc > 0 and a.bootstrap >= 100 and a.pmax > 0 and 0 < a.sigma_rel < 1
            and a.M >= a.K >= 1 and a.limit >= 0):
        p.error('invalid parameters')
    if a.noise is not None and a.noise <= 0:
        p.error('--noise must be > 0')
    if a.frozen_from and a.stage not in ('freeze',):
        p.error('--frozen-from is used with --stage freeze only (test/report read cp03_frozen.json)')

    dataset = Path(a.dataset).resolve()
    H, groups, noise_ds = load_data(dataset, a.M, a.K)
    noise = a.noise if a.noise is not None else (noise_ds if noise_ds is not None else 1e-9)
    cfg = dict(sigma_rel=a.sigma_rel, sinr=10 ** (a.sinr_db / 10), noise=noise, pmax=a.pmax)
    qg = gaussian_q(a.eps, a.K)
    root = Path(a.output_root) / a.run_id
    root.mkdir(parents=True, exist_ok=True)

    settings = {k: v for k, v in vars(a).items()
                if k not in ('stage', 'run_id', 'output_root', 'dataset', 'frozen_from', 'bootstrap', 'noise')}
    settings['noise_w'] = noise
    sigdata = dict(code_sha256=sha(__file__), engine_sha256=sha(Path(__file__).parent / 'experiment.py'),
                   dataset_sha256=sha(dataset), settings=settings)
    signature = sha_obj(sigdata)
    manifest = root / 'cp00_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())['signature'] != signature:
        raise RuntimeError('Code/data/settings changed: use NEW run-id')
    if not manifest.exists():
        atomic_json(manifest, dict(signature=signature, dataset_path=str(dataset), **sigdata))
    physical = {k: settings[k] for k in PHYSICAL}
    frozen_path = root / 'cp03_frozen.json'
    transfer = a.frozen_from != '' or (frozen_path.exists() and json.loads(frozen_path.read_text()).get('transferred'))

    def lim(x):
        return x[:a.limit] if a.limit else x

    if transfer:              # nothing is tuned on a transfer dataset: every group is test data
        if len(np.unique(groups)) < 2:
            raise ValueError('transfer dataset needs >= 2 groups for the group bootstrap')
        splits = dict(test=lim(np.arange(len(H))))
    else:
        splits = {k: lim(v) for k, v in split(groups, a.seed).items()}
    if a.stage == 'preflight':
        print('PASS', [(k, len(v)) for k, v in splits.items()], '| noise_w =', noise, '| q_G =', round(qg, 4))
        return

    if a.stage in ('develop', 'all'):
        grids = candidate_grids(qg)
        rows = run_grid(H, groups, splits['development'], {m: grids[m] for m in TUNED}, cfg, a, qg, 'development')
        out = {}
        for m in TUNED:
            order, st = rank(rows[m], a.eps)
            out[m] = dict(n_candidates=len(grids[m]), finalists=order[:N_FINALISTS],
                          candidates=[dict(id=j, parameters=grids[m][j], metrics=st[j]) for j in range(len(st))])
        atomic_json(root / 'cp01_validation_candidates.json',
                    jsonable(dict(signature=signature, split='development', qgauss=qg, methods=out)))

    if a.stage in ('calibrate', 'all'):
        c1 = json.loads((root / 'cp01_validation_candidates.json').read_text())
        if c1['signature'] != signature:
            raise RuntimeError('cp01 signature mismatch: rerun develop')
        fin = {m: [c1['methods'][m]['candidates'][j]['parameters'] for j in c1['methods'][m]['finalists']]
               for m in TUNED}
        # (1) selection among finalists on VALIDATION
        vrows = run_grid(H, groups, splits['validation'], fin, cfg, a, qg, 'validation')
        sel, vstat = {}, {}
        for m in TUNED:
            order, st = rank(vrows[m], a.eps)
            sel[m] = fin[m][order[0]]
            vstat[m] = [dict(parameters=fin[m][j], metrics=st[j]) for j in range(len(st))]
        # (2) gate (no selection) on CALIBRATION, with the gaussian reference
        gsel = dict(sel, gaussian=dict(q=qg))
        crows = run_grid(H, groups, splits['calibration'], {m: [gsel[m]] for m in METHODS}, cfg, a, qg,
                         'calibration')
        gate = {m: metrics(crows[m][0], a.eps) for m in METHODS}
        atomic_json(root / 'cp02_calibration_screen.json', jsonable(dict(
            signature=signature, validation=vstat, selected=sel, calibration_gate=gate,
            rule='finalists from development; selection on validation; pass/fail gate on calibration: '
                 'conditional outage <= eps AND effective failure <= eps')))

    if a.stage in ('freeze', 'all'):
        if a.frozen_from:
            obj = json.loads(Path(a.frozen_from).read_text())
            if 'physical' not in obj or 'parameters' not in obj or 'gaussian' not in obj['parameters']:
                raise RuntimeError('External frozen file is from an older revision; rerun the source pipeline')
            bad = {k: (obj['physical'][k], physical[k]) for k in PHYSICAL if obj['physical'].get(k) != physical[k]}
            if bad:
                raise RuntimeError(f'Transfer settings differ from frozen source: {bad}')
            frozen = dict(obj, signature=signature, transferred=True,
                          transferred_from=str(Path(a.frozen_from).resolve()), transferred_sha256=sha(a.frozen_from),
                          reason='external transfer without retuning; every group of this dataset is test data')
        else:
            c2 = json.loads((root / 'cp02_calibration_screen.json').read_text())
            if c2['signature'] != signature:
                raise RuntimeError('cp02 signature mismatch: rerun calibrate')
            par = dict(c2['selected'], gaussian=dict(q=qg))
            eligible = bool(c2['calibration_gate']['fuzzy_safe']['gate_pass'])
            if not eligible:
                par['fuzzy_safe'] = fallback_safe(qg)
            frozen = dict(signature=signature, transferred=False, physical=physical, parameters=par,
                          eligible=eligible, calibration_gate=c2['calibration_gate'],
                          reason='fuzzy_safe passed the calibration gate' if eligible else
                          'NO_FUZZY_SAFE_PASS; Gaussian-equivalent fail-closed fallback; no reliability guarantee')
        frozen.update(eps=a.eps, qgauss=qg, statistical_guarantee=False)
        atomic_json(frozen_path, jsonable(frozen))

    if a.stage in ('test', 'all'):
        fr = json.loads(frozen_path.read_text())
        if fr['signature'] != signature:
            raise RuntimeError('frozen mismatch')
        fsha = sha_obj(fr['parameters'])
        dest = root / 'tasks' / 'test'
        dest.mkdir(parents=True, exist_ok=True)
        for i in splits['test']:
            f = dest / f'g{int(i):07d}.json'
            if f.exists():
                chk = json.loads(f.read_text())
                if chk.get('signature') == signature and chk.get('frozen_sha') == fsha and chk.get('complete'):
                    continue
                raise RuntimeError('Checkpoint mismatch ' + str(f))
            ctx = context(H, groups, int(i), cfg, a.seed, a.n_mc, qg)
            rows = [evaluate(ctx, m, fr['parameters'][m], cfg, 'test') for m in METHODS]
            atomic_json(f, jsonable(dict(signature=signature, frozen_sha=fsha, complete=True, index=int(i),
                                         rows=rows)))

    if a.stage in ('report', 'all'):
        fr = json.loads(frozen_path.read_text())
        fsha = sha_obj(fr['parameters'])
        rows = []
        for i in splits['test']:
            f = root / 'tasks' / 'test' / f'g{int(i):07d}.json'
            if not f.exists():
                raise RuntimeError('Missing checkpoint ' + str(f))
            obj = json.loads(f.read_text())
            if not (obj['signature'] == signature and obj.get('frozen_sha') == fsha and obj['complete']):
                raise RuntimeError('Checkpoint mismatch ' + str(f))
            rows.extend(obj['rows'])
        atomic_csv(root / 'cp04_test_geometry.csv', [{k: ('' if v is None else v) for k, v in r.items()} for r in rows],
                   list(rows[0]))
        summ = []
        for m in METHODS:
            rr = [r for r in rows if r['method'] == m]
            s = dict(method=m, **metrics(rr, a.eps))
            s['effective_failure_ci_lo'], s['effective_failure_ci_hi'] = group_bootstrap(
                [r['effective_failure'] for r in rr], [r['group'] for r in rr], a.bootstrap, a.seed + 11)
            ok = [r for r in rr if r['feasible']]
            s['conditional_outage_ci_lo'], s['conditional_outage_ci_hi'] = group_bootstrap(
                [r['n_fail'] for r in ok], [r['group'] for r in ok], a.bootstrap, a.seed + 13,
                den=[r['n_mc'] for r in ok]) if ok else (np.nan, np.nan)
            s['actual_fail_rate'] = float(np.mean([r['actual_fail'] for r in ok])) if ok else np.nan
            s['mean_runtime_total_s'] = float(np.mean([r['runtime_total_s'] for r in rr
                                                       if r['runtime_total_s'] is not None] or [np.nan]))
            summ.append(s)
        atomic_csv(root / 'cp05_test_summary.csv', summ, list(summ[0]))
        pair = [paired(rows, m, 'gaussian', a.bootstrap, a.seed + 77) for m in TUNED]
        pair += [paired(rows, 'fuzzy_safe', b, a.bootstrap, a.seed + 105) for b in ('fixed', 'threshold')]
        atomic_csv(root / 'cp06_paired_comparison.csv', pair, list(pair[0]))
        met = {s['method']: s for s in summ}
        eligible = bool(fr.get('eligible') and met['fuzzy_safe']['gate_pass'])
        baselines_reliable = bool(met['fixed']['gate_pass'] and met['threshold']['gate_pass'])
        vs = {c['baseline']: c for c in pair if c['method'] == 'fuzzy_safe' and c['baseline'] in ('fixed', 'threshold')}
        power_better = all(np.isfinite(vs[b]['power_ratio_ci_hi']) and vs[b]['power_ratio_ci_hi'] < 1
                           and vs[b]['delta_effective_ci_hi'] <= .005 for b in ('fixed', 'threshold'))
        better = bool(baselines_reliable and power_better)
        decision = 'GO_fuzzy_incremental' if eligible and better else 'STOP_no_demonstrated_fuzzy_advantage'
        atomic_json(root / 'cp07_stop_decision.json', jsonable(dict(
            decision=decision, eligible=eligible, baselines_reliable=baselines_reliable,
            power_and_risk_better=bool(power_better), power_and_outage_better=better,
            fuzzy_safe_is_fallback=bool(fr['parameters']['fuzzy_safe'].get('fallback', False)),
            criteria='frozen eligible AND test conditional AND effective failure <= eps; fixed and threshold also '
                     '<= eps on test; vs both: group-bootstrap 95% upper mean power ratio < 1 and upper '
                     'effective-failure difference <= 0.005',
            note='Exploratory group bootstrap; no formal outage guarantee')))
        checks = [dict(index=int(i), sha256=sha(root / 'tasks' / 'test' / f'g{int(i):07d}.json'))
                  for i in splits['test']]
        atomic_csv(root / 'cp08_checkpoint_sha256.csv', checks, ['index', 'sha256'])
        reasons = {}
        for r in rows:
            if not r['feasible']:
                reasons.setdefault(r['method'], {}).setdefault(r['reason'], 0)
                reasons[r['method']][r['reason']] += 1
        atomic_json(root / 'cp09_scope.json', jsonable(dict(
            no_formal_coverage_guarantee=True, transferred=bool(fr.get('transferred')),
            group_split='all groups = test (transfer)' if fr.get('transferred') else
            '40/20/20/20 development/validation/calibration/test',
            test_geometries=len(splits['test']), test_groups=int(len(np.unique(groups[splits['test']]))),
            limited=bool(a.limit), n_mc=a.n_mc, noise_w=noise, qgauss=qg, infeasible_reasons=reasons,
            selection_uses_test=False, gaussian_guarantee='conditional outage <= eps under the simulated CSI law only',
            independent_3gpp_requires_actual_sionna_channels=True, synthetic_data_not_publication_evidence=True)))
        print(json.dumps(jsonable(dict(summary=[{k: s[k] for k in ('method', 'n_feasible', 'conditional_outage',
                                                                   'effective_failure', 'mean_feasible_power_w')}
                                                for s in summ], decision=decision)), indent=1))


if __name__ == '__main__':
    main()
