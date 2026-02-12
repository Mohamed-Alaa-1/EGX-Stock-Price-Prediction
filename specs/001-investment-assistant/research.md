# Phase 0 Research: Investment Assistant (Strategy Engine + Journal)

**Feature**: [specs/001-investment-assistant/spec.md](spec.md)
**Date**: 2026-02-12

## Decision 1: Recommendation engine is a thin ensemble over existing services

**Decision**: Implement a new service layer `StrategyEngine` that consumes existing domain outputs (price series, forecast result, risk snapshot, and statistical validation) and produces a single `StrategyRecommendation` with evidence breakdown.

**Rationale**:
- The repo already has reliable building blocks: `PredictionService` (forecast + risk companion + baseline), `RiskService` (VaR), `SignalValidationService` (ADF + Hurst), and `core.indicators` (RSI/MACD/EMA).
- A thin orchestration layer keeps the “assistant” explainable and reduces duplication.

**Alternatives considered**:
- Embed recommendation logic directly in the UI (`PredictionTab`): rejected because it would be hard to test and reuse.
- Add a full “strategy backtesting engine” as the first step: rejected; exceeds scope and delays delivering P1 value.

## Decision 2: Use regime-aware weighting but keep the regime direction-neutral

**Decision**: Use ADF + Hurst primarily to classify *regime* (trend vs mean-reversion vs neutral) and to adjust weights/targets, not to add a separate bullish/bearish direction by itself.

**Rationale**:
- Regime is best treated as “how to trade” (trend-follow vs mean-revert), not “which direction”.
- This produces cleaner Evidence Panels: users see direction signals (ML/RSI/MACD/EMA) and see regime as a context label.

**Alternatives considered**:
- Treat regime as a directional signal: rejected because it conflates stationarity/trendiness with direction.

## Decision 3: Ensemble scoring algorithm and conflict handling

**Decision**: Compute four normalized directional signals in [-1, +1] and blend with explicit weights (sum to 1.0), then apply risk-first gating and conflict-driven conviction reduction.

**Rationale**:
- Matches constitution: weights disclosed; conflict reduces conviction; default HOLD on uncertainty.
- Produces a stable Conviction Score (0–100) and consistent “bullish/bearish/neutral” evidence lists.

**Alternatives considered**:
- Rules-only (if-else) recommendation: rejected as brittle and hard to tune.
- ML-only classification: rejected by constitution (technical must be explicitly weighted against ML).

## Decision 4: Stop-loss and target levels anchored on VaR

**Decision**: Use 1-day 95% or 99% historical VaR as the primary stop-loss distance anchor; cap it into a stable range to avoid pathological outputs. Derive target distance from stop distance using regime-dependent reward/risk multipliers.

**Rationale**:
- Constitution requires VaR risk context and stop-loss derived from quantitative risk.
- VaR is already computed locally and is explainable.

**Alternatives considered**:
- ATR-only stop: acceptable, but adds a new risk computation when VaR already exists.
- Fixed % stop: rejected as not risk-adaptive.

## Decision 5: Local Trade Journal persistence uses SQLite

**Decision**: Persist the Local Trade Journal in a local SQLite database (built-in `sqlite3`), located under `data/metadata/`.

**Rationale**:
- Supports query-heavy Performance Review metrics (win rate, avg return, stop-loss hit rate) without reading/rewriting a whole JSON file.
- Atomic writes reduce corruption risk if the app exits unexpectedly.

**Alternatives considered**:
- JSON journal file: rejected due to O(n) scans for analytics and higher corruption risk on partial writes.

## Decision 6: “Assistant accuracy” is measured on journaled trades

**Decision**: Define assistant accuracy as trade-level outcome metrics on *closed* journaled trades:
- Win rate (closed trades with positive realized return)
- Avg return per trade
- Stop-loss hit rate

Open trades are tracked separately (count + unrealized P&L) and excluded from accuracy.

**Rationale**:
- The app only has guaranteed ground truth for decisions the user logs.
- Keeps evaluation honest and local-first.

**Alternatives considered**:
- Evaluate every viewed recommendation even without user action: rejected; lacks clear entry/exit and would require arbitrary evaluation horizons.

## Decision 7: UI must clearly separate raw forecast vs assistant recommendation

**Decision**: Redesign `PredictionTab` into a “Strategy Dashboard” that renders:
- Assistant Recommendation Banner + Evidence Panel + decision buttons
- A separate raw forecast section for the underlying model outputs (predicted close, baselines, staleness)

**Rationale**:
- Constitution requires clear labeling and separation.

**Alternatives considered**:
- Merge everything into one banner: rejected; users can’t distinguish model vs assistant logic.
