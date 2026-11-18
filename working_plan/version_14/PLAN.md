# Version 14 plan record

This record was consolidated after execution from the supplied IEEE guide, the
sealed CP03 rule, and retained dataset provenance. It is an audit record, not a
claim that this repository file itself was preregistered before execution.

1. Preserve the supplied Version 14 source, tests, smoke fixtures, and guide.
2. Profile CARD, EARLY, CACHED, and HYBRID on development data only.
3. Fit simple feature-threshold rules on 60% of development groups.
4. Freeze the selected rule only when its validation group-bootstrap lower bound
   exceeds 0.1 ms; otherwise freeze CARD.
5. Seal CP03 before selecting or generating the new test data.
6. Generate a new DeepMIMO test from a scenario distinct from ASU and all
   DeepMIMO tests used in V11--V13; retain generation hashes and provenance.
7. Run `preflight -> scan -> report` without retraining or parameter changes.
8. Audit all 105 finite candidates per geometry against the exhaustive oracle.
9. Retain CP00--CP09 and provenance; exclude real matrices, scenarios, selection
   arrays, task caches, environments, logs, and PID files.
10. Report finite-family exactness separately from runtime benefit. Do not claim
    acceleration if the locked policy is CARD or the independent lower bound is
    not greater than 0.1 ms.
11. Treat a second 3GPP source as a separate transfer run reusing CP03; no such
    transfer run is part of the recorded V14 result.
