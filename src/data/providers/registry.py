"""
Provider registry and selection.
"""

from datetime import date
from typing import Optional

from data.providers.base import BaseProvider
from core.schemas import PriceSeries


class ProviderRegistry:
    """Registry for managing data providers."""
    
    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}
        self._default_order: list[str] = []
    
    def register(self, provider: BaseProvider, is_default: bool = False) -> None:
        """
        Register a provider.
        
        Args:
            provider: Provider instance
            is_default: Add to default fallback chain
        """
        self._providers[provider.name] = provider
        if is_default and provider.name not in self._default_order:
            self._default_order.append(provider.name)
    
    def get(self, name: str) -> Optional[BaseProvider]:
        """Get provider by name."""
        return self._providers.get(name)
    
    def fetch_with_fallback(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        preferred_provider: Optional[str] = None,
        interval: str = "1d",
    ) -> Optional[PriceSeries]:
        """
        Fetch using preferred provider with fallback chain.
        
        Args:
            symbol: Stock symbol
            start_date: Optional start date
            end_date: Optional end date
            preferred_provider: Try this provider first
            
        Returns:
            PriceSeries if any provider succeeds, None otherwise
        """
        # Build order: preferred first, then defaults
        order = []
        if preferred_provider and preferred_provider in self._providers:
            order.append(preferred_provider)
        order.extend([p for p in self._default_order if p not in order])
        
        # Try each provider
        print(f"[ProviderRegistry] fetch_with_fallback({symbol}, interval={interval}), providers={order}")
        for provider_name in order:
            provider = self._providers.get(provider_name)
            if provider and provider.supports_symbol(symbol):
                print(f"[ProviderRegistry] Trying {provider_name} for {symbol}...")
                try:
                    result = provider.fetch(symbol, start_date, end_date, interval=interval)
                    if result:
                        print(f"[ProviderRegistry] {provider_name} SUCCESS: {len(result.bars)} bars")
                        return result
                    else:
                        print(f"[ProviderRegistry] {provider_name} returned None")
                except Exception as e:
                    print(f"[ProviderRegistry] {provider_name} ERROR: {e}")
            else:
                if provider:
                    print(f"[ProviderRegistry] {provider_name} does not support {symbol}")
        
        print(f"[ProviderRegistry] All providers failed for {symbol}")
        return None


# Global registry
_registry: Optional[ProviderRegistry] = None
_provider_mode: str = "yfinance"


def get_registry(provider_mode: Optional[str] = None) -> ProviderRegistry:
    """Get global provider registry."""
    global _registry, _provider_mode
    if provider_mode and provider_mode != _provider_mode:
        # Reset registry when mode changes
        _provider_mode = provider_mode
        _registry = None
    if _registry is None:
        _registry = ProviderRegistry()
        _initialize_providers(_provider_mode)
    return _registry


def _initialize_providers(mode: str = "yfinance") -> None:
    """Initialize and register default providers."""
    from data.providers.yfinance_provider import YFinanceProvider
    from data.providers.csv_provider import CSVProvider
    
    registry = _registry
    
    if mode == "tradingview":
        # TradingView as primary, yfinance as fallback
        try:
            from data.providers.tradingview_provider import TradingViewProvider
            registry.register(TradingViewProvider(), is_default=True)
            print("[Registry] TradingView provider registered as primary")
        except Exception as e:
            print(f"[Registry] Failed to load TradingView provider: {e}")
        # Still register yfinance as fallback for historical data
        registry.register(YFinanceProvider(), is_default=True)
    else:
        # Default: yfinance as primary
        registry.register(YFinanceProvider(), is_default=True)
    
    # Register CSV import as fallback
    registry.register(CSVProvider(), is_default=True)


def get_provider_registry(provider_mode: Optional[str] = None) -> ProviderRegistry:
    """Get global provider registry (alias for get_registry)."""
    return get_registry(provider_mode)
