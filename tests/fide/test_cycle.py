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
    def test_produces_one_list_and_two_audits(self):
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert set(output) == {"RatingList.csv", "Audit_Games.csv", "Audit_Period.csv"}

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
        rows = [row.split(';') for row in output["RatingList.csv"].splitlines()[1:]]
        row = rows[0]
        assert row[header.index("Rtg_Rpd")] != ""
        assert row[header.index("Rtg_Std")] == "1800"   # Classical untouched
        # Discriminates against a broken opponent map: if transposed players were
        # excluded from Rapid's opponent-ratings map, every Rapid game would be
        # dropped and every player's Rapid rating would come out equal to their
        # (untouched) Classical rating — still non-empty, so the check above alone
        # would not catch it.
        assert any(r[header.index("Rtg_Rpd")] != r[header.index("Rtg_Std")] for r in rows)

    def test_two_modalities_in_the_same_period_evolve_independently(self):
        """A player entering both a Classical and a Rapid tournament in the
        same period must end up rated in both, with each modality's game
        count reflecting only that modality's own games."""
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        two = (
            TOURNAMENTS_HEADER + "\n"
            "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
            "2;99999;Torneio Dois;2026-04-20;RR;0;1;RPD\n"
        )
        binaries = {"1-99999.TURX": data, "2-99999.TURX": data}
        outcome = _cycle(two, 1, 2, binaries).run_period()
        player = outcome.players[3741]
        std = player.modalities["STD"]
        rpd = player.modalities["RPD"]

        assert std.rating is not None
        assert rpd.rating is not None
        # 3741 entered the period with 50 Classical games and none in Rapid;
        # the round robin adds 5 games to whichever modality it was played in.
        assert std.games == 55
        assert rpd.games == 5
        # Different starting K (established player vs. transposed newcomer)
        # means the two ratings move differently — proof the modalities were
        # computed independently rather than one clobbering the other.
        assert std.rating != rpd.rating


class TestUnratedAccumulatorAcrossPeriods:
    """§6.1: a player who hasn't reached five games yet must keep accumulating
    opponent sum and points from one period to the next, through the CSV
    round trip — this only breaks in the period *after* the one where it was
    introduced, which a single-period test can't see."""

    _PLAYERS_ONE_UNRATED = (
        LEGACY_HEADER + "\n"
        "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
        "643;;;Roberto Faria;0;CLUB B;01/01/1975;M;BRA;0;0;0\n"
        "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
        "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
        "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
        "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
    )

    def test_the_accumulator_survives_the_trip_through_the_csv_and_into_the_next_period(self):
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        binaries = {"1-99999.TURX": data}

        cycle_1 = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=self._PLAYERS_ONE_UNRATED, binary_files=binaries,
        )
        output_1 = cycle_1.run_cycle()["RatingList.csv"]
        header = output_1.splitlines()[0].split(';')
        row_1 = next(r for r in output_1.splitlines()[1:] if r.startswith("643;")).split(';')

        # Still unrated after period 1 (643 only plays 3 of the round robin's
        # games, short of the 5 needed for an initial rating), but the
        # accumulator moved off zero.
        assert row_1[header.index("Rtg_Std")] == ""
        assert row_1[header.index("AccSumOpp_Std")] != "0"
        assert row_1[header.index("AccPts_Std")] != "0"
        assert row_1[header.index("AccGames_Std")] == "3"
        assert row_1[header.index("AccSince_Std")] != ""

        cycle_2 = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=output_1, binary_files=binaries,
        )
        output_2 = cycle_2.run_cycle()["RatingList.csv"]
        row_2 = next(r for r in output_2.splitlines()[1:] if r.startswith("643;")).split(';')

        # The same round robin run again adds 3 more games, bringing the
        # two-period total to 6 — enough to finally publish a rating. That
        # only happens if period 2 picked up period 1's accumulator instead
        # of starting from zero.
        assert row_2[header.index("Rtg_Std")] != ""


class TestPeak2200IndicatorIsPermanent:
    """§5: once a player reaches 2200, K=10 is permanent from then on. The
    `reached_2200` indicator that drives it must never turn back off, even
    once the rating itself drops below 2200 again."""

    def test_the_indicator_stays_on_after_the_rating_falls_below_2200(self):
        players_csv = (
            FIDE_HEADER + "\n"
            "3741;;;Carlos Mendes;CLUB A;01/01/1980;M;BRA;"
            "2210;50;1;0;0;0;;;0;0;0;0;0;;;0;0;0;0;0;\n"
            "643;;;Roberto Faria;CLUB B;01/01/1975;M;BRA;"
            "1900;50;0;0;0;0;;;0;0;0;0;0;;;0;0;0;0;0;\n"
            "1979;;;Andre Nunes;CLUB C;01/01/1982;M;BRA;"
            "1850;50;0;0;0;0;;;0;0;0;0;0;;;0;0;0;0;0;\n"
            "2831;;;Felipe Borges;CLUB D;01/01/1978;M;BRA;"
            "1950;50;0;0;0;0;;;0;0;0;0;0;;;0;0;0;0;0;\n"
            "3541;;;Lucas Carvalho;CLUB E;01/01/1985;M;BRA;"
            "1800;50;0;0;0;0;;;0;0;0;0;0;;;0;0;0;0;0;\n"
            "5400;;;Bruno Teixeira;CLUB F;01/01/1995;M;BRA;"
            "1900;50;0;0;0;0;;;0;0;0;0;0;;;0;0;0;0;0;\n"
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        cycle = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        )
        output = cycle.run_cycle()["RatingList.csv"]
        header = output.splitlines()[0].split(';')
        row = next(r for r in output.splitlines()[1:] if r.startswith("3741;")).split(';')

        assert int(row[header.index("Rtg_Std")]) < 2210
        assert row[header.index("Peak2200_Std")] == "1"
