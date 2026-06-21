"""Input validation for the FEXERJ rating cycle.

Validates the three input file types (players CSV, tournaments CSV, and binary
tournament files) before the rating cycle is executed.  All rules are
collected into a flat list of human-readable error messages; an empty list
means the inputs are valid.
"""
import csv
import io

# BIO_MARKER and PAIRING_MARKER are imported explicitly so the validator can
# produce specific Portuguese error messages before attempting to parse.  The
# parser raises English ValueErrors for the same conditions, but we prefer to
# surface them here with translated, user-friendly wording.
from calculator.tunx_parser import BIO_MARKER, PAIRING_MARKER, parse_bio_section

_PLAYERS_HEADER = (
    "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;"
    "TotalNumGames;SumOpponRating;TotalPoints"
)
_TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj"
_VALID_TYPES = {"SS", "RR", "ST"}
_TYPE_TO_EXT = {"SS": "TUNX", "RR": "TURX", "ST": "TUMX"}


def validate_inputs(
    players_content: str,
    tournaments_content: str,
    binary_files: dict[str, bytes],
    first: int,
    count: int,
) -> list[str]:
    """Validate all inputs for a rating cycle run.

    Returns a list of human-readable error strings.  An empty list means all
    inputs are valid and the cycle may proceed.

    Binary file validation is skipped when the tournaments CSV has structural
    errors, to avoid confusing cascade messages.
    """
    # Strip UTF-8 BOM if present (common in Windows-exported CSVs)
    players_content = players_content.lstrip("\ufeff")
    tournaments_content = tournaments_content.lstrip("\ufeff")

    errors: list[str] = []
    players_errors = _validate_players_csv(players_content)
    errors.extend(players_errors)
    tournaments_errors = _validate_tournaments_csv(tournaments_content)
    errors.extend(tournaments_errors)
    if not tournaments_errors:
        players_index = _build_players_index(players_content) if not players_errors else None
        errors.extend(
            _validate_binary_files(
                tournaments_content,
                binary_files,
                first,
                count,
                players_index=players_index,
            )
        )
    return errors


# ---------------------------------------------------------------------------
# Players CSV
# ---------------------------------------------------------------------------

def _validate_players_csv(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.splitlines()

    if not lines or not any(lines):
        return ["players.csv: arquivo vazio"]

    if lines[0].strip() != _PLAYERS_HEADER:
        errors.append(
            f"players.csv: cabeçalho inválido — esperado '{_PLAYERS_HEADER}'"
        )
        return errors

    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader)  # skip header

    id_no_seen: dict[str, int] = {}
    id_cbx_seen: dict[str, int] = {}

    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows

        if len(row) != 12:
            errors.append(
                f"players.csv linha {row_num}: esperadas 12 colunas, encontradas {len(row)}"
            )
            continue

        id_no        = row[0].strip()
        id_cbx       = row[1].strip()
        name         = row[3].strip()
        rtg_nat      = row[4].strip()
        total_games  = row[9].strip()
        sum_oppon    = row[10].strip()
        total_points = row[11].strip()

        # Required non-empty fields
        for value, field in [
            (id_no,        "Id_No"),
            (name,         "Name"),
            (rtg_nat,      "Rtg_Nat"),
            (total_games,  "TotalNumGames"),
            (sum_oppon,    "SumOpponRating"),
            (total_points, "TotalPoints"),
        ]:
            if not value:
                errors.append(f"players.csv linha {row_num}: {field} é obrigatório")

        # Type checks (only when non-empty to avoid duplicate errors)
        if id_no:
            try:
                int(id_no)
            except ValueError:
                errors.append(f"players.csv linha {row_num}: Id_No deve ser um número inteiro")

        if rtg_nat:
            try:
                int(rtg_nat)
            except ValueError:
                errors.append(f"players.csv linha {row_num}: Rtg_Nat deve ser um número inteiro")

        if total_games:
            try:
                int(total_games)
            except ValueError:
                errors.append(f"players.csv linha {row_num}: TotalNumGames deve ser um número inteiro")

        if sum_oppon:
            try:
                int(sum_oppon)
            except ValueError:
                errors.append(f"players.csv linha {row_num}: SumOpponRating deve ser um número inteiro")

        if total_points:
            try:
                float(total_points)
            except ValueError:
                errors.append(f"players.csv linha {row_num}: TotalPoints deve ser um número válido")

        # Uniqueness
        if id_no:
            if id_no in id_no_seen:
                errors.append(
                    f"players.csv: Id_No duplicado: {id_no} "
                    f"(linhas {id_no_seen[id_no]} e {row_num})"
                )
            else:
                id_no_seen[id_no] = row_num

        if id_cbx:
            if id_cbx in id_cbx_seen:
                errors.append(
                    f"players.csv: Id_CBX duplicado: {id_cbx} "
                    f"(linhas {id_cbx_seen[id_cbx]} e {row_num})"
                )
            else:
                id_cbx_seen[id_cbx] = row_num

    return errors


def _build_players_index(content: str) -> tuple[set[int], dict[int, int]]:
    """Return FEXERJ ids and CBX→FEXERJ mapping from players.csv data rows."""
    fexerj_ids: set[int] = set()
    cbx_to_fexerj: dict[int, int] = {}
    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader, None)  # skip header
    for row in reader:
        if not any(cell.strip() for cell in row) or len(row) != 12:
            continue
        try:
            fexerj_id = int(row[0].strip())
        except ValueError:
            continue
        fexerj_ids.add(fexerj_id)
        cbx_id = row[1].strip()
        if cbx_id:
            try:
                cbx_to_fexerj[int(cbx_id)] = fexerj_id
            except ValueError:
                continue
    return fexerj_ids, cbx_to_fexerj


# ---------------------------------------------------------------------------
# Tournaments CSV
# ---------------------------------------------------------------------------

def _validate_tournaments_csv(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.splitlines()

    if not lines or not any(lines):
        return ["tournaments.csv: arquivo vazio"]

    if lines[0].strip() != _TOURNAMENTS_HEADER:
        errors.append(
            f"tournaments.csv: cabeçalho inválido — esperado '{_TOURNAMENTS_HEADER}'"
        )
        return errors

    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader)  # skip header

    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows

        if len(row) != 7:
            errors.append(
                f"tournaments.csv linha {row_num}: esperadas 7 colunas, encontradas {len(row)}"
            )
            continue

        id_    = row[0].strip()
        cbx_id = row[1].strip()
        name   = row[2].strip()
        # EndDate (col 3) is optional — no check needed
        type_  = row[4].strip()
        is_irt = row[5].strip()
        is_fex = row[6].strip()

        # Required non-empty fields
        for value, field in [
            (id_,    "Ord"),
            (cbx_id, "CrId"),
            (name,   "Name"),
            (type_,  "Type"),
            (is_irt, "IsIrt"),
            (is_fex, "IsFexerj"),
        ]:
            if not value:
                errors.append(f"tournaments.csv linha {row_num}: {field} é obrigatório")

        if type_ and type_ not in _VALID_TYPES:
            errors.append(
                f"tournaments.csv linha {row_num}: Type '{type_}' inválido; "
                f"deve ser SS, RR ou ST"
            )

        if is_irt and is_irt not in {"0", "1"}:
            errors.append(f"tournaments.csv linha {row_num}: IsIrt deve ser 0 ou 1")

        if is_fex and is_fex not in {"0", "1"}:
            errors.append(f"tournaments.csv linha {row_num}: IsFexerj deve ser 0 ou 1")

    return errors


# ---------------------------------------------------------------------------
# Binary files
# ---------------------------------------------------------------------------

def _validate_binary_files(
    tournaments_content: str,
    binary_files: dict[str, bytes],
    first: int,
    count: int,
    players_index: tuple[set[int], dict[int, int]] | None = None,
) -> list[str]:
    errors: list[str] = []
    fexerj_ids: set[int] | None = None
    cbx_to_fexerj: dict[int, int] | None = None
    if players_index is not None:
        fexerj_ids, cbx_to_fexerj = players_index
    reader = csv.reader(io.StringIO(tournaments_content), delimiter=";")
    next(reader)  # skip header

    for row in reader:
        if not any(cell.strip() for cell in row) or len(row) < 7:
            continue

        try:
            trn_id = int(row[0].strip())
        except ValueError:
            continue

        if trn_id < first or trn_id >= first + count:
            continue

        type_ = row[4].strip()
        if type_ not in _TYPE_TO_EXT:
            continue  # already flagged by the tournaments validator

        cbx_id   = row[1].strip()
        ext      = _TYPE_TO_EXT[type_]
        filename = f"{row[0].strip()}-{cbx_id}.{ext}"
        tournament_name = row[2].strip()
        is_irt = row[5].strip() == "1"

        if filename not in binary_files:
            errors.append(f"Arquivo binário '{filename}' não encontrado")
            continue

        errors.extend(
            _validate_binary_content(
                filename,
                binary_files[filename],
                tournament_ord=trn_id,
                tournament_name=tournament_name,
                is_irt=is_irt,
                fexerj_ids=fexerj_ids,
                cbx_to_fexerj=cbx_to_fexerj,
            )
        )

    return errors


def _validate_binary_content(
    filename: str,
    data: bytes,
    *,
    tournament_ord: int | None = None,
    tournament_name: str | None = None,
    is_irt: bool = False,
    fexerj_ids: set[int] | None = None,
    cbx_to_fexerj: dict[int, int] | None = None,
) -> list[str]:
    errors: list[str] = []

    if BIO_MARKER not in data:
        errors.append(f"{filename}: marcador BIO ausente — formato de arquivo não suportado")
        return errors

    if PAIRING_MARKER not in data:
        errors.append(f"{filename}: marcador PAIRING ausente — formato de arquivo não suportado")
        return errors

    bio = parse_bio_section(data)

    if not bio:
        errors.append(f"{filename}: nenhum jogador encontrado na seção BIO")
        return errors

    missing_from_rating_list: list[str] = []
    for snr, info in bio.items():
        raw_id = info.get("fexerj_id", "")
        try:
            missing_id = not (int(raw_id) if raw_id else 0)
        except ValueError:
            missing_id = False
        if missing_id:
            errors.append(
                f"{filename}: jogador '{info['name']}' (posição inicial {snr}) "
                f"não possui ID FEXERJ"
            )
            continue
        if fexerj_ids is None or cbx_to_fexerj is None:
            continue
        try:
            player_id = int(raw_id)
        except ValueError:
            continue
        if is_irt:
            in_rating_list = player_id in cbx_to_fexerj
        else:
            in_rating_list = player_id in fexerj_ids
        if not in_rating_list:
            missing_from_rating_list.append(f"{player_id} ({info['name']})")

    if missing_from_rating_list and tournament_ord is not None:
        name_part = f" ({tournament_name})" if tournament_name else ""
        errors.append(
            f"{filename}: Torneio {tournament_ord}{name_part}: jogador(es) presente(s) "
            f"no arquivo binário mas ausente(s) da lista de rating (players.csv): "
            f"{', '.join(missing_from_rating_list)}."
        )

    return errors
