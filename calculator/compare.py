"""Runs both rating engines over the same input and produces a comparison.

Depends on both engines; neither of them depends on this module.

Mode restrictions, checked by the validator before this module runs: the
players.csv must be in the 12-column format, because the current engine only
reads that layout, and every tournament in the period must be STD, because
the current engine has no concept of time control.
"""
import csv
import io

from .classes import FexerjRatingCycle
from .fide import audit
from .fide.cycle import FideRatingCycle
from .fide.model import PlayerState
from .fide.ratinglist import write_rating_list
from .fide.tournaments import period_year

_DELIMITER = ";"
_LEGACY_TOURNAMENT_COLUMNS = 7

COMPARISON_PREAMBLE = "# fide_comparison_v1"
COMPARISON_HEADER = "PlayerId;PlayerName;RatingCurrent;RatingFide;Difference"


def run_comparison(
    tournaments_csv: str,
    first: int,
    count: int,
    players_csv: str,
    binary_files: dict[str, bytes],
) -> dict[str, str]:
    """Returns the outputs of both engines plus `Comparison.csv`."""
    legacy_output = FexerjRatingCycle(
        tournaments_csv=_strip_modality_column(tournaments_csv),
        first_item=first,
        items_to_process=count,
        initial_rating_csv=players_csv,
        binary_files=binary_files,
    ).run_cycle()

    # A single `run_period` call: calling both `run_cycle` and `run_period`
    # would recompute the whole period twice, opening room for the two
    # outputs to diverge from each other.
    outcome = FideRatingCycle(
        tournaments_csv=tournaments_csv,
        first_item=first,
        items_to_process=count,
        initial_rating_csv=players_csv,
        binary_files=binary_files,
    ).run_period()

    if outcome.is_empty_window:
        # Both engines saw the same empty window; `legacy_output` is empty too.
        # No files means the backend answers 422 naming the interval, instead
        # of a zip that reads as a result.
        return {}

    output = dict(legacy_output)
    output["RatingList.csv"] = write_rating_list(outcome.players, period_year(outcome.tournaments))
    output["Audit_Games.csv"] = audit.write_games_audit(outcome)
    output["Audit_Period.csv"] = audit.write_period_audit(outcome)
    output["Audit_Checks.csv"] = audit.write_checks_audit(outcome)
    output["Comparison.csv"] = _write_comparison(_legacy_final_ratings(legacy_output), outcome.players)
    return output


def _strip_modality_column(tournaments_csv: str) -> str:
    """Drops the TimeControl column: the current engine reads tournaments.csv by position.

    Cells come from the CSV reader and go back out through the CSV writer, so a
    quoted field containing ';' — a tournament name, typically — round-trips
    instead of coming back out unquoted and shifting every column after it.
    Same fix already applied in `backend.validator`.
    """
    reader = csv.reader(io.StringIO(tournaments_csv.lstrip("﻿")), delimiter=_DELIMITER)
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=_DELIMITER, lineterminator="\n")
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        writer.writerow(row[:_LEGACY_TOURNAMENT_COLUMNS])
    return buf.getvalue()


def _legacy_final_ratings(legacy_output: dict[str, str]) -> dict[int, int]:
    """The current engine's final rating per player: the last RatingList_after_<N> of the cycle.

    `run_cycle` processes tournaments.csv rows in file order, not sorted by `Ord`, so the
    highest `N` is not necessarily the last one processed. `legacy_output` is a plain dict
    built by inserting each `RatingList_after_<N>.csv` as its tournament is processed, so
    insertion order mirrors processing order: the last matching key in iteration order is
    the actual final rating list.
    """
    name = None
    for candidate in legacy_output:
        if candidate.startswith("RatingList_after_"):
            name = candidate
    if name is None:
        return {}
    reader = csv.reader(io.StringIO(legacy_output[name]), delimiter=_DELIMITER)
    next(reader, None)  # skip header
    return {
        int(row[0]): int(row[4])
        for row in reader
        if any(cell.strip() for cell in row)
    }


def _write_comparison(legacy_ratings: dict[int, int], fide_players: dict[int, PlayerState]) -> str:
    buf = io.StringIO()
    print(COMPARISON_PREAMBLE, file=buf)
    print(COMPARISON_HEADER, file=buf)
    for player_id, player in fide_players.items():
        legacy = legacy_ratings.get(player_id)
        fide = player.modalities["STD"].rating
        difference = "" if legacy is None or fide is None else str(fide - legacy)
        print(_DELIMITER.join([
            str(player_id),
            player.name,
            "" if legacy is None else str(legacy),
            "" if fide is None else str(fide),
            difference,
        ]), file=buf)
    return buf.getvalue()
