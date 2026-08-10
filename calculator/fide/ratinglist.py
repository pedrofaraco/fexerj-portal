"""Reading and writing the rating list.

Reads and writes the 26-column format (spec §2.1) and the legacy 12-column
format (spec §2.2).
"""
import csv
import io
from decimal import Decimal

from .model import COLUMN_SUFFIX, MODALITIES, ModalityState, PlayerState
from .rules import K10_THRESHOLD, applies_rating_floor

_DELIMITER = ";"

LEGACY_HEADER = (
    "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;"
    "TotalNumGames;SumOpponRating;TotalPoints"
)

_IDENTITY_COLUMNS = "Id_No;Id_CBX;Title;Name;ClubName;Birthday;Sex;Fed"
FIDE_HEADER = _DELIMITER.join(
    [_IDENTITY_COLUMNS]
    + [
        _DELIMITER.join(
            f"{prefix}_{COLUMN_SUFFIX[modality]}"
            for prefix in ("Rtg", "Games", "Peak2200", "SumOpp", "Pts", "AccGames")
        )
        for modality in MODALITIES
    ]
)

_IDENTITY_FIELD_COUNT = 8
_FIELDS_PER_MODALITY = 6
FIDE_COLUMN_COUNT = _IDENTITY_FIELD_COUNT + _FIELDS_PER_MODALITY * len(MODALITIES)
LEGACY_COLUMN_COUNT = 12

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
    """Read the rating list, in either the 26-column or the legacy 12-column format."""
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
            title=row[2],
            name=row[3],
            club=row[4],
            birthday=row[5],
            sex=row[6],
            federation=row[7],
            modalities={},
        )
        for index, modality in enumerate(MODALITIES):
            base = _IDENTITY_FIELD_COUNT + index * _FIELDS_PER_MODALITY
            player.modalities[modality] = ModalityState(
                rating=_optional_int(row[base]),
                games=int(row[base + 1] or 0),
                reached_2200=row[base + 2].strip() == "1",
                sum_opponents=int(row[base + 3] or 0),
                points=Decimal(row[base + 4].strip() or "0"),
                accumulated_games=int(row[base + 5] or 0),
            )
        players[player.id_fexerj] = player
    return players


def _read_legacy_rows(rows: list[list[str]]) -> dict[int, PlayerState]:
    """Convert the 12-column format into the internal state (spec §2.2).

    Three distinct cases apply to Classical — copying `Rtg_Nat` verbatim
    would be wrong in two of them:

    - `TotalNumGames = 0`: unrated today. The number in `Rtg_Nat` doesn't
      count; the game count decides (see `complete_players_info` in the
      current engine).
    - `Rtg_Nat` below the floor: the current model's floor is 1 point and the
      new one is 1200, so the source list can contain players between 1 and
      1199. §7 is applied here, preserving the game count.
    - everything else enters as rated, with the 2200 peak flag derived from
      the rating itself: the source list is a published rating list (§5).

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
    """
    players: dict[int, PlayerState] = {}
    for row in rows:
        legacy_rating = int(row[4] or 0)
        games = int(row[9] or 0)
        sum_opponents = int(row[10] or 0)
        points = Decimal(row[11].strip() or "0")

        if games == 0 or applies_rating_floor(legacy_rating):
            std = ModalityState(
                rating=None,
                games=games,
                reached_2200=False,
                sum_opponents=sum_opponents,
                points=points,
                accumulated_games=games if games < _LEGACY_TEMP_RATING_GAMES else 0,
            )
        else:
            std = ModalityState(
                rating=legacy_rating,
                games=games,
                reached_2200=legacy_rating >= K10_THRESHOLD,
                sum_opponents=sum_opponents,
                points=points,
                accumulated_games=0,
            )

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


def write_rating_list(players: dict[int, PlayerState]) -> str:
    """Write the list in the 26-column format."""
    buf = io.StringIO()
    print(FIDE_HEADER, file=buf)
    for player in players.values():
        cells = [
            str(player.id_fexerj),
            player.id_cbx,
            player.title,
            player.name,
            player.club,
            player.birthday,
            player.sex,
            player.federation,
        ]
        for modality in MODALITIES:
            state = player.modalities[modality]
            cells.extend([
                "" if state.rating is None else str(state.rating),
                str(state.games),
                "1" if state.reached_2200 else "0",
                str(state.sum_opponents),
                _format_points(state.points),
                str(state.accumulated_games),
            ])
        print(_DELIMITER.join(cells), file=buf)
    return buf.getvalue()


def _format_points(points: Decimal) -> str:
    """Integer with no decimal point, fractional with whatever places it has."""
    return str(points.to_integral_value()) if points == points.to_integral_value() else str(points)
