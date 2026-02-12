# Tasks: Investment Assistant (Strategy Engine + Journal)

**Input**: Design documents from `specs/001-investment-assistant/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), plus `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] T### [P?] [US?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US#]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes a concrete file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new modules and test scaffolding that the rest of the work builds on.

- [ ] T001 Create `src/services/strategy_engine.py` with a `StrategyEngine` skeleton (public `compute_recommendation()` stub)
- [ ] T002 Create `src/services/portfolio_tracker.py` with a `PortfolioTracker` skeleton (public `log_entry()` / `log_exit()` stubs)
- [ ] T003 [P] Create `src/services/trade_journal_store.py` with a `TradeJournalStore` skeleton (SQLite open/init stubs)
- [ ] T004 [P] Create unit test scaffolding file `tests/unit/test_strategy_engine.py`
- [ ] T005 [P] Create unit test scaffolding file `tests/unit/test_trade_journal_store.py`
- [ ] T006 [P] Create unit test scaffolding file `tests/unit/test_portfolio_tracker.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schemas + config + quant API shims needed by all user stories.

**Checkpoint**: Foundation ready → user story implementation can begin.

- [ ] T007 Add assistant recommendation schemas in `src/core/schemas.py` (StrategyAction, EvidenceSource/Direction, EvidenceSignal, StrategyRecommendation)
- [ ] T008 Add local journaling schemas in `src/core/schemas.py` (TradeLog/TradeJournalEntry with Recommendation ID + PerformanceSummary)
- [ ] T009 Add `Config.TRADE_JOURNAL_DB_PATH` in `src/core/config.py` pointing to `data/metadata/trade_journal.sqlite3`
- [ ] T010 Add `calculate_var()` alias that calls existing `compute_var()` in `src/core/quant.py`
- [ ] T011 Add `calculate_hurst()` alias that calls existing `compute_hurst()` in `src/core/quant.py`
- [ ] T012 [P] Add unit test coverage for the new quant aliases in `tests/unit/test_strategy_engine.py` (or split into a new `tests/unit/test_quant_helpers.py`)

---

## Phase 3: User Story 1 — Risk-First Action & Stop-Loss (Priority: P1) 🎯 MVP

**Goal**: Produce a mathematically defined, risk-first `StrategyRecommendation` with Action + Stop-Loss + Conviction for a selected symbol.

**Independent Test**: Running `pytest -k strategy_engine` and/or a manual run in the UI shows Action + Stop-Loss (or explicit N/A for HOLD) and Conviction for a chosen EGX symbol.

### Definition of Done (P1)

- Recommendation always includes Conviction Score (0–100)
- BUY/SELL always include Stop-Loss (price + implied % distance); HOLD shows explicit N/A fields
- Explicit weights are used and are surfaced in the evidence output
- Risk-First policy defaults to HOLD on missing/conflicting inputs
- Unit tests validate thresholds, HOLD behavior, and stop-loss presence

### Implementation

- [ ] T013 [US1] Implement signal extraction from `ForecastResult` + `PriceSeries` in `src/services/strategy_engine.py`
- [ ] T014 [US1] Implement technical indicator scoring (RSI/MACD/EMA) in `src/services/strategy_engine.py`
- [ ] T015 [US1] Implement regime extraction (ADF/Hurst) and regime label in `src/services/strategy_engine.py`
- [ ] T016 [US1] Implement blended score + conviction calculation (incl. disagreement penalty) in `src/services/strategy_engine.py`
- [ ] T017 [US1] Implement VaR-based risk distance + Entry Zone + Stop-Loss formulas in `src/services/strategy_engine.py`
- [ ] T018 [US1] Implement regime-consistent Target Exit formulas in `src/services/strategy_engine.py`
- [ ] T019 [US1] Build EvidenceSignal lists (bullish/bearish/neutral) with disclosed weights in `src/services/strategy_engine.py`
- [ ] T020 [US1] Generate a human-readable `logic_summary` string in `src/services/strategy_engine.py`

### Tests

- [ ] T021 [P] [US1] Add unit tests for Risk-First HOLD on missing inputs in `tests/unit/test_strategy_engine.py`
- [ ] T022 [P] [US1] Add unit tests that BUY/SELL always include stop-loss and HOLD uses explicit N/A in `tests/unit/test_strategy_engine.py`
- [ ] T023 [P] [US1] Add unit tests for conviction reduction on disagreement in `tests/unit/test_strategy_engine.py`
- [ ] T024 [P] [US1] Add unit tests for action thresholds (BUY/SELL/HOLD) in `tests/unit/test_strategy_engine.py`

**Checkpoint**: StrategyEngine can compute a complete recommendation for one symbol and is covered by unit tests.

---

## Phase 4: User Story 2 — Understand the “Why” (Priority: P2)

**Goal**: Refactor the Prediction tab into a Strategy Dashboard that shows a recommendation banner and an evidence breakdown, clearly separated from raw forecast output.

**Independent Test**: Launch app → run Predict → Strategy Dashboard shows Assistant Recommendation (banner + evidence) and Raw Forecast as separate labeled sections.

### Implementation

- [ ] T025 [US2] Rename Prediction tab label to “Strategy” in `src/app/main.py`
- [ ] T026 [US2] Refactor layout into “Assistant Recommendation” + “Raw Forecast” groups in `src/app/ui/prediction_tab.py`
- [ ] T027 [US2] Implement color-coded Recommendation Banner UI in `src/app/ui/prediction_tab.py`
- [ ] T028 [US2] Implement Evidence Panel UI (bullish vs bearish vs neutral lists) in `src/app/ui/prediction_tab.py`
- [ ] T029 [US2] After prediction completes, call `StrategyEngine` and render the recommendation in `src/app/ui/prediction_tab.py`
- [ ] T030 [US2] Ensure Raw Forecast output remains visible and clearly labeled (predicted close, baselines, staleness, VaR/validation) in `src/app/ui/prediction_tab.py`

**Checkpoint**: US2 delivers the “Why” without requiring journaling.

---

## Phase 5: User Story 3 — Local Trade Journal & Performance Review (Priority: P2)

**Goal**: Log simulated entries/exits locally and show a minimal Performance Review summary.

**Independent Test**: Execute Entry → restart app → open Performance Review → entry still present; Log Exit updates metrics.

### Persistence (Store + Tracker)

- [ ] T031 [US3] Implement SQLite schema creation and migrations-by-version (minimal) in `src/services/trade_journal_store.py`
- [ ] T032 [US3] Implement append-only journal entry writes (entry/exit) in `src/services/trade_journal_store.py`
- [ ] T033 [US3] Implement queries for open positions and closed trades in `src/services/trade_journal_store.py`
- [ ] T034 [US3] Implement PerformanceSummary SQL computations (count, win rate, avg return, stop-loss hit rate) in `src/services/trade_journal_store.py`
- [ ] T035 [US3] Implement `PortfolioTracker` orchestration over the store in `src/services/portfolio_tracker.py`

### UI Integration

- [ ] T036 [US3] Add Execute Entry / Log Exit buttons and callbacks into `src/app/ui/prediction_tab.py`
- [ ] T037 [P] [US3] Create Performance Review UI in `src/app/ui/performance_tab.py`
- [ ] T038 [US3] Wire Performance Review tab into the main window in `src/app/main.py`

### Tests

- [ ] T039 [P] [US3] Add test that journal entries persist across store re-open (simulated restart) in `tests/unit/test_trade_journal_store.py`
- [ ] T040 [P] [US3] Add tests for open/close position flow in `tests/unit/test_portfolio_tracker.py`
- [ ] T041 [P] [US3] Add tests for PerformanceSummary calculations (win rate, avg return, stop-loss hit rate) in `tests/unit/test_portfolio_tracker.py`

**Checkpoint**: US3 provides durable journaling + performance review.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final pass to keep docs and UX consistent with the constitution.

- [ ] T042 [P] Update user-facing docs to mention Strategy Dashboard + journal DB location in `README.md`
- [ ] T043 [P] Validate and adjust walkthrough steps for this feature in `specs/001-investment-assistant/quickstart.md`
- [ ] T044 [P] Run ruff/pytest and fix any issues introduced by this feature in `ruff.toml` (config only, if needed) and `tests/`

---

## Dependencies & Execution Order

### Dependency Graph (User Story Completion Order)

- Phase 1 (Setup) → Phase 2 (Foundational) → US1 (MVP)
- After Foundational:
  - US2 depends on US1’s `StrategyEngine` output contract
  - US3’s persistence layer can start after Foundational, but UI wiring for journal buttons depends on US2’s Strategy Dashboard refactor

### Parallel Opportunities (by story)

**US1 (StrategyEngine)**
- In parallel: implement scoring/targets in `src/services/strategy_engine.py` and write unit tests in `tests/unit/test_strategy_engine.py`.

**US2 (UI “Why”)**
- In parallel: banner UI and evidence panel UI changes in `src/app/ui/prediction_tab.py` can be split if kept in separate helper methods.

**US3 (Journal + Performance)**
- In parallel: SQLite store implementation in `src/services/trade_journal_store.py` and Performance Review UI in `src/app/ui/performance_tab.py`.

---

## Parallel Execution Examples

### User Story 1

- Task: "T016 Implement blended score + conviction" in `src/services/strategy_engine.py`
- Task: "T022 Add unit tests that BUY/SELL always include stop-loss" in `tests/unit/test_strategy_engine.py`

### User Story 2

- Task: "T027 Implement Recommendation Banner UI" in `src/app/ui/prediction_tab.py`
- Task: "T028 Implement Evidence Panel UI" in `src/app/ui/prediction_tab.py`

### User Story 3

- Task: "T032 Implement append-only journal writes" in `src/services/trade_journal_store.py`
- Task: "T037 Create Performance Review UI" in `src/app/ui/performance_tab.py`
