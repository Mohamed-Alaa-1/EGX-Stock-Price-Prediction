"""
Stock universe manager — add/remove stocks from the CSV file.

Provides programmatic access to modify egx_stocks.csv with yfinance validation.
"""

import csv
from pathlib import Path

import yfinance as yf

from core.schemas import Stock


class StockUniverseManager:
    """Manages the EGX stock universe CSV file."""

    def __init__(self, csv_path: Path | None = None):
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / "data" / "egx_stocks.csv"
        self.csv_path = csv_path

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def load_all(self) -> list[Stock]:
        """Load all stocks from CSV."""
        if not self.csv_path.exists():
            return []

        stocks = []
        with open(self.csv_path, encoding="utf-8") as f:
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

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def save_all(self, stocks: list[Stock]) -> None:
        """Overwrite CSV with the provided stock list."""
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["symbol", "company_name", "sector"])
            writer.writeheader()
            for stock in stocks:
                writer.writerow({
                    "symbol": stock.symbol.upper(),
                    "company_name": stock.company_name,
                    "sector": stock.sector,
                })

    def add_stock(
        self,
        symbol: str,
        company_name: str,
        sector: str = "Unknown",
    ) -> Stock:
        """
        Add a new stock to the CSV (append).

        Args:
            symbol: Stock symbol (will be uppercased).
            company_name: Full company name.
            sector: Sector/industry.

        Returns:
            The newly created Stock object.

        Raises:
            ValueError: If stock already exists.
        """
        stocks = self.load_all()
        symbol = symbol.upper()

        # Check for duplicates
        if any(s.symbol == symbol for s in stocks):
            raise ValueError(f"Stock {symbol} already exists in the universe.")

        new_stock = Stock(
            symbol=symbol,
            company_name=company_name,
            sector=sector,
            exchange="EGX",
        )
        stocks.append(new_stock)
        self.save_all(stocks)
        return new_stock

    def remove_stock(self, symbol: str) -> bool:
        """
        Remove a stock from the CSV.

        Args:
            symbol: Stock symbol to remove.

        Returns:
            True if removed, False if not found.
        """
        stocks = self.load_all()
        symbol = symbol.upper()
        original_count = len(stocks)
        stocks = [s for s in stocks if s.symbol != symbol]

        if len(stocks) < original_count:
            self.save_all(stocks)
            return True
        return False

    # ------------------------------------------------------------------
    # yfinance validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_symbol_with_yfinance(symbol: str) -> tuple[bool, str, str]:
        """
        Validate a stock symbol using yfinance and fetch metadata.

        Args:
            symbol: Stock symbol to validate.

        Returns:
            Tuple of (is_valid, company_name, error_message).
            If valid, company_name is populated and error_message is empty.
            If invalid, company_name is empty and error_message explains why.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Check if we got meaningful data
            if not info or "symbol" not in info:
                return False, "", f"Symbol {symbol} not found in yfinance database."

            # Extract company name (yfinance uses different keys)
            company_name = (
                info.get("longName")
                or info.get("shortName")
                or info.get("name")
                or symbol
            )

            return True, company_name, ""

        except Exception as e:
            return False, "", f"yfinance error: {str(e)}"
