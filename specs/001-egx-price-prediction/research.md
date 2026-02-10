# Phase 0 Research: EGX Price Prediction UI

**Feature**: [specs/001-egx-price-prediction/spec.md](spec.md)
**Date**: 2026-02-10

## Decision 1: Market data source for EGX (free)

**Decision**: Prefer a user-import + pluggable provider approach; support at least one free automatic fetch provider, but do not depend on any single free provider for EGX completeness.

**Rationale**:
- Free providers’ EGX coverage varies by ticker and time range.
- The feature must remain usable even when free automated coverage is incomplete.
- A user-import fallback (CSV) guarantees the system can function for “any selected stock” in practice.

**Alternatives considered**:
- Rely solely on `yfinance`: good UX if coverage exists, but EGX coverage can be spotty.
- Rely on TradingView scraping: terms and stability risk; avoid hard dependency.
- Rely solely on Stooq: often no EGX coverage.

## Decision 2: Model strategy (per-stock vs federated)

**Decision**: Implement both model types:
- **Per-stock model**: trained on the selected stock’s history; used by default when available.
- **Federated model**: trained across a user-selected set of stocks; available as an alternative prediction option.

**Rationale**:
- Per-stock training aligns with the UI workflow (train a model for the chosen ticker and reuse it).
- Federated training is useful when per-stock history is short/noisy and to share representation across EGX stocks.

**Alternatives considered**:
- Federated-only: weaker UX when user expects a ticker-specific model.
- Per-stock only: misses the user’s explicit federated requirement.

## Decision 3: Federated learning approach

**Decision**: Use a **simple, local federated simulation** approach (FedAvg-style aggregation) across multiple tickers treated as clients.

**Rationale**:
- This is a local, single-user app; true multi-device FL is out of scope.
- A local simulation satisfies the “federated mode” requirement while staying simple and reproducible.

**Alternatives considered**:
- Real multi-device federated learning: high complexity, networking, security, and coordination.

## Decision 4: Retraining policy

**Decision**: Track `last_trained_at` for each saved model and consider it **stale** after 14 days.

**Rationale**:
- Matches the “every 2 weeks or so” requirement.
- Keeps behavior deterministic and testable.

**Alternatives considered**:
- Always retrain on prediction: too slow and contradicts “save for later.”
- Fully automatic background retraining: added complexity and scheduling differences across OS.

## Decision 5: Prediction target definition

**Decision**: Default target is **next trading-day close**; label the target date clearly.

**Rationale**:
- Matches the constitution’s minimal scope and avoids ambiguous “tomorrow” on holidays/weekends.

## Decision 6: Indicators and chart

**Decision**: Provide toggles for RSI, MACD, EMA, and support/resistance overlays driven by deterministic computations on the locally available price series.

**Rationale**:
- Keeps indicator output consistent and testable.
- Avoids reliance on external chart engines for computations.

## Open Questions (to resolve during implementation planning)

- EGX trading calendar source: whether to embed a simple weekend-only calendar initially or allow a configurable holiday list.
- Minimum history required to enable training/prediction for each model type.
- Exact meaning of “TradingView-like”: embedded TradingView widget vs a similar interactive chart experience.
