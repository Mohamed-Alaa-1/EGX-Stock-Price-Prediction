"""
Portfolio optimization: MPT efficient frontier + risk parity.

Uses NumPy for matrix math and SciPy SLSQP for constrained optimization.
Includes covariance shrinkage, diagonal loading, and PSD enforcement.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# Covariance estimation helpers
# ---------------------------------------------------------------------------


def shrink_cov(
    sample_cov: np.ndarray,
    alpha: float = 0.1,
    target: str = "diag",
) -> np.ndarray:
    """
    Shrink sample covariance towards a target.

    Parameters
    ----------
    sample_cov : (N, N) array
    alpha : float in [0, 1]
    target : "diag" or "identity"

    Returns
    -------
    Shrunk covariance matrix.
    """
    if target == "diag":
        t = np.diag(np.diag(sample_cov))
    elif target == "identity":
        avg_var = np.mean(np.diag(sample_cov))
        t = avg_var * np.eye(sample_cov.shape[0])
    else:
        raise ValueError(f"Unknown shrinkage target: {target}")
    return (1 - alpha) * sample_cov + alpha * t


def diagonal_load(cov: np.ndarray, lam: float) -> np.ndarray:
    """Add diagonal loading: Σ + λI."""
    return cov + lam * np.eye(cov.shape[0])


def enforce_psd(cov: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Clamp eigenvalues to ensure positive semi-definiteness."""
    eigvals, eigvecs = np.linalg.eigh(cov)
    eigvals = np.maximum(eigvals, eps)
    return eigvecs @ np.diag(eigvals) @ eigvecs.T


def stabilize_covariance(
    returns: np.ndarray,
    shrinkage_alpha: float = 0.1,
    diagonal_loading_lambda: float = 0.0,
) -> np.ndarray:
    """
    Full covariance stabilization pipeline:
      1. Sample covariance
      2. Diagonal shrinkage
      3. Diagonal loading (optional)
      4. PSD enforcement

    Parameters
    ----------
    returns : (T, N) array of asset returns
    shrinkage_alpha : shrinkage intensity
    diagonal_loading_lambda : ridge term

    Returns
    -------
    Stabilized (N, N) covariance matrix.
    """
    sample_cov = np.cov(returns, rowvar=False, ddof=1)
    if sample_cov.ndim == 0:
        sample_cov = np.array([[float(sample_cov)]])

    cov = shrink_cov(sample_cov, alpha=shrinkage_alpha, target="diag")

    if diagonal_loading_lambda > 0:
        cov = diagonal_load(cov, diagonal_loading_lambda)

    cov = enforce_psd(cov)
    return cov


# ---------------------------------------------------------------------------
# Variance contributions
# ---------------------------------------------------------------------------


def variance_contributions(
    w: np.ndarray,
    cov: np.ndarray,
) -> tuple[np.ndarray, float]:
    """
    Compute variance contributions per asset.

    Returns
    -------
    rc : (N,) array of variance contributions (sums to portfolio variance)
    port_var : float — portfolio variance
    """
    m = cov @ w
    port_var = float(w @ m)
    rc = w * m
    return rc, port_var


# ---------------------------------------------------------------------------
# MPT: Minimum-variance portfolio
# ---------------------------------------------------------------------------


def min_variance_portfolio(
    cov: np.ndarray,
    w_max: float = 1.0,
) -> dict[str, Any]:
    """
    Solve the long-only minimum-variance portfolio.

    Returns
    -------
    dict with keys: weights, volatility, success
    """
    n = cov.shape[0]
    x0 = np.ones(n) / n
    bounds = [(0.0, w_max)] * n
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

    def objective(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    def grad(w: np.ndarray) -> np.ndarray:
        return 2.0 * cov @ w

    res = minimize(
        objective,
        x0,
        method="SLSQP",
        jac=grad,
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-12},
    )

    return {
        "weights": res.x if res.success else x0,
        "volatility": float(np.sqrt(res.fun)) if res.success else None,
        "success": res.success,
    }


# ---------------------------------------------------------------------------
# MPT: Efficient frontier
# ---------------------------------------------------------------------------


def efficient_frontier(
    mu: np.ndarray,
    cov: np.ndarray,
    n_points: int = 20,
    w_max: float = 1.0,
) -> list[dict[str, Any]]:
    """
    Compute points along the efficient frontier by varying target return.

    Parameters
    ----------
    mu : (N,) expected returns
    cov : (N, N) stabilized covariance
    n_points : number of frontier points
    w_max : max weight per asset

    Returns
    -------
    list of dicts with keys: target_return, weights, volatility, expected_return, sharpe
    """
    n = len(mu)
    x0 = np.ones(n) / n
    bounds = [(0.0, w_max)] * n

    # Get feasible return range
    min_var = min_variance_portfolio(cov, w_max=w_max)
    r_min = float(mu @ min_var["weights"])
    r_max = float(np.max(mu))  # Max single-asset return under long-only

    if r_max <= r_min:
        # Degenerate case
        return []

    targets = np.linspace(r_min, r_max, n_points)
    frontier: list[dict[str, Any]] = []

    for r_target in targets:
        eq_constraint = {"type": "eq", "fun": lambda w: w.sum() - 1.0}
        ret_constraint = {
            "type": "ineq",
            "fun": lambda w, rt=r_target: float(mu @ w) - rt,
        }

        def objective(w: np.ndarray) -> float:
            return float(w @ cov @ w)

        def grad(w: np.ndarray) -> np.ndarray:
            return 2.0 * cov @ w

        res = minimize(
            objective,
            x0,
            method="SLSQP",
            jac=grad,
            bounds=bounds,
            constraints=[eq_constraint, ret_constraint],
            options={"maxiter": 500, "ftol": 1e-12},
        )

        if res.success:
            vol = float(np.sqrt(res.fun))
            exp_ret = float(mu @ res.x)
            sharpe = exp_ret / vol if vol > 0 else 0.0
            frontier.append({
                "target_return": float(r_target),
                "weights": res.x.tolist(),
                "volatility": vol,
                "expected_return": exp_ret,
                "sharpe": sharpe,
            })

    return frontier


# ---------------------------------------------------------------------------
# Risk parity
# ---------------------------------------------------------------------------


def risk_parity_portfolio(
    cov: np.ndarray,
    budget: np.ndarray | None = None,
    w_max: float = 1.0,
) -> dict[str, Any]:
    """
    Compute risk parity (equal risk contribution) weights.

    Minimises Σ (RC_i - b_i * σ²_p)².

    Parameters
    ----------
    cov : (N, N) stabilized covariance
    budget : (N,) risk budget (sums to 1). Default = equal.
    w_max : maximum weight per asset

    Returns
    -------
    dict with keys: weights, risk_contributions, pct_risk_contributions,
                     portfolio_volatility, success
    """
    n = cov.shape[0]
    if budget is None:
        budget = np.ones(n) / n

    x0 = np.ones(n) / n
    bounds = [(1e-8, w_max)] * n  # Small floor to avoid division issues
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

    def objective(w: np.ndarray) -> float:
        m = cov @ w
        port_var = float(w @ m)
        rc = w * m
        target_rc = budget * port_var
        return float(np.sum((rc - target_rc) ** 2))

    res = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-14},
    )

    weights = res.x if res.success else x0
    rc, port_var = variance_contributions(weights, cov)
    pct_rc = rc / port_var if port_var > 0 else rc

    return {
        "weights": weights,
        "risk_contributions": rc,
        "pct_risk_contributions": pct_rc,
        "portfolio_volatility": float(np.sqrt(port_var)),
        "success": res.success,
    }
