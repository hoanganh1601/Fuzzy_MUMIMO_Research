#!/usr/bin/env python3
"""SYNTHETIC 8-user drops for smoke tests and pipeline rehearsal ONLY.
NOT DeepMIMO, NOT 3GPP: numbers obtained on these files must never be reported.

Clustered ULA multipath: one drop per group; users of a drop share a centre
azimuth/distance with a drop-specific angular spread; log-distance path loss
(35 dB/decade) with 4 dB shadowing. A fraction of drops is placed at the cell
edge (--edge-fraction) so that both interference-limited and power-limited
channel conditions occur.
"""
import argparse, json
from pathlib import Path
import numpy as np


def steering(M, theta):
    return np.exp(1j * np.pi * np.arange(M)[:, None] * np.sin(theta)[None, :])


def drop(rng, M, K, dmin, dmax):
    centre = rng.uniform(-60, 60) * np.pi / 180; dist = rng.uniform(dmin, dmax)
    spread = rng.choice([1., 3., 8., 20.]) * np.pi / 180; H = np.empty((M, K), complex)
    for k in range(K):
        th = centre + rng.uniform(-spread, spread); r = dist * rng.uniform(.8, 1.2)
        pl = 32.4 + 35 * np.log10(r) + rng.normal(0, 4)
        offs = th + rng.laplace(0, 3 * np.pi / 180 / np.sqrt(2), size=6)
        gains = (rng.normal(size=6) + 1j * rng.normal(size=6)) / np.sqrt(12)
        H[:, k] = np.sqrt(10**(-pl / 10)) * steering(M, offs) @ gains
    return H


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True); p.add_argument('--n', type=int, default=24)
    p.add_argument('--seed', type=int, default=123); p.add_argument('--prefix', default='DEV')
    p.add_argument('--m', type=int, default=16); p.add_argument('--k', type=int, default=8)
    p.add_argument('--edge-fraction', type=float, default=.5)
    p.add_argument('--near', default='40,250'); p.add_argument('--edge', default='300,1200')
    p.add_argument('--prior-use', default='smoke')
    a = p.parse_args()
    if a.m < 8 or a.k < 8: raise ValueError('Need M>=8 and K>=8')
    rng = np.random.default_rng(a.seed); near = [float(x) for x in a.near.split(',')]; edge = [float(x) for x in a.edge.split(',')]
    H = []; G = []
    for i in range(a.n):
        lo, hi = edge if rng.uniform() < a.edge_fraction else near
        H.append(drop(rng, a.m, a.k, lo, hi)); G.append(f'{a.prefix}_{i:05d}')
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.output, H=np.asarray(H), groups=np.asarray(G), scenario=np.array('SYNTHETIC_ONLY'))
    Path(a.output + '.provenance.json').write_text(json.dumps({
        'source': 'synthetic_' + a.prefix.lower(), 'scenario': 'SYNTHETIC_ONLY clustered ULA, NOT DeepMIMO/3GPP',
        'group_definition': 'one drop per group', 'independence_basis': f'independent PRNG stream, seed {a.seed}',
        'prior_use': a.prior_use, 'edge_fraction': a.edge_fraction}, indent=2), encoding='utf8')
    print(a.output, np.asarray(H).shape)


if __name__ == '__main__': main()
