#!/usr/bin/env python3
"""Robust MU-MIMO power allocation with a fuzzy (Sugeno) CSI-margin selector.

Pilot framework. Revision R1 (2026-10-19). Main changes against R0:
  * Uncertainty set made explicit: slab set |e_k^H v_j| <= r_k for all j, which is
    exactly the set under which the coupling bound is valid. R0 described it as a
    norm ball ||e_k|| <= r_k, which the chosen radii do not cover.
  * Gaussian baseline radius corrected to the Bonferroni slab radius
    q = sqrt(ln(K^2/eps)); R0 used sqrt(2 ln(K/eps)) without a matching derivation.
  * Fixed and threshold baselines are now tuned on validation with their own grids
    and the same selection rule as Sugeno (R0 tied them to the Sugeno candidate).
  * Degenerate channels are recorded as infeasible instead of being silently dropped.
  * Scale-invariant numerical thresholds; noise can be read from the dataset.
  * Full transmitter-side runtime, actual-channel check, Wilson and group-bootstrap
    intervals, common-feasible-set power comparison, transfer compatibility check.
No test data are used for any selection.
"""
import argparse
import csv
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

METHODS = ('gaussian', 'fixed', 'threshold', 'sugeno')
ADAPTIVE = ('threshold', 'sugeno')          # methods that need the CSI features
LIMITATIONS = [
    'CSI error is synthetic (circularly symmetric Gaussian, relative variance sigma_rel^2); not estimator residuals',
    'Outage is evaluated under the same simulated error law centred on the estimated channel; the gaussian '
    'guarantee (Proposition 1) holds only under that law',
    'actual_fail uses a single dataset channel per geometry and is a binary check, not an outage estimate',
    'Fuzzy, fixed and threshold radii are heuristic (slab coverage << 1-eps); their reliability is empirical only',
    'Beam directions are fixed RZF on the estimated channel; infeasibility is relative to this beam set and to the '
    'triangle-inequality bound, not a certificate of problem infeasibility',
    'DeepMIMO groups are ordered UE blocks unless replaced by verified spatial blocks',
    'umi_inspired generator is not a TR 38.901 channel simulator',
    'Pooled Wilson intervals ignore clustering by channel; use the group-bootstrap intervals for claims',
]


# ----------------------------------------------------------------------------- I/O
def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def sha_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', encoding='utf8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_csv(path, rows, cols):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def clean(x):
    """JSON-safe float: NaN/inf -> None."""
    if x is None or x == '':
        return None
    x = float(x)
    return x if np.isfinite(x) else None


def load_data(path, M, K):
    d = np.load(path, allow_pickle=False)
    if 'H' not in d:
        raise ValueError('NPZ must contain H')
    H = d['H']
    if H.ndim != 3 or H.shape[1:] != (M, K):
        raise ValueError(f'H must have shape (N,{M},{K}), got {H.shape}')
    if not np.iscomplexobj(H) or not np.isfinite(H).all():
        raise ValueError('H needs finite complex samples')
    if 'groups' not in d:
        raise ValueError('groups is mandatory for disjoint site/scenario split')
    groups = d['groups']
    if groups.ndim != 1 or len(groups) != len(H):
        raise ValueError('groups must be 1-D with one label per channel')
    if len(np.unique(groups)) < 3:
        raise ValueError('at least 3 distinct groups required')
    noise_w = float(d['noise_w']) if 'noise_w' in d else None
    return H, groups, noise_w


def grouped_split(groups, seed):
    """Disjoint 60/20/20 split over group labels (train / validation / test)."""
    uniq = np.unique(groups)
    if len(uniq) < 3:
        raise ValueError('need >= 3 groups for train/validation/test')
    u = np.random.default_rng(seed).permutation(uniq)
    a = max(1, int(.6 * len(u)))
    b = min(max(a + 1, int(.8 * len(u))), len(u) - 1)
    if b <= a:
        raise ValueError('need >= 3 groups for train/validation/test')
    masks = [np.isin(groups, u[lo:hi]) for lo, hi in ((0, a), (a, b), (b, len(u)))]
    if any(not m.any() for m in masks):
        raise ValueError('empty grouped split')
    return masks


# --------------------------------------------------------------------- core model
def rzf(H, reg=.05):
    """Unit-norm RZF directions V = H (H^H H + alpha I)^-1, alpha = reg*tr(H^H H)/K."""
    _, K = H.shape
    G = H.conj().T @ H
    alpha = reg * np.trace(G).real / K
    if not np.isfinite(alpha) or alpha <= 0:
        return None
    try:
        V = H @ np.linalg.solve(G + alpha * np.eye(K), np.eye(K))
    except np.linalg.LinAlgError:
        return None
    norms = np.linalg.norm(V, axis=0)
    if np.min(norms) <= 1e-12 * np.max(norms):
        return None
    return V / norms


def radii(H, q, sigma_rel):
    """r_k = q*s_k with s_k = sigma_rel*||h_k||/sqrt(M), the std of e_k^H v for unit v."""
    M = H.shape[0]
    return q * sigma_rel * np.linalg.norm(H, axis=0) / np.sqrt(M)


def gaussian_q(eps, K):
    """Bonferroni slab radius.

    Under e_k ~ CN(0, s_k^2 I_M) and ||v_j|| = 1, e_k^H v_j ~ CN(0, s_k^2), so
    P(|e_k^H v_j| > q s_k) = exp(-q^2). A union bound over the K^2 slabs gives
    P(e not in U(q)) <= K^2 exp(-q^2) = eps  =>  q = sqrt(ln(K^2/eps)).
    """
    return float(np.sqrt(np.log(K * K / eps)))


def coupling(H, V, q, sigma_rel, sinr, noise):
    """Robust SINR coefficients on the slab set U(q) = {e_k : |e_k^H v_j| <= r_k, all j}.

    On U(q):  |h_k^H v_k| >= |hhat_k^H v_k| - r_k  and  |h_k^H v_j| <= |hhat_k^H v_j| + r_k,
    so p >= F p + u implies SINR_k >= gamma for every user and every e in U(q).
    Returns None when the robust desired gain vanishes (r_k >= |hhat_k^H v_k|).
    """
    gains = np.abs(H.conj().T @ V)                # gains[k, j] = |hhat_k^H v_j|
    r = radii(H, q, sigma_rel)
    dk = gains.diagonal()
    diag = np.maximum(dk - r, 0.) ** 2
    if np.any(diag <= 1e-12 * dk ** 2) or np.any(dk <= 0):
        return None
    upper = (gains + r[:, None]) ** 2
    F = sinr * upper / diag[:, None]
    np.fill_diagonal(F, 0.)
    u = sinr * noise / diag
    return F, u


def power_alloc(H, V, q, cfg):
    """Minimum-power solution of p >= F p + u, 1^T p <= Pmax.

    For non-negative F with spectral radius rho(F) < 1, (I-F)^-1 = sum_n F^n >= 0 and
    p* = (I-F)^-1 u is the component-wise minimal feasible point, hence also the
    minimum-sum-power point. Returns (p or None, rho, reason).
    """
    val = coupling(H, V, q, cfg['sigma_rel'], cfg['sinr'], cfg['noise'])
    if val is None:
        return None, float('inf'), 'robust_desired_gain_zero'
    F, u = val
    rho = float(np.max(np.abs(np.linalg.eigvals(F))))
    if rho >= 1 - 1e-10:
        return None, rho, 'spectral_radius_ge_1'
    try:
        p = np.linalg.solve(np.eye(len(u)) - F, u)
    except np.linalg.LinAlgError:
        return None, rho, 'singular_system'
    scale = max(float(np.max(u)), 1e-300)
    if not np.all(np.isfinite(p)) or np.min(p) < -1e-9 * np.max(np.abs(p)):
        return None, rho, 'numerical'
    p = np.maximum(p, 0.)
    if np.min(p - F @ p - u) < -1e-8 * max(scale, float(np.max(p))):
        return None, rho, 'residual_audit_failed'
    if np.sum(p) > cfg['pmax'] * (1 + 1e-8):
        return None, rho, 'power_gt_pmax'
    return p, rho, 'ok'


def power_lp(H, V, q, cfg):
    """Backward-compatible wrapper: (p or None, rho)."""
    p, rho, _ = power_alloc(H, V, q, cfg)
    return p, rho


def joint_failures(Htrue, V, p, cfg):
    """Number of realisations with SINR_k < gamma for at least one user."""
    Ht = Htrue if Htrue.ndim == 3 else Htrue[None]
    gain = np.abs(np.einsum('nmk,mj->nkj', Ht.conj(), V)) ** 2   # |h_k^H v_j|^2
    desired = p[None, :] * np.diagonal(gain, axis1=1, axis2=2)
    interf = np.einsum('nkj,j->nk', gain, p) - desired + cfg['noise']
    return int(np.sum(np.any(desired < cfg['sinr'] * interf * (1 - 1e-12), axis=1)))


# ----------------------------------------------------------------- fuzzy & rules
def features(H, V, cfg, qref):
    """z1 = log10 cond(Hhat^H Hhat)/8, z2 = rho(F(qref))/2, both clipped to [0, 1]."""
    sv = np.linalg.svd(H.conj().T @ H, compute_uv=False)
    cond = float(sv[0] / max(sv[-1], sv[0] * 1e-16)) if sv[0] > 0 else 1.
    tmp = coupling(H, V, qref, cfg['sigma_rel'], cfg['sinr'], cfg['noise'])
    rho = float(np.max(np.abs(np.linalg.eigvals(tmp[0])))) if tmp is not None else 10.
    return np.array([np.clip(np.log10(max(cond, 1.)), 0, 8) / 8, np.clip(rho / 2, 0, 1)])


def triangle(x, c, w):
    return max(0., 1 - abs(x - c) / w)


def fuzzy_q(z, constants):
    """Zero-order Sugeno, 3x3 triangular sets (centres 0, .5, 1; half-width .55).

    Rule index l = 3*i1 + i2, i1 = set of z1 (conditioning), i2 = set of z2 (coupling).
    For z in [0,1]^2 the nearest centre is within .25 < .55, so sum(w) > 0.
    """
    w = np.array([triangle(z[0], c, .55) * triangle(z[1], d, .55)
                  for c in (0, .5, 1) for d in (0, .5, 1)])
    if w.sum() < 1e-15:
        return float(np.mean(constants))
    return float(np.dot(w, constants) / w.sum())


def choose_q(method, z, param):
    if method == 'gaussian':
        return param['qgauss']
    if method == 'fixed':
        return param['qfixed']
    if method == 'threshold':          # z2 > .5  <=>  rho(F(qref)) > 1
        return param['qlo'] if z[1] > .5 else param['qhi']
    return fuzzy_q(z, param['rules'])


def candidate_grid(qg):
    """Per-method validation grids over the same q range [0.45, 1.8] (6 candidates each)."""
    grid = {'gaussian': [dict(qgauss=qg)],
            'fixed': [dict(qfixed=q) for q in (.45, .65, .85, 1.05, 1.25, 1.45)],
            'threshold': [dict(qlo=lo, qhi=min(lo + d, 1.8))
                          for lo in (.45, .65, .85) for d in (.35, .7)],
            'sugeno': []}
    for qs in (.45, .65, .85):
        for family in ('rise_with_coupling', 'fall_with_coupling'):
            rules = []
            for l in range(9):
                i1, i2 = divmod(l, 3)
                k2 = i2 if family == 'rise_with_coupling' else 2 - i2
                rules.append(float(np.clip(qs + .2 * i1 + .1 * k2, .3, 1.8)))
            grid['sugeno'].append(dict(rules=rules, family=family, qsmall=qs))
    return grid


# ------------------------------------------------------------------- evaluation
def channel_context(H, groups, ii, cfg, seed, n_mc, qref):
    """Estimated channel, beams, features and MC 'true' channels shared by all methods."""
    actual = H[ii]
    M = actual.shape[0]
    s = cfg['sigma_rel']
    rng = np.random.default_rng(np.random.SeedSequence([seed, int(ii), 227]))
    err = (rng.normal(size=actual.shape) + 1j * rng.normal(size=actual.shape)) / np.sqrt(2 * M)
    est = actual + s * np.linalg.norm(actual, axis=0)[None, :] * err
    t0 = time.perf_counter()
    V = rzf(est)
    t_rzf = time.perf_counter() - t0
    ctx = dict(index=int(ii), group=str(groups[ii]), actual=actual, est=est, V=V, t_rzf=t_rzf)
    if V is None:
        return ctx
    t0 = time.perf_counter()
    ctx['z'] = features(est, V, cfg, qref)
    ctx['t_feat'] = time.perf_counter() - t0
    # MC channels drawn around the ESTIMATE with the same relative error law (no use of `actual`).
    rmc = np.random.default_rng(np.random.SeedSequence([seed, int(ii), 921]))
    innov = (rmc.normal(size=(n_mc, *est.shape)) + 1j * rmc.normal(size=(n_mc, *est.shape))) / np.sqrt(2 * M)
    ctx['true'] = est[None] + s * np.linalg.norm(est, axis=0)[None, None, :] * innov
    return ctx


def eval_method(ctx, method, param, cfg, tag):
    base = dict(index=ctx['index'], group=ctx['group'], cohort=tag, method=method)
    if ctx['V'] is None:
        return dict(base, feasible=0, reason='rzf_failed', q='', power_w='', rho='', n_mc=0,
                    failures=0, outage='', actual_fail='', runtime_solver_s='', runtime_total_s='',
                    z1='', z2='')
    t0 = time.perf_counter()
    q = choose_q(method, ctx['z'], param)
    t_inf = time.perf_counter() - t0
    t0 = time.perf_counter()
    p, rho, reason = power_alloc(ctx['est'], ctx['V'], q, cfg)
    t_sol = time.perf_counter() - t0
    total = ctx['t_rzf'] + t_inf + t_sol + (ctx['t_feat'] if method in ADAPTIVE else 0.)
    row = dict(base, reason=reason, q=float(q), rho=clean(rho), runtime_solver_s=t_sol,
               runtime_total_s=total, z1=float(ctx['z'][0]), z2=float(ctx['z'][1]))
    if p is None:
        return dict(row, feasible=0, power_w='', n_mc=0, failures=0, outage='', actual_fail='')
    n_mc = len(ctx['true'])
    fail = joint_failures(ctx['true'], ctx['V'], p, cfg)
    return dict(row, feasible=1, power_w=float(np.sum(p)), n_mc=n_mc, failures=fail,
                outage=fail / n_mc, actual_fail=joint_failures(ctx['actual'], ctx['V'], p, cfg))


def evaluate_batch(H, groups, indices, params, cfg, n_mc, seed, tag):
    out = []
    for ii in indices:
        ctx = channel_context(H, groups, ii, cfg, seed, n_mc, params['qref'])
        out.extend(eval_method(ctx, m, params, cfg, tag) for m in METHODS)
    return out


# ------------------------------------------------------------------- statistics
def wilson(k, n, z=1.959964):
    if n == 0:
        return np.nan, np.nan
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return max(0., c - h), min(1., c + h)


def group_bootstrap(num, grp, reps, seed, den=None):
    """95% percentile CI of sum(num)/sum(den) with whole groups resampled (cluster bootstrap).
    den=None gives the plain mean of `num`."""
    num = np.asarray(num, float)
    den = np.ones_like(num) if den is None else np.asarray(den, float)
    if len(num) == 0 or reps <= 0:
        return np.nan, np.nan
    ug, inv = np.unique(np.asarray(grp), return_inverse=True)
    sn = np.bincount(inv, weights=num, minlength=len(ug))
    sd = np.bincount(inv, weights=den, minlength=len(ug))
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(ug), size=(reps, len(ug)))
    with np.errstate(invalid='ignore', divide='ignore'):
        stat = sn[pick].sum(1) / sd[pick].sum(1)
    stat = stat[np.isfinite(stat)]
    return (np.nan, np.nan) if len(stat) == 0 else tuple(np.percentile(stat, [2.5, 97.5]))


def summarize(rows, reps=0, seed=0):
    ans = []
    for tag in sorted(set(r['cohort'] for r in rows)):
        for method in METHODS:
            rr = [r for r in rows if r['cohort'] == tag and r['method'] == method]
            if not rr:
                continue
            ok = [r for r in rr if int(r['feasible'])]
            eff_vals = [float(r['outage']) if int(r['feasible']) else 1. for r in rr]
            grp = [r['group'] for r in rr]
            nmc = sum(int(r['n_mc']) for r in ok)
            nf = sum(int(r['failures']) for r in ok)
            wl, wh = wilson(nf, nmc)
            el, eh = group_bootstrap(eff_vals, grp, reps, seed)
            cl, ch = group_bootstrap([int(r['failures']) for r in ok], [r['group'] for r in ok], reps, seed + 1,
                                     den=[int(r['n_mc']) for r in ok]) if ok else (np.nan, np.nan)
            ans.append(dict(
                cohort=tag, method=method, n=len(rr), feasible=len(ok), feasible_rate=len(ok) / len(rr),
                mc_samples=nmc, failures=nf,
                conditional_outage=nf / nmc if nmc else np.nan,
                conditional_outage_wilson_lo=wl, conditional_outage_wilson_hi=wh,
                conditional_outage_boot_lo=cl, conditional_outage_boot_hi=ch,
                effective_failure=float(np.mean(eff_vals)), effective_failure_boot_lo=el,
                effective_failure_boot_hi=eh,
                actual_fail_rate=float(np.mean([int(r['actual_fail']) for r in ok])) if ok else np.nan,
                mean_feasible_power_w=float(np.mean([float(r['power_w']) for r in ok])) if ok else np.nan,
                mean_runtime_total_s=float(np.mean([float(r['runtime_total_s']) for r in rr
                                                    if r['runtime_total_s'] != ''] or [np.nan]))))
    return ans


def common_set_power(rows, reps, seed, ref='gaussian'):
    """Per-geometry power ratio vs `ref` on channels feasible for ALL methods."""
    by = {}
    for r in rows:
        by.setdefault(r['index'], {})[r['method']] = r
    common = [i for i, d in by.items() if all(m in d and int(d[m]['feasible']) for m in METHODS)]
    out = []
    for m in METHODS:
        db = [10 * np.log10(float(by[i][m]['power_w']) / float(by[i][ref]['power_w'])) for i in common]
        lo, hi = group_bootstrap(db, [by[i][m]['group'] for i in common], reps, seed)
        out.append(dict(method=m, n_common=len(common), n_total=len(by),
                        mean_power_w=float(np.mean([float(by[i][m]['power_w']) for i in common])) if common else np.nan,
                        mean_db_vs_gaussian=float(np.mean(db)) if common else np.nan,
                        db_boot_lo=lo, db_boot_hi=hi))
    return out


# ------------------------------------------------------------------- selection
def select_method(method, cands, rows_by_cand, target, pmax):
    """Eligible: validation effective failure <= target. Among eligible, minimum mean power on
    the channels feasible for every eligible candidate (common set), so candidates are not
    rewarded for dropping hard channels. Fallback: minimum effective failure, then power."""
    stats = []
    for j, rows in enumerate(rows_by_cand):
        eff = float(np.mean([float(r['outage']) if r['feasible'] else 1. for r in rows]))
        stats.append(dict(candidate=j, params=cands[j], eff=eff,
                          feasible=int(sum(r['feasible'] for r in rows)), n=len(rows),
                          power_all_feasible=clean(np.mean([r['power_w'] for r in rows if r['feasible']]))
                          if any(r['feasible'] for r in rows) else None))
    eligible = [s for s in stats if s['eff'] <= target]
    pool = eligible if eligible else stats
    feas = [{r['index'] for r in rows_by_cand[s['candidate']] if r['feasible']} for s in pool]
    common = set.intersection(*feas) if feas else set()
    for s in stats:
        rows = rows_by_cand[s['candidate']]
        if common:
            s['power_common'] = float(np.mean([r['power_w'] for r in rows if r['index'] in common]))
        else:     # no common set: penalise infeasible channels with Pmax
            s['power_common'] = float(np.mean([r['power_w'] if r['feasible'] else pmax for r in rows]))
        s['n_common'] = len(common)
    if eligible:
        best = min(eligible, key=lambda s: (s['power_common'], s['candidate']))
    else:
        best = min(stats, key=lambda s: (s['eff'], s['power_common'], s['candidate']))
    return best, stats, bool(eligible)


# ------------------------------------------------------------------------ main
PHYSICAL = ('M', 'K', 'sigma_rel', 'sinr_db', 'eps')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--stage', choices=['preflight', 'develop', 'freeze', 'test', 'report', 'all'], required=True)
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--out-root', default='outputs')
    ap.add_argument('--M', type=int, default=8)
    ap.add_argument('--K', type=int, default=4)
    ap.add_argument('--sigma-rel', type=float, default=.04, help='relative CSI error std')
    ap.add_argument('--sinr-db', type=float, default=6.)
    ap.add_argument('--noise', type=float, default=None,
                    help='receiver noise power [W]; default: dataset noise_w if present, else 1e-9')
    ap.add_argument('--pmax', type=float, default=1., help='total transmit power budget [W]')
    ap.add_argument('--eps', type=float, default=.05, help='joint outage target of the gaussian baseline')
    ap.add_argument('--select-target', type=float, default=.10,
                    help='validation effective-failure ceiling used for candidate selection')
    ap.add_argument('--seed', type=int, default=20261019)
    ap.add_argument('--n-mc', type=int, default=300)
    ap.add_argument('--boot', type=int, default=2000, help='group-bootstrap replicates (report only)')
    ap.add_argument('--limit', type=int, default=0, help='smoke tests only')
    ap.add_argument('--frozen-from', default='')
    a = ap.parse_args()

    if not (0 < a.sigma_rel < 1 and a.pmax > 0 and a.n_mc >= 1 and 0 < a.eps < 1
            and 0 < a.select_target <= 1 and a.M >= a.K >= 1 and a.limit >= 0 and a.boot >= 0):
        ap.error('invalid physical, statistical or MC arguments')
    if a.noise is not None and a.noise <= 0:
        ap.error('--noise must be > 0')

    dataset = Path(a.dataset).resolve()
    H, groups, noise_ds = load_data(dataset, a.M, a.K)
    noise = a.noise if a.noise is not None else (noise_ds if noise_ds is not None else 1e-9)
    masks = grouped_split(groups, a.seed)
    cfg = dict(sigma_rel=a.sigma_rel, sinr=10 ** (a.sinr_db / 10), noise=noise, pmax=a.pmax)
    qg = gaussian_q(a.eps, a.K)

    root = Path(a.out_root) / a.run_id
    root.mkdir(parents=True, exist_ok=True)
    settings = {k: v for k, v in vars(a).items()
                if k not in ('stage', 'out_root', 'run_id', 'dataset', 'frozen_from', 'boot', 'noise')}
    settings['noise_w'] = noise
    settings['frozen_from_sha256'] = sha(a.frozen_from) if a.frozen_from else ''
    sigdata = dict(code_sha256=sha(__file__), dataset_sha256=sha(dataset), settings=settings, n=len(H),
                   group_counts=[int(m.sum()) for m in masks])
    signature = sha_obj(sigdata)
    manifest = root / 'cp00_manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['signature'] != signature:
            raise RuntimeError('Manifest signature mismatch: use a new run-id (code, data or settings changed)')
    else:
        atomic_json(manifest, dict(signature=signature, dataset_path=str(dataset), **sigdata))
    if a.stage == 'preflight':
        print('PASS grouped split (train/val/test channels):', sigdata['group_counts'], '| noise_w =', noise)
        return

    def lim(x):
        return x[:a.limit] if a.limit else x
    validx, testidx = lim(np.flatnonzero(masks[1])), lim(np.flatnonzero(masks[2]))
    physical = {k: settings[k] for k in PHYSICAL}

    if a.stage in ('develop', 'all'):
        if len(validx) == 0:
            raise RuntimeError('empty validation set')
        grid = candidate_grid(qg)
        res = {m: [[] for _ in grid[m]] for m in METHODS}
        nmc = min(a.n_mc, 300)
        for ii in validx:                       # one context per channel, shared by all candidates
            ctx = channel_context(H, groups, ii, cfg, a.seed + 501, nmc, qg)
            for m in METHODS:
                for j, c in enumerate(grid[m]):
                    res[m][j].append(eval_method(ctx, m, c, cfg, 'validation'))
        cp01 = {}
        for m in METHODS:
            best, stats, elig = select_method(m, grid[m], res[m], a.select_target, a.pmax)
            cp01[m] = dict(selected=best['candidate'], eligible=elig, candidates=stats)
        atomic_json(root / 'cp01_candidates.json', dict(signature=signature, qref=qg, methods=cp01))

    if a.stage in ('freeze', 'all'):
        c1 = json.loads((root / 'cp01_candidates.json').read_text())
        if c1.get('signature') != signature:
            raise RuntimeError('cp01 signature mismatch: rerun --stage develop')
        params = dict(qref=c1['qref'])
        per = {}
        for m in METHODS:
            st = c1['methods'][m]
            s = st['candidates'][st['selected']]
            params.update({k: v for k, v in s['params'].items() if k in ('qgauss', 'qfixed', 'qlo', 'qhi', 'rules')})
            per[m] = dict(s, eligible=st['eligible'])
        atomic_json(root / 'cp02_frozen.json', dict(
            signature=signature, physical=physical, selected=dict(params=params, per_method=per),
            criterion=f'per method: validation effective failure <= {a.select_target}, then minimum mean power on '
                      'the common feasible set of eligible candidates; fallback minimum effective failure'))

    if a.stage in ('test', 'all'):
        if a.frozen_from:
            f = json.loads(Path(a.frozen_from).read_text())
            if 'selected' not in f or 'physical' not in f or 'qref' not in f['selected'].get('params', {}):
                raise RuntimeError('External frozen file is from an older revision (no physical settings/qref); '
                                   'rerun develop+freeze on the source dataset')
            bad = {k: (f['physical'][k], physical[k]) for k in PHYSICAL if f['physical'].get(k) != physical[k]}
            if bad:
                raise RuntimeError(f'Transfer settings differ from frozen source: {bad}')
            atomic_json(root / 'cp02_frozen.json', dict(
                signature=signature, physical=physical, selected=f['selected'],
                transferred_from=str(Path(a.frozen_from).resolve()), transferred_sha256=sha(a.frozen_from),
                criterion='external frozen transfer: no tuning on this dataset'))
        f = json.loads((root / 'cp02_frozen.json').read_text())
        if f['signature'] != signature:
            raise RuntimeError('cp02 signature mismatch')
        par = f['selected']['params']
        fsha = sha_obj(par)
        dest = root / 'tasks' / 'test'
        for i in testidx:
            fp = dest / f'{i:07d}.json'
            if fp.exists():
                o = json.loads(fp.read_text())
                if o['signature'] == signature and o.get('frozen_sha') == fsha and o['complete']:
                    continue
                raise RuntimeError(f'Task checkpoint mismatch: {fp}')
            rows = evaluate_batch(H, groups, [i], par, cfg, a.n_mc, a.seed, 'test')
            atomic_json(fp, dict(signature=signature, frozen_sha=fsha, complete=True,
                                 rows=[{k: (clean(v) if isinstance(v, float) else v) for k, v in r.items()}
                                       for r in rows]))

    if a.stage in ('report', 'all'):
        f = json.loads((root / 'cp02_frozen.json').read_text())
        fsha = sha_obj(f['selected']['params'])
        rows = []
        for i in testidx:
            p = root / 'tasks' / 'test' / f'{i:07d}.json'
            if not p.exists():
                raise RuntimeError(f'Missing checkpoint: {p}')
            x = json.loads(p.read_text())
            if not (x['signature'] == signature and x.get('frozen_sha') == fsha and x['complete']):
                raise RuntimeError(f'Checkpoint mismatch: {p}')
            rows.extend({k: ('' if v is None else v) for k, v in r.items()} for r in x['rows'])
        if not rows:
            raise RuntimeError('no test rows')
        atomic_csv(root / 'cp03_test_geometry.csv', rows, list(rows[0]))
        summary = summarize(rows, a.boot, a.seed)
        atomic_csv(root / 'cp04_test_summary.csv', summary, list(summary[0]))
        cs = common_set_power(rows, a.boot, a.seed + 7)
        atomic_csv(root / 'cp06_common_set_power.csv', cs, list(cs[0]))
        reasons = {}
        for r in rows:
            if not int(r['feasible']):
                reasons.setdefault(r['method'], {}).setdefault(r['reason'], 0)
                reasons[r['method']][r['reason']] += 1
        atomic_json(root / 'cp05_scope.json', dict(
            signature=signature, dataset=str(dataset), noise_w=noise, qgauss=qg, eps=a.eps,
            test_groups=int(len(np.unique(groups[masks[2]]))), test_geometries=int(len(testidx)),
            limited=bool(a.limit), infeasible_reasons=reasons, frozen=f, limitations=LIMITATIONS))
        print(json.dumps([{k: (round(v, 6) if isinstance(v, float) else v) for k, v in s.items()
                           if k in ('method', 'feasible', 'n', 'conditional_outage', 'effective_failure',
                                    'mean_feasible_power_w')} for s in summary], indent=1))


if __name__ == '__main__':
    main()
