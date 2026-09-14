#!/usr/bin/env python3
"""Figura de la réplica por TCP: el onset no se dispersa, se bifurca.

Dos histogramas de los 50 toques de cada campaña, centrados cada uno en su propia
mediana —así la comparación es de FORMA y no depende del montaje, que cambió
entre ambas—. En la fila de serial se marcan las barras que la regla de 1.5·IQR
descartaba como «outliers de detección»: de ahí salía la σ de 10.0 publicada.

El punto de la figura: el dedo no aterriza en una posición con ruido, sino en
UNA DE DOS, separadas ~70 counts y cada una apretada (σ 5–10). La estructura se
repite en los dos transportes y en dos montajes distintos, así que no es un
artefacto de detección. Lo que cambia es el PESO de cada grupo (20 % arriba por
serial, 46 % por TCP), y por eso la regla del IQR recortaba el grupo alto en una
campaña y no en la otra. Una σ sobre la mezcla —10.0 o 40.2— no describe nada.

Salida: figures/replica_tcp_onset.html (SVG autocontenido).
"""
import csv, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
INK, MUTED, HAIR = '#12181f', '#5a6472', '#dbe2ec'
ACC, AMBER = '#285F97', '#B4740F'      # validados: ΔE 22.3 protan · 27.2 normal
SURF = '#ffffff'
BIN = 10
LO, HI = -30, 160


def load(path):
    return [int(r['onset_pos']) for r in csv.DictReader(open(path))
            if r['onset_pos'] and r.get('aborted', '0') == '0']


def iqr_fences(vals):
    q1, _, q3 = statistics.quantiles(sorted(vals), n=4)
    d = q3 - q1
    return q1 - 1.5 * d, q3 + 1.5 * d


def clusters(vals, min_gap=12):
    """Parte la muestra por el hueco mayor si supera `min_gap`. Devuelve grupos."""
    v = sorted(vals)
    gaps = [(b - a, i) for i, (a, b) in enumerate(zip(v, v[1:])) if b - a >= min_gap]
    if not gaps:
        return [v]
    out, prev = [], 0
    for _, i in sorted(gaps, key=lambda g: g[1]):
        out.append(v[prev:i + 1]); prev = i + 1
    out.append(v[prev:])
    return [g for g in out if g]


def hist(dx):
    h = {}
    for v in dx:
        h[int((v - LO) // BIN)] = h.get(int((v - LO) // BIN), 0) + 1
    return h


def panel(y0, vals, color, title, note, mark_outliers, x_of, hmax, hpx=110):
    med = statistics.median(vals)
    lo, hi = iqr_fences(vals)
    dx = [v - med for v in vals]
    cut = {int((v - med - LO) // BIN) for v in vals if mark_outliers and not (lo <= v <= hi)}
    s = [f'<text x="8" y="{y0 + 14}" fill="{INK}" font-size="13" font-weight="600">{title}</text>',
         f'<text x="8" y="{y0 + 31}" fill="{MUTED}" font-size="11.5">{note}</text>']
    base = y0 + hpx
    for b, n in sorted(hist(dx).items()):
        x = x_of(LO + b * BIN) + 1
        w = x_of(LO + (b + 1) * BIN) - x_of(LO + b * BIN) - 2
        h = n / hmax * (hpx - 58)      # 58 px para título, nota y la etiqueta del grupo
        if b in cut:
            s.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'rx="3" fill="{SURF}" stroke="{color}" stroke-width="1.6" '
                     f'stroke-dasharray="3 2.2"/>')
        else:
            s.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'rx="3" fill="{color}" opacity="0.9"/>')
    s.append(f'<line x1="{x_of(LO):.1f}" y1="{base:.1f}" x2="{x_of(HI):.1f}" y2="{base:.1f}" '
             f'stroke="{HAIR}" stroke-width="1"/>')
    return '\n'.join(s), cut


def main():
    ser = load(os.path.join(HERE, 'exp2/data_dof4_onset/onset_trials.csv'))
    tcp = load(os.path.join(HERE, 'exp2/data_dof4_tcp_onset/onset_trials.csv'))
    n_cut = sum(1 for v in ser if not (iqr_fences(ser)[0] <= v <= iqr_fences(ser)[1]))
    W, H, L, R = 840, 372, 24, 22

    def x_of(d):
        return L + (d - LO) / (HI - LO) * (W - L - R)

    hmax = max(max(hist([v - statistics.median(ser) for v in ser]).values()),
               max(hist([v - statistics.median(tcp) for v in tcp]).values()))
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif" role="img" '
         f'aria-label="Distribución de la posición de contacto por serial y por Modbus TCP">']
    for t in range(-30, 161, 30):
        s.append(f'<line x1="{x_of(t):.1f}" y1="48" x2="{x_of(t):.1f}" y2="{H-46}" '
                 f'stroke="{HAIR}" stroke-width="1"/>')
        s.append(f'<text x="{x_of(t):.1f}" y="{H-28}" fill="{MUTED}" font-size="11.5" '
                 f'text-anchor="middle">{t:+d}</text>')
    s.append(f'<text x="{W/2:.0f}" y="{H-9}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle">posición de primer contacto − mediana de su campaña '
             f'(counts de POS)</text>')
    p1, cut = panel(44, ser, ACC, 'RS-485 · 65 Hz',
                    f'σ de la mezcla {statistics.pstdev(ser):.1f} counts · la σ publicada de '
                    f'10.0 es la del grupo izquierdo, tras recortar el derecho', True, x_of, hmax)
    p2, _ = panel(198, tcp, AMBER, 'Modbus TCP · 600 Hz',
                  f'σ de la mezcla {statistics.pstdev(tcp):.1f} counts · la misma regla de '
                  f'recorte aquí no descarta ninguno', False, x_of, hmax)
    s.append(p1); s.append(p2)

    # Etiqueta directa sobre cada grupo: el peso es el dato que cambia entre
    # campañas, y una leyenda de color no lo diría.
    for y0, vals, color in ((44, ser, ACC), (198, tcp, AMBER)):
        med = statistics.median(vals)
        h = hist([v - med for v in vals])
        for g in clusters(vals):
            if len(g) < 3:
                continue
            bins = {int((v - med - LO) // BIN) for v in g}
            top = max(h.get(b, 0) for b in bins)
            xmid = statistics.fmean([x_of(v - med) for v in g])
            ytop = y0 + 110 - top / hmax * (110 - 58)
            s.append(f'<text x="{xmid:.0f}" y="{ytop - 7:.0f}" fill="{color}" font-size="12" '
                     f'font-weight="600" text-anchor="middle">{len(g)} de {len(vals)}</text>')
            s.append(f'<text x="{xmid:.0f}" y="{y0 + 110 + 13:.0f}" fill="{MUTED}" '
                     f'font-size="11" text-anchor="middle">σ {statistics.pstdev(g):.1f}</text>')
    s.append(f'<text x="{W-R}" y="36" fill="{MUTED}" font-size="11.5" text-anchor="end">'
             f'trazo discontinuo = descartado como «outlier de detección»</text>')
    s.append('</svg>')
    svg = '\n'.join(s)

    out = os.path.join(HERE, 'figures/replica_tcp_onset.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(
        f'<!doctype html><meta charset="utf-8">'
        f'<title>Réplica por TCP — dispersión del contacto</title>'
        f'<body style="background:{SURF};color:{INK};font-family:system-ui;margin:24px;'
        f'max-width:900px">'
        f'<h1 style="font-size:17px">La dispersión del contacto no baja al muestrear 9× '
        f'más rápido</h1>{svg}</body>')
    print('escrito:', out)
    for tag, v in (('serial', ser), ('TCP', tcp)):
        q1, q2, q3 = statistics.quantiles(sorted(v), n=4)
        print(f'  {tag:7s} N={len(v)} q1={q1:.0f} mediana={q2:.0f} q3={q3:.0f} '
              f'IQR={q3-q1:.0f} σ={statistics.pstdev(v):.1f} rango={min(v)}–{max(v)}')


if __name__ == '__main__':
    main()
