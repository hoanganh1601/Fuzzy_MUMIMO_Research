# E1-R–E3-R: Reliability-screened Sugeno MU-MIMO

## Scientific scope
A follow-up to the DeepMIMO / Sionna MU-MIMO pilot. Five strategies are evaluated under the SAME RZF power solver and shared error draws: Gaussian, validation-tuned fixed margin, validation-tuned threshold margin, raw Sugeno, safety-filtered Sugeno. Reliability = conditional SINR outage AND effective failure; compare power only on commonly feasible geometries. No theorem of 5% outage guarantee is claimed.

## Inputs
`data/*.npz` must include finite complex `H` shaped `(N,M,K)` and `groups` array with **at least 12 meaningful, non-overlapping spatial/scenario groups**. The DeepMIMO prior adapter groups contiguous UE indices; re-check physical coordinates and regenerate `groups` before making scientific claims. Do NOT use `umi_inspired` as a 3GPP TR 38.901 validation.

## Quick test
```
python -m pip install -r code/requirements.txt
python code/generate_data.py --source synthetic --M 16 --K 4 --n 240 --output data/demo.npz
python code/experiment_r.py --stage all --dataset data/demo.npz --M 16 --run-id smoke --limit 2 --n-mc 8 --bootstrap 100
```
This is a code smoke test, NOT study data.

## Publication sequence
Replace `data/deepmimo.npz` with spatially grouped genuine DeepMIMO channel data and run:
```
python code/experiment_r.py --stage preflight --dataset data/deepmimo.npz --run-id DM_R --M 16
python code/experiment_r.py --stage develop --dataset data/deepmimo.npz --run-id DM_R --M 16
python code/experiment_r.py --stage calibrate --dataset data/deepmimo.npz --run-id DM_R --M 16
python code/experiment_r.py --stage freeze --dataset data/deepmimo.npz --run-id DM_R --M 16
python code/experiment_r.py --stage test --dataset data/deepmimo.npz --run-id DM_R --M 16
python code/experiment_r.py --stage report --dataset data/deepmimo.npz --run-id DM_R --M 16
```

For transfer to actual Sionna-generated 3GPP channels (new independent dataset):
```
python code/experiment_r.py --stage freeze --dataset data/sionna_3gpp.npz --run-id TR_R --M 16 --frozen-from outputs_r/DM_R/cp03_frozen.json
python code/experiment_r.py --stage test --dataset data/sionna_3gpp.npz --run-id TR_R --M 16
python code/experiment_r.py --stage report --dataset data/sionna_3gpp.npz --run-id TR_R --M 16
```
`--frozen-from` is given to the freeze stage only. M, K, sigma_rel, SINR and eps must match the source run. Every group of the transfer dataset is test data. Set `--noise` (or store `noise_w` with `import_3gpp.py --noise-w`).
The 3GPP NPZ must preserve simulator metadata elsewhere. An external frozen parameter set is transferred without retuning; never refer to an artificially generated UMi-inspired dataset as full 3GPP.

## Tests
```
python tests/test_invariants.py   # engine: bound validity, LP optimality, q_G coverage, scale invariance, resume
python tests/test_r_pipeline.py   # E1R-E3R: splits, non-degenerate grids, distinct finalists, transfer workflow
```

## Outputs and resilience
CP00 manifest; CP01 candidate JSON; CP02 calibration JSON; CP03 frozen JSON; CP04 test-geometry CSV; CP05 summary CSV; CP06 paired comparison CSV; CP07 GO/STOP JSON; CP08 checkpoint SHA256 CSV; CP09 scope JSON. Per-geometry tasks are under `outputs_r/<run-id>/tasks/test/`. JSON/CSV atomic writes, source/data/settings hashes and per-task signature ensure safe resume. Retry identical commands after power failure. Changed code/data/settings require a new `run-id`.

## Decision
GO only if fuzzy_safe passes calibration, both outage/effective failure <= `eps` on independent test, fixed and threshold also meet `eps` on test, AND upper 95% group-bootstrap bound on mean power ratio vs BOTH fixed and threshold < 1, with upper paired effective-risk difference <= 0.005. Otherwise STOP. These are empirical gates, not formal probability guarantees. Development (40% of groups) searches each method's grid and keeps 4 distinct finalists; validation (20%) selects one configuration per method; calibration (20%) only GATES the selected configuration (no selection); test (20%) is touched once. Fixed and threshold follow the same path. Test must not be reused for method redesign. Report `floor_active_rate`: when it is close to 1, fuzzy_safe is in effect a fixed margin.

## Revision R1 (2026-10-21)
See `docs/CODE_REVIEW_E1R_E3R_R1_VI.md`. Built on the R1 engine (`docs/CODE_REVIEW_R1_VI.md`). Runs and frozen files from the delivered version are not compatible: use new run-ids.
