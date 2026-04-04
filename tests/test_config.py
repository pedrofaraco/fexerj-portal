"""Tests for backend configuration and environment validation."""
import pytest
from pydantic import ValidationError

from backend.config import Settings


def test_development_allows_default_password() -> None:
    s = Settings(portal_environment="development", portal_password="changeme")
    assert s.portal_password == "changeme"


def test_production_rejects_changeme() -> None:
    with pytest.raises(ValidationError, match="changeme"):
        Settings(
            portal_environment="production",
            portal_user="u",
            portal_password="changeme",
        )


def test_production_rejects_short_password() -> None:
    with pytest.raises(ValidationError, match="8 characters"):
        Settings(
            portal_environment="production",
            portal_user="u",
            portal_password="short",
        )


def test_production_accepts_strong_password() -> None:
    s = Settings(
        portal_environment="production",
        portal_user="u",
        portal_password="adequatepw",
    )
    assert s.portal_password == "adequatepw"
