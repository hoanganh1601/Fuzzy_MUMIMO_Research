# V152 Sionna 3GPP run

- Test pool: 120 newly generated Sionna UMi groups, 60 near and 60 edge;
  `prior_use=never_seen`.
- Selection: 15 groups in frozen region `R` and 15 outside; runtime was not used.
- The DeepMIMO CP03 lock was reused without retraining on 3GPP.
- Region gate: 15/10 groups, passed.
- Decision: `GO_BREAK_EVEN`; P1--P4 passed; oracle mismatch 0.
- At K=8 in `R`: mean frozen-policy saving 83.57% and 126.69 ms.
- Scope: finite ZF/RZF codebook and recorded machine/runtime environment.
