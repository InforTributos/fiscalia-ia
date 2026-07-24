#!/usr/bin/env python3
"""Generate PDF from manual-implementacion-api.md using fpdf2."""

import re
from fpdf import FPDF

MD_PATH = "docs/manual-implementacion-api.md"
PDF_PATH = "docs/manual-implementacion-api.pdf"


FONT_DIR = "C:/Windows/Fonts"


class ManualPDF(FPDF):
    def __init__(self):
        super().__init__()
        # Register Unicode fonts
        self.add_font("Arial", "", FONT_DIR + "/arial.ttf", uni=True)
        self.add_font("Arial", "B", FONT_DIR + "/arialbd.ttf", uni=True)
        self.add_font("Arial", "I", FONT_DIR + "/ariali.ttf", uni=True)
        self.add_font("Arial", "BI", FONT_DIR + "/arialbi.ttf", uni=True)
        self.add_font("Mono", "", FONT_DIR + "/consola.ttf", uni=True)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Arial", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, "FiscalIA — Manual de Implementación API", align="C")
            self.ln(4)
            self.set_draw_color(200, 200, 200)
            self.line(20, 14, self.w - 20, 14)
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title, level=1):
        colors = {
            1: (13, 27, 42),
            2: (21, 101, 192),
            3: (46, 125, 50),
            4: (230, 81, 0),
        }
        r, g, b = colors.get(level, (0, 0, 0))
        sizes = {1: 16, 2: 13, 3: 11, 4: 10}
        sz = sizes.get(level, 10)

        self.set_font("Arial", "B", sz)
        self.set_text_color(r, g, b)
        self.multi_cell(0, sz * 0.5, title)
        if level <= 2:
            self.set_draw_color(r, g, b)
            self.line(self.get_x(), self.get_y(), self.get_x() + 170, self.get_y())
        self.ln(3)

    def body_text(self, text):
        self.set_font("Arial", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bold_text(self, text):
        self.set_font("Arial", "B", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def code_block(self, code):
        self.set_font("Mono", "", 7.5)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(40, 40, 40)
        x = self.get_x()
        w = self.w - 2 * self.l_margin
        lines = code.strip().split("\n")
        # Estimate height
        line_h = 4
        block_h = len(lines) * line_h + 6
        if self.get_y() + block_h > self.h - 25:
            self.add_page()
        self.set_x(x)
        self.set_fill_color(245, 245, 245)
        self.rect(x, self.get_y(), w, block_h, "F")
        self.ln(3)
        for line in lines[:80]:  # Limit long blocks
            self.set_x(x + 4)
            self.cell(w - 8, line_h, line[:120])
            self.ln(line_h)
        self.ln(3)

    def mermaid_placeholder(self):
        self.set_font("Arial", "I", 8)
        self.set_fill_color(230, 240, 250)
        self.set_text_color(100, 130, 160)
        w = self.w - 2 * self.l_margin
        self.cell(w, 8, "[ Diagrama Mermaid — ver versión interactiva en el .md original ]", fill=True, align="C")
        self.ln(6)

    def table_row(self, cells, is_header=False):
        if is_header:
            self.set_font("Arial", "B", 8)
            self.set_fill_color(13, 27, 42)
            self.set_text_color(255, 255, 255)
        else:
            self.set_font("Arial", "", 8)
            self.set_text_color(30, 30, 30)

        col_w = (self.w - 2 * self.l_margin) / max(len(cells), 1)
        for cell in cells:
            txt = str(cell)[:60]
            self.cell(col_w, 6, txt, border=0, fill=is_header, align="L")
        self.ln(6)
        if is_header:
            self.set_draw_color(200, 200, 200)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(1)


def parse_md(md_path: str) -> list[tuple[str, str]]:
    """Parse markdown into a list of (type, content) tuples."""
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    elements = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")

        # Heading
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            elements.append(("heading", (level, m.group(2).strip())))
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].rstrip("\n").startswith("```"):
                code_lines.append(lines[i].rstrip("\n"))
                i += 1
            i += 1  # skip closing ```
            code = "\n".join(code_lines)
            if lang == "mermaid":
                elements.append(("mermaid", code))
            else:
                elements.append(("code", code))
            continue

        # Table
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[-\s|]+\|\s*$", lines[i + 1]):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                table_lines.append(row)
                i += 1
            elements.append(("table", table_lines))
            continue

        # Horizontal rule
        if re.match(r"^---+\s*$", line):
            elements.append(("hr", ""))
            i += 1
            continue

        # Blockquote
        if line.startswith(">"):
            bq_lines = []
            while i < len(lines) and lines[i].startswith(">"):
                bq_lines.append(lines[i].lstrip("> ").rstrip("\n"))
                i += 1
            elements.append(("blockquote", " ".join(bq_lines)))
            continue

        # Regular text
        if line.strip():
            text_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].startswith("```") and not lines[i].startswith("|") and not lines[i].startswith(">") and not re.match(r"^---+$", lines[i]):
                text_lines.append(lines[i].rstrip("\n"))
                i += 1
            elements.append(("text", " ".join(text_lines)))
        else:
            i += 1

    return elements


def generate_pdf(md_path: str, pdf_path: str):
    elements = parse_md(md_path)

    pdf = ManualPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Title page
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Arial", "B", 28)
    pdf.set_text_color(13, 27, 42)
    pdf.cell(0, 15, "FiscalIA", align="C")
    pdf.ln(18)
    pdf.set_font("Arial", "", 16)
    pdf.set_text_color(21, 101, 192)
    pdf.cell(0, 10, "Manual de Implementación API", align="C")
    pdf.ln(15)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Versión 2.0.0 — Julio 2026", align="C")
    pdf.ln(6)
    pdf.cell(0, 8, "Arquitectura: Hexagonal (Ports & Adapters) + DDD", align="C")
    pdf.ln(6)
    pdf.cell(0, 8, "Stack: Python 3.12+ / FastAPI / asyncpg / PostgreSQL 16+", align="C")
    pdf.ln(30)
    pdf.set_draw_color(21, 101, 192)
    pdf.line(60, pdf.get_y(), pdf.w - 60, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "Municipio de Valledupar — Departamento del Cesar", align="C")

    for etype, content in elements:
        # Skip title metadata (already on cover)
        if etype == "text" and content.startswith("> **Versión:"):
            continue
        if etype == "text" and content.startswith("> **Última"):
            continue
        if etype == "text" and content.startswith("> **Arquitectura:"):
            continue
        if etype == "text" and content.startswith("> **Stack:"):
            continue
        if etype == "heading" and content[1] == "Manual de Implementación — FiscalIA API":
            continue
        if etype == "hr":
            continue

        if etype == "heading":
            level, title = content
            # Check if we need a new page for level 1
            if level == 1 and pdf.get_y() > 50:
                pdf.add_page()
            elif level <= 2 and pdf.get_y() > pdf.h - 40:
                pdf.add_page()
            pdf.chapter_title(title, level)

        elif etype == "text":
            # Strip markdown bold/italic for plain text
            clean = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
            clean = re.sub(r"\*(.*?)\*", r"\1", clean)
            clean = re.sub(r"`(.*?)`", r"\1", clean)
            pdf.body_text(clean)

        elif etype == "code":
            pdf.code_block(content)

        elif etype == "mermaid":
            pdf.mermaid_placeholder()

        elif etype == "table":
            rows = content
            if len(rows) > 0:
                # Check if page break needed
                est_h = len(rows) * 6 + 10
                if pdf.get_y() + est_h > pdf.h - 25:
                    pdf.add_page()
                for idx, row in enumerate(rows):
                    pdf.table_row(row, is_header=(idx == 0))
                pdf.ln(4)

        elif etype == "blockquote":
            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(13, 71, 161)
            pdf.set_fill_color(227, 242, 253)
            w = pdf.w - 2 * pdf.l_margin
            x = pdf.get_x()
            pdf.rect(x, pdf.get_y(), w, 8, "F")
            pdf.cell(w, 8, f"  {content[:100]}")
            pdf.ln(10)

    pdf.output(pdf_path)
    print(f"PDF generado: {pdf_path}")


if __name__ == "__main__":
    generate_pdf(MD_PATH, PDF_PATH)
