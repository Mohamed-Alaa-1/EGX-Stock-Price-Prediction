"""
Disclaimer banner widget.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class DisclaimerBanner(QWidget):
    """Disclaimer banner for application."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        disclaimer_label = QLabel(
            "<b>DISCLAIMER:</b> This tool is for educational and personal use only. "
            "Not financial advice. All predictions are experimental. "
            "Use at your own risk. Always verify data independently."
        )
        disclaimer_label.setWordWrap(True)
        disclaimer_label.setStyleSheet(
            "background-color: #ff6b35; color: white; padding: 8px; border-radius: 4px; font-size: 11px;"
        )
        disclaimer_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(disclaimer_label)
        self.setLayout(layout)
        self.setMaximumHeight(60)
