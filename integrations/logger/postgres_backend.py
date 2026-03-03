from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from integrations.logger.databases_backend import DatabaseBackend

class PostgresBackend(DatabaseBackend):

    def __init__(self, dsn: str):
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise ImportError(
                "psycopg2 is required for PostgreSQL. "
                "Install with: pip install psycopg2-binary"
            )
        self.dsn = dsn
        self._psycopg2 = psycopg2

    @contextmanager
    def connection(self) -> Iterator:
        conn = self._psycopg2.connect(self.dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, conn, sql, params=()):
        import psycopg2.extras
        if getattr(conn, '_use_dict_cursor', False):
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = conn.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, conn, sql, params_seq):
        cur = conn.cursor()
        cur.executemany(sql, params_seq)

    def executescript(self, conn, sql):
        cur = conn.cursor()
        cur.execute(sql)

    def fetchall(self, cursor):
        return cursor.fetchall()

    def fetchone(self, cursor):
        return cursor.fetchone()

    def row_factory_dict(self, conn):
        conn._use_dict_cursor = True

    @property
    def placeholder(self) -> str:
        return "%s"

    @property
    def name(self) -> str:
        return "postgres"

    def timestamp_to_display(self, column: str) -> str:
        return f"to_timestamp({column})"

    def upsert_demand_sql(self) -> str:
        p = self.placeholder
        return f"""
            INSERT INTO demand_summary
                (geohash, point_type, attempt_count, unique_users, first_seen, last_seen)
            VALUES ({p}, {p}, 1, 1, {p}, {p})
            ON CONFLICT(geohash, point_type) DO UPDATE SET
                attempt_count = demand_summary.attempt_count + 1,
                unique_users  = (
                    SELECT COUNT(DISTINCT user_id)
                    FROM failed_route_attempts
                    WHERE origin_geohash = {p} OR dest_geohash = {p}
                ),
                last_seen = {p}
        """
