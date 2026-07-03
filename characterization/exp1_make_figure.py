#!/usr/bin/env python3
"""Genera la figura Exp 1 (hoja técnica HTML autocontenida) desde el análisis."""
import csv, json, math, os

OUT = 'exp1_out'
DST = 'characterization/figures/exp1_step_response.html'

# ── datos ───────────────────────────────────────────────────────────────
ov = json.load(open(os.path.join(OUT, 'overlay_traces.json')))
grid = ov['grid']
traces = ov['traces']                      # {speed: [y|None,...]}
by = list(csv.DictReader(open(os.path.join(OUT, 'analysis_by_speed.csv'))))
def g(row, k):
    v = row[k]; return float(v) if v not in ('', None) else None
speeds = [int(r['speed']) for r in by]
rows = {int(r['speed']): r for r in by}

# ── color: rampa secuencial (claro->oscuro por velocidad) ────────────────
RAMP = ['#9FC2E0', '#6FA3D2', '#4682BE', '#285F97', '#123F63']
ACCENT = '#285F97'; AMBER = '#B4740F'
INK = '#12181f'; MUTED = '#5a6472'; HAIR = '#dbe2ec'; GRID = '#eef2f7'

def srgb_L(hex):
    r, gg, b = (int(hex[i:i+2], 16)/255 for i in (1, 3, 5))
    def lin(c): return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    Y = 0.2126*lin(r)+0.7152*lin(gg)+0.0722*lin(b)
    return 116*(Y**(1/3) if Y > 0.008856 else 7.787*Y+16/116)-16
Ls = [round(srgb_L(c), 1) for c in RAMP]
print("L* rampa (debe descender):", Ls,
      "monótona" if all(Ls[i] > Ls[i+1] for i in range(len(Ls)-1)) else "NO monótona")

# ── helpers SVG ──────────────────────────────────────────────────────────
def sx(x, x0, x1, px0, px1): return px0+(x-x0)/(x1-x0)*(px1-px0)
def sy(y, y0, y1, py0, py1): return py0+(y-y0)/(y1-y0)*(py1-py0)

def overlay_svg():
    W, H = 760, 400
    L, R, T, B = 58, 26, 20, 46
    x0, x1 = -0.12, 2.6
    y0, y1 = -0.05, 1.08
    def X(x): return sx(x, x0, x1, L, W-R)
    def Y(y): return sy(y, y1, y0, T, H-B)     # y invertida
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="POS_ACT normalizada vs tiempo desde el comando, por velocidad">']
    # grid + ticks x
    for xv in [0, 0.5, 1.0, 1.5, 2.0, 2.5]:
        px = X(xv)
        s.append(f'<line x1="{px:.1f}" y1="{T}" x2="{px:.1f}" y2="{H-B}" stroke="{GRID}"/>')
        s.append(f'<text x="{px:.1f}" y="{H-B+18}" fill="{MUTED}" font-size="12" text-anchor="middle" class="mono">{xv:.1f}</text>')
    for yv in [0, 0.25, 0.5, 0.75, 1.0]:
        py = Y(yv)
        s.append(f'<line x1="{L}" y1="{py:.1f}" x2="{W-R}" y2="{py:.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{py+4:.1f}" fill="{MUTED}" font-size="12" text-anchor="end" class="mono">{yv:.2f}</text>')
    # eje: linea del comando (t=0)
    s.append(f'<line x1="{X(0):.1f}" y1="{T}" x2="{X(0):.1f}" y2="{H-B}" stroke="{INK}" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>')
    s.append(f'<text x="{X(0)+5:.1f}" y="{T+13}" fill="{INK}" font-size="11" class="ey">comando</text>')
    # trazas
    for i, sp in enumerate(speeds):
        tr = traces[str(sp)]
        pts = [(X(grid[j]), Y(tr[j])) for j in range(len(grid)) if tr[j] is not None and x0 <= grid[j] <= x1]
        if not pts: continue
        d = 'M ' + ' L '.join(f'{x:.1f} {y:.1f}' for x, y in pts)
        s.append(f'<path d="{d}" fill="none" stroke="{RAMP[i]}" stroke-width="2.4" stroke-linejoin="round"/>')
        lx, ly = pts[-1]
        s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.2" fill="{RAMP[i]}"/>')
    # ejes
    s.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" fill="{MUTED}" font-size="12.5" text-anchor="middle" class="ey">tiempo desde el comando  (s)</text>')
    s.append(f'<text transform="translate(15,{(T+H-B)/2:.0f}) rotate(-90)" fill="{MUTED}" font-size="12.5" text-anchor="middle" class="ey">POS_ACT normalizada  (0 = abierto · 1 = final)</text>')
    s.append('</svg>')
    return '\n'.join(s)

def small_svg(xs, ys, sds, xlabel, ylabel, fit=None, ymax=None, note=None, color=ACCENT):
    W, H = 372, 288
    L, R, T, B = 56, 20, 22, 46
    x0, x1 = 0, 1080
    y0, y1 = 0, (ymax or max(ys)*1.18)
    def X(x): return sx(x, x0, x1, L, W-R)
    def Y(y): return sy(y, y1, y0, T, H-B)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{ylabel} vs {xlabel}">']
    for gy in [i*y1/4 for i in range(5)]:
        py = Y(gy)
        s.append(f'<line x1="{L}" y1="{py:.1f}" x2="{W-R}" y2="{py:.1f}" stroke="{GRID}"/>')
        lab = f'{gy:.0f}' if y1 >= 20 else f'{gy:.1f}'
        s.append(f'<text x="{L-8}" y="{py+4:.1f}" fill="{MUTED}" font-size="11" text-anchor="end" class="mono">{lab}</text>')
    for xv in [100, 250, 500, 750, 1000]:
        s.append(f'<text x="{X(xv):.1f}" y="{H-B+17}" fill="{MUTED}" font-size="11" text-anchor="middle" class="mono">{xv}</text>')
    if fit:
        m, b = fit
        s.append(f'<line x1="{X(0):.1f}" y1="{Y(b):.1f}" x2="{X(1080):.1f}" y2="{Y(m*1080+b):.1f}" stroke="{color}" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.55"/>')
    # error bars
    if sds:
        for x, y, sd in zip(xs, ys, sds):
            if sd:
                s.append(f'<line x1="{X(x):.1f}" y1="{Y(y-sd):.1f}" x2="{X(x):.1f}" y2="{Y(y+sd):.1f}" stroke="{color}" stroke-width="1.4" opacity="0.5"/>')
    # points
    pts = ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in zip(xs, ys))
    s.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.6" opacity="0.35"/>')
    for x, y in zip(xs, ys):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.2" fill="{color}" stroke="#fff" stroke-width="1.5"/>')
    if note:
        s.append(f'<text x="{W-R:.0f}" y="{T+6}" fill="{color}" font-size="12" text-anchor="end" class="mono b">{note}</text>')
    s.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" fill="{MUTED}" font-size="12" text-anchor="middle" class="ey">{xlabel}</text>')
    s.append(f'<text transform="translate(14,{(T+H-B)/2:.0f}) rotate(-90)" fill="{MUTED}" font-size="12" text-anchor="middle" class="ey">{ylabel}</text>')
    s.append('</svg>')
    return '\n'.join(s)

# fit slope ~ k*v (por origen)
sv = [rows[s]['slope_cps_mean'] for s in speeds]
sv = [float(x) for x in sv]
k = sum(s*y for s, y in zip(speeds, sv))/sum(s*s for s in speeds)   # min sq por origen
slope_chart = small_svg(speeds, sv, None, 'SPEED_SET (comando)', 'pendiente lineal (counts/s)',
                        fit=(k, 0), ymax=3300, note=f'≈ {k:.2f} × v', color=ACCENT)

lat = [float(rows[s]['L_band_ms_mean']) for s in speeds]
latsd = [float(rows[s]['L_band_ms_sd']) for s in speeds]
lat_chart = small_svg(speeds, lat, latsd, 'SPEED_SET (comando)', 'latencia L_band (ms)',
                     ymax=105, note='deadtime ~64 ms', color=AMBER)

# ── tabla ────────────────────────────────────────────────────────────────
def fmt(row, k, dp=0):
    m = row.get(k+'_mean'); sd = row.get(k+'_sd')
    if m in (None, ''): return '—'
    m = float(m); sd = float(sd) if sd not in (None, '') else 0
    return f'{m:.{dp}f}<span class="pm">±{sd:.{dp}f}</span>'
trows = ''
for sp in speeds:
    r = rows[sp]
    trows += (f'<tr><td class="mono b">{sp}</td>'
              f'<td class="mono">{fmt(r,"L_band_ms",0)}</td>'
              f'<td class="mono">{fmt(r,"rise_ms",0)}</td>'
              f'<td class="mono">{fmt(r,"settle_ms",0)}</td>'
              f'<td class="mono">{fmt(r,"overshoot_pct",1)}</td>'
              f'<td class="mono">{float(r["slope_cps_mean"]):.0f}</td>'
              f'<td class="mono">{float(r["r2_mean"]):.3f}</td></tr>')

legend_html = ('<div class="legend"><span class="ll">SPEED_SET &rarr;</span>'
               + ''.join(f'<span class="li"><span class="sw" style="background:{RAMP[i]}"></span>{sp}</span>'
                         for i, sp in enumerate(speeds)) + '</div>')

HTML = f'''<title>Exp 1 — Respuesta al escalón · RH56DFTP</title>
<style>
  :root{{--ink:{INK};--muted:{MUTED};--hair:{HAIR};--accent:{ACCENT};--amber:{AMBER};
    --bg:#f6f8fb;--panel:#ffffff;}}
  *{{box-sizing:border-box;}}
  .wrap{{max-width:900px;margin:0 auto;padding:44px 24px 64px;color:var(--ink);
    background:var(--bg);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.55;}}
  .mono{{font-family:ui-monospace,"SF Mono","JetBrains Mono","Cascadia Code",Menlo,monospace;
    font-variant-numeric:tabular-nums;}}
  .b{{font-weight:600;}} .ey{{letter-spacing:.14em;text-transform:uppercase;}}
  .eyebrow{{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);
    font-weight:600;}}
  h1{{font-size:31px;line-height:1.15;margin:.35rem 0 .5rem;text-wrap:balance;letter-spacing:-.01em;}}
  .dek{{color:var(--muted);font-size:16.5px;max-width:62ch;margin:0;}}
  .rule{{height:1px;background:var(--hair);border:0;margin:26px 0;}}
  .panel{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;
    padding:18px 18px 12px;box-shadow:0 1px 2px rgba(18,24,31,.04);}}
  .cap{{font-size:12px;color:var(--muted);margin:2px 2px 14px;}}
  .cap b{{color:var(--ink);}}
  figure{{margin:0;}}
  .legend{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:2px 2px 12px;font-size:12.5px;}}
  .legend .ll{{color:var(--muted);letter-spacing:.1em;text-transform:uppercase;font-size:11px;}}
  .legend .li{{display:inline-flex;align-items:center;gap:6px;color:var(--ink);}}
  .legend .sw{{width:22px;height:4px;border-radius:2px;display:inline-block;}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;}}
  @media(max-width:680px){{.grid2{{grid-template-columns:1fr;}}}}
  svg{{width:100%;height:auto;display:block;}}
  .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:4px 0 2px;}}
  .kpi{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;padding:14px 16px;}}
  .kpi .n{{font-size:25px;font-weight:600;letter-spacing:-.01em;}}
  .kpi .l{{font-size:12px;color:var(--muted);margin-top:2px;}}
  .kpi .n .u{{font-size:14px;color:var(--muted);font-weight:500;}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;}}
  th,td{{text-align:right;padding:8px 10px;border-bottom:1px solid var(--hair);}}
  th:first-child,td:first-child{{text-align:left;}}
  th{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600;}}
  .pm{{color:var(--muted);font-size:11px;margin-left:1px;}}
  .foot{{font-size:12.5px;color:var(--muted);margin-top:22px;}}
  .foot code{{font-family:ui-monospace,Menlo,monospace;color:var(--ink);
    background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:12px;}}
  .tag{{display:inline-block;font-size:11px;color:var(--muted);border:1px solid var(--hair);
    border-radius:20px;padding:2px 10px;}}
</style>
<div class="wrap">
  <div class="eyebrow">Experimento 1 · Respuesta al escalón</div>
  <h1>El dedo índice responde al comando con un retardo fijo y una velocidad proporcional al setpoint</h1>
  <p class="dek">Inspire RH56DFTP, DOF&nbsp;3, movimiento en espacio libre. Escalón de <span class="mono">ANGLE_SET</span> abierto→300, cinco velocidades × 20 trials, muestreado a ~87&nbsp;Hz sobre <span class="mono">POS_ACT</span> con <span class="mono">perf_counter()</span>.</p>

  <div style="margin:18px 0 22px" class="kpis">
    <div class="kpi"><div class="n">~64<span class="u"> ms</span></div><div class="l">deadtime comando→sensor (v=1000; incl. ~10 ms Modbus)</div></div>
    <div class="kpi"><div class="n">{k:.2f}<span class="u"> × v</span></div><div class="l">pendiente lineal ∝ velocidad · R²&nbsp;≥&nbsp;0.98</div></div>
    <div class="kpi"><div class="n">≈0<span class="u"> %</span></div><div class="l">sobreimpulso de posición (sin deceleración)</div></div>
  </div>

  <figure class="panel">
    {legend_html}
    {overlay_svg()}
    <figcaption class="cap"><b>Figura 1.</b> Trayectorias medias normalizadas de <span class="mono">POS_ACT</span> (N=20 por velocidad) alineadas al instante del comando. El abanico de pendientes muestra velocidad creciente con el setpoint; el arranque común confirma un retardo independiente de la velocidad y ausencia de pre-deceleración.</figcaption>
  </figure>

  <hr class="rule">
  <div class="grid2">
    <figure class="panel"><div style="font-weight:600;font-size:13.5px;margin:2px 2px 8px">Pendiente ∝ velocidad comandada</div>{slope_chart}<figcaption class="cap">La velocidad del dedo en el tramo lineal escala de forma proporcional al <span class="mono">SPEED_SET</span>. Ajuste por el origen.</figcaption></figure>
    <figure class="panel"><div style="font-weight:600;font-size:13.5px;margin:2px 2px 8px">Latencia ~plana con la velocidad</div>{lat_chart}<figcaption class="cap">El retardo comando→sensor no depende de la velocidad (barras = ±1σ). Mejor estimado a v=1000 (menos sesgo de cruce lento).</figcaption></figure>
  </div>

  <hr class="rule">
  <div class="panel" style="padding-bottom:6px">
    <div style="font-weight:600;font-size:13.5px;margin:2px 2px 12px">Métricas por velocidad <span class="tag">media ± σ · N=20</span></div>
    <div style="overflow-x:auto">
    <table>
      <thead><tr><th>SPEED_SET</th><th>Latencia (ms)</th><th>Subida 10–90% (ms)</th><th>Estab. ±2% (ms)</th><th>Sobreimp. (%)</th><th>Pendiente (c/s)</th><th>R²</th></tr></thead>
      <tbody>{trows}</tbody>
    </table>
    </div>
  </div>

  <p class="foot">100 trials, 0 abortos, 0 sin asentar. <code>FORCE_ACT</code> tiene un offset dependiente de la flexión (~216→326&nbsp;g) sin contacto externo (corriente→0 al sostener) — relevante para el Exp&nbsp;2. Datos: <code>exp1_out/</code>. Análisis: <code>exp1_analyze.py</code> (Python puro).</p>
</div>'''

open(DST, 'w').write(HTML)
print("escrito:", DST, f"({len(HTML)} bytes)")
