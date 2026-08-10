"""Comparison between the current model and the per-game model."""
import csv
import io
import pathlib

from calculator.compare import COMPARISON_HEADER, COMPARISON_PREAMBLE, run_comparison
from calculator.fide.ratinglist import LEGACY_HEADER
from calculator.fide.tournaments import TOURNAMENTS_HEADER

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'

_PLAYERS_CSV = (
    LEGACY_HEADER + "\n"
    "3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0\n"
    "643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0\n"
    "1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0\n"
    "2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0\n"
    "3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0\n"
    "5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0\n"
)

_TOURNAMENTS = TOURNAMENTS_HEADER + "\n1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"


def _run():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return run_comparison(_TOURNAMENTS, 1, 1, _PLAYERS_CSV, {"1-99999.TURX": data})


def test_output_carries_both_models_and_the_comparison():
    output = _run()
    assert "Comparison.csv" in output
    assert "RatingList.csv" in output          # per-game model
    assert "RatingList_after_1.csv" in output  # current model
    assert "Audit_Games.csv" in output


def test_comparison_preamble_and_header():
    lines = _output_comparison().splitlines()
    assert lines[0] == COMPARISON_PREAMBLE
    assert lines[1] == COMPARISON_HEADER


def _output_comparison():
    return _run()["Comparison.csv"]


def test_one_row_per_player():
    lines = [row for row in _output_comparison().splitlines()[2:] if row]
    assert len(lines) == 6


def test_difference_is_new_minus_current():
    header = COMPARISON_HEADER.split(';')
    for line in _output_comparison().splitlines()[2:]:
        if not line:
            continue
        cells = dict(zip(header, line.split(';'), strict=True))
        if cells["RatingFide"] and cells["RatingCurrent"]:
            assert int(cells["Difference"]) == int(cells["RatingFide"]) - int(cells["RatingCurrent"])


def test_models_disagree_on_at_least_one_player():
    """Different ratings from identical history is the point, not a defect."""
    header = COMPARISON_HEADER.split(';')
    diffs = []
    for line in _output_comparison().splitlines()[2:]:
        if not line:
            continue
        cells = dict(zip(header, line.split(';'), strict=True))
        diffs.append(int(cells["Difference"] or 0))
    assert any(diff != 0 for diff in diffs)


def test_no_tournament_in_the_window_produces_no_files():
    """Same as the two engines on their own: nothing in the window, nothing out —
    the backend turns that into a 422 instead of a zip that looks like a result."""
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    assert run_comparison(_TOURNAMENTS, 99, 1, _PLAYERS_CSV, {"1-99999.TURX": data}) == {}


def test_a_quoted_tournament_name_containing_the_delimiter_does_not_break_the_run():
    """The TimeControl column is dropped before the current engine reads the file.
    Cutting the cells is fine; re-joining them with ';' is not — a quoted name
    carrying a ';' would come back out unquoted and shift every column after it."""
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    tournaments = (
        TOURNAMENTS_HEADER + "\n"
        '1;99999;"Torneio Um; Etapa Final";2026-03-15;RR;0;1;STD\n'
    )
    output = run_comparison(tournaments, 1, 1, _PLAYERS_CSV, {"1-99999.TURX": data})

    assert "RatingList_after_1.csv" in output
    assert len([row for row in output["Comparison.csv"].splitlines()[2:] if row]) == 6


# Two tournaments in the period, but the row for Ord 2 appears before the row for
# Ord 1. The current engine processes tournaments.csv in file order, not sorted by
# Ord (see `FexerjRatingCycle.run_cycle`), so it writes RatingList_after_2.csv
# first and RatingList_after_1.csv last — the latter is the actual final state.
_OUT_OF_ORDER_TOURNAMENTS = (
    TOURNAMENTS_HEADER + "\n"
    "2;99999;Torneio Dois;2026-03-22;RR;0;1;STD\n"
    "1;99999;Torneio Um;2026-03-15;RR;0;1;STD\n"
)


def _run_out_of_order():
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    binaries = {"2-99999.TURX": data, "1-99999.TURX": data}
    return run_comparison(_OUT_OF_ORDER_TOURNAMENTS, 1, 2, _PLAYERS_CSV, binaries)


def _legacy_ratings_from(rating_list_csv):
    reader = csv.reader(io.StringIO(rating_list_csv), delimiter=';')
    next(reader, None)  # skip header
    return {int(row[0]): int(row[4]) for row in reader if any(cell.strip() for cell in row)}


def test_current_rating_is_the_last_list_the_engine_actually_wrote():
    """Rows out of Ord order must not fool the comparison into reporting the list
    with the highest Ord number as RatingCurrent: it must report the list the
    engine actually wrote last."""
    output = _run_out_of_order()
    actual_last = _legacy_ratings_from(output["RatingList_after_1.csv"])
    stale = _legacy_ratings_from(output["RatingList_after_2.csv"])
    assert actual_last != stale  # otherwise this test cannot tell the two apart

    header = COMPARISON_HEADER.split(';')
    for line in output["Comparison.csv"].splitlines()[2:]:
        if not line:
            continue
        cells = dict(zip(header, line.split(';'), strict=True))
        player_id = int(cells["PlayerId"])
        assert cells["RatingCurrent"] == str(actual_last[player_id])
