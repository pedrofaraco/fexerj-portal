"""Conversion from the 12-column legacy format — spec §2.2."""
from decimal import Decimal

from calculator.fide.ratinglist import LEGACY_HEADER, read_rating_list

_LEGACY_CSV = (
    LEGACY_HEADER + "\n"
    # rated, ordinary case
    "1;;;Carlos Mendes;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
    # unrated today: TotalNumGames = 0, even though Rtg_Nat carries a number
    "2;;;Roberto Faria;1500;CLUB B;01/01/1992;M;BRA;0;3200;1.5\n"
    # below the new floor: the current model's floor is 1 point
    "3;;;Andre Nunes;900;CLUB C;01/01/1988;M;BRA;40;0;0\n"
    # already at 2200 in the source list
    "4;36633;;Felipe Borges;2250;CLUB D;01/01/1980;M;BRA;300;0;0\n"
    # today's temporary band: 1 to 14 games, enters as rated
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
        """In the current model, TotalNumGames = 0 decides, not Rtg_Nat."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).rating is None
        assert _std(players[2]).games == 0

    def test_zero_games_keeps_the_unrated_accumulators(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).sum_opponents == 3200
        assert _std(players[2]).points == Decimal("1.5")

    def test_below_the_floor_becomes_unrated_but_keeps_the_game_count(self):
        """§7 applied at conversion time: without it the initial list would be invalid."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[3]).rating is None
        assert _std(players[3]).games == 40

    def test_at_or_above_2200_sets_the_peak_flag(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[4]).reached_2200 is True

    def test_temporary_band_enters_as_rated(self):
        """§12 retires the TEMPORARY rule; it doesn't reclassify players who already have a published rating."""
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
