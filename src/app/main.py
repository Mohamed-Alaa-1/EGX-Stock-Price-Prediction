"""
EGX Price Prediction - Desktop Application Entry Point

Local desktop app for Egyptian stock market analysis and prediction.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def main():
    """Main application entry point."""
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget
    from app.ui.training_tab import TrainingTab
    from app.ui.prediction_tab import PredictionTab
    from app.ui.disclaimer_banner import DisclaimerBanner
    from app.ui.launcher_dialog import LauncherDialog
    from data.providers.registry import get_provider_registry
    from core.config import Config
    
    # Ensure directories exist
    Config.ensure_directories()
    
    print("EGX Price Prediction - Starting...")
    print("Constitution: Local-first, personal-use only. Not financial advice.")
    
    app = QApplication(sys.argv)
    app.setApplicationName("EGX Price Prediction")
    app.setOrganizationName("LocalStocks")
    
    # Show launcher dialog to choose provider
    launcher = LauncherDialog()
    if launcher.exec() != LauncherDialog.Accepted:
        print("User cancelled launcher dialog. Exiting.")
        return 0
    
    provider_mode = launcher.get_provider_choice()
    print(f"[Main] Provider mode: {provider_mode}")
    
    # Initialize provider registry with chosen mode
    get_provider_registry(provider_mode)
    
    # Main window
    window = QMainWindow()
    title_suffix = " [TradingView]" if provider_mode == "tradingview" else ""
    window.setWindowTitle(f"EGX Price Prediction - Personal Use Only{title_suffix}")
    window.setMinimumSize(1024, 768)
    
    # Central widget with disclaimer
    central_widget = QWidget()
    central_layout = QVBoxLayout()
    central_layout.setContentsMargins(0, 0, 0, 0)
    
    # Add disclaimer banner
    disclaimer = DisclaimerBanner()
    central_layout.addWidget(disclaimer)
    
    # Tab widget
    tabs = QTabWidget()
    
    # Prediction tab
    prediction_tab = PredictionTab()
    
    # Set TradingView-specific timeframe options if applicable
    if provider_mode == "tradingview":
        prediction_tab.chart_panel.set_timeframe_options([
            ("1 Min", "1m"),
            ("5 Min", "5m"),
            ("15 Min", "15m"),
            ("1 Hour", "1h"),
            ("1 Day", "1d"),
            ("1 Week", "1wk"),
            ("1 Month", "1mo"),
        ])
    
    tabs.addTab(prediction_tab, "Prediction")
    
    # Training tab
    training_tab = TrainingTab()
    tabs.addTab(training_tab, "Training")
    
    # Settings tab
    from app.ui.settings_panel import SettingsPanel
    settings_tab = SettingsPanel()
    tabs.addTab(settings_tab, "Settings")
    
    central_layout.addWidget(tabs)
    central_widget.setLayout(central_layout)
    window.setCentralWidget(central_widget)
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
