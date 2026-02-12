# Data Model (Phase 1)

**Feature**: [specs/001-investment-assistant/spec.md](spec.md)
**Date**: 2026-02-12

## Entities

### StrategyRecommendation
Assistant-produced strategy guidance for a symbol at a point in time.

- `symbol` (string)
- `as_of_date` (date): last available candle date used for computation
- `action` (enum): buy | sell | hold
- `conviction` (int): 0–100
- `regime` (enum): trending | mean_reverting | random_like | unknown
- `entry_zone` (object | null):
  - `lower` (number)
  - `upper` (number)
- `target_exit` (number | null)
- `stop_loss` (number | null)
- `risk_distance_pct` (number | null): stop distance as % of reference price
- `evidence` (object):
  - `bullish[]` (EvidenceSignal)
  - `bearish[]` (EvidenceSignal)
  - `neutral[]` (EvidenceSignal)
- `logic_summary` (string)
- `raw_inputs` (object): minimal snapshot for auditing (forecast summary, VaR, RSI/MACD/EMA values, ADF/Hurst)

**Validation rules**:
- If `action` is buy or sell: `entry_zone`, `target_exit`, `stop_loss`, and `risk_distance_pct` must be non-null.
- If `action` is hold: `entry_zone`, `target_exit`, `stop_loss`, and `risk_distance_pct` must be null.
- `conviction` must be between 0 and 100.

### EvidenceSignal
One explainable contribution to a recommendation.

- `source` (enum): ml_forecast | rsi | macd | ema | var | hurst | adf
- `direction` (enum): bullish | bearish | neutral
- `weight` (number): blending weight for the source-group (for disclosure)
- `score` (number): normalized signal in [-1, +1]
- `summary` (string): short reason shown in UI
- `raw_value` (number/string/object | null): optional raw metric (e.g., RSI=72)

### TradeJournalEntry
An immutable log of a user action triggered from the Strategy Dashboard.

- `id` (string/uuid)
- `created_at` (datetime)
- `symbol` (string)
- `event_type` (enum): entry | exit
- `side` (enum): long | short
- `price` (number)
- `recommendation_snapshot` (StrategyRecommendation): assistant snapshot at decision time
- `notes` (string | null)

### SimulatedPosition
Derived from TradeJournalEntry events.

- `position_id` (string/uuid)
- `symbol` (string)
- `side` (enum): long | short
- `entry_at` (datetime)
- `entry_price` (number)
- `exit_at` (datetime | null)
- `exit_price` (number | null)
- `stop_loss_price` (number | null)
- `target_exit_price` (number | null)
- `stop_loss_hit` (bool | null): computed using OHLCV while holding window is evaluable
- `realized_return_pct` (number | null)

### PerformanceSummary
Aggregated analytics computed from closed positions (plus a separate view of open positions).

- `as_of_date` (date)
- `symbol` (string | null): null means “all symbols”
- `closed_trade_count` (int)
- `open_trade_count` (int)
- `win_rate` (number | null)
- `avg_return_pct` (number | null)
- `stop_loss_hit_rate` (number | null)
- `warnings[]` (string)

## Relationships

- StrategyRecommendation is computed from:
  - PriceSeries (historical)
  - ForecastResult (raw forecast)
  - RiskMetricsSnapshot (VaR)
  - StatisticalValidationResult (ADF + Hurst)
  - Technical indicators computed from PriceSeries

- TradeJournalEntry references exactly one StrategyRecommendation snapshot.
- SimulatedPosition is derived by pairing an entry event with the next exit event for the same symbol (and side).
- PerformanceSummary aggregates metrics over SimulatedPositions.

## Lifecycle & State

### Recommendation lifecycle
- Recomputed on demand when the user requests a strategy for a symbol.
- Stored inside the trade journal only as a snapshot when the user logs entry/exit.

### Journal lifecycle
- App persists entries locally (SQLite).
- Entries are append-only; closing a position is represented by an exit entry referencing the open position.

### Stop-loss hit determination (daily OHLCV)
- Long: stop considered “hit” if any candle low ≤ stop price between entry and exit.
- Short: stop considered “hit” if any candle high ≥ stop price between entry and exit.
- If both stop and target are touched in the same day, the evaluation uses a conservative convention (treat stop as hit first).
