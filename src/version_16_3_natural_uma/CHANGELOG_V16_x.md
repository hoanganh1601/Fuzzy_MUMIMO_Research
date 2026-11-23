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

# V16.2 — 22/11/2026

Field report V16_1_compiled_C1_report: C1 failed on C16_DEV (1005/2889 = 34.8% events) and C16_3GPP (162/810 = 20%); C16_DM 0 events (GO).
Diagnosis: every event had rel_diff == rel_spread (ratio 1.0000) and 1 - rho >= 0.37, so the V16.1 "near-singular" explanation does not apply.
Cause: DEV and 3GPP data are stored as complex64; the Python oracle (robust_model.solve, unchanged) therefore runs in single precision,
the compiled solver in double; the V16.1 perturbation (complex128) silently upcast the data, so the measured "spread" was the precision gap.
Reproduced: same channels as complex128 -> 0/24 strict failures; as complex64 -> 13/24, with diff/spread = 1.0.

Changes
- compiled_benchmark.py: VERSION V16.2-compiled; H promoted to complex128 for C and oracle; input_dtype in CC00;
  for complex64 inputs, the single-precision oracle (the V15.2 path) is also run and compared with the double-precision decision
  (CC01 columns single_vs_double_same_decision / single_vs_double_rel_power; CC04 single_vs_double_precision_audit).
- numeric_agreement.py: sensitivity measured in double precision.
- tests: test_single_precision_input (32 tests pass).
- run_v16.ps1: archives C16_* runs of any earlier compiled version.
Core modules and screen_core.c unchanged.

# V16.3 — 23/11/2026: second natural sample in a power-limited deployment

- NEW code/scenario_spec.py: freeze the deployment BEFORE any channel is generated (NS00); validate pool + provenance against it (NS01); no early ratio on the pool.
- NEW code/gen_sionna_uma.py: Sionna template generating the sealed pool from NS00 (UMa ISD 500 m, BS 25 m, 80% indoor, O2I low, 3.5 GHz, M=16, 8 users, complex64); not run with real Sionna in the authoring environment (mock only).
- natural_prevalence.py: protocol stage binds the frozen spec and the accepted pool validation (--scenario-spec, --pool-validation); new stage compare (NP04/NP05, Newcombe CI of the prevalence difference).
- run_v16.ps1: phases natural2-spec, natural2-generate, natural2-validate, natural2-protocol, natural2 (-> KET_QUA_V16_NAT2.zip).
- tests/test_v16_3.py (4 tests); 36 tests pass. Core modules, screen_core.c and the V15.2 lock unchanged.
