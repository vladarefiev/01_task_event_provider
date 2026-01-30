import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _to_async_dsn(connection_string: str) -> str:
    """Convert postgresql:// or postgres:// to postgresql+asyncpg:// for async driver."""
    dsn = connection_string
    if dsn.startswith("postgresql://") and "postgresql+asyncpg://" not in dsn:
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    # Remove query params (asyncpg handles ssl differently)
    if "?" in dsn:
        dsn = dsn.split("?")[0]
    return dsn


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/events_aggregator"
    events_provider_url: str = "http://events-provider.dev-1.python-labs.ru"
    events_provider_api_key: str = ""

    host: str = "0.0.0.0"
    port: int = 8000

    @model_validator(mode="before")
    @classmethod
    def set_database_url_from_postgres_connection_string(cls, values):
        """Read POSTGRES_CONNECTION_STRING and set database_url with async driver."""
        if isinstance(values, dict):
            postgres_conn = os.getenv("POSTGRES_CONNECTION_STRING")
            if postgres_conn:
                values["database_url"] = _to_async_dsn(postgres_conn)
            elif "POSTGRES_CONNECTION_STRING" in values:
                values["database_url"] = _to_async_dsn(values["POSTGRES_CONNECTION_STRING"])
        return values


settings = Settings()
