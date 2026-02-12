# Quickstart: Quantitative Finance Integration

This quickstart validates the feature end-to-end against P1–P3 in [specs/001-quant-finance-integration/spec.md](spec.md).

## Prereqs
- Python 3.11+ (see [pyproject.toml](../../pyproject.toml))
- Install deps: `pip install -r requirements.txt`
- Planned deps for this feature (if/when implemented): `scipy`, `statsmodels`

> Note: This repo is a local desktop app. The steps below describe the user workflow and the intended outputs; implementation lands in Phase 2.

---

## P1 — Risk & Signal Context (VaR, Sharpe, ADF, Hurst)

### Scenario: Prediction includes risk companion
1. Launch the app.
2. Go to the **Prediction** tab.
3. Select a ticker with sufficient daily history.
4. Click **Predict**.

Expected:
- Prediction output shows:
  - predicted close + target date
  - 1-day VaR at 95% and 99% with assumptions (method + lookback)
  - Sharpe ratio with the same stated lookback and return convention
- If history is too short, each missing metric shows **"Insufficient data"** (not a silent numeric fallback).

### Scenario: Training records ADF + Hurst
1. Go to the **Training** tab.
2. Train/retrain a ticker.

Expected:
- The run records ADF p-value and Hurst estimate (with regime classification).
- If validation indicates weak signal, the UI/logs clearly surface a warning.

---

## P2 — Backtesting + Portfolio Insights

### Scenario: Backtest is net-of-cost
1. Choose an indicator strategy (RSI/MACD/EMA) and a historical window.
2. Run a backtest.

Expected:
- Report shows **gross** and **net-of-cost** metrics.
- Transaction cost assumptions include at least:
  - commissions
  - stamp duties
- The report shows the cost assumptions used and the cost impact (gross vs net).

### Scenario: Federated portfolio insights (MPT + risk parity)
1. Enter/enable federated mode with multiple tickers (≥2).
2. Request portfolio insights.

Expected:
- Efficient-frontier style risk/return summary is produced (with stated window).
- At least one long-only MPT allocation is shown under stated constraints.
- A risk-parity allocation is shown with per-ticker risk contributions.

---

## P3 — GDR Premium/Discount (optional when data exists)

### Scenario: Premium/discount series computes from mapping + cached primitives
1. Configure a cross-list mapping (local symbol, GDR symbol, ratio, FX pair).
2. Ensure local, GDR, and FX series exist via free providers and/or CSV import.
3. View the premium/discount overlay.

Expected:
- Premium/discount is plotted and labeled with the definition.
- If any input is missing or stale, the UI clearly explains why and continues to work for the rest of analytics.

---

## Done checklist
- P1: prediction always includes VaR 95/99 + assumptions
- P1: ADF + Hurst recorded before training
- P2: backtests are always net-of-cost; cost model assumptions displayed
- P2: federated portfolio insights include MPT frontier + risk parity with risk contributions
- P3: premium/discount works when inputs exist and fails gracefully when they don’t
