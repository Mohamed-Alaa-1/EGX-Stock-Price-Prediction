"""
Web bridge for chart communication.
"""

from PySide6.QtCore import QObject, Signal
import json


class ChartBridge(QObject):
    """Bridge between Qt and web chart via runJavaScript."""

    chart_ready = Signal()

    def __init__(self):
        super().__init__()
        self._ready = False
        self._pending_data: dict | None = None
        self._page = None

    def mark_ready(self, page):
        """Mark the chart page as ready (called after loadFinished)."""
        self._ready = True
        self._page = page
        print("[ChartBridge] Page loaded, bridge is ready")
        self.chart_ready.emit()
        # Flush any data that was queued before the page finished loading
        if self._pending_data is not None:
            print("[ChartBridge] Flushing pending chart data")
            self._send_to_page(self._pending_data)
            self._pending_data = None

    def is_ready(self) -> bool:
        return self._ready

    def update_chart(self, page, data: dict):
        """
        Update chart with new data.

        If the page hasn't finished loading yet the data is stored and
        will be sent automatically once loadFinished fires.
        """
        self._page = page
        if not self._ready:
            print("[ChartBridge] Page not ready yet, buffering data")
            self._pending_data = data
            return
        self._send_to_page(data)

    def toggle_indicator(self, page, indicator: str):
        """Toggle indicator visibility."""
        self._page = page
        if not self._ready:
            print(f"[ChartBridge] Page not ready, ignoring toggle({indicator})")
            return
        js_code = f"window.toggleIndicator('{indicator}');"
        page.runJavaScript(js_code)

    def _send_to_page(self, data: dict):
        """Actually push data into the web view."""
        json_data = json.dumps(data, default=str)
        js_code = f"window.updateChart({json_data});"
        print(f"[ChartBridge] runJavaScript(updateChart) for {data.get('symbol', '?')}")
        self._page.runJavaScript(js_code)
