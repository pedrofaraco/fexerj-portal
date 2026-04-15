# Calculator (`calculator/`) — how it works

This note explains what the **rating calculator** does: which files it reads, what it writes, which
parts of the Swiss Manager binary file it trusts, and how it picks a rating rule.

It stays close to the real code on purpose (file names, column names, and rule order match the
implementation), but the goal is that you can understand the **behavior** without reading every line
of Python first.

## What the calculator does

The portal runs a **rating cycle** over one or more tournaments:

- Starts from the rating list (`players.csv`).
- For each tournament you selected in `tournaments.csv`, reads that tournament’s Swiss Manager
  binary file (`.TUNX`, `.TURX`, or `.TUMX`).
- Writes two CSV files per tournament:
  - `RatingList_after_<Ord>.csv` — rating list **after** that tournament
  - `Audit_of_Tournament_<Ord>.csv` — one row per player with the numbers that led to the new rating

The Python entry point is `calculator.FexerjRatingCycle` (see `calculator/__init__.py`).

## What goes in and what comes out

### Starting the cycle

`FexerjRatingCycle(...)` is constructed with:

- **`tournaments_csv`**: full text of `tournaments.csv`.
- **`first_item`** and **`items_to_process`**: which tournaments to run. The code keeps rows whose
  `Ord` is a whole number from **`first_item`** up to **`first_item + items_to_process - 1`** (the
  same window as the portal upload form).
- **`initial_rating_csv`**: full text of `players.csv` at the start of the cycle.
- **`binary_files`**: a lookup table `{ "12-34567.TUNX": bytes, ... }` with the uploaded tournament
  files.

Calling `run_cycle()` returns a dictionary: **output file name → CSV text**.

### Output file names

For each tournament with order number `Ord`:

- `RatingList_after_<Ord>.csv`
- `Audit_of_Tournament_<Ord>.csv`

## CSV files the calculator expects

The calculator uses **semicolons** as the column separator (same as the rest of the portal).

### `players.csv` (rating list)

Each row becomes a player record. Important columns:

- **`Id_No`**: FEXERJ id (whole number).
- **`Id_CBX`**: CBX id (may be blank). For IRT tournaments the code can map CBX → FEXERJ using this.
- **`Rtg_Nat`**, **`TotalNumGames`**: whole numbers.
- Point columns are read and carried through.

The website’s validator (`backend/validator.py`) checks headers and types **before** the calculator
runs, so most “bad CSV” problems are caught earlier with clear messages.

### `tournaments.csv`

For each tournament row in the selected range:

- **`Ord`** and **`CrId`** locate the matching binary file name.
- **`Type`** picks the file extension:
  - `SS` → `.TUNX`
  - `RR` → `.TURX`
  - `ST` → `.TUMX`
- **`IsIrt`** and **`IsFexerj`** change how player ids are read and which special rules may apply.

## Binary file names

The calculator looks for a file named:

`<Ord>-<CrId>.<Ext>`

…where `<Ext>` comes from `Type` (`TUNX` / `TURX` / `TUMX`).

If that file is missing from `binary_files`, the calculator stops with an error (the API turns that
into **HTTP 422** with a short text message).

## Swiss Manager binary files — what the code assumes

The parser is in `calculator/tunx_parser.py`. It does **not** read a nice table from Swiss Manager;
it reads **raw bytes** and looks for known patterns.

### Section markers (fixed byte patterns)

The file is expected to contain two markers (shown here as hex, the way programmers write them):

- **BIO marker** (`a5ff8944`) — where player names and ids live
- **PAIRING marker** (`b3ff8944`) — where results / pairings live

The portal validator checks these markers early so you get a **Portuguese** error in the browser when
possible, instead of a low-level parser error.

### BIO block (players)

The BIO block is turned into a simple table keyed by **`snr`** (Swiss Manager’s **starting rank /
board number** — a 1, 2, 3… index inside that tournament file):

`{ snr → { name, fexerj_id } }`

Important details:

- `snr` starts at 1 and goes up one step per player record.
- Names are read as **UTF‑16LE** text (a two-byte-per-character encoding Swiss Manager uses).
- Sometimes there is a stray `'*'` field before an abbreviation; the parser skips that case.

Every player must end up with a **FEXERJ id**. Empty ids raise an error. The portal validator also
checks “every BIO line has an id” so the message is easier to act on.

### PAIRING block (games)

Games are turned into a simple list:

`(player snr, opponent snr, score for the first player)`

Assumptions:

- Each stored pairing record has a **fixed length** in the file (`PAIRING_STRIDE = 21` in code).
- Known result letters become numeric scores: win **1.0**, draw **0.5**, loss **0.0**.
- Byes and empty slots are ignored.

### Parser warnings (soft signals)

`parse`/`validate` can print **warnings** when the file shape looks “off” — for example:

- pairing data size not a clean multiple of the fixed record length
- many unknown result codes
- games that mention player numbers not found in BIO

Warnings do not always mean the run failed, but they are a **heads-up** that Swiss Manager may have
changed export details and the parser may need a human review.

## How ratings are updated (big picture)

In plain steps:

1. Load the starting rating list.
2. Read players and games from the tournament binary.
3. Sort players into three buckets by **how many rated games they had before this tournament**:
   - **Unrated** — `TotalNumGames == 0`
   - **Temporary** — played before, but still **fewer than 15** games in total (`1`–`14`)
   - **Established** — **15 or more** games in total
4. Compare **points actually scored** in this tournament to **points the system expected** from the
   opponents’ ratings.
5. Pick **one** calculation rule (stored in the audit column `Calc_Rule`):
   - `TEMPORARY`
   - `RATING_PERFORMANCE`
   - `DOUBLE_K`
   - `NORMAL`
6. Write the updated rating list and the audit CSV.

The audit file exists so you can answer “why did this player’s rating move this way?” without
re-running the code in your head.

### Player buckets (simple definitions)

- **Unrated / temporary** players follow the **`TEMPORARY`** path (see below).
- **Established** players can use **`RATING_PERFORMANCE`**, **`DOUBLE_K`**, or **`NORMAL`**.

### When each rule is used

Only **one** rule is chosen per player. The audit column `Calc_Rule` shows which one.

- **`TEMPORARY`**: player is **unrated** (0 games before) or **temporary** (1–14 games before). This
  path uses a **performance-style** update based on averages across their whole early history (see
  code: `apply_temporary_rule`).
- **`RATING_PERFORMANCE`**: only for **established** players (`15+` games before), and only when the
  tournament is flagged as a **FEXERJ** tournament (`IsFexerj == 1`). Also needs enough games **in
  this tournament** and a strong “scored above expectation” signal (numbers below). If the player
  has **fewer than 5** games in this tournament, this rule is **skipped** and the code keeps
  checking the next rules.
- **`DOUBLE_K`**: for **established** players when a different “scored above expectation” test passes
  (numbers below). Needs **at least 4** games in this tournament. If it applies, the usual K-based
  change is **doubled**. If the player has **fewer than 4** games here, this rule is **skipped**.
- **`NORMAL`**: the usual path for **established** players when none of the special rules apply. The
  rating moves by **K × (points scored − points expected)** (rounded), with a floor so the rating
  does not drop below 1.

#### If more than one rule could fit — the order matters

Think of it as a checklist the code walks top to bottom:

1. If the player is **unrated or temporary** → **`TEMPORARY`** (stop here).
2. Else, if **`RATING_PERFORMANCE`** fits → use it (stop here).
3. Else, if **`DOUBLE_K`** fits → use it (stop here).
4. Else → **`NORMAL`**.

So in a FEXERJ tournament, **`RATING_PERFORMANCE` beats `DOUBLE_K`** when both tests would pass.

#### “Scored above expectation” in one sentence

After invalid opponents are removed, the code compares:

- **`this_expected_points`**: “how many points a typical player with **your old rating** would expect
  against opponents whose strength is summarized by **your average opponent rating** in this
  tournament”. The formula is the usual chess **Elo expected score** (same idea as “400‑point scale”
  math you see in rating manuals), scaled by how many games you actually played here:

  `this_games / (1 + 10 ** ((this_avg_oppon_rating - last_rating) / 400))`

  (Implemented in `calculate_new_rating` in `calculator/classes.py`.)

- **`this_points_above_expected`**: **points you actually scored** minus **`this_expected_points`**.
  The special rules compare this gap to fixed cutoffs that depend on how many games you played here.

**`RATING_PERFORMANCE` cutoffs** (only when this tournament has **5–7** counted games):

| Games here | Needs `this_points_above_expected` at least |
|-----------:|----------------------------------------------:|
| 5 | 1.84 |
| 6 | 2.02 |
| 7 | 2.16 |

If there are **more than 7** games here, the **`RATING_PERFORMANCE` shortcut is not used** (the code
moves on to `DOUBLE_K` / `NORMAL`).

**`DOUBLE_K` cutoffs** (only when this tournament has **4–7** counted games):

| Games here | Needs `this_points_above_expected` at least |
|-----------:|----------------------------------------------:|
| 4 | 1.65 |
| 5 | 1.43 |
| 6 | 1.56 |
| 7 | 1.69 |

If there are **more than 7** games here, **`DOUBLE_K` is not used** (you fall back to **`NORMAL`**).

### K factors (only for `NORMAL` and `DOUBLE_K`)

**K** is simply “how fast the rating moves” for established players on the **K-based** paths
(`NORMAL` and `DOUBLE_K`). Bigger K → bigger jumps for the same over- or under-performance.

**`TEMPORARY`** and **`RATING_PERFORMANCE`** do **not** use this K table to compute the new rating,
even though the audit file may still show a `K` column for bookkeeping.

K is picked from **`TotalNumGames` before the tournament** (`_K_STARTING_NUM_GAMES` in code):

| Games in life before this event | K used on K-based paths |
|--------------------------------:|------------------------:|
| 0–14 | 30 *(but 0–14 players are on the `TEMPORARY` path, so this “30” is not what moves their rating)* |
| 15–39 | 25 |
| 40–79 | 15 |
| 80+ | 10 |

## Common failures (what you’ll see)

- **Missing binary for a tournament** → API **422** with a short message naming the expected file.
- **Unknown `Type` in `tournaments.csv`** → **422** saying it is not a supported tournament type.
- **Missing FEXERJ id in the BIO block** → error from the calculator or a validation list from the
  portal, depending on where it is caught first.
- **Warnings from the parser** → not always fatal, but worth checking whether Swiss Manager changed
  export details.

## Where to read the code

- `calculator/classes.py` — tournament loop, rules, audit columns
- `calculator/tunx_parser.py` — binary layout and warnings
- `backend/validator.py` — friendly checks before the calculator runs
