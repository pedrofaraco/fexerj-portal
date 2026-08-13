"""Audit files for the per-game model.

`Audit_Games.csv` exists so a player can redo their own math, game by game,
against table 8.1.2 of the spec. `Audit_Period.csv` shows that the sum
closes. `Audit_Checks.csv` is the odd one out: it describes nothing, it
points — at the handful of rows in a cycle that deserve a human look.
"""
import io

from .model import MODALITIES
from .period import PeriodOutcome
from .rules import K10_THRESHOLD

_DELIMITER = ";"

DECEASED_STATUS = "4"

GAMES_AUDIT_PREAMBLE = "# fide_games_v1"
GAMES_AUDIT_HEADER = (
    "Tournament;TimeControl;PlayerId;PlayerName;OpponentId;"
    "OpponentRating;D;DiffCapped;PD;Score;DeltaR;K"
)

PERIOD_AUDIT_PREAMBLE = "# fide_period_v1"
# The last three describe a rating substitution (§6.4) and are empty on every
# other row. They exist because the substitution happens *before* the period
# is calculated: without them the row would show the new rating as the one the
# player always had, and a jump of several hundred points would appear in the
# published list with nothing anywhere to explain it. This is the file someone
# opens two years later to ask why.
PERIOD_AUDIT_HEADER = (
    "Tournaments;PlayerId;PlayerName;TimeControl;InitialRating;Games;SumDeltaR;"
    "Variation;RoundedVariation;FinalRating;Path;AccumSumOpp;AccumPoints;AccumGames;AccumSince;"
    "PreviousRating;RatingSource;RatingCheckedOn"
)


def write_games_audit(outcome: PeriodOutcome) -> str:
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


def write_period_audit(outcome: PeriodOutcome) -> str:
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
            str(result.accumulator.sum_opponents),
            str(result.accumulator.points),
            str(result.accumulator.games),
            result.accumulator.since,
            "" if result.substitution is None else str(result.substitution.previous_rating),
            "" if result.substitution is None else result.substitution.source,
            "" if result.substitution is None else result.substitution.checked_on,
        ]), file=buf)
    return buf.getvalue()


CHECKS_AUDIT_PREAMBLE = "# fide_checks_v1"
CHECKS_AUDIT_HEADER = "PlayerId;PlayerName;TimeControl;Check;Detail"

# The two the federation asked for, by name.
#
# K10_BELOW_2200 is the price of the K column being the record of the
# permanent K=10 (§5): a `10` typed by mistake freezes that player's factor
# for good, and nothing in the file tells it apart from a legitimate one left
# by a player who reached 2200 and came back down. So it is reported rather
# than refused, for the operator to recognise. Over the real 2026 cycle it
# fires zero times — all 42 players carrying K=10 are at 2200 or above — so a
# line here is a genuine event, not noise to be scrolled past.
#
# CALCULATED_WHILE_DECEASED is the counterpart of the validator deliberately
# accepting that file (§11.1): the death happens mid-cycle, with tournaments
# already under way, so the games are real and are calculated. Whether the
# rating should be published afterwards is the federation's call, and this is
# how they get told there is a call to make.
K10_BELOW_2200 = "K10_BELOW_2200"
CALCULATED_WHILE_DECEASED = "CALCULATED_WHILE_DECEASED"


def write_checks_audit(outcome: PeriodOutcome) -> str:
    """Rows that deserve the operator's eye. Empty but for its header when
    the cycle raised nothing — an empty file is the answer "nothing to look
    at", which a missing file would not be."""
    rows: list[tuple[int, str, str, str]] = []

    for player_id, player in outcome.players.items():
        for modality in MODALITIES:
            state = player.modalities[modality]
            if state.reached_2200 and (state.rating is None or state.rating < K10_THRESHOLD):
                detail = "" if state.rating is None else str(state.rating)
                rows.append((player_id, modality, K10_BELOW_2200, detail))

    for result in outcome.results:
        if outcome.players[result.player_id].status == DECEASED_STATUS:
            rows.append((
                result.player_id, result.modality, CALCULATED_WHILE_DECEASED,
                str(result.games_counted),
            ))

    buf = io.StringIO()
    print(CHECKS_AUDIT_PREAMBLE, file=buf)
    print(CHECKS_AUDIT_HEADER, file=buf)
    for player_id, modality, check, detail in sorted(rows):
        print(_DELIMITER.join([
            str(player_id), outcome.players[player_id].name, modality, check, detail,
        ]), file=buf)
    return buf.getvalue()
