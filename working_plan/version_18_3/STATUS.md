# V18.3 M32 timing QC status (retrospective, 2026-11-27)

The one-time re-timing rule was declared before measurement in
`../../log/version_18_3/runs/V18_M32_RETIME/G00c_retime.json`. This status
file was written after the run.

The original M32 run remains in `../../log/version_18_2/`. Two original
configurations failed auxiliary timing QC and were re-timed once on the same
machine and held-out drops. The probe passed; both re-timed configurations
passed QC and matched all original decisions. The locked reporting rule
therefore selects their new runtime endpoints. The other seven original M32
configurations remain untouched. The operator did not manually stop
background tasks, as recorded in `NOTES.txt`.
