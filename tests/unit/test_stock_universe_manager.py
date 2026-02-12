"""Unit tests for stock_universe_manager.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.schemas import Stock  # noqa: E402
from services.stock_universe_manager import StockUniverseManager  # noqa: E402


@pytest.fixture()
def tmp_csv(tmp_path: Path):
    """Return a path to a temporary CSV file."""
    return tmp_path / "test_stocks.csv"


@pytest.fixture()
def manager(tmp_csv: Path):
    """Provide a StockUniverseManager backed by a temp CSV."""
    return StockUniverseManager(csv_path=tmp_csv)


# ------------------------------------------------------------------
# Basic CRUD
# ------------------------------------------------------------------


def test_load_empty_csv(manager: StockUniverseManager):
    """Empty CSV returns empty list."""
    stocks = manager.load_all()
    assert stocks == []


def test_add_stock(manager: StockUniverseManager):
    """Can add a stock and it persists."""
    stock = manager.add_stock("AAPL", "Apple Inc.", "Technology")
    assert stock.symbol == "AAPL"
    assert stock.company_name == "Apple Inc."
    assert stock.sector == "Technology"

    # Reload and verify
    stocks = manager.load_all()
    assert len(stocks) == 1
    assert stocks[0].symbol == "AAPL"


def test_add_duplicate_raises(manager: StockUniverseManager):
    """Adding duplicate symbol raises ValueError."""
    manager.add_stock("AAPL", "Apple Inc.", "Technology")
    with pytest.raises(ValueError, match="already exists"):
        manager.add_stock("AAPL", "Apple Inc. 2", "Technology")


def test_symbol_uppercase(manager: StockUniverseManager):
    """Symbols are stored uppercase."""
    manager.add_stock("aapl", "Apple Inc.", "Technology")
    stocks = manager.load_all()
    assert stocks[0].symbol == "AAPL"


def test_remove_stock(manager: StockUniverseManager):
    """Can remove an existing stock."""
    manager.add_stock("AAPL", "Apple Inc.", "Technology")
    manager.add_stock("MSFT", "Microsoft", "Technology")

    result = manager.remove_stock("AAPL")
    assert result is True

    stocks = manager.load_all()
    assert len(stocks) == 1
    assert stocks[0].symbol == "MSFT"


def test_remove_nonexistent_returns_false(manager: StockUniverseManager):
    """Removing nonexistent stock returns False."""
    result = manager.remove_stock("AAPL")
    assert result is False


# ------------------------------------------------------------------
# Full workflow
# ------------------------------------------------------------------


def test_full_workflow(manager: StockUniverseManager):
    """Add multiple stocks, remove one, verify persistence."""
    manager.add_stock("AAPL", "Apple Inc.", "Technology")
    manager.add_stock("MSFT", "Microsoft", "Technology")
    manager.add_stock("GOOGL", "Alphabet Inc.", "Technology")

    stocks = manager.load_all()
    assert len(stocks) == 3

    manager.remove_stock("MSFT")
    stocks = manager.load_all()
    assert len(stocks) == 2
    assert "MSFT" not in [s.symbol for s in stocks]


def test_save_all_overwrites(manager: StockUniverseManager):
    """save_all() completely replaces CSV content."""
    manager.add_stock("AAPL", "Apple Inc.", "Technology")
    manager.add_stock("MSFT", "Microsoft", "Technology")

    # Create new list and save
    new_stocks = [
        Stock(symbol="TSLA", company_name="Tesla", sector="Automotive", exchange="EGX"),
        Stock(symbol="NVDA", company_name="NVIDIA", sector="Technology", exchange="EGX"),
    ]
    manager.save_all(new_stocks)

    # Reload
    stocks = manager.load_all()
    assert len(stocks) == 2
    assert stocks[0].symbol == "TSLA"
    assert stocks[1].symbol == "NVDA"


# ------------------------------------------------------------------
# yfinance validation (integration test - may be slow/flaky)
# ------------------------------------------------------------------


def test_validate_known_symbol():
    """Validate a known stock symbol (AAPL)."""
    is_valid, company_name, error_msg = (
        StockUniverseManager.validate_symbol_with_yfinance("AAPL")
    )
    assert is_valid is True
    assert "Apple" in company_name
    assert error_msg == ""


def test_validate_invalid_symbol():
    """Invalid symbol returns False."""
    is_valid, company_name, error_msg = (
        StockUniverseManager.validate_symbol_with_yfinance("INVALID_SYMBOL_XYZ")
    )
    assert is_valid is False
    assert company_name == ""
    assert len(error_msg) > 0
