"""
Stock selector widget for both tabs.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Signal, Qt
from typing import Optional

from core.schemas import Stock
from data.stock_universe import load_stock_universe, search_stocks


class StockSelectorWidget(QWidget):
    """Stock selector with search functionality."""
    
    # Signal emitted when selection changes
    selection_changed = Signal(str)  # symbol
    
    def __init__(self, allow_multiple: bool = False):
        super().__init__()
        self.allow_multiple = allow_multiple
        self._init_ui()
        self._load_stocks()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type symbol or company name...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Stock list
        self.stock_list = QListWidget()
        if self.allow_multiple:
            self.stock_list.setSelectionMode(QListWidget.MultiSelection)
        else:
            self.stock_list.setSelectionMode(QListWidget.SingleSelection)
        
        self.stock_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.stock_list)
        
        self.setLayout(layout)
    
    def _load_stocks(self):
        """Load all stocks into list."""
        self.stock_list.clear()
        stocks = load_stock_universe()
        
        for stock in stocks:
            display = f"{stock.symbol} - {stock.company_name}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, stock.symbol)
            self.stock_list.addItem(item)
    
    def _on_search(self, query: str):
        """Handle search input."""
        self.stock_list.clear()
        
        if not query.strip():
            self._load_stocks()
            return
        
        matches = search_stocks(query)
        for stock in matches:
            display = f"{stock.symbol} - {stock.company_name}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, stock.symbol)
            self.stock_list.addItem(item)
    
    def _on_selection_changed(self):
        """Handle selection change."""
        selected = self.get_selected_symbols()
        if selected and not self.allow_multiple:
            self.selection_changed.emit(selected[0])
    
    def get_selected_symbols(self) -> list[str]:
        """
        Get selected stock symbols.
        
        Returns:
            List of selected symbols
        """
        selected = []
        for item in self.stock_list.selectedItems():
            symbol = item.data(Qt.UserRole)
            if symbol:
                selected.append(symbol)
        return selected
    
    def select_symbol(self, symbol: str):
        """
        Select a specific symbol.
        
        Args:
            symbol: Symbol to select
        """
        symbol = symbol.upper()
        for i in range(self.stock_list.count()):
            item = self.stock_list.item(i)
            if item.data(Qt.UserRole) == symbol:
                item.setSelected(True)
                self.stock_list.scrollToItem(item)
                break
