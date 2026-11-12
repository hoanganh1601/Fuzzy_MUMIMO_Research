# Version 12 plan record

This record was consolidated after execution from the supplied IEEE guide, frozen
CP00 files, and dataset provenance. It is an audit record, not a claim that every
cross-source choice was preregistered before the DeepMIMO result.

1. Preserve the supplied final-validation source and its tests.
2. Run the channel-derived and algebraic boundary branch without tuning its guard.
3. Prepare a new DeepMIMO scenario with provenance and development-group overlap
   checks; run `lock → preflight → scan → report`.
4. Prepare a real Sionna 3GPP UMi source rather than an UMi-inspired surrogate;
   record the channel-generation protocol before its own generation/evaluation.
5. Run the identical four validation stages for Sionna/3GPP.
6. Apply the read-only manuscript gate to both source decisions and boundary output.
7. Retain selected CP artifacts and provenance; exclude real matrices, downloaded
   scenarios, task caches, environments, logs, and PID files.
8. Report exactness/call reduction separately from wall-clock performance and stop
   any speedup claim if either source lacks a positive lower runtime bound.
