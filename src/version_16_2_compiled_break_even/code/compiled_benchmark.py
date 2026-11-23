#!/usr/bin/env python3
"""V16 part C: runtime of CARD / EARLY / ROUTED with the COMPILED solver (native/screen_core.c).

Reuses the frozen V15.2 lock (CP00 manifest + CP03 cells): same physical parameters, alphas,
K and L, early_ratio bins and policy map. ROUTED = compute early_ratio (compiled), look up the
locked cell, run EARLY if the cell is non-CARD (HYBRID is mapped to EARLY: post-beam
certificates are not compiled), otherwise CARD. Every compiled decision is checked against the
independent Python exhaustive oracle OUTSIDE the timed region.

  python code/compiled_benchmark.py --data data/V152_dm_test.npz --manifest outputs/V152_DM/CP00_manifest.json \
      --lock outputs/V152_DM/CP03_locked_cells.json --run-id C16_DM --python-run outputs/V152_DM

Predeclared compiled endpoints (per dataset; R = geometries whose K_max cell is locked non-CARD):
  C1 exactness: every compiled decision equals the Python oracle, or differs only within the
     floating-point sensitivity of the candidate (numeric_agreement.py, logged in CC06, <= 1% of decisions);
  C2 break-even in R at K_max: CI_lo(mean relative saving of ROUTED) > min_rel_gain (2%);
  C3 trend in R: CI_lo(EARLY relative saving K_max minus K_min) > 0;
  C4 bounded loss outside R: CI_lo(mean relative saving of ROUTED at every K) > -max_rel_loss (2%).
"""
import argparse, csv, hashlib, json, os, platform, subprocess, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from robust_model import digest, jwrite, cwrite
from run_experiment import independent_oracle, same_choice, key, bin_label, rjson, utf8_console, load_any, machine_info
from screening_policy import group_ci
import native_search as ns
from numeric_agreement import agree

VERSION = 'V16.2-compiled'
SOURCES = ['compiled_benchmark.py', 'native_search.py', 'native/screen_core.c', 'numeric_agreement.py']
MAX_EVENT_FRACTION = 0.01   # C1: accepted floating-point events must stay <= 1% of checked decisions


def compiler_id():
    for c in ('gcc', 'cc', 'clang', 'cl'):
        try:
            r = subprocess.run([c, '--version'], capture_output=True, text=True, timeout=10)
            if r.returncode == 0: return c + ': ' + (r.stdout or r.stderr).splitlines()[0]
        except Exception: pass
    return 'unknown'


def timed(P, mode, min_ms=20.0, max_inner=2000000):
    """One measurement: run the policy n times INSIDE C (one ctypes call), n grown until >= min_ms; ms per run."""
    n = 1
    while True:
        t = time.perf_counter(); st = P.repeat(n, mode); dt = (time.perf_counter() - t) * 1000
        if st != 0: raise RuntimeError('native failure')
        if dt >= min_ms or n >= max_inner: return dt / n
        n = min(max_inner, max(n * 2, int(n * min_ms / max(dt, 1e-6)) + 1))


def measure(h, group, gi, ks, Ls, alphas, cfg, guard, lock, bins, kmax, repeats, seed, oracle_check, min_ms=20.0, events=None, h_in=None):
    """h is complex128 (C and the oracle both run in double). h_in is the stored array; if it is single precision,
    the V15.2 Python path (which ran on h_in) is re-run to check that its decision equals the double-precision one."""
    rows = []
    single = h_in is not None and h_in.dtype == np.complex64
    events = [] if events is None else events
    def check(name, got, ref, k, l):
        ok, ev = agree(got, ref, h[:, :k], None, cfg, seed=gi * 1000 + k * 10 + l)
        if ev is not None:
            ev.update(geometry=gi, K=k, L=l, policy=name); events.append(ev)
        if not ok: raise AssertionError(f'COMPILED MISMATCH geometry={gi} K={k} L={l} {name}: {ev}')
    for k in ks:
        for l in Ls:
            al = alphas[:l]; P = ns.Prepared(h[:, :k], al, cfg, guard)
            er = P.er(); cell = bin_label(er, bins); routed = lock.get(key(k, l, cell), 'CARD') != 'CARD'
            # decisions + counters (outside timing)
            res = {}
            for name, pol in (('CARD', 0), ('EARLY', 1)):
                if P.run(pol) != 0: raise RuntimeError('native failure')
                res[name] = P.result()
            if oracle_check:
                ref, _ = independent_oracle(h[:, :k], al, cfg)
                sp_same, sp_rel = None, None
                if single:   # decision of the V15.2 Python path, computed in single precision as in V15.2
                    r32, _ = independent_oracle(h_in[:, :k], al, cfg)
                    sp_same = int((r32 is None and ref is None) or (r32 is not None and ref is not None and
                                  (r32['cardinality'], r32['subset'], r32['alpha']) == (ref['cardinality'], ref['subset'], ref['alpha'])))
                    sp_rel = abs(r32['p_req_w'] - ref['p_req_w']) / ref['p_req_w'] if (r32 and ref) else 0.0
                for name in res: check(name, res[name][0], ref, k, l)
            # Routing is compiled too (early ratio + cell lookup inside C), so its overhead is measured in the same language.
            P.set_routing(bins, {j for j in range(len(bins) + 1) if lock.get(key(k, l, f'ER{j}'), 'CARD') != 'CARD'})
            if P.run_routed() != 0: raise RuntimeError('native failure')
            if P.pol.value != int(routed): raise AssertionError('compiled routing disagrees with Python cell lookup')
            if oracle_check: check('ROUTED', P.result()[0], ref, k, l)
            modes = {'CARD': 0, 'EARLY': 1, 'ROUTED': 2}
            times = defaultdict(list)
            for rep in range(repeats):
                order = list(modes); np.random.default_rng(seed + gi * 71 + rep * 131 + k * 37 + l).shuffle(order)
                for name in order: times[name].append(timed(P, modes[name], min_ms))
            med = {n: float(np.median(v)) for n, v in times.items()}
            cE = res['EARLY'][1]; cC = res['CARD'][1]
            rows.append({'geometry': gi, 'group': str(group), 'K': k, 'L': l, 'early_ratio': er, 'cell': cell,
                         'routed_to_early': int(routed), 'served': res['CARD'][0]['cardinality'] if res['CARD'][0] else 0,
                         'c_card_ms': med['CARD'], 'c_early_ms': med['EARLY'], 'c_routed_ms': med['ROUTED'],
                         'early_saving_ms': med['CARD'] - med['EARLY'], 'routed_saving_ms': med['CARD'] - med['ROUTED'],
                         'early_rel': (med['CARD'] - med['EARLY']) / med['CARD'], 'routed_rel': (med['CARD'] - med['ROUTED']) / med['CARD'],
                         'card_calls': cC['full_calls'], 'early_calls': cE['full_calls'], 'early_rejects': cE['early_rejects'],
                         'subsets_visited': cE['subsets_visited'],
                         'rejected_subsets_by_size': json.dumps(cE['rejected_subsets_by_size']), 'oracle_checked': int(oracle_check),
                         'single_vs_double_same_decision': sp_same if oracle_check else None,
                         'single_vs_double_rel_power': sp_rel if oracle_check else None})
    return rows


def summarize(rows, kmax, kmin, boot, seed, min_rel, max_loss):
    R = sorted({r['geometry'] for r in rows if r['K'] == kmax and r['routed_to_early']})
    grp = {r['geometry']: r['group'] for r in rows}; O = sorted(set(grp) - set(R))
    agg = defaultdict(lambda: [0., 0., 0.])  # (geo, K, field) sums over L
    for r in rows:
        for f, v in (('card', r['c_card_ms']), ('early', r['c_early_ms']), ('routed', r['c_routed_ms'])):
            agg[(r['geometry'], r['K'], f)][0] += v
    rel = lambda g, k, f: 1 - agg[(g, k, f)][0] / agg[(g, k, 'card')][0]
    def ci(v, geos, s): gg = [grp[g] for g in geos]; return group_ci(v, gg, boot, seed=seed + s) if len(set(gg)) >= 3 else (None, None)
    table = []
    for zone, geos in (('R', R), ('outside', O)):
        for i, k in enumerate(sorted({r['K'] for r in rows})):
            for f in ('early', 'routed'):
                v = [rel(g, k, f) for g in geos]
                lo, hi = ci(v, geos, 10 * i + (1 if f == 'early' else 2) + (0 if zone == 'R' else 100))
                table.append({'zone': zone, 'K': k, 'policy': f.upper(), 'geometries': len(geos), 'mean_rel_saving': float(np.mean(v)) if v else None,
                              'ci_lo': lo, 'ci_hi': hi, 'mean_card_ms': float(np.mean([agg[(g, k, 'card')][0] for g in geos])) if geos else None})
    t = lambda z, k, p: next(x for x in table if x['zone'] == z and x['K'] == k and x['policy'] == p)
    c2 = bool(R) and t('R', kmax, 'ROUTED')['ci_lo'] is not None and t('R', kmax, 'ROUTED')['ci_lo'] > min_rel
    d = [rel(g, kmax, 'early') - rel(g, kmin, 'early') for g in R]; dl = ci(d, R, 500)
    c3 = bool(R) and dl[0] is not None and dl[0] > 0
    c4 = all(x['ci_lo'] is None or x['ci_lo'] > -max_loss for x in table if x['zone'] == 'outside' and x['policy'] == 'ROUTED')
    return table, {'region_groups': len({grp[g] for g in R}), 'outside_groups': len({grp[g] for g in O}),
                   'C2_break_even_in_R': c2, 'C3_trend_in_R': c3, 'C4_bounded_loss_outside': c4,
                   'trend_in_R': {'mean_diff': float(np.mean(d)) if d else None, 'ci_lo': dl[0], 'ci_hi': dl[1]}}


def python_comparison(rows, python_run, data_sha):
    """Join with the V15.2 Python timings of the SAME dataset (verified by the test hash in CP04)."""
    pre = Path(python_run) / 'CP04_test_preflight.json'
    if not pre.exists() or rjson(pre)['test_sha256'] != data_sha:
        raise RuntimeError(f'--python-run {python_run} was not run on this dataset (CP04 test_sha256 differs); refusing to join by geometry index')
    P = {(int(r['geometry']), int(r['K']), int(r['L'])): r for r in csv.DictReader(open(Path(python_run) / 'CP06_test_paired_all_policies.csv', encoding='utf8'))
         if r['policy'] == 'EARLY'}
    out = []
    for r in rows:
        p = P.get((r['geometry'], r['K'], r['L']))
        if not p: continue
        out.append({'geometry': r['geometry'], 'group': r['group'], 'K': r['K'], 'L': r['L'], 'cell': r['cell'],
                    'python_card_ms': float(p['card_ms']), 'compiled_card_ms': r['c_card_ms'],
                    'speedup_card': float(p['card_ms']) / r['c_card_ms'],
                    'python_early_rel': float(p['saving_ms']) / float(p['card_ms']), 'compiled_early_rel': r['early_rel']})
    return out


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data', required=True); p.add_argument('--manifest', required=True); p.add_argument('--lock', required=True)
    p.add_argument('--run-id', required=True); p.add_argument('--out-root', default='outputs')
    p.add_argument('--python-run', default='', help='V15.2 test run directory of the SAME dataset (optional comparison)')
    p.add_argument('--repeats', type=int, default=7); p.add_argument('--bootstrap', type=int, default=1000)
    p.add_argument('--min-rel-gain', type=float, default=.02); p.add_argument('--max-rel-loss', type=float, default=.02)
    p.add_argument('--oracle-check', choices=('all', 'none'), default='all'); p.add_argument('--limit', type=int, default=0)
    p.add_argument('--min-ms', type=float, default=20.0, help='minimum duration of one timing measurement (inner loop inside C)')
    a = p.parse_args()
    man = rjson(a.manifest); s = man['settings']; lock = rjson(a.lock)
    if lock['config_signature'] != man['signature']: raise RuntimeError('lock does not belong to manifest')
    cfg = {'q': s['q'], 'sigma': s['sigma_rel'], 'gamma': 10**(s['sinr_db'] / 10), 'noise': s['noise'], 'pmax': s['pmax']}
    ks = sorted(int(v) for v in s['ks'].split(',')); Ls = list(s['beam_counts']); bins = tuple(s['er_bins'])
    alphas = tuple(dict.fromkeys(float(v) for v in s['alphas'].split(',')))
    if s['early_bound'] != 'robust': raise RuntimeError('compiled EARLY implements the robust bound only')
    H_in, G, _ = load_any(a.data)
    input_dtype = str(H_in.dtype)
    H = H_in.astype(np.complex128)   # V16.2: C and the oracle both in double precision
    if a.limit: H, H_in, G = H[:a.limit], H_in[:a.limit], G[:a.limit]
    ns.lib()
    sig = {'version': VERSION, 'data': digest(a.data), 'lock': digest(a.lock), 'manifest': man['signature'], 'repeats': a.repeats, 'min_ms': a.min_ms,
           'oracle_check': a.oracle_check, 'limit': a.limit, 'code': {f: digest(HERE / f) for f in SOURCES},
           'input_dtype': input_dtype, 'machine': machine_info(), 'compiler': compiler_id(), 'lib_sha256': digest(ns.LIB)}
    signature = hashlib.sha256(json.dumps(sig, sort_keys=True).encode()).hexdigest()
    root = Path(a.out_root) / a.run_id; (root / 'tasks').mkdir(parents=True, exist_ok=True)
    mp = root / 'CC00_manifest.json'
    if mp.exists() and rjson(mp)['signature'] != signature: raise RuntimeError('configuration/code/machine changed: use a new run-id')
    if not mp.exists(): jwrite(mp, {'signature': signature, **sig})
    rows = []; events = []
    for i in range(len(H)):
        f = root / 'tasks' / f'{i:07d}.json'
        if f.exists():
            t = rjson(f)
            if t.get('signature') != signature: raise RuntimeError('bad checkpoint ' + str(f))
        else:
            ev = []
            t = {'signature': signature, 'rows': measure(H[i], G[i], i, ks, Ls, alphas, cfg, s['guard'], lock['policy_cells'], bins,
                                                         ks[-1], a.repeats, s['seed'], a.oracle_check == 'all', a.min_ms, ev, H_in[i]),
                 'events': ev}
            jwrite(f, t)
        rows += t['rows']; events += [dict(e, geometry=i) for e in t.get('events', [])]
        if (i + 1) % 10 == 0: print(f'  compiled: {i+1}/{len(H)}', flush=True)
    cwrite(root / 'CC01_compiled_geometry.csv', rows, list(rows[0]))
    table, ends = summarize(rows, ks[-1], ks[0], a.bootstrap, s['seed'], a.min_rel_gain, a.max_rel_loss)
    cwrite(root / 'CC02_compiled_summary.csv', table, list(table[0]))
    comp = python_comparison(rows, a.python_run, digest(a.data)) if a.python_run else []
    if comp: cwrite(root / 'CC03_python_vs_compiled.csv', comp, list(comp[0]))
    n_checked = 3 * len(rows) if a.oracle_check == 'all' else 0
    ev_rows = [{'geometry': e['geometry'], 'K': e['K'], 'L': e['L'], 'policy': e['policy'], 'type': e['type'],
                'rel_diff': e.get('rel_diff'), 'rel_spread': e.get('rel_spread'), 'direct_gain_margin': e.get('direct_gain_margin'),
                'rho': e.get('rho'), 'got': json.dumps(e['got']), 'ref': json.dumps(e['ref'])} for e in events]
    if ev_rows: cwrite(root / 'CC06_numeric_events.csv', ev_rows, list(ev_rows[0]))
    ev_frac = len(ev_rows) / n_checked if n_checked else None
    spc = [r['single_vs_double_same_decision'] for r in rows if r.get('single_vs_double_same_decision') is not None]
    sp_report = {'input_dtype': input_dtype, 'configurations_checked': len(spc), 'decision_changes': len(spc) - sum(spc),
                 'max_rel_power_diff': max([r['single_vs_double_rel_power'] for r in rows if r.get('single_vs_double_rel_power') is not None], default=None)}
    c1 = a.oracle_check == 'all' and (ev_frac is None or ev_frac <= MAX_EVENT_FRACTION)
    dec = {'version': VERSION, 'dataset_sha256': digest(a.data), 'n': len(H), 'C1_exactness_checked_all': c1, 'numeric_events': len(ev_rows), 'decisions_checked': n_checked,
           'numeric_event_fraction': ev_frac, 'single_vs_double_precision_audit': sp_report, 'numeric_event_types': {t: sum(1 for e in ev_rows if e['type'] == t) for t in sorted({e['type'] for e in ev_rows})}, **ends,
           'status': ('GO_COMPILED_BREAK_EVEN' if c1 and ends['C2_break_even_in_R'] and ends['C3_trend_in_R'] and ends['C4_bounded_loss_outside']
                      else ('INCONCLUSIVE_REGION_TOO_SMALL' if ends['region_groups'] < 3 else 'STOP_COMPILED')),
           'speedup_card_median_by_K': {k: float(np.median([c['speedup_card'] for c in comp if c['K'] == k])) for k in ks} if comp else None,
           'note': 'HYBRID cells are executed as EARLY in the compiled path; LP audit not compiled (does not change decisions).'}
    jwrite(root / 'CC04_compiled_decision.json', dec)
    L = [f'# Compiled solver — {a.run_id}: **{dec["status"]}**\n', '| Zone | K | Policy | n | Rel. saving | CI95 | CARD ms (sum over L) |', '|---|---|---|---|---|---|---|']
    fm = lambda x: '—' if x is None else f'{100*x:.2f}%'
    for x in table:
        L.append(f"| {x['zone']} | {x['K']} | {x['policy']} | {x['geometries']} | {fm(x['mean_rel_saving'])} | [{fm(x['ci_lo'])}, {fm(x['ci_hi'])}] | {x['mean_card_ms'] if x['mean_card_ms'] is None else round(x['mean_card_ms'], 4)} |")
    L.append(f"\nC1: {n_checked} decisions checked; {len(ev_rows)} differ only within floating-point sensitivity ({dec['numeric_event_types']}); see CC06.")
    L.append(f"Input dtype {input_dtype}" + (f"; V15.2 single-precision Python decisions vs double: {sp_report['decision_changes']} changes in {sp_report['configurations_checked']} configurations, max relative power difference {sp_report['max_rel_power_diff']}" if spc else ''))
    if comp: L.append(f"\nMedian speed-up of the compiled CARD over Python CARD by K: {dec['speedup_card_median_by_K']}")
    (root / 'CC05_SUMMARY.md').write_text('\n'.join(L), encoding='utf8'); print('\n'.join(L))


if __name__ == '__main__': main()
