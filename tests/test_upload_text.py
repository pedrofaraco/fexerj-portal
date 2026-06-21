"""Tests for CSV upload decoding."""

from backend.upload_text import decode_csv_upload


class TestDecodeCsvUpload:
    def test_utf8_sig_is_accepted(self):
        raw = "Id_No;Name\n1;Test\n".encode("utf-8-sig")
        assert decode_csv_upload(raw, "players.csv").startswith("Id_No")

    def test_cp1252_fallback_is_used(self):
        raw = "Id_No;Name\n1;Carlos\u00a0Mendes\n".encode("cp1252")
        assert "Carlos\u00a0Mendes" in decode_csv_upload(raw, "players.csv")
