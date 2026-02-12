# Implementation Plan: Quantitative Finance Integration

**Branch**: `001-quant-finance-integration` | **Date**: 2026-02-12 | **Spec**: [specs/001-quant-finance-integration/spec.md](spec.md)
**Input**: Feature specification from [specs/001-quant-finance-integration/spec.md](spec.md)

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add local-first quant modules to the EGX prediction app: per-ticker risk + signal context (1-day VaR 95/99, Sharpe, ADF, Hurst), backtesting with EGX transaction costs (gross + net), federated-mode portfolio insights (MPT efficient frontier + risk parity), and optional GDR premium/discount tracking when free data is available.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+ (per [pyproject.toml](../../pyproject.toml))  
**Primary Dependencies**: PyTorch, NumPy, Pandas, Pydantic, PySide6 (+ WebEngine)  
**Planned Additions (this feature)**: SciPy (optimization), statsmodels (ADF)  
**Storage**: Local files only (existing Parquet cache under `data/cache/`, JSON metadata under `data/metadata/`, model artifacts under `data/models/`)  
**Testing**: pytest (unit tests for quant computations + cost model + optimizers)  
**Target Platform**: Local desktop app (Windows primary; cross-platform where PySide6 works)
**Project Type**: Single Python project under `src/` (desktop UI + services + ML)  
**Performance Goals**:
- P1 metrics (VaR/Sharpe/ADF/Hurst) computed for a single ticker in ~2s (per SC-001/003)
- P2 backtest per ticker over 5y daily bars in ~5s (per SC-004)
- Federated portfolio insights for ≤10 tickers in ~10s (per SC-006)
**Constraints**:
- Local-first, personal-use only; no brokerage integration
- Free data sources only; manual CSV import must remain a reliable fallback
- Must degrade gracefully when a free source is unavailable/rate-limited
- All evaluation/backtests must be net-of-transaction-costs (commissions + stamp duties)
**Scale/Scope**: Single-user workstation, tens of tickers, daily bar frequency

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Derived from [.specify/memory/constitution.md](../../.specify/memory/constitution.md):

1) **Local-first / personal-use only**
- No cloud services required for core functionality.
- Explicitly informational outputs; no trading automation.

2) **Free data only + graceful degradation**
- All new analytics computed from locally cached free OHLCV + optional free endpoints.
- Any new provider must be optional; failures must fall back to cache and/or manual CSV import with a clear user-visible status.

3) **Risk companion is mandatory (VaR)**
- Every prediction view must include 1-day VaR at 95% and 99% (or clearly show “insufficient data”).
- VaR assumptions (method + lookback) must be displayed.

4) **Statistical validation before training (ADF + Hurst)**
- Training workflows must compute/record ADF (p-value, regression choice, autolag) and Hurst (method, regime classification) before fitting.
- UI/logging must flag weak/unsuitable signal; avoid overstating confidence.

5) **Realistic evaluation (transaction costs)**
- Backtests must report gross and net-of-cost results.
- Cost model must include commissions + stamp duties with documented defaults and user configurability.

6) **Federated portfolio insights (MPT + risk parity)**
- Federated mode must produce long-only allocations using MPT + risk parity.
- Must show constraints, window, covariance/expected-return assumptions, and portfolio risk metrics.

7) **Leading indicator support (GDR premium/discount)**
- Where mapping + free data exists, support premium/discount series; if not, degrade gracefully.

## Project Structure

### Documentation (this feature)

```text
specs/001-quant-finance-integration/
├── spec.md
├── plan.md
├── research.md
├── gdr-premium-discount-research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── local-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks) — not created here
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── app/
│   └── ui/
│       ├── prediction_tab.py          # Add risk + validation panels
│       └── training_tab.py            # Surface ADF/Hurst + warnings
├── core/
│   ├── indicators.py                  # Existing RSI/MACD/EMA
│   ├── trading_calendar.py            # Existing EGX calendar logic
│   ├── quant.py                       # NEW: VaR, Sharpe, ADF, Hurst utilities
│   └── backtest.py                    # NEW: vectorized backtester + EGX cost model
├── data/
│   ├── cache_store.py                 # Existing Parquet cache
│   ├── providers/
│   │   ├── base.py
│   │   ├── csv_provider.py
│   │   └── registry.py
│   └── metadata/
│       └── cross_listings.json        # NEW: local↔GDR mapping + ratio + FX pair
├── ml/
│   ├── federated_train.py             # Existing FedAvg trainer
│   └── portfolio.py                   # NEW: MPT frontier + risk parity (SciPy)
└── services/
  ├── prediction_service.py          # Extend to compute risk companion
  ├── training_service.py            # Extend to run ADF/Hurst prior to training
  ├── backtest_service.py            # NEW: orchestrate backtests + reports
  ├── portfolio_service.py           # NEW: federated portfolio insights
  └── gdr_bridge_service.py          # NEW: premium/discount series from cached primitives

tests/
└── unit/
  ├── test_quant_var_sharpe.py
  ├── test_quant_adf_hurst.py
  ├── test_backtest_cost_model.py
  └── test_portfolio_optimizers.py
```

**Structure Decision**: Keep the existing single-project `src/` layout and add focused, testable modules in `src/core/`, `src/ml/`, and `src/services/`. UI changes are limited to surfacing the new analytics in existing tabs; data acquisition remains via provider registry + local cache, with manual CSV import as the reliability fallback.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase Plan

### Phase 0 — Research (complete)
- Portfolio optimization approach (SciPy/SLSQP + covariance stabilization): [specs/001-quant-finance-integration/research.md](research.md)
- GDR premium/discount local-first strategy + data sourcing: [specs/001-quant-finance-integration/gdr-premium-discount-research.md](gdr-premium-discount-research.md)

### Phase 1 — Design & Contracts (this planning output)
- Define the data models for results/persistence: `data-model.md`
- Define internal UI↔services “local API” contract: `contracts/local-api.yaml`
- Provide quickstart paths for P1/P2/P3 validation: `quickstart.md`

### Constitution Re-check (post-design)
- Local-first / personal-use only: PASS (all artifacts assume desktop-local orchestration)
- Free data only + graceful degradation: PASS (provider fallback + CSV import is the reliability baseline)
- Risk companion (VaR) required: PASS (P1 contract + data model require VaR fields; plan mandates display per prediction)
- ADF + Hurst recorded before training: PASS (data model + quickstart include required recording and warnings)
- Realistic evaluation (EGX transaction costs): PASS (backtest schema requires cost model and net-of-cost reporting)
- Federated portfolio insights (MPT + risk parity): PASS (portfolio result schema includes both + risk contributions)
- GDR premium/discount optional + graceful failure: PASS (mapping-driven approach documented; missing inputs produce warnings)

### Phase 2 — Implementation (to be decomposed into tasks)
1) Implement `core.quant` (VaR/Sharpe/ADF/Hurst) with clear assumptions and “insufficient data” behavior.
2) Integrate P1 into prediction UI and `PredictionService` output (risk companion always present).
3) Integrate ADF/Hurst into training workflows with warnings/recording.
4) Implement `core.backtest` with EGX transaction cost model; expose P2 backtest UI/service.
5) Implement `ml.portfolio` (MPT + frontier + risk parity) and federated portfolio insights surfaces.
6) Implement cross-list mapping + premium/discount calculation service with graceful degradation and CSV fallback.
