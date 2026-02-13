# Phase 0 Research: Stock Sheet Investment Insights (Batch Train + Analyze)

**Date**: 2026-02-13  
**Branch**: `001-stock-sheet-insights`

## Decision 1: What is the “stocks sheet” source of truth?

- **Decision**: Treat the existing CSV-driven stock list as the “stocks sheet”.
- **Rationale**: The current app already supports user-managed add/remove of symbols via the Stock Manager tab, persisted in `src/data/egx_stocks.csv` and loaded via `StockUniverseManager` / `load_stock_universe()`.
- **Alternatives considered**:
  - Separate watchlist file/database: rejected for MVP because it duplicates existing behavior.

## Decision 2: How to implement “Train + Analyze Sheet (Force Refresh)”

- **Decision**: Implement a batch orchestration service that iterates symbols and emits per-stock results, using background threading so the UI never blocks.
- **Rationale**: Batch operations (network fetch + ML training) are long-running; PySide6 UI must remain responsive.
- **Alternatives considered**:
  - Sequential run on UI thread: rejected (freezes UI).
  - Multiprocessing: rejected for MVP (complexity, torch serialization, Windows quirks).

## Decision 3: “Do not use cache” vs graceful fallback

- **Decision**: During the batch action, attempt fresh retrieval per symbol (no-cache default). If fresh retrieval fails, allow per-symbol fallback to cached series *only when clearly labeled*; otherwise produce a HOLD fallback with a clear reason.
- **Rationale**: This respects the intent (“don’t rely on cache”) while still meeting resilience (“don’t let failures interrupt analysis”).
- **Alternatives considered**:
  - Hard-disable cache fallback: rejected because it produces too many empty rows when a provider is rate-limited.

## Decision 4: How to compute buy/sell/hold and levels

- **Decision**: Reuse the existing `StrategyEngine` recommendation logic (risk-first, stop-loss, conviction, ML-vs-technical weighting) for each stock.
- **Rationale**: The engine already implements constitution-required behavior and UI separation expectations.
- **Alternatives considered**:
  - A new heuristic recommender: rejected (duplicate logic; higher risk of constitution violations).

## Decision 5: How to handle partial failures

- **Decision**: A failure on one stock MUST NOT abort the batch. Return a per-stock status (`OK`, `HOLD_FALLBACK`, `ERROR`) plus a user-readable reason.
- **Rationale**: Matches spec FR-006d and user requirement.
- **Alternatives considered**:
  - Abort the whole batch on first error: rejected.
