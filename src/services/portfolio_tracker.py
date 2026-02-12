"""
Portfolio tracker – orchestration layer over the trade journal store.

Provides high-level entry/exit logging and performance summary retrieval,
used by the Strategy Dashboard UI.

References:
    specs/001-investment-assistant/spec.md  (FR-009 .. FR-011)
    specs/001-investment-assistant/data-model.md
"""

from __future__ import annotations

from typing import Any

from core.schemas import PerformanceSummary, StrategyRecommendation, TradeJournalEntry
from services.trade_journal_store import TradeJournalStore


class PortfolioTracker:
    """
    High-level API for trade journaling.

    Wraps :class:`TradeJournalStore` with convenience methods that
    the UI layer calls directly.
    """

    def __init__(self, store: TradeJournalStore | None = None) -> None:
        self._store = store or TradeJournalStore()

    # ------------------------------------------------------------------
    # Entry / exit logging
    # ------------------------------------------------------------------

    def log_entry(
        self,
        symbol: str,
        side: str,
        price: float,
        recommendation: StrategyRecommendation | None = None,
        notes: str | None = None,
    ) -> TradeJournalEntry:
        """
        Log a simulated trade entry.

        Args:
            symbol: Stock symbol.
            side: "long" or "short".
            price: Entry price.
            recommendation: Current assistant recommendation snapshot.
            notes: Optional user notes.

        Returns:
            The created TradeJournalEntry.

        Raises:
            ValueError: If side is invalid.
        """
        if side not in ("long", "short"):
            raise ValueError(f"Invalid side: {side!r} – must be 'long' or 'short'")

        snapshot: dict[str, Any] = {}
        if recommendation is not None:
            snapshot = recommendation.model_dump(mode="json")

        entry = TradeJournalEntry(
            symbol=symbol.upper(),
            event_type="entry",
            side=side,
            price=price,
            recommendation_snapshot=snapshot,
            notes=notes,
        )
        self._store.add_entry(entry)
        return entry

    def log_exit(
        self,
        symbol: str,
        side: str,
        price: float,
        notes: str | None = None,
    ) -> TradeJournalEntry:
        """
        Log a simulated trade exit.

        Args:
            symbol: Stock symbol.
            side: "long" or "short".
            price: Exit price.
            notes: Optional user notes.

        Returns:
            The created TradeJournalEntry.

        Raises:
            ValueError: If no open position exists for the symbol/side.
        """
        open_pos = self._store.get_open_positions(symbol.upper())
        matching = [p for p in open_pos if p["side"] == side]
        if not matching:
            raise ValueError(
                f"No open {side} position for {symbol.upper()} to close."
            )

        entry = TradeJournalEntry(
            symbol=symbol.upper(),
            event_type="exit",
            side=side,
            price=price,
            notes=notes,
        )
        self._store.add_entry(entry)
        return entry

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_open_positions(
        self, symbol: str | None = None
    ) -> list[dict]:
        """Return list of open positions (entry without matching exit)."""
        return self._store.get_open_positions(symbol)

    def get_performance_summary(
        self, symbol: str | None = None
    ) -> PerformanceSummary:
        """Aggregate performance metrics from closed trades."""
        return self._store.compute_performance_summary(symbol)

    def close(self) -> None:
        """Release the underlying store connection."""
        self._store.close()
