#!/usr/bin/env python3
"""V16.3: generate the sealed UMa pool from the FROZEN scenario spec (NS00_scenario_spec.json) with Sionna.

  python code/gen_sionna_uma.py --spec outputs/NS2/NS00_scenario_spec.json --output data/nat2_pool.npz \
      --bs-rows 1 --bs-cols 16

Output: data/nat2_pool.npz with H (pool_drops, 16, 8) in the spec dtype, groups (one label per drop),
ut_distance_m (pool_drops, 8), and data/nat2_pool.npz.provenance.json containing every spec field,
scenario_spec_sha256, the Sionna / backend versions, the array description and the SHA-256 of this file.

IMPORTANT
- This file is a TEMPLATE written against the public Sionna API (sionna.channel / sionna.phy.channel:
  PanelArray, UMa, gen_single_sector_topology, subcarrier_frequencies, cir_to_ofdm_channel). It was NOT run
  in the authoring environment (no Sionna there). If your Sionna version differs, adapt only the five calls
  marked ADAPT, or reuse the generator that produced the UMi pool of NP16 with the spec values; in both cases
  the provenance must contain scenario_spec_sha256 and the fields checked by scenario_spec.py --stage validate.
- Use the SAME base-station array as the UMi generator of NP16 (--bs-rows/--bs-cols, polarization), so that
  the only change relative to NP16 is the deployment.
- Path loss and shadow fading are kept (no normalization). Every drop is kept: no filtering of any kind.
"""
import argparse, hashlib, importlib, json, sys
from pathlib import Path
import numpy as np


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def to_np(x):
    if hasattr(x, 'detach'): x = x.detach().cpu()
    return np.asarray(x.numpy() if hasattr(x, 'numpy') else x)


def import_sionna():
    import sionna
    for base in ('sionna.phy.channel', 'sionna.channel'):          # ADAPT 1: module layout
        try:
            return sionna, importlib.import_module(base), importlib.import_module(base + '.tr38901'), base
        except ImportError:
            continue
    raise SystemExit('Sionna channel modules not found; adapt import_sionna()')


def set_seed(sionna, seed):
    for path in ('phy.config', 'config'):                          # ADAPT 2: global seed
        obj = sionna
        try:
            for p in path.split('.'): obj = getattr(obj, p)
            obj.seed = seed; return path
        except AttributeError:
            continue
    return 'not set (record manually)'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--spec', required=True); p.add_argument('--output', required=True)
    p.add_argument('--bs-rows', type=int, default=1); p.add_argument('--bs-cols', type=int, default=16)
    p.add_argument('--bs-polarization', default='single'); p.add_argument('--bs-polarization-type', default='V')
    p.add_argument('--bs-pattern', default='38.901'); p.add_argument('--batch', type=int, default=10)
    a = p.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding='utf8')); spec_sha = sha(a.spec)
    if a.bs_rows * a.bs_cols * (2 if a.bs_polarization == 'dual' else 1) != spec['bs_antennas']:
        raise SystemExit('array size does not match spec bs_antennas')
    sionna, ch, tr, base = import_sionna(); seed_path = set_seed(sionna, spec['pool_seed'])
    fc = spec['carrier_frequency_hz']; U = spec['users_per_geometry']; N = spec['pool_drops']
    bs = tr.PanelArray(num_rows_per_panel=a.bs_rows, num_cols_per_panel=a.bs_cols, polarization=a.bs_polarization,
                       polarization_type=a.bs_polarization_type, antenna_pattern=a.bs_pattern, carrier_frequency=fc)
    ut = tr.PanelArray(num_rows_per_panel=1, num_cols_per_panel=1, polarization='single', polarization_type='V',
                       antenna_pattern='omni', carrier_frequency=fc)
    model = tr.UMa(carrier_frequency=fc, o2i_model=spec['o2i_model'], ut_array=ut, bs_array=bs, direction='downlink')   # ADAPT 3
    freqs = ch.subcarrier_frequencies(1, spec['subcarrier_spacing_hz'])
    Hs, D = [], []
    while sum(len(x) for x in Hs) < N:
        b = min(a.batch, N - sum(len(x) for x in Hs))
        topo = ch.gen_single_sector_topology(batch_size=b, num_ut=U, scenario=spec['sionna_scenario'],      # ADAPT 4
                                             min_bs_ut_dist=spec['minimum_bs_ut_distance_m'], isd=spec['inter_site_distance_m'],
                                             bs_height=spec['bs_height_m'], min_ut_height=spec['ut_height_m'], max_ut_height=spec['ut_height_m'],
                                             indoor_probability=spec['indoor_probability'])
        model.set_topology(*topo)
        cir = model(1, 1.0)                                         # ADAPT 5: (num_time_samples, sampling_frequency) -> (a, tau)
        h = to_np(ch.cir_to_ofdm_channel(freqs, *cir, normalize=False))
        # h: [batch, num_rx=U, rx_ant=1, num_tx=1, tx_ant=M, time=1, subcarriers=1]
        if h.shape[1] != U or h.shape[4] != spec['bs_antennas']: raise SystemExit(f'unexpected channel shape {h.shape}; adapt the indexing')
        Hs.append(np.transpose(h[:, :, 0, 0, :, 0, 0], (0, 2, 1)))   # -> (batch, M, U)
        ut_loc, bs_loc = to_np(topo[0]), to_np(topo[1])
        D.append(np.linalg.norm(ut_loc[:, :, :2] - bs_loc[:, :1, :2], axis=-1))
        print(f'  generated {sum(len(x) for x in Hs)}/{N}', flush=True)
    H = np.concatenate(Hs)[:N].astype(spec['dataset_dtype']); dist = np.concatenate(D)[:N]
    if not np.isfinite(H).all(): raise SystemExit('non-finite channels')
    groups = np.array([f"{spec['name']}_{spec['pool_seed']}_{i:04d}" for i in range(N)])
    np.savez_compressed(a.output, H=H, groups=groups, ut_distance_m=dist, scenario=np.array(spec['scenario']))
    prov = {k: spec[k] for k in spec if k not in ('created_utc', 'code_sha256', 'pool_seed', 'sample_groups', 'sample_seed', 'purpose', 'bs_array')}
    prov.update({'seed': spec['pool_seed'], 'scenario_spec_sha256': spec_sha, 'n_geometries': int(N), 'n_groups': int(N),
                 'dataset_shape': list(H.shape), 'dataset_sha256': sha(a.output), 'prior_use': 'never_seen',
                 'generation_code_sha256': sha(Path(__file__)), 'sionna_version': getattr(sionna, '__version__', 'unknown'),
                 'sionna_module': base, 'seed_set_via': seed_path,
                 'bs_array_description': f'PanelArray {a.bs_rows}x{a.bs_cols}, {a.bs_polarization}/{a.bs_polarization_type}, pattern {a.bs_pattern}',
                 'statistical_independence_verified': False,
                 'independence_basis': 'Fresh Sionna UMa single-sector drops generated from a frozen spec after the V15.2 lock and after NP16; separate seed; never used before.'})
    for mod in ('tensorflow', 'torch'):
        if mod in sys.modules: prov[f'{mod}_version'] = getattr(sys.modules[mod], '__version__', 'unknown')
    Path(a.output + '.provenance.json').write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding='utf8')
    print('WROTE', a.output, H.shape, H.dtype, '| per-antenna gain median (dB):',
          float(np.median(10 * np.log10(np.sum(np.abs(H.astype(np.complex128))**2, axis=1) / H.shape[1]))))


if __name__ == '__main__': main()
