# Robust SINR User Scheduling and Beam Selection (K=4)

An independent experiment with fixed CSI margin and robust downlink power control. Exhaustive reference: all 15 nonempty user subsets and a fixed ZF/RZF codebook. Two heuristic baselines: forward admission and backward deletion. The objective is lexicographic: maximize admitted user count, then minimize power **within that count**.

## Quick verification

```
python -m pip install -r code/requirements.txt
python code/make_smoke.py
python code/admission_beam.py --stage all --dataset data/smoke.npz --run-id SMOKE --limit 12
```

## DeepMIMO

Provide `data/deepmimo.npz` with `H` complex `(N,M,4)` and `groups` `(N,)`. Optional `scenario`,`xyz`.

```
python code/admission_beam.py --stage preflight --dataset data/deepmimo.npz --run-id DM01
python code/admission_beam.py --stage scan --dataset data/deepmimo.npz --run-id DM01
python code/admission_beam.py --stage report --dataset data/deepmimo.npz --run-id DM01
```

Resume by calling `scan` again with same dataset, code and parameters. Changes require new run-id. Complete per-geometry atomic JSON checkpoints in `outputs/<run-id>/tasks/`.

The smoke dataset is synthetic, not a DeepMIMO or 3GPP experiment. A best-of-codebook reference is **not** a global beamforming optimum. Selecting fewer users is not a free throughput gain: include fairness, service latency, rates and outage before publication.

Vietnamese IEEE one-column guidance: `docs/GUIDE_IEEE_VI.pdf` and `.tex`.
