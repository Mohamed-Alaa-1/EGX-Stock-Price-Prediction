"""Unit tests for trade_journal_store.py (T005 / T039)."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.schemas import TradeJournalEntry  # noqa: E402
from services.trade_journal_store import TradeJournalStore  # noqa: E402


@pytest.fixture()
def tmp_db(tmp_path: Path):
    """Return a path to a temporary SQLite DB file."""
    return tmp_path / "test_journal.sqlite3"


@pytest.fixture()
def store(tmp_db: Path):
    """Provide a TradeJournalStore backed by a temp DB, close after test."""
    s = TradeJournalStore(db_path=tmp_db)
    yield s
    s.close()


# ------------------------------------------------------------------
# Basic CRUD
# ------------------------------------------------------------------


def test_add_and_retrieve_entry(store: TradeJournalStore):
    entry = TradeJournalEntry(
        symbol="COMI", event_type="entry", side="long", price=50.0
    )
    store.add_entry(entry)
    entries = store.get_all_entries()
    assert len(entries) == 1
    assert entries[0].symbol == "COMI"
    assert entries[0].event_type == "entry"
    assert entries[0].price == 50.0


def test_filter_by_symbol(store: TradeJournalStore):
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="entry", side="long", price=50.0)
    )
    store.add_entry(
        TradeJournalEntry(symbol="PHDC", event_type="entry", side="long", price=10.0)
    )
    assert len(store.get_all_entries("COMI")) == 1
    assert len(store.get_all_entries("PHDC")) == 1
    assert len(store.get_all_entries()) == 2


# ------------------------------------------------------------------
# Open positions
# ------------------------------------------------------------------


def test_open_positions(store: TradeJournalStore):
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="entry", side="long", price=50.0)
    )
    open_pos = store.get_open_positions()
    assert len(open_pos) == 1
    assert open_pos[0]["symbol"] == "COMI"

    # Close the position
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="exit", side="long", price=55.0)
    )
    assert len(store.get_open_positions()) == 0


def test_open_positions_filter_symbol(store: TradeJournalStore):
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="entry", side="long", price=50.0)
    )
    store.add_entry(
        TradeJournalEntry(symbol="PHDC", event_type="entry", side="long", price=10.0)
    )
    assert len(store.get_open_positions("COMI")) == 1
    assert len(store.get_open_positions("PHDC")) == 1


# ------------------------------------------------------------------
# Closed trades
# ------------------------------------------------------------------


def test_closed_trades(store: TradeJournalStore):
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="entry", side="long", price=50.0)
    )
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="exit", side="long", price=55.0)
    )
    trades = store.get_closed_trades()
    assert len(trades) == 1
    assert trades[0]["realized_return_pct"] == pytest.approx(10.0)


def test_closed_trades_short(store: TradeJournalStore):
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="entry", side="short", price=60.0)
    )
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="exit", side="short", price=54.0)
    )
    trades = store.get_closed_trades()
    assert len(trades) == 1
    assert trades[0]["realized_return_pct"] == pytest.approx(10.0)


# ------------------------------------------------------------------
# Performance summary
# ------------------------------------------------------------------


def test_performance_summary_empty(store: TradeJournalStore):
    ps = store.compute_performance_summary()
    assert ps.closed_trade_count == 0
    assert ps.open_trade_count == 0
    assert ps.win_rate is None
    assert ps.as_of_date == date.today()


def test_performance_summary_with_trades(store: TradeJournalStore):
    # Winning trade
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="entry", side="long", price=50.0)
    )
    store.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="exit", side="long", price=55.0)
    )
    # Losing trade
    store.add_entry(
        TradeJournalEntry(symbol="PHDC", event_type="entry", side="long", price=20.0)
    )
    store.add_entry(
        TradeJournalEntry(symbol="PHDC", event_type="exit", side="long", price=18.0)
    )
    ps = store.compute_performance_summary()
    assert ps.closed_trade_count == 2
    assert ps.win_rate == pytest.approx(0.5)


# ------------------------------------------------------------------
# Persistence across re-open (T039)
# ------------------------------------------------------------------


def test_persistence_across_reopen(tmp_db: Path):
    """Data survives store close + reopen."""
    store1 = TradeJournalStore(db_path=tmp_db)
    store1.add_entry(
        TradeJournalEntry(symbol="COMI", event_type="entry", side="long", price=50.0)
    )
    store1.close()

    store2 = TradeJournalStore(db_path=tmp_db)
    entries = store2.get_all_entries()
    assert len(entries) == 1
    assert entries[0].symbol == "COMI"
    store2.close()


def test_recommendation_snapshot_persisted(store: TradeJournalStore):
    """JSON recommendation snapshot round-trips correctly."""
    snap = {"action": "BUY", "conviction": 75, "stop_loss": 45.0}
    entry = TradeJournalEntry(
        symbol="COMI",
        event_type="entry",
        side="long",
        price=50.0,
        recommendation_snapshot=snap,
    )
    store.add_entry(entry)
    retrieved = store.get_all_entries()[0]
    assert retrieved.recommendation_snapshot == snap
