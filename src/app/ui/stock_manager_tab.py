"""
Stock Manager tab — add/remove stocks from the universe.

Allows users to:
- View all stocks in the CSV
- Remove selected stocks
- Add new stocks with yfinance validation
- Changes persist immediately to egx_stocks.csv
"""

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data.stock_universe import load_stock_universe
from services.stock_universe_manager import StockUniverseManager


class StockManagerTab(QWidget):
    """Stock universe management interface."""

    def __init__(self) -> None:
        super().__init__()
        self._manager = StockUniverseManager()
        self._init_ui()
        self._refresh_table()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Stock Universe Manager")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 6px;")
        layout.addWidget(header)

        # ── Stock List ────────────────────────────────────────────────
        list_group = QGroupBox("Current Stocks")
        list_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Symbol", "Company Name", "Sector"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 350)
        list_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self._on_remove)
        btn_row.addWidget(self.remove_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_table)
        btn_row.addWidget(self.refresh_button)
        btn_row.addStretch()

        list_layout.addLayout(btn_row)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # ── Add New Stock ─────────────────────────────────────────────
        add_group = QGroupBox("Add New Stock")
        add_layout = QVBoxLayout()

        # Symbol input
        symbol_row = QHBoxLayout()
        symbol_row.addWidget(QLabel("Symbol:"))
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g., COMI.CA or AAPL")
        self.symbol_input.setMaximumWidth(200)
        symbol_row.addWidget(self.symbol_input)

        self.validate_button = QPushButton("Validate with yfinance")
        self.validate_button.clicked.connect(self._on_validate)
        symbol_row.addWidget(self.validate_button)
        symbol_row.addStretch()
        add_layout.addLayout(symbol_row)

        # Company name (auto-filled after validation)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Company:"))
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Auto-filled after validation")
        self.company_input.setReadOnly(True)
        name_row.addWidget(self.company_input)
        add_layout.addLayout(name_row)

        # Sector input
        sector_row = QHBoxLayout()
        sector_row.addWidget(QLabel("Sector:"))
        self.sector_input = QLineEdit()
        self.sector_input.setPlaceholderText("e.g., Banking & Financial Services")
        sector_row.addWidget(self.sector_input)
        add_layout.addLayout(sector_row)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 4px;")
        add_layout.addWidget(self.status_label)

        # Add button
        add_btn_row = QHBoxLayout()
        self.add_button = QPushButton("Add to Universe")
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self._on_add)
        add_btn_row.addWidget(self.add_button)
        add_btn_row.addStretch()
        add_layout.addLayout(add_btn_row)

        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        layout.addStretch()
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Table Management
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        """Reload stocks from CSV and populate the table."""
        # Clear cache to get fresh data
        load_stock_universe.cache_clear()
        stocks = self._manager.load_all()

        self.table.setRowCount(len(stocks))
        for i, stock in enumerate(stocks):
            self.table.setItem(i, 0, QTableWidgetItem(stock.symbol))
            self.table.setItem(i, 1, QTableWidgetItem(stock.company_name))
            self.table.setItem(i, 2, QTableWidgetItem(stock.sector))

        self.status_label.setText(f"Loaded {len(stocks)} stocks from CSV.")
        self.status_label.setStyleSheet("color: green; padding: 4px;")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_validate(self) -> None:
        """Validate symbol with yfinance and auto-fill company name."""
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            QMessageBox.warning(self, "Empty Symbol", "Please enter a stock symbol.")
            return

        self.validate_button.setEnabled(False)
        self.status_label.setText("Validating with yfinance...")
        self.status_label.setStyleSheet("color: blue; padding: 4px;")

        # Call yfinance validation
        is_valid, company_name, error_msg = (
            StockUniverseManager.validate_symbol_with_yfinance(symbol)
        )

        self.validate_button.setEnabled(True)

        if is_valid:
            self.company_input.setText(company_name)
            self.add_button.setEnabled(True)
            self.status_label.setText(
                f"✓ Symbol validated: {company_name}"
            )
            self.status_label.setStyleSheet("color: green; padding: 4px;")
        else:
            self.company_input.clear()
            self.add_button.setEnabled(False)
            self.status_label.setText(f"✗ Validation failed: {error_msg}")
            self.status_label.setStyleSheet("color: red; padding: 4px;")

    def _on_add(self) -> None:
        """Add the validated stock to the CSV."""
        symbol = self.symbol_input.text().strip().upper()
        company_name = self.company_input.text().strip()
        sector = self.sector_input.text().strip() or "Unknown"

        if not symbol or not company_name:
            QMessageBox.warning(
                self, "Incomplete Data", "Please validate the symbol first."
            )
            return

        try:
            self._manager.add_stock(symbol, company_name, sector)
            QMessageBox.information(
                self, "Success", f"Stock {symbol} added to the universe."
            )

            # Clear inputs and refresh
            self.symbol_input.clear()
            self.company_input.clear()
            self.sector_input.clear()
            self.add_button.setEnabled(False)
            self._refresh_table()

        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add stock: {e}")

    def _on_remove(self) -> None:
        """Remove selected stocks from the CSV."""
        selected_rows = set(item.row() for item in self.table.selectedItems())
        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select one or more stocks to remove."
            )
            return

        # Get symbols to remove
        symbols_to_remove = []
        for row in selected_rows:
            symbol_item = self.table.item(row, 0)
            if symbol_item:
                symbols_to_remove.append(symbol_item.text())

        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove {len(symbols_to_remove)} stock(s)?\n\n"
            + "\n".join(symbols_to_remove),
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            removed_count = 0
            for symbol in symbols_to_remove:
                if self._manager.remove_stock(symbol):
                    removed_count += 1

            QMessageBox.information(
                self, "Success", f"Removed {removed_count} stock(s) from the universe."
            )
            self._refresh_table()
