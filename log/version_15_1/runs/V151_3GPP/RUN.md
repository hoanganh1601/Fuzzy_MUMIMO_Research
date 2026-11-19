# V151_3GPP run card

- Code version: V15.1
- Test: Sionna 2.2.0, 3GPP TR 38.901 V19.2 UMi, 15 geometries/groups
- Test SHA-256: `0b4f0de1c31acfe06181e9e21190e784b77cf54c399dbb1a4d43b473795a0ba8`
- Protocol SHA-256: `dda0dee2a190398766c2f18b73c6434d57d60b226cf3ecd7f81568df373ffd41`
- Frozen lock SHA-256: `9bf4a1b5475cd15e3273b1b3a299eeb55f8f463f3c8353034e3b12dadad2e26d`
- Group overlap: 0
- Exact-channel overlap: 0
- Oracle mismatch: 0
- K=8 mean runtime saving: -0.0705 ms (-1.22%)
- Decision: `STOP_NO_PREDICTABLE_BREAK_EVEN`

E3 exactness passed. E1, E2, and E4 failed; the test contained no ER2
geometry, so the frozen EARLY/HYBRID cells did not activate.

