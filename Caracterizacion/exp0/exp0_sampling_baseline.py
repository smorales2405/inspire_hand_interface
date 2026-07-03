#!/usr/bin/env python3
"""Experimento 0 — Baseline de muestreo de FORCE_ACT (Inspire RH56DFTP).

Standalone: NO importa PyQt ni la GUI. Un solo proceso, un solo hilo,
un solo cliente Modbus. Lee en lazo cerrado el bloque de los 6 registros
FORCE_ACT N veces y caracteriza la tasa de muestreo y su jitter.

Objetivo: confirmar que el bus sostiene >= 100 Hz de lectura del bloque de
fuerzas, que es la senal critica para la caracterizacion dinamica.

IMPORTANTE: correr con la GUI CERRADA. El cliente pymodbus no es thread-safe
y la GUI abre otro cliente sobre el mismo bus; comparten transacciones y
falsearian el baseline.

Uso rapido (TCP):
    .venv/bin/python characterization/exp0_sampling_baseline.py \
        --transport tcp --ip 192.168.11.210 --port 6000

Serial:
    .venv/bin/python characterization/exp0_sampling_baseline.py \
        --transport serial --serial-port /dev/ttyUSB0 --baud 115200
"""
from __future__ import annotations

import argparse
import math
import statistics
import struct
import sys
import time

from pymodbus.client import ModbusTcpClient, ModbusSerialClient


# ── Mapa de registros (direcciones absolutas del manual, sin offset) ──────
# Coincide con core/hand_connection.py (read_forces -> _read_shorts(1582, 6)).
FORCE_ACT_ADDR = 1582      # FORCE_ACT(0-5): 6 registros contiguos
FORCE_ACT_COUNT = 6

# FORCE_ACT viene en gramos-fuerza con signo (int16, rango -4000..4000).
G_TO_N = 9.80665 / 1000.0  # gramos-fuerza -> Newton


# ── Helpers ───────────────────────────────────────────────────────────────

def decode_signed_block(registers):
    """uint16 crudos de pymodbus -> int16 con signo.

    Identico a HandConnection._read_shorts, para que las magnitudes sean
    comparables con el path de produccion.
    """
    n = len(registers)
    packed = struct.pack('>' + 'H' * n, *registers)
    return list(struct.unpack('>' + 'h' * n, packed))


def percentile(sorted_vals, pct):
    """Percentil por interpolacion lineal (metodo 'linear' de numpy).

    `sorted_vals` debe venir ordenado ascendente.
    """
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


def build_client(args):
    """Crea el unico cliente Modbus segun el transporte elegido."""
    if args.transport == 'tcp':
        client = ModbusTcpClient(args.ip, port=args.port, timeout=args.timeout)
        target = f"TCP {args.ip}:{args.port}"
    else:
        client = ModbusSerialClient(
            port=args.serial_port, baudrate=args.baud, timeout=args.timeout
        )
        target = f"serial {args.serial_port} @ {args.baud} baud"
    return client, target


# ── Nucleo del experimento ─────────────────────────────────────────────────

def run(args):
    client, target = build_client(args)
    print(f"Conectando a {target} (device_id={args.device_id}) ...")
    if not client.connect():
        print("ERROR: no se pudo establecer la conexion Modbus.", file=sys.stderr)
        return 1

    dts_ms = []          # periodo entre muestras consecutivas, en ms
    oks = []             # exito/fallo por muestra
    first_sample = None  # primera lectura decodificada (sanity check)
    t0 = None

    try:
        # Warmup: descartar las primeras lecturas (slow-start TCP / 1ra trama).
        for _ in range(args.warmup):
            try:
                client.read_holding_registers(
                    FORCE_ACT_ADDR, FORCE_ACT_COUNT, args.device_id
                )
            except Exception:
                pass

        # Lazo cronometrado. dt_i = periodo entre el fin de la muestra i-1 y
        # el fin de la muestra i. La suma de dt == tiempo total, de modo que
        # tasa_media = N / total = 1 / mean(dt), consistente por construccion.
        t_prev = time.perf_counter()
        t0 = t_prev
        for _ in range(args.n):
            ok = False
            resp = None
            try:
                resp = client.read_holding_registers(
                    FORCE_ACT_ADDR, FORCE_ACT_COUNT, args.device_id
                )
                ok = not resp.isError()
            except Exception:
                ok = False
            t_now = time.perf_counter()
            dts_ms.append((t_now - t_prev) * 1000.0)
            t_prev = t_now
            oks.append(ok)
            if ok and first_sample is None:
                first_sample = decode_signed_block(resp.registers)
        wall = time.perf_counter() - t0
    except KeyboardInterrupt:
        wall = (time.perf_counter() - t0) if t0 is not None else 0.0
        print("\n[interrumpido — reporto muestras parciales]")
    finally:
        client.close()

    report(args, target, dts_ms, oks, wall, first_sample)
    return 0


def report(args, target, dts_ms, oks, wall, first_sample):
    n = len(dts_ms)
    n_ok = sum(oks)
    n_err = n - n_ok
    mean_rate = n / wall if wall > 0 else float('nan')

    s = sorted(dts_ms)
    mean_dt = statistics.fmean(dts_ms) if dts_ms else float('nan')
    std_dt = statistics.pstdev(dts_ms) if len(dts_ms) > 1 else 0.0

    print()
    print("=" * 58)
    print(" Exp 0 — Baseline de muestreo (bloque FORCE_ACT x6)")
    print("=" * 58)
    print(f" Transporte     : {target}  (device_id={args.device_id})")
    print(f" Muestras (N)   : {n}   (warmup descartado: {args.warmup})")
    print(f" Errores        : {n_err} / {n}"
          + ("   <-- ATENCION" if n_err else ""))
    if first_sample is not None:
        newtons = [round(g * G_TO_N, 3) for g in first_sample]
        print(f" 1ra lectura    : {first_sample} g")
        print(f"                  {newtons} N")
    print("-" * 58)
    print(f" Tiempo total   : {wall:.3f} s")
    verdict = 'OK' if mean_rate >= 100.0 else 'NO CUMPLE'
    print(f" Tasa media     : {mean_rate:8.1f} Hz   "
          f"[objetivo >= 100 Hz: {verdict}]")
    print(" Periodo dt (ms):")
    if s:
        print(f"   media : {mean_dt:8.3f}   (sd {std_dt:.3f})")
        print(f"   min   : {s[0]:8.3f}")
        print(f"   p50   : {percentile(s, 50):8.3f}")
        print(f"   p95   : {percentile(s, 95):8.3f}")
        print(f"   p99   : {percentile(s, 99):8.3f}")
        print(f"   max   : {s[-1]:8.3f}")
    else:
        print("   (sin muestras)")
    print("=" * 58)
    if n_err:
        print(" NOTA: hubo lecturas fallidas; tasa y percentiles las incluyen")
        print("       (un timeout aparece como un pico grande de dt).")
    if args.csv:
        _write_csv(args.csv, dts_ms, oks)
        print(f" Serie dt guardada en: {args.csv}")


def _write_csv(path, dts_ms, oks):
    with open(path, 'w') as f:
        f.write("index,dt_ms,ok\n")
        for i, (dt, ok) in enumerate(zip(dts_ms, oks)):
            f.write(f"{i},{dt:.6f},{int(ok)}\n")


# ── CLI ─────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Exp 0 — baseline de muestreo de FORCE_ACT (Inspire RH56DFTP)."
    )
    p.add_argument('--n', type=int, default=2000,
                   help='numero de lecturas cronometradas (def 2000)')
    p.add_argument('--warmup', type=int, default=10,
                   help='lecturas de calentamiento descartadas (def 10)')
    p.add_argument('--transport', choices=['tcp', 'serial'], default='tcp',
                   help='transporte Modbus (def tcp)')
    p.add_argument('--device-id', type=int, default=1,
                   help='ID Modbus del esclavo (def 1)')
    p.add_argument('--timeout', type=float, default=1.0,
                   help='timeout Modbus en s (def 1.0)')
    # TCP
    p.add_argument('--ip', default='192.168.11.210', help='IP (TCP, def 192.168.11.210)')
    p.add_argument('--port', type=int, default=6000, help='puerto (TCP, def 6000)')
    # Serial
    p.add_argument('--serial-port', default='/dev/ttyUSB0',
                   help='puerto serial (def /dev/ttyUSB0)')
    p.add_argument('--baud', type=int, default=115200, help='baudrate serial (def 115200)')
    # Salida opcional
    p.add_argument('--csv', default=None,
                   help='ruta para volcar la serie de dt por muestra (opcional)')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.n < 1:
        print("ERROR: --n debe ser >= 1", file=sys.stderr)
        return 2
    if args.warmup < 0:
        print("ERROR: --warmup debe ser >= 0", file=sys.stderr)
        return 2
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
