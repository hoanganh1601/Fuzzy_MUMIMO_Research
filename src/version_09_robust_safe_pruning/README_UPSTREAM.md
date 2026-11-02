# Robust SINR user-set and ZF/RZF beam safe pruning, K=4

Independent exhaustive oracle (`code/reference_model.py`) versus proven-safe prefilters (`code/safe_pruning.py`). Fixed CSI uncertainty radius. No fuzzy or CSI radius optimization.

## Quick start

```powershell
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
python code/safe_pruning.py --stage all --dataset data/smoke.npz --run-id SMOKE --limit 12
python code/safe_pruning.py --stage scan --dataset data/smoke.npz --run-id SMOKE --limit 12
```

For actual propagation data, supply `data/deepmimo.npz` with finite complex H shape (N,M,4) and `groups` shape (N,), plus optionally scenario and xyz. `data/smoke.npz` is SYNTHETIC and is not validation of DeepMIMO or 3GPP.

Guide: `docs/GUIDE_IEEE_VI.pdf` (Vietnamese IEEE one-column) and `.tex`.

The mathematical certificate is limited to the current conservative linear robust SINR model. Pruning is safe within the enumerated beam family; this is not a global beam optimum or a certified end-to-end outage probability.
