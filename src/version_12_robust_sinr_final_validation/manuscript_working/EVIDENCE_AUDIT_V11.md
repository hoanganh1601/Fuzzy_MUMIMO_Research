# V11 evidence audit and editorial decisions

## Decision
- PASS: 160/160 development geometries match the 105-candidate exhaustive reference.
- PASS: 1,030 constructed boundary cases with zero false pruning and 324 fail-open actions.
- FAIL for speed claim: ALL takes 16.4046 ms versus CARDINALITY_ONLY 15.5838 ms on the development set.
- Synthetic rehearsal only: 160 geometries, 32 groups; ALL takes 13.9126 ms versus CARDINALITY_ONLY 13.1913 ms.
- Missing: genuinely new DeepMIMO groups and independently configured 3GPP channels. V11 JSON D is empty.

## Distinguish cost metrics
- Full solver calls: 19.3375 to 8.5375 (55.85% fewer).
- Mean time: 15.5838 to 16.4046 ms (5.27% slower).
- Mean screening overhead: 1.3677 ms; estimated solved time avoided: 0.5698 ms.
- Descriptive paired 95% cluster-bootstrap CI for CARDINALITY_ONLY minus ALL: [-1.2675, -0.3783] ms on 160 development groups.
- Existing V10 7.26% advantage is NOT reproduced in V11; do not silently pool results.

## Boundary scope
- 1,030 constructed cases: algebraic coupling 10, algebraic power 10, tight power 10, channel-derived one-user power 1,000.
- 161 pruned, 324 fail-open, 515 feasible reference, zero false-prunes.
- Exact rational reference evaluates double coefficients; no interval bound for channel/beam generation.

## Manuscript scope
- The manuscript source is a reconstructed draft from the previously agreed six-section outline, NOT an edited copy of an attached pre-existing article (no matching article source was attached in this turn).
- RESULTS_INSERT.tex is provided for merging into the author's existing article if a separate manuscript source exists.
- Related-work citations and author details have not been invented; verified references must be added before submission.
- Manuscript remains a working draft; no claim of journal readiness.
