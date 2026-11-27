#!/usr/bin/env python3
"""V18.2 — extension of the generality study to M = 32 antennas with a SEPARATE 32-antenna development set.

The main V18 protocol (results/RESULTS_V18) had no 32-antenna development drops, so the nine M = 32 configurations were
not evaluable. This script runs a second, self-contained protocol in outputs_v18_m32/:

  development : three NEW Sionna sets (UMi, UMa, RMa; 32 antennas; new seeds) generated from specifications that copy every
                deployment field of the V18 fresh held-out sets (NS18_UMI/UMA/RMA) and change only the name and the seed;
  held-out    : the three V18 fresh sets data/v18_{umi,uma,rma}_fresh.npz (150 drops each, 32 antennas). They were timed in V18
                only through their first 8 or 16 antennas, never at M = 32 and never for development; this prior use is
                recorded in the protocol (--prior-use);
  grid        : M = 32 x gamma {0, 6, 10} dB x epsilon {0.02, 0.04, 0.08} (optionally M = 16 on the same drops, --control);
  everything else (timing, map rule, endpoints G1-G4, schedulers, statistics) is identical to V18.

  python v18/run_m32.py specs                                   # 1. fix the three development scenarios (before generation)
  <python-with-sionna> v18/run_m32.py generate --bs-cols 32     # 2. generate them (or: generate --sionna-python <path>)
  python v18/run_m32.py validate                                # 3. check them against the fixed specifications
  python v18/run_m32.py protocol                                # 4. fix the protocol (before any timing)
  python v18/run_m32.py run                                     # 5. develop -> lock -> test -> analyze   (resumable)
  python v18/run_m32.py extras                                  # 6. stage timing and hardware bundle of the M = 32 reference
  python v18/run_m32.py pack                                    # 7. KET_QUA_V18_M32_<date>.zip to send back
"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; REPO = HERE.parent
OUT = 'outputs_v18_m32'
SCEN = {'UMI': 20261211, 'UMA': 20261212, 'RMA': 20261213}        # new seeds of the development sets
COPY = ('source', 'scenario', 'sionna_scenario', 'inter_site_distance_m', 'bs_height_m', 'ut_height_m', 'minimum_bs_ut_distance_m',
        'indoor_probability', 'o2i_model', 'carrier_frequency_hz', 'subcarrier_spacing_hz', 'selected_baseband_frequency_hz', 'bs_antennas',
        'users_per_geometry', 'channel_normalization', 'sampling', 'dataset_dtype', 'group_definition')
ENV = dict(os.environ, PYTHONIOENCODING='utf-8', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')


def run(args, py=None, check=True):
    cmd = [py or sys.executable] + [str(x) for x in args]
    print('>>', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=REPO, env=ENV)
    if check and r.returncode != 0: sys.exit(f'step failed (exit {r.returncode})')
    return r.returncode


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def dev_path(s): return f'data/v18_{s.lower()}_dev32.npz'
def hold_path(s): return f'data/v18_{s.lower()}_fresh.npz'
def spec_path(s): return REPO / OUT / f'NS32_{s}' / 'NS00_scenario_spec.json'


def st_specs(a):
    for s, seed in SCEN.items():
        ref = REPO / 'results' / 'RESULTS_V18' / f'NS18_{s}' / 'NS00_scenario_spec.json'
        if not ref.exists(): sys.exit(f'{ref} not found: run inside the lrs-mumimo repository (v1.7 or later).')
        R = json.loads(ref.read_text(encoding='utf8'))
        sets = [f'{k}={R[k]}' for k in COPY if k in R] + [f'name={s}_D32_V18', f'pool_seed={seed}', f'pool_drops={a.dev_drops}', f'sample_groups={min(100, a.dev_drops)}',
                                                          'purpose=V18.2 development set for M = 32 (deployment copied from the V18 held-out set; new seed)']
        args = ['code/scenario_spec.py', '--stage', 'freeze', '--run-id', f'NS32_{s}', '--out-root', OUT]
        for x in sets: args += ['--set', x]
        run(args)
    print('Specifications fixed. Generate the development sets ONLY from these files (generate).')


def st_generate(a):
    for s in SCEN:
        out = REPO / dev_path(s)
        if out.exists(): print(f'{out.name} exists - not regenerated (delete it only if the generation failed)'); continue
        if not spec_path(s).exists(): sys.exit('Run specs first.')
        run(['v18/gen_sionna_3gpp.py', '--spec', spec_path(s), '--output', dev_path(s), '--bs-rows', a.bs_rows, '--bs-cols', a.bs_cols],
            py=a.sionna_python or None)


def st_validate(a):
    for s in SCEN:
        run(['code/scenario_spec.py', '--stage', 'validate', '--run-id', f'NS32_{s}', '--out-root', OUT, '--pool', dev_path(s),
             '--provenance', dev_path(s) + '.provenance.json'])
    known = {'UMI': '134f58ff65b24d5ce707dc9ca5cf5f2adbeba17590efc323f4fd75cf7762b791', 'UMA': 'a1639b6f8e4eac9eceb278ae5f650596449e103e88071d37a1e7f9b0c2658685',
             'RMA': '0c949de711f9b3c1f404a683af98aa82e612fda2e3c0820f9750246c95b49271'}
    for s, h in known.items():
        p = REPO / hold_path(s)
        if not p.exists(): sys.exit(f'{hold_path(s)} missing (held-out set of V18)')
        if sha(p) != h and not a.allow_other_holdout: sys.exit(f'{hold_path(s)} differs from the V18 held-out set (SHA-256)')
        print(f'held-out {hold_path(s)}: SHA-256 matches V18' if sha(p) == h else f'held-out {hold_path(s)}: OTHER file (allowed by option)')
    for s in SCEN:
        d = json.loads((REPO / OUT / f'NS32_{s}' / 'NS01_pool_validation.json').read_text(encoding='utf8'))
        if not d['ok']: sys.exit(f'{s} development set rejected')
    with open(REPO / OUT / 'DATASETS_M32.csv', 'w', encoding='utf8') as h:
        h.write('file,sha256,role\n')
        for s in SCEN: h.write(f'{dev_path(s)},{sha(REPO / dev_path(s))},development M=32\n')
        for s in SCEN: h.write(f'{hold_path(s)},{sha(REPO / hold_path(s))},held-out\n')
    print('CK: development sets accepted; hashes written to', OUT + '/DATASETS_M32.csv')


def v18(*args): run(['v18/run_v18.py'] + list(args) + ['--out', OUT])


def st_protocol(a):
    sets = []
    for s in SCEN: sets += ['--set', f'{s}_D32={dev_path(s)}:dev']
    for s in SCEN: sets += ['--set', f'{s}_F={hold_path(s)}:hold', '--prior-use',
                            f'{s}_F=V18 held-out at M=8 and M=16 (first antennas); never timed at M=32; never used for development']
    grid_m = '16,32' if a.control else '32'
    v18('protocol', *sets, '--grid-M', grid_m, '--grid-gamma-db', '0,6,10', '--grid-eps', '0.02,0.04,0.08', '--min-ms', a.min_ms,
        '--repeats', a.repeats, '--max-drops-per-set', '150', '--reference-config', 'M32_G6_E0.04',
        '--note', 'V18.2: extends results/RESULTS_V18 to M = 32 with a separate 32-antenna development set; same timing, map rule, endpoints and seed')


def st_run(a):
    for st in ('develop', 'lock', 'test', 'analyze'):
        if st == 'lock' and (REPO / OUT / 'G02_maps.json').exists(): print('G02_maps.json exists - maps already fixed'); continue
        v18(st)


def st_extras(a):
    v18('stages', '--max-drops', '40'); v18('hwbundle')


def st_pack(a):
    o = REPO / OUT
    name = f"KET_QUA_V18_M32_{datetime.date.today():%Y%m%d}"
    shutil.make_archive(str(REPO / name), 'zip', root_dir=REPO, base_dir=OUT)
    print('Send back', name + '.zip', '(includes all G01/G03 raw records, NS32_* validations, HW bundle, notes)')
    if not (o / 'NOTES.txt').exists(): print('REMINDER: write outputs_v18_m32/NOTES.txt (dates, machine, anything unusual) and pack again.')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('stage', choices=('specs', 'generate', 'validate', 'protocol', 'run', 'extras', 'pack'))
    p.add_argument('--dev-drops', type=int, default=150, help='drops per development set (default 150)')
    p.add_argument('--sionna-python', default='', help='generate: Python interpreter with Sionna 2.2.0')
    p.add_argument('--bs-rows', default='1'); p.add_argument('--bs-cols', default='32')
    p.add_argument('--control', action='store_true', help='protocol: also evaluate M = 16 on the same drops (doubles the run time)')
    p.add_argument('--min-ms', default='5'); p.add_argument('--repeats', default='3')
    p.add_argument('--allow-other-holdout', action='store_true', help='validate: accept held-out files whose hash differs from V18 (rehearsal only)')
    a = p.parse_args(); (REPO / OUT).mkdir(exist_ok=True)
    {'specs': st_specs, 'generate': st_generate, 'validate': st_validate, 'protocol': st_protocol, 'run': st_run, 'extras': st_extras, 'pack': st_pack}[a.stage](a)


if __name__ == '__main__':
    main()
