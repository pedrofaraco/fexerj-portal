"""Builds the .docx of the rules document from its markdown source.

    python3 scripts/build-docx.py [source.md] [output.docx]

markdown -> HTML -> LibreOffice. Needs `soffice` and Python's `markdown`.

Column widths are computed here, from the content: left to itself, the
LibreOffice HTML importer squeezes short-titled columns and breaks
"Modalidade" in half. Pandoc was tried and rejected for this document -
it gives every column the same width, which is worse on a document with
twelve tables.

Verify what comes out before sending it anywhere:

    soffice --headless --convert-to pdf regras.docx

and look at the tables. A missing glyph (a hollow box) is the failure
that slips through unlooked-at - it is how a non-breaking hyphen in the
8.1.2 ranges was found.
"""
import pathlib, re, subprocess, sys, zipfile
from html.parser import HTMLParser
import markdown

REPO = pathlib.Path(__file__).resolve().parent.parent
MD = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'docs/modelo-rating-fide.md'
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else MD.with_suffix('.docx')
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

CSS = """
body { font-family: Calibri, Carlito, sans-serif; font-size: 11pt; line-height: 1.35; }
h1 { font-size: 20pt; margin-top: 18pt; }
h2 { font-size: 15pt; margin-top: 16pt; border-bottom: 1px solid #999; padding-bottom: 2pt; }
h3 { font-size: 12.5pt; margin-top: 12pt; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
th, td { border: 1px solid #808080; padding: 3pt 5pt; font-size: 10pt; vertical-align: top; }
th { background-color: #e8e8e8; text-align: left; }
code { font-family: "Courier New", monospace; font-size: 9.5pt; }
pre { font-family: "Courier New", monospace; font-size: 9.5pt; background-color: #f4f4f4;
      border: 1px solid #ccc; padding: 6pt; }
blockquote { border-left: 3pt solid #999; margin-left: 0; padding-left: 10pt; color: #333; }
hr { border: none; border-top: 1px solid #bbb; }
"""

class Cells(HTMLParser):
    """Texto de cada celula, linha a linha."""
    def __init__(self):
        super().__init__(); self.rows = []; self.cur = None; self.buf = None
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.cur = []
        elif tag in ("td", "th"): self.buf = []
    def handle_endtag(self, tag):
        if tag == "tr" and self.cur is not None:
            self.rows.append(self.cur); self.cur = None
        elif tag in ("td", "th") and self.buf is not None:
            if self.cur is not None: self.cur.append("".join(self.buf).strip())
            self.buf = None
    def handle_data(self, data):
        if self.buf is not None: self.buf.append(data)

def colgroup(table_html):
    """Larguras proporcionais a maior celula de cada coluna.

    A raiz quadrada comprime a escala: sem ela, uma coluna de frase longa
    engole as vizinhas numericas e o numero fica espremido contra a borda.
    """
    parser = Cells(); parser.feed(table_html)
    rows = [r for r in parser.rows if r]
    if not rows: return ""
    n = max(len(r) for r in rows)
    widths = []
    for i in range(n):
        longest = max((len(r[i]) for r in rows if len(r) > i), default=1)
        widths.append(max(longest, 3) ** 0.5)
    total = sum(widths)
    pct = [100 * w / total for w in widths]
    # Piso de 6%: coluna de uma letra ("K") ainda precisa caber o titulo.
    pct = [max(p, 6.0) for p in pct]
    total = sum(pct)
    pct = [100 * p / total for p in pct]
    return "<colgroup>" + "".join(f'<col style="width:{p:.1f}%" />' for p in pct) + "</colgroup>"

def add_colgroups(html):
    def repl(m):
        table = m.group(0)
        return table.replace("<table>", "<table>" + colgroup(table), 1)
    return re.sub(r"<table>.*?</table>", repl, html, flags=re.S)

body = markdown.markdown(MD.read_text(),
                         extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'])
body = add_colgroups(body)
html = (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
        f'<title>{MD.stem}</title><style>{CSS}</style></head><body>\n{body}\n</body></html>')
tmp = pathlib.Path("_build.html"); tmp.write_text(html, encoding="utf-8")

subprocess.run([SOFFICE, "--headless", "--infilter=HTML (StarWriter)",
                "--convert-to", "docx:MS Word 2007 XML", "--outdir", ".", str(tmp)],
               check=True, capture_output=True)
built = pathlib.Path("_build.docx")

# LibreOffice ignora o lang do HTML e marca tudo como en-US; o corretor do
# Word sublinharia o documento inteiro.
zin = zipfile.ZipFile(built)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename in ("word/styles.xml", "word/document.xml"):
            data = data.decode("utf-8").replace('w:val="en-US"', 'w:val="pt-BR"').encode("utf-8")
        zout.writestr(item, data)
zin.close()
print(f"{OUT} ok")
