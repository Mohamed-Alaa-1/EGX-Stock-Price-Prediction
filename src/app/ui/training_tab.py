"""
Training tab UI component.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QGroupBox,
    QListWidget,
    QMessageBox,
    QRadioButton,
    QButtonGroup,
)
from PySide6.QtCore import Qt, QThread, Signal
from datetime import datetime
from typing import Optional

from core.schemas import ModelArtifact, PriceSeries
from ml.config import TrainingConfig
from services.training_service import TrainingService
from services.model_registry import get_registry
from services.model_staleness import get_staleness_message
from data.providers.registry import get_provider_registry
from app.ui.stock_selector import StockSelectorWidget


class TrainingWorker(QThread):
    """Background training worker."""

    progress = Signal(str)
    finished = Signal(ModelArtifact)
    error = Signal(str)

    def __init__(
        self,
        mode: str,
        symbol: Optional[str],
        symbols: Optional[list[str]],
        series: Optional[PriceSeries],
        series_by_symbol: Optional[dict[str, PriceSeries]],
        config: TrainingConfig,
    ):
        super().__init__()
        self.mode = mode
        self.symbol = symbol
        self.symbols = symbols
        self.series = series
        self.series_by_symbol = series_by_symbol
        self.config = config

    def run(self):
        """Execute training."""
        try:
            def callback(*args):
                if len(args) == 3:
                    if isinstance(args[2], (int, float)):
                        msg = f"Epoch {args[0]}/{args[1]}, val_loss={args[2]:.4f}"
                    else:
                        msg = f"Round {args[0]}/{args[1]}, training {args[2]}..."
                else:
                    msg = f"Epoch {args[0]}/{args[1]}"
                self.progress.emit(msg)

            if self.mode == "per_stock":
                artifact = TrainingService.train_per_stock(
                    self.symbol,
                    self.series,
                    self.config,
                    callback,
                )
            else:
                artifact = TrainingService.train_federated(
                    self.symbols,
                    self.series_by_symbol,
                    self.config,
                    callback,
                )

            self.finished.emit(artifact)

        except Exception as e:
            self.error.emit(str(e))


class TrainingTab(QWidget):
    """Training tab widget."""

    def __init__(self):
        super().__init__()
        self.worker: Optional[TrainingWorker] = None
        self._init_ui()
        self._refresh_model_list()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()

        # Training mode selection
        mode_group = QGroupBox("Training Mode")
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()
        self.per_stock_radio = QRadioButton("Per-Stock (individual model)")
        self.federated_radio = QRadioButton("Federated (multi-stock model)")
        self.per_stock_radio.setChecked(True)

        self.mode_group.addButton(self.per_stock_radio, 0)
        self.mode_group.addButton(self.federated_radio, 1)

        mode_layout.addWidget(self.per_stock_radio)
        mode_layout.addWidget(self.federated_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Stock selection
        stock_group = QGroupBox("Stock Selection")
        stock_layout = QVBoxLayout()

        self.stock_selector = StockSelectorWidget(allow_multiple=True)
        stock_layout.addWidget(self.stock_selector)

        stock_group.setLayout(stock_layout)
        layout.addWidget(stock_group)

        # Training controls
        controls_layout = QHBoxLayout()

        self.train_button = QPushButton("Train Model")
        self.train_button.clicked.connect(self._on_train)
        controls_layout.addWidget(self.train_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._on_stop)
        controls_layout.addWidget(self.stop_button)

        layout.addLayout(controls_layout)

        # Progress display
        progress_group = QGroupBox("Training Progress")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setMaximumHeight(120)
        progress_layout.addWidget(self.progress_text)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Saved models list
        models_group = QGroupBox("Saved Models")
        models_layout = QVBoxLayout()

        self.models_list = QListWidget()
        self.models_list.itemDoubleClicked.connect(self._on_model_selected)
        models_layout.addWidget(self.models_list)

        models_buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_model_list)
        models_buttons.addWidget(self.refresh_button)

        self.retrain_button = QPushButton("Retrain Selected")
        self.retrain_button.clicked.connect(self._on_retrain)
        models_buttons.addWidget(self.retrain_button)

        models_layout.addLayout(models_buttons)
        models_group.setLayout(models_layout)
        layout.addWidget(models_group)

        self.setLayout(layout)

    def _on_train(self):
        """Handle train button click."""
        mode = "per_stock" if self.per_stock_radio.isChecked() else "federated"

        symbols = self.stock_selector.get_selected_symbols()

        if not symbols:
            QMessageBox.warning(self, "No Selection", "Please select at least one stock")
            return

        if mode == "federated" and len(symbols) < 2:
            QMessageBox.warning(
                self,
                "Insufficient Stocks",
                "Federated training requires at least 2 stocks",
            )
            return

        symbol = symbols[0]

        self._log(f"Starting {mode} training for {', '.join(symbols)}...")

        registry = get_provider_registry()

        try:
            if mode == "per_stock":
                self._log(f"Fetching data for {symbol} (interval=1d)...")
                series = registry.fetch_with_fallback(symbol, interval="1d")
                if series is None:
                    raise ValueError(f"No data available for {symbol}")
                self._log(f"Fetched {len(series.bars)} daily bars for {symbol}")
                series_by_symbol = None
                worker_symbols = None
            else:
                self._log(f"Fetching data for {len(symbols)} stocks (interval=1d)...")
                series_by_symbol = {}
                for sym in symbols:
                    s = registry.fetch_with_fallback(sym, interval="1d")
                    if s is None:
                        self._log(f"WARNING: No data for {sym}, skipping")
                        continue
                    series_by_symbol[sym] = s
                if len(series_by_symbol) < 2:
                    raise ValueError(f"Need at least 2 stocks with data, got {len(series_by_symbol)}")
                series = None
                worker_symbols = list(series_by_symbol.keys())

            self.worker = TrainingWorker(
                mode=mode,
                symbol=symbol if mode == "per_stock" else None,
                symbols=worker_symbols,
                series=series,
                series_by_symbol=series_by_symbol,
                config=TrainingConfig.get_default(),
            )

            self.worker.progress.connect(self._log)
            self.worker.finished.connect(self._on_training_finished)
            self.worker.error.connect(self._on_training_error)

            self.train_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.progress_bar.setVisible(True)

            self.worker.start()

        except Exception as e:
            self._log(f"Error: {e}")
            QMessageBox.critical(self, "Training Error", f"Failed to start training:\n{e}")

    def _on_stop(self):
        """Handle stop button click."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self._log("Training stopped by user")
            self._reset_ui()

    def _on_training_finished(self, artifact: ModelArtifact):
        """Handle training completion."""
        self._log(f"Training complete! Artifact ID: {artifact.artifact_id}")
        self._log(f"Metrics: {artifact.metrics}")
        self._reset_ui()
        self._refresh_model_list()

        QMessageBox.information(
            self,
            "Training Complete",
            f"Model trained successfully!\n\nArtifact ID: {artifact.artifact_id}\nSymbols: {', '.join(artifact.covered_symbols)}",
        )

    def _on_training_error(self, error: str):
        """Handle training error."""
        self._log(f"Training failed: {error}")
        print(f"[TrainingTab] ERROR: {error}")
        import traceback
        traceback.print_exc()
        self._reset_ui()
        QMessageBox.critical(self, "Training Error", f"Training failed:\n{error}")

    def _on_model_selected(self, item):
        """Handle model selection."""
        artifact_id = item.data(Qt.UserRole)
        registry = get_registry()
        artifact = next((a for a in registry.list_all() if a.artifact_id == artifact_id), None)

        if artifact:
            msg = f"Artifact: {artifact.artifact_id}\n"
            msg += f"Type: {artifact.type.value}\n"
            msg += f"Symbols: {', '.join(artifact.covered_symbols)}\n"
            msg += f"Trained: {artifact.last_trained_at.strftime('%Y-%m-%d %H:%M')}\n"
            msg += f"Status: {get_staleness_message(artifact)}\n"
            msg += f"Metrics: {artifact.metrics}"

            QMessageBox.information(self, "Model Details", msg)

    def _on_retrain(self):
        """Handle retrain button click."""
        selected = self.models_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a model to retrain")
            return

        artifact_id = selected.data(Qt.UserRole)
        registry = get_registry()
        artifact = next((a for a in registry.list_all() if a.artifact_id == artifact_id), None)

        if artifact:
            symbols_str = ', '.join(artifact.covered_symbols)
            reply = QMessageBox.question(
                self,
                "Confirm Retrain",
                f"Retrain model for:\n{symbols_str}\n\nThis will replace the existing model.",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                for sym in artifact.covered_symbols:
                    self.stock_selector.select_symbol(sym)
                self._on_train()

    def _refresh_model_list(self):
        """Refresh saved models list."""
        self.models_list.clear()
        registry = get_registry()

        for artifact in registry.list_all():
            symbols_str = ', '.join(artifact.covered_symbols)
            age = (datetime.now() - artifact.last_trained_at).days
            label = f"{symbols_str} ({artifact.type.value}, {age}d ago)"

            self.models_list.addItem(label)
            self.models_list.item(self.models_list.count() - 1).setData(
                Qt.UserRole,
                artifact.artifact_id,
            )

    def _log(self, message: str):
        """Append message to progress log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(f"[TrainingTab] {formatted}")
        self.progress_text.append(formatted)

    def _reset_ui(self):
        """Reset UI after training."""
        self.train_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
