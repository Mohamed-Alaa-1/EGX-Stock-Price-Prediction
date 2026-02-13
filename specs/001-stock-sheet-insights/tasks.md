# Tasks: Stock Sheet Investment Insights (Batch Train + Analyze)

**Input**: Design documents from `/specs/001-stock-sheet-insights/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Every task includes exact file path(s) in the description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal repo setup and wiring points for the new feature

- [X] T001 Confirm current tabs and insertion point for new Insights tab in src/app/main.py
- [X] T002 [P] Create initial UI module stub in src/app/ui/stock_sheet_insights_tab.py
- [X] T003 [P] Create initial service module stub in src/services/stock_sheet_insights_service.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas and batch-run primitives that all stories depend on

- [X] T004 Add batch insight schemas in src/core/schemas.py (InsightStatus enum; SheetInsightsRunRequest; StockInsight; InsightBatchRun with summary counts)
- [X] T005 Add a stock-sheet read helper that returns normalized, deduplicated symbols in src/services/stock_universe_manager.py
- [X] T006 Define a per-symbol error/status convention (OK/HOLD_FALLBACK/ERROR + user-readable reason) in src/services/stock_sheet_insights_service.py

**Checkpoint**: Foundation ready (schemas + stock list access + error/status conventions)

---

## Phase 3: User Story 1 - View Insights For All Sheet Stocks (Priority: P1) 🎯 MVP

**Goal**: Provide one view that shows Buy/Sell/Hold insights for every stock in the user’s stock sheet, including a single batch button to compute results.

**Independent Test**: Add 3+ symbols in the stock sheet, open the Stock Sheet Insights tab, click “Train + Analyze Sheet (Force Refresh)”, and verify one row per symbol renders with Action, Conviction, Stop-Loss (or N/A), Target (or N/A), and a short reason when HOLD fallback occurs.

### Implementation

- [X] T007 [US1] Implement batch run orchestration (force-refresh fetch, optional train, compute recommendation, per-stock isolation) in src/services/stock_sheet_insights_service.py
- [X] T008 [US1] Implement force-refresh retrieval using PriceService.get_series(symbol, use_cache=False) and still allow saving fresh results to cache in src/services/stock_sheet_insights_service.py
- [X] T009 [US1] Implement per-stock isolation: wrap each symbol in try/except and always emit a StockInsight result (including HOLD fallback on errors) in src/services/stock_sheet_insights_service.py
- [X] T010 [US1] Build the Stock Sheet Insights tab UI with: buttons, progress label, and a QTableWidget with columns (Symbol, Action, Conviction, Stop-Loss, Target, Status, Reason, As-Of) in src/app/ui/stock_sheet_insights_tab.py
- [X] T011 [US1] Run "Train + Analyze Sheet (Force Refresh)" via a QThread worker with progress signals so the UI stays responsive in src/app/ui/stock_sheet_insights_tab.py
- [X] T012 [US1] Render summary row fields with correct N/A rules (HOLD → Stop-Loss/Target show N/A) in src/app/ui/stock_sheet_insights_tab.py
- [X] T013 [US1] Add empty-state UX when stock sheet has no symbols in src/app/ui/stock_sheet_insights_tab.py
- [X] T014 [US1] Add the new tab to the application (tab label + widget instantiation) in src/app/main.py

**Checkpoint**: US1 complete when the user can run a batch analysis and see one stable row per sheet symbol without UI freezes.

---

## Phase 4: User Story 2 - Drill Into One Stock (Priority: P2)

**Goal**: Let the user select a stock from the list and see a detailed view with evidence and clear separation of raw outputs vs assistant recommendation.

**Independent Test**: After running a batch, select any row and verify the tab shows a details area that includes (1) assistant recommendation summary, (2) evidence breakdown, and (3) a separate raw outputs section (when available).

### Implementation

- [X] T015 [US2] Add row-selection behavior and a details panel region (read-only) in src/app/ui/stock_sheet_insights_tab.py
- [X] T016 [US2] Show an Evidence section (bullish/bearish/neutral lists with weights and short summaries) in src/app/ui/stock_sheet_insights_tab.py
- [X] T017 [US2] Show separate "Assistant Recommendation" vs "Raw Outputs" sections (raw forecast/baseline/risk when present) in src/app/ui/stock_sheet_insights_tab.py

**Checkpoint**: US2 complete when drill-down is understandable and meets constitution UI separation expectations.

---

## Phase 5: User Story 3 - Refresh All Insights (Priority: P3)

**Goal**: Provide refresh flows and resilience rules: force-refresh + optional training, per-stock failures never interrupt the full run, and cached fallback is labeled.

**Independent Test**: Run a batch, then re-run using Refresh/Train+Analyze, simulate one failing symbol (invalid ticker or provider failure), and verify other symbols still update, and the failing symbol shows HOLD fallback or ERROR with a reason.

### Implementation

- [X] T018 [US3] Add a fast "Refresh Insights" action (no training) in src/app/ui/stock_sheet_insights_tab.py
- [X] T019 [US3] If fresh retrieval fails, attempt per-symbol cache fallback and set used_cache_fallback=true (or produce HOLD fallback with an explicit reason) in src/services/stock_sheet_insights_service.py
- [X] T020 [US3] Ensure each batch run has a single computed_at + batch_id and the UI clears/replaces prior rows at run start (no mixed-run rows) in src/app/ui/stock_sheet_insights_tab.py
- [X] T021 [US3] Add a per-run summary (total/ok/hold_fallback/error) displayed in the UI in src/app/ui/stock_sheet_insights_tab.py

**Checkpoint**: US3 complete when batch refresh is robust, clearly labeled, and does not abort on partial failures.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass across stories

- [X] T022 [P] Add consistent logging lines (start/end, per-symbol status, elapsed time) in src/services/stock_sheet_insights_service.py
- [X] T023 [P] Run and verify the user steps in specs/001-stock-sheet-insights/quickstart.md (update if any steps diverge)
- [X] T024 Add basic performance safeguards (e.g., cap max symbols per run or show warning for very large sheets) in src/app/ui/stock_sheet_insights_tab.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → **US1 (Phase 3)** → **US2 (Phase 4)** → **US3 (Phase 5)** → **Polish (Phase 6)**

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 (schemas + stock list helper)
- **US2 (P2)**: Depends on US1 (needs batch results to drill into)
- **US3 (P3)**: Depends on US1 (refresh is a re-run over the same list)

### Dependency Graph (story-level)

- US1 → US2
- US1 → US3

---

## Parallel Execution Examples

### US1 parallel opportunities

- T010 (UI layout) can proceed in parallel with T007/T008/T009 (service logic) as long as both agree on the `StockInsight` shape from T004.

### US3 parallel opportunities

- T018 (UI refresh button wiring) can proceed in parallel with T019 (service fallback labeling) after US1 exists.

---

## Implementation Strategy

### MVP (ship US1 first)

1. Complete Phase 1 + Phase 2
2. Implement Phase 3 (US1)
3. Validate US1 using the Independent Test for US1

### Incremental Delivery

- Add US2 to improve trust/understanding (drill-down)
- Add US3 to improve workflow quality (refresh + resilience)
- Finish with Phase 6 polish
