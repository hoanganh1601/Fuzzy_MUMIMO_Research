#!/usr/bin/env python3
"""Generate the three frozen Sionna TR 38.901 UMi datasets used by V15.1--V16.

Modes
-----
``v151``
    Fifteen single-sector UMi drops used as the V15.1 3GPP test set.
``near-edge``
    The V15.2 selection pool: 60 near drops and 60 edge drops.
``natural``
    Two hundred unstratified single-ISD UMi drops used by V16.

Every mode has two stages.  ``freeze`` writes (or verifies) the immutable
protocol JSON.  ``build`` refuses to run unless that protocol exactly matches
the preset recovered from the original run.  Channel matrices are never
normalized and are written as ``H[geometry, bs_antenna, user]`` complex64.

Examples
--------
python gen_sionna_umi.py --mode v151 --stage freeze --protocol v151.json
python gen_sionna_umi.py --mode v151 --stage build --protocol v151.json \
    --output v151_3gpp_test.npz --audit-output v151_topology_audit.npz
"""

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


COMMON = {
    "source": "Sionna_3GPP",
    "standard": "3GPP TR 38.901",
    "spec_version": "19.2",
    "carrier_frequency_hz": 3.5e9,
    "users_per_geometry": 8,
    "bs_antennas": 16,
    "ut_antennas": 1,
    "bs_height_m": 10.0,
    "ut_height_m": 1.5,
    "indoor_probability": 0.0,
    "subcarrier_spacing_hz": 30000.0,
    "selected_baseband_frequency_hz": 0.0,
    "channel_normalization": "none",
    "direction": "downlink",
    "o2i_model": "low",
    "enable_pathloss": True,
    "enable_shadow_fading": True,
    "enable_spatial_consistency": True,
    "enable_blockage": False,
}


PRESETS = {
    "v151": {
        **COMMON,
        "name": "V15.1_3GPP_UMi_test",
        "seed": 20261119,
        "n_geometries": 15,
        "inter_site_distance_m": 200.0,
        "minimum_bs_ut_distance_m": 10.0,
        "batch_size": 15,
        "ut_antenna_pattern": "38.901",
        "group_prefix": "GPP_UMI",
        "scenario_label": "Sionna_3GPP_UMi_3p5GHz",
        "prior_use": "never_seen",
    },
    "near-edge": {
        **COMMON,
        "name": "V15.2_3GPP_UMi_near_edge_pool",
        "n_geometries": 120,
        "batch_size": 60,
        "ut_antenna_pattern": "38.901",
        "scenario_label": "Sionna_3GPP_UMi_V152",
        "prior_use": "never_seen",
        "v152_lock_sha256": "d5aa76d1d09071c3aae5a297a47feca72693c72619a7971c804c6e0bb286a8f6",
        "strata": [
            {
                "name": "near",
                "seed": 20261120,
                "n_geometries": 60,
                "inter_site_distance_m": 200.0,
                "minimum_bs_ut_distance_m": 10.0,
            },
            {
                "name": "edge",
                "seed": 20261121,
                "n_geometries": 60,
                "inter_site_distance_m": 1000.0,
                "minimum_bs_ut_distance_m": 100.0,
            },
        ],
    },
    "natural": {
        **COMMON,
        "name": "V16_natural_UMi_ISD200_pool",
        "seed": 20261123,
        "n_geometries": 200,
        "inter_site_distance_m": 200.0,
        "minimum_bs_ut_distance_m": 10.0,
        "batch_size": 10,
        "ut_antenna_pattern": "omni",
        "group_prefix": "GPP_UMI200",
        "scenario_label": "3GPP_TR_38.901_UMi_single_sector_ISD200",
        "sampling": (
            "Sionna uniform random drops in one sector, single ISD; "
            "no near/edge strata or channel-based selection"
        ),
        "prior_use": "never_seen",
    },
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_npz(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, **values)
    temporary.replace(path)


def arrays(protocol):
    frequency = float(protocol["carrier_frequency_hz"])
    user_array = PanelArray(
        num_rows_per_panel=1,
        num_cols_per_panel=1,
        polarization="single",
        polarization_type="V",
        antenna_pattern=protocol["ut_antenna_pattern"],
        carrier_frequency=frequency,
        precision="single",
        device="cpu",
    )
    # The historical natural-pool generator used a 16x1 vertical panel,
    # whereas the V15.1 and near/edge generators used a 1x16 horizontal
    # panel.  Preserve that distinction: it changes the channel coefficients.
    if protocol["name"] == "V16_natural_UMi_ISD200_pool":
        base_array = PanelArray(
            num_rows_per_panel=16,
            num_cols_per_panel=1,
            polarization="single",
            polarization_type="V",
            antenna_pattern="38.901",
            carrier_frequency=frequency,
            precision="single",
            device="cpu",
        )
    else:
        base_array = PanelArray(
            num_rows_per_panel=1,
            num_cols_per_panel=16,
            polarization="single",
            polarization_type="V",
            antenna_pattern="38.901",
            carrier_frequency=frequency,
            element_horizontal_spacing=0.5,
            precision="single",
            device="cpu",
        )
    if user_array.num_ant != 1 or base_array.num_ant != 16:
        raise RuntimeError("Unexpected antenna configuration")
    return user_array, base_array


def generate_part(protocol, part):
    seed = int(part["seed"])
    count = int(part["n_geometries"])
    batch_size = min(int(protocol["batch_size"]), count)
    np.random.seed(seed)
    torch.manual_seed(seed)
    sionna_config.seed = seed

    user_array, base_array = arrays(protocol)
    model = UMi(
        carrier_frequency=float(protocol["carrier_frequency_hz"]),
        o2i_model=protocol["o2i_model"],
        ut_array=user_array,
        bs_array=base_array,
        direction=protocol["direction"],
        enable_pathloss=bool(protocol["enable_pathloss"]),
        enable_shadow_fading=bool(protocol["enable_shadow_fading"]),
        enable_spatial_consistency=bool(protocol["enable_spatial_consistency"]),
        enable_blockage=bool(protocol["enable_blockage"]),
        spec_version=protocol["spec_version"],
        precision="single",
        device="cpu",
    )
    frequencies = subcarrier_frequencies(
        num_subcarriers=1,
        subcarrier_spacing=float(protocol["subcarrier_spacing_hz"]),
        precision="single",
        device="cpu",
    )

    channels, audit = [], {
        "ut_locations_m": [],
        "bs_locations_m": [],
        "ut_orientations_rad": [],
        "bs_orientations_rad": [],
        "ut_velocities_mps": [],
        "indoor_state": [],
        "path_delays_s": [],
    }
    completed = 0
    while completed < count:
        current = min(batch_size, count - completed)
        topology = gen_single_sector_topology(
            batch_size=current,
            num_ut=int(protocol["users_per_geometry"]),
            scenario="umi",
            min_bs_ut_dist=float(part["minimum_bs_ut_distance_m"]),
            isd=float(part["inter_site_distance_m"]),
            bs_height=float(protocol["bs_height_m"]),
            min_ut_height=float(protocol["ut_height_m"]),
            max_ut_height=float(protocol["ut_height_m"]),
            indoor_probability=float(protocol["indoor_probability"]),
            min_ut_velocity=0.0,
            max_ut_velocity=0.0,
            precision="single",
            device="cpu",
        )
        model.set_topology(*topology)
        coefficients, delays = model(
            num_time_samples=1,
            sampling_frequency=float(protocol["subcarrier_spacing_hz"]),
        )
        frequency_response = cir_to_ofdm_channel(
            frequencies, coefficients, delays, normalize=False
        )
        channel = (
            frequency_response[:, :, 0, 0, :, 0, 0]
            .permute(0, 2, 1)
            .detach()
            .cpu()
            .numpy()
            .astype(np.complex64, copy=False)
        )
        expected = (current, 16, int(protocol["users_per_geometry"]))
        if channel.shape != expected:
            raise RuntimeError(f"Unexpected channel shape {channel.shape}; expected {expected}")
        if not np.isfinite(channel).all() or np.any(np.linalg.norm(channel, axis=1) == 0):
            raise RuntimeError("Non-finite or zero channel vector")
        channels.append(channel)
        for key, tensor in zip(list(audit)[:-1], topology):
            audit[key].append(tensor.detach().cpu().numpy())
        audit["path_delays_s"].append(delays.detach().cpu().numpy())
        completed += current
        print(f"  generated {completed}/{count}", flush=True)

    return np.concatenate(channels), {
        key: np.concatenate(values) for key, values in audit.items()
    }


def build(mode, protocol, output, audit_output):
    if mode == "near-edge":
        parts = protocol["strata"]
    else:
        parts = [
            {
                "name": mode,
                "seed": protocol["seed"],
                "n_geometries": protocol["n_geometries"],
                "inter_site_distance_m": protocol["inter_site_distance_m"],
                "minimum_bs_ut_distance_m": protocol["minimum_bs_ut_distance_m"],
            }
        ]

    all_channels, all_audit, labels = [], [], []
    for part in parts:
        print(
            f"Generating {part['name']}: n={part['n_geometries']}, "
            f"ISD={part['inter_site_distance_m']} m, "
            f"min_dist={part['minimum_bs_ut_distance_m']} m"
        )
        channel, audit = generate_part(protocol, part)
        all_channels.append(channel)
        all_audit.append(audit)
        labels.extend([part["name"]] * len(channel))

    channel = np.concatenate(all_channels).astype(np.complex64, copy=False)
    expected = (int(protocol["n_geometries"]), 16, int(protocol["users_per_geometry"]))
    if channel.shape != expected:
        raise RuntimeError(f"Pool shape {channel.shape}; expected {expected}")

    if mode == "near-edge":
        groups = np.asarray(
            [
                f"GPP_{part['name'].upper()}_{index:04d}"
                for part in parts
                for index in range(int(part["n_geometries"]))
            ],
            dtype="U64",
        )
        values = {
            "H": channel,
            "groups": groups,
            "stratum": np.asarray(labels, dtype="U16"),
            "xyz": np.concatenate([item["ut_locations_m"] for item in all_audit]),
            "scenario": np.full(len(channel), protocol["scenario_label"], dtype="U64"),
        }
    else:
        group_values = [
            f"{protocol['group_prefix']}_{index:04d}" for index in range(len(channel))
        ]
        # V16 natural used NumPy's minimal-width string dtype; V15.1 used U64.
        groups = (
            np.asarray(group_values)
            if mode == "natural"
            else np.asarray(group_values, dtype="U64")
        )
        scenario = (
            np.full(len(channel), protocol["scenario_label"])
            if mode == "natural"
            else np.full(len(channel), protocol["scenario_label"], dtype="U64")
        )
        values = {
            "H": channel,
            "groups": groups,
            "xyz": np.concatenate([item["ut_locations_m"] for item in all_audit]),
            "scenario": scenario,
        }
    write_npz(output, values)

    if audit_output:
        combined = {
            key: np.concatenate([item[key] for item in all_audit])
            for key in all_audit[0]
        }
        combined["groups"] = groups
        if mode == "near-edge":
            combined["stratum"] = np.asarray(labels, dtype="U16")
        write_npz(audit_output, combined)

    provenance = {
        **protocol,
        "generator_mode": mode,
        "dataset_sha256": sha256(output),
        "dataset_shape": list(channel.shape),
        "dataset_dtype": str(channel.dtype),
        "n_groups": int(len(np.unique(groups))),
        "generation_code_sha256": sha256(Path(__file__).resolve()),
        "sionna_version": sionna.__version__,
        "torch_version": torch.__version__,
        "statistical_independence_verified": False,
    }
    write_json(str(output) + ".provenance.json", provenance)
    print("SIONNA UMI BUILD PASS")
    print("Mode:", mode)
    print("H shape:", channel.shape)
    print("H dtype:", channel.dtype)
    print("Dataset:", Path(output).resolve())
    print("Dataset SHA256:", provenance["dataset_sha256"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", required=True, choices=sorted(PRESETS))
    parser.add_argument("--stage", required=True, choices=("freeze", "build"))
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--output")
    parser.add_argument("--audit-output")
    args = parser.parse_args()

    protocol_path = Path(args.protocol)
    preset = PRESETS[args.mode]
    if args.stage == "freeze":
        if protocol_path.exists():
            existing = json.loads(protocol_path.read_text(encoding="utf-8"))
            if existing != preset:
                raise RuntimeError("Existing protocol differs from the frozen preset")
        else:
            protocol_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(protocol_path, preset)
        print("SIONNA UMI PROTOCOL FROZEN")
        print("Mode:", args.mode)
        print("Protocol:", protocol_path.resolve())
        print("SHA256:", sha256(protocol_path))
        return

    if not args.output:
        parser.error("--output is required for --stage build")
    if not protocol_path.is_file():
        raise FileNotFoundError("Freeze the protocol before building")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol != preset:
        raise RuntimeError("Protocol does not match the frozen preset")
    if Path(args.output).exists() or Path(str(args.output) + ".provenance.json").exists():
        raise FileExistsError("Output or provenance already exists; refusing to overwrite")
    if args.audit_output and Path(args.audit_output).exists():
        raise FileExistsError("Audit output already exists; refusing to overwrite")
    build(args.mode, protocol, args.output, args.audit_output)


if __name__ == "__main__":
    main()
