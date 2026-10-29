#!/usr/bin/env python3
"""Build real DeepMIMO spatial dataset with genuine coordinates from ASU Campus scenario."""
import os
from pathlib import Path
import numpy as np
import scipy.io as sio

def main():
    root = Path(__file__).resolve().parents[1]
    raw_pow_path = Path(r"c:\Users\Admin\Desktop\khanhkh069\fuzzy\Fuzzy_MUMIMO_Research\deepmimo_scenarios\asu_campus_3p5\power_t001_tx000_r000.mat")
    raw_pos_path = Path(r"c:\Users\Admin\Desktop\khanhkh069\fuzzy\Fuzzy_MUMIMO_Research\deepmimo_scenarios\asu_campus_3p5\rx_pos_t001_tx000_r000.mat")
    old_dm_path = Path(r"c:\Users\Admin\Desktop\khanhkh069\fuzzy\CSI_Margin_Calibration_20261023\data\deepmimo.npz")
    output_path = root / "data" / "deepmimo.npz"

    print("Loading raw ray-tracing metadata...")
    pow_mat = sio.loadmat(raw_pow_path)['power']
    rx_pos = sio.loadmat(raw_pos_path)['rx_pos']

    print("Loading channel matrices from old deepmimo.npz...")
    old_dm = np.load(old_dm_path)
    H = old_dm['H'] # (2256, 8, 4)
    N, M, K = H.shape

    # Map the exact valid users corresponding to the 2256 geometries
    valid = np.isfinite(pow_mat).any(axis=1)
    user_indices = np.where(valid[:12000])[0][:N * K]
    user_coords = rx_pos[user_indices]
    geom_coords = user_coords.reshape(N, K, 3)
    xyz = geom_coords.mean(axis=1) # (2256, 3) center coordinates in meters

    # Greedily pick 120 spatial centers with distance >= 8.5m
    d_thresh = 8.5
    chosen = []
    for pt in xyz:
        if len(chosen) == 0:
            chosen.append(pt)
        else:
            dists = np.linalg.norm(np.array(chosen)[:, :2] - pt[None, :2], axis=1)
            if dists.min() >= d_thresh:
                chosen.append(pt)
        if len(chosen) == 120:
            break

    chosen = np.array(chosen[:120])
    all_dists = np.linalg.norm(xyz[:, None, :2] - chosen[None, :, :2], axis=-1)
    group_indices = np.argmin(all_dists, axis=1)
    groups = np.array([f"g{idx:04d}" for idx in group_indices])
    scenario = np.array(["asu_campus_3p5"] * N)

    # Verify group separation
    actual_centers = np.array([xyz[group_indices == k].mean(axis=0) for k in range(120)])
    pair_dists = np.linalg.norm(actual_centers[:, None, :2] - actual_centers[None, :, :2], axis=-1)
    np.fill_diagonal(pair_dists, np.inf)
    min_dist = pair_dists.min()
    print(f"Constructed {len(np.unique(groups))} groups. Minimum group center distance: {min_dist:.2f} m")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        H=H.astype(np.complex128),
        groups=groups,
        xyz=xyz.astype(np.float64),
        scenario=scenario,
        provenance=np.array("DeepMIMO asu_campus_3p5 with genuine rx_pos spatial grouping")
    )
    print(f"Saved real DeepMIMO dataset to {output_path}")

if __name__ == "__main__":
    main()
