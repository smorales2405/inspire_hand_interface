#!/usr/bin/env python3
"""A2 · analisis del protocolo intercalado.

Lee el indice que escribe `lazo.py --modo comparar` y compara los dos brazos.

**Prueba de permutacion, no prueba t.** Son N ~ 10 por brazo, la metrica es una
mediana y no hay ninguna razon para creer que el error en regimen sea normal: el
brazo del lazo esta truncado por la banda muerta. La permutacion no supone nada
sobre la forma de la distribucion — solo que, si los dos brazos fueran
equivalentes, la etiqueta `firmware`/`lazo` seria intercambiable.

**Solo compara dentro de la misma tanda.** Dos tandas del mismo dedo, objeto y
pose difirieron en un factor 2 por deriva del cero (Exp 2). Por eso el indice
lleva `bloque`: mezclar bloques exige decirlo explicitamente.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import random
import statistics
import sys


def permutacion(a, b, n_iter=20000, semilla=0):
    """p a dos colas para la diferencia de medianas. Exacta si el numero de
    particiones es manejable; si no, Monte Carlo."""
    obs = abs(statistics.median(a) - statistics.median(b))
    todo = list(a) + list(b)
    na = len(a)
    combos = list(itertools.combinations(range(len(todo)), na))
    if len(combos) <= n_iter:
        reps, exacta = combos, True
    else:
        rnd = random.Random(semilla)
        reps = [tuple(rnd.sample(range(len(todo)), na)) for _ in range(n_iter)]
        exacta = False
    extremos = 0
    for idx in reps:
        s = set(idx)
        ga = [todo[i] for i in s]
        gb = [todo[i] for i in range(len(todo)) if i not in s]
        if abs(statistics.median(ga) - statistics.median(gb)) >= obs - 1e-12:
            extremos += 1
    return (extremos + (0 if exacta else 1)) / (len(reps) + (0 if exacta else 1)), exacta


def resumen(v):
    return (f"mediana {statistics.median(v):7.1f} · rango {min(v):.0f}–{max(v):.0f}"
            f" · n={len(v)}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('csv')
    p.add_argument('--bloque', help='analiza solo este bloque')
    p.add_argument('--mezclar-bloques', action='store_true',
                   help='permite mezclar bloques. Hay que justificarlo: el cero deriva entre tandas')
    p.add_argument('--iter', type=int, default=20000)
    a = p.parse_args(argv)

    filas = [r for r in csv.DictReader(open(a.csv))
             if r.get('nota') != 'abortado' and r.get('err_reg')]
    if a.bloque:
        filas = [r for r in filas if r['bloque'] == a.bloque]
    bloques = sorted({r['bloque'] for r in filas})
    if len(bloques) > 1 and not a.mezclar_bloques:
        print(f"Hay {len(bloques)} bloques ({', '.join(bloques)}). Elige uno con "
              f"--bloque, o usa --mezclar-bloques si puedes justificarlo.")
        return 2

    abortados = sum(1 for r in csv.DictReader(open(a.csv)) if r.get('nota') == 'abortado')
    sin_tara = sum(1 for r in filas if r.get('tarado') == 'no')

    g = {}
    for r in filas:
        g.setdefault(r['brazo'], []).append(r)
    if len(g) < 2:
        print("hacen falta los dos brazos"); return 2

    print(f"A2 · INTERCALADO · bloques {', '.join(bloques)} · "
          f"{len(filas)} trials validos" + (f" ({abortados} abortados)" if abortados else ""))
    if sin_tara:
        print(f"  ⚠ {sin_tara} trial(s) sin tara aceptada: el cero no es comparable")
    print()

    met = [('|error| en regimen (g)', lambda r: abs(float(r['err_reg'])), 'menor mejor'),
           ('error con signo (g)',    lambda r: float(r['err_reg']),      'el firmware deberia decaer'),
           ('pico (g)',               lambda r: float(r['pico']),         'menor mejor'),
           ('corriente en regimen (mA)', lambda r: float(r['I_med']),     'el par activo se paga en corriente')]
    if any(r.get('recup') for r in filas):
        met.insert(0, ('RESIDUAL tras la perturbacion (g)',
                       lambda r: abs(float(r['resid'])),
                       'cuanto queda SOBRE SU PROPIA BASE 20 s despues; menor mejor'))
        met.insert(1, ('pico de la excursion (g)',
                       lambda r: float(r['salto']),
                       'RESPUESTA, no perturbacion: el lazo ya abre dentro de la ventana'))

    for nombre, f, nota in met:
        va = [f(r) for r in g['firmware']]
        vb = [f(r) for r in g['lazo']]
        pv, exacta = permutacion(va, vb, a.iter)
        print(f"{nombre}   ({nota})")
        print(f"  firmware  {resumen(va)}")
        print(f"  lazo      {resumen(vb)}")
        print(f"  p = {pv:.4f} ({'exacta' if exacta else f'{a.iter} permutaciones'})")
        print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
