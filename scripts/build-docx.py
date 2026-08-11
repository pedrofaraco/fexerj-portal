"""Builds the .docx of the rules document from its markdown source.

    python3 scripts/build-docx.py [source.md] [output.docx]

markdown -> HTML -> LibreOffice -> a pass over the OOXML. Needs `soffice`
and Python's `markdown` (in requirements-dev.txt).

The last step is not optional. LibreOffice's HTML importer sizes a table to
its content and ignores CSS widths: the two-column modality table came out
1623 twips wide, which breaks "Modalidade" across two lines. Word then
re-flows whatever it is given, so widths have to be stated the way Word
obeys them - a fixed layout, an explicit grid, and an explicit width on
every cell. Rows are also marked unbreakable, or a range like "198-206"
ends up with its halves on different pages.

Pandoc was tried and rejected for this document: it gives every column the
same width, which is worse on a document with twelve tables.

Verify what comes out before sending it anywhere - open the .docx in Word
if you can, since Word and LibreOffice disagree about tables:

    soffice --headless --convert-to pdf regras.docx

A hollow box is the failure that slips through unlooked-at: it is how a
non-breaking hyphen in the 8.1.2 ranges was found.
"""
import pathlib
import re
import subprocess
import sys
import zipfile
from html.parser import HTMLParser

import markdown

REPO = pathlib.Path(__file__).resolve().parent.parent
MD = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "docs/modelo-rating-fide.md"
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else MD.with_suffix(".docx")
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

# US Letter, as LibreOffice's HTML import sets it, with symmetric margins.
PAGE_WIDTH = 12240
MARGIN = 1134
PRINTABLE = PAGE_WIDTH - 2 * MARGIN

# Calibri 10pt: a character averages ~100 twips, bold a little more. Only
# used to keep a column from being narrower than its longest single word.
TWIPS_PER_CHAR = 112
CELL_PADDING = 160

CSS = """
body { font-family: Calibri, Carlito, sans-serif; font-size: 11pt; line-height: 1.35; }
h1 { font-size: 20pt; margin-top: 18pt; }
h2 { font-size: 15pt; margin-top: 16pt; border-bottom: 1px solid #999; padding-bottom: 2pt; }
h3 { font-size: 12.5pt; margin-top: 12pt; }
table { border-collapse: collapse; margin: 8pt 0; }
th, td { border: 1px solid #808080; padding: 3pt 5pt; font-size: 10pt; vertical-align: top; }
th { background-color: #e8e8e8; text-align: left; }
code { font-family: "Courier New", monospace; font-size: 9.5pt; }
pre { font-family: "Courier New", monospace; font-size: 9.5pt; background-color: #f4f4f4;
      border: 1px solid #ccc; padding: 6pt; }
blockquote { border-left: 3pt solid #999; margin-left: 0; padding-left: 10pt; color: #333; }
hr { border: none; border-top: 1px solid #bbb; }
"""


class Cells(HTMLParser):
    """The text of every cell, row by row."""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self.cur: list[str] | None = None
        self.buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.cur = []
        elif tag in ("td", "th"):
            self.buf = []

    def handle_endtag(self, tag):
        if tag == "tr" and self.cur is not None:
            self.rows.append(self.cur)
            self.cur = None
        elif tag in ("td", "th") and self.buf is not None:
            if self.cur is not None:
                self.cur.append("".join(self.buf).strip())
            self.buf = None

    def handle_data(self, data):
        if self.buf is not None:
            self.buf.append(data)


def column_widths(rows: list[list[str]]) -> list[int]:
    """Twips per column, summing to exactly the printable width.

    Each column first claims enough room for its longest unbreakable word —
    that is what keeps "Modalidade" and "198-206" on one line. What is left
    over is shared out by total content length, damped by a square root so a
    column of long sentences does not swallow its numeric neighbours.
    """
    columns = max(len(r) for r in rows)
    floors, weights = [], []
    for i in range(columns):
        texts = [r[i] for r in rows if len(r) > i]
        longest_word = max((len(w) for t in texts for w in t.split()), default=1)
        longest_text = max((len(t) for t in texts), default=1)
        floors.append(longest_word * TWIPS_PER_CHAR + CELL_PADDING)
        weights.append(max(longest_text, 3) ** 0.5)

    if sum(floors) >= PRINTABLE:
        # Too wide even at the minimum: scale down and accept some wrapping.
        scale = PRINTABLE / sum(floors)
        widths = [int(f * scale) for f in floors]
    else:
        spare = PRINTABLE - sum(floors)
        total_weight = sum(weights)
        widths = [
            int(f + spare * w / total_weight)
            for f, w in zip(floors, weights, strict=True)
        ]

    widths[-1] += PRINTABLE - sum(widths)  # absorb rounding
    return widths


def _cell_width(widths: list[int]):
    """Replacement callback that walks the cells in document order.

    Cells appear row by row, so cycling through the column widths lands each
    one on its own column.
    """
    column = iter(range(10**6))

    def replace(_match):
        return f'<w:tcW w:w="{widths[next(column) % len(widths)]}" w:type="dxa"/>'

    return replace


def size_tables(xml: str, tables: list[list[list[str]]]) -> str:
    """Writes the computed widths into every table, the way Word reads them."""
    blocks = list(re.finditer(r"<w:tbl>.*?</w:tbl>", xml, re.S))
    if len(blocks) != len(tables):
        raise SystemExit(f"{len(blocks)} tabelas no XML, {len(tables)} no HTML — abortando")

    out, last = [], 0
    for block, rows in zip(blocks, tables, strict=True):
        widths = column_widths(rows)
        table = block.group(0)

        table = re.sub(r'<w:tblW w:w="\d+" w:type="\w+"/>',
                       f'<w:tblW w:w="{PRINTABLE}" w:type="dxa"/>', table, count=1)
        table = re.sub(r"<w:tblGrid>.*?</w:tblGrid>",
                       "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
                       + "</w:tblGrid>", table, count=1, flags=re.S)
        # A row must not split across pages: half of "198-206" on the next
        # page is the worst of the failures this script exists to prevent.
        table = table.replace("<w:trPr>", "<w:trPr><w:cantSplit/>")
        table = re.sub(r"<w:tr>(?!<w:trPr>)", "<w:tr><w:trPr><w:cantSplit/></w:trPr>", table)

        table = re.sub(r'<w:tcW w:w="\d+" w:type="\w+"/>', _cell_width(widths), table)

        out.append(xml[last:block.start()])
        out.append(table)
        last = block.end()
    out.append(xml[last:])
    return "".join(out)


def set_margins(xml: str) -> str:
    """Symmetric margins; LibreOffice's HTML default is 2cm left, 1cm right."""
    return re.sub(r'<w:pgMar w:left="\d+" w:right="\d+"',
                  f'<w:pgMar w:left="{MARGIN}" w:right="{MARGIN}"', xml, count=1)


def main() -> None:
    body = markdown.markdown(
        MD.read_text(), extensions=["tables", "fenced_code", "sane_lists", "attr_list"]
    )
    tables = []
    for match in re.finditer(r"<table>.*?</table>", body, re.S):
        parser = Cells()
        parser.feed(match.group(0))
        tables.append([r for r in parser.rows if r])

    html = (
        f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
        f"<title>{MD.stem}</title><style>{CSS}</style></head><body>\n{body}\n</body></html>"
    )
    tmp = pathlib.Path("_build.html")
    tmp.write_text(html, encoding="utf-8")
    subprocess.run(
        [SOFFICE, "--headless", "--infilter=HTML (StarWriter)",
         "--convert-to", "docx:MS Word 2007 XML", "--outdir", ".", str(tmp)],
        check=True, capture_output=True,
    )

    built = pathlib.Path("_build.docx")
    zin = zipfile.ZipFile(built)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                text = size_tables(set_margins(data.decode("utf-8")), tables)
                data = text.replace('w:val="en-US"', 'w:val="pt-BR"').encode("utf-8")
            elif item.filename == "word/styles.xml":
                # LibreOffice ignores the HTML lang and marks everything
                # en-US; Word would underline the whole document.
                data = data.decode("utf-8").replace('w:val="en-US"', 'w:val="pt-BR"').encode("utf-8")
            zout.writestr(item, data)
    zin.close()
    tmp.unlink(missing_ok=True)
    built.unlink(missing_ok=True)
    print(f"{OUT} ok — {len(tables)} tabelas, largura útil {PRINTABLE} twips")


if __name__ == "__main__":
    main()
