#!/usr/bin/env python3
"""V15.2: predictable computational break-even of PRE-BEAM feasibility screening.

V15.2 adds (relative to V15.1), all predeclared and part of the run signature:
  * Primary endpoints P1-P4 are evaluated INSIDE the predicted region (test
    geometries whose K_max cell is locked to a non-CARD policy); outcome
    INCONCLUSIVE when the region has too few groups (covariate shift is reported,
    not mistaken for a refutation). V15.1 all-geometry endpoints stay secondary.
  * Stage test-preflight: covariate-only check of a candidate test set (early_ratio
    cells under the frozen lock), BEFORE any runtime is measured; every attempt is
    appended to TEST_SELECTION_LOG.csv. Stage test refuses a set that failed it.
  * Fit/validation split stratified by the K_max early_ratio cell; larger
    development set (>= 80 groups, >= 20 power-limited groups by default).

V15.1 notes:

Physics and oracle: robust_model.solve/get_beam (unchanged); fixed CSI radius q.
Policies: CARD (cardinality-ordered baseline), EARLY (pre-beam robust noise bound),
CACHED (post-beam certificates on shared coefficients), HYBRID (EARLY+CACHED).

Changes relative to V15 (all predeclared, locked before any test data are read):
  * Policy cells are (K, L, early_ratio bin); early_ratio is the quantity EARLY tests.
  * EARLY uses the robust bound (||h||-r)^2 by default (valid, tighter than ||h||^2).
  * Primary decision per test source = break-even at K_max + increasing trend in K
    + predictability on activated geometries + exactness. A combine stage requires
    GO on both DeepMIMO and 3GPP with the same frozen lock.
  * Machine/library/thread information is part of the signature (runtime is
    machine-specific); BLAS threads pinned to 1; UTF-8 file I/O; deterministic
    tie-break; development group count checked at develop/lock.
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ.setdefault(_v, '1')  # must precede the NumPy import; recorded in the manifest
import argparse, csv, hashlib, itertools, json, math, platform, sys, time
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
import scipy
from robust_model import solve, get_beam, digest, jwrite, cwrite
from certified_screening import build_Fu
from screening_policy import early_bound, post_bound, from_comp, group_ci

VERSION = 'V15.2'
HERE = Path(__file__).resolve().parent
SOURCES = ['run_experiment.py', 'robust_model.py', 'screening_policy.py', 'certified_screening.py', 'screening_bounds.py']
POLICIES = ('CARD', 'EARLY', 'CACHED', 'HYBRID')
TIE_REL = 1e-9
ER_CAP = 1e12


def utf8_console():
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError): pass


def rjson(p): return json.loads(Path(p).read_text(encoding='utf8'))
def sha_text(x): return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
def raw_h(h): return hashlib.sha256(np.ascontiguousarray(h).tobytes()).hexdigest()


def machine_info():
    """Runtime is only comparable on the same machine and software stack."""
    return {'platform': platform.platform(), 'machine': platform.machine(), 'processor': platform.processor(),
            'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__,
            'cpu_count': os.cpu_count(),
            'threads': {v: os.environ.get(v) for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}}


def load_any(path):
    with np.load(path, allow_pickle=False) as f:
        H = f['H']; G = f['groups']; meta = {z: f[z].tolist() for z in ('scenario',) if z in f.files}
    if H.ndim != 3 or H.shape[0] != len(G) or H.shape[1] < 8 or H.shape[2] < 8:
        raise ValueError('H must be complex (N,M,>=8), M>=8, with groups (N,)')
    if not np.iscomplexobj(H) or not np.isfinite(H).all(): raise ValueError('H must be finite complex')
    if len(np.unique(G)) < 4: raise ValueError('Need >=4 distinct groups')
    return H, G, meta


def cfg(a): return {'q': a.q, 'sigma': a.sigma_rel, 'gamma': 10**(a.sinr_db/10), 'noise': a.noise, 'pmax': a.pmax}


def er_bins(a):
    b = tuple(float(v) for v in a.er_bins.split(','))
    if not b or any(x <= 0 for x in b) or list(b) != sorted(set(b)): raise ValueError('--er-bins must be increasing positive values')
    return b


def configs(a):
    ks = sorted(set(int(v) for v in a.ks.split(',')))
    if any(k not in (4, 6, 8) for k in ks) or not ks: raise ValueError('K must be subset of 4,6,8')
    alphas = tuple(dict.fromkeys(float(v) for v in a.alphas.split(',')))
    if len(alphas) < max(a.beam_counts) or min(alphas) < 0 or alphas[0] != 0.: raise ValueError('alpha-list must begin 0, >=max beam-count, >=0')
    if a.repeats < 2 or a.bootstrap < 100 or a.q < 0 or a.sigma_rel <= 0 or a.noise <= 0 or a.pmax <= 0 or a.guard <= 0:
        raise ValueError('Invalid parameters')
    if not (0 <= a.min_rel_gain < 1): raise ValueError('--min-rel-gain must be in [0,1)')
    er_bins(a)
    return [(k, l, alphas[:l]) for k in ks for l in a.beam_counts]


def bin_label(er, bins): return f'ER{sum(er >= b for b in bins)}'


def channel_features(h, c, robust, bins):
    """early_ratio = sum_k gamma*N0/g_k / Pmax with the SAME g_k used by EARLY.
    early_ratio > 1 means the full user set is already rejected before beam generation."""
    nrm = np.linalg.norm(h, axis=0)
    v = h / np.maximum(nrm, 1e-30)[None, :]
    cr = np.abs(v.conj().T @ v); np.fill_diagonal(cr, 0.)
    coherence = float(np.max(cr)) if h.shape[1] > 1 else 0.
    if robust:
        r = c['q'] * c['sigma'] * nrm / np.sqrt(h.shape[0]); g = np.maximum(nrm - r, 0.)**2
    else:
        g = nrm**2
    er = ER_CAP if np.any(g <= 1e-300) else min(ER_CAP, float(np.sum(c['gamma'] * c['noise'] / g) / c['pmax']))
    return {'coherence': coherence, 'early_ratio': er, 'cell': bin_label(er, bins)}


def key(k, l, d): return f'K{k}_L{l}_{d}'


def pick(cands):
    """Deterministic lexicographic choice: max cardinality; min power with relative
    ties <= TIE_REL treated as equal; then smaller alpha (ZF first); then subset label."""
    if not cands: return None
    cmax = max(c['cardinality'] for c in cands)
    top = [c for c in cands if c['cardinality'] == cmax]
    pmin = min(c['p_req_w'] for c in top)
    return min([c for c in top if c['p_req_w'] <= pmin * (1 + TIE_REL)], key=lambda c: (c['alpha'], c['subset']))


def same_choice(x, y):
    if x is None or y is None: return x is None and y is None
    return (x['cardinality'] == y['cardinality'] and x['subset'] == y['subset'] and x['alpha'] == y['alpha'] and
            abs(x['p_req_w'] - y['p_req_w']) <= 1e-7 * max(1e-18, abs(x['p_req_w']), abs(y['p_req_w'])))


def search(h, alphas, c, policy, guard, robust=True, profile=False):
    """Cardinality-ordered search over remaining candidates; beams recomputed per subset."""
    k = h.shape[1]; met = defaultdict(float); trace = []
    for size in range(k, 0, -1):
        feasible = []
        for subset in itertools.combinations(range(k), size):
            skip = False; early_t = 0.; r_early = ''
            if policy in ('EARLY', 'HYBRID'):
                st = time.perf_counter_ns(); skip, r_early, unc, lb = early_bound(h, subset, c, guard, robust); early_t = (time.perf_counter_ns() - st) / 1e6
                met['early_ms'] += early_t; met['fail_open'] += int(unc)
            for alpha in alphas:
                met['candidates_seen'] += 1
                if skip:
                    met['early_rejects'] += 1
                    if profile: trace.append({'subset': ''.join(map(str, subset)), 'alpha': alpha, 'reject_stage': 'prebeam', 'solve_ms': 0., 'screen_ms': early_t / len(alphas), 'reason': r_early})
                    continue
                post_ms = 0.; solver_ms = 0.
                if policy in ('CACHED', 'HYBRID'):
                    st = time.perf_counter_ns(); comp = build_Fu(h, subset, alpha, c); beam_ms = (time.perf_counter_ns() - st) / 1e6
                    met['beam_ms'] += beam_ms
                    st = time.perf_counter_ns(); drop, reason, unc = post_bound(comp, c, guard); post_ms = (time.perf_counter_ns() - st) / 1e6
                    met['screen_ms'] += post_ms; met['fail_open'] += int(unc)
                    if drop:
                        met['post_rejects'] += 1
                        if profile: trace.append({'subset': ''.join(map(str, subset)), 'alpha': alpha, 'reject_stage': 'postbeam', 'solve_ms': 0., 'screen_ms': post_ms, 'reason': reason})
                        continue
                    st = time.perf_counter_ns(); r = from_comp(comp, c); solver_ms = (time.perf_counter_ns() - st) / 1e6
                else:
                    st = time.perf_counter_ns(); r = solve(h, list(subset), alpha, c); solver_ms = (time.perf_counter_ns() - st) / 1e6
                met['solve_ms'] += solver_ms; met['full_calls'] += 1
                if profile: trace.append({'subset': ''.join(map(str, subset)), 'alpha': alpha, 'reject_stage': 'none', 'solve_ms': solver_ms, 'screen_ms': post_ms, 'reason': r['status']})
                if r['status'] == 'FEASIBLE': feasible.append({'subset': ''.join(map(str, subset)), 'alpha': alpha, 'cardinality': size, 'p_req_w': float(r['p_req_w'])})
        if feasible: return pick(feasible), dict(met), trace
    return None, dict(met), trace


def independent_oracle(h, alphas, c):
    """Independent all-subsets/all-beams reference; never uses screening decisions."""
    k = h.shape[1]; winners = []; n = 0
    for size in range(1, k + 1):
        for subset in itertools.combinations(range(k), size):
            for alpha in alphas:
                n += 1; r = solve(h, list(subset), alpha, c)
                if r['status'] == 'FEASIBLE':
                    winners.append({'subset': ''.join(map(str, subset)), 'alpha': alpha, 'cardinality': size, 'p_req_w': float(r['p_req_w'])})
    return pick(winners), n


def process_one(h, group, geometry, k, l, alphas, c, guard, repeats, seed, profile, robust, bins):
    h = h[:, :k]; st = time.perf_counter_ns(); z = channel_features(h, c, robust, bins)
    feature_ms = (time.perf_counter_ns() - st) / 1e6
    rows = []; traces = []
    oracle, n_oracle = independent_oracle(h, alphas, c)
    for rep in range(repeats):
        order = list(POLICIES); np.random.default_rng(seed + geometry * 71 + rep * 131 + k * 37 + l).shuffle(order)
        for pol in order:
            st = time.perf_counter_ns(); x, met, trace = search(h, alphas, c, pol, guard, robust, profile=profile and rep == 0)
            ms = (time.perf_counter_ns() - st) / 1e6
            if not same_choice(x, oracle): raise AssertionError(f'Oracle mismatch geometry={geometry}, K={k}, L={l}, policy={pol}')
            rows.append({'geometry': geometry, 'group': str(group), 'K': k, 'L': l, 'cell': z['cell'],
                         'early_ratio': z['early_ratio'], 'coherence': z['coherence'], 'feature_ms': feature_ms,
                         'oracle_candidates': n_oracle, 'rep': rep, 'policy': pol,
                         'runtime_ms': ms, 'calls': met.get('full_calls', 0), 'candidates_seen': met.get('candidates_seen', 0),
                         'early_rejects': met.get('early_rejects', 0), 'post_rejects': met.get('post_rejects', 0),
                         'early_ms': met.get('early_ms', 0.), 'beam_ms': met.get('beam_ms', 0.),
                         'screen_ms': met.get('screen_ms', 0.), 'solve_ms': met.get('solve_ms', 0.),
                         'oracle_match': 1, 'served': oracle['cardinality'] if oracle else 0})
            if profile and rep == 0:
                for t in trace: traces.append({'geometry': geometry, 'group': str(group), 'K': k, 'L': l, 'policy': pol, **t})
    if profile:
        # Candidate-level diagnostic outside the benchmark clock; never used for rule selection on test.
        for size in range(k, 0, -1):
            for sub in itertools.combinations(range(k), size):
                st = time.perf_counter_ns(); early_drop, early_why, _, _ = early_bound(h, sub, c, guard, robust); early_ms = (time.perf_counter_ns() - st) / 1e6 / len(alphas)
                for alpha in alphas:
                    st = time.perf_counter_ns(); r = solve(h, list(sub), alpha, c); solver_ms = (time.perf_counter_ns() - st) / 1e6
                    st = time.perf_counter_ns(); comp = build_Fu(h, sub, alpha, c); beam_ms = (time.perf_counter_ns() - st) / 1e6
                    st = time.perf_counter_ns(); post_drop, post_why, _ = post_bound(comp, c, guard); post_ms = (time.perf_counter_ns() - st) / 1e6
                    if r['status'] == 'FEASIBLE' and (early_drop or post_drop): raise AssertionError('False certificate in full candidate profiling')
                    traces.append({'geometry': geometry, 'group': str(group), 'K': k, 'L': l, 'policy': 'CANDIDATE_ORACLE',
                                   'subset': ''.join(map(str, sub)), 'alpha': alpha, 'oracle_status': r['status'],
                                   'reject_stage': 'early' if early_drop else ('post' if post_drop else 'none'),
                                   'reason': early_why if early_drop else post_why, 'early_screen_ms': early_ms,
                                   'beam_ms': beam_ms, 'post_screen_ms': post_ms, 'solve_ms': solver_ms,
                                   'false_reject': 0})
    return rows, traces


def write_rows(path, rows):
    if not rows: raise ValueError('Empty output: ' + str(path))
    cwrite(path, rows, list(dict.fromkeys(k for row in rows for k in row.keys())))


def summary_from_rows(rows):
    by = defaultdict(list)
    for r in rows: by[(r['geometry'], r['K'], r['L'])].append(r)
    out = []
    for (geom, k, l), rr in sorted(by.items()):
        base = float(np.median([r['runtime_ms'] for r in rr if r['policy'] == 'CARD'])); z = rr[0]
        card_calls = next(v['calls'] for v in rr if v['policy'] == 'CARD')
        for pol in POLICIES[1:]:
            pp = [r for r in rr if r['policy'] == pol]
            val = float(np.median([r['runtime_ms'] for r in pp]))
            out.append({'geometry': geom, 'group': z['group'], 'K': k, 'L': l, 'cell': z['cell'],
                        'early_ratio': z['early_ratio'], 'coherence': z['coherence'], 'policy': pol, 'card_ms': base, 'policy_ms': val,
                        'feature_ms': float(z['feature_ms']), 'saving_ms': base - val - float(z['feature_ms']),
                        'calls_saved': card_calls - pp[0]['calls']})
    return out


def split_groups(G, seed):
    groups = sorted(set(map(str, G))); np.random.default_rng(seed).shuffle(groups)
    n = max(1, int(.6 * len(groups)))
    return set(groups[:n]), set(groups[n:])


def top_cell(a): return f'ER{len(er_bins(a))}'


def group_cells(H, G, a):
    """Cell of each group at K_max (majority over its geometries). Covariate only."""
    kmax = max(int(v) for v in a.ks.split(',')); c = cfg(a); robust = a.early_bound == 'robust'; bins = er_bins(a)
    by = defaultdict(list)
    for h, g in zip(H, G): by[str(g)].append(channel_features(h[:, :kmax], c, robust, bins)['cell'])
    return {g: Counter(v).most_common(1)[0][0] for g, v in by.items()}


def stratified_split(H, G, a):
    """60/40 fit/validation split of groups, stratified by K_max early_ratio cell, so
    that every cell receives validation groups in proportion to its size."""
    gc = group_cells(H, G, a); rng = np.random.default_rng(a.seed); fit = set(); valid = set()
    for cell in sorted(set(gc.values())):
        gs = sorted(g for g, c_ in gc.items() if c_ == cell); rng.shuffle(gs)
        n = int(math.ceil(.6 * len(gs))) if len(gs) > 1 else 1
        fit |= set(gs[:n]); valid |= set(gs[n:])
    return fit, valid, gc


def region_geometries(rows, kmax):
    """Predicted region: geometries whose K_max cell is locked to a non-CARD policy for at least one L."""
    return sorted({r['geometry'] for r in rows if r['K'] == kmax and r['selected_policy'] != 'CARD'})


def region_tests(selected, paired, a, nviol):
    """V15.2 primary endpoints for ONE test source, inside the predicted region R.
    Gate: R must contain >= min_region_groups groups, otherwise INCONCLUSIVE.
    P1 break-even in R at K_max: CI_lo(mean relative saving of the frozen map) > min_rel_gain
       and CI_lo(mean absolute saving per (K,L) configuration) > min_gain_ms.
    P2 trend of pre-beam screening in R: CI_lo(mean paired difference of EARLY relative
       saving, K_max minus K_min) > 0 (EARLY is predeclared, not selected on test).
    P3 exactness: no oracle mismatch.
    P4 no missed gain outside R (falsification test): fails only if there is evidence that
       pre-beam screening would have paid outside R, i.e. CI_lo(mean EARLY absolute saving at
       K_max) >= min_gain_ms (not evaluable with < 3 groups outside R; then it does not block GO).
    Relative saving per geometry and K = sum_L saving / sum_L CARD runtime."""
    ks = sorted(set(r['K'] for r in selected)); kmin, kmax = ks[0], ks[-1]
    grp = {r['geometry']: r['group'] for r in selected}
    R = region_geometries(selected, kmax); Rset = set(R); out_geos = sorted(g for g in grp if g not in Rset)
    fr = defaultdict(lambda: [0., 0., 0]); ea = defaultdict(lambda: [0., 0., 0])
    for r in selected:
        x = fr[(r['geometry'], r['K'])]; x[0] += r['saved_ms']; x[1] += r['card_ms']; x[2] += 1
    for r in paired:
        if r['policy'] == 'EARLY':
            x = ea[(r['geometry'], r['K'])]; x[0] += r['saving_ms']; x[1] += r['card_ms']; x[2] += 1
    rel = lambda d, g, k: d[(g, k)][0] / d[(g, k)][1] if d[(g, k)][1] > 0 else 0.
    ab = lambda d, g, k: d[(g, k)][0] / max(d[(g, k)][2], 1)
    def ci(vals, geos, s):
        gg = [grp[g] for g in geos]
        return group_ci(vals, gg, a.bootstrap, seed=a.seed + s) if len(set(gg)) >= 3 else (None, None)
    n_region_groups = len({grp[g] for g in R})
    by_k = []
    for i, k in enumerate(ks):
        fv = [rel(fr, g, k) for g in R]; ev = [rel(ea, g, k) for g in R]; av = [ab(fr, g, k) for g in R]
        c1 = ci(fv, R, 101 + i); c2 = ci(ev, R, 121 + i); c3 = ci(av, R, 141 + i)
        by_k.append({'K': k, 'region_geometries': len(R),
                     'frozen_rel_saved': float(np.mean(fv)) if R else None, 'frozen_rel_ci_lo': c1[0], 'frozen_rel_ci_hi': c1[1],
                     'frozen_abs_saved_ms': float(np.mean(av)) if R else None, 'frozen_abs_ci_lo': c3[0], 'frozen_abs_ci_hi': c3[1],
                     'early_rel_saved': float(np.mean(ev)) if R else None, 'early_rel_ci_lo': c2[0], 'early_rel_ci_hi': c2[1]})
    top = by_k[-1]
    p1 = (top['frozen_rel_ci_lo'] is not None and top['frozen_rel_ci_lo'] > a.min_rel_gain and
          top['frozen_abs_ci_lo'] is not None and top['frozen_abs_ci_lo'] > a.min_gain_ms)
    d = [rel(ea, g, kmax) - rel(ea, g, kmin) for g in R]; dc = ci(d, R, 161)
    p2 = kmax > kmin and dc[0] is not None and dc[0] > 0
    ov = [ab(ea, g, kmax) for g in out_geos]; oc = ci(ov, out_geos, 181)
    p4 = None if oc[0] is None else bool(oc[0] < a.min_gain_ms)
    p3 = nviol == 0
    gate = n_region_groups >= a.min_region_groups
    reasons = [n for n, ok in (('P1_no_break_even_in_region', p1), ('P2_no_increasing_trend_in_region', p2),
                               ('P3_oracle_mismatch', p3), ('P4_screening_would_pay_outside_region', p4 is not False)) if not ok]
    if not p3: status = 'STOP_ORACLE_MISMATCH'
    elif not gate: status = 'INCONCLUSIVE_REGION_TOO_SMALL'
    elif not reasons: status = 'GO_BREAK_EVEN'
    else: status = 'STOP_NO_PREDICTABLE_BREAK_EVEN'
    return {'status': status, 'region_gate': {'region_groups': n_region_groups, 'required': a.min_region_groups, 'passed': gate},
            'endpoints': {'P1_break_even_in_region': p1, 'P2_trend_in_region': p2, 'P3_exactness': p3, 'P4_no_missed_gain_outside_region': p4},
            'fail_reasons': reasons if gate else ['region_too_small'] + reasons, 'by_K_in_region': by_k,
            'trend_in_region': {'K_min': kmin, 'K_max': kmax, 'mean_diff': float(np.mean(d)) if d else None, 'ci_lo': dc[0], 'ci_hi': dc[1]},
            'outside_region': {'geometries': len(out_geos), 'groups': len({grp[g] for g in out_geos}),
                               'early_abs_saved_ms': float(np.mean(ov)) if ov else None, 'ci_lo': oc[0], 'ci_hi': oc[1]}}


def covariate_preflight(a, TH, TG, lock):
    """Covariate-only check of a candidate test set under the frozen lock (no runtime)."""
    ks = sorted(set(int(v) for v in a.ks.split(','))); kmax = ks[-1]; c = cfg(a); robust = a.early_bound == 'robust'; bins = er_bins(a)
    pol = lock['policy_cells']; per_k = []; region = set(); outside = set()
    for k in ks:
        cells = defaultdict(set)
        for h, g in zip(TH, TG):
            z = channel_features(h[:, :k], c, robust, bins); cells[z['cell']].add(str(g))
            if k == kmax:
                active = any(pol.get(key(kmax, l, z['cell']), 'CARD') != 'CARD' for l in a.beam_counts)
                (region if active else outside).add(str(g))
        per_k.append({'K': k, 'groups_per_cell': {x: len(v) for x, v in sorted(cells.items())}})
    return {'test_sha256': digest(a.test), 'n': len(TH), 'groups': len(set(map(str, TG))), 'per_K': per_k,
            'region_groups': len(region), 'outside_groups': len(outside), 'min_region_groups': a.min_region_groups,
            'accepted': len(region) >= a.min_region_groups,
            'non_card_cells': sorted(k_ for k_, v in pol.items() if v != 'CARD')}


def group_boot(rows, boot, seed, field='saving_ms'):
    if len(set(r['group'] for r in rows)) < 3: return (None, None)
    return group_ci([r[field] for r in rows], [r['group'] for r in rows], boot, seed=seed)


def choose_policy(per_geometry, train_groups, valid_groups, boot, min_gain, min_cell):
    """Per (K,L,early_ratio cell): best policy on fit groups, accepted only if the
    validation-group bootstrap lower bound exceeds min_gain. Otherwise CARD."""
    cells = sorted(set((r['K'], r['L'], r['cell']) for r in per_geometry))
    decisions = []; lock = {}
    for k, l, d in cells:
        rr = [r for r in per_geometry if (r['K'], r['L'], r['cell']) == (k, l, d)]
        fit = [r for r in rr if r['group'] in train_groups]; valid = [r for r in rr if r['group'] in valid_groups]
        names = sorted(set(r['group'] for r in fit)); vnames = sorted(set(r['group'] for r in valid))
        fits = []
        for pol in POLICIES[1:]:
            s = [r for r in fit if r['policy'] == pol]
            fits.append((float(np.mean([r['saving_ms'] for r in s])) if s else -1e100, pol))
        best = max(fits)
        p = best[1] if best[0] > 0 else 'CARD'
        vs = [r for r in valid if r['policy'] == p]
        ci = group_boot(vs, boot, 1 + k * 17 + l * 3) if p != 'CARD' else (None, None)
        accepted = (p != 'CARD' and len(names) >= min_cell and len(vnames) >= min_cell and ci[0] is not None and ci[0] > min_gain)
        lock[key(k, l, d)] = p if accepted else 'CARD'
        decisions.append({'K': k, 'L': l, 'cell': d, 'fit_groups': len(names), 'valid_groups': len(vnames),
                          'fit_best_policy': p, 'fit_best_saved_ms': best[0] if best[0] > -1e99 else '',
                          'valid_saved_ms': float(np.mean([r['saving_ms'] for r in vs])) if vs else '',
                          'valid_ci_lo': ci[0], 'valid_ci_hi': ci[1], 'accepted': int(accepted), 'locked_policy': lock[key(k, l, d)]})
    return lock, decisions


def policy_results(paired, lock, boot, seed, min_gain):
    """Score the frozen map. Geometries routed to CARD pay the feature cost whenever
    their (K,L) has at least one non-CARD cell (routing requires the feature)."""
    routed = {(int(c.split('_')[0][1:]), int(c.split('_')[1][1:])) for c, p in lock.items() if p != 'CARD'}
    rows = []; grouped = defaultdict(list)
    for r in paired: grouped[(r['geometry'], r['K'], r['L'])].append(r)
    for (g, k, l), rs in sorted(grouped.items()):
        r = rs[0]; pol = lock.get(key(k, l, r['cell']), 'CARD')
        match = next((x for x in rs if x['policy'] == pol), None)
        if match:
            saved = match['saving_ms']; sel = match['policy_ms'] + match['feature_ms']; calls = match['calls_saved']
        else:
            fee = r['feature_ms'] if (k, l) in routed else 0.
            saved = -fee; sel = r['card_ms'] + fee; calls = 0.
        rows.append({'geometry': g, 'group': r['group'], 'K': k, 'L': l, 'cell': r['cell'], 'early_ratio': r['early_ratio'],
                     'selected_policy': pol, 'saved_ms': saved, 'card_ms': r['card_ms'], 'selected_ms': sel,
                     'rel_saved': saved / r['card_ms'] if r['card_ms'] > 0 else 0., 'calls_saved': calls})
    aggregate = []
    for k, l in sorted(set((r['K'], r['L']) for r in rows)):
        rr = [r for r in rows if r['K'] == k and r['L'] == l]
        ci = group_ci([r['saved_ms'] for r in rr], [r['group'] for r in rr], boot, seed + 100 * k + l)
        aggregate.append({'K': k, 'L': l, 'geometries': len(rr), 'groups': len(set(r['group'] for r in rr)),
                          'mean_card_ms': float(np.mean([r['card_ms'] for r in rr])),
                          'mean_saved_ms': float(np.mean([r['saved_ms'] for r in rr])), 'ci_lo': ci[0], 'ci_hi': ci[1],
                          'mean_rel_saved': float(np.mean([r['rel_saved'] for r in rr])),
                          'mean_calls_saved': float(np.mean([r['calls_saved'] for r in rr])),
                          'activated_fraction': float(np.mean([r['selected_policy'] != 'CARD' for r in rr])),
                          'pass_runtime_strict': int(ci[0] is not None and ci[0] > min_gain)})
    return rows, aggregate


def hypothesis_tests(rows, a, nviol):
    """Predeclared primary endpoints for ONE test source (frozen policy map):
    E1 break-even at K_max: CI_lo(mean relative saving) > min_rel_gain AND
       CI_lo(mean absolute saving per (K,L) configuration) > min_gain_ms;
    E2 trend in K: CI_lo(mean paired difference rel(K_max) - rel(K_min)) > 0;
    E3 exactness: no oracle mismatch (false certificates abort the run);
    E4 predictability: on geometries activated by the lock at K_max,
       CI_lo(mean saving) > 0.
    Relative saving per geometry and K = sum_L saved_ms / sum_L CARD ms."""
    ks = sorted(set(r['K'] for r in rows)); kmin, kmax = ks[0], ks[-1]
    per = defaultdict(lambda: {'s': 0., 'c': 0., 'n': 0, 'act': 0})
    grp = {}
    for r in rows:
        p = per[(r['geometry'], r['K'])]; p['s'] += r['saved_ms']; p['c'] += r['card_ms']; p['n'] += 1
        p['act'] += int(r['selected_policy'] != 'CARD'); grp[r['geometry']] = r['group']
    geos = sorted(grp)
    def rel(g, k): p = per[(g, k)]; return p['s'] / p['c'] if p['c'] > 0 else 0.
    def ab(g, k): p = per[(g, k)]; return p['s'] / max(p['n'], 1)
    def ci(vals, gg, s): return group_ci(vals, gg, a.bootstrap, seed=a.seed + s)
    G = [grp[g] for g in geos]
    by_k = []
    for i, k in enumerate(ks):
        rv = [rel(g, k) for g in geos]; av = [ab(g, k) for g in geos]
        rc = ci(rv, G, 11 + i); acI = ci(av, G, 31 + i)
        by_k.append({'K': k, 'mean_rel_saved': float(np.mean(rv)), 'rel_ci_lo': rc[0], 'rel_ci_hi': rc[1],
                     'mean_saved_ms': float(np.mean(av)), 'abs_ci_lo': acI[0], 'abs_ci_hi': acI[1],
                     'activated_fraction': float(np.mean([per[(g, k)]['act'] > 0 for g in geos]))})
    top = by_k[-1]
    e1 = top['rel_ci_lo'] is not None and top['rel_ci_lo'] > a.min_rel_gain and top['abs_ci_lo'] is not None and top['abs_ci_lo'] > a.min_gain_ms
    if kmax > kmin:
        d = [rel(g, kmax) - rel(g, kmin) for g in geos]; dc = ci(d, G, 51)
        trend = {'K_min': kmin, 'K_max': kmax, 'mean_diff': float(np.mean(d)), 'ci_lo': dc[0], 'ci_hi': dc[1]}
        e2 = dc[0] is not None and dc[0] > 0
    else:
        trend = None; e2 = False
    act = [r for r in rows if r['K'] == kmax and r['selected_policy'] != 'CARD']
    ac = group_ci([r['saved_ms'] for r in act], [r['group'] for r in act], a.bootstrap, seed=a.seed + 71) if len(set(r['group'] for r in act)) >= 3 else (None, None)
    e4 = ac[0] is not None and ac[0] > 0
    e3 = nviol == 0
    reasons = [n for n, ok in (('E1_no_break_even_at_Kmax', e1), ('E2_no_increasing_trend_in_K', e2),
                               ('E3_oracle_mismatch', e3), ('E4_activated_cells_not_positive', e4)) if not ok]
    return {'endpoints': {'E1_break_even_Kmax': e1, 'E2_trend_in_K': e2, 'E3_exactness': e3, 'E4_predictability': e4},
            'by_K': by_k, 'trend': trend,
            'activated_at_Kmax': {'rows': len(act), 'groups': len(set(r['group'] for r in act)),
                                  'mean_saved_ms': float(np.mean([r['saved_ms'] for r in act])) if act else None,
                                  'ci_lo': ac[0], 'ci_hi': ac[1]},
            'status': 'GO_BREAK_EVEN' if not reasons else 'STOP_NO_PREDICTABLE_BREAK_EVEN', 'fail_reasons': reasons}


def curve(paired, boot, seed):
    """Break-even curve: saving of every policy by (K, L, early_ratio cell)."""
    out = []; by = defaultdict(list)
    for r in paired: by[(r['K'], r['L'], r['cell'], r['policy'])].append(r)
    for (k, l, c, p), rr in sorted(by.items()):
        ci = group_boot(rr, boot, seed + k * 13 + l)
        out.append({'K': k, 'L': l, 'cell': c, 'policy': p, 'geometries': len(rr), 'groups': len(set(r['group'] for r in rr)),
                    'mean_early_ratio': float(np.median([r['early_ratio'] for r in rr])), 'mean_card_ms': float(np.mean([r['card_ms'] for r in rr])),
                    'mean_saving_ms': float(np.mean([r['saving_ms'] for r in rr])), 'ci_lo': ci[0], 'ci_hi': ci[1],
                    'mean_rel_saving': float(np.mean([r['saving_ms'] / r['card_ms'] for r in rr if r['card_ms'] > 0]))})
    return out


def config_signature(a):
    return {'version': VERSION, 'q': a.q, 'sigma_rel': a.sigma_rel, 'sinr_db': a.sinr_db, 'noise': a.noise, 'pmax': a.pmax,
            'ks': a.ks, 'alphas': a.alphas, 'beam_counts': a.beam_counts, 'guard': a.guard, 'repeats': a.repeats,
            'bootstrap': a.bootstrap, 'min_gain_ms': a.min_gain_ms, 'min_rel_gain': a.min_rel_gain,
            'min_cell_groups': a.min_cell_groups, 'min_dev_groups': a.min_dev_groups, 'min_test_groups': a.min_test_groups,
            'er_bins': list(er_bins(a)), 'early_bound': a.early_bound,
            'min_region_groups': a.min_region_groups, 'min_dev_region_groups': a.min_dev_region_groups,
            'split': 'groups 60/40, stratified by K_max early_ratio cell',
            'primary_endpoints': 'Inside predicted region (gate >= min_region_groups, else INCONCLUSIVE): P1 break-even of frozen map at K_max (relative and absolute), P2 EARLY trend K_min->K_max, P3 exactness, P4 no missed gain outside region (CI_lo of EARLY saving < min_gain_ms); GO on both DeepMIMO and 3GPP with the same lock',
            'smoke': a.smoke, 'limit': a.limit, 'profile_candidates': a.profile_candidates,
            'seed': a.seed, 'dev_hash': digest(a.development), 'machine': machine_info(),
            'code_hashes': {n: digest(HERE / n) for n in SOURCES}}


def run_tasks(a, root, phase, H, G, manifest, source_hash):
    tdir = root / 'tasks' / phase; tdir.mkdir(parents=True, exist_ok=True)
    tsig = sha_text({'manifest': manifest['signature'], 'phase': phase, 'source_hash': source_hash})
    rows = []; traces = []; robust = a.early_bound == 'robust'; bins = er_bins(a)
    for i in range(len(H)):
        p = tdir / f'{i:07d}.json'
        if p.exists():
            entry = rjson(p)
            if entry.get('signature') != tsig: raise RuntimeError('Checkpoint mismatch at ' + str(p))
        else:
            rr = []; tt = []
            for k, l, alphas in configs(a):
                rx, tx = process_one(H[i], G[i], i, k, l, alphas, cfg(a), a.guard, a.repeats, a.seed, a.profile_candidates, robust, bins)
                rr.extend(rx); tt.extend(tx)
            entry = {'signature': tsig, 'complete': True, 'rows': rr, 'traces': tt}
            jwrite(p, entry)
        if not entry.get('complete'): raise RuntimeError('Incomplete task ' + str(p))
        rows.extend(entry['rows']); traces.extend(entry['traces'])
        if (i + 1) % 10 == 0: print(f'  {phase}: {i+1}/{len(H)} geometries', flush=True)
    return rows, traces


def provenance(path, smoke):
    if not path:
        if smoke: return {'source': 'synthetic', 'scenario': 'smoke', 'prior_use': 'smoke'}
        raise ValueError('Official run requires provenance JSON')
    d = rjson(path)
    for n in ('source', 'scenario', 'group_definition', 'independence_basis', 'prior_use'):
        if not d.get(n): raise ValueError('Missing provenance ' + n)
    return d


def preflight(a, H, G):
    """Development data only: early_ratio distribution per K and cell support.
    Use it to anticipate whether break-even is reachable BEFORE spending a full run."""
    bins = er_bins(a); robust = a.early_bound == 'robust'; c = cfg(a); out = {'per_K': []}
    for k in sorted(set(int(v) for v in a.ks.split(','))):
        z = [channel_features(h[:, :k], c, robust, bins) for h in H]
        er = np.array([x['early_ratio'] for x in z])
        cells = defaultdict(set)
        for x, g in zip(z, G): cells[x['cell']].add(str(g))
        out['per_K'].append({'K': k, 'early_ratio_quantiles': {q: float(np.quantile(er, q)) for q in (.1, .25, .5, .75, .9)},
                             'fraction_er_ge_1': float(np.mean(er >= 1)),
                             'groups_per_cell': {c_: len(v) for c_, v in sorted(cells.items())}})
    need = int(np.ceil(a.min_cell_groups / .4))
    out['note'] = (f'A cell needs >= {a.min_cell_groups} fit and validation groups (about {need} groups in total, 60/40 split) '
                   'to be activated; cells with fewer groups stay CARD.')
    return out


def combine(a):
    runs = [x for x in a.combine_runs.split(',') if x]
    if len(runs) < 2: raise ValueError('--combine-runs needs at least two run-ids (DeepMIMO and 3GPP)')
    root = Path(a.out_root); decs = []; locks = set(); tests = set()
    for r in runs:
        d = rjson(root / r / 'CP08_decision.json'); lk = rjson(root / r / 'CP03_locked_cells.json')
        pre = rjson(root / r / 'CP04_test_preflight.json')
        locks.add(sha_text(lk)); tests.add(pre['test_sha256']); decs.append((r, d, pre))
    if len(locks) != 1: raise RuntimeError('Runs do not share the same frozen lock (CP03 differs)')
    if len(tests) != len(runs): raise RuntimeError('Two runs used the same test file')
    srcs = [p['source'].get('source', '') for _, _, p in decs]
    st = [d['primary']['status'] for _, d, _ in decs]
    if any(d.get('smoke') for _, d, _ in decs): status = 'SMOKE_ONLY'
    elif any(x.startswith('STOP') for x in st): status = 'STOP'
    elif any(x.startswith('INCONCLUSIVE') for x in st): status = 'INCONCLUSIVE'
    elif all(x == 'GO_BREAK_EVEN' for x in st) and len(set(srcs)) >= 2: status = 'GO_PREDICTABLE_BREAK_EVEN'
    else: status = 'INCONCLUSIVE'
    res = {'status': status, 'version': VERSION, 'runs': runs, 'sources': srcs, 'source_status': dict(zip(runs, st)), 'lock_sha': locks.pop(),
           'per_source': {r: {'source': p['source'], 'primary': d['primary']} for r, d, p in decs},
           'rule': 'GO only if every source is GO_BREAK_EVEN (same frozen lock, >= 2 distinct sources); any STOP -> STOP; otherwise INCONCLUSIVE'}
    out = root / a.run_id; out.mkdir(parents=True, exist_ok=True)
    jwrite(out / 'CP11_combined_decision.json', res)
    f = lambda x, m=1.: '—' if x is None else f'{m*x:.2f}'
    L = [f'# {VERSION} combined decision: **{status}**\n',
         'Predicted region R = test geometries whose K_max early_ratio cell is locked to a non-CARD policy.\n',
         '| Run | Source | Status | R groups | K | Frozen map rel. saving in R | CI95 | EARLY rel. saving in R | CI95 | Frozen abs. saving in R (ms) |',
         '|---|---|---|---|---|---|---|---|---|---|']
    for r, d, p in decs:
        pr = d['primary']
        for b in pr['by_K_in_region']:
            L.append(f"| {r} | {p['source'].get('source','')} | {pr['status']} | {pr['region_gate']['region_groups']} | {b['K']} | "
                     f"{f(b['frozen_rel_saved'],100)}% | [{f(b['frozen_rel_ci_lo'],100)}, {f(b['frozen_rel_ci_hi'],100)}]% | "
                     f"{f(b['early_rel_saved'],100)}% | [{f(b['early_rel_ci_lo'],100)}, {f(b['early_rel_ci_hi'],100)}]% | {f(b['frozen_abs_saved_ms'])} |")
    L.append('')
    for r, d, p in decs:
        pr = d['primary']; t = pr['trend_in_region']; o = pr['outside_region']
        L.append(f"- **{r}**: {pr['endpoints']}; EARLY trend K{t['K_min']}→K{t['K_max']} in R: {f(t['mean_diff'],100)} pp, CI [{f(t['ci_lo'],100)}, {f(t['ci_hi'],100)}] pp; "
                 f"outside R ({o['groups']} groups) EARLY abs. saving {f(o['early_abs_saved_ms'])} ms, CI [{f(o['ci_lo'])}, {f(o['ci_hi'])}]; reasons: {pr['fail_reasons'] or 'none'}")
    (out / 'CP11_MANUSCRIPT_TABLE.md').write_text('\n'.join(L), encoding='utf8')
    print('\n'.join(L))


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--stage', choices=('preflight', 'develop', 'lock', 'test-preflight', 'test', 'report', 'all', 'combine'), required=True)
    p.add_argument('--development', default=''); p.add_argument('--test', default='')
    p.add_argument('--dev-provenance', default=''); p.add_argument('--test-provenance', default='')
    p.add_argument('--run-id', required=True); p.add_argument('--out-root', default='outputs')
    p.add_argument('--ks', default='4,6,8'); p.add_argument('--alphas', default='0,0.001,0.01,0.05,0.1,0.3,1')
    p.add_argument('--beam-counts', default='3,5,7')
    p.add_argument('--q', type=float, default=2.960414); p.add_argument('--sigma-rel', type=float, default=.04)
    p.add_argument('--sinr-db', type=float, default=6.); p.add_argument('--noise', type=float, default=2e-13)
    p.add_argument('--pmax', type=float, default=1.); p.add_argument('--guard', type=float, default=1e-5)
    p.add_argument('--repeats', type=int, default=5); p.add_argument('--bootstrap', type=int, default=1000)
    p.add_argument('--min-gain-ms', type=float, default=.1); p.add_argument('--min-rel-gain', type=float, default=.02)
    p.add_argument('--min-cell-groups', type=int, default=5)
    p.add_argument('--min-dev-groups', type=int, default=80); p.add_argument('--min-test-groups', type=int, default=10)
    p.add_argument('--min-dev-region-groups', type=int, default=20, help='development groups required in the top early_ratio cell at K_max')
    p.add_argument('--min-region-groups', type=int, default=10, help='test groups required inside the predicted region')
    p.add_argument('--allow-small-region', action='store_true', help='run test although test-preflight failed (result will be INCONCLUSIVE)')
    p.add_argument('--er-bins', default='0.1,1.0', help='early_ratio cell boundaries (predeclared)')
    p.add_argument('--early-bound', choices=('robust', 'nominal'), default='robust')
    p.add_argument('--seed', type=int, default=20261117); p.add_argument('--smoke', action='store_true'); p.add_argument('--lock-from', default='')
    p.add_argument('--limit', type=int, default=0); p.add_argument('--profile-candidates', action='store_true')
    p.add_argument('--combine-runs', default='', help='comma list of finished test run-ids (stage combine)')
    a = p.parse_args()
    if a.stage == 'combine': combine(a); return
    if not a.development: raise ValueError('--development is required')
    a.beam_counts = tuple(int(v) for v in a.beam_counts.split(',')); configs(a)
    if not a.smoke and a.min_gain_ms < 0: raise ValueError('min-gain must be nonnegative')
    H, G, meta = load_any(a.development)
    if a.limit:
        if not a.smoke: raise ValueError('--limit only for smoke')
        H, G = H[:a.limit], G[:a.limit]
    if a.stage == 'preflight':
        res = {'stage': 'preflight', 'version': VERSION, 'n_dev': len(H), 'n_groups': len(set(map(str, G))),
               'configs': [(k, l) for k, l, _ in configs(a)], 'candidates_per_geometry': {f'K{k}_L{l}': l * (2**k - 1) for k, l, _ in configs(a)},
               'machine': machine_info(), **preflight(a, H, G)}
        print(json.dumps(res, indent=2, ensure_ascii=False)); return
    devp = provenance(a.dev_provenance, a.smoke)
    if not a.smoke and len(set(map(str, G))) < a.min_dev_groups:
        raise ValueError(f'At least {a.min_dev_groups} development groups required (found {len(set(map(str, G)))})')
    if not a.smoke and a.stage in ('develop', 'lock', 'all'):
        ntop = sum(1 for v in group_cells(H, G, a).values() if v == top_cell(a))
        if ntop < a.min_dev_region_groups:
            raise ValueError(f'Development set has {ntop} groups in {top_cell(a)} at K_max; {a.min_dev_region_groups} required. '
                             'Add power-limited (cell-edge) drops to the development set before developing (see preflight).')
    root = Path(a.out_root) / a.run_id; root.mkdir(parents=True, exist_ok=True)
    sign = config_signature(a)
    manifest = json.loads(json.dumps({'signature': sha_text(sign), 'settings': sign, 'source': devp,
                                      'development_n': len(H), 'development_groups': len(set(map(str, G))), 'scope': 'development only'}, ensure_ascii=False))
    mp = root / 'CP00_manifest.json'
    if mp.exists():
        old = rjson(mp)
        if old != manifest:
            if old.get('settings', {}).get('machine') != manifest['settings']['machine']:
                raise RuntimeError('Different machine/software stack from the one that created this run; runtime is not comparable. Use the original machine.')
            raise RuntimeError('Configuration changed; use a new run-id')
    else: jwrite(mp, manifest)
    if a.stage in ('develop', 'all'):
        dr, trace = run_tasks(a, root, 'development', H, G, manifest, digest(a.development))
        write_rows(root / 'CP01_development_repeats.csv', dr)
        if trace: write_rows(root / 'CP01_candidate_cost.csv', trace)
        paired = summary_from_rows(dr); write_rows(root / 'CP02_development_paired.csv', paired)
        write_rows(root / 'CP02_development_breakeven_curve.csv', curve(paired, a.bootstrap, a.seed))
    if a.stage in ('lock', 'all'):
        lockfile = root / 'CP03_locked_cells.json'
        if lockfile.exists(): raise RuntimeError('Already locked: refuse retraining')
        if a.lock_from: raise RuntimeError('Cannot retrain when --lock-from is supplied')
        pth = root / 'CP02_development_paired.csv'
        if not pth.exists(): raise RuntimeError('Run --stage develop')
        with pth.open(encoding='utf8', newline='') as f: rows = list(csv.DictReader(f))
        for r in rows:
            for x in ('geometry', 'K', 'L'): r[x] = int(r[x])
            for x in ('saving_ms', 'calls_saved', 'coherence', 'early_ratio', 'card_ms', 'policy_ms', 'feature_ms'): r[x] = float(r[x])
        fit, valid, gcell = stratified_split(H, G, a)
        policies, details = choose_policy(rows, fit, valid, a.bootstrap, a.min_gain_ms, a.min_cell_groups)
        write_rows(root / 'CP03_cell_validation.csv', details)
        jwrite(lockfile, {'version': VERSION, 'policy_cells': policies, 'config_signature': manifest['signature'],
                          'development_sha256': digest(a.development), 'fit_groups': sorted(fit), 'valid_groups': sorted(valid),
                          'min_gain_ms': a.min_gain_ms, 'er_bins': list(er_bins(a)), 'early_bound': a.early_bound,
                          'conditioned_on': 'K, L, early_ratio cell; no test tuning',
                          'split': 'stratified by K_max cell', 'group_cell_counts': dict(Counter(gcell.values()))})
        print('LOCKED cells:', json.dumps(policies))
    if a.stage in ('test-preflight', 'test', 'all'):
        lockfile = root / 'CP03_locked_cells.json'
        if not lockfile.exists() and a.lock_from:
            imported = rjson(a.lock_from)
            if imported['config_signature'] != manifest['signature']:
                raise RuntimeError('External lock and development/configuration/machine hashes differ')
            jwrite(lockfile, imported)
        if not lockfile.exists(): raise RuntimeError('Must freeze before test')
        lock = rjson(lockfile)
        if lock['config_signature'] != manifest['signature']: raise RuntimeError('Frozen signature mismatch')
        if not a.test: raise ValueError('Need test dataset')
        TH, TG, _ = load_any(a.test)
        if a.limit: TH, TG = TH[:a.limit], TG[:a.limit]
        if set(map(str, G)) & set(map(str, TG)): raise RuntimeError('Overlapping group labels')
        if {raw_h(x) for x in H} & {raw_h(x) for x in TH}: raise RuntimeError('Duplicate channels')
        cpf = root / 'CP04b_test_covariate_preflight.json'
        if a.stage in ('test-preflight', 'all'):
            cov = covariate_preflight(a, TH, TG, lock)
            log = root / 'TEST_SELECTION_LOG.csv'; new = not log.exists()
            with log.open('a', encoding='utf8', newline='') as f:
                w = csv.writer(f)
                if new: w.writerow(['utc_time', 'test_file', 'test_sha256', 'n', 'groups', 'region_groups', 'outside_groups', 'accepted'])
                w.writerow([time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), Path(a.test).name, cov['test_sha256'], cov['n'],
                            cov['groups'], cov['region_groups'], cov['outside_groups'], int(cov['accepted'])])
            if cpf.exists() and rjson(cpf).get('accepted') and rjson(cpf)['test_sha256'] != cov['test_sha256']:
                raise RuntimeError('This run already accepted another test set; use a new run-id (or --lock-from) for a new source')
            jwrite(cpf, cov)
            print(json.dumps(cov, indent=2)); print('TEST-PREFLIGHT', 'ACCEPTED' if cov['accepted'] else 'REJECTED (region too small)')
            if a.stage == 'test-preflight': print('STAGE test-preflight OK', root); return
        if not cpf.exists() or rjson(cpf)['test_sha256'] != digest(a.test):
            raise RuntimeError('Run --stage test-preflight on this exact test file first')
        if not rjson(cpf)['accepted'] and not a.allow_small_region and not a.smoke:
            raise RuntimeError('Test-preflight rejected this set (predicted region too small). Choose another sealed set, or pass --allow-small-region (result INCONCLUSIVE).')
        tp = provenance(a.test_provenance, a.smoke)
        if not a.smoke and tp['prior_use'] not in ('never_seen', 'sealed_before_development'): raise ValueError('Test is not sealed')
        if not a.smoke and len(set(map(str, TG))) < a.min_test_groups: raise ValueError(f'At least {a.min_test_groups} test groups required')
        if digest(a.development) == digest(a.test): raise RuntimeError('Same development and test file')
        pre = {'test_sha256': digest(a.test), 'source': tp, 'test_n': len(TH), 'test_groups': len(set(map(str, TG))),
               'group_overlap': 0, 'exact_channel_overlap': 0, 'statistical_independence_requires_source_audit': True}
        pp = root / 'CP04_test_preflight.json'
        if pp.exists() and rjson(pp) != json.loads(json.dumps(pre, ensure_ascii=False)): raise RuntimeError('Test changed; use new run-id')
        if not pp.exists(): jwrite(pp, pre)
        tr, trace = run_tasks(a, root, 'test', TH, TG, manifest, digest(a.test))
        write_rows(root / 'CP05_test_repeats.csv', tr)
        if trace: write_rows(root / 'CP05_candidate_cost.csv', trace)
        paired = summary_from_rows(tr)
        write_rows(root / 'CP06_test_paired_all_policies.csv', paired)
        write_rows(root / 'CP06_test_breakeven_curve.csv', curve(paired, a.bootstrap, a.seed + 7))
        selected, agg = policy_results(paired, lock['policy_cells'], a.bootstrap, a.seed, a.min_gain_ms)
        write_rows(root / 'CP07_frozen_policy_geometry.csv', selected)
        write_rows(root / 'CP07_break_even_summary.csv', agg)
        nviol = sum(1 for r in tr if r['oracle_match'] != 1)
        primary = region_tests(selected, paired, a, nviol)
        secondary = hypothesis_tests(selected, a, nviol)
        strict = nviol == 0 and all(x['pass_runtime_strict'] for x in agg)
        decision = {'status': 'SMOKE_ONLY' if a.smoke else primary['status'], 'smoke': a.smoke, 'version': VERSION,
                    'primary': primary, 'secondary_all_geometry_V15_1': secondary, 'secondary_strict_all_KL_gate': bool(strict),
                    'oracle_mismatch': nviol, 'test_source': tp, 'per_config': agg,
                    'interpretation': 'Primary endpoints were predeclared in CP00/CP03; cells and thresholds were not tuned on test.'}
        jwrite(root / 'CP08_decision.json', decision)
        print('TEST DECISION:', decision['status'], '| endpoints:', primary['endpoints'])
    if a.stage in ('report', 'all'):
        files = sorted([p for p in root.glob('CP*') if p.is_file() and p.name != 'CP09_SHA256.csv'] + list(root.glob('TEST_SELECTION_LOG.csv')) + list((root / 'tasks').rglob('*.json')))
        write_rows(root / 'CP09_SHA256.csv', [{'file': str(p.relative_to(root)), 'sha256': digest(p)} for p in files]); print('REPORT', root)
    print('STAGE', a.stage, 'OK', root)


if __name__ == '__main__': main()
