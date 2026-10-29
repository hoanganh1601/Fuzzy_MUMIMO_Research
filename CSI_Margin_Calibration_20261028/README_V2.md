# CSI uncertainty-margin calibration: spatially grouped version

Use `docs/CALIBRATION_SPATIAL_IEEE_VI.pdf` for complete Vietnamese instructions.

- Required real-data NPZ fields: `H` complex (N,M,K), `groups` string (N), `xyz` real meters (N,3), `scenario` string (N). The package does **not** contain real DeepMIMO or certified 3GPP datasets.
- Run `python -m pip install -r code/requirements.txt` then `python code/calibration_v2.py --stage preflight --dataset data/deepmimo.npz --run-id EXP01` and stages `develop`, `calibrate`, `freeze`, `test`, `transfer`, `report`.
- Calibration uses one channel episode per group, 50% of groups. Requires >=59 calibration groups (minimum 118 total). Distance is a diagnostic, NOT proof of independence.
- Candidate q selected on development only. On calibration failure decision is STOP, not an automatically certified Gaussian fallback. Never retune after viewing calibration/test.
- Synthetic sample `data/grouped_smoke.npz` is for logic testing only.
- All stages share a fingerprint; JSON task files persist across interruptions.
- CP05 calibration certificate is valid only under independent exchangeable group-episode assumptions, not under shifted 3GPP distribution. 3GPP simulator/model provenance must be retained separately.
- Do not claim superiority in power until paired, group-aware statistics on the independent test are available.
