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

DOF anclados (`--hold`): otro DOF puede quedar fijo en un ángulo durante todo el
experimento. Caso pulgar: FLEXIÓN (DOF 4) con la ROTACIÓN (DOF 5) anclada en su
tope de oposición (ANGLE_SET 0 ≈ 90°, medido con `pose_check.py`) →
`--dof 4 --hold 5:0`. El ancla se re-afirma en cada escritura de ANGLE_SET, la tara
`forceClb` se hace en esa misma postura, y los DOF anclados se vigilan por fuerza
(si el dedo bajo prueba empuja contra ellos, la carga aparece ahí y no en `--dof`).

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
    DOF_NAMES, fmt_angle, parse_hold, describe_hold,
    angle_vector, open_vector, report_hold,
    load_pos_angle_map, pos_to_angle,
)

# Lectura de bloque ancho: POS_ACT(1534)…CURRENT(1599) en una sola transacción.
WIDE_ADDR = POS_ACT                 # 1534
WIDE_COUNT = CURRENT - POS_ACT + NDOF        # 1594-1534+6 = 66
OFF_POS = 0
OFF_FORCE = FORCE_ACT - POS_ACT     # 48
OFF_CUR = CURRENT - POS_ACT         # 60

FORCE_CLB = 1009                    # GESTURE_FORCE_CLB: escribir 1 (palma abierta) tara la fuerza


def default_outdir(dof):
    """exp2/data para el índice (histórico); exp2/data_dofN para el resto."""
    return os.path.join(_HERE, 'data' if dof == 3 else f'data_dof{dof}')


def open_and_settle(hand, dof, open_angle, band, timeout_s, open_speed=1000, hold=None):
    hand.write_block(SPEED_SET, [open_speed] * NDOF)
    hand.write_block(ANGLE_SET, angle_vector(dof, open_angle, hold))
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
    hold = args.hold_map
    print("Calibración de fuerza (forceClb, reg 1009). Requiere palma ABIERTA sin tocar nada.")
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
    time.sleep(0.8)
    report_hold(hand, hold, args.settle_band, args.settle_timeout_s, args.open_speed)
    open_and_settle(hand, dof, args.open_angle, args.settle_band, args.settle_timeout_s,
                    args.open_speed, hold)

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
    hand.write_block(ANGLE_SET, angle_vector(dof, ang, hold))
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
    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle, hold))
    if p is not None and f is not None:
        print(f" A POS≈{p} (flexionado, libre): FORCE_ACT={f} g   "
              f"(residual por flexión vs reposo calibrado: {f - (f_after or 0):+.0f} g)")
    print("\n Interpretación: si el reposo calibrado ≈0 y el residual por flexión es pequeño,")
    print(" FORCE_SET/FORCE_ACT ≈ fuerza externa y el grid del protocolo (Fset 100..1000) es directo.")
    print(" Si el residual por flexión sigue grande, restaremos la curva libre F(POS) igual.")


# ── Sondeo de contacto ──────────────────────────────────────────────────────

def run_probe(hand, args):
    dof = args.dof
    hold = args.hold_map
    print(f"Abriendo todos los dedos (DOF de sondeo: {dof} = {DOF_NAMES[dof]})"
          + ("  [SIN bloque: mapeo del recorrido libre]" if args.no_block else "") + "...")
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
    time.sleep(0.6)
    report_hold(hand, hold, args.settle_band, args.settle_timeout_s, args.open_speed)
    open_and_settle(hand, dof, args.open_angle, args.settle_band, args.settle_timeout_s,
                    args.open_speed, hold)

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
    hand.write_block(ANGLE_SET, angle_vector(dof, 0, hold))     # cerrar
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
    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle, hold))

    # Si una salvaguarda cortó justo en el contacto (POS ya detenido), inferir
    # el POS de contacto del tramo final.
    if contact_pos is None and len(samples) >= 5:
        tail = [p for (_, p, _, _) in samples[-8:] if p is not None]
        if tail and (max(tail) - min(tail)) <= args.stall_band * 2 and (tail[-1] - start_pos) > 50:
            contact_pos = tail[-1]

    # 3) Guardar + reportar.
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir,
                        f'probe_dof{dof}{"_libre" if args.no_block else ""}.csv')
    with open(path, 'w', newline='') as fp:
        wtr = csv.writer(fp)
        wtr.writerow(['t_s', 'pos_act', 'force_g', 'current_mA'])
        for (t, p, f, c) in samples:
            wtr.writerow([f'{t:.6f}', '' if p is None else p,
                          '' if f is None else f, '' if c is None else c])

    forces = [f for (_, _, f, _) in samples if f is not None]
    f_contact = forces[-1] if forces else None
    poss = [p for (_, p, _, _) in samples if p is not None]
    label = 'recorrido libre' if args.no_block else 'contacto'
    print(f"\n=== Exp 2 — sondeo de {label} (DOF {dof} = {DOF_NAMES[dof]}) ===")
    print(f" Anclado          : {describe_hold(args.hold_map)}")
    print(f" Motivo de parada : {reason}")
    print(f" POS: reposo={p_open}  máximo alcanzado={max(poss) if poss else '—'}"
          f"  (recorrido {max(poss) - start_pos if poss else '—'} counts)")
    if args.no_block:
        # Referencia SIN bloque: dónde se detiene el dedo por sí solo (tope
        # mecánico o auto-colisión). El sondeo CON bloque debe detenerse ANTES.
        print(f"   → POS libre de referencia. El sondeo CON bloque debe parar por debajo de")
        print(f"     este valor; si para en el mismo punto, el bloque está fuera de alcance.")
    elif contact_pos is not None:
        src = '' if reason == 'contacto' else f'  (inferido del punto de parada por {reason})'
        print(f" POS de contacto  : {contact_pos}{src}")
        print(f"   → úsalo como referencia del ángulo de aproximación del modo B (híbrido).")
        print(f"     Compáralo con el POS libre (--no-block): si coinciden, el dedo llegó a su")
        print(f"     tope/auto-colisión y NO al bloque.")
    else:
        print(" POS de contacto  : no detectado (no hubo stall; revisa montaje/alcance)")
    print(f" Fuerza al parar  : {f_contact} g   (offset en reposo: {f_open} g "
          f"→ contacto externo aprox: {f_contact - f_open if (f_contact is not None and f_open is not None) else '—'} g)")
    print(f" Fuerza máx cruda : {max_force} g   (techo era {args.probe_ceiling} g)")
    print(f" Corriente máx    : {hi_cur} mA")
    print(f" Muestras         : {len(samples)}  ({len(samples)/max(samples[-1][0],1e-9):.0f} Hz)  "
          f"lectura: {'ancha' if wide_ok else 'separada'}")
    print(f" CSV              : {path}")
    if reason == 'contacto' and not args.no_block:
        print(" ✔ Contacto detectado por stall y dedo abierto. Mándame el CSV y "
              "caracterizo la curva libre F(POS) + onset para diseñar el grid.")
    elif reason == 'contacto':
        print(" ✔ El dedo se detuvo solo (tope mecánico / auto-colisión): ese es el POS libre.")
    elif reason == 'techo_fuerza':
        print(" ⚠ Se llegó al techo de fuerza antes del stall: baja --probe-speed "
              + ("o revisa que el bloque frene el dedo." if not args.no_block else
                 "— sin bloque, esto indica auto-colisión con carga: revisa la postura anclada."))


# ── Grid modo A: una celda (v, Fset) ────────────────────────────────────────

def calibrate(hand, args):
    """forceClb con la palma abierta (fuerza ≈ externa tras esto).

    La tara se hace CON los DOF anclados en su ángulo de trabajo: así cualquier
    sesgo estático de esa postura queda incluido en el cero.
    """
    hold = args.hold_map
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
    time.sleep(0.6)
    open_and_settle(hand, args.dof, args.open_angle, args.settle_band,
                    args.settle_timeout_s, args.open_speed, hold)
    hand.write_block(FORCE_CLB, [1])
    time.sleep(1.5)


def run_trial_A(hand, dof, speed, fset, args):
    """Modo A: dedo ya pre-posicionado antes del contacto → cierra a `speed`,
    firmware frena en `fset`. Muestrea FORCE_ACT a alta tasa (pico) + POS/CURRENT
    periódicos. Devuelve series y métricas."""
    hold = args.hold_map
    hold_dofs = sorted(hold)
    hand.write_block(SPEED_SET, [speed] * NDOF)
    hand.write_block(FORCE_SET, [fset] * NDOF)

    # Baseline de los DOF ANCLADOS: se vigila la DESVIACIÓN, no el absoluto (ese
    # sensor tiene offset propio y se mueve con la postura del DOF bajo prueba).
    hold_base = {}
    reads = [fb for fb in (hand.read_block(FORCE_ACT) for _ in range(5)) if fb]
    if hold_dofs and reads:
        hold_base = {d: statistics.median([r[d] for r in reads]) for d in hold_dofs}
    # Fuerza del DOF bajo prueba EN LA PRE-POSICIÓN, antes de cerrar: es el
    # residual por flexión (sin contacto) en ese punto. `FORCE_SET` se compara
    # contra la lectura CRUDA, así que el umbral efectivo en fuerza externa es
    # Fset − f_base. En el índice ese residual era ~9 g (despreciable); en el
    # pulgar P2.1 midió ~51 g, así que hay que registrarlo por trial.
    f_base = statistics.median([r[dof] for r in reads]) if reads else None

    samples = []                 # (t, force, pos|None, cur|None)
    f_max = None; peak_t = None; onset_pos = None
    f_max_hold = 0
    aborted = False; abort_reason = ''; cur_over = 0
    ref_pos = None; ref_t = None                 # seguimiento del plateau de POS
    pb0 = hand.read_block(POS_ACT)
    start_pos = pb0[dof] if pb0 else 0
    last_pos = start_pos
    i = 0
    t_start = time.perf_counter()
    hand.write_block(ANGLE_SET, angle_vector(dof, 0, hold))    # cerrar contra el bloque
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
                    aborted = True; abort_reason = 'corriente'; break
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
            # Vigilancia de los DOF anclados: si el dedo bajo prueba empuja
            # contra uno de ellos, la carga aparece ahí, no en `dof`.
            f_h = (max((abs(fb[d] - hold_base.get(d, 0)) for d in hold_dofs), default=0)
                   if fb else 0)
            f_max_hold = max(f_max_hold, f_h)
            hold_over = args.safety_force_hold_g > 0 and f_h > args.safety_force_hold_g
            if abs(force) > args.safety_force_g or hold_over:
                aborted = True
                abort_reason = ('fuerza' if abs(force) > args.safety_force_g else 'fuerza_hold')
                samples.append((elapsed, force, pos, cur)); break
        samples.append((elapsed, force, pos, cur))
        i += 1
        if elapsed >= args.trial_window:
            break

    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle, hold))   # abrir

    forces = [f for (_, f, _, _) in samples if f is not None]
    tail = [f for (tt, f, _, _) in samples if f is not None and tt >= samples[-1][0] - 0.3]
    f_settle = statistics.fmean(tail) if tail else None
    return {
        'samples': samples, 'speed': speed, 'fset': fset,
        'f_max': f_max, 'delta_f': (f_max - fset) if f_max is not None else None,
        'f_settle': f_settle, 't_peak_ms': (peak_t - t_cmd) * 1000 if peak_t else None,
        'onset_pos': onset_pos, 'aborted': aborted, 'abort_reason': abort_reason,
        'f_max_hold': f_max_hold, 'start_pos': start_pos, 'f_base': f_base,
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
    hold = args.hold_map
    report_hold(hand, hold, args.settle_band, args.settle_timeout_s, args.open_speed)
    if not args.no_cal:
        print("Calibrando fuerza (forceClb, palma abierta)...")
        calibrate(hand, args)
    print(f"Pre-posicionando a ANGLE_SET={args.start_angle} "
          f"({fmt_angle(args.start_angle, dof)}, justo antes del contacto)...")
    open_and_settle(hand, dof, args.start_angle, args.settle_band,
                    args.settle_timeout_s, args.approach_speed, hold)

    trial = run_trial_A(hand, dof, args.speed, args.fset, args)
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, f'cell_dof{dof}_v{args.speed}_F{args.fset}.csv')
    save_cell_csv(path, trial)

    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle, hold))
    n = len(trial['samples']); rate = n / max(trial['samples'][-1][0], 1e-9)
    print("\n=== Exp 2 — celda única (modo A, validación) ===")
    print(f" DOF={dof} ({DOF_NAMES[dof]})  v={args.speed}  Fset={args.fset} g")
    print(f" Anclado: {describe_hold(hold)}")
    print(f" F_max = {trial['f_max']} g   ΔF (sobreimpulso) = {trial['delta_f']} g")
    print(f" F_régimen = {trial['f_settle']:.0f} g   t_hasta_pico = "
          f"{trial['t_peak_ms']:.0f} ms" if trial['f_settle'] is not None else " F_régimen = —")
    print(f" onset de contacto en POS = {trial['onset_pos']}   "
          f"(POS de pre-posición = {trial['start_pos']})")
    if trial['f_base'] is not None:
        print(f" Residual por flexión en la pre-posición = {trial['f_base']:.0f} g  →  "
              f"umbral efectivo en fuerza EXTERNA ≈ {args.fset - trial['f_base']:.0f} g "
              f"(FORCE_SET se compara contra la lectura cruda)")
    if hold:
        print(f" DOF anclados: desviación máx sobre su baseline en reposo = "
              f"{trial['f_max_hold']} g (no es el valor absoluto)")
    print(f" Muestras: {n}  ({rate:.0f} Hz)   "
          f"{'⚠ ABORTADO (' + trial['abort_reason'] + ')' if trial['aborted'] else ''}")
    print(f" CSV: {path}")


def check_no_overwrite(outdir, names):
    """Aborta si algún CSV de trial ya existe: ampliar N debe AÑADIR, no pisar.

    Los trials se numeran con `--trial-start`, así que una segunda tanda sobre la
    misma carpeta tiene que arrancar donde terminó la primera.
    """
    clash = [n for n in names if os.path.exists(os.path.join(outdir, n))]
    if clash:
        print(f"ERROR: {len(clash)} trial(s) ya existen en {outdir} y se sobrescribirían, "
              f"p. ej. {clash[0]}.", file=sys.stderr)
        print(f"       Usa --trial-start para continuar la numeración "
              f"(la tanda previa ocupa n=0..{len(clash)-1} o más), o escribe en otra carpeta.",
              file=sys.stderr)
        return False
    return True


# ── Grid modo A: campaña ─────────────────────────────────────────────────────

def run_grid(hand, args):
    dof = args.dof
    hold = args.hold_map
    os.makedirs(args.outdir, exist_ok=True)
    speeds = [int(x) for x in args.speeds.split(',') if x.strip()]
    fsets = [int(x) for x in args.fsets.split(',') if x.strip()]
    n0 = args.trial_start
    order = [(v, F, n) for v in speeds for F in fsets for n in range(n0, n0 + args.trials)]
    random.Random(args.seed).shuffle(order)
    total = len(order)
    print(f"Grid modo A sobre DOF {dof} ({DOF_NAMES[dof]}): {len(speeds)} v × "
          f"{len(fsets)} Fset × {args.trials} = {total} trials (orden aleatorio"
          + (f", numerados desde n={n0}" if n0 else "") + ").")
    if not check_no_overwrite(args.outdir, [f"A_dof{dof}_v{v}_F{F}_n{n:02d}.csv"
                                            for v, F, n in order]):
        return
    report_hold(hand, hold, args.settle_band, args.settle_timeout_s, args.open_speed)

    if not args.no_cal:
        print("Calibrando fuerza (forceClb, palma abierta)...")
        calibrate(hand, args)

    index_path = os.path.join(args.outdir, 'grid_index.csv')
    new_index = not os.path.exists(index_path)
    with open(index_path, 'a', newline='') as idx:
        iw = csv.writer(idx)
        if new_index:
            iw.writerow(['trial_file', 'dof', 'speed', 'fset', 'f_max', 'delta_f',
                         'f_settle', 't_peak_ms', 'onset_pos', 'rate_hz', 'aborted',
                         'hold', 'max_hold_dev_g', 'f_base_g'])
        hold_txt = ';'.join(f"{d}:{a}" for d, a in sorted(hold.items()))
        for k, (v, F, n) in enumerate(order, 1):
            # Recalibración periódica (con el dedo abierto) por la deriva del sensor.
            if not args.no_cal and args.recal_every > 0 and k > 1 and (k - 1) % args.recal_every == 0:
                print("  · recalibrando forceClb ...")
                calibrate(hand, args)
            open_and_settle(hand, dof, args.start_angle, args.settle_band,
                            args.settle_timeout_s, args.approach_speed, hold)
            trial = run_trial_A(hand, dof, v, F, args)
            fname = f"A_dof{dof}_v{v}_F{F}_n{n:02d}.csv"
            save_cell_csv(os.path.join(args.outdir, fname), trial)
            n_s = len(trial['samples'])
            rate = n_s / max(trial['samples'][-1][0], 1e-9) if n_s else 0
            iw.writerow([fname, dof, v, F, trial['f_max'], trial['delta_f'],
                         f"{trial['f_settle']:.0f}" if trial['f_settle'] is not None else '',
                         f"{trial['t_peak_ms']:.0f}" if trial['t_peak_ms'] is not None else '',
                         trial['onset_pos'], f"{rate:.0f}", int(trial['aborted']),
                         hold_txt, trial['f_max_hold'],
                         '' if trial['f_base'] is None else f"{trial['f_base']:.0f}"])
            idx.flush()
            flag = f"  ⚠ABORT ({trial['abort_reason']})" if trial['aborted'] else ''
            print(f"[{k}/{total}] v={v:4d} Fset={F:4d} n={n} → "
                  f"F_max={trial['f_max']} g  ΔF={trial['delta_f']} g{flag}")

    hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
    print(f"\nListo: {total} trials en {args.outdir}/  (series + grid_index.csv).")


# ── Modo B: híbrido (aproximación rápida + cierre lento) ─────────────────────

def run_hybrid(hand, args):
    """Modo B del protocolo: aproxima RÁPIDO hasta justo antes del contacto,
    luego cierra LENTO (hybrid_speed). Debería colapsar el sobreimpulso al nivel
    de v=25. Barre Fset. Reutiliza run_trial_A (la aproximación cercana + baja
    velocidad hacen el resto)."""
    dof = args.dof
    hold = args.hold_map
    os.makedirs(args.outdir, exist_ok=True)
    fsets = [int(x) for x in args.fsets.split(',') if x.strip()]
    n0 = args.trial_start
    order = [(F, n) for F in fsets for n in range(n0, n0 + args.trials)]
    random.Random(args.seed).shuffle(order)
    total = len(order)
    if not check_no_overwrite(args.outdir, [f"B_dof{dof}_v{args.hybrid_speed}_F{F}_n{n:02d}.csv"
                                            for F, n in order]):
        return
    print(f"Modo B (híbrido) sobre DOF {dof} ({DOF_NAMES[dof]}): aproximación rápida a "
          f"{fmt_angle(args.approach_angle, dof)}, "
          f"luego cierre a v={args.hybrid_speed}.  {len(fsets)} Fset × {args.trials} = {total} trials.")
    report_hold(hand, hold, args.settle_band, args.settle_timeout_s, args.open_speed)

    if not args.no_cal:
        print("Calibrando fuerza (forceClb)...")
        calibrate(hand, args)

    index_path = os.path.join(args.outdir, 'grid_index.csv')
    new_index = not os.path.exists(index_path)
    with open(index_path, 'a', newline='') as idx:
        iw = csv.writer(idx)
        if new_index:
            iw.writerow(['trial_file', 'dof', 'speed', 'fset', 'f_max', 'delta_f',
                         'f_settle', 't_peak_ms', 'onset_pos', 'rate_hz', 'aborted',
                         'hold', 'max_hold_dev_g', 'f_base_g'])
        hold_txt = ';'.join(f"{d}:{a}" for d, a in sorted(hold.items()))
        for k, (F, n) in enumerate(order, 1):
            if not args.no_cal and args.recal_every > 0 and k > 1 and (k - 1) % args.recal_every == 0:
                print("  · recalibrando forceClb ...")
                calibrate(hand, args)
            # Aproximación RÁPIDA (open_speed) hasta justo antes del contacto.
            open_and_settle(hand, dof, args.approach_angle, args.settle_band,
                            args.settle_timeout_s, args.open_speed, hold)
            trial = run_trial_A(hand, dof, args.hybrid_speed, F, args)   # cierre lento
            fname = f"B_dof{dof}_v{args.hybrid_speed}_F{F}_n{n:02d}.csv"
            save_cell_csv(os.path.join(args.outdir, fname), trial)
            n_s = len(trial['samples'])
            rate = n_s / max(trial['samples'][-1][0], 1e-9) if n_s else 0
            iw.writerow([fname, dof, args.hybrid_speed, F, trial['f_max'], trial['delta_f'],
                         f"{trial['f_settle']:.0f}" if trial['f_settle'] is not None else '',
                         f"{trial['t_peak_ms']:.0f}" if trial['t_peak_ms'] is not None else '',
                         trial['onset_pos'], f"{rate:.0f}", int(trial['aborted']),
                         hold_txt, trial['f_max_hold'],
                         '' if trial['f_base'] is None else f"{trial['f_base']:.0f}"])
            idx.flush()
            flag = f"  ⚠ABORT ({trial['abort_reason']})" if trial['aborted'] else ''
            print(f"[{k}/{total}] Fset={F:4d} n={n} → F_max={trial['f_max']} g  ΔF={trial['delta_f']} g{flag}")

    hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
    print(f"\nListo: {total} trials (modo B) en {args.outdir}/.")


def _load_probe(path):
    try:
        return [(int(a['pos_act']), int(a['force_g']))
                for a in csv.DictReader(open(path)) if a['pos_act'] and a['force_g']]
    except OSError:
        return None


def geometric_onset_from_probe(path, free_path=None, ext_g=20, jump_g=25, min_pos=300):
    """POS del contacto GEOMÉTRICO a partir del sondeo lento (`--probe`).

    El sondeo corre a v=50, así que su onset está prácticamente libre de retardo
    de detección. Es la referencia correcta para el punto de conmutación del modo
    B — NO el onset medido a v=1000, que llega sistemáticamente tarde (el margen
    de fuerza, las 2 muestras consecutivas y la lectura de POS posterior suman
    ~100 counts a v=1000).

    Con un sondeo libre de referencia (`--probe --no-block`) se resta la curva
    `F(POS)` en espacio libre y se detecta el primer punto con fuerza EXTERNA
    sostenida sobre `ext_g` — el criterio sensible. Sin él se cae a un detector
    por salto entre muestras, que dispara más tarde. Ante la duda se prefiere el
    valor MÁS TEMPRANO: conmutar antes solo alarga el cierre lento, conmutar
    tarde invalida el modo B.
    """
    rows = _load_probe(path)
    if not rows:
        return None
    free = _load_probe(free_path) if free_path else None
    if free:
        f0b = statistics.median([f for p, f in rows[:12]])
        f0f = statistics.median([f for p, f in free[:12]])
        pts = sorted(((p, f - f0f) for p, f in free))

        def resid(pos):
            if pos <= pts[0][0]:
                return pts[0][1]
            for (p0, r0), (p1, r1) in zip(pts, pts[1:]):
                if p0 <= pos <= p1:
                    return r0 if p1 == p0 else r0 + (pos - p0) * (r1 - r0) / (p1 - p0)
            return pts[-1][1]

        run = 0
        for pos, f in rows:
            if pos <= min_pos:
                continue
            if (f - f0b) - resid(pos) > ext_g:
                run += 1
                if run >= 2:
                    return pos
            else:
                run = 0
    prev = None
    for pos, f in rows:
        if prev is not None and (f - prev) > jump_g and pos > min_pos:
            return pos
        prev = f
    return None


# ── Sub-experimento: variabilidad del onset de contacto ──────────────────────

def run_onset(hand, args):
    """A --onset-speed (peor caso, v=1000) conduce el índice contra el bloque N
    veces y mide el POS_ACT de PRIMER contacto (fuerza sobre el baseline propio
    del trial + margen). Retrae apenas detecta el onset → toque suave, no impacto.
    Reporta σ_onset y el margen de conmutación q_sw = ceil(k·σ) para el modo B.
    """
    import math
    dof = args.dof; v = args.onset_speed; F = args.onset_fset
    hold = args.hold_map
    os.makedirs(args.outdir, exist_ok=True)
    print(f"Sub-exp onset sobre DOF {dof} ({DOF_NAMES[dof]}): v={v}, Fset={F}, "
          f"N={args.onset_trials}, margen={args.onset_margin} g sobre baseline. "
          f"Toque suave (retrae al detectar).")
    report_hold(hand, hold, args.settle_band, args.settle_timeout_s, args.open_speed)
    if not args.no_cal:
        print("Calibrando fuerza (forceClb)...")
        calibrate(hand, args)

    # Ancla 1 del mapeo POS→ANGLE: POS medido con el dedo en `open_angle`.
    open_and_settle(hand, dof, args.open_angle, args.settle_band,
                    args.settle_timeout_s, args.open_speed, hold)
    pb_open = hand.read_block(POS_ACT)
    pos_at_open = pb_open[dof] if pb_open else None

    onsets = []
    rows = []
    start_positions = []
    for k in range(1, args.onset_trials + 1):
        if not args.no_cal and args.recal_every > 0 and k > 1 and (k - 1) % args.recal_every == 0:
            calibrate(hand, args)
        open_and_settle(hand, dof, args.start_angle, args.settle_band,
                        args.settle_timeout_s, args.approach_speed, hold)
        # baseline de fuerza estacionario (inmune a la deriva entre trials)
        fbase = []
        for _ in range(8):
            fb = hand.read_block(FORCE_ACT)
            if fb is not None:
                fbase.append(fb[dof])
            time.sleep(0.02)
        f_base = statistics.median(fbase) if fbase else 0
        pb0 = hand.read_block(POS_ACT)
        start_pos = pb0[dof] if pb0 else 0
        if pb0:
            start_positions.append(start_pos)

        hand.write_block(SPEED_SET, [v] * NDOF)
        hand.write_block(FORCE_SET, [F] * NDOF)
        onset_pos = None; consec = 0; aborted = False
        t_start = time.perf_counter()
        hand.write_block(ANGLE_SET, angle_vector(dof, 0, hold))
        while True:
            elapsed = time.perf_counter() - t_start
            fb = hand.read_block(FORCE_ACT)
            force = fb[dof] if fb else None
            if force is not None:
                if abs(force) > args.safety_force_g:
                    aborted = True; break
                if (force - f_base) > args.onset_margin:
                    consec += 1
                    if consec >= 2:
                        pb = hand.read_block(POS_ACT)
                        pos = pb[dof] if pb else None
                        if pos is not None and (pos - start_pos) > args.onset_min_travel:
                            onset_pos = pos
                            break                         # onset real → retraer
                        consec = 0                        # blip de arranque → seguir
                else:
                    consec = 0
            if elapsed >= args.trial_window:
                break
        hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle, hold))   # retraer
        time.sleep(0.15)
        if onset_pos is not None and not aborted:
            onsets.append(onset_pos)
        rows.append((k, onset_pos if onset_pos is not None else '', f"{f_base:.0f}", int(aborted)))
        flag = '  ⚠ABORT' if aborted else ('' if onset_pos is not None else '  (sin onset)')
        print(f"[{k}/{args.onset_trials}] onset_pos={onset_pos}  (f_base={f_base:.0f} g){flag}")

    hand.write_block(ANGLE_SET, open_vector(args.open_angle, hold))
    path = os.path.join(args.outdir, 'onset_trials.csv')
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['trial', 'onset_pos', 'f_base_g', 'aborted'])
        w.writerows(rows)

    # Mapeo POS→ANGLE_SET. Preferido: la tabla completa de pose_check.py
    # (interpolación a tramos — la relación POS↔ANGLE NO es lineal). Si no hay
    # tabla, se cae a las DOS anclas medidas en esta corrida (open_angle y
    # start_angle): sin constantes heredadas de otro DOF, pero con el error de
    # linealizar todo el recorrido.
    pos_at_start = statistics.median(start_positions) if start_positions else None
    pmap = None
    for cand in ([args.pos_angle_csv] if args.pos_angle_csv else
                 [os.path.join(args.outdir, f'pose_dof{dof}.csv'),
                  os.path.join(os.path.dirname(_HERE), 'exp1',
                               'data' if dof == 3 else f'data_dof{dof}',
                               f'pose_dof{dof}.csv')]):
        pmap = load_pos_angle_map(cand)
        if pmap:
            map_src = cand
            break

    def to_angle(pos):
        if pmap:
            return pos_to_angle(pmap, pos)
        if (pos_at_open is None or pos_at_start is None
                or pos_at_start == pos_at_open):
            return None
        a = (args.open_angle + (pos - pos_at_open)
             * (args.start_angle - args.open_angle) / (pos_at_start - pos_at_open))
        return int(max(0, min(1000, round(a))))

    geom, geom_src = args.geom_onset_pos, '(--geom-onset-pos)'
    if geom is None:
        for cand in (os.path.join(args.outdir, f'probe_dof{dof}.csv'),
                     os.path.join(default_outdir(dof), f'probe_dof{dof}.csv')):
            g = geometric_onset_from_probe(
                cand, cand.replace('.csv', '_libre.csv'))
            if g is not None:
                geom, geom_src = g, cand
                break

    print(f"\n=== Sub-exp onset — resultado (N válidos = {len(onsets)}/{args.onset_trials}) ===")
    if pmap:
        print(f" Mapa POS↔ANGLE: tabla de {len(pmap)} puntos, interpolada a tramos "
              f"({os.path.relpath(map_src)})")
    else:
        print(f" Mapa POS↔ANGLE: 2 anclas de esta corrida (ANGLE {args.open_angle}→POS "
              f"{pos_at_open} · ANGLE {args.start_angle}→POS {pos_at_start}). "
              f"Corre pose_check.py --csv para una tabla completa.")
    if len(onsets) >= 4:
        s = sorted(onsets)
        q1, _, q3 = statistics.quantiles(s, n=4)
        iqr = q3 - q1
        clean = [x for x in s if q1 - 1.5 * iqr <= x <= q3 + 1.5 * iqr]  # sin outliers de detección
        mu = statistics.fmean(clean); sd = statistics.pstdev(clean)
        q = math.ceil(args.onset_k * sd)
        switch = mu - q
        print(f" onset POS crudo:   media={statistics.fmean(s):.0f}  σ={statistics.pstdev(s):.1f}  (N={len(s)})")
        print(f" onset POS robusto: media={mu:.0f}  σ={sd:.1f}  min={min(clean)}  "
              f"(N={len(clean)}; {len(s)-len(clean)} outliers de detección excluidos)")
        print(f"   (a v={args.onset_speed} la cuantización de POS por muestra domina la σ medida;")
        print(f"    la repetibilidad mecánica intra-cluster es mucho menor.)")
        print(f" Margen de conmutación  q_sw = ceil({args.onset_k}·σ_robusta) = {q} counts POS")
        # El onset medido a v=1000 llega SISTEMÁTICAMENTE TARDE: entre que la
        # fuerza cruza el margen, se exigen 2 muestras seguidas y se lee POS,
        # el dedo ya avanzó. El punto de conmutación debe anclarse en el onset
        # GEOMÉTRICO del sondeo lento, no en el detectado.
        if geom is not None:
            switch_g = geom - q
            ang = to_angle(switch_g)
            print(f"\n Onset GEOMÉTRICO (sondeo lento, {os.path.relpath(geom_src)}): POS {geom}")
            print(f"   retardo de detección a v={args.onset_speed}: {mu - geom:+.0f} counts "
                  f"(la detección llega tarde; por eso NO se usa {mu:.0f} como referencia)")
            print(f" → modo B: entra al cierre lento en POS ≈ {switch_g:.0f} = {geom} − {q}"
                  + (f"  (--approach-angle ≈ {ang})" if ang is not None else ""))
        else:
            ang = to_angle(mu - q)
            print(f"\n ⚠ SIN sondeo lento de referencia: no se puede corregir el retardo de")
            print(f"   detección, que a esta velocidad puede ser de ~100 counts o más. El punto")
            print(f"   de conmutación de abajo sale del onset DETECTADO y probablemente quede")
            print(f"   TARDE (después del contacto real), que es justo lo que rompe el modo B.")
            print(f"   Corre `--probe` en este mismo montaje y repite, o pasa --geom-onset-pos.")
            print(f" → modo B (SIN CORREGIR): POS ≈ {mu - q:.0f}"
                  + (f"  (--approach-angle ≈ {ang})" if ang is not None else ""))
    elif len(onsets) >= 2:
        mu = statistics.fmean(onsets); sd = statistics.pstdev(onsets)
        print(f" POS onset: media={mu:.0f}  σ={sd:.1f}  q_sw=ceil({args.onset_k}·σ)={math.ceil(args.onset_k*sd)}")
    else:
        print(" Muy pocos onsets válidos; revisa --onset-margin / --onset-min-travel / montaje.")
    print(f" CSV: {path}")


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
    p.add_argument('--hold', default='',
                   help="DOF a ANCLAR durante todo el experimento, 'DOF:ANGLE' o "
                        "'DOF:GRADOSd', coma-separado. Ej. pulgar: --dof 4 --hold 5:0 "
                        "(rotación fija; mide el extremo correcto con pose_check.py). "
                        "Se re-afirma en cada escritura.")
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
    p.add_argument('--no-block', action='store_true',
                   help='sondeo SIN el bloque: mapea el recorrido libre del dedo '
                        '(tope mecánico / auto-colisión) como referencia del sondeo con bloque')
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
    p.add_argument('--trial-start', type=int, default=0,
                   help='primer índice de trial (def 0). Para AMPLIAR una campaña ya '
                        'corrida sin pisarla: --trial-start 5 --trials 15 continúa n=5..19.')
    p.add_argument('--recal-every', type=int, default=20, help='recalibrar forceClb cada N trials (def 20)')
    p.add_argument('--seed', type=int, default=0, help='semilla del orden aleatorio')
    # modo B — híbrido
    p.add_argument('--hybrid', action='store_true', help='corre el modo B (aprox. rápida + cierre lento)')
    p.add_argument('--hybrid-speed', type=int, default=25, help='velocidad de cierre lento del modo B (def 25)')
    p.add_argument('--approach-angle', type=int, default=475,
                   help='ANGLE_SET de aproximación, justo antes del contacto (def 475)')
    # sub-experimento onset
    p.add_argument('--onset', action='store_true', help='sub-exp: variabilidad del onset de contacto')
    p.add_argument('--onset-speed', type=int, default=1000, help='velocidad del sub-exp onset (def 1000)')
    p.add_argument('--onset-fset', type=int, default=500, help='FORCE_SET del sub-exp onset (def 500)')
    p.add_argument('--onset-trials', type=int, default=50, help='nº de toques (def 50)')
    p.add_argument('--onset-margin', type=int, default=120,
                   help='fuerza sobre el baseline del trial para declarar contacto (g, def 120)')
    p.add_argument('--onset-min-travel', type=int, default=200,
                   help='avance mínimo de POS desde el inicio para descartar el blip de arranque')
    p.add_argument('--onset-k', type=float, default=3.3, help='factor para q_sw = ceil(k·σ) (def 3.3)')
    p.add_argument('--geom-onset-pos', type=int, default=None,
                   help='POS del onset GEOMÉTRICO (del sondeo lento --probe). Es la '
                        'referencia correcta para el punto de conmutación del modo B; el '
                        'onset medido a v=1000 llega tarde. Def: se busca probe_dof<N>.csv.')
    p.add_argument('--pos-angle-csv', default=None,
                   help='CSV de pose_check.py para el mapeo POS↔ANGLE a tramos '
                        '(def: se busca pose_dof<N>.csv en --outdir y en exp1/data_dof<N>/)')
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
    p.add_argument('--safety-force-hold-g', type=int, default=None,
                   help='techo de DESVIACIÓN de FORCE_ACT en los DOF ANCLADOS, sobre su '
                        'baseline en reposo (def: igual a --safety-force-g; 0 = desactivar). '
                        'Es desviación y no valor absoluto porque ese sensor tiene offset '
                        'propio y varía con la postura del DOF bajo prueba.')
    p.add_argument('--no-cal', action='store_true', help='no calibrar (forceClb) al inicio')
    p.add_argument('--outdir', default=None,
                   help='carpeta de salida (def exp2/data para DOF 3, exp2/data_dofN si no)')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not (0 <= args.dof < NDOF):
        print(f"ERROR: --dof fuera de rango 0..{NDOF-1}", file=sys.stderr)
        return 2
    if not (args.probe or args.zero or args.cell or args.grid or args.hybrid or args.onset):
        print("Usa --zero, --probe, --cell, --grid (modo A), --hybrid (modo B) o --onset.",
              file=sys.stderr)
        return 2
    if args.cell and (args.speed is None or args.fset is None):
        print("ERROR: --cell requiere --speed y --fset", file=sys.stderr)
        return 2
    try:
        args.hold_map = parse_hold(args.hold)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.dof in args.hold_map:
        print(f"ERROR: --hold no puede anclar el propio DOF bajo prueba ({args.dof})",
              file=sys.stderr)
        return 2
    if args.outdir is None:
        args.outdir = default_outdir(args.dof)
    if args.safety_force_hold_g is None:
        args.safety_force_hold_g = args.safety_force_g

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
        elif args.onset:
            run_onset(hand, args)
        else:
            run_probe(hand, args)
    except KeyboardInterrupt:
        print("\n[interrumpido]")
    finally:
        # SEGURIDAD: abrir al salir; los DOF anclados se MANTIENEN en su ángulo.
        try:
            hand.write_block(ANGLE_SET, open_vector(args.open_angle, args.hold_map))
        except Exception:
            pass
        hand.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
