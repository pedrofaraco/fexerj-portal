"""The `mode` field on the validation and execution routes."""
import io
import pathlib
import zipfile

from fastapi.testclient import TestClient

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
_FIDE_TOURNAMENTS = TOURNAMENTS_HEADER + "\n1;99999;Torneio;2026-03-15;RR;0;1;STD\n"
_LEGACY_TOURNAMENTS = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n1;99999;Torneio;2026-03-15;RR;0;1\n"


def _files(tournaments_csv):
    data = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
    return [
        ("players_csv", ("players.csv", _PLAYERS_CSV.encode(), "text/csv")),
        ("tournaments_csv", ("tournaments.csv", tournaments_csv.encode(), "text/csv")),
        ("binary_files", ("1-99999.TURX", data, "application/octet-stream")),
    ]


def _post(client: TestClient, path: str, tournaments_csv: str, mode: str | None = None, auth=None):
    data = {"first": "1", "count": "1"}
    if mode is not None:
        data["mode"] = mode
    return client.post(path, data=data, files=_files(tournaments_csv), auth=auth)


def test_run_defaults_to_the_current_model(client, auth):
    """Without `mode`, nothing changes for existing portal users."""
    response = _post(client, "/run", _LEGACY_TOURNAMENTS, auth=auth)
    assert response.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert "RatingList_after_1.csv" in names


def test_fide_mode_returns_the_new_output_shape(client, auth):
    response = _post(client, "/run", _FIDE_TOURNAMENTS, mode="fide", auth=auth)
    assert response.status_code == 200
    names = set(zipfile.ZipFile(io.BytesIO(response.content)).namelist())
    assert names == {"RatingList.csv", "Audit_Games.csv", "Audit_Period.csv"}


def test_compare_mode_returns_both_models(client, auth):
    response = _post(client, "/run", _FIDE_TOURNAMENTS, mode="compare", auth=auth)
    assert response.status_code == 200
    names = set(zipfile.ZipFile(io.BytesIO(response.content)).namelist())
    assert "Comparison.csv" in names
    assert "RatingList_after_1.csv" in names
    assert "RatingList.csv" in names


def test_zip_filename_differs_by_mode(client, auth):
    legacy = _post(client, "/run", _LEGACY_TOURNAMENTS, auth=auth)
    fide = _post(client, "/run", _FIDE_TOURNAMENTS, mode="fide", auth=auth)
    assert "rating_cycle_output.zip" in legacy.headers["content-disposition"]
    assert "rating_cycle_fide.zip" in fide.headers["content-disposition"]


def test_unknown_mode_is_rejected(client, auth):
    response = _post(client, "/run", _FIDE_TOURNAMENTS, mode="turbo", auth=auth)
    assert response.status_code == 422


def test_validate_uses_the_mode(client, auth):
    response = _post(client, "/validate", _LEGACY_TOURNAMENTS, mode="fide", auth=auth)
    assert response.status_code == 200
    assert any("TimeControl" in e for e in response.json()["errors"])
