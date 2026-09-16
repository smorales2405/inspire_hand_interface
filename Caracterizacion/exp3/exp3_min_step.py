#!/usr/bin/env python3
"""E3.2 — Incremento mínimo efectivo: el cuanto real de comando en contacto.

Mide, con el dedo YA en contacto a una fuerza `F0`, qué le pasa a `POS_ACT` y a
`FORCE_ACT` cuando se pide un incremento de 1, 2, 3, 5 o 10 unidades de
`ANGLE_SET`, cerrando y abriendo. De ahí salen el **incremento mínimo fiable** y
el **cuanto de fuerza** que acota la precisión alcanzable del regulador PI.

Por qué importa el sentido: el retorno revela juego mecánico e histéresis, que es
lo que el PI sufrirá cada vez que tenga que corregir a la baja.

REGISTRO MULTI-DOF. El log continuo guarda `POS_ACT` y `FORCE_ACT` de los SEIS
DOF, no solo del que se mueve. Cuesta lo mismo (el bloque de 6 shorts se lee
entero de todas formas) y con eso E3.6a —¿los ~33 Hz refrescan los 6 DOF en el
mismo frame o escalonados?— sale de este mismo dataset sin banco adicional. En el
repo no existía ninguna serie temporal multi-DOF: todos los CSV de trial guardan
un solo dedo.

SEGURIDAD para carga sostenida (§3 del plan): techo de fuerza, techo de
temperatura, corriente sostenida, **límite duro de POS** que no se cruza pase lo
que pase, y apertura en cualquier salida.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from hand_modbus import (                                    # noqa: E402
    HandModbus, NDOF, ANGLE_SET, FORCE_SET, SPEED_SET,
    POS_ACT, FORCE_ACT, CURRENT,
    DOF_NAMES, fmt_angle, parse_hold, describe_hold,
    angle_vector, open_vector, report_hold,
    load_pos_angle_map, pos_to_angle,
)

FORCE_CLB = 1009   # GESTURE_FORCE_CLB: escribir 1 con la palma abierta tara la fuerza.
                   # Vive en exp2_force_overshoot.py; se repite aquí para no importar
                   # ese módulo entero (arrastra el grid, el modo B y el sub-exp de onset).


# ── lectura ───────────────────────────────────────────────────────────────
class Reader:
    """Lee POS/FORCE/CURRENT y marca qué registros traen valor NUEVO.

    La mano publica estado cada ~30.7 ms se lea a la tasa que se lea (medido en
    `exp2/exp2_results_bifurcacion.md`), así que la mitad de las métricas de
    Exp 3 solo tienen sentido contadas sobre muestras frescas. `fresh_p` /
    `fresh_f` marcan que el bloque cambió respecto a la lectura anterior.
    """

    def __init__(self, hand):
        self.h = hand
        self.prev_p = self.prev_f = None

    def sample(self):
        p = self.h.read_block(POS_ACT)
        f = self.h.read_block(FORCE_ACT)
        c = self.h.read_block(CURRENT)
        fresh_p = p is not None and p != self.prev_p
        fresh_f = f is not None and f != self.prev_f
        if p is not None:
            self.prev_p = p
        if f is not None:
            self.prev_f = f
        return p, f, c, fresh_p, fresh_f


def window(rd, dof, seconds, log, min_fresh=0):
    """Muestrea durante `seconds` y devuelve (mediana de fuerza, mediana de POS,
    nº de lecturas frescas de fuerza, nº frescas de POS, nº de muestras).

    **No espera a que la fuerza cambie.** Esa era la versión anterior y es
    justamente lo que rompe esta prueba: un incremento demasiado pequeño para
    mover el dedo produce CERO cambios de fuerza, que es el resultado que se
    busca — esperar por él agotaba el timeout y devolvía `None`. La frescura se
    cuenta como diagnóstico, no como condición de parada.

    `seconds` debe cubrir varios refrescos de la mano (~30.7 ms cada uno).
    """
    fs, ps, nf, np_, n = [], [], 0, 0, 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < seconds or n < min_fresh:
        p, f, c, fp, ff = rd.sample()
        log(p, f, c, fp, ff)
        n += 1
        if f:
            fs.append(f[dof])
        if p:
            ps.append(p[dof])
        nf += int(ff)
        np_ += int(fp)
        if time.perf_counter() - t0 > seconds * 4:      # tope duro
            break
        time.sleep(0.002)
    return (statistics.median(fs) if fs else None,
            statistics.median(ps) if ps else None, nf, np_, n)


# ── seguridad ─────────────────────────────────────────────────────────────
class Guard:
    """Techo de fuerza, de temperatura, de corriente sostenida y de posición.

    El límite de POS es ABSOLUTO y se comprueba antes de cada escritura: es la
    única protección que no depende de que la fuerza se lea bien.
    """

    def __init__(self, hand, args, pos_limit):
        self.h, self.a, self.pos_limit = hand, args, pos_limit
        self.cur_over = 0
        self.reason = None

    def temp(self):
        t = self.h.read_temps()
        return max(t) if t else None

    def check(self, pos, force, cur):
        if force is not None and abs(force) > self.a.safety_force_g:
            self.reason = f'fuerza {force} g > {self.a.safety_force_g}'
        elif pos is not None and pos > self.pos_limit:
            self.reason = f'POS {pos} > límite duro {self.pos_limit}'
        elif cur is not None and cur > self.a.current_max:
            self.cur_over += 1
            if self.cur_over > self.a.current_hold_n:
                self.reason = f'corriente {cur} mA sostenida'
        else:
            self.cur_over = 0
        return self.reason


# ── establecer contacto ───────────────────────────────────────────────────
def seek_contact(hand, rd, guard, args, log):
    """Cierra a pasos pequeños desde la pre-posición hasta alcanzar `F0`.

    No se deja frenar al firmware en `F0`: `FORCE_SET` se pone POR ENCIMA (como
    respaldo, no como objetivo) y el acercamiento lo hace este lazo. Así el punto
    de operación queda donde lo ponemos nosotros, que es el régimen en el que
    vivirá el regulador — el firmware es un paro de un disparo, no un regulador.
    """
    dof = args.dof
    cmd = args.approach_angle
    hand.write_block(SPEED_SET, [args.close_speed] * NDOF)
    hand.write_block(FORCE_SET, [min(args.f0 + args.fset_margin, 2500)] * NDOF)
    hand.write_block(ANGLE_SET, angle_vector(dof, cmd, args.hold_map))
    time.sleep(0.4)

    t0 = time.perf_counter()
    while time.perf_counter() - t0 < args.seek_timeout:
        fv, pos, _, _, _ = window(rd, dof, args.seek_dwell, log)
        _, _, c, _, _ = rd.sample()
        if guard.check(pos, fv, c[dof] if c else None):
            return None, cmd
        if fv is not None and fv >= args.f0:
            return fv, cmd
        cmd -= args.seek_step
        if cmd < 0:
            guard.reason = 'ANGLE_SET llegó a 0 sin alcanzar F0'
            return None, cmd
        hand.write_block(ANGLE_SET, angle_vector(dof, cmd, args.hold_map))
    guard.reason = 'timeout buscando F0'
    return None, cmd


# ── la medida ─────────────────────────────────────────────────────────────
def run(hand, args):
    dof = args.dof
    os.makedirs(args.outdir, exist_ok=True)
    rd = Reader(hand)

    rows_log = []
    t_start = time.perf_counter()

    def log(p, f, c, fp, ff):
        rows_log.append([f"{time.perf_counter()-t_start:.6f}",
                         int(fp), int(ff),
                         *(p if p else [''] * NDOF),
                         *(f if f else [''] * NDOF),
                         (c[dof] if c else '')])

    print(f"E3.2 · DOF {dof} ({DOF_NAMES[dof]}) · F0 = {args.f0} g · "
          f"pre-posición {fmt_angle(args.approach_angle, dof)}")
    print(f"  límite duro de POS: {args.pos_limit}   techo fuerza {args.safety_force_g} g   "
          f"techo temp {args.temp_max} °C")

    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, open_vector(args.open_angle, args.hold_map))
    time.sleep(0.8)
    report_hold(hand, args.hold_map, 6, 3.0, args.open_speed)

    guard = Guard(hand, args, args.pos_limit)
    t_ini = guard.temp()
    if t_ini is not None and t_ini > args.temp_start_max:
        print(f"ABORTA: el actuador arranca a {t_ini} °C, por encima de "
              f"--temp-start-max {args.temp_start_max}. Deja enfriar la mano.")
        return 2
    print(f"  temperatura inicial: {t_ini} °C")

    if not args.no_cal:
        print("  calibrando (forceClb, palma abierta)...")
        hand.write_block(FORCE_CLB, [1])
        time.sleep(1.5)

    f_now, cmd = seek_contact(hand, rd, guard, args, log)
    if f_now is None:
        print(f"ABORTA estableciendo contacto: {guard.reason}")
        return 3
    p, _, _, _, _ = rd.sample()
    print(f"  contacto establecido: F = {f_now:.0f} g  ·  POS = {p[dof] if p else '—'}  ·  "
          f"comando {fmt_angle(cmd, dof)}")

    steps = [int(x) for x in args.steps.split(',') if x.strip()]
    order = [(s, d, n) for s in steps for d in ('cerrar', 'abrir')
             for n in range(args.trials)]
    random.Random(args.seed).shuffle(order)

    idx_path = os.path.join(args.outdir, f'e32_dof{dof}_F{args.f0}.csv')
    new = not os.path.exists(idx_path)
    with open(idx_path, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['n', 'step_units', 'dir', 'cmd_before', 'cmd_after',
                        'pos_before', 'pos_after', 'dpos',
                        'f_before', 'f_after', 'df',
                        'fresh_before_f/p', 'fresh_after_f/p', 'temp_c', 'aborted'])
        for k, (step, direction, n) in enumerate(order, 1):
            sgn = -1 if direction == 'cerrar' else +1
            f_b, pos_b, nfb, npb, _ = window(rd, dof, args.settle_s, log)
            if guard.check(pos_b, f_b, None):
                print(f"  ABORTA: {guard.reason}"); break

            cmd2 = max(0, min(1000, cmd + sgn * step))
            hand.write_block(ANGLE_SET, angle_vector(dof, cmd2, args.hold_map))
            time.sleep(args.step_dwell)
            f_a, pos_a, nfa, npa, _ = window(rd, dof, args.settle_s, log)
            _, _, c_a, _, _ = rd.sample()
            temp = guard.temp()

            bad = guard.check(pos_a, f_a, c_a[dof] if c_a else None) or \
                (temp is not None and temp > args.temp_max and f"temp {temp} °C")
            w.writerow([n, step, direction, cmd, cmd2, pos_b, pos_a,
                        '' if None in (pos_a, pos_b) else pos_a - pos_b,
                        '' if f_b is None else f"{f_b:.0f}",
                        '' if f_a is None else f"{f_a:.0f}",
                        '' if None in (f_a, f_b) else f"{f_a-f_b:.0f}",
                        f"{nfb}/{npb}", f"{nfa}/{npa}", temp, int(bool(bad))])
            fh.flush()
            print(f"[{k}/{len(order)}] {direction:6s} {step:2d}u → "
                  f"Δpos={'' if None in (pos_a,pos_b) else pos_a-pos_b:>4} "
                  f"ΔF={'' if None in (f_a,f_b) else f'{f_a-f_b:+.0f}':>6} g  "
                  f"(frescas F {nfb}→{nfa}, POS {npb}→{npa}, {temp} °C)"
                  + (f"   ⚠ABORT {bad}" if bad else ''))
            if bad:
                break

            # Volver al punto de operación y dejar que se asiente otra vez.
            hand.write_block(ANGLE_SET, angle_vector(dof, cmd, args.hold_map))
            time.sleep(args.step_dwell)

    log_path = os.path.join(args.outdir, f'e32_dof{dof}_F{args.f0}_log.csv')
    with open(log_path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['t_s', 'fresh_pos', 'fresh_force']
                   + [f'pos{i}' for i in range(NDOF)]
                   + [f'force{i}' for i in range(NDOF)] + ['cur'])
        w.writerows(rows_log)
    print(f"\nÍndice : {idx_path}")
    print(f"Log    : {log_path}  ({len(rows_log)} muestras multi-DOF)")
    print(f"Temperatura final: {guard.temp()} °C")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="E3.2 — incremento mínimo efectivo en contacto.")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='tcp')
    p.add_argument('--ip', default='192.168.124.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)

    p.add_argument('--dof', type=int, required=True)
    p.add_argument('--hold', default='')
    p.add_argument('--f0', type=int, required=True, help='fuerza de operación (g)')
    p.add_argument('--approach-angle', type=int, required=True,
                   help='pre-posición, del sondeo de ese montaje')
    p.add_argument('--pos-limit', type=int, required=True,
                   help='POS máximo ABSOLUTO; no se cruza pase lo que pase')
    p.add_argument('--steps', default='1,2,3,5,10', help='incrementos de ANGLE_SET a probar')
    p.add_argument('--trials', type=int, default=10, help='N por (incremento, sentido)')
    p.add_argument('--seed', type=int, default=0)

    p.add_argument('--close-speed', type=int, default=25)
    p.add_argument('--open-speed', type=int, default=300)
    p.add_argument('--open-angle', type=int, default=1000)
    p.add_argument('--seek-step', type=int, default=2, help='paso de búsqueda de F0 (unidades)')
    p.add_argument('--seek-dwell', type=float, default=0.12)
    p.add_argument('--seek-timeout', type=float, default=60.0)
    p.add_argument('--fset-margin', type=int, default=500,
                   help='FORCE_SET se pone en F0+margen: respaldo del firmware, no objetivo')
    p.add_argument('--step-dwell', type=float, default=0.25,
                   help='espera tras cada escalón (≥ 8 refrescos de 30.7 ms)')
    p.add_argument('--settle-s', type=float, default=0.30,
                   help='ventana de promediado antes y después de cada escalón, s '
                        '(0.30 s ≈ 10 refrescos de la mano)')

    p.add_argument('--safety-force-g', type=int, default=1500)
    p.add_argument('--current-max', type=int, default=700)
    p.add_argument('--current-hold-n', type=int, default=25)
    p.add_argument('--temp-max', type=int, default=55,
                   help='techo de temperatura (def 55; el Exp 2 llegó a 52 con impactos)')
    p.add_argument('--temp-start-max', type=int, default=45,
                   help='no empezar si el actuador ya está por encima')
    p.add_argument('--no-cal', action='store_true')
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        args.hold_map = parse_hold(args.hold)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr); return 2
    hand = (HandModbus.open_tcp(args.ip, args.port, args.device_id, args.timeout)
            if args.transport == 'tcp' else
            HandModbus.open_serial(args.serial_port, args.baud, args.device_id, args.timeout))
    if hand is None:
        print("ERROR: sin conexión Modbus.", file=sys.stderr); return 1
    try:
        return run(hand, args)
    except KeyboardInterrupt:
        print("\n[interrumpido]"); return 130
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
