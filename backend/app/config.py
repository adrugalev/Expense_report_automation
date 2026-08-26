from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    environment: str = "development"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'storage' / 'expense_web.db').as_posix()}"
    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 480
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    storage_dir: Path = PROJECT_ROOT / "storage"
    templates_dir: Path = PROJECT_ROOT / "templates"
    legacy_data_dir: Path = PROJECT_ROOT / "data"
    max_upload_size: int = 15 * 1024 * 1024
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMe123!"
    admin_name: str = "Администратор"
    cookie_name: str = "expense_session"
    cookie_secure: bool = False
    log_level: str = "INFO"
    api_title: str = "Expense Report Automation API"
    api_version: str = "1.0.0"
    trusted_hosts: str = "localhost,127.0.0.1"

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def host_allowlist(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    def prepare_directories(self) -> None:
        for path in (self.storage_dir, self.storage_dir / "uploads", self.storage_dir / "reports"):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
