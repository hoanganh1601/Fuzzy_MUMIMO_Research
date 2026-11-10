# Manuscript tables — run `V11_DEV_20261110`

**Dev dataset:** DeepMIMO v10 development set. Numbers below come only from checkpoint outputs of this run.

## Table A — Exactness and scheduling performance

| Metric | Value |
|---|---|
| Channel geometries | 160 |
| Candidates per geometry | 105 |
| Exact match with exhaustive (ALL / CARDINALITY_ONLY) | 160/160 / 160/160 |
| Optimum serves 4 users | 97/160 (60.6%) |
| Optimum serves 3 users | 58/160 (36.2%) |
| Optimum serves 2 users | 5/160 (3.1%) |
| Optimum serves 1 users | 0/160 (0.0%) |
| Optimum serves 0 users | 0/160 (0.0%) |
| Mean admitted users | 3.5750 |
| Optimum beam ZF / RZF | 42 / 118 |
| False prunes (all 16800 candidate audits) | 0 |
| Fail-open activations | 0 |

## Table B — Incremental benefit (per geometry, mean over geometries; runtime = median of repeated runs)

| Variant | Full solves | Beams built | Runtime (ms) | Beam (ms) | Screening (ms) | Solver (ms) |
|---|---|---|---|---|---|---|
| EXHAUSTIVE | 105.0000 | 105.0000 | 140.8923 | — | 0.0000 | — |
| CARDINALITY_ONLY | 19.3375 | 19.3375 | 15.5838 | 2.9029 | 0.0000 | 12.5238 |
| ALL | 8.5375 | 17.8062 | 16.4046 | 2.3297 | 1.3677 | 12.5417 |
| WITHOUT_NORM_NOISE_LOWER_BOUND | 8.5375 | 19.3375 | 15.9394 | 2.5931 | 0.8175 | 12.3629 |
| WITHOUT_ZERO_ROBUST_GAIN | 8.6000 | 17.8062 | 16.5145 | 2.3453 | 1.3678 | 12.6339 |
| WITHOUT_NOISE_LOWER_BOUND | 8.5375 | 17.8062 | 16.4488 | 2.3344 | 1.3637 | 12.5889 |
| WITHOUT_NEUMANN_LOWER_BOUND | 9.4125 | 17.8062 | 15.9254 | 2.3016 | 1.1496 | 12.3165 |
| WITHOUT_TWO_CYCLE_COUPLING | 8.7875 | 17.8062 | 16.2314 | 2.3253 | 1.3335 | 12.4081 |

- Full solves, ALL vs CARDINALITY_ONLY: 8.5375 vs 19.3375 (55.85% fewer).
- Runtime, ALL vs CARDINALITY_ONLY: 16.4046 vs 15.5838 ms (-5.27% reduction); paired saving 95% cluster-bootstrap CI [-1.2675, -0.3783] ms over 160 groups → advantage confirmed: **False**.
- Runtime, ALL vs EXHAUSTIVE: 16.4046 vs 140.8923 ms (88.36% reduction); CI [118.9078, 130.3357] ms.
- Reference status of certificate-pruned candidates: {'ZERO_ROBUST_DIRECT_GAIN': 11, 'COUPLING_RHO_GE_ONE': 1481, 'POWER_BUDGET': 1023}.

| Reference status | Evaluations (exhaustive) | Beam generation (ms) | Power solve (ms) | Pruned by ALL |
|---|---|---|---|---|
| COUPLING_RHO_GE_ONE | 1484 | 0.1186 | 0.0251 | 1481 |
| FEASIBLE | 14222 | 0.2042 | 1.4343 | 0 |
| POWER_BUDGET | 1083 | 0.1443 | 0.0528 | 1023 |
| ZERO_ROBUST_DIRECT_GAIN | 11 | 0.2714 | 0.0014 | 11 |

- Cost balance per geometry under ALL: screening 1.3677 ms vs. estimated power-solve time avoided 0.5698 ms (pruned candidates × mean power-solve cost of their reference status). Beam generation is not avoided for candidates pruned after beam generation.

## Table B2 — Certificate ablation (difference to ALL; positive = removing the rule costs more)

| Removed rule | Δ full solves | Δ runtime (ms) | Prunes by rule under ALL (mean/geometry) |
|---|---|---|---|
| NORM_NOISE_LOWER_BOUND | +0.0000 | -0.4653 | 1.5312 |
| ZERO_ROBUST_GAIN | +0.0625 | +0.1098 | 0.0625 |
| NOISE_LOWER_BOUND | +0.0000 | +0.0442 | 3.7062 |
| NEUMANN_LOWER_BOUND | +0.8750 | -0.4793 | 5.2500 |
| TWO_CYCLE_COUPLING | +0.2500 | -0.1733 | 0.2500 |

## Table C — Boundary stress

Outcome **PASS** — 1030 cases, 0 false prunes, 324 fail-open, 515 feasible reference cases.

| Family | Cases | Feasible truth | Prune | Fail-open | False prune |
|---|---|---|---|---|---|
| algebraic:COUPLING | 10 | 5 | 2 | 1 | 0 |
| algebraic:POWER | 10 | 5 | 1 | 0 | 0 |
| algebraic:POWER_TIGHT | 10 | 5 | 2 | 1 | 0 |
| channel:POWER | 1000 | 500 | 156 | 322 | 0 |
