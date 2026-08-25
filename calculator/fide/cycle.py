"""The per-game model's cycle: CSV and binaries go in, CSV comes out.

Same usage shape as the current engine (`FexerjRatingCycle`), so the backend
can treat both the same way.
"""
import copy

from . import audit
from .model import Accumulator, Game, ModalityState, PlayerState
from .period import (
    PeriodOutcome,
    PeriodResult,
    RatingSubstitution,
    compute_rated_period,
    compute_unrated_period,
    fide_entry_state,
    fide_substitution_state,
    transposed_state,
)
from .ratinglist import read_rating_list, write_rating_list
from .rules import K10_THRESHOLD, parse_birth_year
from .tournaments import collect_games, period_month, period_year, read_tournaments

# Paths on which the player ends the period still without a published rating,
# so the §6.1 accumulator must survive into the next period.
_STILL_UNRATED_PATHS = frozenset({"ACCUMULATING", "FIRST_EVENT_ZEROED"})


class FideRatingCycle:
    """Runs a single period in the per-game model."""

    def __init__(
        self,
        tournaments_csv: str,
        first_item: int,
        items_to_process: int,
        initial_rating_csv: str,
        binary_files: dict[str, bytes],
    ):
        self.tournaments_csv = tournaments_csv
        self.first_item = first_item
        self.items_to_process = items_to_process
        self.initial_rating_csv = initial_rating_csv
        self.binary_files = binary_files

    def run_period(self) -> PeriodOutcome:
        """Computes the period and returns the structured result."""
        initial_players = read_rating_list(self.initial_rating_csv)
        tournaments = read_tournaments(
            self.tournaments_csv, self.first_item, self.items_to_process
        )
        if not tournaments:
            # Copied like every other path, so what the caller gets back is
            # always its own to mutate.
            return PeriodOutcome(players=copy.deepcopy(initial_players))

        year = period_year(tournaments)
        month = period_month(tournaments)
        games = collect_games(tournaments, self.binary_files, initial_players)

        # §4: the state at the start of the period is frozen; nothing here changes it.
        entry_states, substitutions = _entry_states(initial_players, games, month)
        opponent_ratings = _opponent_ratings_by_modality(entry_states)

        results: list[PeriodResult] = []
        for (player_id, modality), state in sorted(entry_states.items()):
            player_games = [
                g for g in games if g.player_id == player_id and g.modality == modality
            ]
            if not player_games:
                continue
            ratings = opponent_ratings.get(modality, {})
            if state.is_rated:
                results.append(compute_rated_period(
                    player_id=player_id,
                    modality=modality,
                    state=state,
                    games=player_games,
                    opponent_ratings=ratings,
                    period_year=year,
                    birth_year=parse_birth_year(initial_players[player_id].birthday),
                    path=_path_for(
                        initial_players[player_id],
                        modality,
                        state,
                        (player_id, modality) in substitutions,
                    ),
                    substitution=substitutions.get((player_id, modality)),
                ))
            else:
                results.append(compute_unrated_period(
                    player_id=player_id,
                    modality=modality,
                    state=state,
                    games=player_games,
                    opponent_ratings=ratings,
                    period_month=month,
                ))

        final_players = _apply_results(initial_players, results, entry_states, month)
        return PeriodOutcome(players=final_players, tournaments=tournaments, results=results)

    def run_cycle(self) -> dict[str, str]:
        """Returns `{filename: CSV content}` for the period.

        A window that caught no tournament produces no files, exactly as the
        current engine does: the backend turns that into a 422 naming the
        interval. Emitting the three files here would hand an operator who
        mistyped the interval a complete `RatingList.csv`, indistinguishable
        from a published list.
        """
        outcome = self.run_period()
        if outcome.is_empty_window:
            return {}
        return {
            "RatingList.csv": write_rating_list(outcome.players, period_year(outcome.tournaments)),
            "Audit_Games.csv": audit.write_games_audit(outcome),
            "Audit_Period.csv": audit.write_period_audit(outcome),
            "Audit_Checks.csv": audit.write_checks_audit(outcome),
        }


def _entry_states(
    players: dict[int, PlayerState], games: list[Game], period_month: str
) -> tuple[dict[tuple[int, str], ModalityState], dict[tuple[int, str], RatingSubstitution]]:
    """Entry state of every (player, modality) pair that played in the period,
    plus the rating substitutions (§6.4) that produced some of them.

    The three §6.4 paths are mutually exclusive by their own conditions —
    entry needs no rating and no games, substitution needs a rating — so the
    order between them is a matter of reading, not of precedence. §1.1 comes
    last: the cross-modality carry-over defers to a FIDE rating whenever one
    applies.
    """
    states: dict[tuple[int, str], ModalityState] = {}
    substitutions: dict[tuple[int, str], RatingSubstitution] = {}
    for game in games:
        key = (game.player_id, game.modality)
        if key in states:
            continue
        player = players[game.player_id]
        entry = fide_entry_state(player, game.modality)
        if entry is None:
            substituted = fide_substitution_state(player, game.modality, period_month)
            if substituted is not None:
                entry, substitutions[key] = substituted
        if entry is None:
            entry = transposed_state(player, game.modality)
        states[key] = entry if entry is not None else player.modalities[game.modality]
    return states, substitutions


def _opponent_ratings_by_modality(
    entry_states: dict[tuple[int, str], ModalityState],
) -> dict[str, dict[int, int]]:
    """Entry ratings of rated opponents, by modality.

    The transposed player belongs here too: §1.1 treats them as rated, and
    computing their opponents is part of that modality's own period
    calculation.
    """
    by_modality: dict[str, dict[int, int]] = {}
    for (player_id, modality), state in entry_states.items():
        if state.rating is None:
            continue
        by_modality.setdefault(modality, {})[player_id] = state.rating
    return by_modality


def _path_for(
    player: PlayerState, modality: str, entry: ModalityState, substituted: bool
) -> str:
    """How the player came to be rated this period, for the audit trail.

    A player with no rating on file who is nonetheless calculated as rated
    got there one of two ways: on a FIDE rating (§6.4), which is the only
    entry that carries `fide_rating` into the entry state, or on the
    cross-modality carry-over (§1.1). One who *did* have a rating either kept
    it or had it substituted (§6.4).
    """
    if player.modalities[modality].is_rated:
        return "FIDE_SUBSTITUTION" if substituted else "RATED"
    return "FIDE_ENTRY" if entry.fide_rating is not None else "TRANSPOSED"


def _apply_results(
    initial_players: dict[int, PlayerState],
    results: list[PeriodResult],
    entry_states: dict[tuple[int, str], ModalityState],
    period_month: str,
) -> dict[int, PlayerState]:
    """Applies the results onto a copy of the initial state.

    The initial state itself is never modified: §4 requires the whole period
    to be computed against it.

    `reached_2200` only ever goes from false to true: neither the floor nor
    the window takes the permanent K=10 away. `first_tournament_played` is
    different — the floor resets it (§7, decided by FEXERJ on 2026-08-20:
    "quando o piso derruba, ele tem que refazer o rating como acima"), so a
    player who loses their rating rebuilds it with the §6.1 protection intact.
    The FIDE columns are the operator's and are copied through untouched.
    """
    final = copy.deepcopy(initial_players)
    for result in results:
        player = final[result.player_id]
        before = player.modalities[result.modality]
        entry = entry_states[(result.player_id, result.modality)]
        games = before.games + result.games_counted
        # `first_tournament_seen` reports that a tournament was *accepted*
        # this period; a discarded one leaves it false, which is what keeps
        # the next one discardable.
        first_tournament_played = (
            before.first_tournament_played
            or result.first_tournament_seen
            or result.games_counted > 0
        )
        # Any game at all in the period counts as activity, including games
        # against unrated opponents and a discarded tournament's: a result
        # only exists for a player who played.
        last_played = period_month
        # `entry.reached_2200` is the one that is not in `before`: a player
        # entering on a FIDE rating of 2200 or more (§6.4) has the indicator
        # switched on at entry, and would otherwise lose it by ending the
        # period a few points below the mark.
        reached_2200 = (
            before.reached_2200
            or entry.reached_2200
            or (result.final_rating is not None and result.final_rating >= K10_THRESHOLD)
        )

        if result.final_rating is None and result.path in _STILL_UNRATED_PATHS:
            # Still unrated: the §6.1 accumulator carries over to the next period.
            player.modalities[result.modality] = ModalityState(
                rating=None,
                games=games,
                reached_2200=reached_2200,
                first_tournament_played=first_tournament_played,
                last_played=last_played,
                fide_rating=before.fide_rating,
                fide_date=before.fide_date,
                accumulator=result.accumulator,
            )
            continue

        # Gained a rating, kept one, or ended the period without one because
        # of the floor (§7). Either way the unrated accumulator no longer
        # applies and is zeroed, and the game count stays.
        #
        # Ending without a rating means rebuilding from scratch, and FEXERJ
        # decided the §6.1 protection comes back with it: the player is a
        # newcomer again for the purpose of the discard, though not for the
        # game count or the K that follows from it.
        rebuilding_from_scratch = result.final_rating is None
        player.modalities[result.modality] = ModalityState(
            rating=result.final_rating,
            games=games,
            reached_2200=reached_2200,
            first_tournament_played=first_tournament_played and not rebuilding_from_scratch,
            last_played=last_played,
            fide_rating=before.fide_rating,
            fide_date=before.fide_date,
            accumulator=Accumulator(),
        )
    return final
