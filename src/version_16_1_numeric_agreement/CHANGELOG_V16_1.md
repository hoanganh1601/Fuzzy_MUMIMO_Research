# V16.1 — 21/11/2026

Fix: `COMPILED MISMATCH geometry=8 K=6 L=3 CARD` (same subset '24', alpha 0.01, cardinality 2; power 0.379298587602968 vs 0.37929854287093945, relative difference 1.2e-7 > strict 1e-7).

Root cause: near-singular (I - F) when rho(F) is close to 1; rounding-order differences between C and NumPy are amplified by about 1/(1 - rho). Reproduced: 1 - rho = 1e-7, 1e-8, 1e-9 give relative power differences 6e-7, 3e-5, 8e-5. Both implementations are correct to floating-point accuracy.

Changes
- NEW code/numeric_agreement.py: floating-point-aware agreement (applied only when the strict test fails); accepted cases are logged.
- code/compiled_benchmark.py: VERSION V16.1-compiled; uses numeric_agreement; writes CC06_numeric_events.csv; CC04 reports numeric_events, decisions_checked, numeric_event_fraction, numeric_event_types; C1 requires fraction <= 1%.
- code/native_search.py: selftest reports floating-point events separately.
- tests/test_v16.py: regression test for the near-singular case (strict test fails, new rule accepts, a genuine 1e-5 error is rejected). 31/31 tests pass.
- scripts/run_v16.ps1: archives C16_* folders created by V16 before re-running (old checkpoints cannot be resumed because the code hash changed).

Unchanged: run_experiment.py, robust_model.py, screening_policy.py, certified_screening.py, screening_bounds.py (hashes e5109400…, 1511351d…, 8606efa3…, 23344bb8…, edacac60…), native/screen_core.c, the V15.2 lock.
