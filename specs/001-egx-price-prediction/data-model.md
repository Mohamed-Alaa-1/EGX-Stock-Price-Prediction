# Data Model (Phase 1)

**Feature**: [specs/001-egx-price-prediction/spec.md](spec.md)
**Date**: 2026-02-10

## Entities

### Stock
Represents an EGX-listed equity.

- `symbol` (string): exchange symbol used throughout the app
- `name` (string): company name
- `exchange` (string): defaults to `EGX`
- `status` (enum): active | suspended | delisted (best-effort; may be unknown)

### PriceBar (daily)
One historical bar/candle.

- `date` (date)
- `open` (number)
- `high` (number)
- `low` (number)
- `close` (number)
- `volume` (number | null)
- `adjusted_close` (number | null)

**Validation rules**:
- `high >= max(open, close, low)`
- `low <= min(open, close, high)`
- No duplicate `(symbol, date)` rows after normalization

### PriceSeries
Collection of `PriceBar` for a `Stock`.

- `symbol`
- `bars[]`
- `source` (DataSourceRecord)
- `last_updated_at` (datetime)

### DataSourceRecord
Provenance and caching metadata.

- `provider` (string): e.g., yfinance | tradingview | stooq | csv_import
- `provider_details` (object/string): e.g., url, symbol mapping notes
- `fetched_at` (datetime)
- `range_start` (date)
- `range_end` (date)

### IndicatorSelection
User toggles that affect the chart.

- `rsi_enabled` (bool)
- `macd_enabled` (bool)
- `ema_enabled` (bool)
- `support_resistance_enabled` (bool)

### ModelArtifact
A saved model usable for prediction.

- `artifact_id` (string)
- `type` (enum): per_stock | federated
- `covered_symbols` (string[])  
  - per_stock: exactly one symbol
  - federated: all symbols used during training
- `created_at` (datetime)
- `last_trained_at` (datetime)
- `data_source` (DataSourceRecord)
- `training_window` (object): range start/end dates
- `model_version` (string)
- `hyperparams` (object)
- `metrics` (object): baseline + model eval metrics
- `storage_path` (string): local file path to weights/config

### ForecastRequest
A user-initiated forecast.

- `symbol` (string)
- `target_date` (date)  
  - defined as next trading day by calendar rules
- `requested_at` (datetime)
- `model_choice` (enum): per_stock | federated
- `seed` (int | null)

### ForecastResult
What the Prediction tab displays.

- `symbol`
- `target_date`
- `predicted_close` (number)
- `baseline_close` (number)
- `expected_pct_change` (number)
- `momentum_label` (enum): bullish | bearish | neutral
- `latest_data_date` (date)
- `model_artifact_id` (string)

## Relationships

- Stock 1—N PriceBar (via `symbol`)
- Stock 1—N ModelArtifact (per-stock artifacts)
- ModelArtifact (federated) N—N Stock (via `covered_symbols`)
- ForecastRequest 1—1 ForecastResult

## State and Lifecycle

### Model staleness
- A model is considered **stale** when `now - last_trained_at > 14 days`.
- Stale models remain selectable but must show a stale warning and offer retraining.

### Training outcomes
- Training produces a new ModelArtifact or updates the existing one.
- Failed training does not alter the previous artifact.
