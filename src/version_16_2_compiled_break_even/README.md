# Version 16.2 — compiled break-even and natural prevalence

This directory preserves the 93-file supplied V16.2 package. All 93 entries
match `UPSTREAM_FILE_SHA256.csv`. The original README and validation report are
retained as `README_UPSTREAM.md` and `VALIDATION_REPORT_UPSTREAM.json`; their
manifest entries retain the original names. `build_natural_pool.py` is an
additional data-preparation script used for the natural-prevalence run, not part
of the supplied package. Run a copy of it in the external dataset directory;
the repository does not store the generated channel matrices.

Read `HUONG_DAN_V16.md` for the supplied procedure and `CHANGELOG_V16_x.md`
for the V16.2 numerical change. The five frozen V15.2 core modules
(`run_experiment.py`, `robust_model.py`, `screening_policy.py`,
`certified_screening.py`, `screening_bounds.py`) are byte identical to the
V15.2 snapshot. The V15.2 policy lock was reused without retraining or
threshold changes.

## Observed results

- `check`: C self-test 216/216; unit tests 32/32; V15.2 lock reusable as-is.
- `compiled`: development, DeepMIMO, and 3GPP each passed C1–C4 and returned
  `GO_COMPILED_BREAK_EVEN`. Their numeric-event counts were 0/2889, 0/810,
  and 0/810. The natural sample had only one group in the predicted region R;
  its compiled run returned `INCONCLUSIVE_REGION_TOO_SMALL` while C1 and C4
  passed.
- `model`: both Python and C timing models were fitted on development and
  evaluated on DeepMIMO and 3GPP. The C timing model has larger percentage-point
  errors than the Python model. K=10 and K=12 are model extrapolations.
- `natural`: a fresh Sionna 3GPP UMi single-sector pool with one 200 m ISD
  contained 200 eight-user groups. The locked protocol selected 100 whole
  groups without covariate or runtime stratification. Region R occurred in
  1/100 groups. The decision is `NATURAL_NO_HARM`: N2=false, N3=true, and N4
  is not evaluable with fewer than five R groups. This does not establish a
  positive whole-cell runtime gain.

The first `natural` script invocation stopped before timing because the
external pool provenance lacked the required `independence_basis` field. The
pool and locked protocol were not changed. The pool and sample provenance were
completed, including the sample's own SHA-256, then the remaining test,
report, compiled, and analysis stages were run separately on the same frozen
sample. See `../../log/version_16_2/README.md` and its console logs.

The reported C/Python speedups have a measurement-scope caveat: C omits the LP
audit from its timed region and implements HYBRID as EARLY, as stated in the
supplied guide. The source-level statistical independence of the simulated
natural pool has not been formally verified. No global beamforming optimum or
general runtime benefit is claimed.
