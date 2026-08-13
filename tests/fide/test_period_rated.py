"""Rated player period calculation — spec §3, §4 and §5."""
from decimal import Decimal

from calculator.fide.model import Game, ModalityState, PlayerState
from calculator.fide.period import compute_rated_period, fide_substitution_state


def _game(ord_, opponent_id, score):
    return Game(ord_, "STD", 1, opponent_id, Decimal(score))


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


class TestKIsConstantAcrossTheWholePeriod:
    def test_a_period_mixing_two_tournaments_applies_the_same_k_to_every_game(self):
        """FEXERJ abolished the Art. 68 §2 halving (§2, §5.2): a period built from
        more than one tournament — one of them formerly "internal", one not — gets
        exactly one K for every game, regardless of which tournament it came from.
        This is the guarantee that the old exception is gone, not half-applied."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(2, 3, "1")],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        ks = {g.k for g in result.game_results}
        assert ks == {20}


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


class TestFideSubstitution:
    """§6.4, decided by FEXERJ on 2026-08-13: a local rating that stopped in
    time is replaced by the player's FIDE rating on the period they come
    back. Three conditions, all at once: local rating below 1600, FIDE rating
    of 2000 or more, and more than 26 months without playing that modality."""

    MONTH = "2026-03"

    def _player(self, **std):
        state = ModalityState(**{
            "rating": 1400, "games": 60, "last_played": "2023-01",
            "fide_rating": 2100, "fide_date": "10/07/2026",
            **std,
        })
        return PlayerState(
            id_fexerj=1, name="Player One",
            modalities={"STD": state, "RPD": ModalityState(), "BLZ": ModalityState()},
        )

    def test_all_three_conditions_met_substitutes(self):
        state, substitution = fide_substitution_state(self._player(), "STD", self.MONTH)
        assert state.rating == 2100
        assert substitution.previous_rating == 1400
        assert substitution.source == "FIDE"
        assert substitution.checked_on == "10/07/2026"

    def test_an_active_player_is_left_alone(self):
        """The one the federation asked about: a gap on an active player is
        two fields of opponents disagreeing, not a stale number."""
        assert fide_substitution_state(
            self._player(last_played="2026-01"), "STD", self.MONTH
        ) is None

    def test_exactly_at_the_window_is_still_active(self):
        """26 months elapsed is inside the window; the rule needs *more* than 26."""
        assert fide_substitution_state(
            self._player(last_played="2024-01"), "STD", self.MONTH
        ) is None

    def test_one_month_past_the_window_substitutes(self):
        assert fide_substitution_state(
            self._player(last_played="2023-12"), "STD", self.MONTH
        ) is not None

    def test_a_local_rating_at_1600_is_left_alone(self):
        assert fide_substitution_state(self._player(rating=1600), "STD", self.MONTH) is None

    def test_a_local_rating_just_below_1600_substitutes(self):
        assert fide_substitution_state(self._player(rating=1599), "STD", self.MONTH) is not None

    def test_a_fide_rating_below_2000_is_left_alone(self):
        assert fide_substitution_state(self._player(fide_rating=1999), "STD", self.MONTH) is None

    def test_a_fide_rating_of_exactly_2000_substitutes(self):
        """"2000 ou mais" — the case that motivated the rule lands exactly on
        the boundary, which is why it is not "acima de 2000"."""
        assert fide_substitution_state(self._player(fide_rating=2000), "STD", self.MONTH) is not None

    def test_no_fide_rating_is_left_alone(self):
        assert fide_substitution_state(self._player(fide_rating=None), "STD", self.MONTH) is None

    def test_no_local_rating_is_not_below_1600(self):
        """Having no rating is the absence of one, not a low one — the same
        reading §7 takes of a zero in the list being converted. An unrated
        player takes the §6.1 road back."""
        assert fide_substitution_state(self._player(rating=None), "STD", self.MONTH) is None

    def test_an_empty_activity_date_counts_as_inactive(self):
        """Every player converted from the current list arrives with this
        column empty, since the old format never had it."""
        assert fide_substitution_state(self._player(last_played=""), "STD", self.MONTH) is not None

    def test_the_game_count_is_untouched(self):
        """One of the three questions FEXERJ used to sink an earlier proposal:
        the substitution alters no game count."""
        state, _ = fide_substitution_state(self._player(), "STD", self.MONTH)
        assert state.games == 60

    def test_a_fide_rating_of_2200_locks_the_permanent_k10(self):
        state, _ = fide_substitution_state(self._player(fide_rating=2200), "STD", self.MONTH)
        assert state.reached_2200 is True

    def test_below_2200_does_not_lock_it(self):
        state, _ = fide_substitution_state(self._player(fide_rating=2199), "STD", self.MONTH)
        assert state.reached_2200 is False

    def test_a_player_who_already_reached_2200_keeps_it(self):
        state, _ = fide_substitution_state(
            self._player(fide_rating=2000, reached_2200=True), "STD", self.MONTH
        )
        assert state.reached_2200 is True

    def test_the_substituted_rating_drives_the_period(self):
        """The substitution happens before the calculation, so every game of
        the period is computed against the new rating."""
        state, substitution = fide_substitution_state(self._player(), "STD", self.MONTH)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1")],
            opponent_ratings={2: 2000},
            period_year=2026, birth_year=None,
            substitution=substitution,
        )
        assert result.initial_rating == 2100
        assert result.substitution is substitution

    def test_it_fires_again_on_a_later_return(self):
        """FEXERJ, 2026-08-13: "deve valer de novo tantas vezes quanto
        necessário". Nothing records that a substitution already happened,
        and nothing needs to: the substitution itself lifts the rating over
        1600 and stamps the activity date, so only another long absence
        *and* another fall back below 1600 can bring the conditions round
        again. This is the state of a player that happened to."""
        after_a_previous_substitution = self._player(
            rating=1450, last_played="2023-05", fide_rating=2100,
        )
        assert fide_substitution_state(
            after_a_previous_substitution, "STD", self.MONTH
        ) is not None
