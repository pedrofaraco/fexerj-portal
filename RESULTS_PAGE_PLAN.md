# Results Page — Implementation Plan

## Summary

After a successful rating cycle run, replace the current auto-download behavior with a **results page** that shows the processed tournaments, their players, and the per-player audit details. The ZIP remains available via an explicit download button. Nothing is stored server-side; the next run overwrites the previous results in React state.

## Decisions (confirmed)

1. **Player summary row shows:** FEXERJ ID, name, old → new rating, rating delta, `Calc_Rule`.
2. **"Nova execução"** returns to the upload page with the previously uploaded files **preserved**. The upload page gets a new **"Limpar formulário"** button to reset everything.
3. **Download is button-driven**, not automatic. The user clicks "Baixar ZIP" on the results page to get the file.
4. **Player ordering** within a tournament: preserve the row order of `Audit_of_Tournament_<Ord>.csv`, which reflects the `snr` (starting rank) order from the Swiss Manager binary file. Name ordering is a fallback only if that assumption ever breaks.
5. **Language:** all user-facing text in Portuguese; raw audit column names are not exposed to users.
6. **Ratings for display:** `oldRating`, `newRating`, and `delta` come **only from the audit CSV** (`Ro`, `Rn`, and `Rn − Ro`). The production parser does **not** join `RatingList_after_*.csv` for the UI — that only adds matching complexity with no user-visible benefit (the audit is the calculation ledger).
7. **Loading UX:** Keep the existing **`Executando…`** submit state active until both the HTTP response is received **and** client-side unzip + CSV parsing completes—then flip to idle and show results. Do **not** add a separate label such as “Processando resultados…”. If benchmarking later shows multi-second parses, reconsider (e.g. progress UI), not a second wording for the same wait.

## Architecture

**No backend changes.** `/run` continues to stream the ZIP response as today. All derived data comes from parsing the ZIP on the client.

**Frontend flow:**
1. User clicks **Executar** → UI shows **Executando…** until step 5 completes.
2. POST `/run` → receives ZIP blob.
3. The blob is stored in state (retained for the download button).
4. The ZIP is parsed client-side using `jszip` (still within **Executando…**).
5. Parsed data becomes a structured `result` object in React state; **Executando…** ends; the UI swaps the upload page for the results page.
6. A subsequent run replaces `result` and revokes the previous blob URL.

## Data model

```js
result = {
  zipBlob,               // Blob — for download button
  zipFilename,           // "rating_cycle_output.zip"
  tournaments: [
    {
      ord: 1,
      crId: 99999,
      name: "Copa Rio 2026",     // from user's tournaments.csv (kept in form state)
      type: "RR",                // SS | RR | ST
      endDate: "2025-01-01",
      isFexerj: true,
      players: [
        {
          // summary line (always visible)
          fexerjId,
          name,
          oldRating,       // Ro from audit
          newRating,       // Rn from audit (same values as RatingList_after for that player, but UI does not join)
          delta,           // Rn − Ro
          calcRule,        // TEMPORARY | RATING_PERFORMANCE | DOUBLE_K | NORMAL

          // detail section (revealed on expand — all audit fields)
          gamesBefore,              // Ind
          validGames,               // N
          avgOpponRating,           // Avg_Oppon_Rating
          pointsScored,             // This_Points_Against_Oppon
          expectedPoints,           // This_Expected_Points
          pointsAboveExpected,      // This_Points_Above_Expected
          k,                        // K
          // ...any additional audit columns carried through verbatim
        }
      ]
    }
  ]
}
```

## UI structure

```
┌─────────────────────────────────────────────────────────────┐
│ Portal FEXERJ                                      [ Sair ] │
├─────────────────────────────────────────────────────────────┤
│ Resultado do Ciclo de Rating                                │
│                                                             │
│ [ ⬇ Baixar ZIP ]    [ Nova execução ]                       │
│                                                             │
│ ▼ 1 — Copa Rio 2026   (RR, 6 jogadores)                     │
│   ▼ 1234 — João Silva          1800 → 1823  (+23)  NORMAL   │
│      Jogos anteriores: 50                                   │
│      Jogos válidos neste torneio: 5                         │
│      Rating médio dos adversários: 1750                     │
│      Pontos obtidos: 3.5                                    │
│      Pontos esperados: 2.95                                 │
│      Diferença (obtido − esperado): +0.55                   │
│      K: 25                                                  │
│   ▶ 5678 — Maria Souza         1650 → 1658  (+8)   NORMAL   │
│   ▶ ...                                                     │
│                                                             │
│ ▶ 2 — Aberto FEXERJ   (SS, 18 jogadores)                    │
└─────────────────────────────────────────────────────────────┘
```

Two levels of disclosure:
- **Tournament row** — default collapsed; click to expand the player list.
- **Player row** — default collapsed summary; click to expand the audit detail block.

## Portuguese labels

| Field in code / audit CSV | Label shown to the user |
|---|---|
| `Calc_Rule`              | Regra aplicada |
| `Ind` (games before)     | Jogos anteriores |
| `N` (valid games)        | Jogos válidos neste torneio |
| `Avg_Oppon_Rating`       | Rating médio dos adversários |
| `This_Points_Against_Oppon` | Pontos obtidos |
| `This_Expected_Points`   | Pontos esperados |
| `This_Points_Above_Expected` | Diferença (obtido − esperado) |
| `K`                      | K |
| old / new rating         | Rating inicial → Novo rating |
| rating delta             | Variação |
| tournament type          | Tipo (Suíço / Round-Robin / Equipes) |

Exposed rule labels (`TEMPORARY`, `RATING_PERFORMANCE`, `DOUBLE_K`, `NORMAL`) stay as-is — they are stable identifiers that also appear in the audit ZIP, so matching them 1:1 helps users cross-reference. A tooltip or legend can explain each if needed.

## Implementation steps

### 1. Add `jszip` dependency
- `frontend/package.json` → add `jszip` to `dependencies`.
- Run `npm install` locally and commit `package-lock.json`.

### 2. New utility module `frontend/src/resultParser.js`

Public API:
```js
export async function parseRunResult(zipBlob, tournamentsCsvText) → result
```

Responsibilities:
- Unzip the blob with `jszip`.
- Locate `Audit_of_Tournament_<Ord>.csv` entries (primary source for players and ratings). Optionally read `RatingList_after_<Ord>.csv` only if needed for future features—not required for display per decision (6).
- Parse CSVs (semicolon delimiter, handle UTF-8 BOM) with a small local parser — no new dependency for CSV.
- Parse the user's `tournaments.csv` text to get tournament name, type, end date, `IsFexerj`, `CrId`.
- Map each audit row to the `result` data model: summary and detail fields from audit columns (`Ro`, `Rn`, `Ind`, `N`, …).
- Preserve audit CSV row order for each tournament.
- Return the `result` object described above.

Edge cases:
- A tournament with no players in the audit file (e.g. everyone had fewer valid games than the minimum) → empty `players` list, still render the tournament row.
- A CSV with a BOM prefix (utf-8-sig) → strip before parsing.
- Missing expected audit file → throw a clear error; the UI falls back to download-only mode with an explanatory message.

### 3. `App.jsx` changes

- New state: `result` (object | null).
- On successful `/run`:
  - Replace current "auto-download" logic with: store `zipBlob`, call `parseRunResult(zipBlob, tournamentsCsvText)`, store the result—all while **`status === 'loading'`** / button shows **Executando…** until parse resolves (see decision (7)).
  - If parsing fails, set an error state that renders a minimal fallback results page with just the download button and an explanatory message; then end loading.
- On `handleLogout`: clear `result` and revoke any blob URLs held.
- Route selection:
  - No credentials → `<LoginPage>`
  - Credentials + `result === null` → `<RunPage>` (current upload page)
  - Credentials + `result !== null` → `<ResultsPage>`

### 4. Upload page (`RunPage`) updates

- New button **"Limpar formulário"** that resets `form` to `INITIAL_FORM`. Appears alongside the Executar button (secondary styling).
- No other behavioral change — form state preservation happens automatically because the component doesn't unmount when `result` is cleared via "Nova execução".

### 5. New component `frontend/src/ResultsPage.jsx`

Responsibilities:
- Header: page title + two primary actions: **Baixar ZIP**, **Nova execução**.
- **Baixar ZIP** uses `URL.createObjectURL(zipBlob)` with cleanup on click (or hold the URL and revoke on unmount).
- **Nova execução** clears `result` (returns to upload page with form state preserved).
- Renders `<TournamentAccordion>` for each tournament.

### 6. Reusable accordion components

- `<TournamentAccordion>` — default collapsed, stores open state locally.
- `<PlayerRow>` — default collapsed summary, stores open state locally.
- Both use `aria-expanded` / `aria-controls` following the pattern already established in `HelpSection`.

### 7. State cleanup

- When `result` is replaced or cleared, revoke the previous blob URL if one was created.
- When the user logs out, revoke and clear.

### 8. Tests

**Unit — `resultParser.test.js`:**
- Given a fixture ZIP + fixture `tournaments.csv`, `parseRunResult` returns the expected structure.
- BOM-prefixed CSVs parse correctly.
- Audit row order is preserved.
- `oldRating` / `newRating` / `delta` match audit `Ro` / `Rn` / arithmetic delta (no rating-list join in production code).
- **Consistency guard (tests only):** from the same fixture ZIP, parse `RatingList_after_<Ord>.csv` and assert for every player `audit.Rn === ratingList.Rtg_Nat` (same FEXERJ ID). Catches calculator regressions without complicating the UI path.
- Empty audit CSV → empty players array, tournament still present.
- Missing expected audit file → throws a clear error.

**Component — `ResultsPage.test.jsx`:**
- Renders with a fixture `result`.
- Accordion expand/collapse works at both levels.
- Download button creates a blob URL of the expected blob.
- "Nova execução" calls the reset callback.
- ARIA attributes present on both accordion levels.

**Integration — existing `App.test.jsx`:**
- Mock `/run` to return a fixture ZIP.
- After Executar, the results page renders (not an auto-download).
- "Nova execução" returns to the upload page with form state preserved.
- "Limpar formulário" resets the form.

**Fixture assets:**
- Use the existing binary fixtures to produce a real ZIP via a one-off setup script, or hand-craft small CSVs and zip them at test time using `jszip`.

### 9. Documentation

- Update `README.md`: brief mention of the results page in the user flow section.
- No changes needed to `docs/calculator.md`.

## Scope boundaries (explicit non-goals)

- **No server-side storage** of results.
- **No URL routing / deep links** to results.
- **No persistence across reloads** — refreshing the page loses the result; the user must re-run.
- **No filtering, sorting, or search** in the tournament/player lists (can come later if needed).
- **No new backend endpoints** — this is purely a frontend feature.

## Open questions (non-blocking)

These can be resolved during implementation without reopening the plan:
- Should the accordion remember expand/collapse state across renders within the same result? (Default: no — local state is fine.)
- Should "Baixar ZIP" trigger the browser download immediately (current flow emulated) or open a "save as" dialog? (Default: immediate — matches current behavior.)
- Should rating delta be shown with explicit `+` prefix for gains? (Default: yes — `+23` reads better than `23`.)

**Resolved (see Decisions (6)–(7)):** audit vs rating-list source for display; single **Executando…** through parse vs a second processing label.

## Delivery

A single PR on `feat/results-page` → `develop`. Commit structure:
1. Add `jszip` dependency.
2. Add `resultParser.js` + tests.
3. Add `ResultsPage.jsx` + tests.
4. Wire into `App.jsx`; add "Limpar formulário"; add "Nova execução" flow.
5. Update existing `App.test.jsx`.
6. README note.
