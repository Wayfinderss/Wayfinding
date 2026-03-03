from app.services.schema_creator_service import _exec_sqlite, _exec_postgres

class SchemaDeleterService:
    DROP_ALL_SQL = """
        DROP TABLE IF EXISTS
            demand_summary,
            failed_route_attempts;
    """

    _EXECUTORS = {
        "sqlite": _exec_sqlite,
        "postgres": _exec_postgres,
    }

    def drop_schema(self, backend: str, connection_string: str, echo: bool = False):
        """Drop all pipeline tables. Useful for tests or full reset."""
        executor = self._get_executor(backend)
        executor(connection_string, self.DROP_ALL_SQL, echo)

    @classmethod
    def _get_executor(cls, backend: str):
        try:
            return cls._EXECUTORS[backend]
        except KeyError as exc:
            supported = ", ".join(sorted(cls._EXECUTORS))
            raise ValueError(
                f"Unsupported backend: {backend!r}. Use one of: {supported}."
            ) from exc

    def run(self, *kwargs):
        self.drop_schema(*kwargs)