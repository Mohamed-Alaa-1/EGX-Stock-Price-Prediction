# EGX Stock Price Prediction - Desktop Application

**Local, personal-use desktop app for Egyptian Exchange (EGX) stock price forecasting using deep learning.**

⚠️ **DISCLAIMER**: This tool is for educational and personal use only. Not financial advice. All predictions are experimental. Use at your own risk.

If the app presents an “Assistant” recommendation (e.g., Buy/Sell/Hold), it will be clearly labeled as processed guidance and visually separated from raw model outputs.

## Overview

A PySide6 desktop application that trains PyTorch LSTM models on EGX stock data and generates next trading-day price predictions.

### Key Features

- **Two Training Modes**: Per-Stock (individual) and Federated (multi-stock FedAvg)
- **Interactive Charts**: Plotly.js candlestick charts with RSI/MACD/EMA/Support-Resistance toggles
- **Free Data Sources**: yfinance (with EGX-specific suffixes) + CSV import fallback
- **Local-First**: All data cached in Parquet files, models saved as PyTorch checkpoints
- **Model Staleness**: 14-day threshold with automatic warnings
- **EGX Stock Universe**: 20+ Egyptian stocks with searchable selector
- **Strategy Dashboard**: ML-powered Buy/Hold/Sell recommendations with conviction scores
- **Trade Journal**: Simulated trade logging with entry/exit tracking (SQLite-backed at `data/metadata/trade_journal.sqlite3`)
- **Performance Review**: Win rate, average return, and stop-loss analytics

## Installation

### Prerequisites

- Python 3.11+
- Git

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python -m src.app.main
```

## Usage

### Strategy Tab

1. Search and select a stock (e.g., COMI - Commercial International Bank)
2. Choose prediction method (ML Model/Naive Baseline/SMA Baseline)
3. Click Predict for next trading-day forecast
4. See predicted price, model info, staleness warnings, momentum
5. Review the **Assistant Recommendation** panel (Buy/Hold/Sell with conviction %)
6. Use **Execute Entry** / **Log Exit** buttons to record simulated trades

### Chart Tab

- Full-size interactive candlestick chart with RSI/MACD/EMA/Support-Resistance overlays
- Automatically loads when you select a stock in the Strategy tab

### Performance Tab

- View overall trade statistics (win rate, avg return, stop-loss hit rate)
- See open positions and closed trade counts
- Data persisted in `data/metadata/trade_journal.sqlite3`

### Training Tab

1. Select mode (Per-Stock or Federated for 2+ stocks)
2. Search and select stock(s)
3. Click Train and monitor progress
4. View saved models with last-trained timestamps
5. Retrain existing models with confirmation

### Settings Tab

- View cache status and clear cached data
- See configuration details

## Implementation Status

✅ **All 62 tasks complete** from the EGX Price Prediction spec (100%)
✅ **All 44 tasks complete** from the Investment Assistant spec (100%)

### EGX Price Prediction
- Phase 1: Setup (8 tasks)
- Phase 2: Foundational (13 tasks)
- Phase 3: Prediction (8 tasks)
- Phase 4: Charts (8 tasks)
- Phase 5: Training (13 tasks)
- Phase 6: Stock Universe (6 tasks)
- Phase 7: Polish (6 tasks)

### Investment Assistant
- Phase 3: Strategy Engine core (T001–T024)
- Phase 4: Strategy Dashboard UI (T025–T030)
- Phase 5: Trade Journal & Performance (T002–T003, T005–T006, T008, T031–T041)
- Phase 6: Polish (T042–T044)

See [tasks.md](specs/001-investment-assistant/tasks.md) for detailed breakdown.
