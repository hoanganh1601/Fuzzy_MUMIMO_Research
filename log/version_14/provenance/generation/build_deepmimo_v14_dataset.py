"""Build the locked DeepMIMO V14 Denver channel test dataset."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import deepmimo as dm
import numpy as np


ROOT = Path(__file__).resolve().parent
SCENARIO = "city_18_denver_3p5"
SELECTION = ROOT / "deepmimo_v14_selection.npz"
SELECTION_PROTOCOL = ROOT / "deepmimo_v14_selection_protocol.json"
OUTPUT = ROOT / "deepmimo_v14_test.npz"
PROVENANCE_OUTPUT = ROOT / "deepmimo_v14_test_provenance.json"
LOCK_FILE = ROOT / "locks" / "CP03_locked_rule_DM_ASU35_20261117.json"

EXPECTED_LOCK_SHA256 = "19259a0cc12b86160169a46b90f8e99140171c11d7e5549305dbdd5c16020567"
EXPECTED_SELECTION_SHA256 = "a943bd266407e7fbcc52f2ab7301b94c64e9ef75842807781985746d49872fd2"
EXPECTED_PROTOCOL_SHA256 = "41a887fd41fd5c9ea28d62a69a446beee362a22609b2b13f7729dadc046941b2"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUTPUT.exists() or PROVENANCE_OUTPUT.exists():
        raise SystemExit("Locked V14 test dataset already exists; refusing to overwrite")
    if digest(LOCK_FILE) != EXPECTED_LOCK_SHA256:
        raise SystemExit("CP03 lock hash mismatch")
    if digest(SELECTION) != EXPECTED_SELECTION_SHA256:
        raise SystemExit("Selection hash mismatch")
    if digest(SELECTION_PROTOCOL) != EXPECTED_PROTOCOL_SHA256:
        raise SystemExit("Selection protocol hash mismatch")

    with np.load(SELECTION, allow_pickle=False) as selected:
        ue_indices = np.asarray(selected["ue_indices"], dtype=np.int64)
        groups = np.asarray(selected["groups"])
        centers = np.asarray(selected["centers"], dtype=np.float64)
        user_xyz = np.asarray(selected["user_xyz"], dtype=np.float64)

    n_geometries = len(ue_indices)
    if ue_indices.shape != (92, 4):
        raise SystemExit(f"Invalid locked selection shape {ue_indices.shape}")
    if len(np.unique(ue_indices)) != n_geometries * 4:
        raise SystemExit("UE reuse detected in locked selection")
    if len(np.unique(groups)) != 23:
        raise SystemExit("Expected 23 locked spatial groups")

    flat_indices = ue_indices.reshape(-1)
    dataset = dm.load(
        SCENARIO,
        max_paths=10,
        tx_sets={3: [0]},
        rx_sets={0: flat_indices},
        matrices=[
            "power", "phase", "delay", "aoa_az", "aoa_el",
            "aod_az", "aod_el", "rx_pos", "tx_pos",
        ],
    )

    loaded_xyz = np.asarray(dataset.rx_pos, dtype=np.float64).reshape(
        n_geometries, 4, 3
    )
    if not np.allclose(loaded_xyz, user_xyz, rtol=0.0, atol=1e-9):
        raise SystemExit("Loaded UE order or coordinates do not match locked selection")

    channel_parameters = dm.ChannelParameters(
        bs_antenna={"shape": [16, 1], "spacing": 0.5},
        ue_antenna={"shape": [1, 1], "spacing": 0.5},
        num_paths=10,
        freq_domain=1,
        doppler=0,
        ofdm={
            "bandwidth": 10_000_000.0,
            "subcarriers": 512,
            "selected_subcarriers": [0],
            "rx_filter": 0,
        },
    )
    raw_channel = np.asarray(dataset.compute_channels(channel_parameters))
    expected_raw_shape = (n_geometries * 4, 1, 16, 1)
    if raw_channel.shape != expected_raw_shape:
        raise SystemExit(
            f"Unexpected raw channel shape {raw_channel.shape}; "
            f"expected {expected_raw_shape}"
        )

    h = raw_channel[:, 0, :, 0].reshape(n_geometries, 4, 16).transpose(0, 2, 1)
    h = np.asarray(h, dtype=np.complex64)
    if h.shape != (n_geometries, 16, 4) or not np.isfinite(h).all():
        raise SystemExit("Invalid final H matrix")
    if np.any(np.linalg.norm(h, axis=1) == 0):
        raise SystemExit("At least one selected user has zero channel norm")

    np.savez_compressed(
        OUTPUT,
        H=h,
        groups=groups,
        xyz=centers,
        scenario=np.full(n_geometries, SCENARIO),
    )

    provenance = {
        "source": "DeepMIMO 4.0.5",
        "scenario": SCENARIO,
        "split": "new_independent_test",
        "prior_use": "never_seen",
        "created_after_rule_lock": True,
        "group_definition": "23 fixed 25 m spatial grid cells; four geometries per cell; four users per geometry; 368 unique UEs without reuse",
        "independence_basis": "Denver city_18_denver_3p5 is a newly downloaded ray-tracing scenario distinct from ASU development and all DeepMIMO tests used in V11-V13; selection and channel generation occurred after the V14 CP03 rule lock",
        "statistical_independence_verified": False,
        "dataset_sha256": digest(OUTPUT),
        "dataset_shape": list(h.shape),
        "dataset_dtype": str(h.dtype),
        "selection_sha256": digest(SELECTION),
        "selection_protocol_sha256": digest(SELECTION_PROTOCOL),
        "cp03_locked_rule_sha256": digest(LOCK_FILE),
        "dataset_generation_code_sha256": digest(Path(__file__)),
        "deepmimo_version": dm.__version__,
        "transmitter": "BS1 / TX set 3 / index 0",
        "channel_normalization": "none; absolute DeepMIMO complex channel scale retained",
        "channel_matrix_convention": "H[geometry, bs_antenna, user]",
        "max_paths": 10,
        "bs_antenna_shape": [16, 1],
        "ue_antenna_shape": [1, 1],
        "antenna_spacing_wavelengths": 0.5,
        "frequency_domain": True,
        "ofdm_bandwidth_hz": 10_000_000.0,
        "ofdm_total_subcarriers": 512,
        "selected_subcarrier": 0,
        "path_delay_unit": "seconds",
        "noise_power_W": 2e-13,
        "cautions": [
            "Different scenarios and post-lock generation support separation but do not prove statistical independence.",
            "The finite ZF/RZF candidate audit is not global beamforming optimality.",
            "The V14 test dataset must not be used to retune the locked rule."
        ],
    }
    PROVENANCE_OUTPUT.write_text(json.dumps(provenance, indent=2) + "\n")

    print("DEEPMIMO V14 TEST DATASET BUILD PASS")
    print("H shape:", h.shape)
    print("H dtype:", h.dtype)
    print("Geometries:", n_geometries)
    print("Spatial groups:", len(np.unique(groups)))
    print("Dataset:", OUTPUT)
    print("Dataset SHA256:", digest(OUTPUT))
    print("Provenance:", PROVENANCE_OUTPUT)
    print("Provenance SHA256:", digest(PROVENANCE_OUTPUT))
    print("Generation code SHA256:", digest(Path(__file__)))


if __name__ == "__main__":
    main()
