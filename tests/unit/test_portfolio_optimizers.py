"""Unit tests for portfolio optimizers in src/ml/portfolio.py."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ml.portfolio import (
    efficient_frontier,
    enforce_psd,
    min_variance_portfolio,
    risk_parity_portfolio,
    shrink_cov,
    stabilize_covariance,
    variance_contributions,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_returns(n_obs: int = 300, n_assets: int = 3, seed: int = 42):
    """Generate synthetic multi-asset returns."""
    rng = np.random.default_rng(seed)
    return rng.normal(0, 0.02, (n_obs, n_assets))


def _sample_cov(n_assets: int = 3, seed: int = 42):
    """Generate a stable sample covariance."""
    returns = _make_returns(n_assets=n_assets, seed=seed)
    return np.cov(returns, rowvar=False, ddof=1)


# ---------------------------------------------------------------------------
# Covariance stability tests
# ---------------------------------------------------------------------------

class TestCovarianceStability:
    """Tests for covariance estimation helpers."""

    def test_shrink_cov_diagonal(self):
        """Shrinkage towards diagonal should preserve diagonal."""
        cov = _sample_cov()
        shrunk = shrink_cov(cov, alpha=0.5, target="diag")
        # Diagonal elements should be between original and diag target
        for i in range(cov.shape[0]):
            assert shrunk[i, i] == pytest.approx(
                cov[i, i], rel=0.01,
            )

    def test_shrink_cov_reduces_offdiag(self):
        """Shrinkage should reduce off-diagonal magnitude."""
        cov = _sample_cov()
        shrunk = shrink_cov(cov, alpha=0.5, target="diag")
        for i in range(cov.shape[0]):
            for j in range(cov.shape[1]):
                if i != j:
                    assert abs(shrunk[i, j]) <= abs(cov[i, j]) + 1e-12

    def test_enforce_psd(self):
        """PSD enforcement should make all eigenvalues positive."""
        cov = _sample_cov()
        # Artificially create a non-PSD matrix
        bad = cov.copy()
        bad[0, 0] = -0.001
        fixed = enforce_psd(bad)
        eigvals = np.linalg.eigvalsh(fixed)
        assert all(e > 0 for e in eigvals)

    def test_stabilize_pipeline(self):
        """Full stabilization pipeline produces PSD matrix."""
        returns = _make_returns()
        cov = stabilize_covariance(
            returns, shrinkage_alpha=0.1,
        )
        eigvals = np.linalg.eigvalsh(cov)
        assert all(e > 0 for e in eigvals)
        assert cov.shape == (3, 3)


# ---------------------------------------------------------------------------
# Min-variance tests
# ---------------------------------------------------------------------------

class TestMinVariance:
    """Tests for min_variance_portfolio."""

    def test_weights_sum_to_one(self):
        """Min-var weights must sum to 1."""
        cov = _sample_cov()
        result = min_variance_portfolio(cov)
        assert result["success"]
        assert abs(result["weights"].sum() - 1.0) < 1e-6

    def test_long_only(self):
        """All weights should be ≥ 0 (long-only)."""
        cov = _sample_cov()
        result = min_variance_portfolio(cov)
        assert all(w >= -1e-8 for w in result["weights"])

    def test_volatility_is_positive(self):
        """Portfolio volatility should be positive."""
        cov = _sample_cov()
        result = min_variance_portfolio(cov)
        assert result["volatility"] is not None
        assert result["volatility"] > 0


# ---------------------------------------------------------------------------
# Efficient frontier tests
# ---------------------------------------------------------------------------

class TestEfficientFrontier:
    """Tests for efficient_frontier."""

    def test_frontier_non_empty(self):
        """Frontier should have at least some points."""
        returns = _make_returns(n_obs=300, n_assets=3)
        mu = returns.mean(axis=0)
        cov = stabilize_covariance(returns)
        frontier = efficient_frontier(mu, cov, n_points=10)
        assert len(frontier) > 0

    def test_frontier_returns_increase(self):
        """Frontier points should span return range."""
        returns = _make_returns(n_obs=300, n_assets=3)
        mu = returns.mean(axis=0)
        cov = stabilize_covariance(returns)
        frontier = efficient_frontier(mu, cov, n_points=20)
        if len(frontier) >= 2:
            rets = [p["expected_return"] for p in frontier]
            # First should have lower return than last
            assert rets[-1] >= rets[0] - 1e-10


# ---------------------------------------------------------------------------
# Risk parity tests
# ---------------------------------------------------------------------------

class TestRiskParity:
    """Tests for risk_parity_portfolio."""

    def test_weights_sum_to_one(self):
        """Risk parity weights must sum to 1."""
        cov = _sample_cov()
        result = risk_parity_portfolio(cov)
        assert result["success"]
        assert abs(result["weights"].sum() - 1.0) < 1e-6

    def test_long_only(self):
        """All weights should be ≥ 0."""
        cov = _sample_cov()
        result = risk_parity_portfolio(cov)
        assert all(w >= -1e-8 for w in result["weights"])

    def test_risk_contributions_sum(self):
        """Variance contributions should sum to portfolio variance."""
        cov = _sample_cov()
        result = risk_parity_portfolio(cov)
        rc = result["risk_contributions"]
        port_vol = result["portfolio_volatility"]
        port_var = port_vol ** 2
        assert abs(rc.sum() - port_var) < 1e-6

    def test_equal_risk_contributions(self):
        """With equal budget, risk contributions should be ~equal."""
        # Use a well-conditioned covariance for best convergence
        returns = _make_returns(n_obs=1000, n_assets=3, seed=99)
        cov = stabilize_covariance(returns, shrinkage_alpha=0.2)
        result = risk_parity_portfolio(cov)
        pct_rc = result["pct_risk_contributions"]
        n = len(pct_rc)
        target = 1.0 / n
        # Each contribution should be within 5% of target
        for rc in pct_rc:
            assert abs(rc - target) < 0.05, (
                f"Risk contribution {rc:.4f} deviates from "
                f"target {target:.4f}"
            )

    def test_portfolio_volatility_positive(self):
        """Portfolio volatility should be positive."""
        cov = _sample_cov()
        result = risk_parity_portfolio(cov)
        assert result["portfolio_volatility"] > 0


# ---------------------------------------------------------------------------
# variance_contributions helper
# ---------------------------------------------------------------------------

class TestVarianceContributions:
    """Tests for variance_contributions."""

    def test_contributions_sum_to_variance(self):
        """RC should sum to portfolio variance."""
        cov = _sample_cov()
        w = np.array([0.4, 0.3, 0.3])
        rc, port_var = variance_contributions(w, cov)
        assert abs(rc.sum() - port_var) < 1e-10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
