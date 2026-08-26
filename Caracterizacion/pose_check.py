#!/usr/bin/env python3
"""Fase 0 de un DOF nuevo: mapear ANGLE_SET → postura física real.

El manual (secc. 2.6.11) publica el rango angular de cada DOF —dedos 20°-176°,
flexión del pulgar -13°-70°, rotación del pulgar 90°-165°— pero NO dice qué
extremo del registro `ANGLE_SET` (0 o 1000) corresponde a cada ángulo. Para los
dedos quedó resuelto («ANGLE_ACT(3)=1000, i.e. fully open» + las campañas del
Exp 1). Para el pulgar hay que MEDIRLO antes de usarlo, en vez de suponerlo.

Este script recorre un DOF por una lista de `ANGLE_SET`, se detiene en cada uno y
reporta `ANGLE_ACT`, `POS_ACT`, `FORCE_ACT` y `CURRENT`. Tú miras la mano y anotas
qué postura corresponde a cada parada. También sirve para mapear el RECORRIDO
LIBRE de un dedo (dónde topa solo) antes de montarle un bloque.

Seguridad: velocidad baja, techo de fuerza, watchdog de corriente, y abre todos
los dedos al salir. Los DOF anclados con `--hold` se mantienen durante todo el
barrido (p. ej. fijar la rotación mientras se barre la flexión).

Uso típico (pulgar):
    # 1) ¿qué extremo de ANGLE_SET(5) es 165°?  Mira la mano en cada parada.
    .venv/bin/python Caracterizacion/pose_check.py \
        --transport serial --serial-port /dev/ttyUSB0 --dof 5 --angles 1000,500,0

    # 2) con la rotación ya anclada, ¿hasta dónde flexiona libre el pulgar?
    .venv/bin/python Caracterizacion/pose_check.py \
        --transport serial --serial-port /dev/ttyUSB0 --dof 4 --hold 5:0 \
        --angles 1000,750,500,250,0
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from hand_modbus import (
    HandModbus, NDOF, ANGLE_SET, FORCE_SET, SPEED_SET,
    POS_ACT, ANGLE_ACT, FORCE_ACT, CURRENT,
    DOF_NAMES, DOF_DEG_RANGE, DOF_DEG_ENDPOINTS, reg_to_deg,
    parse_hold, describe_hold, angle_vector, open_vector, report_hold,
)


def goto(hand, dof, angle, args, hold):
    """Comanda ANGLE_SET y espera a que POS_ACT se detenga (o al timeout).

    Devuelve (pos, angle_act, force, current, motivo).
    """
    hand.write_block(SPEED_SET, [args.speed] * NDOF)
    hand.write_block(FORCE_SET, [args.force_set] * NDOF)
    hand.write_block(ANGLE_SET, angle_vector(dof, angle, hold))

    t0 = time.perf_counter()
    ref_pos = None; ref_t = t0
    pos = ang = force = cur = None
    reason = 'timeout'
    cur_over = 0
    while time.perf_counter() - t0 < args.timeout_move_s:
        t = time.perf_counter()
        pb = hand.read_block(POS_ACT)
        fb = hand.read_block(FORCE_ACT)
        cb = hand.read_block(CURRENT)
        pos = pb[dof] if pb else pos
        force = fb[dof] if fb else force
        cur = cb[dof] if cb else cur

        if force is not None and abs(force) > args.force_ceiling:
            reason = 'techo_fuerza'; break
        if cur is not None and cur > args.current_max:
            cur_over += 1
            if cur_over >= 3:
                reason = 'corriente'; break
        else:
            cur_over = 0

        if pos is not None:
            if ref_pos is None or abs(pos - ref_pos) > args.stall_band:
                ref_pos, ref_t = pos, t
            elif (t - ref_t) >= args.stall_hold and (t - t0) > 0.4:
                reason = 'detenido'; break
        time.sleep(0.005)

    ab = hand.read_block(ANGLE_ACT)
    ang = ab[dof] if ab else None
    return pos, ang, force, cur, reason


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Fase 0 de un DOF: mapear ANGLE_SET → postura física real.")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='serial')
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--ip', default='192.168.11.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)

    p.add_argument('--dof', type=int, required=True, help='DOF a barrer (0..5)')
    p.add_argument('--angles', default='1000,750,500,250,0',
                   help='lista de ANGLE_SET a visitar, coma-separada (def 1000..0)')
    p.add_argument('--hold', default='',
                   help="DOF a anclar durante el barrido, 'DOF:ANGLE' coma-separado")
    p.add_argument('--speed', type=int, default=200, help='SPEED_SET del barrido (def 200, lento)')
    p.add_argument('--force-set', type=int, default=600,
                   help='FORCE_SET durante el barrido (g crudos, def 600)')
    p.add_argument('--dwell-s', type=float, default=2.0,
                   help='segundos de pausa en cada parada, para que puedas mirar (def 2)')
    p.add_argument('--open-angle', type=int, default=1000)
    p.add_argument('--open-speed', type=int, default=500)
    p.add_argument('--settle-band', type=int, default=6)
    p.add_argument('--settle-timeout-s', type=float, default=4.0)
    p.add_argument('--timeout-move-s', type=float, default=8.0,
                   help='tope por parada (s, def 8)')
    p.add_argument('--stall-band', type=int, default=6,
                   help='avance de POS bajo el cual se considera detenido (def 6)')
    p.add_argument('--stall-hold', type=float, default=0.3,
                   help='tiempo detenido para dar la parada por asentada (s, def 0.3)')
    p.add_argument('--force-ceiling', type=int, default=600,
                   help='techo |FORCE_ACT| de emergencia (g crudos, def 600)')
    p.add_argument('--current-max', type=int, default=1000, help='corriente máx (mA, def 1000)')
    p.add_argument('--csv', default=None, help='ruta opcional para volcar la tabla')
    args = p.parse_args(argv)

    if not (0 <= args.dof < NDOF):
        print(f"ERROR: --dof fuera de rango 0..{NDOF-1}", file=sys.stderr)
        return 2
    try:
        hold = parse_hold(args.hold)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.dof in hold:
        print(f"ERROR: --hold no puede anclar el propio DOF barrido ({args.dof})", file=sys.stderr)
        return 2
    angles = [int(x) for x in args.angles.split(',') if x.strip()]
    if any(not (0 <= a <= 1000) for a in angles):
        print("ERROR: los --angles deben estar en 0..1000", file=sys.stderr)
        return 2

    if args.transport == 'tcp':
        hand = HandModbus.open_tcp(args.ip, args.port, args.device_id, args.timeout)
    else:
        hand = HandModbus.open_serial(args.serial_port, args.baud, args.device_id, args.timeout)
    if hand is None:
        print("ERROR: no se pudo establecer la conexión Modbus.", file=sys.stderr)
        return 1

    dof = args.dof
    lo, hi = DOF_DEG_RANGE[dof]
    known = DOF_DEG_ENDPOINTS[dof] is not None
    rows = []
    try:
        print(f"Barrido de DOF {dof} ({DOF_NAMES[dof]}).  Rango del manual: {lo}° … {hi}°.")
        print("Dirección registro↔ángulo: "
              + ("YA medida (se muestran grados)." if known
                 else "NO medida — por eso corres esto. MIRA la mano en cada parada."))
        print(f"Paradas: {angles}   pausa {args.dwell_s} s   v={args.speed}\n")

        print("Abriendo todos los dedos...")
        hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
        hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
        time.sleep(1.0)
        report_hold(hand, hold, args.settle_band, args.settle_timeout_s, args.open_speed)

        hdr = f"\n{'ANGLE_SET':>10} {'ANGLE_ACT':>10} {'POS_ACT':>9} {'FORCE_g':>8} {'mA':>6}  parada"
        print(hdr); print('-' * (len(hdr) - 1))
        for a in angles:
            pos, ang, force, cur, reason = goto(hand, dof, a, args, hold)
            deg = reg_to_deg(a, dof)
            print(f"{a:>10} {('—' if ang is None else ang):>10} "
                  f"{('—' if pos is None else pos):>9} {('—' if force is None else force):>8} "
                  f"{('—' if cur is None else cur):>6}  {reason}"
                  + (f"   ({deg}°)" if deg is not None else ""))
            rows.append({'angle_set': a, 'angle_act': ang, 'pos_act': pos,
                         'force_g': force, 'current_mA': cur, 'stop': reason})
            time.sleep(args.dwell_s)     # pausa para observar la mano

        poss = [r['pos_act'] for r in rows if r['pos_act'] is not None]
        if len(poss) >= 2:
            print(f"\nRecorrido de POS_ACT en el barrido: {min(poss)} … {max(poss)} "
                  f"({max(poss) - min(poss)} counts).")
        stalled = [r for r in rows if r['stop'] != 'detenido']
        if stalled:
            print(f"⚠ {len(stalled)} parada(s) NO se detuvieron limpio "
                  f"({', '.join(str(r['angle_set']) + ':' + r['stop'] for r in stalled)}): "
                  f"revisa si hay tope mecánico, colisión o timeout corto.")
        if not known:
            print(f"\n→ Anota qué postura viste en ANGLE_SET={angles[0]} y en ANGLE_SET={angles[-1]}.")
            print(f"  Con eso se completa DOF_DEG_ENDPOINTS[{dof}] en hand_modbus.py "
                  f"(rango {lo}°-{hi}°) y `--hold {dof}:<reg>` queda justificado.")

        if args.csv:
            with open(args.csv, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)
            print(f"\nCSV: {args.csv}")
    except KeyboardInterrupt:
        print("\n[interrumpido]")
    finally:
        try:
            hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
        except Exception:
            pass
        hand.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
