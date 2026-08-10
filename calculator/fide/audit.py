"""Audit files for the per-game model.

`Audit_Games.csv` exists so a player can redo their own math, game by game,
against table 8.1.2 of the spec. `Audit_Period.csv` shows that the sum
closes.
"""
import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cycle import PeriodOutcome

_DELIMITER = ";"

GAMES_AUDIT_PREAMBLE = "# fide_games_v1"
GAMES_AUDIT_HEADER = (
    "Tournament;TimeControl;IsInternal;PlayerId;PlayerName;OpponentId;"
    "OpponentRating;D;DiffCapped;PD;Score;DeltaR;K"
)

PERIOD_AUDIT_PREAMBLE = "# fide_period_v1"
PERIOD_AUDIT_HEADER = (
    "Tournaments;PlayerId;PlayerName;TimeControl;InitialRating;Games;SumDeltaR;"
    "Variation;RoundedVariation;FinalRating;Path;AccumSumOpp;AccumPoints;AccumGames"
)


def write_games_audit(outcome: "PeriodOutcome") -> str:
    """One row per computed game, per side."""
    buf = io.StringIO()
    print(GAMES_AUDIT_PREAMBLE, file=buf)
    print(GAMES_AUDIT_HEADER, file=buf)
    for result in outcome.results:
        name = outcome.players[result.player_id].name
        for entry in result.game_results:
            # Games audit rows only ever come from the rated path, which always
            # sets initial_rating — see PeriodResult.game_results.
            assert result.initial_rating is not None
            raw_diff = result.initial_rating - entry.opponent_rating
            diff_capped = "1" if entry.capped_diff != raw_diff else "0"
            print(_DELIMITER.join([
                str(entry.game.tournament_ord),
                entry.game.modality,
                "1" if entry.game.is_internal else "0",
                str(result.player_id),
                name,
                str(entry.game.opponent_id),
                str(entry.opponent_rating),
                str(entry.capped_diff),
                diff_capped,
                str(entry.pd),
                str(entry.game.score),
                str(entry.delta),
                str(entry.k),
            ]), file=buf)
    return buf.getvalue()


def write_period_audit(outcome: "PeriodOutcome") -> str:
    """One row per player x modality, naming the tournaments of the period."""
    tournaments = ",".join(str(t.ord) for t in outcome.tournaments)
    buf = io.StringIO()
    print(PERIOD_AUDIT_PREAMBLE, file=buf)
    print(PERIOD_AUDIT_HEADER, file=buf)
    for result in outcome.results:
        print(_DELIMITER.join([
            tournaments,
            str(result.player_id),
            outcome.players[result.player_id].name,
            result.modality,
            "" if result.initial_rating is None else str(result.initial_rating),
            str(result.games_counted),
            str(result.sum_delta),
            str(result.variation),
            str(result.rounded_variation),
            "" if result.final_rating is None else str(result.final_rating),
            result.path,
            str(result.accumulated_sum_opponents),
            str(result.accumulated_points),
            str(result.accumulated_games),
        ]), file=buf)
    return buf.getvalue()
