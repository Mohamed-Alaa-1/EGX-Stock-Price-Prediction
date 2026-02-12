# Feature Specification: Investment Assistant Strategy Recommendations

**Feature Branch**: `001-investment-assistant`  
**Created**: 2026-02-12  
**Status**: Draft  
**Input**: User description: "Transform the app from a raw price predictor into an Investment Assistant that outputs Buy/Sell/Hold recommendations with entry/exit targets, stop-losses, conviction, explanations, local trade journaling, and performance review."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Risk-First Action & Stop-Loss (Priority: P1)

As a trader, I want to see a clear **Action** (Buy/Sell/Hold) and an explicit **Stop-Loss** for a selected stock so I can manage my risk before entering a trade.

**Why this priority**: This is the minimum viable value of an “assistant” recommendation—an actionable decision with capital-preserving risk controls.

**Independent Test**: Can be fully tested by selecting a symbol and verifying a complete recommendation is produced (or safely defaults to HOLD) including stop-loss handling.

**Acceptance Scenarios**:

1. **Given** a symbol with sufficient historical data and a current price, **When** I open the Strategy Dashboard, **Then** I see a Strategy Recommendation with Action, Entry Zone, Target Exit, Stop-Loss (or explicit N/A when HOLD), and Conviction Score.
2. **Given** the system cannot compute one or more required inputs, **When** I open the Strategy Dashboard, **Then** the system defaults to HOLD and clearly indicates which inputs are missing while still displaying the best-available partial evidence.
3. **Given** evidence sources are strongly aligned bullish and the blended score is at least +0.20, **When** the recommendation is computed, **Then** the Action is BUY and Conviction Score is at least 30.
4. **Given** evidence sources disagree such that the alignment factor is 0.50 or lower, **When** the recommendation is computed, **Then** the Conviction Score is reduced accordingly and the Action is HOLD unless the blended score magnitude is at least 0.55.

---

### User Story 2 - Understand the “Why” (Priority: P2)

As a trader, I want to see a concise **Logic Summary** and supporting evidence (bullish vs bearish signals) behind a recommendation so I can decide whether I trust the signal.

**Why this priority**: Recommendations without transparency reduce trust and increase misuse; evidence makes the assistant interpretable.

**Independent Test**: Can be fully tested by opening the Strategy Dashboard and verifying the explanation and evidence are present and consistent with the computed action.

**Acceptance Scenarios**:

1. **Given** a computed recommendation, **When** I view the Evidence Panel, **Then** I can see which signals are bullish vs bearish and how they contributed to the final recommendation.
2. **Given** a HOLD recommendation due to uncertainty, **When** I view the Logic Summary, **Then** it explicitly states that uncertainty/disagreement triggered HOLD and identifies the major conflicting signals.

---

### User Story 3 - Local Trade Journal & Performance Review (Priority: P2)

As a trader, I want to log my simulated trades locally based on the assistant’s recommendations so I can track my performance against the assistant’s advice over time.

**Why this priority**: Logging decisions is necessary to learn whether the assistant is helping and to compare outcomes over time.

**Independent Test**: Can be fully tested by logging an entry and exit locally and verifying the Performance Review updates using those journal entries.

**Acceptance Scenarios**:

1. **Given** a recommendation is shown for a symbol, **When** I click Execute Entry, **Then** a local trade journal entry is created containing the recommendation context (action, conviction, entry zone, target, stop-loss) and the simulated entry price/time.
2. **Given** I have an open simulated position for a symbol, **When** I click Log Exit, **Then** the position is closed in the local journal with exit price/time and the performance summary updates to reflect the closed trade outcome.

---

### Edge Cases

- Missing one of the four signal sources (ML, technicals, risk, regime) for a symbol.
- Highly conflicting signals (e.g., ML bullish while technicals bearish).
- Extremely high risk (VaR implies an unacceptably wide stop-loss or poor reward-to-risk).
- Hurst/regime classification is inconclusive or unstable between runs.
- User presses Execute Entry multiple times or presses Log Exit with no open position.
- Price data contains gaps/outliers that materially distort indicators.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a Strategy Recommendation for a selected symbol that includes: Action (Buy/Sell/Hold), Entry Zone (price range or explicit N/A), Target Exit (price or explicit N/A), Stop-Loss (price or explicit N/A), Conviction Score (0–100), and a Logic Summary.
- **FR-002**: System MUST ensemble-combine four evidence sources to determine direction and conviction: ML forecast signal, technical indicator signal (RSI, MACD, EMA), quantitative risk signal (VaR), and statistical regime signal (Hurst exponent).
- **FR-003**: System MUST expose the contribution of each evidence source in the Evidence Panel as bullish, bearish, or neutral, including the relative weight used for blending.
- **FR-004**: System MUST apply a Risk-First policy: if evidence is insufficient or materially conflicting, the default Action MUST be HOLD.
- **FR-005**: System MUST compute Stop-Loss using Value-at-Risk as the primary risk anchor and MUST not output BUY/SELL recommendations without a Stop-Loss.
- **FR-006**: System MUST adapt target/entry guidance using the statistical regime: recommendations MUST indicate whether the logic is trend-following or mean-reverting, and targets MUST be consistent with that regime.
- **FR-007**: System MUST present a Strategy Dashboard that replaces the prior prediction-focused view and includes: (a) a Recommendation Banner color-coded by Action, (b) an Evidence Panel, and (c) the decision buttons Execute Entry and Log Exit.
- **FR-008**: System MUST clearly separate raw ML forecast outputs from the assistant-processed recommendation within the Strategy Dashboard.
- **FR-009**: System MUST provide a Local Trade Journal that stores simulated decisions on the user’s device and persists across application restarts.
- **FR-010**: System MUST allow users to create an entry log from the current recommendation context via Execute Entry and close an open position via Log Exit.
- **FR-011**: System MUST provide a Performance Review that summarizes outcomes over time using journaled trades, including at minimum: number of trades, win rate, average return per trade, and stop-loss hit rate.

#### Recommendation Logic (normative behavior)

- **FR-012**: System MUST compute a directional score for each evidence source on a consistent scale from -1.0 (bearish) to +1.0 (bullish), where 0.0 is neutral, and blend them using explicit weights that sum to 1.0.
- **FR-013**: Default evidence weights MUST be: ML Forecast 0.35, Technical Indicators 0.30, Statistical Regime 0.20, Quantitative Risk 0.15.
- **FR-014**: System MUST compute a blended score as the weighted sum of the four evidence scores.
- **FR-015**: Conviction Score MUST be computed on a stable 0–100 scale and MUST be reduced on disagreement. The default conviction calculation MUST be:
  - Let $A$ be the alignment factor = (number of evidence sources whose score sign matches the blended score sign) ÷ 4.
  - Conviction = round(100 × min(1.0, |blended score|) × A).
- **FR-016**: Action selection MUST follow this threshold rule:
  - BUY when blended score ≥ +0.20 and Conviction ≥ 30.
  - SELL when blended score ≤ -0.20 and Conviction ≥ 30.
  - Otherwise HOLD.
- **FR-017**: For BUY/SELL recommendations, system MUST compute a “risk distance” from the 1-day 95% Value-at-Risk (VaR) expressed as a percentage of current price, and MUST cap it into the range 0.5%–10% for stability.
- **FR-018**: Entry Zone and Target Exit MUST be consistent with Action using the computed risk distance:
  - BUY Entry Zone = [current price × (1 - risk distance), current price × (1 + 0.25 × risk distance)].
  - SELL Entry Zone = [current price × (1 - 0.25 × risk distance), current price × (1 + risk distance)].
  - HOLD shows Entry Zone, Target Exit, and Stop-Loss as explicit N/A.
- **FR-019**: Stop-Loss MUST be computed from VaR and MUST be displayed as a concrete price for BUY/SELL:
  - BUY Stop-Loss = (lower bound of BUY Entry Zone) × (1 - risk distance).
  - SELL Stop-Loss = (upper bound of SELL Entry Zone) × (1 + risk distance).
- **FR-020**: Target Exit MUST be regime-consistent:
  - If trend-following:
    - BUY Target Exit = min(ML-forecast price, current price × (1 + 4 × risk distance)).
    - SELL Target Exit = max(ML-forecast price, current price × (1 - 4 × risk distance)).
  - If mean-reverting:
    - Define the mean anchor as EMA(50).
    - BUY Target Exit = if EMA(50) > current price then EMA(50) else current price × (1 + 1.5 × risk distance).
    - SELL Target Exit = if EMA(50) < current price then EMA(50) else current price × (1 - 1.5 × risk distance).
- **FR-021**: Logic Summary MUST be human-readable and must mention, at minimum: the Action, Conviction Score, the regime classification (trend vs mean-reversion), and the top 2–4 contributing bullish/bearish signals.

### Constitution-Driven Requirements (fill when applicable)

- **INV-001**: System MUST implement Risk-First recommendation policy (default HOLD on uncertainty)
- **INV-002**: Every recommendation MUST include Stop-Loss and Conviction Score
- **INV-003**: System MUST compute an explicit blended score (ML + technical with disclosed weights)
- **INV-004**: UI MUST clearly label and separate raw model outputs vs Assistant recommendation

### Key Entities *(include if feature involves data)*

- **StrategyRecommendation**: The assistant’s recommendation for a symbol at a point in time (Action, Entry Zone, Target Exit, Stop-Loss, Conviction Score, regime label, Logic Summary, and evidence breakdown).
- **EvidenceSignal**: One normalized contribution to the recommendation (source: ML/Technical/Risk/Regime, direction: bullish/bearish/neutral, weight, and a short explanation string).
- **TradeJournalEntry**: A local record of a user decision (timestamp, symbol, action taken, recommendation snapshot at decision time, and price).
- **SimulatedPosition**: An open or closed simulated trade derived from journal entries (entry details, exit details, and outcome metrics).
- **PerformanceSummary**: Aggregated metrics over a selected time range computed from simulated positions.

### Assumptions

- This feature operates without user authentication; journaling is local to the device.
- The system evaluates “recommendation accuracy” primarily from journaled simulated trades (not from all viewed recommendations).
- When the system cannot compute a required value, it prefers HOLD rather than emitting partially-formed BUY/SELL guidance.
- Recommendations depend on having a current price and sufficient recent price history to compute technical indicators and VaR; ML forecast input is used when available but MUST not be the only basis for a BUY/SELL decision.

### Scope Boundaries

- No real-money brokerage integration; buttons log simulated decisions only.
- No user accounts or cloud sync; the journal is local to the device.
- UI scope is limited to: Strategy Dashboard (Recommendation Banner, Evidence Panel, Execute Entry, Log Exit) and a minimal Performance Review view for journaled trades.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of displayed recommendations include Action and Conviction Score; BUY/SELL recommendations always include a concrete Stop-Loss value.
- **SC-002**: In a usability check, at least 90% of users can correctly answer “What is the Action and Stop-Loss?” for a shown recommendation within 30 seconds.
- **SC-003**: Users can create a simulated entry and exit in the Local Trade Journal in under 60 seconds and see those actions reflected in the Performance Review.
- **SC-004**: Performance Review correctly computes (and visibly updates) trade count, win rate, average return per trade, and stop-loss hit rate based on the journaled trades.
