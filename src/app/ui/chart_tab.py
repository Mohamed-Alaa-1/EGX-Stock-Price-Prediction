"""
Chart tab – dedicated full-size chart viewer.

Moved out of the Strategy tab so the controls panel has room to breathe.
The chart still reacts to stock-selection signals emitted by the Strategy tab.
"""

from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from app.ui.chart_panel import ChartPanel
from services.price_service import PriceService


class ChartTab(QWidget):
    """Full-width interactive chart tab."""

    def __init__(self) -> None:
        super().__init__()
        self.chart_panel = ChartPanel()
        self._current_symbol: str | None = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._header = QLabel("Select a stock in the Strategy tab to load a chart")
        self._header.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 6px;"
        )
        layout.addWidget(self._header)
        layout.addWidget(self.chart_panel)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Public API – called from main.py when strategy tab selects a stock
    # ------------------------------------------------------------------

    def load_symbol(self, symbol: str) -> None:
        """Load chart data for *symbol*."""
        self._current_symbol = symbol
        self._header.setText(f"Chart: {symbol}")
        try:
            self.chart_panel.set_symbol(symbol)
            interval = self.chart_panel.get_interval()
            price_service = PriceService()
            series = price_service.get_series(symbol, interval=interval)
            self.chart_panel.load_series(series)
        except Exception as e:
            QMessageBox.warning(
                self, "Chart Error", f"Failed to load chart data:\n{e}"
            )

    def load_premium_discount(self, result) -> None:
        """Overlay GDR premium/discount on the chart."""
        self.chart_panel.load_premium_discount(result)
