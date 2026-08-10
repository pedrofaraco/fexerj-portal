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

    def test_permanent_k10_takes_precedence_over_under_18(self):
        """K is a brake that only tightens (§5, decided by FEXERJ): a player who reached
        2200 and then dropped below 2100 before turning 18 keeps the permanent K=10,
        not the under-18 K=40 — the opposite of the old §5 table order."""
        assert rules.base_k(1900, 100, True, 2009, 2026) == 10

    def test_permanent_k10_takes_precedence_over_new_player(self):
        """Same rule, other collision: a player who reached 2200 in a modality but has
        fewer than 30 games in it keeps K=10, not the new-player K=40."""
        assert rules.base_k(1900, 5, True, 1990, 2026) == 10

    def test_transposed_player_keeps_new_player_40_despite_high_rating(self):
        """§1.1: `reached_2200` is per modality. A player entering a new modality with a
        high STD rating and zero games there still has the flag False and gets the
        new-player K=40 — the permanent K=10 never triggers on rating alone."""
        assert rules.base_k(2250, 0, False, 1990, 2026) == 40


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

    def test_period_example_40_games_at_k40_caps_to_17(self):
        """The headline §5.1 example: 40 games in the period under K=40 must cap to a
        single period K=17 (40 x 17 = 680), not to 35 per 20-game tournament."""
        assert rules.cap_k_by_games(40, 40) == 17


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

    def test_rejects_a_four_digit_run_inside_a_longer_digit_sequence(self):
        """The regex anchors on ^|\\D and \\D|$, so it must not pull a year out
        of the middle of a longer digit run — unlike a naive \\d{4} search."""
        assert rules.parse_birth_year("19901234") is None

    def test_still_accepts_both_formats_alongside_the_longer_sequence_case(self):
        assert rules.parse_birth_year("01/01/1990") == 1990
        assert rules.parse_birth_year("1990-01-01") == 1990


def test_order_is_cap_then_halve():
    """§5.1, decided by FEXERJ: the period cap runs first, then the Art. 68 §2 halving
    — the reverse of the old order. Halving the raw K=40 first and capping the halved
    K=20 on 40 games would also land on 17 here by coincidence (700 // 40 doesn't
    depend on K once the product exceeds 700); halving *after* the cap is what makes
    the internal-tournament K land at exactly half of 17, not half of 40."""
    period_k = rules.base_k(1500, 0, False, 1990, 2026)
    assert period_k == 40
    capped = rules.cap_k_by_games(period_k, 40)   # 40 x 40 = 1600 > 700 -> 700 // 40 = 17
    assert capped == 17
    assert rules.halve_for_internal(capped) == 8   # half of the capped 17, not of the raw 40


def test_sentinel_date_falls_into_the_safe_not_under_18_path():
    # Legacy "unknown date" sentinel. birth_year=0 makes is_under_18_at_year_end
    # False for any real period_year, so this falls into the safe (not-under-18)
    # path instead of wrongly granting K=40. Rejecting a missing date is the
    # validation layer's job, not these functions'.
    assert rules.parse_birth_year("00/00/0000") == 0
    assert rules.is_under_18_at_year_end(0, 2026) is False
