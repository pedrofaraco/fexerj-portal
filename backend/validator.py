"""Input validation for the FEXERJ rating cycle.

Validates the three input file types (players CSV, tournaments CSV, and binary
tournament files) before the rating cycle is executed.  All rules are
collected into a flat list of human-readable error messages; an empty list
means the inputs are valid.
"""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from calculator.fide.model import COLUMN_SUFFIX, MODALITIES
from calculator.fide.ratinglist import (
    FIDE_COLUMN_COUNT,
    FIDE_FIELDS_PER_MODALITY,
    FIDE_HEADER,
    FIDE_IDENTITY_FIELD_COUNT,
    LEGACY_HEADER,
    read_rating_list,
)
from calculator.fide.rules import RATING_FLOOR, birthday_decides_k, parse_birth_year
from calculator.fide.tournaments import parsed_end_date

# BIO_MARKER and PAIRING_MARKER are imported explicitly so the validator can
# produce specific Portuguese error messages before attempting to parse.  The
# parser raises English ValueErrors for the same conditions, but we prefer to
# surface them here with translated, user-friendly wording.
from calculator.tunx_parser import BIO_MARKER, PAIRING_MARKER, parse_bio_section

_PLAYERS_HEADER = LEGACY_HEADER
_TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj"
_FIDE_TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj;TimeControl"
_VALID_TYPES = {"SS", "RR", "ST"}
_TYPE_TO_EXT = {"SS": "TUNX", "RR": "TURX", "ST": "TUMX"}
_VALID_TIME_CONTROLS = frozenset(MODALITIES)

MODE_LEGACY = "legacy"
MODE_FIDE = "fide"
MODE_COMPARE = "compare"
_VALID_MODES = frozenset({MODE_LEGACY, MODE_FIDE, MODE_COMPARE})

# §11.1. Cadastral only: the status governs publication, never calculation.
_PLAYER_STATUSES = frozenset({"0", "1", "2", "3", "4"})
# §5. The three factors the model produces, before the 700 cap of §5.1.
_K_FACTORS = frozenset({"10", "20", "40"})


def validate_inputs(
    players_content: str,
    tournaments_content: str,
    binary_files: dict[str, bytes],
    first: int,
    count: int,
    mode: str = MODE_LEGACY,
) -> list[str]:
    """Validate all inputs for a rating cycle run, per the chosen execution mode.

    Returns a list of human-readable error strings.  An empty list means all
    inputs are valid and the cycle may proceed.

    Binary file validation is skipped when the tournaments CSV has structural
    errors, to avoid confusing cascade messages.
    """
    if mode not in _VALID_MODES:
        return [f"Modo de execu\u00e7\u00e3o '{mode}' desconhecido."]

    # Strip UTF-8 BOM if present (common in Windows-exported CSVs)
    players_content = players_content.lstrip("\ufeff")
    tournaments_content = tournaments_content.lstrip("\ufeff")

    errors: list[str] = []
    players_errors = _validate_players_for_mode(players_content, mode)
    errors.extend(players_errors)
    tournaments_errors = _validate_tournaments_for_mode(tournaments_content, mode)
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


def _validate_players_for_mode(content: str, mode: str) -> list[str]:
    """In legacy mode only the 12-column format is valid; in FIDE mode both are.

    Birthday is checked by *mode*, not by column format: fide and compare
    both read it, because the under-18 K depends on it, even when the list
    still uses the 12-column legacy layout — the compatibility path
    exercised on every run. In legacy mode the current engine never looks at
    it, so it stays optional. Which players must have it is `_validate_birthdays`.
    """
    if mode == MODE_LEGACY:
        return _validate_players_csv(content)
    if mode == MODE_COMPARE:
        # The current engine only reads the 12-column format, so the compare
        # mode cannot accept the new one — the limitation is the mode's, not
        # a malformed file, hence the dedicated message.
        first_line = content.splitlines()[0].strip() if content.splitlines() else ""
        if first_line == FIDE_HEADER:
            return [
                "players.csv: o modo comparar exige a lista no formato de 12 colunas, porque o "
                "modelo atual não lê outro formato. Use o arquivo que a federação usa hoje."
            ]
        return _validate_players_csv(content) + _validate_birthdays(content)
    lines = content.splitlines()
    if not lines or not any(lines):
        return ["players.csv: arquivo vazio"]
    first_line = lines[0].strip()
    if first_line == FIDE_HEADER:
        return _validate_fide_players_csv(content) + _validate_birthdays(content)
    if first_line == _PLAYERS_HEADER:
        return _validate_players_csv(content) + _validate_birthdays(content)
    return [
        "players.csv: cabe\u00e7alho inv\u00e1lido \u2014 aceito o formato de 12 colunas "
        f"ou o de {FIDE_COLUMN_COUNT} colunas do modelo por partida."
    ]


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


def _validate_birthdays(content: str) -> list[str]:
    """Birthday, required of the players whose K factor it decides (§5.2).

    Not of everyone. The date is read by one rule — the under-18 K=40 — and
    `birthday_decides_k` says exactly when that rule can be reached; for
    every other player the K comes out the same with the date and without
    it. Demanding it from all of them would hold the whole file hostage to
    cadastral work that changes no rating: on the federation's list of 2385
    players it is **1** row rather than 298, and the player who would
    silently lose the under-18 K=40 is still the one being protected.

    Runs on the **converted** state rather than on raw cells, through the
    same `read_rating_list` the engine uses, so both column formats are
    covered by one check and the 12-column conversion rules are never
    reimplemented here. A file too malformed to read yields nothing: the
    structural checks report that, and guessing at a state nobody can parse
    would only bury their messages.
    """
    try:
        players = read_rating_list(content)
    except (ValueError, IndexError, InvalidOperation):
        # Every way a cell can defeat the reader: a non-numeric id or count,
        # a short row, a points field that is not a number.
        return []

    rows_by_id = _row_numbers_by_id(content)
    errors: list[str] = []
    for player_id, player in players.items():
        deciding = [
            modality for modality in MODALITIES
            if birthday_decides_k(
                rating=(state := player.modalities[modality]).rating,
                games=state.games,
                reached_2200=state.reached_2200,
                has_fide_rating=state.fide_rating is not None,
            )
        ]
        if not deciding:
            continue
        where = f"players.csv linha {rows_by_id[player_id]}" if player_id in rows_by_id else "players.csv"
        modalities = ", ".join(COLUMN_SUFFIX[m] for m in deciding)
        birthday = player.birthday.strip()
        if not birthday:
            errors.append(
                f"{where}: Birthday é obrigatório para este jogador — o fator K dele depende "
                f"da regra de sub-18 ({modalities})"
            )
        elif parse_birth_year(birthday) is None:
            errors.append(
                f"{where}: Birthday '{birthday}' não foi reconhecida como uma data, e o fator K "
                f"deste jogador depende dela ({modalities})"
            )
    return errors


def _row_numbers_by_id(content: str) -> dict[int, int]:
    """Line number of each Id_No, so a message can point at the row to fix."""
    numbers: dict[int, int] = {}
    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader, None)
    for row_num, row in enumerate(reader, start=2):
        if not row or not row[0].strip().isdigit():
            continue
        numbers.setdefault(int(row[0].strip()), row_num)
    return numbers


def _validate_fide_players_csv(content: str) -> list[str]:
    """Rules for the 42-column format (spec §11.1).

    Two things this deliberately does **not** check, both §11.1:

    - the status is never correlated with anything. It governs publication,
      not calculation, so a player marked deceased with games in the period
      is a valid file: the death happens mid-cycle, with tournaments already
      under way. Refusing it would stop the federation's own list.
    - a `K_` of 10 on a player rated below 2200 is accepted. That is the
      permanent K=10 of §5 doing its job, not a corrupt cell.
    """
    errors: list[str] = []
    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader, None)

    id_no_seen: dict[str, int] = {}
    id_cbx_seen: dict[str, int] = {}

    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != FIDE_COLUMN_COUNT:
            errors.append(
                f"players.csv linha {row_num}: esperadas {FIDE_COLUMN_COUNT} colunas, "
                f"encontradas {len(row)}"
            )
            continue

        id_no = row[0].strip()
        id_cbx = row[1].strip()

        if not id_no:
            errors.append(f"players.csv linha {row_num}: Id_No é obrigatório")
        if not row[3].strip():
            errors.append(f"players.csv linha {row_num}: Name é obrigatório")
        status = row[8].strip()
        if status not in _PLAYER_STATUSES:
            errors.append(
                f"players.csv linha {row_num}: Status deve ser "
                f"{', '.join(sorted(_PLAYER_STATUSES))} — ver §11.1"
            )
        for index, modality in enumerate(MODALITIES):
            base = FIDE_IDENTITY_FIELD_COUNT + index * FIDE_FIELDS_PER_MODALITY
            suffix = COLUMN_SUFFIX[modality]
            rating = row[base].strip()
            if rating:
                if not _is_int(rating):
                    errors.append(f"players.csv linha {row_num}: Rtg_{suffix} deve ser inteiro ou vazio")
                elif int(rating) < RATING_FLOOR:
                    # An empty rating means "unrated" in this format; a published
                    # rating below the floor is impossible by construction, so
                    # accepting one means accepting a corrupted file (§7). Left
                    # unchecked, a bogus "0" reads as a real rated opponent and
                    # silently docks points from everyone who played them.
                    errors.append(
                        f"players.csv linha {row_num}: Rtg_{suffix} deve ser vazio ou um inteiro "
                        f"maior ou igual ao piso de {RATING_FLOOR}"
                    )
            if not _is_int(row[base + 1].strip() or "0"):
                errors.append(f"players.csv linha {row_num}: Games_{suffix} deve ser um inteiro")
            if row[base + 2].strip() not in _K_FACTORS:
                # The K is not decoration: a 10 here is what tells the program
                # the player has reached 2200, permanently (§5). Anything else
                # in the cell is a corrupt file, and blank is the worst of them
                # — it would silently drop a legitimate K=10.
                errors.append(
                    f"players.csv linha {row_num}: K_{suffix} deve ser "
                    f"{', '.join(sorted(_K_FACTORS, key=int))}"
                )
            if row[base + 3].strip() not in {"0", "1"}:
                errors.append(f"players.csv linha {row_num}: FirstTrn_{suffix} deve ser 0 ou 1")
            last_played = row[base + 4].strip()
            if last_played and not _is_year_month(last_played):
                errors.append(
                    f"players.csv linha {row_num}: LastPlayed_{suffix} deve ser vazio ou uma data "
                    "no formato AAAA-MM"
                )
            errors.extend(_validate_fide_rating_pair(row, base, suffix, row_num))
            if not _is_int(row[base + 7].strip() or "0"):
                errors.append(f"players.csv linha {row_num}: AccGames_{suffix} deve ser um inteiro")
            acc_sum_opp = row[base + 8].strip()
            if acc_sum_opp and (not _is_int(acc_sum_opp) or int(acc_sum_opp) < 0):
                errors.append(
                    f"players.csv linha {row_num}: AccSumOpp_{suffix} deve ser um inteiro não negativo"
                )
            acc_points = row[base + 9].strip()
            if acc_points:
                try:
                    Decimal(acc_points)
                except InvalidOperation:
                    errors.append(f"players.csv linha {row_num}: AccPts_{suffix} deve ser um número válido")
            acc_since = row[base + 10].strip()
            if acc_since and not _is_year_month(acc_since):
                errors.append(
                    f"players.csv linha {row_num}: AccSince_{suffix} deve ser vazio ou uma data "
                    "no formato AAAA-MM"
                )

        # Uniqueness — mirrors the legacy validator's checks below.  A shared
        # Id_CBX is not cosmetic: in an IRT tournament, collect_games maps the
        # binary's CBX id to a FEXERJ id from the whole player list, so two
        # players sharing an Id_CBX would silently misattribute one player's
        # games to the other.
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


def _validate_fide_rating_pair(row: list[str], base: int, suffix: str, row_num: int) -> list[str]:
    """The `RtgFide_`/`FideDate_` pair of §6.4.

    The two travel together: the rating is reconferred before first use
    (§6.4, alínea d) and it is the date of that check that says which value
    was adopted. A rating without its date leaves the audit unable to say
    when the number was taken, and a date without a rating is a half-finished
    edit.
    """
    errors: list[str] = []
    rating = row[base + 5].strip()
    date = row[base + 6].strip()

    if rating:
        if not _is_int(rating):
            errors.append(f"players.csv linha {row_num}: RtgFide_{suffix} deve ser inteiro ou vazio")
        elif int(rating) < RATING_FLOOR:
            # §6.4: the FIDE rating enters at face value, and a player entering
            # rated below the floor is a state §7 does not admit.
            errors.append(
                f"players.csv linha {row_num}: RtgFide_{suffix} deve ser vazio ou um inteiro "
                f"maior ou igual ao piso de {RATING_FLOOR}"
            )
        if not date:
            errors.append(
                f"players.csv linha {row_num}: FideDate_{suffix} é obrigatório quando "
                f"RtgFide_{suffix} está preenchido"
            )
    elif date:
        errors.append(
            f"players.csv linha {row_num}: FideDate_{suffix} só se preenche junto com "
            f"RtgFide_{suffix}"
        )

    if date and parsed_end_date(date) is None:
        errors.append(
            f"players.csv linha {row_num}: FideDate_{suffix} '{date}' não foi reconhecida como "
            "uma data (formatos aceitos: AAAA-MM-DD, DD/MM/AAAA ou DD.MM.AAAA)"
        )
    return errors


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_year_month(value: str) -> bool:
    """True for "AAAA-MM" (§6.2's AccSince_ marker), month between 01 and 12."""
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError:
        return False
    return True


def _build_players_index(content: str) -> tuple[set[int], dict[int, int]]:
    """Return FEXERJ ids and CBX→FEXERJ mapping from players.csv data rows.

    Dispatches on the header, like the rest of the validator: Id_No and
    Id_CBX sit in the same first two columns in both the legacy 12-column
    format and the FIDE 42-column format, so only the expected row width
    differs between them.
    """
    lines = content.splitlines()
    first_line = lines[0].strip() if lines else ""
    expected_width = FIDE_COLUMN_COUNT if first_line == FIDE_HEADER else 12

    fexerj_ids: set[int] = set()
    cbx_to_fexerj: dict[int, int] = {}
    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader, None)  # skip header
    for row in reader:
        if not any(cell.strip() for cell in row) or len(row) != expected_width:
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

    ord_seen: dict[str, int] = {}

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

        # Uniqueness: Ord identifies the tournament everywhere downstream — it
        # names the binary file, the current engine's output file, and the
        # per-game engine's game grouping. Two rows sharing it merge into one
        # tournament with no warning anywhere after this point.
        if id_:
            if id_ in ord_seen:
                errors.append(
                    f"tournaments.csv: Ord duplicado: {id_} "
                    f"(linhas {ord_seen[id_]} e {row_num})"
                )
            else:
                ord_seen[id_] = row_num

    return errors


def _validate_tournaments_for_mode(content: str, mode: str) -> list[str]:
    """In legacy mode the 7-column header applies; in the other modes, the 8-column one."""
    if mode == MODE_LEGACY:
        return _validate_tournaments_csv(content)

    lines = content.splitlines()
    if not lines or not any(lines):
        return ["tournaments.csv: arquivo vazio"]
    if lines[0].strip() != _FIDE_TOURNAMENTS_HEADER:
        return [
            "tournaments.csv: cabeçalho inválido — o modelo por partida precisa da coluna "
            f"TimeControl. Esperado '{_FIDE_TOURNAMENTS_HEADER}'"
        ]

    # Reuse the legacy row-level checks (Ord/CrId/Name/Type/IsIrt/IsFexerj) by
    # feeding them the first 7 cells of each row under the legacy header, then
    # add the two columns the per-game model introduces: EndDate and
    # TimeControl.  Cells come from the CSV reader (not a raw string split)
    # and are re-serialized with the CSV writer, so a quoted field containing
    # ';' round-trips correctly instead of corrupting the column count or
    # leaving an unbalanced quote that swallows the following rows.
    legacy_buffer = io.StringIO()
    legacy_writer = csv.writer(legacy_buffer, delimiter=";", lineterminator="\n")
    legacy_writer.writerow(_TOURNAMENTS_HEADER.split(";"))
    legacy_reader = csv.reader(io.StringIO(content), delimiter=";")
    next(legacy_reader)  # skip header
    for row in legacy_reader:
        legacy_writer.writerow(row[:7])
    errors = _validate_tournaments_csv(legacy_buffer.getvalue())

    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader)  # skip header
    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows
        if len(row) != 8:
            errors.append(
                f"tournaments.csv linha {row_num}: esperadas 8 colunas, encontradas {len(row)}"
            )
            continue

        end_date = row[3].strip()
        if not end_date:
            # §5: the under-18 K depends on the period's year, and EndDate is
            # the only source of it in the per-game model.
            errors.append(
                f"tournaments.csv linha {row_num}: EndDate é obrigatório no modelo por partida "
                f"— o fator K de sub-18 depende do ano do período"
            )
        elif parsed_end_date(end_date) is None:
            # Same parser the calculator uses, so validation and calculation
            # cannot disagree about what a readable date is. Left unchecked,
            # an Excel serial (24857) or free text passes here and raises
            # mid-run instead, which reads as a portal failure rather than a
            # file to fix.
            errors.append(
                f"tournaments.csv linha {row_num}: EndDate '{end_date}' não foi reconhecida "
                f"como uma data (formatos aceitos: AAAA-MM-DD, DD/MM/AAAA ou DD.MM.AAAA)"
            )

        time_control = row[7].strip().upper()
        if not time_control:
            errors.append(f"tournaments.csv linha {row_num}: TimeControl é obrigatório")
        elif time_control not in _VALID_TIME_CONTROLS:
            errors.append(
                f"tournaments.csv linha {row_num}: TimeControl '{row[7]}' inválido; "
                f"deve ser STD, RPD ou BLZ"
            )
        elif mode == MODE_COMPARE and time_control != "STD":
            # The current engine has no notion of time control, so comparing
            # it against a non-STD tournament would produce a meaningless
            # difference — the limitation is the mode's, not a malformed file.
            errors.append(
                f"tournaments.csv linha {row_num}: o modo comparar aceita apenas torneios STD. "
                f"O modelo atual não tem conceito de modalidade, então comparar um torneio de "
                f"'{time_control}' produziria uma diferença sem significado."
            )

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
