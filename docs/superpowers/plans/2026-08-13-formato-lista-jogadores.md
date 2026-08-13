# Players file format — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change `players.csv` from 29 to 43 columns, once and for all, and make
`compute_unrated_period` stop counting the discarded first tournament's games.

**Architecture:** The 29-column format is replaced wholesale — it has never been used in
production, so there is no migration path to keep. `Peak2200_<mod>` is absorbed by
`K_<mod>`: FEXERJ decided the K factor is written to the file and *is* the "already reached
2200" indicator (test `K == 10`). The engine keeps `ModalityState.reached_2200` internally;
only the serialization changes. Four other columns join in the same pass, because the
federation keeps this file between cycles and it must not change twice.

**Tech Stack:** Python 3.12, pytest, ruff, mypy; JS (vitest) for the browser-side validation.

## Global Constraints

- Code in English — identifiers, docstrings, comments, test names, commit messages. Only
  operator-facing portal strings and `docs/` stay in Portuguese.
- Never use real player names in tests or fixtures (CLAUDE.md).
- `logger.warning()`, never `print()` to stdout. `print(..., file=buf)` for CSV buffers is
  intentional and stays.
- The current engine (`calculator/classes.py`, `calculator/tunx_parser.py`) is untouchable;
  `tests/test_legacy_engine_golden.py` locks it byte for byte.
- `git add` naming files explicitly. Never `-A`, never `.`.
- Every behaviour fix ships with a test that fails before and passes after, proven by
  mutation: break the implementation on purpose, watch the test fail, undo.

## Out of scope — decided, do not touch

- The three rating-substitution audit fields (`Audit_Period.csv`). The trigger rule is still
  being negotiated, and the audit is regenerated output: it is cheap to change later.
- Reorganizing `docs/modelo-rating-fide.md` into three annexes. The trigger rule enters the
  document first; doing it now is doing it twice.
- The trigger rule itself. When it closes it becomes a new item under `### 6.4 Jogador que já
  tem rating FIDE`, not a new section.

---

## The format

43 columns. Identity block, then one 11-column group per modality (`Std`, `Rpd`, `Blz`).

```
Id_No;Id_CBX;PrevId;Title;Name;ClubName;Birthday;Sex;Fed;Status;
Rtg_Std;Games_Std;K_Std;FirstTrn_Std;LastPlayed_Std;RtgFide_Std;FideDate_Std;
AccGames_Std;AccSumOpp_Std;AccPts_Std;AccSince_Std;   (× Rpd, × Blz)
```

| Column | Written by | Meaning |
|---|---|---|
| `PrevId` | operator | Id of the record this person had before. Must exist as an `Id_No` in the file (§11.1). Not read by the calculation. |
| `Status` | operator | `1` active, `0` inactive, `2` grampo, `3` other state, `4` deceased. Governs publication, never calculation. |
| `K_<mod>` | program | §5 K factor **before** the 700 cap, computed from the state at the *end* of the period. `K == 10` is the permanent "reached 2200" indicator. |
| `FirstTrn_<mod>` | program | `1` once the player has played a first tournament with at least one rated opponent. Spends the §6.1 discard. |
| `LastPlayed_<mod>` | program | `AAAA-MM` of the last period in which the player had any game in that modality. |
| `RtgFide_<mod>` | operator | FIDE rating, face value (§6.4). Empty when there is none. |
| `FideDate_<mod>` | operator | Date the FIDE rating was checked (§6.4 d). Required whenever `RtgFide_<mod>` is filled, and only then. |

### Two properties the format depends on — verified, do not break

1. **`base_k()` returns 10 if and only if `reached_2200` is true.** That is what makes
   `K == 10` an exact replacement for `Peak2200_`. It holds only for the *base* K:
   `cap_k_by_games(20, 64..70)` also returns 10, so writing the 700-capped K would freeze a
   player at K=10 forever after a single 64-to-70-game period. The effective (capped) K is
   already in `Audit_Games.csv`; the column carries the §5 factor.
2. **The K is computed from the state at the end of the period.** A player who enters at
   2150 and leaves at 2210 has to leave the cycle with `10` in the file — writing the entry
   K would lose the permanence in the very cycle that earned it.

### Decisions taken inside §6.4 that the document does not yet spell out

- **The K-by-band rule persists.** A player who entered on a FIDE rating would flip to the
  new-player K=40 on their second period, since they still have fewer than 30 FEXERJ games —
  which is exactly what §6.4 says must not happen. So: while `RtgFide_<mod>` is filled, the
  new-player branch of §5 never applies. The under-18 branch still does; it keys on age and
  rating, not on the game count.
- **FIDE entry only fires on zero FEXERJ games** in that modality (§6.4 d's own wording).
  Without that guard, a player dropped by the floor (§7) would be re-entered at their FIDE
  rating every period, forever.
- **`RtgFide_<mod>` must be at or above the 1200 floor**, mirroring the check `Rtg_<mod>`
  already gets: a rated player below the floor is a state the model forbids.

---

## Files

| File | Change |
|---|---|
| `calculator/fide/model.py` | `PlayerState.prev_id`, `.status`; `ModalityState.first_tournament_played`, `.last_played`, `.fide_rating`, `.fide_date` |
| `calculator/fide/ratinglist.py` | 43-column header, read/write, K ⇄ `reached_2200`, legacy conversion |
| `calculator/fide/rules.py` | `base_k(..., from_fide_rating=False)` |
| `calculator/fide/period.py` | discard marker, discarded games leave the count, `fide_entry_state` |
| `calculator/fide/cycle.py` | entry-state dispatch, `_apply_results` persistence |
| `calculator/compare.py` | `write_rating_list` call site |
| `backend/validator.py` | rules for the 43-column format |
| `frontend/src/csvUploadValidation.js` | header constant and column count |
| `tests/…` | fixtures and behaviour |
| `README.md`, `docs/modelo-rating-fide.md` | the format and the rules |

---

### Task 1: The format — model, read, write

**Files:**
- Modify: `calculator/fide/model.py`, `calculator/fide/ratinglist.py`,
  `calculator/fide/cycle.py:107`, `calculator/compare.py:60`
- Test: `tests/fide/test_ratinglist.py`, `tests/fide/test_ratinglist_legacy.py`

**Interfaces produced:**
- `FIDE_HEADER: str` — 43 columns, `FIDE_COLUMN_COUNT = 43`
- `write_rating_list(players: dict[int, PlayerState], period_year: int) -> str`
- `ModalityState(rating, games, reached_2200, first_tournament_played, last_played,
  fide_rating, fide_date, accumulator)`
- `PlayerState(..., prev_id: str = "", status: int = 1)`

- [ ] **Step 1: Write the failing tests** in `tests/fide/test_ratinglist.py`, over a
      43-column fixture whose per-field values are pairwise distinct so a column swap
      changes an assertion:
      - `test_k_10_reads_as_reached_2200` / `test_k_20_does_not`
      - `test_reads_first_tournament_marker`, `test_reads_last_played`
      - `test_reads_fide_rating_and_date`, `test_empty_fide_rating_is_none`
      - `test_reads_status_and_prev_id`
      - `test_writes_base_k_not_capped_k` — a player with 70 games in the period still
        writes `20`, never `10`
      - `test_writes_10_for_a_player_who_reached_2200_and_fell_below` (rating 2150,
        `reached_2200=True`) and `test_writes_10_for_an_unrated_player_who_reached_2200`
      - `test_round_trip` — read then write reproduces the fixture byte for byte
- [ ] **Step 2: Run and watch them fail.** `.venv/bin/pytest tests/fide/test_ratinglist.py -v`
- [ ] **Step 3: Implement.** `FIDE_HEADER` from the per-modality prefix tuple
      `("Rtg", "Games", "K", "FirstTrn", "LastPlayed", "RtgFide", "FideDate", "AccGames",
      "AccSumOpp", "AccPts", "AccSince")`, `_IDENTITY_COLUMNS` gaining `PrevId` and `Status`,
      `_IDENTITY_FIELD_COUNT = 10`, `_FIELDS_PER_MODALITY = 11`. Read `reached_2200` as
      `row[base + 2].strip() == "10"` — string comparison, so a blank or a corrupt cell reads
      as "not reached" instead of raising. Write `rules.base_k(rating=state.rating,
      games=state.games, reached_2200=state.reached_2200, birth_year=parse_birth_year(
      player.birthday), period_year=period_year, from_fide_rating=state.fide_rating is not
      None)`.
- [ ] **Step 4: Legacy conversion** (`_read_legacy_rows`): `status=1`, `prev_id=""`,
      `fide_rating=None`, `fide_date=""`, `last_played=""`, and — the one that matters —
      `first_tournament_played=games > 0`, which is exactly the `state.games == 0` test
      Task 2 replaces. Add `test_converted_player_with_games_has_spent_the_discard` and
      `test_converted_player_with_no_games_still_has_it`.
- [ ] **Step 5: Fix the two call sites.** `cycle.run_cycle` and `compare.run_comparison`
      pass `period_year(outcome.tournaments)`; both already return early on an empty window,
      so the list is never written without tournaments to date it.
- [ ] **Step 6: Run the whole suite.** `.venv/bin/pytest -q` — expect failures only in
      `tests/fide/test_cycle.py`, `tests/test_validator_fide.py`, `tests/test_validator_modes.py`
      and `tests/test_contract.py`, which later tasks own.
- [ ] **Step 7: Commit** `calculator/fide/model.py calculator/fide/ratinglist.py
      calculator/fide/cycle.py calculator/compare.py tests/fide/test_ratinglist.py
      tests/fide/test_ratinglist_legacy.py`

### Task 2: The discard stops counting, and gets its own marker

**Files:**
- Modify: `calculator/fide/period.py:169-303`
- Test: `tests/fide/test_period_unrated.py`

**Interfaces produced:** `PeriodResult.first_tournament_seen: bool = False`

The order is forced: the moment the discarded tournament stops incrementing the game count,
`state.games == 0` stops meaning "has not played yet" and the player silently earns a second
discard. The marker has to be in place in the same commit.

- [ ] **Step 1: Write the failing tests.**
      - `test_discarded_tournament_games_do_not_count` — a zeroed 4-game first tournament
        returns `games_counted == 0` (today: 4)
      - `test_second_zeroed_tournament_counts_after_the_marker_is_set` — state with
        `first_tournament_played=True, games=0` zeroes a tournament: it is *not* discarded
      - `test_marker_is_reported_when_a_tournament_is_discarded` —
        `result.first_tournament_seen is True` even though `games_counted == 0`
      - `test_marker_is_reported_when_the_first_tournament_is_counted`
      - `test_tournament_without_rated_opponents_does_not_spend_the_discard` — the existing
        behaviour: `counted` empty means the tournament is skipped entirely
- [ ] **Step 2: Run and watch them fail.**
      `.venv/bin/pytest tests/fide/test_period_unrated.py -v`
- [ ] **Step 3: Implement.** `first_tournament_pending = not state.first_tournament_played`;
      move `games_counted += len(counted)` below the discard branch so the discarded
      tournament contributes nothing; set `first_tournament_seen = True` where the pending
      flag is cleared. Rewrite the docstring paragraph that explains the old marker and the
      `(If decision B ever stops counting unrated games…)` comment — the "if" has happened.
- [ ] **Step 4: Run and watch them pass**, then prove by mutation: restore
      `first_tournament_pending = state.games == 0`, confirm
      `test_second_zeroed_tournament_counts_after_the_marker_is_set` fails, undo.
- [ ] **Step 5: Commit** `calculator/fide/period.py tests/fide/test_period_unrated.py`

### Task 3: The cycle persists the new state

**Files:**
- Modify: `calculator/fide/cycle.py:149-184`
- Test: `tests/fide/test_cycle.py`

- [ ] **Step 1: Write the failing tests.**
      - `test_last_played_is_stamped_for_every_player_who_played` — including a player whose
        only games were against unrated opponents (`games_counted == 0`), who is active
      - `test_first_tournament_marker_survives_a_discarded_period`
      - `test_marker_is_not_reset_by_the_26_month_window` (§6.2: the reset does not hand the
        discard back)
      - `test_status_prev_id_and_fide_columns_round_trip_through_a_cycle`
      - `test_reached_2200_comes_from_the_entry_state` — set up in Task 4
- [ ] **Step 2: Run and watch them fail.** `.venv/bin/pytest tests/fide/test_cycle.py -v`
- [ ] **Step 3: Implement.** `_apply_results(initial_players, results, entry_states, month)`:
      carry `first_tournament_played = before.first_tournament_played or
      result.first_tournament_seen or result.games_counted > 0`; `last_played = month` for
      every result; copy `fide_rating`/`fide_date` from `before`; and take `reached_2200`
      from `before.reached_2200 or entry.reached_2200 or (final is not None and final >=
      K10_THRESHOLD)` — `entry` is why a FIDE entrant at 2300 who ends the period at 2190
      still keeps the permanent K=10.
- [ ] **Step 4: Run the suite.** `.venv/bin/pytest tests/fide -q`
- [ ] **Step 5: Commit** `calculator/fide/cycle.py tests/fide/test_cycle.py`

### Task 4: Entry on a FIDE rating (§6.4)

**Files:**
- Modify: `calculator/fide/rules.py:70-106`, `calculator/fide/period.py:147-166`,
  `calculator/fide/cycle.py:113-146`
- Test: `tests/fide/test_rules_k.py`, `tests/fide/test_period_rated.py`, `tests/fide/test_cycle.py`

**Interfaces produced:**
- `base_k(rating, games, reached_2200, birth_year, period_year, from_fide_rating=False)`
- `fide_entry_state(player: PlayerState, modality: str) -> ModalityState | None`

- [ ] **Step 1: Write the failing tests.**
      - `test_fide_entrant_takes_k_from_the_rating_band_not_the_game_count` — rating 1900,
        0 games, `from_fide_rating=True` → 20, not 40
      - `test_fide_entrant_under_18_still_takes_the_under_18_k` → 40
      - `test_fide_entrant_at_2200_locks_k10`
      - `test_fide_rating_beats_the_cross_modality_carry_over` (§1.1 defers to §6.4)
      - `test_fide_rating_is_ignored_once_the_player_has_games_in_the_modality` — the
        floor-dropped player is not re-entered
      - `test_fide_entrant_is_capped_at_400_against_a_far_stronger_field` — the 2000 cap of
        §6.3 does not apply, the 400 cap of §3 does
- [ ] **Step 2: Run and watch them fail.**
- [ ] **Step 3: Implement.** In `base_k`, guard the `games < NEW_PLAYER_GAMES` branch with
      `not from_fide_rating`. `fide_entry_state` returns `None` unless
      `state.rating is None and state.games == 0 and state.fide_rating is not None`;
      otherwise a `ModalityState` at the FIDE rating with `reached_2200 = rating >=
      K10_THRESHOLD`, carrying `fide_rating`/`fide_date` forward so
      `compute_rated_period` can read them. In `_entry_states`, try `fide_entry_state`
      **before** `transposed_state`. `_path_for` gains `"FIDE_ENTRY"`.
      `compute_rated_period` passes `from_fide_rating=state.fide_rating is not None`.
- [ ] **Step 4: Run and watch them pass**, then prove by mutation: swap the order of
      `fide_entry_state` and `transposed_state`, confirm
      `test_fide_rating_beats_the_cross_modality_carry_over` fails, undo.
- [ ] **Step 5: Commit** `calculator/fide/rules.py calculator/fide/period.py
      calculator/fide/cycle.py tests/fide/test_rules_k.py tests/fide/test_period_rated.py
      tests/fide/test_cycle.py`

### Task 5: Validator

**Files:**
- Modify: `backend/validator.py:257-360`
- Test: `tests/test_validator_fide.py`, `tests/test_validator_modes.py`

- [ ] **Step 1: Write the failing tests.**
      - `test_deceased_player_with_games_is_accepted` — **the one the federation asked for**:
        status `4`, `Games_Std` above zero, no error. Death happens mid-cycle.
      - `test_status_outside_0_to_4_is_rejected`, `test_status_is_required`
      - `test_k_must_be_10_20_or_40`, `test_k_10_below_2200_is_accepted` (that is the
        permanence, not an error)
      - `test_first_trn_must_be_0_or_1`
      - `test_last_played_must_be_year_month`
      - `test_fide_rating_below_the_floor_is_rejected`
      - `test_fide_rating_without_a_date_is_rejected` and the mirror
        `test_fide_date_without_a_rating_is_rejected`
      - `test_prev_id_must_point_at_a_player_in_the_file`
- [ ] **Step 2: Run and watch them fail.** `.venv/bin/pytest tests/test_validator_fide.py -v`
- [ ] **Step 3: Implement** in `_validate_fide_players_csv`, keeping the existing message
      style (`players.csv linha {row_num}: …`). `PrevId` needs a second pass: collect the
      referenced ids while looping and check them against `id_no_seen` at the end.
- [ ] **Step 4: Run and watch them pass.** Confirm no check anywhere correlates `Status`
      with games, ratings or accumulators — the status is cadastral, full stop.
- [ ] **Step 5: Commit** `backend/validator.py tests/test_validator_fide.py
      tests/test_validator_modes.py`

### Task 6: Browser-side validation and the contract test

**Files:**
- Modify: `frontend/src/csvUploadValidation.js:15-19`
- Test: `tests/test_contract.py`, `frontend/src/csvUploadValidation.test.js`

The browser pass stays structural (header, column count, ids, name, duplicates); the
per-modality rules stay on the server. `tests/test_contract.py` is what keeps the two
headers from drifting.

- [ ] **Step 1: Run the contract test and watch it fail.**
      `.venv/bin/pytest tests/test_contract.py -v`
- [ ] **Step 2:** Update `FIDE_PLAYERS_HEADER` and `FIDE_PLAYERS_COLUMN_COUNT = 43`, and the
      43-column fixtures in `csvUploadValidation.test.js`.
- [ ] **Step 3: Run both suites.** `.venv/bin/pytest tests/test_contract.py -v` and
      `cd frontend && npm test`
- [ ] **Step 4: Commit** `frontend/src/csvUploadValidation.js
      frontend/src/csvUploadValidation.test.js tests/test_contract.py`

### Task 7: README and the rules document

**Files:**
- Modify: `README.md:103-137`, `docs/modelo-rating-fide.md`

- [ ] **Step 1: README** — the 43-column block, the per-modality group, one line per new
      column, and a sentence on which columns the operator fills and which the program
      overwrites every cycle.
- [ ] **Step 2: `docs/modelo-rating-fide.md` → version 1.5, 13/08/2026.**
      - Open point 1 (how the K=10 permanence is stored) is **closed**: it comes out of the
        open-points section and becomes rule in §5 — the K column is the indicator, written
        by the program, and a manual `10` freezes that player's factor, which is why the
        audit will flag a K=10 below 2200.
      - Open point 3 (how the document fits the regimento) is **closed**: it does not enter
        the regimento; it becomes three annexes — normative, transition, tests. One
        sentence. No reorganizing.
      - §5: the permanence indicator is the `K_<mod>` column; the column carries the §5
        factor before the 700 cap, and the effective K of each game is in the audit.
      - §6.1: name the `FirstTrn_<mod>` marker as what carries "only the first tournament"
        across periods, now that the discarded tournament's games no longer count.
      - §6.4: the K-band rule persists while a FIDE rating is recorded; the entry only fires
        on zero FEXERJ games in the modality; `RtgFide_` sits at or above the floor;
        `FideDate_` is the conference date of item (d).
      - §11.1: the full 43-column table, replacing the prose about the 29-column layout.
- [ ] **Step 3: Build the `.docx`.** `.venv/bin/python scripts/build-docx.py`
- [ ] **Step 4: Ask Pedro to check it in Word** — not LibreOffice, which lays tables out
      differently and has already cost two rounds of corrections.
- [ ] **Step 5: Commit** `README.md docs/modelo-rating-fide.md` and the generated `.docx`
      only if Pedro says it is going to the federation.

### Task 8: Full verification

- [ ] `.venv/bin/pytest -q` — 1121+ tests, coverage at or above 95%
- [ ] `.venv/bin/ruff check .` and `.venv/bin/mypy .`
- [ ] `cd frontend && npm test && npx eslint src`
- [ ] `.venv/bin/pytest tests/test_legacy_engine_golden.py -v` — the current engine must
      still be byte-identical
- [ ] Run the real cycle from `~/Downloads/2601.zip` through the new format end to end:
      convert the 12-column list, run the three bimesters, and confirm the file the third
      one writes still reads back. This is the only check that exercises 2.385 real rows.
