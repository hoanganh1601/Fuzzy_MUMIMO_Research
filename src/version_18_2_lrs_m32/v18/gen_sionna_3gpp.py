#!/usr/bin/env python3
"""V18: generate a fresh 3GPP TR 38.901 channel set (UMi, UMa or RMa) with Sionna from a FROZEN scenario specification.

It reuses the helpers of code/gen_sionna_uma.py (which ran unchanged with Sionna 2.2.0) and only selects the channel model
from the spec field `sionna_scenario` (umi, uma, rma). The output format and provenance are those of gen_sionna_uma.py, so
code/scenario_spec.py --stage validate accepts the file.

  python code/scenario_spec.py --stage freeze --run-id NS18_UMI --out-root outputs_v18 --set name=UMI_V18 --set sionna_scenario=umi ...
  python v18/gen_sionna_3gpp.py --spec outputs_v18/NS18_UMI/NS00_scenario_spec.json --output data/v18_umi_fresh.npz --bs-cols 32
  python code/scenario_spec.py --stage validate --run-id NS18_UMI --out-root outputs_v18 --pool data/v18_umi_fresh.npz \
         --provenance data/v18_umi_fresh.npz.provenance.json
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'code'))
from gen_sionna_uma import import_sionna, set_seed, to_np, sha   # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--spec', required=True); p.add_argument('--output', required=True)
    p.add_argument('--bs-rows', type=int, default=1); p.add_argument('--bs-cols', type=int, default=16)
    p.add_argument('--bs-polarization', default='single'); p.add_argument('--bs-polarization-type', default='V')
    p.add_argument('--bs-pattern', default='38.901'); p.add_argument('--batch', type=int, default=10)
    a = p.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding='utf8')); spec_sha = sha(a.spec); scen = spec['sionna_scenario'].lower()
    if a.bs_rows * a.bs_cols * (2 if a.bs_polarization == 'dual' else 1) != spec['bs_antennas']: raise SystemExit('array size does not match spec bs_antennas')
    sionna, ch, tr, base = import_sionna(); seed_path = set_seed(sionna, spec['pool_seed'])
    fc = spec['carrier_frequency_hz']; U = spec['users_per_geometry']; N = spec['pool_drops']
    bs = tr.PanelArray(num_rows_per_panel=a.bs_rows, num_cols_per_panel=a.bs_cols, polarization=a.bs_polarization,
                       polarization_type=a.bs_polarization_type, antenna_pattern=a.bs_pattern, carrier_frequency=fc)
    ut = tr.PanelArray(num_rows_per_panel=1, num_cols_per_panel=1, polarization='single', polarization_type='V', antenna_pattern='omni', carrier_frequency=fc)
    if scen == 'umi': model = tr.UMi(carrier_frequency=fc, o2i_model=spec['o2i_model'], ut_array=ut, bs_array=bs, direction='downlink')   # ADAPT
    elif scen == 'uma': model = tr.UMa(carrier_frequency=fc, o2i_model=spec['o2i_model'], ut_array=ut, bs_array=bs, direction='downlink')
    elif scen == 'rma': model = tr.RMa(carrier_frequency=fc, ut_array=ut, bs_array=bs, direction='downlink')
    else: raise SystemExit('sionna_scenario must be umi, uma or rma')
    freqs = ch.subcarrier_frequencies(1, spec['subcarrier_spacing_hz']); Hs, D = [], []
    while sum(len(x) for x in Hs) < N:
        b = min(a.batch, N - sum(len(x) for x in Hs))
        topo = ch.gen_single_sector_topology(batch_size=b, num_ut=U, scenario=scen, min_bs_ut_dist=spec['minimum_bs_ut_distance_m'],
                                             isd=spec['inter_site_distance_m'], bs_height=spec['bs_height_m'], min_ut_height=spec['ut_height_m'],
                                             max_ut_height=spec['ut_height_m'], indoor_probability=spec['indoor_probability'])
        model.set_topology(*topo); cir = model(1, 1.0)
        h = to_np(ch.cir_to_ofdm_channel(freqs, *cir, normalize=False))
        if h.shape[1] != U or h.shape[4] != spec['bs_antennas']: raise SystemExit(f'unexpected channel shape {h.shape}; adapt the indexing')
        Hs.append(np.transpose(h[:, :, 0, 0, :, 0, 0], (0, 2, 1)))
        ut_loc, bs_loc = to_np(topo[0]), to_np(topo[1]); D.append(np.linalg.norm(ut_loc[:, :, :2] - bs_loc[:, :1, :2], axis=-1))
        print(f'  generated {sum(len(x) for x in Hs)}/{N}', flush=True)
    H = np.concatenate(Hs)[:N].astype(spec['dataset_dtype']); dist = np.concatenate(D)[:N]
    if not np.isfinite(H).all(): raise SystemExit('non-finite channels')
    groups = np.array([f"{spec['name']}_{spec['pool_seed']}_{i:04d}" for i in range(N)])
    np.savez_compressed(a.output, H=H, groups=groups, ut_distance_m=dist, scenario=np.array(spec['scenario']))
    prov = {k: spec[k] for k in spec if k not in ('created_utc', 'code_sha256', 'pool_seed', 'sample_groups', 'sample_seed', 'purpose', 'bs_array')}
    prov.update({'seed': spec['pool_seed'], 'scenario_spec_sha256': spec_sha, 'n_geometries': int(N), 'n_groups': int(N), 'dataset_shape': list(H.shape),
                 'dataset_sha256': sha(a.output), 'prior_use': 'never_seen', 'generation_code_sha256': sha(Path(__file__)),
                 'sionna_version': getattr(sionna, '__version__', 'unknown'), 'sionna_module': base, 'seed_set_via': seed_path,
                 'bs_array_description': f'PanelArray {a.bs_rows}x{a.bs_cols}, {a.bs_polarization}/{a.bs_polarization_type}, pattern {a.bs_pattern}',
                 'statistical_independence_verified': False, 'independence_basis': f'Fresh Sionna {scen.upper()} drops from a frozen V18 spec; separate seed; never used before.'})
    for mod in ('tensorflow', 'torch'):
        if mod in sys.modules: prov[f'{mod}_version'] = getattr(sys.modules[mod], '__version__', 'unknown')
    Path(a.output + '.provenance.json').write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding='utf8')
    print('WROTE', a.output, H.shape, H.dtype)


if __name__ == '__main__': main()
