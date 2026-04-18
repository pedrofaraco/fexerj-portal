"""Unit tests for Tournament class methods."""
import csv
import io
import pathlib
from unittest.mock import MagicMock

import pytest

from calculator.classes import (
    _AUDIT_FILE_HEADER,
    _MAX_NUM_GAMES_TEMP_RATING,
    CalcRule,
    FexerjPlayer,
    Tournament,
    TournamentPlayer,
)

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'

TUNX_T1_DATA  = (BINARY_DIR / 'swiss_system_18players.TUNX').read_bytes()
TURX_T6_DATA  = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
TUNX_T23_DATA = (BINARY_DIR / 'swiss_system_51players.TUNX').read_bytes()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fexerj_player(id_fexerj, total_games, last_rating, sum_oppon=0, pts_oppon=0.0, id_cbx=""):
    return FexerjPlayer(id_fexerj, id_cbx, "", f"Player {id_fexerj}", last_rating,
                        "CLUB", "01/01/1990", "M", "BRA", total_games, sum_oppon, pts_oppon)


def _make_tournament(is_irt=0, is_fexerj=1, rating_list=None, cbx_to_fexerj=None, binary_data=b''):
    rc = MagicMock()
    rc.rating_list = rating_list or {}
    rc.cbx_to_fexerj = cbx_to_fexerj or {}
    rc.binary_files = {"1-12345.TUNX": binary_data}
    data = ["1", "12345", "Test Tournament", "2025-01-01", "SS", str(is_irt), str(is_fexerj)]
    return Tournament(rc, data)


def _make_tp(tournament, fexerj_id, snr, opponents_list=None):
    """Build a TournamentPlayer with opponents as pre-complete_players_info list format."""
    tp = TournamentPlayer(tournament)
    tp.id = fexerj_id
    tp.snr = snr
    tp.name = f"Player {fexerj_id}"
    tp.opponents = opponents_list if opponents_list is not None else {}
    tp.is_unrated = None
    tp.is_temp = None
    return tp


def _make_calculated_tp(tournament, fexerj_id=100, last_rating=1500, last_total_games=50,
                         last_k=15, this_pts=1.0, this_games=1, this_sum_oppon=1500,
                         this_avg_oppon=1500.0, this_expected=0.5, this_points_above=0.5,
                         new_rating=1508, new_total_games=51, calc_rule=CalcRule.NORMAL):
    """Build a TournamentPlayer with all post-calculation attributes set."""
    tp = TournamentPlayer(tournament)
    tp.id = fexerj_id
    tp.name = f"Player {fexerj_id}"
    tp.last_rating = last_rating
    tp.last_total_games = last_total_games
    tp.last_k = last_k
    tp.this_pts_against_oppon = this_pts
    tp.this_games = this_games
    tp.this_sum_oppon_ratings = this_sum_oppon
    tp.this_avg_oppon_rating = this_avg_oppon
    tp.this_expected_points = this_expected
    tp.this_points_above_expected = this_points_above
    tp.new_rating = new_rating
    tp.new_total_games = new_total_games
    tp.calc_rule = calc_rule
    return tp


# ---------------------------------------------------------------------------
# Tournament.__init__ — binary file lookup
# ---------------------------------------------------------------------------

class TestTournamentInit:
    def test_missing_binary_file_raises(self):
        rc = MagicMock()
        rc.binary_files = {}  # empty — no file available
        data = ["1", "12345", "Test", "2025-01-01", "SS", "0", "1"]
        with pytest.raises(ValueError, match="1-12345.TUNX"):
            Tournament(rc, data)

    def test_correct_extension_for_rr(self):
        rc = MagicMock()
        rc.binary_files = {"1-12345.TURX": b'\x00'}
        data = ["1", "12345", "Test", "2025-01-01", "RR", "0", "1"]
        t = Tournament(rc, data)
        assert t.binary_data == b'\x00'

    def test_correct_extension_for_st(self):
        rc = MagicMock()
        rc.binary_files = {"1-12345.TUMX": b'\x00'}
        data = ["1", "12345", "Test", "2025-01-01", "ST", "0", "1"]
        t = Tournament(rc, data)
        assert t.binary_data == b'\x00'


# ---------------------------------------------------------------------------
# complete_players_info
# ---------------------------------------------------------------------------

class TestCompletePlersInfo:
    def test_unrated_player_classified(self):
        fp = _make_fexerj_player(1, total_games=0, last_rating=0)
        t = _make_tournament(rating_list={1: fp})
        tp = _make_tp(t, fexerj_id=1, snr=1)
        t.players = {1: tp}
        t.complete_players_info()
        assert tp.is_unrated is True
        assert 1 in t.unrated_keys
        assert 1 not in t.temp_keys
        assert 1 not in t.established_keys

    def test_temp_player_classified(self):
        fp = _make_fexerj_player(2, total_games=5, last_rating=1200)
        t = _make_tournament(rating_list={2: fp})
        tp = _make_tp(t, fexerj_id=2, snr=2)
        t.players = {2: tp}
        t.complete_players_info()
        assert tp.is_temp is True
        assert 2 in t.temp_keys

    def test_established_player_classified(self):
        fp = _make_fexerj_player(3, total_games=_MAX_NUM_GAMES_TEMP_RATING, last_rating=1500)
        t = _make_tournament(rating_list={3: fp})
        tp = _make_tp(t, fexerj_id=3, snr=3)
        t.players = {3: tp}
        t.complete_players_info()
        assert 3 in t.established_keys

    def test_boundary_exactly_15_games_is_established(self):
        fp = _make_fexerj_player(5, total_games=15, last_rating=1400)
        t = _make_tournament(rating_list={5: fp})
        tp = _make_tp(t, fexerj_id=5, snr=5)
        t.players = {5: tp}
        t.complete_players_info()
        assert 5 in t.established_keys

    def test_boundary_14_games_is_temp(self):
        fp = _make_fexerj_player(6, total_games=14, last_rating=1400)
        t = _make_tournament(rating_list={6: fp})
        tp = _make_tp(t, fexerj_id=6, snr=6)
        t.players = {6: tp}
        t.complete_players_info()
        assert 6 in t.temp_keys

    def test_opponents_converted_to_player_references(self):
        fp1 = _make_fexerj_player(1, total_games=50, last_rating=1500)
        fp2 = _make_fexerj_player(2, total_games=50, last_rating=1600)
        t = _make_tournament(rating_list={1: fp1, 2: fp2})
        tp1 = _make_tp(t, fexerj_id=1, snr=1, opponents_list={2: ["Player 2", 1.0]})
        tp2 = _make_tp(t, fexerj_id=2, snr=2, opponents_list={1: ["Player 1", 0.0]})
        t.players = {1: tp1, 2: tp2}
        t.complete_players_info()
        assert tp1.opponents[2][0] is tp2
        assert tp1.opponents[2][1] == 1.0

    def test_irt_tournament_uses_cbx_to_fexerj_mapping(self):
        fp = _make_fexerj_player(10, total_games=50, last_rating=1800)
        t = _make_tournament(is_irt=1, rating_list={10: fp}, cbx_to_fexerj={99: 10})
        tp = _make_tp(t, fexerj_id=99, snr=1)
        t.players = {1: tp}
        t.complete_players_info()
        assert tp.last_rating == 1800

    def test_all_player_types_classified_together(self):
        fp_unrated = _make_fexerj_player(1, total_games=0,  last_rating=0)
        fp_temp    = _make_fexerj_player(2, total_games=5,  last_rating=1200)
        fp_estab   = _make_fexerj_player(3, total_games=50, last_rating=1500)
        t = _make_tournament(rating_list={1: fp_unrated, 2: fp_temp, 3: fp_estab})
        tp1 = _make_tp(t, fexerj_id=1, snr=1)
        tp2 = _make_tp(t, fexerj_id=2, snr=2)
        tp3 = _make_tp(t, fexerj_id=3, snr=3)
        t.players = {1: tp1, 2: tp2, 3: tp3}
        t.complete_players_info()
        assert t.unrated_keys == [1]
        assert t.temp_keys == [2]
        assert t.established_keys == [3]

    def test_unknown_fexerj_id_raises_value_error(self):
        fp = _make_fexerj_player(1, total_games=50, last_rating=1500)
        t = _make_tournament(rating_list={1: fp})
        tp = _make_tp(t, fexerj_id=9999, snr=1)
        tp.name = "Fulano de Tal"
        t.players = {1: tp}
        with pytest.raises(ValueError, match=r"9999.*Fulano de Tal"):
            t.complete_players_info()

    def test_unknown_cbx_id_in_irt_tournament_raises_value_error(self):
        fp = _make_fexerj_player(10, total_games=50, last_rating=1800)
        t = _make_tournament(is_irt=1, rating_list={10: fp}, cbx_to_fexerj={99: 10})
        tp = _make_tp(t, fexerj_id=123, snr=1)
        t.players = {1: tp}
        with pytest.raises(ValueError, match=r"123"):
            t.complete_players_info()

    def test_missing_player_error_lists_all_unknown_ids(self):
        fp = _make_fexerj_player(1, total_games=50, last_rating=1500)
        t = _make_tournament(rating_list={1: fp})
        tp_ok = _make_tp(t, fexerj_id=1, snr=1)
        tp_bad1 = _make_tp(t, fexerj_id=9999, snr=2)
        tp_bad2 = _make_tp(t, fexerj_id=8888, snr=3)
        t.players = {1: tp_ok, 2: tp_bad1, 3: tp_bad2}
        with pytest.raises(ValueError) as exc:
            t.complete_players_info()
        message = str(exc.value)
        assert "9999" in message
        assert "8888" in message


# ---------------------------------------------------------------------------
# write_tournament_audit
# ---------------------------------------------------------------------------

class TestWriteTournamentAudit:
    def test_header_is_written(self):
        t = _make_tournament()
        t.players = {}
        output = t.write_tournament_audit()
        assert output.splitlines()[0] == _AUDIT_FILE_HEADER

    def test_one_line_per_player(self):
        t = _make_tournament()
        t.players = {
            1: _make_calculated_tp(t, fexerj_id=101),
            2: _make_calculated_tp(t, fexerj_id=102),
        }
        lines = [row for row in t.write_tournament_audit().splitlines() if row]
        assert len(lines) == 3  # header + 2 players

    def test_correct_number_of_fields_per_line(self):
        t = _make_tournament()
        t.players = {1: _make_calculated_tp(t)}
        lines = t.write_tournament_audit().splitlines()
        assert len(lines[1].split(";")) == 19

    def test_player_values_in_output(self):
        t = _make_tournament()
        t.players = {1: _make_calculated_tp(t, fexerj_id=100, new_rating=1508, calc_rule=CalcRule.NORMAL)}
        content = t.write_tournament_audit()
        assert "1508" in content
        assert "NORMAL" in content
        assert "100" in content

    def test_zero_games_player_we_and_p_are_none(self):
        t = _make_tournament()
        tp = _make_calculated_tp(t, this_games=0, this_pts=None,
                                  this_sum_oppon=None, this_avg_oppon=None,
                                  this_expected=None, this_points_above=None,
                                  new_rating=1500, new_total_games=50, calc_rule=None)
        t.players = {1: tp}
        reader = csv.reader(io.StringIO(t.write_tournament_audit()), delimiter=";")
        next(reader)  # skip header
        row = next(reader)
        assert row[11] == "None"   # We
        assert row[17] == "None"   # P


# ---------------------------------------------------------------------------
# write_new_ratings_list
# ---------------------------------------------------------------------------

class TestWriteNewRatingsList:
    def _setup(self, new_total_games):
        fp = _make_fexerj_player(100, total_games=50, last_rating=1500)
        t = _make_tournament(rating_list={100: fp})
        tp = TournamentPlayer(t)
        tp.id = 100
        tp.new_rating = 1520
        tp.new_total_games = new_total_games
        tp.new_sum_oppon_ratings = 3000
        tp.new_pts_against_oppon = 2.0
        t.players = {1: tp}
        return t, fp

    def test_fexerj_player_rating_updated(self):
        t, fp = self._setup(new_total_games=51)
        t.write_new_ratings_list()
        assert fp.last_rating == 1520
        assert fp.total_games == 51

    def test_established_player_stats_reset_to_zero(self):
        t, fp = self._setup(new_total_games=51)
        t.write_new_ratings_list()
        assert fp.sum_opponents_ratings == 0
        assert fp.points_against_opponents == 0

    def test_temp_player_stats_preserved(self):
        t, fp = self._setup(new_total_games=8)
        t.write_new_ratings_list()
        assert fp.sum_opponents_ratings == 3000
        assert fp.points_against_opponents == 2.0

    def test_output_has_header(self):
        t, _ = self._setup(new_total_games=51)
        output = t.write_new_ratings_list()
        assert output.splitlines()[0].startswith("Id_No")

    def test_output_contains_new_rating(self):
        t, _ = self._setup(new_total_games=51)
        assert "1520" in t.write_new_ratings_list()

    def test_boundary_exactly_15_new_games_resets_stats(self):
        t, fp = self._setup(new_total_games=15)
        t.write_new_ratings_list()
        assert fp.sum_opponents_ratings == 0
        assert fp.points_against_opponents == 0

    def test_boundary_14_new_games_preserves_stats(self):
        t, fp = self._setup(new_total_games=14)
        t.write_new_ratings_list()
        assert fp.sum_opponents_ratings == 3000
        assert fp.points_against_opponents == 2.0

    def test_returns_string(self):
        t, _ = self._setup(new_total_games=51)
        assert isinstance(t.write_new_ratings_list(), str)


# ---------------------------------------------------------------------------
# calculate_players_ratings — processing order
# ---------------------------------------------------------------------------

class TestCalculatePlayersRatings:
    def test_unrated_processed_before_established(self):
        """Unrated players must be processed first so their new_rating is available
        for established players who face them as opponents."""
        t = _make_tournament()

        tp_unrated = TournamentPlayer(t)
        tp_unrated.id = 1
        tp_unrated.name = "Unrated"
        tp_unrated.is_unrated = True
        tp_unrated.is_temp = False
        tp_unrated.last_rating = 0
        tp_unrated.last_total_games = 0
        tp_unrated.last_sum_oppon_ratings = 0
        tp_unrated.last_pts_against_oppon = 0.0

        tp_established = TournamentPlayer(t)
        tp_established.id = 2
        tp_established.name = "Established"
        tp_established.is_unrated = False
        tp_established.is_temp = False
        tp_established.last_rating = 1500
        tp_established.last_total_games = 50
        tp_established.last_sum_oppon_ratings = 0
        tp_established.last_pts_against_oppon = 0.0

        tp_unrated.opponents = {2: [tp_established, 1.0]}
        tp_established.opponents = {1: [tp_unrated, 0.0]}

        t.players = {1: tp_unrated, 2: tp_established}
        t.unrated_keys = [1]
        t.temp_keys = []
        t.established_keys = [2]

        t.calculate_players_ratings()

        assert tp_unrated.new_rating is not None
        assert tp_unrated.new_rating > 0
        assert tp_established.this_sum_oppon_ratings == tp_unrated.new_rating

    def test_all_player_types_are_processed(self):
        t = _make_tournament()

        def _build_tp(fexerj_id, is_unrated, is_temp, last_rating, last_total_games):
            tp = TournamentPlayer(t)
            tp.id = fexerj_id
            tp.name = f"P{fexerj_id}"
            tp.is_unrated = is_unrated
            tp.is_temp = is_temp
            tp.last_rating = last_rating
            tp.last_total_games = last_total_games
            tp.last_sum_oppon_ratings = 0
            tp.last_pts_against_oppon = 0.0
            tp.opponents = {}
            return tp

        tp1 = _build_tp(1, is_unrated=True,  is_temp=False, last_rating=0,    last_total_games=0)
        tp2 = _build_tp(2, is_unrated=False, is_temp=True,  last_rating=1200, last_total_games=5)
        tp3 = _build_tp(3, is_unrated=False, is_temp=False, last_rating=1500, last_total_games=50)

        t.players = {1: tp1, 2: tp2, 3: tp3}
        t.unrated_keys = [1]
        t.temp_keys = [2]
        t.established_keys = [3]

        t.calculate_players_ratings()

        assert tp1.new_rating is not None
        assert tp2.new_rating is not None
        assert tp3.new_rating is not None


# ---------------------------------------------------------------------------
# load_player_list — binary loading
# ---------------------------------------------------------------------------

def _make_rr_tournament(binary_data, is_irt=0, rating_list=None, cbx_to_fexerj=None):
    """Build an RR tournament using a TURX binary blob."""
    rc = MagicMock()
    rc.rating_list = rating_list or {}
    rc.cbx_to_fexerj = cbx_to_fexerj or {}
    rc.binary_files = {"1-99999.TURX": binary_data}
    data = ["1", "99999", "Test RR", "2025-01-01", "RR", str(is_irt), "1"]
    return Tournament(rc, data)


class TestLoadPlayerList:
    def test_players_populated_from_turx(self):
        t = _make_rr_tournament(TURX_T6_DATA)
        t.load_player_list()
        assert len(t.players) == 6

    def test_player_names_set(self):
        t = _make_rr_tournament(TURX_T6_DATA)
        t.load_player_list()
        assert all(tp.name for tp in t.players.values())

    def test_player_ids_resolved(self):
        t = _make_rr_tournament(TURX_T6_DATA)
        t.load_player_list()
        assert t.players[1].id == 3741

    def test_opponents_populated(self):
        t = _make_rr_tournament(TURX_T6_DATA)
        t.load_player_list()
        assert len(t.players[1].opponents) > 0

    def test_opponent_scores_sum_to_one(self):
        t = _make_rr_tournament(TURX_T6_DATA)
        t.load_player_list()
        for snr_a, tp_a in t.players.items():
            for snr_b, (_, score_a) in tp_a.opponents.items():
                score_b = t.players[snr_b].opponents[snr_a][1]
                assert abs(score_a + score_b - 1.0) < 0.001

    def test_missing_id_raises_value_error(self):
        """TUNX T1 has SNR 18 with no FEXERJ ID — resolve_id must raise ValueError."""
        rc = MagicMock()
        rc.binary_files = {"1-12345.TUNX": TUNX_T1_DATA}
        data = ["1", "12345", "Test", "2025-01-01", "SS", "0", "1"]
        t = Tournament(rc, data)
        with pytest.raises(ValueError, match="FEXERJ ID"):
            t.load_player_list()

    def test_t23_all_players_loaded_despite_asterisk_prefix(self):
        """51-player TUNX with '*'-prefix records must load all 51 players."""
        rc = MagicMock()
        rc.binary_files = {"1-12345.TUNX": TUNX_T23_DATA}
        data = ["1", "12345", "Test", "2025-01-01", "SS", "0", "1"]
        t = Tournament(rc, data)
        t.load_player_list()
        assert len(t.players) == 51
