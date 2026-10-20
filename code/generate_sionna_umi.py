#!/usr/bin/env python3
"""Generate grouped narrowband MU-MIMO channels with Sionna 3GPP UMi."""

import argparse
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import torch
from sionna.phy import config
from sionna.phy.channel import gen_single_sector_topology
from sionna.phy.channel.tr38901 import PanelArray, UMi


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--M", type=int, default=16)
    parser.add_argument("--K", type=int, default=4)
    parser.add_argument("--groups", type=int, default=30)
    parser.add_argument(
        "--samples-per-group",
        type=int,
        default=25,
    )
    parser.add_argument(
        "--carrier-frequency",
        type=float,
        default=3.5e9,
    )
    parser.add_argument(
        "--sampling-frequency",
        type=float,
        default=15e3,
    )
    parser.add_argument("--isd", type=float, default=200.0)
    parser.add_argument(
        "--min-bs-ut-dist",
        type=float,
        default=10.0,
    )
    parser.add_argument("--bs-height", type=float, default=10.0)
    parser.add_argument("--ut-height", type=float, default=1.5)
    parser.add_argument(
        "--indoor-probability",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--noise-w",
        type=float,
        default=6.324555320336759e-13,
    )
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument(
        "--precision",
        choices=("single", "double"),
        default="double",
    )
    parser.add_argument(
        "--device",
        default=("cuda:0" if torch.cuda.is_available() else "cpu"),
    )
    return parser.parse_args()


def validate_args(args):
    if args.M < args.K or args.K < 1:
        raise ValueError("M must be greater than or equal to K")
    if args.groups < 5:
        raise ValueError("at least five independent groups are required")
    if args.samples_per_group < 1:
        raise ValueError("samples-per-group must be positive")
    if args.carrier_frequency <= 0:
        raise ValueError("carrier-frequency must be positive")
    if args.sampling_frequency <= 0:
        raise ValueError("sampling-frequency must be positive")
    if args.isd <= 2 * args.min_bs_ut_dist:
        raise ValueError("isd must exceed twice min-bs-ut-dist")
    if args.bs_height <= args.ut_height:
        raise ValueError("bs-height must exceed ut-height")
    if not 0 <= args.indoor_probability <= 1:
        raise ValueError("indoor-probability must be in [0,1]")
    if args.noise_w <= 0:
        raise ValueError("noise-w must be positive")
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise ValueError("CUDA requested but unavailable")


def make_arrays(args):
    common = {
        "carrier_frequency": args.carrier_frequency,
        "precision": args.precision,
        "device": args.device,
    }
    bs_array = PanelArray(
        num_rows_per_panel=1,
        num_cols_per_panel=args.M,
        polarization="single",
        polarization_type="V",
        antenna_pattern="38.901",
        element_vertical_spacing=0.5,
        element_horizontal_spacing=0.5,
        **common,
    )
    ut_array = PanelArray(
        num_rows_per_panel=1,
        num_cols_per_panel=1,
        polarization="single",
        polarization_type="V",
        antenna_pattern="omni",
        **common,
    )
    return bs_array, ut_array


def main():
    args = parse_args()
    validate_args(args)

    config.seed = args.seed
    sionna_version = importlib.metadata.version("sionna-no-rt")
    torch_version = torch.__version__

    bs_array, ut_array = make_arrays(args)
    channel_model = UMi(
        carrier_frequency=args.carrier_frequency,
        o2i_model="low",
        ut_array=ut_array,
        bs_array=bs_array,
        direction="downlink",
        enable_pathloss=True,
        enable_shadow_fading=True,
        always_generate_lsp=False,
        precision=args.precision,
        device=args.device,
        spec_version="19.2",
        enable_spatial_consistency=False,
        enable_blockage=False,
    )

    channel_matrices = []
    labels = []
    group_ut_positions = []
    group_bs_positions = []
    group_indoor = []

    for group in range(args.groups):
        topology = gen_single_sector_topology(
            batch_size=1,
            num_ut=args.K,
            scenario="umi",
            min_bs_ut_dist=args.min_bs_ut_dist,
            isd=args.isd,
            bs_height=args.bs_height,
            min_ut_height=args.ut_height,
            max_ut_height=args.ut_height,
            indoor_probability=args.indoor_probability,
            min_ut_velocity=0.0,
            max_ut_velocity=0.0,
            precision=args.precision,
            device=args.device,
        )
        channel_model.set_topology(*topology)

        ut_locations, bs_locations = topology[:2]
        indoor_state = topology[5]
        group_ut_positions.append(
            ut_locations[0].detach().cpu().numpy()
        )
        group_bs_positions.append(
            bs_locations[0, 0].detach().cpu().numpy()
        )
        group_indoor.append(
            indoor_state[0].detach().cpu().numpy()
        )

        for _ in range(args.samples_per_group):
            coefficients, _ = channel_model(
                num_time_samples=1,
                sampling_frequency=args.sampling_frequency,
            )

            expected_prefix = (
                1,
                args.K,
                1,
                1,
                args.M,
            )
            if tuple(coefficients.shape[:5]) != expected_prefix:
                raise RuntimeError(
                    "Unexpected Sionna CIR shape: "
                    f"{tuple(coefficients.shape)}"
                )

            # Sionna downlink coefficients have shape
            # [B, K, RX-ant, BS, TX-ant, path, time]. Summing paths
            # gives the centre-frequency narrowband row a in y=a*x.
            # The experiment stores columns h with y=h^H*x, so h=conj(a).
            row_channel = coefficients[
                0,
                :,
                0,
                0,
                :,
                :,
                0,
            ].sum(dim=-1)
            H = row_channel.conj().transpose(0, 1)
            channel_matrices.append(
                H.detach().cpu().numpy()
            )
            labels.append(group)

        print(
            f"Generated group {group + 1}/{args.groups}",
            flush=True,
        )

    H = np.asarray(channel_matrices, dtype=np.complex128)
    groups = np.asarray(labels, dtype=np.int32)

    expected_shape = (
        args.groups * args.samples_per_group,
        args.M,
        args.K,
    )
    if H.shape != expected_shape:
        raise RuntimeError(
            f"Expected H shape {expected_shape}, got {H.shape}"
        )
    if not np.isfinite(H).all():
        raise RuntimeError("Generated channel contains non-finite values")
    if np.any(np.linalg.norm(H, axis=1) == 0):
        raise RuntimeError("Generated channel contains zero user links")

    metadata = {
        "source": "Sionna 3GPP TR 38.901 UMi",
        "sionna_version": sionna_version,
        "torch_version": torch_version,
        "spec_version": "19.2",
        "scenario": "UMi",
        "direction": "downlink",
        "carrier_frequency_hz": args.carrier_frequency,
        "M": args.M,
        "K": args.K,
        "groups": args.groups,
        "samples_per_group": args.samples_per_group,
        "isd_m": args.isd,
        "min_bs_ut_distance_m": args.min_bs_ut_dist,
        "bs_height_m": args.bs_height,
        "ut_height_m": args.ut_height,
        "indoor_probability": args.indoor_probability,
        "pathloss_enabled": True,
        "shadow_fading_enabled": True,
        "blockage_enabled": False,
        "spatial_consistency_enabled": False,
        "array": "single-polarized 1xM ULA, half-wavelength spacing",
        "narrowband_reduction": (
            "coherent sum of CIR paths at baseband frequency zero"
        ),
        "grouping": (
            "one independent topology and LSP draw per group; "
            "repeated small-scale channel draws within group"
        ),
        "seed": args.seed,
        "precision": args.precision,
        "device": args.device,
        "noise_w": args.noise_w,
    }
    provenance = (
        "Sionna 3GPP TR 38.901 UMi; "
        f"Sionna={sionna_version}; spec=19.2; "
        f"fc={args.carrier_frequency}Hz; M={args.M}; K={args.K}; "
        f"groups={args.groups}; samples_per_group="
        f"{args.samples_per_group}; seed={args.seed}"
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        H=H,
        groups=groups,
        noise_w=np.float64(args.noise_w),
        provenance=np.array(provenance),
        group_ut_positions=np.asarray(
            group_ut_positions,
            dtype=np.float64,
        ),
        group_bs_positions=np.asarray(
            group_bs_positions,
            dtype=np.float64,
        ),
        group_indoor=np.asarray(group_indoor, dtype=np.bool_),
        metadata_json=np.array(json.dumps(metadata, sort_keys=True)),
    )

    powers = np.sum(np.abs(H) ** 2, axis=1)
    print("\nSIONNA EXPORT PASS")
    print("Output:", output.resolve())
    print("H shape:", H.shape)
    print("Groups:", len(np.unique(groups)))
    print("Samples/group:", np.unique(groups, return_counts=True)[1])
    print("Complex:", np.iscomplexobj(H))
    print("Finite:", np.isfinite(H).all())
    print(
        "User channel-power percentiles:",
        np.percentile(
            powers,
            [0, 1, 10, 50, 90, 99, 100],
        ),
    )
    print("Noise [W]:", args.noise_w)
    print("Provenance:", provenance)


if __name__ == "__main__":
    main()
