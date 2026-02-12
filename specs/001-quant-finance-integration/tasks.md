---

description: "Task list for Quantitative Finance Integration implementation"
---

# Tasks: Quantitative Finance Integration

**Input**: Design documents in `specs/001-quant-finance-integration/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Every task includes an exact file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure required dependencies and repo-wide defaults exist for this feature.

- [x] T001 Update dependencies for quant finance in requirements.txt (add `scipy` and `statsmodels`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared building blocks used by all user stories.

**⚠️ CRITICAL**: No user story work should start until this phase is complete.

- [x] T002 Add shared PriceSeries→DataFrame helpers in src/core/series_utils.py (sorted bars, close series, simple/log returns)
- [x] T003 Add risk + validation schemas to src/core/schemas.py (RiskMetricsSnapshot, StatisticalValidationResult)
- [x] T004 Add backtest + cost schemas to src/core/schemas.py (TransactionCostModel, BacktestRun)
- [x] T005 Add portfolio + GDR schemas to src/core/schemas.py (PortfolioOptimizationResult, GdrPremiumDiscountSeries)
- [x] T006 Add feature defaults/constants in src/core/config.py (default lookbacks, default EGX cost bps, default risk-free rate labeling)

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 — Risk & Signal Context (Priority: P1) 🎯 MVP

**Goal**: Every prediction includes VaR+Sharpe and statistical context (ADF+Hurst) with clear assumptions and “insufficient data” behavior.

**Independent Test**: In the app, select a ticker with sufficient history and click Predict; verify the results include VaR 95/99 + assumptions, Sharpe + assumptions, ADF + Hurst + regime classification; verify “insufficient data” for short histories.

### Implementation (User Story 1)

- [x] T007 [US1] Implement VaR + Sharpe computations in src/core/quant.py (return conventions, assumptions, insufficient-data handling)
- [x] T008 [US1] Implement ADF + Hurst computations in src/core/quant.py (statsmodels ADF wrapper; Hurst agg-variance + regime classification + diagnostics)
- [x] T009 [P] [US1] Implement risk snapshot orchestration in src/services/risk_service.py (build RiskMetricsSnapshot from PriceSeries + Config defaults)
- [x] T010 [P] [US1] Implement signal validation orchestration in src/services/signal_validation_service.py (ADF + Hurst + warnings from PriceSeries)
- [x] T011 [US1] Integrate risk+validation+baseline into predictions in src/services/prediction_service.py (compute on every predict; attach results + baseline to ForecastResult.model_features)
- [x] T012 [US1] Render risk+validation+baseline in the UI in src/app/ui/prediction_tab.py (show prediction + baseline, VaR+Sharpe+ADF+Hurst with assumptions and "insufficient data" messages)
- [x] T013 [US1] Run validation before training in src/services/training_service.py (compute ADF/Hurst prior to train; persist outputs into ModelArtifact.hyperparams and log warnings)
- [x] T014 [US1] Surface validation outputs in src/app/ui/training_tab.py (display ADF p-value, Hurst, regime, and warnings during/after training)

**Checkpoint**: US1 is complete when Prediction and Training workflows both show the new analytics without breaking existing functionality.

---

## Phase 4: User Story 2 — Backtesting + Portfolio Insights (Priority: P2)

**Goal**: Provide realistic backtests net-of-cost and portfolio insights (efficient frontier + risk parity) in federated mode.

**Independent Test**: Run a backtest on one ticker over a fixed date range and verify results include gross and net-of-cost performance (with commissions+stamp duty assumptions). In federated mode with multiple tickers, compute portfolio insights and verify MPT frontier summary + risk parity weights and risk contributions.

### Implementation (User Story 2)

- [x] T015 [US2] Implement vectorized backtester in src/core/backtest.py (signal-at-t, trade-at-(t+1)-close; turnover-based costs; gross vs net returns; drawdown and turnover metrics)
- [x] T016 [P] [US2] Add backtest orchestration in src/services/backtest_service.py (fetch series, run core.backtest, return BacktestRun summary)
- [x] T017 [US2] Add minimal backtest controls + results display in src/app/ui/prediction_tab.py (strategy select: RSI/MACD/EMA; date range defaults; cost params; show gross vs net)
- [x] T018 [US2] Implement portfolio optimizers in src/ml/portfolio.py (covariance estimation + stabilization, min-variance, efficient frontier grid, risk parity, risk contributions)
- [x] T019 [P] [US2] Add portfolio orchestration in src/services/portfolio_service.py (align multi-symbol returns window, compute mu/cov, call ml.portfolio, return PortfolioOptimizationResult)
- [x] T020 [US2] Add federated portfolio insights UI in src/app/ui/training_tab.py (button + output panel for MPT frontier summary and risk parity weights + contributions)

**Checkpoint**: US2 is complete when backtests always report net-of-cost metrics and federated portfolio insights produce explainable allocations.

---

## Phase 5: User Story 3 — GDR Premium/Discount Signal (Priority: P3)

**Goal**: Show a premium/discount time series for cross-listed stocks when mappings and free data exist; degrade gracefully otherwise.

**Independent Test**: Configure a cross-list mapping; compute premium/discount and verify a time series renders; break one input (missing FX or GDR series) and verify a clear error state without breaking other analytics.

### Implementation (User Story 3)

- [x] T021 [US3] Create cross-list mapping registry file in data/metadata/cross_listings.json (schema + empty/default example)
- [x] T022 [US3] Implement premium/discount calculation service in src/services/gdr_bridge_service.py (load mapping, fetch/cache local+GDR+FX primitives, align dates, compute premium series, return warnings on missing inputs)
- [x] T023 [US3] Extend chart data contract in src/app/ui/web_bridge.py to accept an optional premium/discount time series payload
- [x] T024 [US3] Render premium/discount series in the chart UI in src/app/ui/chart_template.html (add a Plotly trace/subplot and label definition)
- [x] T025 [US3] Wire premium/discount to the chart panel in src/app/ui/chart_panel.py (send series to web bridge; preserve existing RSI/MACD/EMA/SR)
- [x] T026 [US3] Add premium/discount controls in src/app/ui/prediction_tab.py (compute button; display last value + status; handle unmapped/missing data gracefully)

**Checkpoint**: US3 is complete when premium/discount works for mapped symbols and fails gracefully when inputs are missing.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Make the feature robust, consistent, and easy to validate.

- [x] T027 [P] Validate P1/P2/P3 flows by following specs/001-quant-finance-integration/quickstart.md end-to-end
- [x] T028 [P] Run `ruff check .` using ruff.toml and fix any violations in the files Ruff reports
- [x] T029 [P] Add unit tests for VaR + Sharpe in tests/unit/test_quant_var_sharpe.py (include insufficient-data cases and tolerance-based assertions)
- [x] T030 [P] Add unit tests for ADF + Hurst in tests/unit/test_quant_adf_hurst.py (cover stable synthetic series + regime classification thresholds)
- [x] T031 [P] Add unit tests for EGX cost model/backtest accounting in tests/unit/test_backtest_cost_model.py (gross vs net, commissions + stamp duty)
- [x] T032 [P] Add unit tests for portfolio optimizers in tests/unit/test_portfolio_optimizers.py (long-only constraints, risk parity contributions sum checks)
- [x] T033 [P] Add a small fixed reference dataset/fixture + expected metric values to support SC-002 (place under tests/fixtures/ and document tolerances)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → **User stories (Phases 3–5)** → **Polish (Phase 6)**

### User Story Dependencies

- **US1 (P1)** depends on Phase 1–2 completion.
- **US2 (P2)** depends on Phase 1–2 completion and reuses `src/core/series_utils.py`.
- **US3 (P3)** depends on Phase 1–2 completion and is otherwise independent of US2.

Dependency graph (story-level):

- Setup/Foundational → US1
- Setup/Foundational → US2
- Setup/Foundational → US3

Suggested delivery order:

- MVP: **US1 only**
- Next: US2
- Last: US3

---

## Parallel Execution Examples

### US1 parallelizable example

- Task: T009 Implement risk snapshot orchestration in src/services/risk_service.py
- Task: T010 Implement signal validation orchestration in src/services/signal_validation_service.py

### US2 parallelizable example

- Task: T016 Add backtest orchestration in src/services/backtest_service.py
- Task: T019 Add portfolio orchestration in src/services/portfolio_service.py

### US3 parallelizable example

- Task: T023 Extend chart data contract in src/app/ui/web_bridge.py
- Task: T024 Render premium/discount series in the chart UI in src/app/ui/chart_template.html

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 + Phase 2
2. Implement US1 (T007–T014)
3. Validate US1 via the P1 steps in specs/001-quant-finance-integration/quickstart.md

### Incremental Delivery

- Add US2 (T015–T020), validate P2 quickstart scenarios
- Add US3 (T021–T026), validate P3 quickstart scenarios

---

## Format validation

- All tasks are in checklist format `- [ ] T### ...`.
- `[P]` is used only when tasks can be done in parallel (different files, minimal dependencies).
- `[US#]` labels are applied to user-story phases only.
- Every task includes an exact file path.
