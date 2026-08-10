"""Primitives from spec §2, §3 and §7."""
from decimal import Decimal

import pytest

from calculator.fide import rules


class TestCappedDiff:
    @pytest.mark.parametrize("player,opponent,expected", [
        (1800, 1700, 100),
        (1700, 1800, -100),
        (2400, 1500, 400),      # positive cap
        (1500, 2400, -400),     # negative cap
        (2000, 1600, 400),      # exactly at the cap, not clipped
        (1500, 1500, 0),
    ])
    def test_caps_at_400_both_directions(self, player, opponent, expected):
        assert rules.capped_diff(player, opponent) == expected

    def test_cap_applies_even_for_very_high_ratings(self):
        """Art. 68 §3: the FIDE exception for 2650+ does not apply at FEXERJ."""
        assert rules.capped_diff(2700, 1500) == 400


class TestRoundHalfAwayFromZero:
    @pytest.mark.parametrize("value,expected", [
        ("0.5", 1),      # built-in round() would give 0
        ("1.5", 2),
        ("2.5", 3),      # built-in round() would give 2
        ("-0.5", -1),    # built-in round() would give 0
        ("-2.5", -3),
        ("0.4", 0),
        ("-0.4", 0),
        ("19.60", 20),
        ("-19.60", -20),
    ])
    def test_ties_go_away_from_zero(self, value, expected):
        assert rules.round_half_away_from_zero(Decimal(value)) == expected


class TestRatingFloor:
    @pytest.mark.parametrize("rating,expected", [
        (1199, True), (1200, False), (0, True), (2000, False),
    ])
    def test_floor_at_1200(self, rating, expected):
        assert rules.applies_rating_floor(rating) is expected


def test_constants_match_art_68():
    assert rules.RATING_FLOOR == 1200
    assert rules.FICTITIOUS_OPPONENT_RATING == 1600
    assert rules.INITIAL_RATING_CAP == 2000
    assert rules.K10_THRESHOLD == 2200
    assert rules.U18_RATING_CAP == 2100
    assert rules.MAX_RATING_DIFF == 400
    assert rules.MIN_GAMES_FOR_FIRST_RATING == 5
    assert rules.NEW_PLAYER_GAMES == 30
    assert rules.K_GAMES_PRODUCT_CAP == 700
