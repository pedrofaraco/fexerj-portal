"""Reading and writing the rating list.

Accepts two input formats: the legacy 12-column one and the new 23-column
one (spec §2.1). Writing is always done in the new format.
"""
import csv
import io
from decimal import Decimal

from .model import COLUMN_SUFFIX, MODALITIES, ModalityState, PlayerState

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
            for prefix in ("Rtg", "Games", "Peak2200", "SumOpp", "Pts")
        )
        for modality in MODALITIES
    ]
)

_IDENTITY_FIELD_COUNT = 8
_FIELDS_PER_MODALITY = 5
FIDE_COLUMN_COUNT = _IDENTITY_FIELD_COUNT + _FIELDS_PER_MODALITY * len(MODALITIES)
LEGACY_COLUMN_COUNT = 12


def _rows(csv_text: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(csv_text.lstrip("﻿")), delimiter=_DELIMITER)
    return [row for row in reader if any(cell.strip() for cell in row)]


def _optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def read_rating_list(csv_text: str) -> dict[int, PlayerState]:
    """Read the rating list in the 23-column format.

    The legacy 12-column format is added in Task 7.
    """
    rows = _rows(csv_text)
    if not rows:
        return {}
    header = _DELIMITER.join(cell.strip() for cell in rows[0])
    if header == FIDE_HEADER:
        return _read_fide_rows(rows[1:])
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
            )
        players[player.id_fexerj] = player
    return players


def write_rating_list(players: dict[int, PlayerState]) -> str:
    """Write the list in the 23-column format."""
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
            ])
        print(_DELIMITER.join(cells), file=buf)
    return buf.getvalue()


def _format_points(points: Decimal) -> str:
    """Integer with no decimal point, fractional with whatever places it has."""
    return str(points.to_integral_value()) if points == points.to_integral_value() else str(points)
