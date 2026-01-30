from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/events_aggregator"
    events_provider_url: str = "http://events-provider.dev-1.python-labs.ru"
    events_provider_api_key: str = ""

    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
