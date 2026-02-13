# Data Model: Stock Sheet Investment Insights

**Date**: 2026-02-13  
**Branch**: `001-stock-sheet-insights`

This feature is a local desktop workflow; the “contracts” document service boundaries, not a public network API.

## Entities

### StockSheetEntry

Represents one user-managed stock in the sheet.

Fields (conceptual):
- `symbol: str`
- `company_name: str | None`
- `sector: str | None`
- `enabled: bool` (implicit today; for MVP we treat all CSV entries as enabled)

### SheetInsightsRunRequest

Represents the parameters for one batch run.

Fields:
- `symbols: list[str] | None` (when omitted, run over all sheet entries)
- `forecast_method: str` (e.g., `ml`, `naive`, `sma`)
- `train_models: bool` (whether to train/update per-stock model before analysis)
- `force_refresh: bool` (attempt fresh retrieval first; no-cache default)

Validation:
- If `symbols` is provided, each symbol must be normalized to uppercase.

### InsightStatus

Per-stock processing outcome.

Enum:
- `OK`
- `HOLD_FALLBACK`
- `ERROR`

### StockInsight

Computed insight for one stock.

Fields:
- `symbol: str`
- `as_of_date: date` (last bar date used)
- `computed_at: datetime`
- `action: Buy|Sell|Hold`
- `conviction: int (0..100)`
- `stop_loss: float | None` (None implies N/A)
- `target_exit: float | None` (None implies N/A)
- `entry_zone_lower: float | None`
- `entry_zone_upper: float | None`
- `logic_summary: str`
- `status: InsightStatus`
- `status_reason: str | None`
- `used_cache_fallback: bool` (true only if fresh retrieval failed and cached series was used)
- `raw_outputs: object | None` (raw forecast + baseline + risk snapshot; shown separately in UI)
- `assistant_recommendation: object` (the StrategyEngine recommendation payload)

Invariants:
- If `action` is BUY/SELL then `stop_loss` MUST be present.
- If `action` is HOLD then `stop_loss` MUST be N/A.

### InsightBatchRun

One batch run across many symbols.

Fields:
- `batch_id: str`
- `computed_at: datetime`
- `request: SheetInsightsRunRequest`
- `results: list[StockInsight]`
- `summary: { total, ok, hold_fallback, error }`

Rules:
- The batch must complete even when individual results are ERROR.
- Each result must contain a `status` and a reason when not OK.
