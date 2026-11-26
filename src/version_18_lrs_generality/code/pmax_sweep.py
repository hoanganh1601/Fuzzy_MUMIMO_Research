#!/usr/bin/env python3
"""V17 (final round): power-budget sweep of the FROZEN V15.2 policy map on fresh natural groups.

Question
--------
The V15.2 map was locked at Pmax = 30 dBm. Since the early ratio rho_E = sum_k gamma N0 / ((||h_k|| - r_k)^2 Pmax)
is normalised by Pmax and Lemma 1 (rho_E <= 1 => no subset rejected) holds for every Pmax, the map keyed on
(K, L, rho_E cell) can be applied unchanged at another budget. V17 tests this TRANSFER, without re-development,
at 35, 46 and 49 dBm, with 30 dBm (the lock value) as the reference level measured on the same groups.

Design (frozen by --stage protocol before any measurement at a new budget)
-------------------------------------------------------------------------
- Deployments: the two sealed natural pools already used in V16 (UMi ISD 200 m outdoor; UMa ISD 500 m, 80 % indoor).
- Groups: the COMPLEMENT of the V16 natural samples, i.e. the 100 groups of each pool that were never sampled,
  timed or inspected. No randomness, no covariate.
- Levels: 30 (reference), 35, 46, 49 dBm. Everything else (gamma, N0, q_c, sigma, alphas, K, L, bins, map) is the lock.
- Solver: compiled (C) with the frozen map; every decision checked against the Python oracle at the same budget.
- Endpoints per deployment and level (relative saving of ROUTED vs compiled CARD, ratio of sums over L per group):
    X1 exactness  : no decision mismatch, numeric events <= 1 %, no single/double decision change;
    X2 prevalence : share of groups whose K_max cell is locked non-CARD, Wilson 95 % CI (estimate);
    X3 no harm    : CI_lo(cell-wide saving) > -2 % at every K;
    X4 gain       : CI_lo(cell-wide saving at K_max) > 0                         (reported, expected only where R is large);
    X5 region     : if R >= 5 groups, CI_lo(saving inside R at K_max) > 0;
    X6 outside    : if outside-R >= 5 groups, CI_lo(saving outside R) > -2 % at every K.
  Transfer verdict per level: TRANSFER_OK if X1, X3, X5 (when evaluable) and X6 (when evaluable) hold in BOTH deployments.

Stages
  protocol : freeze PX00_protocol.json (pools, previous samples, levels, endpoints, lock) -> also writes the complement sets
  check    : verify the frozen protocol, complement files and lock (checkpoint CK1); run before every measurement
  progress : checkpoint CK2 after each compiled run: run exists, right data, right budget, exactness (X1)
  analyze  : read the compiled runs C17_<DEP>_P<dBm>, compute X1-X6, write PX02/PX03 (checkpoint CK3)
"""
import argparse, csv, hashlib, json, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from screening_policy import group_ci

PROTOCOL = 'PX00_protocol.json'
LEVELS = (30.0, 35.0, 46.0, 49.0)
DEPS = ('UMI', 'UMA')
BETA_TH_30DBM_DB = -132.77   # Corollary 1 with the lock parameters at 30 dBm


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def rj(p): return json.loads(Path(p).read_text(encoding='utf8'))


def wj(p, d): Path(p).write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf8')


def wilson(k, n, z=1.959964):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (float((c - h) / d), float((c + h) / d))


def run_id(dep, lvl): return f'C17_{dep}_P{int(round(lvl))}'


def complement(pool, pool_prov, sample, out):
    with np.load(pool, allow_pickle=False) as d: data = {k: d[k] for k in d.files}
    with np.load(sample, allow_pickle=False) as d: used = set(map(str, d['groups']))
    G = data['groups'].astype(str)
    if not used <= set(G): raise SystemExit(f'{sample} is not a sample of {pool}')
    idx = np.array([i for i, g in enumerate(G) if g not in used])
    if len(idx) == 0: raise SystemExit('empty complement')
    o = {k: (v[idx] if (np.ndim(v) and len(v) == len(G)) else v) for k, v in data.items()}
    np.savez_compressed(out, **o)
    prov = rj(pool_prov) if pool_prov else {}
    prov.update({'prior_use': 'never_seen', 'split': 'pmax_sweep_complement',
                 'pmax_complement': {'pool_sha256': sha(pool), 'excluded_sample_sha256': sha(sample), 'n_groups': int(len(set(G[idx]))),
                                     'rule': 'all pool groups not contained in the V16 natural sample'}})
    wj(out + '.provenance.json', prov)
    return int(len(set(G[idx])))


def stage_protocol(a, root):
    f = root / PROTOCOL
    if f.exists(): raise SystemExit(f'{f} already frozen; use a new run-id to change anything')
    for x in (a.manifest, a.lock, a.umi_pool, a.umi_sample, a.uma_pool, a.uma_sample): Path(x).resolve(strict=True)
    if rj(a.lock)['config_signature'] != rj(a.manifest)['signature']: raise SystemExit('lock does not belong to manifest')
    sets = {}
    for dep, pool, prov, samp in (('UMI', a.umi_pool, a.umi_pool_provenance, a.umi_sample), ('UMA', a.uma_pool, a.uma_pool_provenance, a.uma_sample)):
        out = str(Path(a.data_dir) / f'V17_{dep.lower()}_complement.npz')
        n = complement(pool, prov, samp, out)
        sets[dep] = {'pool': str(pool), 'pool_sha256': sha(pool), 'v16_sample': str(samp), 'v16_sample_sha256': sha(samp),
                     'complement': out, 'complement_sha256': sha(out), 'groups': n}
    s = rj(a.manifest)['settings']
    prot = {'version': 'V17-pmax', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'lock_sha256': sha(a.lock), 'manifest_sha256': sha(a.manifest), 'lock_pmax_w': s['pmax'],
            'levels_dbm': list(LEVELS), 'reference_level_dbm': 30.0, 'deployments': sets,
            'fixed': {k: s[k] for k in ('q', 'sigma_rel', 'sinr_db', 'noise', 'alphas', 'ks', 'beam_counts', 'er_bins', 'guard')},
            'solver': 'compiled (native/screen_core.c), frozen map, oracle check all, 7 repeats, min 20 ms',
            'endpoints': {'X1': 'no mismatch; numeric events <= 1%; no single/double decision change',
                          'X2': 'prevalence of R, Wilson CI', 'X3': 'CI_lo cell-wide saving > -2% at every K',
                          'X4': 'CI_lo cell-wide saving at K_max > 0', 'X5': 'if R >= 5 groups: CI_lo saving in R at K_max > 0',
                          'X6': 'if outside >= 5 groups: CI_lo saving outside R > -2% at every K'},
            'verdict': 'TRANSFER_OK at a level if X1, X3, X5 (if evaluable), X6 (if evaluable) hold in both deployments',
            'max_rel_loss': 0.02, 'bootstrap': a.bootstrap, 'code_sha256': {n: sha(HERE / n) for n in ('pmax_sweep.py', 'compiled_benchmark.py', 'native_search.py', 'native/screen_core.c', 'numeric_agreement.py')}}
    wj(f, prot)
    print('FROZEN', f, sha(f)); print(json.dumps({d: {k: v for k, v in x.items() if k in ('groups', 'complement')} for d, x in sets.items()}, indent=1))


def stage_check(a, root):
    """CK1: everything the measurement relies on is unchanged since the freeze."""
    prot = rj(root / PROTOCOL); bad = []
    if sha(a.lock) != prot['lock_sha256']: bad.append('lock changed')
    if sha(a.manifest) != prot['manifest_sha256']: bad.append('manifest changed')
    for dep, x in prot['deployments'].items():
        if not Path(x['complement']).exists() or sha(x['complement']) != x['complement_sha256']: bad.append(f'{dep} complement changed or missing')
    for n, h in prot['code_sha256'].items():
        if sha(HERE / n) != h: bad.append(f'code changed: {n}')
    out = {'checkpoint': 'CK1', 'ok': not bad, 'problems': bad, 'protocol_sha256': sha(root / PROTOCOL), 'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    wj(root / 'PX01_CK1_check.json', out); print(json.dumps(out, indent=1))
    if bad: raise SystemExit('CK1 FAILED')


def stage_progress(a, root):
    prot = rj(root / PROTOCOL); rows = []; bad = False
    for dep in DEPS:
        for lvl in prot['levels_dbm']:
            d = Path(a.out_root) / run_id(dep, lvl); st = {'run': run_id(dep, lvl)}
            f = d / 'CC04_compiled_decision.json'
            if not f.exists():
                done = len(list((d / 'tasks').glob('*.json'))) if (d / 'tasks').exists() else 0
                st.update(state='NOT FINISHED', groups_done=done)
            else:
                c4 = rj(f); sp = c4.get('single_vs_double_precision_audit') or {}
                okdata = c4['dataset_sha256'] == prot['deployments'][dep]['complement_sha256']
                okp = bool(abs(10 * np.log10(c4['pmax_w']) + 30 - lvl) < 1e-6)
                ok1 = bool(c4.get('C1_exactness_checked_all')) and sp.get('decision_changes', 0) == 0
                st.update(state='DONE' if (okdata and okp and ok1) else 'PROBLEM', data_ok=okdata, pmax_ok=okp, X1=ok1,
                          decisions=c4.get('decisions_checked'), numeric_events=c4.get('numeric_events'))
                bad |= not (okdata and okp and ok1)
            rows.append(st)
    out = {'checkpoint': 'CK2', 'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'runs': rows}
    wj(root / 'PX01b_CK2_progress.json', out)
    for r in rows: print(r)
    if bad: raise SystemExit('CK2: at least one finished run has a PROBLEM (send the log)')


def per_group(rows):
    """saving ratio of sums over L, per (geometry, K)"""
    s = defaultdict(lambda: [0., 0.]); grp = {}; act = {}; er = {}; served = {}
    for r in rows:
        g, k = int(r['geometry']), int(r['K']); s[(g, k)][0] += float(r['routed_saving_ms']); s[(g, k)][1] += float(r['c_card_ms'])
        grp[g] = r['group']; act[(g, k)] = int(r['routed_to_early']); er[(g, k)] = float(r['early_ratio']); served[(g, k)] = int(r['served'])
    return s, grp, act, er, served


def analyze_one(run_dir, prot, seed):
    run_dir = Path(run_dir); c4 = rj(run_dir / 'CC04_compiled_decision.json'); c0 = rj(run_dir / 'CC00_manifest.json')
    rows = list(csv.DictReader(open(run_dir / 'CC01_compiled_geometry.csv', encoding='utf8')))
    s, grp, act, er, served = per_group(rows)
    ks = sorted({k for _, k in s}); kmax = ks[-1]; geos = sorted(grp)
    R = [g for g in geos if act[(g, kmax)]]; O = [g for g in geos if g not in R]
    rel = lambda g, k: s[(g, k)][0] / s[(g, k)][1]
    def ci(v, gs, sd):
        gg = [grp[g] for g in gs]
        return group_ci(v, gg, prot['bootstrap'], seed=sd) if len(set(gg)) >= 3 else (None, None)
    byk = []
    for i, k in enumerate(ks):
        v = [rel(g, k) for g in geos]; lo, hi = ci(v, geos, seed + i)
        vo = [rel(g, k) for g in O]; olo, ohi = ci(vo, O, seed + 50 + i)
        byk.append({'K': k, 'all_mean': float(np.mean(v)), 'all_ci': [lo, hi], 'outside_mean': float(np.mean(vo)) if vo else None, 'outside_ci': [olo, ohi]})
    vr = [rel(g, kmax) for g in R]; rlo, rhi = ci(vr, R, seed + 99) if len(R) >= 5 else (None, None)
    nR, nG = len({grp[g] for g in R}), len(set(grp.values()))
    sp = c4.get('single_vs_double_precision_audit') or {}
    x1 = bool(c4.get('C1_exactness_checked_all')) and (sp.get('decision_changes', 0) == 0)
    x3 = all(b['all_ci'][0] is not None and b['all_ci'][0] > -prot['max_rel_loss'] for b in byk)
    x4 = byk[-1]['all_ci'][0] is not None and byk[-1]['all_ci'][0] > 0
    x5 = None if nR < 5 else bool(rlo is not None and rlo > 0)
    x6 = None if len(O) < 5 else all(b['outside_ci'][0] is not None and b['outside_ci'][0] > -prot['max_rel_loss'] for b in byk)
    bth = BETA_TH_30DBM_DB - (10 * np.log10(c4['pmax_w']) + 30 - 30)
    erK = np.array([er[(g, kmax)] for g in geos])
    hm = 10 * np.log10(kmax * 10 ** (bth / 10) / np.maximum(erK, 1e-300))
    adm = [served[(g, kmax)] for g in geos]
    return {'run': str(run_dir), 'data_sha256': c4['dataset_sha256'], 'pmax_dbm': float(10 * np.log10(c4['pmax_w']) + 30),
            'X1_exact': x1, 'decisions_checked': c4.get('decisions_checked'), 'numeric_events': c4.get('numeric_events'), 'single_double_changes': sp.get('decision_changes'),
            'X2_prevalence': {'region_groups': nR, 'groups': nG, 'share': nR / nG, 'wilson': wilson(nR, nG)},
            'X3_no_harm': x3, 'X4_gain': x4, 'X5_region': x5, 'X6_outside': x6,
            'by_K': byk, 'region_Kmax': {'groups': len(R), 'mean': float(np.mean(vr)) if vr else None, 'ci': [rlo, rhi]},
            'beta_th_db': float(bth), 'threshold_Kmax_db': float(bth + 10 * np.log10(kmax)), 'median_harmonic_gain_Kmax_db': float(np.median(hm)),
            'admitted_Kmax': {'min': int(min(adm)), 'median': float(np.median(adm)), 'max': int(max(adm)), 'zero': int(sum(1 for x in adm if x == 0))},
            'compiled_status': c4['status'], 'card_ms_median_Kmax_sum_L': float(np.median([s[(g, kmax)][1] for g in geos]))}


def stage_analyze(a, root):
    prot = rj(root / PROTOCOL); res = {}; missing = []
    for dep in DEPS:
        for lvl in prot['levels_dbm']:
            d = Path(a.out_root) / run_id(dep, lvl)
            if not (d / 'CC04_compiled_decision.json').exists(): missing.append(str(d)); continue
            r = analyze_one(d, prot, seed=1000 + 10 * int(lvl) + (0 if dep == 'UMI' else 5))
            if r['data_sha256'] != prot['deployments'][dep]['complement_sha256']: raise SystemExit(f'{d} was not run on the frozen complement of {dep}')
            if abs(r['pmax_dbm'] - lvl) > 1e-6: raise SystemExit(f'{d} was run at {r["pmax_dbm"]} dBm, expected {lvl}')
            res[f'{dep}_P{int(lvl)}'] = r
    verdict = {}
    for lvl in prot['levels_dbm']:
        rs = [res.get(f'{d}_P{int(lvl)}') for d in DEPS]
        if any(r is None for r in rs): verdict[str(int(lvl))] = 'INCOMPLETE'; continue
        ok = all(r['X1_exact'] and r['X3_no_harm'] and r['X5_region'] is not False and r['X6_outside'] is not False for r in rs)
        verdict[str(int(lvl))] = 'TRANSFER_OK' if ok else 'TRANSFER_FAILED'
    out = {'checkpoint': 'CK3', 'protocol_sha256': sha(root / PROTOCOL), 'missing_runs': missing, 'verdict_by_level_dbm': verdict, 'results': res}
    wj(root / 'PX02_results.json', out)
    f = lambda x: '—' if x is None else f'{100*x:.1f}%'
    L = ['# V17 power-budget sweep of the frozen map (compiled solver, fresh natural groups)\n',
         '| Deployment | Pmax | Prevalence of R (Wilson) | Median harm. gain vs threshold (K_max) | Saving K=4 (all) | Saving K_max (all) | In R, K_max | Worst outside R | X1 | X3 | X5 | X6 |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for key, r in res.items():
        b4, bk = r['by_K'][0], r['by_K'][-1]; p = r['X2_prevalence']
        wo = min((b['outside_ci'][0] for b in r['by_K'] if b['outside_ci'][0] is not None), default=None)
        L.append(f"| {key.split('_')[0]} | {r['pmax_dbm']:.0f} dBm | {p['region_groups']}/{p['groups']} = {f(p['share'])} [{f(p['wilson'][0])}, {f(p['wilson'][1])}] | "
                 f"{r['median_harmonic_gain_Kmax_db']:.1f} vs {r['threshold_Kmax_db']:.1f} dB | {f(b4['all_mean'])} [{f(b4['all_ci'][0])}, {f(b4['all_ci'][1])}] | "
                 f"{f(bk['all_mean'])} [{f(bk['all_ci'][0])}, {f(bk['all_ci'][1])}] | {f(r['region_Kmax']['mean'])} [{f(r['region_Kmax']['ci'][0])}, {f(r['region_Kmax']['ci'][1])}] | "
                 f"CI_lo {f(wo)} | {r['X1_exact']} | {r['X3_no_harm']} | {r['X5_region']} | {r['X6_outside']} |")
    L.append('\nVerdict by level: ' + ', '.join(f'{k} dBm: **{v}**' for k, v in verdict.items()))
    if missing: L.append('\nMissing runs: ' + ', '.join(missing))
    (root / 'PX03_SUMMARY.md').write_text('\n'.join(L), encoding='utf8'); print('\n'.join(L))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--stage', choices=('protocol', 'check', 'progress', 'analyze'), required=True)
    p.add_argument('--run-id', default='PX17'); p.add_argument('--out-root', default='outputs'); p.add_argument('--data-dir', default='data')
    p.add_argument('--manifest', default=''); p.add_argument('--lock', default='')
    p.add_argument('--umi-pool', default=''); p.add_argument('--umi-pool-provenance', default=''); p.add_argument('--umi-sample', default='')
    p.add_argument('--uma-pool', default=''); p.add_argument('--uma-pool-provenance', default=''); p.add_argument('--uma-sample', default='')
    p.add_argument('--bootstrap', type=int, default=1000)
    a = p.parse_args(); root = Path(a.out_root) / a.run_id; root.mkdir(parents=True, exist_ok=True)
    {'protocol': stage_protocol, 'check': stage_check, 'progress': stage_progress, 'analyze': stage_analyze}[a.stage](a, root)


if __name__ == '__main__': main()
