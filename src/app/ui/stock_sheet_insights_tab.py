"""
Stock Sheet Insights tab — batch training and analysis for all stocks.

Provides a "Train + Analyze Sheet (Force Refresh)" workflow that:
- Fetches fresh data for all stocks in the sheet (no-cache by default)
- Optionally trains/updates models per stock
- Computes Buy/Sell/Hold recommendations for each stock
- Isolates per-stock failures without interrupting the batch
"""

from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QMessageBox,
)

from core.schemas import InsightStatus, StockInsight
from services.stock_sheet_insights_service import StockSheetInsightsService


class BatchWorker(QThread):
    """Background worker for batch insights computation."""

    progress = Signal(int, int, str)  # current, total, symbol
    finished = Signal(object)  # InsightBatchRun
    error = Signal(str)

    def __init__(
        self,
        service: StockSheetInsightsService,
        forecast_method: str,
        train_models: bool,
        force_refresh: bool,
    ):
        super().__init__()
        self.service = service
        self.forecast_method = forecast_method
        self.train_models = train_models
        self.force_refresh = force_refresh

    def run(self):
        """Run batch insights in background."""
        try:
            result = self.service.run_batch_insights(
                symbols=None,
                forecast_method=self.forecast_method,
                train_models=self.train_models,
                force_refresh=self.force_refresh,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class StockSheetInsightsTab(QWidget):
    """Stock Sheet Insights UI tab."""

    def __init__(self) -> None:
        super().__init__()
        self.service = StockSheetInsightsService()
        self.current_results: list[StockInsight] = []
        self.worker: BatchWorker | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI layout."""
        layout = QVBoxLayout()

        # Header
        header = QLabel("Stock Sheet Investment Insights")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 6px;")
        layout.addWidget(header)

        # Controls group
        controls_group = QGroupBox("Batch Actions")
        controls_layout = QHBoxLayout()

        self.train_analyze_btn = QPushButton("🚀 Train + Analyze Sheet (Force Refresh)")
        self.train_analyze_btn.setToolTip(
            "Fetch fresh data, train models, and compute recommendations for all stocks"
        )
        self.train_analyze_btn.clicked.connect(self._on_train_analyze_clicked)
        controls_layout.addWidget(self.train_analyze_btn)

        self.refresh_btn = QPushButton("🔄 Refresh Insights (No Training)")
        self.refresh_btn.setToolTip("Recompute recommendations without training (faster)")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        controls_layout.addWidget(self.refresh_btn)

        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Progress label
        self.progress_label = QLabel("Ready")
        self.progress_label.setStyleSheet("padding: 4px; color: #666;")
        layout.addWidget(self.progress_label)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Action", "Conviction", "Stop-Loss", "Target", "Status", "Reason", "As-Of"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table)

        # Detail panel (initially hidden)
        self.detail_panel = QTextEdit()
        self.detail_panel.setReadOnly(True)
        self.detail_panel.setMaximumHeight(200)
        self.detail_panel.setVisible(False)
        layout.addWidget(self.detail_panel)

        # Empty state label
        self.empty_state = QLabel(
            "No insights yet.\n\n"
            "Click 'Train + Analyze Sheet (Force Refresh)' to compute recommendations\n"
            "for all stocks in your stock sheet."
        )
        self.empty_state.setAlignment(Qt.AlignCenter)
        self.empty_state.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
        layout.addWidget(self.empty_state)

        self.setLayout(layout)
        self._update_empty_state()

    def _update_empty_state(self):
        """Show/hide empty state based on results."""
        has_results = self.table.rowCount() > 0
        self.table.setVisible(has_results)
        self.empty_state.setVisible(not has_results)

    def _on_train_analyze_clicked(self):
        """Handle Train + Analyze button click."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Batch Running", "A batch run is already in progress.")
            return

        self._start_batch(train_models=True)

    def _on_refresh_clicked(self):
        """Handle Refresh button click (no training)."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Batch Running", "A batch run is already in progress.")
            return

        self._start_batch(train_models=False)

    def _start_batch(self, train_models: bool):
        """Start a batch insights run."""
        # Check symbol count for performance warning
        from services.stock_universe_manager import StockUniverseManager
        universe_mgr = StockUniverseManager()
        symbols = universe_mgr.list_symbols()
        
        # T024: Performance safeguard for large sheets
        if len(symbols) > 50:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                self,
                "Large Sheet Warning",
                f"Your stock sheet contains {len(symbols)} symbols.\n\n"
                "Processing may take several minutes and will fetch data + train models for each stock.\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Disable buttons
        self.train_analyze_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress_label.setText(f"Starting batch run for {len(symbols)} symbols...")

        # Clear previous results
        self.table.setRowCount(0)
        self.current_results = []
        self.detail_panel.setVisible(False)
        self._update_empty_state()

        # Start worker thread
        self.worker = BatchWorker(
            service=self.service,
            forecast_method="ml",
            train_models=train_models,
            force_refresh=True,
        )
        self.worker.finished.connect(self._on_batch_finished)
        self.worker.error.connect(self._on_batch_error)
        self.worker.start()

    def _on_batch_finished(self, result):
        """Handle batch completion."""
        self.current_results = result.results

        # Populate table
        self.table.setRowCount(len(result.results))
        for i, insight in enumerate(result.results):
            self.table.setItem(i, 0, QTableWidgetItem(insight.symbol))
            
            # Action (colored)
            action_item = QTableWidgetItem(insight.action.value.upper())
            if insight.action.value == "buy":
                action_item.setForeground(Qt.darkGreen)
            elif insight.action.value == "sell":
                action_item.setForeground(Qt.darkRed)
            self.table.setItem(i, 1, action_item)

            self.table.setItem(i, 2, QTableWidgetItem(str(insight.conviction)))

            # Stop-Loss (N/A for HOLD)
            stop_loss_text = "N/A" if insight.stop_loss is None else f"{insight.stop_loss:.2f}"
            self.table.setItem(i, 3, QTableWidgetItem(stop_loss_text))

            # Target (N/A for HOLD)
            target_text = "N/A" if insight.target_exit is None else f"{insight.target_exit:.2f}"
            self.table.setItem(i, 4, QTableWidgetItem(target_text))

            # Status
            status_item = QTableWidgetItem(insight.status.value)
            if insight.status == InsightStatus.HOLD_FALLBACK:
                status_item.setForeground(Qt.darkYellow)
            elif insight.status == InsightStatus.ERROR:
                status_item.setForeground(Qt.darkRed)
            self.table.setItem(i, 5, status_item)

            # Reason
            reason_text = insight.status_reason or ""
            if insight.used_cache_fallback:
                reason_text = f"[Cache fallback] {reason_text}"
            self.table.setItem(i, 6, QTableWidgetItem(reason_text))

            # As-Of
            self.table.setItem(i, 7, QTableWidgetItem(str(insight.as_of_date)))

        # Update progress label with summary
        summary = result.summary
        self.progress_label.setText(
            f"Batch complete: {summary['total']} stocks | "
            f"✓ {summary['ok']} OK | "
            f"⚠ {summary['hold_fallback']} Fallback | "
            f"✗ {summary['error']} Error | "
            f"Computed at {result.computed_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Re-enable buttons
        self.train_analyze_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)

        self._update_empty_state()

    def _on_batch_error(self, error_msg: str):
        """Handle batch error."""
        self.progress_label.setText(f"Error: {error_msg}")
        self.train_analyze_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        QMessageBox.critical(self, "Batch Error", f"Batch run failed:\n{error_msg}")

    def _on_row_selected(self):
        """Handle row selection to show details."""
        selected = self.table.selectedItems()
        if not selected:
            self.detail_panel.setVisible(False)
            return

        row = selected[0].row()
        if row < 0 or row >= len(self.current_results):
            return

        insight = self.current_results[row]
        self._show_details(insight)

    def _show_details(self, insight: StockInsight):
        """Show detailed view for selected insight."""
        details = []
        details.append(f"<h3>{insight.symbol} — Detailed Insight</h3>")
        details.append(f"<p><b>As of:</b> {insight.as_of_date} | <b>Computed:</b> {insight.computed_at.strftime('%Y-%m-%d %H:%M:%S')}</p>")
        
        # Assistant Recommendation
        details.append("<h4>📊 Assistant Recommendation</h4>")
        details.append(f"<p><b>Action:</b> {insight.action.value.upper()}</p>")
        details.append(f"<p><b>Conviction:</b> {insight.conviction}/100</p>")
        if insight.stop_loss:
            details.append(f"<p><b>Stop-Loss:</b> {insight.stop_loss:.2f}</p>")
        if insight.target_exit:
            details.append(f"<p><b>Target Exit:</b> {insight.target_exit:.2f}</p>")
        if insight.entry_zone_lower and insight.entry_zone_upper:
            details.append(f"<p><b>Entry Zone:</b> {insight.entry_zone_lower:.2f} - {insight.entry_zone_upper:.2f}</p>")
        details.append(f"<p><b>Logic:</b> {insight.logic_summary}</p>")

        # Evidence (if available in assistant_recommendation)
        if insight.assistant_recommendation and "evidence" in insight.assistant_recommendation:
            evidence = insight.assistant_recommendation["evidence"]
            details.append("<h4>📋 Evidence</h4>")
            bullish = [e for e in evidence if e.get("direction") == "bullish"]
            bearish = [e for e in evidence if e.get("direction") == "bearish"]
            neutral = [e for e in evidence if e.get("direction") == "neutral"]
            
            if bullish:
                details.append("<p><b>Bullish signals:</b></p><ul>")
                for e in bullish:
                    details.append(f"<li>{e.get('label', 'N/A')}: {e.get('summary', 'N/A')}</li>")
                details.append("</ul>")
            if bearish:
                details.append("<p><b>Bearish signals:</b></p><ul>")
                for e in bearish:
                    details.append(f"<li>{e.get('label', 'N/A')}: {e.get('summary', 'N/A')}</li>")
                details.append("</ul>")
            if neutral:
                details.append("<p><b>Neutral signals:</b></p><ul>")
                for e in neutral:
                    details.append(f"<li>{e.get('label', 'N/A')}: {e.get('summary', 'N/A')}</li>")
                details.append("</ul>")

        # Raw Outputs (separate section)
        details.append("<h4>🔧 Raw Outputs</h4>")
        if insight.raw_outputs and insight.raw_outputs.get("forecast"):
            forecast = insight.raw_outputs["forecast"]
            details.append(f"<p><b>Forecast Method:</b> {forecast.get('method', 'N/A')}</p>")
            details.append(f"<p><b>Predicted Price:</b> {forecast.get('predicted_price', 'N/A')}</p>")
        else:
            details.append("<p>No raw forecast data available.</p>")

        self.detail_panel.setHtml("".join(details))
        self.detail_panel.setVisible(True)

