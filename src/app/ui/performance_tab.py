"""
Performance review tab – read-only dashboard displaying journal metrics.

References:
    specs/001-investment-assistant/spec.md  (FR-011, FR-012)
    specs/001-investment-assistant/data-model.md  (PerformanceSummary)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.portfolio_tracker import PortfolioTracker


class PerformanceTab(QWidget):
    """Read-only performance overview built from the trade journal."""

    def __init__(self) -> None:
        super().__init__()
        self._tracker = PortfolioTracker()
        self._init_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # Header row
        header = QHBoxLayout()
        title = QLabel("Performance Review")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 6px;")
        header.addWidget(title)
        header.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        # Summary card
        summary_group = QGroupBox("Overall Summary")
        summary_layout = QVBoxLayout()

        self.summary_label = QLabel("No trades recorded yet.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.summary_label.setStyleSheet("font-size: 14px; padding: 10px;")
        summary_layout.addWidget(self.summary_label)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Open positions
        open_group = QGroupBox("Open Positions")
        open_layout = QVBoxLayout()

        self.open_positions_text = QTextEdit()
        self.open_positions_text.setReadOnly(True)
        self.open_positions_text.setPlaceholderText("No open positions")
        open_layout.addWidget(self.open_positions_text)

        open_group.setLayout(open_layout)
        layout.addWidget(open_group)

        # Warnings
        self.warnings_label = QLabel("")
        self.warnings_label.setWordWrap(True)
        self.warnings_label.setStyleSheet("color: orange; font-size: 12px; padding: 4px;")
        layout.addWidget(self.warnings_label)

        layout.addStretch()
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload performance summary and open positions from the journal."""
        try:
            ps = self._tracker.get_performance_summary()

            parts: list[str] = []
            parts.append(f"<b>Closed trades:</b> {ps.closed_trade_count}")
            parts.append(f"<b>Open trades:</b> {ps.open_trade_count}")
            if ps.win_rate is not None:
                parts.append(f"<b>Win rate:</b> {ps.win_rate * 100:.1f}%")
            if ps.avg_return_pct is not None:
                parts.append(f"<b>Avg return:</b> {ps.avg_return_pct:.2f}%")
            if ps.stop_loss_hit_rate is not None:
                parts.append(f"<b>Stop-loss hit rate:</b> {ps.stop_loss_hit_rate * 100:.1f}%")
            self.summary_label.setText("<br/>".join(parts) if parts else "No trades recorded yet.")

            # Warnings
            if ps.warnings:
                self.warnings_label.setText("⚠ " + " | ".join(ps.warnings))
            else:
                self.warnings_label.setText("")

            # Open positions
            open_pos = self._tracker.get_open_positions()
            if open_pos:
                lines = []
                for p in open_pos:
                    lines.append(
                        f"<b>{p['symbol']}</b> {p['side']} @ {p['price']:.2f} "
                        f"(opened {p.get('created_at', '?')})"
                    )
                self.open_positions_text.setHtml("<br/>".join(lines))
            else:
                self.open_positions_text.clear()

        except Exception as exc:
            self.summary_label.setText(f"<span style='color:red;'>Error: {exc}</span>")
