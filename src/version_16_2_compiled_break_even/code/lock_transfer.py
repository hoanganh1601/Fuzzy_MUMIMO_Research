#!/usr/bin/env python3
"""Check whether the frozen V15.2 lock can be reused on this machine, and if not, transfer it.

The V15.2 run signature contains the machine/software description (runtime is machine-specific).
After an OS or kernel update the platform string changes and --lock-from is refused, although the
policy map itself is unchanged. This tool:

  check    : compares the current machine/code/development data with the lock and prints the
             differing fields. Exit code 0 = lock reusable as is (use --lock-from directly).
  transfer : ONLY if code hashes and development data are identical and the difference is limited
             to the 'machine' field, writes a new run manifest (CP00) for this machine and a
             transferred lock whose policy cells are byte-identical to the original (verified by
             hash), with a transfer record (old/new signature, machine diff). Report it in the paper.
             The transferred lock never retrains anything.

  python code/lock_transfer.py --stage check --manifest outputs/V152_DM/CP00_manifest.json --lock outputs/V152_DM/CP03_locked_cells.json --development data/dev.npz
  python code/lock_transfer.py --stage transfer ... --dev-provenance data/dev.npz.provenance.json --new-run-id V16_NAT
"""
import argparse, hashlib, json, sys, types
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from robust_model import digest, jwrite
from run_experiment import config_signature, machine_info, sha_text, rjson, utf8_console, SOURCES, provenance, load_any


def rebuild_args(settings, development):
    s = settings
    return types.SimpleNamespace(q=s['q'], sigma_rel=s['sigma_rel'], sinr_db=s['sinr_db'], noise=s['noise'], pmax=s['pmax'], ks=s['ks'],
                                 alphas=s['alphas'], beam_counts=tuple(s['beam_counts']), guard=s['guard'], repeats=s['repeats'],
                                 bootstrap=s['bootstrap'], min_gain_ms=s['min_gain_ms'], min_rel_gain=s['min_rel_gain'],
                                 min_cell_groups=s['min_cell_groups'], min_dev_groups=s['min_dev_groups'], min_test_groups=s['min_test_groups'],
                                 er_bins=','.join(repr(float(x)) for x in s['er_bins']), early_bound=s['early_bound'],
                                 min_region_groups=s['min_region_groups'], min_dev_region_groups=s['min_dev_region_groups'],
                                 smoke=s['smoke'], limit=s['limit'], profile_candidates=s['profile_candidates'], seed=s['seed'], development=development)


def compare(a):
    man = rjson(a.manifest); lock = rjson(a.lock); old = man['settings']
    if lock['config_signature'] != man['signature']: raise RuntimeError('lock does not belong to this manifest')
    new = json.loads(json.dumps(config_signature(rebuild_args(old, a.development)), ensure_ascii=False))
    diffs = {k: {'lock': old.get(k), 'now': new.get(k)} for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)}
    return man, lock, old, new, diffs


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--stage', choices=('check', 'transfer'), required=True)
    p.add_argument('--manifest', required=True); p.add_argument('--lock', required=True); p.add_argument('--development', required=True)
    p.add_argument('--dev-provenance', default=''); p.add_argument('--new-run-id', default=''); p.add_argument('--out-root', default='outputs')
    a = p.parse_args()
    man, lock, old, new, diffs = compare(a)
    if not diffs:
        print('LOCK REUSABLE AS IS: identical code, data, settings and machine. Use --lock-from', a.lock); sys.exit(0)
    print('DIFFERENCES between the lock and this machine/code/data:')
    for k, v in diffs.items(): print(f'  {k}:\n    lock: {json.dumps(v["lock"], ensure_ascii=False)}\n    now : {json.dumps(v["now"], ensure_ascii=False)}')
    if a.stage == 'check': sys.exit(1)
    if set(diffs) != {'machine'}:
        raise RuntimeError('Transfer refused: only the machine description may differ (code hashes, development data and settings must be identical).')
    if not a.new_run_id or not a.dev_provenance: raise ValueError('--new-run-id and --dev-provenance are required for transfer')
    H, G, _ = load_any(a.development); devp = provenance(a.dev_provenance, False)
    manifest = json.loads(json.dumps({'signature': sha_text(new), 'settings': new, 'source': devp, 'development_n': len(H),
                                      'development_groups': len(set(map(str, G))), 'scope': 'development only'}, ensure_ascii=False))
    root = Path(a.out_root) / a.new_run_id; root.mkdir(parents=True, exist_ok=True)
    mp = root / 'CP00_manifest.json'
    if mp.exists() and rjson(mp) != manifest: raise RuntimeError(f'{mp} exists with different content; choose another --new-run-id')
    jwrite(mp, manifest)
    cells_sha = sha_text(lock['policy_cells'])
    tl = dict(lock); tl['config_signature'] = manifest['signature']
    tl['transfer'] = {'reason': 'machine description changed; policy map unchanged', 'original_lock_sha256': digest(a.lock),
                      'original_signature': lock['config_signature'], 'new_signature': manifest['signature'],
                      'policy_cells_sha256': cells_sha, 'machine_before': old['machine'], 'machine_after': new['machine']}
    out = root / 'CP03T_transferred_lock.json'; jwrite(out, tl)
    assert sha_text(rjson(out)['policy_cells']) == cells_sha
    print('TRANSFERRED lock written:', out, '\nUse it with: --lock-from', out, ' (run id', a.new_run_id, ')')


if __name__ == '__main__': main()
