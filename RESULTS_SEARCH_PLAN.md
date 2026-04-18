# Results page: unified search (tournaments + players)

## Goal

One search field filters the visible list on the active tab:

| Tab | Filter targets |
|-----|----------------|
| **Por torneio** | Tournament **name**, cycle **`ord`** (display order), **Chess Results `crId`** |
| **Por jogador** | Player **name**, **FEXERJ id** (`fexerjId`) |

Reduce scrolling for large rating cycles without backend changes.

## Decisions (locked before implement)

| Topic | Choice |
|-------|--------|
| **(a) `crId === 0`** | Treat like missing: **do not** use `crId` for ID matching when `crId === 0` (avoids false positives: `String(0).includes('0')` matching digit runs like `"100"` / `"2025"` for every tournament with placeholder 0). **`ord`** matching is unchanged. |
| **(b) Module** | **[`frontend/src/searchUtils.js`](frontend/src/searchUtils.js)** — pure helpers only; **no imports from `resultParser`**. Tests in **`frontend/src/searchUtils.test.js`**. Keeps [`resultParser.js`](frontend/src/resultParser.js) focused on ZIP/CSV/index. |
| **(c) `aria-controls`** | **Omit on the input for v1.** `<label htmlFor>` + `<input id>` is sufficient for SRs; `aria-controls` on a search box adds coupling without a live region benefit. |

## UX

- **Placement:** A single control sits **above both tab panels** (below the tablist, or directly under the tab row—same horizontal band as tabs). Same **query string** applies whichever tab is selected; switching tabs does **not** clear the input (**keep query**).
- **Control:** `<label htmlFor="…">` + `<input type="search" id="…" className="input">`, Portuguese label e.g. **Filtrar por nome ou ID**.
- **Accessibility (v1):** Label ↔ input association only; no `aria-controls` on the search field.
- **Empty state:** When the query is non-empty (after trim) and the filtered list is empty, show a short message (e.g. **Nenhum resultado encontrado.**) **inside** the relevant **`role="tabpanel"`** (alongside where the accordion list would be)—**not** between the search input and the panels, or the copy would sit above the hidden panel too.

## Matching rules (shared normalizer)

Implement **pure** helpers in `searchUtils.js`:

- **`normalizeForSearch(s)`** — Use **`String(s ?? '')`** before **`.normalize('NFD')`** so **null** / **undefined** names (e.g. player with id only, or blank tournament name from CSV) never throw.

**Name match:** `normalizedName.includes(normalizedQuery)` where the query is **trimmed** then normalized as a single substring (**v1**).

**ID match (digit run):**

1. From **trimmed** query: `digitPart = query.replace(/\D/g, '')`.
2. If `digitPart` is **non-empty**:
   - **Player:** if `fexerjId != null`, match when `String(fexerjId).includes(digitPart)`.
   - **Tournament:** `String(ord).includes(digitPart)` **OR** (`crId != null && crId !== 0 && String(crId).includes(digitPart)`).

3. **Combined:** show row if **nameMatch OR idMatch**.

### Mixed query behavior (informational, not a bug)

A query like `"João 100"` yields `digitPart === "100"`. Name match fails (no full-name substring `"joão 100"` after normalize). ID match still returns every player whose `fexerjId` contains `"100"` (100, 1001, 2100, …). **OR** semantics make this intentional for v1—review tests with that expectation.

**Edge cases:**

- **Empty / whitespace-only query** → trim to `''` → **no filtering** (full list). Explicit unit test: `" "` / `"\t"` → passthrough.
- **`fexerjId === null`:** only **name** can match.

## Implementation sketch

| Piece | Location |
|-------|----------|
| `normalizeForSearch`, `filterTournamentsForSearch`, `filterPlayersForSearch` | [`frontend/src/searchUtils.js`](frontend/src/searchUtils.js) |
| Unit tests | [`frontend/src/searchUtils.test.js`](frontend/src/searchUtils.test.js) |
| `useState` for query + **two** `useMemo` hooks | [`frontend/src/ResultsPage.jsx`](frontend/src/ResultsPage.jsx): **`filteredTournaments`** depends on `[query, tournaments]`; **`filteredPlayers`** depends on `[query, playersByPlayer]`. Keep them **separate** so changing tabs does not re-run filtering for the inactive list. |
| Map filtered arrays | each `role="tabpanel"` |

**Chrome 109:** Reuse [`.input`](frontend/src/index.css) for the field.

### Implementation notes (engineer checklist)

1. **`normalizeForSearch`:** `String(s ?? '').normalize('NFD')` … — null-safe for names.
2. **`useMemo`:** Two derivations, not one combined memo, to avoid redundant work when switching tabs.
3. **Empty state:** Render **inside** each `tabpanel` only; never sole child between global search and both panels.

## Tests

| Layer | Cases |
|-------|--------|
| **Unit** (`searchUtils.test.js`) | Tournament: name; `ord` digits; `crId` digits (with **`crId === 0`** excluded from ID branch); combined OR; **empty string** passthrough; **whitespace-only** passthrough. Player: name + id digits; same edge cases. |
| **Integration** (`ResultsPage.test.jsx`) | Filter shrinks lists on both tabs; clear restores; tab switch keeps query behavior. |

## Non-goals (v1)

- Filtering **players inside** an expanded tournament on **Por torneio** (only top-level tournament accordions).
- URL persistence, debouncing (lists are in-memory; optional debounce only if profiling says so).

## Follow-up (optional)

- Highlight matching substring in titles (accessibility + complexity).
- Separate placeholders per tab if user testing shows confusion (“nome ou ID” is intentionally generic).
