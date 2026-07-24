#!/usr/bin/env node
/**
 * Generate PDF from manual-implementacion-api.md
 * Markdown → HTML (TOC + Mermaid rendered) → PDF via Playwright
 */

const fs = require("fs");
const path = require("path");

const MD_PATH = path.join(__dirname, "..", "docs", "manual-implementacion-api.md");
const HTML_PATH = path.join(__dirname, "..", "docs", "manual-implementacion-api.html");
const PDF_PATH = path.join(__dirname, "..", "docs", "manual-implementacion-api.pdf");

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function slugify(text) {
  return text
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function mdToHtml(md) {
  const lines = md.split("\n");
  let html = "";
  const headings = []; // { level, text, id }
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // --- Code block ---
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      const code = escapeHtml(codeLines.join("\n"));
      if (lang === "mermaid") {
        html += `<div class="mermaid">${codeLines.join("\n")}</div>\n`;
      } else {
        html += `<pre><code class="language-${lang}">${code}</code></pre>\n`;
      }
      continue;
    }

    // --- Table ---
    if (line.trim().startsWith("|") && i + 1 < lines.length && /^\s*\|[-\s:|]+\|\s*$/.test(lines[i + 1])) {
      const headerCells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());
      i += 2;
      const bodyRows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        const cells = lines[i].trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());
        bodyRows.push(cells);
        i++;
      }
      const ths = headerCells.map(c => `<th>${escapeHtml(c)}</th>`).join("");
      const trs = bodyRows.map(cells => {
        const tds = cells.map(c => `<td>${escapeHtml(c)}</td>`).join("");
        return `<tr>${tds}</tr>`;
      }).join("\n");
      html += `<table><thead><tr>${ths}</tr></thead><tbody>\n${trs}\n</tbody></table>\n`;
      continue;
    }

    // --- Heading ---
    const hMatch = line.match(/^(#{1,4})\s+(.*)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const text = hMatch[2].replace(/\*\*/g, "").replace(/`/g, "").trim();
      const id = slugify(text);
      headings.push({ level, text, id });
      // Skip "Tabla de Contenidos" heading (TOC is generated automatically)
      if (/tabla de contenidos/i.test(text)) {
        i++;
        // Also skip the manual TOC list that follows
        while (i < lines.length && (lines[i].trim().startsWith("1.") || lines[i].trim().startsWith("2.") || lines[i].trim().startsWith("3.") || lines[i].trim().startsWith("4.") || lines[i].trim().startsWith("5.") || lines[i].trim().startsWith("6.") || lines[i].trim().startsWith("7.") || lines[i].trim().startsWith("8.") || lines[i].trim().startsWith("9.") || lines[i].trim().startsWith("10.") || lines[i].trim().startsWith("11.") || lines[i].trim().startsWith("12.") || lines[i].trim().startsWith("-") || lines[i].trim() === "")) {
          i++;
        }
        continue;
      }
      html += `<h${level} id="${id}">${inlineFormat(hMatch[2])}</h${level}>\n`;
      i++;
      continue;
    }

    // --- Horizontal rule ---
    if (/^---+\s*$/.test(line)) {
      html += `<hr>\n`;
      i++;
      continue;
    }

    // --- Blockquote ---
    if (line.startsWith(">")) {
      const bqLines = [];
      while (i < lines.length && lines[i].startsWith(">")) {
        bqLines.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      // Skip the metadata blockquote (Version, Last update, Architecture, Stack)
      const bqText = bqLines.join(" ");
      if (/Versi[oó]n:/.test(bqText) && /Arquitectura:/.test(bqText)) {
        continue;
      }
      html += `<blockquote>${inlineFormat(bqLines.join(" "))}</blockquote>\n`;
      continue;
    }

    // --- List ---
    if (/^- /.test(line)) {
      const items = [];
      while (i < lines.length && /^- /.test(lines[i])) {
        items.push(`<li>${inlineFormat(lines[i].slice(2))}</li>`);
        i++;
      }
      html += `<ul>\n${items.join("\n")}\n</ul>\n`;
      continue;
    }

    // --- Empty line ---
    if (line.trim() === "") {
      i++;
      continue;
    }

    // --- Paragraph ---
    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].startsWith("#") &&
      !lines[i].startsWith("```") &&
      !lines[i].startsWith("|") &&
      !lines[i].startsWith(">") &&
      !lines[i].startsWith("-") &&
      !/^---+\s*$/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      html += `<p>${inlineFormat(paraLines.join(" "))}</p>\n`;
    }
  }

  return { html, headings };
}

function inlineFormat(text) {
  let s = text;
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\*(.+?)\*/g, "<em>$1</em>");
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  return s;
}

function buildToc(headings) {
  // Skip first h1 (title) and "Tabla de Contenidos" (self-reference)
  const tocHeadings = headings.filter((h, idx) => {
    if (h.level === 1 && idx === 0) return false;
    if (/tabla de contenidos/i.test(h.text)) return false;
    return true;
  });

  let toc = '<nav id="toc">\n<ul class="toc-list">\n';
  for (const h of tocHeadings) {
    const indent = h.level - 2; // h2 = 0 indent, h3 = 1, h4 = 2
    const cls = indent <= 0 ? "toc-item" : `toc-item toc-indent-${indent}`;
    toc += `<li class="${cls}"><a href="#${h.id}">${escapeHtml(h.text)}</a></li>\n`;
  }
  toc += "</ul>\n</nav>\n";
  return toc;
}

function buildFullHtml(tocHtml, bodyHtml) {
  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>FiscalIA — Manual de Implementación API</title>
<style>
@page { size: A4; margin: 2cm 2.2cm; }
* { box-sizing: border-box; }

body {
  font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.65;
  color: #1a1a1a;
  margin: 0; padding: 0;
}

/* ── Cover Page ── */
.cover {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  text-align: center;
  page-break-after: always;
  padding: 40px;
}
.cover h1 {
  font-size: 28pt;
  color: #0d1b2a;
  border: none;
  margin-bottom: 10px;
  padding-bottom: 0;
}
.cover h2 {
  font-size: 20pt;
  color: #1565c0;
  border: none;
  margin-bottom: 40px;
  padding-bottom: 0;
}
.cover .divider {
  width: 120px;
  height: 3px;
  background: #1565c0;
  margin: 0 auto;
}

/* ── TOC ── */
#toc {
  page-break-after: always;
  padding-top: 20px;
}
#toc h2 {
  font-size: 18pt; color: #0d1b2a;
  border-bottom: 3px solid #1565c0;
  padding-bottom: 8px; margin-bottom: 20px;
}
.toc-list {
  list-style: none; padding: 0; margin: 0;
}
.toc-item {
  margin: 0; padding: 0;
}
.toc-item a {
  display: block;
  padding: 6px 0 6px 0;
  color: #1a1a1a;
  text-decoration: none;
  border-bottom: 1px dotted #ddd;
  font-size: 10.5pt;
  transition: background 0.15s;
}
.toc-item a:hover {
  background: #e3f2fd;
}
/* h2 entries: bold, larger */
.toc-item a {
  font-weight: 600;
  color: #0d1b2a;
}
/* h3 entries: indented, normal weight */
.toc-indent-1 a {
  padding-left: 20px;
  font-weight: 400;
  color: #333;
  font-size: 10pt;
}
/* h4 entries: double indented, smaller */
.toc-indent-2 a {
  padding-left: 40px;
  font-weight: 400;
  color: #555;
  font-size: 9.5pt;
}

/* ── Headings ── */
h1 {
  font-size: 20pt; color: #0d1b2a;
  border-bottom: 3px solid #1565c0;
  padding-bottom: 8px; margin-top: 32px;
}
h2 {
  font-size: 15pt; color: #1565c0;
  border-bottom: 1px solid #ccc;
  padding-bottom: 4px; margin-top: 28px;
}
h3 {
  font-size: 12pt; color: #2e7d32;
  margin-top: 20px;
}
h4 {
  font-size: 11pt; color: #e65100;
  margin-top: 16px;
}

/* ── Tables ── */
table {
  width: 100%; border-collapse: collapse;
  margin: 12px 0; font-size: 9.5pt;
}
th {
  background-color: #0d1b2a; color: #fff;
  padding: 7px 10px; text-align: left; font-weight: 600;
}
td {
  padding: 5px 10px; border-bottom: 1px solid #e0e0e0;
  vertical-align: top; color: #1a1a1a;
}
tr:nth-child(even) { background-color: #f8f9fa; }

/* ── Code ── */
code {
  font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
  background: #f0f0f0; padding: 1px 5px; border-radius: 3px;
  font-size: 9.5pt; color: #b71c1c;
}
pre {
  background: #1e1e2e; color: #cdd6f4;
  padding: 14px 16px; border-radius: 6px;
  font-size: 8.5pt; line-height: 1.5;
  margin: 12px 0;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: break-word;
  page-break-inside: avoid;
}
pre code {
  background: transparent; color: #cdd6f4;
  padding: 0; font-size: 8.5pt;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── Blockquote ── */
blockquote {
  border-left: 4px solid #1976d2;
  margin: 14px 0; padding: 10px 16px;
  background: #e8f4fd; color: #0d47a1;
  border-radius: 0 6px 6px 0;
  font-style: italic;
}
blockquote strong { color: #0d47a1; }

/* ── Lists ── */
ul, ol { margin: 8px 0; padding-left: 24px; }
li { margin-bottom: 4px; }

/* ── Misc ── */
strong { color: #0d1b2a; }
hr { border: none; border-top: 1px solid #ccc; margin: 20px 0; }
p { margin: 6px 0; }
a { color: #1565c0; text-decoration: none; }

/* ── Mermaid ── */
.mermaid {
  background: #f8fafb; border: 1px solid #cfd8dc;
  border-radius: 8px; padding: 12px;
  margin: 14px 0; text-align: center;
  page-break-inside: auto;
  overflow: visible;
}
.mermaid svg {
  max-width: 100%; height: auto;
  max-height: 500px;
}
</style>
</head>
<body>
<div class="cover">
  <h1>Manual de Implementación</h1>
  <h2>FiscalIA API</h2>
  <div class="divider"></div>
</div>
${tocHtml}
${bodyHtml}
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({
    startOnLoad: true,
    theme: 'base',
    themeVariables: {
      primaryColor: '#e3f2fd',
      primaryTextColor: '#0d1b2a',
      primaryBorderColor: '#1565c0',
      lineColor: '#1565c0',
      fontSize: '13px'
    },
    securityLevel: 'loose',
    flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'cardinal' },
    sequence: { useMaxWidth: true, actorMargin: 50, mirrorActors: false },
    mindmap: { useMaxWidth: true },
    er: { useMaxWidth: true }
  });
</script>
</body>
</html>`;
}

async function main() {
  const md = fs.readFileSync(MD_PATH, "utf-8");
  const { html: bodyHtml, headings } = mdToHtml(md);

  console.log(`Headings encontrados: ${headings.length}`);
  headings.forEach(h => console.log(`  ${"  ".repeat(h.level - 1)}h${h.level} → #${h.id}`));

  const tocHtml = buildToc(headings);
  const fullHtml = buildFullHtml(tocHtml, bodyHtml);

  fs.writeFileSync(HTML_PATH, fullHtml, "utf-8");
  console.log(`\nHTML generado: ${HTML_PATH}`);

  const { chromium } = require("playwright");
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.setContent(fullHtml, { waitUntil: "networkidle" });

  // Wait for Mermaid
  console.log("Esperando renderizado de Mermaid...");
  const diagramCount = (fullHtml.match(/class="mermaid"/g) || []).length;
  console.log(`Diagramas Mermaid: ${diagramCount}`);

  try {
    await page.waitForFunction(
      (expected) => document.querySelectorAll(".mermaid svg").length >= expected,
      diagramCount,
      { timeout: 30000 }
    );
    console.log("Todos los diagramas renderizados.");
  } catch {
    const rendered = await page.evaluate(() => document.querySelectorAll(".mermaid svg").length);
    console.log(`Timeout: ${rendered}/${diagramCount} renderizados.`);
  }

  // Generate PDF
  await page.pdf({
    path: PDF_PATH,
    format: "A4",
    margin: { top: "2cm", bottom: "2cm", left: "2.2cm", right: "2.2cm" },
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<div style="font-size:8px;color:#999;width:100%;text-align:center;margin-top:8px;">FiscalIA — Manual de Implementación API</div>',
    footerTemplate: '<div style="font-size:8px;color:#999;width:100%;text-align:center;margin-bottom:8px;">Página <span class="pageNumber"></span> de <span class="totalPages"></span></div>',
  });

  await browser.close();
  console.log(`\nPDF generado: ${PDF_PATH}`);
  const stats = fs.statSync(PDF_PATH);
  console.log(`Tamaño: ${(stats.size / 1024).toFixed(0)} KB`);
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
