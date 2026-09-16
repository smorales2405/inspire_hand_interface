#!/usr/bin/env python3
"""E3.4 + E3.5 — Decaimiento a comando constante y deriva del cero.

Las dos pruebas comparten montaje y, de hecho, **comparten ciclo**: el
procedimiento de E3.5 (abrir → leer la base sin contacto → cerrar a `F₀` →
sostener 60 s → abrir → leer la base otra vez) contiene dentro la medida de E3.4
(qué le pasa a la fuerza con `ANGLE_SET` congelado). Correrlas por separado sería
pagar dos veces la misma rampa térmica.

E3.4 pregunta: con el comando congelado, ¿la fuerza decae? Si decae, el
integrador del PI empujará indefinidamente y caminará la posición hacia dentro
del objeto. Se mide la curva, su magnitud, su constante y si `POS_ACT` se mueve
solo (retroceso del actuador).

E3.5 pregunta: ¿cuánto deriva el cero de fuerza mientras el actuador se calienta?
En impactos breves da igual; en un lazo que SOSTIENE fuerza, la deriva del cero
**es** error de fuerza, y el integrador la persigue.

**SE CALIBRA UNA SOLA VEZ, en frío y con la palma abierta.** Recalibrar entre
ciclos borraría justo lo que E3.5 mide. Por eso el script arranca exigiendo el
actuador frío y a partir de ahí no vuelve a tarar.
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
sys.path.insert(0, _HERE)

from hand_modbus import (                                    # noqa: E402
    HandModbus, NDOF, ANGLE_SET, FORCE_SET, SPEED_SET,
    POS_ACT, FORCE_ACT, CURRENT,
    DOF_NAMES, fmt_angle, parse_hold,
    angle_vector, open_vector, report_hold,
)
from exp3_min_step import (                                  # noqa: E402
    Reader, Guard, seek_contact, wait_arrived, window, FORCE_CLB,
)


def sample_window(rd, dof, seconds, sink=None, tag=''):
    """Muestrea `seconds` y devuelve las medianas. Si hay `sink`, escribe cada fila."""
    fs, ps, cs = [], [], []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        p, f, c, fp, ff = rd.sample()
        t = time.perf_counter() - t0
        if f:
            fs.append(f[dof])
        if p:
            ps.append(p[dof])
        if c:
            cs.append(c[dof])
        if sink is not None:
            sink([tag, f"{t:.4f}",
                  '' if not f else f[dof], '' if not p else p[dof],
                  '' if not c else c[dof], int(ff), int(fp)])
        time.sleep(0.002)
    med = lambda v: statistics.median(v) if v else None      # noqa: E731
    return med(fs), med(ps), med(cs), len(fs)


def decay_metrics(rows, head_s, tail_s):
    """De la traza del sostenimiento: caída total, constante y movimiento de POS."""
    v = [(float(t), fv, pv) for _tag, t, fv, pv, _c, _ff, _fp in rows
         if fv != '' and pv != '']
    v = [(t, float(f), float(p)) for t, f, p in v]
    if len(v) < 20:
        return None
    t_end = v[-1][0]
    head = [f for t, f, _ in v if t <= head_s]
    tail = [f for t, f, _ in v if t >= t_end - tail_s]
    ph = [p for t, _, p in v if t <= head_s]
    pt = [p for t, _, p in v if t >= t_end - tail_s]
    f0, f1 = statistics.median(head), statistics.median(tail)
    drop = f0 - f1
    t63 = None
    if abs(drop) > 5:
        target = f0 - 0.632 * drop
        for t, f, _ in v:
            if (drop > 0 and f <= target) or (drop < 0 and f >= target):
                t63 = t
                break
    return dict(f_start=f0, f_end=f1, drop=drop, frac=drop / f0 if f0 else None,
                t63=t63, pos_start=statistics.median(ph),
                pos_end=statistics.median(pt),
                dpos=statistics.median(pt) - statistics.median(ph),
                n=len(v), dur=t_end)


def run(hand, args):
    dof = args.dof
    os.makedirs(args.outdir, exist_ok=True)
    rd = Reader(hand)

    print(f"E3.4+E3.5 · DOF {dof} ({DOF_NAMES[dof]}) · F₀ = {args.f0} g · "
          f"{args.cycles} ciclos de {args.hold_s:.0f} s")
    print(f"  límite duro de POS: {args.pos_limit}   techo fuerza {args.safety_force_g} g")

    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, open_vector(args.open_angle, args.hold_map))
    time.sleep(1.0)
    report_hold(hand, args.hold_map, 6, 3.0, args.open_speed)

    guard = Guard(hand, args, args.pos_limit)
    t_ini = guard.temp()
    if not args.no_cal:
        if t_ini is not None and t_ini > args.temp_start_max:
            print(f"ABORTA: arranca a {t_ini} °C. E3.5 EXIGE actuador frío "
                  f"(≤ {args.temp_start_max}). Deja enfriar la mano.")
            return 2
        print(f"  temperatura inicial: {t_ini} °C  (frío, como pide E3.5)")
        print("  calibrando (forceClb, palma abierta) — ÚNICA vez de la sesión")
        hand.write_block(FORCE_CLB, [1])
        time.sleep(1.5)
    else:
        print(f"  temperatura inicial: {t_ini} °C  ·  SIN recalibrar (continuación)")

    sum_path = os.path.join(args.outdir, f'e345_dof{dof}_F{args.f0}.csv')
    trc_path = os.path.join(args.outdir, f'e345_dof{dof}_F{args.f0}_holds.csv')
    new = not os.path.exists(sum_path)
    fh_t = open(trc_path, 'a', newline='')
    w_t = csv.writer(fh_t)
    if os.path.getsize(trc_path) == 0:
        w_t.writerow(['cycle', 'phase', 't_s', 'force_g', 'pos_act', 'cur_mA',
                      'fresh_f', 'fresh_p'])

    t_session = time.perf_counter()
    cmd = args.start_cmd if args.start_cmd else None

    with open(sum_path, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['cycle', 't_session_s', 'temp_before', 'temp_after',
                        'base_before_g', 'base_after_g', 'cmd', 'pos_contact',
                        'f_start', 'f_end', 'drop_g', 'drop_frac', 't63_s',
                        'pos_start', 'pos_end', 'dpos', 'cur_med', 'aborted'])
        for cyc in range(1, args.cycles + 1):
            cyc_id = f"{args.tag}{cyc}"
            # 1. abrir y leer la base SIN contacto
            hand.write_block(ANGLE_SET, open_vector(args.open_angle, args.hold_map))
            time.sleep(args.open_s)
            t_b = guard.temp()
            base_b, _, _, _ = sample_window(rd, dof, args.base_s,
                                            lambda r: w_t.writerow([cyc_id] + r), 'base_pre')

            # 2. acercarse y establecer F0
            if cmd is None:
                f_now, cmd = seek_contact(hand, rd, guard, args, lambda *a: None)
                if f_now is None:
                    print(f"ABORTA estableciendo contacto: {guard.reason}")
                    break
            else:
                # ya sabemos el comando: ir rápido hasta un poco antes y afinar
                hand.write_block(SPEED_SET, [args.close_speed] * NDOF)
                hand.write_block(FORCE_SET,
                                 [min(args.f0 + args.fset_margin, 2500)] * NDOF)
                hand.write_block(ANGLE_SET,
                                 angle_vector(dof, cmd + args.backoff, args.hold_map))
                time.sleep(0.5)
                wait_arrived(rd, dof, lambda *a: None)
                hand.write_block(ANGLE_SET, angle_vector(dof, cmd, args.hold_map))
                time.sleep(0.5)
                wait_arrived(rd, dof, lambda *a: None)
                for _ in range(args.retrim_max):
                    f_now, pos, _, _, _ = window(rd, dof, 0.3, lambda *a: None)
                    if guard.check(pos, f_now, None):
                        break
                    if f_now is None or abs(f_now - args.f0) <= args.f0_tol:
                        break
                    cmd = max(0, min(1000, cmd + (-1 if f_now < args.f0 else +1)))
                    hand.write_block(ANGLE_SET, angle_vector(dof, cmd, args.hold_map))
                    time.sleep(0.25)
                    wait_arrived(rd, dof, lambda *a: None)
            if guard.reason:
                print(f"ABORTA: {guard.reason}")
                break

            p, _, _, _, _ = rd.sample()
            pos_c = p[dof] if p else None

            # 3. CONGELAR el comando y mirar 60 s
            hold_rows = []
            def sink(r):
                hold_rows.append(r)
                w_t.writerow([cyc_id] + r)
            _f, _p, cur_med, _n = sample_window(rd, dof, args.hold_s, sink, 'hold')
            m = decay_metrics(hold_rows, args.head_s, args.tail_s)

            # 4. abrir y volver a leer la base
            hand.write_block(ANGLE_SET, open_vector(args.open_angle, args.hold_map))
            time.sleep(args.open_s)
            base_a, _, _, _ = sample_window(rd, dof, args.base_s,
                                            lambda r: w_t.writerow([cyc_id] + r), 'base_post')
            t_a = guard.temp()
            bad = 1 if guard.reason else 0

            ts = time.perf_counter() - t_session
            if m is None:
                w.writerow([cyc_id, f"{ts:.1f}", t_b, t_a, base_b, base_a, cmd,
                            pos_c] + [''] * 9 + [bad])
                print(f"[{cyc}/{args.cycles}] ciclo sin traza utilizable")
            else:
                w.writerow([cyc_id, f"{ts:.1f}", t_b, t_a,
                            '' if base_b is None else f"{base_b:.0f}",
                            '' if base_a is None else f"{base_a:.0f}",
                            cmd, pos_c,
                            f"{m['f_start']:.0f}", f"{m['f_end']:.0f}",
                            f"{m['drop']:.0f}",
                            '' if m['frac'] is None else f"{m['frac']:.3f}",
                            '' if m['t63'] is None else f"{m['t63']:.2f}",
                            f"{m['pos_start']:.0f}", f"{m['pos_end']:.0f}",
                            f"{m['dpos']:.1f}",
                            '' if cur_med is None else f"{cur_med:.0f}", bad])
                t63_s = '—' if m['t63'] is None else f"{m['t63']:.1f}"
                print(f"[{cyc}/{args.cycles}] t={ts:6.0f}s  {t_b}→{t_a} °C  "
                      f"base {base_b:+5.0f}→{base_a:+5.0f} g  |  "
                      f"F {m['f_start']:4.0f}→{m['f_end']:4.0f} g "
                      f"({m['drop']:+5.0f}, {100*(m['frac'] or 0):+4.0f} %)  "
                      f"t63={t63_s:>5}s  "
                      f"ΔPOS={m['dpos']:+5.1f}  I={cur_med:.0f} mA")
            fh.flush()
            fh_t.flush()
            if bad:
                break

    fh_t.close()
    print(f"\nResumen: {sum_path}")
    print(f"Trazas : {trc_path}")
    print(f"Comando final: {cmd}   ·   temperatura final: {guard.temp()} °C")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="E3.4+E3.5 — decaimiento y deriva del cero.")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='tcp')
    p.add_argument('--ip', default='192.168.124.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)

    p.add_argument('--dof', type=int, required=True)
    p.add_argument('--hold', default='')
    p.add_argument('--f0', type=int, default=500)
    p.add_argument('--approach-angle', type=int, required=True)
    p.add_argument('--pos-limit', type=int, required=True)
    p.add_argument('--cycles', type=int, default=5)
    p.add_argument('--tag', default='c', help='prefijo de los ciclos, para encadenar tandas')
    p.add_argument('--start-cmd', type=int, default=0,
                   help='comando que ya da F0 (salta la búsqueda lenta; para continuaciones)')
    p.add_argument('--backoff', type=int, default=6,
                   help='unidades por encima del comando a las que se llega antes de afinar')

    p.add_argument('--hold-s', type=float, default=60.0)
    p.add_argument('--base-s', type=float, default=3.0)
    p.add_argument('--open-s', type=float, default=5.0)
    p.add_argument('--head-s', type=float, default=1.0)
    p.add_argument('--tail-s', type=float, default=2.0)
    p.add_argument('--f0-tol', type=float, default=40.0)
    p.add_argument('--retrim-max', type=int, default=25)

    p.add_argument('--settle-s', type=float, default=0.30)
    p.add_argument('--step-dwell', type=float, default=0.25)
    p.add_argument('--seek-step', type=int, default=2)
    p.add_argument('--seek-dwell', type=float, default=0.12)
    p.add_argument('--seek-timeout', type=float, default=180.0)
    p.add_argument('--fset-margin', type=int, default=900)
    p.add_argument('--close-speed', type=int, default=25)
    p.add_argument('--open-speed', type=int, default=1000)
    p.add_argument('--open-angle', type=int, default=1000)
    p.add_argument('--no-cal', action='store_true')

    p.add_argument('--safety-force-g', type=int, default=1500)
    p.add_argument('--current-max', type=int, default=700)
    p.add_argument('--current-hold-n', type=int, default=2000)
    p.add_argument('--temp-max', type=int, default=55)
    p.add_argument('--temp-start-max', type=int, default=32)
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))

    args = p.parse_args(argv)
    args.hold_map = parse_hold(args.hold)
    return args


def main(argv=None):
    args = parse_args(argv)
    hand = (HandModbus.open_tcp(args.ip, args.port, args.device_id, args.timeout)
            if args.transport == 'tcp' else
            HandModbus.open_serial(args.serial_port, args.baud, args.device_id, args.timeout))
    if hand is None:
        print("ERROR: sin conexión Modbus.", file=sys.stderr)
        return 1
    try:
        return run(hand, args)
    except KeyboardInterrupt:
        print("\n[interrumpido]")
        return 130
    finally:
        try:
            hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
            hand.write_block(ANGLE_SET, open_vector(args.open_angle, args.hold_map))
            time.sleep(0.3)
        except Exception:
            pass
        hand.close()


if __name__ == '__main__':
    raise SystemExit(main())
