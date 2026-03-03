"""
Database backend abstraction layer.

Provides a uniform interface so the pipeline code never touches raw
connection logic. Swap between SQLite (local dev) and PostgreSQL (cloud)
by changing one argument.

Usage:
    from invalid_route_pipeline.db import get_backend

    db = get_backend("sqlite", "walkway_demand.db")
    db = get_backend("postgres", "host=... dbname=... user=... password=...")
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence


# -------------------------------------------------------------------------
# Abstract interface
# -------------------------------------------------------------------------

class DatabaseBackend(ABC):
    """
    Minimal interface that the pipeline needs from a database.
    Every method uses standard DB-API-style parameterized queries.
    """

    @abstractmethod
    @contextmanager
    def connection(self) -> Iterator:
        """Yield a connection (auto-committed on success, rolled back on error)."""
        ...

    @abstractmethod
    def execute(self, conn, sql: str, params: Sequence = ()) -> Any:
        """Execute a single statement. Returns a cursor-like object."""
        ...

    @abstractmethod
    def executemany(self, conn, sql: str, params_seq: Sequence[Sequence]) -> None:
        """Execute a statement for each set of params (batch insert)."""
        ...

    @abstractmethod
    def executescript(self, conn, sql: str) -> None:
        """Execute multiple semicolon-separated statements."""
        ...

    @abstractmethod
    def fetchall(self, cursor) -> list[tuple]:
        ...

    @abstractmethod
    def fetchone(self, cursor) -> Optional[tuple]:
        ...

    @abstractmethod
    def row_factory_dict(self, conn) -> None:
        """Switch the connection to return dict-like rows."""
        ...

    @property
    @abstractmethod
    def placeholder(self) -> str:
        """Parameter placeholder: '?' for sqlite, '%s' for postgres."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for logging ('sqlite' or 'postgres')."""
        ...

    # -- Dialect helpers used by the pipeline for SQL differences ----------

    def timestamp_to_display(self, column: str) -> str:
        """SQL expression to format a timestamp column for display."""
        raise NotImplementedError

    def upsert_demand_sql(self) -> str:
        """Return the backend-appropriate UPSERT statement for demand_summary."""
        raise NotImplementedError