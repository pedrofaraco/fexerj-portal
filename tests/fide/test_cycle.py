"""The per-game model's complete cycle."""
import pathlib
from decimal import Decimal

from calculator.fide import FideRatingCycle
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER
from calculator.tunx_parser import parse_bio_section

BINARY_DIR = pathlib.Path(__file__).parent.parent / 'binary'


_EMPTY_MODALITY = ["", "0", "40", "0", "", "", "", "0", "0", "0", ""]
_STD_FIELDS = (
    "rtg", "games", "k", "first", "last", "fide", "fide_date",
    "acc_games", "acc_sum", "acc_pts", "acc_since",
)


def _player_row(id_no, name, birthday="01/01/1980", status="1", **std) -> str:
    """One row of the 42-column format.

    Keyword arguments override the Classical group, field by field; a `rpd`
    dict does the same for Rapid. Blitz always stays empty. The K passed in
    has to be the one §5 produces for the state alongside it, because the
    column is also the record of the permanent K=10 (§5): a 10 on the way in
    says this player has already reached 2200.
    """
    rpd = std.pop("rpd", None) or {}
    empty = dict(zip(_STD_FIELDS, _EMPTY_MODALITY, strict=True))
    cells = [str(id_no), "", "", name, "CLUB", birthday, "M", "BRA", status]
    for group in (empty | std, empty | rpd):
        cells += [str(group[field]) for field in _STD_FIELDS]
    cells += _EMPTY_MODALITY
    return ";".join(cells)


def _players_csv(*rows: str) -> str:
    return "\n".join([FIDE_HEADER, *rows]) + "\n"


def _rated(id_no, name, birthday, rating, k, games=50) -> str:
    return _player_row(id_no, name, birthday, rtg=rating, games=games, k=k, first="1")


def _audit_rows(csv_text: str) -> list[dict[str, str]]:
    """Audit rows as dicts, keyed by column name — the file carries a
    preamble line before its header."""
    lines = csv_text.splitlines()
    header = lines[1].split(";")
    return [dict(zip(header, line.split(";"), strict=True)) for line in lines[2:]]


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
    def test_produces_one_list_and_three_audits(self):
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert set(output) == {
            "RatingList.csv", "Audit_Games.csv", "Audit_Period.csv", "Audit_Checks.csv",
        }

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


class TestEmptyWindow:
    """A window that catches no tournament is an operator mistake — a mistyped
    interval. The current engine produces no files at all, which the backend
    turns into a 422; the per-game engine must not answer it with a full
    RatingList.csv the operator cannot tell from a published list."""

    def test_no_tournament_in_the_window_produces_no_files(self):
        output = _cycle(_ONE_TOURNAMENT, first=99, count=1, binaries={}).run_cycle()
        assert output == {}

    def test_the_outcome_of_an_empty_window_reports_itself_as_empty(self):
        outcome = _cycle(_ONE_TOURNAMENT, first=99, count=1, binaries={}).run_period()
        assert outcome.is_empty_window
        assert not _cycle(_ONE_TOURNAMENT).run_period().is_empty_window


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
        players_csv = _players_csv(
            _rated("3741", "Carlos Mendes", "01/01/1980", 2210, 10),
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
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
        assert row[header.index("K_Std")] == "10"


class TestCadastralColumnsSurviveTheCycle:
    """§11.1: the status and the two FIDE columns are the operator's. The
    program reads them and writes them back untouched."""

    def _run(self, status="4"):
        players_csv = _players_csv(
            _player_row("3741", "Carlos Mendes", status=status,
                        rtg=1800, games=50, k=20, first="1",
                        fide=1750, fide_date="10/07/2026"),
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()["RatingList.csv"]
        header = output.splitlines()[0].split(";")
        row = next(r for r in output.splitlines()[1:] if r.startswith("3741;")).split(";")
        return dict(zip(header, row, strict=True))

    def test_a_deceased_player_is_still_calculated(self):
        """The status governs publication, not calculation: someone who died
        mid-cycle has tournaments in flight."""
        row = self._run(status="4")
        assert row["Status"] == "4"
        assert row["Games_Std"] == "55"          # 50 on file plus the five played

    def test_every_status_is_calculated_and_written_back(self):
        """No status is a reason to skip a player, and none is a reason to
        leave them out of the file the cycle writes. Taking the unpublished
        ones out happens at publication, by the federation, outside the run.

        Status 2 is the one worth naming: a grampo is the temporary id of a
        player who has not federated yet, and reading "não-federado" as "do
        not calculate" is the mistake this test exists to stop — it was in
        the spec itself until 2026-08-13.
        """
        for status in ("0", "1", "2", "3", "4"):
            row = self._run(status=status)
            assert row["Status"] == status, status
            assert row["Games_Std"] == "55", status
            assert row["Rtg_Std"] != "", status

    def test_the_fide_columns_are_written_back(self):
        row = self._run()
        assert row["RtgFide_Std"] == "1750"
        assert row["FideDate_Std"] == "10/07/2026"


class TestActivityAndFirstTournamentMarkers:
    def _run(self, newcomer):
        players_csv = _players_csv(
            newcomer,
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()["RatingList.csv"]
        header = output.splitlines()[0].split(";")
        return {
            row.split(";")[0]: dict(zip(header, row.split(";"), strict=True))
            for row in output.splitlines()[1:]
        }

    def test_last_played_is_stamped_with_the_period(self):
        """The tournament ends 2026-03-15, so the period is 2026-03."""
        rows = self._run(_rated("3741", "Carlos Mendes", "01/01/1980", 1800, 20))
        assert rows["3741"]["LastPlayed_Std"] == "2026-03"
        assert rows["643"]["LastPlayed_Std"] == "2026-03"

    def test_the_other_modalities_are_left_alone(self):
        """Activity is per modality: a Classical tournament says nothing
        about Rapid."""
        rows = self._run(_rated("3741", "Carlos Mendes", "01/01/1980", 1800, 20))
        assert rows["3741"]["LastPlayed_Rpd"] == ""

    def test_a_newcomer_spends_the_discard_on_their_first_tournament(self):
        rows = self._run(_player_row("3741", "Carlos Mendes"))
        assert rows["3741"]["FirstTrn_Std"] == "1"

    def test_the_marker_stays_on_for_a_player_who_already_had_it(self):
        rows = self._run(_rated("3741", "Carlos Mendes", "01/01/1980", 1800, 20))
        assert rows["3741"]["FirstTrn_Std"] == "1"


class TestEntryOnAFideRating:
    """§6.4: a player arriving with a FIDE rating enters on it, at face
    value, without the initial-rating calculation and without the §1.1
    carry-over."""

    def _run(self, entrant):
        players_csv = _players_csv(
            entrant,
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()
        header = output["RatingList.csv"].splitlines()[0].split(";")
        row = next(
            r for r in output["RatingList.csv"].splitlines()[1:] if r.startswith("3741;")
        ).split(";")
        period = next(r for r in _audit_rows(output["Audit_Period.csv"]) if r["PlayerId"] == "3741")
        games = [r for r in _audit_rows(output["Audit_Games.csv"]) if r["PlayerId"] == "3741"]
        return dict(zip(header, row, strict=True)), period, games

    def test_the_period_is_calculated_from_the_fide_rating(self):
        _, period, _ = self._run(
            _player_row("3741", "Carlos Mendes", fide=2300, fide_date="10/07/2026")
        )
        assert period["InitialRating"] == "2300"
        assert period["Path"] == "FIDE_ENTRY"

    def test_the_k_comes_from_the_rating_band_not_the_game_count(self):
        """Zero games in the federation would otherwise mean the new-player
        K=40. A rating of 1900 puts them in the K=20 band."""
        _, _, games = self._run(
            _player_row("3741", "Carlos Mendes", fide=1900, fide_date="10/07/2026")
        )
        assert games
        assert {row["K"] for row in games} == {"20"}

    def test_2200_or_more_locks_k10_even_if_the_period_ends_below_it(self):
        """The indicator is switched on at entry, so losing a few points in
        the first period cannot take it away again."""
        row, _, _ = self._run(
            _player_row("3741", "Carlos Mendes", fide=2201, fide_date="10/07/2026")
        )
        assert int(row["Rtg_Std"]) < 2200
        assert row["K_Std"] == "10"

    def test_a_player_with_games_in_the_modality_does_not_re_enter(self):
        """Whoever the floor dropped (§7) would otherwise come back at their
        FIDE rating every single period. They take the ordinary unrated road
        back instead: the five games of §6.1 and the §6.3 formula, which is
        what puts them a long way from the 2300 on file."""
        row, period, _ = self._run(
            _player_row("3741", "Carlos Mendes", games=40, first="1", k=20,
                        fide=2300, fide_date="10/07/2026")
        )
        assert period["Path"] == "INITIAL_RATING"
        assert period["InitialRating"] == ""      # entered the period unrated
        assert int(row["Rtg_Std"]) < 2000         # §6.3's cap, not the FIDE rating

    def test_a_fide_rating_beats_the_cross_modality_carry_over(self):
        """§1.1 defers to §6.4. The player holds a Classical rating that
        would otherwise carry into Rapid at K=40, and a Rapid FIDE rating
        that takes precedence over it."""
        players_csv = _players_csv(
            _player_row("3741", "Carlos Mendes", rtg=1800, games=50, k=20, first="1",
                        rpd={"fide": 2300, "fide_date": "10/07/2026"}),
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        rapid = TOURNAMENTS_HEADER + "\n1;99999;Torneio Rápido;2026-03-15;RR;0;1;RPD\n"
        output = FideRatingCycle(
            tournaments_csv=rapid, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()
        period = next(
            r for r in _audit_rows(output["Audit_Period.csv"])
            if r["PlayerId"] == "3741" and r["TimeControl"] == "RPD"
        )
        assert period["Path"] == "FIDE_ENTRY"
        assert period["InitialRating"] == "2300"   # not the 1800 §1.1 would carry over


class TestRatingSubstitutionThroughTheCycle:
    """§6.4: the substitution happens before the period is calculated, so the
    audit is the only place the previous rating survives."""

    def _run(self, **std):
        stale = {"rtg": 1400, "games": 60, "k": 20, "first": "1", "last": "2023-01",
                 "fide": 2100, "fide_date": "10/07/2026"}
        players_csv = _players_csv(
            _player_row("3741", "Carlos Mendes", **stale | std),
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()
        header = output["RatingList.csv"].splitlines()[0].split(";")
        row = next(
            r for r in output["RatingList.csv"].splitlines()[1:] if r.startswith("3741;")
        ).split(";")
        rows = _audit_rows(output["Audit_Period.csv"])
        return dict(zip(header, row, strict=True)), rows

    def test_the_period_opens_on_the_fide_rating(self):
        _, rows = self._run()
        line = next(r for r in rows if r["PlayerId"] == "3741")
        assert line["Path"] == "FIDE_SUBSTITUTION"
        assert line["InitialRating"] == "2100"

    def test_the_audit_carries_the_three_substitution_fields(self):
        """Without them the list shows a 700-point jump and the file says
        nothing about where it came from."""
        _, rows = self._run()
        line = next(r for r in rows if r["PlayerId"] == "3741")
        assert line["PreviousRating"] == "1400"
        assert line["RatingSource"] == "FIDE"
        assert line["RatingCheckedOn"] == "10/07/2026"

    def test_every_other_player_leaves_the_three_fields_empty(self):
        _, rows = self._run()
        others = [r for r in rows if r["PlayerId"] != "3741"]
        assert others
        assert all(
            r["PreviousRating"] == "" and r["RatingSource"] == "" and r["RatingCheckedOn"] == ""
            for r in others
        )

    def test_an_active_player_is_not_substituted(self):
        _, rows = self._run(last="2026-01")
        line = next(r for r in rows if r["PlayerId"] == "3741")
        assert line["Path"] == "RATED"
        assert line["InitialRating"] == "1400"
        assert line["PreviousRating"] == ""

    def test_the_game_count_grows_by_the_games_played_and_nothing_else(self):
        row, _ = self._run()
        assert row["Games_Std"] == "65"  # 60 on file plus the five played

    def test_the_substituted_rating_is_what_the_opponents_face(self):
        """The substitution is part of the period's opening state, so the
        five opponents are calculated against 2100, not against 1400."""
        players_csv = _players_csv(
            _player_row("3741", "Carlos Mendes", rtg=1400, games=60, k=20, first="1",
                        last="2023-01", fide=2100, fide_date="10/07/2026"),
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()
        facing = [
            r for r in _audit_rows(output["Audit_Games.csv"])
            if r["OpponentId"] == "3741"
        ]
        assert facing
        assert {r["OpponentRating"] for r in facing} == {"2100"}


def _players_from_binary(filename: str, rating: int = 1600) -> tuple[str, dict[str, bytes]]:
    """A rated player list covering every id in a binary's BIO section.

    Names are generated, never read from the file: the binaries carry real
    names and test code does not.
    """
    data = (BINARY_DIR / filename).read_bytes()
    ids = sorted(
        int(entry["fexerj_id"])
        for entry in parse_bio_section(data).values()
        if str(entry.get("fexerj_id", "")).strip().isdigit()
    )
    rows = [_rated(str(i), f"Player {i}", "01/01/1990", rating, 20) for i in ids]
    return _players_csv(*rows), data


class TestTeamTournament:
    """The Interclubes is the federation's largest event — hundreds of
    players — and the one they named as the hardest test of the calculation.
    It is a team tournament (`ST`, read from a `.TUMX` binary), a format the
    per-game engine had no test over at all: the golden test covers it only
    for the current engine.

    The 93-player binary in `tests/binary/` is the largest team file
    available here, so what these tests can lock is the shape of the result
    over a whole field at once, not the real event's size.
    """

    TOURNAMENT = TOURNAMENTS_HEADER + "\n1;99999;Interclubes;2026-03-15;ST;0;1;STD\n"

    def _run(self):
        players_csv, data = _players_from_binary("swiss_team_93players.TUMX")
        output = FideRatingCycle(
            tournaments_csv=self.TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TUMX": data},
        ).run_cycle()
        return output, _audit_rows(output["Audit_Period.csv"]), _audit_rows(output["Audit_Games.csv"])

    def test_a_team_tournament_runs_a_whole_cycle(self):
        output, period, games = self._run()
        assert set(output) == {
            "RatingList.csv", "Audit_Games.csv", "Audit_Period.csv", "Audit_Checks.csv",
        }
        assert period, "no player was calculated from the team binary"
        assert games

    def test_every_player_in_the_list_survives(self):
        output, _, _ = self._run()
        rows = [r for r in output["RatingList.csv"].splitlines()[1:] if r]
        assert len(rows) == 93

    def test_only_players_who_played_are_calculated(self):
        """A team event carries reserves who never sit down."""
        _, period, _ = self._run()
        assert 0 < len(period) < 93

    def test_each_game_is_recorded_once_for_each_side(self):
        """The check that catches a pairing read gone wrong over a large
        field: every game has to appear twice, once from each side. A parser
        dropping or duplicating one side leaves an unmatched row here while
        every other assertion still passes."""
        _, _, games = self._run()
        pairs = {(g["Tournament"], g["PlayerId"], g["OpponentId"]) for g in games}
        assert len(pairs) == len(games), "the same game side appears twice"
        unmatched = [(t, p, o) for t, p, o in pairs if (t, o, p) not in pairs]
        assert unmatched == []

    def test_the_two_sides_of_a_game_expect_complementary_scores(self):
        """§3: the table's L column is 1 − H, and the 400 cap is symmetric,
        so the two sides' expectations sum to exactly 1. Off-by-one in the
        table lookup or a diff sign error breaks this and nothing else."""
        _, _, games = self._run()
        by_side = {(g["Tournament"], g["PlayerId"], g["OpponentId"]): Decimal(g["PD"]) for g in games}
        for (tournament, player, opponent), pd in by_side.items():
            assert pd + by_side[(tournament, opponent, player)] == 1

    def test_the_game_count_grows_by_the_games_played(self):
        output, period, _ = self._run()
        header = output["RatingList.csv"].splitlines()[0].split(";")
        rows = {
            row.split(";")[0]: dict(zip(header, row.split(";"), strict=True))
            for row in output["RatingList.csv"].splitlines()[1:]
        }
        for line in period:
            # 50 games on the way in, from the fixture, plus this period's.
            assert int(rows[line["PlayerId"]]["Games_Std"]) == 50 + int(line["Games"])


class TestChecksAudit:
    """§5 and §11.1: the file that points at the rows a human should look at,
    rather than describing a calculation. Both checks were asked for by
    FEXERJ — the K=10 one as the price of the K column carrying the permanent
    indicator, the deceased one because the validator deliberately accepts
    that file."""

    def _run(self, **std):
        players_csv = _players_csv(
            _player_row("3741", "Carlos Mendes", **{
                "rtg": 1800, "games": 50, "k": 20, "first": "1", **std}),
            _rated("643", "Roberto Faria", "01/01/1975", 1900, 20),
            _rated("1979", "Andre Nunes", "01/01/1982", 1850, 20),
            _rated("2831", "Felipe Borges", "01/01/1978", 1950, 20),
            _rated("3541", "Lucas Carvalho", "01/01/1985", 1800, 20),
            _rated("5400", "Bruno Teixeira", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()
        return _audit_rows(output["Audit_Checks.csv"])

    def test_an_ordinary_cycle_raises_nothing(self):
        """The file is still written: empty is the answer "nothing to look
        at", which a missing file would not be."""
        assert self._run() == []

    def test_k10_on_a_player_below_2200_is_raised(self):
        rows = self._run(k=10, rtg=1500)
        raised = [r for r in rows if r["Check"] == "K10_BELOW_2200"]
        assert len(raised) == 1
        assert raised[0]["PlayerId"] == "3741"
        assert raised[0]["TimeControl"] == "STD"

    def test_k10_at_or_above_2200_is_not_raised(self):
        assert self._run(k=10, rtg=2250) == []

    def test_k10_on_a_player_the_floor_dropped_is_raised(self):
        """No rating at all, and the permanence still on: the case §7 leaves
        behind, and the one a stray 10 is least distinguishable from.

        This player never sits down, which also shows the check reads the
        whole file and not only the players of the period — a stray 10 on
        someone who did not play is exactly as permanent."""
        players_csv = _players_csv(
            _player_row("9999", "Carlos Mendes", rtg="", games=60, k=10),
            _rated("3741", "Roberto Faria", "01/01/1975", 1800, 20),
            _rated("643", "Andre Nunes", "01/01/1975", 1900, 20),
            _rated("1979", "Felipe Borges", "01/01/1982", 1850, 20),
            _rated("2831", "Lucas Carvalho", "01/01/1978", 1950, 20),
            _rated("3541", "Bruno Teixeira", "01/01/1985", 1800, 20),
            _rated("5400", "Diego Alves", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()
        raised = _audit_rows(output["Audit_Checks.csv"])
        assert len(raised) == 1
        assert raised[0]["Check"] == "K10_BELOW_2200"
        assert raised[0]["PlayerId"] == "9999"
        assert raised[0]["Detail"] == ""

    def test_games_calculated_for_a_deceased_player_are_raised(self):
        rows = self._run(status="4")
        raised = [r for r in rows if r["Check"] == "CALCULATED_WHILE_DECEASED"]
        assert len(raised) == 1
        assert raised[0]["PlayerId"] == "3741"
        assert raised[0]["Detail"] == "5"      # the five games of the round robin

    def test_no_other_status_is_raised(self):
        for status in ("0", "1", "2", "3"):
            assert self._run(status=status) == [], status

    def test_a_deceased_player_who_did_not_play_is_not_raised(self):
        """The check is about games being calculated, not about the status
        sitting in the file."""
        players_csv = _players_csv(
            _player_row("9999", "Carlos Mendes", status="4", rtg=1800, games=50, k=20, first="1"),
            _rated("3741", "Roberto Faria", "01/01/1975", 1800, 20),
            _rated("643", "Andre Nunes", "01/01/1975", 1900, 20),
            _rated("1979", "Felipe Borges", "01/01/1982", 1850, 20),
            _rated("2831", "Lucas Carvalho", "01/01/1978", 1950, 20),
            _rated("3541", "Bruno Teixeira", "01/01/1985", 1800, 20),
            _rated("5400", "Diego Alves", "01/01/1995", 1900, 20),
        )
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        output = FideRatingCycle(
            tournaments_csv=_ONE_TOURNAMENT, first_item=1, items_to_process=1,
            initial_rating_csv=players_csv, binary_files={"1-99999.TURX": data},
        ).run_cycle()
        assert _audit_rows(output["Audit_Checks.csv"]) == []
