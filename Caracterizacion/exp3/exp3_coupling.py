#!/usr/bin/env python3
"""E3.6 — Acoplamiento en los modos de pinza reales (y E3.6a, sincronía).

Tres fases, una invocación cada una, porque entre ellas actúa una PERSONA:

  --phase grasp    La persona sostiene el objeto en la pinza. La mano tara con los
                   dedos abiertos, cierra DESPACIO todos los dedos del modo a la vez
                   y congela cada uno en cuanto toca. Sale SIN ABRIR y guarda el
                   estado. La persona suelta el objeto.
  --phase couple   Con el objeto ya sujeto por la mano: escalona el comando de UN
                   dedo y registra la fuerza de TODOS. Sale SIN ABRIR.
  --phase release  La persona sujeta el objeto; la mano abre.

SEGURIDAD — hay manos humanas en el recorrido. En la fase de agarre:
  · cierre a v=25, donde el Exp 2 midió sobreimpulsos de 7–73 g;
  · cada dedo se congela POR SOFTWARE al tocar (`--f-grasp`), no por el paro del
    firmware, que además secuestra la posición en los dos sentidos;
  · dos techos independientes: el software abre la mano a `--safety-force-g`
    (600 g) y `FORCE_SET` queda de respaldo por encima (700 g) por si el software
    se colgara;
  · antes de cualquier apertura se sube `FORCE_SET`, para que un dedo que hubiera
    llegado al paro del firmware acepte la orden de abrir.

FÍSICA que condiciona la lectura. En una pinza de dos dedos sobre un objeto
libre, las dos fuerzas normales están obligadas a igualarse (acción y reacción a
través del objeto), así que el acoplamiento del modo 1 tiene que salir cerca del
100 %. Lo informativo es la DESVIACIÓN de ese 100 % —que es una calibración
cruzada de los sensores de yema— y el retardo entre la fuerza del dedo movido y la
reacción en el otro.

E3.6a sale del log de la fase de agarre: es el primer registro en el que dos o
más DOF se mueven a la vez, que es lo único que permite ver si la mano refresca
todos los DOF en el mismo frame o escalonados.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from hand_modbus import (                                    # noqa: E402
    HandModbus, NDOF, ANGLE_SET, ANGLE_ACT, FORCE_SET, SPEED_SET,
    POS_ACT, FORCE_ACT, CURRENT, DOF_NAMES, open_vector, report_hold,
)
from exp3_min_step import FORCE_CLB                          # noqa: E402

MODES = {1: [4, 3], 2: [4, 3, 2]}      # pulgar primero: es el que se opone a todos
FSET_RELEASE = 3000                    # FORCE_SET antes de abrir: nunca debe frenar la apertura


# ── utilidades ────────────────────────────────────────────────────────────
def vec(cmds, hold):
    """Bloque ANGLE_SET con varios DOF a la vez; el resto en -1 (no tocar)."""
    v = [-1] * NDOF
    for d, a in hold.items():
        v[d] = a
    for d, a in cmds.items():
        v[d] = int(a)
    return v


def open_hand(hand, args):
    """Apertura segura: primero se quita el paro del firmware, luego se abre."""
    try:
        hand.write_block(FORCE_SET, [FSET_RELEASE] * NDOF)
        hand.write_block(SPEED_SET, [args.open_speed] * NDOF)
        hand.write_block(ANGLE_SET, open_vector(args.open_angle, args.hold_map))
        time.sleep(0.4)
    except Exception:
        pass


class Log:
    """Escribe cada lectura al disco: POS y FORCE de los 6 DOF, sin acumular en RAM
    (el sistema tiene poca memoria libre y el vigilante mata procesos largos)."""

    def __init__(self, path):
        self.fh = open(path, 'w', newline='')
        self.w = csv.writer(self.fh)
        self.w.writerow(['t_s', 'phase', 'tag']
                        + [f'pos{i}' for i in range(NDOF)]
                        + [f'force{i}' for i in range(NDOF)])
        self.t0 = time.perf_counter()

    def row(self, phase, tag, p, f):
        self.w.writerow([f"{time.perf_counter()-self.t0:.5f}", phase, tag,
                         *(p if p else [''] * NDOF), *(f if f else [''] * NDOF)])

    def close(self):
        self.fh.close()


def read_pf(hand):
    return hand.read_block(POS_ACT), hand.read_block(FORCE_ACT)


def sample(hand, dofs, seconds, log, phase, tag):
    """Muestrea `seconds` y devuelve {dof: (mediana F, mediana POS)} y la traza."""
    fs = {d: [] for d in dofs}
    ps = {d: [] for d in dofs}
    tr = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        p, f = read_pf(hand)
        t = time.perf_counter() - t0
        log.row(phase, tag, p, f)
        if p and f:
            tr.append((t, p, f))
            for d in dofs:
                fs[d].append(f[d])
                ps[d].append(p[d])
    med = {d: (statistics.median(fs[d]) if fs[d] else None,
               statistics.median(ps[d]) if ps[d] else None) for d in dofs}
    return med, tr


def check(forces, dofs, args):
    for d in dofs:
        if forces.get(d) is not None and abs(forces[d]) > args.safety_force_g:
            return f"DOF {d} ({DOF_NAMES[d]}): {forces[d]} g > techo {args.safety_force_g}"
    return None


# ── fase 1: agarre ────────────────────────────────────────────────────────
def phase_grasp(hand, args, dofs, log):
    print(f"E3.6 · AGARRE · modo {args.mode}: " + " + ".join(DOF_NAMES[d] for d in dofs)
          + f" · rotación del pulgar ANGLE_SET {args.rot}")
    print(f"  cierre a v={args.close_speed} · congela al tocar {args.f_grasp} g · "
          f"techo software {args.safety_force_g} g · FORCE_SET de respaldo {args.fset_backstop} g")

    open_hand(hand, args)
    report_hold(hand, args.hold_map, 6, 4.0, args.open_speed)
    t = hand.read_temps()
    tmax = max(t[d] for d in dofs) if t else None
    print(f"  temperatura: {t}")
    if tmax is not None and tmax > args.temp_max:
        print(f"ABORTA: {tmax} °C > {args.temp_max}")
        return 2

    # E3.5: el cero queda corrido 21–46 g hasta ~8 s después de soltar una carga.
    print(f"  esperando {args.pre_tare_wait:.0f} s con la mano abierta antes de tarar "
          f"(E3.5: el cero tarda ~8 s en volver tras soltar)...")
    time.sleep(args.pre_tare_wait)
    print("  tarando (forceClb, dedos abiertos y sin carga)...")
    hand.write_block(FORCE_CLB, [1])
    time.sleep(1.5)

    base, _ = sample(hand, dofs, 0.8, log, 'grasp', 'base')
    print("  base tras tarar: " + "  ".join(f"{DOF_NAMES[d]} {base[d][0]:+.0f} g" for d in dofs))

    hand.write_block(SPEED_SET, [args.close_speed] * NDOF)
    hand.write_block(FORCE_SET, [args.fset_backstop] * NDOF)

    # La persona no ve esta salida en vivo: la ventana de colocación es FIJA y
    # holgada, y empieza después de la tara para que el objeto no cargue el cero.
    print(f"  VENTANA DE COLOCACIÓN: {args.place_wait:.0f} s para poner el objeto en la pinza...")
    t_pl = time.perf_counter()
    while time.perf_counter() - t_pl < args.place_wait:
        p, f = read_pf(hand)
        log.row('grasp', 'place', p, f)
        if p and f:
            bad = check({d: f[d] for d in dofs}, dofs, args)
            if bad:
                print(f"ABORTA durante la colocación: {bad}. Abro.")
                open_hand(hand, args)
                return 4
        time.sleep(0.02)

    print(f"  CERRANDO {len(dofs)} dedos a la vez...")
    hand.write_block(ANGLE_SET, vec({d: args.close_target for d in dofs}, args.hold_map))

    frozen = {}
    t0 = time.perf_counter()
    while len(frozen) < len(dofs):
        if time.perf_counter() - t0 > args.grasp_timeout:
            print(f"ABORTA: {args.grasp_timeout:.0f} s sin tocar con todos los dedos "
                  f"(tocaron: {[DOF_NAMES[d] for d in frozen] or 'ninguno'}). Abro.")
            open_hand(hand, args)
            return 3
        p, f = read_pf(hand)
        log.row('grasp', 'close', p, f)
        if not (p and f):
            continue
        bad = check({d: f[d] for d in dofs}, dofs, args)
        if bad:
            print(f"ABORTA: {bad}. Abro.")
            open_hand(hand, args)
            return 4
        for d in dofs:
            if d in frozen or f[d] < args.f_grasp:
                continue
            a = hand.read_block(ANGLE_ACT)
            cmd = a[d] if a else None
            if cmd is None:
                continue
            hand.write_block(ANGLE_SET, vec({d: cmd}, args.hold_map))
            frozen[d] = dict(cmd=int(cmd), pos=p[d], force=f[d],
                             t=time.perf_counter() - t0)
            print(f"  · {DOF_NAMES[d]:<16} toca a t={frozen[d]['t']:5.2f} s  "
                  f"POS {p[d]}  F {f[d]} g  → congelado en ANGLE_SET {cmd}")

    settle, _ = sample(hand, dofs, args.settle_s, log, 'grasp', 'held')
    print("  sujetando: " + "  ".join(f"{DOF_NAMES[d]} {settle[d][0]:.0f} g" for d in dofs))

    state = dict(mode=args.mode, rot=args.rot, dofs=dofs,
                 cmds={str(d): frozen[d]['cmd'] for d in dofs},
                 contact={str(d): frozen[d] for d in dofs},
                 held_force={str(d): settle[d][0] for d in dofs},
                 base_after_tare={str(d): base[d][0] for d in dofs},
                 tag=args.tag, t_wall=time.strftime('%Y-%m-%d %H:%M:%S'))
    with open(args.state, 'w') as fh:
        json.dump(state, fh, indent=2)
    print(f"\n  Estado: {args.state}")
    print("  ✔ AGARRE ESTABLECIDO. La mano NO se abre. Ya puedes soltar el objeto.")
    return 0


# ── fase 2: acoplamiento ──────────────────────────────────────────────────
def onset_ms(trace, d, base_f, thr):
    """Primer instante en que la fuerza del DOF `d` se separa de su base: sobre
    cambios de valor DE ESE DOF, no del bloque — así cada dedo tiene su propio reloj."""
    prev = None
    for t, _p, f in trace:
        v = f[d]
        if prev is not None and v != prev and abs(v - base_f) > thr:
            return t * 1000
        prev = v
    return None


def phase_couple(hand, args, dofs, log):
    st = json.load(open(args.state))
    if st['dofs'] != dofs:
        print(f"ABORTA: el estado es del modo {st['mode']} ({st['dofs']}), no de {dofs}")
        return 2
    cmds = {int(d): c for d, c in st['cmds'].items()}
    print(f"E3.6 · ACOPLAMIENTO · modo {args.mode} · estado de {st['t_wall']}")
    print(f"  comandos de agarre: " + "  ".join(f"{DOF_NAMES[d]} {cmds[d]}" for d in dofs))

    hand.write_block(FORCE_SET, [args.fset_backstop] * NDOF)
    hand.write_block(SPEED_SET, [args.close_speed] * NDOF)

    now, _ = sample(hand, dofs, 1.5, log, 'couple', 'check')
    print("  fuerza actual: " + "  ".join(f"{DOF_NAMES[d]} {now[d][0]:.0f} g" for d in dofs))
    low = [d for d in dofs if (now[d][0] or 0) < args.min_hold_g]
    if low:
        print(f"ABORTA: {[DOF_NAMES[d] for d in low]} por debajo de {args.min_hold_g} g — "
              f"el objeto no está sujeto. No abro: puede que ya no haya nada que soltar.")
        return 3

    ref = args.retrim_dof
    steps = {int(k): int(v) for k, v in (x.split(':') for x in args.steps.split(','))}
    margin = args.retrim_max + max(steps[d] for d in dofs)
    edge = [d for d in dofs if cmds[d] < margin or cmds[d] > 1000 - margin]
    if edge:
        print(f"ABORTA: {[f'{DOF_NAMES[d]} en {cmds[d]}' for d in edge]} — demasiado cerca del "
              f"extremo del comando para escalonar ±{margin} unidades. Los trials en ese "
              f"sentido saldrían vacíos. No abro.")
        return 3
    order = [(m, dr, n) for m in dofs for dr in ('cerrar', 'abrir') for n in range(args.trials)]
    random.Random(args.seed).shuffle(order)

    idx_path = os.path.join(args.outdir, f'e36_modo{args.mode}_{args.tag}.csv')
    new = not os.path.exists(idx_path)
    with open(idx_path, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['trial', 'moved_dof', 'dir', 'step_units', 'obs_dof',
                        'f_base', 'f_end', 'df', 'pos_base', 'pos_end', 'dpos',
                        't_onset_ms', 'ref_force_before', 'aborted'])
        for k, (m, dr, n) in enumerate(order, 1):
            # re-ajuste: la fuerza del dedo de referencia a F0, moviendo TODOS a la vez
            # (en oposición no se pueden fijar por separado: se aprieta o se afloja)
            for _ in range(args.retrim_max):
                cur, _ = sample(hand, dofs, 0.25, log, 'couple', f'trim{k}')
                bad = check({d: cur[d][0] for d in dofs}, dofs, args)
                if bad:
                    print(f"ABORTA: {bad}. Abro (el objeto caerá).")
                    open_hand(hand, args)
                    return 4
                fr = cur[ref][0]
                if fr is None or abs(fr - args.f0) <= args.f0_tol:
                    break
                sgn = -1 if fr < args.f0 else +1
                for d in dofs:
                    cmds[d] = max(0, min(1000, cmds[d] + sgn))
                hand.write_block(ANGLE_SET, vec(cmds, args.hold_map))
                time.sleep(args.step_dwell)

            base, _ = sample(hand, dofs, args.base_s, log, 'couple', f'base{k}')
            su = steps[m]
            new_cmd = max(0, min(1000, cmds[m] + (-su if dr == 'cerrar' else +su)))
            hand.write_block(ANGLE_SET, vec({m: new_cmd}, args.hold_map))
            end, trace = sample(hand, dofs, args.capture_s, log, 'couple', f'step{k}')
            tail = [x for x in trace if x[0] >= args.capture_s - args.tail_s]

            forces = {d: (statistics.median([x[2][d] for x in tail]) if tail else None)
                      for d in dofs}
            pos_end = {d: (statistics.median([x[1][d] for x in tail]) if tail else None)
                       for d in dofs}
            bad = check(forces, dofs, args)

            line = []
            for j in dofs:
                fb, pb = base[j]
                df = None if None in (forces[j], fb) else forces[j] - fb
                dp = None if None in (pos_end[j], pb) else pos_end[j] - pb
                on = onset_ms(trace, j, fb, args.onset_thr_g) if fb is not None else None
                w.writerow([n, m, dr, su, j,
                            '' if fb is None else f"{fb:.0f}",
                            '' if forces[j] is None else f"{forces[j]:.0f}",
                            '' if df is None else f"{df:.0f}",
                            '' if pb is None else f"{pb:.0f}",
                            '' if pos_end[j] is None else f"{pos_end[j]:.0f}",
                            '' if dp is None else f"{dp:.1f}",
                            '' if on is None else f"{on:.1f}",
                            f"{base[ref][0]:.0f}", int(bool(bad))])
                tag = '*' if j == m else ' '
                line.append(f"{tag}{DOF_NAMES[j][:6]} {'' if df is None else f'{df:+5.0f}'}g"
                            f"/{'' if on is None else f'{on:3.0f}'}ms")
            fh.flush()
            print(f"[{k:2d}/{len(order)}] mueve {DOF_NAMES[m][:6]:<6} {dr:6s} {su:2d}u → "
                  + "   ".join(line) + (f"   ⚠ {bad}" if bad else ''))
            if bad:
                print("  Abro (el objeto caerá).")
                open_hand(hand, args)
                return 4

            hand.write_block(ANGLE_SET, vec({m: cmds[m]}, args.hold_map))
            time.sleep(args.step_dwell)
            sample(hand, dofs, 0.3, log, 'couple', f'ret{k}')

    st['cmds'] = {str(d): cmds[d] for d in dofs}
    with open(args.state, 'w') as fh2:
        json.dump(st, fh2, indent=2)
    print(f"\n  Índice: {idx_path}")
    print("  ✔ Terminado. La mano SIGUE SUJETANDO el objeto: sujétalo tú antes de abrir.")
    return 0


# ── fase 3: soltar ────────────────────────────────────────────────────────
def phase_release(hand, args, dofs, log):
    print("E3.6 · SOLTAR — abriendo la mano.")
    open_hand(hand, args)
    time.sleep(0.8)
    p, f = read_pf(hand)
    print(f"  POS: {p}")
    return 0


# ── E3.6a: sincronía ──────────────────────────────────────────────────────
def analyze_sync(path, dofs):
    """¿Refrescan los DOF en el mismo frame? Sobre el log de agarre (todos se mueven).

    Para cada lectura en la que cambia el POS de un DOF, se mira si el de los demás
    cambió EN LA MISMA lectura. Si la mano publica los 6 DOF en un solo frame, dos
    dedos que se mueven a la vez cambian siempre juntos; si publica escalonado,
    aparecen cambios aislados con un desfase fijo.
    """
    rows = [r for r in csv.DictReader(open(path)) if r['phase'] == 'grasp' and r['tag'] == 'close']
    t = [float(r['t_s']) for r in rows]
    pos = {d: [r[f'pos{d}'] for r in rows] for d in dofs}
    ch = {d: [i for i in range(1, len(rows)) if pos[d][i] != pos[d][i - 1] and pos[d][i] != '']
          for d in dofs}
    print(f"E3.6a · {len(rows)} lecturas en {t[-1]-t[0]:.1f} s "
          f"({len(rows)/(t[-1]-t[0]):.0f} Hz) durante el cierre simultáneo\n")
    for d in dofs:
        if len(ch[d]) > 2:
            dt = [(t[b] - t[a]) * 1000 for a, b in zip(ch[d], ch[d][1:])]
            print(f"  {DOF_NAMES[d]:<16} {len(ch[d]):4d} cambios de POS · "
                  f"periodo mediano {statistics.median(dt):5.1f} ms")
    print()
    for i, a in enumerate(dofs):
        for b in dofs[i + 1:]:
            if not ch[a] or not ch[b]:
                continue
            # el dedo con MENOS cambios es el que se mueve más despacio en counts: cada
            # uno de sus cambios DEBE caer en un frame en que el otro también se mueve
            slow, fast = (a, b) if len(ch[a]) <= len(ch[b]) else (b, a)
            fast_t = [t[i2] for i2 in ch[fast]]
            offs = []
            for i2 in ch[slow]:
                offs.append(min(abs(t[i2] - x) for x in fast_t) * 1000)
            same = sum(1 for o in offs if o == 0)
            nz = [o for o in offs if o > 0]
            read_ms = (t[-1] - t[0]) / len(rows) * 1000
            print(f"  {DOF_NAMES[slow]} (lento) contra {DOF_NAMES[fast]}:")
            print(f"    {same}/{len(offs)} de sus cambios ({100*same/len(offs):.0f} %) caen en la "
                  f"MISMA lectura que un cambio del otro")
            if nz:
                print(f"    los {len(nz)} restantes, a {statistics.median(nz):.1f} ms de mediana "
                      f"(una lectura son {read_ms:.1f} ms; el frame, 30.7)")
            verdict = ('MISMO FRAME' if same / len(offs) > 0.9 else
                       'ESCALONADO' if nz and statistics.median(nz) > 2 * read_ms else 'NO CONCLUYENTE')
            print(f"    → {verdict}")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────
def parse_args(argv=None):
    p = argparse.ArgumentParser(description="E3.6 — acoplamiento en los modos de pinza.")
    p.add_argument('--transport', choices=['tcp', 'serial'], default='tcp')
    p.add_argument('--ip', default='192.168.124.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--serial-port', default='/dev/ttyUSB0')
    p.add_argument('--baud', type=int, default=115200)
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)

    p.add_argument('--phase', choices=['grasp', 'couple', 'release', 'sync'], required=True)
    p.add_argument('--mode', type=int, choices=[1, 2], required=True)
    p.add_argument('--rot', type=int, default=None,
                   help='ANGLE_SET de la rotación del pulgar (DOF 5). Modo 1: 0 por defecto. '
                        'Modo 2: OBLIGATORIO, no hay valor medido.')
    p.add_argument('--tag', default='a', help='etiqueta del objeto/sesión')
    p.add_argument('--state', default=None, help='JSON de estado entre fases')
    p.add_argument('--sync-log', default=None, help='log de agarre para --phase sync')

    # agarre
    p.add_argument('--f-grasp', type=float, default=150.0, help='congela cada dedo al tocar esto (g)')
    p.add_argument('--close-target', type=int, default=0)
    p.add_argument('--close-speed', type=int, default=25)
    p.add_argument('--grasp-timeout', type=float, default=45.0)
    p.add_argument('--pre-tare-wait', type=float, default=12.0)
    p.add_argument('--place-wait', type=float, default=15.0,
                   help='ventana tras la tara para colocar el objeto, antes de cerrar')
    p.add_argument('--settle-s', type=float, default=1.5)

    # acoplamiento
    p.add_argument('--f0', type=float, default=300.0, help='fuerza del dedo de referencia (g)')
    p.add_argument('--f0-tol', type=float, default=40.0)
    p.add_argument('--retrim-dof', type=int, default=4, help='DOF cuya fuerza se lleva a F0')
    p.add_argument('--retrim-max', type=int, default=20)
    p.add_argument('--steps', default='4:12,3:6,2:6', help='DOF:unidades del escalón')
    p.add_argument('--trials', type=int, default=8)
    p.add_argument('--seed', type=int, default=36)
    p.add_argument('--base-s', type=float, default=0.6)
    p.add_argument('--capture-s', type=float, default=1.5)
    p.add_argument('--tail-s', type=float, default=0.5)
    p.add_argument('--onset-thr-g', type=float, default=15.0)
    p.add_argument('--step-dwell', type=float, default=0.25)
    p.add_argument('--min-hold-g', type=float, default=60.0)

    # seguridad
    p.add_argument('--safety-force-g', type=int, default=600)
    p.add_argument('--fset-backstop', type=int, default=700)
    p.add_argument('--temp-max', type=int, default=50)
    p.add_argument('--open-speed', type=int, default=300)
    p.add_argument('--open-angle', type=int, default=1000)
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))

    a = p.parse_args(argv)
    if a.rot is None:
        if a.mode == 2 and a.phase in ('grasp', 'couple'):
            p.error('--rot es obligatorio en modo 2: la rotación del pulgar para alcanzar '
                    'índice y medio no está medida')
        a.rot = 0
    a.hold_map = {5: a.rot}
    if a.fset_backstop <= a.safety_force_g:
        p.error('--fset-backstop debe quedar POR ENCIMA de --safety-force-g, o el paro del '
                'firmware llega antes que el software y secuestra la posición')
    if a.state is None:
        a.state = os.path.join(a.outdir, f'e36_modo{a.mode}_{a.tag}_state.json')
    return a


def main(argv=None):
    args = parse_args(argv)
    dofs = MODES[args.mode]
    os.makedirs(args.outdir, exist_ok=True)
    if args.phase == 'sync':
        return analyze_sync(args.sync_log or os.path.join(
            args.outdir, f'e36_modo{args.mode}_{args.tag}_grasp_log.csv'), dofs)

    hand = (HandModbus.open_tcp(args.ip, args.port, args.device_id, args.timeout)
            if args.transport == 'tcp' else
            HandModbus.open_serial(args.serial_port, args.baud, args.device_id, args.timeout))
    if hand is None:
        print("ERROR: sin conexión Modbus.", file=sys.stderr)
        return 1
    log = Log(os.path.join(args.outdir, f'e36_modo{args.mode}_{args.tag}_{args.phase}_log.csv'))
    rc = 1
    try:
        fn = {'grasp': phase_grasp, 'couple': phase_couple, 'release': phase_release}[args.phase]
        rc = fn(hand, args, dofs, log)
        return rc
    except KeyboardInterrupt:
        print("\n[interrumpido] Abro.")
        open_hand(hand, args)
        return 130
    except Exception as e:
        # cualquier fallo inesperado con manos cerca: abrir
        print(f"\n[ERROR {type(e).__name__}: {e}] Abro.")
        open_hand(hand, args)
        raise
    finally:
        log.close()
        hand.close()


if __name__ == '__main__':
    raise SystemExit(main())
