"""FEXERJ Portal FastAPI application.

Exposes a single ``POST /run`` endpoint that accepts a players CSV, a
tournaments CSV, and one or more Swiss Manager binary files, then runs the
FEXERJ rating cycle and returns a zip archive containing one rating-list CSV
and one audit CSV per processed tournament.
"""
import io
import secrets
import zipfile

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from calculator import FexerjRatingCycle
from backend.config import settings

app = FastAPI(title="FEXERJ Portal")
_security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    """FastAPI dependency that enforces HTTP Basic authentication."""
    user_ok = secrets.compare_digest(
        credentials.username.encode(), settings.portal_user.encode()
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode(), settings.portal_password.encode()
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.post("/run")
async def run(
    players_csv: UploadFile = File(..., description="Initial rating list CSV (players.csv)"),
    tournaments_csv: UploadFile = File(..., description="Tournament list CSV (tournaments.csv)"),
    binary_files: list[UploadFile] = File(..., description="Binary tournament files (.TUNX/.TURX/.TUMX)"),
    first: int = Form(..., description="First tournament number to process (1-based)"),
    count: int = Form(..., description="Number of tournaments to process"),
    _: None = Depends(require_auth),
) -> StreamingResponse:
    """Run a FEXERJ rating cycle and return results as a zip archive.

    The returned zip contains ``RatingList_after_N.csv`` and
    ``Audit_of_Tournament_N.csv`` for each processed tournament.
    """
    players_content = (await players_csv.read()).decode("utf-8-sig")
    tournaments_content = (await tournaments_csv.read()).decode("utf-8-sig")

    binary_files_dict: dict[str, bytes] = {
        f.filename: await f.read() for f in binary_files
    }

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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    if not output_files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No tournaments found in range first={first}, count={count}.",
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
