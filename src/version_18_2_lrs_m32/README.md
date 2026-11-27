# Version 18.2 — LRS generality at M = 32

This directory archives the code used for the separate M32 extension. It
preserves the V18 modules under `code/` and `v18/`, and adds `v18/run_m32.py`
plus `v18/HUONG_DAN_V18_M32.md`. For a rerun, place this source in a
`lrs-mumimo` checkout with the V18 and V15.2 reference files under `results/`
and supply the channel datasets listed in the guide. The M32 workflow writes
to `outputs_v18_m32/` and does not alter the frozen V18 run.

The authoritative workflow is
[`v18/HUONG_DAN_V18_M32.md`](v18/HUONG_DAN_V18_M32.md). Real channel NPZ files
are excluded from Git; their hashes are recorded in
[`../../log/version_18_2/runs/V18_M32/DATASETS_M32.csv`](../../log/version_18_2/runs/V18_M32/DATASETS_M32.csv).
The selected results and complete raw measurement ZIP are in
[`../../log/version_18_2`](../../log/version_18_2).

On the recorded machine, all nine M32 configurations passed G1 exactness,
G2 in-region gain and G4 load-rule accuracy. Four passed all gates; five
failed the frozen G3 outside-region loss criterion. The held-out sets had
previously been observed at M=8/M=16, but not timed or used for development
at M=32. See the run record for the scope and limitations.
