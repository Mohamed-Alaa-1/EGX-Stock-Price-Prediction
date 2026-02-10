"""
Launcher dialog for choosing data provider before app starts.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QPushButton,
    QButtonGroup,
    QGroupBox,
)
from PySide6.QtCore import Qt


class LauncherDialog(QDialog):
    """
    Dialog shown at startup to let the user choose a data provider.

    Options:
      - YFinance (Historical Data): Full historical OHLCV via yfinance
      - TradingView (Real-Time Analysis): Current snapshot via tradingview-ta
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EGX Price Prediction - Select Data Source")
        self.setFixedSize(420, 260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._provider_choice = "yfinance"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Choose Data Provider")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Select the data source to use for stock analysis.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray; margin-bottom: 12px;")
        layout.addWidget(subtitle)

        # Provider options
        group = QGroupBox("Data Source")
        group_layout = QVBoxLayout()

        self.button_group = QButtonGroup(self)

        self.yfinance_radio = QRadioButton("YFinance (Historical Data)")
        self.yfinance_radio.setToolTip(
            "Full historical OHLCV data via Yahoo Finance.\n"
            "Best for chart viewing and model training."
        )
        self.yfinance_radio.setChecked(True)
        self.button_group.addButton(self.yfinance_radio, 0)
        group_layout.addWidget(self.yfinance_radio)

        yf_desc = QLabel("   Full historical daily/weekly/monthly OHLCV candles")
        yf_desc.setStyleSheet("color: gray; font-size: 11px;")
        group_layout.addWidget(yf_desc)

        group_layout.addSpacing(8)

        self.tradingview_radio = QRadioButton("TradingView (Real-Time Analysis)")
        self.tradingview_radio.setToolTip(
            "Real-time technical analysis snapshot via TradingView.\n"
            "Provides current price and TA recommendations."
        )
        self.button_group.addButton(self.tradingview_radio, 1)
        group_layout.addWidget(self.tradingview_radio)

        tv_desc = QLabel("   Current price snapshot + technical analysis signals")
        tv_desc.setStyleSheet("color: gray; font-size: 11px;")
        group_layout.addWidget(tv_desc)

        group.setLayout(group_layout)
        layout.addWidget(group)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.ok_button = QPushButton("Launch")
        self.ok_button.setDefault(True)
        self.ok_button.setFixedWidth(100)
        self.ok_button.clicked.connect(self._on_launch)
        btn_layout.addWidget(self.ok_button)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_launch(self):
        if self.tradingview_radio.isChecked():
            self._provider_choice = "tradingview"
        else:
            self._provider_choice = "yfinance"
        self.accept()

    def get_provider_choice(self) -> str:
        """Return the selected provider: 'yfinance' or 'tradingview'."""
        return self._provider_choice
