from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SOSFlow API"
    database_url: str = "sqlite:///./sosflow.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    priority_rules_path: str = "/config/priority-rules.yaml"
    seed_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def rules_path(self) -> Path:
        return Path(self.priority_rules_path)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
