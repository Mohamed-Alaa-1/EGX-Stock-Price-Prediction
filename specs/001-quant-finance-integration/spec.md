# Feature Specification: Quantitative Finance Integration

**Feature Branch**: `001-quant-finance-integration`  
**Created**: 2026-02-12  
**Status**: Draft  
**Input**: User description: "Extend the EGX Stock Prediction project beyond price forecasting with local-first, free-data quant modules: risk metrics (1-day VaR 95%/99%, Sharpe), statistical signal validation (ADF, Hurst), backtesting with EGX transaction costs, federated-mode portfolio optimization (efficient frontier + risk parity), and GDR premium/discount tracking for cross-listed stocks."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Risk & Signal Context (Priority: P1)

As a personal EGX investor using the app locally, I want every single-stock prediction to include risk and statistical context (VaR, Sharpe, ADF, Hurst) so I can interpret the prediction in a realistic “worst-case” and “signal quality” frame.

**Why this priority**: This is the minimum governance expansion required by the constitution: every prediction needs risk context and statistically grounded validation to avoid misleading confidence.

**Independent Test**: Can be fully tested by selecting a ticker with sufficient history and confirming the UI/report shows prediction + 1-day VaR (95%/99%), Sharpe ratio, ADF result, Hurst regime classification, and a clear “insufficient data” state when history is too short.

**Acceptance Scenarios**:

1. **Given** a selected EGX ticker with sufficient historical daily closes, **When** I view the next-trading-day prediction, **Then** the output also shows 1-day VaR at 95% and 99% confidence with its stated assumptions.
2. **Given** a selected EGX ticker with sufficient historical data, **When** I view the prediction, **Then** the output also shows the historical Sharpe ratio and clearly states the lookback window and return convention used.
3. **Given** a selected EGX ticker, **When** I initiate (or the app initiates) model training or retraining, **Then** the run records ADF test results and Hurst exponent results and classifies the series as trending / random-like / mean-reverting.
4. **Given** insufficient data for a requested metric, **When** the metric cannot be computed reliably, **Then** the app shows an explicit “insufficient data” message and does not silently fall back to a misleading numeric value.

---

### User Story 2 - Backtesting + Portfolio Insights (Priority: P2)

As a personal user exploring strategies and portfolios locally, I want fast backtesting with EGX transaction cost modeling and federated-mode portfolio optimization so I can evaluate whether a strategy’s apparent edge remains viable net-of-cost and translate predictions into disciplined allocations.

**Why this priority**: Risk and signal validation are necessary, but users also need realistic evaluation and portfolio-level insights (especially in federated mode) to avoid overfitting to “paper alpha.”

**Independent Test**: Can be fully tested by running a backtest over a fixed historical window and confirming the reported returns are net-of-cost, plus running federated optimization on a small set of tickers and confirming the system outputs an efficient frontier summary and suggested weights (MPT and risk parity) with clearly stated constraints.

**Acceptance Scenarios**:

1. **Given** a chosen indicator-based strategy and date range, **When** I run a backtest, **Then** results include net-of-cost P/L where commissions and stamp duties are applied consistently to trades.
2. **Given** federated mode with multiple participating tickers, **When** I request portfolio insights, **Then** the app produces efficient-frontier style options and suggests at least one allocation using an MPT objective under stated constraints.
3. **Given** federated mode with multiple tickers, **When** I request risk parity, **Then** the app outputs weights and risk contributions per ticker with a clear explanation of the risk budget interpretation.

---

### User Story 3 - GDR Premium/Discount Signal (Priority: P3)

As a user analyzing cross-listed EGX stocks, I want to see the GDR premium/discount as a leading indicator when free data is available so I can incorporate cross-market price signals into interpretation and (optionally) forecasting.

**Why this priority**: This is valuable but depends on free-data availability and mapping of cross-listed instruments; it should not block core risk/validation/backtesting features.

**Independent Test**: Can be fully tested by selecting a supported cross-listed ticker mapping and verifying the app computes and displays the premium/discount series; if data is unavailable, the app clearly states the limitation without breaking the rest of the workflow.

**Acceptance Scenarios**:

1. **Given** a cross-listed EGX stock with a configured GDR mapping and free price data, **When** I view the ticker’s analytics, **Then** I can see a time series of the GDR premium/discount with a clear definition of the calculation.
2. **Given** missing or rate-limited free data for the GDR leg or FX rate, **When** I request the premium/discount, **Then** the app degrades gracefully (cached data and/or a clear error) without blocking other analytics.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- Insufficient history for a requested metric (e.g., VaR, Sharpe, ADF, Hurst) due to short listing history or missing data.
- Gaps in data due to EGX holidays/suspensions; alignment between price series and indicator/backtest dates.
- Extreme returns/outliers leading to unstable metrics; results must be labeled as estimates with assumptions.
- Federated mode contains too few tickers or too-short overlap window to form a stable covariance estimate.
- Transaction costs configured as zero vs non-zero; costs must never be implicitly omitted in reported “net” results.
- GDR/FX data unavailable, unmapped, or stale; premium/discount is unavailable but the rest of the app continues.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST compute and display a 1-day VaR estimate at 95% and 99% confidence for the currently selected ticker alongside any price prediction.
- **FR-002**: System MUST display the VaR assumptions used (methodology label, lookback window, and confidence level).
- **FR-003**: System MUST compute and display a historical Sharpe ratio for the selected ticker using a clearly stated lookback window and return convention.

- **FR-017**: System MUST display a baseline prediction (e.g., "naive: last close") alongside the model prediction for every prediction run.

- **FR-004**: Before training or retraining a model for a ticker, the system MUST compute and record ADF stationarity test outputs (including the test target and p-value) for the time series being modeled.
- **FR-005**: Before training or retraining a model for a ticker, the system MUST compute and record a Hurst exponent estimate and a regime classification (trending / random-like / mean-reverting).
- **FR-006**: If statistical validation indicates weak/unsuitable signal for the chosen modeling assumption, the system MUST flag this clearly in the user-facing output and must not present the prediction as high-confidence.

- **FR-007**: The system MUST keep all quant computations local-first and must not require paid data sources or paid accounts.
- **FR-008**: When free data sources are rate-limited or unavailable, the system MUST degrade gracefully (use cache where available and provide a clear error state).

- **FR-009**: The system MUST provide a backtesting capability that simulates strategy performance based on commonly used technical indicators (including RSI, MACD, and EMA).
- **FR-010**: All backtesting performance results MUST be net-of-transaction-costs and MUST apply a configurable EGX transaction cost model that includes at least commissions and stamp duties.
- **FR-011**: The system MUST show the transaction cost assumptions used in a backtest run and allow users to change them for re-evaluation.

- **FR-012**: In federated mode, the system MUST provide portfolio insights across the participating tickers and MUST be able to suggest long-only allocations using an MPT-style approach under clearly stated constraints.
- **FR-013**: In federated mode, the system MUST compute and present an efficient-frontier style set of options (risk/return trade-off summary) using a clearly stated historical window.
- **FR-014**: In federated mode, the system MUST provide a risk-parity allocation option and MUST report per-ticker risk contribution alongside the suggested weights.

- **FR-015**: For cross-listed EGX stocks where free data is available and a mapping exists, the system MUST compute and present GDR premium/discount tracking as a leading indicator.
- **FR-016**: If GDR/FX inputs are missing or invalid, the system MUST clearly report why premium/discount cannot be computed and continue to support the rest of the analytics/prediction workflow.

### Assumptions

- The app remains for personal-use only and does not provide brokerage integration or automated trading.
- VaR is presented as an estimate with explicitly stated assumptions; exact methodology choice is allowed to evolve as long as assumptions are disclosed.
- Transaction cost parameters vary over time; defaults are documented and user-adjustable.
- Portfolio optimization suggestions are informational and long-only by default.

### Key Entities *(include if feature involves data)*

- **RiskMetricsSnapshot**: A timestamped set of risk outputs for one ticker (VaR 95/99, Sharpe) plus the assumptions used.
- **StatisticalValidationResult**: A record of ADF and Hurst outputs for a ticker/time window, including regime classification and any warnings.
- **BacktestRun**: A stored definition of a strategy run (indicator parameters, date range, cost assumptions) and its resulting performance summary.
- **TransactionCostModel**: A user-configurable set of cost parameters (commissions, stamp duties, and any other fees supported) applied consistently during backtests.
- **PortfolioOptimizationResult**: A federated-mode output containing suggested weights, constraints, risk/return summary, and (for risk parity) risk contributions.
- **GdrPremiumDiscountSeries**: A derived time series for a mapped cross-listed ticker showing premium/discount values and calculation inputs/assumptions.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: For a single ticker with at least 2 years of daily data, the app computes and displays VaR (95%/99%) and Sharpe alongside the prediction within 2 seconds on a typical user machine.
- **SC-002**: For a fixed, versioned sample dataset, the reported VaR (95%/99%) and Sharpe values match expected reference results within a documented tolerance.
- **SC-003**: For a single ticker with at least 2 years of daily data, the app computes and records ADF + Hurst outputs within 2 seconds and displays a regime classification without requiring network access beyond free-data fetching.
- **SC-004**: Backtesting results for a single ticker over 5 years of daily data update in under 5 seconds and always report performance net-of-transaction-costs.
- **SC-005**: When transaction costs are enabled, the backtest report clearly shows the cost assumptions used and the difference between gross and net performance.
- **SC-006**: In federated mode with up to 10 tickers and at least 3 years of overlapping daily history, portfolio insights (efficient frontier summary and suggested weights) are produced within 10 seconds and include stated constraints and risk metrics.
