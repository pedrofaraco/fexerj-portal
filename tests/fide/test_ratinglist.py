"""Reading and writing the 29-column format — spec §2.1."""
from decimal import Decimal

import pytest

from calculator.fide.ratinglist import FIDE_HEADER, read_rating_list, write_rating_list

_FIDE_CSV = (
    FIDE_HEADER + "\n"
    "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;"
    "2201;51;1;6;11;0.5;;1702;32;0;7;12;1.5;;1603;13;0;8;13;2.5;\n"
    "2;36633;;Roberto Faria;CLUB B;15/06/1985;M;BRA;"
    "1904;44;0;9;21;3.5;;2205;25;1;10;22;4.5;;;6;0;11;23;5.5;\n"
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
        assert std.rating == 2201
        assert std.games == 51
        assert std.reached_2200 is True

    def test_empty_rating_means_unrated(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[2].modalities["BLZ"].rating is None

    def test_reads_peak_flag(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[2].modalities["RPD"].reached_2200 is True

    def test_reads_unrated_accumulators(self):
        players = read_rating_list(_FIDE_CSV)
        blz = players[2].modalities["BLZ"]
        assert blz.rating is None
        assert blz.accumulator.sum_opponents == 23
        assert blz.accumulator.points == Decimal("5.5")
        assert blz.accumulator.games == 11

    def test_reads_all_modality_fields_for_player_one(self):
        """Direct guard against a column swap: every one of the 21 modality
        fields is asserted, and the fixture's per-field values are pairwise
        distinct within each field type so a swap changes at least one
        assertion."""
        players = read_rating_list(_FIDE_CSV)
        std = players[1].modalities["STD"]
        rpd = players[1].modalities["RPD"]
        blz = players[1].modalities["BLZ"]

        assert std.rating == 2201
        assert std.games == 51
        assert std.reached_2200 is True
        assert std.accumulator.games == 6
        assert std.accumulator.sum_opponents == 11
        assert std.accumulator.points == Decimal("0.5")

        assert rpd.rating == 1702
        assert rpd.games == 32
        assert rpd.reached_2200 is False
        assert rpd.accumulator.games == 7
        assert rpd.accumulator.sum_opponents == 12
        assert rpd.accumulator.points == Decimal("1.5")

        assert blz.rating == 1603
        assert blz.games == 13
        assert blz.reached_2200 is False
        assert blz.accumulator.games == 8
        assert blz.accumulator.sum_opponents == 13
        assert blz.accumulator.points == Decimal("2.5")

    def test_reads_accumulation_since(self):
        """AccSince_ is the §6.2 marker for the 26-month pooling window."""
        with_since = _FIDE_CSV.replace(
            "2201;51;1;6;11;0.5;;", "2201;51;1;6;11;0.5;2025-11;"
        )
        players = read_rating_list(with_since)
        assert players[1].modalities["STD"].accumulator.since == "2025-11"

    def test_empty_since_means_no_accumulation_start_recorded(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].modalities["STD"].accumulator.since == ""

    def test_skips_all_blank_rows(self):
        players = read_rating_list(_FIDE_CSV + ";" * 28 + "\n")
        assert len(players) == 2

    def test_rejects_unknown_header(self):
        with pytest.raises(ValueError, match="cabeçalho"):
            read_rating_list("Foo;Bar\n1;2\n")


class TestWriteFideFormat:
    def test_round_trip_is_stable(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players) == _FIDE_CSV

    def test_header_is_the_29_column_one(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players).splitlines()[0] == FIDE_HEADER
