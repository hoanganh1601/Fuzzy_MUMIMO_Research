# Version 15.2 acceptance criteria and outcome

- Region gate: at least 10 groups in `R`: **passed, 15 per source**.
- P1: K=8 lower CI bounds exceed 2% and 0.1 ms in `R`: **passed**.
- P2: lower CI bound of K8 minus K4 relative saving is positive: **passed**.
- P3: zero oracle mismatch: **passed on both sources**.
- P4: no demonstrated missed EARLY benefit outside `R`: **passed**.
- Same frozen lock used for DeepMIMO and 3GPP: **met**.
- Test selection used covariates and no runtime: **met**.
- Combined outcome: **`GO_PREDICTABLE_BREAK_EVEN`**.
- Prototype/monitored-pilot progression supported: **yes**.
- Production-readiness claim allowed: **no**.
- Statistical independence mathematically verified: **no**.
