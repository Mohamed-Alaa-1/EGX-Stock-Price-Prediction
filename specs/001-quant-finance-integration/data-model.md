# Data Model: Quantitative Finance Integration

This document defines the data entities introduced/expanded by the feature in [specs/001-quant-finance-integration/spec.md](spec.md). Entities are designed to be:
- local-first (serializable to JSON/Parquet)
- reproducible (capture assumptions + windows)
- UI-friendly (explainability fields included)

## Shared Types

### WindowSpec
- `start_date`: date
- `end_date`: date
- `lookback_days`: int
- `min_observations`: int

### ReturnSpec
- `return_type`: enum (`simple`, `log`)
- `price_field`: enum (`close`, `adjusted_close`)
- `frequency`: enum (`1d`)

### DataProvenance
- `provider`: string (e.g., `yfinance`, `tradingview`, `csv_import`, `stooq`, `auto`)
- `fetched_at`: datetime
- `range_start`: date | null
- `range_end`: date | null
- `notes`: string | null

---

## RiskMetricsSnapshot
**Purpose**: per-ticker risk companion alongside predictions (FR-001..FR-003).

Fields:
- `symbol`: string
- `as_of_date`: date (last bar date used)
- `window`: WindowSpec
- `return_spec`: ReturnSpec
- `var_95_pct`: float | null
- `var_99_pct`: float | null
- `var_95_abs`: float | null (EGP)
- `var_99_abs`: float | null (EGP)
- `var_method`: enum (`historical`)
- `sharpe`: float | null
- `risk_free_rate`: float (default 0.0, must be labeled)
- `warnings`: list[string]
- `provenance`: DataProvenance

Validation rules:
- If insufficient observations, set numeric outputs to null and add warning.
- Must include VaR assumptions (method + lookback) in UI.

---

## StatisticalValidationResult
**Purpose**: record stationarity/regime diagnostics prior to training (FR-004..FR-006).

Fields:
- `symbol`: string
- `as_of_date`: date
- `window`: WindowSpec
- `series_tested`: enum (`returns`, `log_price`, `price_diff`)

ADF:
- `adf_statistic`: float | null
- `adf_pvalue`: float | null
- `adf_used_lag`: int | null
- `adf_nobs`: int | null
- `adf_critical_values`: dict[string, float] | null
- `adf_regression`: string (e.g., `c`)
- `adf_autolag`: string (e.g., `AIC`)

Hurst:
- `hurst`: float | null
- `hurst_method`: enum (`aggvar_increments`)
- `hurst_r2`: float | null
- `hurst_regime`: enum (`mean_reverting`, `random_like`, `trending`) | null

Meta:
- `warnings`: list[string]
- `provenance`: DataProvenance

Validation rules:
- Training must still run if desired, but UI/logs must surface warnings when signal looks weak.

---

## TransactionCostModel
**Purpose**: user-configurable EGX cost assumptions (FR-010..FR-011).

Fields:
- `commission_bps`: float
- `stamp_duty_bps`: float
- `slippage_bps`: float (optional, default 0)
- `min_cost_abs`: float (optional)
- `notes`: string | null

Derived:
- `total_cost_rate`: float (decimal; computed)

---

## BacktestRun
**Purpose**: store a reproducible strategy evaluation (FR-009..FR-011).

Fields:
- `run_id`: string
- `symbol`: string
- `strategy`: enum (`rsi`, `macd`, `ema`)
- `strategy_params`: dict[string, number]
- `window`: WindowSpec
- `execution_model`: enum (`signal_t_trade_t_plus_1_close`)
- `cost_model`: TransactionCostModel

Outputs:
- `gross_total_return`: float
- `net_total_return`: float
- `gross_cagr`: float | null
- `net_cagr`: float | null
- `gross_vol_annualized`: float | null
- `net_vol_annualized`: float | null
- `gross_sharpe`: float | null
- `net_sharpe`: float | null
- `max_drawdown`: float | null
- `turnover`: float | null
- `total_costs_paid`: float | null
- `warnings`: list[string]
- `provenance`: DataProvenance

---

## PortfolioOptimizationResult
**Purpose**: federated-mode allocation suggestions (FR-012..FR-014).

Fields:
- `symbols`: list[string]
- `as_of_date`: date
- `window`: WindowSpec
- `return_spec`: ReturnSpec
- `constraints`:
  - `long_only`: bool
  - `min_weight`: float
  - `max_weight`: float
  - `sum_to_one`: bool

Inputs:
- `mu`: dict[symbol, float]
- `covariance`:
  - `method`: enum (`sample`, `shrunk_diag`)
  - `shrinkage_alpha`: float
  - `diagonal_loading_lambda`: float

Outputs:
- `mpt_min_variance_weights`: dict[symbol, float] | null
- `mpt_frontier`: list[{
    `target_return`: float,
    `expected_return`: float,
    `volatility`: float,
    `weights`: dict[symbol, float]
  }]
- `risk_parity_weights`: dict[symbol, float] | null
- `risk_contributions`: dict[symbol, float] | null
- `warnings`: list[string]

---

## GdrPremiumDiscountSeries
**Purpose**: leading indicator for cross-listed stocks (FR-015..FR-016).

Fields:
- `local_symbol`: string
- `gdr_symbol`: string
- `fx_pair`: string
- `ratio_local_per_gdr`: float
- `window`: WindowSpec
- `premium_discount_pct`: list[{`date`: date, `value`: float, `is_imputed_fx`: bool}]
- `definition`: string (must match spec definition)
- `warnings`: list[string]
- `provenance_local`: DataProvenance
- `provenance_gdr`: DataProvenance
- `provenance_fx`: DataProvenance
