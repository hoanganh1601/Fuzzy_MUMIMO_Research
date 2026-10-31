"""Invariant and correctness tests. Run: python tests/test_invariants.py  (or pytest)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

CODE = Path(__file__).resolve().parents[1] / 'code'
sys.path.insert(0, str(CODE))
from experiment import (coupling, power_alloc, power_lp, rzf, grouped_split, fuzzy_q, gaussian_q,  # noqa: E402
                        joint_failures, radii, select_method, candidate_grid, wilson, group_bootstrap)


def channel(seed, M=8, K=4):
    rng = np.random.default_rng(seed)
    return (rng.normal(size=(M, K)) + 1j * rng.normal(size=(M, K))) / np.sqrt(2)


CFG = dict(sigma_rel=.04, sinr=10 ** .6, noise=1e-9, pmax=1.)


def test_rzf_unit_norm():
    V = rzf(channel(1))
    assert np.allclose(np.linalg.norm(V, axis=0), 1)
    assert rzf(np.zeros((8, 4), complex)) is None


def test_power_is_lp_optimum():
    """(I-F)^-1 u equals the minimum of 1^T p s.t. (I-F) p >= u, p >= 0 (solved by linprog)."""
    for s in range(20):
        H = channel(100 + s)
        V = rzf(H)
        p, rho, why = power_alloc(H, V, 1.0, CFG)
        F, u = coupling(H, V, 1.0, CFG['sigma_rel'], CFG['sinr'], CFG['noise'])
        c = u.max()                                   # normalise: HiGHS tolerances are absolute
        lp = linprog(np.ones(4), A_ub=-(np.eye(4) - F), b_ub=-u / c, bounds=[(0, None)] * 4, method='highs')
        if p is None:
            assert rho >= 1 - 1e-10 or why != 'ok'
            continue
        assert lp.status == 0 and np.allclose(p / c, lp.x, rtol=1e-6, atol=1e-9)
        assert np.all(p >= F @ p + u - 1e-12 * np.max(p))


def test_robust_bound_holds_on_slab_set():
    """Every error inside U(q) satisfies the SINR target with the robust power."""
    rng = np.random.default_rng(5)
    for s in range(10):
        Hh = channel(200 + s)
        V = rzf(Hh)
        q = gaussian_q(.05, 4)
        p, _, why = power_alloc(Hh, V, q, CFG)
        assert why == 'ok'
        r = radii(Hh, q, CFG['sigma_rel'])
        sk = CFG['sigma_rel'] * np.linalg.norm(Hh, axis=0) / np.sqrt(8)
        # scale up the errors (x1.5) and keep only those inside U(q): stresses the boundary of the set
        E = 1.5 * sk[None, None, :] * (rng.normal(size=(20000, 8, 4)) + 1j * rng.normal(size=(20000, 8, 4))) / np.sqrt(2)
        proj = np.abs(np.einsum('nmk,mj->nkj', E.conj(), V))            # |e_k^H v_j|
        inside = np.all(proj <= r[None, :, None], axis=(1, 2))
        assert inside.sum() > 50
        assert joint_failures(Hh[None] + E[inside], V, p, CFG) == 0


def test_gaussian_radius_coverage():
    """P(e not in U(q_gauss)) <= eps under the simulated CSI law (union bound is tight here)."""
    K, M, eps = 4, 8, .05
    q = gaussian_q(eps, K)
    assert abs(K * K * np.exp(-q * q) - eps) < 1e-12
    rng = np.random.default_rng(9)
    E = (rng.normal(size=(200000, M, K)) + 1j * rng.normal(size=(200000, M, K))) / np.sqrt(2)   # s_k = 1
    V = rzf(channel(3))
    miss = np.mean(np.any(np.abs(np.einsum('nmk,mj->nkj', E.conj(), V)) > q, axis=(1, 2)))
    assert miss <= eps + 3 * np.sqrt(eps / 200000) and miss > .8 * eps


def test_scale_invariance():
    """H -> cH, noise -> c^2 noise leaves feasibility and powers unchanged (no absolute thresholds)."""
    H = channel(11)
    for c in (1e-6, 1., 1e4):
        cfg = dict(CFG, noise=CFG['noise'] * c * c)
        V = rzf(c * H)
        p, _, _ = power_alloc(c * H, V, 1.2, cfg)
        if c == 1e-6:
            p0 = p
        assert p is not None and np.allclose(p, p0, rtol=1e-8)


def test_split_and_fuzzy():
    masks = grouped_split(np.repeat(np.arange(12), 10), 22)
    assert all(not np.any(masks[i] & masks[j]) for i in range(3) for j in range(i + 1, 3))
    assert np.all(masks[0] | masks[1] | masks[2])
    for z in np.random.default_rng(1).random((200, 2)):
        assert abs(fuzzy_q(z, [.5] * 9) - .5) < 1e-12
        q = fuzzy_q(z, list(np.linspace(.4, 1.6, 9)))
        assert .4 - 1e-12 <= q <= 1.6 + 1e-12
    assert len(candidate_grid(2.4)['sugeno']) == len(candidate_grid(2.4)['fixed']) == 6


def test_selection_uses_common_set():
    """A candidate must not win by dropping the hard (high-power) channel."""
    mk = lambda i, f, pw, o=0.: dict(index=i, feasible=f, power_w=pw if f else '', outage=o if f else '')
    a = [mk(0, 1, 1.), mk(1, 1, 1.), mk(2, 1, 9.)]                 # feasible everywhere
    b = [mk(0, 1, 2.), mk(1, 1, 2.), mk(2, 0, 0)]                  # drops channel 2, eff = 1/3
    best, _, _ = select_method('x', [{}, {}], [a, b], .5, 10.)
    assert best['candidate'] == 0                                   # 1.0 < 2.0 on common set {0,1}


def test_stats():
    lo, hi = wilson(0, 100)
    assert lo == 0 and .03 < hi < .04
    lo, hi = group_bootstrap(np.r_[np.zeros(50), np.ones(50)], np.repeat(np.arange(10), 10), 500, 1)
    assert lo < .5 < hi
    assert power_lp(channel(1), rzf(channel(1)), .5, CFG)[0] is not None


def test_end_to_end_resume_and_transfer():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        run = lambda *x: subprocess.run([sys.executable, str(CODE / x[0]), *x[1:]], check=True, cwd=d,
                                        capture_output=True, text=True)
        run('generate_data.py', '--source', 'synthetic', '--n', '120', '--output', 'syn.npz')
        run('generate_data.py', '--source', 'umi_inspired', '--n', '120', '--output', 'umi.npz')
        base = ['--dataset', 'syn.npz', '--run-id', 'R', '--limit', '4', '--n-mc', '50', '--boot', '50']
        run('experiment.py', '--stage', 'all', *base)
        for f in ('cp00_manifest.json', 'cp01_candidates.json', 'cp02_frozen.json', 'cp03_test_geometry.csv',
                  'cp04_test_summary.csv', 'cp05_scope.json', 'cp06_common_set_power.csv'):
            assert (d / 'outputs/R' / f).exists(), f
        run('experiment.py', '--stage', 'test', *base)             # resume: completed tasks reused
        bad = subprocess.run([sys.executable, str(CODE / 'experiment.py'), '--stage', 'test',
                              *base[:-4], '--n-mc', '51', '--boot', '50', '--limit', '4'], cwd=d,
                             capture_output=True, text=True)
        assert bad.returncode != 0 and 'signature mismatch' in bad.stderr
        fz = str(d / 'outputs/R/cp02_frozen.json')
        tr = ['--dataset', 'umi.npz', '--run-id', 'T', '--limit', '3', '--n-mc', '30', '--frozen-from', fz]
        run('experiment.py', '--stage', 'test', *tr)
        out = run('experiment.py', '--stage', 'report', *tr).stdout
        assert 'gaussian' in out
        scope = json.loads((d / 'outputs/T/cp05_scope.json').read_text())
        assert scope['noise_w'] < 1e-11                               # physical thermal noise from dataset
        mism = subprocess.run([sys.executable, str(CODE / 'experiment.py'), '--stage', 'test', *tr[:-2],
                               '--run-id', 'T2', '--frozen-from', fz, '--sinr-db', '3'], cwd=d,
                              capture_output=True, text=True)
        assert mism.returncode != 0 and 'Transfer settings differ' in mism.stderr


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for t in tests:
        t()
        print('PASS', t.__name__)
    print(f'PASS all {len(tests)} tests')
