#!/usr/bin/env python3
"""Figura: distribución del sobreimpulso del pulgar a máxima velocidad.

El mapa de ΔF reporta medianas, y la mediana esconde lo que aquí importa: a
`v=1000, Fset=100` los impactos **no** forman una distribución unimodal alrededor
de ~900 g. Hay dos regímenes separados por un hueco de 500 g, y el discriminante
no es la geometría del contacto sino si el dedo se relaja tras el impacto.

  · 51/55 impactos: pico ~900 g y el dedo REBOTA (fuerza de régimen ~91 g)
  ·  4/55 impactos: pico ~1800 g y el dedo SE QUEDA CARGADO (régimen ~676 g)

Datos: los 40 trials dedicados de `data_dof4_termico/` + los 15 de esa misma
celda y montaje en `data_dof4/`. Modo B (`data_dof4_hybrid/`) como referencia.

Color: rampa ordinal de un solo tono sobre el ámbar del pulgar, verificada con el
validador del skill dataviz (monotonía de luminosidad, salto ΔL, contraste del
extremo claro y tono único: todas PASS).
"""
from __future__ import annotations

import csv
import os
import statistics as st

_HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(_HERE, 'exp2', 'figures', 'exp2_dof4_distribucion.html')

LOW, HIGH = '#D9A441', '#B4740F'      # rampa ordinal (rebota / se queda cargado)
INK, MUTED, HAIR, GRID = '#12181f', '#5a6472', '#dbe2ec', '#eef2f7'
SPLIT = 1500                           # el hueco de la distribución cae en 1100-1600


def num(x):
    return float(x) if x not in ('', None) else None


def load():
    rows = []
    for p, only in ((os.path.join(_HERE, 'exp2/data_dof4_termico/grid_index.csv'), False),
                    (os.path.join(_HERE, 'exp2/data_dof4/grid_index.csv'), True)):
        for x in csv.DictReader(open(p)):
            if only and not (int(x['fset']) == 100 and int(x['speed']) == 1000
                             and x.get('mount') == 'm3'):
                continue
            if x['delta_f'] and x['f_settle']:
                rows.append((num(x['delta_f']), num(x['f_settle'])))
    return rows


A = load()
B = sorted(num(x['delta_f']) for x in
           csv.DictReader(open(os.path.join(_HERE, 'exp2/data_dof4_hybrid/grid_index.csv')))
           if int(x['fset']) == 100 and x['delta_f'])
dfs = sorted(v for v, _ in A)
hi = [v for v in dfs if v > SPLIT]
lo = [v for v in dfs if v <= SPLIT]
MED = st.median(dfs)


def sx(x, x0, x1, p0, p1):
    return p0 + (x - x0) / (x1 - x0) * (p1 - p0)


# ── histograma ───────────────────────────────────────────────────────────
def hist_svg():
    W, H = 936, 320
    L, R, T, Bm = 52, 26, 30, 56
    x0, x1, BIN = 0, 2050, 100
    ymax = 30
    X = lambda v: sx(v, x0, x1, L, W - R)
    Y = lambda v: sx(v, ymax, 0, T, H - Bm)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Histograma del sobreimpulso de '
         f'fuerza del pulgar a velocidad máxima: 51 impactos agrupados cerca de 900 gramos, '
         f'un hueco, y 4 impactos aislados por encima de 1600">']
    for gy in (0, 10, 20, 30):
        s.append(f'<line x1="{L}" y1="{Y(gy):.1f}" x2="{W-R}" y2="{Y(gy):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{Y(gy)+4:.1f}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="end" class="mono">{gy}</text>')
    for xv in range(0, 2001, 250):
        s.append(f'<text x="{X(xv):.1f}" y="{H-Bm+17}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="middle" class="mono">{xv}</text>')
    # barras: 2 px de hueco entre vecinas, sin borde
    bw = X(BIN) - X(0) - 2
    for b in range(0, 2050, BIN):
        c = sum(1 for v in dfs if b <= v < b + BIN)
        if not c:
            continue
        col = HIGH if b > SPLIT else LOW
        s.append(f'<rect x="{X(b)+1:.1f}" y="{Y(c):.1f}" width="{bw:.1f}" '
                 f'height="{Y(0)-Y(c):.1f}" fill="{col}" rx="3"/>')
        if c >= 5:
            s.append(f'<text x="{X(b)+1+bw/2:.1f}" y="{Y(c)-6:.1f}" fill="{col}" '
                     f'font-size="11" text-anchor="middle" class="mono b">{c}</text>')
    # modo B: marcador de referencia, NO una barra (su N es distinto)
    bx0, bx1 = X(min(B)), X(max(B))
    s.append(f'<line x1="{bx0:.1f}" y1="{Y(0):.1f}" x2="{bx1+3:.1f}" y2="{Y(0):.1f}" '
             f'stroke="{INK}" stroke-width="4"/>')
    s.append(f'<line x1="{(bx0+bx1)/2:.1f}" y1="{Y(0):.1f}" x2="{(bx0+bx1)/2:.1f}" '
             f'y2="{Y(0)-52:.1f}" stroke="{INK}" stroke-width="1"/>')
    s.append(f'<text x="{(bx0+bx1)/2+7:.1f}" y="{Y(0)-56:.1f}" fill="{INK}" font-size="11.5" '
             f'class="b">modo B</text>')
    s.append(f'<text x="{(bx0+bx1)/2+7:.1f}" y="{Y(0)-42:.1f}" fill="{MUTED}" font-size="11" '
             f'class="mono">{min(B):.0f}–{max(B):.0f} g · N={len(B)}</text>')
    # el hueco (el vacío ya lo dice; basta nombrarlo)
    s.append(f'<text x="{X(1350):.1f}" y="{Y(0)-14:.1f}" fill="{MUTED}" font-size="11" '
             f'text-anchor="middle">500 g sin un solo impacto</text>')
    # la cola, como GRUPO: 4 barras de altura 1 no se leen sueltas
    tx0, tx1 = X(1600), X(2000)   # abarca las barras, no los valores
    ty = Y(0) - 30
    s.append(f'<path d="M {tx0:.1f} {ty+7:.1f} L {tx0:.1f} {ty:.1f} L {tx1:.1f} {ty:.1f} '
             f'L {tx1:.1f} {ty+7:.1f}" fill="none" stroke="{HIGH}" stroke-width="1.4"/>')
    s.append(f'<text x="{(tx0+tx1)/2:.1f}" y="{ty-7:.1f}" fill="{HIGH}" font-size="11.5" '
             f'text-anchor="middle" class="b">{len(hi)} impactos · {max(dfs)/MED:.1f}× la mediana</text>')
    # mediana
    s.append(f'<line x1="{X(MED):.1f}" y1="{T}" x2="{X(MED):.1f}" y2="{Y(0):.1f}" '
             f'stroke="{INK}" stroke-width="1" opacity="0.45"/>')
    s.append(f'<text x="{X(MED)+6:.1f}" y="{T+11}" fill="{INK}" font-size="11" '
             f'class="mono">mediana {MED:.0f}</text>')
    s.append(f'<line x1="{L}" y1="{Y(0):.1f}" x2="{W-R}" y2="{Y(0):.1f}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-8}" fill="{MUTED}" font-size="12" '
             f'text-anchor="middle" class="ey">ΔF = F_max − Fset  (g)</text>')
    s.append(f'<text transform="translate(14,{(T+H-Bm)/2:.0f}) rotate(-90)" fill="{MUTED}" '
             f'font-size="12" text-anchor="middle" class="ey">impactos</text>')
    s.append('</svg>')
    return '\n'.join(s)


# ── dispersión ΔF vs fuerza de régimen ───────────────────────────────────
def scatter_svg():
    W, H = 452, 320
    L, R, T, Bm = 58, 24, 26, 54
    X = lambda v: sx(v, 0, 900, L, W - R)
    Y = lambda v: sx(v, 2100, 600, T, H - Bm)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Sobreimpulso frente a fuerza de '
         f'régimen: los impactos altos son los que no se relajan tras tocar">']
    for gy in (600, 1000, 1400, 1800):
        s.append(f'<line x1="{L}" y1="{Y(gy):.1f}" x2="{W-R}" y2="{Y(gy):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{Y(gy)+4:.1f}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="end" class="mono">{gy}</text>')
    for xv in (0, 300, 600, 900):
        s.append(f'<text x="{X(xv):.1f}" y="{H-Bm+17}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="middle" class="mono">{xv}</text>')
    for d, f in A:
        col = HIGH if d > SPLIT else LOW
        s.append(f'<circle cx="{X(min(f,900)):.1f}" cy="{Y(min(d,2100)):.1f}" r="4.6" '
                 f'fill="{col}" stroke="#fff" stroke-width="1.6" opacity="0.95"/>')
    s.append(f'<text x="{X(300):.1f}" y="{Y(840):.1f}" fill="{LOW}" font-size="11.5" '
             f'class="b">rebota y se relaja · {len(lo)}</text>')
    s.append(f'<text x="{X(720):.1f}" y="{Y(2010):.1f}" fill="{HIGH}" font-size="11.5" '
             f'text-anchor="middle" class="b">se queda cargado · 3</text>')
    odd = min((r for r in A if r[0] > SPLIT), key=lambda r: r[1])
    s.append(f'<text x="{X(odd[1])+13:.1f}" y="{Y(odd[0])+4:.1f}" fill="{MUTED}" '
             f'font-size="11">…pero el 4º sí se relajó</text>')
    s.append(f'<line x1="{L}" y1="{H-Bm}" x2="{W-R}" y2="{H-Bm}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-Bm}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-7}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle" class="ey">fuerza de régimen tras el impacto (g)</text>')
    s.append(f'<text transform="translate(14,{(T+H-Bm)/2:.0f}) rotate(-90)" fill="{MUTED}" '
             f'font-size="11.5" text-anchor="middle" class="ey">ΔF  (g)</text>')
    s.append('</svg>')
    return '\n'.join(s)


kpi = [(f"{len(hi)}/{len(dfs)}", f"impactos que llegan a ~{st.median(hi):.0f} g en vez de ~{st.median(lo):.0f}"),
       (f"{max(dfs)/MED:.1f}×", "el peor impacto frente a la mediana"),
       (f"{max(B):.0f} g", "el peor sobreimpulso del modo B, contra "
        f"{max(dfs):.0f} g del modo directo")]

HTML = f'''<title>Dos regímenes de impacto</title>
<style>
  :root{{--ink:{INK};--muted:{MUTED};--hair:{HAIR};--low:{LOW};--high:{HIGH};
    --bg:#f6f8fb;--panel:#ffffff;}}
  *{{box-sizing:border-box;}}
  body{{background:var(--bg);color:var(--ink);margin:0;}}
  .wrap{{max-width:1000px;margin:0 auto;padding:44px 24px 64px;background:var(--bg);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.55;}}
  .mono{{font-family:ui-monospace,"SF Mono","JetBrains Mono",Menlo,monospace;
    font-variant-numeric:tabular-nums;}}
  .b{{font-weight:600;}} .ey{{letter-spacing:.14em;text-transform:uppercase;}}
  .eyebrow{{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--high);
    font-weight:600;}}
  h1{{font-size:30px;line-height:1.15;margin:.35rem 0 .5rem;text-wrap:balance;letter-spacing:-.01em;}}
  .dek{{color:var(--muted);font-size:16.5px;max-width:64ch;margin:0;}}
  .rule{{height:1px;background:var(--hair);border:0;margin:26px 0;}}
  .panel{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;
    padding:18px 18px 12px;box-shadow:0 1px 2px rgba(18,24,31,.04);}}
  .cap{{font-size:12px;color:var(--muted);margin:2px 2px 12px;}}
  .cap b{{color:var(--ink);}}
  figure{{margin:0;}}
  .legend{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:2px 2px 10px;font-size:12.5px;}}
  .legend .li{{display:inline-flex;align-items:center;gap:6px;}}
  .legend .sw{{width:22px;height:10px;border-radius:3px;display:inline-block;}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;}}
  @media(max-width:760px){{.grid2{{grid-template-columns:1fr;}}}}
  svg{{width:100%;height:auto;display:block;}}
  .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0 22px;}}
  .kpi{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;padding:14px 16px;}}
  .kpi .n{{font-size:25px;font-weight:600;letter-spacing:-.01em;}}
  .kpi .l{{font-size:12px;color:var(--muted);margin-top:2px;}}
  .foot{{font-size:12.5px;color:var(--muted);margin-top:22px;}}
  .foot code{{font-family:ui-monospace,Menlo,monospace;color:var(--ink);background:#eef2f7;
    padding:1px 5px;border-radius:4px;font-size:12px;}}
</style>
<div class="wrap">
  <div class="eyebrow">Pulgar · velocidad máxima · umbral 100 g</div>
  <h1>El sobreimpulso no tiene un valor típico: tiene dos</h1>
  <p class="dek">55 impactos del pulgar contra el bloque rígido a <span class="mono">SPEED_SET&nbsp;=&nbsp;1000</span> con el umbral de fuerza en su valor más bajo. El mapa de ΔF reporta la mediana, y la mediana esconde justo lo que decide si un objeto delicado sobrevive.</p>

  <div class="kpis">
    {''.join(f'<div class="kpi"><div class="n">{v}</div><div class="l">{l}</div></div>' for v, l in kpi)}
  </div>

  <figure class="panel">
    <div class="legend">
      <span class="li"><span class="sw" style="background:{LOW}"></span>el dedo rebota y se relaja</span>
      <span class="li"><span class="sw" style="background:{HIGH}"></span>el dedo se queda cargado</span>
      <span class="li" style="color:var(--muted)">▮ modo B (híbrido), como referencia</span>
    </div>
    {hist_svg()}
    <figcaption class="cap"><b>Figura 1.</b> La distribución no es unimodal: {len(lo)} impactos se agrupan entre {min(lo):.0f} y {max(lo):.0f}&nbsp;g, no hay <b>ninguno</b> en los 500&nbsp;g siguientes, y {len(hi)} llegan a {min(hi):.0f}–{max(hi):.0f}&nbsp;g. El modo B, a la izquierda, no está en la misma escala del problema: sus {len(B)} trials caben en {min(B):.0f}–{max(B):.0f}&nbsp;g.</figcaption>
  </figure>

  <hr class="rule">
  <div class="grid2">
    <figure class="panel">
      {scatter_svg()}
      <figcaption class="cap"><b>Figura 2.</b> Lo que <b>no</b> los separa: la posición del contacto es la misma dentro de 4&nbsp;counts, y el residual por flexión es idéntico. Lo que sí acompaña al régimen duro es que el dedo <b>no se relaja</b>: <b>3 de los 4</b> quedan en 673–780&nbsp;g de fuerza sostenida frente a ~91&nbsp;g del grupo suave. El cuarto sí se relajó, así que con N=4 esto es una pista del mecanismo, <b>no una explicación establecida</b>.</figcaption>
    </figure>
    <div class="panel">
      <div class="b" style="font-size:13.5px;margin:2px 2px 10px">Por qué importa para el agarre</div>
      <p style="font-size:14.5px;margin:0 0 12px">Dimensionar el agarre con la mediana (~{MED:.0f}&nbsp;g) da una respuesta equivocada. Un objeto que aguante esa fuerza no falla «a veces»: falla en <b>1 de cada {len(dfs)//len(hi)}</b> agarres, y cuando falla recibe además <b>presión sostenida</b>, no solo un pico.</p>
      <p style="font-size:14.5px;margin:0 0 12px">El régimen duro <b>no se anuncia</b>: ocurre en la misma posición de contacto, con el mismo residual y el mismo comando. Nada en la señal permite anticiparlo desde el lado del control. En 3 de los 4 casos el dedo además se queda cargado en vez de relajarse, pero con N=4 eso es una pista, no una explicación.</p>
      <p style="font-size:14.5px;margin:0">Por eso la mitigación correcta no es acotar el pico en promedio sino <b>no llegar a impactar</b>. El modo B suprime el régimen duro entero: sus {len(B)} trials caben en {max(B):.0f}&nbsp;g, un orden de magnitud por debajo del grupo suave.</p>
    </div>
  </div>

  <p class="foot">N={len(dfs)}: {len(A)-15} trials dedicados (<code>data_dof4_termico/</code>) + 15 de la misma celda y montaje en <code>data_dof4/</code>. Modo B: <code>data_dof4_hybrid/</code>. Generado por <code>impact_distribution_figure.py</code>. Rampa ordinal de un tono verificada con el validador del skill <code>dataviz</code>.</p>
</div>'''

if __name__ == '__main__':
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    open(DST, 'w').write(HTML)
    print(f"escrito: {DST} ({len(HTML)} bytes)")
    print(f"  N={len(dfs)}  mediana {MED:.0f}  grupo duro {len(hi)} ({min(hi):.0f}-{max(hi):.0f} g)  "
          f"modo B {min(B):.0f}-{max(B):.0f} g")
