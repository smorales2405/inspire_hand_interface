#!/usr/bin/env python3
"""Fase 0 del tactil — Smoke test / mapa vivo (Inspire RH56DFTP).

Standalone: NO importa PyQt ni la GUI. Un solo proceso, un solo hilo, un solo
cliente Modbus, lazo intercalado, time.perf_counter() para TODOS los timestamps.
Al salir deja la mano en estado seguro (dedos abiertos).

Compuerta blanda del punto 2: identifica taxeles muertos/pegados/ruidosos y mide
la tasa real de muestreo ANTES de invertir en las fases caras (A1/A2/A3).

Hace, en orden:
  1. BASELINE EN REPOSO   — N frames completos, mano quieta y sin contacto ->
                            media y desviacion por taxel.
  2. BARRIDO MANUAL GUIADO— presionas una a una las 17 zonas; confirma que la
                            zona sube y las OTRAS no (cross-talk, matriz 17x17).
                            Re-baseline POR ZONA (referencia fresca en reposo antes
                            de cada presion) para des-confundir el cross-talk del
                            offset residual + medir la no-recuperacion acumulada.
  3. DIAGNOSTICO DE TAXELES— marca muertos / pegados-alto / pegados-bajo / ruidosos.
                            Umbrales como parametros; los defaults son TODO hasta
                            ver datos reales.
  4. TASA DE MUESTREO      — Hz de frame completo (17 zonas) y de zona unica, con
                            media y percentiles p50/p95/p99/max de dt.

IMPORTANTE: correr con la GUI CERRADA. pymodbus no es thread-safe y la GUI abre
otro cliente sobre el mismo bus; compartir transacciones falsearia todo.

Uso (serial):
    .venv/bin/python Caracterizacion/tactil/fase0/fase0_smoke_test.py \
        --transport serial --serial-port /dev/ttyUSB0 --baud 115200

Solo tasa (rapido, no interactivo):
    .venv/bin/python Caracterizacion/tactil/fase0/fase0_smoke_test.py \
        --transport serial --serial-port /dev/ttyUSB0 --rate-only

Sin el barrido manual (baseline + tasa; diagnostico parcial):
    ... --skip-barrido
"""
from __future__ import annotations

import argparse
import math
import os
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))     # Caracterizacion/tactil/

from hand_tactile import (                      # noqa: E402
    TactileHand, ZONES, N_ZONES, TAXELS, ZONE_SLICES, N_TAXELS,
    TAXEL_RAW_MAX, taxel_label,
)


# ── Estadistica (pura, sin numpy — igual que el resto del repo) ─────────────

def percentile(sorted_vals, pct):
    """Percentil por interpolacion lineal (metodo 'linear' de numpy)."""
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
    """Mediana de desviaciones absolutas (robusta)."""
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


def prompt(msg):
    """input() con salida limpia ante EOF/Ctrl-C (para el flujo interactivo)."""
    try:
        return input(msg)
    except (EOFError, KeyboardInterrupt):
        print()
        raise KeyboardInterrupt


# ── Paso 1: baseline en reposo ──────────────────────────────────────────────

def capture_baseline(th, n_frames, warmup):
    """Lee n_frames COMPLETOS en reposo -> stats por taxel.

    Devuelve dict con listas de largo N_TAXELS: mu, sigma, mn, mx; y n_used,
    n_dropped, dt_ms (serie por frame completo).
    """
    # Acumuladores por taxel (Welford simplificado: suma y suma de cuadrados).
    s1 = [0.0] * N_TAXELS
    s2 = [0.0] * N_TAXELS
    mn = [float('inf')] * N_TAXELS
    mx = [float('-inf')] * N_TAXELS
    dt_ms = []
    n_used = 0
    n_dropped = 0

    # Warmup (descarta slow-start / 1ra trama).
    for _ in range(warmup):
        th.read_frame_flat()

    t_prev = time.perf_counter()
    while n_used < n_frames:
        flat, failed = th.read_frame_flat()
        t_now = time.perf_counter()
        if flat is None:
            n_dropped += 1
            t_prev = t_now
            if n_dropped > n_frames:          # bus caido: no colgar el proceso
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

    mu = [0.0] * N_TAXELS
    sigma = [0.0] * N_TAXELS
    if n_used:
        for i in range(N_TAXELS):
            m = s1[i] / n_used
            var = max(0.0, s2[i] / n_used - m * m)   # poblacional
            mu[i] = m
            sigma[i] = math.sqrt(var)
    return {
        'mu': mu, 'sigma': sigma, 'mn': mn, 'mx': mx,
        'n_used': n_used, 'n_dropped': n_dropped, 'dt_ms': dt_ms,
    }


# ── Paso 2: barrido manual guiado (cross-talk grueso) ───────────────────────

def capture_ref(th, n_frames, settle=1):
    """Captura n_frames en reposo -> MEDIA por taxel (referencia fresca).

    Devuelve list[N_TAXELS] o None si no se pudo leer ningun frame completo.
    """
    s1 = [0.0] * N_TAXELS
    got = 0
    for _ in range(settle):
        th.read_frame_flat()
    tries = 0
    while got < n_frames and tries < n_frames * 4:
        flat, _ = th.read_frame_flat()
        tries += 1
        if flat is None:
            continue
        for i, v in enumerate(flat):
            s1[i] += v
        got += 1
    if got == 0:
        return None
    return [s / got for s in s1]


def capture_peak(th, n_frames, settle):
    """Captura n_frames bajo presion -> PICO (max) del crudo por taxel.

    Devuelve list[N_TAXELS] o None si no se pudo leer. El rise se calcula fuera
    restando la referencia elegida (fresca por-zona o baseline global).
    """
    peak = [float('-inf')] * N_TAXELS
    got = 0
    # Descarta 'settle' frames para que el usuario ya este presionando.
    for _ in range(settle):
        th.read_frame_flat()
    tries = 0
    while got < n_frames and tries < n_frames * 4:
        flat, _ = th.read_frame_flat()
        tries += 1
        if flat is None:
            continue
        for i, v in enumerate(flat):
            if v > peak[i]:
                peak[i] = v
        got += 1
    if got == 0:
        return None
    return [(p if p != float('-inf') else 0.0) for p in peak]


def run_barrido(th, base, args):
    """Interactivo: presiona zona por zona. Matriz de cross-talk + residual.

    Re-baseline POR ZONA (default): antes de cada presion toma una referencia
    fresca en reposo. El rise queda referido a esa referencia -> des-confunde el
    cross-talk del offset residual de zonas ya presionadas. Ademas, cuanto se
    aparta esa referencia del baseline GLOBAL mide la NO-RECUPERACION acumulada
    (adelanto de A1.3). Con --global-baseline usa el baseline global (previo).

    Devuelve:
      cross_mat[zi][zj]  = max rise sobre los taxeles de zj al presionar zi.
      own_rise[t]        = rise del taxel t cuando se presiono SU zona (o None).
      cross_rise[t]      = max rise del taxel t mientras se presionaba OTRA zona.
      pressed[zi]        = True si la zona zi fue presionada (no saltada).
      resid_max[zi]      = max(referencia_reposo - baseline_global) antes de zi.
      resid_zone[zi]     = zona del taxel que aporta ese residual.
      per_zone_ref       = bool (modo usado).
    """
    base_mu = base['mu']
    per_zone_ref = not args.global_baseline
    cross_mat = [[float('nan')] * N_ZONES for _ in range(N_ZONES)]
    own_rise = [None] * N_TAXELS
    cross_rise = [0.0] * N_TAXELS
    pressed = [False] * N_ZONES
    resid_max = [float('nan')] * N_ZONES
    resid_zone = [-1] * N_ZONES

    print()
    print("── BARRIDO MANUAL GUIADO ─────────────────────────────────────────")
    if per_zone_ref:
        print("  Re-baseline POR ZONA: primero SUELTA todo (reposo) para la")
        print("  referencia, luego PRESIONA la zona y manten. [Enter] avanza,")
        print("  's' salta, 'q' termina. Confirma: la zona sube, las otras casi no.")
    else:
        print("  Baseline GLOBAL (--global-baseline). Presiona y manten; [Enter]")
        print("  captura, 's' salta, 'q' termina.")
    print()

    for zi in range(N_ZONES):
        name, _addr, n, grid = ZONES[zi]

        if per_zone_ref:
            ans = prompt(f"  z{zi:<2} {name}  ({grid[0]}x{grid[1]}, {n} tax) — "
                         f"SUELTA todo (reposo) y [Enter] (s=saltar, q=fin): "
                         ).strip().lower()
            if ans == 'q':
                print("  [barrido terminado por el usuario]")
                break
            if ans == 's':
                print("  · saltada")
                continue
            ref = capture_ref(th, args.ref_frames)
            if ref is None:
                print("  · sin lectura (bus) — zona no evaluada")
                continue
            # Residual acumulado: cuanto se aparta el reposo del baseline global.
            rr, rz = -1.0, -1
            for t in range(N_TAXELS):
                d = ref[t] - base_mu[t]
                if d > rr:
                    rr, rz = d, TAXELS[t][0]
            resid_max[zi], resid_zone[zi] = rr, rz
            prompt(f"     residual en reposo: max={rr:6.0f} (z{rz}).  Ahora "
                   f"PRESIONA z{zi} y manten, [Enter]: ")
        else:
            ans = prompt(f"  z{zi:<2} {name}  ({grid[0]}x{grid[1]}, {n} tax) — "
                         f"presiona y [Enter] (s=saltar, q=fin): ").strip().lower()
            if ans == 'q':
                print("  [barrido terminado por el usuario]")
                break
            if ans == 's':
                print("  · saltada")
                continue
            ref = base_mu

        peak = capture_peak(th, args.press_frames, args.press_settle)
        if peak is None:
            print("  · sin lectura (bus) — zona no evaluada")
            continue
        pressed[zi] = True
        rise = [peak[t] - ref[t] for t in range(N_TAXELS)]

        # Rise por zona destino (max sobre sus taxeles).
        for zj in range(N_ZONES):
            a, b = ZONE_SLICES[zj]
            cross_mat[zi][zj] = max(rise[a:b])

        # Acumula own/cross por taxel.
        a0, b0 = ZONE_SLICES[zi]
        for t in range(N_TAXELS):
            if a0 <= t < b0:
                own_rise[t] = rise[t]
            elif rise[t] > cross_rise[t]:
                cross_rise[t] = rise[t]

        own = cross_mat[zi][zi]
        worst_other, worst_zj = -1.0, -1
        for zj in range(N_ZONES):
            if zj != zi and cross_mat[zi][zj] > worst_other:
                worst_other, worst_zj = cross_mat[zi][zj], zj
        ratio = (worst_other / own) if own > 0 else float('nan')
        print(f"     rise propio={own:7.0f}   peor otra=z{worst_zj} "
              f"{worst_other:7.0f}  ({ratio*100:4.0f}% del propio)")

    return {
        'cross_mat': cross_mat, 'own_rise': own_rise, 'cross_rise': cross_rise,
        'pressed': pressed, 'resid_max': resid_max, 'resid_zone': resid_zone,
        'per_zone_ref': per_zone_ref,
    }


# ── Paso 3: diagnostico de taxeles ──────────────────────────────────────────

def diagnose(base, barrido, args):
    """Clasifica cada taxel: ok / dead / stuck_high / stuck_low / noisy / unknown.

    Umbrales: la compuerta de ruido usa un cerco ROBUSTO derivado de la
    distribucion medida de sigma (mediana + k*1.4826*MAD), no una constante
    inventada. stuck_high / abs_floor / sigma_floor SI son constantes -> TODO.
    """
    mu, sigma = base['mu'], base['sigma']

    # Cerco de ruido robusto sobre la distribucion de sigma (excluye pegados-alto).
    sig_pool = [sigma[t] for t in range(N_TAXELS) if mu[t] < args.stuck_high]
    med_s = median(sig_pool)
    mad_s = mad(sig_pool, med_s)
    noisy_fence = med_s + args.noisy_k * 1.4826 * mad_s

    own_rise = barrido['own_rise'] if barrido else [None] * N_TAXELS

    status = [''] * N_TAXELS
    counts = {'ok': 0, 'dead': 0, 'stuck_high': 0, 'stuck_low': 0,
              'noisy': 0, 'unknown': 0}
    for t in range(N_TAXELS):
        thr = max(args.contact_k * sigma[t], args.contact_floor)
        rise = own_rise[t]
        responded = (rise is not None) and (rise > thr)
        tested = rise is not None

        if mu[t] >= args.stuck_high and not responded:
            st = 'stuck_high'
        elif not tested:
            # Barrido no cubrio esta zona: solo se puede juzgar por baseline.
            if mu[t] >= args.stuck_high:
                st = 'stuck_high'
            elif sigma[t] > noisy_fence:
                st = 'noisy'
            else:
                st = 'unknown'
        elif not responded and sigma[t] <= args.sigma_floor:
            st = 'stuck_low'
        elif not responded:
            st = 'dead'
        elif sigma[t] > noisy_fence:
            st = 'noisy'
        else:
            st = 'ok'
        status[t] = st
        counts[st] += 1

    return {
        'status': status, 'counts': counts,
        'noisy_fence': noisy_fence, 'med_sigma': med_s, 'mad_sigma': mad_s,
    }


# ── Paso 4: tasa de muestreo ────────────────────────────────────────────────

def measure_rate(read_fn, n, warmup):
    """Cronometra n lecturas de read_fn(); devuelve (dt_ms list, n_err)."""
    for _ in range(warmup):
        read_fn()
    dt_ms = []
    n_err = 0
    t_prev = time.perf_counter()
    for _ in range(n):
        ok = read_fn()
        t_now = time.perf_counter()
        dt_ms.append((t_now - t_prev) * 1000.0)
        t_prev = t_now
        if not ok:
            n_err += 1
    return dt_ms, n_err


def _dt_stats_line(label, dt_ms):
    if not dt_ms:
        print(f"   {label}: (sin muestras)")
        return
    s = sorted(dt_ms)
    hz = 1000.0 / statistics.fmean(dt_ms)
    print(f"   {label}:")
    print(f"      tasa media : {hz:8.1f} Hz")
    print(f"      dt (ms)    : media {statistics.fmean(dt_ms):7.3f}"
          f"  p50 {percentile(s,50):7.3f}  p95 {percentile(s,95):7.3f}"
          f"  p99 {percentile(s,99):7.3f}  max {s[-1]:7.3f}")


# ── Salidas CSV ─────────────────────────────────────────────────────────────

def write_baseline_csv(path, base, diag):
    status = diag['status'] if diag else [''] * N_TAXELS
    with open(path, 'w') as f:
        f.write("taxel,zone,zone_name,row,col,addr,mu,sigma,min,max,status\n")
        for t in range(N_TAXELS):
            zi, name, r, c, addr = TAXELS[t]
            mn = base['mn'][t]
            mx = base['mx'][t]
            mn = '' if mn == float('inf') else f"{mn:.0f}"
            mx = '' if mx == float('-inf') else f"{mx:.0f}"
            f.write(f"{t},{zi},{name},{r},{c},{addr},"
                    f"{base['mu'][t]:.3f},{base['sigma'][t]:.3f},"
                    f"{mn},{mx},{status[t]}\n")


def write_diagnosis_csv(path, base, barrido, diag):
    own = barrido['own_rise'] if barrido else [None] * N_TAXELS
    cross = barrido['cross_rise'] if barrido else [None] * N_TAXELS
    with open(path, 'w') as f:
        f.write("taxel,zone,zone_name,row,col,mu,sigma,own_rise,cross_rise,status\n")
        for t in range(N_TAXELS):
            zi, name, r, c, _addr = TAXELS[t]
            o = '' if own[t] is None else f"{own[t]:.1f}"
            x = '' if cross[t] is None else f"{cross[t]:.1f}"
            f.write(f"{t},{zi},{name},{r},{c},"
                    f"{base['mu'][t]:.3f},{base['sigma'][t]:.3f},"
                    f"{o},{x},{diag['status'][t]}\n")


def write_crosstalk_csv(path, barrido):
    cm = barrido['cross_mat']
    with open(path, 'w') as f:
        f.write("pressed\\victim," + ",".join(f"z{zj}" for zj in range(N_ZONES)) + "\n")
        for zi in range(N_ZONES):
            row = []
            for zj in range(N_ZONES):
                v = cm[zi][zj]
                row.append('' if v != v else f"{v:.0f}")   # v!=v -> NaN
            f.write(f"z{zi}," + ",".join(row) + "\n")


def write_residual_csv(path, barrido):
    """Resumen por zona: residual acumulado, respuesta propia y peor cross-talk."""
    cm = barrido['cross_mat']
    with open(path, 'w') as f:
        f.write("zone,zone_name,pressed,ref_residual_max,ref_residual_zone,"
                "own_rise,worst_cross_zone,worst_cross_val\n")
        for zi in range(N_ZONES):
            own = cm[zi][zi]
            worst, wj = -1.0, -1
            for zj in range(N_ZONES):
                v = cm[zi][zj]
                if zj != zi and v == v and v > worst:   # v==v -> no NaN
                    worst, wj = v, zj
            rm = barrido['resid_max'][zi]
            rz = barrido['resid_zone'][zi]
            f.write(
                f"z{zi},{ZONES[zi][0]},{int(barrido['pressed'][zi])},"
                f"{'' if rm != rm else f'{rm:.1f}'},"
                f"{'' if rz < 0 else f'z{rz}'},"
                f"{'' if own != own else f'{own:.0f}'},"
                f"{'' if wj < 0 else f'z{wj}'},"
                f"{'' if worst < 0 else f'{worst:.0f}'}\n")


def write_dt_csv(path, dt_ms):
    with open(path, 'w') as f:
        f.write("index,dt_ms\n")
        for i, dt in enumerate(dt_ms):
            f.write(f"{i},{dt:.6f}\n")


# ── Reporte a consola ───────────────────────────────────────────────────────

def report_diag(base, barrido, diag, args):
    c = diag['counts']
    print()
    print("── DIAGNOSTICO DE TAXELES ────────────────────────────────────────")
    print(f"  Taxeles totales : {N_TAXELS}")
    print(f"  ok         : {c['ok']}")
    print(f"  muertos    : {c['dead']}   (no responden al presionar su zona)")
    print(f"  pegado-alto: {c['stuck_high']}   (mu >= {args.stuck_high} [TODO])")
    print(f"  pegado-bajo: {c['stuck_low']}   (sigma<= {args.sigma_floor} [TODO] y sin respuesta)")
    print(f"  ruidosos   : {c['noisy']}   (sigma > cerco robusto {diag['noisy_fence']:.2f})")
    print(f"  sin evaluar: {c['unknown']}   (su zona no se presiono en el barrido)")
    print(f"  [cerco ruido: mediana(sigma)={diag['med_sigma']:.2f}, "
          f"MAD={diag['mad_sigma']:.2f}, k={args.noisy_k}]")

    # Lista de sospechosos (excluye 'ok' y 'unknown').
    bad = [t for t in range(N_TAXELS)
           if diag['status'][t] in ('dead', 'stuck_high', 'stuck_low', 'noisy')]
    if bad:
        print(f"  Sospechosos ({len(bad)}) — excluir del analisis posterior:")
        for t in bad[:40]:
            zi, name, r, c2, _addr = TAXELS[t]
            print(f"     {taxel_label(t):32s} mu={base['mu'][t]:7.1f} "
                  f"sd={base['sigma'][t]:6.2f}  -> {diag['status'][t]}")
        if len(bad) > 40:
            print(f"     ... (+{len(bad)-40} mas; ver el CSV de diagnostico)")
    else:
        print("  Sin taxeles sospechosos.")

    # Resumen de cross-talk por zona.
    if barrido:
        ref_note = ("referido a baseline fresco por-zona"
                    if barrido.get('per_zone_ref') else "referido a baseline global")
        print()
        print(f"  Cross-talk por zona ({ref_note}):")
        cm = barrido['cross_mat']
        for zi in range(N_ZONES):
            if not barrido['pressed'][zi]:
                continue
            own = cm[zi][zi]
            worst = -1.0
            wj = -1
            for zj in range(N_ZONES):
                if zj != zi and cm[zi][zj] == cm[zi][zj] and cm[zi][zj] > worst:
                    worst = cm[zi][zj]
                    wj = zj
            ratio = (worst / own * 100.0) if own > 0 else float('nan')
            flag = '  <-- alto' if (ratio == ratio and ratio > 30) else ''
            print(f"     z{zi:<2} {ZONES[zi][0]:20s} propio={own:7.0f}  "
                  f"peor=z{wj:<2} {worst:7.0f} ({ratio:4.0f}%){flag}")

        # Recuperacion / residual (solo con re-baseline por zona).
        if barrido.get('per_zone_ref'):
            print()
            print("  Recuperacion: residual en reposo ANTES de cada zona "
                  "(vs baseline global);")
            print("  crece si zonas ya presionadas no volvieron al cero (adelanto A1.3):")
            for zi in range(N_ZONES):
                rm = barrido['resid_max'][zi]
                if rm != rm:      # NaN -> zona no evaluada
                    continue
                rz = barrido['resid_zone'][zi]
                print(f"     antes de z{zi:<2} {ZONES[zi][0]:20s} "
                      f"residual max={rm:7.0f} (z{rz})")


# ── Orquestacion ────────────────────────────────────────────────────────────

def run(args):
    th, target = connect(args)
    if th is None:
        print("ERROR: no se pudo establecer la conexion Modbus.", file=sys.stderr)
        return 1
    print(f"Conectado a {target} (device_id={args.device_id}).")
    print(f"Zonas: {N_ZONES}   Taxeles: {N_TAXELS}   (1 registro/taxel, crudo 0-{TAXEL_RAW_MAX})")

    base = None
    barrido = None
    diag = None
    try:
        # ── Solo tasa ──────────────────────────────────────────────────
        if args.rate_only:
            _do_rates(th, args)
            return 0

        # ── 1) Baseline ────────────────────────────────────────────────
        if not args.no_prompt:
            prompt("\n[1/4] BASELINE: deja la mano QUIETA y SIN contacto. [Enter] para capturar... ")
        print(f"  Capturando {args.frames} frames completos en reposo...")
        base = capture_baseline(th, args.frames, args.warmup)
        print(f"  Frames usados: {base['n_used']}  (descartados por bus: {base['n_dropped']})")
        if base['dt_ms']:
            hz = 1000.0 / statistics.fmean(base['dt_ms'])
            print(f"  Tasa de frame completo durante el baseline: {hz:.1f} Hz")
        if base['n_used'] == 0:
            print("ERROR: 0 frames validos; revisa la conexion.", file=sys.stderr)
            return 1

        # ── 2) Barrido ─────────────────────────────────────────────────
        if not args.skip_barrido:
            barrido = run_barrido(th, base, args)
        else:
            print("\n[2/4] Barrido SALTADO (--skip-barrido): diagnostico parcial.")

        # ── 3) Diagnostico ─────────────────────────────────────────────
        diag = diagnose(base, barrido, args)
        report_diag(base, barrido, diag, args)

        # ── 4) Tasa ────────────────────────────────────────────────────
        _do_rates(th, args)

        _write_outputs(args, base, barrido, diag)
        return 0

    except KeyboardInterrupt:
        print("\n[interrumpido — dejo la mano en estado seguro]")
        if base is not None:
            diag = diag or diagnose(base, barrido, args)
            _write_outputs(args, base, barrido, diag)
        return 0
    finally:
        if not args.no_safe_open:
            th.open_fingers()
        th.close()


def _do_rates(th, args):
    print()
    print("── TASA DE MUESTREO ──────────────────────────────────────────────")
    dt_full, err_full = measure_rate(
        lambda: th.read_frame_flat()[0] is not None, args.rate_frames, args.warmup)
    _dt_stats_line(f"Frame completo (17 zonas, {N_TAXELS} tax)", dt_full)
    if err_full:
        print(f"      (frames con zona fallida: {err_full}/{args.rate_frames})")

    zi = args.rate_zone
    name, _addr, n, _grid = ZONES[zi]
    dt_zone, err_zone = measure_rate(
        lambda: th.read_zone(zi) is not None, args.rate_zone_frames, args.warmup)
    _dt_stats_line(f"Zona unica z{zi} {name} ({n} tax)", dt_zone)
    if err_zone:
        print(f"      (lecturas fallidas: {err_zone}/{args.rate_zone_frames})")
    print("  [la tasa de zona unica depende de su nº de taxeles; z{} tiene {}]"
          .format(zi, n))
    # Guarda las series si se pidio --csv.
    if args.csv:
        write_dt_csv(os.path.join(args.outdir, 'rate_full_dt.csv'), dt_full)
        write_dt_csv(os.path.join(args.outdir, 'rate_zone_dt.csv'), dt_zone)


def _write_outputs(args, base, barrido, diag):
    os.makedirs(args.outdir, exist_ok=True)
    tag = f"_{args.tag}" if args.tag else ""
    bp = os.path.join(args.outdir, f"baseline_taxels{tag}.csv")
    dp = os.path.join(args.outdir, f"taxel_diagnosis{tag}.csv")
    write_baseline_csv(bp, base, diag)
    write_diagnosis_csv(dp, base, barrido, diag)
    print()
    print("  Salidas:")
    print(f"    baseline por taxel : {bp}")
    print(f"    diagnostico taxeles: {dp}")
    if barrido:
        cp = os.path.join(args.outdir, f"crosstalk_zonas{tag}.csv")
        write_crosstalk_csv(cp, barrido)
        print(f"    matriz cross-talk  : {cp}")
        rp = os.path.join(args.outdir, f"residual_zonas{tag}.csv")
        write_residual_csv(rp, barrido)
        print(f"    residual por zona  : {rp}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Fase 0 del tactil — smoke test / mapa vivo (Inspire RH56DFTP).")
    # Transporte
    p.add_argument('--transport', choices=['tcp', 'serial'], default='serial')
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--ip', default='192.168.11.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    # Flujo
    p.add_argument('--rate-only', action='store_true',
                   help='solo mide la tasa (no interactivo, no mueve la mano)')
    p.add_argument('--skip-barrido', action='store_true',
                   help='salta el barrido manual (diagnostico parcial)')
    p.add_argument('--no-prompt', action='store_true',
                   help='no pausa antes del baseline (asume mano ya lista)')
    p.add_argument('--no-safe-open', action='store_true',
                   help='NO abre los dedos al salir (por defecto SI, estado seguro)')
    # Baseline
    p.add_argument('--frames', type=int, default=300,
                   help='frames completos de baseline en reposo (def 300)')
    p.add_argument('--warmup', type=int, default=10)
    # Barrido
    p.add_argument('--press-frames', type=int, default=15,
                   help='frames capturados mientras presionas cada zona (def 15)')
    p.add_argument('--press-settle', type=int, default=3,
                   help='frames descartados al inicio de cada presion (def 3)')
    p.add_argument('--ref-frames', dest='ref_frames', type=int, default=6,
                   help='frames de referencia fresca en reposo antes de cada zona (def 6)')
    p.add_argument('--global-baseline', dest='global_baseline', action='store_true',
                   help='usa el baseline global en vez de re-baseline por zona (modo previo)')
    # Tasa
    p.add_argument('--rate-frames', type=int, default=200,
                   help='lecturas cronometradas de frame completo (def 200)')
    p.add_argument('--rate-zone-frames', type=int, default=500,
                   help='lecturas cronometradas de zona unica (def 500)')
    p.add_argument('--rate-zone', type=int, default=10,
                   help='indice de zona para el test de zona unica (def 10 = Indice-Distal)')
    # Umbrales de diagnostico (los defaults dependientes de medicion son TODO)
    p.add_argument('--contact-k', dest='contact_k', type=float, default=5.0,
                   help='k del umbral de respuesta k*sigma (def 5)')
    p.add_argument('--contact-floor', dest='contact_floor', type=float, default=20.0,
                   help='piso absoluto de rise para contar como respuesta [TODO] (def 20)')
    p.add_argument('--stuck-high', dest='stuck_high', type=float, default=3900.0,
                   help='mu >= esto -> pegado-alto [TODO] (def 3900, ~techo 4095)')
    p.add_argument('--sigma-floor', dest='sigma_floor', type=float, default=0.5,
                   help='sigma <= esto (y sin respuesta) -> pegado-bajo/flatline [TODO] (def 0.5)')
    p.add_argument('--noisy-k', dest='noisy_k', type=float, default=5.0,
                   help='k del cerco robusto de ruido: mediana + k*1.4826*MAD (def 5)')
    # Salida
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'),
                   help='directorio de salida (def Caracterizacion/tactil/fase0/data)')
    p.add_argument('--tag', default='',
                   help='sufijo opcional para los CSV (p.ej. corrida)')
    p.add_argument('--csv', action='store_true',
                   help='ademas guarda las series de dt de las tasas')
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not (0 <= args.rate_zone < N_ZONES):
        print(f"ERROR: --rate-zone debe estar en [0,{N_ZONES-1}]", file=sys.stderr)
        return 2
    os.makedirs(args.outdir, exist_ok=True)
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
