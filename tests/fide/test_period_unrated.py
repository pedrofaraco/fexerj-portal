"""Cross-modality transposition (§1.1) and the in-period initial rating (§6)."""
from decimal import Decimal

from calculator.fide.model import Accumulator, Game, ModalityState, PlayerState
from calculator.fide.period import compute_rated_period, compute_unrated_period, transposed_state

_MONTH = "2026-01"
_LATER_MONTH = "2026-03"


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
            period_month=_MONTH,
        )
        assert result.final_rating is None
        assert result.path == "ACCUMULATING"
        assert result.games_counted == 2

    def test_accumulator_advances_so_the_next_period_can_reach_five(self):
        """Without this, the player counts games but never accumulates opponent sum and points."""
        state = ModalityState(games=1, accumulator=Accumulator(
            games=1, sum_opponents=1600, points=Decimal("0.5"), since="2025-12",
        ))
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0")],
            opponent_ratings={2: 1700, 3: 1500},
            period_month=_MONTH,
        )
        assert result.accumulator.sum_opponents == 1600 + 1700 + 1500
        assert result.accumulator.points == Decimal("1.5")
        assert result.accumulator.games == 3
        assert result.accumulator.since == "2025-12"  # unchanged: the accumulation already had a start

    def test_a_discarded_first_event_does_not_advance_the_accumulator(self):
        state = ModalityState()
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, i, "0") for i in range(2, 8)],
            opponent_ratings={i: 1600 for i in range(2, 8)},
            period_month=_MONTH,
        )
        assert result.accumulator.sum_opponents == 0
        assert result.accumulator.points == Decimal("0")

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
            period_month=_MONTH,
        )
        assert result.final_rating == 1743
        assert result.path == "INITIAL_RATING"

    def test_accumulated_history_counts_toward_the_five(self):
        # Same reasoning as above: opponents at 1800, not 1600, so the
        # fictitious opponents are actually exercised by the assertion.
        state = ModalityState(games=3, accumulator=Accumulator(
            games=3, sum_opponents=5400, points=Decimal("1.5"), since="2025-11",
        ))
        games = [_game(1, i, "0.5") for i in range(2, 4)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={2: 1800, 3: 1800},
            period_month=_MONTH,
        )
        assert result.final_rating == 1743

    def test_a_zeroed_first_event_is_discarded(self):
        """§6.1 / 8.2.1: zeroing the first event discards the result from the
        accumulator, and — answered by FEXERJ — from `games_counted` too, the
        lifetime total §5's K factor reads. The count records games that were
        valid for a rating calculation, and these went into none."""
        state = ModalityState()
        games = [_game(1, i, "0") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 8)},
            period_month=_MONTH,
        )
        assert result.final_rating is None
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.games_counted == 0
        assert result.accumulator.games == 0
        # Nothing was accepted, which is what leaves the next scoreless
        # tournament discardable too.
        assert result.first_tournament_seen is False

    def test_a_zeroed_later_event_is_not_discarded(self):
        state = ModalityState(games=4, first_tournament_played=True, accumulator=Accumulator(
            games=4, sum_opponents=6400, points=Decimal("2"), since="2025-10",
        ))
        games = [_game(1, i, "0") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 8)},
            period_month=_MONTH,
        )
        assert result.path == "INITIAL_RATING"

    def test_below_the_floor_stays_unrated(self):
        state = ModalityState()
        games = [_game(1, i, "0.5") for i in range(2, 7)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1000 for i in range(2, 7)},
            period_month=_MONTH,
        )
        assert result.final_rating is None
        assert result.path == "BELOW_FLOOR"


class TestPerTournamentDiscard:
    """§6.1 / 8.2.1: "event" is the tournament, not the period — FEXERJ's
    reading of the FIDE rule, decided over the period-level reading the
    engine used to implement."""

    def test_zeroing_the_first_tournament_discards_only_that_tournament(self):
        """Two tournaments in the same period: zero in the first, a win in
        the second. The first tournament leaves nothing behind — neither in
        the accumulator nor in games_counted — while the second is counted
        normally, because the discard is per tournament and not per period."""
        state = ModalityState()
        games = [_game(1, 2, "0"), _game(1, 3, "0"), _game(2, 4, "1")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={2: 1600, 3: 1600, 4: 1600},
            period_month=_MONTH,
        )
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.games_counted == 1          # only the second tournament's game
        assert result.accumulator.games == 1        # only the second tournament fed the accumulator
        assert result.accumulator.points == Decimal("1")
        assert result.accumulator.sum_opponents == 1600

    def test_zeroing_a_tournament_that_is_not_the_first_discards_nothing(self):
        """Reversed order: a win in the first tournament spends the one
        discard opportunity, so a zero result in the second tournament of
        the same period counts normally instead of being discarded too."""
        state = ModalityState()
        games = [_game(1, 2, "1"), _game(2, 3, "0")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={2: 1600, 3: 1600},
            period_month=_MONTH,
        )
        assert result.path == "ACCUMULATING"
        assert result.games_counted == 2
        assert result.accumulator.games == 2         # nothing discarded: both tournaments fed it
        assert result.accumulator.points == Decimal("1")

    def test_a_carried_over_accumulator_is_never_first_again(self):
        """"Primeiro" also looks at earlier periods: once the accumulator
        already has games behind it, this period's first tournament is not
        eligible for the discard even if it scores zero."""
        state = ModalityState(games=2, first_tournament_played=True, accumulator=Accumulator(
            games=2, sum_opponents=3200, points=Decimal("1"), since="2025-12",
        ))
        games = [_game(1, 5, "0")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={5: 1600},
            period_month=_MONTH,
        )
        assert result.path == "ACCUMULATING"
        assert result.accumulator.games == 3          # the zero result was NOT discarded
        assert result.accumulator.points == Decimal("1")


class TestScoringAgainstRatedOpponentsIsWhatCounts:
    """Decided by FEXERJ on 2026-08-20, reversing their reading of
    2026-08-11: "Ele deve pontuar pelo menos contra um rated em seu primeiro
    torneio válido."

    What opens the accumulation is scoring against **rated** opponents.
    Points taken from unrated ones are invisible to the rating calculation,
    so they cannot start it either — which is the opposite of the earlier
    rule, where beating a field of unrated players made the tournament count
    and dragged the one rated loss in with it."""

    def test_points_against_unrated_opponents_do_not_open_the_accumulation(self):
        # One rated opponent, lost; three unrated opponents, all beaten.
        # Nothing was taken from a rated player, so the tournament is
        # discarded and the loss does not enter.
        games = [_game(1, 2, "0"), _game(1, 90, "1"), _game(1, 91, "1"), _game(1, 92, "1")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=games,
            opponent_ratings={2: 1600},   # 90, 91, 92 are unrated
            period_month=_MONTH,
        )
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.accumulator.games == 0
        assert result.games_counted == 0

    def test_half_a_point_against_a_rated_opponent_is_enough(self):
        games = [_game(1, 2, "0.5"), _game(1, 3, "0")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=games,
            opponent_ratings={2: 1600, 3: 1600},
            period_month=_MONTH,
        )
        assert result.path == "ACCUMULATING"
        assert result.accumulator.games == 2
        assert result.accumulator.points == Decimal("0.5")

    def test_losing_everything_still_discards(self):
        games = [_game(1, 2, "0"), _game(1, 90, "0")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=games,
            opponent_ratings={2: 1600},
            period_month=_MONTH,
        )
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.accumulator.games == 0

    def test_a_discarded_tournaments_games_do_not_count(self):
        """The games of a discarded tournament leave the lifetime count as
        well. The player ends the period looking exactly as they started —
        which is why the discard needs a marker of its own, and cannot be
        read off the game count."""
        games = [_game(1, 2, "0"), _game(1, 90, "0")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=games,
            opponent_ratings={2: 1600},
            period_month=_MONTH,
        )
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.games_counted == 0
        assert result.first_tournament_seen is False

    def test_a_surviving_tournaments_rated_games_do_count(self):
        """The counterpart: something was taken from a rated opponent, so the
        tournament opens the accumulation — and only the rated game enters."""
        games = [_game(1, 2, "1"), _game(1, 90, "0")]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=games,
            opponent_ratings={2: 1600},
            period_month=_MONTH,
        )
        assert result.games_counted == 1


class TestEveryScorelessTournamentIsDiscarded:
    """Decided by FEXERJ on 2026-08-20, reversing the reading of 2026-08-11:
    "Tantos descartes quantos forem os torneios zerados contra rated, ou
    seja, considera somente a partir do 1 não zerado."

    The accumulation does not begin until the player scores. What carries
    across periods is therefore that a tournament was **accepted**, not that
    one was played."""

    def test_a_player_with_an_accepted_tournament_gets_no_discard(self):
        """Once something has been accepted, a later zero counts normally."""
        state = ModalityState(games=0, first_tournament_played=True, accumulator=Accumulator())
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 5, "0")],
            opponent_ratings={5: 1600},
            period_month=_MONTH,
        )
        assert result.path == "ACCUMULATING"
        assert result.accumulator.games == 1        # counted, not discarded
        assert result.accumulator.points == Decimal("0")

    def test_the_marker_is_reported_when_the_first_tournament_is_counted(self):
        """The opportunity is spent by playing, not by being discarded."""
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=[_game(1, 2, "1")],
            opponent_ratings={2: 1600},
            period_month=_MONTH,
        )
        assert result.path == "ACCUMULATING"
        assert result.first_tournament_seen is True

    def test_a_tournament_with_no_rated_opponents_does_not_spend_the_discard(self):
        """A tournament that contributes nothing to the accumulator is
        skipped whole: it is not the "first tournament" for §6.1 purposes,
        and the player keeps the discard for the next one."""
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=[_game(1, 90, "0"), _game(1, 91, "0")],
            opponent_ratings={},
            period_month=_MONTH,
        )
        assert result.games_counted == 0
        assert result.first_tournament_seen is False

    def test_two_scoreless_tournaments_in_one_period_are_both_discarded(self):
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=[_game(1, 2, "0"), _game(2, 3, "0")],
            opponent_ratings={2: 1600, 3: 1600},
            period_month=_MONTH,
        )
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.games_counted == 0
        assert result.accumulator.games == 0

    def test_the_count_starts_at_the_first_tournament_that_is_not_scoreless(self):
        """Two zeroes, then a win: only the third tournament enters."""
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=[_game(1, 2, "0"), _game(2, 3, "0"), _game(3, 4, "1")],
            opponent_ratings={2: 1600, 3: 1600, 4: 1600},
            period_month=_MONTH,
        )
        assert result.games_counted == 1
        assert result.accumulator.games == 1
        assert result.accumulator.points == Decimal("1")
        assert result.accumulator.sum_opponents == 1600

    def test_a_zero_after_an_accepted_tournament_counts(self):
        """Once the accumulation has begun, the protection is over."""
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=[_game(1, 2, "1"), _game(2, 3, "0")],
            opponent_ratings={2: 1600, 3: 1600},
            period_month=_MONTH,
        )
        assert result.games_counted == 2
        assert result.accumulator.games == 2
        assert result.accumulator.points == Decimal("1")

    def test_the_marker_is_the_authority_not_the_game_count(self):
        """A game count above zero does not mean a tournament was accepted.
        The engine cannot produce that state — a discarded tournament adds no
        games — but a file can carry it, and then the marker is what decides.
        Reading the count instead would silently deny the discard."""
        state = ModalityState(games=5, first_tournament_played=False)
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "0")],
            opponent_ratings={2: 1600},
            period_month=_MONTH,
        )
        assert result.path == "FIRST_EVENT_ZEROED"
        assert result.accumulator.games == 0

    def test_it_discards_again_across_periods(self):
        """Two periods back to back, each a single scoreless tournament, with
        the state carried between them by the engine itself. Under the rule
        this replaces, the second one would have counted."""
        first = compute_unrated_period(
            player_id=1, modality="RPD", state=ModalityState(),
            games=[_game(1, 2, "0")],
            opponent_ratings={2: 1600},
            period_month=_MONTH,
        )
        assert first.path == "FIRST_EVENT_ZEROED"

        carried = ModalityState(
            games=first.games_counted,
            first_tournament_played=first.first_tournament_seen,
            accumulator=first.accumulator,
        )
        assert carried.games == 0        # the discarded tournament left no games behind
        second = compute_unrated_period(
            player_id=1, modality="RPD", state=carried,
            games=[_game(2, 3, "0")],
            opponent_ratings={3: 1600},
            period_month=_LATER_MONTH,
        )
        assert second.path == "FIRST_EVENT_ZEROED"
        assert second.accumulator.games == 0
        assert second.games_counted == 0


class TestAccumulationWindow:
    """§6.2 / FIDE 7.1.4: results pool across periods only within a 26-month
    window measured from the period the accumulation began."""

    def test_within_the_window_the_accumulator_is_preserved(self):
        state = ModalityState(games=3, accumulator=Accumulator(
            games=3, sum_opponents=4800, points=Decimal("1.5"), since="2024-01",
        ))
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "0.5")],
            opponent_ratings={2: 1600},
            period_month="2026-02",  # 25 months after 2024-01
        )
        assert result.accumulator.games == 4
        assert result.accumulator.sum_opponents == 4800 + 1600
        assert result.accumulator.points == Decimal("2")
        assert result.accumulator.since == "2024-01"  # start is unchanged

    def test_past_the_window_the_accumulator_is_discarded_and_restarts(self):
        state = ModalityState(games=3, accumulator=Accumulator(
            games=3, sum_opponents=4800, points=Decimal("1.5"), since="2024-01",
        ))
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "0.5")],
            opponent_ratings={2: 1600},
            period_month="2026-04",  # 27 months after 2024-01
        )
        assert result.accumulator.games == 1            # the old 3 games are gone
        assert result.accumulator.sum_opponents == 1600
        assert result.accumulator.points == Decimal("0.5")
        assert result.accumulator.since == "2026-04"     # restarted from this period

    def test_a_window_reset_does_not_hand_back_the_discard(self):
        """A window reset wipes the accumulator, but it does not turn the
        player back into a newcomer: they have played before, and "só o
        primeiro" (FEXERJ, 2026-08-11) spends the discard on the first
        tournament ever, not on the first after a reset. The marker is what
        remembers it — the accumulator cannot, since a reset is
        indistinguishable from never having played once it is zeroed."""
        state = ModalityState(games=3, first_tournament_played=True, accumulator=Accumulator(
            games=3, sum_opponents=4800, points=Decimal("1.5"), since="2024-01",
        ))
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "0")],
            opponent_ratings={2: 1600},
            period_month="2026-04",  # past the window
        )
        assert result.path == "ACCUMULATING"
        assert result.accumulator.games == 1               # counted, not discarded
        assert result.accumulator.points == Decimal("0")
        assert result.accumulator.sum_opponents == 1600
        assert result.accumulator.since == "2026-04"       # restarted from this period


class TestFloorExpelledPlayerAccumulator:
    """A player dropped out of rated status by the §7 floor keeps their
    lifetime `games` count (K and §7 need it), but the §6.1 accumulator
    toward the next initial rating has to start over from
    `accumulator.games`, not from that lifetime count — otherwise the
    "phantom" lifetime games, which never fed the accumulator, drag the
    average down and the player can never climb back out."""

    def test_floor_expelled_player_returns_with_a_rating(self):
        """The reported bug: a player with 60 lifetime games, expelled by the
        floor, wins six games against 1500-rated opponents. Confusing the
        lifetime count for the accumulator used to send this player out with
        no rating at all (66 phantom games diluting the average below 1200);
        with the two counts separated, the six real games alone decide it."""
        state = ModalityState(rating=None, games=60)
        games = [_game(1, i, "1") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1500 for i in range(2, 8)},
            period_month=_MONTH,
        )
        assert result.final_rating == 1861
        assert result.path == "INITIAL_RATING"

    def test_accumulates_in_one_period_and_rates_in_the_next(self):
        """Same floor-expelled player, but the six games needed for a first
        rating are spread across two periods — proving the accumulator (not
        just a single call) carries forward correctly."""
        state = ModalityState(rating=None, games=60)
        period_one = [_game(1, i, "1") for i in range(2, 4)]  # 2 games
        result_one = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=period_one,
            opponent_ratings={i: 1500 for i in range(2, 4)},
            period_month=_MONTH,
        )
        assert result_one.path == "ACCUMULATING"
        assert result_one.accumulator.games == 2

        # The lifetime count keeps growing (as cycle.py's _apply_results does),
        # while the accumulator carries over from result_one.
        state_period_two = ModalityState(
            rating=None,
            games=state.games + result_one.games_counted,
            accumulator=result_one.accumulator,
        )
        period_two = [_game(2, i, "1") for i in range(4, 8)]  # 4 more games -> 6 total
        result_two = compute_unrated_period(
            player_id=1, modality="RPD", state=state_period_two,
            games=period_two,
            opponent_ratings={i: 1500 for i in range(4, 8)},
            period_month=_LATER_MONTH,
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
