"""Golden test for the current engine: the output must not change by a single byte.

The engine in `calculator/classes.py` generates the official FEXERJ rating and
is not touched by the migration. This test fails if someone changes it by accident.
"""
import pathlib

from calculator import FexerjRatingCycle

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'
GOLDEN_DIR = pathlib.Path(__file__).parent / 'golden'

_PLAYERS_CSV = (
    "Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;"
    "TotalNumGames;SumOpponRating;TotalPoints\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

_TOURNAMENTS_CSV = (
    "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n"
    "1;99999;Test RR Tournament;2025-01-01;RR;0;1\n"
)


def _run_legacy_cycle():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    cycle = FexerjRatingCycle(
        tournaments_csv=_TOURNAMENTS_CSV,
        first_item=1,
        items_to_process=1,
        initial_rating_csv=_PLAYERS_CSV,
        binary_files={"1-99999.TURX": data},
    )
    return cycle.run_cycle()


def test_legacy_rating_list_is_byte_identical():
    output = _run_legacy_cycle()
    expected = (GOLDEN_DIR / 'legacy_rr_1_ratinglist.csv').read_text(encoding='utf-8')
    assert output["RatingList_after_1.csv"] == expected


def test_legacy_audit_is_byte_identical():
    output = _run_legacy_cycle()
    expected = (GOLDEN_DIR / 'legacy_rr_1_audit.csv').read_text(encoding='utf-8')
    assert output["Audit_of_Tournament_1.csv"] == expected
