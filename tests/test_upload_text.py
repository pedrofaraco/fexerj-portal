"""Tests for CSV upload decoding."""
from backend.upload_text import decode_csv_upload


class TestDecodeCsvUpload:
    def test_utf8_sig_is_accepted(self):
        raw = "Id_No;Name\n1;Test\n".encode("utf-8-sig")
        text, err = decode_csv_upload(raw, "players.csv")
        assert err is None
        assert text is not None
        assert text.startswith("Id_No")

    def test_cp1252_fallback_is_used(self):
        raw = "Id_No;Name\n1;Carlos\u00a0Mendes\n".encode("cp1252")
        text, err = decode_csv_upload(raw, "players.csv")
        assert err is None
        assert "Carlos\u00a0Mendes" in text
