# Tasks: EGX Price Prediction – Enhancement Round

**Input**: Design documents from `/specs/001-egx-price-prediction/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md  

**Tests**: Not explicitly requested — test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## User Story Mapping

| Story | Title | Priority | Source |
|-------|-------|----------|--------|
| US1 | Timeframe-aware data fetching (1-day default for training) | P1 | User request: ensure training uses 1-day timeframe |
| US2 | Chart timeframe switching UI | P1 | User request: chart should plot 1-day with options to switch |
| US3 | TradingView data provider + launcher dialog | P2 | User request: tradingview-ta provider + provider choice dialog |
| US4 | AI model improvements (multi-feature, attention, LR scheduler) | P2 | User request: find improvement areas, plan, execute |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure the interval/timeframe parameter flows through the entire provider chain so all downstream features can specify intervals

- [x] T001 [US1] Add `interval: str = "1d"` parameter to abstract `fetch()` method in `src/data/providers/base.py`
- [x] T002 [US1] Add `interval` parameter to `fetch_with_fallback()` in `src/data/providers/registry.py` and pass to `provider.fetch()`
- [x] T003 [US1] Add `interval` parameter to `get_series()` in `src/services/price_service.py` and pass to `fetch_with_fallback()`
- [x] T004 [US1] Add `interval` parameter to `fetch()` in `src/data/providers/yfinance_provider.py` and pass `interval=interval` to `ticker.history()`
- [x] T005 [P] [US1] Add `interval` parameter to `fetch()` signature in `src/data/providers/csv_provider.py` (accept but ignore — CSV has no interval concept)

**Checkpoint**: The provider chain now accepts an `interval` parameter end-to-end; default is `"1d"` so existing behavior is unchanged

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Install new dependencies and verify existing infrastructure

- [x] T006 Install `tradingview-ta` package via `pip install tradingview-ta` for TradingView provider support
- [x] T007 Verify the app still launches correctly with `python -m src.app.main` after Phase 1 changes

**Checkpoint**: Dependencies installed, existing app functionality intact

---

## Phase 3: User Story 1 – Timeframe-Aware Training Data (Priority: P1) 🎯 MVP

**Goal**: Ensure the ML training pipeline explicitly fetches 1-day interval data, eliminating any ambiguity about monthly/weekly defaults

**Independent Test**: Train a model for any stock; verify the dataset contains daily bars (not monthly aggregates) by checking bar count and date spacing in the training log

### Implementation for User Story 1

- [x] T008 [US1] Update `_on_train` in `src/app/ui/training_tab.py` to pass `interval="1d"` to `registry.fetch_with_fallback()` calls (lines ~208 and ~217)
- [x] T009 [P] [US1] Add `features: list[str]` field to `TrainingConfig` in `src/ml/config.py` with default `["close", "open", "high", "low", "volume"]`
- [x] T010 [US1] Update `train_per_stock_model()` in `src/ml/train.py` to pass `config.features` to `TimeSeriesDataset` constructor
- [x] T011 [US1] Add log message in `src/ml/train.py` showing bar count, date range, and interval used before training starts
- [x] T012 [US1] Update `InferenceEngine.predict()` in `src/ml/inference.py` to read `features` from `artifact.hyperparams` and pass to `TimeSeriesDataset`

**Checkpoint**: Training always uses daily data; training log confirms 1-day interval and bar count; features list is configurable

---

## Phase 4: User Story 2 – Chart Timeframe Switching UI (Priority: P1)

**Goal**: Allow the user to switch chart timeframe between 1 Day, 1 Week, and 1 Month; chart re-fetches and re-renders on change

**Independent Test**: Select a stock, switch timeframe via dropdown, verify chart updates with the correct number of bars per timeframe

### Implementation for User Story 2

- [x] T013 [US2] Add `QComboBox` for timeframe selection (items: "1 Day", "1 Week", "1 Month" with data "1d", "1wk", "1mo") to `_init_ui()` in `src/app/ui/chart_panel.py`
- [x] T014 [US2] Add `self._current_symbol: Optional[str]` and `self._current_interval: str` instance variables to `ChartPanel.__init__()` in `src/app/ui/chart_panel.py`
- [x] T015 [US2] Add `_on_timeframe_changed()` slot in `src/app/ui/chart_panel.py` that re-fetches data via `PriceService().get_series(symbol, interval=interval)` and calls `load_series()`
- [x] T016 [US2] Create `set_symbol(symbol: str)` method in `src/app/ui/chart_panel.py` to store the current symbol (called by prediction_tab)
- [x] T017 [US2] Update `_on_stock_selected()` in `src/app/ui/prediction_tab.py` to call `self.chart_panel.set_symbol(symbol)` and pass `interval` from `chart_panel.get_interval()` to `price_service.get_series()`
- [x] T018 [US2] Add `get_interval() -> str` method to `ChartPanel` in `src/app/ui/chart_panel.py` returning current combo box data value

**Checkpoint**: Chart panel has a working timeframe dropdown; switching timeframes re-fetches and re-renders the chart

---

## Phase 5: User Story 3 – TradingView Provider + Launcher Dialog (Priority: P2)

**Goal**: Create a TradingView-based data provider using `tradingview-ta` and a launcher dialog so the user chooses between YFinance and TradingView before the app opens

**Independent Test**: Launch app, choose TradingView, select an EGX stock (e.g., COMI), verify chart loads with TradingView data

### Implementation for User Story 3

- [x] T019 [P] [US3] Create `src/data/providers/tradingview_provider.py` implementing `BaseProvider` with `TA_Handler(symbol, screener="egypt", exchange="EGX", interval=...)` — map interval strings to `tradingview_ta.Interval` constants, fetch indicator/price data, convert to `PriceSeries`
- [x] T020 [P] [US3] Create interval mapping dict in `src/data/providers/tradingview_provider.py`: map `"1m"` → `Interval.INTERVAL_1_MINUTE`, `"5m"` → `Interval.INTERVAL_5_MINUTES`, `"15m"` → `Interval.INTERVAL_15_MINUTES`, `"1h"` → `Interval.INTERVAL_1_HOUR`, `"1d"` → `Interval.INTERVAL_1_DAY`, `"1wk"` → `Interval.INTERVAL_1_WEEK`, `"1mo"` → `Interval.INTERVAL_1_MONTH`
- [x] T021 [P] [US3] Create `src/app/ui/launcher_dialog.py` with `QDialog` containing radio buttons "YFinance (Historical Data)" and "TradingView (Real-Time Analysis)", an OK button, and a `get_provider_choice() -> str` method returning `"yfinance"` or `"tradingview"`
- [x] T022 [US3] Update `_initialize_providers()` in `src/data/providers/registry.py` to accept optional `provider_mode: str` parameter and register `TradingViewProvider` when mode is `"tradingview"`
- [x] T023 [US3] Update `get_registry()` / `get_provider_registry()` in `src/data/providers/registry.py` to accept and forward `provider_mode` parameter
- [x] T024 [US3] Update `main()` in `src/app/main.py` to show `LauncherDialog` before creating `QMainWindow`, pass chosen provider mode to `get_provider_registry(provider_mode)`
- [x] T025 [US3] Add TradingView-specific timeframe options to `ChartPanel` combo when provider mode is `"tradingview"` (add "1 Min", "5 Min", "15 Min", "1 Hour" options) in `src/app/ui/chart_panel.py`
- [x] T026 [US3] Handle TradingView API errors gracefully in `src/data/providers/tradingview_provider.py` — catch `Exception`, log warning, return `None`

**Checkpoint**: Launcher dialog appears on startup; choosing TradingView loads data from TradingView TA; choosing YFinance uses existing flow

---

## Phase 6: User Story 4 – AI Model Improvements (Priority: P2)

**Goal**: Improve prediction accuracy by expanding input features to OHLCV, adding an attention mechanism to the LSTM, and using a learning rate scheduler during training

**Independent Test**: Train a model for any stock; verify training log shows multi-feature input (input_size=5), attention layer present, LR scheduler reducing LR on plateau; compare val loss to previous single-feature model

### AI Improvement Plan

The current model has these limitations:
1. **Single feature**: Uses only `close` price — misses OHLCV patterns
2. **No attention**: Uses only the last LSTM hidden state — loses information from earlier timesteps
3. **Fixed learning rate**: No adaptive LR — training may plateau or diverge
4. **No gradient clipping**: Risk of exploding gradients with deeper/wider models

### Implementation for User Story 4

- [x] T027 [P] [US4] Update default features in `TimeSeriesDataset.__init__()` in `src/ml/dataset.py` from `["close"]` to `["close", "open", "high", "low", "volume"]`
- [x] T028 [P] [US4] Add `Attention` module class to `src/ml/models/lstm_regressor.py` — learnable query vector, computing attention weights over all LSTM hidden states via scaled dot-product, returning weighted context vector
- [x] T029 [US4] Integrate attention module into `LSTMRegressor.forward()` in `src/ml/models/lstm_regressor.py` — replace `last_output = lstm_out[:, -1, :]` with attention-weighted output; add `use_attention: bool = True` constructor parameter for backward compatibility
- [x] T030 [US4] Update `get_config()` and `create_model()` in `src/ml/models/lstm_regressor.py` to include `use_attention` parameter
- [x] T031 [US4] Add `torch.optim.lr_scheduler.ReduceLROnPlateau` to training loop in `src/ml/train.py` — initialize after optimizer with `patience=5, factor=0.5`, step after each validation epoch, log LR changes
- [x] T032 [US4] Add gradient clipping (`torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)`) before `optimizer.step()` in `src/ml/train.py` to stabilize training
- [x] T033 [US4] Store `features` list in `ModelArtifact.hyperparams` when saving model in `src/ml/train.py` so inference can reconstruct the correct dataset
- [x] T034 [US4] Log model architecture summary (input_size, hidden_size, num_layers, use_attention, LR scheduler params) at training start in `src/ml/train.py`

**Checkpoint**: Models train with 5 OHLCV features, attention mechanism, LR scheduling, and gradient clipping; val loss should improve vs single-feature baseline

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, validation, and documentation

- [x] T035 [P] Update `src/app/ui/training_tab.py` log display to show data interval confirmation ("Training on 1d interval, N bars from YYYY-MM-DD to YYYY-MM-DD")
- [x] T036 [P] Update `specs/001-egx-price-prediction/quickstart.md` to document new features: timeframe switching, TradingView provider, launcher dialog, improved ML model
- [x] T037 Run full app validation: launch → launcher dialog → select provider → prediction tab → select stock → switch timeframes → train model → predict → verify all features work end-to-end
- [x] T038 Verify backward compatibility: existing saved models (single-feature, no attention) still load and run inference correctly — fallback to `features=["close"]` and `use_attention=False` if not in `hyperparams`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion
- **Phase 3 (US1 – Training Data)**: Depends on Phase 1 (interval chain must be complete)
- **Phase 4 (US2 – Chart UI)**: Depends on Phase 1 (interval chain must be complete)
- **Phase 5 (US3 – TradingView)**: Depends on Phase 2 (`tradingview-ta` must be installed)
- **Phase 6 (US4 – ML Improvements)**: Independent of Phases 3–5; only needs existing codebase
- **Phase 7 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1 (Training Timeframe)**: Depends on Phase 1 interval plumbing — No dependency on other stories
- **US2 (Chart Timeframe UI)**: Depends on Phase 1 interval plumbing — No dependency on other stories
- **US3 (TradingView Provider)**: Independent of US1/US2 but benefits from interval plumbing in Phase 1
- **US4 (ML Improvements)**: Fully independent — can start in parallel with US1/US2/US3

### Within Each User Story

- Provider/data changes before UI changes
- Configuration before training loop changes
- Training changes before inference changes
- Core implementation before integration

### Parallel Opportunities

- **Phase 1**: T001–T005 are sequential edits to the same call chain but can be done rapidly
- **Phase 3**: T009 (config.py) can run in parallel with T010 (train.py prep)
- **Phase 4**: T013–T016 all edit `chart_panel.py` — sequential within file, but T017 (prediction_tab.py) is independent
- **Phase 5**: T019+T020 (tradingview_provider.py) and T021 (launcher_dialog.py) are new files — fully parallel
- **Phase 6**: T027 (dataset.py) and T028 (lstm_regressor.py) are different files — fully parallel

---

## Parallel Example: User Story 4 (ML Improvements)

```text
# Launch independent model changes in parallel:
Task T027: "Update default features in src/ml/dataset.py"          ←  parallel
Task T028: "Add Attention module to src/ml/models/lstm_regressor.py" ←  parallel

# Then sequential integration (depends on T028):
Task T029: "Integrate attention into LSTMRegressor forward pass"
Task T030: "Update get_config() and create_model()"

# Then training loop changes (depends on T010 from US1):
Task T031: "Add LR scheduler to training loop"
Task T032: "Add gradient clipping"
Task T033: "Store features in ModelArtifact hyperparams"
Task T034: "Log model architecture summary"
```

## Parallel Example: User Story 3 (TradingView)

```text
# Launch new file creation in parallel:
Task T019: "Create tradingview_provider.py"   ←  parallel (new file)
Task T021: "Create launcher_dialog.py"        ←  parallel (new file)

# Then integration (depends on T019, T021):
Task T022: "Update registry to accept provider_mode"
Task T023: "Update get_registry() to forward provider_mode"
Task T024: "Update main.py to show launcher dialog"
Task T025: "Add TradingView timeframe options to chart"
Task T026: "Handle TradingView errors gracefully"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Interval plumbing through provider chain
2. Complete Phase 3: Training explicitly uses 1-day data with multi-feature config
3. Complete Phase 4: Chart has timeframe dropdown
4. **STOP and VALIDATE**: Verify daily training + chart switching works
5. Proceed to US3 (TradingView) and US4 (ML improvements)

### Incremental Delivery

1. Phase 1 (Setup) → Interval chain ready
2. US1 (Training Data) → Training confirmed on daily data → Validate
3. US2 (Chart UI) → Timeframe switching works → Validate
4. US3 (TradingView) → Launcher dialog + TradingView provider → Validate
5. US4 (ML Improvements) → Better models with attention + OHLCV features → Validate
6. Phase 7 (Polish) → Full integration validated

### Suggested MVP Scope

- **US1 + US2** (Phases 1, 3, 4): Timeframe-aware data fetching + chart switching
- These are the highest priority and provide immediate user-visible value
- US3 and US4 can be delivered as incremental improvements

---

## Notes

- All 38 tasks (T001–T038) completed successfully
- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- T001–T005: Interval parameter plumbed through entire provider chain
- T019–T026: TradingView provider + launcher dialog fully integrated
- T027–T034: LSTM upgraded with 5-feature OHLCV input, attention mechanism, LR scheduler, gradient clipping
- T038: Backward compatibility verified — old single-feature models fallback to `features=["close"]`
- All imports and logic verified via automated test
