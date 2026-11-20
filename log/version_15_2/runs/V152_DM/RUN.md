# V152 DeepMIMO run

- Development: 107 spatial groups from `asu_campus_3p5`.
- Test pool: 107 groups from new `city_1_losangeles_3p5`; `prior_use=never_seen`.
- Selection: 15 groups in frozen region `R` and 15 outside; runtime was not used.
- Region gate: 15/10 groups, passed.
- Decision: `GO_BREAK_EVEN`; P1--P4 passed; oracle mismatch 0.
- At K=8 in `R`: mean frozen-policy saving 73.73% and 138.69 ms.
- Scope: finite ZF/RZF codebook and recorded machine/runtime environment.
