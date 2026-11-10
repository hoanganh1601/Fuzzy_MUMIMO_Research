# Robust SINR Feasibility Screening — consolidated R2 (2026-11-06)

**Người chạy trên Windows: đọc `HUONG_DAN_NCS.md` trước** (check_env → CHAY_TOAN_BO.ps1).

Supersedes the packages of 2026-11-01, 11-02, 11-04 and 11-06. Read `CHANGELOG_R2_20261106.md` first (R2 changes, rehearsal results, manuscript implications, commands for real data), then `CHANGELOG_R1_20261106.md`.

**One-command reproduction of manuscript Section V:** `python code/run_manuscript.py --help`.

**Rehearsal:** `rehearsal/` holds a full A–D run on SYNTHETIC channels from `code/make_synthetic.py` (NOT DeepMIMO/3GPP) — pipeline verification only.

## Original package notes (2026-11-06)

**Scope:** fixed CSI uncertainty margin, K=4, finite 15 subsets × 7 ZF/RZF beam choices. This package **does not** optimize CSI margin and **does not** make an outage guarantee.

## Contents
- `code/reference_model.py`, `ablation_audit.py`, `ablation_certified.py`: original v10-compatible mathematical model and safe screening.
- `code/boundary_stress.py`: controlled algebraic coupling/power boundary and channel-derived near-power-boundary checks; fail-open accounting.
- `code/independent_validation.py`: lock-first, provenance-audited evaluation against exhaustive oracle and cardinality-only; paired repeated runtime benchmark, per-candidate audit, grouped bootstrap.
- `docs/GUIDE_BOUNDARY_INDEPENDENT_IEEE_VI.pdf` and `.tex`: Vietnamese IEEE single-column instructions.
- `tests/`: 23 automated unit tests (8 original, 11 R1 regression, 4 R2 pipeline).
- `smoke.npz`, `provenance_example.json`: **SYNTHETIC/EXAMPLE ONLY**, not validated real DeepMIMO/3GPP.

## Core commands

```bash
python -m pip install -r code/requirements.txt
python -m unittest discover -s tests -v
python code/boundary_stress.py --stage all --run-id BOUNDARY01 --dataset /path/new_independent.npz --limit 20
python code/independent_validation.py --stage lock --run-id DM_NEW01
python code/independent_validation.py --stage preflight --run-id DM_NEW01 --dataset /path/new_independent.npz --provenance /path/provenance.json
python code/independent_validation.py --stage scan --run-id DM_NEW01 --dataset /path/new_independent.npz --provenance /path/provenance.json
python code/independent_validation.py --stage report --run-id DM_NEW01 --dataset /path/new_independent.npz --provenance /path/provenance.json
```

For a separate Sionna 3GPP run, use a new run-id and identical frozen parameters; update `provenance.json` (source `Sionna_3GPP`). Avoid opening test data to tune parameters. Optional `--development-groups groups_dev.json` rejects overlapping group labels; users must establish physical and scenario separation externally.

**Resumption:** rerun `--stage scan` with unchanged paths/configuration/code and same `run-id`. Existing tasks are checked against a signature. Changing source or arguments requires a different run-id. Never override a locked test run.

**Changes in R1 (2026-11-06):** see `CHANGELOG_R1_20261106.md`. Key points: shared tolerances (`POWER_REL_TOL`, `PRUNE_REL_MARGIN`) in `reference_model.py`; `CARDINALITY_ONLY` performs no screening work; exact rational reference (no `mpmath`); A1 families all have a feasible side and PASS requires fail-open activity; analysis parameters locked in I-CP00. Earlier smoke outputs and locks are invalidated.

**Critical limitations:** Group names and provenance statements do not prove statistical independence; exact rational recheck on derived double F/u is not formal interval arithmetic. Runtime on one run is not a deployment prediction. Tests only claim exactness within the finite codebook.
