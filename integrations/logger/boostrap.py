# integrations/logger/bootstrap.py

from integrations.logger.sql_backend import SQLiteBackend
from integrations.logger.postgres_backend import PostgresBackend
from integrations.logger.postgres_config_model import PostgresConfig
from typing import Dict

class Bootstrapper:
    def bootstrap(self, backend: str, connection_string: str) -> None:
        Bootstrapper.bootstrap_db(self, backend, connection_string)

    @staticmethod
    def _parse_postgres_dsn_kv(dsn: str) -> Dict[str, str]:
        parts: Dict[str, str] = {}
        for token in dsn.split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            parts[key.strip()] = value.strip()
        return parts

    def bootstrap_db(self, backend: str, connection_string: str) -> None:
        backend = backend.lower().strip()

        if backend == "sqlite":
            db = SQLiteBackend(connection_string)

        elif backend == "postgres":
            dsn_parts = self._parse_postgres_dsn_kv(connection_string)
            config = PostgresConfig(**dsn_parts)
            db = PostgresBackend(config)

        else:
            raise ValueError(f"Unknown backend: {backend}")

        db.create_database()