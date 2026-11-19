# V151_DM run card

- Code version: V15.1
- Development: DeepMIMO `asu_campus_3p5`, 41 geometries/groups
- Test: DeepMIMO `city_4_phoenix_3p5`, 11 geometries/groups
- Development SHA-256: `4677e7f39255dc2cf97ea5aa0c52c553aabebb058c15c0184e5badb6a697af8a`
- Test SHA-256: `16788e7691cef03444db953dcafa2a65cf6eaf493664d8d27ea4f72c05cae574`
- Frozen lock SHA-256: `9bf4a1b5475cd15e3273b1b3a299eeb55f8f463f3c8353034e3b12dadad2e26d`
- Group overlap: 0
- Exact-channel overlap: 0
- Oracle mismatch: 0
- K=8 mean runtime saving: -0.0606 ms (-0.32%)
- Decision: `STOP_NO_PREDICTABLE_BREAK_EVEN`

E3 exactness passed. E1, E2, and E4 failed; the test contained no ER2
geometry, so the frozen EARLY/HYBRID cells did not activate.

