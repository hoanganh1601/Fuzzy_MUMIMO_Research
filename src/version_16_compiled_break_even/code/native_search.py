#!/usr/bin/env python3
"""ctypes wrapper of native/screen_core.c (compiled CARD and EARLY search).

  python code/native_search.py --build      # compile the shared library (gcc/cc/clang; MSVC 'cl' on Windows)
  python code/native_search.py --selftest   # compiled vs Python decisions on random channels

The compiled search mirrors robust_model.solve and run_experiment.search (V15.2) except
for the LP audit, which verifies p* but does not change the decision.
"""
import argparse, ctypes, os, platform, shutil, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / 'native' / 'screen_core.c'
LIBNAME = {'Windows': 'screen_core.dll', 'Darwin': 'libscreen_core.dylib'}.get(platform.system(), 'libscreen_core.so')
LIB = HERE / 'native' / 'build' / LIBNAME
NCOUNT = 4 + 16 + 1


def build(verbose=True):
    LIB.parent.mkdir(parents=True, exist_ok=True)
    tried = []
    if platform.system() == 'Windows':
        cands = [['gcc', '-O3', '-shared', '-o', str(LIB), str(SRC)],
                 ['cl', '/O2', '/LD', str(SRC), '/Fe' + str(LIB), '/link']]
    else:
        cands = [[c, '-O3', '-shared', '-fPIC', '-o', str(LIB), str(SRC), '-lm'] for c in ('gcc', 'cc', 'clang')]
    for cmd in cands:
        if not shutil.which(cmd[0]): tried.append(cmd[0] + ' (not found)'); continue
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(LIB.parent))
        if r.returncode == 0 and LIB.exists():
            if verbose: print('BUILT', LIB, 'with', cmd[0])
            return LIB
        tried.append(cmd[0] + ': ' + (r.stderr or r.stdout)[-400:])
    raise RuntimeError('Could not compile screen_core.c. Install a C compiler (Linux: gcc; Windows: MinGW-w64 gcc '
                       'or Visual Studio Build Tools "cl"). Attempts:\n' + '\n'.join(tried))


_lib = None
def lib():
    global _lib
    if _lib is None:
        if not LIB.exists() or LIB.stat().st_mtime < SRC.stat().st_mtime: build(verbose=False)
        L = ctypes.CDLL(str(LIB))
        dp = ctypes.POINTER(ctypes.c_double); ip = ctypes.POINTER(ctypes.c_int); lp = ctypes.POINTER(ctypes.c_long)
        L.search.argtypes = [dp, dp, ctypes.c_int, ctypes.c_int, dp, ctypes.c_int] + [ctypes.c_double] * 6 + [ctypes.c_int, ip, ip, dp, ip, lp]
        L.search.restype = ctypes.c_int
        L.early_ratio.argtypes = [dp, dp, ctypes.c_int, ctypes.c_int] + [ctypes.c_double] * 5
        L.early_ratio.restype = ctypes.c_double
        L.search_routed.argtypes = [dp, dp, ctypes.c_int, ctypes.c_int, dp, ctypes.c_int] + [ctypes.c_double] * 6 + [dp, ctypes.c_int, ctypes.c_int, ip, ip, dp, ip, lp, ip]
        L.search_routed.restype = ctypes.c_int
        L.repeat_search.argtypes = [ctypes.c_int, ctypes.c_int] + L.search_routed.argtypes
        L.repeat_search.restype = ctypes.c_int
        _lib = L
    return _lib


class Prepared:
    """Channel and parameters converted once to C buffers (conversion is outside the timed region)."""
    def __init__(self, h, alphas, cfg, guard):
        h = np.asarray(h); self.M, self.K = h.shape
        self.re = np.ascontiguousarray(h.real.T, dtype=np.float64); self.im = np.ascontiguousarray(h.imag.T, dtype=np.float64)
        self.al = np.ascontiguousarray(alphas, dtype=np.float64); self.L = len(alphas); self.alphas = tuple(float(x) for x in alphas)
        self.cfg = cfg; self.guard = guard
        d = ctypes.POINTER(ctypes.c_double)
        self.p_re = self.re.ctypes.data_as(d); self.p_im = self.im.ctypes.data_as(d); self.p_al = self.al.ctypes.data_as(d)
        self.sub = (ctypes.c_int * 16)(); self.ai = ctypes.c_int(); self.pw = ctypes.c_double(); self.card = ctypes.c_int()
        self.cnt = (ctypes.c_long * NCOUNT)()
        self.args_cfg = (cfg['q'], cfg['sigma'], cfg['gamma'], cfg['noise'], cfg['pmax'])

    def run(self, policy):
        """policy: 0 CARD, 1 EARLY. Returns status code; results in self.* buffers."""
        return lib().search(self.p_re, self.p_im, self.M, self.K, self.p_al, self.L, *self.args_cfg, self.guard, policy,
                            self.sub, ctypes.byref(self.ai), ctypes.byref(self.pw), ctypes.byref(self.card), self.cnt)

    def set_routing(self, bins, active_cells):
        """bins: early_ratio edges; active_cells: set of cell indices j (ER{j}) routed to EARLY."""
        self.bins = np.ascontiguousarray(bins, dtype=np.float64); self.nb = len(bins)
        self.p_bins = self.bins.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        self.mask = sum(1 << j for j in active_cells); self.pol = ctypes.c_int()

    def run_routed(self):
        return lib().search_routed(self.p_re, self.p_im, self.M, self.K, self.p_al, self.L, *self.args_cfg, self.guard,
                                   self.p_bins, self.nb, self.mask, self.sub, ctypes.byref(self.ai), ctypes.byref(self.pw),
                                   ctypes.byref(self.card), self.cnt, ctypes.byref(self.pol))

    def repeat(self, n, mode):
        """Run mode (0 CARD, 1 EARLY, 2 ROUTED) n times inside C; requires set_routing for mode 2."""
        if not hasattr(self, 'p_bins'): self.set_routing([1.0], set())
        return lib().repeat_search(n, mode, self.p_re, self.p_im, self.M, self.K, self.p_al, self.L, *self.args_cfg, self.guard,
                                   self.p_bins, self.nb, self.mask, self.sub, ctypes.byref(self.ai), ctypes.byref(self.pw),
                                   ctypes.byref(self.card), self.cnt, ctypes.byref(self.pol))

    def er(self):
        return lib().early_ratio(self.p_re, self.p_im, self.M, self.K, *self.args_cfg)

    def result(self):
        c = self.card.value
        choice = None if c == 0 else {'subset': ''.join(str(self.sub[i]) for i in range(c)), 'alpha': self.alphas[self.ai.value],
                                      'cardinality': c, 'p_req_w': float(self.pw.value)}
        cnt = list(self.cnt)
        return choice, {'full_calls': cnt[0], 'early_rejects': cnt[1], 'candidates_seen': cnt[2], 'subsets_visited': cnt[3],
                        'rejected_subsets_by_size': {s: cnt[4 + s] for s in range(1, self.K + 1)}}


def native_search(h, alphas, cfg, policy, guard=1e-5):
    P = Prepared(h, alphas, cfg, guard); st = P.run({'CARD': 0, 'EARLY': 1}[policy])
    if st != 0: raise RuntimeError(f'native search failed with code {st}')
    return P.result()


def selftest(n=12, seed=3):
    sys.path.insert(0, str(HERE))
    from run_experiment import search, same_choice
    from make_synthetic import drop
    cfg = {'q': 2.960414, 'sigma': .04, 'gamma': 10**.6, 'noise': 2e-13, 'pmax': 1.}
    rng = np.random.default_rng(seed); bad = 0; tot = 0
    for t in range(n):
        h = drop(rng, 16, 8, *((40, 250) if t % 2 else (300, 1200)))
        for k in (4, 6, 8):
            for al in ((0.,), (0., .001, .01), (0., .001, .01, .05, .1, .3, 1.)):
                for pol in ('CARD', 'EARLY'):
                    ref = search(h[:, :k], al, cfg, pol, 1e-5)[0]; got = native_search(h[:, :k], al, cfg, pol)[0]
                    tot += 1
                    if not same_choice(got, ref): bad += 1; print('MISMATCH', t, k, len(al), pol, ref, got)
    print(f'selftest: {tot - bad}/{tot} decisions identical to Python')
    return bad == 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--build', action='store_true'); p.add_argument('--selftest', action='store_true')
    a = p.parse_args()
    if a.build: build()
    if a.selftest: sys.exit(0 if selftest() else 1)
