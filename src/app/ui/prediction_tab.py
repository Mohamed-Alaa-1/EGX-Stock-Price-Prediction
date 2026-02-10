"""
Prediction tab UI component.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QSplitter,
)
from PySide6.QtCore import Qt, QThread, Signal
from datetime import datetime

from core.schemas import ForecastMethod, ForecastResult
from core.trading_calendar import TradingCalendar
from core.momentum import calculate_momentum, get_momentum_signal
from services.prediction_service import PredictionService
from services.price_service import PriceService
from services.model_staleness import get_staleness_message
from services.model_registry import get_registry
from app.ui.chart_panel import ChartPanel
from app.ui.stock_selector import StockSelectorWidget


class PredictionWorker(QThread):
    """Background prediction worker."""

    finished = Signal(ForecastResult)
    error = Signal(str)

    def __init__(self, symbol: str, method: ForecastMethod):
        super().__init__()
        self.symbol = symbol
        self.method = method

    def run(self):
        """Execute prediction."""
        try:
            print(f"[PredictionWorker] Starting prediction: {self.symbol}, method={self.method.value}")
            service = PredictionService()
            result = service.predict(self.symbol, method=self.method)
            print(f"[PredictionWorker] Prediction complete: {result.predicted_close:.2f}")
            self.finished.emit(result)
        except Exception as e:
            print(f"[PredictionWorker] ERROR: {e}")
            self.error.emit(str(e))


class PredictionTab(QWidget):
    """Prediction tab widget."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        # Main splitter for chart and controls
        splitter = QSplitter(Qt.Horizontal)

        # Left side: Chart
        self.chart_panel = ChartPanel()
        splitter.addWidget(self.chart_panel)

        # Right side: Controls
        controls_widget = QWidget()
        controls_layout = QVBoxLayout()

        # Stock selection
        stock_group = QGroupBox("Stock Selection")
        stock_layout = QVBoxLayout()

        self.stock_selector = StockSelectorWidget(allow_multiple=False)
        stock_layout.addWidget(self.stock_selector)

        stock_group.setLayout(stock_layout)
        controls_layout.addWidget(stock_group)

        # Prediction method
        method_group = QGroupBox("Prediction Method")
        method_layout = QVBoxLayout()

        self.method_button_group = QButtonGroup()
        self.ml_radio = QRadioButton("ML Model (LSTM)")
        self.naive_radio = QRadioButton("Naive Baseline (last close)")
        self.sma_radio = QRadioButton("SMA Baseline (20-day)")
        self.ml_radio.setChecked(True)

        self.method_button_group.addButton(self.ml_radio, 0)
        self.method_button_group.addButton(self.naive_radio, 1)
        self.method_button_group.addButton(self.sma_radio, 2)

        method_layout.addWidget(self.ml_radio)
        method_layout.addWidget(self.naive_radio)
        method_layout.addWidget(self.sma_radio)

        method_group.setLayout(method_layout)
        controls_layout.addWidget(method_group)

        # Predict button
        self.predict_button = QPushButton("Predict")
        self.predict_button.clicked.connect(self._on_predict)
        controls_layout.addWidget(self.predict_button)

        # Results display
        results_group = QGroupBox("Prediction Results")
        results_layout = QVBoxLayout()

        self.results_label = QLabel("Select a stock and click Predict")
        self.results_label.setStyleSheet("font-size: 14px; padding: 20px;")
        self.results_label.setAlignment(Qt.AlignCenter)
        self.results_label.setWordWrap(True)
        results_layout.addWidget(self.results_label)

        results_group.setLayout(results_layout)
        controls_layout.addWidget(results_group)

        # Momentum display
        momentum_group = QGroupBox("Technical Indicators")
        momentum_layout = QVBoxLayout()

        self.momentum_label = QLabel("---")
        self.momentum_label.setStyleSheet("font-size: 13px; padding: 10px;")
        momentum_layout.addWidget(QLabel("10-day Momentum:"))
        momentum_layout.addWidget(self.momentum_label)

        momentum_group.setLayout(momentum_layout)
        controls_layout.addWidget(momentum_group)

        controls_layout.addStretch()
        controls_widget.setLayout(controls_layout)
        splitter.addWidget(controls_widget)

        # Set splitter proportions (70% chart, 30% controls)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Connect stock selection to chart loading
        self.stock_selector.selection_changed.connect(self._on_stock_selected)

    def _on_stock_selected(self, symbol: str):
        """Load chart data when stock is selected."""
        print(f"[PredictionTab] Stock selected: {symbol}")
        try:
            self.chart_panel.set_symbol(symbol)
            interval = self.chart_panel.get_interval()
            price_service = PriceService()
            series = price_service.get_series(symbol, interval=interval)
            print(f"[PredictionTab] Loading chart for {symbol} ({len(series.bars)} bars, interval={interval})")
            self.chart_panel.load_series(series)
            print(f"[PredictionTab] Chart loaded successfully for {symbol}")
        except Exception as e:
            print(f"[PredictionTab] ERROR loading chart: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Chart Error", f"Failed to load chart data:\n{e}")

    def _on_predict(self):
        """Handle predict button click."""
        selected = self.stock_selector.get_selected_symbols()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a stock")
            return

        symbol = selected[0]
        print(f"[PredictionTab] Predict clicked for {symbol}")

        if self.ml_radio.isChecked():
            method = ForecastMethod.ML
        elif self.naive_radio.isChecked():
            method = ForecastMethod.NAIVE
        else:
            method = ForecastMethod.SMA

        # Check if model exists for ML
        if method == ForecastMethod.ML:
            service = PredictionService()
            if not service.has_model(symbol):
                reply = QMessageBox.question(
                    self,
                    "No Model Available",
                    f"No trained model found for {symbol}.\n\n"
                    "Would you like to switch to the Training tab to train a model?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    parent_tabs = self.parent()
                    if parent_tabs:
                        parent_tabs.setCurrentIndex(1)
                return

        # Run prediction
        self.predict_button.setEnabled(False)
        self.results_label.setText("Generating prediction...")

        self.worker = PredictionWorker(symbol, method)
        self.worker.finished.connect(self._on_prediction_finished)
        self.worker.error.connect(self._on_prediction_error)
        self.worker.start()

    def _on_prediction_finished(self, result: ForecastResult):
        """Handle prediction completion."""
        self.predict_button.setEnabled(True)
        print(f"[PredictionTab] Prediction finished: {result.request.symbol} -> {result.predicted_close:.2f}")

        # Format results
        symbol = result.request.symbol
        target = result.request.target_date
        predicted = result.predicted_close
        method = result.request.method.value

        text = f"<h2>{symbol}</h2>"
        text += f"<p><b>Predicted Close for {target}:</b> {predicted:.2f} EGP</p>"
        text += f"<p>Method: {method}</p>"
        text += f"<p>Generated: {result.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>"

        if result.model_artifact_id:
            text += f"<p>Model: {result.model_artifact_id}</p>"

            # Get model details
            registry = get_registry()
            artifact = next(
                (a for a in registry.list_all() if a.artifact_id == result.model_artifact_id),
                None,
            )

            if artifact:
                staleness = get_staleness_message(artifact)
                text += f"<p>{staleness}</p>"

                if result.is_model_stale:
                    text += "<p style='color: orange;'>Warning: Consider retraining the model</p>"

        self.results_label.setText(text)

        # Update momentum
        try:
            service = PredictionService()
            series = service._get_series(symbol)
            momentum = calculate_momentum(series)
            signal = get_momentum_signal(momentum)

            if momentum is not None:
                self.momentum_label.setText(f"{momentum:.2f}% ({signal})")
            else:
                self.momentum_label.setText("Insufficient data")
        except Exception as e:
            self.momentum_label.setText(f"Error: {e}")

    def _on_prediction_error(self, error: str):
        """Handle prediction error."""
        self.predict_button.setEnabled(True)
        print(f"[PredictionTab] Prediction error: {error}")
        self.results_label.setText(f"<p style='color: red;'>Prediction failed: {error}</p>")
