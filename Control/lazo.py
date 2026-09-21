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
import csv
import random
import statistics
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from nucleo import (                                         # noqa: E402
    Lector, Guarda, Disparador, PI, DetectorResbalon, DetectorEscape, Tara, Bitacora,
    EstimadorRLS,
    abrir_mano, conectar, vector, argumentos_comunes,
    NDOF, ANGLE_SET, ANGLE_ACT, FORCE_SET, SPEED_SET, DOF_NAMES,
)
from hand_modbus import report_hold                          # noqa: E402

MODOS = {1: [4, 3], 2: [4, 3, 2]}      # pulgar primero: es quien se opone a los demás


class Contexto:
    """Lo que el bucle comparte: lectura, guarda, detectores, bitácora y comandos."""

    def __init__(self, hand, args, dofs, etiqueta):
        self.hand, self.args, self.dofs = hand, args, dofs
        # --rot -1: no anclar. El indice se caracterizo sin ancla, y A2 compara
        # contra esas medidas, asi que la condicion debe ser la misma.
        self.hold = {} if args.rot < 0 else {5: args.rot}
        self.lector = Lector(hand, args.aux_every)
        self.guarda = Guarda(args, dofs)
        self.resbalon = DetectorResbalon(dofs, args.resbalon_counts, args.resbalon_ventana)
        self.escape = DetectorEscape(dofs, args.escape_g, args.escape_frac,
                                     args.resbalon_ventana)
        self.tara = Tara(args.tara_espera)
        # el control avanza por DOF, no por "frame" de bloque: ver Disparador
        self.disp = {d: Disparador(d, args.disparo_plazo) for d in dofs}
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.bit = Bitacora(os.path.join(args.outdir, f'a1_{etiqueta}_{ts}.csv'))
        self.cmds = {}
        # CONJUNTO, no un solo DOF: en A3 se regulan dos dedos y cada uno es
        # dueño de su disparo. Con un escalar, el segundo lazo volveria a recibir
        # dt = 0 — el mismo bug que dejo Ki muerto en A2.
        self.dof_control = set()     # lo fija el modo que regula; ver bucle()
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
            # el DOF que se regula, no dofs[0]: registrar el pulgar en una tanda
            # de indice daba 0 mA en TODAS las filas, incluida la aproximacion
            I_mA=g(c, min(self.dof_control) if self.dof_control else self.dofs[0]),
            evento=evento)


def bucle(ctx, duracion, actuador=None, parar_en_evento=True):
    """El bucle común: sondea, actualiza guarda y detectores, registra.

    `actuador(ctx, t, p, f, ff)` decide comandos. En A1 nunca es un controlador:
    es una trayectoria predefinida o una rampa de prueba.

    El control **solo avanzaría con muestra fresca del dedo que regula**; aquí se
    registra la frescura para poder demostrarlo en la compuerta.
    """
    t_fin = time.perf_counter() + duracion
    motivo = None
    t_temp = 0.0
    temps = None
    while time.perf_counter() < t_fin:
        t, p, f, c, fp, ff, frame = ctx.lector.muestra()
        if not (p and f):
            continue
        ev = ''
        # La temperatura SI se vigila: la guarda la soportaba pero nadie se la
        # daba. Cada 5 s, que es lento comparado con la inercia termica y no
        # cuesta un viaje Modbus por iteracion.
        if t - t_temp > 5.0:
            temps = ctx.hand.read_temps()
            t_temp = t
        m = ctx.guarda.revisa(f, c, temps)
        if m:
            motivo = f"GUARDA: {m}"
            print(f"  ⛔ GUARDA · {m}")
            ctx.registra(t, p, f, c, fp, ff, frame, 'guarda')
            break
        r = ctx.resbalon.actualiza(t, p, ctx.cmds, f, ctx.args.contacto_min)
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
        # El disparo de `dof_control` es del ACTUADOR: `toca()` muta `t_ultimo`,
        # asi que consumirlo aqui le entregaria dt = 0 (matando a Ki) y le
        # ocultaria los disparos por plazo. Los demas DOF se cuentan aqui.
        for d in ctx.dofs:
            if d not in ctx.dof_control:
                ctx.disp[d].toca(t, ff)
        ctx.registra(t, p, f, c, fp, ff, frame, ev)
        if actuador and actuador(ctx, t, p, f, ff) is True:
            break
        if ev and parar_en_evento:
            motivo = f"EVENTO: {ev}"
            break
    return motivo


def informe_tasas(ctx):
    son, fr, ff, fpp, jit = ctx.lector.tasas(ctx.dofs)
    T = max(time.perf_counter() - ctx.lector.t_ini, 1e-6)
    print(f"\n  sondeo {son:7.1f} Hz · jitter (p10–p90) {jit:.1f} ms · "
          f"{ctx.lector.n_lecturas} lecturas")
    print(f"  DISPARO DEL CONTROL (por DOF, cambio o plazo de "
          f"{ctx.args.disparo_plazo*1000:.0f} ms):")
    for d in ctx.dofs:
        print(f"    {DOF_NAMES[d]:<16}{ctx.disp[d].resumen(T)}")
    print(f"  bloque cambiado {fr:7.1f} Hz  ← SOBRECUENTA: es la unión de 6 DOF "
          f"escalonados, no un frame")
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
        if t < estado['t_prox']:
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
        if t < estado['t_prox']:
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



def _aproxima(ctx, args, d, hasta):
    """Pre-posición rápida y luego pasos pequeños hasta `hasta` gramos.

    Las dos fases son necesarias: desde la mano abierta hay ~1300 counts hasta el
    contacto, y a pasos de 2 unidades no se cubren. La pre-posición se detiene
    ANTES del objeto —de ahí que sea un ángulo medido del sondeo, no un número
    inventado— y a partir de ahí se entra despacio, que es la política híbrida que
    el Exp 2 validó para no golpear.
    """
    ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)
    if args.angulo_aprox is not None:
        print(f"  pre-posición rápida de {DOF_NAMES[d]} a ANGLE_SET {args.angulo_aprox}")
        ctx.hand.write_block(SPEED_SET, [args.vel_aprox] * NDOF)
        ctx.lee_comandos()
        ctx.manda({d: args.angulo_aprox})
        bucle(ctx, args.aprox_s, parar_en_evento=True)
        # NO releer ANGLE_ACT aquí: es dónde ESTÁ el dedo, no lo que se le pidió. Si
        # aún no ha llegado, releerlo cancela la pre-posición y lo deja a medias.
        ctx.cmds[d] = args.angulo_aprox
    else:
        ctx.lee_comandos()
    print(f"  aproximando {DOF_NAMES[d]} hasta {hasta:.0f} g...")
    ctx.hand.write_block(SPEED_SET, [args.vel_cierre] * NDOF)
    # El dwell se cuenta desde que arranca ESTA rampa. Medirlo contra `ctx.t0`
    # (inicio de la tanda) deja `t_prox` muy por detras de `t`, y la rampa suelta
    # de golpe tantos pasos como segundos lleve la tanda: inofensivo en una tanda
    # de un solo trial, un golpe contra el objeto en la sexta de una intercalada.
    estado = {'t_prox': None, 'ok': False}

    def rampa(c, t, p, f, ff):
        if estado['t_prox'] is None:
            estado['t_prox'] = t
        if f[d] >= hasta:
            # CONGELAR donde está, no solo dejar de mandar pasos: el dedo sigue
            # viajando hacia el último comando y se pasa de largo. Medido: llegaba
            # a 711 g cuando se le pedía parar en 150.
            a = c.hand.read_block(ANGLE_ACT)
            if a:
                c.manda({d: a[d]})
            estado['ok'] = True
            return True
        if t < estado['t_prox']:
            return
        cmd = c.cmds.get(d)
        if cmd is None or cmd <= 0:
            return
        c.manda({d: cmd - args.paso_u})
        estado['t_prox'] += args.paso_dwell

    bucle(ctx, args.seek_s, rampa, parar_en_evento=True)
    return estado['ok']


def modo_pi(ctx, args):
    """A2 · lazo SISO de fuerza sobre un dedo, contra el bloque apoyado."""
    d = args.dof
    pi = PI(args.kp, args.ki, args.lam, args.banda,
            args.paso_cierra, args.paso_abre, args.dq_max, args.refractario)
    print(f"A2 · PI · {DOF_NAMES[d]} → F* = {args.ref:.0f} g")
    print(f"  Kp={args.kp:.4f}  Ki={args.ki:.4f}  fuga λ={args.lam:.3f}  "
          f"banda={args.banda:.0f} g  cuanto {args.paso_cierra}↓/{args.paso_abre}↑ u")

    if not _aproxima(ctx, args, d, args.ref * args.frac_aprox):
        print("  ABORTA: no se alcanzó el contacto de partida")
        return 3
    t_ini = time.perf_counter()
    ctx.dof_control = {d}
    ctx.disp[d].t_ultimo = None
    hist = []

    def control(c, t, p, f, ff):
        toca, dt, por_que = c.disp[d].toca(t, ff)
        if not toca:
            return
        dq, e, P, I = pi.paso(args.ref, f[d], dt, t)
        if dq:
            cmd = c.cmds.get(d)
            if cmd is not None:
                # dq > 0 CIERRA, y cerrar es BAJAR ANGLE_SET
                c.manda({d: max(0, min(1000, cmd - dq))})
        hist.append((t - t_ini, f[d], e, dq, P, I))

    m = bucle(ctx, args.duracion, control, parar_en_evento=True)

    if not hist:
        print("  sin muestras de control"); return 3
    T = [h[0] for h in hist]; F = [h[1] for h in hist]; E = [h[2] for h in hist]
    cola = [h for h in hist if h[0] >= T[-1] - args.cola_s]
    ef = [abs(h[2]) for h in cola]
    pico = max(F)
    asent = next((h[0] for h in hist
                  if all(abs(g[2]) <= args.banda for g in hist[hist.index(h):]
                         if g[0] <= h[0] + 2.0)), None)
    print(f"\n  {len(hist)} pasos de control en {T[-1]:.0f} s "
          f"({len(hist)/max(T[-1],1e-6):.1f} Hz) · {pi.n_accion} con acción, "
          f"{pi.n_banda} en banda, {pi.n_espera} esperando refractario")
    print(f"  pico {pico:.0f} g ({100*(pico-args.ref)/args.ref:+.0f} % sobre F*)")
    print(f"  error en régimen (últimos {args.cola_s:.0f} s): "
          f"mediana {statistics.median(ef):.0f} g · máx {max(ef):.0f} g")
    print(f"  en unidades de cuanto del dedo ({args.banda:.0f} g): "
          f"{statistics.median(ef)/max(args.banda,1):.2f} × banda")
    if asent is not None:
        print(f"  entra en banda a los {asent:.1f} s")
    if m:
        print(f"  {m}")
    return 0


def modo_firmware(ctx, args):
    """Brazo de comparación: la consigna se la damos al FIRMWARE por FORCE_SET y
    cerramos a v=25 (modo A del Exp 2). Sin lazo."""
    d = args.dof
    print(f"A2 · FIRMWARE · {DOF_NAMES[d]} → FORCE_SET = {args.ref:.0f} g, v={args.vel_cierre}")
    ctx.lee_comandos()
    ctx.hand.write_block(SPEED_SET, [args.vel_cierre] * NDOF)
    ctx.hand.write_block(FORCE_SET, [int(args.ref)] * NDOF)
    ctx.manda({d: args.objetivo_angulo})
    t_ini = time.perf_counter()
    hist = []

    def observa(c, t, p, f, ff):
        hist.append((t - t_ini, f[d]))

    m = bucle(ctx, args.duracion, observa, parar_en_evento=True)
    if not hist:
        print("  sin muestras"); return 3
    T=[h[0] for h in hist]; F=[h[1] for h in hist]
    cola=[h[1] for h in hist if h[0] >= T[-1]-args.cola_s]
    print(f"\n  pico {max(F):.0f} g ({100*(max(F)-args.ref)/args.ref:+.0f} % sobre la consigna)")
    print(f"  en régimen (últimos {args.cola_s:.0f} s): mediana {statistics.median(cola):.0f} g "
          f"→ error {statistics.median(cola)-args.ref:+.0f} g")
    # FORCE_SET vuelve a un valor seguro antes de salir
    ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)
    if m:
        print(f"  {m}")
    return 0



SOPORTE = [0, 1, 2, 3]      # menique, anular, medio, indice: sostienen el bloque


def _prepara_soporte(ctx, args):
    """Pre-flexiona el soporte para que quede margen de perturbar.

    La autoridad es de un solo sentido: flexionar carga el pulgar (+56 g en 32 u,
    medido), extender apenas descarga (-23 g en 45 u, y satura) porque el bloque
    no baja con los dedos que se retiran — lo retiene la friccion del pulgar. Con
    el soporte en reposo (1000) no habria hacia donde flexionar.
    """
    if args.soporte is None:
        return
    ctx.hand.write_block(SPEED_SET, [args.vel_aprox] * NDOF)
    ctx.manda({d: args.soporte for d in SOPORTE})
    bucle(ctx, 2.0, parar_en_evento=False)


def _perturbador(ctx, args, hist):
    """Devuelve un callback que aplica el escalon UNA vez, a `--perturba-t`.

    Identico en los dos brazos: es la perturbacion, no el tratamiento.
    """
    estado = {'hecho': False, 't': None}

    def aplica(t_rel):
        if estado['hecho'] or args.perturba_u <= 0:
            return
        if t_rel >= args.perturba_t:
            ctx.manda({d: args.soporte - args.perturba_u for d in SOPORTE})
            estado['hecho'] = True
            estado['t'] = t_rel
    return aplica, estado


def _trial_firmware(ctx, args):
    """Brazo A: la consigna la ejecuta el FIRMWARE por FORCE_SET, cierre a v=25.

    Comparte con el brazo B la MISMA pre-posicion rapida. Sin ella el firmware
    arranca desde la mano abierta y se gasta parte del trial viajando, asi que lo
    que se compararia es quien llega antes y no quien sostiene la consigna.
    """
    d = args.dof
    _prepara_soporte(ctx, args)
    if args.angulo_aprox is not None:
        ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)
        ctx.hand.write_block(SPEED_SET, [args.vel_aprox] * NDOF)
        ctx.lee_comandos()
        ctx.manda({d: args.angulo_aprox})
        bucle(ctx, args.aprox_s, parar_en_evento=True)
        ctx.cmds[d] = args.angulo_aprox
    else:
        ctx.lee_comandos()
    ctx.hand.write_block(SPEED_SET, [args.vel_cierre] * NDOF)
    ctx.hand.write_block(FORCE_SET, [int(args.ref)] * NDOF)
    ctx.manda({d: args.objetivo_angulo})
    t0 = time.perf_counter()
    h = []
    pert, est = _perturbador(ctx, args, h)

    def obs(c, t, p, f, ff):
        pert(t - t0)
        h.append((t - t0, f[d], c.lector.cur[d] if c.lector.cur[d] is not None else 0))

    bucle(ctx, args.hold_s, obs, parar_en_evento=True)
    ctx.t_pert = est['t']
    ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)
    return h


def _trial_lazo(ctx, args):
    """Brazo B: la consigna la sostiene el LAZO."""
    d = args.dof
    pi = PI(args.kp, args.ki, args.lam, args.banda,
            args.paso_cierra, args.paso_abre, args.dq_max, args.refractario)
    _prepara_soporte(ctx, args)
    if not _aproxima(ctx, args, d, args.ref * args.frac_aprox):
        return None
    ctx.dof_control = {d}
    ctx.disp[d].t_ultimo = None
    t0 = time.perf_counter()
    h = []

    pert, est = _perturbador(ctx, args, h)

    def ctl(c, t, p, f, ff):
        pert(t - t0)
        toca, dt, _ = c.disp[d].toca(t, ff)
        if toca:
            dq, e, P, I = pi.paso(args.ref, f[d], dt, t)
            if dq:
                cmd = c.cmds.get(d)
                if cmd is not None:
                    c.manda({d: max(0, min(1000, cmd - dq))})
        h.append((t - t0, f[d], c.lector.cur[d] if c.lector.cur[d] is not None else 0))

    bucle(ctx, args.hold_s, ctl, parar_en_evento=True)
    ctx.t_pert = est['t']
    return h


def _metricas(h, args):
    if not h or len(h) < 20:
        return None
    T = [x[0] for x in h]; F = [x[1] for x in h]
    cola = [x for x in h if x[0] >= T[-1] - args.cola_s]
    f_fin = statistics.median([x[1] for x in cola])
    m = dict(pico=max(F), err_reg=f_fin - args.ref, err_abs=abs(f_fin - args.ref),
             I_med=statistics.median([x[2] for x in cola]), n=len(h),
             f_base=None, salto=None, recup=None, resid=None)
    if args.perturba_u > 0 and T[-1] > args.perturba_t + 5:
        tp = args.perturba_t
        antes = [x[1] for x in h if tp - 5 <= x[0] < tp]
        desp = [x[1] for x in h if tp <= x[0] <= tp + 3]
        if antes and desp:
            # LA PERTURBACION ES EL ESCALON DE `--perturba-u`, identico por
            # construccion en los dos brazos. El salto de FUERZA no lo es: es ya
            # parte de la RESPUESTA, porque el lazo empieza a abrir dentro de la
            # ventana. Normalizar por el premiaba al que reacciona rapido con un
            # divisor mas pequeño (piloto: +33 g el lazo contra +83 g el firmware,
            # del mismo escalon de 32 u).
            m['f_base'] = statistics.median(antes)
            m['salto'] = max(desp) - m['f_base']
            # Lo que se compara es si VUELVE A SU PROPIA LINEA DE BASE. Medirlo
            # contra F* mezclaria el rechazo de la perturbacion con el error en
            # regimen que el brazo ya arrastraba antes de perturbarlo.
            m['resid'] = f_fin - m['f_base']
            if abs(m['salto']) >= 10:
                m['recup'] = 1.0 - abs(m['resid']) / abs(m['salto'])
    return m


def modo_comparar(ctx, args):
    """A2 · protocolo intercalado: los dos brazos en UNA tanda, orden aleatorizado
    por bloques balanceados, misma tara y mismo montaje.

    Dos tandas separadas del mismo dedo, objeto y pose difirieron en un factor 2
    por deriva del cero entre tandas (Exp 2). Comparar entre tandas no vale.
    """
    d = args.dof
    # Aleatorizacion POR BLOQUES: se baraja DENTRO de cada par, no el conjunto
    # entero. Barajar el conjunto balanceado deja rachas —la primera tanda salio
    # L L L L L F— y una racha carga cualquier deriva lenta (la temperatura subio
    # 36→38 °C en seis trials) sobre el brazo que toco agrupado. Con bloques de
    # dos, cada par lleva uno de cada y el equilibrio es local, no solo global.
    rnd = random.Random(args.seed)
    orden = []
    for _ in range(args.pares):
        par = ['firmware', 'lazo']
        rnd.shuffle(par)
        orden += par
    print(f"A2 · INTERCALADO · {DOF_NAMES[d]} · F* = {args.ref:.0f} g · "
          f"{args.pares} pares · orden {' '.join(o[0].upper() for o in orden)}")

    # El sufijo de perturbacion NO es cosmetico: sin el, una tanda con escalon
    # se anexaria al indice de la compuerta A2 sin perturbacion y mezclaria dos
    # experimentos distintos en el mismo fichero.
    suf = f'_pert{args.perturba_u}' if args.perturba_u > 0 else ''
    idx = os.path.join(args.outdir, f'a2_intercalado_dof{d}_F{int(args.ref)}{suf}.csv')
    nuevo_f = not os.path.exists(idx)
    res = {'firmware': [], 'lazo': []}
    with open(idx, 'a', newline='') as fh:
        w = csv.writer(fh)
        if nuevo_f:
            w.writerow(['bloque', 'n', 'brazo', 'pico', 'err_reg', 'I_med',
                        'temp', 'n_muestras', 'tarado', 'nota',
                        'f_base', 'salto', 'resid', 'recup'])
        for k, brazo in enumerate(orden, 1):
            abrir_mano(ctx.hand, args, ctx.hold)
            # Cada trial arranca limpio: si no, el timeout de la guarda corre desde
            # el inicio de la TANDA y la historia de los detectores cruza la
            # apertura, que parece un retroceso de POS de 11 counts.
            ctx.guarda.t0 = time.perf_counter()
            ctx.guarda.cur_alta = 0
            ctx.resbalon.reinicia()
            ctx.escape.reinicia()
            ctx.dof_control = set()
            ctx.tara.marca_suelta()
            print(f"\n[{k}/{len(orden)}] {brazo.upper()} · esperando "
                  f"{args.tara_espera:.0f} s para tarar (E3.5)...")
            time.sleep(args.tara_espera + 0.5)
            # una sola muestra puede ser ruido; la mediana de unas cuantas, no
            mu = []
            while len(mu) < 5:
                _t, _p, _f, _c, _fp, _ff, _fr = ctx.lector.muestra()
                if _f:
                    mu.append(_f)
            f = [int(statistics.median([m[d] for m in mu])) for d in range(NDOF)]
            ok, por_que = ctx.tara.aplica(ctx.hand, f, ctx.dofs)
            if not ok:
                print(f"  tara rechazada: {por_que}")
            temps = ctx.hand.read_temps()
            # segundo reinicio, ya con el dedo en reposo: el primero (tras abrir)
            # deja dentro de la ventana el propio viaje de apertura
            ctx.resbalon.reinicia(); ctx.escape.reinicia()
            ctx.guarda.t0 = time.perf_counter()
            h = _trial_firmware(ctx, args) if brazo == 'firmware' else _trial_lazo(ctx, args)
            m = _metricas(h, args) if h else None
            if m is None:
                # se registra igual: un trial abortado que desaparece del indice
                # deja un N que no se puede auditar
                print("  trial sin datos utilizables — queda anotado como abortado")
                w.writerow([args.bloque, k, brazo, '', '', '',
                            temps[d] if temps else '', 0,
                            'si' if ok else 'no', 'abortado', '', '', '', ''])
                fh.flush()
                continue
            res[brazo].append(m)
            w.writerow([args.bloque, k, brazo, f"{m['pico']:.0f}",
                        f"{m['err_reg']:+.0f}", f"{m['I_med']:.0f}",
                        temps[d] if temps else '', m['n'],
                        'si' if ok else 'no', '',
                        '' if m['f_base'] is None else f"{m['f_base']:.0f}",
                        '' if m['salto'] is None else f"{m['salto']:+.0f}",
                        '' if m['resid'] is None else f"{m['resid']:+.0f}",
                        '' if m['recup'] is None else f"{m['recup']:.3f}"])
            fh.flush()
            extra = ''
            if m['salto'] is not None:
                extra = (f" · pico {m['salto']:+.0f} g sobre base {m['f_base']:.0f}"
                         f" → residual {m['resid']:+.0f} g"
                         + (f" ({100*m['recup']:.0f} % rechazado)" if m['recup'] is not None else ''))
            print(f"  pico {m['pico']:4.0f} g · error en régimen {m['err_reg']:+5.0f} g · "
                  f"I {m['I_med']:3.0f} mA · {temps[d] if temps else '?'} °C{extra}")

    print(f"\n  índice: {idx}")
    for b in ('firmware', 'lazo'):
        v = res[b]
        if not v:
            continue
        e = [x['err_abs'] for x in v]
        r = [x['recup'] for x in v if x['recup'] is not None]
        sa = [x['salto'] for x in v if x['salto'] is not None]
        linea = (f"  {b:9s} n={len(v)} · |error| mediana {statistics.median(e):5.1f} g "
                 f"(rango {min(e):.0f}–{max(e):.0f}) · pico mediana "
                 f"{statistics.median([x['pico'] for x in v]):5.0f} g")
        rs = [x['resid'] for x in v if x['resid'] is not None]
        if sa:
            linea += f" · pico mediano {statistics.median(sa):+.0f} g"
        if rs:
            linea += (f" · RESIDUAL mediano {statistics.median(rs):+.0f} g "
                      f"(rango {min(rs):+.0f}–{max(rs):+.0f})")
        if r:
            linea += (f" · RECUPERACIÓN mediana {100*statistics.median(r):.0f} % "
                      f"(rango {100*min(r):.0f}–{100*max(r):.0f})")
        print(linea)
    return 0


def modo_pinza(ctx, args):
    """A3 · pinza real: apriete y balance sobre DOS dedos, con desacoplo medido.

    Los dedos NO son independientes: en la bola de espuma, mover el indice
    arrastra al pulgar un **75 %**, y al reves un 44 %. Tratarlos como dos lazos
    SISO haria que cada uno peleara contra la correccion del otro. Por eso el PI
    trabaja en FUERZA y su salida se pasa por J^-1, la inversa de la matriz de
    acoplamiento medida en ESTE montaje.

        J = [ dF_pulgar/dcmd_pulgar   dF_pulgar/dcmd_indice ]
            [ dF_indice/dcmd_pulgar   dF_indice/dcmd_indice ]

    `J` es de la pareja objeto+pose, no del robot: hay que volver a medirla si
    cambia cualquiera de los dos.
    """
    T, I = 4, 3
    if T not in ctx.dofs or I not in ctx.dofs:
        print("  ABORTA: la pinza necesita pulgar e indice (--pinza 1)"); return 3
    jtt, jti, jit, jii = args.j_tt, args.j_ti, args.j_it, args.j_ii
    det = jtt * jii - jti * jit
    if abs(det) < 1e-6:
        print("  ABORTA: matriz de acoplamiento singular"); return 3
    # dcmd = J^-1 · dF   (J en g por unidad de comando: el camino fijo de A3)
    inv_fijo = ((jii / det, -jti / det), (-jit / det, jtt / det))
    # A4: el estimador trabaja en g por COUNT de POS, porque POS dice lo que el
    # dedo hizo de verdad. El prior sale de la misma J, dividida por los counts
    # que da cada unidad de comando (medido: 1.00 pulgar, 1.75 indice).
    rT, rI = args.pos_por_u_t, args.pos_por_u_i
    est = EstimadorRLS(((jtt / rT, jti / rI), (jit / rT, jii / rI)),
                       lam=args.rls_lam, min_pos=args.rls_min_pos,
                       ridge=args.rls_ridge) if args.rls else None
    # UNA colocacion, VARIAS consignas. Al salir del proceso la mano se abre
    # —politica de seguridad innegociable— asi que cada invocacion cuesta una
    # recolocacion a mano. Encadenando los tramos dentro de la misma tanda, un
    # solo agarre da la caracterizacion entera de los dos ejes.
    if args.secuencia:
        tramos = []
        for par in args.secuencia.split(','):
            a_, b_ = par.split(':')
            tramos.append((float(a_), float(b_)))
    else:
        tramos = [(args.ref, args.ref_balance)]
    print(f"A3 · PINZA · {len(tramos)} tramo(s) de {args.tramo_s:.0f} s: "
          + "  ".join(f"[{a_:.0f}, {b_:+.0f}]" for a_, b_ in tramos))
    ref_T = tramos[0][0] + tramos[0][1] / 2.0
    ref_I = tramos[0][0] - tramos[0][1] / 2.0
    print(f"  J = [{jtt:5.1f} {jti:5.1f} ; {jit:5.1f} {jii:5.1f}]  det={det:.1f}  "
          f"κ≈{args.kappa if args.kappa else 0:.0f}" if args.kappa else
          f"  J = [{jtt:5.1f} {jti:5.1f} ; {jit:5.1f} {jii:5.1f}]  det={det:.1f}")

    t, p, f, c, fp, ff, fr = ctx.lector.muestra()
    while not f:
        t, p, f, c, fp, ff, fr = ctx.lector.muestra()
    if min(f[T], f[I]) < args.contacto_min:
        print(f"  ABORTA: sin contacto en los dos dedos (pulgar {f[T]} g, "
              f"indice {f[I]} g < --contacto-min {args.contacto_min:.0f}). "
              f"La bola debe estar ya sujeta: este modo NO abre la mano.")
        return 3
    print(f"  partida: pulgar {f[T]} g · indice {f[I]} g · "
          f"desequilibrio {f[T] - f[I]:+d} g")
    ctx.hand.write_block(FORCE_SET, [args.fset_respaldo] * NDOF)
    ctx.hand.write_block(SPEED_SET, [args.vel_cierre] * NDOF)
    ctx.lee_comandos()
    ctx.dof_control = {T, I}
    for d in (T, I):
        ctx.disp[d].t_ultimo = None
    pi = {T: PI(args.kp, args.ki, args.lam, args.banda, args.paso_cierra,
                args.paso_abre, args.dq_max, args.refractario),
          I: PI(args.kp, args.ki, args.lam, args.banda, args.paso_cierra,
                args.paso_abre, args.dq_max, args.refractario)}
    t_ini = time.perf_counter()
    hist = []
    st = {'k': 0, 'rT': ref_T, 'rI': ref_I, 't_tramo': 0.0}
    # accion pendiente de evaluar: (t, POS, F) antes del escalon
    pend = {'t': None, 'p': None, 'f': None}
    n_fallback = [0]
    perdido = {'si': False}

    def control(c2, t, p2, f2, ff2):
        # SE NOS ESCAPA: con la bola en el aire, que cualquiera de los dos dedos
        # baje del umbral de contacto significa que la estamos soltando. El
        # DetectorEscape no cubre esto —el dedo esta OBEDECIENDO un comando de
        # abrir, no cediendo— y sin esta guarda la primera tanda siguio 36 s mas
        # con la mano vacia.
        if min(f2[T], f2[I]) < args.contacto_min:
            perdido['si'] = True
            print(f"  ⛔ PERDIENDO EL OBJETO · pulgar {f2[T]} g, indice {f2[I]} g "
                  f"< {args.contacto_min:.0f} g")
            return True
        # cada dedo es dueño de SU disparo; basta con que uno traiga dato nuevo
        tT, dtT, _ = c2.disp[T].toca(t, ff2)
        tI, dtI, _ = c2.disp[I].toca(t, ff2)
        if not (tT or tI):
            return
        # cambio de tramo
        k = min(int((t - t_ini) / args.tramo_s), len(tramos) - 1)
        if k != st['k']:
            st['k'] = k
            ap, ba = tramos[k]
            st['rT'] = ap + ba / 2.0
            st['rI'] = ap - ba / 2.0
            print(f"  → tramo {k+1}: apriete {ap:.0f} g, balance {ba:+.0f} g")
        eT, eI = st['rT'] - f2[T], st['rI'] - f2[I]
        # el PI pide CAMBIO DE FUERZA; J^-1 lo traduce a comando
        uT = pi[T].fuerza_pedida(eT, dtT if tT else 0.0, t)
        uI = pi[I].fuerza_pedida(eI, dtI if tI else 0.0, t)
        # cerrar la accion anterior y dar de comer al estimador
        if est is not None and pend['t'] is not None and t - pend['t'] >= args.rls_espera:
            dp = (p2[T] - pend['p'][0], p2[I] - pend['p'][1])
            dF = (f2[T] - pend['f'][0], f2[I] - pend['f'][1])
            est.actualiza(dp, dF)
            pend['t'] = None
        if est is not None and args.banda_auto > 0:
            # la banda la dimensiona la ganancia estimada, por dedo
            pi[T].banda = est.banda(0, args.paso_cierra, rT, args.banda_auto)
            pi[I].banda = est.banda(1, args.paso_cierra, rI, args.banda_auto)
        if est is not None:
            iK = est.inversa()
            if iK is None:
                n_fallback[0] += 1
                inv = inv_fijo
                dT = inv[0][0] * uT + inv[0][1] * uI
                dI = inv[1][0] * uT + inv[1][1] * uI
            else:
                # K^-1 da Δpos; Δpos/ratio da el comando
                dT = (iK[0][0] * uT + iK[0][1] * uI) / rT
                dI = (iK[1][0] * uT + iK[1][1] * uI) / rI
        else:
            inv = inv_fijo
            dT = inv[0][0] * uT + inv[0][1] * uI
            dI = inv[1][0] * uT + inv[1][1] * uI
        # ESCALAR, no recortar por separado. Recortar un dedo y no el otro cambia
        # la DIRECCION de la correccion en el espacio de fuerzas y deshace el
        # desacoplo. Escalando los dos por el mismo factor se conserva.
        mx = max(abs(dT), abs(dI))
        if mx > args.dq_max:
            k = args.dq_max / mx
            dT *= k; dI *= k
        emitido = False
        for d, dq_f, pid in ((T, dT, pi[T]), (I, dI, pi[I])):
            dq = pid.cuantiza(dq_f, t)
            if dq:
                cmd = c2.cmds.get(d)
                if cmd is not None:
                    c2.manda({d: max(0, min(1000, cmd - dq))})
                    emitido = True
        if emitido and est is not None and pend['t'] is None:
            pend['t'] = t; pend['p'] = (p2[T], p2[I]); pend['f'] = (f2[T], f2[I])
        hist.append((t - t_ini, f2[T], f2[I], eT, eI, st['k']))

    m = bucle(ctx, args.duracion, control, parar_en_evento=True)
    if not hist:
        print("  sin muestras de control"); return 3
    if perdido['si']:
        print("  ABORTADO al perder el contacto"); 
    T_ = [h[0] for h in hist]
    print(f"\n  {len(hist)} pasos en {T_[-1]:.0f} s ({len(hist)/max(T_[-1],1e-6):.1f} Hz)")
    print(f"  {'tramo':>5}  {'apriete':>22}  {'balance':>22}")
    for k, (ap, ba) in enumerate(tramos):
        seg = [h for h in hist if h[5] == k]
        if len(seg) < 20:
            continue
        cola = [h for h in seg if h[0] >= seg[-1][0] - args.cola_s]
        a_ini = statistics.median([(h[1] + h[2]) / 2 for h in seg[:20]])
        b_ini = statistics.median([h[1] - h[2] for h in seg[:20]])
        a_fin = statistics.median([(h[1] + h[2]) / 2 for h in cola])
        b_fin = statistics.median([h[1] - h[2] for h in cola])
        print(f"  {k+1:>5}  {a_ini:6.0f}→{a_fin:4.0f} (obj {ap:3.0f}, err {a_fin-ap:+4.0f})"
              f"  {b_ini:+6.0f}→{b_fin:+4.0f} (obj {ba:+4.0f}, err {b_fin-ba:+4.0f})")
    if est is not None:
        print(f"  RLS · K final (g/count) = {est}")
        if args.banda_auto > 0:
            print(f"        banda final: pulgar {pi[T].banda:.0f} g · "
                  f"indice {pi[I].banda:.0f} g  (arrancaron en "
                  f"{est.banda(0,args.paso_cierra,rT,args.banda_auto):.0f}/"
                  f"{est.banda(1,args.paso_cierra,rI,args.banda_auto):.0f})")
        print(f"        {est.n_uso} actualizaciones · {est.n_congelado} congeladas "
              f"por poco movimiento · {n_fallback[0]} caidas al prior")
    if m:
        print(f"  {m}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Lazo de fuerza · A1 (sin controlador)")
    argumentos_comunes(p)
    p.add_argument('--modo', required=True,
                   choices=['tasas', 'passthrough', 'guarda', 'resbalon', 'tara',
                            'pi', 'firmware', 'comparar', 'pinza'])
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
    p.add_argument('--ref', type=float, default=250.0, help='consigna F* (g)')
    p.add_argument('--kp', type=float, default=0.02)
    p.add_argument('--ki', type=float, default=0.0)
    p.add_argument('--lam', type=float, default=0.98, help='fuga del integrador (<1)')
    p.add_argument('--banda', type=float, default=90.0,
                   help='banda muerta. Al menos el cuanto del dedo: ~20 g pulgar, ~90 g índice')
    p.add_argument('--paso-cierra', type=int, default=5)
    p.add_argument('--paso-abre', type=int, default=3)
    p.add_argument('--dq-max', type=int, default=20)
    p.add_argument('--refractario', type=float, default=0.20,
                   help='espera tras cada accion antes de decidir la siguiente. La planta '
                        'asienta en ~111 ms (E3.3); sin esto el lazo encadena escalones '
                        'antes de ver el efecto del primero')
    p.add_argument('--angulo-aprox', type=int, default=None,
                   help='ANGLE_SET de pre-posición, JUSTO ANTES del objeto. Sale del '
                        'sondeo de contacto; para el índice con block1, 456')
    p.add_argument('--vel-aprox', type=int, default=300)
    p.add_argument('--aprox-s', type=float, default=4.0)
    p.add_argument('--frac-aprox', type=float, default=0.6,
                   help='fracción de F* a la que se deja el contacto antes de activar el lazo')
    p.add_argument('--cola-s', type=float, default=10.0, help='ventana de régimen permanente')
    p.add_argument('--pares', type=int, default=3, help='pares firmware/lazo por invocación')
    p.add_argument('--hold-s', type=float, default=25.0, help='duración de cada trial')
    p.add_argument('--bloque', default='a', help='etiqueta del bloque, para encadenar invocaciones')
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--banda-auto', type=float, default=0.0,
                   help='k: la banda pasa a ser k x escalon_minimo x ganancia '
                        'ESTIMADA, por dedo. 0.5 = medio escalon, el mejor error '
                        'que el dedo puede garantizar. Requiere --rls')
    p.add_argument('--rls', action='store_true',
                   help='estima J en linea (A4) en vez de usar la matriz fija')
    p.add_argument('--rls-lam', type=float, default=0.97, help='olvido del RLS')
    p.add_argument('--rls-min-pos', type=float, default=5.0,
                   help='counts de Σ|Δpos| por debajo de los cuales se CONGELA')
    p.add_argument('--rls-ridge', type=float, default=5e-3)
    p.add_argument('--rls-espera', type=float, default=0.40,
                   help='segundos tras la accion antes de medir su efecto')
    p.add_argument('--pos-por-u-t', type=float, default=1.00,
                   help='counts de POS por unidad de comando, pulgar (MEDIDO)')
    p.add_argument('--pos-por-u-i', type=float, default=1.75, help='idem indice')
    p.add_argument('--secuencia', default=None,
                   help='tramos "apriete:balance,apriete:balance,..." en UNA sola '
                        'tanda; al salir la mano se abre y se pierde el objeto')
    p.add_argument('--tramo-s', type=float, default=20.0, help='segundos por tramo')
    p.add_argument('--ref-balance', type=float, default=0.0,
                   help='F_pulgar - F_indice deseado; 0 = reparto simetrico')
    p.add_argument('--j-tt', type=float, default=5.4, help='dF_pulgar/dcmd_pulgar (MEDIDO, por montaje)')
    p.add_argument('--j-ti', type=float, default=9.5, help='dF_pulgar/dcmd_indice')
    p.add_argument('--j-it', type=float, default=2.4, help='dF_indice/dcmd_pulgar')
    p.add_argument('--j-ii', type=float, default=12.6, help='dF_indice/dcmd_indice')
    p.add_argument('--kappa', type=float, default=None, help='solo informativo')
    p.add_argument('--soporte', type=int, default=None,
                   help='ANGLE_SET de los 4 dedos de soporte; pre-flexionarlos deja margen de perturbar')
    p.add_argument('--perturba-u', type=int, default=0,
                   help='unidades que se FLEXIONA el soporte como escalon de perturbacion')
    p.add_argument('--perturba-t', type=float, default=25.0,
                   help='segundos dentro del sostenimiento a los que entra el escalon')
    p.add_argument('--contacto-min', type=float, default=80.0,
                   help='resbalón: fuerza mínima para considerar que ya hay contacto')
    p.add_argument('--aplicar', action='store_true', help='tara: aplicarla de verdad')
    args = p.parse_args(argv)

    dofs = MODOS[args.pinza]
    if args.modo in ('passthrough', 'guarda', 'resbalon', 'pi', 'firmware', 'comparar', 'pinza') \
            and args.dof not in dofs:
        dofs = [args.dof] + [d for d in dofs if d != args.dof]

    hand = conectar(args)
    if hand is None:
        print("ERROR: sin conexión Modbus.", file=sys.stderr)
        return 1
    ctx = Contexto(hand, args, dofs, args.modo)
    print(f"  DOF implicados: {', '.join(DOF_NAMES[d] for d in dofs)} · "
          + (f"rotación anclada en ANGLE_SET {args.rot}" if ctx.hold else "rotación SIN anclar"))
    if ctx.hold:
        report_hold(hand, ctx.hold, 6, 3.0, args.vel_abrir)
    rc = 1
    try:
        fn = {'tasas': modo_tasas, 'passthrough': modo_passthrough,
              'guarda': modo_guarda, 'resbalon': modo_resbalon, 'tara': modo_tara,
              'pi': modo_pi, 'firmware': modo_firmware,
              'comparar': modo_comparar,
              'pinza': modo_pinza}[args.modo]
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
