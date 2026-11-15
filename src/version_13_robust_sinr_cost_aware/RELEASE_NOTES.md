# V13 release notes

1. Added pre-beam CSI norm lower bound valid for uncertainty sets containing zero error and normalized beams, with fail-open numerical guard.
2. Added cached robust F,u path, using the same original power/LP audit while avoiding duplicated beam construction on surviving candidates.
3. Added development-only cost-aware policy selection (paired group bootstrap with minimum improvement threshold); baseline fallback if selection not supported.
4. Added CP08 105-candidate cross-check per geometry against exhaustive oracle.
5. Added independent test overlap detection by group labels and exact channel content; full spatial/temporal independence still requires dataset provenance verification.
6. Added CP01–CP08, SHA256 and resumable per-geometry tasks.
7. Smoke test confirmed PASS execution, exact oracle matches, and STOP-style fallback. No DeepMIMO or 3GPP performance validation is included.

Known restrictions: fixed K=4 and seven ZF/RZF options; group-bootstrap is descriptive if source grouping does not ensure independence; wall-clock estimates depend on hardware and loaded system conditions; LP tolerance is inherited from V12.
