"""Decode uploaded CSV bytes from multipart forms."""


def decode_csv_upload(raw: bytes, filename: str) -> tuple[str | None, str | None]:
    """Decode CSV upload bytes.

    Returns ``(text, None)`` on success or ``(None, error_message)`` when no
    supported encoding applies.

    Tries UTF-8 with BOM first, then Windows-1252 (common Excel export on
    Windows in Brazil).
    """
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return None, (
        f"{filename}: codificação inválida — salve o arquivo em UTF-8 "
        '(no Excel: "Salvar como" → "CSV UTF-8 (delimitado por vírgula)").'
    )
