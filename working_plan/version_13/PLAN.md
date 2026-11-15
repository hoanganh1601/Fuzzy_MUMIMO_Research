# Version 13 plan record

This record was consolidated after execution from the supplied IEEE guide, the
sealed CP02 policy lock, and the retained dataset provenance. It is an audit
record, not a claim of prospective preregistration before all implementation work.

1. Preserve the supplied Version 13 source, smoke fixtures, tests and guide.
2. Evaluate CARD, EARLY, CACHED and HYBRID on development only.
3. Freeze a single policy when its paired group-bootstrap lower runtime-saving
   bound exceeds 0.1 ms; otherwise freeze CARD.
4. Seal CP02 before selecting or generating the new test data.
5. Build a new DeepMIMO test from a scenario distinct from development and record
   data-selection/generation code hashes.
6. Run `preflight → scan → report` without retraining or parameter changes.
7. Audit all 105 finite candidates per geometry against exhaustive reference.
8. Retain selected CP/provenance artifacts and exclude real matrices, downloaded
   scenarios, task caches, environments, logs and PID files.
9. Report exactness separately from runtime benefit and stop any speedup claim if
   development selects CARD or the test runtime lower bound is not positive.
