# Robust MU-MIMO V16 — extension of the locked V15.2 study (2026-11-20)

**Read `HUONG_DAN_V16.md` first.** Windows runner: `scripts/run_v16.ps1` (phases check, transfer, compiled, model, natural-protocol, natural).

V16 adds, WITHOUT modifying the five V15.2 core modules (so the V15.2 lock stays valid):
- `code/native/screen_core.c`, `code/native_search.py`, `code/compiled_benchmark.py` — compiled CARD / EARLY / ROUTED search (C via ctypes), oracle-checked, endpoints C1-C4;
- `code/breakeven_model.py` — analytical break-even model (Lemma 1: early_ratio <= 1 => no rejection; Lemma 2: monotone rejected fraction; NNLS cost model fitted on development, validated on tests);
- `code/natural_prevalence.py` — natural-prevalence test (protocol frozen before a simple random sample; endpoints N1-N4);
- `code/lock_transfer.py` — checks lock reusability on the current machine and, for machine-only differences, transfers the lock with identical policy cells.

`examples/REHEARSAL_V16_SYNTHETIC` holds rehearsal summaries on synthetic channels (not results).

---
# Robust MU-MIMO V15.2 — predictable break-even of pre-beam screening (2026-11-19)

**Read `HUONG_DAN_V15_2.md` first.** Windows: `scripts/run_v15_2.ps1` in three phases (develop -> select -> test); smoke: `scripts/smoke_v15_2.ps1`.

V15.2 vs V15.1: primary endpoints P1-P4 inside the predicted region R with an INCONCLUSIVE gate (>= 10 region groups); stage `test-preflight` (covariates only, before any runtime) with `TEST_SELECTION_LOG.csv`; `code/stratify_test_pool.py` (covariate-stratified sealed test sets); fit/validation split stratified by K_max early_ratio cell; development >= 80 groups with >= 20 ER2 groups; distance filter in `pack_deepmimo_users.py`. V15.1 all-geometry endpoints remain as secondary output. Physics, beams, CSI radius, oracle and screening bounds are unchanged from V15.1.

`examples/REHEARSAL_SYNTHETIC` is a synthetic rehearsal (not a result). `paper/` and `docs/GUIDE_...pdf` are still the V15 versions.

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
