"""Validation of the new player format and header-based dispatch."""
import pathlib
from unittest.mock import patch

from backend.validator import validate_inputs
from calculator.fide.ratinglist import FIDE_COLUMN_COUNT, FIDE_HEADER, LEGACY_HEADER
from calculator.fide.rules import RATING_FLOOR
from calculator.fide.tournaments import TOURNAMENTS_HEADER
from calculator.tunx_parser import BIO_MARKER, PAIRING_MARKER

# The 42-column row, built field by field: hand-written semicolon strings are
# unreadable at this width and shift silently when a column is added.
_MODALITY_DEFAULTS = {
    "rtg": "", "games": "0", "k": "40", "first": "0", "last": "",
    "fide": "", "fide_date": "", "acc_games": "0", "acc_sum": "0",
    "acc_pts": "0", "acc_since": "",
}
_MODALITY_FIELDS = tuple(_MODALITY_DEFAULTS)


def _row(id_no="1", id_cbx="", title="", name="Player One",
         club="CLUB A", birthday="01/01/1990", sex="M", fed="BRA", status="1",
         rpd=None, **std) -> str:
    """One row of the 42-column format. Keyword arguments override the
    Classical group; `rpd` does the same for Rapid, as a dict."""
    cells = [id_no, id_cbx, title, name, club, birthday, sex, fed, status]
    for group in (_MODALITY_DEFAULTS | std, _MODALITY_DEFAULTS | (rpd or {}), _MODALITY_DEFAULTS):
        cells += [str(group[field]) for field in _MODALITY_FIELDS]
    return ";".join(cells)


def _players(*rows: str) -> str:
    return "\n".join([FIDE_HEADER, *rows]) + "\n"


_RATED = {"rtg": "1800", "games": "50", "k": "20", "first": "1"}
_FIDE_PLAYERS = _players(_row(**_RATED))
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
    assert "12" in joined and str(FIDE_COLUMN_COUNT) in joined


class TestKFactorColumn:
    """§5, decided by FEXERJ: the K column is written by the program and is
    itself the record of the permanent K=10. It is the one column an operator
    can corrupt into changing a calculation, so nothing outside 10/20/40 gets
    through."""

    def test_a_value_outside_the_three_factors_is_rejected(self):
        errors = _errors(_players(_row(**_RATED | {"k": "7"})), "fide")
        assert any("K_Std deve ser 10, 20, 40" in e for e in errors)

    def test_blank_is_rejected(self):
        """Blank would read as "never reached 2200" and quietly drop a
        legitimate K=10."""
        errors = _errors(_players(_row(**_RATED | {"k": ""})), "fide")
        assert any("K_Std deve ser" in e for e in errors)

    def test_each_of_the_three_factors_is_accepted(self):
        for k in ("10", "20", "40"):
            errors = _errors(_players(_row(**_RATED | {"k": k})), "fide")
            assert not any("K_Std" in e for e in errors), k

    def test_k10_below_2200_is_accepted(self):
        """That is the permanence of §5 at work — the player reached 2200 and
        came back down — not a corrupt cell."""
        errors = _errors(_players(_row(**_RATED | {"rtg": "1500", "k": "10"})), "fide")
        assert not any("K_Std" in e for e in errors)

    def test_k10_on_an_unrated_player_is_accepted(self):
        """Whoever the floor (§7) dropped keeps the permanence."""
        errors = _errors(_players(_row(k="10", games="300")), "fide")
        assert not any("K_Std" in e for e in errors)


def test_rtg_non_numeric_is_rejected():
    bad = _players(_row(**_RATED | {"rtg": "abc"}))
    errors = _errors(bad, "fide")
    assert any("Rtg_Std deve ser inteiro ou vazio" in e for e in errors)


def test_games_non_numeric_is_rejected():
    bad = _players(_row(**_RATED | {"games": "abc"}))
    errors = _errors(bad, "fide")
    assert any("Games_Std deve ser um inteiro" in e for e in errors)


def test_sum_opp_non_numeric_is_rejected():
    bad = _players(_row(**_RATED | {"acc_sum": "abc"}))
    errors = _errors(bad, "fide")
    assert any("AccSumOpp_Std deve ser um inteiro não negativo" in e for e in errors)


def test_sum_opp_negative_is_rejected():
    bad = _players(_row(**_RATED | {"acc_sum": "-5"}))
    errors = _errors(bad, "fide")
    assert any("AccSumOpp_Std deve ser um inteiro não negativo" in e for e in errors)


def test_pts_non_numeric_is_rejected():
    bad = _players(_row(**_RATED | {"acc_pts": "abc"}))
    errors = _errors(bad, "fide")
    assert any("AccPts_Std deve ser um número válido" in e for e in errors)


def test_acc_games_non_numeric_is_rejected():
    bad = _players(_row(**_RATED | {"acc_games": "abc"}))
    errors = _errors(bad, "fide")
    assert any("AccGames_Std deve ser um inteiro" in e for e in errors)


def test_acc_since_bad_format_is_rejected():
    bad = _players(_row(**_RATED | {"acc_since": "2026"}))
    errors = _errors(bad, "fide")
    assert any("AccSince_Std deve ser vazio ou uma data no formato AAAA-MM" in e for e in errors)


def test_acc_since_valid_year_month_is_accepted():
    ok = _players(_row(**_RATED | {"acc_since": "2026-01"}))
    errors = _errors(ok, "fide")
    assert not any("AccSince_Std" in e for e in errors)


def test_acc_since_empty_is_accepted():
    errors = _errors(_FIDE_PLAYERS, "fide")
    assert not any("AccSince_Std" in e for e in errors)


def test_empty_rating_is_accepted():
    unrated = _players(_row())
    errors = _errors(unrated, "fide")
    assert not any("Rtg_Std" in e for e in errors)


def test_empty_rating_with_the_permanent_k10_is_accepted():
    """Player who reached 2200 and later fell below the floor (§7)."""
    fallen = _players(_row(games="300", k="10", first="1"))
    errors = _errors(fallen, "fide")
    assert not any("players.csv" in e for e in errors)


class TestRatingFloor:
    """A rating column in the 42-column format must be empty or >= RATING_FLOOR (§7).

    Empty means "unrated" in this format. Nothing used to stop a literal
    "0" from being accepted as a rating, so the player was read as rated at
    zero. The bug is invisible in the final list — the zero-rated player
    falls below the floor and drops out, same as an empty rating would — it
    is the player's *opponents* who lose points, because the games count in
    their calculation instead of being discarded as unrated.
    """

    @staticmethod
    def _players(rating: str) -> str:
        return _players(_row(**_RATED | {"rtg": rating}))

    def test_zero_is_rejected(self):
        errors = _errors(self._players("0"), "fide")
        assert any(
            "players.csv linha 2: Rtg_Std deve ser vazio ou um inteiro maior ou igual ao piso de "
            f"{RATING_FLOOR}" == e
            for e in errors
        )

    def test_empty_is_accepted(self):
        errors = _errors(self._players(""), "fide")
        assert not any("Rtg_Std" in e for e in errors)

    def test_exact_floor_is_accepted(self):
        errors = _errors(self._players(str(RATING_FLOOR)), "fide")
        assert not any("Rtg_Std" in e for e in errors)

    def test_just_below_floor_is_rejected(self):
        errors = _errors(self._players(str(RATING_FLOOR - 1)), "fide")
        assert any(
            "players.csv linha 2: Rtg_Std deve ser vazio ou um inteiro maior ou igual ao piso de "
            f"{RATING_FLOOR}" == e
            for e in errors
        )


def test_legacy_mode_still_rejects_the_new_header():
    errors = _errors(_FIDE_PLAYERS, "legacy")
    assert any("cabeçalho" in e for e in errors)


def test_fide_mode_empty_file_reports_empty_not_bad_header():
    """An empty players.csv means a forgotten attachment, not a bad header."""
    errors = _errors("", "fide")
    assert any("arquivo vazio" in e for e in errors)
    assert not any("cabeçalho" in e for e in errors)


def test_wrong_column_count_is_rejected():
    bad = FIDE_HEADER + "\n" + ";".join(["1"] * 13) + "\n"
    errors = _errors(bad, "fide")
    assert any(f"esperadas {FIDE_COLUMN_COUNT} colunas, encontradas 13" in e for e in errors)


def test_id_no_empty_is_rejected():
    no_id = _players(_row(id_no="", **_RATED))
    errors = _errors(no_id, "fide")
    assert any("Id_No é obrigatório" in e for e in errors)


def test_name_empty_is_rejected():
    no_name = _players(_row(name="", **_RATED))
    errors = _errors(no_name, "fide")
    assert any("Name é obrigatório" in e for e in errors)


def test_missing_birthday_is_rejected():
    """§5.3: birthday becomes required in the per-game model — the under-18 K depends on it."""
    no_birthday = _players(_row(birthday="", **_RATED))
    errors = _errors(no_birthday, "fide")
    assert any("Birthday" in e for e in errors)


def test_unreadable_birthday_is_rejected():
    """A two-digit year like '10/05/10' must not silently pass as a readable date.

    parse_birth_year (calculator.fide.rules) only matches four consecutive
    digits, so this used to slip through the old empty-check unnoticed and
    drop the under-18 K=40 for that player at calculation time.
    """
    unreadable = _players(_row(birthday="10/05/10", **_RATED))
    errors = _errors(unreadable, "fide")
    assert any(
        "players.csv linha 2: Birthday '10/05/10' não foi reconhecida como uma data" == e
        for e in errors
    )


def test_duplicate_id_no_is_rejected():
    dup = _players(
        _row(**_RATED),
        _row(name="Player Two", **_RATED | {"rtg": "1600", "games": "40"}),
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
    dup = _players(
        _row(id_cbx="999", **_RATED),
        _row(id_no="2", id_cbx="999", name="Player Two", **_RATED),
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
# 29-column list, it returned an empty index, so every player in the binary
# was reported as absent from the rating list — the new-format mode was
# unusable end-to-end. These tests lock in the fix.
# ---------------------------------------------------------------------------

def _fide_row(id_no: int, id_cbx: str = "") -> str:
    return _row(id_no=str(id_no), id_cbx=id_cbx, name=f"Player {id_no}",
                rtg="1500", games="50", k="20", first="1")


def _legacy_row(id_no: int, id_cbx: str = "") -> str:
    return f"{id_no};{id_cbx};;Player {id_no};1500;CLUB A;01/01/1990;M;BRA;50;0;0"


def _fide_players_list(ids: list[int]) -> str:
    return _players(*(_fide_row(i) for i in ids))


def _legacy_players_list(ids: list[int]) -> str:
    return LEGACY_HEADER + "\n" + "\n".join(_legacy_row(i) for i in ids) + "\n"


def test_fide_format_players_list_matching_binary_returns_no_errors():
    """The bug case: a valid 42-column list with every binary player present."""
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

    The 42-column format must build that CBX→FEXERJ mapping from the same
    second column the legacy format uses.
    """
    tournaments = TOURNAMENTS_HEADER + "\n1;12345;IRT Memorial;2026-03-15;SS;1;1;STD\n"
    players = _players(_row(id_cbx="36633", rtg="1500", games="50", k="20", first="1"))
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


class TestStatusColumn:
    """§11.1: the status governs publication, not calculation."""

    def test_each_documented_status_is_accepted(self):
        for status in ("0", "1", "2", "3", "4"):
            errors = _errors(_players(_row(status=status, **_RATED)), "fide")
            assert not any("Status" in e for e in errors), status

    def test_an_undocumented_status_is_rejected(self):
        errors = _errors(_players(_row(status="9", **_RATED)), "fide")
        assert any("Status deve ser 0, 1, 2, 3, 4" in e for e in errors)

    def test_an_empty_status_is_rejected(self):
        errors = _errors(_players(_row(status="", **_RATED)), "fide")
        assert any("Status deve ser" in e for e in errors)

    def test_a_deceased_player_with_games_is_accepted(self):
        """Asked for by FEXERJ: death happens mid-cycle, with tournaments
        already under way. A validator that refused this would stop the
        federation's own list on the month it matters."""
        deceased = _players(_row(status="4", **_RATED | {"games": "120"}))
        errors = _errors(deceased, "fide")
        assert not any("players.csv" in e for e in errors)

    def test_a_deceased_player_mid_accumulation_is_accepted(self):
        deceased = _players(_row(
            status="4", games="3", acc_games="3", acc_sum="4800",
            acc_pts="1.5", acc_since="2026-01", first="1",
        ))
        errors = _errors(deceased, "fide")
        assert not any("players.csv" in e for e in errors)


class TestFirstTournamentColumn:
    def test_zero_and_one_are_accepted(self):
        for value in ("0", "1"):
            errors = _errors(_players(_row(**_RATED | {"first": value})), "fide")
            assert not any("FirstTrn_Std" in e for e in errors), value

    def test_anything_else_is_rejected(self):
        errors = _errors(_players(_row(**_RATED | {"first": "2"})), "fide")
        assert any("FirstTrn_Std deve ser 0 ou 1" in e for e in errors)


class TestLastPlayedColumn:
    def test_a_year_month_is_accepted(self):
        errors = _errors(_players(_row(**_RATED | {"last": "2026-03"})), "fide")
        assert not any("LastPlayed_Std" in e for e in errors)

    def test_empty_is_accepted(self):
        """A player who has never played in that modality."""
        errors = _errors(_players(_row(**_RATED)), "fide")
        assert not any("LastPlayed_Std" in e for e in errors)

    def test_a_full_date_is_rejected(self):
        errors = _errors(_players(_row(**_RATED | {"last": "2026-03-15"})), "fide")
        assert any("LastPlayed_Std deve ser vazio ou uma data no formato AAAA-MM" in e
                   for e in errors)


class TestFideRatingColumns:
    """§6.4. The rating and the date it was checked travel together."""

    def test_a_rating_with_its_date_is_accepted(self):
        errors = _errors(
            _players(_row(fide="2300", fide_date="10/07/2026")), "fide"
        )
        assert not any("Fide" in e for e in errors)

    def test_the_three_date_formats_are_accepted(self):
        for date in ("2026-07-10", "10/07/2026", "10.07.2026"):
            errors = _errors(_players(_row(fide="2300", fide_date=date)), "fide")
            assert not any("Fide" in e for e in errors), date

    def test_a_rating_without_a_date_is_rejected(self):
        errors = _errors(_players(_row(fide="2300")), "fide")
        assert any("FideDate_Std é obrigatório quando RtgFide_Std está preenchido" in e
                   for e in errors)

    def test_a_date_without_a_rating_is_rejected(self):
        errors = _errors(_players(_row(fide_date="10/07/2026")), "fide")
        assert any("FideDate_Std só se preenche junto com RtgFide_Std" in e for e in errors)

    def test_an_unreadable_date_is_rejected(self):
        errors = _errors(_players(_row(fide="2300", fide_date="julho")), "fide")
        assert any("FideDate_Std 'julho' não foi reconhecida como uma data" in e
                   for e in errors)

    def test_a_rating_below_the_floor_is_rejected(self):
        """§6.4 enters the rating at face value, and §7 admits no rated
        player below the floor."""
        errors = _errors(
            _players(_row(fide=str(RATING_FLOOR - 1), fide_date="10/07/2026")), "fide"
        )
        assert any(
            "players.csv linha 2: RtgFide_Std deve ser vazio ou um inteiro maior ou igual "
            f"ao piso de {RATING_FLOOR}" == e
            for e in errors
        )

    def test_a_rating_at_the_floor_is_accepted(self):
        errors = _errors(
            _players(_row(fide=str(RATING_FLOOR), fide_date="10/07/2026")), "fide"
        )
        assert not any("RtgFide_Std" in e for e in errors)

    def test_a_non_numeric_rating_is_rejected(self):
        errors = _errors(_players(_row(fide="abc", fide_date="10/07/2026")), "fide")
        assert any("RtgFide_Std deve ser inteiro ou vazio" in e for e in errors)

    def test_the_columns_are_checked_per_modality(self):
        errors = _errors(_players(_row(rpd={"fide": "2300"})), "fide")
        assert any("FideDate_Rpd é obrigatório" in e for e in errors)
        assert not any("FideDate_Std" in e for e in errors)
