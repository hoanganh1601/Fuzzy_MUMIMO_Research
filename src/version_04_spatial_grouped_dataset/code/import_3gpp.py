"""Strict adapter for independently generated 3GPP TR 38.901 complex channel tensors.
Generate H_true with an actual compliant simulator; this adapter does not simulate 3GPP.
Convention: column k of H[n] is h_k with y_k = h_k^H x (conjugate a y = a x export first).
"""
import argparse
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--M', type=int, default=8)
    p.add_argument('--K', type=int, default=4)
    p.add_argument('--source-note', required=True)
    p.add_argument('--noise-w', type=float, default=None, help='receiver noise power [W] matching the export')
    a = p.parse_args()
    x = np.load(a.input, allow_pickle=False)
    if 'H' not in x or 'groups' not in x:
        raise ValueError('3GPP export must include H[N,M,K] and disjoint scenario groups[N]')
    H, g = x['H'], x['groups']
    if H.ndim != 3 or H.shape[1:] != (a.M, a.K) or not np.iscomplexobj(H):
        raise ValueError('wrong 3GPP channel shape or dtype')
    if g.ndim != 1 or len(g) != len(H) or len(np.unique(g)) < 5:
        raise ValueError('need groups[N] with at least five independently grouped channel blocks')
    if not np.isfinite(H).all():
        raise ValueError('non-finite channels')
    if np.any(np.linalg.norm(H, axis=1) == 0):
        raise ValueError('zero user channel present')
    if '3GPP' not in a.source_note and '38.901' not in a.source_note:
        raise ValueError('source note must identify the model (3GPP / 38.901)')
    if a.noise_w is not None and a.noise_w <= 0:
        raise ValueError('--noise-w must be > 0')
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    extra = {} if a.noise_w is None else dict(noise_w=np.float64(a.noise_w))
    np.savez_compressed(a.output, H=H.astype(np.complex128), groups=g, provenance=np.array(a.source_note), **extra)
    print('3GPP IMPORT PASS', H.shape, 'groups', len(np.unique(g)))


if __name__ == '__main__':
    main()
