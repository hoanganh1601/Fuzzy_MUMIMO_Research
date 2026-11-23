# V16.2 status record

This note was written after the runs. It is retrospective, not a new protocol
or authorization to change the frozen V15.2 lock or natural sampling rule.

1. `check`: 216/216 C self-test, 32/32 unit tests; V15.2 lock reusable as-is.
2. `compiled`: C16_DEV, C16_DM, C16_3GPP pass C1–C4 with zero numeric events.
3. `model`: M16_PY and M16_C fitted on development and evaluated on both test
   sources. K=10 and K=12 are extrapolations.
4. `natural-protocol`: frozen before the 100-group sample was taken.
5. `natural`: one sample from a new 200-group, single-ISD Sionna UMi pool.
   Initial script run stopped on incomplete provenance before timing; metadata
   was corrected and the same sample completed. NP16 returned
   `NATURAL_NO_HARM`, not a confirmed positive whole-cell gain. N4 was not
   evaluable because R contained only one group.

No new sample was drawn after observing the result. The source-level
statistical-independence claim remains unverified.
