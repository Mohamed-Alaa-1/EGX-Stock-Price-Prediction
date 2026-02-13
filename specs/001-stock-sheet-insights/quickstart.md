# Quickstart: Stock Sheet Investment Insights

**Date**: 2026-02-13  
**Branch**: `001-stock-sheet-insights`

## What this feature does

Shows investment insights (Buy/Sell/Hold) for every stock you added to your stock sheet, with:
- Conviction score
- Stop-loss and target (when applicable)
- A short explanation and evidence

## How to use

1. Open the app.
2. Ensure your stock sheet contains the stocks you care about (use the Stock Manager tab to add/remove).
3. Open the **Stock Sheet Insights** tab.
4. Click **Train + Analyze Sheet (Force Refresh)**.

## Interpreting results

- **BUY / Buy more**: indicates the assistant sees an attractive opportunity *with risk controls*.
- **SELL**: indicates expected downside risk.
- **HOLD**: means uncertainty, conflicting signals, or missing data; stop-loss is shown as N/A.

Each row shows:
- Action, Conviction
- Stop-loss and Target (or N/A)
- Status and any warning reason

## Data freshness and failures

- The batch action attempts to retrieve fresh data first (not from cache by default).
- If fresh retrieval fails for a stock, the app may fall back to cached data only for that stock and will label that a fallback happened.
- Failures on one stock do not stop analysis for other stocks.

## Important

This feature is for personal experimentation only and is **not financial advice**.
