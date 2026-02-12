"""
SQLite-backed trade journal store.

Provides append-only journal entry persistence, position queries,
and PerformanceSummary SQL computations.

References:
    specs/001-investment-assistant/data-model.md
    specs/001-investment-assistant/spec.md (FR-009 .. FR-011)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from core.config import Config
from core.schemas import PerformanceSummary, TradeJournalEntry

# ---------------------------------------------------------------------------
# Schema version — bump to trigger migration
# ---------------------------------------------------------------------------
_SCHEMA_VERSION = 1

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS journal_entries (
    id          TEXT    PRIMARY KEY,
    created_at  TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    event_type  TEXT    NOT NULL CHECK(event_type IN ('entry', 'exit')),
    side        TEXT    NOT NULL CHECK(side IN ('long', 'short')),
    price       REAL    NOT NULL,
    recommendation_snapshot TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class TradeJournalStore:
    """
    Local SQLite store for the trade journal.

    - Append-only writes (entry / exit events).
    - Queries for open positions (unmatched entries) and closed trades.
    - Aggregate PerformanceSummary from closed positions.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or Config.TRADE_JOURNAL_DB_PATH
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(_CREATE_SQL)
        # Check / set version
        cur = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        )
        row = cur.fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES ('version', ?)",
                (str(_SCHEMA_VERSION),),
            )
            conn.commit()
        # Future: migration logic when _SCHEMA_VERSION > stored version

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Writes (T032)
    # ------------------------------------------------------------------

    def add_entry(self, entry: TradeJournalEntry) -> None:
        """Append a journal entry (entry or exit event)."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO journal_entries
                (id, created_at, symbol, event_type, side, price,
                 recommendation_snapshot, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.created_at.isoformat(),
                entry.symbol.upper(),
                entry.event_type,
                entry.side,
                entry.price,
                json.dumps(entry.recommendation_snapshot),
                entry.notes,
            ),
        )
        conn.commit()

    # ------------------------------------------------------------------
    # Reads (T033)
    # ------------------------------------------------------------------

    def get_all_entries(self, symbol: str | None = None) -> list[TradeJournalEntry]:
        """Return all journal entries, optionally filtered by symbol."""
        conn = self._get_conn()
        if symbol:
            rows = conn.execute(
                "SELECT * FROM journal_entries WHERE symbol = ? ORDER BY created_at",
                (symbol.upper(),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM journal_entries ORDER BY created_at"
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def get_open_positions(
        self, symbol: str | None = None
    ) -> list[dict]:
        """
        Return open positions (entries without a matching exit).

        An entry is "open" if there is no subsequent exit event
        for the same symbol + side after it.
        """
        conn = self._get_conn()
        query = """
            SELECT e.*
            FROM journal_entries e
            WHERE e.event_type = 'entry'
              AND NOT EXISTS (
                  SELECT 1 FROM journal_entries x
                  WHERE x.event_type = 'exit'
                    AND x.symbol = e.symbol
                    AND x.side = e.side
                    AND x.created_at > e.created_at
              )
        """
        params: tuple = ()
        if symbol:
            query += " AND e.symbol = ?"
            params = (symbol.upper(),)
        query += " ORDER BY e.created_at"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_closed_trades(
        self, symbol: str | None = None
    ) -> list[dict]:
        """
        Return closed trades: paired entry → exit events.

        Returns list of dicts with entry_* and exit_* fields + computed
        realized_return_pct.
        """
        conn = self._get_conn()
        # Pair each exit with the most recent unmatched entry for same symbol+side
        query = """
            SELECT
                en.id          AS entry_id,
                en.created_at  AS entry_at,
                en.symbol      AS symbol,
                en.side        AS side,
                en.price       AS entry_price,
                en.recommendation_snapshot AS entry_snapshot,
                ex.id          AS exit_id,
                ex.created_at  AS exit_at,
                ex.price       AS exit_price,
                ex.notes       AS exit_notes
            FROM journal_entries ex
            INNER JOIN journal_entries en
                ON en.symbol = ex.symbol
               AND en.side = ex.side
               AND en.event_type = 'entry'
               AND en.created_at < ex.created_at
            WHERE ex.event_type = 'exit'
        """
        params: tuple = ()
        if symbol:
            query += " AND ex.symbol = ?"
            params = (symbol.upper(),)
        query += " ORDER BY ex.created_at"

        rows = conn.execute(query, params).fetchall()
        trades: list[dict] = []
        for r in rows:
            d = dict(r)
            ep = d["entry_price"]
            xp = d["exit_price"]
            if d["side"] == "long":
                d["realized_return_pct"] = ((xp - ep) / ep) * 100 if ep else None
            else:
                d["realized_return_pct"] = ((ep - xp) / ep) * 100 if ep else None

            # Detect stop-loss hit from snapshot
            try:
                snap = json.loads(d.get("entry_snapshot") or "{}")
                sl = snap.get("stop_loss")
                if sl is not None:
                    if d["side"] == "long":
                        d["stop_loss_hit"] = xp <= sl
                    else:
                        d["stop_loss_hit"] = xp >= sl
                else:
                    d["stop_loss_hit"] = None
            except Exception:
                d["stop_loss_hit"] = None
            trades.append(d)
        return trades

    # ------------------------------------------------------------------
    # Performance summary (T034)
    # ------------------------------------------------------------------

    def compute_performance_summary(
        self, symbol: str | None = None
    ) -> PerformanceSummary:
        """Aggregate performance metrics from closed trades."""
        closed = self.get_closed_trades(symbol)
        open_positions = self.get_open_positions(symbol)

        warnings: list[str] = []
        closed_count = len(closed)
        open_count = len(open_positions)

        if closed_count == 0:
            return PerformanceSummary(
                as_of_date=date.today(),
                symbol=symbol,
                closed_trade_count=0,
                open_trade_count=open_count,
                warnings=["No closed trades to summarize."],
            )

        wins = sum(1 for t in closed if (t.get("realized_return_pct") or 0) > 0)
        win_rate = wins / closed_count

        returns = [t.get("realized_return_pct", 0) or 0 for t in closed]
        avg_return = sum(returns) / len(returns)

        sl_evaluable = [t for t in closed if t.get("stop_loss_hit") is not None]
        if sl_evaluable:
            sl_hits = sum(1 for t in sl_evaluable if t["stop_loss_hit"])
            sl_rate = sl_hits / len(sl_evaluable)
        else:
            sl_rate = None
            warnings.append("No trades with stop-loss data for hit-rate calculation.")

        return PerformanceSummary(
            as_of_date=date.today(),
            symbol=symbol,
            closed_trade_count=closed_count,
            open_trade_count=open_count,
            win_rate=round(win_rate, 4),
            avg_return_pct=round(avg_return, 4),
            stop_loss_hit_rate=round(sl_rate, 4) if sl_rate is not None else None,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> TradeJournalEntry:
        d = dict(row)
        snap = d.get("recommendation_snapshot")
        if isinstance(snap, str):
            try:
                d["recommendation_snapshot"] = json.loads(snap)
            except Exception:
                d["recommendation_snapshot"] = {}
        return TradeJournalEntry(**d)
