# integrations/logger/config_models.py

from pydantic import BaseModel, Field

class PostgresConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    dbname: str
    user: str
    password: str
    sslmode: str | None = None