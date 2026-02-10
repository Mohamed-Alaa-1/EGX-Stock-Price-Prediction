# Implementation Plan: EGX Price Prediction UI

**Branch**: `001-egx-price-prediction` | **Date**: 2026-02-10 | **Spec**: [specs/001-egx-price-prediction/spec.md](spec.md)
**Input**: Feature specification from [specs/001-egx-price-prediction/spec.md](spec.md)

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a local desktop app for EGX analysis and next trading-day close prediction with two tabs (Training and Prediction). The system fetches/caches historical OHLCV using free methods (with user-import fallback), trains PyTorch deep learning models (per-stock and optional federated simulation across multiple tickers), stores model artifacts locally for reuse, and renders an interactive TradingView-like chart with toggles (RSI/MACD/EMA/support-resistance). Key decisions are recorded in [specs/001-egx-price-prediction/research.md](research.md).

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PyTorch (modeling/training), yfinance (free market-data provider), PySide6 (desktop UI toolkit), QtWebEngine + Plotly.js (embedded HTML/JS chart with indicators)  
**Storage**: Local files (data cache + model artifacts) and JSON metadata store  
**Testing**: pytest  
**Target Platform**: Windows local desktop (primary); keep pathing portable  
**Project Type**: Single repository with an app package (desktop) and a core ML/data library  
**Performance Goals**: Training completes within a user-tolerable time (target: <10 minutes for typical stock on CPU); prediction returns <30 seconds on cached data  
**Constraints**: Free data only; offline-capable for viewing cached data; reproducible runs (seeded); no PII collection; no automated trading  
**Scale/Scope**: Single user; tens to hundreds of tickers; daily-resolution time series

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Pass: Local-first personal-use only (no accounts, no trading, no advice language).
- Pass: Free data sources only (automated free providers + user-import fallback).
- Pass: Minimal prediction scope (next trading-day close; label target date and data timestamp).
- Pass: Reproducible enough (record parameters, model version/config, seed; include baseline).
- Pass: Safety/robustness (clear labeling, graceful errors, correct trading-day handling).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
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
├── app/                 # Desktop UI app entrypoints and UI composition
├── core/                # Domain logic (stocks, calendars, indicators)
├── data/                # Data providers (free fetch + import), caching, schemas
├── ml/                  # PyTorch models, training loops, evaluation, persistence
└── services/            # Orchestration: train, predict, model registry

tests/
├── unit/
└── integration/
```

**Structure Decision**: Single local desktop application with a separated core library for data/ML so training and prediction logic can be tested independently of the UI.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase 2: Implementation Planning (stop after this section)

### Re-check Constitution (post-design)

- Local-first: maintained (no cloud required; local API contract is internal only).
- Free data only: maintained (provider is pluggable; CSV import fallback is specified).
- Minimal prediction scope: maintained (next trading-day close; target date and data timestamp required).
- Reproducibility: maintained (entities include seed, model metadata, artifact registry).
- Safety/robustness: maintained (baseline + clear labeling; staleness + training failures handled).

### Implementation Steps (high-level)

1. **Repository scaffolding**
  - Create `src/` layout from Project Structure section.
  - Define configuration for data paths (cache directory, models directory).

2. **Stock universe (EGX list)**
  - Add a local EGX stock list source (static seed file + optional update path).
  - Implement search and selection model for the UI.

3. **Data layer**
  - Implement provider interface: `get_prices(symbol, start, end)`.
  - Implement free provider(s) and CSV import.
  - Normalize OHLCV to `PriceBar` and validate.
  - Add caching + provenance (`DataSourceRecord`).

4. **Indicators**
  - Implement deterministic RSI, MACD, EMA calculations.
  - Implement support/resistance heuristic (documented and deterministic).

5. **Model registry + persistence**
  - Define `ModelArtifact` metadata store and filesystem layout.
  - Implement staleness detection (>14 days) and display messaging hooks.

6. **Training pipeline (PyTorch)**
  - Implement per-stock training pipeline (dataset windowing, train/val split).
  - Implement federated simulation training pipeline (FedAvg-style aggregation across selected tickers).
  - Record baseline metrics and model metrics.
  - Save artifacts and update `last_trained_at`.

7. **Prediction pipeline**
  - Implement next-trading-day target selection.
  - Load selected model (per-stock or federated) and produce forecast.
  - Compute baseline, expected % change, momentum label.

8. **Desktop UI**
  - Implement exactly two tabs: Training + Prediction.
  - Training tab: stock/multi-stock selection, federated toggle, Train action, progress.
  - Prediction tab: chart, indicator toggles, predict action, model-choice toggle when both available.
  - Missing model flow: prompt user, navigate to Training tab, prefill selection, start training.

9. **Testing gates**
  - Unit tests: data normalization/validation; indicator computations; trading-day logic; model staleness.
  - Integration tests: training -> artifact -> prediction uses saved model.
  - Determinism tests: fixed seed yields stable outputs (within tolerance) for a fixed dataset.

### Verification Checklist

- Training tab can train and save per-stock model for one ticker.
- Federated training saves a federated artifact that lists `covered_symbols`.
- Prediction tab works offline with cached data.
- If no model exists, the train prompt + auto navigation works end-to-end.
- Chart toggles show/hide RSI/MACD/EMA/support-resistance without errors.
- Output always includes predicted value, target date, and latest data date.
