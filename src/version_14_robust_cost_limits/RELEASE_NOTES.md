# V14 release notes
- Reuses V13 reference oracle and robust SINR model; does not refine CSI margin.
- Adds candidate-level solver-cost profiling, group-aware fit/validation, simple cost-aware conditional switching and a frozen decision lock.
- Adds test-time cost-inclusive paired repeated timing, 105-candidate oracle/certificate audit per test geometry, and group-bootstrap GO/STOP.
- Adds an explicit frozen-lock transfer path for a second independent channel source.
- The examples are synthetic. No scientific performance result on new DeepMIMO or Sionna/3GPP has been generated in this release.
- Current scope: K=4, seven ZF/RZF beams per subset, finite approximation robust SINR.
