# Version 12 acceptance criteria and outcome

- Supplied unit tests pass: **12/12 PASS**.
- Boundary branch has zero false prunes and returns PASS: **met**.
- Every source audits the full finite candidate family without false pruning:
  **met for DeepMIMO and Sionna/3GPP**.
- Dataset/provenance hashes and required metadata are recorded: **met**.
- FAST runtime GO requires a positive lower paired-bootstrap bound on each source:
  **not met on either source**.
- Manuscript lock requires both source-level runtime GO decisions and boundary PASS:
  **not met; `STOP_MANUSCRIPT_NOT_LOCKED`**.
- No claim of global beamforming optimality, statistical independence, outage
  certification, or formal floating-point interval proof: **retained**.
- No real channel matrices, downloaded scenarios, task caches, console logs, PID
  files, or environments are committed: **met**.
