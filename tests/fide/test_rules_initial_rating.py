"""Initial rating for a non-rated player — spec §6."""
from decimal import Decimal

from calculator.fide.rules import initial_rating


def test_five_draws_against_1600_lands_on_1600():
    """Five draws against 1600, plus the two fictitious 1600 opponents, give p = 0.50 and dp = 0."""
    assert initial_rating(1600 * 5, 5, Decimal("2.5")) == 1600


def test_fictitious_opponents_enter_the_average_and_the_score():
    """Ra and p include the two fictitious 1600 opponents, drawn against (§6.2)."""
    # Ra = (5x1700 + 2x1600) / 7 = 11700/7 = 1671.428...
    # p  = (2.5 + 1) / 7 = 0.5 -> dp = 0 -> 1671
    # Without fictitious opponents an implementation would return 1700, so this test catches that omission.
    assert initial_rating(1700 * 5, 5, Decimal("2.5")) == 1671


def test_caps_at_2000():
    assert initial_rating(2000 * 5, 5, Decimal("5")) == 2000


def test_returns_none_below_the_floor():
    """Below 1200 the player stays non-rated (§6.2)."""
    assert initial_rating(1300 * 5, 5, Decimal("0")) is None


def test_uses_the_table_not_the_logistic_formula():
    # Ra = (5x1500 + 2x1600) / 7 = 10700/7 = 1528.571...
    # p  = (3 + 1) / 7 = 0.5714... -> 0.57 -> dp = 50 -> 1578.571... -> 1579
    assert initial_rating(1500 * 5, 5, Decimal("3")) == 1579


def test_uses_the_exact_sum_not_a_rounded_average():
    """The accumulator stores the sum; rebuilding it from the average would lose the division remainder."""
    # sum = 7514 (not evenly divisible by 5); Ra = (7514 + 3200) / 7 = 10714/7 = 1530.571... -> 1531
    # p = (2.5 + 1) / 7 = 0.50 -> dp = 0
    # An implementation using 7514/5 = 1502.8, then treating it as 1502 or 1503 would differ from the exact sum.
    assert initial_rating(7514, 5, Decimal("2.5")) == 1531
