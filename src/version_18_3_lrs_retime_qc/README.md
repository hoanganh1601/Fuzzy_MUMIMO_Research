# Version 18.3 — timing QC and the M32 re-timing run

This is an archival copy of the code after applying the teacher's V18.3 patch
to V18.2. The modules under `code/` are unchanged. The patch updates
`v18/run_v18.py`, `v18/run_m32.py` and `v18/README.md`, and adds the QC test and
the re-timing guide. The teacher's accompanying note is
[`RELEASE_NOTES_UPSTREAM.md`](RELEASE_NOTES_UPSTREAM.md).

The authoritative workflow is
[`v18/HUONG_DAN_V18_M32_RETIME.md`](v18/HUONG_DAN_V18_M32_RETIME.md). To replay
it, place this source in an `lrs-mumimo` checkout with the original
`outputs_v18_m32/`, the V18/V15.2 reference files under `results/`, and the
channel datasets recorded by V18.2. The re-timing run writes to a separate
`outputs_v18_m32_retime/` directory. No real channel NPZ is stored in Git.

The selected output, retrospective QC table and complete raw measurement ZIP
are in [`../../log/version_18_3`](../../log/version_18_3). Only the two
predeclared timing-QC failures were re-timed. Both re-timed runs passed QC and
matched the original decisions, allowing the locked reporting rule to select
their new runtime endpoints. The original V18.2 result is preserved in
[`../../log/version_18_2`](../../log/version_18_2).
