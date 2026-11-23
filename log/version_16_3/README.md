# Version 16.3 observed results — Sionna UMa natural sample

This is a retrospective run record. The pre-run commitments are in
`runs/NS2/NS00_scenario_spec.json` and
`runs/NP16B/NP00_natural_protocol.json`. The original V15.2 policy lock was
reused without retuning. `reports/KET_QUA_V16_NAT2.zip` is the supplied
25-file report bundle, mirrored under `runs/` and `provenance/` for review.

| Phase | Evidence | Observed result |
|---|---|---|
| check | `console/natural2.log` and user check output | 216/216 C self-test, 36/36 unit tests, V15.2 lock reusable |
| spec/pool | `runs/NS2` | Spec frozen before generation; 200-drop Sionna UMa pool accepted |
| sample | `runs/NP16B/NP00_natural_protocol.json` | 100 whole groups selected without covariate or runtime stratification |
| Python test | `runs/V16_NAT2/CP08_decision.json` | `GO_BREAK_EVEN`, 0 oracle mismatches; P1–P3 true, P4 not evaluable with one group outside R |
| compiled test | `runs/C16_NAT2/CC04_compiled_decision.json` | `GO_COMPILED_BREAK_EVEN`, 0 numeric events in 2,700 decisions; 0 single-vs-double decision changes in 900 configurations |
| natural analysis | `runs/NP16B/NP02_natural_decision.json` | `NATURAL_GAIN`; N2–N4 true; R in 99/100 groups (Wilson 95% CI 94.55–99.82%) |

Mean relative runtime saving across all 100 geometries was 42.33% at K=4,
70.97% at K=6, and 84.33% at K=8; the latter has group-bootstrap 95% CI
81.81–86.49%. Compiled ROUTED saving at K=8 was 95.89% (95% CI
93.42–97.47%). The earlier UMi natural run had R in 1/100 groups and K=8
saving 0.27% (95% CI −0.06–0.93%); the secondary prevalence difference is
98 percentage points (Newcombe 95% CI 91.71–99.16%). The older protocol did
not record its scenario string, so `NP04` labels it `not recorded`; the
earlier V16.2 run record identifies it as Sionna UMi, ISD 200 m.

The UMa comparison changes the macro layout and indoor-user fraction at the
same time. It does not isolate either cause. Only one UMa sample group is
outside R, so outside-region performance has no useful interval estimate;
the compiled C4 flag should be read with that limit. Source-level statistical
independence of the simulated drops was not formally verified. The generator
holds indoor users at 1.5 m, a simplification called out in the supplied
guide. C timings omit the LP audit, and HYBRID executes as EARLY in the
compiled path. No global beamforming optimum or general runtime guarantee is
claimed.

The generated sample's local provenance copied the 200-group pool fields
`dataset_sha256`, `n_geometries`, and `dataset_shape` without replacing them
with the 100-group sample values. The sample itself has SHA-256
`a94ad4981b68141085df0d419bc9d41f13c99ae61f90fe0bf4f8f0b5b788dee3`,
recorded correctly in `runs/V16_NAT2/CP04_test_preflight.json` and the
decisions. The misleading local sample provenance was not included in the
supplied report ZIP; `provenance/pool2.provenance.json` describes the pool.
Do not treat the pool hash as the sample hash when citing the run.

The generated NPZ files remain in the external `datasets/` and run
workspaces. `ARTIFACT_SHA256.csv` hashes the curated repository artifacts.
