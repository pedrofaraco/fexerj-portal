"""Period calculation for a player in one modality.

Every game in the period is calculated against the state at the start of the
period (§4), including the opponent's rating. Nothing here reads updated
state.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from . import rules
from .model import Game, ModalityState, PlayerState
from .tables import pd_for_diff


@dataclass(frozen=True)
class GameResult:
    """A single computed game, with everything the per-game audit trail needs."""

    game: Game
    opponent_rating: int
    capped_diff: int
    pd: Decimal
    delta: Decimal
    k: int


@dataclass
class PeriodResult:
    """The period's closing result for a player in one modality.

    `accumulated_sum_opponents` and `accumulated_points` are only used on the
    unrated path (§6.1): they are the accumulator that carries over to the
    next period while the player hasn't reached five games yet.
    """

    player_id: int
    modality: str
    initial_rating: int | None
    games_counted: int
    sum_delta: Decimal
    variation: Decimal
    rounded_variation: int
    final_rating: int | None
    path: str
    game_results: list[GameResult] = field(default_factory=list)
    accumulated_sum_opponents: int = 0
    accumulated_points: Decimal = Decimal("0")


def compute_rated_period(
    player_id: int,
    modality: str,
    state: ModalityState,
    games: list[Game],
    opponent_ratings: dict[int, int],
    period_year: int,
    birth_year: int | None,
    path: str = "RATED",
) -> PeriodResult:
    """Closes the period for a rated player.

    `opponent_ratings` carries only opponents who were **rated** at the start
    of the period; games against anyone not in the map are dropped (§3).

    K comes out of §5 once for the whole period, and is halved for games in
    an internal tournament (§5.2). The 700 cap is applied per tournament,
    with that tournament's K and game count, per the §5.1 proposal — a point
    still open with FEXERJ.
    """
    if state.rating is None:
        raise ValueError(
            "compute_rated_period requires a player with a rating at the start of the period; "
            "the unrated path is compute_unrated_period (arriving in a later task)"
        )
    initial_rating = state.rating

    period_k = rules.base_k(
        rating=initial_rating,
        games=state.games,
        reached_2200=state.reached_2200,
        birth_year=birth_year,
        period_year=period_year,
    )

    counted = [g for g in games if g.opponent_id in opponent_ratings]
    k_by_tournament = _k_by_tournament(counted, period_k)

    results: list[GameResult] = []
    for game in counted:
        opponent_rating = opponent_ratings[game.opponent_id]
        diff = rules.capped_diff(initial_rating, opponent_rating)
        pd = pd_for_diff(diff)
        results.append(GameResult(
            game=game,
            opponent_rating=opponent_rating,
            capped_diff=diff,
            pd=pd,
            delta=game.score - pd,
            k=k_by_tournament[game.tournament_ord],
        ))

    sum_delta = sum((r.delta for r in results), Decimal("0"))
    variation = sum((r.delta * r.k for r in results), Decimal("0"))
    rounded = rules.round_half_away_from_zero(variation)
    computed_rating = initial_rating + rounded
    final_rating: int | None = None if rules.applies_rating_floor(computed_rating) else computed_rating

    return PeriodResult(
        player_id=player_id,
        modality=modality,
        initial_rating=initial_rating,
        games_counted=len(results),
        sum_delta=sum_delta,
        variation=variation,
        rounded_variation=rounded,
        final_rating=final_rating,
        path=path,
        game_results=results,
    )


def _k_by_tournament(games: list[Game], period_k: int) -> dict[int, int]:
    """Effective K per tournament: halved if internal, then the 700 cap."""
    games_per_tournament: dict[int, int] = {}
    internal: dict[int, bool] = {}
    for game in games:
        games_per_tournament[game.tournament_ord] = games_per_tournament.get(game.tournament_ord, 0) + 1
        internal[game.tournament_ord] = game.is_internal

    effective: dict[int, int] = {}
    for ord_, count in games_per_tournament.items():
        k = rules.halve_for_internal(period_k) if internal[ord_] else period_k
        effective[ord_] = rules.cap_k_by_games(k, count)
    return effective


def transposed_state(player: PlayerState, modality: str) -> ModalityState | None:
    """Entry state for a cross-modality transposition (§1.1), or `None` when it doesn't apply.

    A player who has no rating in `modality` but does have one in STD enters
    that modality with the STD rating, and is treated as rated there —
    including for their opponents, since computing the opponents is part of
    that modality's own period calculation.

    K comes out of the new modality's own game count, which is zero here, so
    it resolves to 40 (§5). Game counts and the `reached_2200` flag are
    independent per modality and never carry over from STD.
    """
    if modality == "STD":
        return None
    if player.modalities[modality].is_rated:
        return None
    std = player.modalities["STD"]
    if not std.is_rated:
        return None
    return ModalityState(rating=std.rating, games=0, reached_2200=False)


def compute_unrated_period(
    player_id: int,
    modality: str,
    state: ModalityState,
    games: list[Game],
    opponent_ratings: dict[int, int],
) -> PeriodResult:
    """Closes the period for a player without a rating in `modality` (§6).

    Games against rated opponents accumulate across periods until the total
    reaches five, at which point the initial rating is computed from the
    full accumulated history. Zeroing the very first event discards that
    event's result instead of counting it (§6.1 / 8.2.1); a zero score in a
    later event is counted normally.
    """
    counted = [g for g in games if g.opponent_id in opponent_ratings]
    points = sum((g.score for g in counted), Decimal("0"))

    is_first_event = state.games == 0
    if is_first_event and counted and points == 0:
        # §6.1 / 8.2.1: the result is discarded — the accumulator does not advance.
        return PeriodResult(
            player_id=player_id,
            modality=modality,
            initial_rating=None,
            games_counted=0,
            sum_delta=Decimal("0"),
            variation=Decimal("0"),
            rounded_variation=0,
            final_rating=None,
            path="FIRST_EVENT_ZEROED",
            accumulated_sum_opponents=state.sum_opponents,
            accumulated_points=state.points,
        )

    total_games = state.games + len(counted)
    total_points = state.points + points
    total_sum_opponents = state.sum_opponents + sum(opponent_ratings[g.opponent_id] for g in counted)

    if total_games < rules.MIN_GAMES_FOR_FIRST_RATING:
        return PeriodResult(
            player_id=player_id,
            modality=modality,
            initial_rating=None,
            games_counted=len(counted),
            sum_delta=Decimal("0"),
            variation=Decimal("0"),
            rounded_variation=0,
            final_rating=None,
            path="ACCUMULATING",
            accumulated_sum_opponents=total_sum_opponents,
            accumulated_points=total_points,
        )

    ru = rules.initial_rating(total_sum_opponents, total_games, total_points)
    return PeriodResult(
        player_id=player_id,
        modality=modality,
        initial_rating=None,
        games_counted=len(counted),
        sum_delta=Decimal("0"),
        variation=Decimal("0"),
        rounded_variation=0,
        final_rating=ru,
        path="INITIAL_RATING" if ru is not None else "BELOW_FLOOR",
        accumulated_sum_opponents=total_sum_opponents,
        accumulated_points=total_points,
    )
