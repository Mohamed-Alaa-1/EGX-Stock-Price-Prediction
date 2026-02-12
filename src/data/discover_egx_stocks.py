"""
Utility to scrape/fetch EGX stock symbols from TradingView.

This script attempts to discover all available EGX stocks and update egx_stocks.csv.
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from tradingview_ta import TA_Handler, Interval
except ImportError:
    print("tradingview-ta not installed. Install with: pip install tradingview-ta")
    sys.exit(1)


# Known EGX stock symbols to verify (from major indices)
KNOWN_EGX_SYMBOLS = [
    "COMI", "PHDC", "CCAP", "ORTE", "SWDY", "HRHO", "TMGH", "ESRS", "ETEL", "EFIH",
    "OCDI", "JUFO", "BITE", "EKHO", "ORWE", "HELI", "ALCN", "AMER", "SKPC", "EAST",
    "ATQA", "CLHO", "EGAS", "EGTS", "ELSO", "EMFD", "FWRY", "GTHE", "IDHC", "ISMA",
    "KORP", "MNHD", "MTFP", "NICC", "ORAS", "ORHD", "OTMT", "PIOH", "TMSA", "UEGC",
    "OCIC", "RAYA", "IDKU", "DLTA", "DPHE", "EDRE", "EGCH", "EGNB", "ELFF", "ELSW",
    "EXAM", "FLTR", "GAMA", "GEMS", "GROU", "HDIC", "IRON", "ISTH", "KOAM", "LCSW",
    "MFPC", "NTRA", "ORAK", "ORDS", "PHAR", "PSCM", "RCMD", "RMFC", "SCRP", "SFIP",
    "SUNS", "TPIP", "UASG", "UETC", "VALU", "WATH",
]


def test_symbol(symbol: str) -> tuple[bool, str]:
    """
    Test if a symbol is available on TradingView EGX.
    
    Args:
        symbol: Stock symbol to test
        
    Returns:
        (is_valid, company_name or error_message)
    """
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="egypt",
            exchange="EGX",
            interval=Interval.INTERVAL_1_DAY,
        )
        
        analysis = handler.get_analysis()
        
        # If we get here, symbol exists
        close = analysis.indicators.get("close")
        if close:
            return (True, f"Close: {close}")
        else:
            return (False, "No price data")
            
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return (False, "Not found")
        return (False, error_msg)


def discover_egx_stocks():
    """
    Discover valid EGX stocks from known list.
    """
    print("Testing known EGX symbols on TradingView...")
    print("=" * 60)
    
    valid_symbols = []
    
    for symbol in KNOWN_EGX_SYMBOLS:
        is_valid, message = test_symbol(symbol)
        status = "✓" if is_valid else "✗"
        print(f"{status} {symbol:6s} - {message}")
        
        if is_valid:
            valid_symbols.append(symbol)
    
    print("=" * 60)
    print(f"\nFound {len(valid_symbols)} valid symbols out of {len(KNOWN_EGX_SYMBOLS)} tested")
    print(f"Valid symbols: {', '.join(valid_symbols)}")
    
    return valid_symbols


def update_csv_file(valid_symbols: list[str]):
    """
    Update egx_stocks.csv with discovered symbols.
    
    Args:
        valid_symbols: List of valid EGX symbols
    """
    csv_path = Path(__file__).parent / "egx_stocks.csv"
    
    # Read existing file to preserve company names
    existing = {}
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row["symbol"]] = {
                    "company_name": row["company_name"],
                    "sector": row["sector"],
                }
    
    # Prepare new data
    new_data = []
    for symbol in valid_symbols:
        if symbol in existing:
            new_data.append({
                "symbol": symbol,
                "company_name": existing[symbol]["company_name"],
                "sector": existing[symbol]["sector"],
            })
        else:
            # New symbol - add with placeholder
            new_data.append({
                "symbol": symbol,
                "company_name": f"{symbol} (Company Name TBD)",
                "sector": "Unknown",
            })
    
    # Add XAUUSD if not present
    if not any(row["symbol"] == "XAUUSD" for row in new_data):
        new_data.append({
            "symbol": "XAUUSD",
            "company_name": "Gold Spot Price (XAU/USD)",
            "sector": "Commodities",
        })
    
    # Write updated CSV
    backup_path = csv_path.with_suffix(".csv.backup")
    if csv_path.exists():
        csv_path.rename(backup_path)
        print(f"\nBackup created: {backup_path}")
    
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "company_name", "sector"])
        writer.writeheader()
        writer.writerows(new_data)
    
    print(f"Updated {csv_path} with {len(new_data)} symbols")


def main():
    """Main entry point."""
    print("EGX Stock Symbol Discovery Tool")
    print("=" * 60)
    print("This tool tests known EGX symbols on TradingView")
    print("and updates egx_stocks.csv with valid symbols.\n")
    
    valid_symbols = discover_egx_stocks()
    
    if valid_symbols:
        response = input("\nUpdate egx_stocks.csv with discovered symbols? (y/n): ")
        if response.lower() == "y":
            update_csv_file(valid_symbols)
            print("\n✓ Stock list updated successfully!")
        else:
            print("\nNo changes made.")
    else:
        print("\nNo valid symbols found. Check your internet connection.")


if __name__ == "__main__":
    main()
