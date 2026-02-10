# EGX Stock Price Prediction - Desktop Application

**Local, personal-use desktop app for Egyptian Exchange (EGX) stock price forecasting using deep learning.**

⚠️ **DISCLAIMER**: This tool is for educational and personal use only. Not financial advice. All predictions are experimental. Use at your own risk.

## Overview

A PySide6 desktop application that trains PyTorch LSTM models on EGX stock data and generates next trading-day price predictions.

### Key Features

- **Two Training Modes**: Per-Stock (individual) and Federated (multi-stock FedAvg)
- **Interactive Charts**: Plotly.js candlestick charts with RSI/MACD/EMA/Support-Resistance toggles
- **Free Data Sources**: yfinance (with EGX-specific suffixes) + CSV import fallback
- **Local-First**: All data cached in Parquet files, models saved as PyTorch checkpoints
- **Model Staleness**: 14-day threshold with automatic warnings
- **EGX Stock Universe**: 20+ Egyptian stocks with searchable selector

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

### Prediction Tab

1. Search and select a stock (e.g., COMI - Commercial International Bank)
2. Choose prediction method (ML Model/Naive Baseline/SMA Baseline)
3. View chart with historical data and toggle indicators
4. Click Predict for next trading-day forecast
5. See predicted price, model info, staleness warnings, momentum

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

✅ **All 62 tasks complete** (100%)

- Phase 1: Setup (8 tasks)
- Phase 2: Foundational (13 tasks)
- Phase 3: Prediction (8 tasks)
- Phase 4: Charts (8 tasks)
- Phase 5: Training (13 tasks)
- Phase 6: Stock Universe (6 tasks)
- Phase 7: Polish (6 tasks)

See [tasks.md](specs/001-egx-price-prediction/tasks.md) for detailed breakdown.
