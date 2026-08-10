"""Per-game and per-period audit files."""
import pathlib
from decimal import Decimal

from calculator.fide import FideRatingCycle
from calculator.fide.audit import (
    GAMES_AUDIT_HEADER,
    GAMES_AUDIT_PREAMBLE,
    PERIOD_AUDIT_HEADER,
    PERIOD_AUDIT_PREAMBLE,
    write_games_audit,
    write_period_audit,
)
from calculator.fide.cycle import PeriodOutcome
from calculator.fide.model import Game, ModalityState, PlayerState
from calculator.fide.period import GameResult, PeriodResult, compute_unrated_period
from calculator.fide.ratinglist import LEGACY_HEADER
from calculator.fide.rules import capped_diff
from calculator.fide.tables import pd_for_diff
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


def _game_result(opponent_id, initial_rating, opponent_rating, score):
    diff = capped_diff(initial_rating, opponent_rating)
    pd = pd_for_diff(diff)
    game = Game(1, "STD", 1, opponent_id, Decimal(score))
    return GameResult(
        game=game,
        opponent_rating=opponent_rating,
        capped_diff=diff,
        pd=pd,
        delta=Decimal(score) - pd,
        k=20,
    )


class TestGamesAuditDiffCap:
    """A player redoing `InitialRating - OpponentRating` by hand must be able
    to tell, from the row itself, when the 400 cap changed D (Art. 68 §3)."""

    def _rows(self):
        capped = _game_result(opponent_id=901, initial_rating=1800, opponent_rating=1350, score="1")
        uncapped = _game_result(opponent_id=902, initial_rating=1800, opponent_rating=1750, score="0.5")
        result = PeriodResult(
            player_id=1,
            modality="STD",
            initial_rating=1800,
            games_counted=2,
            sum_delta=capped.delta + uncapped.delta,
            variation=capped.delta * capped.k + uncapped.delta * uncapped.k,
            rounded_variation=0,
            final_rating=1800,
            path="RATED",
            game_results=[capped, uncapped],
        )
        player = PlayerState(id_fexerj=1, name="Generic Player")
        outcome = PeriodOutcome(players={1: player}, tournaments=[], results=[result])

        header = GAMES_AUDIT_HEADER.split(';')
        lines = [r for r in write_games_audit(outcome).splitlines()[2:] if r]
        return {
            row["OpponentId"]: row
            for row in (dict(zip(header, line.split(';'), strict=True)) for line in lines)
        }

    def test_flags_the_row_where_the_cap_acted(self):
        """1800 vs 1350 is a raw diff of 450, capped down to 400."""
        row = self._rows()["901"]
        assert row["OpponentRating"] == "1350"
        assert row["D"] == "400"
        assert row["DiffCapped"] == "1"

    def test_does_not_flag_the_row_where_it_did_not(self):
        """1800 vs 1750 is a raw diff of 50, well under the cap."""
        row = self._rows()["902"]
        assert row["OpponentRating"] == "1750"
        assert row["D"] == "50"
        assert row["DiffCapped"] == "0"


class TestPeriodAuditAccumulator:
    """A player who gets their first rating this period has no per-game row
    (§6 isn't a per-game calculation), so the period audit itself must expose
    the accumulator the initial rating was built from."""

    def test_first_rating_exposes_accumulated_sum_and_points(self):
        state = ModalityState()  # games == 0: this is the player's first event
        games = [
            Game(1, "STD", 1, 901, Decimal("1")),
            Game(1, "STD", 1, 902, Decimal("1")),
            Game(1, "STD", 1, 903, Decimal("0.5")),
            Game(1, "STD", 1, 904, Decimal("0")),
            Game(1, "STD", 1, 905, Decimal("0")),
        ]
        opponent_ratings = {901: 1600, 902: 1650, 903: 1700, 904: 1550, 905: 1600}
        result = compute_unrated_period(1, "STD", state, games, opponent_ratings)
        assert result.path == "INITIAL_RATING"  # sanity check on the fixture

        player = PlayerState(id_fexerj=1, name="Generic Player")
        outcome = PeriodOutcome(players={1: player}, tournaments=[], results=[result])

        header = PERIOD_AUDIT_HEADER.split(';')
        row = write_period_audit(outcome).splitlines()[2].split(';')
        cells = dict(zip(header, row, strict=True))
        assert cells["AccumSumOpp"] == str(result.accumulated_sum_opponents) == "8100"
        assert cells["AccumPoints"] == str(result.accumulated_points) == "2.5"
        assert cells["AccumGames"] == str(result.accumulated_games) == "5"
