# Version 15 smoke plan record

This record follows the smoke section of the supplied IEEE guide. It is a
software acceptance workflow, not an independent scientific validation plan.

1. Preserve the code modules, requirements, synthetic generator, fixtures,
   provenance, unit tests, smoke launcher, and guide required by the PDF.
2. Run all four supplied unit tests.
3. Generate deterministic eight-user synthetic development and test fixtures.
4. Run the single entrypoint with `K=4,6,8`, `L=3`, four geometries per source,
   two timing repetitions, and smoke mode enabled.
5. Retain the 12 top-level CP00--CP09 artifacts and exclude per-geometry task
   caches, logs, PIDs, environments, and all real-data experiments.
6. Require zero oracle mismatch and valid checkpoint hashes.
7. Report the result only as `SMOKE_ONLY`; do not claim DeepMIMO/3GPP evidence,
   statistical independence, or runtime superiority.
