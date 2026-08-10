"""Reads tournaments.csv and flattens the binaries into games.

The binary parser is the same one used by the current engine
(`calculator.tunx_parser`), used read-only: it already returns
`(snr_a, snr_b, score_for_a)`.
"""
import csv
import io
import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from ..tunx_parser import parse_tunx_from_bytes
from .model import MODALITIES, Game, PlayerState

logger = logging.getLogger(__name__)

_DELIMITER = ";"

TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj;TimeControl"

_TYPE_TO_EXT = {"SS": "TUNX", "RR": "TURX", "ST": "TUMX"}
_YEAR_RE = re.compile(r"(\d{4})")


@dataclass(frozen=True)
class TournamentRow:
    """A row from tournaments.csv, in the new format."""

    ord: int
    cr_id: int
    name: str
    end_date: str
    type_: str
    is_irt: bool
    is_fexerj: bool
    modality: str

    @property
    def is_internal(self) -> bool:
        """§2.1: a tournament is internal when both flags are off."""
        return not self.is_irt and not self.is_fexerj

    @property
    def binary_filename(self) -> str:
        return f"{self.ord}-{self.cr_id}.{_TYPE_TO_EXT[self.type_]}"


def read_tournaments(csv_text: str, first: int, count: int) -> list[TournamentRow]:
    """Reads tournaments.csv and returns the rows in the `first`..`first+count-1` window."""
    reader = csv.reader(io.StringIO(csv_text.lstrip("﻿")), delimiter=_DELIMITER)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return []
    header = _DELIMITER.join(cell.strip() for cell in rows[0])
    if header != TOURNAMENTS_HEADER:
        raise ValueError(
            f"tournaments.csv: cabeçalho não reconhecido. Esperado '{TOURNAMENTS_HEADER}'."
        )

    selected: list[TournamentRow] = []
    for row in rows[1:]:
        ord_ = int(row[0])
        if not (first <= ord_ < first + count):
            continue
        modality = row[7].strip().upper()
        if modality not in MODALITIES:
            raise ValueError(
                f"Torneio {ord_}: TimeControl '{row[7]}' inválido; deve ser STD, RPD ou BLZ."
            )
        type_ = row[4].strip()
        if type_ not in _TYPE_TO_EXT:
            raise ValueError(f"Torneio {ord_}: Type '{type_}' não é um tipo suportado.")
        selected.append(
            TournamentRow(
                ord=ord_,
                cr_id=int(row[1]),
                name=row[2],
                end_date=row[3].strip(),
                type_=type_,
                is_irt=row[5].strip() == "1",
                is_fexerj=row[6].strip() == "1",
                modality=modality,
            )
        )
    return selected


def period_year(tournaments: list[TournamentRow]) -> int:
    """Period year, used by the under-18 rule (§5).

    It is the year of the latest `EndDate` among the tournaments in the
    period. The field is optional in the current model and becomes required
    in the new one, because the under-18 K depends on it.
    """
    years = []
    for tournament in tournaments:
        match = _YEAR_RE.search(tournament.end_date)
        if match is None:
            raise ValueError(
                f"Torneio {tournament.ord}: EndDate '{tournament.end_date}' não traz um ano "
                f"reconhecível. O modelo por partida precisa do ano do período para a regra de sub-18."
            )
        years.append(int(match.group(1)))
    if not years:
        raise ValueError("Nenhum torneio no período: não há como determinar o ano.")
    return max(years)


def collect_games(
    tournaments: list[TournamentRow],
    binary_files: dict[str, bytes],
    players: dict[int, PlayerState],
) -> list[Game]:
    """Flattens the period's binaries into a list of games with FEXERJ ids.

    Each game enters twice, once for each side, with the score inverted —
    the §3 calculation is per player.
    """
    games: list[Game] = []
    for tournament in tournaments:
        filename = tournament.binary_filename
        if filename not in binary_files:
            raise ValueError(
                f"Arquivo binário '{filename}' não encontrado entre os arquivos enviados."
            )
        bio, pairings = parse_tunx_from_bytes(
            binary_files[filename], name=f"{tournament.ord}-{tournament.cr_id}"
        )
        snr_to_id = _resolve_ids(tournament, bio, players)
        for snr_a, snr_b, score_a in pairings:
            if snr_a not in snr_to_id or snr_b not in snr_to_id:
                continue
            id_a, id_b = snr_to_id[snr_a], snr_to_id[snr_b]
            score = Decimal(str(score_a))
            games.append(
                Game(tournament.ord, tournament.modality, tournament.is_internal, id_a, id_b, score)
            )
            games.append(
                Game(
                    tournament.ord,
                    tournament.modality,
                    tournament.is_internal,
                    id_b,
                    id_a,
                    Decimal("1") - score,
                )
            )
    return games


def _resolve_ids(
    tournament: TournamentRow,
    bio: dict,
    players: dict[int, PlayerState],
) -> dict[int, int]:
    """Maps the binary's board number (SNR) to the FEXERJ id.

    In an IRT tournament the binary carries the CBX id, which is resolved
    through the rating list.
    """
    cbx_to_fexerj = {
        int(p.id_cbx): p.id_fexerj for p in players.values() if p.id_cbx.strip().isdigit()
    }
    resolved: dict[int, int] = {}
    missing: list[str] = []
    for snr, info in bio.items():
        raw = info.get("fexerj_id")
        if not raw:
            raise ValueError(
                f"Torneio {tournament.ord}: jogador '{info.get('name', '')}' (tabuleiro {snr}) "
                f"está sem id no arquivo binário."
            )
        binary_id = int(raw)
        player_id = cbx_to_fexerj.get(binary_id) if tournament.is_irt else binary_id
        if player_id is None or player_id not in players:
            missing.append(f"{binary_id} ({info.get('name') or 'sem nome'})")
            continue
        resolved[snr] = player_id

    if missing:
        raise ValueError(
            f"Torneio {tournament.ord} ({tournament.name}): jogador(es) presente(s) no arquivo "
            f"binário mas ausente(s) da lista de rating: {', '.join(missing)}."
        )
    return resolved
