#!/usr/bin/env python3
"""V18 generality study of load-routed screening (LRS). Separate from the published code: it only READS code/.

Questions (see HUONG_DAN_V18.md):
  Q1  Does the break-even at eta = 1 hold for other M, SINR requirements gamma and CSI errors epsilon, with a policy map
      re-developed on a separate development set and tested on held-out drops?                         (develop, lock, test)
  Q2  How does LRS compare with the cardinality bound of the Corollary (CBD, CBPBS), ascending-cardinality search (ACS,
      ACSSTOP) and greedy admission (GREEDY), with the same protocol, hardware and candidate family?        (test, analyze)
  Q3  Are the intervals reliable when drops are nested in scenes? Two-level bootstrap, ICC, paired sign-flip permutation
      test on drop-level differences, drops required for a target precision.                                (analyze)
  Q4  Which stage of the compiled search consumes the runtime, and does the analytical cost model / cost bound hold on
      several machines?                                                                                     (stages, hwbundle, hwcompare)

Stages (run in this order; every stage is resumable, rerun the same command after an interruption):
  selftest   build screen_v18.c (untimed and stage-timed), compare with screen_core.c and the Python oracle
  protocol   fix sets, roles, drop split, parameter grid, endpoints, seeds -> G00_protocol.json, G00b_split.csv (before any timing)
  develop    time DCS and PBS on the DEVELOPMENT drops of every configuration -> G01_dev_<cfg>.jsonl
  lock       develop one policy map per configuration -> G02_maps.json (hash recorded; test refuses to run without it)
  test       time DCS, PBS, LRS (own map), LRSPUB (published map), CBD, CBPBS, ACS, ACSSTOP, GREEDY on HELD-OUT drops -> G03_hold_<cfg>.jsonl
  analyze    endpoints G1-G4, comparison table, hierarchical statistics -> G04..G07
  stages     stage-timed runs + per-operation micro-benchmarks on this machine -> G08_stages.csv, G10_op_costs.csv
  hwbundle   machine bundle: per-operation costs, cost model fit (development) and validation (held-out), cost-bound validity
  hwcompare  combine bundles from several machines -> G09_HARDWARE.md
"""
import argparse, hashlib, json, math, os, platform, random, shutil, socket, subprocess, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; REPO = HERE.parent
sys.path.insert(0, str(REPO / 'code')); sys.path.insert(0, str(HERE))
from run_experiment import load_any, independent_oracle   # noqa: E402  (read-only use of the published modules)
import native18 as n18                                     # noqa: E402
import v18_stats as S                                      # noqa: E402

VERSION = 'V18.3'   # V18.1: stop if the published map is missing; V18.2: M = 32 options; V18.3: timing QC, probe, retime
OUT = REPO / 'outputs_v18'
ALPHAS = (0., .001, .01, .05, .1, .3, 1.)
NOISE = 2e-13; QC = 2.960414; GUARD = 1e-5
TEST_POLICIES = ('DCS', 'PBS', 'LRS', 'LRSPUB', 'CBD', 'CBPBS', 'ACS', 'ACSSTOP', 'GREEDY')
EXACT = ('PBS', 'LRS', 'LRSPUB', 'CBD', 'CBPBS', 'ACS')
PUBLISHED_MAP = REPO / 'results' / 'RESULTS_V15_2' / 'V152_DM' / 'CP03_locked_cells.json'


# ------------------------------------------------------------------ utilities
def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def sha_text(x): return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
def u01(*parts): return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16) / float(1 << 48)
def rj(p): return json.loads(Path(p).read_text(encoding='utf8'))
def wj(p, x): Path(p).write_text(json.dumps(x, indent=2, ensure_ascii=False, default=str), encoding='utf8')


def machine():
    cpu = platform.processor()
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.lower().startswith('model name'): cpu = line.split(':', 1)[1].strip(); break
    except Exception: pass
    if platform.system() == 'Darwin':
        try: cpu = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip() or cpu
        except Exception: pass
    return {'host': socket.gethostname(), 'platform': platform.platform(), 'cpu': cpu, 'cpu_count': os.cpu_count(),
            'python': platform.python_version(), 'numpy': np.__version__, 'compiler': n18.compiler_id(),
            'threads': {v: os.environ.get(v) for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}}


def cfg_id(M, gdb, eps): return f'M{M}_G{gdb:g}_E{eps:g}'
def make_cfg(gdb, eps, pmax_dbm): return {'q': QC, 'sigma': eps, 'gamma': 10 ** (gdb / 10), 'noise': NOISE, 'pmax': 10 ** ((pmax_dbm - 30) / 10)}
def bin_index(eta, bins): return int(sum(eta >= b for b in bins))


def read_jsonl(p):
    if not Path(p).exists(): return []
    out = []
    for line in Path(p).read_text(encoding='utf8').splitlines():
        if line.strip():
            try: out.append(json.loads(line))
            except json.JSONDecodeError: pass        # a line cut by an interruption is measured again
    return out


def timed(P, policy, min_ms, max_inner=1000000):
    n = 1
    while True:
        t = time.perf_counter(); P.repeat(n, policy); dt = (time.perf_counter() - t) * 1000
        if dt >= min_ms or n >= max_inner: return dt / n, n
        n = min(max_inner, max(n * 2, int(n * min_ms / max(dt, 1e-6)) + 1))


def measure(Ps, policies, min_ms, repeats, rng):
    """Interleaved, order-randomized repeats; median ms per run of every policy. Ps: dict policy -> P18."""
    t = {p: [] for p in policies}
    for _ in range(repeats):
        order = list(policies); rng.shuffle(order)
        for p in order: t[p].append(timed(Ps[p], p, min_ms)[0])
    return {p: float(np.median(v)) for p, v in t.items()}


def check_env():
    bad = [v for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS') if os.environ.get(v) != '1']
    if bad: print('WARNING: set', ', '.join(f'{v}=1' for v in bad), 'before timing (single-thread protocol).')


# ------------------------------------------------------------------ protocol
def st_protocol(a):
    OUT.mkdir(exist_ok=True); f = OUT / 'G00_protocol.json'
    sets = []
    for s in a.set:
        lab, rest = s.split('=', 1); path, role = (rest.rsplit(':', 1) + ['split'])[:2] if ':' in rest else (rest, 'split')
        if role not in ('dev', 'hold', 'split'): sys.exit(f'role must be dev, hold or split: {s}')
        H, G, meta = load_any(REPO / path if not Path(path).is_absolute() else path)
        pv = Path(str(REPO / path) + '.provenance.json')
        prov = rj(pv) if pv.exists() else {}
        override = dict(x.split('=', 1) for x in a.prior_use)
        sets.append({'label': lab, 'path': path, 'role': role, 'sha256': sha_file(REPO / path), 'n_drops': int(len(H)), 'M': int(H.shape[1]),
                     'K_max': int(H.shape[2]), 'groups': int(len(set(map(str, G)))), 'prior_use': override.get(lab, prov.get('prior_use', 'unknown')),
                     'scenario': str(meta.get('scenario', prov.get('scenario', '')))})
    grid = [{'M': M, 'gamma_db': g, 'eps': e} for M in a.grid_M for g in a.grid_gamma_db for e in a.grid_eps]
    proto = {'version': VERSION, 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'sets': sets, 'grid': grid,
             'pmax_dbm': a.pmax_dbm, 'noise_w': NOISE, 'q_c': QC, 'guard': GUARD, 'alphas': ALPHAS, 'ks': a.ks, 'Ls': a.Ls,
             'bins': [0.1, 1.0], 'split_fraction_dev': a.split_frac, 'inner_fit_fraction': 0.6, 'seed': a.seed,
             'timing': {'min_ms': a.min_ms, 'repeats': a.repeats, 'statistic': 'median of order-randomized interleaved repeats'},
             'bootstrap': a.bootstrap, 'n_perm': a.n_perm, 'oracle_fraction': a.oracle_fraction, 'max_drops_per_set': a.max_drops_per_set,
             'reference_config': a.reference_config or (cfg_id(16, 6, 0.04) if 16 in a.grid_M else cfg_id(a.grid_M[0], 6 if 6 in a.grid_gamma_db else a.grid_gamma_db[0], 0.04 if 0.04 in a.grid_eps else a.grid_eps[0])),
             'note': a.note,
             'antenna_subarray': 'configuration M uses the first M antennas of each channel set with at least M antennas (contiguous sub-array)',
             'map_rule': 'cell (K,L,load bin) -> PBS iff n_fit>=5, n_valid>=5, mean_fit>0 and CI95_lo(valid, drop bootstrap stratified by scene) of the relative saving > min_rel_gain',
             'min_rel_gain': 0.02, 'max_rel_loss': 0.02, 'min_region_drops': 10,
             'region': 'held-out drop in R iff its (K_max, L_max, load bin) cell is mapped to PBS',
             'endpoints': {
                 'G1': 'every exact scheduler (PBS, LRS, LRSPUB, CBD, CBPBS, ACS) returns the DCS decision on every held-out (drop,K,L); audited DCS decisions equal the Python oracle',
                 'G2': 'if R has >= 10 drops: CI95_lo of the LRS relative saving at K_max in R > 2% and paired permutation p < 0.05 (LRS faster than DCS)',
                 'G3': 'outside R (>= 5 drops): CI95_lo of the LRS relative saving > -2% at every K',
                 'G4': 'at K_max, among held-out realizations with |PBS saving| > 2%, the rule eta >= 1 predicts the sign in >= 95%'},
             'machine': machine()}
    split = []
    for s in sets:
        H, G, _ = load_any(REPO / s['path']); groups = sorted(set(map(str, G)))
        if a.max_drops_per_set: groups = sorted(groups, key=lambda g: u01(a.seed, 'cap', s['label'], g))[:a.max_drops_per_set]
        for g in groups:
            role = s['role'] if s['role'] != 'split' else ('dev' if u01(a.seed, 'split', s['label'], g) < a.split_frac else 'hold')
            split.append({'set': s['label'], 'group': g, 'role': role, 'fit': u01(a.seed, 'inner', s['label'], g) < 0.6})
    proto['split_sha256'] = sha_text(split); proto['n_dev'] = sum(r['role'] == 'dev' for r in split); proto['n_hold'] = sum(r['role'] == 'hold' for r in split)
    if f.exists():
        old = rj(f); keep = ('created_utc', 'machine')
        if {k: v for k, v in old.items() if k not in keep} != {k: v for k, v in json.loads(json.dumps(proto, default=str)).items() if k not in keep}:
            sys.exit('G00_protocol.json exists with different content. Use a new outputs folder (move outputs_v18) for a new protocol.')
        print('Protocol already fixed (unchanged):', f); return
    wj(f, proto)
    with open(OUT / 'G00b_split.csv', 'w', encoding='utf8') as h:
        h.write('set,group,role,inner_fit\n'); [h.write(f"{r['set']},{r['group']},{r['role']},{int(r['fit'])}\n") for r in split]
    print(f"Protocol fixed: {f}  ({len(grid)} configurations, {proto['n_dev']} development / {proto['n_hold']} held-out drops)")
    for s in sets:
        if s['role'] == 'hold' and s['prior_use'] != 'never_seen': print(f"  NOTE: held-out set {s['label']} has prior_use={s['prior_use']} (report it)")


def load_protocol():
    f = OUT / 'G00_protocol.json'
    if not f.exists(): sys.exit('Run the protocol stage first.')
    return rj(f)


def drops(proto, role, M):
    """(set label, group, index, H[:M, :Kmax]) of the requested role, in a fixed order."""
    split = {(r['set'], r['group']): r for r in (dict(zip(['set', 'group', 'role', 'fit'], l.strip().split(','))) for l in
                                                  (OUT / 'G00b_split.csv').read_text(encoding='utf8').splitlines()[1:])}
    out = []
    for s in proto['sets']:
        if s['M'] < M: continue
        H, G, _ = load_any(REPO / s['path'])
        if sha_file(REPO / s['path']) != s['sha256']: sys.exit(f"{s['path']} changed since the protocol was fixed")
        seen = set()
        for i, g in enumerate(map(str, G)):
            r = split.get((s['label'], g))
            if r is None or r['role'] != role or g in seen: continue
            seen.add(g); out.append((s['label'], g, i, np.asarray(H[i, :M, :], dtype=np.complex128), r['fit'] == '1'))
    return out


def configs(proto, only):
    out = [(cfg_id(c['M'], c['gamma_db'], c['eps']), c) for c in proto['grid']]
    if only: out = [x for x in out if x[0] in only.split(',')]
    return out


# ------------------------------------------------------------------ develop / lock
def st_develop(a):
    proto = load_protocol(); check_env(); host = machine()['host']
    for cid, c in configs(proto, a.configs):
        f = OUT / f'G01_dev_{cid}.jsonl'; done = {(r['set'], r['group'], r['K'], r['L']) for r in read_jsonl(f)}
        cfg = make_cfg(c['gamma_db'], c['eps'], proto['pmax_dbm']); D = drops(proto, 'dev', c['M'])
        if not D: print(cid, 'no development drops for this M - not evaluable'); continue
        rng = random.Random(f"{proto['seed']}|dev|{cid}"); t0 = time.time(); new = 0
        with open(f, 'a', encoding='utf8') as h:
            for n, (lab, g, i, H, fit) in enumerate(D):
                for K in proto['ks']:
                    for L in proto['Ls']:
                        if (lab, g, K, L) in done: continue
                        al = ALPHAS[:L]; P = {p: n18.P18(H[:, :K], al, cfg) for p in ('DCS', 'PBS')}
                        res = {}
                        for p in ('DCS', 'PBS'): P[p].repeat(1, p); res[p] = P[p].result()
                        ms = measure(P, ('DCS', 'PBS'), proto['timing']['min_ms'], proto['timing']['repeats'], rng)
                        row = {'set': lab, 'group': g, 'K': K, 'L': L, 'fit': fit, 'eta': P['DCS'].eta(), 'sbar': P['DCS'].sbar(),
                               't_DCS': ms['DCS'], 't_PBS': ms['PBS'], 'card': res['DCS'][0]['cardinality'] if res['DCS'][0] else 0,
                               'same': n18.same(res['PBS'][0], res['DCS'][0]), 'pbs': res['PBS'][1], 'dcs_calls': res['DCS'][1]['full_calls'], 'host': host}
                        h.write(json.dumps(row) + '\n'); h.flush(); new += 1
                if n % 20 == 0: print(f'  {cid} development {n + 1}/{len(D)} drops ({time.time() - t0:.0f} s)', flush=True)
        print(f'{cid}: development complete ({new} new measurements)')


def develop_map(rows, proto, B, seed):
    bins = proto['bins']; nb = len(bins) + 1; maps = {}; cells = []
    for K in proto['ks']:
        for L in proto['Ls']:
            active = []
            for j in range(nb):
                R = [r for r in rows if r['K'] == K and r['L'] == L and bin_index(r['eta'], bins) == j and r['t_DCS'] > 0]
                fit = [(r['t_DCS'] - r['t_PBS']) / r['t_DCS'] for r in R if r['fit']]
                val = [r for r in R if not r['fit']]
                ci = S.boot_stratified([(r['t_DCS'] - r['t_PBS']) / r['t_DCS'] for r in val], [r['set'] for r in val], B, seed + 31 * K + L + j) if val else {'lo': None}
                ok = len(fit) >= 5 and len(val) >= 5 and np.mean(fit) > 0 and ci['lo'] is not None and ci['lo'] > proto['min_rel_gain']
                if ok: active.append(j)
                cells.append({'K': K, 'L': L, 'bin': j, 'n_fit': len(fit), 'n_valid': len(val), 'mean_fit': float(np.mean(fit)) if fit else None,
                              'ci_valid_lo': ci['lo'], 'policy': 'PBS' if ok else 'DCS'})
            maps[f'K{K}_L{L}'] = active
    return maps, cells


def st_lock(a):
    proto = load_protocol(); f = OUT / 'G02_maps.json'
    if f.exists() and not a.force: sys.exit(f'{f} exists: maps are fixed. The test stage uses them.')
    out = {'version': VERSION, 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'protocol_sha256': sha_file(OUT / 'G00_protocol.json'),
           'configs': {}}
    for cid, c in configs(proto, ''):
        rows = read_jsonl(OUT / f'G01_dev_{cid}.jsonl'); D = drops(proto, 'dev', c['M'])
        need = len(D) * len(proto['ks']) * len(proto['Ls'])
        if not D: out['configs'][cid] = {'status': 'NOT_EVALUABLE', 'reason': 'no development drops'}; continue
        if len({(r['set'], r['group'], r['K'], r['L']) for r in rows}) < need: sys.exit(f'{cid}: development incomplete ({len(rows)}/{need}); run develop')
        if not all(r['same'] for r in rows): sys.exit(f'{cid}: a PBS decision differs from DCS on development data - stop and report')
        maps, cells = develop_map(rows, proto, proto['bootstrap'], proto['seed'])
        rule = all(v == [len(proto['bins'])] or v == [] for v in maps.values())
        out['configs'][cid] = {'status': 'LOCKED', 'maps': maps, 'cells': cells, 'only_top_bin_active': rule, 'n_dev_rows': len(rows),
                               'dev_hosts': sorted({r['host'] for r in rows})}
    wj(f, out); print('Policy maps fixed:', f, sha_file(f))
    for cid, v in out['configs'].items(): print(' ', cid, v.get('status'), v.get('maps'))


# ------------------------------------------------------------------ test
def published_masks():
    if not PUBLISHED_MAP.exists(): sys.exit(f'Published policy map not found: {PUBLISHED_MAP}. Run V18 inside the lrs-mumimo repository (results/ is required).')
    lk = rj(PUBLISHED_MAP); cells = lk.get('policy_cells', {})
    m = {}
    for k, v in cells.items():
        pol = v if isinstance(v, str) else v.get('policy', 'CARD')
        if not k.startswith('K'): continue
        K, L, cell = k.split('_'); j = int(cell.replace('ER', ''))
        if pol != 'CARD': m.setdefault(f'{K}_{L}', []).append(j)
    return m


def st_test(a):
    proto = load_protocol(); check_env(); f2 = OUT / 'G02_maps.json'
    if not f2.exists(): sys.exit('No G02_maps.json: run lock first (the maps must be fixed before held-out drops are timed).')
    maps = rj(f2); host = machine()['host']; pub = published_masks()
    for cid, c in configs(proto, a.configs):
        mc = maps['configs'].get(cid, {})
        if mc.get('status') != 'LOCKED': print(cid, 'not locked - skipped'); continue
        f = OUT / f'G03_hold_{cid}.jsonl'; done = {(r['set'], r['group'], r['K'], r['L']) for r in read_jsonl(f)}
        cfg = make_cfg(c['gamma_db'], c['eps'], proto['pmax_dbm']); D = drops(proto, 'hold', c['M'])
        rng = random.Random(f"{proto['seed']}|hold|{cid}"); t0 = time.time(); recent = []
        with open(f, 'a', encoding='utf8') as h:
            for n, (lab, g, i, H, _) in enumerate(D):
                for K in proto['ks']:
                    for L in proto['Ls']:
                        if (lab, g, K, L) in done: continue
                        al = ALPHAS[:L]; own = mc['maps'][f'K{K}_L{L}']; pm = pub.get(f'K{K}_L{L}', [])
                        P = {p: n18.P18(H[:, :K], al, cfg, bins=proto['bins'], active_cells=own if p == 'LRS' else (pm if p == 'LRSPUB' else ()))
                             for p in TEST_POLICIES}
                        res = {}
                        for p in TEST_POLICIES:
                            P[p].repeat(1, 'LRS' if p == 'LRSPUB' else p); res[p] = P[p].result()
                        ms = measure({p: P[p] for p in TEST_POLICIES}, TEST_POLICIES, proto['timing']['min_ms'], proto['timing']['repeats'], rng) \
                            if not a.decisions_only else {p: None for p in TEST_POLICIES}
                        # LRSPUB is timed with the routed code (-1): P['LRSPUB'].repeat uses its own mask
                        ref = res['DCS'][0]
                        row = {'set': lab, 'group': g, 'K': K, 'L': L, 'eta': P['DCS'].eta(), 'sbar': P['DCS'].sbar(),
                               'card': ref['cardinality'] if ref else 0, 'p_ref': ref['p_req_w'] if ref else None, 'host': host,
                               'in_R_cell': bin_index(P['DCS'].eta(), proto['bins']) in own, 'routed_LRS': res['LRS'][1]['routed_policy'],
                               't': ms, 'same': {p: n18.same(res[p][0], ref) for p in TEST_POLICIES if p != 'DCS'},
                               'card_by': {p: (res[p][0]['cardinality'] if res[p][0] else 0) for p in TEST_POLICIES},
                               'p_by': {p: (res[p][0]['p_req_w'] if res[p][0] else None) for p in TEST_POLICIES},
                               'calls': {p: res[p][1]['full_calls'] for p in TEST_POLICIES},
                               'visited': {p: res[p][1]['subsets_visited'] for p in TEST_POLICIES}, 'pbs': res['PBS'][1]}
                        if u01(proto['seed'], 'oracle', cid, lab, g, K, L) < proto['oracle_fraction']:
                            o, _ = independent_oracle(H[:, :K], al, cfg); row['oracle_same'] = n18.same(ref, o)
                        bad = [p for p in EXACT if not row['same'][p]]
                        if bad: print(f'  WARNING exactness: {cid} {lab} {g} K={K} L={L}: {bad} differ from DCS (recorded; endpoint G1 fails)')
                        h.write(json.dumps(row) + '\n'); h.flush()
                        x = identical_pairs(row)
                        if x is not None:
                            recent = (recent + [abs(math.log(x)) > math.log(QC_RATIO)])[-100:]
                            if len(recent) == 100 and sum(recent) > 5:
                                print(f'  TIMING UNSTABLE: {sum(recent)} of the last 100 identical-path pairs differ by more than {QC_RATIO}x. '
                                      'Stop other jobs on this machine; the QC endpoint will report it.', flush=True); recent = []
                if n % 10 == 0: print(f'  {cid} held-out {n + 1}/{len(D)} drops ({time.time() - t0:.0f} s)', flush=True)
        print(f'{cid}: held-out measurements complete')


# ------------------------------------------------------------------ analyze
def drop_level(rows, fn, K=None, cond=None):
    """Average fn(row) over L (and anything else) inside each (set, group) drop -> lists (values, scenes, keys)."""
    acc = {}
    for r in rows:
        if K is not None and r['K'] != K: continue
        if cond is not None and not cond(r): continue
        v = fn(r)
        if v is None: continue
        acc.setdefault((r['set'], r['group']), []).append(v)
    keys = sorted(acc)
    return [float(np.mean(acc[k])) for k in keys], [k[0] for k in keys], keys


QC_RATIO = 1.5          # two timings of the SAME search path that differ by more than this factor are discordant
QC_MAX_RATE = 0.01      # timing QC passes if at most 1% of the identical-path pairs are discordant
PROBE_MIN_PAIRS = 200   # probe: enough identical pairs to resolve the 1% threshold


def identical_pairs(r):
    """LRS executes exactly the search of DCS (routed to DCS) or of PBS (routed to PBS), plus the load computation;
    the two timings of such a pair can differ only by the routing overhead or by measurement noise."""
    t = r.get('t') or {}
    if not t.get('LRS'): return None
    ref = t.get('DCS') if r['routed_LRS'] == 0 else t.get('PBS')
    return None if not ref else t['LRS'] / ref


def timing_qc(rows):
    q = [x for x in (identical_pairs(r) for r in rows) if x is not None]
    if not q: return {'pairs': 0, 'discordant': 0, 'rate': None, 'pass': None}
    d = int(sum(abs(math.log(x)) > math.log(QC_RATIO) for x in q))
    return {'pairs': len(q), 'discordant': d, 'rate': d / len(q), 'pass': d / len(q) <= QC_MAX_RATE,
            'median_abs_log_ratio': float(np.median([abs(math.log(x)) for x in q]))}


def rel(p): return lambda r: (r['t']['DCS'] - r['t'][p]) / r['t']['DCS'] if r['t'].get(p) and r['t'].get('DCS') else None


def st_analyze(a):
    proto = load_protocol(); maps = rj(OUT / 'G02_maps.json'); B = proto['bootstrap']; NP = proto['n_perm']; seed = proto['seed']
    Kmax = max(proto['ks']); Lmax = max(proto['Ls']); E, C, ST = [], [], {}
    for cid, c in configs(proto, a.configs):
        rows = read_jsonl(OUT / f'G03_hold_{cid}.jsonl')
        if not rows: continue
        mc = maps['configs'][cid]['maps']; topR = lambda r: bin_index(r['eta'], proto['bins']) in mc[f'K{Kmax}_L{Lmax}']
        # region membership per drop from its K_max realization
        inR = {(r['set'], r['group']) for r in rows if r['K'] == Kmax and r['L'] == Lmax and topR(r)}
        R = lambda r: (r['set'], r['group']) in inR
        timed_ok = all(r['t'].get('DCS') for r in rows)
        g1 = all(all(r['same'][p] for p in EXACT) for r in rows) and all(r.get('oracle_same', True) for r in rows)
        res = {'config': cid, **c, 'n_hold_drops': len({(r['set'], r['group']) for r in rows}), 'n_R': len(inR), 'G1_exact': g1,
               'oracle_audits': sum('oracle_same' in r for r in rows)}
        if timed_ok:
            v, sc, _ = drop_level(rows, rel('LRS'), Kmax, R)
            if len(v) >= proto['min_region_drops']:
                ci = S.boot_stratified(v, sc, B, seed); pm = S.perm_paired(v, NP, seed)
                res.update(G2_mean=ci['mean'], G2_lo=ci['lo'], G2_hi=ci['hi'], G2_p=pm['p'], G2=bool(ci['lo'] > proto['min_rel_gain'] and pm['p'] < 0.05))
            else: res.update(G2=None, G2_note=f'{len(v)} drops in R (< {proto["min_region_drops"]})')
            worst = None; g3 = True; nout = 0
            for K in proto['ks']:
                v, sc, _ = drop_level(rows, rel('LRS'), K, lambda r: not R(r)); nout = len(v)
                if len(v) >= 5:
                    ci = S.boot_stratified(v, sc, B, seed + K); worst = ci['lo'] if worst is None else min(worst, ci['lo'])
                    g3 &= ci['lo'] > -proto['max_rel_loss']
            res.update(G3=(g3 if worst is not None else None), G3_worst_lo=worst, n_out=nout)
            e = [r['eta'] for r in rows if r['K'] == Kmax]; y = [rel('PBS')(r) for r in rows if r['K'] == Kmax]
            be = S.break_even_threshold(e, y, B=min(B, 1000), seed=seed)
            res.update(G4_acc_rule_eta1=be['acc_rule_1'], G4_n=be['n'], eta_star=be['eta_star'], eta_star_lo=be.get('lo'), eta_star_hi=be.get('hi'),
                       G4=(be['acc_rule_1'] >= 0.95 if be['n'] >= 10 else None))
            # hierarchical statistics of the LRS saving at K_max over all held-out drops
            v, sc, _ = drop_level(rows, rel('LRS'), Kmax)
            ic = S.icc(v, sc); tl = S.boot_two_level(v, sc, B, seed); sf = S.boot_stratified(v, sc, B, seed)
            ST[cid] = {'cellwide_LRS_Kmax': {'stratified': sf, 'two_level': tl, 'icc': ic,
                                             'drops_for_halfwidth_2pp': S.n_required(float(np.std(v, ddof=1)) if len(v) > 1 else None, 0.02, ic.get('design_effect') or 1.0),
                                             'note': 'with a large ICC, the precision is limited by the number of scenes; add scenes, not only drops'}}
            # comparison with the other schedulers
            for K in proto['ks']:
                for region, cond in (('all', None), ('R', R), ('outside', lambda r: not R(r))):
                    for p in TEST_POLICIES[1:]:
                        v, sc, keys = drop_level(rows, rel(p), K, cond)
                        if not v: continue
                        ci = S.boot_stratified(v, sc, B, seed + K)
                        sub = [r for r in rows if r['K'] == K and (cond is None or cond(r))]
                        row = {'config': cid, 'K': K, 'region': region, 'policy': p, 'n_drops': len(v), 'rel_saving_mean': ci['mean'],
                               'rel_saving_lo': ci['lo'], 'rel_saving_hi': ci['hi'], 'median_ms': float(np.median([r['t'][p] for r in sub])),
                               'median_ms_DCS': float(np.median([r['t']['DCS'] for r in sub])),
                               'power_solves_mean': float(np.mean([r['calls'][p] for r in sub])), 'power_solves_DCS': float(np.mean([r['calls']['DCS'] for r in sub])),
                               'subsets_visited_mean': float(np.mean([r['visited'][p] for r in sub])),
                               'same_decision': float(np.mean([r['same'][p] for r in sub])),
                               'same_cardinality': float(np.mean([r['card_by'][p] == r['card'] for r in sub])),
                               'cardinality_loss_mean': float(np.mean([r['card'] - r['card_by'][p] for r in sub]))}
                        if p in ('LRS',) and region != 'outside':
                            d, _, _ = drop_level(rows, lambda r: (r['t']['CBD'] - r['t']['LRS']) / r['t']['DCS'], K, cond)
                            row['perm_p_LRS_vs_CBD_two_sided'] = S.perm_paired(d, NP, seed, 'two')['p'] if d else None
                        C.append(row)
        qc = timing_qc(rows); res.update(QC_pairs=qc['pairs'], QC_discordant=qc['discordant'], QC_rate=qc['rate'], QC_pass=qc['pass'])
        res['verdict'] = ('DECISIONS_ONLY: G1 ' + ('PASS' if g1 else 'FAIL')) if not timed_ok else 'PASS' if res['G1_exact'] and res.get('G3') is not False and res.get('G2') is not False and res.get('G4') is not False else 'FAIL'
        E.append(res)
    if not E: sys.exit('No held-out measurements yet.')
    write_csv(OUT / 'G04_endpoints.csv', E); write_csv(OUT / 'G05_comparison.csv', C); wj(OUT / 'G06_stats.json', ST)
    loso = leave_one_scene_out(proto, maps); wj(OUT / 'G06b_leave_one_scene_out.json', loso)
    summary(proto, E, C, ST, loso)


def leave_one_scene_out(proto, maps):
    """Secondary analysis: map developed without scene s, applied to the held-out drops of s. The LRS time of the alternative
    map is inferred from the measured DCS/PBS times of the same realization plus the measured LRS routing overhead."""
    out = {}; Kmax = max(proto['ks']); Lmax = max(proto['Ls'])
    for cid, c in configs(proto, ''):
        dev = read_jsonl(OUT / f'G01_dev_{cid}.jsonl'); hold = read_jsonl(OUT / f'G03_hold_{cid}.jsonl')
        if not dev or not hold or not all(r['t'].get('DCS') for r in hold): continue
        for s in sorted({r['set'] for r in hold}):
            m, _ = develop_map([r for r in dev if r['set'] != s], proto, 500, proto['seed'])
            H = [r for r in hold if r['set'] == s and r['K'] == Kmax and r['L'] == Lmax]
            if not H: continue
            sav = []
            for r in H:
                on = bin_index(r['eta'], proto['bins']) in m[f'K{Kmax}_L{Lmax}']
                ovh = max(0.0, r['t']['LRS'] - (r['t']['PBS'] if r['routed_LRS'] else r['t']['DCS']))
                t = (r['t']['PBS'] if on else r['t']['DCS']) + ovh; sav.append((r['t']['DCS'] - t) / r['t']['DCS'])
            out.setdefault(cid, {})[s] = {'map_without_scene': m[f'K{Kmax}_L{Lmax}'], 'n': len(sav), 'mean_rel_saving_Kmax_Lmax': float(np.mean(sav)),
                                           'min': float(np.min(sav))}
    return out


def write_csv(p, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, 'w', encoding='utf8') as h:
        h.write(','.join(keys) + '\n')
        for r in rows: h.write(','.join('' if r.get(k) is None else (f'{r[k]:.6g}' if isinstance(r[k], float) else str(r[k]).replace(',', ';')) for k in keys) + '\n')


def qc_text(e):
    if e.get('QC_rate') is None: return '—'
    return ('PASS ' if e['QC_pass'] else 'FAIL ') + f"{100 * e['QC_rate']:.2f}% ({e['QC_discordant']}/{e['QC_pairs']})"


def pct(x): return '—' if x is None else f'{100 * x:.1f}%'


def summary(proto, E, C, ST, loso):
    L = ['# V18 generality study — summary', '', f"Protocol {VERSION}; held-out drops only. Machine: {machine()['cpu']}.", '',
         '## Endpoints per configuration', '', '| Config | drops | in R | G1 exact | G2 LRS in R, K_max [CI] p | G3 worst CI lo outside R | G4 acc(eta>=1) | eta* [CI] | verdict | timing QC (discordant pairs) |',
         '|---|---|---|---|---|---|---|---|---|---|']
    for e in E:
        g2 = f"{pct(e.get('G2_mean'))} [{pct(e.get('G2_lo'))}, {pct(e.get('G2_hi'))}] p={e.get('G2_p'):.3g}" if e.get('G2_mean') is not None else e.get('G2_note', '—')
        es = f"{e['eta_star']:.2f} [{e.get('eta_star_lo') or float('nan'):.2f}, {e.get('eta_star_hi') or float('nan'):.2f}]" if e.get('eta_star') else '—'
        L.append(f"| {e['config']} | {e['n_hold_drops']} | {e['n_R']} | {e['G1_exact']} | {g2} | {pct(e.get('G3_worst_lo'))} | "
                 f"{pct(e.get('G4_acc_rule_eta1'))} (n={e.get('G4_n')}) | {es} | {e['verdict']} | "
                 f"{qc_text(e)} |")
    L += ['', '## Schedulers at K_max (all held-out drops, relative saving vs DCS, drop-level mean [CI95])', '',
          '| Config | policy | saving | same decision | same cardinality | power solves (DCS) |', '|---|---|---|---|---|---|']
    Kmax = max(proto['ks'])
    for r in C:
        if r['K'] == Kmax and r['region'] == 'all':
            L.append(f"| {r['config']} | {r['policy']} | {pct(r['rel_saving_mean'])} [{pct(r['rel_saving_lo'])}, {pct(r['rel_saving_hi'])}] | "
                     f"{pct(r['same_decision'])} | {pct(r['same_cardinality'])} | {r['power_solves_mean']:.1f} ({r['power_solves_DCS']:.1f}) |")
    L += ['', '## Hierarchical statistics (LRS saving at K_max, all held-out drops)', '', '| Config | stratified CI | two-level CI (scenes) | ICC | n_eff | drops for ±2 pp |', '|---|---|---|---|---|---|']
    for cid, s in ST.items():
        x = s['cellwide_LRS_Kmax']; t = x['two_level']
        L.append(f"| {cid} | {pct(x['stratified']['mean'])} [{pct(x['stratified']['lo'])}, {pct(x['stratified']['hi'])}] | [{pct(t['lo'])}, {pct(t['hi'])}]"
                 f"{'' if t.get('reliable') else ' (fewer than 5 scenes)'} | {x['icc'].get('icc') if x['icc'].get('icc') is None else round(x['icc']['icc'], 3)} | "
                 f"{x['icc'].get('n_effective') and round(x['icc']['n_effective'], 1)} | {x['drops_for_halfwidth_2pp']} |")
    if loso:
        L += ['', '## Leave-one-scene-out (secondary, inferred LRS time)', '']
        for cid, d in loso.items(): L.append(f"- {cid}: " + '; '.join(f"{s}: map {v['map_without_scene']}, mean {pct(v['mean_rel_saving_Kmax_Lmax'])}, min {pct(v['min'])}" for s, v in d.items()))
    (OUT / 'G07_SUMMARY.md').write_text('\n'.join(L) + '\n', encoding='utf8'); print('\n'.join(L))


# ------------------------------------------------------------------ stage timing and per-operation costs (Q4)
def st_stages(a):
    proto = load_protocol(); check_env(); cid = a.config or proto['reference_config']
    c = next(c for i, c in configs(proto, '') if i == cid); cfg = make_cfg(c['gamma_db'], c['eps'], proto['pmax_dbm'])
    maps = rj(OUT / 'G02_maps.json')['configs'][cid]['maps'] if (OUT / 'G02_maps.json').exists() else {}
    L1 = n18.lib(True); pair = L1.timer_pair_cost_ms(200000)
    D = sample_drops(proto, c['M'], a.max_drops, proto['seed'])
    rows = []; rng = random.Random(proto['seed'])
    for n, (lab, g, role, H) in enumerate(D):
        for K in proto['ks']:
            for L in proto['Ls']:
                al = ALPHAS[:L]; act = maps.get(f'K{K}_L{L}', [len(proto['bins'])])
                for p in ('DCS', 'PBS', 'LRS', 'CBD'):
                    Pu = n18.P18(H[:, :K], al, cfg, bins=proto['bins'], active_cells=act)
                    Pt = n18.P18(H[:, :K], al, cfg, bins=proto['bins'], active_cells=act, timed=True)
                    tu = float(np.median([timed(Pu, p, a.min_ms)[0] for _ in range(3)]))
                    L1.stage_reset(); nrep = max(1, timed(Pt, p, a.min_ms)[1]); L1.stage_reset()
                    t0 = time.perf_counter(); Pt.repeat(nrep, p); tt = (time.perf_counter() - t0) * 1000 / nrep
                    st, cnt = Pt.stages(); Pt.repeat(1, p); _, info = Pt.result()
                    r = {'set': lab, 'group': g, 'role': role, 'K': K, 'L': L, 'policy': p, 'eta': Pu.eta(), 't_untimed_ms': tu, 't_timed_ms': tt,
                         'timer_pair_ms': pair, 'timer_overhead_ms': pair * sum(cnt) / nrep}
                    for s, v, k in zip(n18.STAGES, st, cnt): r[f'{s}_ms'] = v / nrep; r[f'{s}_n'] = k / nrep
                    r['other_ms'] = tt - sum(v / nrep for v in st); r['closure'] = sum(v / nrep for v in st) / tt if tt > 0 else None
                    r.update({k: info[k] for k in ('full_calls', 'subsets_visited', 'prebeam_rejected', 'sbar', 'cls_feasible', 'cls_coupling', 'cls_power', 'cls_zero')})
                    rows.append(r)
        print(f'  stages {n + 1}/{len(D)} drops', flush=True)
    write_csv(OUT / 'G08_stages.csv', rows)
    ops = op_costs(D, cfg, proto, a.min_ms); write_csv(OUT / 'G10_op_costs.csv', ops)
    shares = stage_shares(rows); wj(OUT / 'G08b_stage_shares.json', {'config': cid, 'timer_pair_ms': pair, 'shares': shares})
    print(json.dumps(shares, indent=1))


def sample_drops(proto, M, cap, seed):
    out = []
    for role in ('dev', 'hold'):
        D = drops(proto, role, M); D = sorted(D, key=lambda d: u01(seed, 'stage', d[0], d[1]))
        per = {}
        for d in D:
            if len(per.setdefault(d[0], [])) < max(1, cap // (2 * max(1, len({x[0] for x in D})))): per[d[0]].append(d)
        out += [(d[0], d[1], role, d[3]) for v in per.values() for d in v]
    return out


def op_costs(D, cfg, proto, min_ms):
    """Per-candidate cost by size and class, pre-beam bound cost by size, load cost (untimed library)."""
    rows = []; rng = np.random.default_rng(proto['seed'])
    for lab, g, role, H in D[:40]:
        K = max(proto['ks']); P = n18.P18(H[:, :K], ALPHAS, cfg)
        for s in range(1, K + 1):
            subs = [tuple(sorted(rng.choice(K, size=s, replace=False))) for _ in range(4)]
            for sub in dict.fromkeys(subs):
                for l in (0, len(ALPHAS) - 1):
                    n = 1
                    while True:
                        t0 = time.perf_counter(); stt = P.bench_candidate(n, sub, l); dt = (time.perf_counter() - t0) * 1000
                        if dt >= min_ms / 4 or n > 10 ** 6: break
                        n *= 4
                    nb = 1
                    while True:
                        t0 = time.perf_counter(); P.bench_bound(nb, sub); db = (time.perf_counter() - t0) * 1000
                        if db >= min_ms / 8 or nb > 10 ** 7: break
                        nb *= 8
                    rows.append({'set': lab, 'group': g, 'size': s, 'alpha_index': l, 'status': ['feasible', 'beam', 'zero', 'coupling', 'invalid', 'power'][stt],
                                 'candidate_ms': dt / n, 'bound_ms': db / nb})
        n = 1000; t0 = time.perf_counter(); P.bench_load(n); rows.append({'set': lab, 'group': g, 'size': 0, 'status': 'load', 'candidate_ms': (time.perf_counter() - t0) * 1000 / n})
    return rows


def stage_shares(rows):
    out = {}
    for p in sorted({r['policy'] for r in rows}):
        R = [r for r in rows if r['policy'] == p]; tot = sum(r['t_timed_ms'] for r in R)
        out[p] = {s: sum(r[f'{s}_ms'] for r in R) / tot for s in n18.STAGES}
        out[p]['other'] = sum(r['other_ms'] for r in R) / tot
        out[p]['inflation_timed_over_untimed'] = float(np.median([r['t_timed_ms'] / r['t_untimed_ms'] for r in R if r['t_untimed_ms'] > 0]))
        out[p]['median_closure'] = float(np.median([r['closure'] for r in R if r['closure'] is not None]))
    return out


# ------------------------------------------------------------------ hardware bundle and comparison (Q4)
def features(r):
    """Cost-model features of eq. (model) from the PBS counters: rejected subsets by size at visited levels, visited subsets."""
    K, L = r['K'], r['L']; rej = r['pbs']['rejected_by_size']; card = max(r['card'], 1)
    x = [L * sum(rej[s - 1] * s ** e for s in range(card, K + 1)) for e in (1, 2, 3)]
    return x + [-r['pbs']['subsets_visited'], -1.0]


def fit_nnls(rows):
    from scipy.optimize import nnls
    X = np.array([features(r) for r in rows]); y = np.array([r['t_DCS'] - r['t_PBS'] for r in rows])
    coef, _ = nnls(X, y); return coef


def evaluate(coef, rows, scale=1.0):
    X = np.array([features(r) for r in rows]); y = np.array([r['t_DCS'] - r['t_PBS'] for r in rows]); yh = scale * X @ coef
    ss = np.sum((y - y.mean()) ** 2); big = np.abs(y) > 0.02 * np.array([r['t_DCS'] for r in rows])
    return {'R2': float(1 - np.sum((y - yh) ** 2) / ss) if ss > 0 else None, 'n': int(len(y)),
            'sign_acc_all': float(np.mean(np.sign(y) == np.sign(yh))), 'sign_acc_gt2pct': float(np.mean(np.sign(y[big]) == np.sign(yh[big]))) if big.any() else None}


def cost_bound(rows, ops):
    """Conservative lower bound of the PBS saving: avoided candidates at the 5th-percentile cost of an infeasible candidate of
    their size, minus visited subsets at the 95th-percentile bound cost and the 95th-percentile load cost."""
    inf = {}; bnd = []; load = []
    for o in ops:
        if o['status'] == 'load': load.append(o['candidate_ms']); continue
        bnd.append(o['bound_ms'])
        if o['status'] != 'feasible': inf.setdefault(o['size'], []).append(o['candidate_ms'])
    clo = {s: float(np.quantile(v, .05)) for s, v in inf.items()}; cE = float(np.quantile(bnd, .95)); cl = float(np.quantile(load, .95)) if load else 0.0
    out = []
    for r in rows:
        K, L = r['K'], r['L']; rej = r['pbs']['rejected_by_size']; card = max(r['card'], 1)
        lb = sum(L * rej[s - 1] * clo.get(s, min(clo.values())) for s in range(card, K + 1)) - r['pbs']['subsets_visited'] * cE - cl
        out.append((r['t_DCS'] - r['t_PBS']) >= lb)
    return {'c_low_by_size_ms': clo, 'bound_cost_q95_ms': cE, 'load_cost_q95_ms': cl, 'validity': float(np.mean(out)) if out else None, 'n': len(out)}


def st_hwbundle(a):
    proto = load_protocol(); check_env(); cid = proto['reference_config']; m = machine()
    c = next(c for i, c in configs(proto, '') if i == cid); cfg = make_cfg(c['gamma_db'], c['eps'], proto['pmax_dbm'])
    tag = f"HW_{m['host']}_{hashlib.sha256(m['cpu'].encode()).hexdigest()[:6]}"; d = OUT / tag; d.mkdir(exist_ok=True)
    dev = [r for r in read_jsonl(OUT / f'G01_dev_{cid}.jsonl') if r['host'] == m['host']]
    hold = [r for r in read_jsonl(OUT / f'G03_hold_{cid}.jsonl') if r['host'] == m['host'] and r['t'].get('DCS')]
    hold = [dict(r, t_DCS=r['t']['DCS'], t_PBS=r['t']['PBS']) for r in hold]
    if a.quick or not dev or not hold:
        print('Measuring the reference configuration on a sample of drops (quick mode)')
        dev, hold = quick_rows(proto, c, cfg, a.max_drops, m['host'])
    coef = fit_nnls(dev)
    ops = op_costs(sample_drops(proto, c['M'], 40, proto['seed']), cfg, proto, 10.0)
    out = {'machine': m, 'config': cid, 'coef_ms': dict(zip(('t1', 't2', 't3', 'c_E', 'c_0'), map(float, coef))),
           'fit_development': evaluate(coef, dev), 'validation_held_out': evaluate(coef, hold), 'cost_bound_held_out': cost_bound(hold, ops),
           'median_t_DCS_dev_ms': float(np.median([r['t_DCS'] for r in dev])),
           'break_even': S.break_even_threshold([r['eta'] for r in hold if r['K'] == max(proto['ks'])],
                                                [(r['t_DCS'] - r['t_PBS']) / r['t_DCS'] for r in hold if r['K'] == max(proto['ks'])], 500, proto['seed'])}
    wj(d / 'HW_bundle.json', out); write_csv(d / 'HW_op_costs.csv', ops)
    with open(d / 'HW_rows.jsonl', 'w', encoding='utf8') as h:
        for r in dev: h.write(json.dumps(dict(r, role='dev')) + '\n')
        for r in hold: h.write(json.dumps(dict(r, role='hold')) + '\n')
    print(json.dumps({k: out[k] for k in ('coef_ms', 'fit_development', 'validation_held_out', 'cost_bound_held_out')}, indent=1))
    print('Bundle:', d, '-> copy this folder to the machine that runs hwcompare')


def quick_rows(proto, c, cfg, cap, host):
    rng = random.Random(proto['seed']); dev, hold = [], []
    for lab, g, role, H in sample_drops(proto, c['M'], cap, proto['seed']):
        for K in proto['ks']:
            for L in proto['Ls']:
                P = {p: n18.P18(H[:, :K], ALPHAS[:L], cfg) for p in ('DCS', 'PBS')}
                res = {}
                for p in P: P[p].repeat(1, p); res[p] = P[p].result()
                ms = measure(P, ('DCS', 'PBS'), proto['timing']['min_ms'], proto['timing']['repeats'], rng)
                r = {'set': lab, 'group': g, 'K': K, 'L': L, 'eta': P['DCS'].eta(), 't_DCS': ms['DCS'], 't_PBS': ms['PBS'],
                     'card': res['DCS'][0]['cardinality'] if res['DCS'][0] else 0, 'pbs': res['PBS'][1], 'host': host}
                (dev if role == 'dev' else hold).append(r)
    return dev, hold


def st_hwcompare(a):
    B = [(Path(b).name, rj(Path(b) / 'HW_bundle.json'), read_jsonl(Path(b) / 'HW_rows.jsonl')) for b in a.bundles]
    L = ['# V18 — hardware comparison of the cost model and the cost bound', '',
         '| Machine | CPU | t1 (ms) | c_E (ms) | dev R2 | held-out R2 | sign acc (|saving|>2%) | bound validity | eta* [CI] | acc(eta>=1) |', '|---|---|---|---|---|---|---|---|---|---|']
    for n, b, _ in B:
        be = b['break_even']
        f3 = lambda x: '—' if x is None else f'{x:.3f}'
        L.append(f"| {n} | {b['machine']['cpu']} | {b['coef_ms']['t1']:.4g} | {b['coef_ms']['c_E']:.4g} | {f3(b['fit_development']['R2'])} | "
                 f"{f3(b['validation_held_out']['R2'])} | {f3(b['validation_held_out']['sign_acc_gt2pct'])} | {f3(b['cost_bound_held_out']['validity'])} | "
                 f"{f3(be.get('eta_star'))} [{f3(be.get('lo'))}, {f3(be.get('hi'))}] | {f3(be.get('acc_rule_1'))} |")
    L += ['', '## Transfer: coefficients of machine A applied to machine B with one speed factor (ratio of median DCS times on development drops)', '',
          '| A -> B | speed factor | R2 on B held-out | sign acc on B (|saving|>2%) |', '|---|---|---|---|']
    res = []
    for na, ba, _ in B:
        coef = np.array([ba['coef_ms'][k] for k in ('t1', 't2', 't3', 'c_E', 'c_0')])
        for nb, bb, rb in B:
            if na == nb: continue
            f = bb['median_t_DCS_dev_ms'] / ba['median_t_DCS_dev_ms']; ev = evaluate(coef, [r for r in rb if r['role'] == 'hold'], f)
            res.append({'from': na, 'to': nb, 'speed_factor': f, **ev})
            L.append(f"| {na} -> {nb} | {f:.3f} | {ev['R2']:.3f} | {'—' if ev['sign_acc_gt2pct'] is None else round(ev['sign_acc_gt2pct'], 3)} |")
    (OUT / 'G09_HARDWARE.md').write_text('\n'.join(L) + '\n', encoding='utf8'); wj(OUT / 'G09_hardware.json', res); print('\n'.join(L))


# ------------------------------------------------------------------ timing stability probe, re-timing (V18.3)
def st_probe(a):
    """Times the SAME DCS search twice (two independent C buffers) on a sample of drops; the machine is stable if the
    discordance of these identical pairs is <= 1% and their median |log ratio| <= 0.03. Run it before any timing stage."""
    proto = load_protocol(); check_env(); cid = a.config or proto['reference_config']
    c = next(c for i, c in configs(proto, '') if i == cid); cfg = make_cfg(c['gamma_db'], c['eps'], proto['pmax_dbm'])
    D = sample_drops(proto, c['M'], a.max_drops, proto['seed'] + 7); rng = random.Random(proto['seed']); q = []; t0 = time.time()
    blocks = max(1, math.ceil(PROBE_MIN_PAIRS / (2 * max(1, len(D)))))      # >= 200 pairs resolve a 1% rate
    for lab, g, role, H in D:
        for K in (min(proto['ks']), max(proto['ks'])):
            P = {'A': n18.P18(H[:, :K], ALPHAS, cfg), 'B': n18.P18(H[:, :K], ALPHAS, cfg)}
            for _ in range(blocks):      # one pair = the same statistic as the held-out timing (median of interleaved repeats)
                t = {'A': [], 'B': []}
                for _ in range(proto['timing']['repeats']):
                    order = ['A', 'B']; rng.shuffle(order)
                    for k in order: t[k].append(timed(P[k], 'DCS', proto['timing']['min_ms'])[0])
                q.append(float(np.median(t['A']) / np.median(t['B'])))
    d = sum(abs(math.log(x)) > math.log(QC_RATIO) for x in q); med = float(np.median([abs(math.log(x)) for x in q]))
    out = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'machine': machine(), 'config': cid, 'pairs': len(q), 'discordant': int(d),
           'rate': d / len(q), 'median_abs_log_ratio': med, 'seconds': time.time() - t0,
           'stable': d / len(q) <= QC_MAX_RATE and med <= 0.03}
    f = OUT / f"G11_probe_{time.strftime('%Y%m%d_%H%M%S')}.json"; wj(f, out)
    print(json.dumps({k: out[k] for k in ('pairs', 'discordant', 'rate', 'median_abs_log_ratio', 'stable')}, indent=1))
    print('STABLE: timing may start.' if out['stable'] else 'NOT STABLE: stop other jobs (updates, indexing, GPU jobs, browsers), wait, and probe again.')
    sys.exit(0 if out['stable'] else 2)


def st_retime_setup(a):
    """New output folder for a declared re-timing of selected configurations: same protocol, split, maps and drops.
    The rule is fixed here, before the new timing starts."""
    src = Path(a.source) if Path(a.source).is_absolute() else REPO / a.source
    if not (src / 'G02_maps.json').exists(): sys.exit(f'{src} has no G02_maps.json')
    cfgs = [c for c in a.configs.split(',') if c]
    if not cfgs: sys.exit('give --configs')
    orig = {c: sha_file(src / f'G03_hold_{c}.jsonl') for c in cfgs if (src / f'G03_hold_{c}.jsonl').exists()}
    qc0 = {c: timing_qc(read_jsonl(src / f'G03_hold_{c}.jsonl')) for c in orig}
    decl = {'version': VERSION, 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'source': str(a.source), 'configs': cfgs,
            'reason': a.reason, 'source_G03_sha256': orig, 'source_timing_qc': qc0,
            'qc_rule': f'identical-path pairs (LRS vs the DCS or PBS search it executes) differing by more than {QC_RATIO}x must be <= {100 * QC_MAX_RATE:.0f}%',
            'reporting_rule': 'the re-timed run replaces the original runtime endpoints only if its timing QC passes and every decision equals the original run; '
                              'otherwise both runs are reported and the configuration is marked timing-unresolved. Decisions (G1, G4 inputs) of the original run are kept.',
            'one_retime_only': True}
    OUT.mkdir(parents=True, exist_ok=True); f = OUT / 'G00c_retime.json'
    if f.exists():
        old = rj(f)
        if {k: v for k, v in old.items() if k != 'created_utc'} != {k: v for k, v in json.loads(json.dumps(decl, default=str)).items() if k != 'created_utc'}:
            sys.exit('G00c_retime.json exists with different content: a configuration may be re-timed only once.')
        print('Re-timing already declared (unchanged):', f); return
    for name in ('G00_protocol.json', 'G00b_split.csv', 'G02_maps.json'): shutil.copy2(src / name, OUT / name)
    for c in cfgs:
        if (src / f'G01_dev_{c}.jsonl').exists(): shutil.copy2(src / f'G01_dev_{c}.jsonl', OUT / f'G01_dev_{c}.jsonl')
    wj(f, decl); print('Re-timing declared:', f); print(json.dumps({c: qc0[c] for c in qc0}, indent=1))


def st_retime_compare(a):
    decl = rj(OUT / 'G00c_retime.json'); src = Path(decl['source']) if Path(decl['source']).is_absolute() else REPO / decl['source']
    E0 = {r['config']: r for r in csv_rows(src / 'G04_endpoints.csv')}; E1 = {r['config']: r for r in csv_rows(OUT / 'G04_endpoints.csv')}
    rep_ = []; L = ['# V18 re-timing report', '', f"Reason: {decl['reason']}", '', f"QC rule: {decl['qc_rule']}", '', f"Reporting rule: {decl['reporting_rule']}", '',
                    '| Config | decisions identical | QC original | QC re-timed | G2 lo orig -> new | G3 worst lo orig -> new | verdict orig -> new | reported run |', '|---|---|---|---|---|---|---|---|']
    for c in decl['configs']:
        A = {(r['set'], r['group'], r['K'], r['L']): r for r in read_jsonl(src / f'G03_hold_{c}.jsonl')}
        B = {(r['set'], r['group'], r['K'], r['L']): r for r in read_jsonl(OUT / f'G03_hold_{c}.jsonl')}
        same = decisions_identical(A, B)
        q0, q1 = timing_qc(A.values()), timing_qc(B.values()); e0, e1 = E0.get(c, {}), E1.get(c, {})
        use = 're-timed' if same and q1['pass'] else 'both (timing-unresolved)'
        rep_.append({'config': c, 'decisions_identical': same, 'qc_original': q0, 'qc_retimed': q1, 'endpoints_original': e0, 'endpoints_retimed': e1, 'reported': use})
        L.append(f"| {c} | {same} | {100 * (q0['rate'] or 0):.2f}% | {100 * (q1['rate'] or 0):.2f}% | {fpct(e0.get('G2_lo'))} -> {fpct(e1.get('G2_lo'))} | "
                 f"{fpct(e0.get('G3_worst_lo'))} -> {fpct(e1.get('G3_worst_lo'))} | {e0.get('verdict')} -> {e1.get('verdict')} | {use} |")
    wj(OUT / 'G12_retime_report.json', rep_); (OUT / 'G12_RETIME.md').write_text('\n'.join(L) + '\n', encoding='utf8'); print('\n'.join(L))


def fpct(x):
    try: return f'{100 * float(x):.1f}%'
    except (TypeError, ValueError): return '—'


def decisions_identical(A, B):
    """A, B: dict key -> row. True if both runs hold the same realizations with the same decisions and counters."""
    if set(A) != set(B): return False
    for k in A:
        a, b = A[k], B[k]
        if a['card_by'] != b['card_by'] or a['calls'] != b['calls'] or a['same'] != b['same'] or a['routed_LRS'] != b['routed_LRS']: return False
        for p in a['p_by']:
            x, y = a['p_by'][p], b['p_by'].get(p)
            if (x is None) != (y is None) or (x is not None and abs(x - y) > 1e-9 * max(1e-18, abs(x))): return False
    return True


def csv_rows(p):
    import csv as _c
    with open(p, encoding='utf8') as h: return list(_c.DictReader(h))


# ------------------------------------------------------------------ CLI
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('stage', choices=('selftest', 'protocol', 'develop', 'lock', 'test', 'analyze', 'stages', 'hwbundle', 'hwcompare', 'probe', 'retime-setup', 'retime-compare'))
    p.add_argument('--source', default='', help='retime-setup: output folder of the original run'); p.add_argument('--reason', default='', help='retime-setup: why the configurations are re-timed')
    p.add_argument('--set', action='append', default=[], help='LABEL=path[:dev|hold|split] (protocol stage), e.g. UMA=data/nat2_pool.npz')
    p.add_argument('--grid-M', type=lambda s: [int(x) for x in s.split(',')], default=[8, 16])
    p.add_argument('--grid-gamma-db', type=lambda s: [float(x) for x in s.split(',')], default=[0., 6., 10.])
    p.add_argument('--grid-eps', type=lambda s: [float(x) for x in s.split(',')], default=[0.02, 0.04, 0.08])
    p.add_argument('--pmax-dbm', type=float, default=30.); p.add_argument('--ks', type=lambda s: [int(x) for x in s.split(',')], default=[4, 6, 8])
    p.add_argument('--Ls', type=lambda s: [int(x) for x in s.split(',')], default=[3, 7]); p.add_argument('--split-frac', type=float, default=0.5)
    p.add_argument('--reference-config', default='', help='protocol: configuration used by stages/hwbundle (default M16_G6_E0.04, or the first M of the grid)')
    p.add_argument('--prior-use', action='append', default=[], help='protocol: LABEL=text, records the actual prior use of a set (overrides its provenance)')
    p.add_argument('--note', default='', help='protocol: free text stored in G00 (e.g. which study this protocol extends)')
    p.add_argument('--seed', type=int, default=20261125); p.add_argument('--min-ms', type=float, default=10.); p.add_argument('--repeats', type=int, default=5)
    p.add_argument('--bootstrap', type=int, default=2000); p.add_argument('--n-perm', type=int, default=100000)
    p.add_argument('--oracle-fraction', type=float, default=0.02); p.add_argument('--max-drops-per-set', type=int, default=0)
    p.add_argument('--configs', default='', help='comma list of configuration ids (default: all)')
    p.add_argument('--config', default='', help='stages: configuration id (default: reference M16_G6_E0.04)')
    p.add_argument('--max-drops', type=int, default=40, help='stages / hwbundle: drops sampled (half development, half held-out)')
    p.add_argument('--quick', action='store_true', help='hwbundle: measure a sample instead of reusing develop/test rows')
    p.add_argument('--bundles', nargs='*', default=[]); p.add_argument('--force', action='store_true')
    p.add_argument('--out', default='outputs_v18', help='output folder (relative to the repository root)')
    p.add_argument('--decisions-only', action='store_true', help='test: decisions and counters without timing (dry run)')
    a = p.parse_args()
    global OUT
    OUT = (REPO / a.out) if not Path(a.out).is_absolute() else Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
    if a.stage == 'selftest': n18.build(); sys.exit(0 if n18.selftest() else 1)
    {'protocol': st_protocol, 'develop': st_develop, 'lock': st_lock, 'test': st_test, 'analyze': st_analyze,
     'stages': st_stages, 'hwbundle': st_hwbundle, 'hwcompare': st_hwcompare, 'probe': st_probe, 'retime-setup': st_retime_setup,
     'retime-compare': st_retime_compare}[a.stage](a)


if __name__ == '__main__':
    main()
