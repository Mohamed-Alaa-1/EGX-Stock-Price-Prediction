# Quickstart

This project is a **local, personal-use** desktop app to train PyTorch models on EGX stock data and make next trading-day close predictions.

## Installation & Setup

```bash
# Clone repository
git clone <repository-url>
cd stocks-project

# Install dependencies
pip install -r requirements.txt

# Run application
python -m src.app.main
```

## Launcher Dialog

On startup, a **Launcher Dialog** appears with two provider options:

- **YFinance (Historical Data)**: Full historical OHLCV data via yfinance. Best for training and historical analysis.
- **TradingView (Real-Time Analysis)**: Current technical analysis snapshot via `tradingview-ta`. Provides real-time price data with additional timeframe options (1 Min, 5 Min, 15 Min, 1 Hour).

Select a provider and click **Launch** to open the main application window.

## User Workflow

### Tab 1: Prediction

1. **Select a stock** from the searchable list (e.g., COMI - Commercial International Bank)
2. **Choose prediction method**:
   - ML Model (LSTM) - requires trained model
   - Naive Baseline (last close)
   - SMA Baseline (20-day average)
3. **View interactive chart** with price history
4. **Switch chart timeframe** using the dropdown (1 Day / 1 Week / 1 Month; additional intraday options when using TradingView)
5. **Toggle indicators** (RSI, MACD, EMA, Support/Resistance)
6. **Press Predict** to get next trading-day forecast
7. **If no model exists**: App prompts to train and switches to Training tab

**Prediction displays**:
- Predicted closing price for next trading day
- Prediction method used
- Model artifact ID and training date
- Staleness warning if model is >14 days old
- 10-day momentum indicator

### Tab 2: Training

1. **Select training mode**:
   - Per-Stock: Train individual model for one ticker
   - Federated: Train aggregated model across multiple tickers (select 2+)
2. **Select stock(s)** from searchable list
3. **Press Train** to start training
4. **Monitor progress** in real-time log
5. **View saved models** in list with last-trained timestamps
6. **Retrain existing models** with confirmation dialog

**Training features**:
- Progress updates per epoch/round
- Automatic model versioning
- Metrics comparison to baseline
- Model staleness tracking (14-day threshold)
- **Multi-feature OHLCV input** (close, open, high, low, volume)
- **Attention-enhanced LSTM** with learnable attention over all timesteps
- **Learning rate scheduler** (ReduceLROnPlateau, patience=5, factor=0.5)
- **Gradient clipping** (max_norm=1.0) for training stability
- Training log shows bar count, date range, features, and model architecture

### Tab 3: Settings

- **View cache status**: Number of cached files and total size
- **Clear cache**: Remove all cached price data
- **View configuration**: Data/cache/models directories, staleness threshold

## Core Behaviors

- **Provider choice**: YFinance (historical) or TradingView (real-time) — selected at launch
- **Free data only**: yfinance (with .CA/.CAI suffix fallback) + TradingView TA + CSV import
- **Chart timeframes**: Switch between 1 Day, 1 Week, 1 Month (plus intraday with TradingView)
- **Local-first**: All data cached in Parquet files, models saved as PyTorch .pt files
- **Trading calendar**: EGX (Sun-Thu), auto-calculates next trading day
- **Model staleness**: 14-day threshold with user warnings
- **Baseline comparison**: All ML predictions compared to naive/SMA baselines
- **Backward compatibility**: Old single-feature models load and run inference (fallback to close-only)
- **No financial advice**: Disclaimer banner on all screens

## "No Model → Prompt → Train → Predict" Path

1. User opens app, goes to Prediction tab
2. User selects "COMI" and chooses "ML Model"
3. User clicks "Predict"
4. App detects no trained model exists for COMI
5. App shows dialog: "No trained model found for COMI. Would you like to switch to the Training tab to train a model?"
6. User clicks "Yes"
7. App switches to Training tab with COMI pre-selected
8. User clicks "Train" (per-stock mode)
9. App fetches data, trains LSTM model, saves artifact
10. Training completes, artifact appears in saved models list
11. User switches back to Prediction tab
12. User clicks "Predict" again
13. App loads trained model, runs inference, displays prediction with chart

## Artifacts in this Spec Folder

- [spec.md](spec.md): Requirements and user stories
- [plan.md](plan.md): Implementation plan with tech stack
- [tasks.md](tasks.md): Task breakdown (62 tasks organized by user story)
- [research.md](research.md): Key architectural decisions
- [data-model.md](data-model.md): Entity schemas and lifecycle
- [contracts/local-api.yaml](contracts/local-api.yaml): Internal service contracts
