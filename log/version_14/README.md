# Version 14 run log

Version 14 evaluates whether a development-locked cost-aware switch improves
paired end-to-end runtime over the cardinality-only baseline while preserving
the exhaustive result over the finite ZF/RZF candidate family.

The recorded run is
[`DM_ASU35_COST_LIMITS_V14_20261117`](runs/DM_ASU35_COST_LIMITS_V14_20261117/RUN.md):

- Development used 160 previously observed ASU geometries. The best fit rule
  used `EARLY` when `early_ratio >= 0.4690403640`, but its validation CI crossed
  zero and failed the locked 0.1 ms gate, so CP03 froze `CARD`.
- Test used a newly downloaded Denver DeepMIMO 4.0.5 scenario. Selection and
  channel generation occurred after CP03 was sealed, producing 92 geometries in
  23 spatial groups and 368 unique UEs.
- CP04 recorded zero group-label overlap and zero exact-channel overlap with
  development. These checks support separation but do not prove statistical
  independence.
- CP06 audited all 9,660 finite candidates. CP08 observed zero oracle mismatch
  and zero false certificate.
- The locked `CARD` policy activated no screening, saved no solver calls, and
  had mean runtime saving -0.0145 ms with CI95 `[-0.0319, -0.00004]` ms. The
  decision was `STOP_NO_RUNTIME_GAIN`.

The 12 checkpoint files are bundled in
[`Results.Robust.Cost.Limits.V14.CP00-CP09.zip`](reports/Results.Robust.Cost.Limits.V14.CP00-CP09.zip).
The exact selection/channel-generation scripts and provenance are retained under
`provenance/`. Real channel matrices, selection arrays, downloaded scenarios,
task caches, environments, console logs, and PID files are excluded.

No V14 3GPP transfer run was executed. This record therefore does not establish
cross-source acceleration, verified statistical independence, global
beamforming optimality, an outage certificate, or formal interval arithmetic.
