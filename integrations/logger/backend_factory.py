from integrations.logger.databases_backend import DatabaseBackend
from integrations.logger.postgres_backend import PostgresBackend
from integrations.logger.sql_backend import SQLiteBackend


class BackendFactory:
    @staticmethod
    def get_backend(backend: str, connection_string: str) -> DatabaseBackend:
        """
        Create a database backend.

        Args:
            backend:    "sqlite" or "postgres"
            connection_string:  File path (sqlite) or DSN (postgres).
        """
        if backend == "sqlite":
            return SQLiteBackend(connection_string)
        elif backend == "postgres":
            return PostgresBackend(connection_string)
        else:
            raise ValueError(
                f"Unknown backend {backend!r}. Supported: 'sqlite', 'postgres'"
            )