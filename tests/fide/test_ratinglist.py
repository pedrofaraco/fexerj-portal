"""Reading and writing the 43-column format — spec §11.1."""
from decimal import Decimal

import pytest

from calculator.fide.model import ModalityState, PlayerState
from calculator.fide.ratinglist import FIDE_HEADER, read_rating_list, write_rating_list

_PERIOD_YEAR = 2026

# Every per-field value is distinct within its field type, so a column swap
# changes at least one assertion. The K of each modality is the one §5 produces
# for that state — the round-trip test below would otherwise fail, which is
# exactly the guard wanted: the K column is written, never copied.
_FIDE_CSV = (
    FIDE_HEADER + "\n"
    "1;;;;Player One;CLUB A;01/01/1990;M;BRA;1;"
    "2201;51;10;1;2026-05;;;6;11;0.5;;"
    "1702;32;20;1;2026-03;;;7;12;1.5;;"
    "1603;13;40;0;;;;8;13;2.5;\n"
    "2;36633;1;;Player Two;CLUB B;15/06/1985;M;BRA;4;"
    "1904;44;20;1;2026-05;;;9;21;3.5;;"
    "2205;25;10;1;2026-01;;;10;22;4.5;;"
    ";6;20;1;2025-11;1550;10/07/2026;11;23;5.5;2025-11\n"
)


class TestReadFideFormat:
    def test_reads_identity_columns(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].name == "Player One"
        assert players[1].birthday == "01/01/1990"
        assert players[2].id_cbx == "36633"

    def test_reads_status(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].status == "1"
        assert players[2].status == "4"

    def test_reads_prev_id(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].prev_id == ""
        assert players[2].prev_id == "1"

    def test_reads_std_modality(self):
        players = read_rating_list(_FIDE_CSV)
        std = players[1].modalities["STD"]
        assert std.rating == 2201
        assert std.games == 51

    def test_empty_rating_means_unrated(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[2].modalities["BLZ"].rating is None

    def test_k_10_reads_as_having_reached_2200(self):
        """§5, decided by FEXERJ: the K column *is* the indicator."""
        players = read_rating_list(_FIDE_CSV)
        assert players[1].modalities["STD"].reached_2200 is True
        assert players[2].modalities["RPD"].reached_2200 is True

    def test_any_other_k_reads_as_not_reached(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].modalities["RPD"].reached_2200 is False
        assert players[1].modalities["BLZ"].reached_2200 is False

    def test_blank_k_reads_as_not_reached_instead_of_raising(self):
        blanked = _FIDE_CSV.replace("2201;51;10;", "2201;51;;")
        assert read_rating_list(blanked)[1].modalities["STD"].reached_2200 is False

    def test_reads_the_first_tournament_marker(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].modalities["STD"].first_tournament_played is True
        assert players[1].modalities["BLZ"].first_tournament_played is False

    def test_reads_last_played(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].modalities["STD"].last_played == "2026-05"
        assert players[1].modalities["BLZ"].last_played == ""

    def test_reads_the_fide_rating_and_its_date(self):
        blz = read_rating_list(_FIDE_CSV)[2].modalities["BLZ"]
        assert blz.fide_rating == 1550
        assert blz.fide_date == "10/07/2026"

    def test_no_fide_rating_reads_as_none(self):
        std = read_rating_list(_FIDE_CSV)[1].modalities["STD"]
        assert std.fide_rating is None
        assert std.fide_date == ""

    def test_reads_unrated_accumulators(self):
        players = read_rating_list(_FIDE_CSV)
        blz = players[2].modalities["BLZ"]
        assert blz.rating is None
        assert blz.accumulator.sum_opponents == 23
        assert blz.accumulator.points == Decimal("5.5")
        assert blz.accumulator.games == 11

    def test_reads_all_modality_fields_for_player_one(self):
        """Direct guard against a column swap: every one of the 33 modality
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
        assert std.first_tournament_played is True
        assert std.last_played == "2026-05"
        assert std.fide_rating is None
        assert std.fide_date == ""
        assert std.accumulator.games == 6
        assert std.accumulator.sum_opponents == 11
        assert std.accumulator.points == Decimal("0.5")
        assert std.accumulator.since == ""

        assert rpd.rating == 1702
        assert rpd.games == 32
        assert rpd.reached_2200 is False
        assert rpd.first_tournament_played is True
        assert rpd.last_played == "2026-03"
        assert rpd.fide_rating is None
        assert rpd.fide_date == ""
        assert rpd.accumulator.games == 7
        assert rpd.accumulator.sum_opponents == 12
        assert rpd.accumulator.points == Decimal("1.5")
        assert rpd.accumulator.since == ""

        assert blz.rating == 1603
        assert blz.games == 13
        assert blz.reached_2200 is False
        assert blz.first_tournament_played is False
        assert blz.last_played == ""
        assert blz.fide_rating is None
        assert blz.fide_date == ""
        assert blz.accumulator.games == 8
        assert blz.accumulator.sum_opponents == 13
        assert blz.accumulator.points == Decimal("2.5")
        assert blz.accumulator.since == ""

    def test_reads_accumulation_since(self):
        """AccSince_ is the §6.2 marker for the 26-month pooling window."""
        players = read_rating_list(_FIDE_CSV)
        assert players[2].modalities["BLZ"].accumulator.since == "2025-11"

    def test_empty_since_means_no_accumulation_start_recorded(self):
        players = read_rating_list(_FIDE_CSV)
        assert players[1].modalities["STD"].accumulator.since == ""

    def test_skips_all_blank_rows(self):
        players = read_rating_list(_FIDE_CSV + ";" * 42 + "\n")
        assert len(players) == 2

    def test_rejects_unknown_header(self):
        with pytest.raises(ValueError, match="cabeçalho"):
            read_rating_list("Foo;Bar\n1;2\n")


def _one_player(state: ModalityState, birthday: str = "01/01/1990") -> dict[int, PlayerState]:
    return {
        1: PlayerState(
            id_fexerj=1,
            name="Player One",
            birthday=birthday,
            modalities={"STD": state, "RPD": ModalityState(), "BLZ": ModalityState()},
        )
    }


def _written_k(state: ModalityState, birthday: str = "01/01/1990") -> str:
    row = write_rating_list(_one_player(state, birthday), _PERIOD_YEAR).splitlines()[1]
    return row.split(";")[12]  # K_Std: ten identity columns, then Rtg, Games, K


class TestWriteFideFormat:
    def test_round_trip_is_stable(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players, _PERIOD_YEAR) == _FIDE_CSV

    def test_header_is_the_43_column_one(self):
        players = read_rating_list(_FIDE_CSV)
        assert write_rating_list(players, _PERIOD_YEAR).splitlines()[0] == FIDE_HEADER

    def test_writes_the_k_the_state_ends_on(self):
        """A player who crosses 2200 during the period has to leave the cycle
        holding a 10, or the permanence is lost in the very cycle that earned
        it."""
        assert _written_k(ModalityState(rating=2210, games=60, reached_2200=True)) == "10"

    def test_writes_10_for_a_player_who_reached_2200_and_fell_back(self):
        assert _written_k(ModalityState(rating=2150, games=60, reached_2200=True)) == "10"

    def test_writes_10_for_an_unrated_player_who_had_reached_2200(self):
        """The floor (§7) drops the rating, never the permanence."""
        assert _written_k(ModalityState(rating=None, games=60, reached_2200=True)) == "10"

    def test_writes_the_base_k_never_the_700_capped_one(self):
        """`cap_k_by_games(20, 70)` is also 10 (§5.1). Writing the capped K
        would mark a player as having reached 2200 on the strength of a long
        period alone, and there is no way back from that."""
        assert _written_k(ModalityState(rating=1500, games=70, reached_2200=False)) == "20"

    def test_writes_40_for_a_new_player(self):
        assert _written_k(ModalityState(rating=1500, games=29, reached_2200=False)) == "40"

    def test_writes_40_for_an_under_18_player(self):
        assert _written_k(
            ModalityState(rating=1500, games=60, reached_2200=False), birthday="01/01/2010"
        ) == "40"

    def test_a_recorded_fide_rating_drops_the_new_player_k(self):
        """§6.4: the K comes from the rating band, not from the FEXERJ game
        count — and it has to keep doing so after the period they entered on."""
        assert _written_k(
            ModalityState(rating=1900, games=6, reached_2200=False, fide_rating=1900)
        ) == "20"

    def test_the_fide_columns_are_written_back_unchanged(self):
        players = _one_player(
            ModalityState(rating=1900, games=6, fide_rating=1900, fide_date="10/07/2026")
        )
        row = write_rating_list(players, _PERIOD_YEAR).splitlines()[1].split(";")
        assert row[15] == "1900"  # RtgFide_Std
        assert row[16] == "10/07/2026"  # FideDate_Std
