#!/usr/bin/env python3
"""Comprobación del techo de fuerza sostenible, con el objeto YA sujeto en la pinza.

E3.3 midió que el índice y el pulgar, llevados a ~1000 g **contra `block1` apoyado
en la palma**, se desplomaban a una meseta de ~585 g en ~0.3 s, y esta página
concluyó que era un límite de la mano porque dos dedos con rigideces distintas
daban la misma meseta.

Esa conclusión tiene una explicación alternativa que se descartó demasiado
rápido: **que lo que cedía fuera el bloque**, no la mano. Los dos dedos empujaban
el mismo objeto sobre el mismo tipo de apoyo compliante, así que una meseta común
es justo lo que se esperaría.

Esta prueba separa las dos hipótesis. Con el objeto sujeto **entre dedos** —sin
apoyo externo que pueda deslizar— se sube un dedo hacia la consigna y se mira si
la fuerza aguanta. Si aguanta, el desplome era del montaje.

No abre la mano ni re-tara: eso soltaría el objeto. Las cifras son relativas a la
tara vigente, que es suficiente porque lo que se mide es **si la fuerza se
mantiene**, no su valor absoluto.
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from hand_modbus import (                                    # noqa: E402
    HandModbus, NDOF, ANGLE_SET, FORCE_SET, SPEED_SET,
    POS_ACT, FORCE_ACT, CURRENT, DOF_NAMES,
)


def vec(dof, value, hold):
    v = [-1] * NDOF
    for d, a in hold.items():
        v[d] = a
    v[dof] = int(value)
    return v


def read(hand):
    return hand.read_block(POS_ACT), hand.read_block(FORCE_ACT), hand.read_block(CURRENT)


def run(hand, args):
    dof, watch = args.dof, [int(d) for d in args.watch.split(',')]
    hold = {5: args.rot}
    p, f, c = read(hand)
    if not (p and f):
        print("sin lecturas"); return 1
    print(f"Comprobación del techo · empuja {DOF_NAMES[dof]} hacia {args.target} g")
    print("  estado inicial: " + "  ".join(f"{DOF_NAMES[d]} {f[d]}g/POS {p[d]}" for d in watch))
    print(f"  topes: fuerza {args.force_max} g en cualquier dedo · POS {args.pos_limit} · "
          f"temp {args.temp_max} °C")
    if any(f[d] > args.force_max for d in watch):
        print("ABORTA: ya se parte por encima del tope de fuerza"); return 2
    if min(f[d] for d in watch) < args.min_hold_g:
        print(f"ABORTA: algún dedo por debajo de {args.min_hold_g} g — "
              f"el objeto no está sujeto"); return 2

    hand.write_block(SPEED_SET, [args.speed] * NDOF)
    hand.write_block(FORCE_SET, [args.fset] * NDOF)

    # ── subir hasta la consigna, en pasos pequeños ────────────────────────
    a = hand.read_block(ANGLE_SET)
    cmd = a[dof] if a else None
    if cmd is None:
        print("no se pudo leer ANGLE_SET"); return 1
    t0 = time.perf_counter()
    reached = False
    while time.perf_counter() - t0 < args.seek_timeout:
        p, f, c = read(hand)
        if not (p and f):
            continue
        if f[dof] >= args.target:
            reached = True
            break
        bad = next((f"{DOF_NAMES[d]} {f[d]} g > {args.force_max}"
                    for d in watch if f[d] > args.force_max), None) \
            or (f"POS {p[dof]} > {args.pos_limit}" if p[dof] > args.pos_limit else None)
        if bad:
            print(f"PARA la subida: {bad}")
            break
        cmd = max(0, cmd - args.step)
        hand.write_block(ANGLE_SET, vec(dof, cmd, hold))
        time.sleep(args.dwell)
    p, f, _ = read(hand)
    print(f"  {'alcanzado' if reached else 'parado'} en {f[dof]} g "
          f"(POS {p[dof]}, ANGLE_SET {cmd}) tras {time.perf_counter()-t0:.0f} s")

    # ── congelar y mirar ──────────────────────────────────────────────────
    print(f"\n  COMANDO CONGELADO. Observando {args.hold_s:.0f} s:\n")
    print(f"{'t(s)':>6}" + "".join(f"{DOF_NAMES[d][:8]:>10}" for d in watch)
          + f"{'POS':>8}{'I(mA)':>7}")
    rows = []
    t0 = time.perf_counter()
    nxt = 0.0
    while True:
        el = time.perf_counter() - t0
        if el > args.hold_s:
            break
        p, f, c = read(hand)
        if not (p and f):
            continue
        rows.append([f"{el:.3f}"] + [f[d] for d in watch] + [p[dof], c[dof] if c else ''])
        if el >= nxt:
            print(f"{el:6.0f}" + "".join(f"{f[d]:>10}" for d in watch)
                  + f"{p[dof]:>8}{c[dof] if c else 0:>7}")
            nxt += args.print_every
        bad = next((f"{DOF_NAMES[d]} {f[d]} g" for d in watch if f[d] > args.force_max), None)
        if bad:
            print(f"  ABORTA durante el sostenimiento: {bad}")
            break

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, f'techo_dof{dof}_{args.tag}.csv')
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['t_s'] + [f'force{d}' for d in watch] + ['pos', 'cur'])
        w.writerows(rows)

    # ── veredicto ─────────────────────────────────────────────────────────
    col = {d: [r[1 + i] for r in rows] for i, d in enumerate(watch)}
    print(f"\n  Traza: {path}  ({len(rows)} muestras)\n")
    for d in watch:
        v = col[d]
        head = statistics.median(v[:max(3, len(v) // 20)])
        tail = statistics.median(v[-max(3, len(v) // 20):])
        print(f"  {DOF_NAMES[d]:<16} {head:5.0f} → {tail:5.0f} g   "
              f"({tail-head:+.0f} g, {100*(tail-head)/head if head else 0:+.0f} %)")
    # El veredicto va contra el PICO al congelar, no contra la mediana del primer
    # tramo: si el resbalón ocurre en el primer segundo, esa mediana ya es
    # posterior al desplome y la prueba se declara a sí misma no concluyente.
    v, pos = col[dof], [r[-2] for r in rows]
    peak = max(v[:max(5, len(v) // 50)])
    tail = statistics.median(v[-max(3, len(v) // 20):])
    drop = (peak - tail) / peak if peak else 0
    dpos = pos[-1] - pos[0]
    t_slip = next((float(rows[k][0]) for k in range(len(v)) if v[k] < peak - 0.5 * (peak - tail)),
                  None) if drop > 0.10 else None
    print()
    if peak < args.target * 0.8:
        print(f"  → no se alcanzó la consigna ({peak:.0f} de {args.target:.0f} g): no concluyente")
    elif drop < 0.10:
        print(f"  → SOSTIENE {tail:.0f} g con el comando congelado ({100*drop:.0f} % de caída).")
    else:
        print(f"  → RESBALA: {peak:.0f} → {tail:.0f} g ({100*drop:.0f} %)"
              + (f" a los {t_slip:.1f} s" if t_slip else "")
              + f", con el dedo retrocediendo {dpos:+.0f} counts.")
        print(f"     El retroceso de POS lo delata: el que cede es el ACTUADOR, no el objeto.")
        print(f"     Y por debajo aguanta: {tail:.0f} g estables el resto del registro.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="¿Sostiene la mano la fuerza, con el objeto en pinza?")
    p.add_argument('--ip', default='192.168.124.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--dof', type=int, default=4)
    p.add_argument('--watch', default='4,3,2')
    p.add_argument('--rot', type=int, default=0)
    p.add_argument('--target', type=float, default=1000.0)
    p.add_argument('--hold-s', type=float, default=60.0)
    p.add_argument('--step', type=int, default=2)
    p.add_argument('--dwell', type=float, default=0.30)
    p.add_argument('--speed', type=int, default=25)
    p.add_argument('--fset', type=int, default=2200, help='paro del firmware, muy por encima')
    p.add_argument('--seek-timeout', type=float, default=180.0)
    p.add_argument('--print-every', type=float, default=5.0)
    p.add_argument('--force-max', type=float, default=1250.0)
    p.add_argument('--pos-limit', type=int, default=820)
    p.add_argument('--min-hold-g', type=float, default=60.0)
    p.add_argument('--temp-max', type=int, default=50)
    p.add_argument('--tag', default='a')
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))
    a = p.parse_args(argv)

    hand = HandModbus.open_tcp(a.ip, a.port, a.device_id, a.timeout)
    if hand is None:
        print("sin conexión", file=sys.stderr); return 1
    try:
        return run(hand, a)
    except KeyboardInterrupt:
        print("\n[interrumpido] — la mano NO se abre para no soltar el objeto")
        return 130
    finally:
        hand.close()


if __name__ == '__main__':
    raise SystemExit(main())
