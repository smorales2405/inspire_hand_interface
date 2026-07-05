#!/usr/bin/env python3
"""A1.1 — Ruido en reposo y piso de umbral de contacto (táctil RH56DFTP).

El "Exp 0 del táctil": caracteriza el RUIDO por taxel en reposo (sin contacto)
y fija el umbral de detección de contacto `thr = max(k·σ_taxel, abs_floor)` que
usará A1.2/A1.3 y todo el pipeline multimodal. Excluye los taxeles muertos/
pegados del screening de Fase 0.

Standalone: NO importa PyQt. Un proceso/hilo/cliente Modbus, lazo intercalado,
time.perf_counter() para todos los timestamps. Al salir deja la mano en estado
seguro (dedos abiertos). Correr con la GUI CERRADA.

Loguea la temperatura de los 6 actuadores (reg 1618, manual 2.6.19) al inicio y
al final como proxy térmico — la deriva resistiva es térmica (ver A1.2).

Uso:
    .venv/bin/python Caracterizacion/tactil/fase_a1/a1_noise.py \
        --transport serial --serial-port /dev/ttyUSB0 --baud 115200 --secs 180
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))     # Caracterizacion/tactil/

from hand_tactile import (                      # noqa: E402
    TactileHand, ZONES, TAXELS, N_TAXELS, taxel_label,
)


# ── Estadistica (pura, sin numpy) ───────────────────────────────────────────

def percentile(sorted_vals, pct):
    if not sorted_vals:
        return float('nan')
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_vals[int(k)]
    return sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo)


def median(vals):
    return statistics.median(vals) if vals else float('nan')


def mad(vals, med=None):
    if not vals:
        return float('nan')
    if med is None:
        med = statistics.median(vals)
    return statistics.median([abs(v - med) for v in vals])


# ── Conexion ────────────────────────────────────────────────────────────────

def connect(args):
    if args.transport == 'tcp':
        th = TactileHand.open_tcp(args.ip, args.port, args.device_id, args.timeout)
        target = f"TCP {args.ip}:{args.port}"
    else:
        th = TactileHand.open_serial(args.serial_port, args.baud,
                                     args.device_id, args.timeout)
        target = f"serial {args.serial_port} @ {args.baud} baud"
    return th, target


# ── Exclusion desde el screening de Fase 0 ──────────────────────────────────

def load_exclusion(diag_path):
    """Lee taxel_diagnosis.csv de Fase 0 -> set de taxeles a excluir.

    Excluye status en {dead, stuck_high, stuck_low, unknown}. Siempre excluye la
    zona 6 (Medio·Punta, muerta por hardware). Devuelve (excl_set, motivo_str).
    """
    excl = set()
    # z6 muerta por hardware, pase lo que pase.
    for t, (zi, *_rest) in enumerate(TAXELS):
        if zi == 6:
            excl.add(t)
    if not diag_path or not os.path.exists(diag_path):
        return excl, f"(sin diagnosis de Fase 0; solo excluyo z6) [{diag_path}]"
    bad = {'dead', 'stuck_high', 'stuck_low', 'unknown'}
    with open(diag_path) as f:
        for row in csv.DictReader(f):
            if row.get('status', '') in bad:
                excl.add(int(row['taxel']))
    return excl, f"Fase 0: {diag_path}"


# ── Captura ─────────────────────────────────────────────────────────────────

def capture(th, args):
    """Lee frames completos en reposo por --secs (o --frames). Stats por taxel."""
    s1 = [0.0] * N_TAXELS
    s2 = [0.0] * N_TAXELS
    mn = [float('inf')] * N_TAXELS
    mx = [float('-inf')] * N_TAXELS
    dt_ms = []
    n_used = 0
    n_dropped = 0

    for _ in range(args.warmup):
        th.read_frame_flat()

    temp_start = th.read_temps()
    t0 = time.perf_counter()
    t_prev = t0
    use_frames = args.frames is not None
    while True:
        if use_frames:
            if n_used >= args.frames:
                break
        elif time.perf_counter() - t0 >= args.secs:
            break
        flat, _failed = th.read_frame_flat()
        t_now = time.perf_counter()
        if flat is None:
            n_dropped += 1
            t_prev = t_now
            if n_dropped > 5000:
                break
            continue
        dt_ms.append((t_now - t_prev) * 1000.0)
        t_prev = t_now
        for i, v in enumerate(flat):
            s1[i] += v
            s2[i] += v * v
            if v < mn[i]:
                mn[i] = v
            if v > mx[i]:
                mx[i] = v
        n_used += 1
    elapsed = time.perf_counter() - t0
    temp_end = th.read_temps()

    mu = [0.0] * N_TAXELS
    sigma = [0.0] * N_TAXELS
    excursion = [0.0] * N_TAXELS
    for i in range(N_TAXELS):
        if n_used:
            m = s1[i] / n_used
            var = max(0.0, s2[i] / n_used - m * m)
            mu[i] = m
            sigma[i] = math.sqrt(var)
            if mx[i] != float('-inf'):
                excursion[i] = max(mx[i] - m, m - mn[i])
    return {
        'mu': mu, 'sigma': sigma, 'mn': mn, 'mx': mx, 'excursion': excursion,
        'n_used': n_used, 'n_dropped': n_dropped, 'elapsed': elapsed,
        'dt_ms': dt_ms, 'temp_start': temp_start, 'temp_end': temp_end,
    }


# ── Analisis + reporte ──────────────────────────────────────────────────────

def analyze_and_report(cap, excl, excl_src, args):
    mu, sigma, exc = cap['mu'], cap['sigma'], cap['excursion']
    good = [t for t in range(N_TAXELS) if t not in excl]
    n_good = len(good)

    sg = sorted(sigma[t] for t in good)
    ex = sorted(exc[t] for t in good)
    med_s = median(sg)
    mad_s = mad(sg, med_s)
    fence = med_s + args.k * 1.4826 * mad_s
    noisy = [t for t in good if sigma[t] > fence]

    # abs_floor recomendado desde datos: cubre la excursion rara de taxeles
    # quietos. p99.9 de la excursion sobre taxeles buenos, redondeado hacia arriba.
    abs_floor = math.ceil(percentile(ex, 99.9)) if ex else 0
    # Cuantos taxeles buenos quedarian gobernados por el piso vs k·sigma.
    n_by_floor = sum(1 for t in good if args.k * sigma[t] <= abs_floor)

    print()
    print("=" * 64)
    print(" A1.1 — Ruido en reposo y piso de umbral de contacto (táctil)")
    print("=" * 64)
    print(f" Frames usados : {cap['n_used']}  (descartados bus: {cap['n_dropped']})")
    print(f" Duracion      : {cap['elapsed']:.1f} s"
          + (f"   ({1000.0/statistics.fmean(cap['dt_ms']):.1f} Hz frame)"
             if cap['dt_ms'] else ""))
    _report_temp(cap)
    print(f" Exclusion     : {len(excl)} taxeles ({excl_src})")
    print(f" Taxeles buenos: {n_good} / {N_TAXELS}")
    print("-" * 64)
    print(" Ruido sigma por taxel (solo buenos), counts:")
    print(f"   min {sg[0]:.2f}   med {med_s:.2f}   p95 {percentile(sg,95):.2f}"
          f"   p99 {percentile(sg,99):.2f}   max {sg[-1]:.2f}")
    print(f"   ==0 (nunca fluctuan): {sum(1 for s in sg if s == 0)} / {n_good}")
    print(f"   cerco robusto (med + {args.k}·1.4826·MAD) = {fence:.2f}"
          f"   -> taxeles ruidosos: {len(noisy)}")
    print(" Excursion max |v-μ| por taxel (solo buenos), counts:")
    print(f"   med {median(ex):.1f}   p95 {percentile(ex,95):.1f}"
          f"   p99 {percentile(ex,99):.1f}   p99.9 {percentile(ex,99.9):.1f}"
          f"   max {ex[-1]:.1f}")
    print("-" * 64)
    print(f" UMBRAL DE CONTACTO recomendado: thr = max({args.k}·σ_taxel, abs_floor)")
    print(f"   abs_floor (empirico, ⌈p99.9 excursion⌉) = {abs_floor} counts")
    print(f"   taxeles buenos gobernados por el piso (k·σ ≤ floor): "
          f"{n_by_floor} / {n_good}")
    if noisy:
        noisy.sort(key=lambda t: -sigma[t])
        print(" Taxeles mas ruidosos (top 10):")
        for t in noisy[:10]:
            print(f"   {taxel_label(t):34s} σ={sigma[t]:6.2f}  "
                  f"exc={exc[t]:6.1f}  μ={mu[t]:7.1f}")
    print("=" * 64)
    return {'good': good, 'fence': fence, 'noisy': set(noisy),
            'abs_floor': abs_floor, 'med_sigma': med_s, 'mad_sigma': mad_s}


def _report_temp(cap):
    ts, te = cap['temp_start'], cap['temp_end']
    if ts is None or te is None:
        print(" Temperatura   : (no disponible)")
        return
    dt = [te[i] - ts[i] for i in range(len(te))]
    print(f" Temp actuadores (C) inicio: {ts}")
    print(f"                     final : {te}   ΔT={dt}")


def write_csv(path, cap, excl, res, args):
    thr = []
    for t in range(N_TAXELS):
        thr.append(max(args.k * cap['sigma'][t], res['abs_floor']))
    with open(path, 'w') as f:
        f.write("taxel,zone,zone_name,row,col,mu,sigma,min,max,excursion_max,"
                "excluded,noisy,thr\n")
        for t in range(N_TAXELS):
            zi, name, r, c, _addr = TAXELS[t]
            mn = cap['mn'][t]
            mx = cap['mx'][t]
            mn = '' if mn == float('inf') else f"{mn:.0f}"
            mx = '' if mx == float('-inf') else f"{mx:.0f}"
            f.write(f"{t},{zi},{name},{r},{c},"
                    f"{cap['mu'][t]:.3f},{cap['sigma'][t]:.3f},{mn},{mx},"
                    f"{cap['excursion'][t]:.1f},"
                    f"{int(t in excl)},{int(t in res['noisy'])},{thr[t]:.1f}\n")


# ── Orquestacion ────────────────────────────────────────────────────────────

def run(args):
    th, target = connect(args)
    if th is None:
        print("ERROR: no se pudo establecer la conexion Modbus.", file=sys.stderr)
        return 1
    print(f"Conectado a {target} (device_id={args.device_id}).")
    excl, excl_src = load_exclusion(args.diag)

    try:
        if not args.no_prompt:
            dur = f"{args.frames} frames" if args.frames else f"{args.secs:.0f} s"
            input(f"\nA1.1: mano QUIETA y SIN contacto. Capturare {dur}. [Enter]... ")
        print("  Capturando ruido en reposo...")
        cap = capture(th, args)
        if cap['n_used'] == 0:
            print("ERROR: 0 frames validos.", file=sys.stderr)
            return 1
        res = analyze_and_report(cap, excl, excl_src, args)
        os.makedirs(args.outdir, exist_ok=True)
        out = os.path.join(args.outdir, f"a1_noise_taxels{('_'+args.tag) if args.tag else ''}.csv")
        write_csv(out, cap, excl, res, args)
        print(f"\n  Salida: {out}")
        return 0
    except KeyboardInterrupt:
        print("\n[interrumpido — mano a estado seguro]")
        return 0
    finally:
        if not args.no_safe_open:
            th.open_fingers()
        th.close()


# ── CLI ─────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="A1.1 — ruido en reposo y piso de umbral (táctil RH56DFTP).")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='serial')
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--ip', default='192.168.11.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    # Captura
    p.add_argument('--secs', type=float, default=180.0,
                   help='duracion de la captura en reposo (def 180 s ~ 3 min)')
    p.add_argument('--frames', type=int, default=None,
                   help='si se da, captura N frames en vez de por tiempo')
    p.add_argument('--warmup', type=int, default=10)
    # Analisis
    p.add_argument('--k', type=float, default=5.0,
                   help='k del umbral k·σ y del cerco de ruido (def 5)')
    p.add_argument('--diag', default=os.path.join(os.path.dirname(_HERE),
                   'fase0', 'data', 'taxel_diagnosis.csv'),
                   help='taxel_diagnosis.csv de Fase 0 para la exclusion')
    # Flujo / salida
    p.add_argument('--no-prompt', action='store_true')
    p.add_argument('--no-safe-open', action='store_true')
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))
    p.add_argument('--tag', default='')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    os.makedirs(args.outdir, exist_ok=True)
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
