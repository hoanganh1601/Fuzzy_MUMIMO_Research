# Shared Sionna UMi generator

`gen_sionna_umi.py` regenerates three historical Sionna TR 38.901 UMi
datasets used across multiple research versions. It is repository-level
reproducibility tooling, not source code belonging exclusively to V17.

| Mode | Dataset | Expected SHA-256 |
|---|---|---|
| `v151` | V15.1 UMi test, 15 drops | `0b4f0de1c31acfe06181e9e21190e784b77cf54c399dbb1a4d43b473795a0ba8` |
| `near-edge` | V15.2 UMi selection pool, 120 drops | `fbfda83348922473fe16bc0caa58b700b8135fce8a47b82df0f641fd111a99da` |
| `natural` | V16 natural UMi pool, 200 drops | `099a26d5e46c9b585a4b03e5c2e6284ffee13241c7727bfee6384593c4c06645` |

Use Sionna 2.2.0 with PyTorch 2.15.0+cpu. Each mode has a committed frozen
protocol and refuses to overwrite an existing output.

```bash
SIONNA_PY=/path/to/sionna/python

"$SIONNA_PY" reproducibility/sionna/gen_sionna_umi.py \
  --mode natural --stage build \
  --protocol reproducibility/sionna/protocols/sionna_umi_natural.json \
  --output data/natural_umi_pool.npz
```

The generated NPZ and provenance are excluded from Git. Verify distributed
datasets with the root `DATASETS.csv` as described in `DATA_AVAILABILITY.md`.
