"""Application configuration loaded from environment variables.

All settings can be overridden by environment variables of the same name
(case-insensitive).  An optional ``.env`` file in the working directory is
also loaded automatically.

Usage::

    from backend.config import settings

    print(settings.portal_user)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the FEXERJ Portal backend."""

    portal_user: str = "fexerj"
    portal_password: str = "changeme"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
