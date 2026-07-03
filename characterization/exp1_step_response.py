#!/usr/bin/env python3
"""Experimento 1 — Respuesta al escalón y latencia comando→sensor (espacio libre).

Sigue characterization/PROTOCOL_Dynamic_Characterization_RH56DFTP.md (Exp 1):
el dedo se mueve EN EL AIRE (sin objeto). Mide latencia, tiempo de subida y
establecimiento sobre POS_ACT. FORCE_SET alto para que el umbral de fuerza nunca
dispare → se caracteriza movimiento puro.

Standalone (no PyQt), un solo proceso/hilo/cliente Modbus, lazo intercalado: se
escribe el escalón UNA vez y se lee POS_ACT en lazo cerrado con
time.perf_counter() por muestra.

Estrategia de muestreo (desviación deliberada del ejemplo del protocolo, que
leía 3 bloques/iteración → ~33 Hz):
  --read pos  (def): lee solo POS_ACT por iteración (~87-98 Hz); chequea
                     FORCE_ACT cada --safety-every iteraciones (seguridad).
  --read full     : lee POS_ACT + FORCE_ACT + CURRENT por iteración (~33 Hz).

⚠ SEGURIDAD: aunque es espacio libre, un --target-angle mal elegido puede chocar
el dedo contra la palma u otros dedos. VALIDA SIEMPRE primero con:
    exp1_step_response.py ... --single --speed 100 --read full
y confirma que |FORCE_ACT|max ≈ 0 (sin contacto) antes de correr la campaña.
Al salir (fin, Ctrl-C o aborto) el script abre todos los dedos.

Ejemplos:
  # validación de un trial (índice, lento, con fuerza por muestra)
  .venv/bin/python characterization/exp1_step_response.py \
      --transport serial --serial-port /dev/ttyUSB1 --single --speed 100 --read full

  # campaña completa del protocolo (5 velocidades x 20 trials, orden aleatorio)
  .venv/bin/python characterization/exp1_step_response.py \
      --transport serial --serial-port /dev/ttyUSB1 --outdir exp1_out
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import statistics
import sys
import time

from hand_modbus import (
    HandModbus, NDOF, ANGLE_SET, FORCE_SET, SPEED_SET,
    POS_ACT, ANGLE_ACT, FORCE_ACT, CURRENT,
)


# ── Helpers de comando ─────────────────────────────────────────────────────

def angle_vector(dof, value):
    """Bloque ANGLE_SET que mueve solo `dof`; -1 = mantener el resto."""
    v = [-1] * NDOF
    v[dof] = value
    return v


def open_and_settle(hand, dof, open_angle, band, timeout_s, open_speed=1000):
    """Abre el dedo `dof` a velocidad rápida fija y espera settle de ANGLE_ACT.

    La velocidad de reapertura es independiente de la velocidad de prueba del
    trial, para que la reapertura no herede una `SPEED_SET` lenta.
    """
    hand.write_block(SPEED_SET, [open_speed] * NDOF)
    hand.write_block(ANGLE_SET, angle_vector(dof, open_angle))
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        a = hand.read_block(ANGLE_ACT)
        if a is not None and abs(a[dof] - open_angle) <= band:
            time.sleep(0.05)   # pequeño margen extra de asentamiento
            return True
        time.sleep(0.02)
    return False


# ── Un trial ────────────────────────────────────────────────────────────────

def run_trial(hand, dof, speed, args):
    """Un escalón: baseline → comando ANGLE_SET=target → log POS_ACT hasta window_s."""
    # Configurar velocidad y umbral de fuerza (todos los DOF; solo `dof` se moverá).
    hand.write_block(SPEED_SET, [speed] * NDOF)
    hand.write_block(FORCE_SET, [args.force_set] * NDOF)

    full = (args.read == 'full')
    samples = []            # (t_rel, pos, force|None, current|None)
    max_abs_force = 0
    aborted = False
    settled = False
    t_cmd = None
    write_cost = None
    cmd_issued = False
    i = 0

    t_start = time.perf_counter()
    while True:
        t = time.perf_counter()
        elapsed = t - t_start

        # Disparo del escalón una sola vez, tras el baseline.
        if not cmd_issued and elapsed >= args.baseline_s:
            tb = time.perf_counter()
            hand.write_block(ANGLE_SET, angle_vector(dof, args.target_angle))
            t_cmd = time.perf_counter()
            write_cost = t_cmd - tb
            cmd_issued = True

        # Lectura de alto ritmo: POS_ACT siempre.
        pblk = hand.read_block(POS_ACT)
        pos = pblk[dof] if pblk else None

        force = None
        current = None
        # FORCE_ACT: por muestra en modo full, si no periódico para seguridad.
        if full or (i % args.safety_every == 0):
            fblk = hand.read_block(FORCE_ACT)
            if fblk is not None:
                force = fblk[dof]
                max_abs_force = max(max_abs_force, abs(force))
                if abs(force) > args.safety_force_g:
                    hand.write_block(ANGLE_SET, angle_vector(dof, args.open_angle))
                    aborted = True
                    samples.append((elapsed, pos, force, current))
                    break
        if full:
            cblk = hand.read_block(CURRENT)
            current = cblk[dof] if cblk else None

        samples.append((elapsed, pos, force, current))
        i += 1

        # Paro-al-asentar: tras el comando y un mínimo de respuesta, si POS_ACT
        # no varía más que settle_pos_band durante settle_hold_s → asentado.
        t_cmd_rel = (t_cmd - t_start) if t_cmd is not None else None
        if (cmd_issued and t_cmd_rel is not None
                and elapsed >= t_cmd_rel + args.settle_hold_s + 0.3):
            recent = [p for (tt, p, f, c) in samples
                      if p is not None and tt >= elapsed - args.settle_hold_s]
            if len(recent) >= 3 and (max(recent) - min(recent)) <= args.settle_pos_band:
                settled = True
                break

        if elapsed >= args.window_s:   # tope máximo
            break

    return {
        'samples': samples, 'dof': dof, 'speed': speed,
        'force_set': args.force_set, 'target': args.target_angle,
        't_cmd_rel': (t_cmd - t_start) if t_cmd is not None else None,
        'write_cost': write_cost, 'aborted': aborted, 'settled': settled,
        'max_abs_force_g': max_abs_force,
    }


# ── Métrica rápida (sanity; el análisis fino va offline sobre los CSV) ──────

def quick_metrics(trial):
    s = trial['samples']
    tc = trial['t_cmd_rel']
    pos_all = [(r[0], r[1]) for r in s if r[1] is not None]
    if not pos_all or tc is None:
        return {}
    base = [p for (t, p) in pos_all if t < tc]
    if not base:
        return {}
    mu = statistics.fmean(base)
    sd = statistics.pstdev(base) if len(base) > 1 else 0.0
    band = max(4.0, 3.0 * sd)          # 4 counts o 3σ (protocolo)

    onset_t = next((t for (t, p) in pos_all if t >= tc and abs(p - mu) > band), None)
    t_end = pos_all[-1][0]
    tail = [p for (t, p) in pos_all if t >= t_end - 0.2]
    final = statistics.fmean(tail) if tail else None

    # Fuerza: baseline en reposo (offset), desvío máximo y desvío final.
    force_all = [(r[0], r[2]) for r in s if r[2] is not None]
    fbase = [f for (t, f) in force_all if t < tc]
    f_mu = statistics.fmean(fbase) if fbase else None
    f_dev_max = (max(abs(f - f_mu) for (t, f) in force_all)
                 if (force_all and f_mu is not None) else None)
    f_tail = [f for (t, f) in force_all if t >= t_end - 0.3]
    f_final_dev = (statistics.fmean(f_tail) - f_mu) if (f_tail and f_mu is not None) else None

    n = len(s)
    rate = n / (s[-1][0] - s[0][0]) if s[-1][0] > s[0][0] else float('nan')
    return {
        'latency_ms': (onset_t - tc) * 1000.0 if onset_t is not None else None,
        'baseline_pos': mu, 'final_pos': final,
        'delta_pos': (final - mu) if final is not None else None,
        'rate_hz': rate, 'n': n,
        'force_base_g': f_mu, 'force_dev_max_g': f_dev_max,
        'force_final_dev_g': f_final_dev,
    }


def save_trial_csv(path, trial):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['t_s', 'pos_act', 'force_g', 'current_mA'])
        for (t, pos, force, cur) in trial['samples']:
            w.writerow([f"{t:.6f}",
                        '' if pos is None else pos,
                        '' if force is None else force,
                        '' if cur is None else cur])


# ── Campaña ─────────────────────────────────────────────────────────────────

def _fmt(x, spec=''):
    return format(x, spec) if isinstance(x, (int, float)) and x is not None else ''


def run_campaign(hand, args):
    os.makedirs(args.outdir, exist_ok=True)
    speeds = [int(x) for x in args.speeds.split(',') if x.strip()]
    order = [(v, n) for v in speeds for n in range(args.trials)]
    random.Random(args.seed).shuffle(order)

    print(f"Abriendo todos los dedos para despejar el área (DOF de prueba: {args.dof})...")
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
    time.sleep(0.6)

    index_path = os.path.join(args.outdir, 'index.csv')
    new_index = not os.path.exists(index_path)
    with open(index_path, 'a', newline='') as idx:
        iw = csv.writer(idx)
        if new_index:
            iw.writerow(['trial_file', 'dof', 'speed', 'force_set', 'target',
                         't_cmd_s', 'write_cost_s', 'rate_hz', 'latency_ms',
                         'baseline_pos', 'final_pos', 'delta_pos',
                         'force_base_g', 'force_final_dev_g',
                         'max_abs_force_g', 'settled', 'aborted'])
        total = len(order)
        for k, (v, n) in enumerate(order, 1):
            if not open_and_settle(hand, args.dof, args.open_angle,
                                   args.settle_band, args.settle_timeout_s,
                                   args.open_speed):
                print(f"[{k}/{total}] WARN: apertura no asentó (v={v} n={n}); continúo")
            trial = run_trial(hand, args.dof, v, args)
            m = quick_metrics(trial)
            fname = f"trial_dof{args.dof}_v{v}_n{n:02d}.csv"
            save_trial_csv(os.path.join(args.outdir, fname), trial)
            iw.writerow([fname, args.dof, v, args.force_set, args.target_angle,
                         _fmt(trial['t_cmd_rel'], '.6f'), _fmt(trial['write_cost'], '.6f'),
                         _fmt(m.get('rate_hz'), '.1f'), _fmt(m.get('latency_ms'), '.1f'),
                         _fmt(m.get('baseline_pos'), '.1f'), _fmt(m.get('final_pos'), '.1f'),
                         _fmt(m.get('delta_pos'), '.1f'),
                         _fmt(m.get('force_base_g'), '.0f'), _fmt(m.get('force_final_dev_g'), '.0f'),
                         trial['max_abs_force_g'], int(trial['settled']), int(trial['aborted'])])
            idx.flush()
            flag = ('  ⚠ABORTADO' if trial['aborted']
                    else ('' if trial['settled'] else '  (no asentó)'))
            print(f"[{k}/{total}] v={v:4d} n={n:02d} → {_fmt(m.get('rate_hz'),'.0f')} Hz, "
                  f"lat={_fmt(m.get('latency_ms'),'.1f')} ms, "
                  f"Δpos={_fmt(m.get('delta_pos'),'.0f')}, "
                  f"Fdev_fin={_fmt(m.get('force_final_dev_g'),'.0f')} g{flag}")

    print(f"\nListo: {total} trials en {args.outdir}/  (series por trial + index.csv).")


def run_single(hand, args):
    print(f"Abriendo todos los dedos (DOF de prueba: {args.dof})...")
    hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
    hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
    time.sleep(0.6)
    open_and_settle(hand, args.dof, args.open_angle, args.settle_band,
                    args.settle_timeout_s, args.open_speed)

    trial = run_trial(hand, args.dof, args.speed, args)
    m = quick_metrics(trial)
    os.makedirs(args.outdir, exist_ok=True)
    fname = f"single_dof{args.dof}_v{args.speed}.csv"
    save_trial_csv(os.path.join(args.outdir, fname), trial)

    print("\n=== Exp 1 — trial único (validación) ===")
    print(f" DOF={args.dof}  v={args.speed}  target={args.target_angle}  "
          f"force_set={args.force_set}")
    print(f" Muestras: {m.get('n')}   Tasa: {_fmt(m.get('rate_hz'),'.1f')} Hz")
    print(f" t_cmd={_fmt(trial['t_cmd_rel'],'.4f')} s  (write_cost={_fmt(trial['write_cost'],'.5f')} s)")
    print(f" Latencia≈ {_fmt(m.get('latency_ms'),'.1f')} ms   "
          f"Δpos= {_fmt(m.get('delta_pos'),'.0f')} (base {_fmt(m.get('baseline_pos'),'.0f')} → "
          f"final {_fmt(m.get('final_pos'),'.0f')})")
    fb, fd, ff = m.get('force_base_g'), m.get('force_dev_max_g'), m.get('force_final_dev_g')
    print(f" FORCE_ACT: baseline≈{_fmt(fb,'.0f')} g (offset en reposo), "
          f"desvío máx {_fmt(fd,'.0f')} g, desvío final {_fmt(ff,'.0f')} g")
    contact = (ff is not None and ff > args.contact_delta_g)
    print("   → " + ("⚠ posible CONTACTO: fuerza final muy por encima del baseline"
                     if contact else
                     "sin contacto: la fuerza queda cerca de su baseline en reposo"))
    if not trial.get('settled'):
        print("   ⚠ NO asentó dentro de --window-s; sube la ventana o el dedo no llegó al target")
    if trial['aborted']:
        print("   ⚠ TRIAL ABORTADO por techo de fuerza (--safety-force-g)")
    print(f" CSV: {os.path.join(args.outdir, fname)}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def connect(args):
    if args.transport == 'tcp':
        return HandModbus.open_tcp(args.ip, args.port, args.device_id, args.timeout)
    return HandModbus.open_serial(args.serial_port, args.baud, args.device_id, args.timeout)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Exp 1 — respuesta al escalón en espacio libre (Inspire RH56DFTP)."
    )
    # transporte
    p.add_argument('--transport', choices=['tcp', 'serial'], default='serial')
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--ip', default='192.168.11.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB1')
    p.add_argument('--baud', type=int, default=115200)
    # experimento
    p.add_argument('--dof', type=int, default=3, help='DOF a caracterizar (def 3 = índice)')
    p.add_argument('--speeds', default='100,250,500,750,1000',
                   help='SPEED_SET a barrer, coma-separado (def protocolo)')
    p.add_argument('--trials', type=int, default=20, help='trials por velocidad (def 20)')
    p.add_argument('--open-angle', type=int, default=1000, help='ANGLE_SET abierto (def 1000)')
    p.add_argument('--open-speed', type=int, default=1000,
                   help='velocidad fija para reabrir entre trials (def 1000)')
    p.add_argument('--target-angle', type=int, default=300,
                   help='ANGLE_SET objetivo SIN contacto (def 300) — ⚠ VERIFICA en tu montaje')
    p.add_argument('--force-set', type=int, default=3000,
                   help='FORCE_SET alto para no limitar (def 3000)')
    p.add_argument('--baseline-s', type=float, default=0.2, help='baseline previo al escalón (s)')
    p.add_argument('--window-s', type=float, default=10.0,
                   help='ventana MÁXIMA de logging (s); para al asentar POS_ACT (def 10)')
    p.add_argument('--settle-pos-band', type=int, default=8,
                   help='rango de POS_ACT (counts) para dar por asentado el movimiento (def 8)')
    p.add_argument('--settle-hold-s', type=float, default=0.3,
                   help='tiempo sostenido sin movimiento para declarar asentado (def 0.3)')
    p.add_argument('--contact-delta-g', type=int, default=150,
                   help='desvío de fuerza sobre baseline que sugiere contacto (def 150)')
    p.add_argument('--read', choices=['pos', 'full'], default='pos',
                   help="pos=solo POS_ACT ~90 Hz (def) | full=POS+FORCE+CURRENT ~33 Hz")
    p.add_argument('--safety-force-g', type=int, default=1800,
                   help='techo |FORCE_ACT| para abortar y abrir (g, def 1800)')
    p.add_argument('--safety-every', type=int, default=8,
                   help='en modo pos, cada cuántas iters se chequea FORCE_ACT (def 8)')
    p.add_argument('--settle-band', type=int, default=6,
                   help='banda ANGLE_ACT para dar por asentada la apertura (def 6)')
    p.add_argument('--settle-timeout-s', type=float, default=3.0)
    p.add_argument('--seed', type=int, default=0, help='semilla del orden aleatorio (def 0)')
    p.add_argument('--outdir', default='exp1_out', help='carpeta de salida (def exp1_out)')
    # modo trial único (validación)
    p.add_argument('--single', action='store_true', help='corre un solo trial (validación)')
    p.add_argument('--speed', type=int, default=None, help='velocidad para --single')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not (0 <= args.dof < NDOF):
        print(f"ERROR: --dof fuera de rango 0..{NDOF-1}", file=sys.stderr)
        return 2
    if args.single and args.speed is None:
        print("ERROR: --single requiere --speed", file=sys.stderr)
        return 2

    hand = connect(args)
    if hand is None:
        print("ERROR: no se pudo establecer la conexión Modbus.", file=sys.stderr)
        return 1
    try:
        if args.single:
            run_single(hand, args)
        else:
            run_campaign(hand, args)
    except KeyboardInterrupt:
        print("\n[interrumpido]")
    finally:
        # SEGURIDAD: abrir todos los dedos al salir.
        try:
            hand.write_block(ANGLE_SET, [args.open_angle] * NDOF)
        except Exception:
            pass
        hand.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
