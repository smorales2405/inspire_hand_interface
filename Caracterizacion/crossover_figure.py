#!/usr/bin/env python3
"""El cruce: con el umbral de fuerza MÁS BAJO el golpe acaba siendo el MÁS FUERTE.

Dos paneles —medio y anular— con ΔF frente a la velocidad de cierre para las dos
columnas extremas del grid, `Fset` 100 y 1000. A baja velocidad el umbral bajo da
menos sobreimpulso, como dice la intuición; a alta velocidad da MÁS. Las dos
curvas se cruzan, y el cruce está en los dos dedos.

Es la figura del hallazgo: durante meses el proyecto sostuvo que un `Fset` bajo
era la "zona segura" del índice, cuando en realidad aquel dedo nunca llegaba a
tocar el objeto con ese ajuste. El medio es el primer DOF que sí lo alcanza a
todas las velocidades, y lo que muestra es lo contrario de la creencia.
"""
import json, math, os

_HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(_HERE, 'exp2', 'figures', 'exp2_cruce_fset.html')

# Rampa ORDINAL de un solo tono (Fset bajo → alto), la misma que la figura de la
# distribución de impactos. No es categórica: los dos niveles están ordenados.
LO, HI = '#D9A441', '#B4740F'
INK, MUTED, HAIR, GRID = '#12181f', '#5a6472', '#dbe2ec', '#eef2f7'


def grid(d):
    return json.load(open(os.path.join(_HERE, 'exp2', d, 'exp2_overshoot_grid.json')))


G = {'Medio (DOF 2)': grid('data_dof2_tcp'), 'Anular (DOF 1)': grid('data_dof1_tcp')}


def sx(x, x0, x1, p0, p1):
    return p0 + (x - x0) / (x1 - x0) * (p1 - p0)


def panel(name, g):
    W, H = 452, 320
    L, R, T, B = 60, 26, 30, 52
    VS = [int(v) for v in g['speeds']]
    lo, hi = 15.0, 4200.0
    X = lambda i: sx(i, 0, len(VS) - 1, L + 10, W - R - 10)
    Y = lambda v: sx(math.log10(max(v, lo)), math.log10(hi), math.log10(lo), T, H - B)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Sobreimpulso frente a la '
         f'velocidad de cierre en {name}, para umbral de fuerza 100 y 1000 gramos, '
         f'escala logarítmica: las dos curvas se cruzan">']
    for gy in (100, 1000):
        s.append(f'<line x1="{L}" y1="{Y(gy):.1f}" x2="{W-R}" y2="{Y(gy):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{Y(gy)+4:.1f}" fill="{MUTED}" font-size="11" '
                 f'text-anchor="end" class="mono">{gy}</text>')
    for i, v in enumerate(VS):
        s.append(f'<text x="{X(i):.1f}" y="{H-B+17}" fill="{MUTED}" font-size="10.5" '
                 f'text-anchor="middle" class="mono">{v}</text>')

    series = []
    for F, color in ((100, LO), (1000, HI)):
        pts = [(X(i), Y(g['median'][str(v)][str(F)])) for i, v in enumerate(VS)
               if g['median'][str(v)].get(str(F)) is not None]
        series.append((F, color, pts))
        s.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) +
                 f'" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round"/>')
        for x, y in pts:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="{color}" '
                     f'stroke="#fff" stroke-width="2"/>')

    # Etiqueta directa en el extremo derecho, que es donde está el mensaje.
    for F, color, pts in series:
        val = g['median']['1000'][str(F)]
        dy = -12 if F == 100 else 18
        s.append(f'<text x="{pts[-1][0]-6:.1f}" y="{pts[-1][1]+dy:.1f}" fill="{color}" '
                 f'font-size="11.5" text-anchor="end" class="b">Fset {F} · {val:.0f} g</text>')

    # Marca del cruce: primera velocidad en que la columna baja supera a la alta.
    cross = next((i for i, v in enumerate(VS)
                  if g['median'][str(v)]['100'] > g['median'][str(v)]['1000']), None)
    if cross:
        xc = (X(cross - 1) + X(cross)) / 2
        s.append(f'<line x1="{xc:.1f}" y1="{T}" x2="{xc:.1f}" y2="{H-B}" stroke="{INK}" '
                 f'stroke-width="1" stroke-dasharray="3 3" opacity="0.35"/>')
        # La nota va arriba a la IZQUIERDA, no junto a la línea: a la derecha
        # compiten con ella las etiquetas directas de las dos series, y en el
        # anular el cruce cae tan tarde que el texto se les montaba encima.
        # Abajo a la izquierda las dos curvas están en su mínimo, así que esa
        # esquina superior queda libre en los dos paneles.
        s.append(f'<text x="{L+12}" y="{T+12:.1f}" fill="{INK}" font-size="10.5">'
                 f'a partir de aquí el umbral bajo</text>')
        s.append(f'<text x="{L+12}" y="{T+25:.1f}" fill="{INK}" font-size="10.5">'
                 f'golpea <tspan class="b">MÁS</tspan> fuerte →</text>')

    s.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-8}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle" class="ey">SPEED_SET comandado</text>')
    s.append(f'<text transform="translate(14,{(T+H-B)/2:.0f}) rotate(-90)" fill="{MUTED}" '
             f'font-size="11.5" text-anchor="middle" class="ey">ΔF  (g, log)</text>')
    s.append('</svg>')
    return '\n'.join(s)


HTML = f'''<title>El cruce del umbral de fuerza · RH56DFTP</title>
<style>
  :root{{--ink:{INK};--muted:{MUTED};--hair:{HAIR};--bg:#f6f8fb;--panel:#fff;}}
  body{{background:var(--bg);color:var(--ink);margin:0;
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}}
  .wrap{{max-width:1000px;margin:0 auto;padding:40px 24px 60px;}}
  .mono{{font-family:ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums;}}
  .b{{font-weight:600;}} .ey{{letter-spacing:.14em;text-transform:uppercase;}}
  h1{{font-size:27px;margin:.3rem 0 .6rem;letter-spacing:-.015em;max-width:26ch;}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
  @media(max-width:760px){{.grid2{{grid-template-columns:1fr;}}}}
  .panel{{background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:14px;}}
  .tt{{font-weight:600;font-size:13.5px;margin:0 0 8px;}}
  svg{{width:100%;height:auto;display:block;}}
  .cap{{font-size:12.5px;color:var(--muted);margin-top:12px;line-height:1.55;}}
  .cap b{{color:var(--ink);}}
  .legend{{display:flex;gap:16px;font-size:12px;color:var(--muted);margin-bottom:10px;}}
  .sw{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;
    vertical-align:-1px;}}
</style>
<div class="wrap">
  <h1>Con el umbral de fuerza más bajo, el golpe acaba siendo el más fuerte</h1>
  <div class="legend">
    <span><span class="sw" style="background:{LO}"></span>FORCE_SET = 100 g</span>
    <span><span class="sw" style="background:{HI}"></span>FORCE_SET = 1000 g</span>
  </div>
  <div class="grid2">
    <div class="panel"><div class="tt">Medio (DOF 2)</div>{panel('Medio (DOF 2)', G['Medio (DOF 2)'])}</div>
    <div class="panel"><div class="tt">Anular (DOF 1)</div>{panel('Anular (DOF 1)', G['Anular (DOF 1)'])}</div>
  </div>
  <p class="cap"><b>El cruce.</b> A velocidad baja el umbral bajo hace lo que promete: menos
  sobreimpulso. A partir de <span class="mono">v ≈ 500–750</span> las curvas se cruzan y se
  invierte — a máxima velocidad el ajuste de 100 g golpea con
  {G['Medio (DOF 2)']['median']['1000']['100']:.0f} g en el medio y
  {G['Anular (DOF 1)']['median']['1000']['100']:.0f} g en el anular, por encima del de 1000 g
  en los dos dedos. El umbral solo manda mientras el dedo va lo bastante despacio para que el
  firmware alcance a frenar; pasado ese punto lo único que queda es el momento en el instante
  del contacto, y con el umbral bajo el dedo llega ahí habiendo acelerado más recorrido.</p>
</div>'''

os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, 'w').write(HTML)
print(f"escrito: {DST} ({len(HTML)} bytes)")
for n, g in G.items():
    print(f"  {n}: Fset=100 a v=1000 = {g['median']['1000']['100']:.0f} g · "
          f"Fset=1000 = {g['median']['1000']['1000']:.0f} g")
