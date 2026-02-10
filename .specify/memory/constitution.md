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

### III. Minimal Prediction Scope
- Supported target: predict the closing price for either:
	- “next trading day close” (default), or
	- “today’s close” only when the market session is not yet closed (clearly labeled as an estimate).
- The output must include:
	- the predicted value,
	- the prediction date/target session,
	- the last available data timestamp used.

### IV. Reproducible and Explainable Enough
- Every prediction run records: ticker, date range used, data source, model version/config, and a random seed (when applicable).
- Provide a baseline (e.g., “naive: last close”) alongside the model prediction.
- Prefer simple models by default; only add complexity when it clearly improves validation metrics.

### V. Safety, Honesty, and Robustness
- Never claim certainty; always present outputs as probabilistic/approximate.
- Clearly label when the market is closed/open and whether the target close is already known.
- Validate inputs (ticker format, date range) and handle missing/holiday data correctly.

## Constraints
- No paid APIs, paid datasets, or mandatory accounts.
- Store data locally only (CSV/SQLite/Parquet are acceptable).
- Do not collect or transmit personal data.

## Development Workflow
- Keep the app small and maintainable (YAGNI).
- Add unit tests for:
	- data fetching/parsing,
	- trading-day calendar handling,
	- prediction pipeline determinism (when seed is set).
- When changing a data source or model, update any docs/notes that describe assumptions.

## Governance
- This document is the top-level constraints for this repo.
- Any change that expands scope (new targets, new markets, new data sources) must update this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-02-10 | **Last Amended**: 2026-02-10
