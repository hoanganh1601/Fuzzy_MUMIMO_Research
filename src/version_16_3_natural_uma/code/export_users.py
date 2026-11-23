#!/usr/bin/env python3
"""Convert an exported channel file (DeepMIMO or Sionna, .npz or .mat) into the
per-user narrowband format required by pack_deepmimo_users.py:
    user_channels (U, M) complex,  user_positions (U, 3) float.

No assumption is made about the simulator version: first inspect the file, then
state the axis order explicitly.

  python code/export_users.py --input raw.npz --inspect
  python code/export_users.py --input raw.npz --output users.npz \
      --channel-key channel --pos-key rx_pos --layout u,rx,tx,sc --rx 0 --sc 0

--layout names every axis of the channel array: u = user, tx = base-station
antenna (becomes M), rx = user antenna (one index kept, --rx), sc = subcarrier or
time/path sample (one index kept, --sc). Missing axes are simply omitted.
Path loss is kept (no normalization): the noise power of the experiment refers
to these absolute gains. Record every choice in the provenance file.
"""
import argparse, json
from pathlib import Path
import numpy as np


def load(path):
    if path.lower().endswith('.mat'):
        from scipy.io import loadmat
        d = loadmat(path); return {k: v for k, v in d.items() if not k.startswith('__')}
    with np.load(path, allow_pickle=False) as f: return {k: f[k] for k in f.files}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', required=True); p.add_argument('--output', default='')
    p.add_argument('--inspect', action='store_true')
    p.add_argument('--channel-key', default='channel'); p.add_argument('--pos-key', default='rx_pos')
    p.add_argument('--layout', default='u,rx,tx,sc'); p.add_argument('--rx', type=int, default=0); p.add_argument('--sc', type=int, default=0)
    a = p.parse_args(); d = load(a.input)
    if a.inspect:
        for k, v in d.items():
            v = np.asarray(v); print(f'{k:24s} shape={v.shape} dtype={v.dtype}')
        return
    if not a.output: raise ValueError('--output required')
    h = np.asarray(d[a.channel_key]); axes = a.layout.split(',')
    if h.ndim != len(axes) or 'u' not in axes or 'tx' not in axes: raise ValueError(f'layout {axes} does not match channel shape {h.shape}')
    idx = tuple({'rx': a.rx, 'sc': a.sc}.get(ax, slice(None)) if ax not in ('u', 'tx') else slice(None) for ax in axes)
    h = h[idx]; kept = [ax for ax in axes if ax in ('u', 'tx')]
    if kept != ['u', 'tx']: h = h.T
    pos = np.asarray(d[a.pos_key], dtype=float)
    if pos.shape[0] != h.shape[0] and pos.shape[-1] == h.shape[0]: pos = pos.T
    if pos.shape[1] == 2: pos = np.c_[pos, np.zeros(len(pos))]
    if not np.iscomplexobj(h): raise ValueError('channel must be complex')
    ok = np.isfinite(h).all(axis=1) & np.isfinite(pos).all(axis=1) & (np.linalg.norm(h, axis=1) > 0)
    h, pos = h[ok], pos[ok, :3]
    np.savez_compressed(a.output, user_channels=h.astype(complex), user_positions=pos)
    info = {'input': str(Path(a.input).name), 'channel_key': a.channel_key, 'layout': a.layout, 'rx_index': a.rx,
            'sc_index': a.sc, 'users_kept': int(ok.sum()), 'users_dropped_inactive_or_nonfinite': int((~ok).sum()), 'M': int(h.shape[1]),
            'gain_db_median': float(np.median(20 * np.log10(np.linalg.norm(h, axis=1))))}
    Path(a.output + '.export.json').write_text(json.dumps(info, indent=2), encoding='utf8')
    print(json.dumps(info, indent=2))


if __name__ == '__main__': main()
