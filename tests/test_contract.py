"""Contract tests: catch drift between backend/calculator constants and frontend.

These tests read the frontend JavaScript source files as text and assert that
the canonical wire-format strings defined in Python appear verbatim in the JS.
Any divergence means the frontend would silently misparsing backend output.

When a test here fails, synchronise the constant on the side that changed and
update the other to match before merging.
"""
import pathlib

from backend.validator import _PLAYERS_HEADER, _TOURNAMENTS_HEADER
from calculator.classes import _AUDIT_FILE_HEADER, _AUDIT_FILE_PREAMBLE

_FRONTEND_SRC = pathlib.Path(__file__).parent.parent / "frontend" / "src"


def _read(relative_path: str) -> str:
    return (_FRONTEND_SRC / relative_path).read_text(encoding="utf-8")


class TestCsvHeaderContracts:
    """Players and tournaments CSV headers must match between backend validator and frontend."""

    def test_players_csv_header_matches_frontend(self):
        content = _read("csvUploadValidation.js")
        assert _PLAYERS_HEADER in content, (
            "PLAYERS_HEADER in backend/validator.py has drifted from "
            "frontend/src/csvUploadValidation.js — update them to match."
        )

    def test_tournaments_csv_header_matches_frontend(self):
        content = _read("csvUploadValidation.js")
        assert _TOURNAMENTS_HEADER in content, (
            "TOURNAMENTS_HEADER in backend/validator.py has drifted from "
            "frontend/src/csvUploadValidation.js — update them to match."
        )


class TestAuditFormatContracts:
    """Audit file preamble and column header must match between calculator and frontend parser."""

    def test_audit_preamble_matches_frontend(self):
        content = _read("resultParser.js")
        assert _AUDIT_FILE_PREAMBLE in content, (
            "_AUDIT_FILE_PREAMBLE in calculator/classes.py has drifted from "
            "frontend/src/resultParser.js — update AUDIT_PREAMBLE in one of them."
        )

    def test_audit_header_matches_frontend(self):
        content = _read("resultParser.js")
        assert _AUDIT_FILE_HEADER in content, (
            "_AUDIT_FILE_HEADER in calculator/classes.py has drifted from "
            "frontend/src/resultParser.js — update AUDIT_FILE_HEADER in one of them."
        )
