# Version 18 — LRS generality study

This directory is a self-contained archival copy of the V18 package. Run all
commands from this directory so that `v18/` can import the published modules
under `code/` without modifying them.

V18 studies whether the load-routed screening (LRS) break-even rule transfers
across antenna counts, SINR targets, uncertainty levels and channel scenes. It
also compares DCS, PBS, LRS, LRSPUB, cardinality-bounded and heuristic
schedulers using the same compiled core.

The authoritative Vietnamese workflow is
[`v18/HUONG_DAN_V18.md`](v18/HUONG_DAN_V18.md). Real NPZ channel matrices are
not stored in Git. The full result bundle, including all raw G01/G03 JSONL
measurements, is under
[`../../log/version_18/reports`](../../log/version_18/reports).

Observed result on the recorded machine:

- 18 M=8/M=16 configurations were evaluable: 15 PASS and 3 FAIL.
- G1 exactness, G2 in-region gain and G4 sign prediction passed in all 18.
- G3 failed for `M8_G6_E0.08`, `M16_G0_E0.04` and `M16_G6_E0.02`.
- M=32 was `NOT_EVALUABLE` because the frozen protocol contained no
  independent 32-antenna development set.
- Only one hardware bundle was available, so cross-machine transfer was not
  established.

Do not describe V18 as a universal PASS. See
[`../../log/version_18/README.md`](../../log/version_18/README.md) for the
recorded scope and limitations.
