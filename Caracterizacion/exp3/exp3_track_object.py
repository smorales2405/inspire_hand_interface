#!/usr/bin/env python3
"""Sigue el objeto agarrado en un vídeo, para separar compresión de traslación.

En una pinza hay dos cosas que el comando de un dedo puede hacer: **comprimir** el
objeto contra el otro dedo (sube la fuerza de los dos) o **trasladarlo** (el otro
dedo apenas se entera). Las fuerzas solas no las distinguen; el vídeo sí.

Seguimiento por correlación de plantilla **con refinamiento subpíxel**, que no es
un lujo: los dedos se desplazan 0.45–0.60 mm por escalón y un píxel de esta
cámara son ~0.5 mm. Sin subpíxel la medida no resuelve el fenómeno que busca —
pasó, y el primer análisis salió en falso.

La cámara debe mirar **perpendicular al eje de la pinza**. La que mira a lo largo
del eje no ve la traslación, por bien que enfoque.

El suelo de ruido se mide en el propio vídeo, en un tramo con la mano quieta, y
sin él ninguna cifra de desplazamiento significa nada.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

try:
    import cv2
    import numpy as np
except ImportError:
    print("Faltan OpenCV/numpy:  .venv/bin/pip install opencv-python-headless", file=sys.stderr)
    raise


def subpixel(surf, loc):
    """Refina el pico de correlación por parábola en cada eje (~0.1 px)."""
    x, y = loc
    h, w = surf.shape
    out = [0.0, 0.0]
    for k, (a, b) in enumerate([((x - 1, y), (x + 1, y)), ((x, y - 1), (x, y + 1))]):
        if 0 <= a[0] < w and 0 <= b[0] < w and 0 <= a[1] < h and 0 <= b[1] < h:
            c0, c1, c2 = surf[a[1], a[0]], surf[y, x], surf[b[1], b[0]]
            den = c0 - 2 * c1 + c2
            if abs(den) > 1e-9:
                out[k] = 0.5 * (c0 - c2) / den
    return x + out[0], y + out[1]


def _frames(path, every):
    """Genera (t, imagen). Acepta un vídeo o una CARPETA de fotos de una ráfaga.

    La ráfaga en fotos existe porque a 4K el vídeo pesa ~7 MB/s: una tanda de
    cuatro minutos no cabe. Y no hace falta velocidad — los escalones duran
    segundos, así que 1 Hz de fotos a plena resolución bate a 30 fps recortados.
    """
    if os.path.isdir(path):
        files = sorted(f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.png')))
        if not files:
            raise SystemExit(f"{path} no tiene fotos")
        stamps = {}
        for name in os.listdir(path):                    # el CSV que deja camara.py
            if name.endswith('_frames.csv'):
                with open(os.path.join(path, name)) as fh:
                    for r in csv.DictReader(fh):
                        stamps[r['fichero']] = float(r['t_unix'])
        t0 = min(stamps.values()) if stamps else 0.0
        for k, f in enumerate(files):
            if k % every:
                continue
            t = stamps.get(f, None)
            yield (t - t0 if t is not None else float(k)), cv2.imread(os.path.join(path, f))
        return
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n <= 0:
        raise SystemExit(f"no se pudo leer {path}")
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % every == 0:
            yield i, fr
        i += 1
    cap.release()


def track(path, tpl_box, search_box, every, min_corr, fps):
    seq = list(_frames(path, every))
    if not seq:
        raise SystemExit("sin fotogramas")
    ref = seq[len(seq) // 3][1]
    ty0, ty1, tx0, tx1 = tpl_box
    tpl = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)[ty0:ty1, tx0:tx1]
    sy0, sy1, sx0, sx1 = search_box
    is_dir = os.path.isdir(path)
    rows = []
    for k, fr in seq:
        if fr is None:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)[sy0:sy1, sx0:sx1]
        surf = cv2.matchTemplate(g, tpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(surf)
        if mx >= min_corr:
            sx, sy = subpixel(surf, loc)
            rows.append((k if is_dir else k / fps, sx, sy, mx))
    return np.array(rows)


def ptp_windows(t, x, y, win_s):
    """Excursión pico a pico en ventanas solapadas del tamaño de un trial."""
    if len(t) < 20:
        return None
    rate = len(t) / (t[-1] - t[0])
    n = max(4, int(win_s * rate))
    v = [max(np.ptp(x[i:i + n]), np.ptp(y[i:i + n]))
         for i in range(0, len(t) - n, max(1, n // 2))]
    return (float(np.median(v)), float(max(v)), len(v)) if v else None


def main(argv=None):
    p = argparse.ArgumentParser(description="Seguimiento subpíxel del objeto agarrado.")
    p.add_argument('video', help='fichero de vídeo o CARPETA con la ráfaga de fotos')
    p.add_argument('--tpl', required=True, metavar='y0,y1,x0,x1',
                   help='recuadro de la plantilla: un rasgo SOLIDARIO con el objeto '
                        '(un logo impreso va perfecto)')
    p.add_argument('--search', required=True, metavar='y0,y1,x0,x1')
    p.add_argument('--mm-per-px', type=float, required=True,
                   help='escala: mide el objeto en píxeles y divide su tamaño real')
    p.add_argument('--quiet', metavar='t0,t1', required=True,
                   help='tramo en segundos con la mano QUIETA: da el suelo de ruido')
    p.add_argument('--active', metavar='t0,t1', required=True,
                   help='tramo en segundos con los escalones')
    p.add_argument('--trial-s', type=float, default=5.0, help='duración de un trial')
    p.add_argument('--every', type=int, default=3, help='procesa 1 de cada N fotogramas')
    p.add_argument('--min-corr', type=float, default=0.6)
    p.add_argument('--fps', type=float, default=28.0)
    p.add_argument('--finger-mm', type=float, default=None,
                   help='avance del dedo por escalón (mm). Con esto el resultado se expresa '
                        'como fracción, que es lo comparable entre montajes')
    a = p.parse_args(argv)

    box = lambda s: tuple(int(v) for v in s.split(','))      # noqa: E731
    rng = lambda s: tuple(float(v) for v in s.split(','))    # noqa: E731
    d = track(a.video, box(a.tpl), box(a.search), a.every, a.min_corr, a.fps)
    if not len(d):
        raise SystemExit("la plantilla no se encontró en ningún fotograma: revisa --tpl/--search")
    t, x, y = d[:, 0], d[:, 1] * a.mm_per_px, d[:, 2] * a.mm_per_px
    print(f"{len(t)} muestras · escala {a.mm_per_px:.3f} mm/px · "
          f"resolución subpíxel ~{a.mm_per_px/10:.3f} mm\n")

    res = {}
    for lab, spec in (('quieta', a.quiet), ('escalones', a.active)):
        t0, t1 = rng(spec)
        m = (t >= t0) & (t < t1)
        r = ptp_windows(t[m], x[m], y[m], a.trial_s)
        if r is None:
            print(f"  {lab}: muestras insuficientes")
            continue
        res[lab] = r
        print(f"  {lab:<10} [{t0:.0f}–{t1:.0f} s]  pico-a-pico en {a.trial_s:.0f} s: "
              f"mediana {r[0]:.3f} mm · máx {r[1]:.3f} mm  ({r[2]} ventanas)")
    if len(res) == 2 and res['quieta'][0] > 0:
        f = res['escalones'][0] / res['quieta'][0]
        print(f"\n  relación escalones/ruido = {f:.1f}×  "
              f"({'medible' if f > 3 else 'en el ruido'})")
    # La relación con el ruido solo dice si la medida EXISTE, y depende del montaje
    # (resolución y tramo quieto). Lo que dice si el movimiento IMPORTA es cuánto se
    # desplaza el objeto comparado con lo que avanza el dedo que lo empuja.
    if 'escalones' in res and a.finger_mm:
        frac = res['escalones'][0] / a.finger_mm
        print(f"\n  el objeto se desplaza {res['escalones'][0]:.3f} mm y el dedo avanza "
              f"{a.finger_mm:.2f} mm  →  {100*frac:.0f} %")
        print("  → " + (
            "el dedo MUEVE el objeto en vez de comprimirlo" if frac > 0.6 else
            "el objeto está sujeto: el avance del dedo se convierte en fuerza" if frac < 0.25
            else "parte del avance mueve el objeto y parte lo comprime"))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
