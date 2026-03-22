"""Unit tests for TournamentPlayer pure-logic methods."""
import math
import pytest

from calculator.classes import TournamentPlayer, CalcRule, _MAX_NUM_GAMES_TEMP_RATING


# ---------------------------------------------------------------------------
# resolve_id
# ---------------------------------------------------------------------------

class TestResolveId:
    def test_returns_int_when_id_present(self, make_tournament_player):
        p = make_tournament_player()
        assert p.resolve_id('1078') == 1078

    def test_raises_when_id_empty(self, make_tournament_player):
        p = make_tournament_player(name="Newton Gomes", snr=18)
        with pytest.raises(ValueError, match="Newton Gomes"):
            p.resolve_id('')

    def test_raises_mentions_snr(self, make_tournament_player):
        p = make_tournament_player(name="Unknown Player", snr=5)
        with pytest.raises(ValueError, match="5"):
            p.resolve_id('')


# ---------------------------------------------------------------------------
# add_opponent
# ---------------------------------------------------------------------------

class TestAddOpponent:
    def test_win_added(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        p.add_opponent(5, "Opponent A", "1")
        assert len(p.opponents) == 1
        assert p.opponents[5] == ["Opponent A", 1.0]

    def test_draw_added(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        p.add_opponent(3, "Opponent B", "½")
        assert p.opponents[3][1] == 0.5

    def test_loss_added(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        p.add_opponent(7, "Opponent C", "0")
        assert p.opponents[7][1] == 0.0

    def test_forfeit_ignored(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        p.add_opponent(2, "Opponent D", "1K")
        assert len(p.opponents) == 0

    def test_multiple_opponents(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        p.add_opponent(1, "A", "1")
        p.add_opponent(2, "B", "½")
        p.add_opponent(3, "C", "0")
        assert len(p.opponents) == 3

    def test_duplicate_sno_overwrites(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        p.add_opponent(5, "Opponent A", "0")
        p.add_opponent(5, "Opponent A", "1")
        assert len(p.opponents) == 1
        assert p.opponents[5][1] == 1.0

    def test_empty_result_raises(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        with pytest.raises(ValueError, match="Unexpected result"):
            p.add_opponent(1, "Opponent A", "")

    def test_unrecognised_result_raises(self, make_tournament_player):
        p = make_tournament_player(opponents={})
        with pytest.raises(ValueError, match="Unexpected result"):
            p.add_opponent(1, "Opponent A", "X")


# ---------------------------------------------------------------------------
# keep_current_rating
# ---------------------------------------------------------------------------

class TestKeepCurrentRating:
    def test_copies_last_values(self, make_tournament_player):
        p = make_tournament_player(
            last_rating=1600,
            last_total_games=30,
            last_sum_oppon_ratings=48000,
            last_pts_against_oppon=15.5,
        )
        p.keep_current_rating()
        assert p.new_rating == 1600
        assert p.new_total_games == 30
        assert p.new_sum_oppon_ratings == 48000
        assert p.new_pts_against_oppon == 15.5


# ---------------------------------------------------------------------------
# get_current_k
# ---------------------------------------------------------------------------

class TestGetCurrentK:
    def test_grampo_range(self, make_tournament_player):
        for games in [0, 1, 14]:
            p = make_tournament_player(last_total_games=games)
            assert p.get_current_k() == 30

    def test_entry_at_15_games(self, make_tournament_player):
        p = make_tournament_player(last_total_games=_MAX_NUM_GAMES_TEMP_RATING)
        assert p.get_current_k() == 25

    def test_mid_range_25(self, make_tournament_player):
        p = make_tournament_player(last_total_games=39)
        assert p.get_current_k() == 25

    def test_entry_at_40_games(self, make_tournament_player):
        p = make_tournament_player(last_total_games=40)
        assert p.get_current_k() == 15

    def test_mid_range_15(self, make_tournament_player):
        p = make_tournament_player(last_total_games=79)
        assert p.get_current_k() == 15

    def test_entry_at_80_games(self, make_tournament_player):
        p = make_tournament_player(last_total_games=80)
        assert p.get_current_k() == 10

    def test_large_game_count(self, make_tournament_player):
        p = make_tournament_player(last_total_games=500)
        assert p.get_current_k() == 10

    def test_empty_k_table_raises_value_error(self, make_tournament_player, monkeypatch):
        import calculator.classes as classes_module
        monkeypatch.setattr(classes_module, "_K_STARTING_NUM_GAMES", [])
        p = make_tournament_player(last_total_games=10)
        with pytest.raises(ValueError, match="K factor"):
            p.get_current_k()


# ---------------------------------------------------------------------------
# get_performance_rating
# ---------------------------------------------------------------------------

class TestGetPerformanceRating:
    def test_even_score_equals_average(self, make_tournament_player):
        p = make_tournament_player()
        result = p.get_performance_rating(1500, 4, 2.0)
        assert abs(result - 1500) < 0.01

    def test_perfect_score_adjusted(self, make_tournament_player):
        p = make_tournament_player()
        result = p.get_performance_rating(1500, 4, 4.0)
        expected = 1500 + 400 * math.log10(0.9 / 0.1)
        assert abs(result - expected) < 0.01

    def test_zero_score_adjusted(self, make_tournament_player):
        p = make_tournament_player()
        result = p.get_performance_rating(1500, 4, 0.0)
        expected = 1500 + 400 * math.log10(0.1 / 0.9)
        assert abs(result - expected) < 0.01

    def test_above_average_score_raises_rating(self, make_tournament_player):
        p = make_tournament_player()
        assert p.get_performance_rating(1500, 4, 3.0) > 1500

    def test_below_average_score_lowers_rating(self, make_tournament_player):
        p = make_tournament_player()
        assert p.get_performance_rating(1500, 4, 1.0) < 1500

    def test_single_game_win(self, make_tournament_player):
        p = make_tournament_player()
        result = p.get_performance_rating(1600, 1, 1.0)
        expected = 1600 + 400 * math.log10(0.75 / 0.25)
        assert abs(result - expected) < 0.01


# ---------------------------------------------------------------------------
# check_rating_performance_rule
# ---------------------------------------------------------------------------

class TestCheckRatingPerformanceRule:
    def test_fewer_than_5_games_always_false(self, make_tournament_player):
        for games in range(0, 5):
            p = make_tournament_player()
            p.this_games = games
            p.this_points_above_expected = 999.0
            assert p.check_rating_performance_rule() is False

    def test_5_games_below_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 5
        p.this_points_above_expected = 1.83
        assert p.check_rating_performance_rule() is False

    def test_5_games_at_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 5
        p.this_points_above_expected = 1.84
        assert p.check_rating_performance_rule() is True

    def test_6_games_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 6
        p.this_points_above_expected = 2.02
        assert p.check_rating_performance_rule() is True

    def test_6_games_below_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 6
        p.this_points_above_expected = 2.01
        assert p.check_rating_performance_rule() is False

    def test_7_games_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 7
        p.this_points_above_expected = 2.16
        assert p.check_rating_performance_rule() is True

    def test_more_than_7_games_returns_false(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 8
        p.this_points_above_expected = 999.0
        assert p.check_rating_performance_rule() is False


# ---------------------------------------------------------------------------
# check_double_k_rule
# ---------------------------------------------------------------------------

class TestCheckDoubleKRule:
    def test_fewer_than_4_games_always_false(self, make_tournament_player):
        for games in range(0, 4):
            p = make_tournament_player()
            p.this_games = games
            p.this_points_above_expected = 999.0
            assert p.check_double_k_rule() is False

    def test_4_games_at_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 4
        p.this_points_above_expected = 1.65
        assert p.check_double_k_rule() is True

    def test_4_games_below_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 4
        p.this_points_above_expected = 1.64
        assert p.check_double_k_rule() is False

    def test_5_games_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 5
        p.this_points_above_expected = 1.43
        assert p.check_double_k_rule() is True

    def test_6_games_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 6
        p.this_points_above_expected = 1.56
        assert p.check_double_k_rule() is True

    def test_7_games_threshold(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 7
        p.this_points_above_expected = 1.69
        assert p.check_double_k_rule() is True

    def test_more_than_7_games_returns_false(self, make_tournament_player):
        p = make_tournament_player()
        p.this_games = 8
        p.this_points_above_expected = 999.0
        assert p.check_double_k_rule() is False


# ---------------------------------------------------------------------------
# get_calculation_rule
# ---------------------------------------------------------------------------

class TestGetCalculationRule:
    def test_temporary_player_returns_temporary(self, make_tournament_player):
        p = make_tournament_player(is_temp=True, is_unrated=False)
        p.this_games = 5
        p.this_points_above_expected = 0.0
        assert p.get_calculation_rule(is_fexerj_tournament=True) == CalcRule.TEMPORARY

    def test_unrated_player_returns_temporary(self, make_tournament_player):
        p = make_tournament_player(is_temp=False, is_unrated=True)
        p.this_games = 5
        p.this_points_above_expected = 0.0
        assert p.get_calculation_rule(is_fexerj_tournament=True) == CalcRule.TEMPORARY

    def test_rating_performance_in_fexerj_tournament(self, make_tournament_player):
        p = make_tournament_player(is_temp=False, is_unrated=False)
        p.this_games = 5
        p.this_points_above_expected = 1.84
        assert p.get_calculation_rule(is_fexerj_tournament=True) == CalcRule.RATING_PERFORMANCE

    def test_rating_performance_not_applied_outside_fexerj(self, make_tournament_player):
        p = make_tournament_player(is_temp=False, is_unrated=False)
        p.this_games = 5
        p.this_points_above_expected = 1.84
        assert p.get_calculation_rule(is_fexerj_tournament=False) != CalcRule.RATING_PERFORMANCE

    def test_double_k_rule(self, make_tournament_player):
        p = make_tournament_player(is_temp=False, is_unrated=False)
        p.this_games = 4
        p.this_points_above_expected = 1.65
        assert p.get_calculation_rule(is_fexerj_tournament=True) == CalcRule.DOUBLE_K

    def test_normal_rule(self, make_tournament_player):
        p = make_tournament_player(is_temp=False, is_unrated=False)
        p.this_games = 4
        p.this_points_above_expected = 0.0
        assert p.get_calculation_rule(is_fexerj_tournament=True) == CalcRule.NORMAL

    def test_rp_takes_precedence_over_dk_in_fexerj_tournament(self, make_tournament_player):
        p = make_tournament_player(is_temp=False, is_unrated=False)
        p.this_games = 5
        p.this_points_above_expected = 2.0  # satisfies both RP and DK
        assert p.get_calculation_rule(is_fexerj_tournament=True) == CalcRule.RATING_PERFORMANCE

    def test_dk_applies_when_rp_not_triggered_outside_fexerj(self, make_tournament_player):
        p = make_tournament_player(is_temp=False, is_unrated=False)
        p.this_games = 5
        p.this_points_above_expected = 2.0
        assert p.get_calculation_rule(is_fexerj_tournament=False) == CalcRule.DOUBLE_K


# ---------------------------------------------------------------------------
# calculate_new_rating
# ---------------------------------------------------------------------------

class TestCalculateNewRating:
    def _make_opponent(self, make_tournament_player, **kwargs):
        return make_tournament_player(**kwargs)

    def test_no_opponents_keeps_rating(self, make_tournament_player):
        p = make_tournament_player(
            last_rating=1500, last_total_games=50, opponents={},
            is_unrated=False, is_temp=False,
        )
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating == 1500
        assert p.new_total_games == 50

    def test_established_player_win_increases_rating(self, make_tournament_player):
        opp = self._make_opponent(make_tournament_player, last_rating=1500,
                                  new_rating=None, is_unrated=False, is_temp=False)
        p = make_tournament_player(
            last_rating=1500, last_total_games=50,
            opponents={1: [opp, 1.0]},
            is_unrated=False, is_temp=False,
        )
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating > 1500

    def test_established_player_loss_decreases_rating(self, make_tournament_player):
        opp = self._make_opponent(make_tournament_player, last_rating=1500,
                                  new_rating=None, is_unrated=False, is_temp=False)
        p = make_tournament_player(
            last_rating=1500, last_total_games=50,
            opponents={1: [opp, 0.0]},
            is_unrated=False, is_temp=False,
        )
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating < 1500

    def test_rating_never_below_one(self, make_tournament_player):
        opp = self._make_opponent(make_tournament_player, last_rating=1,
                                  new_rating=None, is_unrated=False, is_temp=False)
        p = make_tournament_player(
            last_rating=1, last_total_games=50,
            opponents={1: [opp, 0.0]},
            is_unrated=False, is_temp=False,
        )
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating >= 1

    def test_unrated_opponent_excluded_for_unrated_player(self, make_tournament_player):
        opp_unrated = self._make_opponent(make_tournament_player, last_rating=0,
                                          new_rating=None, is_unrated=True, is_temp=False)
        p = make_tournament_player(
            last_rating=0, last_total_games=0,
            opponents={1: [opp_unrated, 1.0]},
            is_unrated=True, is_temp=False,
        )
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating == 0

    def test_temp_player_rating_accumulates(self, make_tournament_player):
        opp = self._make_opponent(make_tournament_player, last_rating=1400,
                                  new_rating=None, is_unrated=False, is_temp=False)
        p = make_tournament_player(
            last_rating=1350, last_total_games=5,
            last_sum_oppon_ratings=7000, last_pts_against_oppon=3.0,
            opponents={1: [opp, 1.0]},
            is_unrated=False, is_temp=True,
        )
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating is not None
        assert p.new_total_games == 6
        assert p.calc_rule == CalcRule.TEMPORARY

    def test_calc_rule_set_after_calculation(self, make_tournament_player):
        opp = self._make_opponent(make_tournament_player, last_rating=1500,
                                  new_rating=None, is_unrated=False, is_temp=False)
        p = make_tournament_player(
            last_rating=1500, last_total_games=50,
            opponents={1: [opp, 0.5]},
            is_unrated=False, is_temp=False,
        )
        p.calculate_new_rating(is_fexerj_tournament=True)
        assert p.calc_rule in {CalcRule.NORMAL, CalcRule.DOUBLE_K, CalcRule.RATING_PERFORMANCE}


# ---------------------------------------------------------------------------
# calculate_new_rating — exact formula verification per calc_rule path
# ---------------------------------------------------------------------------

class TestCalculateNewRatingPaths:
    def _opp(self, make_tournament_player, **kwargs):
        return make_tournament_player(**kwargs)

    def test_normal_rule_exact_gain(self, make_tournament_player):
        # 4 opponents at 1500, player at 1500, scores 3/4
        # k=15 (50 games), expected=2.0, points_above=1.0 → gain=15 → new=1515
        opps = {i: [self._opp(make_tournament_player, last_rating=1500,
                              new_rating=None, is_unrated=False, is_temp=False), score]
                for i, score in enumerate([1.0, 1.0, 1.0, 0.0], start=1)}
        p = make_tournament_player(last_rating=1500, last_total_games=50,
                                   opponents=opps, is_unrated=False, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.calc_rule == CalcRule.NORMAL
        assert p.new_rating == 1515

    def test_double_k_exact_gain(self, make_tournament_player):
        # 4 opponents at 1500, scores 4/4
        # k=15, expected=2.0, points_above=2.0 → gain=2*15*2=60 → new=1560
        opps = {i: [self._opp(make_tournament_player, last_rating=1500,
                              new_rating=None, is_unrated=False, is_temp=False), 1.0]
                for i in range(1, 5)}
        p = make_tournament_player(last_rating=1500, last_total_games=50,
                                   opponents=opps, is_unrated=False, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.calc_rule == CalcRule.DOUBLE_K
        assert p.new_rating == 1560

    def test_rating_performance_exact_formula(self, make_tournament_player):
        # 5 opponents at 1500, all wins → RP rule in FEXERJ tournament
        opps = {i: [self._opp(make_tournament_player, last_rating=1500,
                              new_rating=None, is_unrated=False, is_temp=False), 1.0]
                for i in range(1, 6)}
        p = make_tournament_player(last_rating=1500, last_total_games=50,
                                   opponents=opps, is_unrated=False, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=True)
        assert p.calc_rule == CalcRule.RATING_PERFORMANCE
        performance = p.get_performance_rating(1500, 5, 5.0)
        expected_new = round(1500 + (performance - 1500) / 2)
        assert p.new_rating == expected_new

    def test_unrated_player_with_positive_score_gets_new_rating(self, make_tournament_player):
        opp = self._opp(make_tournament_player, last_rating=1500,
                        new_rating=None, is_unrated=False, is_temp=False)
        p = make_tournament_player(last_rating=0, last_total_games=0,
                                   last_sum_oppon_ratings=0, last_pts_against_oppon=0.0,
                                   opponents={1: [opp, 1.0]},
                                   is_unrated=True, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating is not None
        assert p.new_rating > 0
        assert p.new_total_games == 1
        assert p.calc_rule == CalcRule.TEMPORARY


# ---------------------------------------------------------------------------
# calculate_new_rating — opponent rating source selection
# ---------------------------------------------------------------------------

class TestOpponentRatingSelection:
    def test_established_vs_unrated_uses_new_rating(self, make_tournament_player):
        opp = make_tournament_player(last_rating=0, new_rating=1000,
                                     is_unrated=True, is_temp=False)
        p = make_tournament_player(last_rating=1500, last_total_games=50,
                                   opponents={1: [opp, 0.5]},
                                   is_unrated=False, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.this_sum_oppon_ratings == 1000

    def test_established_vs_temp_uses_new_rating(self, make_tournament_player):
        opp = make_tournament_player(last_rating=1300, new_rating=1350,
                                     is_unrated=False, is_temp=True)
        p = make_tournament_player(last_rating=1500, last_total_games=50,
                                   opponents={1: [opp, 0.5]},
                                   is_unrated=False, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.this_sum_oppon_ratings == 1350

    def test_established_vs_established_uses_last_rating(self, make_tournament_player):
        opp = make_tournament_player(last_rating=1600, new_rating=1700,
                                     is_unrated=False, is_temp=False)
        p = make_tournament_player(last_rating=1500, last_total_games=50,
                                   opponents={1: [opp, 0.5]},
                                   is_unrated=False, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.this_sum_oppon_ratings == 1600

    def test_unrated_opponent_excluded_when_new_rating_is_zero(self, make_tournament_player):
        opp = make_tournament_player(last_rating=0, new_rating=0,
                                     is_unrated=True, is_temp=False)
        p = make_tournament_player(last_rating=1500, last_total_games=50,
                                   opponents={1: [opp, 1.0]},
                                   is_unrated=False, is_temp=False)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.new_rating == 1500

    def test_temp_vs_temp_uses_last_rating(self, make_tournament_player):
        opp = make_tournament_player(last_rating=1300, new_rating=1350,
                                     is_unrated=False, is_temp=True)
        p = make_tournament_player(last_rating=1200, last_total_games=5,
                                   last_sum_oppon_ratings=0, last_pts_against_oppon=0.0,
                                   opponents={1: [opp, 0.5]},
                                   is_unrated=False, is_temp=True)
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.this_sum_oppon_ratings == 1300

    def test_sum_uses_correct_rating_per_opponent_type(self, make_tournament_player):
        """Established player facing unrated (new=1200), temp (new=1350),
        and established (last=1600): sum must be 1200 + 1350 + 1600 = 4150."""
        opp_unrated = make_tournament_player(last_rating=0, new_rating=1200,
                                             is_unrated=True, is_temp=False)
        opp_temp = make_tournament_player(last_rating=1300, new_rating=1350,
                                          is_unrated=False, is_temp=True)
        opp_estab = make_tournament_player(last_rating=1600, new_rating=1700,
                                           is_unrated=False, is_temp=False)
        p = make_tournament_player(
            last_rating=1500, last_total_games=50,
            opponents={1: [opp_unrated, 1.0], 2: [opp_temp, 1.0], 3: [opp_estab, 0.0]},
            is_unrated=False, is_temp=False,
        )
        p.calculate_new_rating(is_fexerj_tournament=False)
        assert p.this_sum_oppon_ratings == 4150
        assert p.this_games == 3
