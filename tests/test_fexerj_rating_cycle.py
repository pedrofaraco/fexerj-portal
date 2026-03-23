"""Unit and integration tests for FexerjRatingCycle."""
import pathlib
import textwrap

import pytest

from calculator.classes import FexerjPlayer, FexerjRatingCycle, TournamentType

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'

# ---------------------------------------------------------------------------
# Fixtures — TURX round-robin (6 players, all IDs present)
# ---------------------------------------------------------------------------
# Player IDs in round_robin_6players.TURX:
#   SNR 1 → 3741, SNR 2 → 643, SNR 3 → 1979, SNR 4 → 2831, SNR 5 → 3541, SNR 6 → 5400

_TURX_DATA = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()

_TURX_PLAYERS_CSV = textwrap.dedent("""\
    Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
    3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0
    643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0
    1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0
    2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0
    3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0
    5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0
""")

_TURX_TOURNAMENTS_CSV = textwrap.dedent("""\
    Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
    1;99999;Test RR Tournament;2025-01-01;RR;0;1
""")

_TURX_BINARY_FILES = {"1-99999.TURX": _TURX_DATA}


# ---------------------------------------------------------------------------
# FexerjRatingCycle.__init__
# ---------------------------------------------------------------------------

class TestFexerjRatingCycleInit:
    def test_initial_state(self):
        cycle = FexerjRatingCycle("tournaments\n", 1, 10, "ratings\n", {})
        assert cycle.first_item == 1
        assert cycle.items_to_process == 10
        assert cycle.rating_list == {}
        assert cycle.cbx_to_fexerj == {}
        assert cycle.binary_files == {}

    def test_stores_constructor_arguments(self):
        bf = {"1-1.TUNX": b'\x00'}
        cycle = FexerjRatingCycle("t", 3, 2, "r", bf)
        assert cycle.tournaments_csv == "t"
        assert cycle.initial_rating_csv == "r"
        assert cycle.binary_files is bf


# ---------------------------------------------------------------------------
# get_rating_list
# ---------------------------------------------------------------------------

class TestGetRatingList:
    def test_loads_all_players(self):
        from tests.conftest import RATING_LIST_CSV
        cycle = FexerjRatingCycle("", 1, 1, RATING_LIST_CSV, {})
        cycle.get_rating_list(RATING_LIST_CSV)
        assert len(cycle.rating_list) == 3

    def test_player_attributes_parsed_correctly(self):
        from tests.conftest import RATING_LIST_CSV
        cycle = FexerjRatingCycle("", 1, 1, RATING_LIST_CSV, {})
        cycle.get_rating_list(RATING_LIST_CSV)
        player = cycle.rating_list[1]
        assert isinstance(player, FexerjPlayer)
        assert player.id_fexerj == 1
        assert player.last_rating == 1500
        assert player.total_games == 50

    def test_cbx_to_fexerj_mapping_built(self):
        from tests.conftest import RATING_LIST_CSV
        cycle = FexerjRatingCycle("", 1, 1, RATING_LIST_CSV, {})
        cycle.get_rating_list(RATING_LIST_CSV)
        assert 36633 in cycle.cbx_to_fexerj
        assert cycle.cbx_to_fexerj[36633] == 2

    def test_players_without_cbx_not_in_mapping(self):
        from tests.conftest import RATING_LIST_CSV
        cycle = FexerjRatingCycle("", 1, 1, RATING_LIST_CSV, {})
        cycle.get_rating_list(RATING_LIST_CSV)
        assert 1 not in cycle.cbx_to_fexerj

    def test_empty_csv_yields_empty_rating_list(self):
        header = "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints\n"
        cycle = FexerjRatingCycle("", 1, 1, header, {})
        cycle.get_rating_list(header)
        assert cycle.rating_list == {}
        assert cycle.cbx_to_fexerj == {}

    def test_multiple_players_all_loaded(self):
        csv = (
            "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints\n"
            "10;;;PLAYER A;1500;C;01/01/1990;M;BRA;50;0;0\n"
            "11;99;;PLAYER B;1600;C;01/01/1985;M;BRA;80;0;0\n"
            "12;;;PLAYER C;1700;C;01/01/1980;M;BRA;0;0;0\n"
        )
        cycle = FexerjRatingCycle("", 1, 1, csv, {})
        cycle.get_rating_list(csv)
        assert set(cycle.rating_list.keys()) == {10, 11, 12}
        assert cycle.cbx_to_fexerj == {99: 11}


# ---------------------------------------------------------------------------
# TournamentType
# ---------------------------------------------------------------------------

class TestTournamentType:
    def test_valid_types(self):
        assert TournamentType('SS') == TournamentType.SS
        assert TournamentType('RR') == TournamentType.RR
        assert TournamentType('ST') == TournamentType.ST

    def test_invalid_type_raises_value_error(self):
        with pytest.raises(ValueError):
            TournamentType('XX')

    def test_invalid_type_in_run_cycle_includes_tournament_number(self):
        tournaments_csv = (
            "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
            "42;12345;Test Tournament;2025-01-01;XX;0;1\n"
        )
        ratings_csv = (
            "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints\n"
        )
        cycle = FexerjRatingCycle(tournaments_csv, 42, 1, ratings_csv, {"42-12345.TUNX": b''})
        with pytest.raises(ValueError, match="42"):
            cycle.run_cycle()


# ---------------------------------------------------------------------------
# run_cycle — integration test using real TURX binary
# ---------------------------------------------------------------------------

class TestRunCycle:
    def test_returns_expected_output_filenames(self):
        cycle = FexerjRatingCycle(
            _TURX_TOURNAMENTS_CSV, 1, 1, _TURX_PLAYERS_CSV, _TURX_BINARY_FILES
        )
        output = cycle.run_cycle()
        assert "RatingList_after_1.csv" in output
        assert "Audit_of_Tournament_1.csv" in output

    def test_rating_list_output_has_header(self):
        cycle = FexerjRatingCycle(
            _TURX_TOURNAMENTS_CSV, 1, 1, _TURX_PLAYERS_CSV, _TURX_BINARY_FILES
        )
        output = cycle.run_cycle()
        first_line = output["RatingList_after_1.csv"].splitlines()[0]
        assert first_line.startswith("Id_No")

    def test_rating_list_output_has_all_players(self):
        cycle = FexerjRatingCycle(
            _TURX_TOURNAMENTS_CSV, 1, 1, _TURX_PLAYERS_CSV, _TURX_BINARY_FILES
        )
        output = cycle.run_cycle()
        lines = [row for row in output["RatingList_after_1.csv"].splitlines() if row]
        assert len(lines) == 7  # header + 6 players

    def test_audit_output_has_header(self):
        cycle = FexerjRatingCycle(
            _TURX_TOURNAMENTS_CSV, 1, 1, _TURX_PLAYERS_CSV, _TURX_BINARY_FILES
        )
        output = cycle.run_cycle()
        first_line = output["Audit_of_Tournament_1.csv"].splitlines()[0]
        assert first_line.startswith("Id_Fexerj")

    def test_audit_output_has_one_line_per_player(self):
        cycle = FexerjRatingCycle(
            _TURX_TOURNAMENTS_CSV, 1, 1, _TURX_PLAYERS_CSV, _TURX_BINARY_FILES
        )
        output = cycle.run_cycle()
        lines = [row for row in output["Audit_of_Tournament_1.csv"].splitlines() if row]
        assert len(lines) == 7  # header + 6 players

    def test_ratings_change_after_cycle(self):
        """At least some players should have a different rating after the tournament."""
        cycle = FexerjRatingCycle(
            _TURX_TOURNAMENTS_CSV, 1, 1, _TURX_PLAYERS_CSV, _TURX_BINARY_FILES
        )
        output = cycle.run_cycle()
        # Parse output ratings
        lines = output["RatingList_after_1.csv"].splitlines()[1:]
        new_ratings = {int(row.split(';')[0]): int(row.split(';')[4]) for row in lines if row}
        original_ratings = {3741: 1800, 643: 1900, 1979: 1700, 2831: 1750, 3541: 1650, 5400: 1600}
        changed = sum(1 for pid, new_r in new_ratings.items() if new_r != original_ratings[pid])
        assert changed > 0

    def test_out_of_range_tournament_skipped(self):
        """Tournaments outside first/count range must not appear in output."""
        tournaments_csv = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;Tournament 1;2025-01-01;RR;0;1
            2;88888;Tournament 2;2025-02-01;RR;0;1
        """)
        cycle = FexerjRatingCycle(
            tournaments_csv, 1, 1, _TURX_PLAYERS_CSV,
            {"1-99999.TURX": _TURX_DATA}
        )
        output = cycle.run_cycle()
        assert "RatingList_after_1.csv" in output
        assert "RatingList_after_2.csv" not in output

    def test_missing_binary_file_raises(self):
        """If the binary file for a tournament is not in binary_files, ValueError is raised."""
        cycle = FexerjRatingCycle(
            _TURX_TOURNAMENTS_CSV, 1, 1, _TURX_PLAYERS_CSV, {}  # empty binary_files
        )
        with pytest.raises(ValueError, match="1-99999.TURX"):
            cycle.run_cycle()

    def test_two_tournament_chain(self):
        """Run two tournaments in sequence; the second reads from the first's output."""
        tournaments_csv = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
            1;99999;Tournament 1;2025-01-01;RR;0;1
            2;99999;Tournament 2;2025-02-01;RR;0;1
        """)
        binary_files = {
            "1-99999.TURX": _TURX_DATA,
            "2-99999.TURX": _TURX_DATA,
        }
        cycle = FexerjRatingCycle(tournaments_csv, 1, 2, _TURX_PLAYERS_CSV, binary_files)
        output = cycle.run_cycle()
        assert "RatingList_after_1.csv" in output
        assert "RatingList_after_2.csv" in output
        assert "Audit_of_Tournament_1.csv" in output
        assert "Audit_of_Tournament_2.csv" in output
