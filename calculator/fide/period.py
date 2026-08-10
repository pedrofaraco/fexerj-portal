"""Period calculation for a player in one modality.

Every game in the period is calculated against the state at the start of the
period (§4), including the opponent's rating. Nothing here reads updated
state.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from . import rules
from .model import Accumulator, Game, ModalityState, PlayerState
from .tables import pd_for_diff
from .tournaments import TournamentRow


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

    `accumulator` is only meaningful on the unrated path (§6.1): it is the
    §6.1 accumulator that carries over to the next period while the player
    hasn't reached five games yet — distinct from `games_counted` below
    (this period's own game count) and from `ModalityState.games` (the
    lifetime count).
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
    accumulator: Accumulator = field(default_factory=Accumulator)


@dataclass
class PeriodOutcome:
    """The period's raw result, before it becomes CSV.

    Lives here, next to `PeriodResult`, because `audit` consumes it and
    `cycle` produces it — putting it in `cycle` would make the audit import
    the engine that calls it.
    """

    players: dict[int, PlayerState]
    tournaments: list[TournamentRow] = field(default_factory=list)
    results: list[PeriodResult] = field(default_factory=list)

    @property
    def is_empty_window(self) -> bool:
        """True when the requested window caught no tournament at all.

        Every computed period has at least one tournament — `run_period`
        returns early otherwise — so an empty list means the window itself
        was empty, not that a period somehow ran without tournaments.
        """
        return not self.tournaments


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

    K comes out of §5 once for the whole period, and the 700 cap (§5.1) is
    applied once against the period's total game count — decided by FEXERJ.
    The same K then applies to every game in the period.
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
    k = rules.cap_k_by_games(period_k, len(counted))

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
            k=k,
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
    period_month: str,
) -> PeriodResult:
    """Closes the period for a player without a rating in `modality` (§6).

    Games against rated opponents accumulate across periods until the total
    reaches five, at which point the initial rating is computed from the
    full accumulated history.

    Zeroing the player's first tournament while unrated discards that
    tournament's result from the accumulator instead of counting it (§6.1 /
    8.2.1) — "event" is the tournament, not the period, so a second
    tournament in the same period is counted normally even when the first
    one was just discarded. "First" also looks past this period:
    `state.accumulator.games == 0` is what marks the opportunity as still
    open, so once any tournament has actually contributed to the
    accumulator — this period or an earlier one — it is gone. The discarded
    tournament's games still feed `games_counted`, and therefore the
    lifetime `ModalityState.games` count §5's K factor reads: only the
    initial-rating calculation drops them, not the player's game count.

    `period_month` ("YYYY-MM") is checked against `state.accumulator.since`
    for the 26-month pooling window (§6.2 / FIDE 7.1.4): once the gap is
    more than 26 months, the old accumulation can no longer be grouped and
    is dropped, restarting from this period's games alone. The same reset
    applies when the accumulator has games but no recorded start at all —
    only possible right after the §2.2 legacy conversion, which has no
    start date to carry over — on the conservative reading that an
    accumulation of unknown age cannot be assumed to still be inside the
    window.

    The accumulator this reads and advances is `state.accumulator`, not
    `state.games`: the latter is the lifetime count, which keeps growing
    after the floor (§7) drops a player back out of rated status, and would
    otherwise make this path see games that never fed the accumulator at
    all.
    """
    accumulator = state.accumulator
    if accumulator.games > 0 and (
        not accumulator.since or rules.accumulation_expired(accumulator.since, period_month)
    ):
        accumulator = Accumulator()

    games_by_tournament: dict[int, list[Game]] = {}
    for game in games:
        games_by_tournament.setdefault(game.tournament_ord, []).append(game)

    first_tournament_pending = accumulator.games == 0
    games_counted = 0
    total_games = accumulator.games
    total_points = accumulator.points
    total_sum_opponents = accumulator.sum_opponents
    discarded_first_tournament = False

    for ord_ in sorted(games_by_tournament):
        counted = [g for g in games_by_tournament[ord_] if g.opponent_id in opponent_ratings]
        if not counted:
            continue
        tournament_points = sum((g.score for g in counted), Decimal("0"))
        games_counted += len(counted)

        if first_tournament_pending:
            first_tournament_pending = False
            if tournament_points == 0:
                # §6.1 / 8.2.1: discarded from the accumulator, but its games
                # were already added to games_counted above.
                discarded_first_tournament = True
                continue

        total_games += len(counted)
        total_points += tournament_points
        total_sum_opponents += sum(opponent_ratings[g.opponent_id] for g in counted)

    since = accumulator.since
    if accumulator.games == 0 and total_games > 0:
        # The accumulation actually starts this period — either from
        # scratch, or right after a window reset above.
        since = period_month

    if total_games < rules.MIN_GAMES_FOR_FIRST_RATING:
        return PeriodResult(
            player_id=player_id,
            modality=modality,
            initial_rating=None,
            games_counted=games_counted,
            sum_delta=Decimal("0"),
            variation=Decimal("0"),
            rounded_variation=0,
            final_rating=None,
            path="FIRST_EVENT_ZEROED" if discarded_first_tournament else "ACCUMULATING",
            accumulator=Accumulator(
                games=total_games,
                sum_opponents=total_sum_opponents,
                points=total_points,
                since=since,
            ),
        )

    ru = rules.initial_rating(total_sum_opponents, total_games, total_points)
    return PeriodResult(
        player_id=player_id,
        modality=modality,
        initial_rating=None,
        games_counted=games_counted,
        sum_delta=Decimal("0"),
        variation=Decimal("0"),
        rounded_variation=0,
        final_rating=ru,
        path="INITIAL_RATING" if ru is not None else "BELOW_FLOOR",
        accumulator=Accumulator(
            games=total_games,
            sum_opponents=total_sum_opponents,
            points=total_points,
            since=since,
        ),
    )
