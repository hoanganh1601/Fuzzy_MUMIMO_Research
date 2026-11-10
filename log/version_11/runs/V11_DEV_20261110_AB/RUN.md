# Run card: V11_DEV_20261110_AB

- Code version: Version 11 R2, source commit `1b0bca0`
- Dataset: reused DeepMIMO v10 development set, shape `(160,16,4)`, 160 groups
- Dataset SHA-256: `1d479a06b94fff565a8997ceb870c670bda7458dbf5e5cd54c2fc0afc14b1f50`
- Configuration: q=2.960414, sigma_rel=0.04, SINR=6 dB, noise=2e-13 W, Pmax=1 W, seven ZF/RZF alphas, repeats=5, bootstrap=2000
- Status: `PASS_EXACTNESS`; 16,800 candidates, 160/160 exact matches for every variant, zero false prunes

Mean full solves per geometry were 105.0 for exhaustive, 19.3375 for CARDINALITY_ONLY, and 8.5375 for ALL. ALL reduced calls by 55.85% relative to cardinality-only.

Mean runtimes were 140.8923 ms, 15.5838 ms, and 16.4046 ms respectively. ALL was 5.27% slower than cardinality-only; paired runtime-saving CI95 was `[-1.2675,-0.3783]` ms, so `runtime_advantage_confirmed=false`. The 88.36% reduction relative to exhaustive is primarily attributable to cardinality ordering, not solely to certificates.

This is development-data evidence over a finite candidate family, not independent validation or continuous-beam optimality.
