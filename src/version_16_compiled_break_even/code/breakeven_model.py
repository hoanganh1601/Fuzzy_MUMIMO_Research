#!/usr/bin/env python3
"""V16 part B: analytical break-even model of pre-beam screening (EARLY).

Notation for one channel realization with K users: x_k = gamma N0 / ((||h_k|| - r_k)^2 Pmax), so that
early_ratio = sum_k x_k and EARLY rejects a subset S iff sum_{k in S} x_k > 1 + guard (up to fail-open).

Lemma 1 (no-gain region).  If early_ratio <= 1 + guard, EARLY rejects no subset, hence
        Delta T_EARLY = -(N_vis c_E + c_0) < 0 exactly (pure overhead).
Proof: sum_{k in S} x_k <= sum_k x_k = early_ratio for every S.
Lemma 2 (monotone rejection).  The rejected family is an up-set (S rejected => every superset rejected),
        so by the normalized matching property of the Boolean lattice the rejected FRACTION
        f_s = n_rej(s) / C(K, s) is nondecreasing in the subset size s.
Model.  CARD visits every subset of size s* .. K (s* = optimal cardinality); EARLY skips the L beam
        computations and power solves of each rejected subset:
        Delta T = L * sum_{s=s*}^{K} n_rej(s) c(s)  -  N_vis c_E  -  c_0,     N_vis = sum_{s=s*}^{K} C(K, s),
        c(s) = t1 s + t2 s^2 + t3 s^3  (beam generation + rejection cost per beam rule), c_E, c_0 >= 0.
        n_rej(s) is computed exactly from channel norms (no beam). The coefficients are fitted by
        nonnegative least squares on DEVELOPMENT measurements only and evaluated on test sets.
        A priori variant: s* replaced by s_E = largest size with a non-rejected subset (no solver needed).

  python code/breakeven_model.py --manifest outputs/V152_DM/CP00_manifest.json --run-id M16_PY \
      --fit data/dev.npz outputs/V152_DM:development \
      --validate DM data/V152_dm_test.npz outputs/V152_DM:test \
      --validate 3GPP data/V152_3gpp_test.npz outputs/V152_3GPP:test
  (use C16_* compiled run directories instead of V15.2 directories to model the compiled solver)
"""
import argparse, csv, itertools, json, math, sys
from collections import defaultdict
from math import comb
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from robust_model import jwrite, cwrite, digest
from run_experiment import load_any, rjson, utf8_console


def user_x(h, cfg):
    nrm = np.linalg.norm(h, axis=0); r = cfg['q'] * cfg['sigma'] * nrm / np.sqrt(h.shape[0])
    g = np.maximum(nrm - r, 0.) ** 2
    return np.where(g > 1e-300, cfg['gamma'] * cfg['noise'] / np.maximum(g, 1e-300) / cfg['pmax'], np.inf)


def rejected_counts(x, guard):
    """n_rej(s) for s = 1..K from per-user x (exact enumeration over 2^K subsets; norms only)."""
    K = len(x); n = [0] * (K + 1)
    for s in range(1, K + 1):
        for S in itertools.combinations(range(K), s):
            if sum(x[i] for i in S) > 1 + guard: n[s] += 1
    return n


def load_measurements(src):
    """src = 'DIR:development' | 'DIR:test' (V15.2 Python run) or 'DIR' with CC01 (compiled run)."""
    d, _, phase = src.partition(':'); d = Path(d); meas = {}
    if (d / 'CC01_compiled_geometry.csv').exists():
        for r in csv.DictReader(open(d / 'CC01_compiled_geometry.csv', encoding='utf8')):
            meas[(int(r['geometry']), int(r['K']), int(r['L']))] = {'saving': float(r['early_saving_ms']), 'card': float(r['c_card_ms']),
                                                                   'served': int(r['served']), 'group': r['group']}
        return meas, 'compiled'
    pfile, rfile = (('CP02_development_paired.csv', 'CP01_development_repeats.csv') if phase == 'development'
                    else ('CP06_test_paired_all_policies.csv', 'CP05_test_repeats.csv'))
    served = {(int(r['geometry']), int(r['K']), int(r['L'])): int(r['served']) for r in csv.DictReader(open(d / rfile, encoding='utf8'))
              if r['policy'] == 'CARD' and r['rep'] == '0'}
    for r in csv.DictReader(open(d / pfile, encoding='utf8')):
        if r['policy'] != 'EARLY': continue
        k = (int(r['geometry']), int(r['K']), int(r['L']))
        meas[k] = {'saving': float(r['saving_ms']), 'card': float(r['card_ms']), 'served': served[k], 'group': r['group']}
    return meas, 'python'


def features(H, meas, cfg, guard):
    rows = []; cache = {}
    for (g, k, l), m in sorted(meas.items()):
        if (g, k) not in cache:
            x = user_x(H[g][:, :k], cfg); n = rejected_counts(list(x), guard)
            sE = max((s for s in range(1, k + 1) if n[s] < comb(k, s)), default=0)
            cache[(g, k)] = (x, n, sE)
        x, n, sE = cache[(g, k)]
        for tag, s0 in (('obs', max(m['served'], 1)), ('apriori', max(sE, 1))):
            sizes = range(s0, k + 1)
            row = {'geometry': g, 'group': m['group'], 'K': k, 'L': l, 'variant': tag, 's_star': s0, 'early_ratio': float(np.sum(x)),
                   'measured_saving_ms': m['saving'], 'measured_card_ms': m['card'], 'served': m['served'], 's_E': sE,
                   'N_vis': sum(comb(k, s) for s in sizes),
                   'rej_frac_by_size': json.dumps({s: n[s] / comb(k, s) for s in range(1, k + 1)})}
            for p in (1, 2, 3): row[f'A{p}'] = l * sum(n[s] * s ** p for s in sizes)
            rows.append(row)
    return rows


def design(rows): return np.array([[r['A1'], r['A2'], r['A3'], -r['N_vis'], -1.] for r in rows], float)


def metrics(pred, rows):
    y = np.array([r['measured_saving_ms'] for r in rows]); c = np.array([r['measured_card_ms'] for r in rows])
    pr, yr = pred / c, y / c
    ss = float(np.sum((y - pred) ** 2)); st = float(np.sum((y - y.mean()) ** 2))
    return {'n': len(rows), 'R2_abs': 1 - ss / st if st > 0 else None, 'MAE_ms': float(np.mean(np.abs(y - pred))),
            'MAE_rel_pp': float(100 * np.mean(np.abs(yr - pr))), 'spearman_rel': float(spearmanr(pr, yr).correlation) if len(rows) > 2 else None,
            'sign_agreement': float(np.mean(np.sign(np.round(pred, 9)) == np.sign(np.round(y, 9)))),
            # sign is only informative where the measured effect exceeds timing noise
            'sign_agreement_material': (float(np.mean(np.sign(pr[np.abs(yr) >= .02]) == np.sign(yr[np.abs(yr) >= .02])))
                                        if np.any(np.abs(yr) >= .02) else None),
            'n_material': int(np.sum(np.abs(yr) >= .02))}


def lemma_checks(rows):
    obs = [r for r in rows if r['variant'] == 'obs']
    l1 = [r for r in obs if r['early_ratio'] <= 1 and (r['A1'] > 0)]
    l1_meas = [r for r in obs if r['early_ratio'] <= 1 and r['measured_saving_ms'] > 0]
    mono = 0
    for r in obs:
        f = json.loads(r['rej_frac_by_size']); v = [f[str(s)] for s in range(1, r['K'] + 1)]
        mono += any(v[i] > v[i + 1] + 1e-12 for i in range(len(v) - 1))
    return {'lemma1_rejections_when_er_le_1': len(l1), 'lemma1_positive_measured_savings_when_er_le_1': len(l1_meas),
            'lemma1_rows_with_er_le_1': sum(1 for r in obs if r['early_ratio'] <= 1),
            'lemma2_monotonicity_violations': mono, 'rows': len(obs)}


def population_curve(xpool, theta, L, Ks, guard, draws=400, seed=1):
    """Expected rejected fraction by size and model saving when K users are drawn from the empirical x pool."""
    rng = np.random.default_rng(seed); out = []
    t1, t2, t3, cE, c0 = theta
    for K in Ks:
        fr = np.zeros(K + 1); sav = []
        for _ in range(draws):
            x = list(rng.choice(xpool, size=K, replace=True)); n = rejected_counts(x, guard)
            for s in range(1, K + 1): fr[s] += n[s] / comb(K, s) / draws
            sav.append(L * sum(n[s] * (t1 * s + t2 * s * s + t3 * s ** 3) for s in range(1, K + 1)) - sum(comb(K, s) for s in range(1, K + 1)) * cE - c0)
        out.append({'K': K, 'expected_rej_frac_by_size': {s: float(fr[s]) for s in range(1, K + 1)},
                    'model_saving_ms_all_sizes_mean': float(np.mean(sav)), 'P_positive_saving': float(np.mean(np.array(sav) > 0))})
    return out


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--manifest', required=True); p.add_argument('--run-id', required=True); p.add_argument('--out-root', default='outputs')
    p.add_argument('--fit', nargs=2, metavar=('DATA', 'SOURCE'), required=True)
    p.add_argument('--validate', nargs=3, action='append', default=[], metavar=('NAME', 'DATA', 'SOURCE'))
    p.add_argument('--variant', choices=('obs', 'apriori'), default='obs', help='s* from observed optimum (obs) or norm-only upper bound (apriori)')
    p.add_argument('--population-K', default='4,6,8,10,12')
    a = p.parse_args()
    s = rjson(a.manifest)['settings']
    cfg = {'q': s['q'], 'sigma': s['sigma_rel'], 'gamma': 10**(s['sinr_db'] / 10), 'noise': s['noise'], 'pmax': s['pmax']}; guard = s['guard']
    root = Path(a.out_root) / a.run_id; root.mkdir(parents=True, exist_ok=True)
    allrows = {}; kinds = set()
    for name, data, src in [('FIT',) + tuple(a.fit)] + [tuple(v) for v in a.validate]:
        H, _, _ = load_any(data); meas, kind = load_measurements(src); kinds.add(kind)
        allrows[name] = features(H, meas, cfg, guard)
        print(f'{name}: {len({r["geometry"] for r in allrows[name]})} geometries, {len(meas)} (K,L) measurements, source={kind}')
    if len(kinds) != 1: raise RuntimeError('do not mix python and compiled measurements in one model run')
    fit = [r for r in allrows['FIT'] if r['variant'] == a.variant]
    theta, _ = nnls(design(fit), np.array([r['measured_saving_ms'] for r in fit]))
    names = ['t1_ms_per_size', 't2_ms_per_size2', 't3_ms_per_size3', 'c_E_ms_per_subset', 'c_0_ms']
    res = {'source': kinds.pop(), 'variant': a.variant, 'theta': dict(zip(names, map(float, theta))), 'fit_on': a.fit,
           'metrics': {}, 'lemmas': {}}
    allout = []
    for name, rows in allrows.items():
        rr = [r for r in rows if r['variant'] == a.variant]; pred = design(rr) @ theta
        for r, v in zip(rr, pred): r['predicted_saving_ms'] = float(v); r['set'] = name; allout.append(r)
        res['metrics'][name] = metrics(pred, rr); res['lemmas'][name] = lemma_checks(rows)
        res['metrics'][name]['by_K'] = {k: metrics(pred[[i for i, r in enumerate(rr) if r['K'] == k]], [r for r in rr if r['K'] == k]) for k in sorted({r['K'] for r in rr})}
    cwrite(root / 'CM01_features_predictions.csv', allout, list(allout[0]))
    H, _, _ = load_any(a.fit[0]); xpool = np.concatenate([user_x(h, cfg) for h in H]); xpool = xpool[np.isfinite(xpool)]
    res['population_curve'] = population_curve(xpool, theta, max(s['beam_counts']), [int(v) for v in a.population_K.split(',')], guard)
    res['population_note'] = 'K > 8 is model extrapolation (users drawn i.i.d. from the development x pool; all sizes visited, i.e. s* = 1 upper bound).'
    jwrite(root / 'CM02_model.json', res)
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        col = {'FIT': '#1baf7a'}; pal = ['#2a78d6', '#eb6834', '#8a6ed8', '#e87ba4']
        fig, ax = plt.subplots(figsize=(3.6, 3.0))
        for i, (name, rows) in enumerate(allrows.items()):
            rr = [r for r in rows if r['variant'] == a.variant]
            ax.scatter([100 * r['predicted_saving_ms'] / r['measured_card_ms'] for r in rr], [100 * r['measured_saving_ms'] / r['measured_card_ms'] for r in rr],
                       s=9, color=col.get(name, pal[(i - 1) % 4]), label=name + (' (fit)' if name == 'FIT' else ''), alpha=.75, edgecolors='white', linewidths=.3)
        lim = [-20, 105]; ax.plot(lim, lim, color='#8a8985', lw=.7, ls='--'); ax.set_xlim(lim); ax.set_ylim(lim)
        ax.set_xlabel('Predicted EARLY saving (%)'); ax.set_ylabel('Measured EARLY saving (%)'); ax.legend(fontsize=6, frameon=False)
        for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
        fig.tight_layout(); fig.savefig(root / 'CM03_pred_vs_measured.png', dpi=200)
    except Exception as e: print('figure skipped:', e)
    L = [f'# Break-even model — {a.run_id} (source: {res["source"]}, variant: {a.variant})\n',
         'Fitted on development only: ' + ', '.join(f'{k} = {v:.4g}' for k, v in res['theta'].items()) + '\n',
         '| Set | n | R² (ms) | MAE (pp of CARD) | Spearman (rel.) | Sign agreement (all / where abs(measured) >= 2%) | Lemma 1: rejections / noisy positive timings (rows with early_ratio <= 1) | Lemma 2 violations |', '|---|---|---|---|---|---|---|---|']
    for name in allrows:
        m = res['metrics'][name]; lm = res['lemmas'][name]
        L.append(f"| {name} | {m['n']} | {m['R2_abs']:.3f} | {m['MAE_rel_pp']:.2f} | {m['spearman_rel']:.3f} | {100*m['sign_agreement']:.1f}% / {('—' if m['sign_agreement_material'] is None else f"{100*m['sign_agreement_material']:.1f}%")} (n={m['n_material']}) | "
                 f"{lm['lemma1_rejections_when_er_le_1']} rej. / {lm['lemma1_positive_measured_savings_when_er_le_1']} gains of {lm['lemma1_rows_with_er_le_1']} | {lm['lemma2_monotonicity_violations']} |")
    L.append('\nPopulation curve (model, development x pool): ' + '; '.join(f"K={c['K']}: P(gain) {100*c['P_positive_saving']:.0f}%, mean {c['model_saving_ms_all_sizes_mean']:.2f} ms" for c in res['population_curve']))
    (root / 'CM04_SUMMARY.md').write_text('\n'.join(L), encoding='utf8'); print('\n'.join(L))


if __name__ == '__main__': main()
