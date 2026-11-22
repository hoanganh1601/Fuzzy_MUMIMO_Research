# V16.1 status record (written after the compiled run)

This retrospective note is not a pre-registered protocol. The supplied procedure is `src/version_16_1_numeric_agreement/HUONG_DAN_V16.md`.

1. `check`: complete; 31/31 unit tests passed and V15.2 lock reused.
2. `compiled`: complete; C16_DM returned GO, C16_DEV and C16_3GPP returned STOP because numeric-event fractions exceeded the 1% C1 gate.
3. `model`: not run.
4. `natural-protocol` and `natural`: not run.

The two STOP decisions must not be converted to GO by changing the threshold after seeing the results. Preserve the V16 and V15.2 snapshots. Record any future numerical change as a new code version with new run IDs and provenance.
