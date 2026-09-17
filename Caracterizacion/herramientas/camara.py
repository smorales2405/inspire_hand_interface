#!/usr/bin/env python3
"""Captura de la cámara (Logitech BRIO) como testigo visual de las pruebas.

Deliberadamente **no abre Modbus**. Toda la caracterización corre con un único
cliente Modbus en un único proceso; una segunda conexión desde aquí competiría
con la prueba en curso. Por eso esta herramienta se lanza como proceso aparte:
graba mientras el script de la prueba manda la mano, y los dos se sincronizan
después por reloj de pared.

Modos:
  --shot                 una foto
  --burst N --every S    N fotos separadas S segundos
  --video S              graba S segundos a MJPG/mp4

Cada captura deja su instante de reloj de pared en un CSV al lado, que es lo que
permite alinearla luego con el log de la prueba (los scripts de Exp 3 imprimen su
hora de arranque).

Nota de formato: a 1920×1080 el BRIO entrega YUYV sin comprimir a ~5 fps por el
límite del bus USB. Para vídeo se pide MJPG, que sí da 30 fps.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime

try:
    import cv2
except ImportError:
    print("Falta OpenCV. Instálalo en el venv:  .venv/bin/pip install opencv-python-headless",
          file=sys.stderr)
    raise


def find_device(preferred=None):
    """Devuelve el índice de la BRIO, o el preferido si se pasa."""
    if preferred is not None:
        return preferred
    base = '/sys/class/video4linux'
    for name in sorted(os.listdir(base)):
        try:
            with open(os.path.join(base, name, 'name')) as fh:
                if 'BRIO' in fh.read().upper():
                    return int(name.replace('video', ''))
        except OSError:
            pass
    return 0


def best_focus(cap, roi, coarse=25, fine=5):
    """Busca el enfoque manual que maximiza la nitidez sobre la región de interés.

    El autofoco del BRIO se engancha al fondo cuando la mano no llena el cuadro:
    medido en este banco, 9.9 de varianza del laplaciano con autofoco contra 287
    con el foco fijado a mano. No es un ajuste fino, es un factor 29.
    """
    import numpy as np                                        # noqa: F401
    y0, y1, x0, x1 = roi

    def sharp(f):
        cap.set(cv2.CAP_PROP_FOCUS, f)
        time.sleep(0.8)
        for _ in range(5):
            cap.read()
        ok, fr = cap.read()
        if not ok:
            return -1
        g = cv2.cvtColor(fr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(g, cv2.CV_64F).var()

    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    best = max(((f, sharp(f)) for f in range(0, 256, coarse)), key=lambda t: t[1])
    lo, hi = max(0, best[0] - coarse), min(255, best[0] + coarse)
    best = max([best] + [(f, sharp(f)) for f in range(lo, hi + 1, fine)], key=lambda t: t[1])
    # Fijar el mejor y VACIAR el búfer: sin esto la primera captura sale de un
    # fotograma anterior, tomado con el último foco del barrido. Dentro del bucle
    # ya se descartaban frames; al final faltaba, y el resultado era una foto
    # nítida en la medida y borrosa en el disco.
    cap.set(cv2.CAP_PROP_FOCUS, best[0])
    time.sleep(0.9)
    for _ in range(8):
        cap.read()
    return best


def open_cam(args):
    cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise SystemExit(f"no se pudo abrir /dev/video{args.device}")
    if args.mjpg:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    for _ in range(args.warmup):        # descartar frames de autoexposición
        cap.read()
    if args.focus_auto:
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        roi = (h // 5, h * 9 // 10, w // 6, w * 2 // 3)     # donde vive la mano
        f, sh = best_focus(cap, roi)
        print(f"enfoque fijado a {f} (nitidez {sh:.0f}) — reutilízalo con --focus {f}")
    elif args.focus is not None:
        # enfoque fijo: el autofoco del BRIO "bombea" cuando un dedo se mueve, y
        # eso arruina justo los fotogramas del contacto
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_FOCUS, args.focus)
        time.sleep(0.5)
        for _ in range(5):
            cap.read()
    return cap


def stamp(frame, label, t0):
    if not label and t0 is None:
        return frame
    txt = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    if t0 is not None:
        txt += f"  +{time.perf_counter()-t0:6.2f}s"
    if label:
        txt += f"   {label}"
    h = frame.shape[0]
    cv2.rectangle(frame, (0, h - 46), (760, h), (0, 0, 0), -1)
    cv2.putText(frame, txt, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (255, 255, 255), 2, cv2.LINE_AA)
    return frame


def run(args):
    os.makedirs(args.outdir, exist_ok=True)
    tag = args.label or 'cap'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    cap = open_cam(args)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cc = int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, 'little').decode(errors='replace')
    print(f"/dev/video{args.device} · {w}×{h} · {cc} · {cap.get(cv2.CAP_PROP_FPS):.0f} fps")

    idx_path = os.path.join(args.outdir, f'{tag}_{ts}_frames.csv')
    fh = open(idx_path, 'w', newline='')
    wr = csv.writer(fh)
    wr.writerow(['fichero', 't_wall_iso', 't_unix', 'n'])
    t0 = time.perf_counter()

    try:
        if args.video:
            path = os.path.join(args.outdir, f'{tag}_{ts}.mp4')
            vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'),
                                 args.fps, (w, h))
            n = 0
            print(f"grabando {args.video:.0f} s → {path}")
            while time.perf_counter() - t0 < args.video:
                ok, fr = cap.read()
                if not ok:
                    continue
                wr.writerow([os.path.basename(path), datetime.now().isoformat(),
                             f"{time.time():.3f}", n])
                vw.write(stamp(fr, args.label, t0))
                n += 1
            vw.release()
            print(f"{n} fotogramas ({n/args.video:.1f} fps reales)")
        else:
            for i in range(args.burst):
                if i:
                    time.sleep(args.every)
                ok, fr = cap.read()
                if not ok:
                    print("lectura fallida", file=sys.stderr)
                    continue
                name = f'{tag}_{ts}_{i:03d}.jpg' if args.burst > 1 else f'{tag}_{ts}.jpg'
                path = os.path.join(args.outdir, name)
                cv2.imwrite(path, stamp(fr, args.label, t0 if args.burst > 1 else None),
                            [cv2.IMWRITE_JPEG_QUALITY, args.quality])
                wr.writerow([name, datetime.now().isoformat(), f"{time.time():.3f}", i])
                print(f"  {path}")
    finally:
        fh.close()
        cap.release()
    print(f"índice: {idx_path}")
    return 0


def parse_args(argv=None):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description="Captura de la cámara como testigo de las pruebas.")
    p.add_argument('--device', type=int, default=None, help='índice de /dev/videoN (auto: BRIO)')
    p.add_argument('--shot', action='store_true', help='una foto (por defecto)')
    p.add_argument('--burst', type=int, default=1, help='número de fotos')
    p.add_argument('--every', type=float, default=1.0, help='segundos entre fotos del burst')
    p.add_argument('--video', type=float, default=0.0, help='graba N segundos')
    p.add_argument('--label', default='', help='etiqueta: va en el nombre y sobreimpresa')
    p.add_argument('--width', type=int, default=1920)
    p.add_argument('--height', type=int, default=1080)
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--mjpg', action='store_true', default=True)
    p.add_argument('--no-mjpg', dest='mjpg', action='store_false')
    p.add_argument('--focus', type=int, default=None,
                   help='enfoque manual 0-255 (recomendado: el autofoco bombea al moverse un dedo)')
    p.add_argument('--focus-auto', action='store_true',
                   help='barre el enfoque y fija el más nítido sobre la mano (~20 s). '
                        'Úsalo tras mover la cámara; luego reutiliza el valor con --focus')
    p.add_argument('--warmup', type=int, default=12)
    p.add_argument('--quality', type=int, default=92)
    p.add_argument('--outdir', default=os.path.join(here, 'imagenes', 'pruebas'))
    a = p.parse_args(argv)
    a.device = find_device(a.device)
    return a


if __name__ == '__main__':
    raise SystemExit(run(parse_args()))
