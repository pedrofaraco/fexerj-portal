"""Cross-modality transposition (§1.1) and the in-period initial rating (§6)."""
from decimal import Decimal

from calculator.fide.model import Game, ModalityState, PlayerState
from calculator.fide.period import compute_rated_period, compute_unrated_period, transposed_state


def _game(ord_, opponent_id, score):
    return Game(ord_, "RPD", 1, opponent_id, Decimal(score))


class TestTransposedState:
    def test_uses_the_std_rating_with_zero_games(self):
        """§1.1: enters with the STD rating; K comes out of the new modality's own count."""
        player = PlayerState(id_fexerj=1, name="Carlos Mendes")
        player.modalities["STD"] = ModalityState(rating=1800, games=120, reached_2200=False)
        state = transposed_state(player, "RPD")
        assert state is not None
        assert state.rating == 1800
        assert state.games == 0

    def test_peak_flag_does_not_carry_over(self):
        """Counts and flags are independent per modality (§1.1)."""
        player = PlayerState(id_fexerj=1, name="Roberto Faria")
        player.modalities["STD"] = ModalityState(rating=2250, games=300, reached_2200=True)
        state = transposed_state(player, "RPD")
        assert state is not None
        assert state.reached_2200 is False

    def test_returns_none_when_the_modality_already_has_a_rating(self):
        player = PlayerState(id_fexerj=1, name="Andre Nunes")
        player.modalities["STD"] = ModalityState(rating=1800, games=120)
        player.modalities["RPD"] = ModalityState(rating=1700, games=20)
        assert transposed_state(player, "RPD") is None

    def test_returns_none_without_a_std_rating(self):
        player = PlayerState(id_fexerj=1, name="Felipe Borges")
        assert transposed_state(player, "RPD") is None

    def test_std_never_transposes_from_itself(self):
        player = PlayerState(id_fexerj=1, name="Lucas Carvalho")
        player.modalities["STD"] = ModalityState(rating=1800, games=120)
        assert transposed_state(player, "STD") is None


class TestUnratedPeriod:
    def test_below_five_games_accumulates_without_a_rating(self):
        """§6.1: nothing is published before five games against rated opponents."""
        state = ModalityState()
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0")],
            opponent_ratings={2: 1600, 3: 1600},
        )
        assert result.final_rating is None
        assert result.path == "ACCUMULATING"
        assert result.games_counted == 2

    def test_accumulator_advances_so_the_next_period_can_reach_five(self):
        """Without this, the player counts games but never accumulates opponent sum and points."""
        state = ModalityState(games=1, accumulated_games=1, sum_opponents=1600, points=Decimal("0.5"))
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0")],
            opponent_ratings={2: 1700, 3: 1500},
        )
        assert result.accumulated_sum_opponents == 1600 + 1700 + 1500
        assert result.accumulated_points == Decimal("1.5")
        assert result.accumulated_games == 3

    def test_a_discarded_first_event_does_not_advance_the_accumulator(self):
        state = ModalityState()
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, i, "0") for i in range(2, 8)],
            opponent_ratings={i: 1600 for i in range(2, 8)},
        )
        assert result.accumulated_sum_opponents == 0
        assert result.accumulated_points == Decimal("0")

    def test_five_games_produce_an_initial_rating(self):
        # Opponents at 1800, not 1600: at 1600 the result comes out 1600
        # whether or not the two fictitious 1600 opponents from §6.2 are
        # actually folded in, so that value can't tell a correct
        # implementation from one that dropped them.
        state = ModalityState()
        games = [_game(1, i, "0.5") for i in range(2, 7)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1800 for i in range(2, 7)},
        )
        assert result.final_rating == 1743
        assert result.path == "INITIAL_RATING"

    def test_accumulated_history_counts_toward_the_five(self):
        # Same reasoning as above: opponents at 1800, not 1600, so the
        # fictitious opponents are actually exercised by the assertion.
        state = ModalityState(games=3, accumulated_games=3, sum_opponents=5400, points=Decimal("1.5"))
        games = [_game(1, i, "0.5") for i in range(2, 4)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={2: 1800, 3: 1800},
        )
        assert result.final_rating == 1743

    def test_a_zeroed_first_event_is_discarded(self):
        """§6.1 / 8.2.1: zeroing the first event discards the result."""
        state = ModalityState()
        games = [_game(1, i, "0") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 8)},
        )
        assert result.final_rating is None
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.games_counted == 0

    def test_a_zeroed_later_event_is_not_discarded(self):
        state = ModalityState(games=4, accumulated_games=4, sum_opponents=6400, points=Decimal("2"))
        games = [_game(1, i, "0") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 8)},
        )
        assert result.path == "INITIAL_RATING"

    def test_below_the_floor_stays_unrated(self):
        state = ModalityState()
        games = [_game(1, i, "0.5") for i in range(2, 7)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1000 for i in range(2, 7)},
        )
        assert result.final_rating is None
        assert result.path == "BELOW_FLOOR"


class TestFloorExpelledPlayerAccumulator:
    """A player dropped out of rated status by the §7 floor keeps their
    lifetime `games` count (K and §7 need it), but the §6.1 accumulator
    toward the next initial rating has to start over from
    `accumulated_games`, not from that lifetime count — otherwise the
    "phantom" lifetime games, which never fed `sum_opponents`/`points`,
    drag the average down and the player can never climb back out."""

    def test_floor_expelled_player_returns_with_a_rating(self):
        """The reported bug: a player with 60 lifetime games, expelled by the
        floor, wins six games against 1500-rated opponents. Confusing the
        lifetime count for the accumulator used to send this player out with
        no rating at all (66 phantom games diluting the average below 1200);
        with the two counts separated, the six real games alone decide it."""
        state = ModalityState(rating=None, games=60, sum_opponents=0, points=Decimal("0"))
        games = [_game(1, i, "1") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1500 for i in range(2, 8)},
        )
        assert result.final_rating == 1861
        assert result.path == "INITIAL_RATING"

    def test_accumulates_in_one_period_and_rates_in_the_next(self):
        """Same floor-expelled player, but the six games needed for a first
        rating are spread across two periods — proving the accumulator (not
        just a single call) carries `accumulated_games` forward correctly."""
        state = ModalityState(rating=None, games=60, sum_opponents=0, points=Decimal("0"))
        period_one = [_game(1, i, "1") for i in range(2, 4)]  # 2 games
        result_one = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=period_one,
            opponent_ratings={i: 1500 for i in range(2, 4)},
        )
        assert result_one.path == "ACCUMULATING"
        assert result_one.accumulated_games == 2

        # The lifetime count keeps growing (as cycle.py's _apply_results does),
        # while the accumulator carries over from result_one.
        state_period_two = ModalityState(
            rating=None,
            games=state.games + result_one.games_counted,
            sum_opponents=result_one.accumulated_sum_opponents,
            points=result_one.accumulated_points,
            accumulated_games=result_one.accumulated_games,
        )
        period_two = [_game(2, i, "1") for i in range(4, 8)]  # 4 more games -> 6 total
        result_two = compute_unrated_period(
            player_id=1, modality="RPD", state=state_period_two,
            games=period_two,
            opponent_ratings={i: 1500 for i in range(4, 8)},
        )
        assert result_two.path == "INITIAL_RATING"
        assert result_two.final_rating == 1861

    def test_lifetime_games_still_drive_k_after_the_floor_acted(self):
        """§7 preserves the lifetime `games` count when the floor acts; this
        confirms `compute_rated_period` still reads it correctly once the
        player is rated again — a player with 60+ lifetime games must not be
        charged the new-player K=40."""
        state = ModalityState(rating=1861, games=66, reached_2200=False)
        result = compute_rated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "1")],
            opponent_ratings={2: 1700},
            period_year=2026, birth_year=None,
        )
        assert result.game_results[0].k == 20
