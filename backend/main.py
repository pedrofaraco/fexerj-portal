"""FEXERJ Portal FastAPI application.

Exposes authenticated endpoints:

- ``GET  /health``   — unauthenticated health check for uptime monitoring.
- ``GET  /me``       — validate credentials without performing any action.
- ``POST /validate`` — validates the input files and returns a JSON list of
  errors without running the calculation.
- ``POST /run``      — validates inputs, runs the FEXERJ rating cycle, and
  returns a zip archive containing one rating-list CSV and one audit CSV per
  processed tournament.
"""
import asyncio
import io
import logging
import secrets
import zipfile
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.config import settings
from backend.logging_setup import configure_logging
from backend.request_id import request_id_middleware
from backend.validator import validate_inputs
from calculator import FexerjRatingCycle

configure_logging(json_logs=settings.portal_json_logs)
logger = logging.getLogger(__name__)

app = FastAPI(title="Portal FEXERJ")
# auto_error=False prevents FastAPI from sending WWW-Authenticate: Basic on
# 401 responses, which would cause browsers to show their native auth dialog.
_security = HTTPBasic(auto_error=False)

_UPLOAD_PATHS = frozenset({"/validate", "/run"})


class _RunConcurrencyGuard:
    """At most one concurrent POST /run; additional requests fail fast with 503."""

    __slots__ = ("_busy", "_lock")

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._busy = False

    async def try_enter(self) -> bool:
        async with self._lock:
            if self._busy:
                return False
            self._busy = True
            return True

    async def leave(self) -> None:
        async with self._lock:
            self._busy = False


_run_busy = _RunConcurrencyGuard()


@app.middleware("http")
async def limit_upload_body(request: Request, call_next):
    """Reject oversized multipart uploads before the body is fully parsed."""
    if request.method != "POST" or request.url.path not in _UPLOAD_PATHS:
        return await call_next(request)
    max_bytes = settings.portal_max_upload_bytes
    cl = request.headers.get("content-length")
    if cl is None:
        # Chunked transfer or missing Content-Length: nginx enforces
        # client_max_body_size upstream, so this path is unreachable in the
        # docker nginx→backend topology. Keeps defense-in-depth for direct
        # backend access (e.g. tests, local dev without nginx).
        return await call_next(request)
    try:
        content_length = int(cl)
    except ValueError:
        logger.warning(
            "Invalid Content-Length on %s: %r",
            request.url.path,
            cl,
            extra={"event": "invalid_content_length", "path": request.url.path, "header_value": cl},
        )
        return await call_next(request)
    if content_length > max_bytes:
        mib = settings.portal_max_upload_megabytes
        logger.warning(
            "Rejected %s: Content-Length %d exceeds limit %d bytes",
            request.url.path,
            content_length,
            max_bytes,
            extra={
                "event": "upload_rejected",
                "path": request.url.path,
                "content_length": content_length,
                "limit_bytes": max_bytes,
            },
        )
        return JSONResponse(
            status_code=413,
            content={
                "detail": (
                    f"Corpo da requisição excede o limite permitido ({mib} MiB). "
                    "Reduza o tamanho dos arquivos ou peça ao administrador para aumentar o limite."
                )
            },
        )
    return await call_next(request)


app.middleware("http")(request_id_middleware)


def require_auth(credentials: HTTPBasicCredentials | None = Depends(_security)) -> None:
    """FastAPI dependency that enforces HTTP Basic authentication."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais obrigatórias")
    user_ok = secrets.compare_digest(
        credentials.username.encode(), settings.portal_user.encode()
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode(), settings.portal_password.encode()
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
        )


@app.get("/health")
async def health() -> dict:
    """Unauthenticated health check for uptime monitoring.

    Returns ``{"status": "ok"}`` whenever the service is running.
    """
    return {"status": "ok"}


@app.get("/me")
async def me(_: None = Depends(require_auth)) -> dict:
    """Validate credentials without performing any action.

    Returns ``{"ok": true}`` when credentials are valid, or 401 otherwise.
    Used by the frontend to authenticate on login before showing the main screen.
    """
    return {"ok": True}


@app.post("/validate")
async def validate(
    first: Annotated[int, Form(ge=1, description="First tournament number to process (1-based)")],
    count: Annotated[int, Form(ge=1, description="Number of tournaments to process")],
    players_csv: UploadFile = File(..., description="Initial rating list CSV (players.csv)"),
    tournaments_csv: UploadFile = File(..., description="Tournament list CSV (tournaments.csv)"),
    binary_files: list[UploadFile] = File(..., description="Binary tournament files (.TUNX/.TURX/.TUMX)"),
    _: None = Depends(require_auth),
) -> dict:
    """Validate input files without running the rating cycle.

    Returns ``{"errors": [...]}`` where the list is empty when all inputs are
    valid.  The HTTP status is always 200 when the endpoint itself succeeds —
    the ``errors`` list carries validation results.
    """
    logger.info(
        "POST /validate — first=%d count=%d files=%d",
        first,
        count,
        len(binary_files),
        extra={
            "event": "validate_start",
            "path": "/validate",
            "first": first,
            "count": count,
            "binary_file_count": len(binary_files),
        },
    )
    players_content = (await players_csv.read()).decode("utf-8-sig")
    tournaments_content = (await tournaments_csv.read()).decode("utf-8-sig")
    binary_files_dict: dict[str, bytes] = {
        f.filename: await f.read() for f in binary_files if f.filename is not None
    }

    errors = validate_inputs(players_content, tournaments_content, binary_files_dict, first, count)
    logger.info(
        "POST /validate — %d error(s) found",
        len(errors),
        extra={"event": "validate_done", "path": "/validate", "error_count": len(errors)},
    )
    return {"errors": errors}


@app.post("/run")
async def run(
    first: Annotated[int, Form(ge=1, description="First tournament number to process (1-based)")],
    count: Annotated[int, Form(ge=1, description="Number of tournaments to process")],
    players_csv: UploadFile = File(..., description="Initial rating list CSV (players.csv)"),
    tournaments_csv: UploadFile = File(..., description="Tournament list CSV (tournaments.csv)"),
    binary_files: list[UploadFile] = File(..., description="Binary tournament files (.TUNX/.TURX/.TUMX)"),
    _: None = Depends(require_auth),
) -> StreamingResponse:
    """Run a FEXERJ rating cycle and return results as a zip archive.

    The returned zip contains ``RatingList_after_N.csv`` and
    ``Audit_of_Tournament_N.csv`` for each processed tournament.

    When input validation fails (same rules as ``POST /validate``), the response
    is **422** with ``detail`` set to the **full list** of error strings, not
    only the first one.
    """
    if not await _run_busy.try_enter():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Uma execução já está em andamento. Tente novamente em instantes.",
            headers={"Retry-After": "5"},
        )
    try:
        logger.info(
            "POST /run — first=%d count=%d files=%d",
            first,
            count,
            len(binary_files),
            extra={
                "event": "run_start",
                "path": "/run",
                "first": first,
                "count": count,
                "binary_file_count": len(binary_files),
            },
        )
        players_content = (await players_csv.read()).decode("utf-8-sig")
        tournaments_content = (await tournaments_csv.read()).decode("utf-8-sig")

        binary_files_dict: dict[str, bytes] = {
            f.filename: await f.read() for f in binary_files if f.filename is not None
        }

        errors = validate_inputs(players_content, tournaments_content, binary_files_dict, first, count)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=errors,
            )

        try:
            cycle = FexerjRatingCycle(
                tournaments_csv=tournaments_content,
                first_item=first,
                items_to_process=count,
                initial_rating_csv=players_content,
                binary_files=binary_files_dict,
            )
            output_files = cycle.run_cycle()
        except ValueError as e:
            logger.error(
                "Erro no ciclo de rating: %s",
                e,
                exc_info=True,
                extra={"event": "rating_cycle_failed", "path": "/run"},
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Erro ao processar ciclo de rating: {e}",
            ) from e

        if not output_files:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Nenhum torneio encontrado no intervalo primeiro={first}, quantidade={count}.",
            )

        logger.info(
            "POST /run — ciclo concluído, %d arquivo(s) gerados",
            len(output_files),
            extra={"event": "run_done", "path": "/run", "output_file_count": len(output_files)},
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, content in output_files.items():
                zf.writestr(filename, content)
        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=rating_cycle_output.zip"},
        )
    finally:
        await _run_busy.leave()
