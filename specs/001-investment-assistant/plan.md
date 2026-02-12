# Implementation Plan: Investment Assistant (Strategy Engine + Journal)

**Branch**: `001-investment-assistant` | **Date**: 2026-02-12 | **Spec**: [specs/001-investment-assistant/spec.md](spec.md)
**Input**: Feature specification from [specs/001-investment-assistant/spec.md](spec.md)

## Summary

Transform the app from a raw next-close predictor into an **Investment Assistant** by:
- Adding a `StrategyEngine` service that ensemble-weights ML forecast + RSI/MACD/EMA + VaR risk + ADF/Hurst regime and outputs a `StrategyRecommendation` (Buy/Sell/Hold) with entry/target/stop and conviction.
- Refactoring the Prediction tab into a **Strategy Dashboard** (assistant banner + evidence panel + decision buttons) while keeping a **separate raw forecast section**.
- Adding a **Local Trade Journal** (SQLite) and a minimal **Performance Review** that reports assistant outcomes over time from journaled simulated trades.

Related design artifacts:
- Phase 0 decisions: [specs/001-investment-assistant/research.md](research.md)
- Phase 1 data model: [specs/001-investment-assistant/data-model.md](data-model.md)
- Contracts: [specs/001-investment-assistant/contracts/local-api.yaml](contracts/local-api.yaml)
- User quickstart: [specs/001-investment-assistant/quickstart.md](quickstart.md)

## Technical Context

**Language/Version**: Python 3.11 (per [pyproject.toml](../../pyproject.toml))

**Primary Dependencies**:
- UI: PySide6 (+ WebEngine for Plotly chart)
- ML: torch
- Data: pandas, numpy
- Schemas: pydantic v2
- Quant: scipy, statsmodels
- Data fetching: yfinance (free)

**Storage**:
- Existing: Parquet cache for price series (`data/cache/`), JSON metadata (`data/metadata/*.json`)
- New: SQLite trade journal DB (`data/metadata/trade_journal.sqlite3`) via stdlib `sqlite3`

**Testing**: pytest (already configured in `pyproject.toml`)

**Target Platform**: Local desktop (Windows primary; should remain cross-platform where dependencies allow)

**Project Type**: Single local desktop application (PySide6) with service layer under `src/services/`

**Performance Goals**:
- Strategy recommendation computation should complete in under ~300ms on cached daily data for a single symbol (excluding network fetch).

**Constraints**:
- Local-first; personal-use only; not financial advice.
- No brokerage integration or automated trading.
- Free data sources only; degrade gracefully when providers break.

**Scale/Scope**:
- Single user; tens of symbols; daily timeframes are the primary path.

## Constitution Check

GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.

- Local-first, personal-use only; not financial advice; no brokerage integration.
  - PASS: Strategy outputs are advisory-only and remain local; UI keeps disclaimer banner.
- Free data sources only; graceful degradation on rate limits/breakages.
  - PASS: Uses existing provider registry; strategy uses cached series and defaults to HOLD when inputs are missing.
- Every prediction includes risk context (at minimum 1-day VaR with assumptions).
  - PASS: `PredictionService` already attaches VaR snapshot; strategy engine consumes the same VaR.

If the feature produces an “Assistant” recommendation (Buy/Sell/Hold):
- Risk-First policy (capital preservation; default HOLD on uncertainty)
  - PASS: HOLD on missing/low-quality/conflicting inputs.
- Stop-Loss always included (explicit N/A when HOLD)
  - PASS: Stop derived from VaR for BUY/SELL; HOLD shows N/A.
- Conviction Score always included (stable scale; lowered on signal disagreement)
  - PASS: Conviction computed on 0–100 and reduced on disagreement.
- Technical signals explicitly weighted against ML predictions (weights disclosed)
  - PASS: Weight table is explicit; evidence panel shows weights.
- UI clearly separates raw model outputs from Assistant-processed recommendation
  - PASS: Strategy Dashboard includes distinct “Assistant Recommendation” vs “Raw Forecast” sections.

## Project Structure

### Documentation (this feature)

```text
specs/001-investment-assistant/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── local-api.yaml
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/
├── app/
│   ├── main.py
│   └── ui/
│       ├── prediction_tab.py          # refactor into Strategy Dashboard
│       └── performance_tab.py         # new: Performance Review
├── core/
│   ├── config.py                      # add trade journal DB path constant
│   ├── indicators.py                  # RSI/MACD/EMA already present
│   ├── quant.py                       # VaR + ADF + Hurst already present
│   └── schemas.py                     # add recommendation + journal schemas
└── services/
    ├── prediction_service.py          # already produces raw forecast + risk/validation
    ├── risk_service.py                # VaR snapshot
    ├── signal_validation_service.py   # ADF + Hurst
    ├── strategy_engine.py             # new
    └── portfolio_tracker.py           # new (journal + performance)

tests/
└── unit/
    ├── test_strategy_engine.py
    ├── test_portfolio_tracker.py
    └── test_trade_journal_store.py
```

**Structure Decision**: Single-project desktop app; implement new functionality in `src/services/` and keep UI logic in `src/app/ui/`.

## Phase 0: Outline & Research (completed)

Completed in [specs/001-investment-assistant/research.md](research.md).

Key outcomes:
- SQLite chosen for local trade journal.
- Trade-level metrics define assistant accuracy (win rate, avg return, stop-loss hit rate).
- Ensemble blending is explicit and explainable; regime adjusts weights/targets.

## Phase 1: Design & Contracts (completed)

Artifacts:
- Data model: [specs/001-investment-assistant/data-model.md](data-model.md)
- Contracts: [specs/001-investment-assistant/contracts/local-api.yaml](contracts/local-api.yaml)
- Quickstart: [specs/001-investment-assistant/quickstart.md](quickstart.md)

### Constitution re-check (post-design)

- PASS: Design explicitly separates raw forecast vs assistant recommendation.
- PASS: Stop-loss and VaR framing are explicit and local-first.
- PASS: Recommendation policy defaults HOLD on uncertainty and lowers conviction on disagreement.

## Phase 2: Implementation Plan (this plan ends here)

### Phase 2.1 — Core Logic & Schemas (P1)

1. **Add schemas** in `src/core/schemas.py`:
   - `StrategyAction`, `EvidenceDirection`, `EvidenceSource`
   - `EvidenceSignal`, `StrategyRecommendation`
   - `TradeJournalEntry`, `PerformanceSummary` (minimal)

2. **Add storage path** in `src/core/config.py`:
   - `TRADE_JOURNAL_DB_PATH = METADATA_DIR / "trade_journal.sqlite3"`

3. **Implement `StrategyEngine`** in `src/services/strategy_engine.py`:
   - Inputs: `symbol`, `forecast_method`
   - Dependencies:
     - `PriceService` or `PredictionService` for series/forecast
     - `RiskService` for VaR
     - `SignalValidationService` for ADF/Hurst regime
     - `core.indicators` for RSI/MACD/EMA values
   - Output: `StrategyRecommendation` with:
     - explicit weights (from spec)
     - blended score and conviction
     - risk-anchored stop and regime-adjusted targets
     - evidence lists (bullish/bearish/neutral)
   - Risk-first behavior:
     - if required inputs missing or risk too high → HOLD with explanation

4. **Unit tests (P1)**:
   - `test_strategy_engine.py` validates:
     - HOLD on missing inputs
     - BUY/SELL when aligned and above threshold
     - conviction reduction on disagreement
     - stop-loss present for BUY/SELL and N/A for HOLD

### Phase 2.2 — UI Refactor into Strategy Dashboard (P2)

1. **Refactor `src/app/ui/prediction_tab.py`**:
   - Rename the tab label in `src/app/main.py` from “Prediction” to “Strategy”.
   - Add an “Assistant Recommendation” group above/near existing results:
     - Recommendation Banner (color-coded)
     - Entry/Target/Stop + Conviction
     - Evidence Panel (text list of bullish/bearish signals)
     - Buttons: Execute Entry, Log Exit
   - Keep an explicit “Raw Forecast” group that shows:
     - predicted close, baseline, staleness, VaR snapshot, validation warnings

2. **UI data flow**:
   - After `Predict` completes (raw forecast), call `StrategyEngine` to compute the assistant recommendation and populate the banner + evidence.
   - If raw forecast isn’t available (e.g., user chooses not to run), allow computing recommendation using a baseline forecast method.

3. **Interaction wiring**:
   - Execute Entry logs an entry with recommendation snapshot.
   - Log Exit closes the open position for the symbol (if any).
   - Show user-friendly errors when journaling isn’t possible (no symbol, no open position).

### Phase 2.3 — Persistence & Performance Review (P2)

1. **Implement `PortfolioTracker`** in `src/services/portfolio_tracker.py`:
   - SQLite initialization and schema creation on first use.
   - Methods:
     - `log_entry(symbol, side, price, recommendation)`
     - `log_exit(symbol, side, price, notes=None)`
     - `get_open_positions(symbol=None)`
     - `get_performance_summary(symbol=None)`
   - Performance summary computed from closed positions:
     - closed trade count, win rate, avg return, stop-loss hit rate
   - Stop-loss hit detection using daily OHLCV between entry and exit (conservative convention when ambiguous).

2. **Add `PerformanceTab` UI** in `src/app/ui/performance_tab.py`:
   - Minimal read-only view that displays `PerformanceSummary` and open trade count.
   - Trigger refresh on tab activation and after logging entry/exit.

3. **Unit tests (P2)**:
   - journal CRUD (create entry/exit)
   - performance summary metrics on a small synthetic trade set

## Complexity Tracking

No constitution gate violations are required for this feature.
