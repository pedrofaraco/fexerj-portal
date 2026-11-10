"""Golden test for the current engine: the output must not change.

The engine in `calculator/classes.py` generates the official FEXERJ rating and
is not touched by the migration. This test fails if someone changes it by accident.

The rating lists — the published ratings — are compared byte for byte. The
audit files are compared cell by cell, text exactly and numbers to twelve
digits: the engine writes its floats in full, and the last digit of a few of
them depends on the platform's maths library. The golden files were written
on macOS and CI runs on Linux, which kept this test red there for as long as
the audits were compared as bytes.

Four binary fixtures are covered, each exercising a different engine path:
  - round_robin_6players.TURX: round robin, 6 players (all with a FEXERJ id).
  - swiss_system_51players.TUNX: Swiss system, 51 players (all with a FEXERJ id).
    Player life-game counts and ratings are chosen so all four Calc_Rule values
    (TEMPORARY, RATING_PERFORMANCE, DOUBLE_K, NORMAL) appear in the audit.
  - swiss_team_93players.TUMX: Swiss team, 93 players (all with a FEXERJ id).
    Same idea: inputs are chosen so all four Calc_Rule values appear.
  - swiss_system_18players.TUNX: Swiss system, 18 players, one of them missing
    a FEXERJ id in the BIO block. This fixture cannot produce a rating list —
    the engine raises ValueError. The locked behavior here is the exception
    and its message, not a byte-identical output file.
"""
import math
import pathlib

import pytest

from calculator import FexerjRatingCycle

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'
GOLDEN_DIR = pathlib.Path(__file__).parent / 'golden'

_PLAYERS_CSV = (
    "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;"
    "TotalNumGames;SumOpponRating;TotalPoints\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

_TOURNAMENTS_CSV = (
    "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
    "1;99999;Test RR Tournament;2025-01-01;RR;0;1\n"
)


def _assert_same_audit(actual: str, expected: str) -> None:
    """Cell by cell: text exactly, numbers to twelve digits (see the module docstring)."""
    actual_lines, expected_lines = actual.splitlines(), expected.splitlines()
    assert len(actual_lines) == len(expected_lines)
    for number, (actual_line, expected_line) in enumerate(zip(actual_lines, expected_lines, strict=True), 1):
        actual_cells, expected_cells = actual_line.split(";"), expected_line.split(";")
        assert len(actual_cells) == len(expected_cells), f"line {number}"
        for actual_cell, expected_cell in zip(actual_cells, expected_cells, strict=True):
            if actual_cell == expected_cell:
                continue
            try:
                close = math.isclose(float(actual_cell), float(expected_cell), rel_tol=1e-12, abs_tol=1e-12)
            except ValueError:
                close = False
            assert close, f"line {number}: {actual_cell!r} != {expected_cell!r}"


def _run_legacy_cycle():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    cycle = FexerjRatingCycle(
        tournaments_csv=_TOURNAMENTS_CSV,
        first_item=1,
        items_to_process=1,
        initial_rating_csv=_PLAYERS_CSV,
        binary_files={"1-99999.TURX": data},
    )
    return cycle.run_cycle()


def test_legacy_rating_list_is_byte_identical():
    output = _run_legacy_cycle()
    expected = (GOLDEN_DIR / 'legacy_rr_1_ratinglist.csv').read_text(encoding='utf-8')
    assert output["RatingList_after_1.csv"] == expected


def test_legacy_audit_matches_the_golden_file():
    output = _run_legacy_cycle()
    expected = (GOLDEN_DIR / 'legacy_rr_1_audit.csv').read_text(encoding='utf-8')
    _assert_same_audit(output["Audit_of_Tournament_1.csv"], expected)


_SS_TOURNAMENTS_CSV = (
    "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
    "1;51001;Test SS Tournament;2025-02-01;SS;0;1\n"
)


def _run_ss_cycle():
    data = (BINARY_DIR / 'swiss_system_51players.TUNX').read_bytes()
    players_csv = (GOLDEN_DIR / 'legacy_ss_1_players.csv').read_text(encoding='utf-8')
    cycle = FexerjRatingCycle(
        tournaments_csv=_SS_TOURNAMENTS_CSV,
        first_item=1,
        items_to_process=1,
        initial_rating_csv=players_csv,
        binary_files={"1-51001.TUNX": data},
    )
    return cycle.run_cycle()


def test_ss_rating_list_is_byte_identical():
    output = _run_ss_cycle()
    expected = (GOLDEN_DIR / 'legacy_ss_1_ratinglist.csv').read_text(encoding='utf-8')
    assert output["RatingList_after_1.csv"] == expected


def test_ss_audit_matches_the_golden_file():
    output = _run_ss_cycle()
    expected = (GOLDEN_DIR / 'legacy_ss_1_audit.csv').read_text(encoding='utf-8')
    _assert_same_audit(output["Audit_of_Tournament_1.csv"], expected)


_ST_TOURNAMENTS_CSV = (
    "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
    "1;93001;Test ST Tournament;2025-02-01;ST;0;1\n"
)


def _run_st_cycle():
    data = (BINARY_DIR / 'swiss_team_93players.TUMX').read_bytes()
    players_csv = (GOLDEN_DIR / 'legacy_st_1_players.csv').read_text(encoding='utf-8')
    cycle = FexerjRatingCycle(
        tournaments_csv=_ST_TOURNAMENTS_CSV,
        first_item=1,
        items_to_process=1,
        initial_rating_csv=players_csv,
        binary_files={"1-93001.TUMX": data},
    )
    return cycle.run_cycle()


def test_st_rating_list_is_byte_identical():
    output = _run_st_cycle()
    expected = (GOLDEN_DIR / 'legacy_st_1_ratinglist.csv').read_text(encoding='utf-8')
    assert output["RatingList_after_1.csv"] == expected


def test_st_audit_matches_the_golden_file():
    output = _run_st_cycle()
    expected = (GOLDEN_DIR / 'legacy_st_1_audit.csv').read_text(encoding='utf-8')
    _assert_same_audit(output["Audit_of_Tournament_1.csv"], expected)


_MISSING_ID_TOURNAMENTS_CSV = (
    "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
    "1;18001;Test SS Missing-ID Tournament;2025-02-01;SS;0;1\n"
)

# Minimal header-only players list: the engine raises before it ever needs to
# resolve a player against this list (see load_player_list in classes.py).
_MISSING_ID_PLAYERS_CSV = (
    "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;"
    "TotalNumGames;SumOpponRating;TotalPoints\n"
)


def test_missing_fexerj_id_raises_value_error():
    """swiss_system_18players.TUNX has one player (starting rank 18) with no
    FEXERJ id in the BIO block. The engine can't produce a rating list for
    this file, so the locked behavior is the raised exception, not a golden
    output file. The player's real name from the binary is deliberately left
    out of this assertion (project rule: no real player names in tests).
    """
    data = (BINARY_DIR / 'swiss_system_18players.TUNX').read_bytes()
    cycle = FexerjRatingCycle(
        tournaments_csv=_MISSING_ID_TOURNAMENTS_CSV,
        first_item=1,
        items_to_process=1,
        initial_rating_csv=_MISSING_ID_PLAYERS_CSV,
        binary_files={"1-18001.TUNX": data},
    )
    with pytest.raises(ValueError) as exc_info:
        cycle.run_cycle()
    message = str(exc_info.value)
    assert "(starting rank 18) has no FEXERJ ID in the binary file." in message
    assert "Please fix the Swiss Manager file and re-export before uploading." in message


_GOLDEN_AUDIT = (
    "# audit_v1\n"
    "Id_Fexerj;Name;We;Rn\n"
    "3541;Lucas Carvalho;0.32749035666501497;1648\n"
)


def test_the_audit_comparison_forgives_the_last_digit_of_a_float():
    """The exact pair that kept CI red: macOS wrote the golden file, and
    Linux computes the same number one digit shorter."""
    on_linux = _GOLDEN_AUDIT.replace("0.32749035666501497", "0.3274903566650149")
    _assert_same_audit(on_linux, _GOLDEN_AUDIT)


@pytest.mark.parametrize("changed", [
    _GOLDEN_AUDIT.replace("0.32749035666501497", "0.3274903566"),   # a float, tenth digit
    _GOLDEN_AUDIT.replace(";1648", ";1649"),                        # the rating itself
    _GOLDEN_AUDIT.replace("Carvalho", "Carvalha"),                  # a text cell
    _GOLDEN_AUDIT + "5400;Bruno Teixeira;0.5;1600\n",               # a row too many
    _GOLDEN_AUDIT.replace(";1648", ""),                             # a cell too few
])
def test_the_audit_comparison_forgives_nothing_else(changed):
    with pytest.raises(AssertionError):
        _assert_same_audit(changed, _GOLDEN_AUDIT)
