"""
Quick test script for Stock Sheet Insights feature.

Verifies the batch service can process a small set of symbols.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from services.stock_sheet_insights_service import StockSheetInsightsService
from core.schemas import InsightStatus

def test_stock_sheet_insights():
    """Test the batch insights service with a small sample."""
    print("=" * 80)
    print("Testing Stock Sheet Insights Service")
    print("=" * 80)
    
    service = StockSheetInsightsService()
    
    # Test with just 2 symbols to keep it quick
    test_symbols = ["AAPL", "MSFT"]
    
    print(f"\nTesting with {len(test_symbols)} symbols: {test_symbols}")
    print("This will fetch data, optionally train, and compute recommendations.\n")
    
    try:
        result = service.run_batch_insights(
            symbols=test_symbols,
            forecast_method="naive",  # Use naive for speed
            train_models=False,  # Skip training for quick test
            force_refresh=False,  # Use cache if available
        )
        
        print("\n" + "=" * 80)
        print("RESULTS:")
        print("=" * 80)
        print(f"Batch ID: {result.batch_id}")
        print(f"Computed at: {result.computed_at}")
        print(f"\nSummary: {result.summary}")
        
        print("\nPer-symbol results:")
        for insight in result.results:
            status_icon = "✓" if insight.status == InsightStatus.OK else "⚠" if insight.status == InsightStatus.HOLD_FALLBACK else "✗"
            print(f"  {status_icon} {insight.symbol}: {insight.action.value.upper()} "
                  f"(conviction={insight.conviction}, status={insight.status.value})")
            if insight.status_reason:
                print(f"      Reason: {insight.status_reason}")
        
        print("\n" + "=" * 80)
        print("TEST PASSED: Batch insights service works correctly!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_stock_sheet_insights()
    sys.exit(0 if success else 1)
