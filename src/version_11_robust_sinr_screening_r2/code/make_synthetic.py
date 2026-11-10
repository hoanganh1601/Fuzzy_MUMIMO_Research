#!/usr/bin/env python3
"""SYNTHETIC clustered multipath channels for pipeline rehearsal ONLY.

This is NOT DeepMIMO and NOT 3GPP TR 38.901. It exists so the complete A-D
pipeline can be executed end to end when the ray-tracing data are unavailable.
Numbers obtained on it must never be reported as DeepMIMO/3GPP results.

Model: base station with an M-element half-wavelength ULA. Each spatial block
(group) has a centre azimuth and distance; the K users of a drop are placed inside
the block with a block-specific angular spread (small spread -> highly correlated
users). Each user channel is a sum of P paths with Laplacian angular offsets and
complex Gaussian gains, scaled by a log-distance path loss with log-normal shadowing.
"""
import argparse, json
from pathlib import Path
import numpy as np
from reference_model import utf8_console


def steering(M, theta):
    return np.exp(1j * np.pi * np.arange(M)[:, None] * np.sin(theta)[None, :])


def generate(n_groups, drops, M, K, seed, paths=6, path_spread_deg=3.0):
    rng = np.random.default_rng(seed)
    H = np.empty((n_groups * drops, M, K), complex); groups = []; xyz = []
    for g in range(n_groups):
        centre = rng.uniform(-60, 60) * np.pi / 180
        dist = rng.uniform(40, 250)
        user_spread = rng.choice([1.0, 3.0, 8.0, 20.0]) * np.pi / 180  # mix of correlated and separated users
        for d in range(drops):
            idx = g * drops + d
            for k in range(K):
                th = centre + rng.uniform(-user_spread, user_spread)
                r = dist * rng.uniform(0.8, 1.2)
                pl_db = 32.4 + 35.0 * np.log10(r) + rng.normal(0, 4.0)
                offs = th + rng.laplace(0, path_spread_deg * np.pi / 180 / np.sqrt(2), size=paths)
                gains = (rng.normal(size=paths) + 1j * rng.normal(size=paths)) / np.sqrt(2 * paths)
                H[idx, :, k] = np.sqrt(10 ** (-pl_db / 10)) * steering(M, offs) @ gains
            groups.append(g); xyz.append([dist * np.cos(centre), dist * np.sin(centre), 0.0])
    return H, np.array(groups), np.array(xyz)


def main():
    utf8_console()
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--groups', type=int, default=32); ap.add_argument('--drops', type=int, default=5)
    ap.add_argument('--M', type=int, default=16); ap.add_argument('--label', default='SYNTHETIC_REHEARSAL')
    ap.add_argument('--provenance', default='')
    a = ap.parse_args()
    H, groups, xyz = generate(a.groups, a.drops, a.M, 4, a.seed)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, H=H, groups=groups, xyz=xyz, scenario=np.array([a.label] * len(H)))
    if a.provenance:
        Path(a.provenance).write_text(encoding='utf8',data=json.dumps(dict(
            source='other_independent', scenario=f'{a.label} seed={a.seed}',
            split='new_independent_test',
            generation_method='code/make_synthetic.py clustered ULA multipath; NOT DeepMIMO/3GPP',
            independence_basis='Different generator seed drawn after protocol lock; rehearsal only, no physical independence claim',
            channel_units='Complex baseband gain incl. log-distance path loss (35 dB/decade) and 4 dB shadowing',
            group_definition='One spatial block per group (centre azimuth, distance, user spread)',
            created_before_test=True), indent=1))
    print(out, H.shape, 'groups', len(np.unique(groups)))


if __name__ == '__main__': main()
