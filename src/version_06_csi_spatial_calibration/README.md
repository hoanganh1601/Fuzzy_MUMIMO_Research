# Version 06 — CSI spatial calibration

Spatially grouped CSI-margin calibration for fixed-RZF MU-MIMO downlink.

## Inputs

The real-data NPZ must contain `H` complex `(N,M,K)`, `groups` length `N`, `xyz` in metres `(N,3)`, and `scenario` length `N`.

Real datasets and downloaded DeepMIMO scenarios are not stored in Git.

## Setup

```bash
python -m pip install -r code/requirements.txt
```

For DeepMIMO preparation:

```bash
python -m pip install -r code/requirements-deepmimo.txt
```

## Dataset preparation

```bash
python code/prepare_deepmimo.py --stage select
python code/prepare_deepmimo.py --stage build
python code/prepare_deepmimo.py --stage verify
```

## Calibration stages

```bash
python code/calibration_v2.py --stage preflight  --dataset data/deepmimo.npz --run-id EXP01 --noise 2e-13
python code/calibration_v2.py --stage develop    --dataset data/deepmimo.npz --run-id EXP01 --noise 2e-13
python code/calibration_v2.py --stage calibrate  --dataset data/deepmimo.npz --run-id EXP01 --noise 2e-13
python code/calibration_v2.py --stage freeze     --dataset data/deepmimo.npz --run-id EXP01 --noise 2e-13
python code/calibration_v2.py --stage test       --dataset data/deepmimo.npz --run-id EXP01 --noise 2e-13
python code/calibration_v2.py --stage transfer   --dataset data/deepmimo.npz --external-dataset data/3gpp.npz --run-id EXP01 --noise 2e-13
python code/calibration_v2.py --stage report     --dataset data/deepmimo.npz --run-id EXP01 --noise 2e-13
```

Do not use `--stage all` for confirmatory work. Inspect and lock each checkpoint before continuing.

## Scientific limits

- Distance and disjoint IDs do not prove statistical independence.
- Error realizations are simulated around CSI; they are not measured estimator residuals.
- Fixed RZF has no user scheduler or global beam optimization.
- A DeepMIMO certificate does not transfer to a shifted 3GPP distribution.
- CP05 failure must not be repaired by retuning on the same calibration groups.
