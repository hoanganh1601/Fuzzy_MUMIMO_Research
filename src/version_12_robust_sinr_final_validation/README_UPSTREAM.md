# Robust SINR user scheduling — final validation V12 (NOT manuscript locked)

## Purpose
Follow-on to R2.V11. Holds the fixed CSI uncertainty margin and the 15 user subsets × 7 ZF/RZF candidates for K=4. The independent exhaustive reference is mandatory. **FAST and LITE are experimental screening variants**; a runtime speedup is not assumed.

## Files
- `code/final_runtime_validation.py`: frozen, paired, repeated wall-time experiment on new channel samples; compares FAST, LITE and the strong CARDINALITY_ONLY implementation. Exports CP00–CP07. Stops on oracle mismatch or false certificate.
- `code/boundary_stress.py`: near-boundary tests using development/synthetic input; exports B-CP00–B-CP03.
- `code/manuscript_gate.py`: read-only cross-source gate, requiring verified DeepMIMO, 3GPP and channel-derived boundary data.
- `scripts/run_validation.ps1`: PowerShell orchestration for lock → preflight → scan → report; restart by rerunning the same command.
- `docs/FINAL_VALIDATION_GUIDE_IEEE_VI.tex` and PDF: Vietnamese IEEE single-column methodology and instructions.
- `manuscript_working/`: R2.V11 working draft retained only as context; NOT updated with unverified new results.
- `data/synthetic_smoke/`: synthetic fixture **NOT scientific evidence**. Template provenance files use `created_before_test:false` until verified by the user.
- `smoke_results/V12_SMOKE/`: 4 synthetic geometries used to exercise code; outcome must remain SMOKE_ONLY.

## Quick start (PowerShell, in extracted root)
```powershell
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
python code/boundary_stress.py --stage all --run-id BORDER_V12 --dataset data/development_stress.npz --limit 50
.\scripts\run_validation.ps1 -Source DeepMIMO -Dataset data\deepmimo_new.npz -Provenance data\deepmimo_provenance.json -DevelopmentGroups data\development_groups.json -RunId DM_V12
.\scripts\run_validation.ps1 -Source Sionna_3GPP -Dataset data\3gpp_new.npz -Provenance data\3gpp_provenance.json -RunId GPP_V12
python code/manuscript_gate.py --deepmimo-dir outputs/DM_V12 --threegpp-dir outputs/GPP_V12 --boundary-dir outputs/BORDER_V12 --out outputs/manuscript_gate.json
```
Replace example paths with actual prepared source data. `H` must have complex shape `(N,M,4)` and `groups` length `N`. Do not claim source independence based solely on JSON entries. The generated channels and full independent validation have **not** been run in this environment.

## Scientific controls
V11: 160/160 exact matches; 55.85% fewer full solver calls; however all certificates ran **5.27% slower** than cardinality-only in the repeated timing audit. The latest V12 smoke has 0 false certificates among 420 checked candidates, but its runtime CI is not suitable for a positive claim.

GO requires: no false certificates; exact match for every geometry; positive lower 95% cluster-bootstrap bound for FAST minus cardinality-only runtime saving on *both new sources*; passed channel-derived boundary audit; valid provenance and code/data hashes. If unmet, STOP and report no verified computational superiority. Passage of these technical gates is not automatic journal-readiness or proof of statistical independence.
