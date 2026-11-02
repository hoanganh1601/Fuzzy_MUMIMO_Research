"""Tests for experiment_r.py. Run: python tests/test_r_pipeline.py  (or pytest)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parents[1] / 'code'
sys.path.insert(0, str(CODE))
from experiment import gaussian_q, fuzzy_q  # noqa: E402
from experiment_r import split, candidate_grids, margin, fallback_safe, rank, paired  # noqa: E402

QG = gaussian_q(.05, 4)


def test_fail_closed_fallback():
    fb = fallback_safe(QG)
    for z in [(0., 0.), (.5, .5), (1., 1.), (.3, .9)]:
        assert margin('fuzzy_safe', z, fb)[0] >= QG - 1e-12


def test_disjoint_group_splits():
    groups = np.repeat(np.arange(20), 10)
    s = split(groups, 123)
    allidx = np.concatenate(list(s.values()))
    assert len(allidx) == len(np.unique(allidx)) == len(groups)
    gs = {k: set(groups[v]) for k, v in s.items()}
    assert all(not (gs[a] & gs[b]) for a in gs for b in gs if a != b)


def test_grids_not_degenerate():
    g = candidate_grids(QG)
    raw = [json.dumps(c['rules']) for c in g['fuzzy_raw']]
    safe = [json.dumps([c['rules'], c['qfloor']]) for c in g['fuzzy_safe']]
    assert len(raw) == len(set(raw)) and len(safe) == len(set(safe))          # no duplicated candidates
    for c in g['fuzzy_safe']:                                                 # floor binds for some, not all
        assert min(c['rules']) < c['qfloor'] < max(c['rules'])
    fixed = [c['q'] for c in g['fixed']]
    assert all(any(abs(c['qfloor'] - q) < 1e-9 for q in fixed) for c in g['fuzzy_safe'])
    lo = min(min(c['rules']) for c in g['fuzzy_raw'])
    hi = max(max(c['rules']) for c in g['fuzzy_raw'])
    assert min(fixed) <= lo + .2 and max(fixed) >= hi - 1e-9                  # fixed grid spans fuzzy outputs
    assert all(max(c['rules']) <= QG + 1e-12 for c in g['fuzzy_raw'])


def test_margin_safe_dominates_raw():
    g = candidate_grids(QG)
    for c in g['fuzzy_safe'][:10]:
        for z in np.random.default_rng(0).random((50, 2)):
            qs, act = margin('fuzzy_safe', z, c)
            qr = fuzzy_q(z, c['rules'])
            assert qs >= qr - 1e-12 and qs >= c['qfloor'] - 1e-12 and act == int(c['qfloor'] > qr)


def test_rank_common_set():
    mk = lambda i, f, pw: dict(index=i, feasible=f, power_w=pw if f else None, n_mc=100 if f else 0, n_fail=0,
                               effective_failure=0. if f else 1., floor_active=0)
    a = [mk(i, 1, 1.) for i in range(39)] + [mk(39, 1, 9.)]
    b = [mk(i, 1, 2.) for i in range(39)] + [mk(39, 0, 0)]      # drops hard channel, eff = 0.025 <= eps
    order, st = rank([a, b], .05)
    assert order[0] == 0 and st[0]['n_common'] == 39


def test_paired_group_bootstrap():
    rows = []
    for i in range(60):
        for m, pw in (('x', 1.), ('gaussian', 2.)):
            rows.append(dict(index=i, group=str(i // 5), method=m, feasible=1, power_w=pw, effective_failure=0.))
    c = paired(rows, 'x', 'gaussian', 200, 1)
    assert abs(c['mean_common_power_ratio'] - .5) < 1e-12 and abs(c['mean_db'] + 3.0103) < 1e-3


def test_end_to_end_and_transfer():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)

        def run(*x, ok=True):
            r = subprocess.run([sys.executable, str(CODE / x[0]), *x[1:]], cwd=d, capture_output=True, text=True)
            assert (r.returncode == 0) == ok, r.stderr[-2000:]
            return r
        run('generate_data.py', '--source', 'synthetic', '--M', '16', '--n', '240', '--output', 'demo.npz')
        run('generate_data.py', '--source', 'umi_inspired', '--M', '16', '--n', '240', '--output', 'umi.npz')
        base = ['--dataset', 'demo.npz', '--run-id', 'S', '--limit', '3', '--n-mc', '20', '--bootstrap', '100']
        run('experiment_r.py', '--stage', 'all', *base)
        root = d / 'outputs_r/S'
        for k in range(10):
            assert list(root.glob(f'cp0{k}_*')), k
        c1 = json.loads((root / 'cp01_validation_candidates.json').read_text())
        assert c1['split'] == 'development'
        for m, v in c1['methods'].items():
            fins = [json.dumps(v['candidates'][j]['parameters']) for j in v['finalists']]
            assert len(fins) == len(set(fins)), m                              # distinct finalists
        run('experiment_r.py', '--stage', 'test', *base)                       # resume
        run('experiment_r.py', '--stage', 'report', *base[:-1], '500')         # bootstrap not in signature
        run('experiment_r.py', '--stage', 'test', *base[:-3], '21', '--bootstrap', '100', ok=False)
        # README transfer workflow: freeze --frozen-from, then test/report WITHOUT --frozen-from
        fz = str(root / 'cp03_frozen.json')
        tr = ['--dataset', 'umi.npz', '--run-id', 'T', '--limit', '30', '--n-mc', '20', '--bootstrap', '100']
        run('experiment_r.py', '--stage', 'freeze', *tr, '--frozen-from', fz)
        run('experiment_r.py', '--stage', 'test', *tr)
        run('experiment_r.py', '--stage', 'report', *tr)
        sc = json.loads((d / 'outputs_r/T/cp09_scope.json').read_text())
        assert sc['transferred'] and sc['test_geometries'] == 30 and sc['noise_w'] < 1e-11
        r = run('experiment_r.py', '--stage', 'freeze', *tr[:3], 'T2', *tr[4:], '--sinr-db', '3',
                '--frozen-from', fz, ok=False)
        assert 'Transfer settings differ' in r.stderr


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for t in tests:
        t()
        print('PASS', t.__name__)
    print(f'PASS all {len(tests)} tests')
