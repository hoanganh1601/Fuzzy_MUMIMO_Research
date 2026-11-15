# Version 13 run log

Version 13 evaluates whether cost-aware robust-SINR screening improves paired
end-to-end runtime over the cardinality-only baseline while retaining exactness
over the finite ZF/RZF candidate family.

The recorded run is [`DM_ASU35_COST_V13_20261112`](runs/DM_ASU35_COST_V13_20261112/RUN.md):

- Development used the previously observed ASU Campus set only for policy
  selection. None of `EARLY`, `CACHED`, or `HYBRID` passed the locked 0.1 ms
  lower-confidence-bound threshold, so CP02 froze `CARD`.
- Test used a newly downloaded New York DeepMIMO scenario. Selection and channel
  generation occurred after CP02 was sealed, with 160 geometries in 40 spatial
  groups and no exact channel/group overlap with development.
- The test retained `CARD`, returned `STOP_NO_RUNTIME_GAIN`, and observed zero
  oracle mismatch.
- CP08 audited all 16,800 finite candidates and observed zero false rejection.

The nine checkpoint files are bundled in
[`Results.Robust.SINR.Cost.Aware.V13.CP01-CP08.zip`](reports/Results.Robust.SINR.Cost.Aware.V13.CP01-CP08.zip).
The exact selection/channel-generation scripts and their provenance are retained
under `provenance/`. Real channel matrices, selection arrays, downloaded scenarios,
task caches, environments, console logs, and PID files are excluded.

Different scenarios, post-lock generation, and overlap checks support source
separation but do not prove statistical independence. The result establishes
finite-family exactness for this run, not runtime superiority, global beamforming
optimality, an outage certificate, or formal interval arithmetic.
