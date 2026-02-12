# Quickstart

This project is a **local, personal-use** desktop app for EGX analysis. This feature adds an Investment Assistant that provides **Buy/Sell/Hold** recommendations with entry/exit levels and a local trade journal.

## Installation & Setup

```bash
pip install -r requirements.txt
python -m src.app.main
```

## Strategy Dashboard (formerly Prediction tab)

1. Select a stock (e.g., COMI)
2. Generate a raw forecast (ML / naive / SMA) as usual
3. View the **Assistant Recommendation** section:
   - Recommendation Banner (BUY / SELL / HOLD + conviction)
   - Entry Zone, Target Exit, Stop-Loss (N/A for HOLD)
   - Evidence Panel (bullish vs bearish signals)
4. Click **Execute Entry** to log a simulated entry locally
5. Later, click **Log Exit** to close the simulated position

## Performance Review

The app includes a Performance Review view that summarizes outcomes over your **journaled** simulated trades:
- Closed trade count, win rate, average return
- Stop-loss hit rate
- Open trade count and mark-to-last-close P&L (reported separately)

## Local Storage

- Price cache: Parquet files under `data/cache/`
- Models: `.pt` files under `data/models/`
- Trade journal (this feature): SQLite DB under `data/metadata/trade_journal.sqlite3`

## Artifacts in this Spec Folder

- [spec.md](spec.md): requirements and user stories
- [plan.md](plan.md): implementation plan
- [research.md](research.md): Phase 0 decisions
- [data-model.md](data-model.md): entities and lifecycle
- [contracts/local-api.yaml](contracts/local-api.yaml): internal service contract

## Implementation

All 44 tasks are implemented (T001–T044). Key modules:

| Module | Purpose |
|--------|---------|
| `src/services/strategy_engine.py` | Ensemble scoring → BUY/SELL/HOLD |
| `src/services/trade_journal_store.py` | SQLite-backed journal persistence |
| `src/services/portfolio_tracker.py` | High-level entry/exit logging |
| `src/app/ui/prediction_tab.py` | Strategy Dashboard with recommendation panel |
| `src/app/ui/performance_tab.py` | Read-only performance review |

Tests: 83 total (14 strategy engine + 10 journal store + 9 portfolio tracker + 4 quant aliases + existing suite).
