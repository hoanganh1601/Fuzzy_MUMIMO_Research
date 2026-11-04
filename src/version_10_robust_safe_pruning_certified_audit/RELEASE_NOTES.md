# Differences from November 2 package

1. New `ablation_certified.py` with conservative fail-open for numerically ambiguous certificates. A near-boundary candidate is evaluated by the complete solver, not discarded.
2. Arbitrary-precision numerical diagnostic (mpmath, 70 decimal digits) for near-boundary cases using the computed beam/coupling coefficients; explicitly **not** an interval proof from original CSI.
3. Each of the 105 candidate decisions per geometry is audited against exhaustive independently, including survivors and near-boundary decisions.
4. Paired cardinality-only versus all-certificate deltas with cluster bootstrap 95% intervals. No false declaration of runtime superiority when the interval contains zero.
5. Atomic tasks with signature guarding source/data/config; resumable scan.
6. Fixed summary key bug during smoke testing, reran with a new run-id after changing the source.
7. Kept original model and screening as reference; no CSI margin tuning.

Synthetic smoke (12 geometries): `PASS_EXACTNESS`, zero false-prunes, 7 fewer full solver calls per geometry on average versus cardinality-only, runtime difference CI includes zero. Scientific conclusions require new DeepMIMO and independent 3GPP scenarios.
