# Run card: SYN_REHEARSAL_D_20261110

- Workflow: locked independent-validation pipeline rehearsal
- Dataset: `synthetic_test_seed202.npz`, shape `(160,16,4)`, 32 spatial groups
- Dataset SHA-256: `04ee0d15c1d7673dd58698721bf8a670fad7a5de380fd470308e669cb0c51ad5`
- Provenance source: `other_independent`; different synthetic generator seed, rehearsal only
- Status: `AUDIT_PASS`; 16,800 candidates, zero false prunes

ALL saved 17.63125 solver calls per geometry, but mean runtime was 13.9126 ms versus 13.1913 ms for cardinality-only. Runtime reduction was -5.47%; paired saving CI95 was `[-0.8417,-0.5985]` ms and `observed_runtime_go=false`.

This is not a physical independence claim and must not be reported as independent DeepMIMO or Sionna 3GPP validation.
