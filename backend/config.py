"""Application configuration loaded from environment variables.

All settings can be overridden by environment variables of the same name
(case-insensitive).  An optional ``.env`` file in the working directory is
also loaded automatically.

Usage::

    from backend.config import settings

    print(settings.portal_user)
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the FEXERJ Portal backend."""

    portal_user: str = "fexerj"
    portal_password: str = "changeme"
    portal_max_upload_megabytes: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Maximum multipart body size for POST /validate and POST /run (MiB).",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def portal_max_upload_bytes(self) -> int:
        return self.portal_max_upload_megabytes * 1024 * 1024


settings = Settings()
