"""Reading and writing the rating list.

Reads and writes the 43-column format (spec §11.1) and the legacy 12-column
format (spec §2.2).
"""
import csv
import io
from decimal import Decimal

from .model import COLUMN_SUFFIX, MODALITIES, Accumulator, ModalityState, PlayerState
from .rules import (
    K10_THRESHOLD,
    MIN_GAMES_FOR_FIRST_RATING,
    RATING_FLOOR,
    applies_rating_floor,
    base_k,
    parse_birth_year,
)

_DELIMITER = ";"

LEGACY_HEADER = (
    "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;"
    "TotalNumGames;SumOpponRating;TotalPoints"
)

# `PrevId` and `Status` are cadastral (§11.1): the operator fills them and no
# calculation reads either.
_IDENTITY_COLUMNS = "Id_No;Id_CBX;PrevId;Title;Name;ClubName;Birthday;Sex;Fed;Status"
# Per modality, in three blocks:
#   Rtg, Games, K, FirstTrn, LastPlayed — what the player *is* in that
#     modality. None of them zero out together, and the program writes all
#     five. `K` doubles as the permanent "reached 2200" indicator (§5).
#   RtgFide, FideDate — the operator's, read by §6.4 and never written here.
#   Acc* — the §6.1 accumulator, adjacent and sharing a prefix because the
#     four zero out together the moment the player gains a rating.
_MODALITY_COLUMN_PREFIXES = (
    "Rtg", "Games", "K", "FirstTrn", "LastPlayed", "RtgFide", "FideDate",
    "AccGames", "AccSumOpp", "AccPts", "AccSince",
)
FIDE_HEADER = _DELIMITER.join(
    [_IDENTITY_COLUMNS]
    + [
        _DELIMITER.join(
            f"{prefix}_{COLUMN_SUFFIX[modality]}" for prefix in _MODALITY_COLUMN_PREFIXES
        )
        for modality in MODALITIES
    ]
)

# Public because the validator walks the same row layout, and hardcoding
# the two numbers there is how the two drift apart.
FIDE_IDENTITY_FIELD_COUNT = 10
FIDE_FIELDS_PER_MODALITY = len(_MODALITY_COLUMN_PREFIXES)
FIDE_COLUMN_COUNT = FIDE_IDENTITY_FIELD_COUNT + FIDE_FIELDS_PER_MODALITY * len(MODALITIES)
LEGACY_COLUMN_COUNT = 12

# §5, decided by FEXERJ on 2026-08-11: the K factor is written to the list and
# is itself the record that the player has reached 2200 — there is no separate
# flag. `base_k` returns 10 if and only if `reached_2200` is true, which is
# what makes the two interchangeable, and it only holds for the K *before* the
# 700 cap: `cap_k_by_games(20, 64..70)` is also 10, so writing the capped K
# would freeze a player at K=10 for good after one very long period. The
# effective K of each game is in `Audit_Games.csv`.
K10_MARKER = "10"

# calculator/classes.py (`_MAX_NUM_GAMES_TEMP_RATING`) zeroes SumOpponRating and
# TotalPoints once a legacy player's TotalNumGames reaches this many, and never
# accumulates into them again afterwards. The §2.2 conversion below relies on
# that to know how many of a legacy player's lifetime games are actually behind
# the SumOpponRating/TotalPoints figures still in the file.
_LEGACY_TEMP_RATING_GAMES = 15


def _rows(csv_text: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(csv_text.lstrip("﻿")), delimiter=_DELIMITER)
    return [row for row in reader if any(cell.strip() for cell in row)]


def _optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def read_rating_list(csv_text: str) -> dict[int, PlayerState]:
    """Read the rating list, in either the 43-column or the legacy 12-column format."""
    rows = _rows(csv_text)
    if not rows:
        return {}
    header = _DELIMITER.join(cell.strip() for cell in rows[0])
    if header == FIDE_HEADER:
        return _read_fide_rows(rows[1:])
    if header == LEGACY_HEADER:
        return _read_legacy_rows(rows[1:])
    raise ValueError(
        "players.csv: cabeçalho não reconhecido. Esperado o formato de "
        f"{LEGACY_COLUMN_COUNT} colunas ou o de {FIDE_COLUMN_COUNT} colunas."
    )


def _read_fide_rows(rows: list[list[str]]) -> dict[int, PlayerState]:
    players: dict[int, PlayerState] = {}
    for row in rows:
        player = PlayerState(
            id_fexerj=int(row[0]),
            id_cbx=row[1].strip(),
            prev_id=row[2].strip(),
            title=row[3],
            name=row[4],
            club=row[5],
            birthday=row[6],
            sex=row[7],
            federation=row[8],
            status=row[9].strip(),
            modalities={},
        )
        for index, modality in enumerate(MODALITIES):
            base = FIDE_IDENTITY_FIELD_COUNT + index * FIDE_FIELDS_PER_MODALITY
            player.modalities[modality] = ModalityState(
                rating=_optional_int(row[base]),
                games=int(row[base + 1] or 0),
                # Compared as text, not parsed: a blank or a corrupt K reads as
                # "has not reached 2200" rather than raising. It is the
                # validator that refuses anything outside 10/20/40.
                reached_2200=row[base + 2].strip() == K10_MARKER,
                first_tournament_played=row[base + 3].strip() == "1",
                last_played=row[base + 4].strip(),
                fide_rating=_optional_int(row[base + 5]),
                fide_date=row[base + 6].strip(),
                accumulator=Accumulator(
                    games=int(row[base + 7] or 0),
                    sum_opponents=int(row[base + 8] or 0),
                    points=Decimal(row[base + 9].strip() or "0"),
                    since=row[base + 10].strip(),
                ),
            )
        players[player.id_fexerj] = player
    return players


def _read_legacy_rows(rows: list[list[str]]) -> dict[int, PlayerState]:
    """Convert the 12-column format into the internal state (spec §2.2).

    Four distinct cases apply to Classical — copying `Rtg_Nat` verbatim
    would be wrong in three of them:

    - `TotalNumGames = 0`: unrated today. The number in `Rtg_Nat` doesn't
      count; the game count decides (see `complete_players_info` in the
      current engine).
    - **fewer than five games** (decision C, 2026-08-11): the rating is
      dropped and the player enters unrated, because the new model would
      never produce a rating on fewer than five games (§6.1) — the converted
      list would otherwise open with numbers the model itself refuses to
      make. The game count survives "para registro", and the games already
      played carry over as progress toward the five now required.
    - `Rtg_Nat` **below the floor with five games or more** (decision D,
      2026-08-11): raised to the floor, entering rated. Entering unrated
      would delete the player from the list in silence, since the
      initial-rating calculation rarely returns anyone above 1200; at the
      floor, the exit — if it comes — happens through §7, with an audit
      line. `Rtg_Nat = 0` is not "below the floor": it means the source list
      carries no rating at all, and those players stay unrated.
    - everything else enters as rated, with the 2200 peak flag derived from
      the rating itself: the source list is a published rating list (§5).

    C is checked before D: a player below the floor *and* under five games
    leaves unrated, since neither rule leaves them holding a rating.

    Rapid and Blitz start empty, which triggers the §1.1 carry-over on each
    modality's first tournament.

    A fourth quantity — the §6.1 accumulated-games count — has to be derived
    rather than copied, because the legacy format has no column for it. For
    the two unrated-entering cases, `SumOpponRating`/`TotalPoints` are only
    real accumulator values while `TotalNumGames` is still below
    `_LEGACY_TEMP_RATING_GAMES`; from that point on the legacy engine has
    already zeroed both (see the module-level comment on
    `_LEGACY_TEMP_RATING_GAMES`), so the accumulated count must be zero too —
    never `games`, which would overstate how many games are actually behind
    the (by then zeroed) sums. A rated player carries no unrated accumulator
    at all, so its accumulated count is always zero.

    The accumulator's `since` (§6.2, the 26-month pooling window) has no
    source in the legacy format either, and unlike the games count above
    there is no derivation that recovers it — the legacy file simply never
    recorded when a player's accumulation began. Decided conservatively:
    leave it empty rather than guess a start. `compute_unrated_period`
    already treats an accumulator that has games but an empty `since` as
    expired (only otherwise reachable right after this exact conversion),
    so an imported player who was mid-accumulation loses that partial
    progress on the first period the new engine processes for them, and
    starts a fresh, dateable accumulation from that period's games — instead
    of silently carrying forward pooled results whose age against the
    26-month window can no longer be verified.
    """
    players: dict[int, PlayerState] = {}
    for row in rows:
        legacy_rating = int(row[4] or 0)
        games = int(row[9] or 0)
        sum_opponents = int(row[10] or 0)
        points = Decimal(row[11].strip() or "0")

        raised_to_floor = (
            games >= MIN_GAMES_FOR_FIRST_RATING
            and legacy_rating > 0
            and applies_rating_floor(legacy_rating)
        )
        enters_unrated = not raised_to_floor and (
            games == 0
            or games < MIN_GAMES_FOR_FIRST_RATING
            or applies_rating_floor(legacy_rating)
        )

        # The §6.1 discard is spent by the first tournament the player plays,
        # and the legacy list records no more than that they have played:
        # a lifetime count above zero is exactly the test the engine used to
        # make before the marker became a field of its own, so converting it
        # this way leaves the imported player's discard where it already was.
        # Getting this wrong hands every converted player a fresh discard.
        first_tournament_played = games > 0

        if enters_unrated:
            std = ModalityState(
                rating=None,
                games=games,
                reached_2200=False,
                first_tournament_played=first_tournament_played,
                accumulator=Accumulator(
                    games=games if games < _LEGACY_TEMP_RATING_GAMES else 0,
                    sum_opponents=sum_opponents,
                    points=points,
                ),
            )
        elif raised_to_floor:
            std = ModalityState(
                rating=RATING_FLOOR,
                games=games,
                reached_2200=False,
                first_tournament_played=first_tournament_played,
                accumulator=Accumulator(sum_opponents=sum_opponents, points=points),
            )
        else:
            std = ModalityState(
                rating=legacy_rating,
                games=games,
                reached_2200=legacy_rating >= K10_THRESHOLD,
                first_tournament_played=first_tournament_played,
                accumulator=Accumulator(sum_opponents=sum_opponents, points=points),
            )

        # `status` takes its default of "1" (active) and `prev_id` stays
        # empty: the legacy list carries neither, and both are the operator's
        # to fill in after the conversion (§11.1). `last_played` has no source
        # either — the legacy format never recorded when a player last played.
        player = PlayerState(
            id_fexerj=int(row[0]),
            id_cbx=row[1].strip(),
            title=row[2],
            name=row[3],
            club=row[5],
            birthday=row[6],
            sex=row[7],
            federation=row[8],
            modalities={"STD": std, "RPD": ModalityState(), "BLZ": ModalityState()},
        )
        players[player.id_fexerj] = player
    return players


def write_rating_list(players: dict[int, PlayerState], period_year: int) -> str:
    """Write the list in the 43-column format (§11.1).

    `period_year` dates the under-18 branch of §5, which is why the K factor
    cannot be written without it.

    The K written is the one the state *ends* the period on, not the one the
    period was calculated with. That is forced by K being the record of the
    permanent K=10 (§5): a player who enters at 2150 and leaves at 2210 has
    to leave this file holding a 10, or the permanence is lost in the very
    cycle that earned it. The K each game was actually calculated with — the
    one the 700 cap may have lowered — is in `Audit_Games.csv`.
    """
    buf = io.StringIO()
    print(FIDE_HEADER, file=buf)
    for player in players.values():
        birth_year = parse_birth_year(player.birthday)
        cells = [
            str(player.id_fexerj),
            player.id_cbx,
            player.prev_id,
            player.title,
            player.name,
            player.club,
            player.birthday,
            player.sex,
            player.federation,
            player.status,
        ]
        for modality in MODALITIES:
            state = player.modalities[modality]
            cells.extend([
                "" if state.rating is None else str(state.rating),
                str(state.games),
                str(base_k(
                    rating=state.rating,
                    games=state.games,
                    reached_2200=state.reached_2200,
                    birth_year=birth_year,
                    period_year=period_year,
                    from_fide_rating=state.fide_rating is not None,
                )),
                "1" if state.first_tournament_played else "0",
                state.last_played,
                "" if state.fide_rating is None else str(state.fide_rating),
                state.fide_date,
                str(state.accumulator.games),
                str(state.accumulator.sum_opponents),
                _format_points(state.accumulator.points),
                state.accumulator.since,
            ])
        print(_DELIMITER.join(cells), file=buf)
    return buf.getvalue()


def _format_points(points: Decimal) -> str:
    """Integer with no decimal point, fractional with whatever places it has."""
    return str(points.to_integral_value()) if points == points.to_integral_value() else str(points)
