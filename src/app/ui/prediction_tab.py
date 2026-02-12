"""
Prediction tab UI component.
"""


from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.chart_panel import ChartPanel
from app.ui.stock_selector import StockSelectorWidget
from core.momentum import calculate_momentum, get_momentum_signal
from core.schemas import BacktestStrategy, ForecastMethod, ForecastResult
from services.backtest_service import BacktestService
from services.gdr_bridge_service import GdrBridgeService, list_mapped_symbols
from services.model_registry import get_registry
from services.model_staleness import get_staleness_message
from services.prediction_service import PredictionService
from services.price_service import PriceService


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
            print(
                f"[PredictionWorker] Starting prediction: "
                f"{self.symbol}, method={self.method.value}"
            )
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

        # Backtest controls (US2)
        backtest_group = QGroupBox("Backtest")
        backtest_layout = QVBoxLayout()

        # Strategy selector
        strat_row = QHBoxLayout()
        strat_row.addWidget(QLabel("Strategy:"))
        self.backtest_strategy_combo = QComboBox()
        self.backtest_strategy_combo.addItems(["RSI", "MACD", "EMA"])
        strat_row.addWidget(self.backtest_strategy_combo)
        backtest_layout.addLayout(strat_row)

        # Run button
        self.backtest_button = QPushButton("Run Backtest")
        self.backtest_button.clicked.connect(self._on_run_backtest)
        backtest_layout.addWidget(self.backtest_button)

        # Results area
        self.backtest_output = QTextEdit()
        self.backtest_output.setReadOnly(True)
        self.backtest_output.setMaximumHeight(150)
        self.backtest_output.setPlaceholderText("Backtest results will appear here")
        backtest_layout.addWidget(self.backtest_output)

        backtest_group.setLayout(backtest_layout)
        controls_layout.addWidget(backtest_group)

        # GDR Premium/Discount (US3)
        gdr_group = QGroupBox("GDR Premium/Discount")
        gdr_layout = QVBoxLayout()

        self.gdr_button = QPushButton("Compute Premium/Discount")
        self.gdr_button.clicked.connect(self._on_gdr_compute)
        gdr_layout.addWidget(self.gdr_button)

        self.gdr_status_label = QLabel("Select a cross-listed stock")
        self.gdr_status_label.setWordWrap(True)
        gdr_layout.addWidget(self.gdr_status_label)

        gdr_group.setLayout(gdr_layout)
        controls_layout.addWidget(gdr_group)

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
            print(
                f"[PredictionTab] Loading chart for {symbol}"
                f" ({len(series.bars)} bars, interval={interval})"
            )
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
        print(
            f"[PredictionTab] Prediction finished: "
            f"{result.request.symbol} -> {result.predicted_close:.2f}"
        )

        # Format results
        symbol = result.request.symbol
        target = result.request.target_date
        predicted = result.predicted_close
        method = result.request.method.value

        text = f"<h2>{symbol}</h2>"
        text += f"<p><b>Predicted Close for {target}:</b> {predicted:.2f} EGP</p>"
        text += f"<p>Method: {method}</p>"
        text += f"<p>Generated: {result.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>"

        # Baseline (constitution: show naive alongside model prediction)
        baseline = result.model_features.get("baseline", {})
        if "predicted_close" in baseline:
            text += (
                f"<p><b>Baseline ({baseline.get('method', 'naive')}):</b>"
                f" {baseline['predicted_close']:.2f} EGP</p>"
            )

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

        # Risk companion (VaR + Sharpe) — constitution mandate
        risk = result.model_features.get("risk", {})
        if "error" in risk:
            text += f"<p style='color: orange;'>Risk metrics error: {risk['error']}</p>"
        elif risk:
            text += "<hr/><b>Risk Companion</b>"
            if risk.get("var_95_pct") is not None:
                text += f"<p>1-Day VaR (95%): {risk['var_95_pct']*100:.2f}%"
                if risk.get("var_95_abs") is not None:
                    text += f" ({risk['var_95_abs']:.2f} EGP)"
                text += "</p>"
                text += f"<p>1-Day VaR (99%): {risk['var_99_pct']*100:.2f}%"
                if risk.get("var_99_abs") is not None:
                    text += f" ({risk['var_99_abs']:.2f} EGP)"
                text += "</p>"
            else:
                for w in risk.get("warnings", []):
                    text += f"<p style='color: orange;'>⚠ {w}</p>"

            if risk.get("sharpe") is not None:
                text += f"<p>Sharpe Ratio: {risk['sharpe']:.3f}</p>"

            text += f"<p><small>Method: {risk.get('var_method', '?')}, "
            text += f"Lookback: {risk.get('lookback_days', '?')} days, "
            text += f"Returns: {risk.get('return_type', '?')}, "
            text += f"Risk-free rate: {risk.get('risk_free_rate', 0)}</small></p>"

        # Statistical validation (ADF + Hurst)
        validation = result.model_features.get("validation", {})
        if "error" in validation:
            text += f"<p style='color: orange;'>Validation error: {validation['error']}</p>"
        elif validation:
            text += "<hr/><b>Signal Validation</b>"
            if validation.get("adf_pvalue") is not None:
                text += f"<p>ADF p-value: {validation['adf_pvalue']:.4f}"
                if validation["adf_pvalue"] <= 0.05:
                    text += " ✓ (stationary)"
                else:
                    text += " ⚠ (non-stationary)"
                text += "</p>"
            else:
                text += "<p style='color: orange;'>⚠ Insufficient data for ADF test</p>"

            if validation.get("hurst") is not None:
                regime = validation.get("hurst_regime", "?")
                text += f"<p>Hurst: {validation['hurst']:.3f} ({regime})</p>"
            else:
                text += "<p style='color: orange;'>⚠ Insufficient data for Hurst exponent</p>"

            for w in validation.get("warnings", []):
                text += f"<p style='color: orange;'>⚠ {w}</p>"

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

    def _on_run_backtest(self):
        """Handle backtest button click."""
        selected = self.stock_selector.get_selected_symbols()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a stock")
            return

        symbol = selected[0]
        strategy_name = self.backtest_strategy_combo.currentText().lower()
        strategy_map = {
            "rsi": BacktestStrategy.RSI,
            "macd": BacktestStrategy.MACD,
            "ema": BacktestStrategy.EMA,
        }
        strategy = strategy_map.get(strategy_name, BacktestStrategy.RSI)

        self.backtest_button.setEnabled(False)
        self.backtest_output.setText("Running backtest...")

        try:
            result = BacktestService.run(symbol=symbol, strategy=strategy)

            lines = [
                f"<b>{symbol} — {strategy.value.upper()} Backtest</b>",
                f"Period: {result.start_date} → {result.end_date}",
                f"Gross Return: {result.gross_total_return * 100:.2f}%",
                f"Net Return: {result.net_total_return * 100:.2f}%",
            ]
            if result.gross_cagr is not None:
                lines.append(f"Gross CAGR: {result.gross_cagr * 100:.2f}%")
            if result.net_cagr is not None:
                lines.append(f"Net CAGR: {result.net_cagr * 100:.2f}%")
            if result.gross_sharpe is not None:
                lines.append(f"Gross Sharpe: {result.gross_sharpe:.3f}")
            if result.net_sharpe is not None:
                lines.append(f"Net Sharpe: {result.net_sharpe:.3f}")
            if result.max_drawdown is not None:
                lines.append(f"Max Drawdown: {result.max_drawdown * 100:.2f}%")
            lines.append(f"Trades: {result.trade_count}")
            if result.total_costs_paid is not None:
                lines.append(f"Total Costs: {result.total_costs_paid * 100:.4f}%")

            cm = result.cost_model
            lines.append(
                f"<small>Costs: {cm.commission_bps}bp commission"
                f" + {cm.stamp_duty_bps}bp stamp duty</small>"
            )

            for w in result.warnings:
                lines.append(f"<span style='color: orange;'>⚠ {w}</span>")

            self.backtest_output.setHtml("<br/>".join(lines))

        except Exception as e:
            self.backtest_output.setHtml(f"<span style='color: red;'>Backtest failed: {e}</span>")

        self.backtest_button.setEnabled(True)

    def _on_gdr_compute(self):
        """Compute and display GDR premium/discount for selected stock."""
        selected = self.stock_selector.get_selected_symbols()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a stock")
            return

        symbol = selected[0]
        mapped = list_mapped_symbols()

        if symbol.upper() not in [s.upper() for s in mapped]:
            self.gdr_status_label.setText(
                f"<span style='color: orange;'>{symbol} has no cross-listing mapping. "
                f"Mapped: {', '.join(mapped) if mapped else 'none'}</span>"
            )
            return

        self.gdr_button.setEnabled(False)
        self.gdr_status_label.setText("Computing...")

        try:
            result = GdrBridgeService.compute(symbol)

            if result.warnings and not result.points:
                self.gdr_status_label.setText(
                    f"<span style='color: orange;'>⚠ {'; '.join(result.warnings)}</span>"
                )
            elif result.points:
                last = result.points[-1]
                status = f"<b>Last:</b> {last.value:+.2f}% ({last.date})"
                if result.warnings:
                    status += (
                        "<br/><span style='color: orange;'>"
                        f"⚠ {'; '.join(result.warnings)}</span>"
                    )
                self.gdr_status_label.setText(status)

                # Overlay on chart
                self.chart_panel.load_premium_discount(result)
            else:
                self.gdr_status_label.setText("No data points computed")

        except Exception as e:
            self.gdr_status_label.setText(
                f"<span style='color: red;'>Error: {e}</span>"
            )

        self.gdr_button.setEnabled(True)

    def _on_prediction_error(self, error: str):
        """Handle prediction error."""
        self.predict_button.setEnabled(True)
        print(f"[PredictionTab] Prediction error: {error}")
        self.results_label.setText(f"<p style='color: red;'>Prediction failed: {error}</p>")
