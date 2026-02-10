"""
Settings panel for cache and configuration management.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt
from pathlib import Path

from data.cache_store import CacheStore
from core.config import Config


class SettingsPanel(QWidget):
    """Settings and cache management panel."""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Cache controls
        cache_group = QGroupBox("Cache Management")
        cache_layout = QVBoxLayout()
        
        self.cache_status_label = QLabel()
        self._update_cache_status()
        cache_layout.addWidget(self.cache_status_label)
        
        clear_cache_button = QPushButton("Clear All Cache")
        clear_cache_button.clicked.connect(self._on_clear_cache)
        cache_layout.addWidget(clear_cache_button)
        
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        # Info
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            f"<b>Data Directory:</b> {Config.DATA_DIR}<br>"
            f"<b>Cache Directory:</b> {Config.CACHE_DIR}<br>"
            f"<b>Models Directory:</b> {Config.MODELS_DIR}<br>"
            f"<b>Model Staleness:</b> {Config.MODEL_STALE_DAYS} days"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _update_cache_status(self):
        """Update cache status display."""
        cache_dir = Path(Config.CACHE_DIR)
        
        if not cache_dir.exists():
            self.cache_status_label.setText("Cache: Empty")
            return
        
        cache_files = list(cache_dir.glob("*.parquet"))
        total_size = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)  # MB
        
        self.cache_status_label.setText(
            f"<b>Cache Status:</b> {len(cache_files)} files, {total_size:.2f} MB"
        )
    
    def _on_clear_cache(self):
        """Handle clear cache button."""
        reply = QMessageBox.question(
            self,
            "Confirm Clear Cache",
            "Are you sure you want to clear all cached price data?\n\n"
            "This will require re-fetching data from providers.",
            QMessageBox.Yes | QMessageBox.No,
        )
        
        if reply == QMessageBox.Yes:
            try:
                CacheStore.clear_all()
                self._update_cache_status()
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    "All cached price data has been cleared.",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear cache:\n{e}",
                )
