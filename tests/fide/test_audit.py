"""Per-game and per-period audit files."""
import pathlib
from decimal import Decimal

from calculator.fide import FideRatingCycle
from calculator.fide.audit import (
    GAMES_AUDIT_HEADER,
    GAMES_AUDIT_PREAMBLE,
    PERIOD_AUDIT_HEADER,
    PERIOD_AUDIT_PREAMBLE,
)
from calculator.fide.ratinglist import LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

BINARY_DIR = pathlib.Path(__file__).parent.parent / 'binary'

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

_ONE_TOURNAMENT = TOURNAMENTS_HEADER + "\n1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"

_TWO_TOURNAMENTS = (
    TOURNAMENTS_HEADER + "\n"
    "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
    "2;99999;Torneio Dois;2026-04-20;RR;0;1;STD\n"
)


def _output():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return FideRatingCycle(_ONE_TOURNAMENT, 1, 1, _PLAYERS_CSV, {"1-99999.TURX": data}).run_cycle()


def _output_two_tournaments():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    binaries = {"1-99999.TURX": data, "2-99999.TURX": data}
    return FideRatingCycle(_TWO_TOURNAMENTS, 1, 2, _PLAYERS_CSV, binaries).run_cycle()


class TestGamesAudit:
    def test_preamble_and_header(self):
        lines = _output()["Audit_Games.csv"].splitlines()
        assert lines[0] == GAMES_AUDIT_PREAMBLE
        assert lines[1] == GAMES_AUDIT_HEADER

    def test_one_row_per_computed_game_side(self):
        """The fixture has 10 games among 6 players, so 20 sides."""
        lines = [r for r in _output()["Audit_Games.csv"].splitlines()[2:] if r]
        assert len(lines) == 20

    def test_row_lets_a_player_redo_the_math(self):
        """Opponent rating, D, PD, result and DeltaR all live on the same row."""
        header = GAMES_AUDIT_HEADER.split(';')
        row = _output()["Audit_Games.csv"].splitlines()[2].split(';')
        cells = dict(zip(header, row, strict=True))
        assert Decimal(cells["Score"]) - Decimal(cells["PD"]) == Decimal(cells["DeltaR"])


class TestPeriodAudit:
    def test_preamble_and_header(self):
        lines = _output()["Audit_Period.csv"].splitlines()
        assert lines[0] == PERIOD_AUDIT_PREAMBLE
        assert lines[1] == PERIOD_AUDIT_HEADER

    def test_one_row_per_player_and_modality(self):
        lines = [r for r in _output()["Audit_Period.csv"].splitlines()[2:] if r]
        assert len(lines) == 6

    def test_names_the_tournaments_of_the_period(self):
        """The generated list must not be orphaned from the slice that produced it."""
        header = PERIOD_AUDIT_HEADER.split(';')
        row = _output_two_tournaments()["Audit_Period.csv"].splitlines()[2].split(';')
        cells = dict(zip(header, row, strict=True))
        assert cells["Tournaments"] == "1,2"

    def test_rounded_variation_explains_the_new_rating(self):
        """Final rating = initial rating + rounded variation, except for players
        who fell below the floor."""
        header = PERIOD_AUDIT_HEADER.split(';')
        for line in _output()["Audit_Period.csv"].splitlines()[2:]:
            if not line:
                continue
            cells = dict(zip(header, line.split(';'), strict=True))
            if not cells["InitialRating"] or not cells["FinalRating"]:
                continue
            assert int(cells["FinalRating"]) - int(cells["InitialRating"]) == int(
                cells["RoundedVariation"]
            )

    def test_period_audit_agrees_with_the_games_audit(self):
        """The sum of DeltaR times K across the player's games must equal the
        period's variation."""
        output = _output()
        games_header = GAMES_AUDIT_HEADER.split(';')
        totals: dict[tuple[str, str], Decimal] = {}
        for line in output["Audit_Games.csv"].splitlines()[2:]:
            if not line:
                continue
            c = dict(zip(games_header, line.split(';'), strict=True))
            key = (c["PlayerId"], c["TimeControl"])
            totals[key] = totals.get(key, Decimal("0")) + Decimal(c["DeltaR"]) * Decimal(c["K"])

        period_header = PERIOD_AUDIT_HEADER.split(';')
        for line in output["Audit_Period.csv"].splitlines()[2:]:
            if not line:
                continue
            c = dict(zip(period_header, line.split(';'), strict=True))
            key = (c["PlayerId"], c["TimeControl"])
            assert Decimal(c["Variation"]) == totals.get(key, Decimal("0"))
