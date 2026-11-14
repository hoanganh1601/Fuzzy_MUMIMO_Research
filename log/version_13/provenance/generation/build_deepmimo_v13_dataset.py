"""Build the locked DeepMIMO V13 New York channel test dataset."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import deepmimo as dm
import numpy as np


ROOT = Path(__file__).resolve().parent
SCENARIO = "city_0_newyork_3p5"
SELECTION = ROOT / "deepmimo_v13_selection.npz"
SELECTION_PROTOCOL = ROOT / "deepmimo_v13_selection_protocol.json"
OUTPUT = ROOT / "deepmimo_v13_test.npz"
PROVENANCE_OUTPUT = ROOT / "deepmimo_v13_test_provenance.json"
CP02 = ROOT / "locks" / "CP02_policy_lock_DM_ASU35_20261112.json"
EXPECTED_CP02_SHA256 = "ede58de7c0f2791327b54e929e6da4921db17b8d5c870a3dec5bdc9ef1b8b5be"
EXPECTED_SELECTION_SHA256 = "45ae9175c59452f7209fea5d03a42ddb3ae687b09b57e2664ecff09a3fa4f1a1"
EXPECTED_SELECTION_PROTOCOL_SHA256 = (
    "8066d1e898449440d2c9876a77445f6215fa7ab83d622a7c540faeb5ae302fa3"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUTPUT.exists() or PROVENANCE_OUTPUT.exists():
        raise SystemExit("Locked V13 test dataset already exists; refusing to overwrite")
    if digest(CP02) != EXPECTED_CP02_SHA256:
        raise SystemExit("CP02 policy-lock hash mismatch")
    if digest(SELECTION) != EXPECTED_SELECTION_SHA256:
        raise SystemExit("Selection hash mismatch")
    if digest(SELECTION_PROTOCOL) != EXPECTED_SELECTION_PROTOCOL_SHA256:
        raise SystemExit("Selection protocol hash mismatch")

    with np.load(SELECTION, allow_pickle=False) as selected:
        ue_indices = np.asarray(selected["ue_indices"], dtype=np.int64)
        groups = np.asarray(selected["groups"])
        centers = np.asarray(selected["centers"], dtype=np.float64)
        user_xyz = np.asarray(selected["user_xyz"], dtype=np.float64)

    if ue_indices.shape != (160, 4) or len(np.unique(ue_indices)) != 640:
        raise SystemExit("Invalid locked selection")

    flat_indices = ue_indices.reshape(-1)
    dataset = dm.load(
        SCENARIO,
        max_paths=10,
        tx_sets={3: [0]},
        rx_sets={0: flat_indices},
        matrices=[
            "power",
            "phase",
            "delay",
            "aoa_az",
            "aoa_el",
            "aod_az",
            "aod_el",
            "rx_pos",
            "tx_pos",
        ],
    )

    loaded_xyz = np.asarray(dataset.rx_pos, dtype=np.float64).reshape(160, 4, 3)
    if not np.allclose(loaded_xyz, user_xyz, rtol=0.0, atol=1e-9):
        raise SystemExit("Loaded UE order or coordinates do not match the locked selection")

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
    expected_shape = (640, 1, 16, 1)
    if raw_channel.shape != expected_shape:
        raise SystemExit(
            f"Unexpected raw channel shape {raw_channel.shape}; expected {expected_shape}"
        )

    h = raw_channel[:, 0, :, 0].reshape(160, 4, 16).transpose(0, 2, 1)
    h = np.asarray(h, dtype=np.complex64)
    if h.shape != (160, 16, 4) or not np.isfinite(h).all():
        raise SystemExit("Invalid final H matrix")
    if np.any(np.linalg.norm(h, axis=1) == 0):
        raise SystemExit("At least one selected user has a zero channel norm")

    scenario_labels = np.full(160, SCENARIO)
    np.savez_compressed(
        OUTPUT,
        H=h,
        groups=groups,
        xyz=centers,
        scenario=scenario_labels,
    )

    provenance = {
        "source": "DeepMIMO",
        "scenario": SCENARIO,
        "split": "new_independent_test",
        "prior_use": "never_seen",
        "created_after_policy_lock": True,
        "group_definition": "40 fixed 15 m spatial grid cells; four geometries per cell; four users per geometry; 640 unique UEs without reuse",
        "independence_basis": "New York city_0_newyork_3p5 ray-tracing scenario is distinct from the ASU Campus development scenario; selection and channel generation occurred only after the V13 CP02 policy lock",
        "statistical_independence_verified": False,
        "dataset_sha256": digest(OUTPUT),
        "dataset_shape": list(h.shape),
        "dataset_dtype": str(h.dtype),
        "selection_sha256": digest(SELECTION),
        "selection_protocol_sha256": digest(SELECTION_PROTOCOL),
        "cp02_policy_lock_sha256": digest(CP02),
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
        "path_delay_units": "seconds",
        "noise_power_W": 2e-13,
        "cautions": [
            "Different scenarios and a post-lock selection support separation but do not prove statistical independence.",
            "The finite ZF/RZF candidate audit is not global beamforming optimality.",
            "This test dataset must not be used to retune the locked V13 policy.",
        ],
    }
    PROVENANCE_OUTPUT.write_text(json.dumps(provenance, indent=2) + "\n")

    print("DEEPMIMO V13 TEST DATASET BUILD PASS")
    print("H shape:", h.shape)
    print("H dtype:", h.dtype)
    print("Geometries:", len(h))
    print("Spatial groups:", len(np.unique(groups)))
    print("Dataset:", OUTPUT)
    print("Dataset SHA256:", digest(OUTPUT))
    print("Provenance:", PROVENANCE_OUTPUT)
    print("Provenance SHA256:", digest(PROVENANCE_OUTPUT))
    print("Generation code SHA256:", digest(Path(__file__)))


if __name__ == "__main__":
    main()
