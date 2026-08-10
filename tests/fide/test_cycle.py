"""The per-game model's complete cycle."""
import pathlib

from calculator.fide import FideRatingCycle
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER
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


def _cycle(tournaments_csv, first=1, count=1, binaries=None):
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return FideRatingCycle(
        tournaments_csv=tournaments_csv,
        first_item=first,
        items_to_process=count,
        initial_rating_csv=_PLAYERS_CSV,
        binary_files=binaries if binaries is not None else {"1-99999.TURX": data},
    )


_ONE_TOURNAMENT = (
    TOURNAMENTS_HEADER + "\n"
    "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
)


class TestOutputShape:
    def test_produces_a_single_rating_list(self):
        """The two audit files arrive in Task 13."""
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert "RatingList.csv" in output

    def test_no_per_tournament_rating_list(self):
        """§4: an intermediate per-tournament list is not a valid output."""
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert not any(name.startswith("RatingList_after_") for name in output)

    def test_rating_list_uses_the_new_header(self):
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert output["RatingList.csv"].splitlines()[0] == FIDE_HEADER

    def test_every_player_survives_the_cycle(self):
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        lines = [row for row in output["RatingList.csv"].splitlines() if row]
        assert len(lines) == 7  # header + 6 players


class TestPeriodSemantics:
    def test_two_tournaments_together_differ_from_two_runs(self):
        """The structural difference between the models: the period is a single round."""
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        two = (
            TOURNAMENTS_HEADER + "\n"
            "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
            "2;99999;Torneio Dois;2026-04-20;RR;0;1;STD\n"
        )
        binaries = {"1-99999.TURX": data, "2-99999.TURX": data}
        together = _cycle(two, 1, 2, binaries).run_cycle()["RatingList.csv"]

        first = _cycle(two, 1, 1, binaries).run_cycle()["RatingList.csv"]
        second = FideRatingCycle(
            tournaments_csv=two, first_item=2, items_to_process=1,
            initial_rating_csv=first, binary_files=binaries,
        ).run_cycle()["RatingList.csv"]

        assert together != second

    def test_all_games_use_the_start_of_period_opponent_rating(self):
        """§4: the opponent's rating is also the one from the start of the period."""
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        two = (
            TOURNAMENTS_HEADER + "\n"
            "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
            "2;99999;Torneio Dois;2026-04-20;RR;0;1;STD\n"
        )
        binaries = {"1-99999.TURX": data, "2-99999.TURX": data}
        outcome = _cycle(two, 1, 2, binaries).run_period()
        by_pair = {}
        for result in outcome.results:
            for entry in result.game_results:
                key = (result.player_id, entry.game.opponent_id)
                by_pair.setdefault(key, set()).add(entry.opponent_rating)
        # The same pair plays in both tournaments; the opponent's rating never changes.
        assert all(len(values) == 1 for values in by_pair.values())


class TestModalities:
    def test_rapid_tournament_writes_the_rapid_columns(self):
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        rapid = TOURNAMENTS_HEADER + "\n1;99999;Torneio Rápido;2026-03-15;RR;0;1;RPD\n"
        output = _cycle(rapid, binaries={"1-99999.TURX": data}).run_cycle()
        header = output["RatingList.csv"].splitlines()[0].split(';')
        row = output["RatingList.csv"].splitlines()[1].split(';')
        assert row[header.index("Rtg_Rpd")] != ""
        assert row[header.index("Rtg_Std")] == "1800"   # Classical untouched
