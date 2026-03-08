from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
import shlex
import time

import psycopg2
from psycopg2 import sql

from integrations.logger.databases_backend import DatabaseBackend
from integrations.logger.postgres_config_model import PostgresConfig


class PostgresBackend(DatabaseBackend):
    def __init__(self, config: PostgresConfig | str):
        try:
            import psycopg2.extras
        except ImportError:
            raise ImportError(
                "psycopg2 is required for PostgreSQL. "
                "Install with: pip install psycopg2-binary"
            )

        self._psycopg2 = psycopg2
        self.config = self._normalize_config(config)

    @staticmethod
    def _normalize_config(config: PostgresConfig | str) -> PostgresConfig:
        if isinstance(config, PostgresConfig):
            return config

        parts: dict[str, str] = {}
        for token in shlex.split(config):
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            parts[key.strip()] = value.strip()

        return PostgresConfig(
            host=parts.get("host", "localhost"),
            port=int(parts.get("port", 5432)),
            dbname=parts.get("dbname", "postgres"),
            user=parts.get("user", "postgres"),
            password=parts.get("password", ""),
            sslmode=parts.get("sslmode"),
        )

    def _connect(self):
        return self._psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.dbname,
            user=self.config.user,
            password=self.config.password,
            sslmode=self.config.sslmode,
        )

    def create_database(self) -> None:
        last_error: Exception | None = None

        for _ in range(10):
            try:
                conn = self._psycopg2.connect(
                    host=self.config.host,
                    port=self.config.port,
                    dbname="postgres",
                    user=self.config.user,
                    password=self.config.password,
                    sslmode=self.config.sslmode,
                )
                conn.autocommit = True
                break
            except psycopg2.OperationalError as exc:
                last_error = exc
                time.sleep(2)
        else:
            raise RuntimeError(
                f"Could not connect to PostgreSQL at "
                f"{self.config.host}:{self.config.port} as user '{self.config.user}'"
            ) from last_error

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.config.dbname,),
                )
                exists = cur.fetchone()
                if not exists:
                    cur.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(self.config.dbname)
                        )
                    )
        finally:
            conn.close()

    @contextmanager
    def connection(self) -> Iterator:
        try:
            conn = self._connect()
        except psycopg2.OperationalError as exc:
            if f'database "{self.config.dbname}" does not exist' not in str(exc):
                raise
            self.create_database()
            conn = self._connect()

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
        if getattr(conn, "_use_dict_cursor", False):
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