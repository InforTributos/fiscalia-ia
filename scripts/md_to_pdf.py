import sys
import re
from fpdf import FPDF

MD_PATH = sys.argv[1] if len(sys.argv) > 1 else "docs/cliente/propuesta-desarrollo-fiscalia.md"
PDF_PATH = MD_PATH.replace(".md", ".pdf")

FONT_DIR = "C:/Windows/Fonts"
FONT_REG = f"{FONT_DIR}/calibri.ttf"
FONT_BOLD = f"{FONT_DIR}/calibrib.ttf"
FONT_ITALIC = f"{FONT_DIR}/calibrii.ttf"


class ProposalPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Calibri", "", FONT_REG)
        self.add_font("Calibri", "B", FONT_BOLD)
        self.add_font("Calibri", "I", FONT_ITALIC)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Calibri", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def title_main(self, text):
        self.set_font("Calibri", "B", 18)
        self.set_text_color(0, 51, 102)
        self.multi_cell(0, 10, text)
        self.set_draw_color(0, 51, 102)
        self.set_line_width(1)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(6)

    def h1(self, text):
        self.set_font("Calibri", "B", 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 51, 102)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def h2(self, text):
        self.set_font("Calibri", "B", 12)
        self.set_text_color(0, 51, 102)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h3(self, text):
        self.set_font("Calibri", "B", 11)
        self.set_text_color(42, 90, 138)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def p(self, text):
        self.set_font("Calibri", "", 10)
        self.set_text_color(26, 26, 26)
        self.multi_cell(0, 5.5, text)
        self.ln(1.5)

    def bullet(self, text, bold_prefix=""):
        self.set_font("Calibri", "", 10)
        self.set_text_color(26, 26, 26)
        x0 = self.get_x()
        self.cell(5, 5.5, "•")
        if bold_prefix:
            self.set_font("Calibri", "B", 10)
            self.set_text_color(0, 51, 102)
            self.write(5.5, bold_prefix)
            self.set_font("Calibri", "", 10)
            self.set_text_color(26, 26, 26)
            self.write(5.5, text)
        else:
            self.write(5.5, text)
        self.ln()

    def ordered(self, num, text, bold_prefix=""):
        self.set_font("Calibri", "", 10)
        self.set_text_color(26, 26, 26)
        self.cell(5, 5.5, f"{num}.")
        if bold_prefix:
            self.set_font("Calibri", "B", 10)
            self.set_text_color(0, 51, 102)
            self.write(5.5, bold_prefix)
            self.set_font("Calibri", "", 10)
            self.set_text_color(26, 26, 26)
            self.write(5.5, text)
        else:
            self.write(5.5, text)
        self.ln()
        self.ln(1)

    def table(self, headers, rows):
        col_w = (self.w - self.l_margin - self.r_margin) / len(headers)

        self.set_font("Calibri", "B", 9)
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        self.set_draw_color(200, 200, 200)
        for i, h in enumerate(headers):
            align = "C" if i > 0 else "L"
            self.cell(col_w, 8, h, border=1, fill=True, align=align)
        self.ln()

        self.set_font("Calibri", "", 9)
        self.set_text_color(26, 26, 26)
        fill = False
        for row in rows:
            if fill:
                self.set_fill_color(245, 247, 250)
            max_lines = 1
            cell_h = 7
            for i, cell in enumerate(row):
                align = "C" if i > 0 else "L"
                self.cell(col_w, cell_h, cell, border=1, fill=fill, align=align)
            self.ln()
            fill = not fill

    def blockquote(self, text):
        self.set_font("Calibri", "I", 10)
        self.set_text_color(60, 60, 60)
        self.set_fill_color(240, 244, 248)
        x0 = self.l_margin
        y0 = self.get_y()
        self.multi_cell(self.w - self.l_margin - self.r_margin, 5.5, text)
        y1 = self.get_y()
        self.set_draw_color(0, 51, 102)
        self.set_line_width(0.8)
        self.line(x0 + 1, y0 + 2, x0 + 1, y1 - 1)
        self.ln(3)


pdf = ProposalPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

with open(MD_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Replace emojis with text markers for PDF
content = content.replace("✅", "[OK] ").replace("🟡", "[PARCIAL] ") 

lines = content.split("\n")

# Remove metadata header
i = 0
# Skip blank lines at start
while i < len(lines) and not lines[i].strip():
    i += 1

found_title = False
while i < len(lines):
    line = lines[i].rstrip()

    if not line:
        i += 1
        continue

    # Separator
    if re.match(r"^[-_*]{3,}$", line):
        i += 1
        continue

    # Title (h1)
    if re.match(r"^# [^#]", line):
        if not found_title:
            pdf.title_main(re.sub(r"^# ", "", line))
            found_title = True
        else:
            pdf.h1(re.sub(r"^# ", "", line))
        i += 1
        continue

    # h2
    if re.match(r"^## [^#]", line):
        pdf.h1(re.sub(r"^## ", "", line))
        i += 1
        continue

    # h3
    if re.match(r"^### [^#]", line):
        pdf.h2(re.sub(r"^### ", "", line))
        i += 1
        continue

    # Bold metadata lines
    if line.startswith("**Pre") or line.startswith("**Pro") or line.startswith("**Fec"):
        pdf.p(line.replace("**", ""))
        i += 1
        continue

    # Blockquote
    if line.startswith(">"):
        text = re.sub(r"^> ?", "", line)
        i += 1
        while i < len(lines) and lines[i].strip().startswith(">"):
            text += " " + re.sub(r"^> ?", "", lines[i].strip())
            i += 1
        pdf.blockquote(text)
        continue

    # Table
    if line.startswith("|") and "|" in line:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if i + 1 < len(lines) and re.match(r"^[\|\-\s:]+$", lines[i + 1].strip()):
            headers = cells
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
                rows.append(row)
                i += 1
            pdf.table(headers, rows)
            pdf.ln(2)
        else:
            i += 1
        continue

    # Unordered list
    m = re.match(r"^[\-\*]\s(.+)", line)
    if m:
        text = m.group(1)
        bm = re.match(r"\*\*(.+?)\*\*\s*[—–\-]?\s*(.*)", text)
        if bm:
            pdf.bullet(bm.group(2), bold_prefix=bm.group(1) + " ")
        else:
            pdf.bullet(text)
        i += 1
        continue

    # Ordered list
    m = re.match(r"^(\d+)\.\s(.+)", line)
    if m:
        num, text = m.group(1), m.group(2)
        bm = re.match(r"\*\*(.+?)\*\*\s*[—–\-]?\s*(.*)", text)
        if bm:
            pdf.ordered(num, bm.group(2), bold_prefix=bm.group(1) + " ")
        else:
            pdf.ordered(num, text)
        i += 1
        continue

    # Regular paragraph
    text = line.replace("**", "").replace("*", "").replace("—", " - ").replace("–", "-")
    pdf.p(text)
    i += 1


pdf.output(PDF_PATH)
print(f"PDF generado: {PDF_PATH}")
