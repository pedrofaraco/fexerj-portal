"""Validation of the new player format and header-based dispatch."""
import pathlib
from unittest.mock import patch

from backend.validator import validate_inputs
from calculator.fide.ratinglist import FIDE_COLUMN_COUNT, FIDE_HEADER, LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER
from calculator.tunx_parser import BIO_MARKER, PAIRING_MARKER

_FIDE_PLAYERS = (
    FIDE_HEADER + "\n"
    "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
)
_LEGACY_PLAYERS = (
    LEGACY_HEADER + "\n"
    "1;;;Player One;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
)
# Task 16 dispatches tournaments.csv validation by mode: the FIDE and compare
# modes require the 8-column header (with TimeControl), so the fixture below
# uses calculator.fide.tournaments.TOURNAMENTS_HEADER for these fide-mode tests.
_TOURNAMENTS = TOURNAMENTS_HEADER + "\n1;99999;Test Tournament;2026-03-15;RR;0;1;STD\n"

# Fexerj ids of the six players baked into tests/binary/round_robin_6players.TURX
# (see tests/test_validator.py's _VALID_PLAYERS, which cross-checks the same file).
_BINARY_DIR = pathlib.Path(__file__).parent / "binary"
_BINARY_PLAYER_IDS = [3741, 643, 1979, 2831, 3541, 5400]
_TURX_DATA = (_BINARY_DIR / "round_robin_6players.TURX").read_bytes()


def _errors(players, mode, tournaments=_TOURNAMENTS, binaries=None):
    return validate_inputs(players, tournaments, binaries or {}, 1, 1, mode=mode)


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
    assert "12" in joined and "26" in joined


def test_peak_flag_must_be_zero_or_one():
    bad = _FIDE_PLAYERS.replace(";1800;50;0;", ";1800;50;7;")
    errors = _errors(bad, "fide")
    assert any("Peak2200_Std" in e for e in errors)


def test_rtg_non_numeric_is_rejected():
    bad = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;abc;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(bad, "fide")
    assert any("Rtg_Std deve ser inteiro ou vazio" in e for e in errors)


def test_games_non_numeric_is_rejected():
    bad = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;abc;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(bad, "fide")
    assert any("Games_Std deve ser um inteiro" in e for e in errors)


def test_sum_opp_non_numeric_is_rejected():
    bad = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;abc;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(bad, "fide")
    assert any("SumOpp_Std deve ser um inteiro não negativo" in e for e in errors)


def test_sum_opp_negative_is_rejected():
    bad = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;-5;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(bad, "fide")
    assert any("SumOpp_Std deve ser um inteiro não negativo" in e for e in errors)


def test_pts_non_numeric_is_rejected():
    bad = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;abc;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(bad, "fide")
    assert any("Pts_Std deve ser um número válido" in e for e in errors)


def test_acc_games_non_numeric_is_rejected():
    bad = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;abc;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(bad, "fide")
    assert any("AccGames_Std deve ser um inteiro" in e for e in errors)


def test_empty_rating_is_accepted():
    unrated = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;;0;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(unrated, "fide")
    assert not any("Rtg_Std" in e for e in errors)


def test_empty_rating_with_peak_flag_is_accepted():
    """Player who reached 2200 and later fell below the floor (§7)."""
    fallen = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;;300;1;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(fallen, "fide")
    assert not any("Peak2200_Std" in e for e in errors)


def test_legacy_mode_still_rejects_the_new_header():
    errors = _errors(_FIDE_PLAYERS, "legacy")
    assert any("cabeçalho" in e for e in errors)


def test_fide_mode_empty_file_reports_empty_not_bad_header():
    """An empty players.csv means a forgotten attachment, not a bad header."""
    errors = _errors("", "fide")
    assert any("arquivo vazio" in e for e in errors)
    assert not any("cabeçalho" in e for e in errors)


def test_wrong_column_count_is_rejected():
    bad = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0\n"
    )
    errors = _errors(bad, "fide")
    assert any(f"esperadas {FIDE_COLUMN_COUNT} colunas, encontradas 13" in e for e in errors)


def test_id_no_empty_is_rejected():
    no_id = (
        FIDE_HEADER + "\n"
        ";;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(no_id, "fide")
    assert any("Id_No é obrigatório" in e for e in errors)


def test_name_empty_is_rejected():
    no_name = (
        FIDE_HEADER + "\n"
        "1;;;;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(no_name, "fide")
    assert any("Name é obrigatório" in e for e in errors)


def test_missing_birthday_is_rejected():
    """§5.3: birthday becomes required in the per-game model — the under-18 K depends on it."""
    no_birthday = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;;M;BRA;1800;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(no_birthday, "fide")
    assert any("Birthday" in e for e in errors)


def test_duplicate_id_no_is_rejected():
    dup = (
        FIDE_HEADER + "\n"
        "1;;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
        "1;;;Player Two;CLUB A;01/01/1991;M;BRA;1600;40;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
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
        "1;999;;Player One;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
        "2;999;;Player Two;CLUB A;01/01/1991;M;BRA;1600;40;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    errors = _errors(dup, "fide")
    assert any("Id_CBX duplicado" in e for e in errors)


def test_unknown_mode_returns_error():
    errors = _errors(_FIDE_PLAYERS, "bogus")
    assert any("bogus" in e for e in errors)


# ---------------------------------------------------------------------------
# _build_players_index dispatch (binary-vs-rating-list cross-check)
#
# _build_players_index only knew the legacy 12-column format; fed a
# 26-column list, it returned an empty index, so every player in the binary
# was reported as absent from the rating list — the new-format mode was
# unusable end-to-end. These tests lock in the fix.
# ---------------------------------------------------------------------------

def _fide_row(id_no: int, id_cbx: str = "") -> str:
    return (
        f"{id_no};{id_cbx};;Player {id_no};CLUB A;01/01/1990;M;BRA;"
        "1500;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0"
    )


def _legacy_row(id_no: int, id_cbx: str = "") -> str:
    return f"{id_no};{id_cbx};;Player {id_no};1500;CLUB A;01/01/1990;M;BRA;50;0;0"


def _fide_players_list(ids: list[int]) -> str:
    return FIDE_HEADER + "\n" + "\n".join(_fide_row(i) for i in ids) + "\n"


def _legacy_players_list(ids: list[int]) -> str:
    return LEGACY_HEADER + "\n" + "\n".join(_legacy_row(i) for i in ids) + "\n"


def test_fide_format_players_list_matching_binary_returns_no_errors():
    """The bug case: a valid 26-column list with every binary player present."""
    players = _fide_players_list(_BINARY_PLAYER_IDS)
    errors = _errors(players, "fide", binaries={"1-99999.TURX": _TURX_DATA})
    assert errors == []


def test_fide_format_players_list_missing_one_binary_player_is_reported():
    missing_id = _BINARY_PLAYER_IDS[-1]
    players = _fide_players_list(_BINARY_PLAYER_IDS[:-1])
    errors = _errors(players, "fide", binaries={"1-99999.TURX": _TURX_DATA})
    assert any("ausente(s) da lista de rating" in e for e in errors)
    assert any(f"{missing_id} (" in e for e in errors)


def test_legacy_format_players_list_matching_binary_still_returns_no_errors():
    """Same pair of cases in the legacy 12-column format: behaviour unchanged."""
    players = _legacy_players_list(_BINARY_PLAYER_IDS)
    errors = _errors(players, "fide", binaries={"1-99999.TURX": _TURX_DATA})
    assert errors == []


def test_legacy_format_players_list_missing_one_binary_player_still_reported():
    missing_id = _BINARY_PLAYER_IDS[-1]
    players = _legacy_players_list(_BINARY_PLAYER_IDS[:-1])
    errors = _errors(players, "fide", binaries={"1-99999.TURX": _TURX_DATA})
    assert any("ausente(s) da lista de rating" in e for e in errors)
    assert any(f"{missing_id} (" in e for e in errors)


def test_irt_fide_format_translates_binary_id_via_id_cbx():
    """IRT tournaments key the binary's id off Id_CBX, not Id_No.

    The 26-column format must build that CBX→FEXERJ mapping from the same
    second column the legacy format uses.
    """
    tournaments = TOURNAMENTS_HEADER + "\n1;12345;IRT Memorial;2026-03-15;SS;1;1;STD\n"
    players = (
        FIDE_HEADER + "\n"
        "1;36633;;Player One;CLUB A;01/01/1990;M;BRA;1500;50;0;0;0;0;;0;0;0;0;0;;0;0;0;0;0\n"
    )
    data = BIO_MARKER + PAIRING_MARKER + b"\x00" * 64
    with patch(
        "backend.validator.parse_bio_section",
        return_value={
            1: {"name": "Listed Player", "fexerj_id": "36633"},
            2: {"name": "Unlisted Player", "fexerj_id": "90568"},
        },
    ):
        errors = _errors(
            players, "fide", tournaments=tournaments, binaries={"1-12345.TUNX": data}
        )
    missing = [e for e in errors if "ausente(s) da lista de rating" in e]
    assert len(missing) == 1
    assert "90568 (Unlisted Player)" in missing[0]
    assert "36633" not in missing[0]
