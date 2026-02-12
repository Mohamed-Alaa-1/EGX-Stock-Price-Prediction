"""Unit tests for portfolio_tracker.py (T006 / T040 / T041)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.schemas import StrategyAction, StrategyRecommendation  # noqa: E402
from services.portfolio_tracker import PortfolioTracker  # noqa: E402
from services.trade_journal_store import TradeJournalStore  # noqa: E402


@pytest.fixture()
def tracker(tmp_path: Path):
    """Provide a PortfolioTracker backed by a temp DB."""
    store = TradeJournalStore(db_path=tmp_path / "journal.sqlite3")
    t = PortfolioTracker(store=store)
    yield t
    t.close()


def _make_recommendation(
    symbol: str = "COMI",
    action: StrategyAction = StrategyAction.BUY,
    conviction: int = 70,
) -> StrategyRecommendation:
    """Helper to build a minimal StrategyRecommendation."""
    from datetime import date

    return StrategyRecommendation(
        symbol=symbol,
        as_of_date=date.today(),
        action=action,
        conviction=conviction,
        entry_zone_lower=48.0,
        entry_zone_upper=50.0,
        stop_loss=45.0,
        target_exit=58.0,
        logic_summary="test recommendation",
    )


# ------------------------------------------------------------------
# Entry / exit flow (T040)
# ------------------------------------------------------------------


def test_log_entry(tracker: PortfolioTracker):
    rec = _make_recommendation()
    entry = tracker.log_entry("COMI", "long", 50.0, recommendation=rec)
    assert entry.symbol == "COMI"
    assert entry.event_type == "entry"
    assert entry.price == 50.0
    assert entry.recommendation_snapshot["action"] == "buy"


def test_log_exit_after_entry(tracker: PortfolioTracker):
    tracker.log_entry("COMI", "long", 50.0)
    exit_entry = tracker.log_exit("COMI", "long", 55.0, notes="take profit")
    assert exit_entry.event_type == "exit"
    assert exit_entry.notes == "take profit"


def test_log_exit_without_entry_raises(tracker: PortfolioTracker):
    with pytest.raises(ValueError, match="No open long position"):
        tracker.log_exit("COMI", "long", 55.0)


def test_invalid_side_raises(tracker: PortfolioTracker):
    with pytest.raises(ValueError, match="Invalid side"):
        tracker.log_entry("COMI", "up", 50.0)


def test_open_positions(tracker: PortfolioTracker):
    tracker.log_entry("COMI", "long", 50.0)
    tracker.log_entry("PHDC", "long", 10.0)
    assert len(tracker.get_open_positions()) == 2
    assert len(tracker.get_open_positions("COMI")) == 1

    # Close COMI
    tracker.log_exit("COMI", "long", 55.0)
    assert len(tracker.get_open_positions()) == 1


# ------------------------------------------------------------------
# Performance summary (T041)
# ------------------------------------------------------------------


def test_empty_performance(tracker: PortfolioTracker):
    ps = tracker.get_performance_summary()
    assert ps.closed_trade_count == 0
    assert ps.open_trade_count == 0
    assert ps.win_rate is None


def test_performance_after_closed_trade(tracker: PortfolioTracker):
    tracker.log_entry("COMI", "long", 50.0)
    tracker.log_exit("COMI", "long", 55.0)
    ps = tracker.get_performance_summary()
    assert ps.closed_trade_count == 1
    assert ps.win_rate == pytest.approx(1.0)
    assert ps.avg_return_pct == pytest.approx(10.0)


def test_performance_mixed_wins_losses(tracker: PortfolioTracker):
    # Win
    tracker.log_entry("COMI", "long", 50.0)
    tracker.log_exit("COMI", "long", 55.0)
    # Loss
    tracker.log_entry("PHDC", "long", 20.0)
    tracker.log_exit("PHDC", "long", 18.0)
    ps = tracker.get_performance_summary()
    assert ps.closed_trade_count == 2
    assert ps.win_rate == pytest.approx(0.5)


def test_performance_per_symbol(tracker: PortfolioTracker):
    tracker.log_entry("COMI", "long", 50.0)
    tracker.log_exit("COMI", "long", 55.0)
    tracker.log_entry("PHDC", "long", 10.0)

    ps_comi = tracker.get_performance_summary("COMI")
    assert ps_comi.closed_trade_count == 1
    assert ps_comi.symbol == "COMI"

    ps_phdc = tracker.get_performance_summary("PHDC")
    assert ps_phdc.closed_trade_count == 0
    assert ps_phdc.open_trade_count == 1
