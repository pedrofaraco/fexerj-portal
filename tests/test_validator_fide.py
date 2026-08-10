"""Validation of the new player format and header-based dispatch."""
from backend.validator import validate_inputs
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER

_FIDE_PLAYERS = (
    FIDE_HEADER + "\n"
    "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;;0;0;0;0;;0;0;0;0\n"
)
_LEGACY_PLAYERS = (
    LEGACY_HEADER + "\n"
    "1;;;Player One;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
)
# Tournament dispatch by mode is Task 16's job — in this task tournaments.csv
# is still validated against the current 12-column-era (7-column) header in
# all three modes, so the fixture below intentionally does NOT use
# calculator.fide.tournaments.TOURNAMENTS_HEADER (which adds a TimeControl
# column).
_TOURNAMENTS = (
    "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
    "1;99999;Test Tournament;2026-03-15;RR;0;1\n"
)


def _errors(players, mode, tournaments=_TOURNAMENTS):
    return validate_inputs(players, tournaments, {}, 1, 1, mode=mode)


def test_fide_mode_accepts_the_new_header():
    errors = _errors(_FIDE_PLAYERS, "fide")
    assert not any("cabeçalho" in e for e in errors)


def test_fide_mode_accepts_the_legacy_header():
    """The §2.2 conversion happens at read time, so today's file still works."""
    errors = _errors(_LEGACY_PLAYERS, "fide")
    assert not any("cabeçalho" in e for e in errors)


def test_unknown_header_names_both_accepted_formats():
    errors = _errors("Foo;Bar\n1;2\n", "fide")
    joined = " ".join(errors)
    assert "12" in joined and "23" in joined


def test_peak_flag_must_be_zero_or_one():
    bad = _FIDE_PLAYERS.replace(";1800;50;0;", ";1800;50;7;")
    errors = _errors(bad, "fide")
    assert any("Peak2200_Std" in e for e in errors)


def test_empty_rating_is_accepted():
    unrated = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;;0;0;0;0;;0;0;0;0;;0;0;0;0\n"
    )
    errors = _errors(unrated, "fide")
    assert not any("Rtg_Std" in e for e in errors)


def test_empty_rating_with_peak_flag_is_accepted():
    """Player who reached 2200 and later fell below the floor (§7)."""
    fallen = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;;300;1;0;0;;0;0;0;0;;0;0;0;0\n"
    )
    errors = _errors(fallen, "fide")
    assert not any("Peak2200_Std" in e for e in errors)


def test_legacy_mode_still_rejects_the_new_header():
    errors = _errors(_FIDE_PLAYERS, "legacy")
    assert any("cabeçalho" in e for e in errors)


def test_missing_birthday_is_rejected():
    """§5.3: birthday becomes required in the per-game model — the under-18 K depends on it."""
    no_birthday = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;;M;BRA;1800;50;0;0;0;;0;0;0;0;;0;0;0;0\n"
    )
    errors = _errors(no_birthday, "fide")
    assert any("Birthday" in e for e in errors)


def test_duplicate_id_no_is_rejected():
    dup = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;;0;0;0;0;;0;0;0;0\n"
        "1;;;Player Two;CLUB A;01/01/1991;M;BRA;1600;40;0;0;0;;0;0;0;0;;0;0;0;0\n"
    )
    errors = _errors(dup, "fide")
    assert any("Id_No duplicado" in e for e in errors)


def test_duplicate_id_cbx_is_rejected():
    """A shared Id_CBX is not cosmetic.

    In an IRT tournament, collect_games maps the binary's CBX id to a FEXERJ
    id from the whole player list, so two players sharing an Id_CBX would
    silently misattribute one player's games to the other, with no error or
    warning, in a program that produces official ratings.
    """
    dup = (
        FIDE_HEADER + "\n"
        "1;999;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;;0;0;0;0;;0;0;0;0\n"
        "2;999;;Player Two;CLUB A;01/01/1991;M;BRA;1600;40;0;0;0;;0;0;0;0;;0;0;0;0\n"
    )
    errors = _errors(dup, "fide")
    assert any("Id_CBX duplicado" in e for e in errors)


def test_unknown_mode_returns_error():
    errors = _errors(_FIDE_PLAYERS, "bogus")
    assert any("bogus" in e for e in errors)
