"""Cross-modality transposition (§1.1) and the in-period initial rating (§6)."""
from decimal import Decimal

from calculator.fide.model import Game, ModalityState, PlayerState
from calculator.fide.period import compute_unrated_period, transposed_state


def _game(ord_, opponent_id, score):
    return Game(ord_, "RPD", False, 1, opponent_id, Decimal(score))


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
        state = ModalityState(games=1, sum_opponents=1600, points=Decimal("0.5"))
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0")],
            opponent_ratings={2: 1700, 3: 1500},
        )
        assert result.accumulated_sum_opponents == 1600 + 1700 + 1500
        assert result.accumulated_points == Decimal("1.5")

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
        state = ModalityState(games=3, sum_opponents=5400, points=Decimal("1.5"))
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
        state = ModalityState(games=4, sum_opponents=6400, points=Decimal("2"))
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
