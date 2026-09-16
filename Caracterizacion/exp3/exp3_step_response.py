#!/usr/bin/env python3
"""E3.3 — Respuesta al escalón de fuerza *en contacto*.

El deadtime de ~64 ms del Exp 1 se midió **en aire**: comando → primer cambio de
`POS_ACT`, con el dedo libre. La planta que el PI regula es otra: comando →
cambio de `FORCE_ACT` **con el dedo ya apoyado**. De aquí sale el modelo de
primer orden con retardo para la sintonía, y el **retardo total del lazo** =
retardo en contacto + hasta un periodo de publicación de la mano (~30.7 ms).

DIFERENCIA DE MUESTREO con E3.1/E3.2. Allí interesaba el valor asentado y se
leían los tres bloques por iteración (~90–215 Hz). Aquí interesa *cuándo* cambia
la fuerza, así que el transitorio se captura leyendo **solo `FORCE_ACT`** a tasa
máxima, con `POS_ACT` cada `--aux-every` iteraciones. La mano publica a ~33 Hz
pase lo que pase, así que leer más rápido no crea información: lo que compra es
resolución sobre el INSTANTE en que aparece el refresco, que es justo lo que mide
un retardo.

Ambos sentidos. E3.2 midió asimetrías de hasta 5× entre cerrar y abrir en el
mismo dedo y punto de operación; no hay razón para suponer que la dinámica sea
simétrica, así que se mide en los dos.

SEGURIDAD idéntica a E3.2: techo de fuerza, de temperatura, de corriente
sostenida, límite duro de POS, y apertura en cualquier salida.
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from hand_modbus import (                                    # noqa: E402
    HandModbus, NDOF, ANGLE_SET, SPEED_SET,
    POS_ACT, FORCE_ACT, CURRENT,
    DOF_NAMES, fmt_angle, parse_hold,
    angle_vector, open_vector, report_hold,
)
from exp3_min_step import (                                  # noqa: E402
    Reader, Guard, seek_contact, wait_arrived, window, FORCE_CLB,
)


# ── captura rápida del transitorio ────────────────────────────────────────
class FastCapture:
    """Lee `FORCE_ACT` cada iteración y `POS_ACT` cada `aux_every`.

    Devuelve la traza cruda: (t, force, pos_or_None, fresh_force). El análisis
    se hace sobre las muestras FRESCAS —las que traen valor nuevo— porque las
    repetidas no aportan instante, solo relleno.
    """

    def __init__(self, hand, dof, aux_every):
        self.h, self.dof, self.aux_every = hand, dof, aux_every
        self.prev_f = None

    def run(self, seconds, t0, guard=None):
        rows = []
        i = 0
        last_pos = None
        while time.perf_counter() - t0 < seconds:
            f = self.h.read_block(FORCE_ACT)
            t = time.perf_counter() - t0
            fresh = f is not None and f != self.prev_f
            if f is not None:
                self.prev_f = f
            if i % self.aux_every == 0:
                p = self.h.read_block(POS_ACT)
                if p is not None:
                    last_pos = p[self.dof]
            rows.append((t, f[self.dof] if f else None, last_pos, int(fresh)))
            i += 1
        return rows


# ── métricas ──────────────────────────────────────────────────────────────
def analyse(base_rows, rows, thr_g, settle_frac, settle_hold, tail_s):
    """Del transitorio saca retardo, constante de subida, asentamiento y deriva.

    `base_rows` es la línea base tomada ANTES del comando, con el dedo quieto en
    el punto de operación: de ahí salen el valor de partida y el ruido, y el
    umbral de detección es `max(thr_g, 4·sigma)` para no llamar «respuesta» a la
    cuantización de la celda.
    """
    bf = [r[1] for r in base_rows if r[3] and r[1] is not None]
    if len(bf) < 3:
        return None
    f_base = statistics.median(bf)
    sigma = statistics.pstdev(bf) if len(bf) > 2 else 0.0
    thr = max(thr_g, 4 * sigma)

    fresh = [(t, f, p) for t, f, p, fr in rows if fr and f is not None]
    if len(fresh) < 5:
        return None

    tail = [f for t, f, _ in fresh if t >= fresh[-1][0] - tail_s]
    f_inf = statistics.median(tail) if tail else fresh[-1][1]
    amp = f_inf - f_base

    # retardo: primera muestra FRESCA que se separa del reposo más que el umbral
    t_onset = n_onset = None
    for k, (t, f, _) in enumerate(fresh):
        if abs(f - f_base) > thr:
            t_onset, n_onset = t, k
            break
    if t_onset is None:
        return dict(f_base=f_base, sigma=sigma, thr=thr, f_inf=f_inf, amp=amp,
                    t_onset=None, n_onset=None, tau=None, t28=None, t63=None,
                    tau_s=None, lag_s=None, t_settle=None,
                    f_peak=None, overshoot=None, drift=None, n_fresh=len(fresh))

    # cruces de fracción de la amplitud, medidos desde el COMANDO (t=0)
    def crossing(frac):
        target = f_base + frac * amp
        for t, f, _ in fresh:
            if (amp > 0 and f >= target) or (amp < 0 and f <= target):
                return t
        return None

    t28 = t63 = None
    tau = tau_s = lag_s = None
    if abs(amp) > thr:
        t28, t63 = crossing(0.283), crossing(0.632)
        if t63 is not None:
            tau = t63 - t_onset          # subida vista desde el umbral
        if t28 is not None and t63 is not None and t63 > t28:
            # dos puntos (Smith): insensible a dónde se ponga el umbral de detección,
            # que es lo que sesga `tau` — el umbral llega tarde y la acorta.
            tau_s = 1.5 * (t63 - t28)
            lag_s = max(0.0, t63 - tau_s)

    # asentamiento: primera vez que se queda dentro de la banda y no vuelve a salir
    t_settle = None
    band = max(thr, abs(amp) * settle_frac)
    for k, (t, f, _) in enumerate(fresh):
        if abs(f - f_inf) > band:
            continue
        # se exige que AGUANTE dentro de la banda `settle_hold` segundos
        if all(abs(f2 - f_inf) <= band
               for t2, f2, _p in fresh[k:] if t2 - t <= settle_hold):
            t_settle = t
            break

    f_peak = max((f for _, f, _ in fresh), key=lambda v: abs(v - f_base))
    overshoot = f_peak - f_inf

    # deriva: pendiente de la cola, en g/s. Dice si asienta o sigue caminando.
    tl = [(t, f) for t, f, _ in fresh if t >= fresh[-1][0] - tail_s]
    drift = None
    if len(tl) >= 4:
        mt = statistics.mean(t for t, _ in tl)
        mf = statistics.mean(f for _, f in tl)
        den = sum((t - mt) ** 2 for t, _ in tl)
        if den > 0:
            drift = sum((t - mt) * (f - mf) for t, f in tl) / den

    return dict(f_base=f_base, sigma=sigma, thr=thr, f_inf=f_inf, amp=amp,
                t_onset=t_onset, n_onset=n_onset, tau=tau, t28=t28, t63=t63,
                tau_s=tau_s, lag_s=lag_s, t_settle=t_settle,
                f_peak=f_peak, overshoot=overshoot, drift=drift,
                n_fresh=len(fresh))


# ── la medida ─────────────────────────────────────────────────────────────
def run(hand, args):
    dof = args.dof
    os.makedirs(args.outdir, exist_ok=True)
    rd = Reader(hand)
    cap = FastCapture(hand, dof, args.aux_every)

    rows_log = []
    t_start = time.perf_counter()

    def log(p, f, c, fp, ff):
        rows_log.append([f"{time.perf_counter()-t_start:.6f}", int(fp), int(ff),
                         *(p if p else [''] * NDOF), *(f if f else [''] * NDOF),
                         (c[dof] if c else '')])

    print(f"E3.3 · DOF {dof} ({DOF_NAMES[dof]}) · F0 = {args.f0} g · "
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
    print(f"  captura: {args.capture_s} s por escalón, "
          f"FORCE cada iteración y POS cada {args.aux_every}\n")

    steps = [int(x) for x in args.steps.split(',') if x.strip()]
    order = [(s, d, n) for s in steps for d in ('cerrar', 'abrir')
             for n in range(args.trials)]
    random.Random(args.seed).shuffle(order)

    idx_path = os.path.join(args.outdir, f'e33_dof{dof}_F{args.f0}.csv')
    trc_path = os.path.join(args.outdir, f'e33_dof{dof}_F{args.f0}_traces.csv')
    new = not os.path.exists(idx_path)
    ftr = open(trc_path, 'w', newline='')
    wtr = csv.writer(ftr)
    wtr.writerow(['trial', 'step_units', 'dir', 'phase', 't_s', 'force_g',
                  'pos_act', 'fresh_force'])

    with open(idx_path, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['n', 'step_units', 'dir', 'cmd_before', 'cmd_after',
                        'f_base', 'sigma_g', 'thr_g', 'f_inf', 'amp_g',
                        't_onset_ms', 'n_fresh_onset', 'tau_ms',
                        't28_ms', 't63_ms', 'lag_smith_ms', 'tau_smith_ms',
                        't_settle_ms',
                        'f_peak', 'overshoot_g', 'drift_g_s', 'n_fresh',
                        'pos_before', 'pos_after', 'temp_c', 'aborted'])
        for k, (step, direction, n) in enumerate(order, 1):
            sgn = -1 if direction == 'cerrar' else +1

            # asentar en el punto de operación
            _, pos_b, _, _, _ = window(rd, dof, args.settle_s, log)
            if guard.check(pos_b, None, None):
                print(f"  ABORTA: {guard.reason}")
                break

            # línea base a tasa alta, con el dedo quieto
            t0 = time.perf_counter()
            base_rows = cap.run(args.base_s, t0)

            # EL ESCALÓN. t_cmd es el instante inmediatamente anterior a la escritura.
            cmd2 = max(0, min(1000, cmd + sgn * step))
            t_cmd = time.perf_counter()
            hand.write_block(ANGLE_SET, angle_vector(dof, cmd2, args.hold_map))
            rows = cap.run(args.capture_s, t_cmd)

            m = analyse(base_rows, rows, args.onset_thr_g, args.settle_frac,
                        args.settle_hold, args.tail_s)

            pa = [r[2] for r in rows if r[2] is not None]
            pos_a = pa[-1] if pa else None
            _, _, c_a, _, _ = rd.sample()
            temp = guard.temp()
            f_end = rows[-1][1] if rows and rows[-1][1] is not None else None
            bad = guard.check(pos_a, f_end, c_a[dof] if c_a else None) or \
                (temp is not None and temp > args.temp_max and f"temp {temp} °C")

            for ph, rr in (('base', base_rows), ('step', rows)):
                for t, f, pp, fr in rr:
                    wtr.writerow([n, step, direction, ph, f"{t:.6f}",
                                  '' if f is None else f, '' if pp is None else pp, fr])
            ftr.flush()

            def ms(v):
                return '' if v is None else f"{v*1000:.1f}"

            if m is None:
                w.writerow([n, step, direction, cmd, cmd2] + [''] * 17 +
                           [pos_b, pos_a, temp, 1])
                print(f"[{k}/{len(order)}] {direction:6s} {step:2d}u → sin muestras frescas suficientes")
            else:
                w.writerow([n, step, direction, cmd, cmd2,
                            f"{m['f_base']:.0f}", f"{m['sigma']:.1f}", f"{m['thr']:.0f}",
                            f"{m['f_inf']:.0f}", f"{m['amp']:.0f}",
                            ms(m['t_onset']), m['n_onset'], ms(m['tau']),
                            ms(m['t28']), ms(m['t63']),
                            ms(m['lag_s']), ms(m['tau_s']),
                            ms(m['t_settle']),
                            '' if m['f_peak'] is None else f"{m['f_peak']:.0f}",
                            '' if m['overshoot'] is None else f"{m['overshoot']:.0f}",
                            '' if m['drift'] is None else f"{m['drift']:.1f}",
                            m['n_fresh'], pos_b, pos_a, temp, int(bool(bad))])
                drift_s = '—' if m['drift'] is None else f"{m['drift']:+.1f}"
                print(f"[{k}/{len(order)}] {direction:6s} {step:2d}u → "
                      f"ΔF={m['amp']:+6.0f} g  retardo={ms(m['t_onset']) or '—':>6} ms  "
                      f"L={ms(m['lag_s']) or '—':>6} τ={ms(m['tau_s']) or '—':>6} ms  "
                      f"asienta={ms(m['t_settle']) or '—':>6} ms  "
                      f"deriva={drift_s:>6} g/s  "
                      f"({temp} °C)" + (f"   ⚠ABORT {bad}" if bad else ''))
            fh.flush()
            if bad:
                break

            # volver al punto de operación
            hand.write_block(ANGLE_SET, angle_vector(dof, cmd, args.hold_map))
            time.sleep(args.step_dwell)
            wait_arrived(rd, dof, log)

    ftr.close()
    log_path = os.path.join(args.outdir, f'e33_dof{dof}_F{args.f0}_log.csv')
    with open(log_path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['t_s', 'fresh_pos', 'fresh_force']
                   + [f'pos{i}' for i in range(NDOF)]
                   + [f'force{i}' for i in range(NDOF)] + ['cur'])
        w.writerows(rows_log)
    print(f"\nÍndice : {idx_path}")
    print(f"Trazas : {trc_path}")
    print(f"Log    : {log_path}  ({len(rows_log)} muestras multi-DOF)")
    print(f"Temperatura final: {guard.temp()} °C")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="E3.3 — respuesta al escalón de fuerza en contacto.")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='tcp')
    p.add_argument('--ip', default='192.168.124.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)

    p.add_argument('--dof', type=int, required=True)
    p.add_argument('--hold', default='')
    p.add_argument('--f0', type=int, default=250, help='fuerza del punto de operación (g)')
    p.add_argument('--approach-angle', type=int, required=True)
    p.add_argument('--pos-limit', type=int, required=True)
    p.add_argument('--steps', default='7,15', help='escalones en unidades de comando')
    p.add_argument('--trials', type=int, default=10)
    p.add_argument('--seed', type=int, default=33)

    p.add_argument('--capture-s', type=float, default=2.0, help='ventana del transitorio')
    p.add_argument('--base-s', type=float, default=0.6, help='línea base antes del escalón')
    p.add_argument('--aux-every', type=int, default=12, help='cada cuántas lecturas de FORCE se lee POS')
    p.add_argument('--onset-thr-g', type=float, default=15.0, help='umbral mínimo de detección')
    p.add_argument('--settle-frac', type=float, default=0.05)
    p.add_argument('--settle-hold', type=float, default=0.30)
    p.add_argument('--tail-s', type=float, default=0.50, help='cola para f_inf y deriva')

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
    p.add_argument('--current-hold-n', type=int, default=25)
    p.add_argument('--temp-max', type=int, default=55)
    p.add_argument('--temp-start-max', type=int, default=45)
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
