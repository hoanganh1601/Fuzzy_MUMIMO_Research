# Version 12 run log

Version 12 records the final robust-SINR validation workflow on a new DeepMIMO
scenario, a separately generated Sionna 3GPP UMi source, and the prescribed
boundary stress branch.

- [`BORDER_V12`](runs/BORDER_V12/RUN.md): 1,020 boundary cases, zero false
  prunes, 323 fail-open cases, outcome `PASS`.
- [`DM_V12`](runs/DM_V12/RUN.md): 160 geometries in 40 spatial groups from
  `city_37_seoul_3p5`; 16,800 candidates, zero false prunes, but no FAST
  runtime advantage.
- [`GPP_V12`](runs/GPP_V12/RUN.md): 160 Sionna UMi drops; 16,800 candidates,
  zero false prunes, but no FAST runtime advantage.
- [`manuscript_gate.json`](reports/manuscript_gate.json):
  `STOP_MANUSCRIPT_NOT_LOCKED` because neither source established the required
  positive runtime interval.

The 21 checkpoint files are bundled in
[`Results.Robust.SINR.Final.Validation.V12.zip`](reports/Results.Robust.SINR.Final.Validation.V12.zip).
Per-geometry tasks, console logs, PID files, virtual environments, downloaded
scenarios, topology arrays, and channel matrices are excluded.

The DeepMIMO test uses a distinct Seoul ray-tracing scenario and non-overlapping
group identifiers relative to the ASU development data. These controls support
separation but do not prove statistical independence. The Sionna protocol was
locked before generating and evaluating its own dataset, but after the DeepMIMO
result was observed; the provenance records this limitation explicitly.
