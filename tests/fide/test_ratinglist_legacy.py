"""Conversion from the 12-column legacy format — spec §2.2."""
import pathlib
import subprocess
import sys
from decimal import Decimal

import pytest

from calculator.fide.model import Game
from calculator.fide.period import compute_unrated_period
from calculator.fide.ratinglist import (
    FIDE_HEADER,
    LEGACY_HEADER,
    carry_over_active_accumulations,
    read_rating_list,
)

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
    # no rating on the source list, at/above the legacy engine's 15-game
    # threshold: the engine has already zeroed SumOpponRating/TotalPoints by
    # the time TotalNumGames reaches this many (calculator/classes.py), so
    # this row is what a real federation export looks like — the reported
    # bug's reproduction case, a player with 60 lifetime games and no rating
    "7;;;Marcos Lima;0;CLUB G;01/01/1993;M;BRA;60;0;0\n"
    # no rating on the source list, under the legacy engine's 15-game
    # threshold: here SumOpponRating/TotalPoints are still a real, lock-step
    # accumulation of every game played, so the full count is preserved
    "8;;;Diego Alves;0;CLUB H;01/01/1996;M;BRA;10;8500;1.5\n"
)


# Rows for the two conversion rules the federation settled on 2026-08-11.
# Kept in their own fixture so the cases above, which predate the decisions,
# stay readable as the rules they were written for.
_CONVERSION_CSV = (
    LEGACY_HEADER + "\n"
    # C: rating published with fewer than 5 games — zeroed, count preserved
    "10;;;Jogador C1;1450;CLUB A;01/01/1990;M;BRA;3;2900;1\n"
    # C boundary: exactly 5 games stays rated
    "11;;;Jogador C2;1450;CLUB A;01/01/1990;M;BRA;5;0;0\n"
    # D: below the floor with plenty of games — raised to the floor
    "12;;;Jogador D1;900;CLUB B;01/01/1990;M;BRA;40;0;0\n"
    # D boundary: exactly 5 games, below the floor
    "13;;;Jogador D2;1100;CLUB B;01/01/1990;M;BRA;5;0;0\n"
    # No rating at all on the source list, but games played: stays unrated —
    # "abaixo de 1200" is about a published rating, not about its absence
    "14;;;Jogador D3;0;CLUB C;01/01/1990;M;BRA;40;0;0\n"
    # Both rules could fire: below the floor AND fewer than 5 games. C wins —
    # the player has no business holding a rating either way
    "15;;;Jogador CD;900;CLUB C;01/01/1990;M;BRA;2;1800;0.5\n"
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

    def test_below_the_floor_with_enough_games_is_raised_to_the_floor(self):
        """Decision D: a published rating under 1200 cannot survive into the
        new list, and the player is raised to the floor rather than deleted.
        Detailed coverage in TestConversionDecisionD; here it is pinned on
        the shared fixture, whose accumulator assertions below depend on
        which branch this row takes."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[3]).rating == 1200
        assert _std(players[3]).games == 40

    def test_raised_to_the_floor_keeps_the_accumulators_too(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[3]).accumulator.sum_opponents == 5600
        assert _std(players[3]).accumulator.points == Decimal("2.5")
        assert _std(players[3]).games == 40

    def test_raised_to_the_floor_has_no_accumulated_games(self):
        """Player 3 enters rated at the floor, and a rated player carries no
        §6.1 accumulator: the accumulated count is zero even though the row
        still holds non-zero SumOpponRating/TotalPoints."""
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
        games and no rating, whose SumOpponRating/TotalPoints the legacy
        engine already zeroed (past its own 15-game threshold). The
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

    def test_unrated_under_fifteen_games_keeps_the_full_count(self):
        """Below the legacy engine's 15-game threshold, SumOpponRating/
        TotalPoints are still a real, lock-step accumulation of every game
        played, so the accumulated-games count equals the full game count —
        not zero, and not more than what the accumulators actually hold.
        Player 8 has no rating on the source list, so this stays reachable
        after decision D raised the below-the-floor rows to 1200."""
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


class TestConversionDecisionC:
    """Decided by FEXERJ on 2026-08-11: a player carrying a published rating
    with fewer than five games has the rating zeroed on conversion, but the
    game count is kept "para registro". The new model would never produce a
    rating on fewer than five games (§6.1), so the converted list would
    otherwise start with numbers the model itself refuses to make.
    Affects 256 players in the federation's current list."""

    def test_fewer_than_five_games_loses_the_rating(self):
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[10]).rating is None

    def test_but_keeps_the_game_count(self):
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[10]).games == 3

    def test_exactly_five_games_keeps_the_rating(self):
        """Five is the minimum for a first rating (§6.1), so the boundary
        belongs on the rated side."""
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[11]).rating == 1450

    def test_the_games_played_carry_over_as_accumulated_progress(self):
        """The three games are not thrown away: they count toward the five
        the player now needs."""
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[10]).accumulator.games == 3
        assert _std(players[10]).accumulator.sum_opponents == 2900


class TestConversionDecisionD:
    """Decided by FEXERJ on 2026-08-11: a player below the 1200 floor with
    five games or more is raised to the floor and enters rated, instead of
    entering unrated. Rationale on record: entering unrated removes them from
    the list in silence, because the initial-rating calculation rarely returns
    anyone above 1200; entering at the floor makes the exit, if it comes,
    happen through §7 with an audit line. Affects 60 players."""

    def test_below_the_floor_is_raised_to_the_floor(self):
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[12]).rating == 1200

    def test_the_game_count_is_preserved(self):
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[12]).games == 40

    def test_entering_at_the_floor_does_not_set_the_peak_flag(self):
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[12]).reached_2200 is False

    def test_exactly_five_games_is_raised_too(self):
        """The federation's note said "supondo > 5 partidas" while the
        question asked about "5 ou mais". Read as five or more: at exactly
        five, decision C no longer applies, so anything else would leave a
        rated player sitting below the floor — a state the model forbids."""
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[13]).rating == 1200

    def test_a_player_with_no_rating_at_all_is_not_raised(self):
        """`Rtg_Nat = 0` means the source list carries no rating, not a
        rating of zero. Raising these to 1200 would hand a rating to
        hundreds of unrated players."""
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[14]).rating is None
        assert _std(players[14]).games == 40

    def test_decision_c_wins_when_both_could_apply(self):
        """Below the floor and under five games: the player leaves unrated,
        not raised to 1200."""
        players = read_rating_list(_CONVERSION_CSV)
        assert _std(players[15]).rating is None
        assert _std(players[15]).games == 2


class TestConversionOfTheFirstTournamentMarker:
    """The §6.1 discard is spent by the first tournament the player plays.
    The legacy list records no more than *that* they have played, so a
    lifetime count above zero — the test the engine itself made before the
    marker became a field — is what carries over. Getting this wrong hands
    every converted player in the federation's list a fresh discard."""

    def test_a_player_with_games_has_already_spent_the_discard(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[1]).first_tournament_played is True

    def test_an_unrated_player_with_games_has_spent_it_too(self):
        """Player 7 has 60 games and no rating: exactly the case that must
        not come back as a newcomer."""
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[7]).rating is None
        assert _std(players[7]).first_tournament_played is True

    def test_a_player_with_no_games_still_has_it(self):
        players = read_rating_list(_LEGACY_CSV)
        assert _std(players[2]).games == 0
        assert _std(players[2]).first_tournament_played is False

    def test_rapid_and_blitz_start_with_the_discard_available(self):
        """The marker is per modality, like everything else in §5 and §6."""
        players = read_rating_list(_LEGACY_CSV)
        assert players[1].modalities["RPD"].first_tournament_played is False
        assert players[1].modalities["BLZ"].first_tournament_played is False


class TestConversionOfTheCadastralColumns:
    def test_status_defaults_to_active(self):
        """The legacy list has no status column; the operator fills it after
        the conversion (§11.1)."""
        assert read_rating_list(_LEGACY_CSV)[1].status == "1"

    def test_no_fide_rating_is_invented(self):
        assert _std(read_rating_list(_LEGACY_CSV)[1]).fide_rating is None

    def test_last_played_starts_empty(self):
        """The legacy format never recorded when a player last played."""
        assert _std(read_rating_list(_LEGACY_CSV)[1]).last_played == ""


# The list as it stands at the cut-over, and the one published two years
# before it. Comparing the two is how the operator's check at the cut-over
# (Anexo de Transição §1.1) tells who played in between.
_CUTOVER_CSV = (
    LEGACY_HEADER + "\n"
    # active: three games now, one of them already there two years ago
    "20;;;Jogador A1;1450;CLUB A;01/01/1990;M;BRA;3;4500;1.5\n"
    # inactive: the same three games two years ago
    "21;;;Jogador A2;1450;CLUB A;01/01/1990;M;BRA;3;4500;1.5\n"
    # not on the earlier list at all: every game is from the last two years
    "22;;;Jogador A3;1450;CLUB A;01/01/1990;M;BRA;2;3000;1\n"
    # rated: nothing accumulated to carry
    "23;;;Jogador A4;1800;CLUB A;01/01/1990;M;BRA;50;0;0\n"
    # played since, but not the rule's player: no published rating, ten games
    "24;;;Jogador A5;0;CLUB A;01/01/1990;M;BRA;10;8500;1.5\n"
)
_TWO_YEARS_EARLIER_CSV = (
    LEGACY_HEADER + "\n"
    "20;;;Jogador A1;1400;CLUB A;01/01/1990;M;BRA;1;1500;0.5\n"
    "21;;;Jogador A2;1450;CLUB A;01/01/1990;M;BRA;3;4500;1.5\n"
    "23;;;Jogador A4;1790;CLUB A;01/01/1990;M;BRA;40;0;0\n"
    "24;;;Jogador A5;0;CLUB A;01/01/1990;M;BRA;4;3000;1\n"
)
_CUTOVER = "2027-01"


class TestConversionOfTheActivePlayersGames:
    """Decided by FEXERJ on 2026-09-30, about the player decision C zeroes:
    "se ele está ativo (2025), conta. Se ele inativou (antes) não conta."
    The games of a player who played in the two years before the cut-over
    carry over toward the five; an inactive player's do not. The unit is
    the player, not the game — an active player keeps all of them."""

    def _converted(self):
        players = read_rating_list(_CUTOVER_CSV)
        carried = carry_over_active_accumulations(players, _TWO_YEARS_EARLIER_CSV, _CUTOVER)
        return players, carried

    def test_an_active_player_has_the_accumulation_dated_at_the_cutover(self):
        players, _ = self._converted()
        accumulator = _std(players[20]).accumulator
        assert accumulator.since == _CUTOVER
        assert (accumulator.games, accumulator.sum_opponents, accumulator.points) == (
            3, 4500, Decimal("1.5"),
        )

    def test_an_inactive_player_is_left_undated(self):
        players, _ = self._converted()
        assert _std(players[21]).accumulator.since == ""

    def test_a_player_absent_from_the_earlier_list_is_active(self):
        """An id that did not exist two years ago played every one of its
        games since then."""
        players, _ = self._converted()
        assert _std(players[22]).accumulator.since == _CUTOVER

    def test_only_the_player_decision_c_zeroed_is_touched(self):
        """Player 24 played in between, but holds ten games and no published
        rating: not "rating publicado e menos de 5 partidas". Player 23 is
        rated and has no accumulation to date."""
        players, _ = self._converted()
        assert _std(players[24]).accumulator.since == ""
        assert _std(players[23]).accumulator.since == ""

    def test_it_reports_who_was_carried_over(self):
        _, carried = self._converted()
        assert sorted(carried) == [20, 22]

    def test_the_active_player_reaches_five_games_with_the_old_ones(self):
        """Three carried games plus two new ones are five: a first rating.
        The calculation itself is untouched — it already honours a dated
        accumulator."""
        players, _ = self._converted()
        games = [Game(1, "STD", 20, 900, Decimal("1")), Game(1, "STD", 20, 901, Decimal("0.5"))]
        result = compute_unrated_period(
            20, "STD", _std(players[20]), games, {900: 1500, 901: 1500}, period_month=_CUTOVER,
        )
        assert result.path == "INITIAL_RATING"
        assert result.final_rating == 1579

    def test_the_inactive_player_starts_over_with_the_same_two_games(self):
        players, _ = self._converted()
        games = [Game(1, "STD", 21, 900, Decimal("1")), Game(1, "STD", 21, 901, Decimal("0.5"))]
        result = compute_unrated_period(
            21, "STD", _std(players[21]), games, {900: 1500, 901: 1500}, period_month=_CUTOVER,
        )
        assert result.path == "ACCUMULATING"
        assert result.accumulator.games == 2

    def test_the_earlier_list_must_be_in_the_legacy_format(self):
        players = read_rating_list(_CUTOVER_CSV)
        with pytest.raises(ValueError, match="12 colunas"):
            carry_over_active_accumulations(players, "Id;Nome\n1;X\n", _CUTOVER)


class TestTheCutoverConversionScript:
    """`scripts/converter-lista.py` is what runs the conversion once, at the
    cut-over: both lists in, the 42-column list out."""

    def test_it_writes_the_42_column_list_with_the_active_players_dated(self, tmp_path):
        current = tmp_path / "atual.csv"
        earlier = tmp_path / "antiga.csv"
        out = tmp_path / "nova.csv"
        current.write_text(_CUTOVER_CSV, encoding="utf-8")
        earlier.write_text(_TWO_YEARS_EARLIER_CSV, encoding="utf-8")
        script = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "converter-lista.py"

        done = subprocess.run(
            [sys.executable, str(script), str(current), str(earlier), _CUTOVER, str(out)],
            capture_output=True, text=True,
        )

        assert done.returncode == 0, done.stderr
        written = out.read_text(encoding="utf-8")
        assert written.splitlines()[0] == FIDE_HEADER
        players = read_rating_list(written)
        assert _std(players[20]).accumulator.since == _CUTOVER
        assert _std(players[21]).accumulator.since == ""
