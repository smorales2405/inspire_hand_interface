#!/usr/bin/env python3
"""Arma el documento-resumen de la CARACTERIZACION TACTIL (HTML autocontenido).

Lee los CSV de Fase 0 y Fase A1 y genera graficos SVG + tablas, con el mismo
sistema de diseno que Caracterizacion/RESUMEN_caracterizacion.html. Reproducible:

    python Caracterizacion/tactil/make_summary_tactil.py
"""
import bisect
import csv
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
F0 = os.path.join(HERE, 'fase0', 'data')
A1 = os.path.join(HERE, 'fase_a1', 'data')
DST = os.path.join(HERE, 'RESUMEN_tactil.html')

INK = '#12181f'; MUTED = '#5a6472'; HAIR = '#dbe2ec'
ACC = '#285F97'; AMBER = '#B4740F'; SOFT = '#eef2f7'

# Tasas de muestreo: medidas (consola), documentadas en fase0/fase_a1 results.
HZ_FRAME = 2.9
HZ_ZONE = 32.4


# ── util ────────────────────────────────────────────────────────────────────
def lin(v, vmin, vmax, p0, p1):
    if vmax == vmin:
        return (p0 + p1) / 2.0
    return p0 + (v - vmin) / (vmax - vmin) * (p1 - p0)


def load_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def thin(seq, n):
    if len(seq) <= n:
        return seq
    step = len(seq) / n
    return [seq[int(i * step)] for i in range(n)]


# ── datos ───────────────────────────────────────────────────────────────────
diag = load_rows(os.path.join(F0, 'taxel_diagnosis.csv'))
diag_counts = {}
for r in diag:
    diag_counts[r['status']] = diag_counts.get(r['status'], 0) + 1
N_TAX = len(diag)

noise = load_rows(os.path.join(A1, 'a1_noise_taxels.csv'))
good_sigma = sorted(float(r['sigma']) for r in noise if r['excluded'] == '0')
n_good = len(good_sigma)
abs_floor = min(float(r['thr']) for r in noise if r['excluded'] == '0')

drift_ts = load_rows(os.path.join(A1, 'a1_drift_timeseries.csv'))
creep_ts = load_rows(os.path.join(A1, 'a1_creep_timeseries_z16.csv'))


# ── SVG 1: tasas de muestreo (barras) ───────────────────────────────────────
def chart_rates():
    W, H = 720, 150
    bars = [("Frame completo · 17 zonas (1062 tax)", HZ_FRAME, AMBER),
            ("Zona única · 96 tax (Índice·Distal)", HZ_ZONE, ACC)]
    maxv, L, R, y0, bh, gap = 36.0, 258, 74, 26, 34, 26
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Tasas de muestreo">']
    for i, (lab, v, col) in enumerate(bars):
        y = y0 + i * (bh + gap)
        bw = lin(v, 0, maxv, 0, W - L - R)
        s.append(f'<text x="{L-10}" y="{y+bh/2+4:.0f}" text-anchor="end" '
                 f'font-size="12.5" fill="{MUTED}">{lab}</text>')
        s.append(f'<rect x="{L}" y="{y}" width="{bw:.1f}" height="{bh}" '
                 f'rx="4" fill="{col}"/>')
        s.append(f'<text x="{L+bw+9:.0f}" y="{y+bh/2+5:.0f}" font-size="15" '
                 f'font-weight="600" fill="{INK}">{v} Hz</text>')
    s.append(f'<text x="{L}" y="{H-10}" font-size="11" fill="{MUTED}">'
             f'Nyquist 1.45 Hz (frame) vs 16 Hz (zona) — el frame gatea lo '
             f'cuasi-estático; la zona única habilita respuesta temporal.</text>')
    s.append('</svg>')
    return ''.join(s)


# ── SVG 2: distribución de ruido σ (barras por bucket) ──────────────────────
def chart_noise():
    buckets = [("σ = 0", lambda s: s == 0),
               ("0 < σ ≤ 1", lambda s: 0 < s <= 1),
               ("1 < σ ≤ 5", lambda s: 1 < s <= 5),
               ("5 < σ ≤ 10", lambda s: 5 < s <= 10),
               ("σ > 10", lambda s: s > 10)]
    counts = [sum(1 for s in good_sigma if f(s)) for _, f in buckets]
    pcts = [100.0 * c / n_good for c in counts]
    W, H = 720, 260
    L, R, T, B = 44, 20, 22, 46
    bw = (W - L - R) / len(buckets)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Distribución de σ">']
    # eje y (0..100%) gridlines
    for gy in (0, 25, 50, 75, 100):
        y = lin(gy, 0, 100, H - B, T)
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" '
                 f'stroke="{HAIR}"/>')
        s.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" '
                 f'font-size="11" fill="{MUTED}">{gy}%</text>')
    for i, ((lab, _), c, p) in enumerate(zip(buckets, counts, pcts)):
        x = L + i * bw + bw * 0.16
        w = bw * 0.68
        h = lin(p, 0, 100, 0, (H - B) - T)
        y = (H - B) - h
        col = ACC if i == 0 else AMBER
        s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                 f'height="{h:.1f}" rx="3" fill="{col}"/>')
        val = f'{p:.0f}%' if p >= 1 else f'{c}'
        s.append(f'<text x="{x+w/2:.1f}" y="{y-6:.1f}" text-anchor="middle" '
                 f'font-size="12.5" font-weight="600" fill="{INK}">{val}</text>')
        s.append(f'<text x="{x+w/2:.1f}" y="{H-B+18:.1f}" text-anchor="middle" '
                 f'font-size="11.5" fill="{MUTED}">{lab}</text>')
    s.append(f'<text x="{L}" y="{H-8}" font-size="11" fill="{MUTED}">'
             f'{n_good} taxeles buenos · σ en counts (0–4095) · máx '
             f'{good_sigma[-1]:.1f} · umbral de contacto abs_floor = '
             f'{abs_floor:.0f} counts</text>')
    s.append('</svg>')
    return ''.join(s)


# ── SVG 3: deriva del baseline + temperatura vs tiempo (doble eje) ──────────
def chart_drift():
    pts = []
    for r in drift_ts:
        try:
            pts.append((float(r['t_s']) / 60.0, float(r['gmean']),
                        float(r['t_index'])))
        except (ValueError, KeyError):
            pass
    W, H = 720, 260
    L, R, T, B = 52, 54, 22, 40
    tmax = max(p[0] for p in pts)
    gmin, gmax = 0.0, 2.0
    Tmin, Tmax = 26.0, 40.0
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Deriva del baseline y temperatura">']
    # grid + eje izq (counts)
    for gy in (0, 0.5, 1.0, 1.5, 2.0):
        y = lin(gy, gmin, gmax, H - B, T)
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" '
                 f'stroke="{HAIR}"/>')
        s.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" '
                 f'font-size="10.5" fill="{ACC}">{gy:.1f}</text>')
    # eje der (°C)
    for tc in (28, 32, 36, 40):
        y = lin(tc, Tmin, Tmax, H - B, T)
        s.append(f'<text x="{W-R+8}" y="{y+4:.1f}" font-size="10.5" '
                 f'fill="{AMBER}">{tc}°</text>')
    for tx in (0, 5, 10, 15, 20, 25):
        x = lin(tx, 0, tmax, L, W - R)
        s.append(f'<text x="{x:.1f}" y="{H-B+16:.1f}" text-anchor="middle" '
                 f'font-size="10.5" fill="{MUTED}">{tx}</text>')
    # temp (ámbar)
    tp = ' '.join(f'{lin(t,0,tmax,L,W-R):.1f},'
                  f'{lin(T3,Tmin,Tmax,H-B,T):.1f}' for t, _, T3 in pts)
    s.append(f'<polyline points="{tp}" fill="none" stroke="{AMBER}" '
             f'stroke-width="2"/>')
    # baseline gmean (azul)
    gp = ' '.join(f'{lin(t,0,tmax,L,W-R):.1f},'
                  f'{lin(g,gmin,gmax,H-B,T):.1f}' for t, g, _ in pts)
    s.append(f'<polyline points="{gp}" fill="none" stroke="{ACC}" '
             f'stroke-width="2.2"/>')
    # leyenda
    s.append(f'<rect x="{L+6}" y="{T+2}" width="11" height="11" fill="{ACC}"/>'
             f'<text x="{L+22}" y="{T+12}" font-size="11.5" fill="{INK}">'
             f'baseline (counts)</text>')
    s.append(f'<rect x="{L+150}" y="{T+2}" width="11" height="11" fill="{AMBER}"/>'
             f'<text x="{L+166}" y="{T+12}" font-size="11.5" fill="{INK}">'
             f'temp índice (°C)</text>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" text-anchor="middle" '
             f'font-size="11" fill="{MUTED}">tiempo (min) — baseline plano '
             f'(Δ ≈ +0.5 counts) pese a ΔT ≈ +8 °C</text>')
    s.append('</svg>')
    return ''.join(s)


# ── SVG 4: creep + recuperación (serie temporal) ────────────────────────────
def chart_creep():
    hold = [(float(r['t_s']), float(r['response'])) for r in creep_ts
            if r['phase'] == 'hold']
    rec = [(float(r['t_s']), float(r['response'])) for r in creep_ts
           if r['phase'] == 'recover']
    hold_dur = hold[-1][0] if hold else 240.0
    # x combinado: hold en [0,hold_dur], recuperación desplazada tras el hold
    H_pts = [(t, r) for t, r in thin(hold, 120)]
    # recuperación: fino cerca del retiro (<8s) + grueso después
    rec_fine = [(t, r) for t, r in rec if t <= 8.0]
    rec_fine = thin(rec_fine, 40)
    rec_coarse = thin([(t, r) for t, r in rec if t > 8.0], 40)
    R_pts = [(hold_dur + t, r) for t, r in rec_fine + rec_coarse]
    allpts = H_pts + R_pts
    W, H = 720, 270
    L, R, T, B = 52, 18, 26, 38
    xmax = hold_dur + (rec[-1][0] if rec else 240.0)
    ymax = 1600.0
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Creep y recuperación">']
    for gy in (0, 400, 800, 1200, 1600):
        y = lin(gy, 0, ymax, H - B, T)
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" '
                 f'stroke="{HAIR}"/>')
        s.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" '
                 f'font-size="10.5" fill="{MUTED}">{gy}</text>')
    for tx in (0, 60, 120, 180, 240, 300, 360, 420, 480):
        x = lin(tx, 0, xmax, L, W - R)
        s.append(f'<text x="{x:.1f}" y="{H-B+16:.1f}" text-anchor="middle" '
                 f'font-size="10.5" fill="{MUTED}">{tx}</text>')
    # linea de retiro
    xr = lin(hold_dur, 0, xmax, L, W - R)
    s.append(f'<line x1="{xr:.1f}" y1="{T}" x2="{xr:.1f}" y2="{H-B}" '
             f'stroke="{AMBER}" stroke-width="1.3" stroke-dasharray="4 3"/>')
    s.append(f'<text x="{xr-6:.1f}" y="{T+12}" text-anchor="end" '
             f'font-size="11" fill="{AMBER}">retiro del peso</text>')
    # curva
    pp = ' '.join(f'{lin(t,0,xmax,L,W-R):.1f},{lin(r,0,ymax,H-B,T):.1f}'
                  for t, r in allpts)
    s.append(f'<polyline points="{pp}" fill="none" stroke="{ACC}" '
             f'stroke-width="2.2"/>')
    # anotaciones
    xh = lin(hold_dur / 2, 0, xmax, L, W - R)
    yh = lin(1452, 0, ymax, H - B, T)
    s.append(f'<text x="{xh:.0f}" y="{yh-12:.0f}" text-anchor="middle" '
             f'font-size="11.5" font-weight="600" fill="{INK}">HOLD · '
             f'creep +1%</text>')
    xrec = lin(hold_dur + 40, 0, xmax, L, W - R)
    s.append(f'<text x="{xrec:.0f}" y="{lin(120,0,ymax,H-B,T):.0f}" '
             f'font-size="11.5" font-weight="600" fill="{INK}">recuperación '
             f'&lt;0.4 s · residual 0</text>')
    s.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" text-anchor="middle" '
             f'font-size="11" fill="{MUTED}">tiempo (s) — palma (z16), '
             f'256 g · respuesta = suma del crudo sobre baseline</text>')
    s.append('</svg>')
    return ''.join(s)


# ── Tablas ──────────────────────────────────────────────────────────────────
def table_diag():
    order = [('ok', 'OK', 'responden y baseline limpio'),
             ('noisy', 'Ruidosos', 'los ~7% con algo de fluctuación en reposo (σ ≤ 15 counts)'),
             ('stuck_low', 'Sin respuesta', 'mayormente <b>cobertura</b> del barrido manual en zonas grandes, no muertos'),
             ('unknown', 'Sin evaluar', 'z6 Medio·Punta, <b>muerta por hardware</b> (excluida)'),
             ('dead', 'Anómalos', 'artefactos de deriva del baseline (2 taxeles)')]
    t = ('<div class="tbl-wrap"><table><caption><b>Tabla 1.</b> Diagnóstico de '
         'taxeles (Fase 0, screening): el barrido manual certifica respuesta '
         'a nivel de zona; certificar taxeles muertos individuales en zonas '
         'grandes queda para A3/B con indentador.</caption>'
         '<thead><tr><th>Estado</th><th>Taxeles</th><th>% del total</th>'
         '<th>Interpretación</th></tr></thead><tbody>')
    for key, lab, note in order:
        c = diag_counts.get(key, 0)
        t += (f'<tr><td class="b">{lab}</td><td class="mono">{c}</td>'
              f'<td class="mono">{100.0*c/N_TAX:.1f}%</td>'
              f'<td style="text-align:left">{note}</td></tr>')
    t += ('</tbody></table></div>')
    return t


def table_a1():
    rows = [
        ('A1.1 — Ruido / umbral',
         f'93% de taxeles con σ = 0; máx {good_sigma[-1]:.1f} counts',
         f'umbral de contacto <span class="mono">thr = max(5σ, {abs_floor:.0f})</span> (~1% FS)'),
        ('A1.2 — Deriva sin carga',
         '≈ +0.5 counts en 25 min (desde frío, ΔT +8 °C)',
         'el cero <b>sin tocar</b> es estable'),
        ('A1.3 — Creep / recuperación',
         'creep ~1% en 4 min · recuperación &lt; 0.4 s, residual 0',
         'el cero <b>vuelve</b> tras contacto moderado'),
    ]
    t = ('<div class="tbl-wrap"><table><caption><b>Tabla 2.</b> Métricas de la '
         'Fase A1 (nivel sensor) y su implicación para la estrategia de cero.'
         '</caption><thead><tr><th>Sub-experimento</th><th>Resultado medido</th>'
         '<th>Implicación</th></tr></thead><tbody>')
    for a, b, c in rows:
        t += (f'<tr><td class="b" style="text-align:left">{a}</td>'
              f'<td class="mono" style="text-align:left">{b}</td>'
              f'<td style="text-align:left">{c}</td></tr>')
    t += '</tbody></table></div>'
    return t


def themeify(svg):
    """Enruta los colores fijos del SVG por variables CSS -> adaptan a claro/oscuro.

    Solo se aplica a las cadenas SVG (no a la CSS), así los tokens del tema
    controlan el gráfico entero.
    """
    for hexv, var in ((INK, 'var(--ink)'), (MUTED, 'var(--muted)'),
                      (HAIR, 'var(--hair)'), (ACC, 'var(--acc)'),
                      (AMBER, 'var(--amber)')):
        svg = svg.replace(hexv, var)
    return svg


c_rates, c_noise, c_drift, c_creep = (
    themeify(chart_rates()), themeify(chart_noise()),
    themeify(chart_drift()), themeify(chart_creep()))
t_diag, t_a1 = table_diag(), table_a1()
n_dead_zone = 9   # z6 Medio·Punta

HTML = f'''<title>Caracterización del sensor táctil RH56DFTP — Resultados iniciales</title>
<style>
  :root{{--ink:{INK};--muted:{MUTED};--hair:{HAIR};--acc:{ACC};--amber:{AMBER};
    --bg:#f6f8fb;--panel:#ffffff;--soft:{SOFT};}}
  *{{box-sizing:border-box;}}
  .wrap{{max-width:880px;margin:0 auto;padding:52px 26px 72px;color:var(--ink);background:var(--bg);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.62;font-size:16px;}}
  .mono{{font-family:ui-monospace,"SF Mono","JetBrains Mono",Menlo,monospace;font-variant-numeric:tabular-nums;}}
  .b{{font-weight:600;}} .ey{{letter-spacing:.14em;text-transform:uppercase;}}
  .eyebrow{{font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--acc);font-weight:600;}}
  h1{{font-size:33px;line-height:1.12;margin:.5rem 0 .4rem;letter-spacing:-.015em;text-wrap:balance;max-width:22ch;}}
  .byline{{color:var(--muted);font-size:14px;margin:0 0 22px;}}
  .byline .mono{{color:var(--ink);}}
  .abstract{{font-size:17px;max-width:64ch;margin:0;color:#333b45;}}
  .abstract b{{color:var(--ink);}}
  h2{{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--acc);font-weight:700;
    margin:0 0 4px;display:flex;align-items:baseline;gap:10px;}}
  h2 .tag{{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:var(--muted);
    letter-spacing:0;text-transform:none;border:1px solid var(--hair);border-radius:20px;padding:1px 8px;}}
  h3{{font-size:20px;margin:.1rem 0 .5rem;letter-spacing:-.01em;text-wrap:balance;}}
  section{{margin:30px 0;}}
  p{{margin:.5rem 0;}}
  .rule{{height:1px;background:var(--hair);border:0;margin:30px 0;}}
  .lead{{font-size:16.5px;}}
  ul{{margin:.5rem 0;padding-left:1.1rem;}} li{{margin:.28rem 0;}}
  strong,b{{font-weight:600;}}
  .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0 4px;}}
  @media(max-width:640px){{.kpis{{grid-template-columns:repeat(2,1fr);}}}}
  .kpi{{background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:15px 15px 13px;}}
  .kpi .n{{font-size:22px;font-weight:600;letter-spacing:-.015em;line-height:1.1;}}
  .kpi .n .u{{font-size:13px;color:var(--muted);font-weight:500;}}
  .kpi .l{{font-size:11.5px;color:var(--muted);margin-top:5px;line-height:1.35;}}
  .method{{background:var(--soft);border:1px solid var(--hair);border-radius:11px;padding:16px 18px;
    font-size:14px;color:#3a434e;}}
  .method .h{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:6px;}}
  .method code,.foot code,p code,li code{{font-family:ui-monospace,Menlo,monospace;font-size:.86em;
    background:var(--soft);padding:1px 5px;border-radius:4px;color:var(--ink);}}
  figure{{margin:20px 0 6px;background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:16px 16px 8px;}}
  svg{{width:100%;height:auto;display:block;}}
  figcaption{{font-size:12.5px;color:var(--muted);margin-top:10px;}}
  figcaption b{{color:var(--ink);}}
  .foot{{font-size:12.5px;color:var(--muted);border-top:1px solid var(--hair);margin-top:34px;padding-top:16px;}}
  a{{color:var(--acc);}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;margin:4px 0;}}
  caption{{caption-side:top;text-align:left;font-size:12.5px;color:var(--muted);margin-bottom:9px;line-height:1.5;}}
  caption b{{color:var(--ink);}}
  th,td{{text-align:right;padding:7px 9px;border-bottom:1px solid var(--hair);}}
  th:first-child,td:first-child{{text-align:left;}}
  thead th{{font-size:10.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:600;}}
  .tbl-wrap{{overflow-x:auto;margin:18px 0 6px;}}
  .future{{background:var(--soft);border:1px solid var(--hair);border-radius:11px;padding:6px 20px 10px;}}
  @media(prefers-color-scheme:dark){{:root:not([data-theme="light"]){{
    --ink:#e8edf3;--muted:#9aa6b4;--hair:#2a323d;--bg:#0f1319;--panel:#161b22;--soft:#1a2027;--acc:#5b9bd8;--amber:#d29a3e;}}
    :root:not([data-theme="light"]) .abstract{{color:#c4ccd6;}}
    :root:not([data-theme="light"]) .method{{color:#b6bfca;}}}}
  :root[data-theme="dark"]{{--ink:#e8edf3;--muted:#9aa6b4;--hair:#2a323d;--bg:#0f1319;--panel:#161b22;--soft:#1a2027;--acc:#5b9bd8;--amber:#d29a3e;}}
  :root[data-theme="dark"] .abstract{{color:#c4ccd6;}} :root[data-theme="dark"] .method{{color:#b6bfca;}}
</style>
<div class="wrap">

  <header>
    <div class="eyebrow">Trabajo de tesis · Resultados iniciales</div>
    <h1>Caracterización del sensor táctil de la mano Inspire RH56DFTP</h1>
    <p class="byline"><span class="mono">Sergio Morales</span> · Universidad de Ingeniería y Tecnología (UTEC) · Julio 2026 · <span class="ey" style="font-size:11px">documento de trabajo</span></p>
    <p class="abstract">Se caracterizó el <b>sensor táctil resistivo</b> de la mano Inspire RH56DFTP —<b>17 zonas, {N_TAX} taxeles</b> (crudo 0–4095)— a nivel de señal, con experimentos de <b>hardware en el lazo</b> por fases. Resultados: la lectura sostiene <b>{HZ_FRAME} Hz</b> de frame completo y <b>{HZ_ZONE} Hz</b> por zona (lo que gatea qué mediciones son factibles); el <b>piso de ruido es casi cero</b> (93% de los taxeles no fluctúan); la <b>deriva del cero sin carga es despreciable</b> y bajo carga hay <b>creep ~1% con recuperación completa</b> — de donde se concluye que un <b>cero fijo de sesión es adecuado</b>. Se detectó además <b>una zona muerta</b> (yema del dedo medio). Restan la calibración crudo→fuerza y el benchmark funcional.</p>
  </header>

  <div class="kpis">
    <div class="kpi"><div class="n">{N_TAX}<span class="u"> taxeles</span></div><div class="l">17 zonas · 1 registro/taxel · crudo 0–4095</div></div>
    <div class="kpi"><div class="n">{HZ_FRAME} / {HZ_ZONE}<span class="u"> Hz</span></div><div class="l">muestreo frame completo / zona única</div></div>
    <div class="kpi"><div class="n">93<span class="u"> %</span></div><div class="l">taxeles con ruido σ = 0 (piso ~cero)</div></div>
    <div class="kpi"><div class="n">cero fijo<span class="u"> ✓</span></div><div class="l">deriva ~0 · creep ~1% · recuperación completa</div></div>
  </div>

  <hr class="rule">

  <section>
    <h2>Contexto y objetivo</h2>
    <p class="lead">El táctil de la RH56DFTP es <b>resistivo</b>, con 17 zonas repartidas en dedos y palma ({N_TAX} taxeles, crudo 0–4095 sin unidades). Antes de usarlo como canal de fuerza en un estado multimodal hay que <b>validarlo a nivel de señal</b>: conocer su ruido, su deriva (los resistivos derivan al cargarse/calentarse), su repetibilidad y su calibración. Este documento resume la <b>Fase 0</b> (mapa vivo / compuerta) y la <b>Fase A1</b> (ruido, deriva y creep) completadas sobre la mano física, y deja planteado lo que resta (A2, A3, Fase B).</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Método</h2>
    <h3>Adquisición por fases, con dependencia A→B</h3>
    <p><b>Adquisición.</b> Modbus RTU a 115 200 baud, un solo proceso/hilo/cliente con <b>lazo intercalado</b>, y marcas de tiempo con <code>time.perf_counter()</code>. Cada taxel es <b>1 registro de 16 bits</b> (crudo 0–4095), decodificado con signo. El frame completo son <b>17 transacciones secuenciales</b>; la lectura de <b>zona única</b> es mucho más rápida. Se registra la temperatura de los actuadores (<code>TEMP</code>, reg 1618) como proxy térmico. Todo corre <b>fuera de la interfaz gráfica</b> y es reproducible desde los CSV.</p>
    <p><b>Fase 0 · mapa vivo.</b> Baseline en reposo, barrido manual guiado zona por zona (con re-baseline por zona para des-confundir el cross-talk), diagnóstico de taxeles muertos/pegados/ruidosos, y medición de tasas.</p>
    <p><b>A1.1 · ruido.</b> ~3 min en reposo; media y σ por taxel; fija el umbral de contacto <code>thr = max(k·σ, abs_floor)</code>.</p>
    <p><b>A1.2 · deriva.</b> 25 min desde frío (tras encender); baseline por taxel/zona vs tiempo y temperatura.</p>
    <p><b>A1.3 · creep.</b> Peso constante conocido sobre una zona; registro continuo carga→hold→retiro→recuperación (zona única); respuesta = suma del crudo sobre baseline en el parche cargado.</p>
    <div class="method">
      <div class="h">Definición de métricas</div>
      <b>σ (ruido)</b>: desviación por taxel en reposo. &nbsp;·&nbsp; <b>abs_floor</b>: piso empírico del umbral = ⌈p99.9 de la excursión⌉. &nbsp;·&nbsp; <b>Deriva</b>: |μ_fin − μ_inicio| del baseline. &nbsp;·&nbsp; <b>Creep</b>: (R1 − R0)/R0 de la respuesta bajo carga constante. &nbsp;·&nbsp; <b>Residual</b>: respuesta remanente tras retirar la carga.
    </div>
  </section>

  <hr class="rule">

  <section>
    <h2>Fase 0 <span class="tag">mapa vivo · compuerta</span></h2>
    <h3>Inventario del sensor y qué muestreo es factible</h3>
    <p>El frame completo se muestrea a <b>{HZ_FRAME} Hz</b> (17 transacciones) y una zona única a <b>{HZ_ZONE} Hz</b>. Esta diferencia <b>gatea</b> la caracterización: todo lo cuasi-estático (baseline, deriva, calibración) usa el frame; la respuesta temporal debe medirse por <b>zona única</b>, y aun así el flanco rápido de carga queda al límite del harness. Se detectó <b>1 zona muerta por hardware</b> (z6 · yema del dedo medio, {n_dead_zone} taxeles), excluida de todo análisis. El cross-talk entre zonas es <b>bajo (≤ 5%)</b>, dominado por adyacencia mismo-dedo.</p>
    <figure>
      {c_rates}
      <figcaption><b>Figura 1.</b> Tasas de muestreo medidas. La lectura por zona única (~11×) es la que habilita medir tiempos de respuesta.</figcaption>
    </figure>
    {t_diag}
  </section>

  <hr class="rule">

  <section>
    <h2>Fase A1.1 <span class="tag">ruido · umbral</span></h2>
    <h3>El piso de ruido es casi cero</h3>
    <p>En 3 min de reposo, <b>el 93% de los {n_good} taxeles buenos no fluctúan ni un count</b> (σ = 0); el más ruidoso llega a {good_sigma[-1]:.1f} counts (0.35% del fondo de escala). Esto da un canal muy sensible: el umbral de contacto <code>thr = max(5·σ, {abs_floor:.0f})</code> queda gobernado por un piso empírico de <b>{abs_floor:.0f} counts (~1% FS)</b>.</p>
    <figure>
      {c_noise}
      <figcaption><b>Figura 2.</b> Distribución del ruido σ por taxel (solo taxeles buenos). La abrumadora mayoría está en σ = 0; el ruido se concentra en un ~7% con algo de offset en reposo.</figcaption>
    </figure>
  </section>

  <hr class="rule">

  <section>
    <h2>Fase A1.2 <span class="tag">deriva sin carga</span></h2>
    <h3>Sin carga, el cero no se mueve — aunque el sensor se caliente</h3>
    <p>Registrando 25 min <b>desde frío</b> (el índice sube de 28 a 36 °C, ΔT +8), el baseline del táctil se corre <b>~0.5 counts en total</b>: el 95% de los taxeles no derivan nada. La leve subida correlaciona con la temperatura, pero su magnitud (medio count) es <b>irrelevante</b> frente al umbral de {abs_floor:.0f} counts. La deriva resistiva <b>no es térmica/de asentamiento sin carga</b>.</p>
    <figure>
      {c_drift}
      <figcaption><b>Figura 3.</b> Baseline medio de los taxeles buenos (azul, eje izq.) y temperatura del actuador índice (ámbar, eje der.) durante 25 min. El baseline queda plano mientras la temperatura sube ~8 °C.</figcaption>
    </figure>
  </section>

  <hr class="rule">

  <section>
    <h2>Fase A1.3 <span class="tag">creep · recuperación</span></h2>
    <h3>Bajo carga: creep despreciable y recuperación completa</h3>
    <p>Con un peso constante de <b>256 g</b> sobre la palma, la respuesta se mantiene <b>plana (creep ~1% en 4 min)</b> y, al retirar el peso, <b>vuelve al cero en menos de 0.4 s con residual 0</b>. (Una primera corrida mostró un "+29%" que resultó ser <b>asentamiento mecánico</b> de la carga mal apoyada, no creep del sensor — un recordatorio de montar el contacto estable y plano.) Esto contrasta con un residual observado en Fase 0 tras contactos <b>muy duros</b> en una yema: el residual es <b>dependiente de la carga y la zona</b>, y no aparece a cargas moderadas.</p>
    <figure>
      {c_creep}
      <figcaption><b>Figura 4.</b> Respuesta de la palma a carga constante: hold plano (creep ~1%) y, tras el retiro (línea ámbar), recuperación inmediata a cero sin residual.</figcaption>
    </figure>
    {t_a1}
  </section>

  <hr class="rule">

  <section>
    <h2>Conclusión de la Fase A1 <span class="tag">decisión de re-cero</span></h2>
    <p class="lead">Con el baseline estable sin carga (A1.2) y el creep despreciable con recuperación completa (A1.3), se concluye que <b>un cero fijo de sesión (una tara al inicio) es adecuado</b> para el canal táctil; no hace falta un baseline adaptativo por-toque. Como red de seguridad barata se contempla un <b>re-cero oportunista periódico</b> (refrescar el baseline cuando la mano esté ociosa), por el residual que aparece tras contactos duros. Para la calibración (A3), el crudo mapea bien a fuerza una vez asentado el contacto, leyendo a un <b>tiempo de permanencia consistente</b>.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Trabajo futuro <span class="tag">pendiente</span></h2>
    <div class="future">
    <ul>
      <li><b>A2 — Repetibilidad e histéresis.</b> Carga cíclica con pesos escalonados (subida y bajada) usando un <b>jig de posicionamiento repetible</b>: error de repetibilidad por nivel, lazo de histéresis carga-vs-descarga, y tiempos de respuesta asimétricos (carga/descarga) por zona única. Decide si una sola curva de calibración sirve o hay que separar rama de carga.</li>
      <li><b>A3 — Calibración crudo→fuerza/presión.</b> Rig de ground-truth: <b>indentador plano de área conocida</b> + pesos calibrados. Ajuste del modelo (los resistivos suelen ser no lineales): sensibilidad, rango, resolución y R², en <b>al menos una zona de cada tipo de grid</b> (punta 3×3, distal 12×8, palmar 10×8, palma 14×8). Es el entregable que vuelve <b>cuantitativo</b> el canal táctil.</li>
      <li><b>Fase B — Benchmark funcional.</b> Resolución espacial y cross-talk fino (point-spread, discriminación de dos puntos), umbral mínimo de fuerza detectable por zona, y localización/discriminación de forma (punto vs borde vs área).</li>
      <li><b>Verificación pendiente.</b> Caracterizar el residual tras contactos <b>duros</b> en yemas (reconciliar con Fase 0) para afinar la política de re-cero, y confirmar el mapa de taxeles muertos con el indentador de A3.</li>
    </ul>
    </div>
  </section>

  <p class="foot">Documento de trabajo — resultados iniciales de tesis (caracterización táctil). Datos, código y este resumen reproducibles en el repositorio: <span class="mono">github.com/smorales2405/inspire_hand_interface</span> (<code>Caracterizacion/tactil/</code>). Hardware: Inspire Hand RH56DFTP · táctil resistivo, 17 zonas.</p>

</div>'''

with open(DST, 'w') as f:
    f.write(HTML)
print(f"escrito: {DST} ({len(HTML)} bytes) · taxeles={N_TAX} buenos={n_good} "
      f"diag={diag_counts} sigma_max={good_sigma[-1]:.1f} floor={abs_floor:.0f}")
