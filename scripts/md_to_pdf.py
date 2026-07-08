import sys
import os
import json
import time
import base64
import subprocess
import markdown
import tempfile
import shutil

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

tmp_html = os.path.join(tempfile.gettempdir(), "propuesta-fiscalia.html")
with open(tmp_html, "w", encoding="utf-8") as f:
    f.write(html_doc)

# Find Edge
edge_paths = [
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
edge = next((p for p in edge_paths if os.path.exists(p)), None)
if not edge:
    print("Edge no encontrado")
    sys.exit(1)

# Start Edge headless with debug port
abs_html = os.path.abspath(tmp_html)
user_dir = os.path.join(tempfile.gettempdir(), "edge-profile-" + str(os.getpid()))

proc = subprocess.Popen(
    [edge, f"--headless=new", f"--remote-debugging-port=9222",
     f"--user-data-dir={user_dir}", "--disable-gpu", "--no-first-run",
     "--remote-allow-origins=*",
     f"file:///{abs_html.replace(os.sep, '/')}"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

time.sleep(2)

try:
    import urllib.request
    resp = urllib.request.urlopen("http://localhost:9222/json")
    tabs = json.loads(resp.read())
    ws_url = None
    for t in tabs:
        if t.get("url", "").startswith("file://"):
            ws_url = t["webSocketDebuggerUrl"]
            break
    if not ws_url:
        ws_url = tabs[0]["webSocketDebuggerUrl"]

    import websocket
    ws = websocket.create_connection(ws_url)
    msg_id = 1

    def send_cmd(method, params=None):
        global msg_id
        req = {"id": msg_id, "method": method, "params": params or {}}
        msg_id += 1
        ws.send(json.dumps(req))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == req["id"]:
                return resp.get("result")

    # Wait for page to load
    send_cmd("Page.enable")
    time.sleep(1)

    # Print to PDF with empty header/footer
    pdf_result = send_cmd("Page.printToPDF", {
        "printBackground": True,
        "preferCSSPageSize": True,
        "headerTemplate": "",
        "footerTemplate": "",
        "marginTop": 0.7,
        "marginBottom": 0.7,
        "marginLeft": 0.7,
        "marginRight": 0.7,
        "paperWidth": 8.27,
        "paperHeight": 11.69,
    })

    if pdf_result and "data" in pdf_result:
        pdf_bytes = base64.b64decode(pdf_result["data"])
        with open(PDF_PATH, "wb") as f:
            f.write(pdf_bytes)
        print(f"PDF generado: {PDF_PATH} ({len(pdf_bytes)} bytes)")
    else:
        print("Error: no se recibieron datos del PDF")
        sys.exit(1)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
finally:
    proc.terminate()
    proc.wait()
    time.sleep(0.5)
    # Cleanup temp profile
    try:
        shutil.rmtree(user_dir, ignore_errors=True)
    except Exception:
        pass
