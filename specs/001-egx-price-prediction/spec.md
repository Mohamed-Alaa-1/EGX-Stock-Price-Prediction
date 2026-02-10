# Feature Specification: EGX Price Prediction UI

**Feature Branch**: `001-egx-price-prediction`  
**Created**: 2026-02-10  
**Status**: Draft  
**Input**: User description: "Local personal-use app focused on the Egyptian stock market (EGX) with a sleek UI. The app has two tabs: (1) Training: user selects stock(s), chooses per-stock training or federated mode, trains and saves models; models should be retrained about every 2 weeks. (2) Prediction: user selects a stock, views a TradingView-like chart with indicator toggles (MACD/RSI/EMA + support/resistance), and gets AI/deep-learning predictions for next trading-day close including % change and bullish/bearish momentum. If no trained model exists, prompt user to train and navigate to the Training tab. The AI model is built with PyTorch. Data must be obtained via free methods (TradingView or yfinance or other free reliable options) and the app runs locally."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Select EGX stock and get next-close forecast (Priority: P1)

As a user, I want to pick an EGX-listed stock and instantly see a next trading-day closing price forecast with expected percent change and a clear momentum label, so I can quickly assess bullish/bearish expectations.

**Why this priority**: This is the core value of the product (prediction + momentum for a chosen stock).

**Independent Test**: Can be fully tested by selecting one stock and generating a forecast that includes a prediction, % change, momentum label, and the data timestamp used.

**Acceptance Scenarios**:

1. **Given** the app has access to historical price data for a selected EGX stock, **When** the user selects the stock and requests a forecast, **Then** the app shows (a) predicted next trading-day close, (b) expected % change vs the most recent known close, (c) momentum label, and (d) the timestamp/date of the latest data used.
2. **Given** the selected stock has insufficient history or missing required fields, **When** the user requests a forecast, **Then** the app explains what is missing and does not show a misleading prediction.
3. **Given** the target day is not a trading day, **When** the user requests a “tomorrow” forecast, **Then** the app targets the next trading day and labels it clearly.

4. **Given** no trained model exists for the selected stock, **When** the user requests a forecast, **Then** the app prompts the user to train a model and offers a one-click path that navigates to the Training tab and pre-fills the stock selection.

---

### User Story 2 - View chart and toggle indicators (Priority: P2)

As a user, I want an interactive stock chart for the selected EGX stock and I want to toggle common technical indicators, so I can visually contextualize the forecast.

**Why this priority**: The chart is the primary way users interpret price behavior; indicator toggles are required for usability and credibility.

**Independent Test**: Can be fully tested by loading the chart for one stock and toggling each indicator on/off, verifying the chart updates and the toggles persist while viewing the stock.

**Acceptance Scenarios**:

1. **Given** a stock is selected, **When** the chart loads, **Then** the user sees historical price candles/bars for that stock with clearly labeled time axis and price axis.
2. **Given** the chart is visible, **When** the user toggles RSI, MACD, and EMA, **Then** each indicator appears/disappears without breaking the chart view.
3. **Given** the chart is visible, **When** the user toggles support/resistance levels, **Then** the chart overlays the levels and labels them in a way that remains readable.

---

### User Story 3 - Train and save a model (single-stock or federated) (Priority: P2)

As a user, I want to train a model from EGX data on demand and save it locally, so that later predictions are fast and do not require retraining every time.

**Why this priority**: The system must support explicit training sessions and persistent models to make predictions usable.

**Independent Test**: Can be fully tested by training a single-stock model for one stock, verifying a local model artifact is created, then generating a prediction using that saved model.

**Acceptance Scenarios**:

1. **Given** the user is on the Training tab, **When** they select a stock and press Train, **Then** the app trains a model, displays progress, and saves a reusable model for that stock.
2. **Given** the user chooses federated mode and selects multiple stocks, **When** they press Train, **Then** the app trains a federated model across the chosen stocks and saves it as a reusable federated model artifact.
3. **Given** training fails due to missing data or errors, **When** the failure occurs, **Then** the app reports the reason and does not save a broken model.
4. **Given** a model already exists, **When** the user presses Train again, **Then** the app either retrains/updates the model or asks for confirmation, and records the model’s last-trained date.

---

### User Story 4 - Browse a complete EGX stock list locally (Priority: P3)

As a user, I want a complete list of EGX stocks in the app (with easy search/browse) so I can quickly find and analyze any listed stock without knowing symbol formats.

**Why this priority**: The product becomes “easy to use” only when stock discovery is simple; however, it can be layered after prediction and chart basics.

**Independent Test**: Can be fully tested by loading the stock list, searching for a known EGX company name/symbol, selecting it, and confirming the app switches context to that stock.

**Acceptance Scenarios**:

1. **Given** the app starts, **When** the user opens the stock selector, **Then** the app displays an EGX stock list with both symbol and company name.
2. **Given** the stock list is displayed, **When** the user searches by partial name or symbol, **Then** the list filters to matching stocks.
3. **Given** the user selects a stock from the list, **When** selection is confirmed, **Then** the chart and forecast panels update to that stock.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- No internet connection (must still open and show cached data; forecasts may be unavailable if no cached history exists).
- Data source returns partial history, duplicated days, or non-trading-day rows.
- Market holidays/weekends: “tomorrow” must resolve to next trading day.
- Selected stock is delisted/suspended or has long gaps in trading.
- Very recent IPO with short history.
- User changes stock while a forecast is running (must not mix outputs between stocks).
- Local clock/timezone mismatch (must clearly show the data date used and target date).
- Federated model exists but does not include the selected stock (must be clear and not misrepresent coverage).
- Model is older than the retraining window (should prompt to retrain or clearly show staleness).

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Assumptions & Dependencies

- The primary target market is EGX equities; “tomorrow” means the next EGX trading day.
- Historical data availability for EGX via free sources may vary by ticker and time range.
- The default chart time resolution is daily historical candles/bars unless the data source supports finer granularity for free.
- The app is intended for a single local user and does not include multi-user permissions.
- The ML training and inference run locally; performance depends on local CPU/GPU availability.

### Out of Scope

- Automated trading, brokerage connections, or order execution.
- Claims of guaranteed returns or investment advice.
- Paid datasets and paid market-data subscriptions.

### Functional Requirements

- **FR-001**: System MUST run locally for a single user and MUST NOT require paid subscriptions or paid data sources.
- **FR-002**: System MUST provide an EGX stock selector that allows choosing a stock from a complete EGX list (symbol + company name).
- **FR-003**: System MUST display an interactive historical price chart for the selected stock.
- **FR-004**: Users MUST be able to toggle the following overlays/indicators on the chart: RSI, MACD, EMA, and support/resistance levels.
- **FR-005**: System MUST generate a next trading-day closing price prediction for the selected stock.
- **FR-006**: System MUST display the expected percent change between the predicted close and the most recent known close.
- **FR-007**: System MUST display a momentum label (bullish/bearish) derived from the expected percent change using a documented rule (default: bullish if expected change > 0, bearish if < 0, neutral if exactly 0).
- **FR-008**: System MUST show the target date (next trading day) and the latest data date/time used for the forecast.
- **FR-009**: System MUST use free methods to obtain historical price data and MUST clearly disclose the data source(s) used.
- **FR-010**: System MUST handle data fetch failures gracefully by showing a clear error message and keeping the UI usable.
- **FR-011**: System MUST cache downloaded historical data locally to reduce repeated downloads and enable offline viewing.
- **FR-012**: System MUST support a free fallback data path for cases where EGX data cannot be fetched automatically (e.g., user-provided local import of historical data).
- **FR-013**: System MUST provide a simple baseline forecast (e.g., “naive: last close”) alongside the AI forecast for comparison.
- **FR-014**: System MUST label the feature as informational/personal-use and MUST avoid presenting predictions as guaranteed outcomes.

- **FR-015**: The app MUST have exactly two primary tabs: (1) Training and (2) Prediction.
- **FR-016**: On the Training tab, users MUST be able to select a single stock and train a dedicated model for that stock.
- **FR-017**: On the Training tab, users MUST be able to enable a federated learning mode and select multiple stocks for federated training.
- **FR-018**: The app MUST save trained models locally and reuse them for later predictions without retraining each time.
- **FR-019**: The app MUST record and display the last-trained timestamp for each saved model.
- **FR-020**: The app MUST support retraining on a schedule of approximately every 2 weeks (prompting the user or marking the model as stale when older than the window).
- **FR-021**: On the Prediction tab, if no suitable model exists for the selected stock, the app MUST prompt the user to train and provide a one-click path to start training.
- **FR-022**: On the Prediction tab, if both a stock-focused model and a federated model are available, the app MUST allow the user to choose which model to use for prediction.
- **FR-023**: The deep learning model(s) MUST be implemented using PyTorch.

### Key Entities *(include if feature involves data)*

- **Stock**: An EGX-listed instrument (symbol, company name, optional sector).
- **PriceSeries**: Historical price data for a stock (date/time, open/high/low/close, volume when available).
- **IndicatorSelection**: User’s chosen indicator toggles for the chart (RSI/MACD/EMA/support-resistance on/off).
- **ForecastRequest**: A single prediction request (stock, target date, requested at time, parameters relevant to the forecast).
- **ForecastResult**: Output shown to the user (predicted close, expected % change, momentum label, baseline value, and latest data timestamp).
- **DataSourceRecord**: Provenance metadata describing where and when historical data was obtained.
- **ModelArtifact**: A saved trained model (type: per-stock or federated; covered stocks; last-trained timestamp; version).

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: A user can select a stock and generate a forecast in 3 steps or fewer.
- **SC-002**: For cached historical data, the app shows a forecast result in under 30 seconds for a typical stock.
- **SC-003**: The app correctly identifies the next trading day (not weekend/holiday) for at least 99% of forecast requests.
- **SC-004**: On a defined historical evaluation set, the AI forecast achieves at least a 5% improvement in average absolute error compared to the baseline forecast.
- **SC-005**: Users can toggle each required indicator and see the chart update within 1 second on a typical machine.
- **SC-006**: The app can be used without creating an account and without any paid data sources.
