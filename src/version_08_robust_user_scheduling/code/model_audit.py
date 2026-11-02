"""G1 checks from the guide, separate from measured scheduling algorithms."""
import numpy as np
from scipy.optimize import linprog

import admission_beam as engine


def audit_candidates(H, tasks, cfg, verbose=False):
    summary = {
        "gate": "G1_PASS", "candidate_count": 0, "lp_checks": 0,
        "budget_monotonicity_checks": 0, "extra_engine_solve_calls": 0,
        "max_relative_lp_gap": 0.0, "max_scaled_analytic_violation": 0.0,
        "max_scaled_lp_violation": 0.0,
        "audit_calls_excluded_from_algorithm_calls": True,
        "budget_test": "Below/above required power for stable candidates; half/double Pmax for coupling/zero gain. Audit only, not policy tuning.",
    }
    for task in tasks:
        i = task["geometry"]
        for row in task["rows"]:
            users = [int(k) for k in row["subset"]]
            alpha = row["alpha"]
            context = f"geometry={i}, subset={row['subset']}, alpha={alpha:g}"

            def require(condition, message):
                if not condition:
                    raise ValueError(f"G1 {context}: {message}")

            h = H[i][:, users]
            W = engine.get_beam(h, alpha)
            require(W is not None, "beam rank/numerical condition requires review")
            require(np.allclose(np.linalg.norm(W, axis=0), 1, rtol=1e-10, atol=1e-12),
                    "beam columns are not unit norm")
            gain = np.abs(h.conj().T @ W)
            radius = cfg["q"] * cfg["sigma"] * np.linalg.norm(h, axis=0) / np.sqrt(h.shape[0])
            a = np.maximum(np.diag(gain) - radius, 0) ** 2
            status = row["status"]
            if np.any(a <= 0):
                require(status == "ZERO_ROBUST_DIRECT_GAIN", "zero direct-gain classification mismatch")
                intrinsic = True
            else:
                F = cfg["gamma"] * (gain + radius[:, None]) ** 2 / a[:, None]
                np.fill_diagonal(F, 0)
                u = cfg["gamma"] * cfg["noise"] / a
                require(np.isfinite(F).all() and np.isfinite(u).all(), "nonfinite coefficients")
                require(np.all(F >= 0) and np.all(u > 0), "invalid F/u signs")
                rho = float(np.max(np.abs(np.linalg.eigvals(F))))
                require(row["rho"] is not None and np.isclose(row["rho"], rho, rtol=1e-9, atol=1e-11),
                        "saved spectral radius mismatch")
                intrinsic = rho >= 1 - 1e-10
                if intrinsic:
                    require(status == "COUPLING_RHO_GE_ONE", "coupling classification mismatch")
                else:
                    p = np.linalg.solve(np.eye(len(u)) - F, u)
                    require(np.isfinite(p).all() and np.min(p) >= 0, "invalid analytic power")
                    req = float(np.sum(p))
                    require(req > 0 and np.isclose(row["p_req_w"], req, rtol=1e-8, atol=0),
                            "saved required power mismatch")
                    scale = max(float(np.max(u)), 1e-20)
                    analytic_residual = float(np.min(p - F @ p - u))
                    analytic_violation = max(0.0, -analytic_residual / scale)
                    require(analytic_violation <= 1e-7, "analytic constraint residual failed")
                    require(row["residual"] is not None and
                            abs(row["residual"] - analytic_residual) <= 1e-7 * scale,
                            "saved analytic residual mismatch")
                    # Audit all stable candidates, including those over baseline budget.
                    lp = linprog(np.ones(len(u)), A_ub=F - np.eye(len(u)),
                                 b_ub=-u / scale, bounds=(0, None), method="highs")
                    require(lp.success, f"independent scaled LP failed: status={lp.status}")
                    lp_p = lp.x * scale
                    require(np.isfinite(lp_p).all() and np.min(lp.x) >= -1e-8,
                            "invalid LP powers")
                    gap = abs(float(np.sum(lp_p)) - req) / max(req, 1e-30)
                    lp_violation = max(0.0, -float(np.min(lp_p - F @ lp_p - u)) / scale)
                    require(gap <= 1e-5, "analytic/LP objective mismatch")
                    require(lp_violation <= 1e-7, "LP constraint residual failed")
                    expected = "FEASIBLE" if req <= cfg["pmax"] * (1 + 1e-9) else "POWER_BUDGET"
                    require(status == expected, "baseline budget classification mismatch")
                    low, high = req * 0.5, max(cfg["pmax"], req * 2)
                    lower = engine.solve(H[i], users, alpha, {**cfg, "pmax": low})
                    upper = engine.solve(H[i], users, alpha, {**cfg, "pmax": high})
                    require(lower["status"] == "POWER_BUDGET" and upper["status"] == "FEASIBLE",
                            "feasibility is inconsistent below/above required power")
                    states = sorted([(low, False), (cfg["pmax"], status == "FEASIBLE"), (high, True)])
                    require(all(not x[1] or y[1] for x, y in zip(states, states[1:])),
                            "budget feasibility is not monotone")
                    summary["lp_checks"] += 1
                    summary["max_relative_lp_gap"] = max(summary["max_relative_lp_gap"], gap)
                    summary["max_scaled_analytic_violation"] = max(summary["max_scaled_analytic_violation"], analytic_violation)
                    summary["max_scaled_lp_violation"] = max(summary["max_scaled_lp_violation"], lp_violation)
            if intrinsic:
                for factor in (0.5, 2.0):
                    result = engine.solve(H[i], users, alpha, {**cfg, "pmax": cfg["pmax"] * factor})
                    require(result["status"] == status, "coupling/zero gain changed with budget")
            summary["candidate_count"] += 1
            summary["budget_monotonicity_checks"] += 1
            summary["extra_engine_solve_calls"] += 2
        if verbose and ((i + 1) % 10 == 0 or i + 1 == len(tasks)):
            print(f"G1 progress: {i + 1}/{len(tasks)} geometries", flush=True)
    return summary
