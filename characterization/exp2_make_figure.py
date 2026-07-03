#!/usr/bin/env python3
"""Figura Exp 2 (hoja técnica HTML): sobreimpulso ΔF vs velocidad, agrupado por Fset."""
import csv, json, os, statistics
from collections import defaultdict

OUT='exp2_out'
DST='characterization/figures/exp2_force_overshoot.html'

grid=json.load(open(os.path.join(OUT,'exp2_overshoot_grid.json')))
speeds=grid['speeds']; fsets=grid['fsets']
med=grid['median']; q1=grid['q1']; q3=grid['q3']; ab=grid['abort']
def M(v,F): return med[str(v)][str(F)]
def Q1(v,F): return q1[str(v)][str(F)]
def Q3(v,F): return q3[str(v)][str(F)]
def AB(v,F): return ab[str(v)][str(F)] or 0

# rampa secuencial por Fset (claro→oscuro), igual sistema que Exp 1
RAMP=['#9FC2E0','#6FA3D2','#4682BE','#285F97','#123F63']
ACCENT='#285F97'; AMBER='#B4740F'
INK='#12181f'; MUTED='#5a6472'; HAIR='#dbe2ec'; GRID='#eef2f7'

y1=max(M(v,F) for v in speeds for F in fsets if M(v,F) is not None)*1.10
total_ab=sum(AB(v,F) for v in speeds for F in fsets)

# Modo B (híbrido): mediana de ΔF por Fset
_bd=defaultdict(list)
for _r in csv.DictReader(open('exp2_out_hybrid/grid_index.csv')):
    try: _bd[int(_r['fset'])].append(float(_r['delta_f']))
    except (ValueError,TypeError): pass
modeB={F:statistics.median(_bd[F]) for F in fsets if _bd[F]}
# factor de reducción B vs A rápido (v=1000), promediado sobre Fset>=250
_red=[M(1000,F)/modeB[F] for F in fsets if F>=250 and modeB.get(F)]
red_factor=round(sum(_red)/len(_red)) if _red else None
b_max=max(modeB.values()) if modeB else None

def rtop(x,y,w,h,r):
    r=max(0,min(r,w/2,h))
    return (f"M{x:.1f} {y+h:.1f} L{x:.1f} {y+r:.1f} Q{x:.1f} {y:.1f} {x+r:.1f} {y:.1f} "
            f"L{x+w-r:.1f} {y:.1f} Q{x+w:.1f} {y:.1f} {x+w:.1f} {y+r:.1f} L{x+w:.1f} {y+h:.1f} Z")

def bars_svg():
    W,H=770,430
    L,R,T,B=64,18,22,54
    pw=W-L-R; ph=H-T-B
    ng=len(speeds); gw=pw/ng
    nb=len(fsets); pad=gw*0.10; bw=(gw-2*pad)/nb
    def Y(v): return T+ph*(1-v/y1)
    s=[f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Sobreimpulso de fuerza vs velocidad, agrupado por Fset">']
    # grid y + labels
    for gy in [0,500,1000,1500,2000,2500,3000]:
        if gy>y1: continue
        py=Y(gy)
        s.append(f'<line x1="{L}" y1="{py:.1f}" x2="{W-R}" y2="{py:.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{py+4:.1f}" fill="{MUTED}" font-size="11" text-anchor="end" class="mono">{gy}</text>')
    # techo de seguridad 2200
    if 2200<y1:
        py=Y(2200)
        s.append(f'<line x1="{L}" y1="{py:.1f}" x2="{W-R}" y2="{py:.1f}" stroke="{AMBER}" stroke-width="1" stroke-dasharray="4 3" opacity="0.7"/>')
        s.append(f'<text x="{W-R:.0f}" y="{py-5:.1f}" fill="{AMBER}" font-size="10.5" text-anchor="end" class="mono">techo seguridad 2200 g</text>')
    baseline=T+ph
    for sg,v in enumerate(speeds):
        gx=L+sg*gw+pad
        for sf,F in enumerate(fsets):
            m=M(v,F)
            if m is None: continue
            bx=gx+sf*bw
            top=Y(max(m,0)); bh=baseline-top
            s.append(f'<path d="{rtop(bx+1,top,bw-2,bh,3)}" fill="{RAMP[sf]}"/>')
            # whisker IQR (recortado al área positiva visible)
            a,b=Q1(v,F),Q3(v,F)
            if a is not None and b is not None:
                a=max(0.0,a); b=max(0.0,b)
                if b>a+1:
                    cx=bx+bw/2
                    s.append(f'<line x1="{cx:.1f}" y1="{Y(a):.1f}" x2="{cx:.1f}" y2="{Y(b):.1f}" stroke="{INK}" stroke-width="1" opacity="0.55"/>')
            # marca de abort
            if AB(v,F):
                cx=bx+bw/2
                s.append(f'<text x="{cx:.1f}" y="{top-4:.1f}" fill="{AMBER}" font-size="11" text-anchor="middle">▲</text>')
        # etiqueta de velocidad
        s.append(f'<text x="{L+sg*gw+gw/2:.1f}" y="{H-B+18}" fill="{INK}" font-size="12" text-anchor="middle" class="mono b">{v}</text>')
    s.append(f'<line x1="{L}" y1="{baseline:.1f}" x2="{W-R}" y2="{baseline:.1f}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{baseline:.1f}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" fill="{MUTED}" font-size="12.5" text-anchor="middle" class="ey">SPEED_SET (velocidad de cierre)</text>')
    s.append(f'<text transform="translate(15,{(T+baseline)/2:.0f}) rotate(-90)" fill="{MUTED}" font-size="12.5" text-anchor="middle" class="ey">sobreimpulso  ΔF = F_max − Fset  (g)</text>')
    s.append('</svg>')
    return '\n'.join(s)

def compare_svg():
    W,H=770,330
    L,R,T,B=64,132,18,50
    pw=W-L-R; ph=H-T-B
    nx=len(fsets)
    y1c=max(max(M(1000,F) for F in fsets), 100)*1.12
    def X(i): return L+(pw*(i/(nx-1)) if nx>1 else pw/2)
    def Y(v): return T+ph*(1-v/y1c)
    series=[('A · v=1000 (rápido)', [M(1000,F) for F in fsets], AMBER),
            ('A · v=25 (lento)',    [M(25,F)   for F in fsets], RAMP[1]),
            ('B · híbrido',         [modeB.get(F) for F in fsets], ACCENT)]
    s=[f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Comparación de sobreimpulso: modo A rápido, A lento y B híbrido vs Fset">']
    for gy in [0,1000,2000,3000]:
        if gy>y1c: continue
        py=Y(gy)
        s.append(f'<line x1="{L}" y1="{py:.1f}" x2="{W-R}" y2="{py:.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{py+4:.1f}" fill="{MUTED}" font-size="11" text-anchor="end" class="mono">{gy}</text>')
    for i,F in enumerate(fsets):
        s.append(f'<text x="{X(i):.1f}" y="{H-B+18}" fill="{MUTED}" font-size="11" text-anchor="middle" class="mono">{F}</text>')
    for name,ys,color in series:
        pts=[(X(i),Y(y)) for i,y in enumerate(ys) if y is not None]
        if not pts: continue
        s.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="2.4"/>')
        for x,y in pts:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{color}" stroke="#fff" stroke-width="1.2"/>')
        lx,ly=pts[-1]
        s.append(f'<text x="{lx+8:.1f}" y="{ly+4:.1f}" fill="{color}" font-size="12" class="mono b">{name}</text>')
    s.append(f'<line x1="{L}" y1="{Y(0):.1f}" x2="{W-R}" y2="{Y(0):.1f}" stroke="{HAIR}"/>')
    s.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{Y(0):.1f}" stroke="{HAIR}"/>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" fill="{MUTED}" font-size="12.5" text-anchor="middle" class="ey">FORCE_SET (g)</text>')
    s.append(f'<text transform="translate(15,{(T+Y(0))/2:.0f}) rotate(-90)" fill="{MUTED}" font-size="12.5" text-anchor="middle" class="ey">sobreimpulso ΔF (g)</text>')
    s.append('</svg>')
    return '\n'.join(s)

legend=('<div class="legend"><span class="ll">Fset (g) &rarr;</span>'
        + ''.join(f'<span class="li"><span class="sw" style="background:{RAMP[i]}"></span>{F}</span>'
                  for i,F in enumerate(fsets))
        + f'<span class="li" style="margin-left:6px"><span style="color:{AMBER}">▲</span>&nbsp;impacto &gt; techo (abort)</span></div>')

# tabla
def cell_txt(v,F):
    m=M(v,F); a=AB(v,F)
    if m is None: return '—'
    star=f'<span class="pm">▲{a}</span>' if a else ''
    return f'{m:.0f}{star}'
trows=''
for v in speeds:
    trows+=f'<tr><td class="mono b">{v}</td>'+''.join(f'<td class="mono">{cell_txt(v,F)}</td>' for F in fsets)+'</tr>'

HTML=f'''<title>Exp 2 — Sobreimpulso de fuerza en contacto · RH56DFTP</title>
<style>
  :root{{--ink:{INK};--muted:{MUTED};--hair:{HAIR};--accent:{ACCENT};--amber:{AMBER};--bg:#f6f8fb;--panel:#fff;}}
  *{{box-sizing:border-box;}}
  .wrap{{max-width:900px;margin:0 auto;padding:44px 24px 64px;color:var(--ink);background:var(--bg);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.55;}}
  .mono{{font-family:ui-monospace,"SF Mono","JetBrains Mono",Menlo,monospace;font-variant-numeric:tabular-nums;}}
  .b{{font-weight:600;}} .ey{{letter-spacing:.14em;text-transform:uppercase;}}
  .eyebrow{{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);font-weight:600;}}
  h1{{font-size:30px;line-height:1.15;margin:.35rem 0 .5rem;text-wrap:balance;letter-spacing:-.01em;}}
  .dek{{color:var(--muted);font-size:16.5px;max-width:64ch;margin:0;}}
  .rule{{height:1px;background:var(--hair);border:0;margin:26px 0;}}
  .panel{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;padding:18px 18px 12px;box-shadow:0 1px 2px rgba(18,24,31,.04);}}
  .cap{{font-size:12px;color:var(--muted);margin:2px 2px 14px;}} .cap b{{color:var(--ink);}}
  figure{{margin:0;}}
  .legend{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:2px 2px 12px;font-size:12.5px;}}
  .legend .ll{{color:var(--muted);letter-spacing:.1em;text-transform:uppercase;font-size:11px;}}
  .legend .li{{display:inline-flex;align-items:center;gap:6px;color:var(--ink);}}
  .legend .sw{{width:22px;height:10px;border-radius:2px;display:inline-block;}}
  svg{{width:100%;height:auto;display:block;}}
  .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0 4px;}}
  .kpi{{background:var(--panel);border:1px solid var(--hair);border-radius:10px;padding:14px 16px;}}
  .kpi .n{{font-size:24px;font-weight:600;letter-spacing:-.01em;}} .kpi .n .u{{font-size:14px;color:var(--muted);font-weight:500;}}
  .kpi .l{{font-size:12px;color:var(--muted);margin-top:2px;}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;}}
  th,td{{text-align:right;padding:7px 10px;border-bottom:1px solid var(--hair);}}
  th:first-child,td:first-child{{text-align:left;}}
  th{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600;}}
  .pm{{color:var(--amber);font-size:10.5px;margin-left:3px;}}
  .foot{{font-size:12.5px;color:var(--muted);margin-top:22px;}}
  .foot code{{font-family:ui-monospace,Menlo,monospace;color:var(--ink);background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:12px;}}
  .tag{{display:inline-block;font-size:11px;color:var(--muted);border:1px solid var(--hair);border-radius:20px;padding:2px 10px;}}
</style>
<div class="wrap">
  <div class="eyebrow">Experimento 2 · Sobreimpulso de fuerza en contacto</div>
  <h1>Cerrar rápido dispara un sobreimpulso de fuerza que llega a triplicar el setpoint</h1>
  <p class="dek">Inspire RH56DFTP, DOF&nbsp;3, yema contra bloque rígido. Sensor calibrado (<span class="mono">forceClb</span>) ⇒ <span class="mono">FORCE_ACT</span> ≈ fuerza externa. Modo A (velocidad constante), piloto de 5 trials/celda; barra = mediana, bigote = IQR.</p>

  <div class="kpis">
    <div class="kpi"><div class="n">~3300<span class="u"> g</span></div><div class="l">sobreimpulso máx (v=1000, Fset=250) — el momento del impacto</div></div>
    <div class="kpi"><div class="n">≤36<span class="u"> g</span></div><div class="l">sobreimpulso con Fset=100 a TODA velocidad — setpoint seguro</div></div>
    <div class="kpi"><div class="n">~{red_factor}&times;<span class="u"> menor</span></div><div class="l">sobreimpulso del modo B híbrido vs modo A rápido (ΔF ≤ {b_max:.0f} g, 0 aborts)</div></div>
  </div>

  <hr class="rule">
  <figure class="panel">
    {legend}
    {bars_svg()}
    <figcaption class="cap"><b>Figura 2.</b> Sobreimpulso <span class="mono">ΔF = F_max − Fset</span> por celda (v, Fset). Crece de forma dramática con la velocidad de cierre y satura ~v=750 por el impacto de la yema (efecto de momento, casi independiente de Fset). Con <span class="mono">Fset=100</span> el firmware frena antes de golpear y el sobreimpulso queda plano y bajo. ▲ marca celdas cuyo pico superó el techo de seguridad de 2200 g.</figcaption>
  </figure>

  <hr class="rule">
  <figure class="panel">
    {compare_svg()}
    <figcaption class="cap"><b>Figura 3 · La mitigación.</b> Con el modo B (híbrido: aproximación rápida hasta el borde del contacto, luego cierre lento) el sobreimpulso <span class="mono">ΔF</span> se <b>colapsa</b> al nivel del modo A lento (v=25) para todo Fset, mientras el modo A rápido (v=1000) dispara el impacto. El híbrido alcanza el setpoint con sobreimpulso mínimo y sin aborts.</figcaption>
  </figure>

  <hr class="rule">
  <div class="panel" style="padding-bottom:6px">
    <div style="font-weight:600;font-size:13.5px;margin:2px 2px 12px">ΔF mediana (g) por celda — modo A <span class="tag">N=5 · ▲ = nº de aborts</span></div>
    <div style="overflow-x:auto">
    <table>
      <thead><tr><th>v \\ Fset</th>{''.join(f'<th>{F}</th>' for F in fsets)}</tr></thead>
      <tbody>{trows}</tbody>
    </table>
    </div>
  </div>

  <p class="foot">En modo A el firmware NO sostiene el setpoint tras el impacto: sobrepasa y se relaja a un contacto pasivo por debajo de Fset; a alta velocidad el pico es puro momento de la yema. El <b>modo B (híbrido)</b> lo resuelve (0 aborts). {total_ab} impactos del modo A superaron el techo de 2200 g. Datos: <code>exp2_out/</code>, <code>exp2_out_slow/</code>, <code>exp2_out_hybrid/</code>. Análisis: <code>exp2_analyze.py</code> (Python puro).</p>
</div>'''

open(DST,'w').write(HTML)
print("escrito:",DST,f"({len(HTML)} bytes)  total_ab={total_ab}  y1={y1:.0f}")
