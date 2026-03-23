"""Input validation for the FEXERJ rating cycle.

Validates the three input file types (players CSV, tournaments CSV, and binary
tournament files) before the rating cycle is executed.  All rules are
collected into a flat list of human-readable error messages; an empty list
means the inputs are valid.
"""
import csv
import io

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
    errors.extend(_validate_players_csv(players_content))
    tournaments_errors = _validate_tournaments_csv(tournaments_content)
    errors.extend(tournaments_errors)
    if not tournaments_errors:
        errors.extend(_validate_binary_files(tournaments_content, binary_files, first, count))
    return errors


# ---------------------------------------------------------------------------
# Players CSV
# ---------------------------------------------------------------------------

def _validate_players_csv(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.splitlines()

    if not lines or not any(lines):
        return ["players.csv: file is empty"]

    if lines[0].strip() != _PLAYERS_HEADER:
        errors.append(
            f"players.csv: invalid header — expected '{_PLAYERS_HEADER}'"
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
                f"players.csv row {row_num}: expected 12 columns, got {len(row)}"
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
                errors.append(f"players.csv row {row_num}: {field} is required")

        # Type checks (only when non-empty to avoid duplicate errors)
        if id_no:
            try:
                int(id_no)
            except ValueError:
                errors.append(f"players.csv row {row_num}: Id_No must be a valid integer")

        if rtg_nat:
            try:
                int(rtg_nat)
            except ValueError:
                errors.append(f"players.csv row {row_num}: Rtg_Nat must be a valid integer")

        if total_games:
            try:
                int(total_games)
            except ValueError:
                errors.append(f"players.csv row {row_num}: TotalNumGames must be a valid integer")

        if sum_oppon:
            try:
                int(sum_oppon)
            except ValueError:
                errors.append(f"players.csv row {row_num}: SumOpponRating must be a valid integer")

        if total_points:
            try:
                float(total_points)
            except ValueError:
                errors.append(f"players.csv row {row_num}: TotalPoints must be a valid number")

        # Uniqueness
        if id_no:
            if id_no in id_no_seen:
                errors.append(
                    f"players.csv: duplicate Id_No: {id_no} "
                    f"(rows {id_no_seen[id_no]} and {row_num})"
                )
            else:
                id_no_seen[id_no] = row_num

        if id_cbx:
            if id_cbx in id_cbx_seen:
                errors.append(
                    f"players.csv: duplicate Id_CBX: {id_cbx} "
                    f"(rows {id_cbx_seen[id_cbx]} and {row_num})"
                )
            else:
                id_cbx_seen[id_cbx] = row_num

    return errors


# ---------------------------------------------------------------------------
# Tournaments CSV
# ---------------------------------------------------------------------------

def _validate_tournaments_csv(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.splitlines()

    if not lines or not any(lines):
        return ["tournaments.csv: file is empty"]

    if lines[0].strip() != _TOURNAMENTS_HEADER:
        errors.append(
            f"tournaments.csv: invalid header — expected '{_TOURNAMENTS_HEADER}'"
        )
        return errors

    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader)  # skip header

    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows

        if len(row) != 7:
            errors.append(
                f"tournaments.csv row {row_num}: expected 7 columns, got {len(row)}"
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
                errors.append(f"tournaments.csv row {row_num}: {field} is required")

        if type_ and type_ not in _VALID_TYPES:
            errors.append(
                f"tournaments.csv row {row_num}: Type '{type_}' is not valid; "
                f"must be SS, RR, or ST"
            )

        if is_irt and is_irt not in {"0", "1"}:
            errors.append(f"tournaments.csv row {row_num}: IsIrt must be 0 or 1")

        if is_fex and is_fex not in {"0", "1"}:
            errors.append(f"tournaments.csv row {row_num}: IsFexerj must be 0 or 1")

    return errors


# ---------------------------------------------------------------------------
# Binary files
# ---------------------------------------------------------------------------

def _validate_binary_files(
    tournaments_content: str,
    binary_files: dict[str, bytes],
    first: int,
    count: int,
) -> list[str]:
    errors: list[str] = []
    reader = csv.reader(io.StringIO(tournaments_content), delimiter=";")
    next(reader)  # skip header

    for row in reader:
        if not any(cell.strip() for cell in row) or len(row) < 5:
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

        if filename not in binary_files:
            errors.append(f"Binary file '{filename}' is missing")
            continue

        errors.extend(_validate_binary_content(filename, binary_files[filename]))

    return errors


def _validate_binary_content(filename: str, data: bytes) -> list[str]:
    errors: list[str] = []

    if BIO_MARKER not in data:
        errors.append(f"{filename}: missing BIO marker — unsupported file format")
        return errors

    if PAIRING_MARKER not in data:
        errors.append(f"{filename}: missing PAIRING marker — unsupported file format")
        return errors

    bio = parse_bio_section(data)

    if not bio:
        errors.append(f"{filename}: no players found in BIO section")
        return errors

    for snr, info in bio.items():
        if not info.get("fexerj_id"):
            errors.append(
                f"{filename}: player '{info['name']}' (starting rank {snr}) "
                f"has no FEXERJ ID"
            )

    return errors
