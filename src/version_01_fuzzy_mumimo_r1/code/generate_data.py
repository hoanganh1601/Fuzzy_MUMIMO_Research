"""Demo channel generator and DeepMIMO adapter. Outputs H[N,M,K], groups[N] (+ noise_w if physical).

Convention: user k receives y_k = h_k^H x, so column k of H[n] is h_k.
"""
import argparse
from pathlib import Path

import numpy as np


def save(path, H, groups, provenance, noise_w=None):
    Path(path).parent.mkdir(exist_ok=True, parents=True)
    extra = {} if noise_w is None else dict(noise_w=np.float64(noise_w))
    np.savez_compressed(path, H=H.astype(np.complex128), groups=groups.astype(np.int32),
                        provenance=np.array(provenance), **extra)


def thermal_noise_w(bandwidth_hz, nf_db):
    """N = -174 dBm/Hz + 10 log10(B) + NF, converted to W."""
    dbm = -174 + 10 * np.log10(bandwidth_hz) + nf_db
    return 10 ** ((dbm - 30) / 10)


def synthetic(n, M, K, seed, typ, n_groups=12):
    """Groups are correlation levels c_g = .1 + .75 g/(G-1); a grouped split therefore tests
    transfer to unseen correlation levels. All users of one sample share R."""
    rng = np.random.default_rng(seed)
    groups = np.arange(n) % n_groups
    H = np.empty((n, M, K), complex)
    for i in range(n):
        g = int(groups[i])
        corr = .1 + .75 * (g / (n_groups - 1))
        R = (1 - corr) * np.eye(M) + corr * np.ones((M, M))      # PD for 0 <= corr < 1
        C = np.linalg.cholesky(R)
        Z = (rng.normal(size=(M, K)) + 1j * rng.normal(size=(M, K))) / np.sqrt(2)
        if typ == 'umi_inspired':
            # TR 38.901 UMi-street-canyon LOS PL1 formula (d in m, fc in GHz), sigma_SF = 4 dB.
            # Only the large-scale formula is borrowed; NOT a TR 38.901 channel simulator.
            dist = rng.uniform(25, 180, K)
            fc = 3.5
            pl = 32.4 + 21 * np.log10(dist) + 20 * np.log10(fc) + rng.normal(0, 4, K)
            gains = 10 ** (-pl / 20)
        else:
            gains = np.ones(K)
        H[i] = C @ Z * gains[None, :]
    return H, groups


def deepmimo(path, M, K, scenario, max_users):
    import deepmimo as dm
    dm.download(scenario)
    d = dm.load(scenario)
    # FACT{DeepMIMO v4 API: the quickstart computes channels with default parameters (8 BS antennas) and
    # exposes `dataset.channels` with shape [n_ue, n_ue_ant, n_bs_ant, n_freq]; verify antenna settings
    # and attribute names against the installed version}.
    try:
        pars = dm.ChannelParameters()
        pars.bs_antenna.shape = np.array([M, 1])
        pars.ue_antenna.shape = np.array([1, 1])
        d.compute_channels(pars)
    except (AttributeError, TypeError):
        d.compute_channels()
    A = np.asarray(getattr(d, 'channels', None) if getattr(d, 'channels', None) is not None else d.channel)
    if A.ndim != 4 or A.shape[1] != 1 or A.shape[2] != M:
        raise ValueError(f'DeepMIMO incompatible channel shape {A.shape}')
    # DeepMIMO gives the row a with y = a x; with the y = h^H x convention h = conj(a).
    Hrow = np.conj(A[:max_users, 0, :, 0])
    good = np.isfinite(Hrow).all(axis=1) & (np.linalg.norm(Hrow, axis=1) > 1e-15)
    Hrow = Hrow[good]
    # Consecutive valid UEs form a K-user tuple and contiguous tuples form a block. These are geographic
    # blocks only if the scenario ordering is spatial: verify against positions before claiming it.
    n_blocks = 12
    N = (len(Hrow) // (K * n_blocks)) * (K * n_blocks)
    if N == 0:
        raise ValueError('not enough valid users')
    H = Hrow[:N].reshape(-1, K, M).transpose(0, 2, 1)
    groups = np.repeat(np.arange(n_blocks), len(H) // n_blocks)
    save(path, H, groups, 'DeepMIMO ' + scenario + '; ordered UE blocks require spatial verification')
    print('EXPORTED', H.shape, 'GROUPS', len(set(groups)), '(set --noise for this dataset explicitly)')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', choices=['synthetic', 'umi_inspired', 'deepmimo'], required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--n', type=int, default=360)
    p.add_argument('--M', type=int, default=8)
    p.add_argument('--K', type=int, default=4)
    p.add_argument('--seed', type=int, default=31)
    p.add_argument('--scenario', default='asu_campus_3p5')
    p.add_argument('--max-users', type=int, default=12000)
    p.add_argument('--bandwidth-hz', type=float, default=20e6, help='umi_inspired noise bandwidth')
    p.add_argument('--nf-db', type=float, default=9., help='umi_inspired receiver noise figure')
    a = p.parse_args()
    if a.M < a.K:
        p.error('need M >= K')
    if a.source == 'deepmimo':
        deepmimo(a.output, a.M, a.K, a.scenario, a.max_users)
    else:
        H, g = synthetic(a.n, a.M, a.K, a.seed, a.source)
        nw = thermal_noise_w(a.bandwidth_hz, a.nf_db) if a.source == 'umi_inspired' else None
        save(a.output, H, g, a.source + ' DEMO ONLY', noise_w=nw)
        print('EXPORTED', H.shape, a.source, '' if nw is None else f'noise_w={nw:.3e} W')


if __name__ == '__main__':
    main()
