# Research Notes: Quant Modules (Risk, Validation, Backtesting, Portfolio)

**Scope**: pragmatic, local-first quant modules to satisfy FR-001..FR-016 in [specs/001-quant-finance-integration/spec.md](spec.md). Focus is on explainable defaults, stable computations on daily bars, and graceful degradation when data is missing.

Related research:
- [specs/001-quant-finance-integration/gdr-premium-discount-research.md](gdr-premium-discount-research.md) (free-data + local-first cross-listed premium/discount series)

---

## Inputs & Preprocessing (shared)

### Returns definition
- **Simple returns**: $r_t = \frac{P_t}{P_{t-1}} - 1$ (easier to explain).
- **Log returns**: $\ell_t = \log(P_t) - \log(P_{t-1})$ (additive; sometimes numerically nicer).

**Pragmatic choice**: simple returns for user-facing explainability; internally either is fine if consistent.

### Alignment and missing data
- Build a **common date index** for all assets.
- Prefer **inner join** (intersection of dates) for covariance stability; otherwise you can get spurious covariances.
- Require a minimum overlap (e.g., **≥ 126** trading days) to compute anything beyond trivial baselines.

### Estimation windows
- A rolling lookback window $T$ (common values: 63, 126, 252 trading days).
- Use a single **as-of date** and compute $\mu$ and $\Sigma$ from the trailing window.

**Explainability outputs to always report**:
- lookback length $T$, start/end dates, number of observations after cleaning, and return convention.

---

## Covariance estimation & stability tricks

Sample covariance is noisy and can be near-singular, especially with:
- many assets vs small $T$,
- highly correlated assets,
- missing-data alignment reducing effective sample size.

### Baseline estimators
Let $R \in \mathbb{R}^{T \times N}$ be the matrix of returns.
- Mean: $\mu = \frac{1}{T}\sum_t R_t$.
- Sample covariance: $\Sigma = \mathrm{cov}(R)$ (NumPy: `np.cov(R, rowvar=False, ddof=1)`).

### Shrinkage (NumPy-only)
Use a convex combination:

$$\Sigma_{\text{shrunk}} = (1-\alpha)\,\Sigma + \alpha\,T$$

Common shrink targets $T$:
- **Diagonal target**: $T = \mathrm{diag}(\Sigma)$ (preserves per-asset variance, damps correlations).
- **Scaled identity**: $T = \bar{\sigma}^2 I$, where $\bar{\sigma}^2 = \frac{1}{N}\sum_i \Sigma_{ii}$.

Practical guidance:
- Start with **diagonal shrinkage**.
- Choose $\alpha$ via a simple heuristic (e.g., 0.05–0.30) or tune by walk-forward backtests.

### Diagonal loading / ridge

$$\Sigma_{\text{loaded}} = \Sigma + \lambda I$$

- Useful even without shrinkage.
- Pick $\lambda$ proportional to average variance (e.g., $\lambda = 10^{-4}\,\bar{\sigma}^2$ to $10^{-2}\,\bar{\sigma}^2$).

### PSD enforcement (optional but useful)
If numerical issues produce a non-PSD covariance:
- Eigen-decompose $\Sigma = Q\Lambda Q^T$.
- Clamp eigenvalues: $\Lambda' = \max(\Lambda, \varepsilon)$.
- Recompose: $\Sigma' = Q\Lambda' Q^T$.

This helps keep optimization stable and prevents negative “variance” artifacts.

### Outlier robustness (cheap wins)
- Winsorize returns per asset (e.g., clamp to 1st/99th percentile) before covariance.
- Alternatively clamp daily returns to a reasonable range for EGX (domain-specific).

---

## (1) Long-only Mean–Variance (MPT) + Efficient Frontier

### Optimization problems
Let $w \in \mathbb{R}^N$ be weights.

Constraints (long-only, fully invested):
- $w_i \ge 0$ for all $i$
- $\sum_i w_i = 1$
- Optional: $w_i \le w_{\max}$, group/sector caps, turnover constraints (if you have previous weights)

#### A. Minimum variance portfolio

$$\min_w \quad w^T\Sigma w\;\;\text{s.t.}\;\; \mathbf{1}^T w = 1,\; w \ge 0$$

#### B. Frontier via target return grid
Pick target returns $r_\text{target}$ and solve:

$$\min_w \quad w^T\Sigma w\;\;\text{s.t.}\;\; \mu^T w \ge r_\text{target},\; \mathbf{1}^T w = 1,\; w \ge 0$$

Notes:
- Using “$\ge$” (inequality) is typically more feasible than equality under long-only constraints.
- A feasible grid can be built between:
  - $r_{\min}$: return of the minimum-variance solution
  - $r_{\max}$: return of the max-return long-only solution (often the single highest-mean asset under $w\ge0,\sum w=1$)

#### C. Max Sharpe (optional)
Direct Sharpe maximization is non-convex in this parameterization. A pragmatic approach:
- Search along the frontier grid and pick the best Sharpe.

### Solver choice (SciPy)
Use `scipy.optimize.minimize` with:
- **SLSQP**: good for bounds + linear constraints; widely used for long-only MPT.
- **trust-constr**: more robust sometimes, but more configuration overhead.

Practical settings:
- Initial guess: equal weights.
- Bounds: `(0, w_max)` per asset (use `w_max=1` if no cap).
- Constraints:
  - equality: `sum(w) - 1 = 0`
  - inequality: `mu @ w - r_target >= 0`

Gradients:
- Provide analytic gradient for variance objective: $\nabla (w^T\Sigma w) = 2\Sigma w$ for stability and speed.

### Efficient frontier generation algorithm
1. Compute $\mu$ and stabilized $\Sigma$ from the chosen window.
2. Solve **min-variance** once.
3. Compute feasible return range for grid.
4. For each target return in grid:
   - solve the constrained min-variance problem
   - if infeasible or solver fails, skip and continue
5. Deduplicate near-identical solutions (frontier points can repeat under long-only constraints).

### Explainability outputs to report (per solution)
For each frontier point (and for min-var / chosen point):
- **Weights**: asset → weight.
- **Expected return**: $\hat{r} = \mu^T w$.
- **Risk (vol)**: $\hat{\sigma} = \sqrt{w^T\Sigma w}$.
- **Sharpe** (if you assume $r_f$): $(\hat{r}-r_f)/\hat{\sigma}$; if $r_f$ unknown, set $r_f=0$ and label it.
- **Diversification**:
  - effective number of holdings: $1/\sum_i w_i^2$ (intuitive, cheap).
- **Risk contributions**:
  - marginal risk: $m = \Sigma w$
  - variance contribution: $VC_i = w_i\,m_i$ (sums to portfolio variance)
  - percent contribution: $pVC_i = VC_i / (w^T\Sigma w)$
- **Estimation metadata**: window dates, $T$, shrinkage parameters, diagonal loading $\lambda$.
- **Constraint diagnostics**:
  - which weights are at 0 or at cap (active bounds)
  - realized return slack: $\mu^T w - r_{\text{target}}$

### Common failure modes & mitigations
- **Infeasible target return** under long-only + caps: build grid from feasible endpoints; treat failures as expected.
- **Unstable solutions** (weights jump wildly): increase shrinkage/diagonal loading; increase window length; cap weights.
- **Near-singular covariance**: shrinkage + ridge + PSD clamp.

---

## (2) Risk Parity Weights + Risk Contributions

Risk parity targets equal (or budgeted) risk contributions. Most common is parity on **variance contributions**.

### Definitions
Portfolio variance: $\sigma_p^2 = w^T\Sigma w$

Marginal contribution to variance: $(\Sigma w)_i$

Variance contribution of asset $i$:

$$RC_i = w_i(\Sigma w)_i$$

Then $\sum_i RC_i = \sigma_p^2$.

Risk budget vector $b$:
- equal risk: $b_i = 1/N$
- custom budgets allowed if needed later

Target: $RC_i \approx b_i\,\sigma_p^2$.

### Optimization formulation (SciPy-friendly)
Minimize squared deviations:

$$\min_w \;\sum_i \left(RC_i - b_i\,\sigma_p^2\right)^2\;\;\text{s.t.}\;\; \mathbf{1}^T w = 1,\; w \ge 0$$

Implementation details:
- Use stabilized $\Sigma$ (shrinkage/ridge) or this can be very noisy.
- Add a tiny floor to weights (e.g., bounds `[(0, 1)]`) and let some weights go to ~0 naturally.

Alternative objective (also common): match log contributions to improve scaling:

$$\min_w \;\sum_i \left(\log(RC_i+\epsilon) - \log(b_i\,\sigma_p^2+\epsilon)\right)^2$$

This can be more stable when some assets want to go to near-zero.

### Solver choice
- `scipy.optimize.minimize(method="SLSQP")` with bounds and equality constraint.
- Provide gradients if you want speed; otherwise finite-diff often suffices at small N (≤10).

### Explainability outputs to report
- **Weights**.
- **Portfolio volatility** $\hat{\sigma}$.
- **Risk contributions** (variance contribution $RC_i$) and **percent risk contributions** $RC_i/\sigma_p^2$.
- **Risk budget** vector $b$ and error metrics:
  - max deviation: $\max_i |pRC_i - b_i|$
  - L2 deviation: $\|pRC - b\|_2$
- **Estimation metadata**: same as MPT.

### Practical notes / stability
- Risk parity is especially sensitive to correlation estimation; diagonal shrinkage is usually helpful.
- If you see extreme concentrations, add:
  - max weight cap, or
  - stronger shrinkage (increase $\alpha$), or
  - volatility targeting / variance normalization.

---

## Decision / Rationale / Alternatives

### Decision
Implement two local-first optimizers using NumPy/SciPy:
1. **Long-only MPT** using SLSQP with stabilized covariance, plus **efficient frontier** via target-return grid.
2. **Risk parity** using SLSQP on a risk-contribution matching objective, reporting both weights and risk contributions.

### Rationale
- **Constraint handling**: SLSQP directly supports long-only bounds and linear constraints without extra dependencies.
- **Explainability**: both methods naturally produce interpretable outputs (weights, expected return, volatility, risk contributions, constraint activity).
- **Stability**: shrinkage/diagonal loading/PSD clamping provide robust behavior in small-N, noisy-cov regimes typical of free data and limited EGX history.
- **Local-first**: does not require paid data, remote services, or specialized convex solvers.

### Alternatives (considered, not chosen)
- **Dedicated QP / convex optimization libraries** (CVXOPT, OSQP, quadprog, cvxpy): more robust QP solves and KKT diagnostics, but adds dependencies and complexity beyond the SciPy-only constraint.
- **PyPortfolioOpt / Riskfolio-Lib**: excellent feature set (Ledoit–Wolf shrinkage, robust frontiers, hierarchical risk parity), but violates “NumPy/SciPy only”.
- **Closed-form unconstrained MPT**: fast but ignores long-only constraints; often yields negative weights and is unsuitable for typical personal-investor UX.
- **Single-solution only (e.g., min-var only)**: simpler but does not satisfy efficient-frontier requirement (FR-013) and gives less choice/insight.

---

## Risk & Signal Context (P1): VaR, Sharpe, ADF, Hurst

### 1-day Value at Risk (VaR)

#### Decision
Use **historical simulation VaR** on daily close-to-close returns.

- Inputs: trailing daily returns over lookback window (default 252 trading days; allow user override later).
- Output: VaR at 95% and 99% as a % move and an absolute EGP move (based on the most recent close).

#### Rationale
- Minimal assumptions, easy to explain, and robust under non-normal EGX return behavior.
- Works with local cached daily closes and aligns with the constitution’s “state the assumptions” mandate.

#### Alternatives considered
- Parametric/normal VaR (fast, but often misleading in fat-tail markets).
- EWMA/GARCH VaR (more realistic sometimes but adds complexity and tuning).

#### Notes
- Returns convention: $r_t = \frac{C_t}{C_{t-1}} - 1$.
- VaR computed on the **loss distribution**: for confidence $\alpha$, $\mathrm{VaR}_\alpha = -\mathrm{quantile}(r, 1-\alpha)$.
- Minimum length: require enough non-NaN returns (e.g., ≥ 60) or report “insufficient data.”

### Sharpe ratio

#### Decision
Compute **historical Sharpe** on daily returns with a stated lookback window and assume $r_f = 0$ by default (explicitly labeled), with room to add a configurable risk-free rate later.

#### Rationale
- Keeps dependencies and UX simple while still providing a useful context metric.
- Avoids implying a precise EGP risk-free rate without a reliable local-first data source.

#### Alternatives considered
- Use a user-configured constant EGP risk-free rate.
- Pull a free macro series (e.g., FRED) behind an optional key; adds fragility.

### ADF stationarity test

#### Decision
Use `statsmodels.tsa.stattools.adfuller` with explicit recorded parameters.

- Default: `autolag="AIC"` and `regression="c"` when testing returns.
- Record: test statistic, p-value, used lag, nobs, critical values, regression variant, autolag choice.

#### Rationale
- Avoid re-implementing a statistically subtle routine.
- Produces canonical outputs needed for reproducibility and governance.

#### Alternatives considered
- `arch.unitroot.ADF` (good, but adds another dependency).
- Custom ADF (not recommended).

### Hurst exponent / regime classification

#### Decision
Implement a small NumPy-only Hurst estimator (primary: **aggregated variance on increments**) and classify regimes:
- mean-reverting: $H < 0.45$
- random-like: $0.45 \le H \le 0.55$
- trending: $H > 0.55$

Return fit diagnostics (slope and $R^2$) so users can see when the estimate is unstable.

#### Rationale
- Dependency-light; easy to audit.
- Estimates vary across methods; reporting diagnostics reduces the risk of over-confidence.

#### Alternatives considered
- R/S estimator (common but noisy/bias-prone).
- DFA (more robust but more code).

---

## Realistic Evaluation (P2): Vectorized Backtesting + EGX Costs

### Decision
Implement a **vectorized daily backtester** using “signal at $t$ → exposure on $t+1$” (no-lookahead) and apply costs via turnover.

- Use close-to-close returns.
- Positions/weights computed from indicators using data available through $t$.
- Exposure uses shifted positions: $\text{gross\_ret}_t = w_{t-1}\, r_t$.
- Costs applied when weights change: $\text{net\_ret}_t = \text{gross\_ret}_t - c\cdot\text{turnover}$.

### Rationale
- Small and explainable; avoids building a full event-driven simulator.
- Cost application is consistent across strategies and works with close-only datasets.

### Alternatives considered
- Trade-at-next-open convention (requires reliable open prices).
- Event-driven backtester with fills and intraday rules (heavier and harder to validate).

### EGX transaction cost model
Minimum required components (per constitution + FR-010):
- commissions (bps per notional)
- stamp duties (bps per notional)

Backtest output must report:
- gross vs net performance
- total costs paid / cost drag
- turnover summary


---

## Minimal pseudo-code sketches (implementation guidance)

### Covariance stabilization
```python
import numpy as np

def shrink_cov(sample_cov: np.ndarray, alpha: float = 0.1, target: str = "diag") -> np.ndarray:
    if target == "diag":
        T = np.diag(np.diag(sample_cov))
    elif target == "identity":
        avg_var = np.mean(np.diag(sample_cov))
        T = avg_var * np.eye(sample_cov.shape[0])
    else:
        raise ValueError(target)
    return (1 - alpha) * sample_cov + alpha * T

def diagonal_load(cov: np.ndarray, lam: float) -> np.ndarray:
    return cov + lam * np.eye(cov.shape[0])
```

### Risk contributions
```python
import numpy as np

def variance_contributions(w: np.ndarray, cov: np.ndarray) -> tuple[np.ndarray, float]:
    m = cov @ w
    port_var = float(w @ m)
    rc = w * m
    return rc, port_var
```

### SLSQP pattern (shared)
```python
from scipy.optimize import minimize

# bounds = [(0.0, w_max)] * n
# constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}, ...]
# res = minimize(fun, x0, method="SLSQP", jac=grad, bounds=bounds, constraints=constraints)
```

(Keep these as guidance; production code should include failure handling and reporting.)
