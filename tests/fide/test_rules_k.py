"""K factor — spec §5."""
import pytest

from calculator.fide import rules


class TestBaseK:
    def test_new_player_gets_40_until_30_games(self):
        assert rules.base_k(1500, 0, False, 1990, 2026) == 40
        assert rules.base_k(1500, 29, False, 1990, 2026) == 40

    def test_after_30_games_drops_to_20(self):
        assert rules.base_k(1500, 30, False, 1990, 2026) == 20

    def test_under_18_keeps_40_below_2100(self):
        """Holds until the end of the year the player turns 18."""
        assert rules.base_k(1800, 50, False, 2008, 2026) == 40

    def test_under_18_loses_40_at_or_above_2100(self):
        assert rules.base_k(2100, 50, False, 2008, 2026) == 20

    def test_year_after_turning_18_drops_to_20(self):
        assert rules.base_k(1800, 50, False, 2008, 2027) == 20

    def test_reached_2200_gives_permanent_10(self):
        """K=10 is permanent even after the rating drops (§5)."""
        assert rules.base_k(2250, 200, True, 1990, 2026) == 10
        assert rules.base_k(1900, 200, True, 1990, 2026) == 10

    def test_high_rating_without_the_flag_stays_at_20(self):
        """The flag decides, not the current rating."""
        assert rules.base_k(2250, 200, False, 1990, 2026) == 20

    def test_missing_birth_year_falls_back_to_the_non_u18_path(self):
        assert rules.base_k(1800, 50, False, None, 2026) == 20


class TestIsUnder18AtYearEnd:
    @pytest.mark.parametrize("birth_year,period_year,expected", [
        (2008, 2026, True),    # turns 18 in 2026 — holds until 12/31
        (2008, 2027, False),
        (2010, 2026, True),
        (1990, 2026, False),
    ])
    def test_boundary_is_the_end_of_the_year(self, birth_year, period_year, expected):
        assert rules.is_under_18_at_year_end(birth_year, period_year) is expected


class TestHalveForInternal:
    @pytest.mark.parametrize("k,expected", [(40, 20), (20, 10), (10, 5)])
    def test_halves_each_k(self, k, expected):
        assert rules.halve_for_internal(k) == expected


class TestCapKByGames:
    def test_no_cap_below_the_limit(self):
        assert rules.cap_k_by_games(40, 17) == 40   # 17 x 40 = 680

    def test_caps_when_product_exceeds_700(self):
        assert rules.cap_k_by_games(40, 18) == 38   # 18 x 38 = 684 <= 700

    def test_exact_limit_is_not_capped(self):
        assert rules.cap_k_by_games(20, 35) == 20   # 35 x 20 = 700

    def test_zero_games_is_a_no_op(self):
        assert rules.cap_k_by_games(40, 0) == 40


class TestParseBirthYear:
    @pytest.mark.parametrize("birthday,expected", [
        ("01/01/1990", 1990),
        ("15/06/2008", 2008),
        ("1990-01-01", 1990),
        ("", None),
        ("not a date", None),
    ])
    def test_accepts_both_formats(self, birthday, expected):
        assert rules.parse_birth_year(birthday) == expected


def test_order_is_halve_then_cap():
    """§5.1: the 700 cap is applied last, after the Art. 68 §2 halving."""
    k = rules.halve_for_internal(rules.base_k(1500, 0, False, 1990, 2026))
    assert k == 20
    assert rules.cap_k_by_games(k, 40) == 17   # 40 x 17 = 680 <= 700
