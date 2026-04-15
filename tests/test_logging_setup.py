"""Tests for JSON/text log formatting and request id attachment."""
import json
import logging

from backend.logging_setup import JsonLinesFormatter, RequestIdFilter, TextConsoleFormatter
from backend.request_id import bind_request_id


def test_json_lines_formatter_includes_extra_fields() -> None:
    logger = logging.getLogger("backend.unit")
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        __file__,
        10,
        "hello",
        (),
        None,
        extra={"event": "test_event", "n": 3},
    )
    record.message = record.getMessage()
    assert RequestIdFilter().filter(record)
    payload = json.loads(JsonLinesFormatter().format(record))
    assert payload["message"] == "hello"
    assert payload["event"] == "test_event"
    assert payload["n"] == 3
    assert "request_id" not in payload


def test_json_lines_formatter_includes_request_id_when_bound() -> None:
    logger = logging.getLogger("backend.unit")
    record = logger.makeRecord(logger.name, logging.INFO, __file__, 10, "x", (), None)
    record.message = record.getMessage()
    with bind_request_id("client-req-abcdef12"):
        assert RequestIdFilter().filter(record)
        payload = json.loads(JsonLinesFormatter().format(record))
    assert payload["request_id"] == "client-req-abcdef12"


def test_text_formatter_includes_request_id_placeholder() -> None:
    logger = logging.getLogger("backend.unit")
    record = logger.makeRecord(logger.name, logging.INFO, __file__, 10, "ping", (), None)
    record.message = record.getMessage()
    assert RequestIdFilter().filter(record)
    line = TextConsoleFormatter().format(record)
    assert "[-]" in line
    assert "ping" in line
