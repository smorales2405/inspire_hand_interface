#!/usr/bin/env python3
"""Análisis offline del Exp 1 (respuesta al escalón, espacio libre).

Lee la campaña generada por exp1_step_response.py (index.csv + series por trial)
y calcula, por trial, sobre POS_ACT:
  - latencia por banda (L_band): primer cruce de la banda de ruido tras el comando.
  - latencia por extrapolación (L_extrap): la recta ajustada al tramo 20-80%
    extrapolada hasta el baseline. Quita el sesgo del cruce lento a baja velocidad
    → deadtime comando→sensor casi independiente de la velocidad.
  - tiempo de subida (10%→90%), tiempo de establecimiento (±settle_pct%),
    sobreimpulso de posición, pendiente del tramo lineal (counts/s) y R².

Agrega media ± desv. por velocidad, escribe:
  analysis_per_trial.csv, analysis_by_speed.csv, overlay_traces.json (para figura).

Puro Python (sin numpy/matplotlib).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from collections import defaultdict


# ── utilidades numéricas ──────────────────────────────────────────────────

def linfit(xs, ys):
    """Mínimos cuadrados y = m x + b. Devuelve (m, b, r2) o None."""
    n = len(xs)
    if n < 2:
        return None
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    d = n * sxx - sx * sx
    if d == 0:
        return None
    m = (n * sxy - sx * sy) / d
    b = (sy - m * sx) / n
    ybar = sy / n
    ss_tot = sum((y - ybar) ** 2 for y in ys)
    ss_res = sum((y - (m * x + b)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float('nan')
    return m, b, r2


def cross_time(series, level):
    """Primer t donde la serie (t, y) creciente cruza `level` (interpolado)."""
    for (t0, p0), (t1, p1) in zip(series, series[1:]):
        if (p0 < level <= p1) or (p0 <= level < p1):
            return t0 if p1 == p0 else t0 + (level - p0) / (p1 - p0) * (t1 - t0)
    return None


def mean_sd(a):
    a = [x for x in a if x is not None]
    if not a:
        return (None, None)
    return (statistics.fmean(a), statistics.pstdev(a) if len(a) > 1 else 0.0)


# ── carga ─────────────────────────────────────────────────────────────────

def load_trial(path):
    """Devuelve lista (t_s, pos) — solo muestras con pos_act."""
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            if r['pos_act']:
                out.append((float(r['t_s']), int(r['pos_act'])))
    return out


def load_index(outdir):
    rows = list(csv.DictReader(open(os.path.join(outdir, 'index.csv'))))
    for r in rows:
        r['speed'] = int(r['speed'])
        r['t_cmd'] = float(r['t_cmd_s']) if r['t_cmd_s'] else None
    return rows


# ── métricas por trial ─────────────────────────────────────────────────────

def analyze_trial(series, t_cmd, settle_pct):
    """series: [(t,pos)] ordenado; t_cmd: instante del escalón (s)."""
    if not series or t_cmd is None:
        return None
    base = [p for (t, p) in series if t < t_cmd]
    if len(base) < 2:
        return None
    mu0 = statistics.fmean(base)
    sd0 = statistics.pstdev(base)
    band = max(4.0, 3.0 * sd0)

    t_end = series[-1][0]
    tail = [p for (t, p) in series if t >= t_end - 0.2]
    final = statistics.fmean(tail) if tail else None
    if final is None:
        return None
    step = final - mu0
    if abs(step) < 20:                 # apenas se movió
        return None
    sgn = 1.0 if step > 0 else -1.0

    after = [(t, p) for (t, p) in series if t >= t_cmd]

    # latencia por banda
    onset_t = next((t for (t, p) in after if abs(p - mu0) > band), None)
    L_band = (onset_t - t_cmd) if onset_t is not None else None

    # cruces 10/90% (serie orientada como creciente)
    oriented = [(t, sgn * (p - mu0)) for (t, p) in after]
    lvl10 = 0.10 * abs(step)
    lvl90 = 0.90 * abs(step)
    t10 = cross_time(oriented, lvl10)
    t90 = cross_time(oriented, lvl90)
    rise = (t90 - t10) if (t10 is not None and t90 is not None) else None

    # tramo lineal 20-80% para pendiente, R² y extrapolación de deadtime
    lo, hi = mu0 + 0.2 * step, mu0 + 0.8 * step
    lohi = (min(lo, hi), max(lo, hi))
    lin = [(t, p) for (t, p) in after if lohi[0] <= p <= lohi[1]]
    slope = r2 = L_extrap = None
    if len(lin) >= 2:
        fit = linfit([t for t, _ in lin], [p for _, p in lin])
        if fit:
            m, b, r2 = fit
            slope = m                      # counts/s
            if m != 0:
                t_cross = (mu0 - b) / m    # recta = baseline
                L_extrap = t_cross - t_cmd

    # sobreimpulso de posición (más allá del valor final)
    peak = max((sgn * p for (t, p) in after), default=None)
    over = None
    if peak is not None:
        overshoot_counts = peak - sgn * final
        over = max(0.0, overshoot_counts / abs(step) * 100.0)

    # establecimiento ±settle_pct% del valor final (última salida de banda)
    band2 = (settle_pct / 100.0) * abs(step)
    last_out = None
    for (t, p) in after:
        if abs(p - final) > band2:
            last_out = t
    settle = (last_out - t_cmd) if last_out is not None else 0.0

    return {
        'mu0': mu0, 'final': final, 'step': step,
        'L_band_ms': L_band * 1000 if L_band is not None else None,
        'L_extrap_ms': L_extrap * 1000 if L_extrap is not None else None,
        'rise_ms': rise * 1000 if rise is not None else None,
        'settle_ms': settle * 1000 if settle is not None else None,
        'overshoot_pct': over,
        'slope_cps': slope, 'r2': r2,
    }


# ── traza normalizada media por velocidad (para la figura) ─────────────────

def mean_trace(trials, t_cmd_map, grid):
    """Promedia pos normalizada [(t-t_cmd) -> (pos-mu0)/step] sobre trials en `grid`."""
    acc = [[] for _ in grid]
    for path, tcmd in trials:
        s = load_trial(path)
        if not s or tcmd is None:
            continue
        base = [p for (t, p) in s if t < tcmd]
        if len(base) < 2:
            continue
        mu0 = statistics.fmean(base)
        tail = [p for (t, p) in s if t >= s[-1][0] - 0.2]
        final = statistics.fmean(tail)
        step = final - mu0
        if abs(step) < 20:
            continue
        rel = [(t - tcmd, (p - mu0) / step) for (t, p) in s]
        for i, g in enumerate(grid):
            if rel[0][0] <= g <= rel[-1][0]:
                y = cross_interp(rel, g)
                if y is not None:
                    acc[i].append(y)
    return [statistics.fmean(v) if v else None for v in acc]


def cross_interp(series, x):
    for (x0, y0), (x1, y1) in zip(series, series[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    return None


# ── main ────────────────────────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(description="Análisis Exp 1 (paso, espacio libre).")
    _here = os.path.dirname(os.path.abspath(__file__))
    p.add_argument('--outdir', default=os.path.join(_here, 'data'))
    p.add_argument('--settle-pct', type=float, default=2.0)
    p.add_argument('--grid-dt', type=float, default=0.01)
    p.add_argument('--grid-max', type=float, default=6.0)
    args = p.parse_args(argv)

    idx = load_index(args.outdir)
    by_speed = defaultdict(list)
    per_trial_rows = []

    for r in idx:
        path = os.path.join(args.outdir, r['trial_file'])
        if not os.path.exists(path):
            continue
        m = analyze_trial(load_trial(path), r['t_cmd'], args.settle_pct)
        if m is None:
            continue
        m2 = {'trial_file': r['trial_file'], 'speed': r['speed'], **m}
        per_trial_rows.append(m2)
        by_speed[r['speed']].append(m)

    keys = ['L_band_ms', 'L_extrap_ms', 'rise_ms', 'settle_ms', 'overshoot_pct',
            'slope_cps', 'r2']

    # tabla por velocidad
    print("\n=== Exp 1 — métricas por velocidad (media ± desv, N por celda) ===")
    hdr = (f"{'v':>5} {'N':>3} {'L_band ms':>13} {'L_extr ms':>13} "
           f"{'subida ms':>13} {'estab ms':>12} {'over %':>9} "
           f"{'pend c/s':>11} {'R²':>7}")
    print(hdr); print('-' * len(hdr))
    agg_rows = []
    for v in sorted(by_speed):
        g = by_speed[v]
        stats = {k: mean_sd([t[k] for t in g]) for k in keys}
        def cell(k, w=5, dp=1):
            mu, sd = stats[k]
            return f"{mu:>{w}.{dp}f}±{sd:<4.{dp}f}" if mu is not None else f"{'—':>{w+5}}"
        print(f"{v:>5} {len(g):>3} {cell('L_band_ms')} {cell('L_extrap_ms')} "
              f"{cell('rise_ms')} {cell('settle_ms',4,0)} {cell('overshoot_pct',3,1)} "
              f"{cell('slope_cps',6,0)} {stats['r2'][0]:>6.3f}")
        row = {'speed': v, 'n': len(g)}
        for k in keys:
            row[k + '_mean'], row[k + '_sd'] = stats[k]
        agg_rows.append(row)

    # CSVs
    ptp = os.path.join(args.outdir, 'analysis_per_trial.csv')
    with open(ptp, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(per_trial_rows[0].keys()))
        w.writeheader(); w.writerows(per_trial_rows)
    abp = os.path.join(args.outdir, 'analysis_by_speed.csv')
    with open(abp, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(agg_rows[0].keys()))
        w.writeheader(); w.writerows(agg_rows)

    # trazas normalizadas medias por velocidad (figura)
    grid = [round(-0.1 + i * args.grid_dt, 4)
            for i in range(int((args.grid_max + 0.1) / args.grid_dt) + 1)]
    overlay = {'grid': grid, 'traces': {}}
    for v in sorted(by_speed):
        trials = [(os.path.join(args.outdir, r['trial_file']), r['t_cmd'])
                  for r in idx if r['speed'] == v]
        overlay['traces'][str(v)] = mean_trace(trials, None, grid)
    ovp = os.path.join(args.outdir, 'overlay_traces.json')
    json.dump(overlay, open(ovp, 'w'))

    print(f"\nEscritos:\n  {ptp}\n  {abp}\n  {ovp}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
