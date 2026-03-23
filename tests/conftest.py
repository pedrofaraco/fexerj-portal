"""Shared pytest fixtures for the calculator package test suite."""
import pathlib
import textwrap
from unittest.mock import MagicMock

import pytest

from calculator.classes import FexerjPlayer, TournamentPlayer, Tournament

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'

RATING_LIST_CSV = textwrap.dedent("""\
    Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
    1;;; Pedro Alves;1500;CLUB A;01/01/1990;M;BRA;50;0;0
    2;36633;;Rafael Costa;1800;CLUB B;15/06/1985;M;BRA;100;0;0
    3;;;Lucia Ferreira;1200;CLUB C;20/03/2000;F;BRA;5;30000;2.5
""")


def _make_tournament_player(tournament=None, **kwargs):
    """Build a TournamentPlayer without any HTTP calls."""
    if tournament is None:
        tournament = MagicMock()
    player = TournamentPlayer(tournament)
    player.snr = kwargs.get("snr", 1)
    player.name = kwargs.get("name", "Test Player")
    player.id = kwargs.get("id", 100)
    player.opponents = kwargs.get("opponents", {})
    player.is_unrated = kwargs.get("is_unrated", False)
    player.is_temp = kwargs.get("is_temp", False)
    player.last_rating = kwargs.get("last_rating", 1500)
    player.last_total_games = kwargs.get("last_total_games", 50)
    player.last_sum_oppon_ratings = kwargs.get("last_sum_oppon_ratings", 0)
    player.last_pts_against_oppon = kwargs.get("last_pts_against_oppon", 0.0)
    player.this_pts_against_oppon = kwargs.get("this_pts_against_oppon", None)
    player.this_sum_oppon_ratings = kwargs.get("this_sum_oppon_ratings", None)
    player.this_avg_oppon_rating = kwargs.get("this_avg_oppon_rating", None)
    player.this_games = kwargs.get("this_games", None)
    player.this_score = kwargs.get("this_score", None)
    player.this_expected_points = kwargs.get("this_expected_points", None)
    player.this_points_above_expected = kwargs.get("this_points_above_expected", None)
    player.new_rating = kwargs.get("new_rating", None)
    player.new_total_games = kwargs.get("new_total_games", None)
    player.new_avg_oppon_rating = kwargs.get("new_avg_oppon_rating", None)
    player.new_sum_oppon_ratings = kwargs.get("new_sum_oppon_ratings", None)
    player.new_pts_against_oppon = kwargs.get("new_pts_against_oppon", None)
    player.calc_rule = kwargs.get("calc_rule", None)
    player.last_k = kwargs.get("last_k", None)
    return player


@pytest.fixture
def make_tournament_player():
    """Factory fixture: returns a callable that creates TournamentPlayer instances."""
    return _make_tournament_player


@pytest.fixture
def established_player(make_tournament_player):
    return make_tournament_player(last_total_games=50, last_rating=1500, is_unrated=False, is_temp=False)


@pytest.fixture
def temp_player(make_tournament_player):
    return make_tournament_player(last_total_games=5, last_rating=1400, is_unrated=False, is_temp=True)


@pytest.fixture
def unrated_player(make_tournament_player):
    return make_tournament_player(last_total_games=0, last_rating=0, is_unrated=True, is_temp=False)


def _make_fexerj_player(id_fexerj, total_games, last_rating, sum_oppon=0, pts_oppon=0.0, id_cbx=""):
    return FexerjPlayer(id_fexerj, id_cbx, "", f"Player {id_fexerj}", last_rating,
                        "CLUB", "01/01/1990", "M", "BRA", total_games, sum_oppon, pts_oppon)


def _make_tournament(is_irt=0, is_fexerj=1, rating_list=None, cbx_to_fexerj=None, binary_data=b''):
    """Build a Tournament wired to an in-memory binary blob (SS type, id=12345)."""
    rc = MagicMock()
    rc.rating_list = rating_list or {}
    rc.cbx_to_fexerj = cbx_to_fexerj or {}
    rc.binary_files = {"1-12345.TUNX": binary_data}
    data = ["1", "12345", "Test Tournament", "2025-01-01", "SS", str(is_irt), str(is_fexerj)]
    return Tournament(rc, data)


@pytest.fixture
def make_tournament():
    return _make_tournament
