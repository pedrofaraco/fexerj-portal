"""Reading and writing the 23-column format — spec §2.1."""
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
