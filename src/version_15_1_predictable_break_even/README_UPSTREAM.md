# Robust MU-MIMO V15.1 — predictable break-even of pre-beam screening (2026-11-18)

**Read `HUONG_DAN_V15_1.md` first** (run guide, Vietnamese). Main entry: `code/run_experiment.py`; Windows one-command run: `scripts/run_v15_1.ps1`; smoke: `scripts/smoke_v15_1.ps1`.

V15.1 changes vs V15: cells by `early_ratio` (ER0 < 0.1 <= ER1 < 1 <= ER2); robust pre-beam bound for EARLY; predeclared primary endpoints E1-E4 per source (break-even at K=8, increasing trend in K, exactness, predictability) and a `combine` stage requiring GO on both DeepMIMO and 3GPP with the same lock; `preflight` reports the early_ratio distribution of the development set; machine/library/thread information in the signature (BLAS threads pinned to 1); UTF-8 I/O; deterministic tie rule; feature cost charged to CARD-routed geometries; development group check at develop/lock; `export_users.py` converter; mpmath import made lazy. Physics, beams, CSI radius, oracle and post-beam certificates are unchanged.

`examples/REHEARSAL_GO` and `examples/REHEARSAL_STOP` are SYNTHETIC rehearsals proving that the gate can return both outcomes; they are not results. `docs/GUIDE_...pdf` and `paper/` are the V15 versions (unchanged).

---
## Previous README (unified package)

# Robust MU-MIMO — single reproducible research package (2026-11-18)

## One active experimental entrypoint

`python code/run_experiment.py` — development, lock, test, report for K=4,6,8 and L=3,5,7. The other four core `.py` files implement its physics and screening as dependency modules, **not separately maintained experimental versions**. `make_synthetic.py` and `pack_deepmimo_users.py` are data utilities. The reference model is unchanged relative to V15; historical archive evidence is not silently rerun.

**Working paper:** `paper/main.tex` and `paper/main.pdf`. V10–V14 verified results are integrated, including negative runtime results; V15 is protocol only and has no official measurements yet. Evidence archives are in `evidence/source_archives/`; `evidence/RESULTS_ARCHIVE_INDEX.csv` records SHA-256.

## Quick start (Windows PowerShell)

```powershell
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
.\scripts\smoke_v15.ps1
```

Official run:

```powershell
.\scripts\run_v15.ps1 -Development data\development.npz -Test data\new_deepmimo_test.npz -DevProvenance data\dev_provenance.json -TestProvenance data\test_provenance.json -RunId DM_V15_OFFICIAL
```

Your official inputs must actually exist; smoke NPZ files are not DeepMIMO or 3GPP results. For an independent 3GPP run, use the same development input and the **same frozen lock**, a new `RunId`, the 3GPP test NPZ/provenance, and `-LockFrom <first-run>/CP03_locked_cells.json`.

## Input, replay and scope

- `H`: complex, finite, shape `(N,M,Kmax)` with M >= 8 and Kmax >= 8; `groups`: N labels of separate groups, ideally with position/scenario metadata.
- `dev_provenance.json` and `test_provenance.json` must contain `source`, `scenario`, `group_definition`, `independence_basis`, `prior_use`.
- All choices of K, beam counts, CSI margin, policies and acceptance thresholds are locked before accessing test.
- CP00–CP09 are created within `outputs/<run-id>`. Per-geometry checkpoints in `tasks/` use atomic writes; rerunning the same stage resumes. Code or dataset changes require a new run-id.
- `--profile-candidates` is costly, especially K=8, and is an optional profiling pass. All-subset oracle also grows exponentially: K8, L7 entails 1785 candidates **per geometry**, plus repetitions.
- The independent test must not reuse development/tuning geometries. Group IDs and hashes detect exact collisions but cannot prove statistical independence.

## Manuscript scope

Evidence from V10–V14 is observational and must not be represented as V15 measurements. Baselines: CARD = cardinality-only, EARLY = prebeam lower bound, CACHED = postbeam screening with reused coefficients, HYBRID = combined.

The mathematical guarantee of screening applies only to **the chosen conservative fixed-beam robust SINR power-control model** and a finite set of ZF/RZF beam-generating rules. It does not establish global optimality over unrestricted continuous precoders, nor a certified interval-arithmetic floating-point proof.

**Unified module names:** `run_experiment.py` (only active experiment entrypoint), `robust_model.py` (fixed-beam model/oracle), `screening_bounds.py` (screening bounds), `certified_screening.py` (fail-open/certificate diagnostics), `screening_policy.py` (cost-aware helpers). Function bodies are inherited from V15; module renaming only.
