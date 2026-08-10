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
