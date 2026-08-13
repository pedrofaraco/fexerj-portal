"""Validation rules that depend on the execution mode."""
from backend.validator import validate_inputs
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

_LEGACY_TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj"

_LEGACY_PLAYERS = (
    LEGACY_HEADER + "\n"
    "1;;;Carlos Mendes;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
)
# One rated Classical player in the 42-column format: nine identity columns
# (the last of them the §11.1 status), then eleven per modality.
_FIDE_PLAYERS = (
    FIDE_HEADER + "\n"
    + ";".join(
        ["1", "", "", "Carlos Mendes", "CLUB A", "01/01/1990", "M", "BRA", "1"]
        + ["1800", "50", "20", "1", "", "", "", "0", "0", "0", ""]
        + ["", "0", "40", "0", "", "", "", "0", "0", "0", ""] * 2
    )
    + "\n"
)
# 12-column format with Birthday (column 7 of LEGACY_HEADER) missing or
# unreadable — the compatibility path exercised on every run, which used to
# skip Birthday entirely because it delegated to the legacy validator.
_LEGACY_PLAYERS_NO_BIRTHDAY = (
    LEGACY_HEADER + "\n"
    "1;;;Carlos Mendes;1800;CLUB A;;M;BRA;50;0;0\n"
)
_LEGACY_PLAYERS_BAD_BIRTHDAY = (
    LEGACY_HEADER + "\n"
    "1;;;Carlos Mendes;1800;CLUB A;10/05/10;M;BRA;50;0;0\n"
)
_FIDE_TOURNAMENTS_SINGLE_STD = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"


def _errors(players, tournaments, mode):
    # count=1 mirrors the real API, whose routes declare count with a
    # minimum of 1 — count=0 would never reach the validator in production.
    return validate_inputs(players, tournaments, {}, 1, 1, mode=mode)


class TestTimeControl:
    def test_required_in_fide_mode(self):
        legacy_tournaments = _LEGACY_TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1\n"
        errors = _errors(_FIDE_PLAYERS, legacy_tournaments, "fide")
        assert any("TimeControl" in e for e in errors)

    def test_must_be_a_known_value(self):
        bad = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;RAPIDO\n"
        errors = _errors(_FIDE_PLAYERS, bad, "fide")
        assert any("STD" in e and "RPD" in e for e in errors)

    def test_not_required_in_legacy_mode(self):
        legacy_tournaments = _LEGACY_TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1\n"
        errors = _errors(_LEGACY_PLAYERS, legacy_tournaments, "legacy")
        assert not any("TimeControl" in e for e in errors)


class TestEndDate:
    def test_required_in_fide_mode_for_the_under_18_rule(self):
        no_date = TOURNAMENTS_HEADER + "\n1;99999;Torneio;;RR;0;1;STD\n"
        errors = _errors(_FIDE_PLAYERS, no_date, "fide")
        assert any("EndDate" in e for e in errors)

    def test_optional_in_legacy_mode(self):
        legacy_tournaments = _LEGACY_TOURNAMENTS_HEADER + "\n1;99999;Torneio;;RR;0;1\n"
        errors = _errors(_LEGACY_PLAYERS, legacy_tournaments, "legacy")
        assert not any("EndDate" in e for e in errors)


class TestBirthday:
    # Birthday is required by *mode* (fide/compare), not by the players.csv
    # column format. The hole: fide mode with the 12-column format — the
    # main compatibility path, exercised on every run — used to delegate
    # straight to the legacy validator, which never looks at Birthday at
    # all, so every under-18 player lost K=40 with no warning. compare mode
    # is worse: it *requires* the 12-column format, so the migration
    # comparison the federation will use to decide would always be wrong
    # for juniors.

    def test_required_in_fide_mode_with_12_column_format(self):
        errors = _errors(_LEGACY_PLAYERS_NO_BIRTHDAY, _FIDE_TOURNAMENTS_SINGLE_STD, "fide")
        assert any(
            "players.csv linha 2: Birthday é obrigatório no modelo por partida" == e
            for e in errors
        )

    def test_required_in_compare_mode(self):
        errors = _errors(_LEGACY_PLAYERS_NO_BIRTHDAY, _FIDE_TOURNAMENTS_SINGLE_STD, "compare")
        assert any(
            "players.csv linha 2: Birthday é obrigatório no modelo por partida" == e
            for e in errors
        )

    def test_still_optional_in_legacy_mode(self):
        legacy_tournaments = _LEGACY_TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1\n"
        errors = _errors(_LEGACY_PLAYERS_NO_BIRTHDAY, legacy_tournaments, "legacy")
        assert not any("Birthday" in e for e in errors)

    def test_unreadable_date_rejected_in_fide_mode(self):
        """A two-digit year like '10/05/10' must not pass as a readable date."""
        errors = _errors(_LEGACY_PLAYERS_BAD_BIRTHDAY, _FIDE_TOURNAMENTS_SINGLE_STD, "fide")
        assert any(
            "players.csv linha 2: Birthday '10/05/10' não foi reconhecida como uma data" == e
            for e in errors
        )

    def test_unreadable_date_rejected_in_compare_mode(self):
        errors = _errors(_LEGACY_PLAYERS_BAD_BIRTHDAY, _FIDE_TOURNAMENTS_SINGLE_STD, "compare")
        assert any(
            "players.csv linha 2: Birthday '10/05/10' não foi reconhecida como uma data" == e
            for e in errors
        )


class TestCompareModeRestrictions:
    def test_rejects_the_new_players_format(self):
        tournaments = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"
        errors = _errors(_FIDE_PLAYERS, tournaments, "compare")
        assert any("comparar" in e.lower() and "12" in e for e in errors)

    def test_rejects_non_std_tournaments(self):
        tournaments = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;BLZ\n"
        errors = _errors(_LEGACY_PLAYERS, tournaments, "compare")
        assert any("comparar" in e.lower() and "STD" in e for e in errors)

    def test_accepts_legacy_players_with_std_tournaments(self):
        tournaments = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"
        errors = _errors(_LEGACY_PLAYERS, tournaments, "compare")
        # With count=1 the tournament at Ord=1 falls inside the binary-file
        # window, and no binary file was supplied, so a "file not found"
        # error is expected and unrelated to this test.  What this test
        # actually verifies is that the compare mode's own restrictions
        # (players format, tournament time control) do not fire.
        assert not any("comparar" in e.lower() for e in errors)


class TestEndDateIsReadable:
    """EndDate stops being decoration in the per-game model: the period's year
    and month come out of it. An unreadable one used to pass validation and
    blow up mid-run as a 422, which reads as a portal failure rather than a
    file to fix."""

    # Ord 5 sits outside the 1..1 window `_errors` validates, so no binary is
    # expected for it — the row-level EndDate check runs either way.
    def test_accepts_the_dotted_format_the_federation_exports(self):
        tournaments = TOURNAMENTS_HEADER + "\n5;99999;Torneio;25.01.2026;SS;0;0;STD\n"
        assert _errors(_FIDE_PLAYERS, tournaments, "fide") == []

    def test_rejects_an_excel_serial_at_validation_time(self):
        tournaments = TOURNAMENTS_HEADER + "\n5;99999;Torneio;24857;SS;0;0;STD\n"
        errors = _errors(_FIDE_PLAYERS, tournaments, "fide")
        assert any("EndDate" in e and "24857" in e for e in errors)

    def test_names_the_formats_it_accepts(self):
        tournaments = TOURNAMENTS_HEADER + "\n5;99999;Torneio;janeiro de 2026;SS;0;0;STD\n"
        errors = _errors(_FIDE_PLAYERS, tournaments, "fide")
        assert any("AAAA-MM-DD" in e and "DD.MM.AAAA" in e for e in errors)

    def test_stays_optional_in_the_current_model(self):
        legacy = _LEGACY_TOURNAMENTS_HEADER + "\n5;99999;Torneio;24857;SS;0;0\n"
        assert not any("EndDate" in e for e in _errors(_LEGACY_PLAYERS, legacy, "legacy"))


class TestDuplicateOrd:
    def test_rejected_in_fide_mode_too(self):
        """The per-game engine pools every game under its tournament's Ord, so
        two rows sharing one become a single tournament — with §6.1's
        first-tournament discard reading the merged result."""
        duplicated = (
            TOURNAMENTS_HEADER + "\n"
            "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
            "1;88888;Torneio Dois;2026-04-20;RR;0;1;STD\n"
        )
        errors = _errors(_FIDE_PLAYERS, duplicated, "fide")
        assert any("Ord duplicado" in e for e in errors)


class TestTournamentsColumnReductionIsCsvAware:
    # _validate_tournaments_for_mode reduces the 8-column fide/compare rows
    # to 7 columns to reuse the legacy row checks. That reduction must
    # operate on parsed CSV cells, not a raw string split, so a quoted field
    # containing ';' round-trips correctly.

    def test_accepts_a_quoted_name_containing_a_semicolon(self):
        tournaments = (
            TOURNAMENTS_HEADER + "\n"
            '5;99999;"Torneio; Aberto";2026-03-15;RR;0;1;STD\n'
        )
        errors = _errors(_FIDE_PLAYERS, tournaments, "fide")
        assert errors == []

    def test_unclosed_quote_does_not_hide_a_later_rows_defects(self):
        tournaments = (
            TOURNAMENTS_HEADER + "\n"
            '1;99999;"A;B;C;D;E;F";2026-03-15;RR;0;1;STD\n'
            "2;99999;Torneio Ruim;2026-03-16;XX;9;9;STD\n"
        )
        errors = _errors(_FIDE_PLAYERS, tournaments, "fide")
        assert any("linha 3" in e and "Type" in e for e in errors)
        assert any("linha 3" in e and "IsIrt" in e for e in errors)
        assert any("linha 3" in e and "IsFexerj" in e for e in errors)
