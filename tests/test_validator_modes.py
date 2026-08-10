"""Validation rules that depend on the execution mode."""
from backend.validator import validate_inputs
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

_LEGACY_TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj"

_LEGACY_PLAYERS = (
    LEGACY_HEADER + "\n"
    "1;;;Carlos Mendes;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
)
_FIDE_PLAYERS = (
    FIDE_HEADER + "\n"
    "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;;0;0;0;0;;0;0;0;0\n"
)


def _errors(players, tournaments, mode):
    # count=0 keeps the tournament window empty, since these tests are only
    # about mode-dependent header/field rules, not about the (unrelated)
    # binary-file presence check.
    return validate_inputs(players, tournaments, {}, 1, 0, mode=mode)


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
        assert errors == []
