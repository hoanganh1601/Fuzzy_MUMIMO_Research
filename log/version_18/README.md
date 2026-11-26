# Version 18 observed results — LRS generality

This is a retrospective record of the V18 run completed on 2026-11-26. The
frozen protocol is `runs/V18_GENERALITY/G00_protocol.json`. The official
handover archive is `reports/KET_QUA_V18_20261126.zip`; it contains G00–G10,
all 18 G01 development JSONL files, all 18 G03 held-out JSONL files, scenario
validation records, the hardware bundle and `NOTES.txt`.

| Checkpoint | Result |
|---|---|
| CK0 | Native self-test 576 configurations × 7 schedulers; 96 oracle checks; 8/8 unit tests |
| CK1 | Three new UMi/UMa/RMa sets accepted, each `(150, 32, 8)` complex64 |
| CK2 | Protocol fixed: 27 configurations, 338 development and 746 held-out drops |
| CK3/CK4 | 18 M=8/M=16 maps locked; every map has `only_top_bin_active=true` |
| CK5/CK6 | 80,568 held-out raw records; 15 PASS and 3 FAIL |
| CK7 | Stage closure 0.942–0.976; held-out cost-model R² 0.980 |

G1 exactness, G2 in-region gain and G4 accuracy passed in all 18 evaluable
configurations. The three failures were solely the frozen G3 outside-region
loss gate:

| Configuration | G3 worst CI lower bound | Gate |
|---|---:|---:|
| `M8_G6_E0.08` | −4.97% | > −2% |
| `M16_G0_E0.04` | −2.29% | > −2% |
| `M16_G6_E0.02` | −3.00% | > −2% |

Across all held-out drops, LRS mean relative saving at K-max ranged from about
56% to 79%. Exact schedulers retained the DCS decision; GREEDY was faster in
several settings but was not decision-exact. The hierarchical analysis showed
substantial scene clustering (ICC about 0.57–0.67), so adding independent
scenes matters more than adding drops within the same scene.

Nine M=32 configurations are `NOT_EVALUABLE`: the supplied default protocol
used all new 32-antenna sets as held-out and did not introduce a separate
32-antenna development set. Hardware results are from one Intel i9-10900K
machine only. The held-out cost-bound validity was 94.48%, below 95%. These
limitations prevent a universal generality or hardware-independence claim.

Real NPZ files, generated channel pools, native binaries, PID files and
expanded raw G01/G03 files remain outside the selected Git tree. Raw files are
preserved inside the official ZIP. `ARTIFACT_SHA256.csv` hashes the curated
artifacts stored in this directory.
