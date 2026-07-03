#!/usr/bin/env python3
"""Experimento 2 — Sobreimpulso de fuerza en contacto (Inspire RH56DFTP).

Sigue characterization/PROTOCOL_Dynamic_Characterization_RH56DFTP.md (Exp 2):
el índice cierra contra un bloque rígido fijo y se mide el sobreimpulso de
fuerza ΔF = F_max − Fset. Este archivo implementa por ahora SOLO el modo de
validación previa `--probe`; el grid (modos A/B × v × Fset) se añade después,
calibrado con los resultados del sondeo.

Adaptación clave del Exp 1: `FORCE_ACT` tiene un offset dependiente de la
flexión (~216→330 g sin contacto). Por eso:
  - El sondeo caracteriza la curva libre F(POS_ACT) y localiza el POS de contacto.
  - La detección de contacto en tiempo real usa el STALL de POS_ACT (el dedo
    deja de avanzar al tocar el bloque) — robusto frente al offset de fuerza.
  - `FORCE_SET` se pone alto (800 g > offset máximo) para que el firmware NO
    frene en espacio libre: así cualquier stall es contacto real.

Standalone (no PyQt), un proceso/hilo/cliente, lazo intercalado. Al salir
(contacto, techo, corriente, timeout, Ctrl-C) abre todos los dedos.

⚠ Requiere el bloque rígido montado y fijo. Corre SIEMPRE el sondeo antes del
grid. Presión mínima por diseño (abre al detectar contacto).

    .venv/bin/python characterization/exp2_force_overshoot.py \
        --transport serial --serial-port /dev/ttyUSB0 --probe
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import statistics
import sys
import time

# hand_modbus vive en Caracterizacion/ (un nivel arriba): importable desde cualquier cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from hand_modbus import (
    HandModbus, NDOF, ANGLE_SET, FORCE_SET, SPEED_SET,
    POS_ACT, ANGLE_ACT, FORCE_ACT, CURRENT,
)

# Lectura de bloque ancho: POS_ACT(1534)…CURRENT(1599) en una sola transacción.
WIDE_ADDR = POS_ACT                 # 1534
WIDE_COUNT = CURRENT - POS_ACT + NDOF        # 1594-1534+6 = 66
OFF_POS = 0
OFF_FORCE = FORCE_ACT - POS_ACT     # 48
OFF_CUR = CURRENT - POS_ACT         # 60

FORCE_CLB = 1009                    # GESTURE_FORCE_CLB: escribir 1 (palma abierta) tara la fuerza


def angle_vector(dof, value):
    v = [-1] * NDOF
    v[dof] = value
    return v


def open_and_settle(hand, dof, open_angle, band, timeout_s, open_speed=1000):
    hand.write_block(SPEED_SET, [open_speed] * NDOF)
    hand.write_block(ANGLE_SET, angle_vector(dof, open_angle))
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        a = hand.read_block(ANGLE_ACT)
        if a is not None and abs(a[dof] - open_angle) <= band:
            time.sleep(0.05)
            return True
        time.sleep(0.02)
    return False


def read_signals(hand, dof, wide_ok):
    """(pos, force, current) para `dof`, por bloque ancho si funciona."""
    if wide_ok:
        w = hand.read_block(WIDE_ADDR, WIDE_COUNT)
        if w is None:
            return None, None, None
        return w[OFF_POS + dof], w[OFF_FORCE + dof], w[OFF_CUR + dof]
    pb = hand.read_block(POS_ACT); fb = hand.read_block(FORCE_ACT); cb = hand.read_block(CURRENT)
    return (pb[dof] if pb else None, fb[dof] if fb else None, cb[dof] if cb else None)


# ── Calibración de fuerza (forceClb) — diagnóstico ──────────────────────────

def run_zero(hand, args):
    dof = args.dof
    print("Calibración de fuerza (forceClb, reg 1009). Requiere palma ABIERTA sin tocar nada.")
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
    time.sleep(0.8)
    open_and_settle(hand, dof, args.open_angle, args.settle_band, args.settle_timeout_s, args.open_speed)

    def rest_force(n=10):
        vals = []
        for _ in range(n):
            fb = hand.read_block(FORCE_ACT)
            if fb is not None:
                vals.append(fb[dof])
            time.sleep(0.02)
        return statistics.fmean(vals) if vals else None

    f_before = rest_force()
    print(f" FORCE_ACT en reposo (antes):  {f_before:.0f} g")
    print(" Escribiendo forceClb=1 ...")
    hand.write_block(FORCE_CLB, [1])
    time.sleep(2.0)
    f_after = rest_force()
    print(f" FORCE_ACT en reposo (después): {f_after:.0f} g   "
          f"(offset removido: {f_before - f_after:+.0f} g)")

    # Flexión libre conservadora (antes del bloque) → offset residual por flexión.
    ang = args.zero_flex_angle
    print(f" Flexionando libre a ANGLE_SET={ang} (antes del bloque) para el residual por flexión...")
    hand.write_block(SPEED_SET, [150] * NDOF)
    hand.write_block(FORCE_SET, [args.probe_fset] * NDOF)
    hand.write_block(ANGLE_SET, angle_vector(dof, ang))
    t0 = time.perf_counter()
    last_pos = None; stable_t = t0; p = f = None
    while time.perf_counter() - t0 < 6.0:
        pb = hand.read_block(POS_ACT); fb = hand.read_block(FORCE_ACT)
        p = pb[dof] if pb else p
        f = fb[dof] if fb else f
        if f is not None and abs(f) > args.probe_ceiling:
            print(" ⚠ fuerza alta (¿contacto?). Abro y corto la flexión.")
            break
        if p is not None:
            if last_pos is None or abs(p - last_pos) > 6:
                last_pos, stable_t = p, time.perf_counter()
            elif time.perf_counter() - stable_t > 0.4:
                break                                   # asentó
        time.sleep(0.01)
    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle))
    if p is not None and f is not None:
        print(f" A POS≈{p} (flexionado, libre): FORCE_ACT={f} g   "
              f"(residual por flexión vs reposo calibrado: {f - (f_after or 0):+.0f} g)")
    print("\n Interpretación: si el reposo calibrado ≈0 y el residual por flexión es pequeño,")
    print(" FORCE_SET/FORCE_ACT ≈ fuerza externa y el grid del protocolo (Fset 100..1000) es directo.")
    print(" Si el residual por flexión sigue grande, restaremos la curva libre F(POS) igual.")


# ── Sondeo de contacto ──────────────────────────────────────────────────────

def run_probe(hand, args):
    dof = args.dof
    print(f"Abriendo todos los dedos (DOF de sondeo: {dof})...")
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
    time.sleep(0.6)
    open_and_settle(hand, dof, args.open_angle, args.settle_band, args.settle_timeout_s, args.open_speed)

    # 1) Test de lectura ancha + cross-check contra lecturas separadas (en reposo).
    w = hand.read_block(WIDE_ADDR, WIDE_COUNT)
    pb = hand.read_block(POS_ACT); fb = hand.read_block(FORCE_ACT); cb = hand.read_block(CURRENT)
    wide_ok = False
    if w is not None and pb and fb and cb:
        wide_ok = (w[OFF_POS + dof] == pb[dof] and
                   w[OFF_FORCE + dof] == fb[dof] and
                   w[OFF_CUR + dof] == cb[dof])
    f_open = fb[dof] if fb else None
    p_open = pb[dof] if pb else None
    print(f"Bloque ancho (1 transacción POS+FORCE+CURRENT): "
          f"{'OK — coincide con lecturas separadas' if wide_ok else 'NO usable → uso lecturas separadas'}")
    print(f"En reposo: POS={p_open}  FORCE_ACT={f_open} g (offset)  → cierro lento contra el bloque...")

    # 2) Cierre lento e instrumentado.
    hand.write_block(SPEED_SET, [args.probe_speed] * NDOF)
    hand.write_block(FORCE_SET, [args.probe_fset] * NDOF)

    samples = []                 # (t, pos, force, cur)
    start_pos = p_open if p_open is not None else 0
    ref_pos = ref_t = None
    hi_cur = 0
    max_force = f_open or 0
    contact_pos = None
    reason = 'timeout'
    cur_over = 0

    t_start = time.perf_counter()
    tb = time.perf_counter()
    hand.write_block(ANGLE_SET, angle_vector(dof, 0))     # cerrar
    t_cmd = time.perf_counter()

    while True:
        t = time.perf_counter()
        elapsed = t - t_start
        pos, force, cur = read_signals(hand, dof, wide_ok)
        samples.append((elapsed, pos, force, cur))
        if force is not None:
            max_force = max(max_force, abs(force))
        if cur is not None:
            hi_cur = max(hi_cur, cur)

        # Seguridad 1: techo crudo de fuerza.
        if force is not None and abs(force) > args.probe_ceiling:
            reason = 'techo_fuerza'; break
        # Seguridad 2: watchdog de corriente (sostenida alta = bloqueo).
        if cur is not None and cur > args.current_max:
            cur_over += 1
            if cur_over >= 3:
                reason = 'corriente'; break
        else:
            cur_over = 0

        # Detección de contacto por STALL de POS (dejó de avanzar al tocar).
        if pos is not None:
            if ref_pos is None or abs(pos - ref_pos) > args.stall_band:
                ref_pos, ref_t = pos, t
            elif ((t - ref_t) >= args.stall_hold
                  and elapsed >= (t_cmd - t_start) + 0.3
                  and (pos - start_pos) > 50):
                contact_pos = pos
                reason = 'contacto'; break

        if elapsed >= args.probe_window:
            break

    # Abrir siempre.
    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle))

    # Si una salvaguarda cortó justo en el contacto (POS ya detenido), inferir
    # el POS de contacto del tramo final.
    if contact_pos is None and len(samples) >= 5:
        tail = [p for (_, p, _, _) in samples[-8:] if p is not None]
        if tail and (max(tail) - min(tail)) <= args.stall_band * 2 and (tail[-1] - start_pos) > 50:
            contact_pos = tail[-1]

    # 3) Guardar + reportar.
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, f'probe_dof{dof}.csv')
    with open(path, 'w', newline='') as fp:
        wtr = csv.writer(fp)
        wtr.writerow(['t_s', 'pos_act', 'force_g', 'current_mA'])
        for (t, p, f, c) in samples:
            wtr.writerow([f'{t:.6f}', '' if p is None else p,
                          '' if f is None else f, '' if c is None else c])

    forces = [f for (_, _, f, _) in samples if f is not None]
    f_contact = forces[-1] if forces else None
    print("\n=== Exp 2 — sondeo de contacto ===")
    print(f" Motivo de parada : {reason}")
    if contact_pos is not None:
        note = '  (¡ojo! cerca de cierre completo — ¿bloque fuera de alcance?)' if contact_pos > 1700 else ''
        src = '' if reason == 'contacto' else f'  (inferido del punto de parada por {reason})'
        print(f" POS de contacto  : {contact_pos}{note}{src}")
        print(f"   → úsalo como ángulo de aproximación del modo B (híbrido)")
    else:
        print(" POS de contacto  : no detectado (no hubo stall; revisa montaje/alcance)")
    print(f" Fuerza al parar  : {f_contact} g   (offset en reposo: {f_open} g "
          f"→ contacto externo aprox: {f_contact - f_open if (f_contact is not None and f_open is not None) else '—'} g)")
    print(f" Fuerza máx cruda : {max_force} g   (techo era {args.probe_ceiling} g)")
    print(f" Corriente máx    : {hi_cur} mA")
    print(f" Muestras         : {len(samples)}  ({len(samples)/max(samples[-1][0],1e-9):.0f} Hz)  "
          f"lectura: {'ancha' if wide_ok else 'separada'}")
    print(f" CSV              : {path}")
    if reason == 'contacto':
        print(" ✔ Contacto detectado por stall y dedo abierto. Mándame el CSV y "
              "caracterizo la curva libre F(POS) + onset para diseñar el grid.")
    elif reason == 'techo_fuerza':
        print(" ⚠ Se llegó al techo de fuerza antes del stall: baja --probe-speed "
              "o revisa que el bloque frene el dedo.")


# ── Grid modo A: una celda (v, Fset) ────────────────────────────────────────

def calibrate(hand, args):
    """forceClb con la palma abierta (fuerza ≈ externa tras esto)."""
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
    time.sleep(0.6)
    open_and_settle(hand, args.dof, args.open_angle, args.settle_band, args.settle_timeout_s, args.open_speed)
    hand.write_block(FORCE_CLB, [1])
    time.sleep(1.5)


def run_trial_A(hand, dof, speed, fset, args):
    """Modo A: dedo ya pre-posicionado antes del contacto → cierra a `speed`,
    firmware frena en `fset`. Muestrea FORCE_ACT a alta tasa (pico) + POS/CURRENT
    periódicos. Devuelve series y métricas."""
    hand.write_block(SPEED_SET, [speed] * NDOF)
    hand.write_block(FORCE_SET, [fset] * NDOF)

    samples = []                 # (t, force, pos|None, cur|None)
    f_max = None; peak_t = None; onset_pos = None
    aborted = False; cur_over = 0
    ref_pos = None; ref_t = None                 # seguimiento del plateau de POS
    pb0 = hand.read_block(POS_ACT)
    start_pos = pb0[dof] if pb0 else 0
    last_pos = start_pos
    i = 0
    t_start = time.perf_counter()
    hand.write_block(ANGLE_SET, angle_vector(dof, 0))          # cerrar contra el bloque
    t_cmd = time.perf_counter()

    while True:
        t = time.perf_counter(); elapsed = t - t_start
        fb = hand.read_block(FORCE_ACT)
        force = fb[dof] if fb else None
        pos = cur = None
        if i % args.aux_every == 0:
            pb = hand.read_block(POS_ACT); pos = pb[dof] if pb else None
            cb = hand.read_block(CURRENT); cur = cb[dof] if cb else None
            if pos is not None:
                last_pos = pos
            if cur is not None and cur > args.current_max:
                cur_over += 1
                if cur_over >= 3:
                    aborted = True; break
            else:
                cur_over = 0
            # Fin del trial: el dedo se DETUVO (plateau de POS) tras avanzar al
            # contacto → el firmware sostiene en Fset. Un transitorio de
            # movimiento no detiene el POS, así que no dispara un fin falso.
            if pos is not None:
                if ref_pos is None or abs(pos - ref_pos) > args.stall_band:
                    ref_pos, ref_t = pos, t
                elif ((t - ref_t) >= args.settle_hold
                      and (pos - start_pos) > args.contact_min_travel
                      and elapsed >= (t_cmd - t_start) + 0.3):
                    samples.append((elapsed, force, pos, cur)); break
        if force is not None:
            if f_max is None or force > f_max:
                f_max = force; peak_t = t
            if (onset_pos is None and force > args.onset_thr
                    and (last_pos - start_pos) > 50):
                onset_pos = last_pos
            if abs(force) > args.safety_force_g:
                aborted = True
                samples.append((elapsed, force, pos, cur)); break
        samples.append((elapsed, force, pos, cur))
        i += 1
        if elapsed >= args.trial_window:
            break

    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle))   # abrir

    forces = [f for (_, f, _, _) in samples if f is not None]
    tail = [f for (tt, f, _, _) in samples if f is not None and tt >= samples[-1][0] - 0.3]
    f_settle = statistics.fmean(tail) if tail else None
    return {
        'samples': samples, 'speed': speed, 'fset': fset,
        'f_max': f_max, 'delta_f': (f_max - fset) if f_max is not None else None,
        'f_settle': f_settle, 't_peak_ms': (peak_t - t_cmd) * 1000 if peak_t else None,
        'onset_pos': onset_pos, 'aborted': aborted,
    }


def save_cell_csv(path, trial):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['t_s', 'force_g', 'pos_act', 'current_mA'])
        for (t, force, pos, cur) in trial['samples']:
            w.writerow([f'{t:.6f}', '' if force is None else force,
                        '' if pos is None else pos, '' if cur is None else cur])


def run_cell(hand, args):
    dof = args.dof
    if not args.no_cal:
        print("Calibrando fuerza (forceClb, palma abierta)...")
        calibrate(hand, args)
    print(f"Pre-posicionando a ANGLE_SET={args.start_angle} (justo antes del contacto)...")
    open_and_settle(hand, dof, args.start_angle, args.settle_band, args.settle_timeout_s, args.approach_speed)

    trial = run_trial_A(hand, dof, args.speed, args.fset, args)
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, f'cell_dof{dof}_v{args.speed}_F{args.fset}.csv')
    save_cell_csv(path, trial)

    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle))
    n = len(trial['samples']); rate = n / max(trial['samples'][-1][0], 1e-9)
    print("\n=== Exp 2 — celda única (modo A, validación) ===")
    print(f" DOF={dof}  v={args.speed}  Fset={args.fset} g")
    print(f" F_max = {trial['f_max']} g   ΔF (sobreimpulso) = {trial['delta_f']} g")
    print(f" F_régimen = {trial['f_settle']:.0f} g   t_hasta_pico = "
          f"{trial['t_peak_ms']:.0f} ms" if trial['f_settle'] is not None else " F_régimen = —")
    print(f" onset de contacto en POS = {trial['onset_pos']}")
    print(f" Muestras: {n}  ({rate:.0f} Hz)   {'⚠ ABORTADO' if trial['aborted'] else ''}")
    print(f" CSV: {path}")


# ── Grid modo A: campaña ─────────────────────────────────────────────────────

def run_grid(hand, args):
    dof = args.dof
    os.makedirs(args.outdir, exist_ok=True)
    speeds = [int(x) for x in args.speeds.split(',') if x.strip()]
    fsets = [int(x) for x in args.fsets.split(',') if x.strip()]
    order = [(v, F, n) for v in speeds for F in fsets for n in range(args.trials)]
    random.Random(args.seed).shuffle(order)
    total = len(order)
    print(f"Grid modo A: {len(speeds)} v × {len(fsets)} Fset × {args.trials} = "
          f"{total} trials (orden aleatorio).")

    if not args.no_cal:
        print("Calibrando fuerza (forceClb, palma abierta)...")
        calibrate(hand, args)

    index_path = os.path.join(args.outdir, 'grid_index.csv')
    new_index = not os.path.exists(index_path)
    with open(index_path, 'a', newline='') as idx:
        iw = csv.writer(idx)
        if new_index:
            iw.writerow(['trial_file', 'dof', 'speed', 'fset', 'f_max', 'delta_f',
                         'f_settle', 't_peak_ms', 'onset_pos', 'rate_hz', 'aborted'])
        for k, (v, F, n) in enumerate(order, 1):
            # Recalibración periódica (con el dedo abierto) por la deriva del sensor.
            if not args.no_cal and args.recal_every > 0 and k > 1 and (k - 1) % args.recal_every == 0:
                print("  · recalibrando forceClb ...")
                calibrate(hand, args)
            open_and_settle(hand, dof, args.start_angle, args.settle_band,
                            args.settle_timeout_s, args.approach_speed)
            trial = run_trial_A(hand, dof, v, F, args)
            fname = f"A_dof{dof}_v{v}_F{F}_n{n:02d}.csv"
            save_cell_csv(os.path.join(args.outdir, fname), trial)
            n_s = len(trial['samples'])
            rate = n_s / max(trial['samples'][-1][0], 1e-9) if n_s else 0
            iw.writerow([fname, dof, v, F, trial['f_max'], trial['delta_f'],
                         f"{trial['f_settle']:.0f}" if trial['f_settle'] is not None else '',
                         f"{trial['t_peak_ms']:.0f}" if trial['t_peak_ms'] is not None else '',
                         trial['onset_pos'], f"{rate:.0f}", int(trial['aborted'])])
            idx.flush()
            flag = '  ⚠ABORT' if trial['aborted'] else ''
            print(f"[{k}/{total}] v={v:4d} Fset={F:4d} n={n} → "
                  f"F_max={trial['f_max']} g  ΔF={trial['delta_f']} g{flag}")

    hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
    print(f"\nListo: {total} trials en {args.outdir}/  (series + grid_index.csv).")


# ── Modo B: híbrido (aproximación rápida + cierre lento) ─────────────────────

def run_hybrid(hand, args):
    """Modo B del protocolo: aproxima RÁPIDO hasta justo antes del contacto,
    luego cierra LENTO (hybrid_speed). Debería colapsar el sobreimpulso al nivel
    de v=25. Barre Fset. Reutiliza run_trial_A (la aproximación cercana + baja
    velocidad hacen el resto)."""
    dof = args.dof
    os.makedirs(args.outdir, exist_ok=True)
    fsets = [int(x) for x in args.fsets.split(',') if x.strip()]
    order = [(F, n) for F in fsets for n in range(args.trials)]
    random.Random(args.seed).shuffle(order)
    total = len(order)
    print(f"Modo B (híbrido): aproximación rápida a ANGLE_SET={args.approach_angle}, "
          f"luego cierre a v={args.hybrid_speed}.  {len(fsets)} Fset × {args.trials} = {total} trials.")

    if not args.no_cal:
        print("Calibrando fuerza (forceClb)...")
        calibrate(hand, args)

    index_path = os.path.join(args.outdir, 'grid_index.csv')
    new_index = not os.path.exists(index_path)
    with open(index_path, 'a', newline='') as idx:
        iw = csv.writer(idx)
        if new_index:
            iw.writerow(['trial_file', 'dof', 'speed', 'fset', 'f_max', 'delta_f',
                         'f_settle', 't_peak_ms', 'onset_pos', 'rate_hz', 'aborted'])
        for k, (F, n) in enumerate(order, 1):
            if not args.no_cal and args.recal_every > 0 and k > 1 and (k - 1) % args.recal_every == 0:
                print("  · recalibrando forceClb ...")
                calibrate(hand, args)
            # Aproximación RÁPIDA (open_speed) hasta justo antes del contacto.
            open_and_settle(hand, dof, args.approach_angle, args.settle_band,
                            args.settle_timeout_s, args.open_speed)
            trial = run_trial_A(hand, dof, args.hybrid_speed, F, args)   # cierre lento
            fname = f"B_dof{dof}_v{args.hybrid_speed}_F{F}_n{n:02d}.csv"
            save_cell_csv(os.path.join(args.outdir, fname), trial)
            n_s = len(trial['samples'])
            rate = n_s / max(trial['samples'][-1][0], 1e-9) if n_s else 0
            iw.writerow([fname, dof, args.hybrid_speed, F, trial['f_max'], trial['delta_f'],
                         f"{trial['f_settle']:.0f}" if trial['f_settle'] is not None else '',
                         f"{trial['t_peak_ms']:.0f}" if trial['t_peak_ms'] is not None else '',
                         trial['onset_pos'], f"{rate:.0f}", int(trial['aborted'])])
            idx.flush()
            flag = '  ⚠ABORT' if trial['aborted'] else ''
            print(f"[{k}/{total}] Fset={F:4d} n={n} → F_max={trial['f_max']} g  ΔF={trial['delta_f']} g{flag}")

    hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
    print(f"\nListo: {total} trials (modo B) en {args.outdir}/.")


# ── CLI ─────────────────────────────────────────────────────────────────────

def connect(args):
    if args.transport == 'tcp':
        return HandModbus.open_tcp(args.ip, args.port, args.device_id, args.timeout)
    return HandModbus.open_serial(args.serial_port, args.baud, args.device_id, args.timeout)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Exp 2 — sobreimpulso de fuerza en contacto (sondeo).")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='serial')
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--ip', default='192.168.11.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    p.add_argument('--dof', type=int, default=3)
    p.add_argument('--open-angle', type=int, default=1000)
    p.add_argument('--open-speed', type=int, default=1000)
    p.add_argument('--settle-band', type=int, default=6)
    p.add_argument('--settle-timeout-s', type=float, default=3.0)
    # calibración
    p.add_argument('--zero', action='store_true', help='diagnóstico de calibración de fuerza (forceClb)')
    p.add_argument('--zero-flex-angle', type=int, default=650,
                   help='ANGLE_SET (antes del bloque) para medir el residual por flexión (def 650)')
    # sondeo
    p.add_argument('--probe', action='store_true', help='corre el sondeo de contacto')
    p.add_argument('--probe-speed', type=int, default=50, help='SPEED_SET del cierre lento (def 50)')
    p.add_argument('--probe-fset', type=int, default=400,
                   help='FORCE_SET del sondeo: el firmware frena suave en contacto (crudo; def 400)')
    p.add_argument('--probe-ceiling', type=int, default=550,
                   help='techo |FORCE_ACT| crudo de emergencia (g, def 550)')
    p.add_argument('--current-max', type=int, default=1200, help='corriente máx antes de abortar (mA)')
    p.add_argument('--stall-band', type=int, default=8, help='avance de POS bajo el cual se considera detenido')
    p.add_argument('--stall-hold', type=float, default=0.12, help='tiempo detenido para declarar contacto (s)')
    p.add_argument('--probe-window', type=float, default=15.0, help='tope máximo del sondeo (s)')
    # grid modo A — celda única
    p.add_argument('--cell', action='store_true', help='corre una celda (v, Fset) del grid modo A')
    p.add_argument('--speed', type=int, default=None, help='SPEED_SET para --cell')
    p.add_argument('--fset', type=int, default=None, help='FORCE_SET para --cell (g, calibrado ≈ externo)')
    p.add_argument('--start-angle', type=int, default=680,
                   help='ANGLE_SET de pre-posición justo antes del contacto (def 680)')
    p.add_argument('--approach-speed', type=int, default=300, help='velocidad de pre-posición (def 300)')
    p.add_argument('--aux-every', type=int, default=8,
                   help='cada cuántas iters se lee POS+CURRENT (FORCE va cada iter) (def 8)')
    # grid modo A — campaña
    p.add_argument('--grid', action='store_true', help='corre la campaña del grid modo A')
    p.add_argument('--mode', choices=['a'], default='a',
                   help='modo de control (a=velocidad constante; b híbrido se añade luego)')
    p.add_argument('--speeds', default='25,50,100,250,500,750,1000', help='SPEED_SET a barrer')
    p.add_argument('--fsets', default='100,250,500,750,1000', help='FORCE_SET a barrer (g, calibrado)')
    p.add_argument('--trials', type=int, default=5, help='trials por celda (def 5, piloto)')
    p.add_argument('--recal-every', type=int, default=20, help='recalibrar forceClb cada N trials (def 20)')
    p.add_argument('--seed', type=int, default=0, help='semilla del orden aleatorio')
    # modo B — híbrido
    p.add_argument('--hybrid', action='store_true', help='corre el modo B (aprox. rápida + cierre lento)')
    p.add_argument('--hybrid-speed', type=int, default=25, help='velocidad de cierre lento del modo B (def 25)')
    p.add_argument('--approach-angle', type=int, default=475,
                   help='ANGLE_SET de aproximación, justo antes del contacto (def 475)')
    p.add_argument('--onset-thr', type=int, default=80,
                   help='umbral de fuerza para onset de contacto, sobre el blip de arranque (g)')
    p.add_argument('--contact-min-travel', type=int, default=150,
                   help='avance mínimo de POS desde la pre-posición para aceptar contacto (counts)')
    p.add_argument('--settle-hold', type=float, default=0.4,
                   help='tiempo tras el pico sin nuevo máximo para cerrar el trial (s)')
    p.add_argument('--trial-window', type=float, default=20.0,
                   help='tope máximo por trial (s); v=25 lento necesita ventana amplia (def 20)')
    p.add_argument('--safety-force-g', type=int, default=2200,
                   help='techo |FORCE_ACT| de emergencia (g, def 2200)')
    p.add_argument('--no-cal', action='store_true', help='no calibrar (forceClb) al inicio')
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not (0 <= args.dof < NDOF):
        print(f"ERROR: --dof fuera de rango 0..{NDOF-1}", file=sys.stderr)
        return 2
    if not (args.probe or args.zero or args.cell or args.grid or args.hybrid):
        print("Usa --zero, --probe, --cell, --grid (modo A) o --hybrid (modo B).",
              file=sys.stderr)
        return 2
    if args.cell and (args.speed is None or args.fset is None):
        print("ERROR: --cell requiere --speed y --fset", file=sys.stderr)
        return 2

    hand = connect(args)
    if hand is None:
        print("ERROR: no se pudo establecer la conexión Modbus.", file=sys.stderr)
        return 1
    try:
        if args.zero:
            run_zero(hand, args)
        elif args.cell:
            run_cell(hand, args)
        elif args.grid:
            run_grid(hand, args)
        elif args.hybrid:
            run_hybrid(hand, args)
        else:
            run_probe(hand, args)
    except KeyboardInterrupt:
        print("\n[interrumpido]")
    finally:
        try:
            hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
        except Exception:
            pass
        hand.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
