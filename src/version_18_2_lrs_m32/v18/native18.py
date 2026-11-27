#!/usr/bin/env python3
"""ctypes wrapper of v18/native/screen_v18.c (untimed and stage-timed builds) and its self-test.

  python v18/native18.py --build --selftest

The self-test checks, on synthetic channels: (i) DCS and PBS decisions and counters of screen_v18.c equal those of the
published code/native/screen_core.c; (ii) the exact schedulers CBD, CBPBS and ACS return the DCS decision; (iii) the
cardinality bound s_bar is consistent with the pre-beam bound (PBS rejects every subset of every size above s_bar)
and never lies below the admitted cardinality; (iv) a sample of decisions equals the independent Python oracle.
"""
import argparse, ctypes, itertools, math, platform, shutil, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / 'code'))
SRC = HERE / 'native' / 'screen_v18.c'
EXT = {'Windows': '.dll', 'Darwin': '.dylib'}.get(platform.system(), '.so')
LIBS = {False: HERE / 'native' / 'build' / f'libscreen_v18{EXT}', True: HERE / 'native' / 'build' / f'libscreen_v18_timed{EXT}'}
NCNT = 29
NSTAGE = 8
STAGES = ('load', 'bound', 'beam', 'coefficients', 'coupling', 'power', 'select')
POLICY = {'DCS': 0, 'PBS': 1, 'CBD': 3, 'CBPBS': 4, 'ACS': 5, 'ACSSTOP': 6, 'GREEDY': 7, 'LRS': -1, 'LRSPUB': -1}
EXACT = ('DCS', 'PBS', 'CBD', 'CBPBS', 'ACS', 'LRS')
HEURISTIC = ('ACSSTOP', 'GREEDY')


def compiler_cmds(out, timed):
    d = ['-DSTAGE_TIMING'] if timed else []
    if platform.system() == 'Windows':
        return [['gcc', '-O3', '-shared'] + d + ['-o', str(out), str(SRC)],
                ['cl', '/O2', '/LD'] + (['/DSTAGE_TIMING'] if timed else []) + [str(SRC), '/Fe' + str(out), '/link']]
    return [[c, '-O3', '-shared', '-fPIC'] + d + ['-o', str(out), str(SRC), '-lm'] for c in ('gcc', 'cc', 'clang')]


def build(verbose=True):
    for timed, out in LIBS.items():
        out.parent.mkdir(parents=True, exist_ok=True); tried = []
        for cmd in compiler_cmds(out, timed):
            if not shutil.which(cmd[0]): tried.append(cmd[0] + ' (not found)'); continue
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(out.parent))
            if r.returncode == 0 and out.exists():
                if verbose: print('BUILT', out.name, 'with', cmd[0])
                break
            tried.append(cmd[0] + ': ' + (r.stderr or r.stdout)[-400:])
        else:
            raise RuntimeError('Could not compile screen_v18.c:\n' + '\n'.join(tried))


def compiler_id():
    for c in ('gcc', 'cc', 'clang', 'cl'):
        try:
            r = subprocess.run([c, '--version'], capture_output=True, text=True, timeout=10)
            if r.returncode == 0: return c + ': ' + (r.stdout or r.stderr).splitlines()[0]
        except Exception: pass
    return 'unknown'


_lib = {}
def lib(timed=False):
    if timed not in _lib:
        p = LIBS[timed]
        if not p.exists() or p.stat().st_mtime < SRC.stat().st_mtime: build(verbose=False)
        L = ctypes.CDLL(str(p))
        dp = ctypes.POINTER(ctypes.c_double); ip = ctypes.POINTER(ctypes.c_int); lp = ctypes.POINTER(ctypes.c_long)
        L.search18.argtypes = [dp, dp, ctypes.c_int, ctypes.c_int, dp, ctypes.c_int] + [ctypes.c_double] * 6 + [ctypes.c_int, ip, ip, dp, ip, lp]
        L.search18.restype = ctypes.c_int
        L.repeat18.argtypes = [ctypes.c_int, ctypes.c_int, dp, dp, ctypes.c_int, ctypes.c_int, dp, ctypes.c_int] + [ctypes.c_double] * 6 + \
                              [dp, ctypes.c_int, ctypes.c_int, ip, ip, dp, ip, lp, ip]
        L.repeat18.restype = ctypes.c_int
        L.early_ratio.argtypes = [dp, dp, ctypes.c_int, ctypes.c_int] + [ctypes.c_double] * 5
        L.early_ratio.restype = ctypes.c_double
        L.cardinality_bound.argtypes = [dp, dp, ctypes.c_int, ctypes.c_int] + [ctypes.c_double] * 6
        L.cardinality_bound.restype = ctypes.c_int
        L.stage_timing_enabled.restype = ctypes.c_int
        L.bench_candidate.argtypes = [ctypes.c_int, dp, dp, ctypes.c_int, ip, ctypes.c_int] + [ctypes.c_double] * 6 + [dp]
        L.bench_candidate.restype = ctypes.c_int
        L.bench_bound.argtypes = [ctypes.c_int, dp, dp, ctypes.c_int, ctypes.c_int, ip, ctypes.c_int] + [ctypes.c_double] * 6
        L.bench_bound.restype = ctypes.c_int
        L.bench_load.argtypes = [ctypes.c_int, dp, dp, ctypes.c_int, ctypes.c_int] + [ctypes.c_double] * 5
        L.bench_load.restype = ctypes.c_double
        L.stage_read.argtypes = [dp, lp]
        L.timer_pair_cost_ms.argtypes = [ctypes.c_int]; L.timer_pair_cost_ms.restype = ctypes.c_double
        _lib[timed] = L
    return _lib[timed]


class P18:
    """One channel realization (M x K), beam rules and physical parameters, converted once to C buffers."""
    def __init__(self, h, alphas, cfg, guard=1e-5, bins=(0.1, 1.0), active_cells=(), timed=False):
        h = np.asarray(h, dtype=np.complex128); self.M, self.K = h.shape
        self.re = np.ascontiguousarray(h.real.T); self.im = np.ascontiguousarray(h.imag.T)
        self.al = np.ascontiguousarray(alphas, dtype=np.float64); self.L = len(alphas); self.alphas = tuple(float(x) for x in alphas)
        self.cfg = (cfg['q'], cfg['sigma'], cfg['gamma'], cfg['noise'], cfg['pmax']); self.guard = guard
        self.bins = np.ascontiguousarray(bins, dtype=np.float64); self.mask = sum(1 << j for j in active_cells)
        d = ctypes.POINTER(ctypes.c_double)
        self.p = (self.re.ctypes.data_as(d), self.im.ctypes.data_as(d)); self.pa = self.al.ctypes.data_as(d); self.pb = self.bins.ctypes.data_as(d)
        self.sub = (ctypes.c_int * 16)(); self.ai = ctypes.c_int(); self.pw = ctypes.c_double(); self.card = ctypes.c_int()
        self.cnt = (ctypes.c_long * NCNT)(); self.pol = ctypes.c_int(); self.timed = timed; self.L_ = lib(timed)

    def repeat(self, n, policy):
        code = POLICY[policy] if isinstance(policy, str) else policy
        st = self.L_.repeat18(n, code, *self.p, self.M, self.K, self.pa, self.L, *self.cfg, self.guard, self.pb, len(self.bins), self.mask,
                              self.sub, ctypes.byref(self.ai), ctypes.byref(self.pw), ctypes.byref(self.card), self.cnt, ctypes.byref(self.pol))
        if st != 0: raise RuntimeError(f'screen_v18 failure {st} ({policy})')

    def eta(self): return self.L_.early_ratio(*self.p, self.M, self.K, *self.cfg)
    def sbar(self): return self.L_.cardinality_bound(*self.p, self.M, self.K, *self.cfg, self.guard)

    def result(self):
        c = self.card.value; n = list(self.cnt)
        choice = None if c == 0 else {'subset': ''.join(str(self.sub[i]) for i in range(c)), 'alpha': self.alphas[self.ai.value],
                                      'cardinality': c, 'p_req_w': float(self.pw.value)}
        return choice, {'full_calls': n[0], 'prebeam_rejected': n[1], 'candidates_seen': n[2], 'subsets_visited': n[3],
                        'rejected_by_size': [n[4 + s] for s in range(1, self.K + 1)], 'sbar': n[21], 'levels': n[22],
                        'cls_feasible': n[23], 'cls_beam': n[24], 'cls_zero': n[25], 'cls_coupling': n[26], 'cls_invalid': n[27],
                        'cls_power': n[28], 'routed_policy': self.pol.value}

    def bench_candidate(self, n, subset, l):
        idx = (ctypes.c_int * len(subset))(*subset); pw = ctypes.c_double()
        return self.L_.bench_candidate(n, *self.p, self.M, idx, len(subset), self.al[l], *self.cfg, ctypes.byref(pw))

    def bench_bound(self, n, subset):
        idx = (ctypes.c_int * len(subset))(*subset)
        return self.L_.bench_bound(n, *self.p, self.M, self.K, idx, len(subset), *self.cfg, self.guard)

    def bench_load(self, n): return self.L_.bench_load(n, *self.p, self.M, self.K, *self.cfg)

    def stages(self):
        t = (ctypes.c_double * NSTAGE)(); c = (ctypes.c_long * NSTAGE)(); self.L_.stage_read(t, c)
        return list(t)[:len(STAGES)], list(c)[:len(STAGES)]


def same(x, y, tol=1e-7):
    if x is None or y is None: return x is None and y is None
    return x['cardinality'] == y['cardinality'] and x['subset'] == y['subset'] and x['alpha'] == y['alpha'] and \
        abs(x['p_req_w'] - y['p_req_w']) <= tol * max(1e-18, abs(x['p_req_w']), abs(y['p_req_w']))


def selftest(n=16, seed=5, oracle_every=6):
    import native_search as ns
    from run_experiment import independent_oracle
    from make_synthetic import drop
    rng = np.random.default_rng(seed); bad = []; tot = 0; orc = 0
    for t in range(n):
        h = drop(rng, 16, 8, *((40, 250) if t % 2 else (300, 1200)))
        for M in (8, 16):
            for gdb in (0., 6., 10.):
                cfg = {'q': 2.960414, 'sigma': (.02, .04, .08)[t % 3], 'gamma': 10 ** (gdb / 10), 'noise': 2e-13, 'pmax': 1.}
                for k in (4, 6, 8):
                    for al in ((0., .001, .01), (0., .001, .01, .05, .1, .3, 1.)):
                        hh = h[:M, :k]; P = P18(hh, al, cfg); R = {}
                        for pol in ('DCS', 'PBS', 'CBD', 'CBPBS', 'ACS', 'ACSSTOP', 'GREEDY'):
                            P.repeat(1, pol); R[pol] = P.result()
                        tot += 1
                        for pol, ref in (('DCS', 'CARD'), ('PBS', 'EARLY')):
                            got = ns.native_search(hh, al, cfg, ref)
                            if not same(R[pol][0], got[0]) or R[pol][1]['full_calls'] != got[1]['full_calls']:
                                bad.append(('vs screen_core', t, M, gdb, k, len(al), pol))
                        for pol in ('PBS', 'CBD', 'CBPBS', 'ACS'):
                            if not same(R[pol][0], R['DCS'][0]): bad.append(('exact', t, M, gdb, k, len(al), pol))
                        sb = P.sbar(); card = R['DCS'][0]['cardinality'] if R['DCS'][0] else 0
                        if card > sb: bad.append(('sbar below optimum', t, M, gdb, k, sb, card))
                        rej = R['PBS'][1]['rejected_by_size']
                        for s in range(sb + 1, k + 1):
                            if rej[s - 1] != math.comb(k, s): bad.append(('sbar vs PBS', t, M, gdb, k, s, rej[s - 1]))
                        if tot % oracle_every == 0:
                            ref, _ = independent_oracle(hh, al, cfg); orc += 1
                            if not same(R['DCS'][0], ref): bad.append(('oracle', t, M, gdb, k, len(al)))
    for b in bad[:20]: print('FAIL', b)
    print(f'selftest V18: {tot} configurations x 7 schedulers, {orc} oracle checks, {len(bad)} failures')
    return not bad


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--build', action='store_true'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.build: build()
    if a.selftest: sys.exit(0 if selftest() else 1)
