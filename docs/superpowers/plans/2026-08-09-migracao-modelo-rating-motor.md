# Migração do modelo de rating — motor e API (plano 1 de 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o motor de rating por partida (FIDE + Art. 68 da FEXERJ) como pacote isolado, expor os três modos de execução na API, sem tocar no motor atual.

**Architecture:** `calculator/` (motor atual) fica intocado. Um pacote novo `calculator/fide/` implementa o modelo por partida em camadas puras (`tables` → `rules` → `cycle`). `calculator/compare.py` roda os dois motores e emite o comparativo. O validador passa a despachar por cabeçalho e por modo; `/validate` e `/run` ganham o campo `mode`.

**Tech Stack:** Python 3.12, FastAPI, pytest, `decimal.Decimal` para toda aritmética de rating.

**Spec:** [`docs/superpowers/specs/2026-08-09-migracao-modelo-rating-design.md`](../specs/2026-08-09-migracao-modelo-rating-design.md)
**Regras:** [`docs/modelo-rating-fide.md`](../../modelo-rating-fide.md) — fechada, não redecidir.

## Global Constraints

- **Nunca tocar em `calculator/classes.py` nem `calculator/tunx_parser.py`.** São o motor oficial. Se um teste exigir mudança neles, pare e reporte.
- **Toda aritmética de rating usa `decimal.Decimal`.** O `round()` embutido é bancário (`round(0.5) == 0`) e contraria a §3 passo 5 da spec.
- **Avisos por `logger.warning()`**, nunca `print()` para stdout. `print(..., file=buf)` para buffers CSV é intencional.
- **Nomes de jogadores em testes e fixtures são placeholders genéricos.** Seguir o padrão de `tests/conftest.py` (`Carlos Mendes`, `Roberto Faria`, …). Nunca nomes reais.
- **Delimitador CSV é `;`** em todos os arquivos.
- **O código é todo em inglês** — identificadores, docstrings, comentários e nomes de teste. É a convenção do repositório: `backend/validator.py` e `calculator/classes.py` são inteiramente em inglês. **A única exceção são as strings mostradas ao operador**, que seguem em português, como já acontece hoje (`"players.csv: cabeçalho inválido — esperado ..."`).
- **Os blocos de código deste plano têm docstrings e comentários em português.** Isso é um erro de redação do plano, não uma instrução: ao implementar, escreva-os em inglês. Os **valores** dos blocos — números, dados de tabela, nomes de coluna, cabeçalhos de CSV e o texto português das mensagens ao operador — são para copiar verbatim.
- **Modalidades:** `STD`, `RPD`, `BLZ`. Sufixos de coluna: `Std`, `Rpd`, `Blz`.
- **Constantes FEXERJ (§2 da spec):** piso 1200, adversário fictício 1600, teto do rating inicial 2000, K=10 a partir de 2200, teto sub-18 2100, teto da diferença 400 sempre, 5 partidas para o primeiro rating, 30 partidas para sair do K=40, teto `n × K` de 700.
- **Rodar os testes:** `.venv/bin/pytest -q`

---

## Pendência de entrada

A **Task 10** precisa das 13 partidas da consulta oficial da FIDE citada na §10 da spec. A spec registra o total (19,60) e três partidas de amostra, não as treze. Peça o dado a Pedro antes de começar a Task 10; as tasks 1–9 e 11–17 não dependem dele.

---

## Task 1: Travar o motor atual com um teste de ouro

O motor atual não será tocado, mas o validador e o backend em volta dele mudam. "Não toquei" é afirmação; o teste de ouro é evidência.

**Files:**
- Create: `tests/test_legacy_engine_golden.py`
- Create: `tests/golden/legacy_rr_1_ratinglist.csv` (gerado no passo 3)
- Create: `tests/golden/legacy_rr_1_audit.csv` (gerado no passo 3)
- Modify: `pyproject.toml:4` (ruff exclude), `pyproject.toml:24-28` (mypy exclude e override)

**Interfaces:**
- Consumes: `calculator.FexerjRatingCycle` (existente)
- Produces: nada consumido por outras tasks. É uma rede de segurança.

- [ ] **Step 1: Escrever o teste de ouro**

```python
"""Teste de ouro do motor atual: a saída não pode mudar em nenhum byte.

O motor de `calculator/classes.py` gera rating oficial da FEXERJ e não é
tocado pela migração. Este teste falha se alguém o alterar por acidente.
"""
import pathlib

from calculator import FexerjRatingCycle

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'
GOLDEN_DIR = pathlib.Path(__file__).parent / 'golden'

_PLAYERS_CSV = (
    "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;"
    "TotalNumGames;SumOpponRating;TotalPoints\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

_TOURNAMENTS_CSV = (
    "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
    "1;99999;Test RR Tournament;2025-01-01;RR;0;1\n"
)


def _run_legacy_cycle():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    cycle = FexerjRatingCycle(
        tournaments_csv=_TOURNAMENTS_CSV,
        first_item=1,
        items_to_process=1,
        initial_rating_csv=_PLAYERS_CSV,
        binary_files={"1-99999.TURX": data},
    )
    return cycle.run_cycle()


def test_legacy_rating_list_is_byte_identical():
    output = _run_legacy_cycle()
    expected = (GOLDEN_DIR / 'legacy_rr_1_ratinglist.csv').read_text(encoding='utf-8')
    assert output["RatingList_after_1.csv"] == expected


def test_legacy_audit_is_byte_identical():
    output = _run_legacy_cycle()
    expected = (GOLDEN_DIR / 'legacy_rr_1_audit.csv').read_text(encoding='utf-8')
    assert output["Audit_of_Tournament_1.csv"] == expected
```

- [ ] **Step 2: Rodar e confirmar que falha por falta do arquivo de ouro**

Run: `.venv/bin/pytest tests/test_legacy_engine_golden.py -q -p no:cacheprovider --no-cov`
Expected: FAIL com `FileNotFoundError` apontando `tests/golden/legacy_rr_1_ratinglist.csv`

- [ ] **Step 3: Gerar os arquivos de ouro a partir do motor atual**

```bash
mkdir -p tests/golden
.venv/bin/python - <<'PY'
import pathlib, sys
sys.path.insert(0, '.')
from tests.test_legacy_engine_golden import _run_legacy_cycle
out = _run_legacy_cycle()
g = pathlib.Path('tests/golden')
(g / 'legacy_rr_1_ratinglist.csv').write_text(out["RatingList_after_1.csv"], encoding='utf-8')
(g / 'legacy_rr_1_audit.csv').write_text(out["Audit_of_Tournament_1.csv"], encoding='utf-8')
print("gravado")
PY
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/test_legacy_engine_golden.py -q --no-cov`
Expected: PASS, 2 passed

- [ ] **Step 5: Fazer o lint e o type-check enxergarem `calculator/fide/`**

O `pyproject.toml` hoje exclui `calculator/` inteiro do ruff e do mypy porque o motor atual não é mantido aqui. O pacote novo **é** mantido aqui e precisa ser verificado. Trocar a exclusão de diretório por exclusão dos dois arquivos legados.

Em `pyproject.toml`, substituir a linha do ruff:

```toml
exclude = ["calculator/classes.py", "calculator/tunx_parser.py"]  # motor atual: não mantido aqui
```

E, no bloco `[tool.mypy]`, substituir a exclusão e o override:

```toml
exclude = ["calculator/classes.py", "calculator/tunx_parser.py"]

[[tool.mypy.overrides]]
module = ["calculator.classes", "calculator.tunx_parser"]
ignore_errors = true
```

- [ ] **Step 6: Confirmar que lint e types seguem limpos**

Run: `.venv/bin/ruff check . && .venv/bin/mypy backend calculator`
Expected: sem erros (o pacote `calculator/fide/` ainda não existe)

- [ ] **Step 7: Commit**

```bash
git add tests/test_legacy_engine_golden.py tests/golden/ pyproject.toml
git commit -m "test(calculator): trava a saída do motor atual com teste de ouro"
```

---

## Task 2: Tabelas 8.1.2 e 8.1.1

**Files:**
- Create: `calculator/fide/__init__.py`
- Create: `calculator/fide/tables.py`
- Test: `tests/fide/__init__.py`, `tests/fide/test_tables.py`

**Interfaces:**
- Consumes: nada. Camada mais baixa, sem dependências.
- Produces:
  - `pd_for_diff(diff: int) -> Decimal` — PD da tabela 8.1.2 para `diff = rating_jogador - rating_adversário`
  - `dp_for_score_ratio(p: Decimal) -> int` — dp da tabela 8.1.1

- [ ] **Step 1: Escrever o teste**

```python
"""Tabelas 8.1.2 e 8.1.1 do Handbook FIDE B02."""
from decimal import Decimal

import pytest

from calculator.fide.tables import dp_for_score_ratio, pd_for_diff


class TestPdForDiff:
    @pytest.mark.parametrize("diff,expected", [
        (0, "0.50"), (3, "0.50"),        # fronteira inferior da primeira faixa
        (4, "0.51"), (10, "0.51"),
        (91, "0.62"), (92, "0.63"),      # fronteira que um `<` no lugar de `<=` erraria
        (391, "0.91"), (392, "0.92"), (411, "0.92"),
        (412, "0.93"),                   # inalcançável na FEXERJ pelo teto de 400
        (735, "0.99"), (736, "1.00"),
    ])
    def test_higher_rated_side(self, diff, expected):
        assert pd_for_diff(diff) == Decimal(expected)

    @pytest.mark.parametrize("diff,expected", [
        (-3, "0.50"), (-4, "0.49"), (-92, "0.37"), (-400, "0.08"),
    ])
    def test_lower_rated_side(self, diff, expected):
        assert pd_for_diff(diff) == Decimal(expected)

    @pytest.mark.parametrize("magnitude", [0, 1, 46, 91, 92, 200, 367, 400])
    def test_two_sides_sum_to_one(self, magnitude):
        assert pd_for_diff(magnitude) + pd_for_diff(-magnitude) == Decimal("1.00")

    @pytest.mark.parametrize("diff,expected", [
        (400, "0.92"),   # §10 da spec: a fórmula logística daria 0,9091
        (367, "0.90"),   # §10 da spec: a fórmula daria 0,8921
        (46, "0.56"),    # §10 da spec: a fórmula daria 0,5658
    ])
    def test_matches_official_fide_consultation(self, diff, expected):
        """As três partidas documentadas na §10, onde a fórmula logística diverge."""
        assert pd_for_diff(diff) == Decimal(expected)


class TestDpForScoreRatio:
    @pytest.mark.parametrize("p,expected", [
        ("1.00", 800), ("0.99", 677), ("0.75", 193), ("0.51", 7), ("0.50", 0),
        ("0.49", -7), ("0.25", -193), ("0.01", -677), ("0.00", -800),
    ])
    def test_known_values(self, p, expected):
        assert dp_for_score_ratio(Decimal(p)) == expected

    @pytest.mark.parametrize("hundredths", range(0, 101))
    def test_table_is_antisymmetric(self, hundredths):
        p = Decimal(hundredths) / 100
        assert dp_for_score_ratio(p) == -dp_for_score_ratio(1 - p)

    def test_rounds_to_two_decimals(self):
        """p vem de uma divisão e precisa cair numa casa da tabela."""
        assert dp_for_score_ratio(Decimal("0.7499")) == dp_for_score_ratio(Decimal("0.75"))
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_tables.py -q --no-cov`
Expected: FAIL com `ModuleNotFoundError: No module named 'calculator.fide'`

- [ ] **Step 3: Implementar**

Criar `calculator/fide/__init__.py`:

```python
"""Motor de rating por partida — FIDE B02 com as adaptações do Art. 68 da FEXERJ.

Pacote separado do motor por torneio em `calculator/classes.py`, que segue
gerando o rating oficial e não é tocado por este código.
"""
```

Criar `tests/fide/__init__.py` vazio.

Criar `calculator/fide/tables.py`:

```python
"""Tabelas 8.1.2 e 8.1.1 do Handbook FIDE B02.

A §3 da spec proíbe trocar a 8.1.2 pela fórmula logística: a divergência foi
medida contra uma consulta oficial e está registrada na §10 — 7 de 13 partidas
divergem, e o período fecharia 0,76 ponto errado.
"""
from decimal import ROUND_HALF_UP, Decimal

# Tabela 8.1.2 — (limite superior da faixa de D, PD do jogador de rating maior).
# As faixas são fechadas: D de 0 a 3 → .50; de 4 a 10 → .51; e assim por diante.
_PD_BY_MAX_DIFF: tuple[tuple[int, str], ...] = (
    (3, "0.50"), (10, "0.51"), (17, "0.52"), (25, "0.53"), (32, "0.54"),
    (39, "0.55"), (46, "0.56"), (53, "0.57"), (61, "0.58"), (68, "0.59"),
    (76, "0.60"), (83, "0.61"), (91, "0.62"), (98, "0.63"), (106, "0.64"),
    (113, "0.65"), (121, "0.66"), (129, "0.67"), (137, "0.68"), (145, "0.69"),
    (153, "0.70"), (162, "0.71"), (170, "0.72"), (179, "0.73"), (188, "0.74"),
    (197, "0.75"), (206, "0.76"), (215, "0.77"), (225, "0.78"), (235, "0.79"),
    (245, "0.80"), (256, "0.81"), (267, "0.82"), (278, "0.83"), (290, "0.84"),
    (302, "0.85"), (315, "0.86"), (328, "0.87"), (344, "0.88"), (357, "0.89"),
    (374, "0.90"), (391, "0.91"), (411, "0.92"), (432, "0.93"), (456, "0.94"),
    (484, "0.95"), (517, "0.96"), (559, "0.97"), (619, "0.98"), (735, "0.99"),
)
_PD_ABOVE_LAST_BAND = Decimal("1.00")
_ONE = Decimal("1.00")

# Tabela 8.1.1 — dp para p de 0,50 a 1,00, em passos de 0,01.
# A metade inferior sai por antissimetria: dp(p) = -dp(1-p).
_DP_FROM_HALF: tuple[int, ...] = (
    0, 7, 14, 21, 29, 36, 43, 50, 57, 65,
    72, 80, 87, 95, 102, 110, 117, 125, 133, 141,
    149, 158, 166, 175, 184, 193, 202, 211, 220, 230,
    240, 251, 262, 273, 284, 296, 309, 322, 336, 351,
    366, 383, 401, 422, 444, 470, 501, 538, 589, 677,
    800,
)


def pd_for_diff(diff: int) -> Decimal:
    """PD da tabela 8.1.2 para `diff = rating_do_jogador - rating_do_adversário`.

    `diff >= 0` usa a coluna H (jogador de rating maior); `diff < 0` usa a
    coluna L, que é `1 - H`.
    """
    magnitude = abs(diff)
    higher = _PD_ABOVE_LAST_BAND
    for max_diff, value in _PD_BY_MAX_DIFF:
        if magnitude <= max_diff:
            higher = Decimal(value)
            break
    return higher if diff >= 0 else _ONE - higher


def dp_for_score_ratio(p: Decimal) -> int:
    """dp da tabela 8.1.1 para o percentual de pontos `p`.

    `p` é arredondado para duas casas antes da consulta, porque vem de uma
    divisão e precisa cair numa linha da tabela.
    """
    hundredths = int(p.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)
    if hundredths >= 50:
        return _DP_FROM_HALF[hundredths - 50]
    return -_DP_FROM_HALF[50 - hundredths]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_tables.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/__init__.py calculator/fide/tables.py tests/fide/
git commit -m "feat(fide): tabelas 8.1.2 e 8.1.1 do handbook FIDE"
```

---

## Task 3: Primitivas de rating — teto de 400, arredondamento, piso

**Files:**
- Create: `calculator/fide/rules.py`
- Test: `tests/fide/test_rules_primitives.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - constantes `RATING_FLOOR = 1200`, `FICTITIOUS_OPPONENT_RATING = 1600`, `INITIAL_RATING_CAP = 2000`, `K10_THRESHOLD = 2200`, `U18_RATING_CAP = 2100`, `MAX_RATING_DIFF = 400`, `MIN_GAMES_FOR_FIRST_RATING = 5`, `NEW_PLAYER_GAMES = 30`, `K_GAMES_PRODUCT_CAP = 700`
  - `capped_diff(player_rating: int, opponent_rating: int) -> int`
  - `round_half_away_from_zero(value: Decimal) -> int`
  - `applies_rating_floor(rating: int) -> bool`

- [ ] **Step 1: Escrever o teste**

```python
"""Primitivas da §2, §3 e §7 da spec."""
from decimal import Decimal

import pytest

from calculator.fide import rules


class TestCappedDiff:
    @pytest.mark.parametrize("player,opponent,expected", [
        (1800, 1700, 100),
        (1700, 1800, -100),
        (2400, 1500, 400),      # teto positivo
        (1500, 2400, -400),     # teto negativo
        (2000, 1600, 400),      # exatamente no teto, não recortado
        (1500, 1500, 0),
    ])
    def test_caps_at_400_both_directions(self, player, opponent, expected):
        assert rules.capped_diff(player, opponent) == expected

    def test_cap_applies_even_for_very_high_ratings(self):
        """Art. 68 §3º: a exceção da FIDE para 2650+ não vale na FEXERJ."""
        assert rules.capped_diff(2700, 1500) == 400


class TestRoundHalfAwayFromZero:
    @pytest.mark.parametrize("value,expected", [
        ("0.5", 1),      # round() embutido daria 0
        ("1.5", 2),
        ("2.5", 3),      # round() embutido daria 2
        ("-0.5", -1),    # round() embutido daria 0
        ("-2.5", -3),
        ("0.4", 0),
        ("-0.4", 0),
        ("19.60", 20),
        ("-19.60", -20),
    ])
    def test_ties_go_away_from_zero(self, value, expected):
        assert rules.round_half_away_from_zero(Decimal(value)) == expected


class TestRatingFloor:
    @pytest.mark.parametrize("rating,expected", [
        (1199, True), (1200, False), (0, True), (2000, False),
    ])
    def test_floor_at_1200(self, rating, expected):
        assert rules.applies_rating_floor(rating) is expected


def test_constants_match_art_68():
    assert rules.RATING_FLOOR == 1200
    assert rules.FICTITIOUS_OPPONENT_RATING == 1600
    assert rules.INITIAL_RATING_CAP == 2000
    assert rules.K10_THRESHOLD == 2200
    assert rules.U18_RATING_CAP == 2100
    assert rules.MAX_RATING_DIFF == 400
    assert rules.MIN_GAMES_FOR_FIRST_RATING == 5
    assert rules.NEW_PLAYER_GAMES == 30
    assert rules.K_GAMES_PRODUCT_CAP == 700
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_rules_primitives.py -q --no-cov`
Expected: FAIL com `ModuleNotFoundError: No module named 'calculator.fide.rules'`

- [ ] **Step 3: Implementar**

Criar `calculator/fide/rules.py`:

```python
"""Regras de rating: §2 (parâmetros), §3 (partida), §5 (K), §6 (rating inicial), §7 (piso).

Todos os números vêm da tabela da §2 da spec, que traduz o Art. 68 da FEXERJ
sobre o texto da FIDE. Funções puras: nenhuma lê arquivo nem mantém estado.
"""
from decimal import ROUND_HALF_UP, Decimal

# §2 — parâmetros com a adaptação FEXERJ
RATING_FLOOR = 1200                 # abaixo disso o jogador vira não-rated (§7)
FICTITIOUS_OPPONENT_RATING = 1600   # adversários fictícios do rating inicial (§6.2)
INITIAL_RATING_CAP = 2000           # teto do rating inicial (§6.2)
K10_THRESHOLD = 2200                # rating que fixa K=10 (§5)
U18_RATING_CAP = 2100               # teto de rating para o K=40 de sub-18 (§5)
MAX_RATING_DIFF = 400               # teto da diferença, sempre (Art. 68 §3º)
MIN_GAMES_FOR_FIRST_RATING = 5      # §6.1
NEW_PLAYER_GAMES = 30               # §5 — K=40 até completar 30 partidas
K_GAMES_PRODUCT_CAP = 700           # §5.1


def capped_diff(player_rating: int, opponent_rating: int) -> int:
    """Diferença de rating com o teto de 400 sempre aplicado.

    O Art. 68 §3º remove a exceção da FIDE para jogadores de 2650 ou mais: na
    FEXERJ o teto vale para todo mundo.
    """
    diff = player_rating - opponent_rating
    return max(-MAX_RATING_DIFF, min(MAX_RATING_DIFF, diff))


def round_half_away_from_zero(value: Decimal) -> int:
    """Arredonda para o inteiro mais próximo, com 0,5 indo para longe do zero.

    O `round()` embutido do Python é bancário (`round(0.5) == 0`,
    `round(2.5) == 2`), o que contraria a §3 passo 5 da spec.
    """
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def applies_rating_floor(rating: int) -> bool:
    """Verdadeiro quando o rating cai abaixo do piso e o jogador vira não-rated (§7)."""
    return rating < RATING_FLOOR
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_rules_primitives.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/rules.py tests/fide/test_rules_primitives.py
git commit -m "feat(fide): teto de 400, arredondamento meio-para-longe-do-zero e piso"
```

---

## Task 4: Fator K

**Files:**
- Modify: `calculator/fide/rules.py` (acrescentar ao fim)
- Test: `tests/fide/test_rules_k.py`

**Interfaces:**
- Consumes: constantes da Task 3
- Produces:
  - `is_under_18_at_year_end(birth_year: int, period_year: int) -> bool`
  - `base_k(rating: int | None, games: int, reached_2200: bool, birth_year: int | None, period_year: int) -> int`
  - `halve_for_internal(k: int) -> int`
  - `cap_k_by_games(k: int, games: int) -> int`
  - `parse_birth_year(birthday: str) -> int | None`

- [ ] **Step 1: Escrever o teste**

```python
"""Fator K — §5 da spec."""
import pytest

from calculator.fide import rules


class TestBaseK:
    def test_new_player_gets_40_until_30_games(self):
        assert rules.base_k(1500, 0, False, 1990, 2026) == 40
        assert rules.base_k(1500, 29, False, 1990, 2026) == 40

    def test_after_30_games_drops_to_20(self):
        assert rules.base_k(1500, 30, False, 1990, 2026) == 20

    def test_under_18_keeps_40_below_2100(self):
        """Vale até o fim do ano em que o jogador completa 18."""
        assert rules.base_k(1800, 50, False, 2008, 2026) == 40

    def test_under_18_loses_40_at_or_above_2100(self):
        assert rules.base_k(2100, 50, False, 2008, 2026) == 20

    def test_year_after_turning_18_drops_to_20(self):
        assert rules.base_k(1800, 50, False, 2008, 2027) == 20

    def test_reached_2200_gives_permanent_10(self):
        """K=10 é permanente mesmo depois de o rating cair (§5)."""
        assert rules.base_k(2250, 200, True, 1990, 2026) == 10
        assert rules.base_k(1900, 200, True, 1990, 2026) == 10

    def test_high_rating_without_the_flag_stays_at_20(self):
        """O indicador é que manda, não o rating corrente."""
        assert rules.base_k(2250, 200, False, 1990, 2026) == 20

    def test_missing_birth_year_falls_back_to_the_non_u18_path(self):
        assert rules.base_k(1800, 50, False, None, 2026) == 20


class TestIsUnder18AtYearEnd:
    @pytest.mark.parametrize("birth_year,period_year,expected", [
        (2008, 2026, True),    # completa 18 em 2026 — vale até 31/12
        (2008, 2027, False),
        (2010, 2026, True),
        (1990, 2026, False),
    ])
    def test_boundary_is_the_end_of_the_year(self, birth_year, period_year, expected):
        assert rules.is_under_18_at_year_end(birth_year, period_year) is expected


class TestHalveForInternal:
    @pytest.mark.parametrize("k,expected", [(40, 20), (20, 10), (10, 5)])
    def test_halves_each_k(self, k, expected):
        assert rules.halve_for_internal(k) == expected


class TestCapKByGames:
    def test_no_cap_below_the_limit(self):
        assert rules.cap_k_by_games(40, 17) == 40   # 17 × 40 = 680

    def test_caps_when_product_exceeds_700(self):
        assert rules.cap_k_by_games(40, 18) == 38   # 18 × 38 = 684 <= 700

    def test_exact_limit_is_not_capped(self):
        assert rules.cap_k_by_games(20, 35) == 20   # 35 × 20 = 700

    def test_zero_games_is_a_no_op(self):
        assert rules.cap_k_by_games(40, 0) == 40


class TestParseBirthYear:
    @pytest.mark.parametrize("birthday,expected", [
        ("01/01/1990", 1990),
        ("15/06/2008", 2008),
        ("1990-01-01", 1990),
        ("", None),
        ("nao é data", None),
    ])
    def test_accepts_both_formats(self, birthday, expected):
        assert rules.parse_birth_year(birthday) == expected


def test_order_is_halve_then_cap():
    """§5.1: o teto de 700 é aplicado por último, depois da metade do §2º."""
    k = rules.halve_for_internal(rules.base_k(1500, 0, False, 1990, 2026))
    assert k == 20
    assert rules.cap_k_by_games(k, 40) == 17   # 40 × 17 = 680 <= 700
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_rules_k.py -q --no-cov`
Expected: FAIL com `AttributeError: module 'calculator.fide.rules' has no attribute 'base_k'`

- [ ] **Step 3: Implementar**

Acrescentar ao fim de `calculator/fide/rules.py`:

```python
import re

_BIRTH_YEAR_RE = re.compile(r"(?:^|\D)(\d{4})(?:\D|$)")


def parse_birth_year(birthday: str) -> int | None:
    """Ano de nascimento a partir da coluna `Birthday`.

    Aceita `DD/MM/AAAA` e `AAAA-MM-DD`, os dois formatos que aparecem nos
    arquivos da federação. Devolve `None` quando não há ano reconhecível — a
    validação é que rejeita o campo vazio (§5.3), não esta função.
    """
    if not birthday:
        return None
    match = _BIRTH_YEAR_RE.search(birthday.strip())
    return int(match.group(1)) if match else None


def is_under_18_at_year_end(birth_year: int, period_year: int) -> bool:
    """Verdadeiro até o fim do ano em que o jogador completa 18 anos (§5)."""
    return period_year <= birth_year + 18


def base_k(
    rating: int | None,
    games: int,
    reached_2200: bool,
    birth_year: int | None,
    period_year: int,
) -> int:
    """Fator K da §5, antes da metade do torneio interno e do teto de 700.

    A ordem segue a tabela da §5 de cima para baixo. As duas primeiras
    condições não colidem com `reached_2200`: o rating inicial é limitado a
    2000 (§6.2), então ninguém chega a 2200 com menos de 30 partidas, e o teto
    de 2100 tira o sub-18 da faixa.
    """
    if games < NEW_PLAYER_GAMES:
        return 40
    if (
        birth_year is not None
        and rating is not None
        and rating < U18_RATING_CAP
        and is_under_18_at_year_end(birth_year, period_year)
    ):
        return 40
    if reached_2200:
        return 10
    return 20


def halve_for_internal(k: int) -> int:
    """Art. 68 §2º: em torneio interno o K é reduzido pela metade (40→20, 20→10, 10→5)."""
    return k // 2


def cap_k_by_games(k: int, games: int) -> int:
    """Teto da §5.1: se `games × k > 700`, K vira o maior inteiro com `k × games <= 700`.

    Aplicado por último, depois de qualquer redução do Art. 68 §2º.

    **Ponto em aberto com a FEXERJ** (§5.1 da spec): o teto é definido sobre um
    K único, e a exceção do torneio interno faz o K variar dentro do período.
    A proposta registrada, implementada aqui, é aplicar por torneio, com o K e
    a contagem de partidas daquele torneio. Se a federação decidir diferente,
    esta função e o ponto de chamada em `cycle.py` são os únicos lugares a mudar.
    """
    if games <= 0 or k * games <= K_GAMES_PRODUCT_CAP:
        return k
    return K_GAMES_PRODUCT_CAP // games
```

Mover o `import re` para o topo do arquivo, junto dos outros imports, para o ruff (regra `E402`) não reclamar.

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_rules_k.py -q --no-cov && .venv/bin/ruff check calculator/fide/`
Expected: PASS, sem avisos de lint

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/rules.py tests/fide/test_rules_k.py
git commit -m "feat(fide): fator K com sub-18, torneio interno e teto de 700"
```

---

## Task 5: Rating inicial de não-rated

**Files:**
- Modify: `calculator/fide/rules.py` (acrescentar ao fim)
- Test: `tests/fide/test_rules_initial_rating.py`

**Interfaces:**
- Consumes: `dp_for_score_ratio` da Task 2, constantes da Task 3
- Produces: `initial_rating(opponents_sum: int, opponents_count: int, points: Decimal) -> int | None`

A assinatura recebe soma e contagem, não a lista: o acumulado da §6.1 é guardado
como soma (`SumOpp_`) e contagem (`Games_`), e reconstruir uma lista a partir da
média perderia precisão no arredondamento.

- [ ] **Step 1: Escrever o teste**

```python
"""Rating inicial de jogador não-rated — §6 da spec."""
from decimal import Decimal

from calculator.fide.rules import initial_rating


def test_five_draws_against_1600_lands_on_1600():
    """Cinco empates contra 1600, mais os dois fictícios de 1600, dá p = 0,50 e dp = 0."""
    assert initial_rating(1600 * 5, 5, Decimal("2.5")) == 1600


def test_fictitious_opponents_enter_the_average_and_the_score():
    """Ra e p incluem os dois adversários fictícios de 1600 empatados (§6.2)."""
    # Ra = (5×1800 + 2×1600) / 7 = 12200/7 = 1742,857…
    # p  = (5 + 1) / 7 = 0,857… → 0,86 na tabela → dp = 309 → 2052, limitado a 2000
    assert initial_rating(1800 * 5, 5, Decimal("5")) == 2000


def test_caps_at_2000():
    assert initial_rating(2000 * 5, 5, Decimal("5")) == 2000


def test_returns_none_below_the_floor():
    """Abaixo de 1200 o jogador permanece não-rated (§6.2)."""
    assert initial_rating(1300 * 5, 5, Decimal("0")) is None


def test_uses_the_table_not_the_logistic_formula():
    # Ra = (5×1500 + 2×1600) / 7 = 10700/7 = 1528,571…
    # p  = (3 + 1) / 7 = 0,5714… → 0,57 → dp = 50 → 1578,571… → 1579
    assert initial_rating(1500 * 5, 5, Decimal("3")) == 1579


def test_uses_the_exact_sum_not_a_rounded_average():
    """O acumulado guarda a soma; reconstruir pela média perderia o resto da divisão."""
    # soma = 1500+1501+1502+1503+1504 = 7510 ; Ra = (7510 + 3200) / 7 = 1530,0
    # p = (2,5 + 1) / 7 = 0,50 → dp = 0
    assert initial_rating(7510, 5, Decimal("2.5")) == 1530
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_rules_initial_rating.py -q --no-cov`
Expected: FAIL com `ImportError: cannot import name 'initial_rating'`

- [ ] **Step 3: Implementar**

Acrescentar ao fim de `calculator/fide/rules.py`, com o import de `dp_for_score_ratio` no topo:

```python
def initial_rating(opponents_sum: int, opponents_count: int, points: Decimal) -> int | None:
    """Rating inicial da §6.2, ou `None` quando fica abaixo do piso de 1200.

    `opponents_sum` e `opponents_count` descrevem os adversários **rated**
    enfrentados, e `points` os pontos feitos contra eles. Os dois adversários
    fictícios de 1600, tratados como empate, entram tanto na média quanto no
    percentual de pontos.

    Recebe soma e contagem em vez de uma lista porque é assim que o acumulado
    da §6.1 é guardado entre períodos, e reconstruir a lista a partir da média
    perderia o resto da divisão.
    """
    total_games = opponents_count + 2
    ra = (Decimal(opponents_sum) + 2 * FICTITIOUS_OPPONENT_RATING) / total_games
    p = (points + 1) / total_games
    ru = round_half_away_from_zero(ra + dp_for_score_ratio(p))
    ru = min(ru, INITIAL_RATING_CAP)
    return None if applies_rating_floor(ru) else ru
```

No topo do arquivo, acrescentar aos imports:

```python
from .tables import dp_for_score_ratio
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/ -q --no-cov`
Expected: PASS, toda a suíte de `tests/fide/`

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/rules.py tests/fide/test_rules_initial_rating.py
git commit -m "feat(fide): rating inicial de jogador não-rated"
```

---

## Task 6: Estruturas de dados e leitura/escrita do formato novo

**Files:**
- Create: `calculator/fide/model.py`
- Create: `calculator/fide/ratinglist.py`
- Test: `tests/fide/test_ratinglist.py`

**Interfaces:**
- Consumes: nada das tasks anteriores
- Produces:
  - `model.MODALITIES = ("STD", "RPD", "BLZ")`
  - `model.ModalityState(rating: int | None, games: int, reached_2200: bool, sum_opponents: int, points: Decimal)`
  - `model.PlayerState(id_fexerj, id_cbx, title, name, club, birthday, sex, federation, modalities: dict[str, ModalityState])`
  - `model.Game(tournament_ord: int, modality: str, is_internal: bool, player_id: int, opponent_id: int, score: Decimal)`
  - `ratinglist.FIDE_HEADER`, `ratinglist.LEGACY_HEADER`
  - `ratinglist.read_rating_list(csv_text: str) -> dict[int, PlayerState]`
  - `ratinglist.write_rating_list(players: dict[int, PlayerState]) -> str`

- [ ] **Step 1: Escrever o teste**

```python
"""Leitura e escrita do formato de 23 colunas — §2.1 da spec."""
from decimal import Decimal

import pytest

from calculator.fide.ratinglist import FIDE_HEADER, read_rating_list, write_rating_list

_FIDE_CSV = (
    FIDE_HEADER + "\n"
    "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;"
    "1800;50;0;0;0;"
    ";0;0;0;0;"
    ";0;0;0;0\n"
    "2;36633;;Roberto Faria;CLUB B;15/06/1985;M;BRA;"
    "2250;200;1;0;0;"
    "1900;12;0;0;0;"
    ";0;0;24000;7.5\n"
)


class TestReadFideFormat:
    def test_reads_identity_columns(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].name == "Carlos Mendes"
        assert players[1].birthday == "01/01/1990"
        assert players[2].id_cbx == "36633"

    def test_reads_std_modality(self):
        players = read_rating_list(_FIDE_CSV)
        std = players[1].modalities["STD"]
        assert std.rating == 1800
        assert std.games == 50
        assert std.reached_2200 is False

    def test_empty_rating_means_unrated(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].modalities["RPD"].rating is None
        assert players[1].modalities["BLZ"].rating is None

    def test_reads_peak_flag(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[2].modalities["STD"].reached_2200 is True

    def test_reads_unrated_accumulators(self):
        players = read_rating_list(_FIDE_CSV)
        blz = players[2].modalities["BLZ"]
        assert blz.rating is None
        assert blz.sum_opponents == 24000
        assert blz.points == Decimal("7.5")

    def test_skips_all_blank_rows(self):
        players = read_rating_list(_FIDE_CSV + ";;;;;;;;;;;;;;;;;;;;;;\n")
        assert len(players) == 2

    def test_rejects_unknown_header(self):
        with pytest.raises(ValueError, match="cabeçalho"):
            read_rating_list("Foo;Bar\n1;2\n")


class TestWriteFideFormat:
    def test_round_trip_is_stable(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players) == _FIDE_CSV

    def test_header_is_the_23_column_one(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players).splitlines()[0] == FIDE_HEADER
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_ratinglist.py -q --no-cov`
Expected: FAIL com `ModuleNotFoundError: No module named 'calculator.fide.ratinglist'`

- [ ] **Step 3: Implementar `model.py`**

```python
"""Estruturas de dados do modelo por partida.

`ModalityState` é congelado de propósito: a §4 da spec exige que todo o
período seja calculado contra o estado do início, e o congelamento impede que
um cálculo intermediário vaze para outro por engano.
"""
from dataclasses import dataclass, field
from decimal import Decimal

MODALITIES: tuple[str, ...] = ("STD", "RPD", "BLZ")

# Sufixo das colunas de cada modalidade no players.csv (§2.1 da spec).
COLUMN_SUFFIX: dict[str, str] = {"STD": "Std", "RPD": "Rpd", "BLZ": "Blz"}


@dataclass(frozen=True)
class ModalityState:
    """Rating, contagem e acumuladores de um jogador numa modalidade."""

    rating: int | None = None
    games: int = 0
    reached_2200: bool = False
    sum_opponents: int = 0
    points: Decimal = Decimal("0")

    @property
    def is_rated(self) -> bool:
        return self.rating is not None


@dataclass
class PlayerState:
    """Identidade única do jogador, com uma `ModalityState` por modalidade."""

    id_fexerj: int
    id_cbx: str = ""
    title: str = ""
    name: str = ""
    club: str = ""
    birthday: str = ""
    sex: str = ""
    federation: str = ""
    modalities: dict[str, ModalityState] = field(
        default_factory=lambda: {m: ModalityState() for m in MODALITIES}
    )


@dataclass(frozen=True)
class Game:
    """Uma partida do período, já resolvida para ids FEXERJ."""

    tournament_ord: int
    modality: str
    is_internal: bool
    player_id: int
    opponent_id: int
    score: Decimal
```

- [ ] **Step 4: Implementar `ratinglist.py`**

```python
"""Leitura e escrita da lista de rating.

Aceita dois formatos de entrada: o legado de 12 colunas e o novo de 23 (§2.1
da spec). A escrita é sempre no formato novo.
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
    """Lê a lista de rating no formato de 23 colunas.

    O formato legado de 12 colunas entra na Task 7.
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
    """Escreve a lista no formato de 23 colunas."""
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
    """Inteiro sem casa decimal, fracionário com as casas que tiver."""
    return str(points.to_integral_value()) if points == points.to_integral_value() else str(points)
```

Não defina nenhum stub para o formato legado: nesta task ele simplesmente não é
aceito, e o erro de cabeçalho já cobre esse caso. A Task 7 acrescenta o ramo.

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_ratinglist.py -q --no-cov`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add calculator/fide/model.py calculator/fide/ratinglist.py tests/fide/test_ratinglist.py
git commit -m "feat(fide): estruturas de dados e formato de 23 colunas"
```

---

## Task 7: Conversão do formato legado de 12 colunas

Os três casos da §2.2 da spec. Copiar `Rtg_Nat` direto estaria errado em dois deles.

**Files:**
- Modify: `calculator/fide/ratinglist.py` (`_read_legacy_rows`)
- Test: `tests/fide/test_ratinglist_legacy.py`

**Interfaces:**
- Consumes: `PlayerState`, `ModalityState` da Task 6; `RATING_FLOOR`, `K10_THRESHOLD` da Task 3
- Produces: `read_rating_list` passa a aceitar o cabeçalho legado

- [ ] **Step 1: Escrever o teste**

```python
"""Conversão do formato de 12 colunas — §2.2 da spec."""
from decimal import Decimal

from calculator.fide.ratinglist import LEGACY_HEADER, read_rating_list

_LEGACY_CSV = (
    LEGACY_HEADER + "\n"
    # rated normal
    "1;;;Carlos Mendes;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
    # não-rated hoje: TotalNumGames = 0, mas Rtg_Nat traz um número
    "2;;;Roberto Faria;1500;CLUB B;01/01/1992;M;BRA;0;3200;1.5\n"
    # abaixo do piso novo: o modelo atual tem piso de 1 ponto
    "3;;;Andre Nunes;900;CLUB C;01/01/1988;M;BRA;40;0;0\n"
    # já em 2200 na lista de partida
    "4;36633;;Felipe Borges;2250;CLUB D;01/01/1980;M;BRA;300;0;0\n"
    # faixa temporária de hoje: 1 a 14 partidas, entra como rated
    "5;;;Lucas Carvalho;1450;CLUB E;01/01/1998;M;BRA;8;0;0\n"
)


def _std(player):
    return player.modalities["STD"]


class TestLegacyConversion:
    def test_rated_player_carries_rating_and_games(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[1]).rating == 1800
        assert _std(players[1]).games == 50
        assert _std(players[1]).reached_2200 is False

    def test_zero_games_becomes_unrated_despite_the_rating_column(self):
        """No formato atual quem manda é TotalNumGames = 0, não Rtg_Nat."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).rating is None
        assert _std(players[2]).games == 0

    def test_zero_games_keeps_the_unrated_accumulators(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).sum_opponents == 3200
        assert _std(players[2]).points == Decimal("1.5")

    def test_below_the_floor_becomes_unrated_but_keeps_the_game_count(self):
        """§7 aplicada na conversão: sem isso a lista inicial seria inválida."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[3]).rating is None
        assert _std(players[3]).games == 40

    def test_at_or_above_2200_sets_the_peak_flag(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[4]).reached_2200 is True

    def test_temporary_band_enters_as_rated(self):
        """A §12 aposenta a regra TEMPORARY; não reclassifica quem tem rating publicado."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[5]).rating == 1450
        assert _std(players[5]).games == 8

    def test_rapid_and_blitz_start_empty(self):
        players = read_rating_list(_LEGACY_CSV)
        for modality in ("RPD", "BLZ"):
            state = players[1].modalities[modality]
            assert state.rating is None
            assert state.games == 0
            assert state.reached_2200 is False

    def test_identity_columns_survive_the_conversion(self):
        players = read_rating_list(_LEGACY_CSV)
        assert players[4].id_cbx == "36633"
        assert players[1].birthday == "01/01/1990"
        assert players[1].club == "CLUB A"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_ratinglist_legacy.py -q --no-cov`
Expected: FAIL com `ValueError: players.csv: cabeçalho não reconhecido...`

- [ ] **Step 3: Implementar**

Em `calculator/fide/ratinglist.py`, acrescentar o ramo do formato legado a
`read_rating_list`, logo antes do `raise`:

```python
    if header == LEGACY_HEADER:
        return _read_legacy_rows(rows[1:])
```

E acrescentar a função:

```python
def _read_legacy_rows(rows: list[list[str]]) -> dict[int, PlayerState]:
    """Converte o formato de 12 colunas para o estado interno (§2.2 da spec).

    Três casos distintos no Clássico — copiar `Rtg_Nat` direto erraria em dois:

    - `TotalNumGames = 0`: não-rated hoje. O número em `Rtg_Nat` não vale;
      quem determina é a contagem (ver `complete_players_info` no motor atual).
    - `Rtg_Nat` abaixo do piso: o modelo atual tem piso de 1 ponto e o novo tem
      1200, então a lista de origem pode trazer gente entre 1 e 1199. A §7 é
      aplicada aqui, preservando a contagem de partidas.
    - o resto entra como rated, com o indicador de 2200 saindo do próprio
      rating: a lista de partida é uma lista publicada (§5).

    Rápido e Blitz nascem vazios, o que dispara o transpasse da §1.1 no
    primeiro torneio de cada modalidade.
    """
    players: dict[int, PlayerState] = {}
    for row in rows:
        legacy_rating = int(row[4] or 0)
        games = int(row[9] or 0)
        sum_opponents = int(row[10] or 0)
        points = Decimal(row[11].strip() or "0")

        if games == 0 or applies_rating_floor(legacy_rating):
            std = ModalityState(
                rating=None,
                games=games,
                reached_2200=False,
                sum_opponents=sum_opponents,
                points=points,
            )
        else:
            std = ModalityState(
                rating=legacy_rating,
                games=games,
                reached_2200=legacy_rating >= K10_THRESHOLD,
                sum_opponents=sum_opponents,
                points=points,
            )

        player = PlayerState(
            id_fexerj=int(row[0]),
            id_cbx=row[1].strip(),
            title=row[2],
            name=row[3],
            club=row[5],
            birthday=row[6],
            sex=row[7],
            federation=row[8],
            modalities={"STD": std, "RPD": ModalityState(), "BLZ": ModalityState()},
        )
        players[player.id_fexerj] = player
    return players
```

Acrescentar ao topo do arquivo:

```python
from .rules import K10_THRESHOLD, applies_rating_floor
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/ -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/ratinglist.py tests/fide/test_ratinglist_legacy.py
git commit -m "feat(fide): conversão do formato de 12 colunas com os três casos da §2.2"
```

---

## Task 8: Achatar torneios em partidas

**Files:**
- Create: `calculator/fide/tournaments.py`
- Test: `tests/fide/test_tournaments.py`

**Interfaces:**
- Consumes: `Game` da Task 6; `calculator.tunx_parser.parse_tunx_from_bytes` (motor atual, só leitura)
- Produces:
  - `TournamentRow(ord: int, cr_id: int, name: str, end_date: str, type_: str, is_irt: bool, is_fexerj: bool, modality: str)`
  - `read_tournaments(csv_text: str, first: int, count: int) -> list[TournamentRow]`
  - `collect_games(tournaments, binary_files, players) -> list[Game]`
  - `period_year(tournaments: list[TournamentRow]) -> int`

- [ ] **Step 1: Escrever o teste**

```python
"""Leitura de tournaments.csv e achatamento em partidas."""
import pathlib
from decimal import Decimal

import pytest

from calculator.fide.ratinglist import LEGACY_HEADER, read_rating_list
from calculator.fide.tournaments import (
    TOURNAMENTS_HEADER,
    collect_games,
    period_year,
    read_tournaments,
)

BINARY_DIR = pathlib.Path(__file__).parent.parent / 'binary'

_TOURNAMENTS_CSV = (
    TOURNAMENTS_HEADER + "\n"
    "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
    "2;88888;Torneio Dois;2026-04-20;RR;0;0;RPD\n"
)

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)


class TestReadTournaments:
    def test_reads_the_modality_column(self):
        rows = read_tournaments(_TOURNAMENTS_CSV, 1, 2)
        assert [r.modality for r in rows] == ["STD", "RPD"]

    def test_internal_when_both_flags_are_off(self):
        """§2.1: IsIrt = 0 E IsFexerj = 0 → torneio interno."""
        rows = read_tournaments(_TOURNAMENTS_CSV, 1, 2)
        assert rows[0].is_internal is False
        assert rows[1].is_internal is True

    def test_respects_the_first_count_window(self):
        rows = read_tournaments(_TOURNAMENTS_CSV, 2, 1)
        assert [r.ord for r in rows] == [2]

    def test_rejects_unknown_header(self):
        with pytest.raises(ValueError, match="cabeçalho"):
            read_tournaments("Ord;CrId\n1;2\n", 1, 1)


class TestPeriodYear:
    def test_uses_the_latest_end_date(self):
        rows = read_tournaments(_TOURNAMENTS_CSV, 1, 2)
        assert period_year(rows) == 2026

    def test_raises_when_a_date_is_unusable(self):
        csv_text = TOURNAMENTS_HEADER + "\n1;99999;Torneio;;RR;0;1;STD\n"
        rows = read_tournaments(csv_text, 1, 1)
        with pytest.raises(ValueError, match="EndDate"):
            period_year(rows)


class TestCollectGames:
    def _rows_and_binaries(self):
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        csv_text = TOURNAMENTS_HEADER + "\n1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
        return read_tournaments(csv_text, 1, 1), {"1-99999.TURX": data}

    def test_produces_two_entries_per_game(self):
        """Cada partida aparece uma vez para cada lado, com o placar invertido."""
        rows, binaries = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        pairs = {(g.player_id, g.opponent_id) for g in games}
        for a, b in list(pairs):
            assert (b, a) in pairs

    def test_scores_are_complementary(self):
        rows, binaries = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        by_pair = {(g.player_id, g.opponent_id): g.score for g in games}
        for (a, b), score in by_pair.items():
            assert score + by_pair[(b, a)] == Decimal("1")

    def test_games_carry_modality_and_internal_flag(self):
        rows, binaries = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        assert all(g.modality == "STD" for g in games)
        assert all(g.is_internal is False for g in games)

    def test_missing_binary_raises_with_the_filename(self):
        rows, _ = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        with pytest.raises(ValueError, match="1-99999.TURX"):
            collect_games(rows, {}, players)

    def test_player_absent_from_the_rating_list_raises(self):
        rows, binaries = self._rows_and_binaries()
        with pytest.raises(ValueError, match="lista de rating"):
            collect_games(rows, binaries, {})
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_tournaments.py -q --no-cov`
Expected: FAIL com `ModuleNotFoundError: No module named 'calculator.fide.tournaments'`

- [ ] **Step 3: Implementar**

```python
"""Leitura de tournaments.csv e achatamento dos binários em partidas.

O parser de binários é o mesmo do motor atual (`calculator.tunx_parser`), lido
sem alteração: ele já devolve `(snr_a, snr_b, placar_de_a)`.
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
    """Uma linha de tournaments.csv no formato novo."""

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
        """§2.1: torneio é interno quando as duas flags estão desligadas."""
        return not self.is_irt and not self.is_fexerj

    @property
    def binary_filename(self) -> str:
        return f"{self.ord}-{self.cr_id}.{_TYPE_TO_EXT[self.type_]}"


def read_tournaments(csv_text: str, first: int, count: int) -> list[TournamentRow]:
    """Lê tournaments.csv e devolve as linhas da janela `first`..`first+count-1`."""
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
        selected.append(TournamentRow(
            ord=ord_,
            cr_id=int(row[1]),
            name=row[2],
            end_date=row[3].strip(),
            type_=type_,
            is_irt=row[5].strip() == "1",
            is_fexerj=row[6].strip() == "1",
            modality=modality,
        ))
    return selected


def period_year(tournaments: list[TournamentRow]) -> int:
    """Ano do período, usado pela regra de sub-18 (§5).

    É o ano do `EndDate` mais recente entre os torneios do período. O campo é
    opcional no modelo atual e passa a ser exigido no modelo novo, porque o K
    de sub-18 depende dele.
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
    """Achata os binários do período numa lista de partidas com ids FEXERJ.

    Cada partida entra duas vezes, uma para cada lado, com o placar invertido —
    o cálculo da §3 é por jogador.
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
            games.append(Game(tournament.ord, tournament.modality, tournament.is_internal,
                              id_a, id_b, score))
            games.append(Game(tournament.ord, tournament.modality, tournament.is_internal,
                              id_b, id_a, Decimal("1") - score))
    return games


def _resolve_ids(
    tournament: TournamentRow,
    bio: dict,
    players: dict[int, PlayerState],
) -> dict[int, int]:
    """Mapeia o número de tabuleiro do binário para o id FEXERJ.

    Em torneio IRT o binário traz o id CBX, que é resolvido pela lista de rating.
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
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_tournaments.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/tournaments.py tests/fide/test_tournaments.py
git commit -m "feat(fide): leitura de torneios com modalidade e achatamento em partidas"
```

---

## Task 9: O período — cálculo dos jogadores rated

O coração do modelo. Todas as partidas do período contra o rating do início (§4).

**Files:**
- Create: `calculator/fide/period.py`
- Test: `tests/fide/test_period_rated.py`

**Interfaces:**
- Consumes: `rules`, `tables`, `model`
- Produces:
  - `GameResult(game: Game, opponent_rating: int, capped_diff: int, pd: Decimal, delta: Decimal, k: int)`
  - `PeriodResult(player_id, modality, initial_rating, games_counted, sum_delta, variation, rounded_variation, final_rating, path, game_results)`
  - `compute_rated_period(player_id, modality, state, games, opponent_ratings, period_year, birth_year, internal_by_tournament) -> PeriodResult`

- [ ] **Step 1: Escrever o teste**

```python
"""Cálculo do período para jogador rated — §3, §4 e §5 da spec."""
from decimal import Decimal

from calculator.fide.model import Game, ModalityState
from calculator.fide.period import compute_rated_period


def _game(ord_, opponent_id, score, internal=False):
    return Game(ord_, "STD", internal, 1, opponent_id, Decimal(score))


class TestSingleGame:
    def test_delta_is_result_minus_pd(self):
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1")],
            opponent_ratings={2: 1700},
            period_year=2026, birth_year=1990,
        )
        # D = 100 → PD = 0,64 → ΔR = 1 - 0,64 = 0,36
        assert result.game_results[0].pd == Decimal("0.64")
        assert result.game_results[0].delta == Decimal("0.36")

    def test_opponent_rating_is_capped_before_the_lookup(self):
        state = ModalityState(rating=2400, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1")],
            opponent_ratings={2: 1500},
            period_year=2026, birth_year=1990,
        )
        assert result.game_results[0].capped_diff == 400
        assert result.game_results[0].pd == Decimal("0.92")


class TestPeriodAggregation:
    def test_all_games_use_the_start_of_period_rating(self):
        """§4: o rating não é atualizado entre torneios do mesmo período."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(2, 3, "1")],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        assert all(g.capped_diff == 100 for g in result.game_results)

    def test_rounds_once_at_the_end(self):
        """§3 passo 5: um único arredondamento por período."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0")],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        # ΣΔR = 0,36 + (-0,64) = -0,28 ; K = 20 → -5,6 → -6
        assert result.sum_delta == Decimal("-0.28")
        assert result.rounded_variation == -6
        assert result.final_rating == 1794

    def test_games_against_unrated_opponents_are_skipped(self):
        """§3: partidas contra não-rated não entram no cálculo do rated."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "1")],
            opponent_ratings={2: 1700},   # jogador 3 sem rating
            period_year=2026, birth_year=1990,
        )
        assert result.games_counted == 1


class TestKWithinThePeriod:
    def test_internal_tournament_uses_half_k(self):
        """§5.2: o torneio interno é a exceção à regra de K constante."""
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(2, 3, "1", internal=True)],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        by_tournament = {g.game.tournament_ord: g.k for g in result.game_results}
        assert by_tournament[1] == 20
        assert by_tournament[2] == 10

    def test_variation_sums_delta_times_k_per_game(self):
        state = ModalityState(rating=1800, games=50)
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=[_game(1, 2, "1"), _game(2, 3, "1", internal=True)],
            opponent_ratings={2: 1700, 3: 1700},
            period_year=2026, birth_year=1990,
        )
        # 0,36 × 20 + 0,36 × 10 = 7,2 + 3,6 = 10,8 → 11
        assert result.variation == Decimal("10.8")
        assert result.rounded_variation == 11


class TestFloor:
    def test_dropping_below_1200_clears_the_rating(self):
        """§7: rating zerado, contagem preservada."""
        state = ModalityState(rating=1205, games=50)
        games = [_game(1, i, "0") for i in range(2, 12)]
        result = compute_rated_period(
            player_id=1, modality="STD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 12)},
            period_year=2026, birth_year=1990,
        )
        assert result.final_rating is None
        assert result.games_counted == 10
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_period_rated.py -q --no-cov`
Expected: FAIL com `ModuleNotFoundError: No module named 'calculator.fide.period'`

- [ ] **Step 3: Implementar**

```python
"""Cálculo do período para um jogador numa modalidade.

Todas as partidas do período são calculadas contra o rating do início (§4), o
que inclui o rating dos adversários. Nada aqui lê estado atualizado.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from . import rules
from .model import Game, ModalityState
from .tables import pd_for_diff


@dataclass(frozen=True)
class GameResult:
    """Uma partida computada, com tudo que a auditoria por partida precisa."""

    game: Game
    opponent_rating: int
    capped_diff: int
    pd: Decimal
    delta: Decimal
    k: int


@dataclass
class PeriodResult:
    """O fechamento do período para um jogador numa modalidade.

    `accumulated_sum_opponents` e `accumulated_points` só têm uso no caminho do
    não-rated (§6.1): são o acumulado que segue para o próximo período enquanto
    o jogador não chega às cinco partidas.
    """

    player_id: int
    modality: str
    initial_rating: int | None
    games_counted: int
    sum_delta: Decimal
    variation: Decimal
    rounded_variation: int
    final_rating: int | None
    path: str
    game_results: list[GameResult] = field(default_factory=list)
    accumulated_sum_opponents: int = 0
    accumulated_points: Decimal = Decimal("0")


def compute_rated_period(
    player_id: int,
    modality: str,
    state: ModalityState,
    games: list[Game],
    opponent_ratings: dict[int, int],
    period_year: int,
    birth_year: int | None,
    path: str = "RATED",
) -> PeriodResult:
    """Fecha o período de um jogador rated.

    `opponent_ratings` traz apenas adversários **rated** no início do período;
    partidas contra quem não está no mapa são descartadas (§3).

    O K sai da §5 uma vez para o período, e é reduzido pela metade nas partidas
    de torneio interno (§5.2). O teto de 700 é aplicado por torneio, com o K e a
    contagem daquele torneio, conforme a proposta da §5.1 — ponto ainda aberto
    com a FEXERJ.
    """
    assert state.rating is not None, "compute_rated_period exige rating no início do período"
    initial_rating = state.rating

    period_k = rules.base_k(
        rating=initial_rating,
        games=state.games,
        reached_2200=state.reached_2200,
        birth_year=birth_year,
        period_year=period_year,
    )

    counted = [g for g in games if g.opponent_id in opponent_ratings]
    k_by_tournament = _k_by_tournament(counted, period_k)

    results: list[GameResult] = []
    for game in counted:
        opponent_rating = opponent_ratings[game.opponent_id]
        diff = rules.capped_diff(initial_rating, opponent_rating)
        pd = pd_for_diff(diff)
        results.append(GameResult(
            game=game,
            opponent_rating=opponent_rating,
            capped_diff=diff,
            pd=pd,
            delta=game.score - pd,
            k=k_by_tournament[game.tournament_ord],
        ))

    sum_delta = sum((r.delta for r in results), Decimal("0"))
    variation = sum((r.delta * r.k for r in results), Decimal("0"))
    rounded = rules.round_half_away_from_zero(variation)
    final_rating: int | None = initial_rating + rounded
    if rules.applies_rating_floor(final_rating):
        final_rating = None

    return PeriodResult(
        player_id=player_id,
        modality=modality,
        initial_rating=initial_rating,
        games_counted=len(results),
        sum_delta=sum_delta,
        variation=variation,
        rounded_variation=rounded,
        final_rating=final_rating,
        path=path,
        game_results=results,
    )


def _k_by_tournament(games: list[Game], period_k: int) -> dict[int, int]:
    """K efetivo de cada torneio: metade se interno, depois o teto de 700."""
    games_per_tournament: dict[int, int] = {}
    internal: dict[int, bool] = {}
    for game in games:
        games_per_tournament[game.tournament_ord] = games_per_tournament.get(game.tournament_ord, 0) + 1
        internal[game.tournament_ord] = game.is_internal

    effective: dict[int, int] = {}
    for ord_, count in games_per_tournament.items():
        k = rules.halve_for_internal(period_k) if internal[ord_] else period_k
        effective[ord_] = rules.cap_k_by_games(k, count)
    return effective
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_period_rated.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/period.py tests/fide/test_period_rated.py
git commit -m "feat(fide): cálculo do período para jogador rated"
```

---

## Task 10: Conferência ponta a ponta contra números publicados pela FIDE

A fixture **já existe** em `tests/fide/fixtures/fide_official_period.csv`, com as 13 partidas transcritas da página de cálculos individuais da FIDE (lista Clássico de agosto de 2026, um jogador, dois torneios). Esta task escreve o teste que a consome.

O valor dela não é provar que o modelo está certo — as três partidas que a §10 da spec documenta já estão testadas na Task 2. É provar que a **aritmética do período** reproduz números que a FIDE publicou: somar os ΔR, multiplicar pelo K e arredondar **uma vez só**, conforme o 8.3.4.

**Files:**
- Test: `tests/fide/test_fide_official_anchor.py`

**Interfaces:**
- Consumes: `compute_rated_period` da Task 9
- Produces: nada. É a prova de correção que não depende da nossa leitura da spec.

- [ ] **Step 1: Ler a fixture já existente**

`tests/fide/fixtures/fide_official_period.csv` traz, em comentários `#`, `initial_rating = 2373`, `k = 10`, `published_period_change = 19.60` e `published_tournament_changes = 11.40, 8.20`; depois o cabeçalho `opponent_rating;score;expected_delta` e as 13 linhas.

Os ratings de adversário estão como a FIDE exibe — **já limitados** a 400 de diferença. Não aplique o teto de novo em cima deles ao montar o teste; passe-os direto como rating do adversário e deixe `capped_diff` fazer o trabalho, que nesses casos é inócuo.

- [ ] **Step 2: Escrever o teste**

```python
"""Âncora de correção: a consulta oficial da FIDE citada na §10 da spec.

Se este teste passa, o núcleo do cálculo está certo, e a prova não depende da
nossa leitura da especificação — vem da própria FIDE.
"""
import pathlib
from decimal import Decimal

import pytest

from calculator.fide.model import Game, ModalityState
from calculator.fide.period import compute_rated_period

FIXTURE = pathlib.Path(__file__).parent / 'fixtures' / 'fide_official_period.csv'

EXPECTED_TOTAL_VARIATION = Decimal("19.60")


def _load():
    """Return (initial_rating, k, [(opponent_rating, score, expected_delta), ...])."""
    meta: dict[str, str] = {}
    rows = []
    for line in FIXTURE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            if '=' in line:
                key, _, value = line.lstrip('# ').partition('=')
                meta[key.strip()] = value.strip()
            continue
        if line.startswith('opponent_rating'):
            continue
        opponent, score, delta = line.split(';')
        rows.append((int(opponent), Decimal(score), Decimal(delta)))
    return int(meta['initial_rating']), int(meta['k']), rows


def test_fixture_has_the_thirteen_games():
    _, _, rows = _load()
    assert len(rows) == 13


@pytest.mark.parametrize("index", range(13))
def test_each_game_matches_the_official_delta(index):
    initial_rating, k, rows = _load()
    opponent_rating, score, expected_delta = rows[index]
    state = ModalityState(rating=initial_rating, games=100)
    result = compute_rated_period(
        player_id=1, modality="STD", state=state,
        games=[Game(1, "STD", False, 1, 2, score)],
        opponent_ratings={2: opponent_rating},
        period_year=2026, birth_year=1970,
    )
    assert result.game_results[0].delta == expected_delta


def test_period_total_matches_the_published_variation():
    initial_rating, k, rows = _load()
    state = ModalityState(rating=initial_rating, games=100)
    games = [Game(1, "STD", False, 1, 100 + i, score) for i, (_, score, _) in enumerate(rows)]
    opponent_ratings = {100 + i: opponent for i, (opponent, _, _) in enumerate(rows)}
    result = compute_rated_period(
        player_id=1, modality="STD", state=state,
        games=games, opponent_ratings=opponent_ratings,
        period_year=2026, birth_year=1970,
    )
    assert result.variation == EXPECTED_TOTAL_VARIATION
    assert result.game_results[0].k == k
```

- [ ] **Step 3: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_fide_official_anchor.py -q --no-cov`
Expected: PASS, 15 passed

Se falhar, **não ajuste o motor para caber na fixture antes de conferir a fixture**: a divergência pode estar na transcrição. Compare partida a partida contra a página de cálculo da FIDE.

- [ ] **Step 4: Commit**

```bash
git add tests/fide/fixtures/ tests/fide/test_fide_official_anchor.py
git commit -m "test(fide): âncora de correção contra a consulta oficial da FIDE"
```

---

## Task 11: Transpasse entre modalidades e caminho do não-rated

**Files:**
- Modify: `calculator/fide/period.py` (acrescentar)
- Test: `tests/fide/test_period_unrated.py`

**Interfaces:**
- Consumes: `compute_rated_period`, `rules.initial_rating`
- Produces:
  - `transposed_state(player, modality) -> ModalityState | None`
  - `compute_unrated_period(player_id, modality, state, games, opponent_ratings) -> PeriodResult`

- [ ] **Step 1: Escrever o teste**

```python
"""Transpasse (§1.1) e rating inicial no período (§6)."""
from decimal import Decimal

from calculator.fide.model import Game, ModalityState, PlayerState
from calculator.fide.period import compute_unrated_period, transposed_state


def _game(ord_, opponent_id, score):
    return Game(ord_, "RPD", False, 1, opponent_id, Decimal(score))


class TestTransposedState:
    def test_uses_the_std_rating_with_zero_games(self):
        """§1.1: entra com o rating STD; o K sai da contagem da modalidade nova."""
        player = PlayerState(id_fexerj=1, name="Carlos Mendes")
        player.modalities["STD"] = ModalityState(rating=1800, games=120, reached_2200=False)
        state = transposed_state(player, "RPD")
        assert state is not None
        assert state.rating == 1800
        assert state.games == 0

    def test_peak_flag_does_not_carry_over(self):
        """Contagens e indicadores são independentes por modalidade (§1.1)."""
        player = PlayerState(id_fexerj=1, name="Roberto Faria")
        player.modalities["STD"] = ModalityState(rating=2250, games=300, reached_2200=True)
        state = transposed_state(player, "RPD")
        assert state.reached_2200 is False

    def test_returns_none_when_the_modality_already_has_a_rating(self):
        player = PlayerState(id_fexerj=1, name="Andre Nunes")
        player.modalities["STD"] = ModalityState(rating=1800, games=120)
        player.modalities["RPD"] = ModalityState(rating=1700, games=20)
        assert transposed_state(player, "RPD") is None

    def test_returns_none_without_a_std_rating(self):
        player = PlayerState(id_fexerj=1, name="Felipe Borges")
        assert transposed_state(player, "RPD") is None

    def test_std_never_transposes_from_itself(self):
        player = PlayerState(id_fexerj=1, name="Lucas Carvalho")
        player.modalities["STD"] = ModalityState(rating=1800, games=120)
        assert transposed_state(player, "STD") is None


class TestUnratedPeriod:
    def test_below_five_games_accumulates_without_a_rating(self):
        """§6.1: nada é publicado antes de 5 partidas contra rated."""
        state = ModalityState()
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0")],
            opponent_ratings={2: 1600, 3: 1600},
        )
        assert result.final_rating is None
        assert result.path == "ACUMULANDO"
        assert result.games_counted == 2

    def test_accumulator_advances_so_the_next_period_can_reach_five(self):
        """Sem isso o jogador conta partidas mas nunca acumula adversário e ponto."""
        state = ModalityState(games=1, sum_opponents=1600, points=Decimal("0.5"))
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, 2, "1"), _game(1, 3, "0")],
            opponent_ratings={2: 1700, 3: 1500},
        )
        assert result.accumulated_sum_opponents == 1600 + 1700 + 1500
        assert result.accumulated_points == Decimal("1.5")

    def test_a_discarded_first_event_does_not_advance_the_accumulator(self):
        state = ModalityState()
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=[_game(1, i, "0") for i in range(2, 8)],
            opponent_ratings={i: 1600 for i in range(2, 8)},
        )
        assert result.accumulated_sum_opponents == 0
        assert result.accumulated_points == Decimal("0")

    def test_five_games_produce_an_initial_rating(self):
        state = ModalityState()
        games = [_game(1, i, "0.5") for i in range(2, 7)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 7)},
        )
        assert result.final_rating == 1600
        assert result.path == "RATING_INICIAL"

    def test_accumulated_history_counts_toward_the_five(self):
        state = ModalityState(games=3, sum_opponents=4800, points=Decimal("1.5"))
        games = [_game(1, i, "0.5") for i in range(2, 4)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={2: 1600, 3: 1600},
        )
        assert result.final_rating == 1600

    def test_a_zeroed_first_event_is_discarded(self):
        """§6.1 / 8.2.1: zerar o primeiro evento descarta o resultado."""
        state = ModalityState()
        games = [_game(1, i, "0") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 8)},
        )
        assert result.final_rating is None
        assert result.path == "PRIMEIRO_EVENTO_ZERADO"
        assert result.games_counted == 0

    def test_a_zeroed_later_event_is_not_discarded(self):
        state = ModalityState(games=4, sum_opponents=6400, points=Decimal("2"))
        games = [_game(1, i, "0") for i in range(2, 8)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1600 for i in range(2, 8)},
        )
        assert result.path == "RATING_INICIAL"

    def test_below_the_floor_stays_unrated(self):
        state = ModalityState()
        games = [_game(1, i, "0.5") for i in range(2, 7)]
        result = compute_unrated_period(
            player_id=1, modality="RPD", state=state,
            games=games,
            opponent_ratings={i: 1000 for i in range(2, 7)},
        )
        assert result.final_rating is None
        assert result.path == "ABAIXO_DO_PISO"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_period_unrated.py -q --no-cov`
Expected: FAIL com `ImportError: cannot import name 'compute_unrated_period'`

- [ ] **Step 3: Implementar**

Acrescentar a `calculator/fide/period.py`:

```python
def transposed_state(player: PlayerState, modality: str) -> ModalityState | None:
    """Estado de entrada de um jogador transposto (§1.1), ou `None` se não se aplica.

    Jogador sem rating na modalidade mas com rating STD entra com o rating STD
    e é tratado como rated — inclusive para os adversários dele, porque o
    cálculo dos adversários faz parte do cálculo daquela modalidade.

    O K sai da contagem da modalidade nova, que é zero: K = 40. Contagens e o
    indicador de 2200 são independentes por modalidade e não vêm junto.
    """
    if modality == "STD":
        return None
    if player.modalities[modality].is_rated:
        return None
    std = player.modalities["STD"]
    if not std.is_rated:
        return None
    return ModalityState(rating=std.rating, games=0, reached_2200=False)


def compute_unrated_period(
    player_id: int,
    modality: str,
    state: ModalityState,
    games: list[Game],
    opponent_ratings: dict[int, int],
) -> PeriodResult:
    """Fecha o período de um jogador sem rating (§6).

    Acumula partidas contra adversários rated. Ao alcançar cinco no total
    acumulado, calcula o rating inicial. Zerar o primeiro evento descarta o
    resultado (§6.1).
    """
    counted = [g for g in games if g.opponent_id in opponent_ratings]
    points = sum((g.score for g in counted), Decimal("0"))

    is_first_event = state.games == 0
    if is_first_event and counted and points == 0:
        # §6.1 / 8.2.1: o resultado é descartado — o acumulado não avança.
        return PeriodResult(
            player_id=player_id, modality=modality, initial_rating=None,
            games_counted=0, sum_delta=Decimal("0"), variation=Decimal("0"),
            rounded_variation=0, final_rating=None, path="PRIMEIRO_EVENTO_ZERADO",
            accumulated_sum_opponents=state.sum_opponents,
            accumulated_points=state.points,
        )

    total_games = state.games + len(counted)
    total_points = state.points + points
    total_sum_opponents = state.sum_opponents + sum(
        opponent_ratings[g.opponent_id] for g in counted
    )

    if total_games < rules.MIN_GAMES_FOR_FIRST_RATING:
        return PeriodResult(
            player_id=player_id, modality=modality, initial_rating=None,
            games_counted=len(counted), sum_delta=Decimal("0"), variation=Decimal("0"),
            rounded_variation=0, final_rating=None, path="ACUMULANDO",
            accumulated_sum_opponents=total_sum_opponents,
            accumulated_points=total_points,
        )

    ru = rules.initial_rating(total_sum_opponents, total_games, total_points)
    return PeriodResult(
        player_id=player_id, modality=modality, initial_rating=None,
        games_counted=len(counted), sum_delta=Decimal("0"), variation=Decimal("0"),
        rounded_variation=0, final_rating=ru,
        path="RATING_INICIAL" if ru is not None else "ABAIXO_DO_PISO",
        accumulated_sum_opponents=total_sum_opponents,
        accumulated_points=total_points,
    )
```

Acrescentar `PlayerState` ao import de `.model` no topo do arquivo.

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/ -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/period.py tests/fide/test_period_unrated.py
git commit -m "feat(fide): transpasse entre modalidades e rating inicial no período"
```

---

## Task 12: O ciclo completo

**Files:**
- Create: `calculator/fide/cycle.py`
- Modify: `calculator/fide/__init__.py` (exportar `FideRatingCycle`)
- Test: `tests/fide/test_cycle.py`

**Interfaces:**
- Consumes: tudo das tasks 2–11
- Produces: `FideRatingCycle(tournaments_csv, first_item, items_to_process, initial_rating_csv, binary_files)` com `run_cycle() -> dict[str, str]` e `run_period() -> PeriodOutcome`

- [ ] **Step 1: Escrever o teste**

```python
"""O ciclo completo do modelo por partida."""
import pathlib

from calculator.fide import FideRatingCycle
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

BINARY_DIR = pathlib.Path(__file__).parent.parent / 'binary'

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)


def _cycle(tournaments_csv, first=1, count=1, binaries=None):
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return FideRatingCycle(
        tournaments_csv=tournaments_csv,
        first_item=first,
        items_to_process=count,
        initial_rating_csv=_PLAYERS_CSV,
        binary_files=binaries if binaries is not None else {"1-99999.TURX": data},
    )


_ONE_TOURNAMENT = (
    TOURNAMENTS_HEADER + "\n"
    "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
)


class TestOutputShape:
    def test_produces_a_single_rating_list(self):
        """Os dois arquivos de auditoria entram na Task 13."""
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert "RatingList.csv" in output

    def test_no_per_tournament_rating_list(self):
        """§4: lista intermediária por torneio não é resultado válido."""
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert not any(name.startswith("RatingList_after_") for name in output)

    def test_rating_list_uses_the_new_header(self):
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert output["RatingList.csv"].splitlines()[0] == FIDE_HEADER

    def test_every_player_survives_the_cycle(self):
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        lines = [row for row in output["RatingList.csv"].splitlines() if row]
        assert len(lines) == 7  # cabeçalho + 6 jogadores


class TestPeriodSemantics:
    def test_two_tournaments_together_differ_from_two_runs(self):
        """A diferença estrutural entre os modelos: o período é um só arredondamento."""
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        two = (
            TOURNAMENTS_HEADER + "\n"
            "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
            "2;99999;Torneio Dois;2026-04-20;RR;0;1;STD\n"
        )
        binaries = {"1-99999.TURX": data, "2-99999.TURX": data}
        together = _cycle(two, 1, 2, binaries).run_cycle()["RatingList.csv"]

        first = _cycle(two, 1, 1, binaries).run_cycle()["RatingList.csv"]
        second = FideRatingCycle(
            tournaments_csv=two, first_item=2, items_to_process=1,
            initial_rating_csv=first, binary_files=binaries,
        ).run_cycle()["RatingList.csv"]

        assert together != second

    def test_all_games_use_the_start_of_period_opponent_rating(self):
        """§4: o rating do adversário também é o do início do período."""
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        two = (
            TOURNAMENTS_HEADER + "\n"
            "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
            "2;99999;Torneio Dois;2026-04-20;RR;0;1;STD\n"
        )
        binaries = {"1-99999.TURX": data, "2-99999.TURX": data}
        outcome = _cycle(two, 1, 2, binaries).run_period()
        by_pair = {}
        for result in outcome.results:
            for entry in result.game_results:
                key = (result.player_id, entry.game.opponent_id)
                by_pair.setdefault(key, set()).add(entry.opponent_rating)
        # a mesma dupla joga nos dois torneios; o rating do adversário não muda
        assert all(len(values) == 1 for values in by_pair.values())


class TestModalities:
    def test_rapid_tournament_writes_the_rapid_columns(self):
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        rapid = TOURNAMENTS_HEADER + "\n1;99999;Torneio Rápido;2026-03-15;RR;0;1;RPD\n"
        output = _cycle(rapid, binaries={"1-99999.TURX": data}).run_cycle()
        header = output["RatingList.csv"].splitlines()[0].split(';')
        row = output["RatingList.csv"].splitlines()[1].split(';')
        assert row[header.index("Rtg_Rpd")] != ""
        assert row[header.index("Rtg_Std")] == "1800"   # Clássico intocado
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_cycle.py -q --no-cov`
Expected: FAIL com `ImportError: cannot import name 'FideRatingCycle'`

- [ ] **Step 3: Implementar**

```python
"""O ciclo do modelo por partida: entra CSV e binários, sai CSV.

Mesma forma de uso do motor atual (`FexerjRatingCycle`), para o backend poder
tratar os dois do mesmo jeito.
"""
import copy
from dataclasses import dataclass, field
from decimal import Decimal

from .model import Game, ModalityState, PlayerState
from .period import (
    PeriodResult,
    compute_rated_period,
    compute_unrated_period,
    transposed_state,
)
from .ratinglist import read_rating_list, write_rating_list
from .rules import K10_THRESHOLD, parse_birth_year
from .tournaments import TournamentRow, collect_games, period_year, read_tournaments

# Caminhos em que o jogador termina o período ainda sem rating publicado e o
# acumulado da §6.1 precisa sobreviver para o período seguinte.
_STILL_UNRATED_PATHS = frozenset({"ACUMULANDO", "PRIMEIRO_EVENTO_ZERADO"})


@dataclass
class PeriodOutcome:
    """Resultado bruto do período, antes de virar CSV."""

    players: dict[int, PlayerState]
    tournaments: list[TournamentRow] = field(default_factory=list)
    results: list[PeriodResult] = field(default_factory=list)


class FideRatingCycle:
    """Executa um período no modelo por partida."""

    def __init__(
        self,
        tournaments_csv: str,
        first_item: int,
        items_to_process: int,
        initial_rating_csv: str,
        binary_files: dict[str, bytes],
    ):
        self.tournaments_csv = tournaments_csv
        self.first_item = first_item
        self.items_to_process = items_to_process
        self.initial_rating_csv = initial_rating_csv
        self.binary_files = binary_files

    def run_period(self) -> PeriodOutcome:
        """Calcula o período e devolve o resultado estruturado."""
        initial_players = read_rating_list(self.initial_rating_csv)
        tournaments = read_tournaments(
            self.tournaments_csv, self.first_item, self.items_to_process
        )
        if not tournaments:
            return PeriodOutcome(players=initial_players)

        year = period_year(tournaments)
        games = collect_games(tournaments, self.binary_files, initial_players)

        # §4: o estado do início do período é congelado; nada aqui o modifica.
        entry_states = _entry_states(initial_players, games)
        opponent_ratings = _opponent_ratings_by_modality(entry_states)

        results: list[PeriodResult] = []
        for (player_id, modality), state in sorted(entry_states.items()):
            player_games = [
                g for g in games if g.player_id == player_id and g.modality == modality
            ]
            if not player_games:
                continue
            ratings = opponent_ratings[modality]
            if state.is_rated:
                results.append(compute_rated_period(
                    player_id=player_id,
                    modality=modality,
                    state=state,
                    games=player_games,
                    opponent_ratings=ratings,
                    period_year=year,
                    birth_year=parse_birth_year(initial_players[player_id].birthday),
                    path=_path_for(initial_players[player_id], modality),
                ))
            else:
                results.append(compute_unrated_period(
                    player_id=player_id,
                    modality=modality,
                    state=state,
                    games=player_games,
                    opponent_ratings=ratings,
                ))

        final_players = _apply_results(initial_players, results)
        return PeriodOutcome(players=final_players, tournaments=tournaments, results=results)

    def run_cycle(self) -> dict[str, str]:
        """Devolve `{nome_do_arquivo: conteúdo CSV}` para o período.

        Os dois arquivos de auditoria entram na Task 13.
        """
        outcome = self.run_period()
        return {"RatingList.csv": write_rating_list(outcome.players)}


def _entry_states(
    players: dict[int, PlayerState], games: list[Game]
) -> dict[tuple[int, str], ModalityState]:
    """Estado de entrada de cada par (jogador, modalidade) que jogou no período."""
    states: dict[tuple[int, str], ModalityState] = {}
    for game in games:
        key = (game.player_id, game.modality)
        if key in states:
            continue
        player = players[game.player_id]
        transposed = transposed_state(player, game.modality)
        states[key] = transposed if transposed is not None else player.modalities[game.modality]
    return states


def _opponent_ratings_by_modality(
    entry_states: dict[tuple[int, str], ModalityState],
) -> dict[str, dict[int, int]]:
    """Ratings de entrada dos adversários rated, por modalidade.

    O transposto entra aqui: a §1.1 o trata como rated, e o cálculo dos
    adversários dele faz parte do cálculo daquela modalidade.
    """
    by_modality: dict[str, dict[int, int]] = {}
    for (player_id, modality), state in entry_states.items():
        if state.is_rated:
            by_modality.setdefault(modality, {})[player_id] = state.rating
    return by_modality


def _path_for(player: PlayerState, modality: str) -> str:
    return "TRANSPOSTO" if not player.modalities[modality].is_rated else "RATED"


def _apply_results(
    initial_players: dict[int, PlayerState],
    results: list[PeriodResult],
) -> dict[int, PlayerState]:
    """Aplica os resultados sobre uma cópia do estado inicial.

    O estado inicial em si nunca é modificado: a §4 exige que todo o período
    seja calculado contra ele.
    """
    final = copy.deepcopy(initial_players)
    for result in results:
        player = final[result.player_id]
        before = player.modalities[result.modality]
        games = before.games + result.games_counted

        if result.final_rating is None and result.path in _STILL_UNRATED_PATHS:
            # Segue não-rated: o acumulado da §6.1 avança para o próximo período.
            player.modalities[result.modality] = ModalityState(
                rating=None,
                games=games,
                reached_2200=before.reached_2200,
                sum_opponents=result.accumulated_sum_opponents,
                points=result.accumulated_points,
            )
            continue

        # Ganhou rating, manteve, ou caiu abaixo do piso (§7): o acúmulo de
        # não-rated deixa de valer e é zerado. A contagem de partidas fica.
        player.modalities[result.modality] = ModalityState(
            rating=result.final_rating,
            games=games,
            reached_2200=before.reached_2200 or (
                result.final_rating is not None and result.final_rating >= K10_THRESHOLD
            ),
            sum_opponents=0,
            points=Decimal("0"),
        )
    return final
```

Atualizar `calculator/fide/__init__.py`:

```python
from .cycle import FideRatingCycle

__all__ = ["FideRatingCycle"]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/fide/test_cycle.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add calculator/fide/cycle.py calculator/fide/__init__.py tests/fide/test_cycle.py
git commit -m "feat(fide): ciclo do período com três modalidades"
```

---

## Task 13: Arquivos de auditoria

**Files:**
- Create: `calculator/fide/audit.py`
- Modify: `calculator/fide/cycle.py` (`run_cycle` passa a emitir os três arquivos)
- Modify: `tests/fide/test_cycle.py` (`test_produces_a_single_rating_list` vira a asserção completa)
- Modify: `pyproject.toml` (cobertura passa a incluir `calculator/fide`)
- Test: `tests/fide/test_audit.py`

**Interfaces:**
- Consumes: `PeriodOutcome` da Task 12
- Produces:
  - `GAMES_AUDIT_PREAMBLE = "# fide_games_v1"`, `PERIOD_AUDIT_PREAMBLE = "# fide_period_v1"`
  - `GAMES_AUDIT_HEADER`, `PERIOD_AUDIT_HEADER`
  - `write_games_audit(outcome) -> str`, `write_period_audit(outcome) -> str`

- [ ] **Step 1: Escrever o teste**

```python
"""Auditoria por partida e por período."""
import pathlib

from calculator.fide import FideRatingCycle
from calculator.fide.audit import (
    GAMES_AUDIT_HEADER,
    GAMES_AUDIT_PREAMBLE,
    PERIOD_AUDIT_HEADER,
    PERIOD_AUDIT_PREAMBLE,
)
from calculator.fide.ratinglist import LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

BINARY_DIR = pathlib.Path(__file__).parent.parent / 'binary'

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

_TOURNAMENTS = TOURNAMENTS_HEADER + "\n1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"


def _output():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return FideRatingCycle(_TOURNAMENTS, 1, 1, _PLAYERS_CSV, {"1-99999.TURX": data}).run_cycle()


class TestGamesAudit:
    def test_preamble_and_header(self):
        lines = _output()["Audit_Games.csv"].splitlines()
        assert lines[0] == GAMES_AUDIT_PREAMBLE
        assert lines[1] == GAMES_AUDIT_HEADER

    def test_one_row_per_computed_game_side(self):
        """Round-robin de 6: 15 partidas, 30 lados."""
        lines = [r for r in _output()["Audit_Games.csv"].splitlines()[2:] if r]
        assert len(lines) == 30

    def test_row_lets_a_player_redo_the_math(self):
        """Rating do adversário já limitado, D, PD, resultado e ΔR na mesma linha."""
        header = GAMES_AUDIT_HEADER.split(';')
        row = _output()["Audit_Games.csv"].splitlines()[2].split(';')
        cells = dict(zip(header, row, strict=True))
        from decimal import Decimal
        assert Decimal(cells["Score"]) - Decimal(cells["PD"]) == Decimal(cells["DeltaR"])


class TestPeriodAudit:
    def test_preamble_and_header(self):
        lines = _output()["Audit_Period.csv"].splitlines()
        assert lines[0] == PERIOD_AUDIT_PREAMBLE
        assert lines[1] == PERIOD_AUDIT_HEADER

    def test_one_row_per_player_and_modality(self):
        lines = [r for r in _output()["Audit_Period.csv"].splitlines()[2:] if r]
        assert len(lines) == 6

    def test_names_the_tournaments_of_the_period(self):
        """A lista gerada não pode ficar órfã do recorte que a produziu."""
        header = PERIOD_AUDIT_HEADER.split(';')
        row = _output()["Audit_Period.csv"].splitlines()[2].split(';')
        cells = dict(zip(header, row, strict=True))
        assert cells["Tournaments"] == "1"

    def test_rounded_variation_explains_the_new_rating(self):
        """Rating final = rating inicial + variação arredondada, salvo quem caiu do piso."""
        header = PERIOD_AUDIT_HEADER.split(';')
        for line in _output()["Audit_Period.csv"].splitlines()[2:]:
            if not line:
                continue
            cells = dict(zip(header, line.split(';'), strict=True))
            if not cells["InitialRating"] or not cells["FinalRating"]:
                continue
            assert int(cells["FinalRating"]) - int(cells["InitialRating"]) == int(
                cells["RoundedVariation"]
            )

    def test_period_audit_agrees_with_the_games_audit(self):
        """A soma de ΔR × K das partidas do jogador tem de dar a variação do período."""
        from decimal import Decimal
        output = _output()
        games_header = GAMES_AUDIT_HEADER.split(';')
        totals: dict[tuple[str, str], Decimal] = {}
        for line in output["Audit_Games.csv"].splitlines()[2:]:
            if not line:
                continue
            c = dict(zip(games_header, line.split(';'), strict=True))
            key = (c["PlayerId"], c["TimeControl"])
            totals[key] = totals.get(key, Decimal("0")) + Decimal(c["DeltaR"]) * Decimal(c["K"])

        period_header = PERIOD_AUDIT_HEADER.split(';')
        for line in output["Audit_Period.csv"].splitlines()[2:]:
            if not line:
                continue
            c = dict(zip(period_header, line.split(';'), strict=True))
            key = (c["PlayerId"], c["TimeControl"])
            assert Decimal(c["Variation"]) == totals.get(key, Decimal("0"))
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/fide/test_audit.py -q --no-cov`
Expected: FAIL com `ModuleNotFoundError: No module named 'calculator.fide.audit'`

- [ ] **Step 3: Implementar**

```python
"""Arquivos de auditoria do modelo por partida.

`Audit_Games.csv` existe para que um jogador refaça a própria conta, partida a
partida, contra a tabela 8.1.2 da spec. `Audit_Period.csv` mostra que a soma
fecha.
"""
import io

_DELIMITER = ";"

GAMES_AUDIT_PREAMBLE = "# fide_games_v1"
GAMES_AUDIT_HEADER = (
    "Tournament;TimeControl;IsInternal;PlayerId;PlayerName;OpponentId;"
    "OpponentRatingCapped;D;PD;Score;DeltaR;K"
)

PERIOD_AUDIT_PREAMBLE = "# fide_period_v1"
PERIOD_AUDIT_HEADER = (
    "Tournaments;PlayerId;PlayerName;TimeControl;InitialRating;Games;SumDeltaR;"
    "Variation;RoundedVariation;FinalRating;Path"
)


def write_games_audit(outcome) -> str:
    """Uma linha por partida computada, por lado."""
    buf = io.StringIO()
    print(GAMES_AUDIT_PREAMBLE, file=buf)
    print(GAMES_AUDIT_HEADER, file=buf)
    for result in outcome.results:
        name = outcome.players[result.player_id].name
        for entry in result.game_results:
            print(_DELIMITER.join([
                str(entry.game.tournament_ord),
                entry.game.modality,
                "1" if entry.game.is_internal else "0",
                str(result.player_id),
                name,
                str(entry.game.opponent_id),
                str(entry.opponent_rating),
                str(entry.capped_diff),
                str(entry.pd),
                str(entry.game.score),
                str(entry.delta),
                str(entry.k),
            ]), file=buf)
    return buf.getvalue()


def write_period_audit(outcome) -> str:
    """Uma linha por jogador × modalidade, nomeando os torneios do período."""
    tournaments = ",".join(str(t.ord) for t in outcome.tournaments)
    buf = io.StringIO()
    print(PERIOD_AUDIT_PREAMBLE, file=buf)
    print(PERIOD_AUDIT_HEADER, file=buf)
    for result in outcome.results:
        print(_DELIMITER.join([
            tournaments,
            str(result.player_id),
            outcome.players[result.player_id].name,
            result.modality,
            "" if result.initial_rating is None else str(result.initial_rating),
            str(result.games_counted),
            str(result.sum_delta),
            str(result.variation),
            str(result.rounded_variation),
            "" if result.final_rating is None else str(result.final_rating),
            result.path,
        ]), file=buf)
    return buf.getvalue()
```

Em `calculator/fide/cycle.py`, acrescentar `from . import audit` aos imports e trocar
`run_cycle` para emitir os três arquivos:

```python
    def run_cycle(self) -> dict[str, str]:
        """Devolve `{nome_do_arquivo: conteúdo CSV}` para o período."""
        outcome = self.run_period()
        return {
            "RatingList.csv": write_rating_list(outcome.players),
            "Audit_Games.csv": audit.write_games_audit(outcome),
            "Audit_Period.csv": audit.write_period_audit(outcome),
        }
```

E, em `tests/fide/test_cycle.py`, apertar a asserção de forma:

```python
    def test_produces_one_list_and_two_audits(self):
        output = _cycle(_ONE_TOURNAMENT).run_cycle()
        assert set(output) == {"RatingList.csv", "Audit_Games.csv", "Audit_Period.csv"}
```

- [ ] **Step 4: Rodar tudo e ligar a cobertura do pacote novo**

Run: `.venv/bin/pytest tests/fide/ -q --no-cov`
Expected: PASS

Em `pyproject.toml`, incluir o pacote novo na cobertura (o motor atual segue fora, porque não é mantido aqui):

```toml
[tool.pytest.ini_options]
addopts = "--cov=backend --cov=calculator/fide --cov-branch --cov-report=term-missing --cov-fail-under=80"
testpaths = ["tests"]

[tool.coverage.run]
source = ["backend", "calculator/fide"]
omit = ["tests/*"]
```

- [ ] **Step 5: Rodar a suíte inteira com o portão de cobertura**

Run: `.venv/bin/pytest -q`
Expected: PASS, cobertura acima de 80%

- [ ] **Step 6: Commit**

```bash
git add calculator/fide/audit.py calculator/fide/cycle.py pyproject.toml tests/fide/test_audit.py
git commit -m "feat(fide): auditoria por partida e por período"
```

---

## Task 14: Comparativo entre os dois modelos

**Files:**
- Create: `calculator/compare.py`
- Test: `tests/test_compare.py`

**Interfaces:**
- Consumes: `calculator.FexerjRatingCycle`, `calculator.fide.FideRatingCycle`
- Produces:
  - `COMPARISON_PREAMBLE = "# fide_comparison_v1"`, `COMPARISON_HEADER`
  - `run_comparison(tournaments_csv, first, count, players_csv, binary_files) -> dict[str, str]`

- [ ] **Step 1: Escrever o teste**

```python
"""Comparativo entre o modelo atual e o modelo por partida."""
import pathlib

from calculator.compare import COMPARISON_HEADER, COMPARISON_PREAMBLE, run_comparison
from calculator.fide.ratinglist import LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

_TOURNAMENTS = TOURNAMENTS_HEADER + "\n1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"


def _run():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return run_comparison(_TOURNAMENTS, 1, 1, _PLAYERS_CSV, {"1-99999.TURX": data})


def test_output_carries_both_models_and_the_comparison():
    output = _run()
    assert "Comparison.csv" in output
    assert "RatingList.csv" in output          # modelo novo
    assert "RatingList_after_1.csv" in output  # modelo atual
    assert "Audit_Games.csv" in output


def test_comparison_preamble_and_header():
    lines = _output_comparison().splitlines()
    assert lines[0] == COMPARISON_PREAMBLE
    assert lines[1] == COMPARISON_HEADER


def _output_comparison():
    return _run()["Comparison.csv"]


def test_one_row_per_player():
    lines = [r for r in _output_comparison().splitlines()[2:] if r]
    assert len(lines) == 6


def test_difference_is_new_minus_current():
    header = COMPARISON_HEADER.split(';')
    for line in _output_comparison().splitlines()[2:]:
        if not line:
            continue
        cells = dict(zip(header, line.split(';'), strict=True))
        if cells["RatingFide"] and cells["RatingAtual"]:
            assert int(cells["Difference"]) == int(cells["RatingFide"]) - int(cells["RatingAtual"])


def test_models_disagree_on_at_least_one_player():
    """Ratings diferentes com histórico idêntico é o objetivo, não um defeito."""
    header = COMPARISON_HEADER.split(';')
    diffs = []
    for line in _output_comparison().splitlines()[2:]:
        if not line:
            continue
        cells = dict(zip(header, line.split(';'), strict=True))
        diffs.append(int(cells["Difference"] or 0))
    assert any(d != 0 for d in diffs)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_compare.py -q --no-cov`
Expected: FAIL com `ModuleNotFoundError: No module named 'calculator.compare'`

- [ ] **Step 3: Implementar**

```python
"""Roda os dois modelos sobre o mesmo insumo e emite o comparativo.

Depende dos dois motores; nenhum deles depende deste módulo.

Restrições do modo, verificadas pelo validador antes de chegar aqui: o
players.csv tem de ser o de 12 colunas, porque o motor atual só lê esse
formato, e todo torneio do período tem de ser STD, porque o modelo atual não
tem conceito de modalidade.
"""
import csv
import io

from .classes import FexerjRatingCycle
from .fide import audit
from .fide.cycle import FideRatingCycle
from .fide.ratinglist import write_rating_list

_DELIMITER = ";"

COMPARISON_PREAMBLE = "# fide_comparison_v1"
COMPARISON_HEADER = "PlayerId;PlayerName;RatingAtual;RatingFide;Difference"


def run_comparison(
    tournaments_csv: str,
    first: int,
    count: int,
    players_csv: str,
    binary_files: dict[str, bytes],
) -> dict[str, str]:
    """Devolve as saídas dos dois modelos mais `Comparison.csv`."""
    legacy_output = FexerjRatingCycle(
        tournaments_csv=_strip_modality_column(tournaments_csv),
        first_item=first,
        items_to_process=count,
        initial_rating_csv=players_csv,
        binary_files=binary_files,
    ).run_cycle()

    # Um único `run_period`: chamar `run_cycle` e `run_period` recalcularia tudo
    # duas vezes e abriria espaço para as duas saídas divergirem.
    outcome = FideRatingCycle(
        tournaments_csv=tournaments_csv,
        first_item=first,
        items_to_process=count,
        initial_rating_csv=players_csv,
        binary_files=binary_files,
    ).run_period()

    output = dict(legacy_output)
    output["RatingList.csv"] = write_rating_list(outcome.players)
    output["Audit_Games.csv"] = audit.write_games_audit(outcome)
    output["Audit_Period.csv"] = audit.write_period_audit(outcome)
    output["Comparison.csv"] = _write_comparison(
        _legacy_final_ratings(legacy_output), outcome.players
    )
    return output


def _strip_modality_column(tournaments_csv: str) -> str:
    """Remove a coluna TimeControl para o motor atual, que lê por posição."""
    reader = csv.reader(io.StringIO(tournaments_csv.lstrip("﻿")), delimiter=_DELIMITER)
    buf = io.StringIO()
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        print(_DELIMITER.join(row[:7]), file=buf)
    return buf.getvalue()


def _legacy_final_ratings(legacy_output: dict[str, str]) -> dict[int, int]:
    """Rating final do modelo atual: a última RatingList_after_<N> do ciclo."""
    names = sorted(
        (n for n in legacy_output if n.startswith("RatingList_after_")),
        key=lambda n: int(n.removeprefix("RatingList_after_").removesuffix(".csv")),
    )
    if not names:
        return {}
    reader = csv.reader(io.StringIO(legacy_output[names[-1]]), delimiter=_DELIMITER)
    next(reader, None)
    return {
        int(row[0]): int(row[4])
        for row in reader
        if any(cell.strip() for cell in row)
    }


def _write_comparison(legacy_ratings: dict[int, int], fide_players: dict) -> str:
    buf = io.StringIO()
    print(COMPARISON_PREAMBLE, file=buf)
    print(COMPARISON_HEADER, file=buf)
    for player_id, player in fide_players.items():
        legacy = legacy_ratings.get(player_id)
        fide = player.modalities["STD"].rating
        difference = "" if legacy is None or fide is None else str(fide - legacy)
        print(_DELIMITER.join([
            str(player_id),
            player.name,
            "" if legacy is None else str(legacy),
            "" if fide is None else str(fide),
            difference,
        ]), file=buf)
    return buf.getvalue()
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/test_compare.py -q --no-cov && .venv/bin/pytest tests/test_legacy_engine_golden.py -q --no-cov`
Expected: PASS nos dois — o teste de ouro prova que rodar o motor atual pelo comparativo não o alterou

- [ ] **Step 5: Commit**

```bash
git add calculator/compare.py tests/test_compare.py
git commit -m "feat(calculator): comparativo entre o modelo atual e o modelo FIDE"
```

---

## Task 15: Validador — formato de 23 colunas e despacho por cabeçalho

**Files:**
- Modify: `backend/validator.py`
- Test: `tests/test_validator_fide.py`

**Interfaces:**
- Consumes: `calculator.fide.ratinglist.FIDE_HEADER`, `LEGACY_HEADER`
- Produces: `validate_inputs(..., mode: str = "legacy")` aceitando `"legacy" | "fide" | "compare"`

- [ ] **Step 1: Escrever o teste**

```python
"""Validação do formato novo e do despacho por cabeçalho."""
from backend.validator import validate_inputs
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

_FIDE_PLAYERS = (
    FIDE_HEADER + "\n"
    "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;;0;0;0;0;;0;0;0;0\n"
)
_LEGACY_PLAYERS = (
    LEGACY_HEADER + "\n"
    "1;;;Carlos Mendes;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
)
_FIDE_TOURNAMENTS = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"


def _errors(players, tournaments, mode):
    return validate_inputs(players, tournaments, {}, 1, 1, mode=mode)


def test_fide_mode_accepts_the_new_header():
    errors = _errors(_FIDE_PLAYERS, _FIDE_TOURNAMENTS, "fide")
    assert not any("cabeçalho" in e for e in errors)


def test_fide_mode_accepts_the_legacy_header():
    """A conversão da §2.2 acontece na leitura; o arquivo de hoje continua servindo."""
    errors = _errors(_LEGACY_PLAYERS, _FIDE_TOURNAMENTS, "fide")
    assert not any("cabeçalho" in e for e in errors)


def test_unknown_header_names_both_accepted_formats():
    errors = _errors("Foo;Bar\n1;2\n", _FIDE_TOURNAMENTS, "fide")
    joined = " ".join(errors)
    assert "12" in joined and "23" in joined


def test_peak_flag_must_be_zero_or_one():
    bad = _FIDE_PLAYERS.replace(";1800;50;0;", ";1800;50;7;")
    errors = _errors(bad, _FIDE_TOURNAMENTS, "fide")
    assert any("Peak2200_Std" in e for e in errors)


def test_empty_rating_is_accepted():
    unrated = (
        FIDE_HEADER + "\n"
        "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;;0;0;0;0;;0;0;0;0;;0;0;0;0\n"
    )
    errors = _errors(unrated, _FIDE_TOURNAMENTS, "fide")
    assert not any("Rtg_Std" in e for e in errors)


def test_empty_rating_with_peak_flag_is_accepted():
    """Jogador que atingiu 2200 e depois caiu abaixo do piso (§7)."""
    fallen = (
        FIDE_HEADER + "\n"
        "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;;300;1;0;0;;0;0;0;0;;0;0;0;0\n"
    )
    errors = _errors(fallen, _FIDE_TOURNAMENTS, "fide")
    assert errors == [] or not any("Peak2200_Std" in e for e in errors)


def test_legacy_mode_still_rejects_the_new_header():
    errors = _errors(_FIDE_PLAYERS, _FIDE_TOURNAMENTS, "legacy")
    assert any("cabeçalho" in e for e in errors)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_validator_fide.py -q --no-cov`
Expected: FAIL com `TypeError: validate_inputs() got an unexpected keyword argument 'mode'`

- [ ] **Step 3: Implementar**

Em `backend/validator.py`, acrescentar aos imports:

```python
from calculator.fide.model import COLUMN_SUFFIX, MODALITIES
from calculator.fide.ratinglist import FIDE_COLUMN_COUNT, FIDE_HEADER
```

Trocar a assinatura de `validate_inputs` para aceitar o modo e despachar a validação do players:

```python
MODE_LEGACY = "legacy"
MODE_FIDE = "fide"
MODE_COMPARE = "compare"
_VALID_MODES = frozenset({MODE_LEGACY, MODE_FIDE, MODE_COMPARE})


def validate_inputs(
    players_content: str,
    tournaments_content: str,
    binary_files: dict[str, bytes],
    first: int,
    count: int,
    mode: str = MODE_LEGACY,
) -> list[str]:
    """Valida as entradas de um ciclo, segundo o modo de execução escolhido."""
    if mode not in _VALID_MODES:
        return [f"Modo de execução '{mode}' desconhecido."]

    players_content = players_content.lstrip("﻿")
    tournaments_content = tournaments_content.lstrip("﻿")

    errors: list[str] = []
    players_errors = _validate_players_for_mode(players_content, mode)
    errors.extend(players_errors)
    # A validação de torneios por modo entra na Task 16; aqui as regras atuais
    # valem para os três modos.
    tournaments_errors = _validate_tournaments_csv(tournaments_content)
    errors.extend(tournaments_errors)
    if not tournaments_errors:
        players_index = (
            _build_players_index(players_content) if not players_errors else None
        )
        errors.extend(
            _validate_binary_files(
                tournaments_content, binary_files, first, count, players_index=players_index
            )
        )
    return errors


def _validate_players_for_mode(content: str, mode: str) -> list[str]:
    """No modo legado só vale o formato de 12 colunas; no modo FIDE valem os dois."""
    if mode == MODE_LEGACY or mode == MODE_COMPARE:
        return _validate_players_csv(content)
    first_line = content.splitlines()[0].strip() if content.splitlines() else ""
    if first_line == FIDE_HEADER:
        return _validate_fide_players_csv(content)
    if first_line == _PLAYERS_HEADER:
        return _validate_players_csv(content)
    return [
        "players.csv: cabeçalho inválido — aceito o formato de 12 colunas "
        f"ou o de {FIDE_COLUMN_COUNT} colunas do modelo por partida."
    ]


def _validate_fide_players_csv(content: str) -> list[str]:
    """Regras do formato de 23 colunas (§2.1 da spec)."""
    errors: list[str] = []
    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader, None)

    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != FIDE_COLUMN_COUNT:
            errors.append(
                f"players.csv linha {row_num}: esperadas {FIDE_COLUMN_COUNT} colunas, "
                f"encontradas {len(row)}"
            )
            continue

        if not row[0].strip():
            errors.append(f"players.csv linha {row_num}: Id_No é obrigatório")
        if not row[3].strip():
            errors.append(f"players.csv linha {row_num}: Name é obrigatório")
        if not row[5].strip():
            # §5.3: a data de nascimento passa a ser dado obrigatório.
            errors.append(f"players.csv linha {row_num}: Birthday é obrigatório no modelo por partida")

        for index, modality in enumerate(MODALITIES):
            base = 8 + index * 5
            suffix = COLUMN_SUFFIX[modality]
            rating = row[base].strip()
            if rating and not _is_int(rating):
                errors.append(f"players.csv linha {row_num}: Rtg_{suffix} deve ser inteiro ou vazio")
            if not _is_int(row[base + 1].strip() or "0"):
                errors.append(f"players.csv linha {row_num}: Games_{suffix} deve ser um inteiro")
            if row[base + 2].strip() not in {"0", "1"}:
                errors.append(f"players.csv linha {row_num}: Peak2200_{suffix} deve ser 0 ou 1")

    return errors


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True
```

Nesta task o `tournaments.csv` ainda é validado pelas regras atuais nos três
modos — os testes acima só exercitam o `players.csv`. A Task 16 acrescenta o
despacho por modo.

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/test_validator_fide.py tests/test_validator.py -q --no-cov`
Expected: PASS nos dois — o validador atual não pode ter regredido

- [ ] **Step 5: Commit**

```bash
git add backend/validator.py tests/test_validator_fide.py
git commit -m "feat(validator): formato de 23 colunas e despacho por cabeçalho"
```

---

## Task 16: Validador — regras por modo

**Files:**
- Modify: `backend/validator.py` (`_validate_tournaments_for_mode` e as restrições do modo comparar)
- Test: `tests/test_validator_modes.py`

**Interfaces:**
- Consumes: o modo da Task 15
- Produces: validação de `TimeControl`, `EndDate` e das duas restrições do modo comparar

- [ ] **Step 1: Escrever o teste**

```python
"""Regras de validação que dependem do modo de execução."""
from backend.validator import validate_inputs
from calculator.fide.ratinglist import FIDE_HEADER, LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

_LEGACY_TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj"

_LEGACY_PLAYERS = (
    LEGACY_HEADER + "\n"
    "1;;;Carlos Mendes;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
)
_FIDE_PLAYERS = (
    FIDE_HEADER + "\n"
    "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;1800;50;0;0;0;;0;0;0;0;;0;0;0;0\n"
)


def _errors(players, tournaments, mode):
    return validate_inputs(players, tournaments, {}, 1, 1, mode=mode)


class TestTimeControl:
    def test_required_in_fide_mode(self):
        legacy_tournaments = _LEGACY_TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1\n"
        errors = _errors(_FIDE_PLAYERS, legacy_tournaments, "fide")
        assert any("TimeControl" in e for e in errors)

    def test_must_be_a_known_value(self):
        bad = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;RAPIDO\n"
        errors = _errors(_FIDE_PLAYERS, bad, "fide")
        assert any("STD" in e and "RPD" in e for e in errors)

    def test_not_required_in_legacy_mode(self):
        legacy_tournaments = _LEGACY_TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1\n"
        errors = _errors(_LEGACY_PLAYERS, legacy_tournaments, "legacy")
        assert not any("TimeControl" in e for e in errors)


class TestEndDate:
    def test_required_in_fide_mode_for_the_under_18_rule(self):
        no_date = TOURNAMENTS_HEADER + "\n1;99999;Torneio;;RR;0;1;STD\n"
        errors = _errors(_FIDE_PLAYERS, no_date, "fide")
        assert any("EndDate" in e for e in errors)

    def test_optional_in_legacy_mode(self):
        legacy_tournaments = _LEGACY_TOURNAMENTS_HEADER + "\n1;99999;Torneio;;RR;0;1\n"
        errors = _errors(_LEGACY_PLAYERS, legacy_tournaments, "legacy")
        assert not any("EndDate" in e for e in errors)


class TestCompareModeRestrictions:
    def test_rejects_the_new_players_format(self):
        tournaments = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"
        errors = _errors(_FIDE_PLAYERS, tournaments, "compare")
        assert any("comparar" in e.lower() and "12" in e for e in errors)

    def test_rejects_non_std_tournaments(self):
        tournaments = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;BLZ\n"
        errors = _errors(_LEGACY_PLAYERS, tournaments, "compare")
        assert any("comparar" in e.lower() and "STD" in e for e in errors)

    def test_accepts_legacy_players_with_std_tournaments(self):
        tournaments = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"
        errors = _errors(_LEGACY_PLAYERS, tournaments, "compare")
        assert errors == []
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_validator_modes.py -q --no-cov`
Expected: FAIL — nenhuma das mensagens novas existe

- [ ] **Step 3: Implementar**

Em `backend/validator.py`, trocar a chamada direta a `_validate_tournaments_csv`
dentro de `validate_inputs` por `_validate_tournaments_for_mode(tournaments_content, mode)`
e acrescentar a função, junto das restrições do modo comparar:

```python
_FIDE_TOURNAMENTS_HEADER = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj;TimeControl"
_VALID_TIME_CONTROLS = frozenset(MODALITIES)


def _validate_tournaments_for_mode(content: str, mode: str) -> list[str]:
    """No modo legado vale o cabeçalho de 7 colunas; nos outros, o de 8."""
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

    errors = _validate_tournaments_csv(
        "\n".join([_TOURNAMENTS_HEADER] + [";".join(line.split(";")[:7]) for line in lines[1:]])
    )

    reader = csv.reader(io.StringIO(content), delimiter=";")
    next(reader)
    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != 8:
            errors.append(
                f"tournaments.csv linha {row_num}: esperadas 8 colunas, encontradas {len(row)}"
            )
            continue
        end_date = row[3].strip()
        if not end_date:
            errors.append(
                f"tournaments.csv linha {row_num}: EndDate é obrigatório no modelo por partida "
                f"— o fator K de sub-18 depende do ano do período"
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
            errors.append(
                f"tournaments.csv linha {row_num}: o modo comparar aceita apenas torneios STD. "
                f"O modelo atual não tem conceito de modalidade, então comparar um torneio de "
                f"'{time_control}' produziria uma diferença sem significado."
            )
    return errors
```

E, em `_validate_players_for_mode`, tratar o modo comparar antes de cair no validador legado:

```python
    if mode == MODE_COMPARE:
        first_line = content.splitlines()[0].strip() if content.splitlines() else ""
        if first_line == FIDE_HEADER:
            return [
                "players.csv: o modo comparar exige a lista no formato de 12 colunas, porque o "
                "modelo atual não lê outro formato. Use o arquivo que a federação usa hoje."
            ]
        return _validate_players_csv(content)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/pytest tests/test_validator_modes.py tests/test_validator.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/validator.py tests/test_validator_modes.py
git commit -m "feat(validator): regras por modo, com as restrições do modo comparar"
```

---

## Task 17: API — o campo `mode` em `/validate` e `/run`

**Files:**
- Modify: `backend/main.py:190-230` (`/validate`), `backend/main.py:233-332` (`/run`)
- Test: `tests/test_backend_modes.py`

**Interfaces:**
- Consumes: `validate_inputs(..., mode=...)`, `FideRatingCycle`, `run_comparison`
- Produces: `/validate` e `/run` aceitam `mode` (padrão `legacy`); nome do ZIP por modo

- [ ] **Step 1: Escrever o teste**

```python
"""O campo `mode` nas rotas de validação e execução."""
import io
import pathlib
import zipfile

from fastapi.testclient import TestClient

from backend.main import app
from calculator.fide.ratinglist import LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)
_FIDE_TOURNAMENTS = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"
_LEGACY_TOURNAMENTS = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n1;99999;Torneio;2026-03-15;RR;0;1\n"


def _files(tournaments_csv):
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return [
        ("players_csv", ("players.csv", _PLAYERS_CSV.encode(), "text/csv")),
        ("tournaments_csv", ("tournaments.csv", tournaments_csv.encode(), "text/csv")),
        ("binary_files", ("1-99999.TURX", data, "application/octet-stream")),
    ]


def _post(client, path, tournaments_csv, mode=None, auth=("admin", "senha-de-teste")):
    data = {"first": "1", "count": "1"}
    if mode is not None:
        data["mode"] = mode
    return client.post(path, data=data, files=_files(tournaments_csv), auth=auth)


def test_run_defaults_to_the_current_model(client, auth):
    """Sem `mode`, nada muda para quem já usa o portal."""
    response = _post(client, "/run", _LEGACY_TOURNAMENTS, auth=auth)
    assert response.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert "RatingList_after_1.csv" in names


def test_fide_mode_returns_the_new_output_shape(client, auth):
    response = _post(client, "/run", _FIDE_TOURNAMENTS, mode="fide", auth=auth)
    assert response.status_code == 200
    names = set(zipfile.ZipFile(io.BytesIO(response.content)).namelist())
    assert names == {"RatingList.csv", "Audit_Games.csv", "Audit_Period.csv"}


def test_compare_mode_returns_both_models(client, auth):
    response = _post(client, "/run", _FIDE_TOURNAMENTS, mode="compare", auth=auth)
    assert response.status_code == 200
    names = set(zipfile.ZipFile(io.BytesIO(response.content)).namelist())
    assert "Comparison.csv" in names
    assert "RatingList_after_1.csv" in names
    assert "RatingList.csv" in names


def test_zip_filename_differs_by_mode(client, auth):
    legacy = _post(client, "/run", _LEGACY_TOURNAMENTS, auth=auth)
    fide = _post(client, "/run", _FIDE_TOURNAMENTS, mode="fide", auth=auth)
    assert "rating_cycle_output.zip" in legacy.headers["content-disposition"]
    assert "rating_cycle_fide.zip" in fide.headers["content-disposition"]


def test_unknown_mode_is_rejected(client, auth):
    response = _post(client, "/run", _FIDE_TOURNAMENTS, mode="turbo", auth=auth)
    assert response.status_code == 422


def test_validate_uses_the_mode(client, auth):
    response = _post(client, "/validate", _LEGACY_TOURNAMENTS, mode="fide", auth=auth)
    assert response.status_code == 200
    assert any("TimeControl" in e for e in response.json()["errors"])
```

As fixtures `client` e `auth` devem seguir o padrão já usado em `tests/test_backend.py`; reaproveite-as movendo-as para `tests/conftest.py` se ainda forem locais.

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/pytest tests/test_backend_modes.py -q --no-cov`
Expected: FAIL — o modo `fide` ainda cai no motor atual

- [ ] **Step 3: Implementar**

Em `backend/main.py`, acrescentar aos imports:

```python
from backend.validator import MODE_COMPARE, MODE_FIDE, MODE_LEGACY, validate_inputs
from calculator.compare import run_comparison
from calculator.fide import FideRatingCycle
```

Acrescentar o mapa de nome de ZIP e a assinatura do campo:

```python
_ZIP_NAME_BY_MODE = {
    MODE_LEGACY: "rating_cycle_output.zip",
    MODE_FIDE: "rating_cycle_fide.zip",
    MODE_COMPARE: "rating_cycle_comparison.zip",
}
```

Em `/validate` e `/run`, acrescentar o parâmetro:

```python
    mode: Annotated[str, Form(description="Modo de execução: legacy | fide | compare")] = MODE_LEGACY,
```

Em `/validate`, passar adiante:

```python
    errors = validate_inputs(players_content, tournaments_content, binary_files_dict, first, count, mode=mode)
```

Em `/run`, o mesmo, e trocar a construção do ciclo por um despacho:

```python
        try:
            output_files = _run_for_mode(
                mode, tournaments_content, first, count, players_content, binary_files_dict
            )
        except ValueError as e:
            logger.error(
                "Erro no ciclo de rating: %s",
                e,
                exc_info=True,
                extra={"event": "rating_cycle_failed", "path": "/run", "mode": mode},
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Erro ao processar ciclo de rating: {e}",
            ) from e
```

E a função de despacho:

```python
def _run_for_mode(
    mode: str,
    tournaments_content: str,
    first: int,
    count: int,
    players_content: str,
    binary_files: dict[str, bytes],
) -> dict[str, str]:
    """Roda o ciclo do modo pedido. O modo padrão é o modelo atual, intocado."""
    if mode == MODE_COMPARE:
        return run_comparison(tournaments_content, first, count, players_content, binary_files)
    cycle_class = FideRatingCycle if mode == MODE_FIDE else FexerjRatingCycle
    return cycle_class(
        tournaments_csv=tournaments_content,
        first_item=first,
        items_to_process=count,
        initial_rating_csv=players_content,
        binary_files=binary_files,
    ).run_cycle()
```

E o cabeçalho da resposta:

```python
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition":
                    f"attachment; filename={_ZIP_NAME_BY_MODE.get(mode, _ZIP_NAME_BY_MODE[MODE_LEGACY])}"
            },
        )
```

- [ ] **Step 4: Rodar a suíte inteira**

Run: `.venv/bin/pytest -q`
Expected: PASS, cobertura acima de 80%

- [ ] **Step 5: Confirmar lint e tipos**

Run: `.venv/bin/ruff check . && .venv/bin/mypy backend calculator`
Expected: sem erros

- [ ] **Step 6: Atualizar a documentação**

Em `CALCULATOR.md`, acrescentar uma seção no topo apontando que existem dois motores, qual é o padrão, e que o modelo por partida está descrito em `docs/modelo-rating-fide.md`. Em `README.md`, documentar o campo `mode` de `/validate` e `/run` e os nomes de arquivo de saída por modo. Em `RUNBOOK.md`, acrescentar à seção de testes que `tests/test_legacy_engine_golden.py` é o teste que trava o motor oficial.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py tests/test_backend_modes.py CALCULATOR.md README.md RUNBOOK.md
git commit -m "feat(api): campo mode em /validate e /run com os três modelos"
```

---

## Próximo plano

O portal (seletor, tela de resultado, ajuda) está em
[`2026-08-09-migracao-modelo-rating-portal.md`](2026-08-09-migracao-modelo-rating-portal.md).
Até ele entrar, o portal segue servindo apenas o modelo atual, que é o padrão —
os modos novos ficam alcançáveis pela API.
