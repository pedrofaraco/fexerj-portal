"""Reads tournaments.csv and flattens the binaries into games."""
import pathlib
from decimal import Decimal

import pytest

from calculator.fide.ratinglist import LEGACY_HEADER, read_rating_list
from calculator.fide.tournaments import (
    TOURNAMENTS_HEADER,
    collect_games,
    period_year,
    read_tournaments,
)

BINARY_DIR = pathlib.Path(__file__).parent.parent / 'binary'

# The two tournaments deliberately fall in different years (2026 and 2027) so
# that period_year is exercised across a year boundary, not just picking the
# only year present.
_TOURNAMENTS_CSV = (
    TOURNAMENTS_HEADER + "\n"
    "1;99999;Torneio Um;2026-12-20;RR;0;1;STD\n"
    "2;88888;Torneio Dois;2027-01-15;RR;0;0;RPD\n"
)

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

# Same players as _PLAYERS_CSV, but keyed by FEXERJ id (101..106) with the
# binary's ids (3741, 643, ...) carried in Id_CBX instead of Id_No. Used by
# the IRT tests below: an IRT binary carries CBX ids, which must be
# translated through this column, never used as FEXERJ ids directly.
_IRT_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "101;3741;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "102;643;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "103;1979;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "104;2831;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "105;3541;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "106;5400;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)


class TestReadTournaments:
    def test_reads_the_modality_column(self):
        rows = read_tournaments(_TOURNAMENTS_CSV, 1, 2)
        assert [r.modality for r in rows] == ["STD", "RPD"]

    def test_respects_the_first_count_window(self):
        rows = read_tournaments(_TOURNAMENTS_CSV, 2, 1)
        assert [r.ord for r in rows] == [2]

    def test_rejects_unknown_header(self):
        with pytest.raises(ValueError, match="cabeçalho"):
            read_tournaments("Ord;CrId\n1;2\n", 1, 1)


class TestPeriodYear:
    def test_uses_the_latest_end_date(self):
        """The fixture spans 2026-12-20 and 2027-01-15: only picking the
        latest year, not the first row or a hardcoded one, passes this."""
        rows = read_tournaments(_TOURNAMENTS_CSV, 1, 2)
        assert period_year(rows) == 2027

    def test_raises_when_a_date_is_unusable(self):
        csv_text = TOURNAMENTS_HEADER + "\n1;99999;Torneio;;RR;0;1;STD\n"
        rows = read_tournaments(csv_text, 1, 1)
        with pytest.raises(ValueError, match="EndDate"):
            period_year(rows)


class TestCollectGames:
    def _rows_and_binaries(self):
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        csv_text = TOURNAMENTS_HEADER + "\n1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
        return read_tournaments(csv_text, 1, 1), {"1-99999.TURX": data}

    def _irt_rows_and_binaries(self):
        """Same binary and same tournament row as `_rows_and_binaries`, with
        only IsIrt flipped to 1 - isolates the flag as the sole cause of any
        difference in how ids resolve."""
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        csv_text = TOURNAMENTS_HEADER + "\n1;99999;Torneio Um;2026-03-15;RR;1;1;STD\n"
        return read_tournaments(csv_text, 1, 1), {"1-99999.TURX": data}

    def test_produces_two_entries_per_game(self):
        """Each game appears once per side, with the score inverted."""
        rows, binaries = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        pairs = {(g.player_id, g.opponent_id) for g in games}
        for a, b in list(pairs):
            assert (b, a) in pairs

    def test_scores_are_complementary(self):
        rows, binaries = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        by_pair = {(g.player_id, g.opponent_id): g.score for g in games}
        for (a, b), score in by_pair.items():
            assert score + by_pair[(b, a)] == Decimal("1")

    def test_games_carry_the_modality(self):
        rows, binaries = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        assert all(g.modality == "STD" for g in games)

    def test_modality_comes_from_the_originating_tournament(self):
        """Collects from two tournaments with different modalities, reusing the
        same binary under two filenames. A value hardcoded in collect_games
        instead of read from the tournament row would still pass
        test_games_carry_the_modality (which only has one, STD, tournament) but
        fails here."""
        data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
        csv_text = (
            TOURNAMENTS_HEADER + "\n"
            "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
            "2;99999;Torneio Dois;2026-04-20;RR;0;0;RPD\n"
        )
        rows = read_tournaments(csv_text, 1, 2)
        binaries = {"1-99999.TURX": data, "2-99999.TURX": data}
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)

        from_first = [g for g in games if g.tournament_ord == 1]
        from_second = [g for g in games if g.tournament_ord == 2]
        assert from_first and all(g.modality == "STD" for g in from_first)
        assert from_second and all(g.modality == "RPD" for g in from_second)

    def test_missing_binary_raises_with_the_filename(self):
        rows, _ = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        with pytest.raises(ValueError, match="1-99999.TURX"):
            collect_games(rows, {}, players)

    def test_player_absent_from_the_rating_list_raises(self):
        rows, binaries = self._rows_and_binaries()
        with pytest.raises(ValueError, match="lista de rating"):
            collect_games(rows, binaries, {})

    def test_irt_tournament_resolves_binary_ids_through_id_cbx(self):
        """IsIrt=1: the binary carries CBX ids (3741, 643, ...), which must
        be translated to FEXERJ ids (101..106) through the rating list's
        Id_CBX column. If the code used the binary's id directly, as it does
        for a non-IRT tournament, the collected games would carry the raw
        CBX ids instead - so this also checks that none of them leak through."""
        rows, binaries = self._irt_rows_and_binaries()
        players = read_rating_list(_IRT_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        ids = {g.player_id for g in games} | {g.opponent_id for g in games}
        assert ids == set(range(101, 107))
        assert ids.isdisjoint({3741, 643, 1979, 2831, 3541, 5400})

    def test_irt_missing_cbx_id_raises_like_the_non_irt_path(self):
        """Removing the player whose Id_CBX is 643 (Roberto Faria) from the
        IRT rating list must raise mentioning 643 - the CBX id that could
        not be translated - not his FEXERJ id 102. The message must be
        identical to what the non-IRT path raises when 643 itself, used
        there as the FEXERJ id, is missing: same tournament, same binary,
        same missing number, so the error-building code is shared, not
        duplicated per path."""
        irt_rows, irt_binaries = self._irt_rows_and_binaries()
        irt_players = read_rating_list(_IRT_PLAYERS_CSV)
        del irt_players[102]
        with pytest.raises(ValueError, match="lista de rating") as irt_exc:
            collect_games(irt_rows, irt_binaries, irt_players)
        assert "643" in str(irt_exc.value)

        non_irt_rows, non_irt_binaries = self._rows_and_binaries()
        non_irt_players = read_rating_list(_PLAYERS_CSV)
        del non_irt_players[643]
        with pytest.raises(ValueError, match="lista de rating") as non_irt_exc:
            collect_games(non_irt_rows, non_irt_binaries, non_irt_players)

        assert str(irt_exc.value) == str(non_irt_exc.value)

    def test_non_irt_tournament_resolves_directly_to_binary_ids(self):
        """The same binary, read with IsIrt=0 against a rating list whose
        FEXERJ ids are the numbers in the binary, resolves player_id and
        opponent_id to those raw ids (3741, 643, ...) with no translation.
        Together with test_irt_tournament_resolves_binary_ids_through_id_cbx,
        this pins the choice of resolution path to the IsIrt flag alone,
        not to anything about the binary file itself - both tests read the
        exact same bytes."""
        rows, binaries = self._rows_and_binaries()
        players = read_rating_list(_PLAYERS_CSV)
        games = collect_games(rows, binaries, players)
        ids = {g.player_id for g in games} | {g.opponent_id for g in games}
        assert ids == {3741, 643, 1979, 2831, 3541, 5400}
