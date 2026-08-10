"""Correctness anchor: the official FIDE query cited in spec §10.

The value of this test is not proving the model is correct — the three games
documented in §10 are already covered in test_tables.py. It proves that the
*period* arithmetic — summing every game's delta, multiplying by K, and
rounding once (§3 step 5 / §8.3.4) — reproduces numbers FIDE itself
published for a real player over a real period.
"""
import pathlib
from decimal import Decimal

import pytest

from calculator.fide.model import Game, ModalityState
from calculator.fide.period import compute_rated_period

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "fide_official_period.csv"

EXPECTED_TOTAL_VARIATION = Decimal("19.60")
EXPECTED_ROUNDED_VARIATION = 20


def _load() -> tuple[int, int, list[tuple[int, Decimal, Decimal]]]:
    """Return (initial_rating, k, [(opponent_rating, score, expected_delta), ...])."""
    meta: dict[str, str] = {}
    rows: list[tuple[int, Decimal, Decimal]] = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "=" in line:
                key, _, value = line.lstrip("# ").partition("=")
                meta[key.strip()] = value.strip()
            continue
        if line.startswith("opponent_rating"):
            continue
        opponent, score, delta = line.split(";")
        rows.append((int(opponent), Decimal(score), Decimal(delta)))
    return int(meta["initial_rating"]), int(meta["k"]), rows


def _state(initial_rating: int) -> ModalityState:
    """The player's state at the start of the period.

    `games=100` clears the 30-game newcomer threshold, and `reached_2200` is
    set explicitly: the fixture's published k=10 is the permanent K a player
    keeps after crossing 2200 (§5), which `base_k` only grants through this
    flag — never from the rating value alone.
    """
    return ModalityState(rating=initial_rating, games=100, reached_2200=True)


def test_fixture_has_the_thirteen_games():
    _, _, rows = _load()
    assert len(rows) == 13


@pytest.mark.parametrize("index", range(13))
def test_each_game_matches_the_official_delta(index):
    initial_rating, _, rows = _load()
    opponent_rating, score, expected_delta = rows[index]
    result = compute_rated_period(
        player_id=1, modality="STD", state=_state(initial_rating),
        games=[Game(1, "STD", 1, 2, score)],
        opponent_ratings={2: opponent_rating},
        period_year=2026, birth_year=1970,
    )
    assert result.game_results[0].delta == expected_delta


def test_period_total_matches_the_published_variation():
    """§3 step 5 / §8.3.4: sum every delta, multiply by K, round once.

    FIDE published 19.60 for the period (11.40 and 8.20 per tournament,
    undrounded), which rounds to +20. The two tournaments are folded into a
    single K group here since K is uniform (10) across the whole period, so
    the grouping cannot change the sum.
    """
    initial_rating, k, rows = _load()
    games = [Game(1, "STD", 1, 100 + i, score) for i, (_, score, _) in enumerate(rows)]
    opponent_ratings = {100 + i: opponent for i, (opponent, _, _) in enumerate(rows)}
    result = compute_rated_period(
        player_id=1, modality="STD", state=_state(initial_rating),
        games=games, opponent_ratings=opponent_ratings,
        period_year=2026, birth_year=1970,
    )
    assert result.variation == EXPECTED_TOTAL_VARIATION
    assert result.rounded_variation == EXPECTED_ROUNDED_VARIATION
    assert all(g.k == k for g in result.game_results)
