"""Rated player period calculation — spec §3, §4 and §5."""
from decimal import Decimal

from calculator.fide.model import Game, ModalityState
from calculator.fide.period import compute_rated_period


def _game(ord_, opponent_id, score, internal=False):
    return Game(ord_, "STD", internal, 1, opponent_id, Decimal(score))


class TestSingleGame:
    def test_delta_is_result_minus_pd(self):
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1")],
            opponent_ratings={2: 1700},
            period_year=2026, birth_year=1990,
        )
        # D = 100 -> PD = 0.64 -> delta = 1 - 0.64 = 0.36
        assert result.game_results[0].pd == Decimal("0.64")
        assert result.game_results[0].delta == Decimal("0.36")

    def test_opponent_rating_is_capped_before_the_lookup(self):
        state = ModalityState(rating=2400, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1")],
            opponent_ratings={2: 1500},
            period_year=2026, birth_year=1990,
        )
        assert result.game_results[0].capped_diff == 400
        assert result.game_results[0].pd == Decimal("0.92")


class TestPeriodAggregation:
    def test_all_games_use_the_start_of_period_rating(self):
        """§4: the rating is not updated between tournaments within the same period."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(2, 3, "1")],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        assert all(g.capped_diff == 100 for g in result.game_results)

    def test_rounds_once_at_the_end(self):
        """§3 step 5: a single rounding per period, not one per game.

        Three draws against an opponent 50 points above, player at 1500, K=20.
        Each game's delta is 0.07, so the period sum is 0.21 and the variation
        is 0.21 x 20 = 4.20, which rounds to 4. Rounding game by game would
        give 1 + 1 + 1 = 3 instead (0.07 x 20 = 1.4 rounds to 1 on each game)
        — this case exists to catch exactly that structural bug.
        """
        state = ModalityState(rating=1500, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "0.5"), _game(1, 2, "0.5"), _game(1, 2, "0.5")],
            opponent_ratings={2: 1550},
            period_year=2026, birth_year=1990,
        )
        assert result.sum_delta == Decimal("0.21")
        assert result.rounded_variation == 4
        assert result.final_rating == 1504

    def test_games_against_unrated_opponents_are_skipped(self):
        """§3: games against unrated opponents don't enter the rated calculation."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "1")],
            opponent_ratings={2: 1700},   # player 3 has no rating
            period_year=2026, birth_year=1990,
        )
        assert result.games_counted == 1


class TestKWithinThePeriod:
    def test_internal_tournament_uses_half_k(self):
        """§5.2: the internal tournament is the exception to the constant-K rule."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(2, 3, "1", internal=True)],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        by_tournament = {g.game.tournament_ord: g.k for g in result.game_results}
        assert by_tournament[1] == 20
        assert by_tournament[2] == 10

    def test_variation_sums_delta_times_k_per_game(self):
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(2, 3, "1", internal=True)],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        # 0.36 x 20 + 0.36 x 10 = 7.2 + 3.6 = 10.8 -> 11
        assert result.sum_delta == Decimal("0.72")
        assert result.variation == Decimal("10.8")
        assert result.rounded_variation == 11


class TestPeriodCap:
    def test_700_cap_applies_to_the_period_total_not_per_tournament(self):
        """§5.1, decided by FEXERJ: two 20-game tournaments in the same period share one
        cap. The old per-tournament cap let each 20-game tournament reach its own K=35
        (700 // 20), for a period total of 1400 — double the 700 limit. Capped over the
        period's 40 games, K must be 17 (40 x 17 = 680) in both tournaments."""
        state = ModalityState(rating=1500, games=0)
        games = [_game(1, 2, "0.5") for _ in range(20)] + [_game(2, 2, "0.5") for _ in range(20)]
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=games,
            opponent_ratings={2: 1500},
            period_year=2026, birth_year=1990,
        )
        ks = {g.k for g in result.game_results}
        assert ks == {17}

    def test_internal_tournament_half_is_exactly_half_of_the_capped_k(self):
        """The cap now runs before the halving: the internal tournament's K is half of
        the already-capped period K=17, not half of the raw K=40 — the only order where
        the internal-tournament half stays exactly a half."""
        state = ModalityState(rating=1500, games=0)
        games = (
            [_game(1, 2, "0.5") for _ in range(20)]
            + [_game(2, 2, "0.5", internal=True) for _ in range(20)]
        )
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=games,
            opponent_ratings={2: 1500},
            period_year=2026, birth_year=1990,
        )
        by_tournament = {g.game.tournament_ord: g.k for g in result.game_results}
        assert by_tournament[1] == 17
        assert by_tournament[2] == 8
        assert by_tournament[2] == by_tournament[1] // 2


class TestFloor:
    def test_dropping_below_1200_clears_the_rating(self):
        """§7: rating cleared, game count preserved."""
        state = ModalityState(rating=1205, games=50)
        games = [_game(1, i, "0") for i in range(2, 12)]
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 12)},
            period_year=2026, birth_year=1990,
        )
        assert result.final_rating is None
        assert result.games_counted == 10


class TestNoValidGames:
    def test_all_opponents_unrated_leaves_the_rating_unchanged(self):
        """No game survives the §3 filter: the player keeps their rating, untouched."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0.5")],
            opponent_ratings={},   # neither opponent has a rating
            period_year=2026, birth_year=1990,
        )
        assert result.games_counted == 0
        assert result.variation == Decimal("0")
        assert result.final_rating == 1800
