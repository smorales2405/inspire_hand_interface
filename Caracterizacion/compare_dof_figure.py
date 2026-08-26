#!/usr/bin/env python3
"""Figuras comparativas ÍNDICE (DOF 3) vs PULGAR (DOF 4).

Tres gráficos que cuentan los tres hallazgos de la réplica del protocolo:

  1. Pendiente vs SPEED_SET — misma ganancia en counts/s en los dos dedos
     (SPEED_SET calibra el actuador), con la saturación del pulgar a v=1000.
  2. ΔF a Fset=100 vs velocidad — el "setpoint seguro" del índice NO existe en
     el pulgar. Es el hallazgo central; eje log porque abarca tres décadas.
  3. Modo A (v=1000) → modo B por Fset — la conmutación de velocidad colapsa el
     sobreimpulso en AMBOS dedos.

Color: dos hues categóricos del sistema del documento, validados con el script
del skill dataviz (ΔE 22.3 CVD protan / 27.2 visión normal, todas las
comprobaciones PASS sobre superficie blanca).

Sin capa de hover a propósito: la salida primaria de estas figuras es el SVG
vectorial que se embebe en la tesis (ver figures_to_svg.py), donde no sobrevive
ningún JS. La identidad va por leyenda + etiquetas directas, nunca por color solo.
"""
from __future__ import annotations

import csv
import json
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(_HERE, 'figures', 'comparativa_indice_pulgar.html')

IDX = '#285F97'   # índice
THB = '#B4740F'   # pulgar
INK, MUTED, HAIR, GRID = '#12181f', '#5a6472', '#dbe2ec', '#eef2f7'
FINGERS = (('Índice (DOF 3)', IDX), ('Pulgar (DOF 4)', THB))


# ── datos ────────────────────────────────────────────────────────────────
def by_speed(d):
    rows = list(csv.DictReader(open(os.path.join(_HERE, d, 'analysis_by_speed.csv'))))
    return {int(r['speed']): r for r in rows}


def grid(d):
    return json.load(open(os.path.join(_HERE, d, 'exp2_overshoot_grid.json')))


def hybrid(d):
    out = {}
    for r in csv.DictReader(open(os.path.join(_HERE, d, 'grid_index.csv'))):
        if r['delta_f']:
            out.setdefault(int(r['fset']), []).append(float(r['delta_f']))
    return {k: sorted(v)[len(v) // 2] for k, v in out.items()}


S_I, S_T = by_speed('exp1/data'), by_speed('exp1/data_dof4')
G_I, G_T = grid('exp2/data'), grid('exp2/data_dof4')
B_I, B_T = hybrid('exp2/data_hybrid'), hybrid('exp2/data_dof4_hybrid')
SPEEDS = sorted(S_I)
VS = [int(v) for v in G_I['speeds']]
FSETS = [int(f) for f in G_I['fsets']]


def sx(x, x0, x1, p0, p1):
    return p0 + (x - x0) / (x1 - x0) * (p1 - p0)


def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;')


# ── 1) pendiente vs SPEED_SET ────────────────────────────────────────────
def slope_svg():
    W, H = 452, 320
    L, R, T, B = 62, 62, 24, 50
    x0, x1, y0, y1 = 0, 1060, 0, 3300
    X = lambda v: sx(v, x0, x1, L, W - R)
    Y = lambda v: sx(v, y1, y0, T, H - B)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Pendiente del tramo lineal '
         f'frente a SPEED_SET, para el índice y para el pulgar">']
    for gy in range(0, 3301, 825):
        s.append(f'<line x1="{L}" y1="{Y(gy):.1f}" x2="{W-R}" y2="{Y(gy):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{Y(gy)+4:.1f}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="end" class="mono">{gy}</text>')
    for v in SPEEDS:
        s.append(f'<text x="{X(v):.1f}" y="{H-B+17}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="middle" class="mono">{v}</text>')
    # referencia k·v ajustada con v<=500 sobre el índice
    k = sum(v * float(S_I[v]['slope_cps_mean']) for v in (100, 250, 500)) / sum(v * v for v in (100, 250, 500))
    s.append(f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(1000):.1f}" y2="{Y(k*1000):.1f}" '
             f'stroke="{MUTED}" stroke-width="1" opacity="0.35"/>')
    # esquina superior izquierda: es la única zona que la diagonal deja libre
    s.append(f'<text x="{L+10:.1f}" y="{T+15:.1f}" fill="{MUTED}" font-size="10.5" '
             f'class="mono">recta k·v · k≈{k:.2f}</text>')
    for src, color in ((S_I, IDX), (S_T, THB)):
        pts = [(X(v), Y(float(src[v]['slope_cps_mean']))) for v in SPEEDS]
        s.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) +
                 f'" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
        for x, y in pts:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="{color}" '
                     f'stroke="#fff" stroke-width="2"/>')
    # etiquetas directas en el extremo
    for src, color, lab, dy in ((S_I, IDX, 'índice', -12), (S_T, THB, 'pulgar', 16)):
        v = SPEEDS[-1]; y = Y(float(src[v]['slope_cps_mean']))
        s.append(f'<text x="{X(v)+8:.1f}" y="{y+dy/3:.1f}" fill="{color}" font-size="11.5" '
                 f'class="b">{lab}</text>')
    # anotación de la saturación del pulgar
    yT = Y(float(S_T[1000]['slope_cps_mean'])); yK = Y(k * 1000)
    s.append(f'<line x1="{X(1000)-13:.1f}" y1="{yK:.1f}" x2="{X(1000)-13:.1f}" y2="{yT:.1f}" '
             f'stroke="{THB}" stroke-width="1.2" opacity="0.7"/>')
    s.append(f'<text x="{X(1000)-18:.1f}" y="{(yK+yT)/2+4:.1f}" fill="{THB}" font-size="11" '
             f'text-anchor="end" class="mono b">−12%</text>')
    s.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-7}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle" class="ey">SPEED_SET comandado</text>')
    s.append(f'<text transform="translate(15,{(T+H-B)/2:.0f}) rotate(-90)" fill="{MUTED}" '
             f'font-size="11.5" text-anchor="middle" class="ey">pendiente (counts/s)</text>')
    s.append('</svg>')
    return '\n'.join(s)


# ── 2) ΔF a Fset=100 vs velocidad (eje log) ──────────────────────────────
def fset100_svg():
    W, H = 452, 320
    L, R, T, B = 62, 62, 24, 50
    lo, hi = 3.0, 2200.0
    X = lambda i: sx(i, 0, len(VS) - 1, L + 8, W - R - 8)
    Y = lambda v: sx(math.log10(max(v, lo)), math.log10(hi), math.log10(lo), T, H - B)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Sobreimpulso de fuerza con '
         f'FORCE_SET de 100 gramos frente a la velocidad, escala logarítmica">']
    for gy in (10, 100, 1000):
        s.append(f'<line x1="{L}" y1="{Y(gy):.1f}" x2="{W-R}" y2="{Y(gy):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{Y(gy)+4:.1f}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="end" class="mono">{gy}</text>')
    for i, v in enumerate(VS):
        s.append(f'<text x="{X(i):.1f}" y="{H-B+17}" fill="{MUTED}" font-size="10.5" '
                 f'text-anchor="middle" class="mono">{v}</text>')
    for G, color in ((G_I, IDX), (G_T, THB)):
        pts = [(X(i), Y(G['median'][str(v)]['100'])) for i, v in enumerate(VS)]
        s.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) +
                 f'" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
        for x, y in pts:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="{color}" '
                     f'stroke="#fff" stroke-width="2"/>')
    vI = G_I['median']['1000']['100']; vT = G_T['median']['1000']['100']
    s.append(f'<text x="{X(len(VS)-1)-6:.1f}" y="{Y(vT)-11:.1f}" fill="{THB}" font-size="11.5" '
             f'text-anchor="end" class="b">pulgar · {vT:.0f} g</text>')
    vI5 = G_I['median']['500']['100']
    s.append(f'<text x="{X(4):.1f}" y="{Y(vI5)+30:.1f}" fill="{IDX}" font-size="11.5" '
             f'text-anchor="middle" class="b">índice · plano en 5–36 g</text>')
    s.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-7}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle" class="ey">SPEED_SET comandado</text>')
    s.append(f'<text transform="translate(15,{(T+H-B)/2:.0f}) rotate(-90)" fill="{MUTED}" '
             f'font-size="11.5" text-anchor="middle" class="ey">ΔF con Fset=100 g  (log)</text>')
    s.append('</svg>')
    return '\n'.join(s)


# ── 3) modo A (v=1000) → modo B, por Fset ────────────────────────────────
def hybrid_svg():
    W, H = 936, 330
    L, R, T, B = 66, 26, 34, 54
    lo, hi = 1.5, 5200.0
    Y = lambda v: sx(math.log10(max(v, lo)), math.log10(hi), math.log10(lo), T, H - B)
    span = (W - R - L) / len(FSETS)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Caída del sobreimpulso al pasar '
         f'del modo A a velocidad 1000 al modo B híbrido, por FORCE_SET y por dedo">']
    for gy in (10, 100, 1000):
        s.append(f'<line x1="{L}" y1="{Y(gy):.1f}" x2="{W-R}" y2="{Y(gy):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{Y(gy)+4:.1f}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="end" class="mono">{gy}</text>')
    for i, F in enumerate(FSETS):
        cx = L + span * (i + 0.5)
        s.append(f'<text x="{cx:.1f}" y="{H-B+18}" fill="{MUTED}" font-size="11.5" '
                 f'text-anchor="middle" class="mono">{F}</text>')
        for j, ((lab, color), G, Bh) in enumerate(((FINGERS[0], G_I, B_I), (FINGERS[1], G_T, B_T))):
            x = cx + (j - 0.5) * 34
            a = G['median']['1000'][str(F)]; b = Bh[F]
            s.append(f'<line x1="{x:.1f}" y1="{Y(a):.1f}" x2="{x:.1f}" y2="{Y(b):.1f}" '
                     f'stroke="{color}" stroke-width="2" opacity="0.42"/>')
            # modo A: anillo hueco · modo B: punto lleno
            s.append(f'<circle cx="{x:.1f}" cy="{Y(a):.1f}" r="5" fill="#fff" '
                     f'stroke="{color}" stroke-width="2"/>')
            s.append(f'<circle cx="{x:.1f}" cy="{Y(b):.1f}" r="5" fill="{color}" '
                     f'stroke="#fff" stroke-width="1.6"/>')
            # si el punto está pegado al eje, la etiqueta se va al lado en vez de debajo
            yb = Y(b)
            if yb + 18 < H - B - 10:
                s.append(f'<text x="{x:.1f}" y="{yb+18:.1f}" fill="{color}" font-size="10.5" '
                         f'text-anchor="middle" class="mono">{b:.0f}</text>')
            else:
                s.append(f'<text x="{x+11:.1f}" y="{yb+4:.1f}" fill="{color}" font-size="10.5" '
                         f'class="mono">{b:.0f}</text>')
            s.append(f'<text x="{x:.1f}" y="{Y(a)-10:.1f}" fill="{color}" font-size="10.5" '
                     f'text-anchor="middle" class="mono">{a:.0f}</text>')
    s.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-8}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle" class="ey">FORCE_SET  (g)</text>')
    s.append(f'<text transform="translate(16,{(T+H-B)/2:.0f}) rotate(-90)" fill="{MUTED}" '
             f'font-size="11.5" text-anchor="middle" class="ey">ΔF  (g, log)</text>')
    s.append('</svg>')
    return '\n'.join(s)


def legend(items, extra=''):
    li = ''.join(f'<span class="li"><span class="sw" style="background:{c}"></span>{esc(n)}</span>'
                 for n, c in items)
    return f'<div class="legend">{li}{extra}</div>'


k_i = sum(v * float(S_I[v]['slope_cps_mean']) for v in (100, 250, 500)) / sum(v * v for v in (100, 250, 500))
k_t = sum(v * float(S_T[v]['slope_cps_mean']) for v in (100, 250, 500)) / sum(v * v for v in (100, 250, 500))
red = {F: G_T['median']['1000'][str(F)] / B_T[F] for F in FSETS}

rows = ''.join(
    f'<tr><td class="mono b">{F}</td>'
    f'<td class="mono">{G_I["median"]["1000"][str(F)]:.0f}</td><td class="mono">{B_I[F]:.0f}</td>'
    f'<td class="mono">{G_T["median"]["1000"][str(F)]:.0f}</td><td class="mono">{B_T[F]:.0f}</td>'
    f'<td class="mono b">{red[F]:.0f}×</td></tr>' for F in FSETS)

HTML = f'''<title>Índice vs Pulgar · RH56DFTP</title>
<style>
  :root{{--ink:{INK};--muted:{MUTED};--hair:{HAIR};--idx:{IDX};--thb:{THB};
    --bg:#f6f8fb;--panel:#ffffff;}}
  *{{box-sizing:border-box;}}
  body{{background:var(--bg);margin:0;}}
  .wrap{{max-width:1000px;margin:0 auto;padding:44px 24px 64px;color:var(--ink);
    background:var(--bg);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.55;}}
  .mono{{font-family:ui-monospace,"SF Mono","JetBrains Mono",Menlo,monospace;
    font-variant-numeric:tabular-nums;}}
  .b{{font-weight:600;}} .ey{{letter-spacing:.14em;text-transform:uppercase;}}
  .eyebrow{{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--idx);
    font-weight:600;}}
  h1{{font-size:30px;line-height:1.15;margin:.35rem 0 .5rem;text-wrap:balance;letter-spacing:-.01em;}}
  .dek{{color:var(--muted);font-size:16.5px;max-width:64ch;margin:0;}}
  .rule{{height:1px;background:var(--hair);border:0;margin:26px 0;}}
  .panel{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;
    padding:18px 18px 12px;box-shadow:0 1px 2px rgba(18,24,31,.04);}}
  .cap{{font-size:12px;color:var(--muted);margin:2px 2px 12px;}}
  .cap b{{color:var(--ink);}}
  figure{{margin:0;}}
  .legend{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:2px 2px 10px;
    font-size:12.5px;}}
  .legend .li{{display:inline-flex;align-items:center;gap:6px;color:var(--ink);}}
  .legend .sw{{width:22px;height:4px;border-radius:2px;display:inline-block;}}
  .legend .note{{color:var(--muted);}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;}}
  @media(max-width:760px){{.grid2{{grid-template-columns:1fr;}}}}
  svg{{width:100%;height:auto;display:block;}}
  .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0 22px;}}
  .kpi{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;padding:14px 16px;}}
  .kpi .n{{font-size:24px;font-weight:600;letter-spacing:-.01em;}}
  .kpi .n .u{{font-size:14px;color:var(--muted);font-weight:500;}}
  .kpi .l{{font-size:12px;color:var(--muted);margin-top:2px;}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;}}
  th,td{{text-align:right;padding:8px 10px;border-bottom:1px solid var(--hair);}}
  th:first-child,td:first-child{{text-align:left;}}
  th{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600;}}
  .foot{{font-size:12.5px;color:var(--muted);margin-top:22px;}}
  .foot code{{font-family:ui-monospace,Menlo,monospace;color:var(--ink);background:#eef2f7;
    padding:1px 5px;border-radius:4px;font-size:12px;}}
</style>
<div class="wrap">
  <div class="eyebrow">Réplica del protocolo · Índice vs Pulgar</div>
  <h1>La misma calibración de velocidad en los dos dedos, pero una sola mitigación sobrevive al cambio de dedo</h1>
  <p class="dek">Inspire RH56DFTP. El protocolo de caracterización dinámica ejecutado sobre el <span class="mono">DOF&nbsp;3</span> (índice) y replicado sobre el <span class="mono">DOF&nbsp;4</span> (flexión del pulgar) con la rotación anclada en oposición. 100 trials de escalón y 200 de contacto por dedo.</p>

  <div class="kpis">
    <div class="kpi"><div class="n">{k_i:.2f} <span class="u">vs</span> {k_t:.2f}</div><div class="l">counts/s por unidad de <span class="mono">SPEED_SET</span> — índice y pulgar</div></div>
    <div class="kpi"><div class="n">{G_T['median']['1000']['100']/G_I['median']['1000']['100']:.0f}×<span class="u"> peor</span></div><div class="l">ΔF del pulgar con <span class="mono">Fset=100</span> a v=1000: el "setpoint seguro" no generaliza</div></div>
    <div class="kpi"><div class="n">{min(red.values()):.0f}–{max(red.values()):.0f}×</div><div class="l">reducción de ΔF con el modo híbrido en el pulgar</div></div>
  </div>

  <div class="grid2">
    <figure class="panel">
      {legend(FINGERS)}
      {slope_svg()}
      <figcaption class="cap"><b>Figura 1.</b> La pendiente del tramo lineal escala igual en los dos dedos: <span class="mono">k ≈ {k_i:.2f}</span> y <span class="mono">{k_t:.2f}</span> counts/s por unidad de <span class="mono">SPEED_SET</span>. <span class="mono">SPEED_SET</span> calibra el <b>actuador</b>, no el ángulo. El pulgar se despega de la recta solo en el extremo (−12&nbsp;% a v=1000), su techo de velocidad.</figcaption>
    </figure>
    <figure class="panel">
      {legend(FINGERS)}
      {fset100_svg()}
      <figcaption class="cap"><b>Figura 2.</b> El hallazgo central. Con <span class="mono">Fset=100&nbsp;g</span> el índice mantiene el sobreimpulso plano en 5–36&nbsp;g <b>a cualquier velocidad</b>: el firmware frena antes de que se forme el impacto. En el pulgar esa protección <b>no existe</b> — el mismo ajuste crece hasta 1397&nbsp;g. La diferencia sigue a la rigidez del contacto: 6.4 g/count contra 1.6.</figcaption>
    </figure>
  </div>

  <hr class="rule">
  <figure class="panel">
    {legend(FINGERS, '<span class="li note">○ modo A a v=1000 &nbsp;·&nbsp; ● modo B híbrido</span>')}
    {hybrid_svg()}
    <figcaption class="cap"><b>Figura 3.</b> La conmutación de velocidad (aproximación rápida + cierre lento) colapsa el sobreimpulso <b>en los dos dedos y para todo <span class="mono">Fset</span></b>, entre 30× y 82×. Ataca la causa —el momento en el instante del contacto— y por eso generaliza, mientras que bajar el <span class="mono">Fset</span> depende de la rigidez del contacto y no.</figcaption>
  </figure>

  <hr class="rule">
  <div class="panel" style="padding-bottom:6px">
    <div style="font-weight:600;font-size:13.5px;margin:2px 2px 12px">ΔF a v=1000: modo A frente a modo B <span class="mono" style="color:var(--muted);font-weight:400">· mediana de 5 trials, g</span></div>
    <div style="overflow-x:auto">
    <table>
      <thead><tr><th>FORCE_SET</th><th>Índice · A</th><th>Índice · B</th><th>Pulgar · A</th><th>Pulgar · B</th><th>Reducción (pulgar)</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>
  </div>

  <p class="foot">Datos: <code>exp1/data</code>, <code>exp1/data_dof4</code>, <code>exp2/data*</code>. Generado por <code>compare_dof_figure.py</code> (Python puro). Paleta categórica validada con el verificador del skill <code>dataviz</code>: ΔE 22.3 (protan) y 27.2 (visión normal), todas las comprobaciones PASS.</p>
</div>'''

if __name__ == '__main__':
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    open(DST, 'w').write(HTML)
    print(f"escrito: {DST} ({len(HTML)} bytes)")
    print(f"  k índice={k_i:.2f}  k pulgar={k_t:.2f}  "
          f"reducción modo B pulgar={min(red.values()):.0f}-{max(red.values()):.0f}x")
