"""Tables 8.1.2 and 8.1.1 from the FIDE Handbook B02.

§3 of the spec forbids swapping table 8.1.2 for the logistic formula: the
divergence was measured against an official FIDE consultation and is recorded
in §10 — 7 of 13 games diverge, and the period would close 0.76 point wrong.
"""
from decimal import ROUND_HALF_UP, Decimal

# Table 8.1.2 — (upper bound of the D range, PD of the higher-rated player).
# The ranges are closed: D from 0 to 3 → .50; from 4 to 10 → .51; and so on.
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

# Table 8.1.1 — dp for p from 0.50 to 1.00, in steps of 0.01.
# The lower half comes out via antisymmetry: dp(p) = -dp(1-p).
_DP_FROM_HALF: tuple[int, ...] = (
    0, 7, 14, 21, 29, 36, 43, 50, 57, 65,
    72, 80, 87, 95, 102, 110, 117, 125, 133, 141,
    149, 158, 166, 175, 184, 193, 202, 211, 220, 230,
    240, 251, 262, 273, 284, 296, 309, 322, 336, 351,
    366, 383, 401, 422, 444, 470, 501, 538, 589, 677,
    800,
)


def pd_for_diff(diff: int) -> Decimal:
    """PD from table 8.1.2 for `diff = player_rating - opponent_rating`.

    `diff >= 0` uses column H (higher-rated player); `diff < 0` uses column L,
    which is `1 - H`.
    """
    magnitude = abs(diff)
    higher = _PD_ABOVE_LAST_BAND
    for max_diff, value in _PD_BY_MAX_DIFF:
        if magnitude <= max_diff:
            higher = Decimal(value)
            break
    return higher if diff >= 0 else _ONE - higher


def dp_for_score_ratio(p: Decimal) -> int:
    """dp from table 8.1.1 for the score percentage `p`.

    `p` is rounded to two decimal places before the lookup, because it comes
    from a division and needs to land on a row of the table. `p` must be
    in the range [0, 1].
    """
    hundredths = int(p.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)
    if hundredths >= 50:
        return _DP_FROM_HALF[hundredths - 50]
    return -_DP_FROM_HALF[50 - hundredths]
