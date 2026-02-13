# Feature Specification: Stock Sheet Investment Insights

**Feature Branch**: `001-stock-sheet-insights`  
**Created**: 2026-02-13  
**Status**: Draft  
**Input**: User description: "We are developing a new feature that will allow the user to have investment insight for all the stocks he added to the stocks sheet."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - View Insights For All Sheet Stocks (Priority: P1)

As a user, I want a single view that shows investment insights for every stock I have added to my stocks sheet so I can quickly understand which stocks look attractive, risky, or unclear.

**Why this priority**: This is the core value of the feature: a whole-sheet overview that reduces the need to open each stock individually.

**Independent Test**: Can be fully tested by adding multiple stocks to the sheet, opening the Stock Sheet Insights view, and verifying that one insight row is produced per stock with the required fields and safe fallbacks.

**Acceptance Scenarios**:

1. **Given** the stocks sheet contains at least 3 enabled stocks, **When** I open Stock Sheet Insights, **Then** I see one insight summary row per enabled stock.
2. **Given** at least one stock cannot be evaluated due to missing or invalid data, **When** I open Stock Sheet Insights, **Then** that stock’s row still renders and defaults to HOLD with a clear “why” message.
3. **Given** the stocks sheet is empty (or all stocks are disabled), **When** I open Stock Sheet Insights, **Then** I see an empty state that explains how to add stocks and why no insights are shown.

---

### User Story 2 - Drill Into One Stock (Priority: P2)

As a user, I want to open a detailed insight view for a specific stock from the sheet-wide list so I can understand the reasoning behind the summary and see the evidence behind the recommendation.

**Why this priority**: Users need confidence and context; a summary without a drill-down reduces trust and can lead to misuse.

**Independent Test**: Can be fully tested by selecting any row in Stock Sheet Insights and verifying a detailed view appears that expands the summary into a complete insight with labeled evidence.

**Acceptance Scenarios**:

1. **Given** Stock Sheet Insights shows summary rows, **When** I select a stock row, **Then** I can view the full insight details for that stock.
2. **Given** the assistant produces a recommendation, **When** I view the details, **Then** I can clearly distinguish raw model outputs (if available) from the assistant-processed Buy/Sell/Hold recommendation.

---

### User Story 3 - Refresh All Insights (Priority: P3)

As a user, I want to refresh insights for the entire stocks sheet (optionally forcing fresh retrieval and re-training) so I can re-evaluate my list using the latest available market data.

**Why this priority**: Insights that cannot be refreshed become stale; refresh enables daily/weekly workflow.

**Independent Test**: Can be fully tested by refreshing insights and verifying timestamps update, failures are isolated to specific rows, and partial results remain visible.

**Acceptance Scenarios**:

1. **Given** the stocks sheet contains enabled stocks, **When** I click Refresh Insights, **Then** the system recomputes insights for all enabled stocks and updates each row’s “as of” timestamp.
2. **Given** I use a “Train + Analyze Sheet (Force Refresh)” button, **When** the run starts, **Then** the system attempts to retrieve fresh price data (not from cache by default) and trains/updates analysis per stock without letting failures on one stock interrupt the rest.
3. **Given** one or more stocks fail to retrieve or train during a batch run, **When** the run completes, **Then** I see a per-stock status and reason and still see computed results for all other stocks.

---

### Edge Cases

- Duplicate symbols in the stocks sheet.
- A symbol is present but disabled; it should not appear in the insights list.
- A symbol is invalid, delisted, or has no available price history.
- Data is stale or unavailable at the time insights are generated.
- Fresh retrieval fails (provider down/rate-limited); system falls back safely per-stock without aborting the full run.
- The sheet contains a large number of stocks (performance and usability).
- Mixed market calendars/timezones (e.g., some symbols are not trading today).

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST treat the “stocks sheet” as the user-managed list of stocks (symbols) the user has explicitly added and enabled.
- **FR-002**: System MUST provide a Stock Sheet Insights view that displays insights for every enabled stock in the stocks sheet.
- **FR-003**: For each stock in the sheet, the system MUST produce an Insight Summary containing, at minimum:
  - Stock identifier (symbol and display name when available)
  - Recommendation Action (Buy/Sell/Hold)
  - Conviction Score on a stable 0–100 scale
  - Stop-Loss as a concrete price for Buy/Sell, and explicit N/A for Hold
  - Target Exit as a concrete price for Buy/Sell, and explicit N/A for Hold
  - A short Logic Summary (1–2 sentences)
  - “As of” timestamp indicating the market data time used
- **FR-004**: System MUST apply a Risk-First policy: when required inputs are missing, stale, or materially conflicting, the default Action MUST be HOLD.
- **FR-005**: When the system defaults to HOLD due to missing/invalid inputs, it MUST provide a user-readable reason per affected stock (e.g., “insufficient data,” “data unavailable,” “conflicting signals”).
- **FR-006**: System MUST allow the user to refresh insights for all enabled stocks in the sheet in a single action.
- **FR-006a**: System MUST provide a “Train + Analyze Sheet (Force Refresh)” action that triggers a batch run across all enabled stocks.
- **FR-006b**: During this batch run, the system MUST attempt fresh retrieval of price data for each stock (i.e., do not use cached series by default for that run).
- **FR-006c**: If fresh retrieval fails for a stock, the system SHOULD fall back to cached data for that stock when available, and MUST clearly label that a fallback occurred (or otherwise produce a HOLD fallback with a clear error reason).
- **FR-006d**: A failure to retrieve/train/analyze one stock MUST NOT interrupt the batch analysis for other stocks.
- **FR-006e**: The batch UI MUST show progress and a per-stock status (OK / HOLD_FALLBACK / ERROR) and a user-readable reason when not OK.
- **FR-007**: System MUST allow the user to open a detailed insight view for an individual stock from the insights list.
- **FR-008**: The detailed insight view MUST present an evidence breakdown that is consistent with the summary recommendation and MUST clearly separate raw model outputs (when available) from assistant-processed recommendations.
- **FR-009**: System MUST ensure that an insight batch run is internally consistent: all rows must include a computed-at timestamp and the view must clearly indicate if some rows are from an earlier run (due to partial failures).

#### Recommendation Vocabulary

- **FR-010**: The recommendation action vocabulary MUST support Buy/Sell/Hold. UI may label Buy as “Buy more” to match the user mental model.

### Constitution-Driven Requirements (fill when applicable)

<!--
  If this feature outputs an “Assistant” recommendation (Buy/Sell/Hold), the constitution requires:
  - Risk-First (capital preservation),
  - Stop-Loss included (explicit N/A when HOLD),
  - Conviction Score included (stable scale, lowered on disagreement),
  - Technical signals explicitly weighted against ML predictions,
  - UI clearly separates raw model outputs from Assistant-processed recommendation.
-->

- **INV-001**: System MUST implement Risk-First recommendation policy (default HOLD on uncertainty).
- **INV-002**: Every Buy/Sell recommendation MUST include Stop-Loss and Conviction Score; HOLD MUST explicitly show Stop-Loss as N/A.
- **INV-003**: System MUST compute an explicit blended score combining model-based signals and technical signals using disclosed weights (or an equivalent transparent weighting scheme).
- **INV-004**: The insights UI MUST clearly label and separate raw model outputs vs assistant-processed recommendation.

### Key Entities *(include if feature involves data)*

- **StockSheetEntry**: A stock added by the user (symbol, optional display name, enabled/disabled flag, date added).
- **StockInsight**: The computed insight for one stock at a point in time (Action, Conviction Score, Stop-Loss, Target Exit, Logic Summary, evidence breakdown, as-of timestamp).
- **InsightBatchRun**: A grouping of StockInsight results produced by a single refresh (computed-at timestamp, coverage counts, per-symbol status).
- **InsightStatus**: A per-stock outcome classification (OK, HOLD_FALLBACK, ERROR) with a user-readable reason.

### Assumptions

- The stocks sheet already exists as a user-maintained list and is the source of truth for which stocks should be included.
- This feature provides decision support only; it does not place trades or integrate with brokers.
- Insights are generated on-demand (via explicit refresh) and may be reused until refreshed again.

### Scope Boundaries

- No portfolio weighting, allocation optimization, or “best stock” ranking beyond showing each stock’s Action and Conviction.
- No alerts/notifications; users manually refresh and review.
- No user authentication or cloud sync requirements are introduced by this feature.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: For any displayed sheet, 100% of insight rows show Action and Conviction Score, and all Buy/Sell rows show a concrete Stop-Loss and Target Exit.
- **SC-002**: For a sheet of 50 enabled stocks, users can open Stock Sheet Insights and see all rows rendered (including HOLD fallbacks) within 15 seconds.
- **SC-003**: In a usability check, at least 90% of users can identify (a) which stocks are BUY/SELL/HOLD and (b) the Stop-Loss for a selected BUY/SELL stock within 60 seconds.
- **SC-004**: Refresh Insights completes with a clear per-stock status summary such that users can tell which stocks updated successfully and which fell back to HOLD (or errored) without leaving the insights view.
