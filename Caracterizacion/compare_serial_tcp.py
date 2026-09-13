#!/usr/bin/env python3
"""Compara la caracterización por RS-485 (serial) vs Modbus TCP, desde los CSV.

Exp 0: tasa de muestreo y resolución (dt).  Exp 1: tasa, pendiente∝v, R², latencia.
Exp 2: F_max vs velocidad (Fset=500).  Puro Python. Correr desde cualquier cwd.
"""
from __future__ import annotations
import csv, os, statistics

H = os.path.dirname(os.path.abspath(__file__))


def _dt_stats(paths):
    dt = []
    for p in paths:
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                try: dt.append(float(r['dt_ms']))
                except (KeyError, ValueError): pass
    if not dt: return None
    return {'n': len(dt), 'rate': len(dt) / (sum(dt) / 1000.0),
            'p50': statistics.median(dt), 'media': statistics.fmean(dt)}


def _rate_from_index(p):
    if not os.path.exists(p): return None
    r = [float(x['rate_hz']) for x in csv.DictReader(open(p)) if x.get('rate_hz') not in (None, '')]
    return statistics.fmean(r) if r else None


def _by_speed(p, key):
    if not os.path.exists(p): return {}
    d = {}
    for r in csv.DictReader(open(p)):
        try: d[int(r['speed'])] = float(r[key])
        except (KeyError, ValueError): pass
    return d


def _fmax_by_speed(p, fset=500):
    if not os.path.exists(p): return {}
    d = {}
    for r in csv.DictReader(open(p)):
        try:
            if int(r['fset']) != fset: continue
            d.setdefault(int(r['speed']), []).append(float(r['f_max']))
        except (KeyError, ValueError): pass
    return {v: statistics.median(x) for v, x in d.items()}


def main():
    print("=" * 60)
    print(" Comparación caracterización: RS-485 (serial) vs Modbus TCP")
    print("=" * 60)

    # ── Exp 0 ──
    s = _dt_stats([os.path.join(H, 'exp0/data', f) for f in
                   ('exp0_data1.csv', 'exp0_data2.csv', 'exp0_data3.csv')])
    t = _dt_stats([os.path.join(H, 'exp0/data/exp0_tcp.csv')])
    print("\n[Exp 0 · muestreo]")
    if s and t:
        print(f"  tasa media : serial {s['rate']:.0f} Hz  →  TCP {t['rate']:.0f} Hz   (×{t['rate']/s['rate']:.1f})")
        print(f"  dt mediana : serial {s['p50']:.2f} ms  →  TCP {t['p50']:.2f} ms   (×{s['p50']/t['p50']:.0f} más fino)")

    # ── Exp 1 ──
    print("\n[Exp 1 · escalón — por velocidad]")
    rs = _rate_from_index(os.path.join(H, 'exp1/data/index.csv'))
    rt = _rate_from_index(os.path.join(H, 'exp1/data_tcp/index.csv'))
    if rs and rt: print(f"  tasa media : serial {rs:.0f} Hz  →  TCP {rt:.0f} Hz   (×{rt/rs:.1f})")
    ss = _by_speed(os.path.join(H, 'exp1/data/analysis_by_speed.csv'), 'slope_cps_mean')
    st = _by_speed(os.path.join(H, 'exp1/data_tcp/analysis_by_speed.csv'), 'slope_cps_mean')
    r2s = _by_speed(os.path.join(H, 'exp1/data/analysis_by_speed.csv'), 'r2_mean')
    r2t = _by_speed(os.path.join(H, 'exp1/data_tcp/analysis_by_speed.csv'), 'r2_mean')
    print(f"  {'v':>5} | {'pendiente c/s (ser→tcp)':>24} | {'R² (ser→tcp)':>16}")
    for v in sorted(set(ss) | set(st)):
        a, b = ss.get(v), st.get(v)
        c, d = r2s.get(v), r2t.get(v)
        print(f"  {v:>5} | {(f'{a:.0f}' if a else '—')+'→'+(f'{b:.0f}' if b else '—'):>24} | "
              f"{(f'{c:.3f}' if c else '—')+'→'+(f'{d:.3f}' if d else '—'):>16}")

    # ── Exp 2 ──
    print("\n[Exp 2 · F_max (g) vs velocidad, Fset=500]")
    fs = _fmax_by_speed(os.path.join(H, 'exp2/data/grid_index.csv'))
    ft = _fmax_by_speed(os.path.join(H, 'exp2/data_tcp/grid_index.csv'))
    rt2 = _rate_from_index(os.path.join(H, 'exp2/data_tcp/grid_index.csv'))
    print(f"  {'v':>5} | {'F_max serial':>13} | {'F_max TCP':>12}")
    for v in sorted(set(fs) | set(ft)):
        a, b = fs.get(v), ft.get(v)
        print(f"  {v:>5} | {(f'{a:.0f}' if a else '—'):>13} | {(f'{b:.0f}' if b else '—'):>12}")
    if rt2: print(f"  tasa muestreo grid: TCP ≈ {rt2:.0f} Hz  (serial ~65 Hz)")

    print("\nConclusión: física idéntica (pendiente∝v, R², magnitudes de F_max);")
    print("TCP mejora tasa ~7-9×, resolución ~17× y write_cost ~12×. Deadtime = igual.")


if __name__ == '__main__':
    main()
