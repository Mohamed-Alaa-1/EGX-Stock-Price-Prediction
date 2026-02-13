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

    from app.ui.disclaimer_banner import DisclaimerBanner
    from app.ui.launcher_dialog import LauncherDialog
    from app.ui.prediction_tab import PredictionTab
    from app.ui.training_tab import TrainingTab
    from core.config import Config
    from data.providers.registry import get_provider_registry
    
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
    
    # Strategy tab (controls, recommendations, journal)
    prediction_tab = PredictionTab()
    tabs.addTab(prediction_tab, "Strategy")

    # Chart tab (full-size interactive chart)
    from app.ui.chart_tab import ChartTab
    chart_tab = ChartTab()
    tabs.addTab(chart_tab, "Chart")

    # Connect strategy tab stock selection → chart tab
    prediction_tab.stock_selected.connect(chart_tab.load_symbol)
    # Give strategy tab a reference for GDR overlay
    prediction_tab._chart_tab = chart_tab
    
    # Set TradingView-specific timeframe options if applicable
    if provider_mode == "tradingview":
        chart_tab.chart_panel.set_timeframe_options([
            ("1 Min", "1m"),
            ("5 Min", "5m"),
            ("15 Min", "15m"),
            ("1 Hour", "1h"),
            ("1 Day", "1d"),
            ("1 Week", "1wk"),
            ("1 Month", "1mo"),
        ])
    
    # Training tab
    training_tab = TrainingTab()
    tabs.addTab(training_tab, "Training")
    
    # Stock Sheet Insights tab
    from app.ui.stock_sheet_insights_tab import StockSheetInsightsTab
    sheet_insights_tab = StockSheetInsightsTab()
    tabs.addTab(sheet_insights_tab, "Sheet Insights")
    
    # Settings tab
    from app.ui.settings_panel import SettingsPanel
    settings_tab = SettingsPanel()
    tabs.addTab(settings_tab, "Settings")

    # Stock Manager tab (add/remove stocks from universe)
    from app.ui.stock_manager_tab import StockManagerTab
    stock_manager_tab = StockManagerTab()
    tabs.addTab(stock_manager_tab, "Stock Manager")

    # Performance tab (T038)
    from app.ui.performance_tab import PerformanceTab
    performance_tab = PerformanceTab()
    tabs.addTab(performance_tab, "Performance")
    
    central_layout.addWidget(tabs)
    central_widget.setLayout(central_layout)
    window.setCentralWidget(central_widget)
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
