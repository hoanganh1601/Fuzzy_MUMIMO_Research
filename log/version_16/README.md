# Version 16 run status — stopped during compiled benchmark

The `check` phase passed 30/30 tests and confirmed the frozen V15.2 lock could be reused. The next phase, `compiled`, stopped in its first run (`C16_DEV`) at geometry 8, K=6, L=3, CARD with `COMPILED MISMATCH`.

The two results agreed on subset `24`, alpha `0.01` and cardinality `2`, but reported `p_req_w` of `0.379298587602968` (compiled) and `0.37929854287093945` (Python oracle). The absolute difference is about `4.47e-8 W`. This failed the existing comparison and raised `AssertionError`; the PowerShell runner then exited with code 1.

`V16_compiled.log` is the original console log. `C16_DEV_CC00_manifest.json` is the only top-level C16 checkpoint produced before the error. Per-geometry task caches and PID files are omitted. `C16_DM`, `C16_3GPP`, `model` and `natural` have not completed, so no official V16 runtime or break-even result is claimed. Section 7 of `HUONG_DAN_V16.md` says to stop and send the log when this mismatch occurs.
