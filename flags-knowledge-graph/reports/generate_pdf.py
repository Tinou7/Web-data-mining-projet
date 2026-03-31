"""
Converts final_report.md to final_report.pdf using fpdf2.
Run from: flags-knowledge-graph/
    python reports/generate_pdf.py
"""

import re
from fpdf import FPDF

REPORT_MD = "reports/final_report.md"
REPORT_PDF = "reports/final_report.pdf"

# ---- PDF class ----

class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, "Flags Knowledge Graph - Final Report", align="R")
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


def parse_and_render(pdf, lines):
    in_table = False
    table_rows = []
    in_code = False
    code_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code block
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
                i += 1
                continue
            else:
                # Render code block
                pdf.set_font("Courier", size=7.5)
                pdf.set_fill_color(245, 245, 245)
                pdf.set_draw_color(200, 200, 200)
                pdf.set_x(14)
                block = "\n".join(code_lines)
                pdf.multi_cell(
                    182, 4.5, block,
                    border=1, fill=True, align="L"
                )
                pdf.ln(2)
                in_code = False
                code_lines = []
                i += 1
                continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Table row
        if line.startswith("|"):
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            # Skip separator rows (---|---)
            if all(re.match(r"^[-:]+$", p) for p in parts if p):
                i += 1
                continue
            table_rows.append(parts)
            in_table = True
            i += 1
            # Look ahead: if next line is not a table row, flush
            if i >= len(lines) or not lines[i].startswith("|"):
                render_table(pdf, table_rows)
                table_rows = []
                in_table = False
            continue

        if in_table:
            render_table(pdf, table_rows)
            table_rows = []
            in_table = False

        # Headings
        if line.startswith("#### "):
            pdf.ln(1)
            pdf.set_font("Helvetica", "BI", 10)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 6, line[5:].strip())
            pdf.set_text_color(0, 0, 0)

        elif line.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "BI", 11)
            pdf.set_text_color(40, 40, 120)
            pdf.multi_cell(0, 6, line[4:].strip())
            pdf.set_text_color(0, 0, 0)

        elif line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(0, 0, 150)
            pdf.multi_cell(0, 8, line[3:].strip())
            pdf.set_draw_color(0, 0, 150)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(2)
            pdf.set_text_color(0, 0, 0)
            pdf.set_draw_color(0, 0, 0)

        elif line.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 10, line[2:].strip())
            pdf.ln(2)

        elif line.startswith("- ") or line.startswith("* "):
            pdf.set_font("Helvetica", size=9)
            pdf.set_x(16)
            pdf.cell(4, 5, chr(149))  # bullet
            pdf.set_x(20)
            text = clean_inline(line[2:].strip())
            pdf.multi_cell(175, 5, text)

        elif re.match(r"^\d+\. ", line):
            pdf.set_font("Helvetica", size=9)
            m = re.match(r"^(\d+)\. (.+)", line)
            if m:
                pdf.set_x(16)
                pdf.cell(6, 5, m.group(1) + ".")
                pdf.set_x(22)
                pdf.multi_cell(173, 5, clean_inline(m.group(2)))

        elif line.strip() == "" or line.strip() == "---":
            pdf.ln(2)

        elif line.startswith("> "):
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.set_text_color(80, 80, 80)
            pdf.set_x(16)
            pdf.set_fill_color(240, 240, 255)
            pdf.multi_cell(178, 5, clean_inline(line[2:].strip()), fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

        else:
            # Normal paragraph
            if line.strip():
                pdf.set_font("Helvetica", size=9.5)
                pdf.multi_cell(0, 5.5, clean_inline(line.strip()))
                pdf.ln(1)

        i += 1


def clean_inline(text):
    # Remove bold/italic markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Remove markdown links [text](url) → text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Replace special unicode chars not supported by latin-1 fonts
    replacements = {
        "\u2014": "-",  # em dash
        "\u2013": "-",  # en dash
        "\u2019": "'",  # right single quote
        "\u2018": "'",  # left single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2192": "->", # arrow
        "\u2248": "~=", # approximately equal
        "\u2265": ">=", # greater or equal
        "\u2264": "<=", # less or equal
        "\u00d7": "x",  # multiplication
        "\u2022": "-",  # bullet
        "\u00e9": "e",  # e accent
        "\u00e8": "e",
        "\u00ea": "e",
        "\u00e0": "a",
        "\u00e2": "a",
        "\u00ee": "i",
        "\u00f4": "o",
        "\u00fb": "u",
        "\u00e7": "c",
        "\u00c9": "E",
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Final fallback: encode to latin-1, replacing unknowns
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text


def render_table(pdf, rows):
    if not rows:
        return
    pdf.ln(1)
    n_cols = len(rows[0])
    if n_cols == 0:
        return

    # Column widths
    available = 182
    col_w = available / n_cols

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 220, 240)
    pdf.set_draw_color(150, 150, 150)

    # Header row
    header = rows[0]
    for cell in header:
        pdf.cell(col_w, 5.5, clean_inline(cell)[:40], border=1, fill=True, align="C")
    pdf.ln()

    # Data rows
    pdf.set_font("Helvetica", size=7.5)
    pdf.set_fill_color(255, 255, 255)
    for ri, row in enumerate(rows[1:]):
        fill = (ri % 2 == 0)
        if fill:
            pdf.set_fill_color(245, 245, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        for ci, cell in enumerate(row):
            if ci < n_cols:
                pdf.cell(col_w, 5, clean_inline(cell)[:50], border=1, fill=True)
        pdf.ln()

    pdf.ln(2)


# ---- Main ----

UNICODE_MAP = {
    "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
    "\u201c": '"', "\u201d": '"', "\u2192": "->", "\u2248": "~=",
    "\u2265": ">=", "\u2264": "<=", "\u00d7": "x", "\u2022": "-",
    "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00e0": "a",
    "\u00e2": "a", "\u00ee": "i", "\u00f4": "o", "\u00fb": "u",
    "\u00e7": "c", "\u00c9": "E", "\u00e1": "a", "\u00ed": "i",
    "\u00f3": "o", "\u00fa": "u", "\u00f1": "n", "\u00e4": "a",
    "\u00f6": "o", "\u00fc": "u", "\u00df": "ss", "\u2026": "...",
    "\u00b0": " deg", "\u00b7": ".", "\u2248": "~",
}

def sanitize(text):
    for char, repl in UNICODE_MAP.items():
        text = text.replace(char, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")

with open(REPORT_MD, encoding="utf-8") as f:
    raw = f.read()

# Pre-sanitize entire file
for char, repl in UNICODE_MAP.items():
    raw = raw.replace(char, repl)
# Replace logical/math symbols common in SWRL
raw = raw.replace("\u2227", "^").replace("\u2228", "v").replace("\u00ac", "~")
raw = raw.replace("\u2200", "forall").replace("\u2203", "exists")
raw = raw.replace("\u00d7", "x").replace("\u00f7", "/")
# Final blanket: encode latin-1, replace anything remaining
raw = raw.encode("latin-1", errors="replace").decode("latin-1")
lines = raw.splitlines()

pdf = ReportPDF(orientation="P", unit="mm", format="A4")
pdf.set_margins(10, 15, 10)
pdf.set_auto_page_break(auto=True, margin=14)
pdf.add_page()

parse_and_render(pdf, lines)

pdf.output(REPORT_PDF)
print(f"PDF generated: {REPORT_PDF}")
