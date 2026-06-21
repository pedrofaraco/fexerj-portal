"""Decode uploaded CSV bytes from multipart forms."""


def decode_csv_upload(raw: bytes, filename: str) -> str:
    """Decode CSV upload bytes.

    Tries UTF-8 with BOM first, then Windows-1252 (common Excel export on
    Windows in Brazil).

    Raises:
        ValueError: When no supported encoding applies (message is user-facing).
    """
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    msg = (
        f"{filename}: codificação inválida — salve o arquivo em UTF-8 "
        '(no Excel: "Salvar como" → "CSV UTF-8 (delimitado por vírgula)").'
    )
    raise ValueError(msg)
