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


def track(path, tpl_box, search_box, every, min_corr, fps):
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n <= 0:
        raise SystemExit(f"no se pudo leer {path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * 0.35))
    ok, ref = cap.read()
    if not ok:
        raise SystemExit("no se pudo leer el fotograma de referencia")
    ty0, ty1, tx0, tx1 = tpl_box
    tpl = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)[ty0:ty1, tx0:tx1]
    sy0, sy1, sx0, sx1 = search_box
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    rows, i = [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % every == 0:
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)[sy0:sy1, sx0:sx1]
            surf = cv2.matchTemplate(g, tpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(surf)
            if mx >= min_corr:
                sx, sy = subpixel(surf, loc)
                rows.append((i / fps, sx, sy, mx))
        i += 1
    cap.release()
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
    p.add_argument('video')
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
        print(f"\n  relación escalones/ruido = {f:.1f}×")
        print("  → " + ("el objeto SE TRASLADA con el dedo" if f > 3 else
                        "sin traslación por encima del ruido"))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
