#!/usr/bin/env python3
"""V16.3: second natural sample in a POWER-LIMITED deployment -- scenario specification and pool validation.

Why a separate, earlier freeze
------------------------------
The natural protocol (natural_prevalence.py --stage protocol) needs the hash of an existing pool. To exclude
"scenario shopping" (generating several deployments and keeping the one with the largest predicted region),
the deployment itself is frozen FIRST, before any channel is generated:

  freeze   : write NS00_scenario_spec.json (deployment, array, seeds, pool and sample sizes). The generator
             must copy the SHA-256 of this file into the pool provenance (field scenario_spec_sha256).
  validate : check that a generated pool and its provenance follow the frozen spec exactly; write
             NS01_pool_validation.json. Only path gains and distances are summarised; the early ratio
             (the covariate that defines the region R) is deliberately NOT computed on the pool.

Default spec UMA500_TR38901 (the 3GPP TR 38.901 UMa evaluation layout, used as the standard macro deployment):
  scenario UMa, single sector, ISD 500 m, BS height 25 m, UT height 1.5 m, minimum BS-UT distance 35 m,
  indoor probability 0.8 with the low-loss O2I model (TR 38.901 default for UMa) FACT{check Table 7.2-1 of the
  TR 38.901 version in use}, carrier 3.5 GHz, M = 16 BS antennas (same array as the UMi generator), 8 users per drop,
  one subcarrier, no channel normalization, no distance or channel-based filtering, dataset dtype complex64
  (same precision path as NP16), pool 200 drops, sample 100 groups.
Relative to NP16 (UMi, ISD 200 m, outdoor only) two factors change at once: the macro layout and the indoor
users (outdoor-to-indoor penetration loss). The comparison is therefore between two deployments, not an ablation.
An outdoor-only variant can be frozen instead with --set indoor_probability=0.0 (one freeze per run-id).
The V15.2 lock (gamma = 6 dB, Pmax = 1 W, N0 = 2e-13 W, q_c, sigma) is NOT changed: a higher SINR requirement
(URLLC) would change the problem solved by the locked policy map and needs a new development lock.
"""
import argparse, hashlib, json, sys, time
from pathlib import Path
import numpy as np

SPEC_FILE = 'NS00_scenario_spec.json'
VALID_FILE = 'NS01_pool_validation.json'

DEFAULT = {
    'name': 'UMA500_TR38901',
    'purpose': 'second natural-prevalence sample in a power-limited deployment (V16.3)',
    'source': 'Sionna_3GPP',
    'scenario': '3GPP_TR_38.901_UMa_single_sector_ISD500',
    'sionna_scenario': 'uma',
    'inter_site_distance_m': 500.0,
    'bs_height_m': 25.0,
    'ut_height_m': 1.5,
    'minimum_bs_ut_distance_m': 35.0,
    'indoor_probability': 0.8,
    'o2i_model': 'low',
    'carrier_frequency_hz': 3.5e9,
    'subcarrier_spacing_hz': 30e3,
    'selected_baseband_frequency_hz': 0.0,
    'bs_antennas': 16,
    'bs_array': 'same PanelArray as the UMi generator used for NP16 (record it in bs_array_description)',
    'users_per_geometry': 8,
    'channel_normalization': 'none',
    'sampling': 'Sionna uniform random drops in one sector, single ISD; no near/edge strata, no distance or channel-based selection',
    'dataset_dtype': 'complex64',
    'pool_drops': 200,
    'pool_seed': 20261124,
    'sample_groups': 100,
    'sample_seed': 20261125,
    'group_definition': 'One independent topology drop with eight users per group',
}
# provenance fields that must equal the spec
MUST_MATCH = ['scenario', 'inter_site_distance_m', 'bs_height_m', 'ut_height_m', 'minimum_bs_ut_distance_m', 'indoor_probability', 'o2i_model',
              'carrier_frequency_hz', 'bs_antennas', 'users_per_geometry', 'channel_normalization', 'dataset_dtype']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def stage_freeze(a, root):
    spec = dict(DEFAULT)
    for kv in a.set or []:
        k, v = kv.split('=', 1)
        if k not in spec: raise SystemExit(f'unknown spec field {k}')
        spec[k] = type(spec[k])(v) if not isinstance(spec[k], str) else v
    spec['created_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    spec['code_sha256'] = sha(Path(__file__))
    f = root / SPEC_FILE
    if f.exists():
        old = json.loads(f.read_text(encoding='utf8'))
        if {k: v for k, v in old.items() if k != 'created_utc'} != {k: v for k, v in spec.items() if k != 'created_utc'}:
            raise SystemExit('scenario spec already frozen with different content; use a new run-id')
        print('scenario spec already frozen (unchanged):', f, sha(f)); return
    f.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding='utf8')
    print('FROZEN', f); print('scenario_spec_sha256 =', sha(f)); print(json.dumps(spec, indent=2, ensure_ascii=False))


def stage_validate(a, root):
    f = root / SPEC_FILE
    if not f.exists(): raise SystemExit('freeze the scenario spec first')
    spec = json.loads(f.read_text(encoding='utf8')); spec_sha = sha(f)
    prov = json.loads(Path(a.provenance).read_text(encoding='utf8'))
    errs = []
    if prov.get('scenario_spec_sha256') != spec_sha: errs.append('pool provenance scenario_spec_sha256 does not equal the frozen spec (pool not generated from this spec)')
    for k in MUST_MATCH:
        pv, sv = prov.get(k), spec[k]
        if isinstance(sv, float): ok = pv is not None and abs(float(pv) - sv) <= 1e-9 * max(1.0, abs(sv))
        else: ok = pv == sv
        if not ok: errs.append(f'{k}: provenance {pv!r} != spec {sv!r}')
    if prov.get('seed') != spec['pool_seed']: errs.append(f"seed: provenance {prov.get('seed')!r} != spec pool_seed {spec['pool_seed']!r}")
    if prov.get('prior_use', 'never_seen') != 'never_seen': errs.append('pool was used before')
    with np.load(a.pool, allow_pickle=False) as d:
        H = d['H']; G = d['groups'].astype(str); dist = d['ut_distance_m'] if 'ut_distance_m' in d.files else None
    if prov.get('dataset_sha256') not in (None, sha(a.pool)): errs.append('dataset_sha256 in provenance differs from the pool file')
    if H.ndim != 3 or H.shape[1] != spec['bs_antennas'] or H.shape[2] != spec['users_per_geometry']: errs.append(f'H shape {H.shape}')
    if str(H.dtype) != spec['dataset_dtype']: errs.append(f'H dtype {H.dtype} != {spec["dataset_dtype"]}')
    if not np.isfinite(H).all(): errs.append('non-finite channel entries')
    if len(H) != spec['pool_drops']: errs.append(f'{len(H)} drops, spec {spec["pool_drops"]}')
    if len(set(G)) != len(G): errs.append('group labels are not unique (one drop per group expected)')
    if len(set(G)) < spec['sample_groups']: errs.append('fewer groups than the sample size')
    beta_db = 10 * np.log10(np.sum(np.abs(H.astype(np.complex128))**2, axis=1) / H.shape[1])   # per-antenna gain of every user
    summ = {'per_antenna_gain_db_quantiles': dict(zip(['p01', 'p05', 'p25', 'p50', 'p75', 'p95', 'p99'],
                                                     [float(x) for x in np.quantile(beta_db, [.01, .05, .25, .5, .75, .95, .99])]))}
    if dist is not None:
        summ['ut_distance_m_quantiles'] = dict(zip(['min', 'p50', 'max'], [float(x) for x in np.quantile(dist, [0, .5, 1])]))
        if float(np.min(dist)) < spec['minimum_bs_ut_distance_m'] - 1e-6: errs.append('a user is closer than the minimum BS-UT distance')
    out = {'ok': not errs, 'errors': errs, 'pool_sha256': sha(a.pool), 'provenance_sha256': sha(a.provenance), 'scenario_spec_sha256': spec_sha,
           'n_drops': int(len(H)), 'dtype': str(H.dtype), 'summary': summ,
           'note': 'early ratio intentionally not computed on the pool (the region R is evaluated only on the random sample)'}
    (root / VALID_FILE).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf8')
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if errs: raise SystemExit('POOL REJECTED')
    print('POOL ACCEPTED')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--stage', choices=('freeze', 'validate'), required=True)
    p.add_argument('--run-id', required=True); p.add_argument('--out-root', default='outputs')
    p.add_argument('--set', action='append', help='override a spec field at freeze time, e.g. --set indoor_probability=0.0')
    p.add_argument('--pool', default=''); p.add_argument('--provenance', default='')
    a = p.parse_args(); root = Path(a.out_root) / a.run_id; root.mkdir(parents=True, exist_ok=True)
    {'freeze': stage_freeze, 'validate': stage_validate}[a.stage](a, root)


if __name__ == '__main__': main()
