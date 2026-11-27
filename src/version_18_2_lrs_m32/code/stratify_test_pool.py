#!/usr/bin/env python3
"""Covariate-stratified selection of a sealed test set from a larger channel pool.

Uses ONLY channels and the frozen lock (early_ratio cells); no runtime is ever
measured here. Selects whole groups: --region-groups groups inside the predicted
region R (K_max cell locked to a non-CARD policy) and --outside-groups groups
outside R, with a fixed seed. The selection rule, counts and pool hash are written
into the provenance of the output so that the design is auditable.

  python code/stratify_test_pool.py --pool data/dm_pool.npz --pool-provenance data/dm_pool.npz.provenance.json \
      --manifest outputs/V152_DM/CP00_manifest.json --lock outputs/V152_DM/CP03_locked_cells.json \
      --region-groups 15 --outside-groups 15 --output data/dm_test.npz
"""
import argparse, json
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from run_experiment import channel_features, key, rjson, utf8_console
from robust_model import digest


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--pool', required=True); p.add_argument('--pool-provenance', required=True)
    p.add_argument('--manifest', required=True); p.add_argument('--lock', required=True)
    p.add_argument('--region-groups', type=int, default=15); p.add_argument('--outside-groups', type=int, default=15)
    p.add_argument('--seed', type=int, default=20261119); p.add_argument('--output', required=True)
    a = p.parse_args()
    s = rjson(a.manifest)['settings']; lock = rjson(a.lock)
    if lock['config_signature'] != rjson(a.manifest)['signature']: raise RuntimeError('Lock does not belong to this manifest')
    c = {'q': s['q'], 'sigma': s['sigma_rel'], 'gamma': 10**(s['sinr_db'] / 10), 'noise': s['noise'], 'pmax': s['pmax']}
    ks = sorted(int(v) for v in s['ks'].split(',')); kmax = ks[-1]; bins = tuple(s['er_bins']); robust = s['early_bound'] == 'robust'
    Ls = s['beam_counts']; pol = lock['policy_cells']
    with np.load(a.pool, allow_pickle=False) as f:
        H = f['H']; G = f['groups'].astype(str); extra = {k: f[k] for k in f.files if k not in ('H', 'groups')}
    by = defaultdict(list)
    for i, h in enumerate(H):
        z = channel_features(h[:, :kmax], c, robust, bins)
        by[G[i]].append(any(pol.get(key(kmax, l, z['cell']), 'CARD') != 'CARD' for l in Ls))
    inside = sorted(g for g, v in by.items() if Counter(v).most_common(1)[0][0])
    outside = sorted(g for g in by if g not in set(inside))
    rng = np.random.default_rng(a.seed)
    if len(inside) < a.region_groups or len(outside) < a.outside_groups:
        raise RuntimeError(f'Pool too small: {len(inside)} region / {len(outside)} outside groups available, '
                           f'{a.region_groups} / {a.outside_groups} requested. Enlarge the pool (more cell-edge drops) rather than lowering the target.')
    pick = set(rng.choice(inside, a.region_groups, replace=False)) | set(rng.choice(outside, a.outside_groups, replace=False))
    idx = np.array([i for i, g in enumerate(G) if g in pick])
    out = {'H': H[idx], 'groups': G[idx]}
    for k, v in extra.items():
        if np.ndim(v) and len(v) == len(H): out[k] = v[idx]
        else: out[k] = v
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.output, **out)
    prov = rjson(a.pool_provenance)
    prov.update({'prior_use': prov.get('prior_use', 'never_seen'),
                 'test_selection': {'rule': 'covariate-stratified by frozen lock: region = K_max early_ratio cell locked non-CARD',
                                    'pool_sha256': digest(a.pool), 'lock_signature': lock['config_signature'],
                                    'region_groups_selected': a.region_groups, 'outside_groups_selected': a.outside_groups,
                                    'pool_region_groups': len(inside), 'pool_outside_groups': len(outside), 'seed': a.seed,
                                    'runtime_used_for_selection': False,
                                    'selector_code_sha256': digest(Path(__file__).resolve())}})
    Path(a.output + '.provenance.json').write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding='utf8')
    print(json.dumps(prov['test_selection'], indent=2))
    print('WROTE', a.output, out['H'].shape)


if __name__ == '__main__': main()
