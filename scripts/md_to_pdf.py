import sys
import os
import markdown
import tempfile

MD_PATH = sys.argv[1] if len(sys.argv) > 1 else "docs/cliente/propuesta-desarrollo-fiscalia.md"
PDF_PATH = MD_PATH.replace(".md", ".pdf")

CSS = """
@page {
  size: A4;
  margin: 2cm 2.5cm;
}
body {
  font-family: 'Calibri', 'Segoe UI', Arial, Helvetica, sans-serif;
  font-size: 11pt;
  line-height: 1.5;
  color: #1a1a1a;
}
h1 {
  font-size: 20pt;
  color: #003366;
  border-bottom: 2px solid #003366;
  padding-bottom: 6px;
  margin-top: 30px;
}
h2 {
  font-size: 16pt;
  color: #003366;
  margin-top: 24px;
}
h3 {
  font-size: 13pt;
  color: #2a5a8a;
  margin-top: 18px;
}
p { text-align: justify; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 10pt;
}
th {
  background-color: #003366;
  color: white;
  padding: 6px 10px;
  text-align: left;
}
td {
  border: 1px solid #cccccc;
  padding: 6px 10px;
}
tr:nth-child(even) { background-color: #f7f9fc; }
blockquote {
  border-left: 4px solid #003366;
  padding: 8px 16px;
  margin: 16px 0;
  background: #f0f4f8;
  font-style: italic;
}
strong { color: #003366; }
em { color: #555; }
hr { border: none; border-top: 1px solid #ccc; margin: 24px 0; }
.meta { color: #555; font-size: 10pt; margin: 4px 0; }
"""

with open(MD_PATH, "r", encoding="utf-8") as f:
    md_content = f.read()

html_content = markdown.markdown(
    md_content,
    extensions=["tables", "fenced_code", "codehilite"],
)

html_doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>{CSS}</style>
</head>
<body>
{html_content}
</body>
</html>"""

# Write HTML to a temp file
tmp_html = os.path.join(tempfile.gettempdir(), "propuesta-fiscalia.html")
with open(tmp_html, "w", encoding="utf-8") as f:
    f.write(html_doc)

print(f"HTML generado: {tmp_html}")

# Try Edge headless print-to-pdf
edge_paths = [
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

edge = None
for p in edge_paths:
    if os.path.exists(p):
        edge = p
        break

if edge:
    abs_html = os.path.abspath(tmp_html)
    abs_pdf = os.path.abspath(PDF_PATH)
    import subprocess
    cmd = [edge, "--headless", "--disable-gpu", f"--print-to-pdf={abs_pdf}", f"file:///{abs_html.replace(os.sep, '/')}"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if os.path.exists(abs_pdf) and os.path.getsize(abs_pdf) > 0:
        print(f"PDF generado: {PDF_PATH}")
    else:
        print("Error generando PDF con Edge:", result.stderr)
        sys.exit(1)
else:
    print(f"HTML listo en: {tmp_html}")
    print("Abre el archivo en tu navegador y usa Imprimir > Guardar como PDF")
    sys.exit(1)
