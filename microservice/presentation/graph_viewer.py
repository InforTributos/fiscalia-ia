from __future__ import annotations


def render_graph_viewer(nit: str, periodo: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Grafo de riesgo - {nit}</title>
  <style>
    body {{ margin:0; font-family: Inter, system-ui, -apple-system, sans-serif; background:#f7f8fb; color:#1d2533; }}
    header {{ padding:18px 24px; background:#ffffff; border-bottom:1px solid #dfe5ee; display:flex; justify-content:space-between; gap:16px; align-items:center; }}
    h1 {{ font-size:20px; margin:0; }}
    main {{ display:grid; grid-template-columns:minmax(0, 1fr) 360px; min-height:calc(100vh - 66px); }}
    #graph {{ width:100%; height:calc(100vh - 66px); background:#ffffff; }}
    aside {{ border-left:1px solid #dfe5ee; padding:18px; background:#f7f8fb; overflow:auto; }}
    .metric {{ background:#fff; border:1px solid #dfe5ee; border-radius:8px; padding:14px; margin-bottom:12px; }}
    .metric strong {{ display:block; font-size:28px; line-height:1.1; }}
    .pill {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#e8eef7; font-size:12px; margin:4px 4px 0 0; }}
    .node {{ cursor:pointer; stroke:#fff; stroke-width:2; }}
    .edge {{ stroke:#9aa7b8; stroke-opacity:.7; }}
    .label {{ font-size:12px; fill:#263244; pointer-events:none; }}
    @media (max-width: 900px) {{ main {{ grid-template-columns:1fr; }} aside {{ border-left:0; border-top:1px solid #dfe5ee; }} #graph {{ height:62vh; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Grafo de riesgo fiscal - NIT {nit}</h1>
    <span>Periodo {periodo}</span>
  </header>
  <main>
    <svg id="graph" role="img" aria-label="Grafo de riesgo fiscal"></svg>
    <aside>
      <div class="metric"><span>Score red</span><strong id="score">...</strong><span id="nivel"></span></div>
      <div class="metric"><span>Empresas conectadas</span><strong id="conectadas">...</strong></div>
      <div class="metric"><span>Motivos</span><div id="motivos"></div></div>
      <div class="metric"><span>Nodo seleccionado</span><div id="selected">Seleccione un nodo</div></div>
    </aside>
  </main>
  <script>
    const endpoint = `/api/v1/contribuyente/{nit}/grafo-riesgo?periodo={periodo}`;
    const svg = document.getElementById('graph');
    const colors = {{
      EMPRESA: '#1f77b4',
      ACTIVIDAD_CIIU: '#2ca02c',
      HALLAZGO: '#d62728'
    }};
    fetch(endpoint).then(r => r.json()).then(draw).catch(err => {{
      document.getElementById('selected').textContent = 'No se pudo cargar el grafo: ' + err;
    }});
    function draw(data) {{
      document.getElementById('score').textContent = data.resumen_red.score_red;
      document.getElementById('nivel').textContent = data.resumen_red.nivel_red;
      document.getElementById('conectadas').textContent = data.resumen_red.empresas_conectadas;
      document.getElementById('motivos').innerHTML = data.resumen_red.motivos.map(m => `<span class="pill">${{m}}</span>`).join('');

      const width = svg.clientWidth || 900, height = svg.clientHeight || 620;
      svg.setAttribute('viewBox', `0 0 ${{width}} ${{height}}`);
      const nodes = data.nodes.map((n, i) => ({{...n, x: width/2 + Math.cos(i)*120, y: height/2 + Math.sin(i)*120}}));
      const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
      const edges = data.edges.filter(e => byId[e.source] && byId[e.target]);

      for (let iter=0; iter<180; iter++) {{
        for (const e of edges) {{
          const a = byId[e.source], b = byId[e.target];
          const dx = b.x - a.x, dy = b.y - a.y, dist = Math.hypot(dx, dy) || 1;
          const force = (dist - 160) * 0.006 * e.peso;
          a.x += dx / dist * force; a.y += dy / dist * force;
          b.x -= dx / dist * force; b.y -= dy / dist * force;
        }}
        for (const a of nodes) for (const b of nodes) if (a !== b) {{
          const dx = b.x - a.x, dy = b.y - a.y, dist = Math.hypot(dx, dy) || 1;
          const repulse = Math.min(2.8, 180 / (dist * dist));
          a.x -= dx / dist * repulse; a.y -= dy / dist * repulse;
        }}
        for (const n of nodes) {{ n.x = Math.max(40, Math.min(width-40, n.x)); n.y = Math.max(40, Math.min(height-40, n.y)); }}
      }}

      svg.innerHTML = edges.map(e => `<line class="edge" x1="${{byId[e.source].x}}" y1="${{byId[e.source].y}}" x2="${{byId[e.target].x}}" y2="${{byId[e.target].y}}" stroke-width="${{1 + e.peso*2}}"/>`).join('')
        + nodes.map(n => `<circle class="node" data-id="${{n.id}}" cx="${{n.x}}" cy="${{n.y}}" r="${{n.tipo === 'EMPRESA' ? 15 : 11}}" fill="${{colors[n.tipo] || '#9467bd'}}"></circle><text class="label" x="${{n.x + 18}}" y="${{n.y + 4}}">${{n.label}}</text>`).join('');
      svg.querySelectorAll('.node').forEach(el => el.addEventListener('click', () => {{
        const n = byId[el.dataset.id];
        document.getElementById('selected').innerHTML = `<strong>${{n.label}}</strong><br>${{n.tipo}}<br><code>${{n.id}}</code>`;
      }}));
    }}
  </script>
</body>
</html>"""

