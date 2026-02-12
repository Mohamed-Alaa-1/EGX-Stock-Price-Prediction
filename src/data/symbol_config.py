"""
Symbol-specific configuration for TradingView provider.

Maps symbols to their correct screener/exchange/symbol format for TradingView.
"""

from typing import Optional


class TradingViewSymbolConfig:
    """Configuration for a symbol in TradingView."""
    
    def __init__(self, symbol: str, screener: str = "egypt", exchange: str = "EGX", tv_symbol: Optional[str] = None):
        self.symbol = symbol
        self.screener = screener
        self.exchange = exchange
        self.tv_symbol = tv_symbol or symbol  # TradingView might use different symbol format


# Symbol configuration mapping
SYMBOL_CONFIG: dict[str, TradingViewSymbolConfig] = {
    # EGX stocks (default: screener="egypt", exchange="EGX")
    # Major stocks
    "COMI": TradingViewSymbolConfig("COMI"),
    "PHDC": TradingViewSymbolConfig("PHDC"),
    "CCAP": TradingViewSymbolConfig("CCAP"),
    "ORTE": TradingViewSymbolConfig("ORTE"),
    "SWDY": TradingViewSymbolConfig("SWDY"),
    "HRHO": TradingViewSymbolConfig("HRHO"),
    "TMGH": TradingViewSymbolConfig("TMGH"),
    "ESRS": TradingViewSymbolConfig("ESRS"),
    "ETEL": TradingViewSymbolConfig("ETEL"),
    "EFIH": TradingViewSymbolConfig("EFIH"),
    "OCDI": TradingViewSymbolConfig("OCDI"),
    "JUFO": TradingViewSymbolConfig("JUFO"),
    "BITE": TradingViewSymbolConfig("BITE"),
    "EKHO": TradingViewSymbolConfig("EKHO"),
    "ORWE": TradingViewSymbolConfig("ORWE"),
    "HELI": TradingViewSymbolConfig("HELI"),
    "ALCN": TradingViewSymbolConfig("ALCN"),
    "AMER": TradingViewSymbolConfig("AMER"),
    "SKPC": TradingViewSymbolConfig("SKPC"),
    "EAST": TradingViewSymbolConfig("EAST"),
    
    # Additional EGX stocks - add more as needed
    "ATQA": TradingViewSymbolConfig("ATQA"),
    "CLHO": TradingViewSymbolConfig("CLHO"),
    "EGAS": TradingViewSymbolConfig("EGAS"),
    "EGTS": TradingViewSymbolConfig("EGTS"),
    "MNHD": TradingViewSymbolConfig("MNHD"),
    "ORAS": TradingViewSymbolConfig("ORAS"),
    "RAYA": TradingViewSymbolConfig("RAYA"),
    
    # Forex/Commodities - these use yfinance instead of TradingView
    # TradingView forex support is unreliable for these
    "XAUUSD": TradingViewSymbolConfig("XAUUSD", screener="", exchange="", tv_symbol=""),  # Empty = skip TradingView, use yfinance
}


def get_symbol_config(symbol: str) -> TradingViewSymbolConfig:
    """
    Get TradingView configuration for a symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        TradingViewSymbolConfig with screener/exchange settings
    """
    clean_symbol = symbol.upper().replace(".CA", "").replace(".CAI", "")
    
    # Return configured symbol or default EGX config
    return SYMBOL_CONFIG.get(
        clean_symbol,
        TradingViewSymbolConfig(clean_symbol, screener="egypt", exchange="EGX")
    )


def is_tradingview_supported(symbol: str) -> bool:
    """
    Check if symbol should use TradingView provider.
    
    Symbols with empty exchange are not supported by TradingView.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        True if TradingView should be tried for this symbol
    """
    config = get_symbol_config(symbol)
    return bool(config.exchange)  # Empty exchange = skip TradingView
