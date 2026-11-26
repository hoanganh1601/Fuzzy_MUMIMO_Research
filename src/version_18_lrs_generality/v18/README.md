# V18 — generality study of load-routed screening (separate from the published code)

`v18/` only reads `code/`; it does not modify any module recorded in the published policy map. Outputs go to `outputs_v18/`.

| File | Role |
|---|---|
| `run_v18.py` | stages `selftest, protocol, develop, lock, test, analyze, stages, hwbundle, hwcompare` (`python v18/run_v18.py --help`) |
| `native/screen_v18.c`, `native18.py` | compiled DCS, PBS, routed LRS, CBD and CBPBS (cardinality bound of the Corollary), ACS, ACSSTOP, GREEDY; optional stage timing (`-DSTAGE_TIMING`); per-operation micro-benchmarks |
| `v18_stats.py` | stratified and two-level bootstrap, paired sign-flip permutation test, ICC and design effect, break-even threshold estimate |
| `gen_sionna_3gpp.py` | fresh UMi/UMa/RMa channel sets from a frozen scenario specification (Sionna) |
| `tests/test_v18.py` | unit tests |
| `HUONG_DAN_V18.md` | run guide with checkpoints (Vietnamese) |

The self-test verifies that DCS and PBS of `screen_v18.c` reproduce `code/native/screen_core.c` (decisions and solver-call counts), that CBD, CBPBS and ACS return the DCS decision, that the cardinality bound is consistent with the pre-beam bound, and a sample of decisions against the Python oracle.
