#!/usr/bin/env python3
"""Análisis del grid Exp 2 (modo A): mapa de sobreimpulso ΔF por celda (v, Fset).

Fusiona un dir base (piloto) con un dir override (p. ej. re-run de velocidades
lentas): para las velocidades presentes en el override, usa esas filas. Agrega
por celda con MEDIANA (robusta a outliers/aborts) + IQR, y marca celdas con
abort. Escribe exp2_analysis_by_cell.csv + exp2_overshoot_grid.json (figura).

Puro Python (sin numpy).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from collections import defaultdict


def _isolated_peak(path):
    """(F_max, vecino_máx) del trial: ¿el pico está aislado en UNA muestra?"""
    try:
        f = [int(a['force_g']) for a in csv.DictReader(open(path)) if a['force_g']]
    except OSError:
        return None
    if len(f) < 6:
        return None
    m = max(f); i = f.index(m)
    nb = f[max(0, i - 3):i] + f[i + 1:i + 4]
    return (m, max(nb)) if nb else None


def drop_glitches(rows, d, max_speed=100, peak_ratio=2.0, neighbour_frac=0.4):
    """Descarta trials cuyo F_max es una lectura corrupta, no un impacto.

    Criterio FÍSICO, deliberadamente conservador: a velocidad baja (v <= 100) el
    dedo no lleva energía cinética para un pico inercial, así que un F_max
    aislado en una sola muestra (vecinos por debajo del `neighbour_frac` del
    pico) y muy por encima de la mediana de su propia celda solo puede ser una
    lectura Modbus corrupta. A v >= 250 NO se filtra nada: ahí un pico de
    impacto real dura pocos ms y el muestreo (~78 Hz) lo capta legítimamente en
    una sola muestra.
    """
    cell = defaultdict(list)
    for r in rows:
        if r['f_max'] is not None:
            cell[(r['speed'], r['fset'])].append(r['f_max'])
    med = {k: statistics.median(v) for k, v in cell.items()}
    keep, dropped = [], []
    for r in rows:
        m = r['f_max']
        if m is None or r['speed'] > max_speed or m <= peak_ratio * med[(r['speed'], r['fset'])]:
            keep.append(r); continue
        pk = _isolated_peak(os.path.join(d, r['trial_file']))
        if pk and pk[0] > 300 and pk[1] < neighbour_frac * pk[0]:
            dropped.append((r, pk))
        else:
            keep.append(r)
    return keep, dropped


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(d):
    rows = list(csv.DictReader(open(os.path.join(d, 'grid_index.csv'))))
    for r in rows:
        r['speed'] = int(r['speed']); r['fset'] = int(r['fset'])
        r['delta_f'] = _num(r['delta_f']); r['f_max'] = _num(r['f_max'])
        r['aborted'] = int(r['aborted'])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Análisis grid Exp 2 (mapa de ΔF).")
    _here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--base', default=os.path.join(_here, 'data'), help='dir del piloto')
    ap.add_argument('--override', default=os.path.join(_here, 'data_slow'), help='dir que reemplaza por velocidad')
    ap.add_argument('--out', default=os.path.join(_here, 'data'), help='dir de salida')
    ap.add_argument('--keep-glitches', action='store_true',
                    help='no descartar los F_max que son lecturas corruptas (ver drop_glitches)')
    a = ap.parse_args(argv)

    rows = load(a.base)
    if not a.keep_glitches:
        rows, dropped = drop_glitches(rows, a.base)
        for r, (m, nb) in dropped:
            print(f"Descartado (lectura corrupta, no impacto): {r['trial_file']}  "
                  f"v={r['speed']} Fset={r['fset']}  F_max={m} con vecinos <= {nb} g")
    if a.override and os.path.exists(os.path.join(a.override, 'grid_index.csv')):
        ov = load(a.override)
        if not a.keep_glitches:
            ov, dropped = drop_glitches(ov, a.override)
            for r, (m, nb) in dropped:
                print(f"Descartado (lectura corrupta, no impacto): {r['trial_file']}  "
                      f"v={r['speed']} Fset={r['fset']}  F_max={m} con vecinos <= {nb} g")
        ov_speeds = {r['speed'] for r in ov}
        rows = [r for r in rows if r['speed'] not in ov_speeds] + ov
        print(f"Fusionado: {a.override} reemplaza velocidades {sorted(ov_speeds)} del base.")

    speeds = sorted({r['speed'] for r in rows})
    fsets = sorted({r['fset'] for r in rows})
    cell = defaultdict(list); ab = defaultdict(int); cf = defaultdict(list)
    for r in rows:
        k = (r['speed'], r['fset'])
        if r['delta_f'] is not None:
            cell[k].append(r['delta_f'])
        if r['f_max'] is not None:
            cf[k].append(r['f_max'])
        ab[k] += r['aborted']

    agg = []
    for v in speeds:
        for F in fsets:
            vals = cell[(v, F)]
            if not vals:
                continue
            q = statistics.quantiles(vals, n=4) if len(vals) >= 2 else [vals[0]] * 3
            agg.append({
                'speed': v, 'fset': F, 'n': len(vals),
                'median_df': round(statistics.median(vals), 1),
                'mean_df': round(statistics.fmean(vals), 1),
                'sd_df': round(statistics.pstdev(vals), 1) if len(vals) > 1 else 0.0,
                'q1': round(q[0], 1), 'q3': round(q[-1], 1),
                'min': round(min(vals), 1), 'max': round(max(vals), 1),
                'median_fmax': round(statistics.median(cf[(v, F)]), 1) if cf[(v, F)] else None,
                'n_abort': ab[(v, F)],
            })
    md = {(a2['speed'], a2['fset']): a2 for a2 in agg}

    print("\nΔF mediana (g) por celda [v filas × Fset columnas]  (* = celda con abort):")
    print("  v\\Fset " + "".join(f"{F:>8}" for F in fsets))
    for v in speeds:
        line = f"{v:>7} "
        for F in fsets:
            a2 = md.get((v, F))
            line += (f"{a2['median_df']:>7.0f}" + ("*" if a2['n_abort'] else " ")) if a2 else f"{'—':>8}"
        print(line)

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'exp2_analysis_by_cell.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(agg[0].keys()))
        w.writeheader(); w.writerows(agg)

    def grid_of(key):
        return {str(v): {str(F): (md.get((v, F), {}).get(key)) for F in fsets} for v in speeds}
    grid = {'speeds': speeds, 'fsets': fsets,
            'median': grid_of('median_df'), 'q1': grid_of('q1'), 'q3': grid_of('q3'),
            'abort': grid_of('n_abort'), 'n': grid_of('n')}
    json.dump(grid, open(os.path.join(a.out, 'exp2_overshoot_grid.json'), 'w'))
    print("\nEscritos: exp2_analysis_by_cell.csv, exp2_overshoot_grid.json")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
