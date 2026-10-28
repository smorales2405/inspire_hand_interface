#!/usr/bin/env python3
"""Exp 4 · Tasa de refresco de los registros, por DOF y por carga.

**Qué se puede y qué no se puede medir.** E3.6a dejó la advertencia que gobierna
este diseño: a un DOF *quieto y descargado* no se le puede medir la rejilla de
refresco, porque `POS` no cambia **ni una vez** en 191 s y los «cambios» de
fuerza son ruido cruzando enteros, no refrescos. Para medir los seis hay que
**hacerlos producir señal**: moverlos despacio, o cargarlos.

De ahí las condiciones:

| | qué hace | qué mide |
|---|---|---|
| `quieto` | todo parado y descargado | el CONTROL: `POS` no da rejilla, `FORCE` sí |
| `movimiento` | cada DOF barre despacio, de uno en uno | la rejilla de `POS` por DOF, en vacío |
| `escalonado` | dos DOF barren a la vez | el desfase entre ellos |
| `carga` | el pulgar sostiene contra el montaje | la rejilla de `FORCE` bajo carga |

**El claim honesto es sobre el REGISTRO, no sobre el firmware.** Lo que se
observa es cada cuánto cambia el entero publicado. Un entero que se repite es
indistinguible de «no hubo refresco», así que esto acota la rejilla de
publicación por arriba, no la tasa de muestreo interna.

**Por qué `FORCE` da la rejilla incluso con el dedo quieto.** El registro es un
entero que sólo se reescribe en un instante de refresco, así que *cualquier*
cambio suyo —sea señal o ruido cruzando un entero— cae en la rejilla. Los
intervalos entre cambios siguen siendo múltiplos del periodo aunque la causa sea
ruido. `POS` no sirve para esto porque con el dedo quieto no cambia nunca.
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from hand_modbus import (                                    # noqa: E402
    HandModbus, NDOF, ANGLE_SET, ANGLE_ACT, POS_ACT, FORCE_ACT, FORCE_SET,
    SPEED_SET, CURRENT, DOF_NAMES,
)

REGS = {'POS': POS_ACT, 'FORCE': FORCE_ACT, 'CURRENT': CURRENT}


def sondea(hand, dur, regs=('POS', 'FORCE'), cur_cada=1):
    """Sondea lo más rápido que deje el Modbus y guarda (t, valores).

    `cur_cada` > 1 SUBMUESTREA `CURRENT`. Con 3 bloques por iteración el sondeo
    baja a ~210 Hz, que sigue siendo 6× la rejilla; leyendo uno de cada 8 el
    muestreo efectivo de `CURRENT` cae a ~39 Hz contra una rejilla de ~32, o sea
    1.2×, y los intervalos dejan de ser medibles. Medido: asi salia 27.6 ms con
    60 % de multiplos, contra 30.3 ms y 85 % en `POS` de la misma tanda.
    """
    t0 = time.perf_counter()
    filas = []
    i = 0
    while time.perf_counter() - t0 < dur:
        t = time.perf_counter() - t0
        fila = {'t': t}
        for r in regs:
            if r == 'CURRENT' and i % cur_cada:
                continue
            v = hand.read_block(REGS[r])
            if v:
                fila[r] = list(v)
        filas.append(fila)
        i += 1
    return filas


def cambios(filas, reg, d):
    """Instantes en que el entero de ese DOF cambia de valor."""
    ts, prev = [], None
    for f in filas:
        v = f.get(reg)
        if v is None:
            continue
        if prev is not None and v[d] != prev:
            ts.append(f['t'])
        prev = v[d]
    return ts


def rejilla(ts, tol=0.15):
    """Periodo base y qué fracción de los intervalos son múltiplos suyos.

    Los intervalos se agrupan en T, 2T, 3T… porque un entero que se repite
    esconde un refresco. El periodo base se estima con los intervalos cortos
    —los que sí capturan un solo refresco— y luego se comprueba cuántos del
    total caen cerca de un múltiplo entero.
    """
    if len(ts) < 12:
        return None
    iv = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    if len(iv) < 10:
        return None
    med = statistics.median(iv)
    cortos = [x for x in iv if x <= 1.5 * med]
    T = statistics.median(cortos) if len(cortos) >= 5 else med
    if T <= 0:
        return None
    ok = 0
    for x in iv:
        n = round(x / T)
        if n >= 1 and abs(x - n * T) <= tol * T:
            ok += 1
    q = statistics.quantiles(iv, n=4)
    return dict(T=T, n=len(iv), frac=ok / len(iv), med=med, q1=q[0], q3=q[2],
                tasa=len(ts) / (ts[-1] - ts[0]) if ts[-1] > ts[0] else 0.0)


def desfase(ts_a, ts_b, T):
    """Desfase de b respecto a a, en ms, modulo el periodo."""
    if not ts_a or not ts_b or not T:
        return None
    d = []
    for t in ts_b:
        cerca = min(ts_a, key=lambda x: abs(x - t))
        e = (t - cerca) % T
        if e > T / 2:
            e -= T
        d.append(e * 1000.0)
    return (statistics.median(d), statistics.quantiles(d, n=4)[0],
            statistics.quantiles(d, n=4)[2], len(d)) if len(d) >= 5 else None


def informe(filas, dofs, regs, etiqueta):
    print(f"\n  {etiqueta}")
    tasa = len(filas) / filas[-1]['t'] if filas and filas[-1]['t'] > 0 else 0
    print(f"    sondeo {tasa:.0f} Hz · {len(filas)} lecturas · "
          f"{filas[-1]['t']:.0f} s")
    print(f"    {'DOF':<16} {'reg':<8} {'cambios':>8} {'tasa':>8} "
          f"{'T base':>9} {'mediana':>9} {'multiplos':>10}")
    res = {}
    for d in dofs:
        for r in regs:
            ts = cambios(filas, r, d)
            g = rejilla(ts)
            res[(d, r)] = (ts, g)
            if g is None:
                print(f"    {DOF_NAMES[d]:<16} {r:<8} {len(ts):>8} "
                      f"{'—':>8} {'—':>9} {'—':>9} {'—':>10}"
                      + ("   ← sin señal: no se puede medir" if len(ts) < 12 else ""))
            else:
                print(f"    {DOF_NAMES[d]:<16} {r:<8} {len(ts):>8} "
                      f"{g['tasa']:>7.1f}H {1000*g['T']:>8.1f}m "
                      f"{1000*g['med']:>8.1f}m {100*g['frac']:>9.0f}%")
    return res


def guarda(filas, path, regs):
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['t'] + [f'{r}_{d}' for r in regs for d in range(NDOF)])
        for f in filas:
            fila = [f"{f['t']:.6f}"]
            for r in regs:
                v = f.get(r)
                fila += ([''] * NDOF) if v is None else [str(x) for x in v]
            w.writerow(fila)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--ip', default='192.168.124.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--condicion', required=True,
                   choices=['quieto', 'movimiento', 'escalonado', 'carga'])
    p.add_argument('--dofs', default='0,1,2,3,4,5')
    p.add_argument('--dur', type=float, default=30.0, help='segundos por DOF o condicion')
    p.add_argument('--vel', type=int, default=12, help='SPEED_SET del barrido lento')
    p.add_argument('--hasta', type=int, default=0,
                   help='ANGLE_SET donde acaba el barrido. Con un montaje puesto '
                        'hay que pararlo ANTES del contacto o deja de ser "en vacio"')
    p.add_argument('--rot', type=int, default=None,
                   help='ancla la rotacion del pulgar; obligatorio si se toca el pulgar')
    p.add_argument('--fuerza-carga', type=float, default=250.0)
    p.add_argument('--angulo-min', type=int, default=300,
                   help='suelo de la rampa de contacto; depende de donde quede el '
                        'montaje, no es una constante del dedo')
    p.add_argument('--outdir', default=os.path.join(os.path.dirname(__file__), 'data'))
    a = p.parse_args(argv)
    dofs = [int(x) for x in a.dofs.split(',')]

    h = HandModbus.open_tcp(a.ip, a.port, a.device_id, 1.0)
    ts_etq = time.strftime('%Y%m%d_%H%M%S')

    def manda(cmds, vel=None):
        if vel is not None:
            h.write_block(SPEED_SET, [vel] * NDOF)
        v = [-1] * NDOF
        if a.rot is not None:
            v[5] = a.rot
        for d, x in cmds.items():
            v[d] = int(x)
        h.write_block(ANGLE_SET, v)

    def abre():
        h.write_block(FORCE_SET, [3000] * NDOF)
        manda({d: 1000 for d in range(NDOF) if d != 5}, vel=25)
        if a.rot is not None:
            manda({}, vel=25)
        time.sleep(3.0)
        h.write_block(FORCE_SET, [700] * NDOF)

    try:
        print(f"Exp 4 · tasa de refresco · condicion '{a.condicion}'")
        print(f"  temps al empezar: {h.read_temps()}")

        if a.condicion == 'quieto':
            abre()
            filas = sondea(h, a.dur, ('POS', 'FORCE', 'CURRENT'))
            informe(filas, dofs, ('POS', 'FORCE'), 'TODO QUIETO Y DESCARGADO (control)')
            guarda(filas, os.path.join(a.outdir, f'e4_quieto_{ts_etq}.csv'),
                   ('POS', 'FORCE', 'CURRENT'))
            print("\n    Si POS no cambia, la rejilla NO es observable aqui. Es el")
            print("    control que justifica las demas condiciones, no un fallo.")

        elif a.condicion == 'movimiento':
            todo = {}
            for d in dofs:
                abre()
                print(f"\n  barriendo {DOF_NAMES[d]} despacio (v={a.vel})...")
                manda({d: a.hasta}, vel=a.vel)
                filas = sondea(h, a.dur, ('POS', 'FORCE', 'CURRENT'))
                r = informe(filas, [d], ('POS', 'FORCE', 'CURRENT'),
                            f'{DOF_NAMES[d]} EN MOVIMIENTO, sin carga')
                todo[d] = r
                guarda(filas, os.path.join(a.outdir, f'e4_mov_dof{d}_{ts_etq}.csv'),
                       ('POS', 'FORCE', 'CURRENT'))
            abre()

        elif a.condicion == 'escalonado':
            abre()
            print(f"\n  barriendo {', '.join(DOF_NAMES[d] for d in dofs)} A LA VEZ")
            manda({d: a.hasta for d in dofs}, vel=a.vel)
            filas = sondea(h, a.dur, ('POS', 'FORCE'))
            res = informe(filas, dofs, ('POS',), 'VARIOS DOF A LA VEZ')
            base = [res[(d, 'POS')][1] for d in dofs if res[(d, 'POS')][1]]
            if len(base) >= 2 and len(dofs) >= 2:
                T = statistics.median([g['T'] for g in base])
                print(f"\n    periodo comun {1000*T:.2f} ms · desfases respecto a "
                      f"{DOF_NAMES[dofs[0]]}:")
                ref = res[(dofs[0], 'POS')][0]
                for d in dofs[1:]:
                    ts = res[(d, 'POS')][0]
                    df = desfase(ref, ts, T)
                    if df:
                        print(f"      {DOF_NAMES[d]:<16} {df[0]:+7.2f} ms "
                              f"(cuartiles {df[1]:+.2f} / {df[2]:+.2f}, n={df[3]})")
            guarda(filas, os.path.join(a.outdir, f'e4_escalonado_{ts_etq}.csv'),
                   ('POS', 'FORCE'))
            abre()

        elif a.condicion == 'carga':
            print(f"\n  el montaje debe estar puesto: el pulgar sostendra "
                  f"~{a.fuerza_carga:.0f} g")
            abre()
            manda({4: 450}, vel=25); time.sleep(2.5)
            ang = 450
            while ang > a.angulo_min:
                f = statistics.median([h.read_block(FORCE_ACT)[4] for _ in range(7)])
                if f >= a.fuerza_carga:
                    break
                ang -= 2
                manda({4: ang}); time.sleep(0.18)
            act = h.read_block(ANGLE_ACT); manda({4: act[4]}); time.sleep(1.5)
            f0 = h.read_block(FORCE_ACT)[4]
            print(f"  sosteniendo {f0} g con ANGLE_SET {act[4]}")
            filas = sondea(h, a.dur, ('POS', 'FORCE', 'CURRENT'))
            informe(filas, dofs, ('POS', 'FORCE', 'CURRENT'),
                    f'PULGAR BAJO CARGA (~{f0} g)')
            guarda(filas, os.path.join(a.outdir, f'e4_carga_{ts_etq}.csv'),
                   ('POS', 'FORCE', 'CURRENT'))
            abre()
        print(f"\n  temps al acabar: {h.read_temps()}")
    finally:
        h.write_block(FORCE_SET, [3000] * NDOF)
        v = [1000] * NDOF
        if a.rot is not None:
            v[5] = a.rot
        h.write_block(ANGLE_SET, v)
        time.sleep(2.5)
        h.write_block(FORCE_SET, [700] * NDOF)
        print("  mano abierta")
    return 0


if __name__ == '__main__':
    sys.exit(main())
