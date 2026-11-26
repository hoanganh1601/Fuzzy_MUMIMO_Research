"""Statistics of the V18 generality study, with the drop as the sampling unit and the scene (channel set) as the upper level.

Hierarchy: scene (channel set: ASU, Los Angeles, UMi, UMa, ...) > drop (8 users, one channel realization) > (K, L, repeats).
The K = 4 and K = 6 users are the first users of the K = 8 drop, so measurements at different K of one drop are dependent;
every statistic below is first averaged inside a drop (over L and repeats) and never treats (K, L) cells as independent units.

  boot_stratified : drop bootstrap inside each scene (scenes fixed), for the pooled mean          -> scene-conditional CI
  boot_two_level  : scenes resampled, then drops inside the selected scenes                      -> CI that generalizes over scenes
                    (reported with n_scenes; with fewer than 5 scenes its coverage is unreliable and it is flagged)
  perm_paired     : paired sign-flip permutation test on drop-level differences (exact for n <= 20, else Monte Carlo)
  icc / deff      : one-way ANOVA (method of moments) intra-scene correlation, design effect and effective sample size
  n_required      : drops needed for a target CI half-width, inflated by the design effect
"""
import itertools, math
import numpy as np


def _arr(x): return np.asarray(list(x), dtype=float)


def boot_stratified(values, scenes, B=2000, seed=0, stat=np.mean):
    v = _arr(values); s = np.asarray(list(scenes)); rng = np.random.default_rng(seed)
    if len(v) == 0: return {'mean': None, 'lo': None, 'hi': None, 'n': 0}
    idx = {u: np.flatnonzero(s == u) for u in np.unique(s)}
    bs = np.empty(B)
    for b in range(B):
        sample = np.concatenate([rng.choice(i, size=len(i), replace=True) for i in idx.values()])
        bs[b] = stat(v[sample])
    return {'mean': float(stat(v)), 'lo': float(np.quantile(bs, .025)), 'hi': float(np.quantile(bs, .975)), 'n': int(len(v)),
            'n_scenes': len(idx), 'method': 'drop bootstrap stratified by scene'}


def boot_two_level(values, scenes, B=2000, seed=0):
    v = _arr(values); s = np.asarray(list(scenes)); rng = np.random.default_rng(seed)
    if len(v) == 0: return {'mean': None, 'lo': None, 'hi': None, 'n': 0}
    groups = [v[s == u] for u in np.unique(s)]; G = len(groups)
    bs = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, G, size=G)
        bs[b] = np.mean(np.concatenate([rng.choice(groups[g], size=len(groups[g]), replace=True) for g in pick]))
    return {'mean': float(np.mean(v)), 'lo': float(np.quantile(bs, .025)), 'hi': float(np.quantile(bs, .975)), 'n': int(len(v)),
            'n_scenes': G, 'method': 'two-level bootstrap (scenes, then drops)', 'reliable': G >= 5}


def perm_paired(diffs, n_perm=100000, seed=0, alternative='greater'):
    """H0: drop-level paired differences are symmetric around 0. Statistic: mean difference."""
    d = _arr(diffs); n = len(d)
    if n == 0: return {'p': None, 'n': 0}
    obs = d.mean()
    if n <= 20:
        signs = np.array(list(itertools.product((1., -1.), repeat=n))); null = (signs * d).mean(axis=1); exact = True
    else:
        rng = np.random.default_rng(seed); null = (rng.choice((1., -1.), size=(n_perm, n)) * d).mean(axis=1); exact = False
    if alternative == 'greater': k = np.sum(null >= obs - 1e-15)
    elif alternative == 'less': k = np.sum(null <= obs + 1e-15)
    else: k = np.sum(np.abs(null) >= abs(obs) - 1e-15)
    p = k / len(null) if exact else (k + 1) / (len(null) + 1)
    return {'p': float(p), 'n': n, 'mean_diff': float(obs), 'exact': exact, 'alternative': alternative}


def icc(values, scenes):
    v = _arr(values); s = np.asarray(list(scenes)); us = np.unique(s); a = len(us); N = len(v)
    if a < 2 or N <= a: return {'icc': None, 'n_scenes': a, 'n': N}
    ns = np.array([np.sum(s == u) for u in us]); means = np.array([v[s == u].mean() for u in us])
    msb = np.sum(ns * (means - v.mean()) ** 2) / (a - 1)
    msw = sum(np.sum((v[s == u] - m) ** 2) for u, m in zip(us, means)) / (N - a)
    n0 = (N - np.sum(ns ** 2) / N) / (a - 1)
    s2b = max(0.0, (msb - msw) / n0); r = s2b / (s2b + msw) if s2b + msw > 0 else 0.0
    m = N / a; deff = 1 + (m - 1) * r
    return {'icc': float(r), 'n_scenes': int(a), 'n': int(N), 'mean_cluster_size': float(m), 'design_effect': float(deff),
            'n_effective': float(N / deff), 'sd_within': float(math.sqrt(msw)), 'sd_between': float(math.sqrt(s2b))}


def n_required(sd, half_width, deff=1.0, z=1.96):
    if sd is None or half_width <= 0: return None
    return int(math.ceil((z * sd / half_width) ** 2 * deff))


def break_even_threshold(eta, saving, B=1000, seed=0, min_abs=0.02):
    """Empirical load threshold eta* that best separates negative from positive savings (|saving| > min_abs).
    Returns eta*, its bootstrap interval (over realizations) and the accuracy of the rule eta >= 1."""
    e = _arr(eta); y = _arr(saving); keep = np.abs(y) > min_abs; e, y = e[keep], y[keep]
    if len(e) < 5 or len(np.unique(np.sign(y))) < 2:
        return {'eta_star': None, 'n': int(len(e)), 'acc_rule_1': float(np.mean((e >= 1) == (y > 0))) if len(e) else None}
    def fit(ee, yy):
        cand = np.unique(np.concatenate([ee, [1.0]])); best, bt = -1, None
        for t in cand:
            acc = np.mean((ee >= t) == (yy > 0))
            if acc > best + 1e-12 or (abs(acc - best) <= 1e-12 and abs(np.log(t) if t > 0 else 99) < abs(np.log(bt) if bt and bt > 0 else 99)):
                best, bt = acc, t
        return bt, best
    t0, a0 = fit(e, y); rng = np.random.default_rng(seed); ts = []
    for _ in range(B):
        i = rng.integers(0, len(e), size=len(e))
        if len(np.unique(np.sign(y[i]))) < 2: continue
        ts.append(fit(e[i], y[i])[0])
    return {'eta_star': float(t0), 'acc_at_eta_star': float(a0), 'lo': float(np.quantile(ts, .025)) if ts else None,
            'hi': float(np.quantile(ts, .975)) if ts else None, 'acc_rule_1': float(np.mean((e >= 1) == (y > 0))), 'n': int(len(e))}
