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


@dataclass(frozen=True)
class RatingSubstitution:
    """A local rating replaced by the player's FIDE rating, before the period
    was calculated (§6.4).

    Carried through to `Audit_Period.csv`, which would otherwise show the new
    rating as though it had always been there — a jump of several hundred
    points with nothing in the file to explain it. The date is the operator's
    `FideDate_`, the day they checked the value on FIDE's side.
    """

    previous_rating: int
    source: str
    checked_on: str


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
    # True when this period contained the tournament that spends the §6.1
    # discard. Reported separately from `games_counted` because a discarded
    # tournament leaves the count at zero while still spending the
    # opportunity — which is the whole reason the marker exists.
    first_tournament_seen: bool = False
    # Set when the period opened on a substituted rating (§6.4).
    substitution: "RatingSubstitution | None" = None


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
    substitution: RatingSubstitution | None = None,
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
        # §6.4: while a FIDE rating is on record for the modality, the K comes
        # from the rating band and the new-player K=40 does not apply — not
        # only on the period the player entered on, when they would still have
        # fewer than 30 games here anyway.
        from_fide_rating=state.fide_rating is not None,
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
        substitution=substitution,
    )


def fide_entry_state(player: PlayerState, modality: str) -> ModalityState | None:
    """Entry state for a player arriving on a FIDE rating (§6.4), or `None`.

    The rating enters at face value — the 2000 cap of §6.3 is for an estimate
    made on five games, and a FIDE rating is not an estimate. What still
    limits it is the 400 cap of §3, applied game by game.

    Two conditions, both from §6.4. The operator has recorded a FIDE rating
    for the modality, and the player has **no games at all** there: once they
    have played, the federation's rating is theirs and the recorded FIDE
    rating stops being a door in. Without that second condition a player the
    floor dropped (§7) would be re-entered at their FIDE rating every period,
    and the floor would never take effect on them.

    A rating of 2200 or more switches the permanent K=10 on at entry, exactly
    as if the mark had been reached on a list of the federation's own.

    Runs ahead of `transposed_state`: §1.1 defers to §6.4 when both could
    apply.
    """
    state = player.modalities[modality]
    if state.rating is not None or state.games > 0 or state.fide_rating is None:
        return None
    return ModalityState(
        rating=state.fide_rating,
        games=0,
        reached_2200=state.fide_rating >= rules.K10_THRESHOLD,
        first_tournament_played=state.first_tournament_played,
        last_played=state.last_played,
        fide_rating=state.fide_rating,
        fide_date=state.fide_date,
    )


def fide_substitution_state(
    player: PlayerState, modality: str, period_month: str
) -> tuple[ModalityState, RatingSubstitution] | None:
    """A stale local rating replaced by the player's FIDE rating, or `None`.

    FEXERJ, 2026-08-13. Three conditions, all of them at once, in one
    modality:

    - the player has a **local rating below 1600**. Having none at all is not
      "below 1600" — it is the absence of a rating, the same reading §7 takes
      of a zero in the list being converted;
    - the operator has recorded a **FIDE rating of 2000 or more**;
    - the player has **not played that modality for more than 26 months**.

    What makes the substitution defensible here and nowhere else is that
    there is no local evidence to discard. An active player's two ratings
    differ because they measure two different fields of opponents, and
    replacing one with the other imports a foreign scale for that player
    alone. A player who stopped playing has no current local measurement at
    all: the number is not disagreeing with FIDE, it stopped in time.

    It fires again on a later return, as often as needed — decided by FEXERJ.
    No marker is required for that: the substitution itself lifts the rating
    to 2000 or more and stamps the activity date with the current period, so
    both remaining conditions turn false and only another long absence
    followed by a fall back under 1600 can bring them back.

    The rating enters at face value, and 2200 or more switches the permanent
    K=10 on, exactly as a FIDE rating does when a player first joins the list.
    The game count is untouched: no games were played to justify a change to
    it, and altering it was one of the objections that sank an earlier
    proposal.
    """
    state = player.modalities[modality]
    if (
        state.rating is None
        or state.rating >= rules.SUBSTITUTION_LOCAL_MAX
        or state.fide_rating is None
        or state.fide_rating < rules.SUBSTITUTION_FIDE_MIN
        or not rules.is_inactive(state.last_played, period_month)
    ):
        return None
    substituted = ModalityState(
        rating=state.fide_rating,
        games=state.games,
        reached_2200=state.reached_2200 or state.fide_rating >= rules.K10_THRESHOLD,
        first_tournament_played=state.first_tournament_played,
        last_played=state.last_played,
        fide_rating=state.fide_rating,
        fide_date=state.fide_date,
        accumulator=state.accumulator,
    )
    return substituted, RatingSubstitution(
        previous_rating=state.rating,
        source="FIDE",
        checked_on=state.fide_date,
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
    one was just discarded. "First" also looks past this period, through
    `state.first_tournament_played`.

    The discarded tournament's games are dropped from `games_counted` as
    well, and therefore from the lifetime `ModalityState.games` count §5's K
    factor reads (§6.1, answered by FEXERJ): the count records the games
    that were valid for a rating calculation, and this tournament's went
    into none. That is what forced `first_tournament_played` to become a
    field of its own — a lifetime count of zero used to mean "has not played
    yet", and once the discarded tournament stops incrementing it, the
    player looks like a newcomer again and earns a second discard.

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

    # "Só o primeiro" (FEXERJ, 2026-08-11): the opportunity is spent by the
    # first tournament the player plays, not by the first that survives the
    # discard.
    first_tournament_pending = not state.first_tournament_played
    first_tournament_seen = False
    games_counted = 0
    total_games = accumulator.games
    total_points = accumulator.points
    total_sum_opponents = accumulator.sum_opponents
    discarded_first_tournament = False

    for ord_ in sorted(games_by_tournament):
        tournament_games = games_by_tournament[ord_]
        counted = [g for g in tournament_games if g.opponent_id in opponent_ratings]
        if not counted:
            continue
        tournament_points = sum((g.score for g in counted), Decimal("0"))

        if first_tournament_pending:
            first_tournament_pending = False
            first_tournament_seen = True
            # "Zerar um torneio inteiro" (FEXERJ, 2026-08-11): the whole
            # tournament is what has to be scoreless, not just the games
            # against rated opponents. A newcomer in a field of unrated
            # players may face a single rated opponent and lose to them
            # while winning everything else — that is not a zeroed
            # tournament, and the loss counts.
            if sum((g.score for g in tournament_games), Decimal("0")) == 0:
                # §6.1 / 8.2.1: discarded from the accumulator and from the
                # game count alike — these games were used in no calculation.
                discarded_first_tournament = True
                continue

        games_counted += len(counted)
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
            first_tournament_seen=first_tournament_seen,
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
        first_tournament_seen=first_tournament_seen,
    )
