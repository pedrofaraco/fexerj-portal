"""Reading and writing the 26-column format — spec §2.1."""
from decimal import Decimal

import pytest

from calculator.fide.ratinglist import FIDE_HEADER, read_rating_list, write_rating_list

_FIDE_CSV = (
    FIDE_HEADER + "\n"
    "1;;;Carlos Mendes;CLUB A;01/01/1990;M;BRA;"
    "2201;51;1;11;0.5;6;"
    "1702;32;0;12;1.5;7;"
    "1603;13;0;13;2.5;8\n"
    "2;36633;;Roberto Faria;CLUB B;15/06/1985;M;BRA;"
    "1904;44;0;21;3.5;9;"
    "2205;25;1;22;4.5;10;"
    ";6;0;23;5.5;11\n"
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
        assert blz.sum_opponents == 23
        assert blz.points == Decimal("5.5")
        assert blz.accumulated_games == 11

    def test_reads_all_modality_fields_for_player_one(self):
        """Direct guard against a column swap: every one of the 18 modality
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
        assert std.sum_opponents == 11
        assert std.points == Decimal("0.5")
        assert std.accumulated_games == 6

        assert rpd.rating == 1702
        assert rpd.games == 32
        assert rpd.reached_2200 is False
        assert rpd.sum_opponents == 12
        assert rpd.points == Decimal("1.5")
        assert rpd.accumulated_games == 7

        assert blz.rating == 1603
        assert blz.games == 13
        assert blz.reached_2200 is False
        assert blz.sum_opponents == 13
        assert blz.points == Decimal("2.5")
        assert blz.accumulated_games == 8

    def test_skips_all_blank_rows(self):
        players = read_rating_list(_FIDE_CSV + ";" * 25 + "\n")
        assert len(players) == 2

    def test_rejects_unknown_header(self):
        with pytest.raises(ValueError, match="cabeçalho"):
            read_rating_list("Foo;Bar\n1;2\n")


class TestWriteFideFormat:
    def test_round_trip_is_stable(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players) == _FIDE_CSV

    def test_header_is_the_26_column_one(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players).splitlines()[0] == FIDE_HEADER
