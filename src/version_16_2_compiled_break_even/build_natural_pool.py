#!/usr/bin/env python3
"""Build an unmeasured, single-ISD Sionna UMi pool for V16 natural prevalence."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import sionna
from sionna.phy import config as sionna_config
from sionna.phy.channel import (
    cir_to_ofdm_channel,
    gen_single_sector_topology,
    subcarrier_frequencies,
)
from sionna.phy.channel.tr38901 import PanelArray, UMi


HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "generation_protocol.json"
POOL = HERE / "natural_pool.npz"
PROVENANCE = HERE / "natural_pool.npz.provenance.json"
CONFIG = {
    "source": "Sionna_3GPP",
    "scenario": "3GPP_TR_38.901_UMi_single_sector_ISD200",
    "spec_version": "19.2",
    "seed": 20261123,
    "n_geometries": 200,
    "users_per_geometry": 8,
    "bs_antennas": 16,
    "carrier_frequency_hz": 3.5e9,
    "inter_site_distance_m": 200.0,
    "minimum_bs_ut_distance_m": 10.0,
    "bs_height_m": 10.0,
    "ut_height_m": 1.5,
    "indoor_probability": 0.0,
    "subcarrier_spacing_hz": 30000.0,
    "selected_baseband_frequency_hz": 0.0,
    "batch_size": 10,
    "sampling": "Sionna uniform random drops in one sector, single ISD; no near/edge strata or channel-based selection",
    "channel_normalization": "none",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["freeze", "build"])
    args = parser.parse_args()
    if args.stage == "freeze":
        if PROTOCOL.exists():
            if json.loads(PROTOCOL.read_text(encoding="utf-8")) != CONFIG:
                raise RuntimeError("Existing generation protocol differs")
        else:
            write_json(PROTOCOL, CONFIG)
        print("GENERATION PROTOCOL FROZEN", PROTOCOL, sha256(PROTOCOL))
        return

    if not PROTOCOL.exists() or json.loads(PROTOCOL.read_text(encoding="utf-8")) != CONFIG:
        raise RuntimeError("Freeze the matching generation protocol first")
    if POOL.exists() or PROVENANCE.exists():
        raise RuntimeError("Pool or provenance already exists; refusing to overwrite")

    torch.manual_seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])
    sionna_config.seed = CONFIG["seed"]
    bs_array = PanelArray(16, 1, "single", "V", "38.901", CONFIG["carrier_frequency_hz"])
    ut_array = PanelArray(1, 1, "single", "V", "omni", CONFIG["carrier_frequency_hz"])
    model = UMi(
        carrier_frequency=CONFIG["carrier_frequency_hz"],
        o2i_model="low",
        ut_array=ut_array,
        bs_array=bs_array,
        direction="downlink",
        enable_pathloss=True,
        enable_shadow_fading=True,
        enable_spatial_consistency=True,
        enable_blockage=False,
        spec_version=CONFIG["spec_version"],
        device="cpu",
    )
    frequencies = subcarrier_frequencies(1, CONFIG["subcarrier_spacing_hz"], device="cpu")
    channels, positions = [], []
    for start in range(0, CONFIG["n_geometries"], CONFIG["batch_size"]):
        count = min(CONFIG["batch_size"], CONFIG["n_geometries"] - start)
        topology = gen_single_sector_topology(
            batch_size=count,
            num_ut=CONFIG["users_per_geometry"],
            scenario="umi",
            min_bs_ut_dist=CONFIG["minimum_bs_ut_distance_m"],
            isd=CONFIG["inter_site_distance_m"],
            bs_height=CONFIG["bs_height_m"],
            min_ut_height=CONFIG["ut_height_m"],
            max_ut_height=CONFIG["ut_height_m"],
            indoor_probability=CONFIG["indoor_probability"],
            min_ut_velocity=0.0,
            max_ut_velocity=0.0,
            device="cpu",
        )
        model.set_topology(*topology)
        a, tau = model(num_time_samples=1, sampling_frequency=CONFIG["subcarrier_spacing_hz"])
        h = cir_to_ofdm_channel(frequencies, a, tau, normalize=False)
        # Sionna: [drop, user, user_ant, BS, BS_ant, subcarrier, time].
        channel = h[:, :, 0, 0, :, 0, 0].transpose(1, 2).detach().cpu().numpy()
        channels.append(channel)
        positions.append(topology[0].detach().cpu().numpy())
        print(f"Generated {start + count}/{CONFIG['n_geometries']}", flush=True)

    H = np.concatenate(channels).astype(np.complex64)
    xyz = np.concatenate(positions).astype(np.float32)
    if H.shape != (200, 16, 8) or not np.isfinite(H).all() or np.all(H == 0):
        raise RuntimeError("Invalid channel pool")
    if xyz.shape != (200, 8, 3) or not np.isfinite(xyz).all():
        raise RuntimeError("Invalid topology")
    groups = np.array([f"GPP_UMI200_{i:04d}" for i in range(len(H))])
    scenario = np.full(len(H), CONFIG["scenario"])
    np.savez_compressed(POOL, H=H, groups=groups, xyz=xyz, scenario=scenario)
    provenance = {
        **CONFIG,
        "prior_use": "never_seen",
        "split": "natural_prevalence_pool",
        "group_definition": "One independent topology drop with eight users per group",
        "generation_protocol_sha256": sha256(PROTOCOL),
        "generation_code_sha256": sha256(Path(__file__)),
        "dataset_sha256": sha256(POOL),
        "dataset_shape": list(H.shape),
        "dataset_dtype": str(H.dtype),
        "n_groups": len(groups),
        "sionna_version": sionna.__version__,
        "torch_version": torch.__version__,
        "statistical_independence_verified": False,
    }
    write_json(PROVENANCE, provenance)
    print("POOL BUILD PASS", POOL)
    print("Dataset SHA256:", provenance["dataset_sha256"])
    print("Provenance:", PROVENANCE)


if __name__ == "__main__":
    main()
