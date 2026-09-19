#!/usr/bin/env python3
"""Lazo de fuerza — **A1: andamiaje, seguridad y detectores. Sin controlador.**

El bucle, la guarda y los dos detectores, con el control **desactivado**. Lo que
se valida aquí es la plataforma: que la frescura se cuente por DOF y no por
duplicados, que la guarda dispare, que el detector de resbalón distinga al
actuador del objeto, y que cualquier salida deje la mano abierta.

Modos (uno por compuerta de A1):

  --modo tasas        sondea y reporta tasa de sondeo, de frescas POR DOF y jitter
  --modo passthrough  trayectoria predefinida SIN realimentación
  --modo guarda       cierra con un techo bajo y comprueba que la guarda dispara
  --modo resbalon     empuja un dedo por encima del borde y valida el detector
  --modo tara         ejercita la política de tara (E3.5)

El controlador entra en A2. Aquí `u_s`, `u_t` y `dq` se registran vacíos a
propósito: la bitácora ya tiene sus columnas para que los CSV de A1 y de A2 sean
el mismo formato.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from nucleo import (                                         # noqa: E402
    Lector, Guarda, DetectorResbalon, DetectorEscape, Tara, Bitacora,
    abrir_mano, conectar, vector, argumentos_comunes,
    NDOF, ANGLE_SET, ANGLE_ACT, FORCE_SET, SPEED_SET, DOF_NAMES,
)
from hand_modbus import report_hold                          # noqa: E402

MODOS = {1: [4, 3], 2: [4, 3, 2]}      # pulgar primero: es quien se opone a los demás


class Contexto:
    """Lo que el bucle comparte: lectura, guarda, detectores, bitácora y comandos."""

    def __init__(self, hand, args, dofs, etiqueta):
        self.hand, self.args, self.dofs = hand, args, dofs
        self.hold = {5: args.rot}
        self.lector = Lector(hand, args.aux_every)
        self.guarda = Guarda(args, dofs)
        self.resbalon = DetectorResbalon(dofs, args.resbalon_counts, args.resbalon_ventana)
        self.escape = DetectorEscape(dofs, args.escape_g, args.escape_frac,
                                     args.resbalon_ventana)
        self.tara = Tara(args.tara_espera)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.bit = Bitacora(os.path.join(args.outdir, f'a1_{etiqueta}_{ts}.csv'))
        self.cmds = {}
        self.t0 = time.perf_counter()
        self.eventos = []

    def lee_comandos(self):
        a = self.hand.read_block(ANGLE_ACT)
        if a:
            self.cmds = {d: a[d] for d in self.dofs}
        return self.cmds

    def manda(self, cmds):
        self.cmds.update(cmds)
        self.hand.write_block(ANGLE_SET, vector(cmds, self.hold))

    def registra(self, t, p, f, c, fp, ff, frame=0, evento=''):
        g = lambda v, d: ('' if not v or v[d] is None else v[d])     # noqa: E731
        self.bit.fila(
            t=f"{t - self.t0:.5f}",
            frame=int(frame),
            fresca_f=''.join('1' if ff[d] else '0' for d in self.dofs),
            fresca_p=''.join('1' if fp[d] else '0' for d in self.dofs),
            F_T=g(f, 4), F_I=g(f, 3), F_M=g(f, 2) if 2 in self.dofs else '',
            POS_T=g(p, 4), POS_I=g(p, 3), POS_M=g(p, 2) if 2 in self.dofs else '',
            cmd_T=self.cmds.get(4, ''), cmd_I=self.cmds.get(3, ''),
            cmd_M=self.cmds.get(2, '') if 2 in self.dofs else '',
            I_mA=g(c, self.dofs[0]), evento=evento)


def bucle(ctx, duracion, actuador=None, parar_en_evento=True):
    """El bucle común: sondea, actualiza guarda y detectores, registra.

    `actuador(ctx, t, p, f, ff)` decide comandos. En A1 nunca es un controlador:
    es una trayectoria predefinida o una rampa de prueba.

    El control **solo avanzaría con muestra fresca del dedo que regula**; aquí se
    registra la frescura para poder demostrarlo en la compuerta.
    """
    t_fin = time.perf_counter() + duracion
    motivo = None
    while time.perf_counter() < t_fin:
        t, p, f, c, fp, ff, frame = ctx.lector.muestra()
        if not (p and f):
            continue
        ev = ''
        temps = None
        m = ctx.guarda.revisa(f, c, temps)
        if m:
            motivo = f"GUARDA: {m}"
            ctx.registra(t, p, f, c, fp, ff, frame, 'guarda')
            break
        r = ctx.resbalon.actualiza(t, p, ctx.cmds)
        if r:
            ev = f"resbalon_actuador dof={r['dof']} {r['counts']:+.0f}counts"
            ctx.eventos.append(('resbalon', t - ctx.t0, r))
            print(f"  ⚠ RESBALÓN DEL ACTUADOR · {DOF_NAMES[r['dof']]} retrocede "
                  f"{r['counts']:.0f} counts en <{r['ventana']:.1f} s  → aflojar")
        e = ctx.escape.actualiza(t, p, f)
        if e:
            ev = (ev + ' ' if ev else '') + 'escape_objeto'
            ctx.eventos.append(('escape', t - ctx.t0, e))
            print("  ⚠ EL OBJETO SE ESCAPA · cae la fuerza en todos los dedos y POS "
                  "no retrocede  → apretar o abortar")
        ctx.registra(t, p, f, c, fp, ff, frame, ev)
        if actuador:
            actuador(ctx, t, p, f, ff)
        if ev and parar_en_evento:
            motivo = f"EVENTO: {ev}"
            break
    return motivo


def informe_tasas(ctx):
    son, fr, ff, fpp, jit = ctx.lector.tasas(ctx.dofs)
    print(f"\n  sondeo {son:7.1f} Hz · jitter (p10–p90) {jit:.1f} ms · "
          f"{ctx.lector.n_lecturas} lecturas")
    print(f"  FRAMES  {fr:7.1f} Hz   ← la mano publica a ~32.6 Hz; esto es lo que "
          f"dispara el control")
    print(f"  {'DOF':<16}{'fuerza fresca':>15}{'POS fresca':>13}")
    for d in ctx.dofs:
        print(f"  {DOF_NAMES[d]:<16}{ff[d]:>12.1f} Hz{fpp[d]:>10.1f} Hz")
    print(f"  duplicados descartados: {100*(1-fr/max(son,1)):.1f} % de las lecturas "
          f"no traían estado nuevo")
    print(f"  la frescura POR DOF subestima: si el entero se repite entre frames "
          f"cuenta como no fresca")


# ── modos ─────────────────────────────────────────────────────────────────
def modo_tasas(ctx, args):
    print(f"A1 · TASAS · {args.duracion:.0f} s sondeando sin mover nada")
    ctx.lee_comandos()
    bucle(ctx, args.duracion)
    informe_tasas(ctx)
    return 0


def modo_passthrough(ctx, args):
    """Trayectoria predefinida SIN realimentación: exige que el bucle sostenga la
    tasa mientras escribe, que es la condición en la que vivirá el controlador."""
    d = args.dof
    print(f"A1 · PASSTHROUGH · {DOF_NAMES[d]} recorre una trayectoria sin realimentación")
    ctx.lee_comandos()
    base = ctx.cmds.get(d)
    if base is None:
        print("no se pudo leer ANGLE_ACT"); return 1
    ctx.hand.write_block(SPEED_SET, [args.vel_cierre] * NDOF)
    ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)
    pasos = [0, -args.amplitud, 0, +args.amplitud, 0]
    estado = {'i': 0, 't_prox': 0.0}

    def actuador(c, t, p, f, ff):
        if t - c.t0 < estado['t_prox']:
            return
        if estado['i'] >= len(pasos):
            return
        obj = max(0, min(1000, base + pasos[estado['i']]))
        c.manda({d: obj})
        print(f"    t={t-c.t0:5.1f}s  ANGLE_SET {DOF_NAMES[d]} → {obj}")
        estado['i'] += 1
        estado['t_prox'] += args.paso_s

    m = bucle(ctx, len(pasos) * args.paso_s + 1.0, actuador, parar_en_evento=False)
    informe_tasas(ctx)
    if m:
        print(f"  {m}")
    return 0


def modo_guarda(ctx, args):
    """Cierra un dedo en el aire con el techo de fuerza bajado hasta el residual de
    flexión. La guarda debe disparar SIN que haya objeto: comprueba el camino de
    abortar y abrir, no el contacto."""
    d = args.dof
    print(f"A1 · GUARDA · cierra {DOF_NAMES[d]} en el aire con techo {args.techo_fuerza:.0f} g")
    print("  el dedo NO debe tocar nada: lo que dispara es su propio residual de flexión")
    ctx.lee_comandos()
    ctx.hand.write_block(SPEED_SET, [args.vel_cierre] * NDOF)
    ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)
    ctx.manda({d: args.objetivo_angulo})

    m = bucle(ctx, args.duracion)
    if m and m.startswith('GUARDA'):
        print(f"  ✔ {m}")
        return 0
    print(f"  ✗ la guarda NO disparó en {args.duracion:.0f} s "
          f"(motivo de salida: {m or 'fin de tiempo'})")
    return 3


def modo_resbalon(ctx, args):
    """Empuja un dedo contra el objeto hasta pasarse del borde, y valida que el
    detector dispare.

    Es la versión EN LÍNEA de lo que `exp3_ceiling_check.py` medía offline: allí se
    congelaba el comando y se miraba la traza después; aquí el detector tiene que
    verlo mientras ocurre, que es lo que el lazo necesitará.
    """
    d = args.dof
    print(f"A1 · RESBALÓN · sube {DOF_NAMES[d]} hacia {args.objetivo:.0f} g y congela")
    print(f"  detector: POS retrocede > {args.resbalon_counts} counts en "
          f"< {args.resbalon_ventana:.1f} s (normal 0–2, resbalón ~50)")
    ctx.lee_comandos()
    t, p, f, c, fp, ff, frame = ctx.lector.muestra()
    if not f or f[d] < args.contacto_min:
        print(f"  ABORTA: {DOF_NAMES[d]} marca {f[d] if f else '—'} g, por debajo de "
              f"--contacto-min {args.contacto_min:.0f}.")
        print("  Este modo NO establece el agarre: parte de un contacto YA hecho, "
              "porque la subida son pasos de 2 unidades y desde la mano abierta no llega.")
        return 2
    print(f"  partiendo de {f[d]} g")
    ctx.hand.write_block(SPEED_SET, [args.vel_cierre] * NDOF)
    ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)

    # La rampa va DENTRO del bucle común, no en un lazo aparte. La primera versión
    # la escribió como bucle propio y ahí el detector no corría: justo en la fase
    # donde se cruza el borde, que es cuando tiene que disparar.
    estado = {'t_prox': 0.0, 'alcanzado': False}

    def rampa(c, t, p, f, ff):
        if f[d] >= args.objetivo:
            estado['alcanzado'] = True
            return
        if t - c.t0 < estado['t_prox']:
            return
        cmd = c.cmds.get(d)
        if cmd is None or cmd <= 0:
            return
        c.manda({d: cmd - args.paso_u})
        estado['t_prox'] += args.paso_dwell

    m = bucle(ctx, args.seek_s, rampa, parar_en_evento=True)
    if not ctx.eventos:
        print(f"  {'alcanzada la consigna' if estado['alcanzado'] else 'fin de la rampa'}"
              f" · congelo el comando y observo {args.duracion:.0f} s")
        m = bucle(ctx, args.duracion, parar_en_evento=True)

    hubo = [e for e in ctx.eventos if e[0] == 'resbalon']
    if hubo:
        t_ev, r = hubo[0][1], hubo[0][2]
        print(f"\n  ✔ DETECTADO a t={t_ev:.2f} s del congelado · "
              f"{DOF_NAMES[r['dof']]} retrocedió {r['counts']:.0f} counts")
        return 0
    print(f"\n  ✗ no se detectó resbalón ({m or 'fin de tiempo'}). "
          f"O no se cruzó el borde, o el umbral es alto.")
    return 3


def modo_tara(ctx, args):
    """Ejercita la política de E3.5: la tara debe RECHAZARSE con carga en las yemas
    o antes de 10 s desde la última suelta, y aceptarse cuando toque."""
    print("A1 · TARA · política de E3.5")
    t, p, f, c, fp, ff, frame = ctx.lector.muestra()
    ok, por_que = ctx.tara.puede(f, ctx.dofs)
    print(f"  estado actual: " + "  ".join(f"{DOF_NAMES[d]} {f[d]:+d} g" for d in ctx.dofs))
    print(f"  ¿puede tarar? {'SÍ' if ok else 'NO'} — {por_que}")

    print("\n  simulo una suelta reciente...")
    ctx.tara.marca_suelta()
    ok2, por_que2 = ctx.tara.puede(f, ctx.dofs)
    print(f"  ¿puede tarar? {'SÍ' if ok2 else 'NO'} — {por_que2}")
    if ok2:
        print("  ✗ debería haberla BLOQUEADO")
        return 3
    print(f"\n  esperando {args.tara_espera:.0f} s...")
    time.sleep(args.tara_espera + 0.5)
    t, p, f, c, fp, ff, frame = ctx.lector.muestra()
    ok3, por_que3 = ctx.tara.puede(f, ctx.dofs)
    print(f"  ¿puede tarar? {'SÍ' if ok3 else 'NO'} — {por_que3}")
    if ok3 and args.aplicar:
        hecho, msg = ctx.tara.aplica(ctx.hand, f, ctx.dofs)
        t, p, f, c, fp, ff, frame = ctx.lector.muestra()
        print(f"  {msg}: " + "  ".join(f"{DOF_NAMES[d]} {f[d]:+d} g" for d in ctx.dofs))
    return 0 if ok3 else 3


def main(argv=None):
    p = argparse.ArgumentParser(description="Lazo de fuerza · A1 (sin controlador)")
    argumentos_comunes(p)
    p.add_argument('--modo', required=True,
                   choices=['tasas', 'passthrough', 'guarda', 'resbalon', 'tara'])
    p.add_argument('--pinza', type=int, choices=[1, 2], default=1)
    p.add_argument('--dof', type=int, default=3, help='dedo bajo prueba en los modos de un dedo')
    p.add_argument('--duracion', type=float, default=15.0)
    p.add_argument('--amplitud', type=int, default=60, help='passthrough: unidades de ANGLE_SET')
    p.add_argument('--paso-s', type=float, default=2.0)
    p.add_argument('--objetivo-angulo', type=int, default=300, help='guarda: hacia dónde cierra')
    p.add_argument('--objetivo', type=float, default=900.0, help='resbalón: fuerza a alcanzar')
    p.add_argument('--paso-u', type=int, default=2)
    p.add_argument('--paso-dwell', type=float, default=0.30)
    p.add_argument('--seek-s', type=float, default=120.0)
    p.add_argument('--contacto-min', type=float, default=80.0,
                   help='resbalón: fuerza mínima para considerar que ya hay contacto')
    p.add_argument('--aplicar', action='store_true', help='tara: aplicarla de verdad')
    args = p.parse_args(argv)

    dofs = MODOS[args.pinza]
    if args.modo in ('passthrough', 'guarda', 'resbalon') and args.dof not in dofs:
        dofs = [args.dof] + [d for d in dofs if d != args.dof]

    hand = conectar(args)
    if hand is None:
        print("ERROR: sin conexión Modbus.", file=sys.stderr)
        return 1
    ctx = Contexto(hand, args, dofs, args.modo)
    print(f"  DOF implicados: {', '.join(DOF_NAMES[d] for d in dofs)} · "
          f"rotación anclada en ANGLE_SET {args.rot}")
    report_hold(hand, ctx.hold, 6, 3.0, args.vel_abrir)
    rc = 1
    try:
        fn = {'tasas': modo_tasas, 'passthrough': modo_passthrough,
              'guarda': modo_guarda, 'resbalon': modo_resbalon, 'tara': modo_tara}[args.modo]
        rc = fn(ctx, args)
        return rc
    except KeyboardInterrupt:
        print("\n[interrumpido]")
        return 130
    finally:
        # Salida por cualquier vía: la mano se abre. Sin excepciones.
        abrir_mano(hand, args, ctx.hold)
        ctx.tara.marca_suelta()
        ctx.bit.cierra()
        print(f"  bitácora: {ctx.bit.path}  ({ctx.bit.n} filas) · mano abierta")
        hand.close()


if __name__ == '__main__':
    raise SystemExit(main())
