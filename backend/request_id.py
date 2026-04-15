"""Per-request identifier for logs and tracing (``X-Request-ID``)."""
from __future__ import annotations

import contextvars
import re
import uuid
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager

from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_HEADER = "x-request-id"
_ALT_HEADER = "x-correlation-id"
# Safe passthrough: 8–64 chars, starts with alphanumeric (UUIDs and many proxies match).
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{7,63}$")

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "portal_request_id", default=None
)


def get_request_id() -> str | None:
    """Return the current request id, if any (set by middleware)."""
    return _request_id_var.get()


@contextmanager
def bind_request_id(rid: str) -> Iterator[None]:
    """Temporarily set the request id (tests and scripts)."""
    token = _request_id_var.set(rid)
    try:
        yield
    finally:
        _request_id_var.reset(token)


def _incoming_request_id(request: Request) -> str | None:
    raw = request.headers.get(_REQUEST_ID_HEADER) or request.headers.get(_ALT_HEADER)
    if raw is None:
        return None
    candidate = raw.strip()
    if _CLIENT_ID_RE.fullmatch(candidate):
        return candidate
    return None


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign ``X-Request-ID``, expose it to logging, and echo it on the response."""
    rid = _incoming_request_id(request) or str(uuid.uuid4())
    token = _request_id_var.set(rid)
    try:
        response = await call_next(request)
    finally:
        _request_id_var.reset(token)
    response.headers["X-Request-ID"] = rid
    return response
