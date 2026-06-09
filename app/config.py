from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./vote.db"
    secret_key: str = "dev-secret-change-me"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    media_dir: str = "./uploads"
    access_token_expire_minutes: int = 60 * 24
    seed_mock_data: bool | None = None

    @property
    def should_seed_mock_data(self) -> bool:
        if self.seed_mock_data is not None:
            return self.seed_mock_data
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def media_path(self) -> Path:
        return Path(self.media_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
