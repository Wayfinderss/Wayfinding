from integrations.logger.databases_backend import DatabaseBackend
from contextlib import contextmanager
from typing import Iterator
import sqlite3

class SQLiteBackend(DatabaseBackend):

    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, conn, sql, params=()):
        return conn.execute(sql, params)

    def executemany(self, conn, sql, params_seq):
        conn.executemany(sql, params_seq)

    def executescript(self, conn, sql):
        conn.executescript(sql)

    def fetchall(self, cursor):
        return cursor.fetchall()

    def fetchone(self, cursor):
        return cursor.fetchone()

    def row_factory_dict(self, conn):
        conn.row_factory = sqlite3.Row

    @property
    def placeholder(self) -> str:
        return "?"

    @property
    def name(self) -> str:
        return "sqlite"

    def timestamp_to_display(self, column: str) -> str:
        return f"datetime({column}, 'unixepoch')"

    def upsert_demand_sql(self) -> str:
        p = self.placeholder
        return f"""
            INSERT INTO demand_summary
                (geohash, point_type, attempt_count, unique_users, first_seen, last_seen)
            VALUES ({p}, {p}, 1, 1, {p}, {p})
            ON CONFLICT(geohash, point_type) DO UPDATE SET
                attempt_count = attempt_count + 1,
                unique_users  = (
                    SELECT COUNT(DISTINCT user_id)
                    FROM failed_route_attempts
                    WHERE origin_geohash = {p} OR dest_geohash = {p}
                ),
                last_seen = {p}
        """