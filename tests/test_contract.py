"""Contract tests: catch drift between backend/calculator constants and frontend.

These tests read the frontend JavaScript source files as text and assert that
the canonical wire-format strings defined in Python appear verbatim in the JS.
Any divergence means the frontend would silently misparsing backend output.

When a test here fails, synchronise the constant on the side that changed and
update the other to match before merging.
"""
import pathlib
import re

from backend.main import _ZIP_NAME_BY_MODE
from backend.validator import _FIDE_TOURNAMENTS_HEADER, _PLAYERS_HEADER, _TOURNAMENTS_HEADER
from calculator.classes import _AUDIT_FILE_HEADER, _AUDIT_FILE_PREAMBLE
from calculator.compare import COMPARISON_HEADER, COMPARISON_PREAMBLE
from calculator.fide.audit import (
    GAMES_AUDIT_PREAMBLE,
    PERIOD_AUDIT_HEADER,
    PERIOD_AUDIT_PREAMBLE,
)
from calculator.fide.ratinglist import FIDE_HEADER

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


class TestPerGameModelContracts:
    """The per-game model's formats, read by the frontend the same way."""

    def test_fide_tournaments_header_matches_frontend(self):
        content = _read("csvUploadValidation.js")
        assert _FIDE_TOURNAMENTS_HEADER in content, (
            "_FIDE_TOURNAMENTS_HEADER in backend/validator.py has drifted from "
            "frontend/src/csvUploadValidation.js — update FIDE_TOURNAMENTS_HEADER to match."
        )

    def test_fide_players_header_matches_frontend(self):
        content = _read("csvUploadValidation.js")
        assert FIDE_HEADER in content, (
            "FIDE_HEADER in calculator/fide/ratinglist.py has drifted from "
            "frontend/src/csvUploadValidation.js — update FIDE_PLAYERS_HEADER to match."
        )

    def test_period_audit_preamble_matches_frontend(self):
        assert PERIOD_AUDIT_PREAMBLE in _read("resultParser.js"), (
            "PERIOD_AUDIT_PREAMBLE in calculator/fide/audit.py has drifted from "
            "frontend/src/resultParser.js — update FIDE_PERIOD_PREAMBLE to match."
        )

    def test_games_audit_preamble_matches_frontend(self):
        assert GAMES_AUDIT_PREAMBLE in _read("resultParser.js"), (
            "GAMES_AUDIT_PREAMBLE in calculator/fide/audit.py has drifted from "
            "frontend/src/resultParser.js — update FIDE_GAMES_PREAMBLE to match."
        )

    def test_comparison_preamble_matches_frontend(self):
        assert COMPARISON_PREAMBLE in _read("resultParser.js"), (
            "COMPARISON_PREAMBLE in calculator/compare.py has drifted from "
            "frontend/src/resultParser.js — update COMPARISON_PREAMBLE to match."
        )

    def test_frontend_reads_the_period_audit_by_column_name(self):
        # The parser looks columns up by header name, so drift shows up as a
        # missing name rather than a shifted column: assert every name it
        # reads still exists in the file the engine writes.
        content = _read("resultParser.js")
        emitted = set(PERIOD_AUDIT_HEADER.split(";"))
        for column in ("Tournaments", "PlayerId", "PlayerName", "TimeControl",
                       "InitialRating", "Games", "SumDeltaR", "Variation",
                       "RoundedVariation", "FinalRating", "Path"):
            assert re.search(rf"c\.{column}\b", content), (
                f"resultParser.js no longer reads {column}"
            )
            assert column in emitted, (
                f"resultParser.js reads {column} from Audit_Period.csv, which "
                "calculator/fide/audit.py no longer writes."
            )

    def test_frontend_reads_the_comparison_by_column_name(self):
        content = _read("resultParser.js")
        emitted = set(COMPARISON_HEADER.split(";"))
        for column in ("PlayerId", "PlayerName", "RatingCurrent", "RatingFide", "Difference"):
            assert re.search(rf"c\.{column}\b", content), (
                f"resultParser.js no longer reads {column}"
            )
            assert column in emitted, (
                f"resultParser.js reads {column} from Comparison.csv, which "
                "calculator/compare.py no longer writes."
            )

    def test_zip_filenames_match_frontend(self):
        # Two frontend files name the zips: the parser names the one it read,
        # and useRunCycle names the fallback when the zip cannot be read.
        parser = _read("resultParser.js")
        run_cycle = _read("hooks/useRunCycle.js")
        for filename in _ZIP_NAME_BY_MODE.values():
            assert filename in parser, (
                f"_ZIP_NAME_BY_MODE in backend/main.py has drifted from "
                f"frontend/src/resultParser.js — {filename} is missing there."
            )
            assert filename in run_cycle, (
                f"_ZIP_NAME_BY_MODE in backend/main.py has drifted from "
                f"frontend/src/hooks/useRunCycle.js — {filename} is missing there."
            )
