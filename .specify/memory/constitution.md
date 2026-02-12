<!--
Sync Impact Report
- Version change: 1.1.0 → 1.2.0
- Modified principles:
	- V. Safety, Honesty, Realistic Evaluation → V. Safety, Honesty, Realistic Evaluation (expanded: recommendation/UI labeling constraints)
- Added sections:
	- VI. Investment Advisory Principles (Risk-First Recommendations)
- Removed sections: None
- Templates requiring updates:
	- ✅ .specify/templates/plan-template.md
	- ✅ .specify/templates/spec-template.md
	- ✅ .specify/templates/tasks-template.md
	- ✅ .specify/templates/checklist-template.md
	- ⚠ .specify/templates/commands/*.md (directory not present in repo; nothing to update)
- Runtime docs requiring updates:
	- ✅ README.md (clarify raw model output vs assistant recommendation labeling expectation)
- Follow-up TODOs: None
-->

# Stocks Project Constitution

## Core Principles

### I. Local-First, Personal-Use Only
- Runs locally on the user’s machine.
- Intended for personal experimentation and learning only.
- Not financial advice; no guarantees; no brokerage integration; no automated trading.

### II. Free Data Sources (No Paid Dependencies)
- Must be able to fetch historical OHLCV data using at least one free method.
- Primary (no-key) data source: Stooq daily data (where available).
- Optional (free tier) sources: Alpha Vantage (requires a free API key), other free/public endpoints only if terms allow.
- If a source breaks or rate-limits, the app must degrade gracefully (cached data, clear error message).

- Any additional quantitative signals (statistical tests, risk metrics, optimization inputs, leading indicators)
  MUST be computed locally from already-fetched free data or sourced from free/public endpoints whose
  terms allow local use.

### III. Prediction Scope + Risk & Portfolio Context
- Supported target: predict the closing price for either:
	- “next trading day close” (default), or
	- “today’s close” only when the market session is not yet closed (clearly labeled as an estimate).

- Every price prediction MUST include a companion risk assessment to provide worst-case context.
  At minimum, report a 1-day Value at Risk (VaR) estimate:
	- Provide VaR at a stated confidence level (e.g., 95% and/or 99%).
	- Clearly state the methodology (e.g., historical VaR, parametric/normal, EWMA) and lookback window.
	- Present VaR as an absolute currency move and/or % move, and label it as an estimate.

- The output MUST include:
	- the predicted value,
	- the prediction date/target session,
	- the last available data timestamp used,
	- the risk context summary (including the 1-day VaR estimate and its assumptions).

- Federated mode MUST provide portfolio insights across the participating tickers, computed locally.
  The system MUST be able to suggest long-only allocations using at least:
	- Modern Portfolio Theory (MPT) (e.g., minimum-variance and/or max Sharpe under stated constraints),
	- Risk Parity (risk-budgeted allocations).
  Any suggested allocation MUST show:
	- constraints (weights sum to 1, long-only, any min/max bounds),
	- the inputs used (historical covariance window, expected return proxy),
	- portfolio risk metrics (e.g., volatility and/or 1-day VaR) alongside expected return assumptions.

### IV. Reproducible, Explainable, and Statistically Grounded
- Every prediction run records: ticker, date range used, data source, model version/config, and a random seed (when applicable).
- Provide a baseline (e.g., “naive: last close”) alongside the model prediction.
- Prefer simple models by default; only add complexity when it clearly improves validation metrics.

- Statistical Signal Validation is required before training any model on a ticker/dataset.
  At minimum, the training workflow MUST compute and record:
	- Augmented Dickey-Fuller (ADF) test results (test target and p-value, with chosen significance),
	- Hurst exponent estimate and an interpretation (trending vs mean-reverting vs random-walk-like).
  If validation indicates the series is unsuitable for the intended modeling assumption, the workflow MUST
  explicitly flag it in the UI/logs and avoid overstating expected predictability.

- Leading indicators MUST be used where free data allows.
  For cross-listed EGX stocks where free data is available (e.g., a GDR listing plus FX rate), the system
  MUST support tracking the GDR Premium/Discount (local price vs FX-adjusted GDR price) and expose it as:
	- an explainability overlay/diagnostic, and
	- an optional feature signal for models.

### V. Safety, Honesty, Realistic Evaluation
- Never claim certainty; always present outputs as probabilistic/approximate.
- Clearly label when the market is closed/open and whether the target close is already known.
- Validate inputs (ticker format, date range) and handle missing/holiday data correctly.

- When the UI presents an “Assistant” output that goes beyond raw model inference (e.g., Buy/Sell/Hold), it MUST:
	- clearly distinguish raw model data (forecast/baselines/metrics) from the Assistant’s processed recommendation,
	- avoid implying guaranteed outcomes, and
	- surface key risk context prominently.

- Any success criteria, backtesting, or claims of “alpha” MUST be realistic for the EGX market.
  Performance reporting MUST include transaction cost modeling at minimum for:
	- commissions,
	- stamp duties,
	- and any other mandatory EGX fees when known.
  Backtest results MUST report net-of-cost performance and clearly state the cost assumptions.
  Costs MUST be configurable, with documented defaults.

### VI. Investment Advisory Principles (Risk-First Recommendations)
- Capital preservation is the top priority (Risk-First). If signals conflict or risk is unclear, default to HOLD.

- Any “recommendation” output (including HOLD) MUST include:
	- a Stop-Loss field (explicitly set to “N/A (no position)” when action is HOLD),
	- a Conviction Score, and
	- a short evidence summary that references the underlying signals and assumptions.

- Stop-Loss MUST be derived from quantitative risk context (e.g., volatility/ATR/VaR) and must be expressed as:
	- a price level, and
	- a % distance from the relevant reference price (e.g., last close or proposed entry).

- Conviction Score MUST be defined on a stable scale (default: 0–100) and reflect agreement between signals.
  Conviction MUST decrease when technical signals and ML predictions diverge.

- Technical signals MUST be weighted against ML predictions.
	- The system MUST compute an explicit blended view (weights disclosed) for any recommendation.
	- Technical-only “Buy/Sell” calls without reference to the ML forecast are not allowed.
	- If ML and technical disagree, the recommendation MUST either downgrade to HOLD or reduce conviction and tighten risk.

- UI/UX MUST present raw model data and processed recommendation as separate, clearly labeled sections.
  The user must be able to tell what the model predicted vs what the Assistant inferred.

## Constraints
- No paid APIs, paid datasets, or mandatory accounts.
- Store data locally only (CSV/SQLite/Parquet are acceptable).
- Do not collect or transmit personal data.

- All quant finance modules (statistical tests, backtesting, portfolio optimization, risk analytics)
  MUST remain Local-First and rely only on Free Data Sources.

## Development Workflow
- Keep the app small and maintainable (YAGNI).
- Add unit tests for:
	- data fetching/parsing,
	- trading-day calendar handling,
	- prediction pipeline determinism (when seed is set),
	- statistical signal validation computations (ADF, Hurst),
	- risk metric calculations (e.g., VaR) and transaction cost modeling.
	- recommendation policy (Risk-First), signal blending (ML vs technical), and Stop-Loss/Conviction Score outputs.
- When changing a data source or model, update any docs/notes that describe assumptions.

## Governance
- This document is the top-level constraints for this repo.
- Any change that expands scope (new targets, new markets, new data sources) must update this constitution.

- Versioning follows semantic versioning for this constitution:
	- MAJOR: backward-incompatible governance changes or principle removals/redefinitions.
	- MINOR: new principle/section added, or materially expanded guidance.
	- PATCH: clarifications and non-semantic refinements.

- Compliance expectation: feature specs/plans that touch modeling, evaluation, or new data inputs MUST explicitly
	state how they satisfy Principles II–VI (Free Data, Scope + Risk, Statistical Rigor, Realistic Evaluation,
	Investment Advisory Principles).

**Version**: 1.2.0 | **Ratified**: 2026-02-10 | **Last Amended**: 2026-02-12
