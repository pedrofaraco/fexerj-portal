"""Application configuration loaded from environment variables.

All settings can be overridden by environment variables of the same name
(case-insensitive).  An optional ``.env`` file in the working directory is
also loaded automatically.

Environment variables use the same names as fields, uppercased (e.g. ``PORTAL_ENVIRONMENT``,
``PORTAL_USER``, ``PORTAL_PASSWORD``).

Usage::

    from backend.config import settings

    print(settings.portal_user)
"""
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the FEXERJ Portal backend."""

    portal_environment: Literal["development", "production"] = Field(
        default="development",
        description='Set to "production" on internet-facing servers to enforce credential rules.',
    )
    portal_user: str = "fexerj"
    portal_password: str = "changeme"
    portal_max_upload_megabytes: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Maximum multipart body size for POST /validate and POST /run (MiB).",
    )
    portal_json_logs: bool = Field(
        default=False,
        description='When true, emit one JSON object per line for the "backend" logger (easier log shipping).',
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def portal_max_upload_bytes(self) -> int:
        return self.portal_max_upload_megabytes * 1024 * 1024

    @model_validator(mode="after")
    def enforce_production_credentials(self) -> "Settings":
        if self.portal_environment != "production":
            return self
        if self.portal_password == "changeme":
            msg = (
                "PORTAL_PASSWORD must not be the default placeholder 'changeme' "
                "when PORTAL_ENVIRONMENT is production"
            )
            raise ValueError(msg)
        if len(self.portal_password) < 8:
            msg = "PORTAL_PASSWORD must be at least 8 characters when PORTAL_ENVIRONMENT is production"
            raise ValueError(msg)
        return self


settings = Settings()
