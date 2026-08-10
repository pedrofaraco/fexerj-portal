"""Conversion from the 12-column legacy format — spec §2.2."""
from decimal import Decimal

from calculator.fide.model import Game
from calculator.fide.period import compute_unrated_period
from calculator.fide.ratinglist import LEGACY_HEADER, read_rating_list

_MONTH = "2026-01"

_LEGACY_CSV = (
    LEGACY_HEADER + "\n"
    # rated, ordinary case, with non-zero accumulators
    "1;;;Carlos Mendes;1800;CLUB A;01/01/1990;M;BRA;50;7100;3.5\n"
    # unrated today: TotalNumGames = 0, even though Rtg_Nat carries a number
    "2;;;Roberto Faria;1500;CLUB B;01/01/1992;M;BRA;0;3200;1.5\n"
    # below the new floor, with non-zero accumulators and identity columns
    # that differ from every other row (Title, Sex, Fed)
    "3;;FM;Andre Nunes;900;CLUB C;01/01/1988;F;ARG;40;5600;2.5\n"
    # exactly at the 2200 threshold
    "4;36633;GM;Felipe Borges;2200;CLUB D;01/01/1980;M;BRA;300;0;0\n"
    # today's temporary band: 1 to 14 games, enters as rated
    "5;;;Lucas Carvalho;1450;CLUB E;01/01/1998;M;BRA;8;0;0\n"
    # one point below the 2200 threshold
    "6;;;Bruno Teixeira;2199;CLUB F;01/01/1975;M;BRA;120;0;0\n"
    # below the floor, at/above the legacy engine's 15-game threshold: the
    # engine has already zeroed SumOpponRating/TotalPoints by the time
    # TotalNumGames reaches this many (calculator/classes.py), so this row is
    # what a real federation export looks like — matches the reported bug's
    # reproduction case (60 lifetime games, expelled by the 1200 floor)
    "7;;;Marcos Lima;800;CLUB G;01/01/1993;M;BRA;60;0;0\n"
    # below the floor, under the legacy engine's 15-game threshold: here
    # SumOpponRating/TotalPoints are still a real, lock-step accumulation of
    # every game played, so the full count is preserved instead of zeroed
    "8;;;Diego Alves;700;CLUB H;01/01/1996;M;BRA;10;8500;1.5\n"
)


def _std(player):
    return player.modalities["STD"]


class TestLegacyConversion:
    def test_rated_player_carries_rating_and_games(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[1]).rating == 1800
        assert _std(players[1]).games == 50
        assert _std(players[1]).reached_2200 is False

    def test_rated_player_carries_the_accumulators_too(self):
        """sum_opponents/points default to zero, so forgetting to pass them
        through on the rated path wouldn't fail any other test."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[1]).accumulator.sum_opponents == 7100
        assert _std(players[1]).accumulator.points == Decimal("3.5")

    def test_rated_player_has_no_accumulated_games(self):
        """A rated player carries no §6.1 accumulator at all."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[1]).accumulator.games == 0

    def test_zero_games_becomes_unrated_despite_the_rating_column(self):
        """In the current model, TotalNumGames = 0 decides, not Rtg_Nat."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).rating is None
        assert _std(players[2]).games == 0

    def test_zero_games_keeps_the_unrated_accumulators(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).accumulator.sum_opponents == 3200
        assert _std(players[2]).accumulator.points == Decimal("1.5")

    def test_zero_games_has_zero_accumulated_games(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).accumulator.games == 0

    def test_below_the_floor_becomes_unrated_but_keeps_the_game_count(self):
        """§7 applied at conversion time: without it the initial list would be invalid."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[3]).rating is None
        assert _std(players[3]).games == 40

    def test_below_the_floor_keeps_the_accumulators_too(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[3]).accumulator.sum_opponents == 5600
        assert _std(players[3]).accumulator.points == Decimal("2.5")
        assert _std(players[3]).games == 40

    def test_below_the_floor_at_or_above_fifteen_games_zeroes_the_accumulated_count(self):
        """Player 3 has 40 lifetime games — past the legacy engine's 15-game
        threshold — yet this fixture still carries non-zero SumOpponRating/
        TotalPoints (row crafted to also exercise
        `test_below_the_floor_keeps_the_accumulators_too` above). The
        accumulated-games count must never claim more games than the
        threshold allows: it comes out zero regardless, the safe side of
        `nunca a um número maior`."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[3]).accumulator.games == 0

    def test_at_or_above_2200_sets_the_peak_flag(self):
        """Boundary case: rating is exactly 2200. Pins the threshold so that
        swapping `>=` for `>` in the conversion would be caught here."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[4]).reached_2200 is True

    def test_below_2200_does_not_set_the_peak_flag(self):
        """Boundary case: rating is exactly 2199, the other side of the
        threshold pinned by test_at_or_above_2200_sets_the_peak_flag."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[6]).reached_2200 is False

    def test_temporary_band_enters_as_rated(self):
        """§12 retires the TEMPORARY rule; it doesn't reclassify players who already have a published rating."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[5]).rating == 1450
        assert _std(players[5]).games == 8

    def test_temporary_band_rated_player_has_no_accumulated_games(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[5]).accumulator.games == 0

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

    def test_identity_columns_do_not_shift_between_formats(self):
        """Legacy and FIDE column orders differ; a shifted index would still
        read strings out of the row, so only distinct values catch it."""
        players = read_rating_list(_LEGACY_CSV)
        player = players[3]
        assert player.title == "FM"
        assert player.sex == "F"
        assert player.federation == "ARG"
        assert player.club == "CLUB C"
        assert player.birthday == "01/01/1988"

    def test_established_low_rated_player_gets_a_clean_accumulator(self):
        """Realistic version of the reported bug: a player with 60 lifetime
        games, below the new 1200 floor, whose SumOpponRating/TotalPoints the
        legacy engine already zeroed (past its own 15-game threshold). The
        accumulated-games count must be coherent with that — zero, not the
        lifetime count — so the player can start accumulating cleanly."""
        players = read_rating_list(_LEGACY_CSV)
        std = _std(players[7])
        assert std.rating is None
        assert std.games == 60
        assert std.accumulator.sum_opponents == 0
        assert std.accumulator.points == Decimal("0")
        assert std.accumulator.games == 0

    def test_established_low_rated_player_can_receive_a_rating_afterward(self):
        """Same player as above, run through the six-win reproduction case
        from the bug report end to end, starting from the converted state."""
        players = read_rating_list(_LEGACY_CSV)
        state = _std(players[7])
        games = [Game(1, "STD", 7, 900 + i, Decimal("1")) for i in range(6)]
        result = compute_unrated_period(
            7, "STD", state, games, {900 + i: 1500 for i in range(6)}, period_month=_MONTH,
        )
        assert result.final_rating == 1861
        assert result.path == "INITIAL_RATING"

    def test_below_the_floor_under_fifteen_games_keeps_the_full_count(self):
        """Below the legacy engine's 15-game threshold, SumOpponRating/
        TotalPoints are still a real, lock-step accumulation of every game
        played, so the accumulated-games count equals the full game count —
        not zero, and not more than what the accumulators actually hold."""
        players = read_rating_list(_LEGACY_CSV)
        std = _std(players[8])
        assert std.accumulator.games == 10
        assert std.accumulator.sum_opponents == 8500
        assert std.accumulator.points == Decimal("1.5")

    def test_legacy_accumulator_carries_no_recorded_start(self):
        """The legacy format has no column for §6.2's marker at all — see
        the conversion's own docstring for why an empty `since` here is the
        conservative choice, not an oversight."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[8]).accumulator.since == ""

    def test_legacy_accumulator_with_unknown_start_is_treated_as_expired(self):
        """Player 8 already has 10 accumulated games from the legacy file
        but no recorded start, so the first period the new engine processes
        for them resets the accumulator instead of carrying forward partial
        progress of unverifiable age — the conservative reading of
        "não há essa informação no arquivo antigo"."""
        players = read_rating_list(_LEGACY_CSV)
        state = _std(players[8])
        games = [Game(1, "STD", 8, 900 + i, Decimal("1")) for i in range(2)]
        result = compute_unrated_period(
            8, "STD", state, games, {900 + i: 1500 for i in range(2)}, period_month=_MONTH,
        )
        assert result.accumulator.games == 2          # only this period's games; the old 10 are gone
        assert result.accumulator.since == _MONTH      # restarted fresh, now dateable
