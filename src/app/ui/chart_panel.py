"""
Chart panel widget with interactive indicators.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QGroupBox,
    QComboBox,
    QLabel,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import QUrl
from pathlib import Path
from typing import Optional

from app.ui.web_bridge import ChartBridge
from core.schemas import PriceSeries
from core.indicators import calculate_rsi, calculate_macd, calculate_ema
from core.support_resistance import find_support_resistance_levels
from services.price_service import PriceService


class ChartPanel(QWidget):
    """Chart panel with TradingView-like interface."""
    
    def __init__(self):
        super().__init__()
        self.bridge = ChartBridge()
        self._current_symbol: Optional[str] = None
        self._current_interval: str = "1d"
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Top bar: Timeframe + Indicator toggles
        top_bar = QHBoxLayout()
        
        # Timeframe selector
        tf_label = QLabel("Timeframe:")
        top_bar.addWidget(tf_label)
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItem("1 Day", "1d")
        self.timeframe_combo.addItem("1 Week", "1wk")
        self.timeframe_combo.addItem("1 Month", "1mo")
        self.timeframe_combo.setCurrentIndex(0)
        self.timeframe_combo.currentIndexChanged.connect(self._on_timeframe_changed)
        top_bar.addWidget(self.timeframe_combo)
        
        top_bar.addSpacing(20)
        
        # Indicator toggles
        self.rsi_checkbox = QCheckBox("RSI")
        self.rsi_checkbox.stateChanged.connect(lambda: self._toggle_indicator("rsi"))
        top_bar.addWidget(self.rsi_checkbox)
        
        self.macd_checkbox = QCheckBox("MACD")
        self.macd_checkbox.stateChanged.connect(lambda: self._toggle_indicator("macd"))
        top_bar.addWidget(self.macd_checkbox)
        
        self.ema_checkbox = QCheckBox("EMA")
        self.ema_checkbox.stateChanged.connect(lambda: self._toggle_indicator("ema"))
        top_bar.addWidget(self.ema_checkbox)
        
        self.sr_checkbox = QCheckBox("Support/Resistance")
        self.sr_checkbox.stateChanged.connect(lambda: self._toggle_indicator("support_resistance"))
        top_bar.addWidget(self.sr_checkbox)
        
        top_bar.addStretch()
        layout.addLayout(top_bar)
        
        # Web view for chart
        self.web_view = QWebEngineView()
        
        # Allow the local HTML file to load scripts from the CDN
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        
        # Detect when the page (and Plotly) has finished loading
        self.web_view.loadFinished.connect(self._on_page_load_finished)
        
        # Load chart template
        template_path = Path(__file__).parent / "chart_template.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(template_path)))
        
        layout.addWidget(self.web_view)
        self.setLayout(layout)
    
    def _on_page_load_finished(self, ok: bool):
        """Called when the WebEngine page finishes loading."""
        if ok:
            print("[ChartPanel] Page loaded successfully")
            self.bridge.mark_ready(self.web_view.page())
        else:
            print("[ChartPanel] WARNING: Page failed to load")
    
    def _toggle_indicator(self, indicator: str):
        """Toggle indicator visibility."""
        self.bridge.toggle_indicator(self.web_view.page(), indicator)
    
    def load_series(self, series: PriceSeries):
        """
        Load price series into chart.
        
        Args:
            series: Price series to display
        """
        print(f"[ChartPanel] load_series({series.symbol}, {len(series.bars)} bars)")
        
        # Prepare data (sorted by date)
        sorted_bars = sorted(series.bars, key=lambda b: b.date)
        dates = [bar.date.isoformat() for bar in sorted_bars]
        open_prices = [bar.open for bar in sorted_bars]
        high_prices = [bar.high for bar in sorted_bars]
        low_prices = [bar.low for bar in sorted_bars]
        close_prices = [bar.close for bar in sorted_bars]
        
        # Calculate indicators
        try:
            rsi = calculate_rsi(series)
            print(f"[ChartPanel] RSI calculated: {len(rsi) if rsi is not None else 'None'} values")
        except Exception as e:
            print(f"[ChartPanel] RSI error: {e}")
            rsi = None

        try:
            macd_line, signal_line, histogram = calculate_macd(series)
            print(f"[ChartPanel] MACD calculated: {len(macd_line)} values")
        except Exception as e:
            print(f"[ChartPanel] MACD error: {e}")
            macd_line = signal_line = histogram = None

        try:
            ema = calculate_ema(series)
            print(f"[ChartPanel] EMA calculated: {len(ema) if ema is not None else 'None'} values")
        except Exception as e:
            print(f"[ChartPanel] EMA error: {e}")
            ema = None

        try:
            sr_levels = find_support_resistance_levels(series)
            print(f"[ChartPanel] S/R levels: {len(sr_levels)} found")
        except Exception as e:
            print(f"[ChartPanel] S/R error: {e}")
            sr_levels = []
        
        # Prepare chart data
        data = {
            "symbol": series.symbol,
            "dates": dates,
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "rsi": rsi.tolist() if rsi is not None else None,
            "macd": {
                "macd": macd_line.tolist() if macd_line is not None else [],
                "signal": signal_line.tolist() if signal_line is not None else [],
                "histogram": histogram.tolist() if histogram is not None else [],
            },
            "ema": ema.tolist() if ema is not None else None,
            "sr_levels": [{"price": lvl.price, "type": lvl.type, "strength": lvl.strength} for lvl in sr_levels],
        }
        
        print(f"[ChartPanel] Sending data to web view")
        # Send to chart
        self.bridge.update_chart(self.web_view.page(), data)

    def set_symbol(self, symbol: str):
        """Store the current symbol for timeframe switching."""
        self._current_symbol = symbol

    def get_interval(self) -> str:
        """Return the currently selected interval value."""
        return self.timeframe_combo.currentData() or "1d"

    def _on_timeframe_changed(self, index: int):
        """Handle timeframe combo change — re-fetch and re-render chart."""
        new_interval = self.timeframe_combo.itemData(index)
        if not new_interval or not self._current_symbol:
            return
        
        self._current_interval = new_interval
        print(f"[ChartPanel] Timeframe changed to {new_interval} for {self._current_symbol}")
        
        try:
            price_service = PriceService()
            series = price_service.get_series(
                self._current_symbol, use_cache=False, interval=new_interval,
            )
            self.load_series(series)
        except Exception as e:
            print(f"[ChartPanel] Error re-fetching for timeframe {new_interval}: {e}")

    def set_timeframe_options(self, options: list[tuple[str, str]]):
        """
        Replace timeframe combo items.
        
        Args:
            options: List of (display_text, data_value) tuples
        """
        self.timeframe_combo.blockSignals(True)
        self.timeframe_combo.clear()
        for label, value in options:
            self.timeframe_combo.addItem(label, value)
        self.timeframe_combo.setCurrentIndex(0)
        self.timeframe_combo.blockSignals(False)
