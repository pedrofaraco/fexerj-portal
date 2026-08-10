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
