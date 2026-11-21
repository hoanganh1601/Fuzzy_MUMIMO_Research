# V16 status record (written after the failed run)

This is a retrospective record, not a pre-registered protocol. The experimental procedure is the supplied `src/version_16_compiled_break_even/HUONG_DAN_V16.md`.

1. `check`: complete; 30/30 unit tests passed and V15.2 lock reusable.
2. `compiled`: stopped in `C16_DEV` on an oracle comparison mismatch at geometry 8, K=6, L=3, CARD.
3. `model`: pending because compiled results are unavailable.
4. `natural-protocol` and `natural`: pending.

Resume only after the discrepancy is reviewed and the code, oracle comparison and run provenance are agreed. Preserve the frozen V15.2 source, lock and prior test data.
