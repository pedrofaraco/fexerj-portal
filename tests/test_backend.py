"""Tests for the FastAPI backend (/health, /me, /validate, and /run endpoints)."""
import asyncio
import io
import pathlib
import re
import textwrap
import uuid
import zipfile

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.config import settings
from backend.main import _RunConcurrencyGuard, app

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
    Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
    1;99999;Test RR Tournament;2025-01-01;RR;0;1
""")

VALID_AUTH = (settings.portal_user, settings.portal_password)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_singleton_run_guard():
    """Keep module-level `_run_busy` idle between tests (covers 503 paths that skip `leave`)."""
    main_module._run_busy._busy = False
    yield
    main_module._run_busy._busy = False


@pytest.fixture
def upload_limit_1_mib(monkeypatch):
    """Temporarily cap POST /validate and /run body size to 1 MiB for 413 tests."""
    monkeypatch.setattr(main_module.settings, "portal_max_upload_megabytes", 1)


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


def _parse_csv_from_zip(zip_bytes, filename, *, skip_lines=1):
    """Return data rows (header excluded) as semicolon-split lists.

    Args:
        zip_bytes: Full zip file bytes.
        filename: Entry name inside the zip.
        skip_lines: Number of leading lines to skip (1 for normal CSV header, 2 for audit preamble+header).
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        content = zf.read(filename).decode()
    return [line.split(';') for line in content.splitlines()[skip_lines:] if line]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}

    def test_health_echoes_x_request_id(self):
        response = client.get("/health")
        assert response.status_code == 200
        rid = response.headers.get("X-Request-ID")
        assert rid
        assert uuid.UUID(rid)  # server-generated UUID string

    def test_health_respects_valid_client_request_id(self):
        client_id = "abcdefgh"  # 8 chars, allowed pattern
        response = client.get("/health", headers={"X-Request-ID": client_id})
        assert response.headers.get("X-Request-ID") == client_id

    def test_health_accepts_x_correlation_id_alias(self):
        client_id = "abcdefgh"
        response = client.get("/health", headers={"X-Correlation-ID": client_id})
        assert response.headers.get("X-Request-ID") == client_id

    def test_health_replaces_invalid_request_id(self):
        response = client.get("/health", headers={"X-Request-ID": "bad"})
        rid = response.headers.get("X-Request-ID")
        assert rid
        assert rid != "bad"
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            rid,
            flags=re.IGNORECASE,
        )

    def test_health_does_not_require_auth(self):
        """Health endpoint must be publicly accessible for uptime monitoring."""
        response = client.get("/health")
        assert response.status_code == 200


class TestRunConcurrencyGuard:
    def test_guard_try_enter_fails_while_held(self):
        async def exercise():
            guard = _RunConcurrencyGuard()
            assert await guard.try_enter() is True
            assert await guard.try_enter() is False
            await guard.leave()
            assert await guard.try_enter() is True
            await guard.leave()

        asyncio.run(exercise())

    def test_returns_503_when_run_already_in_progress(self, monkeypatch):
        monkeypatch.setattr(main_module._run_busy, "_busy", True)
        response = _post_run()
        assert response.status_code == 503

    def test_503_includes_retry_after_header(self, monkeypatch):
        monkeypatch.setattr(main_module._run_busy, "_busy", True)
        response = _post_run()
        assert response.headers.get("retry-after") is not None

    def test_503_detail_mentions_execution_in_progress(self, monkeypatch):
        monkeypatch.setattr(main_module._run_busy, "_busy", True)
        response = _post_run()
        assert "andamento" in response.json()["detail"]

    def test_run_clears_busy_flag_after_success(self):
        _post_run()
        assert main_module._run_busy._busy is False

    def test_run_clears_busy_flag_after_error(self, monkeypatch):
        class _FailingCycle:
            def __init__(self, **kwargs):
                pass

            def run_cycle(self):
                raise ValueError("boom")

        monkeypatch.setattr(main_module, "FexerjRatingCycle", _FailingCycle)
        _post_run()
        assert main_module._run_busy._busy is False


# ---------------------------------------------------------------------------
# Validate endpoint
# ---------------------------------------------------------------------------

class TestUploadBodyLimit:
    def test_validate_returns_413_when_content_length_exceeds_limit(self, upload_limit_1_mib):
        limit = main_module.settings.portal_max_upload_bytes
        response = client.post(
            "/validate",
            data={"first": "1", "count": "1"},
            files=[
                ("players_csv", ("players.csv", PLAYERS_CSV.encode(), "text/csv")),
                ("tournaments_csv", ("tournaments.csv", TOURNAMENTS_CSV.encode(), "text/csv")),
                ("binary_files", ("1-99999.TURX", TURX_DATA, "application/octet-stream")),
            ],
            headers={"Content-Length": str(limit + 1)},
            auth=VALID_AUTH,
        )
        assert response.status_code == 413
        assert "MiB" in response.json()["detail"]

    def test_run_returns_413_when_content_length_exceeds_limit(self, upload_limit_1_mib):
        limit = main_module.settings.portal_max_upload_bytes
        response = client.post(
            "/run",
            data={"first": "1", "count": "1"},
            files=[
                ("players_csv", ("players.csv", PLAYERS_CSV.encode(), "text/csv")),
                ("tournaments_csv", ("tournaments.csv", TOURNAMENTS_CSV.encode(), "text/csv")),
                ("binary_files", ("1-99999.TURX", TURX_DATA, "application/octet-stream")),
            ],
            headers={"Content-Length": str(limit + 1)},
            auth=VALID_AUTH,
        )
        assert response.status_code == 413
        assert "limite" in response.json()["detail"].lower()


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
        assert any("não encontrado" in e for e in errors)

    def test_invalid_tournament_type_returns_error_list(self):
        invalid = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n1;99999;T1;2025-01-01;XX;0;1\n"
        response = _post_validate(tournaments=invalid)
        assert response.status_code == 200
        errors = response.json()["errors"]
        assert any("XX" in e for e in errors)

    def test_binary_file_with_missing_player_id_returns_error_list(self):
        tunx_data = (BINARY_DIR / "swiss_system_18players.TUNX").read_bytes()
        tournaments = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n1;12345;T1;2025-01-01;SS;0;1\n"
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
        assert any("ID FEXERJ" in e for e in errors)

    def test_run_with_invalid_files_returns_422(self):
        """Confirms /run enforces validation internally and cannot be bypassed."""
        response = _post_run(binary_filename="wrong_name.TURX")
        assert response.status_code == 422

    def test_first_zero_returns_422(self):
        """first=0 is out of bounds — tournaments are 1-based."""
        response = _post_validate(first=0)
        assert response.status_code == 422

    def test_first_negative_returns_422(self):
        response = _post_validate(first=-1)
        assert response.status_code == 422

    def test_count_zero_returns_422(self):
        response = _post_validate(count=0)
        assert response.status_code == 422

    def test_count_negative_returns_422(self):
        response = _post_validate(count=-1)
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
# /me endpoint
# ---------------------------------------------------------------------------

class TestMeEndpoint:
    def test_returns_200_with_valid_auth(self):
        response = client.get("/me", auth=VALID_AUTH)
        assert response.status_code == 200

    def test_returns_ok_true_body(self):
        response = client.get("/me", auth=VALID_AUTH)
        assert response.json() == {"ok": True}

    def test_returns_401_without_credentials(self):
        response = client.get("/me")
        assert response.status_code == 401

    def test_returns_401_with_wrong_password(self):
        response = client.get("/me", auth=(settings.portal_user, "wrong"))
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Successful run
# ---------------------------------------------------------------------------

class TestRunSuccess:
    def test_returns_200(self):
        assert _post_run().status_code == 200

    def test_returns_zip_content_type(self):
        response = _post_run()
        assert response.headers["content-type"] == "application/zip"

    def test_returns_x_request_id_header(self):
        response = _post_run()
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID")

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
        assert content.splitlines()[1].startswith("Id_Fexerj")

    def test_audit_has_version_preamble(self):
        response = _post_run()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            content = zf.read("Audit_of_Tournament_1.csv").decode()
        assert content.splitlines()[0] == "# audit_v1"

    def test_bom_encoded_csv_is_accepted(self):
        """utf-8-sig BOM prefix (common in Windows-exported CSVs) must be handled."""
        response = _post_run(players="\ufeff" + PLAYERS_CSV)
        assert response.status_code == 200

    def test_two_tournaments_zip_has_four_files(self):
        tournaments_csv = textwrap.dedent("""\
            Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
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
# Rating value verification (end-to-end)
# ---------------------------------------------------------------------------

class TestRunRatingValues:
    """Verify computed rating values through the full HTTP stack."""

    def test_rating_list_has_all_players(self):
        """All 6 round-robin players must appear in the output rating list."""
        response = _post_run()
        rows = _parse_csv_from_zip(response.content, "RatingList_after_1.csv")
        assert len(rows) == 6

    def test_all_new_ratings_in_valid_range(self):
        """Every new rating must be a plausible integer (100 – 3500)."""
        response = _post_run()
        rows = _parse_csv_from_zip(response.content, "RatingList_after_1.csv")
        for row in rows:
            new_rtg = int(row[4])  # Rtg_Nat column
            assert 100 <= new_rtg <= 3500

    def test_audit_each_player_played_at_least_one_game(self):
        """Every player in a round-robin must have at least one valid rated game (N >= 1)."""
        response = _post_run()
        rows = _parse_csv_from_zip(response.content, "Audit_of_Tournament_1.csv", skip_lines=2)
        for row in rows:
            assert int(row[7]) >= 1  # N column: valid games in this tournament

    def test_new_total_games_exceeds_prior_for_active_players(self):
        """Players with valid games must have a higher game count in the output rating list."""
        response = _post_run()
        audit_rows = _parse_csv_from_zip(response.content, "Audit_of_Tournament_1.csv", skip_lines=2)
        rl_rows = _parse_csv_from_zip(response.content, "RatingList_after_1.csv")
        new_games_by_id = {int(row[0]): int(row[9]) for row in rl_rows}  # Id_No → TotalNumGames
        for row in audit_rows:
            pid = int(row[0])         # Id_Fexerj
            n_valid = int(row[7])     # N: valid games in tournament
            ind_before = int(row[4])  # Ind: total games before
            if n_valid > 0:
                assert new_games_by_id[pid] > ind_before


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestRunValidation:
    def test_cycle_valueerror_returns_422_with_string_detail(self, monkeypatch):
        """FexerjRatingCycle.run_cycle ValueError is mapped to 422 (not a validation list)."""

        class _FailingCycle:
            def __init__(self, **kwargs):
                pass

            def run_cycle(self):
                raise ValueError("simulated cycle failure")

        monkeypatch.setattr(main_module, "FexerjRatingCycle", _FailingCycle)
        response = _post_run()
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        assert "Erro ao processar ciclo de rating" in detail
        assert "simulated cycle failure" in detail

    def test_missing_binary_file_returns_422(self):
        response = _post_run(binary_filename="wrong_name.TURX")
        assert response.status_code == 422

    def test_out_of_range_first_returns_422(self):
        # first=99 but only tournament 1 exists → no output files
        response = _post_run(first=99, count=1)
        assert response.status_code == 422

    def test_invalid_tournament_type_returns_422(self):
        invalid_tournaments = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n1;99999;T1;2025-01-01;XX;0;1\n"
        response = _post_run(tournaments=invalid_tournaments)
        assert response.status_code == 422

    def test_run_first_zero_returns_422(self):
        """first=0 is invalid on /run — must be >= 1."""
        response = _post_run(first=0)
        assert response.status_code == 422

    def test_run_count_zero_returns_422(self):
        """count=0 is invalid on /run — must be >= 1."""
        response = _post_run(count=0)
        assert response.status_code == 422

    def test_run_validation_returns_list_of_all_errors(self):
        """POST /run uses the same error list as validation — not only the first message."""
        players = textwrap.dedent("""\
            Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
            100;;; ;1800;CLUB A;01/01/1980;M;BRA;50;0;0
            200;;; ;1900;CLUB B;01/01/1975;M;BRA;80;0;0
        """)
        response = _post_run(players=players)
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert len(detail) >= 2
        assert all(isinstance(e, str) for e in detail)

    def test_player_missing_id_returns_422(self):
        tunx_data = (BINARY_DIR / 'swiss_system_18players.TUNX').read_bytes()
        # Minimal players CSV — doesn't need real players since it will
        # fail before looking them up (resolve_id raises on missing ID)
        tournaments_csv = "Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj\n1;12345;T1;2025-01-01;SS;0;1\n"
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
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any("ID FEXERJ" in e for e in detail)
