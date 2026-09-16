#!/usr/bin/env python3
"""Figura de la réplica por TCP: qué producía los "dos grupos" del contacto.

Dos histogramas de la posición de primer contacto, 60 toques cada uno, sobre el
mismo dedo y el mismo montaje, a velocidad lenta y a máxima. A v=25 sale un solo
pico de σ=1.5 counts; a v=1000 salen dos grupos separados 82 counts. Y 82 es
justo lo que el dedo avanza entre dos refrescos del registro de posición de la
mano, que cambia cada ~30.7 ms sea cual sea la tasa de lectura.

O sea que los dos grupos no son dos posiciones de contacto: son dos escalones del
registro. Salida: figuras/replica_tcp_onset.html (SVG autocontenido).
"""
import csv, os, statistics

# La raíz de Caracterizacion/ es el nivel de ARRIBA: este script vive en una
# subcarpeta y todas las rutas de datos cuelgan de la raíz.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK, MUTED, HAIR = '#12181f', '#5a6472', '#dbe2ec'
ACC, AMBER = '#285F97', '#B4740F'      # validados: ΔE 22.3 protan · 27.2 normal
SURF = '#ffffff'
GEOM = 781            # onset geométrico del sondeo lento, montaje tcp2
BIN, LO, HI = 5, 15, 165


def onsets(v):
    d = os.path.join(RAIZ, f'exp2/data_dof4_tcp_bif_v{v}')
    return sorted(int(r['onset_pos']) - GEOM
                  for r in csv.DictReader(open(os.path.join(d, 'onset_trials.csv')))
                  if r['onset_pos'] and r['aborted'] == '0')


def register_step(v, lo=760, hi=960):
    """Counts que avanza POS_ACT entre dos refrescos del registro, cerca del contacto."""
    d = os.path.join(RAIZ, f'exp2/data_dof4_tcp_bif_v{v}')
    steps = []
    for k in range(1, 61):
        try:
            rows = [(float(r['t_s']), int(r['pos_act']))
                    for r in csv.DictReader(open(os.path.join(d, f'trace_v{v}_n{k:03d}.csv')))
                    if r['pos_act']]
        except OSError:
            continue
        ch = [(t, p) for i, (t, p) in enumerate(rows) if i == 0 or p != rows[i - 1][1]]
        steps += [b[1] - a[1] for a, b in zip(ch, ch[1:]) if lo <= a[1] <= hi and b[1] > a[1]]
    return statistics.median(steps) if steps else None


def clusters(v, min_gap=12):
    g = [(b - a, i) for i, (a, b) in enumerate(zip(v, v[1:])) if b - a >= min_gap]
    if not g:
        return [v]
    _, i = max(g)
    return [v[:i + 1], v[i + 1:]]


def hist(vals):
    h = {}
    for x in vals:
        b = int((x - LO) // BIN)
        h[b] = h.get(b, 0) + 1
    return h


def main():
    data = {v: onsets(v) for v in (25, 1000)}
    step = {v: register_step(v) for v in (25, 1000)}
    # Escala vertical PROPIA de cada panel: el pico de v=25 (60 toques en dos
    # barras) aplastaría el de v=1000 hasta hacerlo ilegible, y lo que compara
    # esta figura es la FORMA. El recuento de cada grupo va etiquetado encima,
    # así que no se pierde la magnitud.
    hmax = {v: max(hist(o).values()) for v, o in data.items()}
    W, H, L, R, HP = 840, 442, 26, 24, 118

    def X(d):
        return L + (d - LO) / (HI - LO) * (W - L - R)

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif" role="img" '
         f'aria-label="Posición de primer contacto en 60 toques a velocidad lenta y a '
         f'velocidad máxima, con el paso del registro de posición">']
    for t in range(20, 161, 20):
        s.append(f'<line x1="{X(t):.1f}" y1="44" x2="{X(t):.1f}" y2="344" '
                 f'stroke="{HAIR}" stroke-width="1"/>')
        s.append(f'<text x="{X(t):.1f}" y="{H-30}" fill="{MUTED}" font-size="11.5" '
                 f'text-anchor="middle">+{t}</text>')
    s.append(f'<text x="{W/2:.0f}" y="{H-10}" fill="{MUTED}" font-size="11.5" '
             f'text-anchor="middle">posición de primer contacto, counts pasado el contacto '
             f'geométrico del sondeo lento · escala vertical propia de cada '
             f'panel</text>')

    for y0, v, color, label in ((44, 25, ACC, 'v = 25 · cierre lento'),
                                (218, 1000, AMBER, 'v = 1000 · velocidad máxima')):
        o = data[v]
        base = y0 + HP
        s.append(f'<text x="8" y="{y0+14}" fill="{INK}" font-size="13" '
                 f'font-weight="600">{label}</text>')
        s.append(f'<text x="8" y="{y0+31}" fill="{MUTED}" font-size="11.5">'
                 f'60 toques · σ {statistics.pstdev(o):.1f} counts · el registro de posición '
                 f'avanza <tspan font-weight="600" fill="{color}">{step[v]:.0f} counts</tspan> '
                 f'entre refrescos</text>')
        for b, n in sorted(hist(o).items()):
            x = X(LO + b * BIN) + 0.8
            w = X(LO + (b + 1) * BIN) - X(LO + b * BIN) - 1.6
            h = n / hmax[v] * (HP - 56)
            s.append(f'<rect x="{x:.1f}" y="{base-h:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'rx="2.5" fill="{color}" opacity="0.9"/>')
        s.append(f'<line x1="{X(LO):.1f}" y1="{base:.1f}" x2="{X(HI):.1f}" y2="{base:.1f}" '
                 f'stroke="{HAIR}" stroke-width="1"/>')
        cl = clusters(o)
        for g in cl:
            xm = statistics.fmean(X(x) for x in g)
            top = max(hist(g).values()) / hmax[v] * (HP - 56)
            s.append(f'<text x="{xm:.0f}" y="{base-top-7:.0f}" fill="{color}" font-size="12" '
                     f'font-weight="600" text-anchor="middle">{len(g)} de {len(o)}</text>')
        if len(cl) == 2:
            # Se mide entre MEDIANAS, que es la magnitud comparable con el paso
            # del registro; el hueco entre bordes seria otra cosa.
            m0, m1 = statistics.median(cl[0]), statistics.median(cl[1])
            x1, x2 = X(m0), X(m1)
            ym = base + 16
            s.append(f'<path d="M {x1:.1f} {ym-6:.1f} L {x1:.1f} {ym:.1f} L {x2:.1f} {ym:.1f} '
                     f'L {x2:.1f} {ym-6:.1f}" fill="none" stroke="{color}" stroke-width="1.4"/>')
            s.append(f'<text x="{(x1+x2)/2:.0f}" y="{ym+15:.0f}" fill="{color}" font-size="11.5" '
                     f'text-anchor="middle" font-weight="600">{m1-m0:.0f} counts entre medianas '
                     f'= un refresco del registro</text>')
    s.append('</svg>')
    svg = '\n'.join(s)

    out = os.path.join(RAIZ, 'figuras/replica_tcp_onset.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(
        f'<!doctype html><meta charset="utf-8">'
        f'<title>Los dos grupos del contacto</title>'
        f'<body style="background:{SURF};color:{INK};font-family:system-ui;margin:24px;'
        f'max-width:900px"><h1 style="font-size:17px">Los «dos contactos» eran dos escalones '
        f'del registro de posición</h1>{svg}</body>')
    print('escrito:', out)
    for v in (25, 1000):
        o = data[v]
        print(f'  v={v:4d}: N={len(o)} σ={statistics.pstdev(o):.1f} rango {min(o)}–{max(o)} '
              f'grupos={[len(g) for g in clusters(o)]} paso del registro={step[v]:.0f}')


if __name__ == '__main__':
    main()
