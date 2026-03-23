"""Tests for the input validator module."""
import pathlib
import textwrap

import pytest

from backend.validator import validate_inputs

BINARY_DIR = pathlib.Path(__file__).parent / "binary"
TURX_DATA = (BINARY_DIR / "round_robin_6players.TURX").read_bytes()
TUNX_MISSING_ID = (BINARY_DIR / "swiss_system_18players.TUNX").read_bytes()

_VALID_PLAYERS = textwrap.dedent("""\
    Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
    1;;;Player One;1500;CLUB A;01/01/1990;M;BRA;50;0;0
    2;36633;;Player Two;1800;CLUB B;15/06/1985;M;BRA;100;0;0
""")

_VALID_TOURNAMENTS = textwrap.dedent("""\
    Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
    1;99999;Test Tournament;2025-01-01;RR;0;1
""")

_VALID_BINARIES = {"1-99999.TURX": TURX_DATA}


def _validate(players=_VALID_PLAYERS, tournaments=_VALID_TOURNAMENTS,
              binaries=None, first=1, count=1):
    if binaries is None:
        binaries = _VALID_BINARIES
    return validate_inputs(players, tournaments, binaries, first, count)


# ---------------------------------------------------------------------------
# Players CSV
# ---------------------------------------------------------------------------

class TestPlayersCSVValidation:

    def test_valid_csv_returns_no_errors(self):
        assert _validate() == []

    def test_empty_file_returns_error(self):
        errors = _validate(players="")
        assert any("vazio" in e for e in errors)

    def test_wrong_header_returns_error(self):
        bad = "Id_No;Name\n1;Player One\n"
        errors = _validate(players=bad)
        assert any("cabeçalho inválido" in e for e in errors)

    def test_too_few_columns_returns_error(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;Player One
        """)
        errors = _validate(players=bad)
        assert any("esperadas 12 colunas" in e for e in errors)

    def test_missing_required_id_no(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            ;;;Player One;1500;;01/01/1990;M;BRA;50;0;0
        """)
        errors = _validate(players=bad)
        assert any("Id_No é obrigatório" in e for e in errors)

    def test_missing_required_name(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;;;;1500;;01/01/1990;M;BRA;50;0;0
        """)
        errors = _validate(players=bad)
        assert any("Name é obrigatório" in e for e in errors)

    def test_missing_required_rtg_nat(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;;;Player One;;;01/01/1990;M;BRA;50;0;0
        """)
        errors = _validate(players=bad)
        assert any("Rtg_Nat é obrigatório" in e for e in errors)

    def test_non_integer_id_no_returns_error(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            ABC;;;Player One;1500;;01/01/1990;M;BRA;50;0;0
        """)
        errors = _validate(players=bad)
        assert any("Id_No deve ser um número inteiro" in e for e in errors)

    def test_non_integer_rtg_nat_returns_error(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;;;Player One;HIGH;;01/01/1990;M;BRA;50;0;0
        """)
        errors = _validate(players=bad)
        assert any("Rtg_Nat deve ser um número inteiro" in e for e in errors)

    def test_non_float_total_points_returns_error(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;;;Player One;1500;;01/01/1990;M;BRA;50;0;X
        """)
        errors = _validate(players=bad)
        assert any("TotalPoints deve ser um número válido" in e for e in errors)

    def test_duplicate_id_no_returns_error(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;;;Player One;1500;;01/01/1990;M;BRA;50;0;0
            1;;;Player Two;1600;;01/01/1991;M;BRA;60;0;0
        """)
        errors = _validate(players=bad)
        assert any("Id_No duplicado" in e for e in errors)

    def test_duplicate_id_cbx_returns_error(self):
        bad = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;999;;Player One;1500;;01/01/1990;M;BRA;50;0;0
            2;999;;Player Two;1600;;01/01/1991;M;BRA;60;0;0
        """)
        errors = _validate(players=bad)
        assert any("Id_CBX duplicado" in e for e in errors)

    def test_empty_id_cbx_not_flagged_as_duplicate(self):
        csv = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;;;Player One;1500;;01/01/1990;M;BRA;50;0;0
            2;;;Player Two;1600;;01/01/1991;M;BRA;60;0;0
        """)
        assert _validate(players=csv) == []

    def test_optional_fields_may_be_empty(self):
        csv = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            1;;;;1500;;;; ;50;0;0
        """)
        errors = _validate(players=csv)
        # Optional fields being empty should not produce errors
        assert not any(f in " ".join(errors) for f in ["Id_CBX", "Title", "ClubName", "Birthday", "Sex", "Fed"])


# ---------------------------------------------------------------------------
# Tournaments CSV
# ---------------------------------------------------------------------------

class TestTournamentsCSVValidation:

    def test_valid_csv_returns_no_errors(self):
        assert _validate() == []

    def test_empty_file_returns_error(self):
        errors = _validate(tournaments="")
        assert any("vazio" in e for e in errors)

    def test_wrong_header_returns_error(self):
        bad = "Id;Name\n1;Test\n"
        errors = _validate(tournaments=bad)
        assert any("cabeçalho inválido" in e for e in errors)

    def test_invalid_type_returns_error(self):
        bad = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;Test;;XX;0;1
        """)
        errors = _validate(tournaments=bad)
        assert any("Type 'XX' inválido" in e for e in errors)

    def test_is_irt_not_zero_or_one_returns_error(self):
        bad = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;Test;;RR;2;1
        """)
        errors = _validate(tournaments=bad)
        assert any("IsIrt deve ser 0 ou 1" in e for e in errors)

    def test_is_fexerj_not_zero_or_one_returns_error(self):
        bad = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;Test;;RR;0;2
        """)
        errors = _validate(tournaments=bad)
        assert any("IsFexerj deve ser 0 ou 1" in e for e in errors)

    def test_date_may_be_empty(self):
        csv = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;Test;;RR;0;1
        """)
        assert _validate(tournaments=csv) == []

    def test_missing_required_name_returns_error(self):
        bad = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;;2025-01-01;RR;0;1
        """)
        errors = _validate(tournaments=bad)
        assert any("Name é obrigatório" in e for e in errors)

    def test_missing_required_cbx_id_returns_error(self):
        bad = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;;Test;2025-01-01;RR;0;1
        """)
        errors = _validate(tournaments=bad)
        assert any("CrId é obrigatório" in e for e in errors)


# ---------------------------------------------------------------------------
# Binary files
# ---------------------------------------------------------------------------

class TestBinaryFileValidation:

    def test_missing_binary_file_returns_error(self):
        errors = _validate(binaries={})
        assert any("não encontrado" in e for e in errors)

    def test_file_missing_bio_marker_returns_error(self):
        errors = _validate(binaries={"1-99999.TURX": b"\x00" * 100})
        assert any("marcador BIO ausente" in e for e in errors)

    def test_file_missing_pairing_marker_returns_error(self):
        from calculator.tunx_parser import BIO_MARKER
        errors = _validate(binaries={"1-99999.TURX": BIO_MARKER + b"\x00" * 100})
        assert any("marcador PAIRING ausente" in e for e in errors)

    def test_valid_turx_file_returns_no_errors(self):
        assert _validate() == []

    def test_file_with_missing_fexerj_id_returns_error(self):
        tournaments = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;12345;Test;;SS;0;1
        """)
        errors = _validate(
            tournaments=tournaments,
            binaries={"1-12345.TUNX": TUNX_MISSING_ID},
        )
        assert any("ID FEXERJ" in e for e in errors)

    def test_only_validates_files_in_range(self):
        """Tournaments outside [first, first+count) must not require binary files."""
        tournaments = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;Tournament 1;;RR;0;1
            2;99999;Tournament 2;;RR;0;1
        """)
        # Only process tournament 1 — tournament 2 binary missing but should not error
        errors = _validate(
            tournaments=tournaments,
            binaries={"1-99999.TURX": TURX_DATA},
            first=1,
            count=1,
        )
        assert errors == []


# ---------------------------------------------------------------------------
# validate_inputs integration
# ---------------------------------------------------------------------------

class TestValidateInputs:

    def test_all_valid_returns_empty_list(self):
        assert _validate() == []

    def test_tournaments_errors_suppress_binary_validation(self):
        """When tournaments CSV has errors, binary validation is skipped."""
        bad_tournaments = "Id;Name\n1;Test\n"  # wrong header
        errors = _validate(tournaments=bad_tournaments, binaries={})
        # There should be a tournaments error but NOT a "missing binary" error
        assert any("tournaments.csv" in e for e in errors)
        assert not any("não encontrado" in e for e in errors)

    def test_bom_encoded_players_csv_is_accepted(self):
        """UTF-8 BOM prefix must not cause a header mismatch."""
        assert _validate(players="\ufeff" + _VALID_PLAYERS) == []
