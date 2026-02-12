"""
EGX stock universe loader and search.
"""

import csv
from pathlib import Path
from typing import Optional
from functools import lru_cache

from core.schemas import Stock


@lru_cache(maxsize=1)
def load_stock_universe() -> list[Stock]:
    """
    Load EGX stock universe from CSV.
    
    Returns:
        List of Stock objects
    """
    csv_path = Path(__file__).parent / "egx_stocks.csv"
    
    if not csv_path.exists():
        return []
    
    stocks = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stock = Stock(
                symbol=row["symbol"].upper(),
                company_name=row["company_name"],
                sector=row.get("sector", "Unknown"),
                exchange="EGX",
            )
            stocks.append(stock)
    
    return stocks


def search_stocks(query: str) -> list[Stock]:
    """
    Search stocks by symbol or company name.
    
    Args:
        query: Search query (case-insensitive)
        
    Returns:
        Matching stocks
    """
    if not query:
        return load_stock_universe()
    
    query = query.lower()
    stocks = load_stock_universe()
    
    matches = []
    for stock in stocks:
        if (
            query in stock.symbol.lower()
            or query in stock.company_name.lower()
        ):
            matches.append(stock)
    
    return matches


def get_stock(symbol: str) -> Optional[Stock]:
    """
    Get stock by symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Stock or None
    """
    symbol = symbol.upper()
    stocks = load_stock_universe()
    
    for stock in stocks:
        if stock.symbol == symbol:
            return stock
    
    return None
