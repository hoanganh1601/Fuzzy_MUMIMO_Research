#!/usr/bin/env python3
"""V16 part A: natural-prevalence test of the frozen V15.2 policy map.

V15.2 tested the map on covariate-STRATIFIED sets (50 % inside the predicted region R). Here the
test set is a SIMPLE RANDOM SAMPLE of whole groups from a sealed pool that represents a cell as
deployed (uniform user drops, no distance filter), so the fraction of R and the cell-wide expected
saving are estimated without design weighting.

Stages (the protocol is frozen BEFORE the sample is drawn):
  protocol : write NP00_natural_protocol.json (lock, pool hash, sample size, seed, endpoints, thresholds)
  sample   : draw the simple random sample of groups -> NPZ + provenance (no covariate is used)
  -- then run V15.2 on the sample with the frozen lock:
     run_experiment.py --stage test-preflight / test --lock-from <V15.2 CP03> --allow-small-region
  analyze  : endpoints N1-N4 from the V15.2 run (and optionally a compiled run on the same sample)

Predeclared endpoints (natural cell):
  N1 prevalence of R: proportion of groups whose K_max cell is locked non-CARD, Wilson 95 % CI (estimate);
  N2 expected gain: CI_lo(mean relative saving of the frozen map at K_max over ALL geometries) > 0;
  N3 no harm: CI_lo(mean relative saving at every K) > -max_rel_loss (default 2 %);
  N4 consistency: if R has >= 5 groups, CI_lo(mean relative saving inside R at K_max) > 0 (else not evaluable).
Status: NATURAL_GAIN (N2, N3, N4 ok or not evaluable) | NATURAL_NO_HARM (N3 only) | NATURAL_HARM.
"""
import argparse, csv, hashlib, json, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from robust_model import digest, jwrite
from run_experiment import rjson, utf8_console
from screening_policy import group_ci

PROTOCOL = 'NP00_natural_protocol.json'


def wilson(k, n, z=1.959964):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (float((c - h) / d), float((c + h) / d))


def stage_protocol(a, root):
    lock = rjson(a.lock); man = rjson(a.manifest)
    if lock['config_signature'] != man['signature']: raise RuntimeError('lock does not belong to manifest')
    pool = np.load(a.pool, allow_pickle=False); groups = sorted(set(map(str, pool['groups'])))
    if a.n_groups > len(groups): raise RuntimeError(f'pool has {len(groups)} groups; {a.n_groups} requested')
    prot = {'version': 'V16-natural', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'lock_sha256': digest(a.lock), 'lock_signature': lock['config_signature'], 'manifest_sha256': digest(a.manifest),
            'pool_sha256': digest(a.pool), 'pool_groups': len(groups), 'n_groups': a.n_groups, 'seed': a.seed,
            'sampling': 'simple random sample of whole groups without replacement; no covariate, no runtime',
            'endpoints': {'N1': 'prevalence of R with Wilson CI (estimate)', 'N2': 'CI_lo mean relative saving at K_max (all geometries) > 0',
                          'N3': f'CI_lo mean relative saving at every K > -{a.max_rel_loss}', 'N4': 'if R >= 5 groups: CI_lo mean relative saving in R at K_max > 0'},
            'max_rel_loss': a.max_rel_loss, 'bootstrap': a.bootstrap, 'code_sha256': digest(Path(__file__))}
    if a.scenario_spec:   # V16.3: the deployment was frozen before the pool was generated
        spec = rjson(a.scenario_spec); val = rjson(a.pool_validation) if a.pool_validation else None
        if val is None or not val.get('ok'): raise RuntimeError('give --pool-validation (NS01) of an ACCEPTED pool')
        if val['pool_sha256'] != prot['pool_sha256']: raise RuntimeError('pool validation belongs to another pool')
        if val['scenario_spec_sha256'] != digest(a.scenario_spec): raise RuntimeError('pool validation belongs to another scenario spec')
        if a.n_groups != spec['sample_groups'] or a.seed != spec['sample_seed']: raise RuntimeError(f"use --n-groups {spec['sample_groups']} --seed {spec['sample_seed']} (frozen in the spec)")
        prot.update({'scenario_spec_sha256': digest(a.scenario_spec), 'scenario': spec['scenario'], 'pool_validation_sha256': digest(a.pool_validation),
                     'comparison': 'secondary: prevalence and K_max saving versus the UMi natural run, reported with --stage compare'})
    f = root / PROTOCOL
    if f.exists():
        old = rjson(f); keep = {k: v for k, v in old.items() if k != 'created_utc'}
        if keep != {k: v for k, v in prot.items() if k != 'created_utc'}: raise RuntimeError('protocol already frozen with different content; use a new run-id')
        print('protocol already frozen (unchanged)'); return
    jwrite(f, prot); print('FROZEN', f); print(json.dumps(prot, indent=2, ensure_ascii=False))


def stage_sample(a, root):
    prot = rjson(root / PROTOCOL)
    if digest(a.pool) != prot['pool_sha256']: raise RuntimeError('pool differs from the frozen protocol')
    with np.load(a.pool, allow_pickle=False) as d:
        data = {k: d[k] for k in d.files}
    G = data['groups'].astype(str); groups = sorted(set(G))
    pick = set(np.random.default_rng(prot['seed']).choice(groups, prot['n_groups'], replace=False))
    idx = np.array([i for i, g in enumerate(G) if g in pick]); out = {}
    for k, v in data.items():
        out[k] = v[idx] if (np.ndim(v) and len(v) == len(G)) else v
    np.savez_compressed(a.output, **out)
    prov = rjson(a.pool_provenance) if a.pool_provenance else {}
    prov.update({'prior_use': 'never_seen', 'split': 'natural_prevalence_test',
                 'natural_sample': {'rule': prot['sampling'], 'pool_sha256': prot['pool_sha256'], 'n_groups': prot['n_groups'],
                                    'seed': prot['seed'], 'protocol_sha256': digest(root / PROTOCOL)}})
    Path(a.output + '.provenance.json').write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding='utf8')
    print('WROTE', a.output, out['H'].shape)


def per_geometry(frozen_csv):
    s = defaultdict(lambda: [0., 0.]); act = defaultdict(int); grp = {}
    for r in csv.DictReader(open(frozen_csv, encoding='utf8')):
        g, k = int(r['geometry']), int(r['K']); s[(g, k)][0] += float(r['saved_ms']); s[(g, k)][1] += float(r['card_ms'])
        act[(g, k)] += int(r['selected_policy'] != 'CARD'); grp[g] = r['group']
    return s, act, grp


def stage_analyze(a, root):
    prot = rjson(root / PROTOCOL); run = Path(a.v152_run)
    pre = rjson(run / 'CP04_test_preflight.json')
    ns = pre['source'].get('natural_sample', {})
    if ns.get('protocol_sha256') != digest(root / PROTOCOL): raise RuntimeError('the V15.2 run was not made on the sample of this protocol')
    if rjson(run / 'CP03_locked_cells.json')['config_signature'] != prot['lock_signature']: raise RuntimeError('lock differs from protocol')
    s, act, grp = per_geometry(run / 'CP07_frozen_policy_geometry.csv')
    ks = sorted({k for _, k in s}); kmax = ks[-1]; geos = sorted(grp)
    R = [g for g in geos if act[(g, kmax)] > 0]; nR = len({grp[g] for g in R}); nG = len(set(grp.values()))
    rel = lambda g, k: s[(g, k)][0] / s[(g, k)][1]
    def ci(v, gs, sd): gg = [grp[g] for g in gs]; return group_ci(v, gg, prot['bootstrap'], seed=sd) if len(set(gg)) >= 3 else (None, None)
    byk = []
    for i, k in enumerate(ks):
        v = [rel(g, k) for g in geos]; lo, hi = ci(v, geos, 11 + i)
        tot = sum(s[(g, k)][0] for g in geos) / sum(s[(g, k)][1] for g in geos)
        boot = []
        rng = np.random.default_rng(91 + i); gl = sorted(set(grp.values())); byg = defaultdict(list)
        for g in geos: byg[grp[g]].append(g)
        for _ in range(prot['bootstrap']):
            dr = rng.choice(len(gl), len(gl)); gs = [g for j in dr for g in byg[gl[j]]]
            boot.append(sum(s[(g, k)][0] for g in gs) / sum(s[(g, k)][1] for g in gs))
        byk.append({'K': k, 'mean_rel_saving': float(np.mean(v)), 'ci_lo': lo, 'ci_hi': hi,
                    'total_time_saving': float(tot), 'total_ci_lo': float(np.quantile(boot, .025)), 'total_ci_hi': float(np.quantile(boot, .975)),
                    'mean_card_ms_sum_L': float(np.mean([s[(g, k)][1] for g in geos]))})
    top = byk[-1]
    rv = [rel(g, kmax) for g in R]; rc = ci(rv, R, 71) if nR >= 5 else (None, None)
    n1 = {'region_groups': nR, 'groups': nG, 'prevalence': nR / nG, 'wilson_ci': wilson(nR, nG)}
    n2 = top['ci_lo'] is not None and top['ci_lo'] > 0
    n3 = all(b['ci_lo'] is not None and b['ci_lo'] > -prot['max_rel_loss'] for b in byk)
    n4 = None if nR < 5 else bool(rc[0] is not None and rc[0] > 0)
    status = 'NATURAL_GAIN' if (n2 and n3 and n4 is not False) else ('NATURAL_NO_HARM' if n3 else 'NATURAL_HARM')
    res = {'status': status, 'N1_prevalence': n1, 'N2_expected_gain_Kmax': n2, 'N3_no_harm_all_K': n3, 'N4_region_consistent': n4,
           'by_K_all_geometries': byk, 'region_at_Kmax': {'geometries': len(R), 'mean_rel_saving': float(np.mean(rv)) if rv else None, 'ci_lo': rc[0], 'ci_hi': rc[1]},
           'v152_run': str(run), 'test_sha256': pre['test_sha256']}
    if a.compiled_run:
        rows = list(csv.DictReader(open(Path(a.compiled_run) / 'CC01_compiled_geometry.csv', encoding='utf8')))
        cs = defaultdict(lambda: [0., 0.])
        for r in rows: cs[(int(r['geometry']), int(r['K']))][0] += float(r['routed_saving_ms']); cs[(int(r['geometry']), int(r['K']))][1] += float(r['c_card_ms'])
        res['compiled_by_K'] = []
        for i, k in enumerate(ks):
            v = [cs[(g, k)][0] / cs[(g, k)][1] for g in geos if (g, k) in cs]; lo, hi = ci(v, [g for g in geos if (g, k) in cs], 211 + i)
            res['compiled_by_K'].append({'K': k, 'mean_rel_saving_routed': float(np.mean(v)), 'ci_lo': lo, 'ci_hi': hi})
    jwrite(root / 'NP02_natural_decision.json', res)
    f = lambda x: '—' if x is None else f'{100*x:.2f}%'
    L = [f'# Natural-prevalence test: **{status}**\n',
         f"Prevalence of the predicted region R: {nR}/{nG} groups = {100*n1['prevalence']:.1f}% (Wilson 95% CI {f(n1['wilson_ci'][0])} – {f(n1['wilson_ci'][1])}).\n",
         '| K | Mean relative saving (all geometries) | CI95 | Total-time saving | CI95 |', '|---|---|---|---|---|']
    for b in byk: L.append(f"| {b['K']} | {f(b['mean_rel_saving'])} | [{f(b['ci_lo'])}, {f(b['ci_hi'])}] | {f(b['total_time_saving'])} | [{f(b['total_ci_lo'])}, {f(b['total_ci_hi'])}] |")
    L.append(f"\nInside R at K={kmax}: {f(res['region_at_Kmax']['mean_rel_saving'])} [{f(rc[0])}, {f(rc[1])}] ({len(R)} geometries). N2={n2}, N3={n3}, N4={n4}.")
    if a.compiled_run: L.append('Compiled ROUTED (same sample): ' + '; '.join(f"K={c['K']}: {f(c['mean_rel_saving_routed'])} [{f(c['ci_lo'])}, {f(c['ci_hi'])}]" for c in res['compiled_by_K']))
    (root / 'NP03_SUMMARY.md').write_text('\n'.join(L), encoding='utf8'); print('\n'.join(L))


def newcombe(k1, n1, k2, n2):
    """Newcombe hybrid-score 95% CI for p2 - p1."""
    l1, u1 = wilson(k1, n1); l2, u2 = wilson(k2, n2); p1, p2 = k1 / n1, k2 / n2
    d = p2 - p1
    return (float(d - np.sqrt((p2 - l2)**2 + (u1 - p1)**2)), float(d + np.sqrt((u2 - p2)**2 + (p1 - l1)**2)))


def stage_compare(a, root):
    """Secondary analysis: natural run A (e.g. UMi NP16) versus natural run B (this run, e.g. UMa NP16B)."""
    A = rjson(Path(a.compare_with) / 'NP02_natural_decision.json'); B = rjson(root / 'NP02_natural_decision.json')
    pa, pb = rjson(Path(a.compare_with) / PROTOCOL), rjson(root / PROTOCOL)
    if pa['lock_signature'] != pb['lock_signature']: raise RuntimeError('the two natural runs use different locks')
    na, nb = A['N1_prevalence'], B['N1_prevalence']
    diff = nb['prevalence'] - na['prevalence']; dci = newcombe(na['region_groups'], na['groups'], nb['region_groups'], nb['groups'])
    ka, kb = A['by_K_all_geometries'][-1], B['by_K_all_geometries'][-1]
    out = {'A': {'run': str(a.compare_with), 'scenario': pa.get('scenario', 'not recorded'), 'status': A['status'], 'prevalence': na, 'Kmax_all': ka},
           'B': {'run': str(root), 'scenario': pb.get('scenario', 'not recorded'), 'status': B['status'], 'prevalence': nb, 'Kmax_all': kb},
           'prevalence_difference_B_minus_A': diff, 'newcombe_ci95': dci}
    jwrite(root / 'NP04_comparison.json', out)
    f = lambda x: '—' if x is None else f'{100*x:.2f}%'
    L = ['# Natural runs compared (secondary)\n', '| Run | Scenario | Status | Prevalence of R | Wilson CI | Saving at K_max (all) | CI95 |', '|---|---|---|---|---|---|---|']
    for t in ('A', 'B'):
        o = out[t]; p = o['prevalence']
        L.append(f"| {t} | {o['scenario']} | {o['status']} | {p['region_groups']}/{p['groups']} = {f(p['prevalence'])} | [{f(p['wilson_ci'][0])}, {f(p['wilson_ci'][1])}] | {f(o['Kmax_all']['mean_rel_saving'])} | [{f(o['Kmax_all']['ci_lo'])}, {f(o['Kmax_all']['ci_hi'])}] |")
    L.append(f"\nDifference of prevalence (B - A): {f(diff)}, Newcombe 95% CI [{f(dci[0])}, {f(dci[1])}].")
    (root / 'NP05_COMPARISON.md').write_text('\n'.join(L), encoding='utf8'); print('\n'.join(L))


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--stage', choices=('protocol', 'sample', 'analyze', 'compare'), required=True)
    p.add_argument('--run-id', required=True); p.add_argument('--out-root', default='outputs')
    p.add_argument('--manifest', default=''); p.add_argument('--lock', default=''); p.add_argument('--pool', default='')
    p.add_argument('--pool-provenance', default=''); p.add_argument('--output', default='')
    p.add_argument('--n-groups', type=int, default=100); p.add_argument('--seed', type=int, default=20261120)
    p.add_argument('--max-rel-loss', type=float, default=.02); p.add_argument('--bootstrap', type=int, default=1000)
    p.add_argument('--v152-run', default=''); p.add_argument('--compiled-run', default='')
    p.add_argument('--scenario-spec', default=''); p.add_argument('--pool-validation', default=''); p.add_argument('--compare-with', default='')
    a = p.parse_args(); root = Path(a.out_root) / a.run_id; root.mkdir(parents=True, exist_ok=True)
    {'protocol': stage_protocol, 'sample': stage_sample, 'analyze': stage_analyze, 'compare': stage_compare}[a.stage](a, root)


if __name__ == '__main__': main()
