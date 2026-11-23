# Version 16.2 observed results

This is a retrospective record of the V16.2 run, not a replacement for the
pre-registered protocol in `runs/NP16/NP00_natural_protocol.json` or the
supplied `src/version_16_2_compiled_break_even/HUONG_DAN_V16.md`.

| Phase | Evidence | Result |
|---|---|---|
| check | User console: 216/216 C self-test, 32/32 unit tests, lock compatibility | V15.2 lock reused unchanged |
| compiled | `runs/C16_DEV`, `runs/C16_DM`, `runs/C16_3GPP` | C1–C4 pass in all three; no numeric events; `GO_COMPILED_BREAK_EVEN` |
| model | `runs/M16_PY`, `runs/M16_C` | Development fit and two-source evaluation complete; K=10,12 extrapolated |
| natural | `runs/NP16`, `runs/V16_NAT`, `runs/C16_NAT` | 1/100 groups in R; `NATURAL_NO_HARM`, N2=false, N3=true, N4 not evaluable |

The natural pool used Sionna 3GPP UMi, one 200 m ISD, and uniform random
single-sector drops: 200 groups, eight users per group. The pool SHA-256 is
`099a26d5e46c9b585a4b03e5c2e6284ffee13241c7727bfee6384593c4c06645`.
The single locked 100-group sample SHA-256 is
`0c92e8393cd6f6abacba5ff53d559648513cea58019f6c664206a3d34d92fcc4`.
The source pool and sample NPZ files remain under the external `datasets/`
workspace and the run workspace respectively; they are not committed.
`provenance/` records generation settings, source and sample provenance.

The initial `natural` script invocation stopped before timing because the
generated pool provenance omitted `independence_basis`; the first console log
records that stop. Metadata was corrected without changing the pool, sample,
locked protocol, or five V15.2 core modules. The test was then resumed through
the script's individual Python stages, and the report ZIP was packaged using
the script's curated-file selection. `reports/KET_QUA_V16.zip` contains 45
selected checkpoints from eight run directories; `runs/` mirrors them for
review. Per-geometry task caches, native binaries, real channel matrices,
environments, and PID files are excluded. `runs/V16_NAT/CP09_SHA256.csv` has
111 verified entries in the run workspace.

The compiled natural run has C1=true and C4=true but its R-only C2/C3 checks
are inconclusive with one R group. The separate natural-prevalence decision
uses the predeclared N1–N4 rules: R prevalence 1% (Wilson 95% CI 0.18–5.45%);
whole-cell mean relative saving at K=8 is 0.27% (95% CI −0.06–0.93%), so
positive whole-cell gain is not established. `NATURAL_NO_HARM` means every K
cleared the predeclared −2% lower-CI threshold, not that overhead is zero.

Scientific scope: the finite fixed-beam candidate family and the measured
datasets. Statistical independence of the simulated natural pool is not
formally verified. The C timing region omits the LP audit and implements
HYBRID as EARLY; these facts and the original input dtypes must be reported
when comparing runtimes.
