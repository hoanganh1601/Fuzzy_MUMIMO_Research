#!/usr/bin/env python3
"""One-command reproduction of manuscript Section V (A-D) and its tables.

  A  Exactness and scheduling performance  -> ablation_certified.py on the dev set
  B  Incremental benefit of safe screening -> same run (EXHAUSTIVE, CARDINALITY_ONLY,
     ALL, WITHOUT_<rule>; repeated, order-randomized runtime)
  C  Boundary stress                        -> boundary_stress.py
  D  Independent validation                 -> independent_validation.py
     (lock -> preflight -> scan -> report) for every --test DATA:PROVENANCE pair

All stages are resumable through their own task checkpoints; rerun the same
command with the same --tag to continue. Afterwards MANUSCRIPT_TABLES.md and
manuscript_results.json are generated from the checkpoint outputs only.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from reference_model import utf8_console
import csv

CODE = Path(__file__).resolve().parent


def run(args):
    cmd = [sys.executable, str(CODE / args[0])] + args[1:]
    print('>>', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def rcsv(p):
    with open(p, newline='', encoding='utf8') as f: return list(csv.DictReader(f))


def pct(new, base): return 100.0 * (base - new) / base


def tables(out, tag, dev_label, tests, boundary_id):
    A = out / f'{tag}_AB'
    dec = json.loads((A / 'CP06_decision.json').read_text(encoding='utf8'))
    summ = {r['variant']: r for r in rcsv(A / 'CP03_ablation_summary.csv')}
    man = json.loads((A / 'CP00_manifest.json').read_text(encoding='utf8'))
    N = dec['n_geometries']; ex = dec['exactness']
    f = lambda r, k: float(r[k]) if r[k] not in ('', None) else float('nan')
    res = dict(dataset_label=dev_label, A=dict(n=N, candidates=man['n_candidates_per_geometry'],
               exact_matches={k: int(v['exact_matches']) for k, v in summ.items()}, **ex,
               false_prunes=dec['false_prunes'], fail_open=dec['n_near_fail_open']))
    L = []
    L.append(f'# Manuscript tables — run `{tag}`\n')
    L.append(f'**Dev dataset:** {dev_label}. Numbers below come only from checkpoint outputs of this run.\n')
    L.append('## Table A — Exactness and scheduling performance\n')
    L.append('| Metric | Value |\n|---|---|')
    L.append(f'| Channel geometries | {N} |')
    L.append(f'| Candidates per geometry | {man["n_candidates_per_geometry"]} |')
    L.append(f'| Exact match with exhaustive (ALL / CARDINALITY_ONLY) | {summ["ALL"]["exact_matches"]}/{N} / {summ["CARDINALITY_ONLY"]["exact_matches"]}/{N} |')
    for k in ('4', '3', '2', '1', '0'):
        L.append(f'| Optimum serves {k} users | {ex["cardinality_distribution"][k]}/{N} ({100*ex["cardinality_distribution"][k]/N:.1f}%) |')
    L.append(f'| Mean admitted users | {ex["mean_admitted_users"]:.4f} |')
    L.append(f'| Optimum beam ZF / RZF | {ex["beam_type_of_optimum"]["ZF"]} / {ex["beam_type_of_optimum"]["RZF"]} |')
    L.append(f'| False prunes (all {dec["candidate_count"]} candidate audits) | {dec["false_prunes"]} |')
    L.append(f'| Fail-open activations | {dec["n_near_fail_open"]} |\n')
    L.append('## Table B — Incremental benefit (per geometry, mean over geometries; runtime = median of repeated runs)\n')
    L.append('| Variant | Full solves | Beams built | Runtime (ms) | Beam (ms) | Screening (ms) | Solver (ms) |\n|---|---|---|---|---|---|---|')
    order = ['EXHAUSTIVE', 'CARDINALITY_ONLY', 'ALL'] + [k for k in summ if k.startswith('WITHOUT_')]
    for k in order:
        r = summ[k]
        fm = lambda x: '—' if x != x else f'{x:.4f}'
        L.append(f'| {k} | {f(r,"mean_full_solves"):.4f} | {f(r,"mean_beams_built"):.4f} | {f(r,"mean_runtime_ms"):.4f} | {fm(f(r,"mean_beam_ms"))} | {fm(f(r,"mean_screening_ms"))} | {fm(f(r,"mean_solver_ms"))} |')
    c, a, e = summ['CARDINALITY_ONLY'], summ['ALL'], summ['EXHAUSTIVE']
    B = dict(solves=dict(exhaustive=f(e, 'mean_full_solves'), cardinality_only=f(c, 'mean_full_solves'), all=f(a, 'mean_full_solves')),
             runtime_ms=dict(exhaustive=f(e, 'mean_runtime_ms'), cardinality_only=f(c, 'mean_runtime_ms'), all=f(a, 'mean_runtime_ms')),
             solve_reduction_vs_cardinality_pct=pct(f(a, 'mean_full_solves'), f(c, 'mean_full_solves')),
             runtime_reduction_vs_cardinality_pct=pct(f(a, 'mean_runtime_ms'), f(c, 'mean_runtime_ms')),
             runtime_reduction_vs_exhaustive_pct=pct(f(a, 'mean_runtime_ms'), f(e, 'mean_runtime_ms')),
             runtime_saved_vs_cardinality_ci95=dec['runtime_saved_ci95'],
             runtime_saved_vs_exhaustive_ci95=dec['runtime_saved_vs_exhaustive_ci95'],
             solver_calls_saved_ci95=dec['solver_calls_ci95'],
             runtime_advantage_vs_cardinality_confirmed=dec['runtime_advantage_confirmed'],
             pruned_by_reference_status=dec['pruned_candidates_by_reference_status'],
             solve_cost_by_status_ms=dec['solve_cost_by_status_ms'], repeats=dec['repeats'])
    res['B'] = B
    ci = dec['runtime_saved_ci95']; ce = dec['runtime_saved_vs_exhaustive_ci95']
    L.append('')
    L.append(f'- Full solves, ALL vs CARDINALITY_ONLY: {B["solves"]["all"]:.4f} vs {B["solves"]["cardinality_only"]:.4f} ({B["solve_reduction_vs_cardinality_pct"]:.2f}% fewer).')
    L.append(f'- Runtime, ALL vs CARDINALITY_ONLY: {B["runtime_ms"]["all"]:.4f} vs {B["runtime_ms"]["cardinality_only"]:.4f} ms ({B["runtime_reduction_vs_cardinality_pct"]:+.2f}% reduction); paired saving 95% cluster-bootstrap CI [{ci["lo"]:.4f}, {ci["hi"]:.4f}] ms over {ci["n_groups"]} groups → advantage confirmed: **{dec["runtime_advantage_confirmed"]}**.')
    L.append(f'- Runtime, ALL vs EXHAUSTIVE: {B["runtime_ms"]["all"]:.4f} vs {B["runtime_ms"]["exhaustive"]:.4f} ms ({B["runtime_reduction_vs_exhaustive_pct"]:.2f}% reduction); CI [{ce["lo"]:.4f}, {ce["hi"]:.4f}] ms.')
    L.append(f'- Reference status of certificate-pruned candidates: {B["pruned_by_reference_status"]}.')
    L.append('\n| Reference status | Evaluations (exhaustive) | Beam generation (ms) | Power solve (ms) | Pruned by ALL |\n|---|---|---|---|---|')
    for k, v in B['solve_cost_by_status_ms'].items():
        L.append(f'| {k} | {v["n"]} | {v["beam"]:.4f} | {v["power_solve"]:.4f} | {B["pruned_by_reference_status"].get(k, 0)} |')
    L.append('')
    sc = f(a, 'mean_screening_ms'); saved = sum(B['pruned_by_reference_status'].get(k, 0) * v['power_solve'] for k, v in B['solve_cost_by_status_ms'].items()) / N
    B['screening_cost_ms'] = sc; B['estimated_power_solve_time_avoided_ms'] = saved
    L.append(f'- Cost balance per geometry under ALL: screening {sc:.4f} ms vs. estimated power-solve time avoided {saved:.4f} ms (pruned candidates × mean power-solve cost of their reference status). Beam generation is not avoided for candidates pruned after beam generation.\n')
    L.append('## Table B2 — Certificate ablation (difference to ALL; positive = removing the rule costs more)\n')
    L.append('| Removed rule | Δ full solves | Δ runtime (ms) | Prunes by rule under ALL (mean/geometry) |\n|---|---|---|---|')
    abl = []
    for k in order[3:]:
        rule = k[len('WITHOUT_'):]
        d1 = f(summ[k], 'mean_full_solves') - f(a, 'mean_full_solves'); d2 = f(summ[k], 'mean_runtime_ms') - f(a, 'mean_runtime_ms')
        geo = rcsv(A / 'CP01_ablation_geometry.csv'); per = np.mean([float(g[rule]) for g in geo if g['variant'] == 'ALL'])
        abl.append(dict(rule=rule, delta_solves=d1, delta_runtime_ms=d2, prunes_under_all=per))
        L.append(f'| {rule} | {d1:+.4f} | {d2:+.4f} | {per:.4f} |')
    res['B2'] = abl
    L.append('')
    if boundary_id:
        bd = json.loads((out / boundary_id / 'CP02_boundary_decision.json').read_text(encoding='utf8'))
        res['C'] = bd
        L.append('## Table C — Boundary stress\n')
        L.append(f'Outcome **{bd["outcome"]}** — {bd["n_cases"]} cases, {bd["false_prunes"]} false prunes, {bd["fail_open_cases"]} fail-open, {bd["feasible_reference_cases"]} feasible reference cases.\n')
        L.append('| Family | Cases | Feasible truth | Prune | Fail-open | False prune |\n|---|---|---|---|---|---|')
        for k, v in bd['by_family'].items():
            L.append(f'| {k} | {v["cases"]} | {v["feasible_truth"]} | {v["prune"]} | {v["fail_open"]} | {v["false_prune"]} |')
        L.append('')
    res['D'] = {}
    if tests:
        L.append('## Table D — Independent validation (locked protocol)\n')
        L.append('| Run | Source | Geometries / groups | False prunes | Calls saved (mean) | Runtime ALL / CARD (ms) | Saving CI95 (ms) | GO |\n|---|---|---|---|---|---|---|---|')
        for rid, _, prov in tests:
            d = json.loads((out / rid / 'CP05_independent_decision.json').read_text(encoding='utf8'))
            src = json.loads(Path(prov).read_text(encoding='utf8'))['source']
            res['D'][rid] = d
            L.append(f'| {rid} | {src} | {d["n_geometries"]}/{d["n_groups"]} | {d["false_prunes"]} | {d["mean_calls_saved"]:.4f} | {d["mean_all_runtime_ms"]:.4f} / {d["mean_cardinality_runtime_ms"]:.4f} | [{d["runtime_ci95"]["lo"]:.4f}, {d["runtime_ci95"]["hi"]:.4f}] | {d["observed_runtime_go"]} |')
        L.append('')
    (out / f'{tag}_MANUSCRIPT_TABLES.md').write_text('\n'.join(L), encoding='utf8')
    (out / f'{tag}_manuscript_results.json').write_text(json.dumps(res, indent=2), encoding='utf8')
    print('\n'.join(L))


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dev', required=True, help='development dataset NPZ (e.g. v10 DeepMIMO, 160 geometries)')
    ap.add_argument('--dev-label', default='', help='label printed in tables, e.g. "DeepMIMO v10 development set"')
    ap.add_argument('--test', action='append', nargs=3, default=[], metavar=('RUNID', 'DATA.npz', 'PROVENANCE.json'),
                    help='independent test set (three separate values, safe for Windows paths such as C:\\data\\x.npz); '
                         'repeat for DeepMIMO-new and Sionna-3GPP. Lock happens before the data are read.')
    ap.add_argument('--tag', required=True); ap.add_argument('--out-root', default='outputs')
    ap.add_argument('--repeats', type=int, default=5); ap.add_argument('--bootstrap', type=int, default=2000)
    ap.add_argument('--boundary-limit', type=int, default=20)
    ap.add_argument('--skip', default='', help='comma list of stages to skip: AB,C,D')
    a = ap.parse_args(); skip = set(filter(None, a.skip.split(',')))
    out = Path(a.out_root); tests = []
    for rid, data, prov in a.test:
        for f in (data, prov):
            if not Path(f).is_file(): raise FileNotFoundError(f)
        tests.append((rid, data, prov))
    if not Path(a.dev).is_file(): raise FileNotFoundError(a.dev)
    if 'AB' not in skip:
        for st in ('preflight', 'scan', 'report'):
            run(['ablation_certified.py', '--stage', st, '--dataset', a.dev, '--run-id', f'{a.tag}_AB', '--out-root', str(out),
                 '--repeats', str(a.repeats), '--bootstrap', str(a.bootstrap)])
    bid = f'{a.tag}_C'
    if 'C' not in skip:
        run(['boundary_stress.py', '--stage', 'all', '--run-id', bid, '--out-root', str(out), '--dataset', a.dev, '--limit', str(a.boundary_limit)])
    if 'D' not in skip:
        for rid, data, prov in tests:
            common = ['--run-id', rid, '--out-root', str(out), '--repeats', str(a.repeats), '--bootstrap', str(a.bootstrap)]
            if not (out / rid / 'CP00_locked_protocol.json').exists():
                run(['independent_validation.py', '--stage', 'lock'] + common)
            for st in ('preflight', 'scan', 'report'):
                run(['independent_validation.py', '--stage', st, '--dataset', data, '--provenance', prov] + common)
    tables(out, a.tag, a.dev_label or a.dev, tests, bid)


if __name__ == '__main__': main()
