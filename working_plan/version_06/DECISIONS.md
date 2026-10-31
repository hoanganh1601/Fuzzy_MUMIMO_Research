# Version 06 decisions

## D001 — Preserve absolute DeepMIMO scale

No channel normalization is applied. Noise and power units must therefore be explicit.

## D002 — Use `2e-13 W` receiver noise

The run uses an approximately `-97 dBm` 10 MHz-equivalent noise assumption. This differs from the smoke-oriented code default `1e-9 W`.

## D003 — Treat infeasibility as failure

An episode fails if robust power allocation is infeasible or if any SINR violation occurs.

## D004 — Do not retune after CP05

The observed 39/80 calibration failures close this confirmatory run. Any new scheduling, grouping, SINR, noise or power rule requires a new version/run and fresh confirmatory groups.
