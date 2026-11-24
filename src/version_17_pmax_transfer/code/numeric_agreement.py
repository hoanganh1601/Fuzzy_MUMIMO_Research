#!/usr/bin/env python3
"""V16.1/V16.2: floating-point-aware agreement between a compiled decision and the Python oracle.

Why this exists
---------------
The compiled solver (native/screen_core.c) and the Python reference (robust_model.solve) evaluate the
same formulas with a different summation order. For an ill-conditioned candidate the total power
p_req = 1^T (I - F)^{-1} u is very sensitive to the last bits of the channel. The dominant mechanism is
the robust direct gain a_k = (g_kk - r_k)^2: when g_kk is only slightly above the CSI radius r_k, the
subtraction cancels most significant digits, so a relative rounding difference of 1e-16 in g_kk becomes
a relative difference of about 2 g_kk / (g_kk - r_k) * 1e-16 in a_k and hence in p_req.
A fixed relative tolerance (1e-7 in run_experiment.same_choice) then reports a "mismatch" although both
implementations are correct to floating-point accuracy.

Rule (predeclared, applied only when the strict same_choice test fails)
----------------------------------------------------------------------
1. Same decision (cardinality, subset, alpha), power differs:
   accept iff |p_c - p_py| <= max(1e-7 * p, FACTOR * spread), where spread is the largest change of
   p_py when every channel entry is perturbed by a relative PERTURB (a few units in the last place,
   DRAWS draws, fixed seed). Event type POWER_WITHIN_FP_SENSITIVITY, otherwise POWER_MISMATCH.
2. Different decision:
   TIE      : same cardinality, both candidates feasible in Python, and
              |p_got - p_ref| <= max(1e-9 * p, FACTOR * (spread_got + spread_ref))  (tie rule 1e-9);
   BOUNDARY : one of the two candidates sits on a feasibility boundary within its sensitivity:
              |p - pmax| <= FACTOR * spread + 1e-9 * pmax, or |rho - (1 - 1e-10)| <= 1e-8.
   Otherwise DECISION_MISMATCH.
Every accepted case is returned as an event and must be reported (CC06 + CC04). Hard mismatches stop the run.
The Python core modules (robust_model.py, run_experiment.py, ...) are NOT modified.
"""
import numpy as np
from robust_model import solve, get_beam
from run_experiment import same_choice

REL_TOL = 1e-7          # = run_experiment.same_choice
TIE_TOL = 1e-9          # = tie rule of the search
PERTURB = 2e-15         # relative perturbation of each channel entry (about 9 ulps)
DRAWS = 16
FACTOR = 4.0
RHO_EDGE = 1 - 1e-10


def _users(label):
    return [int(c) for c in label]


def candidate_profile(h, label, alpha, cfg, seed=0):
    """Python status/power/rho of one candidate, its floating-point sensitivity and its direct-gain margin."""
    h = np.asarray(h, dtype=np.complex128); users = _users(label); base = solve(h, users, alpha, cfg)
    p0, rho = base['p_req_w'], base['rho']
    rng = np.random.default_rng(seed); dp = []; drho = []
    for _ in range(DRAWS):
        d = (rng.standard_normal(h.shape) + 1j * rng.standard_normal(h.shape)) * PERTURB
        r = solve(h * (1 + d), users, alpha, cfg)
        if p0 is not None and r['p_req_w'] is not None: dp.append(abs(r['p_req_w'] - p0))
        if rho is not None and r['rho'] is not None: drho.append(abs(r['rho'] - rho))
    margin = None
    W = get_beam(h[:, users], alpha)
    if W is not None:
        hs = h[:, users]; g = np.abs(np.diag(hs.conj().T @ W))
        rad = cfg['q'] * cfg['sigma'] * np.linalg.norm(hs, axis=0) / np.sqrt(h.shape[0])
        margin = float(np.min((g - rad) / g))
    return {'status': base['status'], 'p': p0, 'rho': rho, 'p_spread': max(dp) if dp else None,
            'rho_spread': max(drho) if drho else None, 'direct_gain_margin': margin}


def _on_boundary(pr, cfg):
    if pr['p'] is not None and pr['p_spread'] is not None and abs(pr['p'] - cfg['pmax']) <= FACTOR * pr['p_spread'] + 1e-9 * cfg['pmax']:
        return True
    if pr['rho'] is not None and abs(pr['rho'] - RHO_EDGE) <= max(1e-8, FACTOR * (pr['rho_spread'] or 0.0)):
        return True
    return False


def agree(got, ref, h, alphas, cfg, seed=0):
    """Return (ok, event). event is None when the strict test passes; otherwise a dict to be logged."""
    h = np.asarray(h, dtype=np.complex128)   # V16.2: sensitivity must be measured in double precision
    if same_choice(got, ref): return True, None
    ev = {'got': got, 'ref': ref}
    if got is None or ref is None:
        ev['type'] = 'DECISION_MISMATCH'; return False, ev
    same_dec = (got['cardinality'] == ref['cardinality'] and got['subset'] == ref['subset'] and got['alpha'] == ref['alpha'])
    if same_dec:
        pr = candidate_profile(h, ref['subset'], ref['alpha'], cfg, seed)
        diff = abs(got['p_req_w'] - ref['p_req_w']); p = max(abs(ref['p_req_w']), 1e-30)
        tol = max(REL_TOL * p, FACTOR * (pr['p_spread'] or 0.0))
        ev.update(type='POWER_WITHIN_FP_SENSITIVITY' if diff <= tol else 'POWER_MISMATCH', rel_diff=diff / p,
                  rel_spread=(pr['p_spread'] or 0.0) / p, direct_gain_margin=pr['direct_gain_margin'], rho=pr['rho'])
        return diff <= tol, ev
    pg = candidate_profile(h, got['subset'], got['alpha'], cfg, seed)
    pf = candidate_profile(h, ref['subset'], ref['alpha'], cfg, seed + 1)
    ev.update(got_profile=pg, ref_profile=pf)
    if (got['cardinality'] == ref['cardinality'] and pg['status'] == 'FEASIBLE' and pf['status'] == 'FEASIBLE'):
        p = max(abs(pf['p']), 1e-30)
        tol = max(TIE_TOL * p, FACTOR * ((pg['p_spread'] or 0.0) + (pf['p_spread'] or 0.0)))
        if abs(pg['p'] - pf['p']) <= tol:
            ev.update(type='TIE_WITHIN_FP_SENSITIVITY', rel_diff=abs(pg['p'] - pf['p']) / p); return True, ev
    if _on_boundary(pg, cfg) or _on_boundary(pf, cfg):
        ev['type'] = 'BOUNDARY_WITHIN_FP_SENSITIVITY'; return True, ev
    ev['type'] = 'DECISION_MISMATCH'; return False, ev
