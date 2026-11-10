#!/usr/bin/env python3
"""Pre-run check for a new or reused machine (Windows/Linux/macOS).

  python code/check_env.py                         # environment + tests + smoke fingerprint
  python code/check_env.py --data data/deepmimo_v10.npz   # also validate a dataset
  python code/check_env.py --write-fingerprint     # maintainer only: regenerate reference

PASS means: supported Python/NumPy/SciPy, all unit tests pass, and the decisions
on smoke.npz (optimal subset, beam, cardinality, solver-call counts, candidate
status counts; power to 1e-6 relative) equal the reference fingerprint shipped
with the package. Bit-level float differences between BLAS builds are tolerated;
decision differences are not.
"""
import argparse, hashlib, json, platform, subprocess, sys, unittest
from pathlib import Path

CODE = Path(__file__).resolve().parent
ROOT = CODE.parent
FP = CODE / 'expected_smoke_fingerprint.json'
MIN = dict(python=(3, 8), numpy=(1, 24), scipy=(1, 10))


def ver(s):
    out = []
    for x in s.split('.')[:2]:
        d = ''.join(ch for ch in x if ch.isdigit()); out.append(int(d or 0))
    return tuple(out)


def fingerprint():
    import numpy as np
    sys.path.insert(0, str(CODE))
    from reference_model import load, exhaustive, oracle
    from ablation_certified import selection, BASE_VARIANTS
    cfg = dict(q=2.960414, sigma=.04, gamma=10**.6, noise=2e-13, pmax=1.)
    alphas = [0., .001, .01, .05, .1, .3, 1.]
    H, groups, _ = load(ROOT / 'smoke.npz'); en = dict(BASE_VARIANTS)
    geo = []; status = {}
    for h in H:
        rows = exhaustive(h, alphas, cfg)
        for r in rows: status[r['status']] = status.get(r['status'], 0) + 1
        o = oracle(rows)
        rec = dict(oracle=None if o is None else [o['cardinality'], o['subset'], o['alpha'], o['p_req_w']])
        for v in ('ALL', 'CARDINALITY_ONLY'):
            c, st = selection(h, alphas, cfg, en[v], 1e-5)
            rec[v] = [st['full_solves'], st['certificate_pruned'], None if c is None else c['subset']]
        geo.append(rec)
    return dict(geometries=geo, status_counts=status)


def same_fp(a, b):
    if a['status_counts'] != b['status_counts']: return 'candidate status counts differ'
    for i, (x, y) in enumerate(zip(a['geometries'], b['geometries'])):
        if (x['oracle'] is None) != (y['oracle'] is None): return f'geometry {i}: feasibility differs'
        if x['oracle'] and (x['oracle'][:3] != y['oracle'][:3] or abs(x['oracle'][3] - y['oracle'][3]) > 1e-6 * abs(y['oracle'][3])):
            return f'geometry {i}: optimum differs {x["oracle"]} vs {y["oracle"]}'
        for v in ('ALL', 'CARDINALITY_ONLY'):
            if x[v] != y[v]: return f'geometry {i} {v}: {x[v]} vs {y[v]}'
    return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', default=''); ap.add_argument('--write-fingerprint', action='store_true')
    a = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError): pass
    ok = True; report = {}
    import numpy, scipy
    vers = dict(python=platform.python_version(), numpy=numpy.__version__, scipy=scipy.__version__)
    report.update(machine=platform.platform(), processor=platform.processor(), versions=vers)
    print('[1] Environment:', platform.platform(), '| Python', vers['python'], '| NumPy', vers['numpy'], '| SciPy', vers['scipy'])
    for k, m in MIN.items():
        if ver(vers[k]) < m:
            ok = False; print(f'    FAIL: {k} {vers[k]} < {".".join(map(str, m))}. Run: python -m pip install -r code/requirements.txt')
    print('[2] Unit tests ...', flush=True)
    res = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT / 'tests')))
    report['tests'] = dict(run=res.testsRun, failures=len(res.failures), errors=len(res.errors))
    if not res.wasSuccessful(): ok = False; print('    FAIL: unit tests')
    else: print(f'    PASS: {res.testsRun} tests')
    print('[3] Smoke fingerprint (24 geometries) ...', flush=True)
    fp = fingerprint()
    if a.write_fingerprint:
        FP.write_text(json.dumps(fp, indent=1), encoding='utf8'); print('    written', FP); return
    diff = same_fp(fp, json.loads(FP.read_text(encoding='utf8')))
    report['fingerprint'] = diff or 'MATCH'
    if diff: ok = False; print('    FAIL:', diff)
    else: print('    PASS: decisions identical to the reference build')
    if a.data:
        print('[4] Dataset', a.data)
        sys.path.insert(0, str(CODE))
        from reference_model import load, digest
        from independent_validation import LEGACY_SHA
        try:
            H, groups, meta = load(a.data)
            sha = digest(a.data)
            import numpy as np
            info = dict(path=str(Path(a.data).resolve()), sha256=sha, shape=list(H.shape), groups=int(len(np.unique(groups))),
                        is_v10_development_set=(sha == LEGACY_SHA), metadata=list(meta))
            report['dataset'] = info
            print(f'    PASS: H {tuple(H.shape)}, {info["groups"]} groups, sha256 {sha[:16]}...')
            print('    v10 development set (sha matches):', info['is_v10_development_set'],
                  '-> use as --dev only' if info['is_v10_development_set'] else '')
        except Exception as e:
            ok = False; print('    FAIL:', e)
    report['outcome'] = 'PASS' if ok else 'FAIL'
    (ROOT / 'ENV_CHECK.json').write_text(json.dumps(report, indent=1), encoding='utf8')
    print('\nRESULT:', report['outcome'], '(details in ENV_CHECK.json; send this file if anything fails)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__': main()
