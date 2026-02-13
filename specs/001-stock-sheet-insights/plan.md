# Implementation Plan: Stock Sheet Investment Insights (Batch Train + Analyze)

**Branch**: `001-stock-sheet-insights` | **Date**: 2026-02-13 | **Spec**: [specs/001-stock-sheet-insights/spec.md](spec.md)
**Input**: Feature specification from [specs/001-stock-sheet-insights/spec.md](spec.md)

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a sheet-wide insights workflow that:
- Computes Buy/Sell/Hold recommendations (with stop-loss + conviction + evidence) for every enabled stock in the user’s stocks sheet.
- Provides a single **batch action** (“Train + Analyze Sheet (Force Refresh)”) that attempts fresh retrieval (no-cache default), trains/updates models as needed, and produces per-stock results without letting single-stock failures interrupt the full run.
- Presents results in a dedicated UI view with a per-stock status and drill-down into evidence.

Related design artifacts:
- Phase 0 decisions: [specs/001-stock-sheet-insights/research.md](research.md)
- Phase 1 data model: [specs/001-stock-sheet-insights/data-model.md](data-model.md)
- Contracts: [specs/001-stock-sheet-insights/contracts/local-api.yaml](contracts/local-api.yaml)
- User quickstart: [specs/001-stock-sheet-insights/quickstart.md](quickstart.md)

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (per [pyproject.toml](../../pyproject.toml))  
**Primary Dependencies**:
- UI: PySide6
- ML: torch
- Data: pandas, numpy
- Schemas: pydantic v2 (in `src/core/schemas.py`)
- Data fetching: yfinance + provider registry under `src/data/providers/`

**Storage**:
- Price cache: Parquet under `data/cache/` via `src/data/cache_store.py`
- Stock sheet source: CSV under `src/data/egx_stocks.csv` via `src/services/stock_universe_manager.py`
- Models/metadata: JSON + `data/models/` via `src/services/model_registry.py`

**Testing**: pytest (configured in [pyproject.toml](../../pyproject.toml))  
**Target Platform**: Local desktop (Windows primary; keep cross-platform where dependencies allow)
**Project Type**: Single local desktop application with a services layer under `src/services/`  

**Performance Goals**:
- Batch run should keep UI responsive (background thread) and stream partial results.
- For a sheet of ~50 symbols, batch analysis should complete in a few minutes depending on network/training; UI must never freeze.

**Constraints**:
- Local-first; personal-use only; not financial advice.
- Free data sources only; degrade gracefully when providers break.
- Batch action must not be blocked by single-stock errors.

**Scale/Scope**: Single user; tens of symbols; daily timeframe.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

For this repository, plans MUST explicitly confirm the following gates when applicable:

- Local-first, personal-use only; not financial advice; no brokerage integration.
- Free data sources only; graceful degradation on rate limits/breakages.
- Every prediction includes risk context (at minimum 1-day VaR with assumptions).

- If the feature produces an “Assistant” recommendation (Buy/Sell/Hold):
  - Risk-First policy (capital preservation; default HOLD on uncertainty)
  - Stop-Loss always included (explicit N/A when HOLD)
  - Conviction Score always included (stable scale; lowered on signal disagreement)
  - Technical signals are explicitly weighted against ML predictions (weights disclosed)
  - UI clearly separates raw model outputs from Assistant-processed recommendation

Constitution gate evaluation for this feature:

- Local-first, personal-use only; not financial advice; no brokerage integration.
  - PASS: The batch workflow is local, advisory-only, and will reuse existing disclaimer UI.
- Free data sources only; graceful degradation on rate limits/breakages.
  - PASS: Uses existing provider registry; per-stock failures do not abort the batch; optional cache fallback can be clearly labeled.
- Every prediction includes risk context (at minimum 1-day VaR with assumptions).
  - PASS: Strategy recommendations are risk-first and are derived from VaR/volatility inputs already computed locally.

If the feature produces an “Assistant” recommendation (Buy/Sell/Hold):
- Risk-First policy
  - PASS: Defaults to HOLD on missing inputs/conflicts.
- Stop-Loss always included (N/A when HOLD)
  - PASS: Reuses `StrategyEngine` behavior.
- Conviction Score always included
  - PASS: Reuses `StrategyEngine` behavior.
- Technical weighted against ML; weights disclosed
  - PASS: Reuses `StrategyEngine` explicit default weights.
- UI separates raw model outputs vs assistant output
  - PASS: Drill-down view will keep distinct sections.

## Project Structure

### Documentation (this feature)

```text
specs/001-stock-sheet-insights/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── local-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── app/
│   ├── main.py
│   └── ui/
│       ├── stock_manager_tab.py              # stock sheet (CSV) management
│       ├── prediction_tab.py                 # single-symbol strategy dashboard
│       └── stock_sheet_insights_tab.py       # new: batch insights UI (planned)
├── core/
│   └── schemas.py                            # add batch insight schemas (planned)
└── services/
  ├── stock_sheet_insights_service.py       # new: batch orchestration (planned)
  ├── price_service.py                      # already supports use_cache flag
  ├── training_service.py                   # batch training per stock
  ├── prediction_service.py                 # may be extended to support no-cache fetch
  └── strategy_engine.py                    # already implements risk-first recommendation

tests/
└── unit/
  ├── test_stock_sheet_insights_service.py  # new
  └── test_price_service_no_cache.py        # new

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: Single-project desktop app; implement batch orchestration in `src/services/` and add one new UI tab under `src/app/ui/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase 0: Outline & Research (completed)

Completed in [specs/001-stock-sheet-insights/research.md](research.md).

Key outcomes:
- “Stocks sheet” maps to the existing CSV-driven user-managed list.
- Batch run uses a background worker and streams per-stock results.
- Fresh retrieval is attempted per stock; fallback to cache is allowed only when explicitly labeled.

## Phase 1: Design & Contracts (completed)

Artifacts:
- Data model: [specs/001-stock-sheet-insights/data-model.md](data-model.md)
- Contracts: [specs/001-stock-sheet-insights/contracts/local-api.yaml](contracts/local-api.yaml)
- Quickstart: [specs/001-stock-sheet-insights/quickstart.md](quickstart.md)

### Constitution re-check (post-design)

- PASS: Batch results include Buy/Sell/Hold + Stop-Loss (or N/A) + Conviction.
- PASS: Risk-first HOLD default on partial failures.
- PASS: Drill-down keeps raw model outputs separate from assistant recommendation.

## Phase 2: Implementation Plan (this plan ends here)

### Phase 2.1 — Batch Orchestration Service (P1)

1. Add pydantic schemas in `src/core/schemas.py` for:
  - `InsightStatus`, `StockInsight`, `InsightBatchRun`
  - `SheetInsightsRunRequest` (symbols, train_models, force_refresh, forecast_method)

2. Implement `StockSheetInsightsService` in `src/services/stock_sheet_insights_service.py`:
  - Load enabled symbols from the stock sheet CSV.
  - For each symbol:
    - Fetch series with `PriceService.get_series(symbol, use_cache=False)`.
    - On fetch error: optionally load cached series and label it, otherwise produce HOLD fallback.
    - If training enabled: call `TrainingService.train_per_stock(symbol, series)`.
    - Produce forecast (ML if available, else baseline) and compute recommendation via `StrategyEngine`.
  - Collect per-stock status without aborting the full batch.

3. Unit tests:
  - Batch continues on per-symbol errors.
  - Force-refresh attempts no-cache fetch.
  - Cache fallback is labeled.

### Phase 2.2 — UI: Stock Sheet Insights Tab (P1)

1. Add `src/app/ui/stock_sheet_insights_tab.py`:
  - Button: “Train + Analyze Sheet (Force Refresh)”.
  - Table/list of results (symbol, action, conviction, stop-loss, target, status, reason).
  - Progress indicator (completed/total).
  - Row selection opens a detail panel (evidence + raw outputs sections).

2. Wire tab into `src/app/main.py`.

### Phase 2.3 — Polish & Resilience (P2)

- Provide a non-training refresh action for faster updates.
- Add cancel/stop capability for long runs (optional).
- Ensure long operations never block the UI thread.
