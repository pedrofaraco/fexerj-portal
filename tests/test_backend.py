"""Tests for the FastAPI backend (/validate and /run endpoints)."""
import io
import pathlib
import textwrap
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'
TURX_DATA = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()

# 6 players matching the IDs in round_robin_6players.TURX
PLAYERS_CSV = textwrap.dedent("""\
    Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
    3741;;;Carlos Mendes;1800;CLUB A;01/01/1980;M;BRA;50;0;0
    643;;;Roberto Faria;1900;CLUB B;01/01/1975;M;BRA;80;0;0
    1979;;;Andre Nunes;1700;CLUB C;01/01/1982;M;BRA;60;0;0
    2831;;;Felipe Borges;1750;CLUB D;01/01/1978;M;BRA;100;0;0
    3541;;;Lucas Carvalho;1650;CLUB E;01/01/1985;M;BRA;45;0;0
    5400;;;Bruno Teixeira;1600;CLUB F;01/01/1995;M;BRA;20;0;0
""")

TOURNAMENTS_CSV = textwrap.dedent("""\
    Id;CbxId;Name;Date;Type;IsIrt;IsFexerj
    1;99999;Test RR Tournament;2025-01-01;RR;0;1
""")

VALID_AUTH = (settings.portal_user, settings.portal_password)

client = TestClient(app)


def _post_validate(players=PLAYERS_CSV, tournaments=TOURNAMENTS_CSV,
                   binary_filename="1-99999.TURX", binary_data=TURX_DATA,
                   first=1, count=1, auth=VALID_AUTH):
    return client.post(
        "/validate",
        data={"first": first, "count": count},
        files=[
            ("players_csv",     ("players.csv",      players.encode(),     "text/csv")),
            ("tournaments_csv", ("tournaments.csv",   tournaments.encode(), "text/csv")),
            ("binary_files",    (binary_filename,     binary_data,          "application/octet-stream")),
        ],
        auth=auth,
    )


def _post_run(players=PLAYERS_CSV, tournaments=TOURNAMENTS_CSV,
              binary_filename="1-99999.TURX", binary_data=TURX_DATA,
              first=1, count=1, auth=VALID_AUTH):
    return client.post(
        "/run",
        data={"first": first, "count": count},
        files=[
            ("players_csv",     ("players.csv",      players.encode(),    "text/csv")),
            ("tournaments_csv", ("tournaments.csv",   tournaments.encode(), "text/csv")),
            ("binary_files",    (binary_filename,     binary_data,         "application/octet-stream")),
        ],
        auth=auth,
    )


# ---------------------------------------------------------------------------
# Validate endpoint
# ---------------------------------------------------------------------------

class TestValidateEndpoint:
    def test_valid_files_return_empty_errors(self):
        response = _post_validate()
        assert response.status_code == 200
        assert response.json() == {"errors": []}

    def test_no_credentials_returns_401(self):
        response = client.post("/validate")
        assert response.status_code == 401

    def test_wrong_password_returns_401(self):
        response = _post_validate(auth=(settings.portal_user, "wrong"))
        assert response.status_code == 401

    def test_missing_binary_file_returns_error_list(self):
        response = _post_validate(binary_filename="wrong_name.TURX")
        assert response.status_code == 200
        errors = response.json()["errors"]
        assert len(errors) > 0
        assert any("missing" in e.lower() for e in errors)

    def test_invalid_tournament_type_returns_error_list(self):
        invalid = "Id;CbxId;Name;Date;Type;IsIrt;IsFexerj\n1;99999;T1;2025-01-01;XX;0;1\n"
        response = _post_validate(tournaments=invalid)
        assert response.status_code == 200
        errors = response.json()["errors"]
        assert any("XX" in e for e in errors)

    def test_binary_file_with_missing_player_id_returns_error_list(self):
        tunx_data = (BINARY_DIR / "swiss_system_18players.TUNX").read_bytes()
        tournaments = "Id;CbxId;Name;Date;Type;IsIrt;IsFexerj\n1;12345;T1;2025-01-01;SS;0;1\n"
        response = client.post(
            "/validate",
            data={"first": 1, "count": 1},
            files=[
                ("players_csv",     ("players.csv",    PLAYERS_CSV.encode(), "text/csv")),
                ("tournaments_csv", ("tournaments.csv", tournaments.encode(), "text/csv")),
                ("binary_files",    ("1-12345.TUNX",   tunx_data, "application/octet-stream")),
            ],
            auth=VALID_AUTH,
        )
        assert response.status_code == 200
        errors = response.json()["errors"]
        assert any("FEXERJ ID" in e for e in errors)

    def test_run_with_invalid_files_returns_422(self):
        """Confirms /run enforces validation internally and cannot be bypassed."""
        response = _post_run(binary_filename="wrong_name.TURX")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuth:
    def test_no_credentials_returns_401(self):
        response = client.post("/run")
        assert response.status_code == 401

    def test_wrong_password_returns_401(self):
        response = _post_run(auth=(settings.portal_user, "wrong"))
        assert response.status_code == 401

    def test_wrong_username_returns_401(self):
        response = _post_run(auth=("wrong", settings.portal_password))
        assert response.status_code == 401

    def test_valid_credentials_accepted(self):
        response = _post_run()
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Successful run
# ---------------------------------------------------------------------------

class TestRunSuccess:
    def test_returns_200(self):
        assert _post_run().status_code == 200

    def test_returns_zip_content_type(self):
        response = _post_run()
        assert response.headers["content-type"] == "application/zip"

    def test_returns_zip_with_correct_filename(self):
        response = _post_run()
        assert "rating_cycle_output.zip" in response.headers["content-disposition"]

    def test_zip_contains_rating_list(self):
        response = _post_run()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            assert "RatingList_after_1.csv" in zf.namelist()

    def test_zip_contains_audit_file(self):
        response = _post_run()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            assert "Audit_of_Tournament_1.csv" in zf.namelist()

    def test_rating_list_has_correct_header(self):
        response = _post_run()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            content = zf.read("RatingList_after_1.csv").decode()
        assert content.splitlines()[0].startswith("Id_No")

    def test_audit_has_correct_header(self):
        response = _post_run()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            content = zf.read("Audit_of_Tournament_1.csv").decode()
        assert content.splitlines()[0].startswith("Id_Fexerj")

    def test_bom_encoded_csv_is_accepted(self):
        """utf-8-sig BOM prefix (common in Windows-exported CSVs) must be handled."""
        response = _post_run(players="\ufeff" + PLAYERS_CSV)
        assert response.status_code == 200

    def test_two_tournaments_zip_has_four_files(self):
        tournaments_csv = textwrap.dedent("""\
            Id;CbxId;Name;Date;Type;IsIrt;IsFexerj
            1;99999;Tournament 1;2025-01-01;RR;0;1
            2;99999;Tournament 2;2025-02-01;RR;0;1
        """)
        response = client.post(
            "/run",
            data={"first": 1, "count": 2},
            files=[
                ("players_csv",     ("players.csv",    PLAYERS_CSV.encode(),   "text/csv")),
                ("tournaments_csv", ("tournaments.csv", tournaments_csv.encode(), "text/csv")),
                ("binary_files",    ("1-99999.TURX",   TURX_DATA, "application/octet-stream")),
                ("binary_files",    ("2-99999.TURX",   TURX_DATA, "application/octet-stream")),
            ],
            auth=VALID_AUTH,
        )
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            names = zf.namelist()
        assert "RatingList_after_1.csv" in names
        assert "RatingList_after_2.csv" in names
        assert "Audit_of_Tournament_1.csv" in names
        assert "Audit_of_Tournament_2.csv" in names


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestRunValidation:
    def test_missing_binary_file_returns_422(self):
        response = _post_run(binary_filename="wrong_name.TURX")
        assert response.status_code == 422

    def test_out_of_range_first_returns_422(self):
        # first=99 but only tournament 1 exists → no output files
        response = _post_run(first=99, count=1)
        assert response.status_code == 422

    def test_invalid_tournament_type_returns_422(self):
        invalid_tournaments = "Id;CbxId;Name;Date;Type;IsIrt;IsFexerj\n1;99999;T1;2025-01-01;XX;0;1\n"
        response = _post_run(tournaments=invalid_tournaments)
        assert response.status_code == 422

    def test_player_missing_id_returns_422(self):
        tunx_data = (BINARY_DIR / 'swiss_system_18players.TUNX').read_bytes()
        # Minimal players CSV — doesn't need real players since it will
        # fail before looking them up (resolve_id raises on missing ID)
        tournaments_csv = "Id;CbxId;Name;Date;Type;IsIrt;IsFexerj\n1;12345;T1;2025-01-01;SS;0;1\n"
        response = client.post(
            "/run",
            data={"first": 1, "count": 1},
            files=[
                ("players_csv",     ("players.csv",    PLAYERS_CSV.encode(), "text/csv")),
                ("tournaments_csv", ("tournaments.csv", tournaments_csv.encode(), "text/csv")),
                ("binary_files",    ("1-12345.TUNX",   tunx_data, "application/octet-stream")),
            ],
            auth=VALID_AUTH,
        )
        assert response.status_code == 422
        assert "FEXERJ ID" in response.json()["detail"]
