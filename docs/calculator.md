# Calculator module (`calculator/`) — specification and invariants

This document provides a high-level description of the rating calculation engine under `calculator/`.

It is intentionally **implementation-adjacent**: it explains the data model, inputs/outputs, and the
binary format assumptions the code relies on.

## What the calculator does

The portal runs a **rating cycle** across one or more tournaments:

- Reads a starting rating list (`players.csv`).
- For each selected tournament row in `tournaments.csv`, reads its Swiss Manager binary file
  (`.TUNX`, `.TURX`, `.TUMX`) and produces:
  - `RatingList_after_<Ord>.csv` (updated ratings after that tournament)
  - `Audit_of_Tournament_<Ord>.csv` (per-player audit row describing the calculation inputs/outputs)

The entry point is `calculator.FexerjRatingCycle` (exported from `calculator/__init__.py`).

## Entry point and I/O contract

### `FexerjRatingCycle(tournaments_csv, first_item, items_to_process, initial_rating_csv, binary_files)`

- **Inputs**
  - `tournaments_csv` (string): full contents of `tournaments.csv`.
  - `first_item` / `items_to_process` (ints): the tournament interval \([first_item, first_item + items_to_process)\).
  - `initial_rating_csv` (string): full contents of `players.csv`.
  - `binary_files` (dict): mapping `{filename: bytes}` for tournament binaries.

- **Output**
  - `run_cycle()` returns `dict[str, str]`: mapping `{output_filename: csv_string}`.

### Output filenames

For each processed tournament with ordinal `Ord`, the calculator returns:

- `RatingList_after_<Ord>.csv`
- `Audit_of_Tournament_<Ord>.csv`

## CSV expectations (calculator-side)

The calculator assumes semicolon-delimited CSV (see `_CSV_DELIMITER`).

### Rating list (`players.csv`)

The calculator parses rows into `FexerjPlayer` objects. It expects:

- `Id_No` (FEXERJ id) as an integer.
- `Id_CBX` (CBX id) may be empty; when present it is mapped to FEXERJ id for IRT tournaments.
- `Rtg_Nat`, `TotalNumGames` as integers.
- Points fields are parsed and carried through.

The portal’s `backend/validator.py` enforces header and type constraints before calling the calculator.

### Tournaments (`tournaments.csv`)

For each row in the selected range:

- `Ord` and `CrId` are used to locate the binary file.
- `Type` drives the expected extension:
  - `SS` → `.TUNX`
  - `RR` → `.TURX`
  - `ST` → `.TUMX`
- `IsIrt` and `IsFexerj` influence how IDs and rules are applied.

## Tournament selection and binary filename mapping

The binary filename is derived as:

`<Ord>-<CrId>.<Ext>`

Where `Ext` depends on `Type` (`SS/RR/ST` → `TUNX/TURX/TUMX`).

If the expected file is missing from `binary_files`, the calculator raises `ValueError`
("Binary file … not found…"). The backend converts this into HTTP 422 with a string detail.

## Binary format assumptions (Swiss Manager)

The parser lives in `calculator/tunx_parser.py` and relies on fixed markers and record layout.

### Markers

The binary is assumed to contain two required markers:

- **BIO marker**: `a5ff8944` (hex)
- **PAIRING marker**: `b3ff8944` (hex)

`backend/validator.py` checks for marker presence early to emit Portuguese errors before the parser
raises English `ValueError`s.

### BIO section parsing (players)

The BIO section is parsed into:

`{snr: {"name": <string>, "fexerj_id": <string>}}`

Invariants:

- `snr` is 1-based and increments per parsed record.
- Each record is expected to contain UTF‑16LE fields for first/last name, plus an ID field.
- Some records may contain a literal `'*'` field before the abbreviation; the parser skips it.

The calculator then resolves each player’s FEXERJ ID:

- Missing/empty IDs raise `ValueError` via `TournamentPlayer.resolve_id`.

The portal’s validator also enforces that **every BIO record has a FEXERJ ID**, producing a friendly
Portuguese error list.

### Pairing section parsing (games)

The pairing section is parsed into a list of games:

`[(snr_a, snr_b, score_for_a), ...]`

Key assumptions:

- Pairing records use a fixed stride (`PAIRING_STRIDE = 21`).
- Known result codes are mapped into scores:
  - win → 1.0
  - draw → 0.5
  - loss → 0.0
- Records with byes or empty slots are skipped.

### Parser validation and warnings

`tunx_parser.validate()` raises on critical issues (missing markers / no players parsed) and emits
warnings for suspicious layout changes, including:

- pairing section size not a multiple of stride
- >5% unknown result codes
- game records referencing SNRs not present in BIO

Operationally, those warnings indicate the Swiss Manager export format may have changed.

## Rating calculation invariants (high-level)

The core loop is:

1. Load starting rating list.
2. Load tournament players + games from binary.
3. Classify players (unrated / temporary / established) based on total games.
4. Compute expected score vs achieved score from opponent ratings.
5. Apply a calculation rule:
   - TEMPORARY
   - RATING_PERFORMANCE
   - DOUBLE_K
   - NORMAL
6. Update rating list and emit audit rows.

The audit output is intended to make the calculation explainable and debuggable without stepping
through code.

### When each calculation rule applies

These rules are mutually exclusive; exactly one is recorded in the audit column `Calc_Rule`.

- **TEMPORARY**: applies when the player is **unrated** (`TotalNumGames == 0`) or **temporary**
  (`0 < TotalNumGames < 15`), i.e. fewer than `_MAX_NUM_GAMES_TEMP_RATING` total games.
- **RATING_PERFORMANCE**: applies only for **established players** (`TotalNumGames >= 15`) in
  **FEXERJ tournaments** (`IsFexerj == 1`) when an over-performance threshold is met (see below).
  If the player has **fewer than 5** valid games in the tournament, the rule is **not eligible** and
  evaluation continues (typically ending in **NORMAL** or **DOUBLE_K**).
- **DOUBLE_K**: applies for **established players** when a different over-performance threshold is met
  (see below). If the player has **fewer than 4** valid games in the tournament, the rule is **not
  eligible** and evaluation continues (typically ending in **NORMAL**). When it fires, the K-based
  gain is doubled.
- **NORMAL**: the default for established players when no special rule fires; rating gain uses the
  standard K-factor.

#### Rule precedence (what happens when multiple could apply)

`get_calculation_rule()` evaluates in this order:

1. **TEMPORARY** if the player is unrated/temporary (this ends evaluation — it cannot coexist with
   the established-player rules).
2. Else **RATING_PERFORMANCE** if eligible (FEXERJ tournament + RP thresholds pass).
3. Else **DOUBLE_K** if eligible (DK thresholds pass).
4. Else **NORMAL**.

So for an established player in a FEXERJ tournament, **RATING_PERFORMANCE wins over DOUBLE_K** when
both thresholds would pass.

#### Over-performance signal (what “threshold” means)

After filtering invalid opponents and counting valid games, the engine computes:

- `this_expected_points`: expected score from the logistic curve vs average opponent rating.
- `this_points_above_expected`: **points scored minus expected points** in the current tournament
  (`this_pts_against_oppon - this_expected_points`).

The RP/DK “thresholds” are explicit comparisons against `this_points_above_expected` by valid-game
count (`this_games`):

- **RATING_PERFORMANCE** (only when `this_games` is 5–7):
  - 5 games: `this_points_above_expected >= 1.84`
  - 6 games: `this_points_above_expected >= 2.02`
  - 7 games: `this_points_above_expected >= 2.16`
  - If `this_games > 7`, the implementation treats RP as **not eligible** (falls through to DK/NORMAL).
- **DOUBLE_K** (only when `this_games` is 4–7):
  - 4 games: `this_points_above_expected >= 1.65`
  - 5 games: `this_points_above_expected >= 1.43`
  - 6 games: `this_points_above_expected >= 1.56`
  - 7 games: `this_points_above_expected >= 1.69`
  - If `this_games > 7`, the implementation treats DK as **not eligible** (falls through to NORMAL).

### K-factor tiers

The K-factor table applies to **NORMAL** and **DOUBLE_K** rating updates (established players using
the K-based gain path). It does **not** drive **TEMPORARY** or **RATING_PERFORMANCE** updates, even
though the audit file still records a `K` column for diagnostics.

The K factor is chosen from the player’s **pre-tournament** total games (`TotalNumGames`) using
`_K_STARTING_NUM_GAMES`:

- **K = 30** when `TotalNumGames < 15` (in practice this tier is for **temporary/unrated** players:
  they take the **TEMPORARY** path, so this K is **not** used to compute their new rating — it may
  still appear in audit output as a diagnostic column.)
- **K = 25** when `15 <= TotalNumGames < 40`
- **K = 15** when `40 <= TotalNumGames < 80`
- **K = 10** when `TotalNumGames >= 80`

## Failure modes you should expect

- **Missing binary file for a tournament** → `ValueError` → backend returns 422 string detail.
- **Unexpected tournament type** → `ValueError` ("not a valid TournamentType") → backend 422 string detail.
- **Missing FEXERJ ID in BIO** → `ValueError` or validator error list.
- **Binary layout drift** → warnings from `tunx_parser.validate()`; treat as a signal to review parsing.

## Key files

- `calculator/classes.py` — rating cycle engine and audit output
- `calculator/tunx_parser.py` — binary parsing and format validation
- `backend/validator.py` — input validation and user-facing error mapping

