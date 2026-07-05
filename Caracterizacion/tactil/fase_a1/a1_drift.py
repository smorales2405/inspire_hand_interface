#!/usr/bin/env python3
"""A1.2 — Deriva sin carga desde frío (táctil RH56DFTP).

Segundo sub-experimento de la Fase A. Loguea el táctil EN REPOSO (sin contacto)
durante 20-30 min ARRANCANDO EN FRÍO (justo tras power-on), para cuantificar
cuánto se corre el cero al calentarse/asentarse el sensor resistivo. Correlaciona
el baseline por taxel/zona contra el TIEMPO y la TEMPERATURA de los actuadores.

Es la evidencia (junto con A1.3) para la decisión de re-cero: si la deriva es
comparable o mayor que el piso de umbral de A1.1 (abs_floor≈41 counts), un cero
fijo de sesión NO basta y hay que usar baseline adaptativo.

Standalone: NO importa PyQt. Un proceso/hilo/cliente, time.perf_counter(), estado
seguro al salir. Correr con la GUI CERRADA.

Temperatura: 6 actuadores desde TEMP (1618..1623, 1 temp/reg; confirmado por
lectura cruda). Orden: 0 meñique, 1 ring, 2 medio, 3 INDICE, 4 pulgar-flex,
5 pulgar-rot. El índice es el dedo de prueba -> proxy térmico principal.

Uso (¡power-cycle la mano justo antes!):
    .venv/bin/python Caracterizacion/tactil/fase_a1/a1_drift.py \
        --transport serial --serial-port /dev/ttyUSB0 --baud 115200 --mins 25
"""
from __future__ import annotations

import argparse
import math
import os
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                       # para importar a1_noise (hermano)
sys.path.insert(0, os.path.dirname(_HERE))      # Caracterizacion/tactil/

from hand_tactile import (                       # noqa: E402
    TactileHand, ZONES, N_ZONES, TAXELS, ZONE_SLICES, N_TAXELS, taxel_label,
)
from a1_noise import percentile, load_exclusion  # noqa: E402


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


# ── Captura con acumulacion por-bucket y ventanas inicio/fin ────────────────

def capture(th, args, excl):
    """Loguea frames en reposo por --mins. Acumula:

    - buckets temporales de --bucket-s: media por zona (solo buenos) + temp.
    - ventanas de inicio/fin (--window-s) por taxel: baseline_start / baseline_end.
    Devuelve dict con series y baselines.
    """
    good = [t for t in range(N_TAXELS) if t not in excl]
    dur = args.mins * 60.0

    buckets = []            # cada uno: dict(t, temp_raw, temp_dec, zmean[17], gmean, gmed)
    b_t0 = 0.0
    b_s1 = [0.0] * N_TAXELS
    b_n = 0

    # Ventanas por-taxel (baseline estable de inicio y de fin).
    start_s1 = [0.0] * N_TAXELS
    start_n = 0
    end_s1 = [0.0] * N_TAXELS
    end_n = 0

    n_used = 0
    n_dropped = 0
    dt_ms = []

    for _ in range(args.warmup):
        th.read_frame_flat()

    # Pre-agrupa taxeles buenos por zona para la media por zona del bucket.
    good_by_zone = [[] for _ in range(N_ZONES)]
    for t in good:
        good_by_zone[TAXELS[t][0]].append(t)

    temp_start = th.read_temps()
    t0 = time.perf_counter()
    t_prev = t0

    def make_bucket(now_rel):
        zmean = []
        for zi in range(N_ZONES):
            gs = good_by_zone[zi]
            zmean.append((sum(b_s1[t] for t in gs) / (b_n * len(gs)))
                         if gs else float('nan'))
        gvals = [b_s1[t] / b_n for t in good]
        return {
            't': now_rel,
            'temp': th.read_temps(),
            'zmean': zmean,
            'gmean': statistics.fmean(gvals) if gvals else float('nan'),
            'gmed': statistics.median(gvals) if gvals else float('nan'),
        }

    while True:
        now = time.perf_counter()
        rel = now - t0
        if rel >= dur:
            break
        flat, _f = th.read_frame_flat()
        t_now = time.perf_counter()
        if flat is None:
            n_dropped += 1
            t_prev = t_now
            if n_dropped > 20000:
                break
            continue
        dt_ms.append((t_now - t_prev) * 1000.0)
        t_prev = t_now
        n_used += 1

        for i, v in enumerate(flat):
            b_s1[i] += v
        b_n += 1

        # Ventanas inicio/fin (por taxel).
        if rel <= args.window_s:
            for i, v in enumerate(flat):
                start_s1[i] += v
            start_n += 1
        if rel >= dur - args.window_s:
            for i, v in enumerate(flat):
                end_s1[i] += v
            end_n += 1

        # Cierre de bucket temporal.
        if rel - b_t0 >= args.bucket_s:
            buckets.append(make_bucket(rel))
            b_t0 = rel
            b_s1 = [0.0] * N_TAXELS
            b_n = 0

    if b_n:
        buckets.append(make_bucket(time.perf_counter() - t0))
    elapsed = time.perf_counter() - t0
    temp_end = th.read_temps()

    mu_start = [start_s1[t] / start_n if start_n else float('nan') for t in range(N_TAXELS)]
    mu_end = [end_s1[t] / end_n if end_n else float('nan') for t in range(N_TAXELS)]

    return {
        'buckets': buckets, 'mu_start': mu_start, 'mu_end': mu_end,
        'start_n': start_n, 'end_n': end_n, 'n_used': n_used,
        'n_dropped': n_dropped, 'elapsed': elapsed, 'dt_ms': dt_ms,
        'temp_start': temp_start, 'temp_end': temp_end,
        'good': good,
    }


# ── Analisis + reporte ──────────────────────────────────────────────────────

def analyze_and_report(cap, args):
    good = cap['good']
    ms, me = cap['mu_start'], cap['mu_end']
    delta = {t: me[t] - ms[t] for t in good
             if ms[t] == ms[t] and me[t] == me[t]}
    dvals = list(delta.values())
    absd = sorted(abs(d) for d in dvals)

    print()
    print("=" * 66)
    print(" A1.2 — Deriva sin carga desde frío (táctil)")
    print("=" * 66)
    print(f" Duracion   : {cap['elapsed']/60:.1f} min  ({cap['n_used']} frames, "
          f"descartados {cap['n_dropped']})"
          + (f", {1000.0/statistics.fmean(cap['dt_ms']):.1f} Hz"
             if cap['dt_ms'] else ""))
    print(f" Ventanas   : inicio {cap['start_n']} frames / fin {cap['end_n']} frames"
          f" (±{args.window_s:.0f} s)")
    _report_temp(cap)
    print("-" * 66)
    print(f" Deriva del cero por taxel (|μ_fin − μ_inicio|), counts, buenos={len(good)}:")
    if absd:
        print(f"   med {statistics.median(absd):.2f}   p95 {percentile(absd,95):.2f}"
              f"   p99 {percentile(absd,99):.2f}   max {absd[-1]:.2f}")
        over = sum(1 for d in absd if d > args.abs_floor)
        print(f"   taxeles con |Δ| > abs_floor({args.abs_floor}): {over} / {len(absd)}"
              f"   ({100.0*over/len(absd):.1f}%)")
        # Deriva global (media de buenos) inicio->fin.
        gm_s = statistics.fmean([ms[t] for t in good if ms[t] == ms[t]])
        gm_e = statistics.fmean([me[t] for t in good if me[t] == me[t]])
        print(f"   deriva global (media de buenos): {gm_s:.2f} -> {gm_e:.2f} "
              f"(Δ={gm_e-gm_s:+.2f} counts)")
    print("-" * 66)
    _report_gate(absd, args)
    # Deriva por zona (media de |Δ|).
    print(" Deriva por zona (media de |Δ| sobre buenos, counts):")
    by_zone = {}
    for t, d in delta.items():
        by_zone.setdefault(TAXELS[t][0], []).append(abs(d))
    for zi in range(N_ZONES):
        if zi in by_zone:
            v = by_zone[zi]
            print(f"   z{zi:<2} {ZONES[zi][0]:20s} n={len(v):3d}  "
                  f"med={statistics.median(v):5.2f}  max={max(v):6.2f}")
    print("=" * 66)
    return {'delta': delta}


def _report_gate(absd, args):
    if not absd:
        return
    p95 = percentile(absd, 95)
    print(" Compuerta de re-cero (preliminar; definitiva al cerrar A1 con A1.3):")
    if p95 <= args.abs_floor * 0.5:
        print(f"   Deriva BAJA (p95 |Δ|={p95:.1f} ≤ ½·abs_floor). Un cero fijo de")
        print("   sesion podria bastar. Confirmar con A1.3 (creep bajo carga).")
    else:
        print(f"   Deriva APRECIABLE (p95 |Δ|={p95:.1f} vs abs_floor={args.abs_floor}).")
        print("   Un cero fijo NO basta -> baseline adaptativo / re-cero periodico.")


TEMP_LABELS = ['meñique', 'ring', 'medio', 'INDICE', 'pulgar-flex', 'pulgar-rot']


def _report_temp(cap):
    ts, te = cap['temp_start'], cap['temp_end']
    if not ts or not te:
        print(" Temperatura : (no disponible)")
        return
    print(" Temperatura actuadores (C):")
    print(f"   {'':12s} " + "  ".join(f"{l:>11s}" for l in TEMP_LABELS))
    print(f"   {'inicio':12s} " + "  ".join(f"{v:>11d}" for v in ts))
    print(f"   {'final':12s} " + "  ".join(f"{v:>11d}" for v in te))
    print(f"   {'ΔT':12s} " + "  ".join(f"{te[i]-ts[i]:>+11d}" for i in range(len(te))))
    print(f"   (índice = proxy térmico del dedo de prueba: "
          f"{ts[3]}->{te[3]} C, ΔT={te[3]-ts[3]:+d})")


# ── Salidas CSV ─────────────────────────────────────────────────────────────

def write_timeseries_csv(path, cap):
    tcols = ["t_little", "t_ring", "t_middle", "t_index", "t_thumbB", "t_thumbR"]
    with open(path, 'w') as f:
        cols = (["t_s"] + tcols + ["gmean", "gmed"]
                + [f"z{zi}_mean" for zi in range(N_ZONES)])
        f.write(",".join(cols) + "\n")
        for b in cap['buckets']:
            tr = b['temp'] or [''] * 6
            row = [f"{b['t']:.2f}"] + [str(x) for x in (list(tr) + [''] * 6)[:6]]
            row += [f"{b['gmean']:.3f}", f"{b['gmed']:.3f}"]
            row += [("" if z != z else f"{z:.3f}") for z in b['zmean']]
            f.write(",".join(row) + "\n")


def write_drift_csv(path, cap, excl):
    ms, me = cap['mu_start'], cap['mu_end']
    with open(path, 'w') as f:
        f.write("taxel,zone,zone_name,row,col,mu_start,mu_end,delta,excluded\n")
        for t in range(N_TAXELS):
            zi, name, r, c, _addr = TAXELS[t]
            s = '' if ms[t] != ms[t] else f"{ms[t]:.3f}"
            e = '' if me[t] != me[t] else f"{me[t]:.3f}"
            d = '' if (ms[t] != ms[t] or me[t] != me[t]) else f"{me[t]-ms[t]:.3f}"
            f.write(f"{t},{zi},{name},{r},{c},{s},{e},{d},{int(t in excl)}\n")


# ── Orquestacion ────────────────────────────────────────────────────────────

def run(args):
    th, target = connect(args)
    if th is None:
        print("ERROR: no se pudo establecer la conexion Modbus.", file=sys.stderr)
        return 1
    print(f"Conectado a {target} (device_id={args.device_id}).")
    excl, excl_src = load_exclusion(args.diag)
    print(f"Exclusion Fase 0: {len(excl)} taxeles ({excl_src})")

    try:
        if not args.no_prompt:
            print("\nA1.2: la mano debe estar RECIEN ENCENDIDA (en frío) y en reposo,")
            print(f"      SIN contacto. Voy a loguear {args.mins:.0f} min.")
            input("      [Enter] para empezar... ")
        print("  Logueando deriva en reposo...")
        cap = capture(th, args, excl)
        if cap['n_used'] == 0:
            print("ERROR: 0 frames validos.", file=sys.stderr)
            return 1
        analyze_and_report(cap, args)
        os.makedirs(args.outdir, exist_ok=True)
        tag = f"_{args.tag}" if args.tag else ""
        ts = os.path.join(args.outdir, f"a1_drift_timeseries{tag}.csv")
        dr = os.path.join(args.outdir, f"a1_drift_taxels{tag}.csv")
        write_timeseries_csv(ts, cap)
        write_drift_csv(dr, cap, excl)
        print(f"\n  Salidas:\n    serie temporal : {ts}\n    deriva/taxel   : {dr}")
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
        description="A1.2 — deriva sin carga desde frío (táctil RH56DFTP).")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='serial')
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--ip', default='192.168.11.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    # Captura
    p.add_argument('--mins', type=float, default=25.0,
                   help='duracion del logueo en minutos (def 25)')
    p.add_argument('--bucket-s', dest='bucket_s', type=float, default=15.0,
                   help='periodo de agregado temporal en s (def 15)')
    p.add_argument('--window-s', dest='window_s', type=float, default=60.0,
                   help='ventana de baseline de inicio/fin por taxel en s (def 60)')
    p.add_argument('--warmup', type=int, default=10)
    # Analisis
    p.add_argument('--abs-floor', dest='abs_floor', type=float, default=41.0,
                   help='piso de umbral de A1.1 para comparar la deriva (def 41)')
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
