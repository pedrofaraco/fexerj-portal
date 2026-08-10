"""The per-game model's cycle: CSV and binaries go in, CSV comes out.

Same usage shape as the current engine (`FexerjRatingCycle`), so the backend
can treat both the same way.
"""
import copy
from dataclasses import dataclass, field

from . import audit
from .model import Accumulator, Game, ModalityState, PlayerState
from .period import (
    PeriodResult,
    compute_rated_period,
    compute_unrated_period,
    transposed_state,
)
from .ratinglist import read_rating_list, write_rating_list
from .rules import K10_THRESHOLD, parse_birth_year
from .tournaments import TournamentRow, collect_games, period_month, period_year, read_tournaments

# Paths on which the player ends the period still without a published rating,
# so the §6.1 accumulator must survive into the next period.
_STILL_UNRATED_PATHS = frozenset({"ACCUMULATING", "FIRST_EVENT_ZEROED"})


@dataclass
class PeriodOutcome:
    """The period's raw result, before it becomes CSV."""

    players: dict[int, PlayerState]
    tournaments: list[TournamentRow] = field(default_factory=list)
    results: list[PeriodResult] = field(default_factory=list)


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
            return PeriodOutcome(players=initial_players)

        year = period_year(tournaments)
        month = period_month(tournaments)
        games = collect_games(tournaments, self.binary_files, initial_players)

        # §4: the state at the start of the period is frozen; nothing here changes it.
        entry_states = _entry_states(initial_players, games)
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
                    path=_path_for(initial_players[player_id], modality),
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

        final_players = _apply_results(initial_players, results)
        return PeriodOutcome(players=final_players, tournaments=tournaments, results=results)

    def run_cycle(self) -> dict[str, str]:
        """Returns `{filename: CSV content}` for the period."""
        outcome = self.run_period()
        return {
            "RatingList.csv": write_rating_list(outcome.players),
            "Audit_Games.csv": audit.write_games_audit(outcome),
            "Audit_Period.csv": audit.write_period_audit(outcome),
        }


def _entry_states(
    players: dict[int, PlayerState], games: list[Game]
) -> dict[tuple[int, str], ModalityState]:
    """Entry state of every (player, modality) pair that played in the period."""
    states: dict[tuple[int, str], ModalityState] = {}
    for game in games:
        key = (game.player_id, game.modality)
        if key in states:
            continue
        player = players[game.player_id]
        transposed = transposed_state(player, game.modality)
        states[key] = transposed if transposed is not None else player.modalities[game.modality]
    return states


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


def _path_for(player: PlayerState, modality: str) -> str:
    return "TRANSPOSED" if not player.modalities[modality].is_rated else "RATED"


def _apply_results(
    initial_players: dict[int, PlayerState],
    results: list[PeriodResult],
) -> dict[int, PlayerState]:
    """Applies the results onto a copy of the initial state.

    The initial state itself is never modified: §4 requires the whole period
    to be computed against it.
    """
    final = copy.deepcopy(initial_players)
    for result in results:
        player = final[result.player_id]
        before = player.modalities[result.modality]
        games = before.games + result.games_counted

        if result.final_rating is None and result.path in _STILL_UNRATED_PATHS:
            # Still unrated: the §6.1 accumulator carries over to the next period.
            player.modalities[result.modality] = ModalityState(
                rating=None,
                games=games,
                reached_2200=before.reached_2200,
                accumulator=result.accumulator,
            )
            continue

        # Gained a rating, kept one, or fell below the floor (§7): the unrated
        # accumulator no longer applies and is zeroed. The game count stays.
        player.modalities[result.modality] = ModalityState(
            rating=result.final_rating,
            games=games,
            reached_2200=before.reached_2200 or (
                result.final_rating is not None and result.final_rating >= K10_THRESHOLD
            ),
            accumulator=Accumulator(),
        )
    return final
