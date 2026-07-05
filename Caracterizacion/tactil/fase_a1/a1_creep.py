#!/usr/bin/env python3
"""A1.3 — Creep y recuperación bajo carga constante (táctil RH56DFTP).

Tercer sub-experimento de la Fase A y el MÁS crítico para la decisión de re-cero:
Fase 0 ya vio ~6% FS de no-recuperación tras un contacto. Aquí se cuantifica con
un peso constante y conocido:

  (a) CREEP    — cómo cambia el crudo bajo fuerza CONSTANTE durante el hold.
  (b) RECUPERACIÓN — al retirar el peso, ¿vuelve al baseline? ¿queda offset
      residual, de cuánto y en cuánto tiempo se disipa?

Lee UNA sola zona (más rápido, ~32 Hz) para resolver los transitorios de carga/
descarga. Respuesta de zona = SUMA del crudo (sobre baseline) en el parche de
taxeles cargados — robusta a la colocación. Excluye los taxeles muertos de Fase 0.

Standalone: NO importa PyQt. Un proceso/hilo/cliente, perf_counter(), estado
seguro al salir. Correr con la GUI CERRADA.

Montaje: la zona objetivo HACIA ARRIBA, plana, para que el peso calibrado apoye
estable y cargue siempre los mismos taxeles. Da la masa con --load-g (F=m·g).

Uso:
    .venv/bin/python Caracterizacion/tactil/fase_a1/a1_creep.py \
        --transport serial --serial-port /dev/ttyUSB0 --baud 115200 \
        --zone 10 --load-g 100 --hold-mins 4 --recover-mins 4
"""
from __future__ import annotations

import argparse
import math
import os
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from hand_tactile import TactileHand, ZONES, ZONE_SLICES, N_TAXELS  # noqa: E402
from a1_noise import load_exclusion                                 # noqa: E402

G_TO_N = 9.80665 / 1000.0


def connect(args):
    if args.transport == 'tcp':
        th = TactileHand.open_tcp(args.ip, args.port, args.device_id, args.timeout)
        target = f"TCP {args.ip}:{args.port}"
    else:
        th = TactileHand.open_serial(args.serial_port, args.baud,
                                     args.device_id, args.timeout)
        target = f"serial {args.serial_port} @ {args.baud} baud"
    return th, target


def prompt(msg):
    try:
        return input(msg)
    except (EOFError, KeyboardInterrupt):
        print()
        raise KeyboardInterrupt


def median_window(samples, t_lo, t_hi):
    """Mediana de la respuesta en la ventana temporal [t_lo, t_hi] (s)."""
    vals = [r for (t, r, _tmp) in samples if t_lo <= t <= t_hi]
    return statistics.median(vals) if vals else float('nan')


# ── Captura de una zona a máxima tasa ───────────────────────────────────────

def capture_baseline_zone(th, zi, secs, keep):
    """Media por taxel (local) de la zona zi en reposo por `secs`. keep=índices locales."""
    n = ZONES[zi][2]
    s1 = [0.0] * n
    got = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < secs:
        z = th.read_zone(zi)
        if z is None:
            continue
        for k in keep:
            s1[k] += z[k]
        got += 1
    return ([s1[k] / got if got else 0.0 for k in range(n)], got)


def log_hold_recover(th, zi, baseline, patch, hold_s, recover_s, samples,
                     temp_every=1.0):
    """Registro CONTINUO de hold + recuperación, SIN cortar en el retiro.

    Loguea hold_s bajo carga (phase 'hold', t desde 0); al cumplirse hold_s avisa
    por consola para retirar el peso y sigue logueando recover_s (phase 'recover',
    t desde 0 en el aviso) -> captura el decaimiento, que antes se perdía en el
    prompt de retiro. Devuelve (nh, nr, tasa_Hz).
    """
    t0 = time.perf_counter()
    nh = nr = 0
    last_temp_t = -1e9
    temp_idx = None
    cued = False
    total = hold_s + recover_s
    while True:
        now = time.perf_counter()
        rel = now - t0
        if rel >= total:
            break
        if not cued and rel >= hold_s:
            print("\n  >>> RETIRA EL PESO AHORA "
                  "(sigo registrando la recuperación) <<<\n")
            cued = True
        z = th.read_zone(zi)
        if z is None:
            continue
        resp = sum(z[k] - baseline[k] for k in patch)
        if now - last_temp_t >= temp_every:
            t6 = th.read_temps()
            temp_idx = t6[3] if t6 else None
            last_temp_t = now
        if rel < hold_s:
            samples.append(('hold', rel, resp, temp_idx))
            nh += 1
        else:
            samples.append(('recover', rel - hold_s, resp, temp_idx))
            nr += 1
    dur = time.perf_counter() - t0
    return nh, nr, ((nh + nr) / dur if dur > 0 else float('nan'))


# ── Orquestación ────────────────────────────────────────────────────────────

def run(args):
    th, target = connect(args)
    if th is None:
        print("ERROR: no se pudo establecer la conexion Modbus.", file=sys.stderr)
        return 1
    zi = args.zone
    zname, _addr, n, grid = ZONES[zi]
    print(f"Conectado a {target} (device_id={args.device_id}).")
    print(f"Zona objetivo: z{zi} {zname} ({grid[0]}x{grid[1]}, {n} tax)")

    # Taxeles a considerar. Por defecto TODOS: el umbral de subida (detect_thr)
    # ya filtra los que no responden, y en zonas grandes la exclusion de Fase 0
    # (artefactos de cobertura del barrido manual) puede quitar justo los taxeles
    # donde apoya la carga. Con --exclude se aplica la exclusion de Fase 0.
    if args.exclude:
        excl, _src = load_exclusion(args.diag)
    else:
        excl = set()
    z0, z1 = ZONE_SLICES[zi]
    keep = [k for k in range(n) if (z0 + k) not in excl]
    if not keep:
        print("ERROR: la zona no tiene taxeles considerables.", file=sys.stderr)
        return 1
    print(f"Taxeles considerados: {len(keep)}/{n}"
          + (" (exclusion Fase 0)" if args.exclude else " (sin exclusion)"))

    samples = []          # (phase, t_rel_fase, response, temp_index)
    try:
        if args.monitor:
            return run_monitor(th, zi, keep, args)
        # 1) Baseline en reposo.
        if not args.no_prompt:
            prompt(f"\n[1/3] Zona {zname} HACIA ARRIBA, SIN peso, en reposo. "
                   f"[Enter] para baseline ({args.settle_s:.0f} s)... ")
        print("  Capturando baseline...")
        baseline, bn = capture_baseline_zone(th, zi, args.settle_s, keep)
        print(f"  baseline: {bn} muestras")

        # 2) Aplicar peso -> detectar parche.
        wtxt = f" (~{args.load_g} g, {args.load_g*G_TO_N:.2f} N)" if args.load_g else ""
        if not args.no_prompt:
            prompt(f"\n[2/3] APLICA el peso{wtxt} sobre la zona, estable. "
                   f"[Enter] cuando este puesto... ")
        # Detecta el parche cargado.
        pk = [0.0] * n
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < args.patch_secs:
            z = th.read_zone(zi)
            if z is None:
                continue
            for k in keep:
                pk[k] = max(pk[k], z[k] - baseline[k])
        patch = [k for k in keep if pk[k] > args.detect_thr]
        if not patch:
            print(f"  AVISO: ningun taxel supero detect_thr={args.detect_thr}. "
                  f"Uso los {min(8,len(keep))} de mayor subida.")
            patch = sorted(keep, key=lambda k: -pk[k])[:min(8, len(keep))]
        print(f"  parche cargado: {len(patch)} taxeles "
              f"(pico max {max(pk):.0f} counts)")
        if not args.no_prompt:
            prompt("     ¿parche OK? [Enter] inicia el hold "
                   "(Ctrl-C para reajustar carga/umbral)... ")

        # HOLD (creep) + RECUPERACION en un registro CONTINUO: se avisa por
        # pantalla para retirar el peso sin cortar el log -> captura el decaimiento.
        print(f"  [3/3] HOLD {args.hold_mins:.1f} min (creep); luego te aviso "
              f"para retirar y sigo {args.recover_mins:.1f} min de recuperacion.")
        nh, nr, hz = log_hold_recover(
            th, zi, baseline, patch, args.hold_mins * 60.0,
            args.recover_mins * 60.0, samples, args.temp_every)
        print(f"    hold {nh} + recuperacion {nr} muestras @ {hz:.1f} Hz")

        report(args, zi, zname, patch, baseline, samples)
        os.makedirs(args.outdir, exist_ok=True)
        tag = f"_{args.tag}" if args.tag else f"_z{zi}"
        out = os.path.join(args.outdir, f"a1_creep_timeseries{tag}.csv")
        write_csv(out, samples)
        print(f"\n  Salida: {out}")
        return 0
    except KeyboardInterrupt:
        print("\n[interrumpido — mano a estado seguro]")
        if samples:
            os.makedirs(args.outdir, exist_ok=True)
            out = os.path.join(args.outdir, f"a1_creep_timeseries_partial.csv")
            write_csv(out, samples)
            print(f"  (guardado parcial: {out})")
        return 0
    finally:
        if not args.no_safe_open:
            th.open_fingers()
        th.close()


def run_monitor(th, zi, keep, args):
    """Monitor en vivo: muestra la respuesta de la zona vs baseline hasta Ctrl-C.

    Para verificar contacto/colocacion de la carga (o que el sensor este vivo,
    presionando con un dedo) antes de comprometer una corrida larga.
    """
    n = ZONES[zi][2]
    cols = ZONES[zi][3][1]
    if not args.no_prompt:
        prompt("\nMONITOR: zona en reposo SIN carga. [Enter] para baseline (5 s)... ")
    baseline, bn = capture_baseline_zone(th, zi, 5.0, keep)
    print(f"  baseline: {bn} muestras. Coloca/ajusta la carga (o presiona con un")
    print("  dedo para ver si el sensor responde). Ctrl-C para salir.\n")
    try:
        while True:
            pk = [0.0] * n
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < 0.5:
                z = th.read_zone(zi)
                if z is None:
                    continue
                for k in keep:
                    d = z[k] - baseline[k]
                    if d > pk[k]:
                        pk[k] = d
            mk = max(keep, key=lambda k: pk[k])
            over = [k for k in keep if pk[k] > args.detect_thr]
            r, c = divmod(mk, cols)
            print(f"  max_rise={pk[mk]:7.1f} @r{r}c{c}   "
                  f">{args.detect_thr:.0f}: {len(over):3d} tax   "
                  f"suma_parche={sum(pk[k] for k in over):8.0f}")
    except KeyboardInterrupt:
        print("\n[fin monitor]")
    return 0


def report(args, zi, zname, patch, baseline, samples):
    hold = [(t, r) for (ph, t, r, _tp) in samples if ph == 'hold']
    rec = [(t, r) for (ph, t, r, _tp) in samples if ph == 'recover']
    if not hold:
        print("  (sin muestras de hold)")
        return
    hold_dur = hold[-1][0]
    w = args.edge_s
    R0 = statistics.median([r for t, r in hold if t <= w])           # inicio hold
    R1 = statistics.median([r for t, r in hold if t >= hold_dur - w])  # fin hold
    creep = (R1 - R0) / R0 * 100.0 if R0 else float('nan')

    print()
    print("=" * 64)
    print(f" A1.3 — Creep y recuperación · z{zi} {zname}")
    print("=" * 64)
    if args.load_g:
        print(f" Carga        : {args.load_g} g  ({args.load_g*G_TO_N:.2f} N)")
    print(f" Parche       : {len(patch)} taxeles")
    print(f" Respuesta (suma counts sobre baseline):")
    print(f"   R0 (inicio hold, ≤{w:.0f}s) : {R0:.0f}")
    print(f"   R1 (fin hold, ≥T-{w:.0f}s)  : {R1:.0f}")
    print(f"   CREEP = (R1-R0)/R0        : {creep:+.1f} %  en {hold_dur/60:.1f} min")
    if rec:
        rec_dur = rec[-1][0]
        Rrec0 = statistics.median([r for t, r in rec if t <= w])   # aun cargado (~R1)
        Rres = statistics.median([r for t, r in rec if t >= rec_dur - w])
        resid_pct = Rres / R0 * 100.0 if R0 else float('nan')
        print(" Recuperacion (t=0 = aviso de retiro; +~1s de reaccion al soltar):")
        print(f"   respuesta al inicio (aun cargada) : {Rrec0:.0f}")
        print(f"   residual (fin, ≥T-{w:.0f}s)        : {Rres:.0f}  "
              f"({resid_pct:+.1f} % de R0)")
        # Tiempo hasta bajar a fracciones de R0.
        for frac in (0.5, 0.1, 0.05):
            tt = _time_below(rec, frac * R0)
            lbl = f"{int(frac*100)}%"
            print(f"   t hasta ≤{lbl:>3} de R0     : "
                  + (f"{tt:.1f} s" if tt is not None else "no alcanzado"))
        # Veredicto de re-cero.
        print("-" * 64)
        if abs(resid_pct) <= 5 and abs(creep) <= 10:
            print(" Compuerta re-cero: creep y residual BAJOS -> un CERO FIJO de")
            print("   sesion puede bastar (revisar junto con A1.2).")
        else:
            print(" Compuerta re-cero: creep/residual APRECIABLES -> baseline")
            print("   ADAPTATIVO / re-cero por-toque (el crudo NO mapea a una fuerza")
            print("   unica; condiciona la calibracion de A2/A3).")
    print("=" * 64)


def _time_below(rec, thr):
    """Primer t (s) en que la respuesta de recuperacion cae <= thr y se mantiene."""
    for i, (t, r) in enumerate(rec):
        if r <= thr:
            # confirma que no vuelve a subir por encima en las siguientes 10 muestras
            if all(rr <= thr * 1.15 for _tt, rr in rec[i:i + 10]):
                return t
    return None


def write_csv(path, samples):
    with open(path, 'w') as f:
        f.write("phase,t_s,response,temp_index\n")
        for ph, t, r, tp in samples:
            f.write(f"{ph},{t:.4f},{r:.2f},{'' if tp is None else tp}\n")


# ── CLI ─────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="A1.3 — creep y recuperación bajo carga constante (táctil).")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='serial')
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--ip', default='192.168.11.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    # Experimento
    p.add_argument('--zone', type=int, default=10,
                   help='zona objetivo (def 10 = Índice·Distal, pad 12x8)')
    p.add_argument('--load-g', dest='load_g', type=float, default=None,
                   help='masa del peso calibrado en g (para F=m·g; metadato)')
    p.add_argument('--settle-s', dest='settle_s', type=float, default=30.0,
                   help='baseline en reposo antes de cargar (s)')
    p.add_argument('--hold-mins', dest='hold_mins', type=float, default=4.0,
                   help='duracion del hold bajo carga (min)')
    p.add_argument('--recover-mins', dest='recover_mins', type=float, default=4.0,
                   help='duracion de la recuperacion tras retirar (min)')
    p.add_argument('--patch-secs', dest='patch_secs', type=float, default=2.0,
                   help='ventana para detectar el parche cargado (s)')
    p.add_argument('--detect-thr', dest='detect_thr', type=float, default=41.0,
                   help='umbral de subida para el parche (def 41 = abs_floor A1.1)')
    p.add_argument('--edge-s', dest='edge_s', type=float, default=5.0,
                   help='ventana para medianas de R0/R1/residual (s)')
    p.add_argument('--temp-every', dest='temp_every', type=float, default=2.0,
                   help='cada cuantos s leer la temperatura (s)')
    # Analisis / flujo
    p.add_argument('--diag', default=os.path.join(os.path.dirname(_HERE),
                   'fase0', 'data', 'taxel_diagnosis.csv'),
                   help='taxel_diagnosis.csv de Fase 0 (solo con --exclude)')
    p.add_argument('--exclude', action='store_true',
                   help='aplica la exclusion de Fase 0 (por defecto NO; el umbral '
                        'de subida ya filtra, y en zonas grandes la exclusion '
                        'puede quitar los taxeles cargados)')
    p.add_argument('--monitor', action='store_true',
                   help='monitor en vivo de la respuesta de la zona (verificar '
                        'contacto/colocacion); no corre el experimento')
    p.add_argument('--no-prompt', action='store_true')
    p.add_argument('--no-safe-open', action='store_true')
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))
    p.add_argument('--tag', default='')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not (0 <= args.zone < len(ZONES)):
        print(f"ERROR: --zone en [0,{len(ZONES)-1}]", file=sys.stderr)
        return 2
    os.makedirs(args.outdir, exist_ok=True)
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
