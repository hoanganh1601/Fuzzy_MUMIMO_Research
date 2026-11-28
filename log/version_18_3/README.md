# Version 18.3 M32 timing QC and re-timing result

This is a retrospective record of the V18.3 run on 2026-11-27. The QC rule
and one-time re-timing rule were declared in
`runs/V18_M32_RETIME/G00c_retime.json` before new timing. The original V18.2
measurements remain in `../version_18_2/`; they were not overwritten.

The retrospective QC check in `reference/QC_TIMING_RETROSPECTIVE.csv` found
that 18/18 M8/M16 configurations and 7/9 M32 configurations met the auxiliary
1% identical-path discordance threshold. The two M32 failures were
`M32_G10_E0.02` (248/2700, 9.19%) and `M32_G10_E0.04` (160/2700, 5.93%).

The code checks passed 11/11 tests. One machine-stability probe passed with
0/216 discordant pairs and median absolute log ratio 0.001553. The re-timing
run measured the same 450 held-out drops for each of the two configurations.
The output is in `runs/V18_M32_RETIME/`; the full raw-measurement archive is
`reports/KET_QUA_V18_M32_RETIME_20261127.zip`.

| Configuration | Original QC | Re-timed QC | Decisions identical | G3 worst CI lower bound | Reported runtime |
|---|---:|---:|---|---:|---|
| `M32_G10_E0.02` | 9.19% | 0.11% | Yes | −31.9% → −1.3% | Re-timed; G3 PASS |
| `M32_G10_E0.04` | 5.93% | 0.04% | Yes | −17.1% → −1.5% | Re-timed; G3 PASS |

Both pass the frozen selection rule: re-timed QC ≤1% and all decisions match
the original run. G1 and G4 decision inputs stay with the original run. Under
that rule, six of the nine M32 configurations meet G1–G4; the three remaining
G3 failures in V18.2 are unchanged. QC is an auxiliary check; the G1–G4
thresholds were not changed.

The operator recorded that no background tasks were manually stopped before
re-timing. The probe and re-timed QC passed, but this deviation from the
guide's machine-preparation instruction remains in `NOTES.txt`. Only three
channel scenes were available, and the M32 held-out sets had previously been
timed at M8/M16. These results do not establish universal transfer or
independent hardware validation.

Expanded G01/G03 records are inside the ZIP rather than the selected Git
tree. The ZIP contains no log, PID, native binary or NPZ. `ARTIFACT_SHA256.csv`
lists checksums for the selected files and archive.
