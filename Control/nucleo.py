#!/usr/bin/env python3
"""Núcleo del regulador de fuerza: lectura, seguridad, detectores y bitácora.

Todo lo que el lazo necesita por debajo del control, en un solo sitio, porque
A2–A5 y la Parte B lo comparten. **Aquí no hay controlador**: el control vive en
`lazo.py` y usa esto como plataforma.

Decisiones que vienen medidas del Exp 3, no elegidas:

- **Frescura POR DOF.** La mano publica estado cada ~30.7 ms se lea a la tasa que
  se lea. `Caracterizacion/exp3/exp3_min_step.py` ya marcaba frescura, pero **por
  bloque** («algún DOF cambió»), que no sirve para un lazo multi-dedo. Integrar
  sobre duplicados infla `Ki` en la proporción entre tasa de sondeo y de refresco
  —del orden de 18×— así que el control solo puede avanzar con muestra fresca del
  dedo que regula.
- **Dos detectores de resbalón, no uno.** Los dos se ven como caída de fuerza y la
  reacción correcta es **opuesta**:

  |  | `POS` | Fuerza | Reacción |
  |---|---|---|---|
  | Resbalón del ACTUADOR | retrocede contra su comando | cae | **aflojar**: ya se pasó del borde |
  | Objeto que SE ESCAPA | sigue al comando | cae en **todos** los dedos a la vez | **apretar** o abortar |

  `POS` es lo único que los separa. Medido: el resbalón del actuador mueve `POS`
  ~50 counts en menos de medio segundo, contra 0–2 counts del sostenimiento
  normal (E3.4), así que un umbral de 10 counts es inequívoco.
- **Sin tope de fuerza constante.** El borde depende de la pose: 455–745 g en lo
  medido. La guarda de fuerza sigue existiendo como red de seguridad, pero quien
  encuentra el borde es el detector de resbalón.
- **Tara solo con la mano abierta, descargada y ≥ 10 s después de soltar.** Tras
  sostener carga el cero queda corrido 21–46 g y tarda ~8 s en volver (E3.5), y el
  signo es **por DOF**: índice −46 g, pulgar +21 g.
- **`FORCE_SET` siempre por encima del rango de trabajo.** Si `FORCE_ACT` lo
  alcanza, el dedo deja de aceptar `ANGLE_SET` **en los dos sentidos**: el paro del
  firmware secuestra la posición.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from collections import deque

_HERE = os.path.dirname(os.path.abspath(__file__))
_CARACT = os.path.join(os.path.dirname(_HERE), 'Caracterizacion')
sys.path.insert(0, _CARACT)

from hand_modbus import (                                    # noqa: E402
    HandModbus, NDOF, ANGLE_SET, ANGLE_ACT, FORCE_SET, SPEED_SET,
    POS_ACT, FORCE_ACT, CURRENT, DOF_NAMES, open_vector, report_hold,
)

FORCE_CLB = 1009        # tara de fuerza; escribir 1 con la palma abierta y descargada
FSET_ABRIR = 3000       # FORCE_SET antes de abrir: nunca debe frenar la apertura

# POS crece al FLEXIONAR y ANGLE_SET decrece al flexionar. Un dedo que "retrocede"
# es POS bajando sin que nadie se lo haya pedido.
CIERRA_POS = +1


def vector(cmds, hold):
    """Bloque ANGLE_SET con varios DOF a la vez; el resto en -1 (no tocar)."""
    v = [-1] * NDOF
    for d, a in (hold or {}).items():
        v[d] = int(a)
    for d, a in cmds.items():
        v[d] = int(a)
    return v


def conectar(args):
    return HandModbus.open_tcp(args.ip, args.port, args.device_id, args.timeout)


# ── lectura con frescura por DOF ──────────────────────────────────────────
class Lector:
    """Sondea POS/FORCE (y CURRENT cada `aux_every`) y devuelve DOS niveles de
    novedad, porque hacen falta los dos.

    - **`frame`**: el bloque entero cambió → llegó estado nuevo de la mano. Es lo
      que debe disparar el control. Fiable, porque con seis DOF algo casi siempre
      cambia.
    - **`fresca_f[d]` / `fresca_p[d]`**: ese DOF concreto trae valor nuevo. Dice si
      el dedo aporta información, pero **subestima**: si el entero se repite entre
      dos frames cuenta como no fresco, y con ruido de ±1–2 g eso pasa en torno a
      una de cada cuatro veces. Medido contra el mock: 26–27 Hz por DOF frente a
      32.6 Hz de frames reales.

    Para `POS` la subestimación es total y esperada: con un solo dedo en
    movimiento, el `POS` de los demás no cambia nunca (E3.6a).
    """

    def __init__(self, hand, aux_every=8):
        self.h = hand
        self.aux_every = aux_every
        self.prev_p = [None] * NDOF
        self.prev_f = [None] * NDOF
        self._prev_bloque_p = None
        self._prev_bloque_f = None
        self.cur = [None] * NDOF
        self.i = 0
        self.n_lecturas = 0
        self.n_frames = 0
        self.n_frescas_f = [0] * NDOF
        self.n_frescas_p = [0] * NDOF
        self.t_ini = None
        self._dt = deque(maxlen=400)
        self._t_ant = None

    def muestra(self):
        """Devuelve (t, pos, fuerza, corriente, fresca_p, fresca_f)."""
        p = self.h.read_block(POS_ACT)
        f = self.h.read_block(FORCE_ACT)
        t = time.perf_counter()
        if self.t_ini is None:
            self.t_ini = t
        if self.i % self.aux_every == 0:
            c = self.h.read_block(CURRENT)
            if c:
                self.cur = c
        self.i += 1
        self.n_lecturas += 1
        if self._t_ant is not None:
            self._dt.append(t - self._t_ant)
        self._t_ant = t

        # "Frame" de bloque: SOBRECUENTA y es solo diagnostico. Se penso como la
        # deteccion fiable de "llego estado nuevo", suponiendo que la mano publica
        # los 6 DOF a la vez. **No lo hace**: E3.6a midio 1.9 ms de desfase entre
        # indice y pulgar, asi que el bloque cambia cada vez que se actualiza
        # CUALQUIERA de los seis y la tasa sale inflada (51 Hz medidos contra 32.6
        # de publicacion). El disparo del control va por DOF, con `Disparador`.
        frame = (p is not None and p != self._prev_bloque_p) or \
                (f is not None and f != self._prev_bloque_f)
        if p is not None:
            self._prev_bloque_p = list(p)
        if f is not None:
            self._prev_bloque_f = list(f)
        self.n_frames += int(frame)

        fp = [False] * NDOF
        ff = [False] * NDOF
        if p:
            for d in range(NDOF):
                if self.prev_p[d] is None or p[d] != self.prev_p[d]:
                    fp[d] = self.prev_p[d] is not None
                    self.prev_p[d] = p[d]
            for d in range(NDOF):
                self.n_frescas_p[d] += int(fp[d])
        if f:
            for d in range(NDOF):
                if self.prev_f[d] is None or f[d] != self.prev_f[d]:
                    ff[d] = self.prev_f[d] is not None
                    self.prev_f[d] = f[d]
            for d in range(NDOF):
                self.n_frescas_f[d] += int(ff[d])
        return t, p, f, list(self.cur), fp, ff, frame

    def tasas(self, dofs):
        """(Hz sondeo, Hz de frame, {dof: Hz fuerza fresca}, {dof: Hz POS fresca}, jitter ms)."""
        if self.t_ini is None or self.n_lecturas < 2:
            return 0.0, 0.0, {}, {}, 0.0
        T = time.perf_counter() - self.t_ini
        if T <= 0:
            return 0.0, 0.0, {}, {}, 0.0
        dts = sorted(self._dt)
        jit = 0.0
        if len(dts) > 10:
            jit = (dts[int(len(dts) * 0.9)] - dts[int(len(dts) * 0.1)]) * 1000
        return (self.n_lecturas / T, self.n_frames / T,
                {d: self.n_frescas_f[d] / T for d in dofs},
                {d: self.n_frescas_p[d] / T for d in dofs},
                jit)


class Disparador:
    """Decide cuándo el control puede avanzar para un DOF concreto.

    Medido en banco, y con la mano publicando cada 30.7 ms por DOF:

    | | cambios de fuerza | intervalo mediano |
    |---|---|---|
    | sin carga | 6–11 Hz | **60.0 ms** = 2 × 30.7 |
    | con carga (330–1077 g) | **28.3 Hz** | **30.4 ms** |

    Los intervalos son múltiplos exactos del periodo: el dedo publica siempre, pero
    si el entero se repite la lectura parece «no fresca». Bajo carga —el régimen
    del regulador— apenas ocurre; sin carga pasa uno de cada dos frames.

    Por eso el disparo es **cambio de valor O tiempo agotado**: el cambio da la
    cadencia natural de 30 ms, y el plazo evita que el lazo se quede parado cuando
    el valor se repite. Un valor repetido no es información vieja: es el valor
    actual. Lo que no puede hacerse es integrar VARIAS veces dentro del mismo
    frame, que es lo que inflaría `Ki`.
    """

    def __init__(self, dof, plazo_s=0.040):
        self.dof, self.plazo = dof, plazo_s
        self.t_ultimo = None
        self.n_cambio = 0
        self.n_plazo = 0

    def toca(self, t, fresca_f):
        if self.t_ultimo is None:
            self.t_ultimo = t
            return True, 0.0, 'inicio'
        dt = t - self.t_ultimo
        if fresca_f[self.dof]:
            self.t_ultimo = t
            self.n_cambio += 1
            return True, dt, 'cambio'
        if dt >= self.plazo:
            self.t_ultimo = t
            self.n_plazo += 1
            return True, dt, 'plazo'
        return False, dt, ''

    def resumen(self, T):
        n = self.n_cambio + self.n_plazo
        return (f"{n/T:.1f} Hz de disparo · {self.n_cambio} por cambio, "
                f"{self.n_plazo} por plazo ({100*self.n_plazo/max(n,1):.0f} %)")


# ── seguridad ─────────────────────────────────────────────────────────────
class Guarda:
    """Red de seguridad: fuerza, corriente sostenida, temperatura y tiempo.

    NO incluye un tope de fuerza «de diseño»: el borde de lo sostenible depende de
    la pose (455–745 g medidos) y quien lo encuentra es `DetectorResbalon`. Esta
    guarda es el último recurso, y su techo debe quedar **por debajo** de
    `FORCE_SET` para que el software actúe antes que el paro del firmware.
    """

    def __init__(self, args, dofs):
        self.a, self.dofs = args, dofs
        self.motivo = None
        self.cur_alta = 0
        self.t0 = time.perf_counter()

    def revisa(self, f, c, temps=None):
        a = self.a
        if f:
            for d in self.dofs:
                if abs(f[d]) > a.techo_fuerza:
                    self.motivo = f"{DOF_NAMES[d]}: {f[d]} g > techo {a.techo_fuerza}"
                    return self.motivo
        if c and any(c[d] is not None and c[d] > a.corriente_max for d in self.dofs):
            self.cur_alta += 1
            if self.cur_alta > a.corriente_ciclos:
                self.motivo = f"corriente > {a.corriente_max} mA sostenida"
                return self.motivo
        else:
            self.cur_alta = 0
        if temps and max(temps[d] for d in self.dofs) > a.temp_max:
            self.motivo = f"temperatura {max(temps[d] for d in self.dofs)} °C"
            return self.motivo
        if time.perf_counter() - self.t0 > a.timeout_s:
            self.motivo = f"timeout de {a.timeout_s:.0f} s"
            return self.motivo
        return None


def abrir_mano(hand, args, hold=None):
    """Apertura segura: primero se quita el paro del firmware, luego se abre.

    El orden importa: un dedo que haya llegado a `FORCE_SET` no acepta `ANGLE_SET`
    en ningún sentido hasta que el umbral suba.
    """
    try:
        hand.write_block(FORCE_SET, [FSET_ABRIR] * NDOF)
        hand.write_block(SPEED_SET, [args.vel_abrir] * NDOF)
        hand.write_block(ANGLE_SET, open_vector(args.angulo_abierto, hold or {}))
        time.sleep(0.4)
        return True
    except Exception:
        return False


# ── detectores de resbalón ────────────────────────────────────────────────
class DetectorResbalon:
    """Resbalón del ACTUADOR: `POS` retrocede contra su propio comando.

    Medido: al pasarse del borde, el dedo retrocede ~49 counts en menos de medio
    segundo y la fuerza cae 553 g; en sostenimiento normal `POS` se mueve 0–2
    counts en 60 s (E3.4). Entre 2 y 50 hay un abismo, así que 10 counts en 0.5 s
    es inequívoco.

    Un objeto que se mueve **no** puede empujar al dedo contra su comando: si `POS`
    retrocede, el que cede es el mecanismo. Ésa es la firma que lo distingue del
    objeto escapándose, y la reacción correcta es **aflojar**, no apretar.
    """

    def __init__(self, dofs, counts=10, ventana_s=0.5):
        self.dofs, self.counts, self.ventana = dofs, counts, ventana_s
        self.hist = {d: deque() for d in dofs}          # (t, pos)
        self.cmd_hist = {d: deque() for d in dofs}      # (t, comando)
        self.eventos = []

    def actualiza(self, t, p, cmds):
        if not p:
            return None
        for d in self.dofs:
            self.hist[d].append((t, p[d]))
            self.cmd_hist[d].append((t, cmds.get(d)))
            while self.hist[d] and t - self.hist[d][0][0] > self.ventana:
                self.hist[d].popleft()
            while self.cmd_hist[d] and t - self.cmd_hist[d][0][0] > self.ventana:
                self.cmd_hist[d].popleft()
            if len(self.hist[d]) < 5:
                continue
            retroceso = self.hist[d][0][1] - self.hist[d][-1][1]     # POS bajando
            if retroceso * CIERRA_POS < self.counts:
                continue
            # ¿se le pidió abrir? entonces no es resbalón, es obediencia
            cmds_v = [c for _, c in self.cmd_hist[d] if c is not None]
            if len(cmds_v) >= 2 and cmds_v[-1] > cmds_v[0]:          # ANGLE_SET subió = abrir
                continue
            ev = dict(t=t, dof=d, counts=retroceso, ventana=self.ventana)
            self.eventos.append(ev)
            self.hist[d].clear()
            return ev
        return None


class DetectorEscape:
    """El OBJETO se escapa: la fuerza cae en TODOS los dedos a la vez y `POS` no
    retrocede.

    Es el complementario del anterior y se confunden con él si solo se mira la
    fuerza. Aquí el mecanismo no cede —`POS` sigue al comando— pero el objeto deja
    de empujar contra las yemas. La reacción es **apretar** o abortar, es decir la
    contraria.
    """

    def __init__(self, dofs, caida_g=60.0, frac=0.35, ventana_s=0.5, pos_counts=6):
        self.dofs, self.ventana = dofs, ventana_s
        self.caida, self.frac, self.pos_counts = caida_g, frac, pos_counts
        self.hist = {d: deque() for d in dofs}          # (t, fuerza, pos)
        self.eventos = []

    def actualiza(self, t, p, f):
        if not (p and f):
            return None
        for d in self.dofs:
            self.hist[d].append((t, f[d], p[d]))
            while self.hist[d] and t - self.hist[d][0][0] > self.ventana:
                self.hist[d].popleft()
        if any(len(self.hist[d]) < 5 for d in self.dofs):
            return None
        caidas, pos_ok = [], True
        for d in self.dofs:
            f0, f1 = self.hist[d][0][1], self.hist[d][-1][1]
            p0, p1 = self.hist[d][0][2], self.hist[d][-1][2]
            caidas.append(f0 - f1)
            if (p0 - p1) * CIERRA_POS >= self.pos_counts:
                pos_ok = False                       # eso es resbalón del actuador
        if not pos_ok:
            return None
        base = [self.hist[d][0][1] for d in self.dofs]
        if all(c > self.caida for c in caidas) and \
           all(c > self.frac * max(b, 1) for c, b in zip(caidas, base)):
            ev = dict(t=t, caidas={d: c for d, c in zip(self.dofs, caidas)})
            self.eventos.append(ev)
            for d in self.dofs:
                self.hist[d].clear()
            return ev
        return None


# ── política de tara ──────────────────────────────────────────────────────
class Tara:
    """Tara de fuerza con las condiciones que E3.5 impone.

    Tras sostener carga el cero queda corrido 21–46 g y vuelve a +6 g/s, o sea ~8 s.
    Tarar antes mete ese error directamente en la consigna del lazo. Por eso la
    tara exige mano abierta, descargada y **≥ 10 s desde la última suelta**.
    """

    def __init__(self, espera_s=10.0, umbral_g=40.0):
        self.espera, self.umbral = espera_s, umbral_g
        self.t_suelta = None
        self.n = 0

    def marca_suelta(self):
        self.t_suelta = time.perf_counter()

    def puede(self, f, dofs):
        if self.t_suelta is not None:
            falta = self.espera - (time.perf_counter() - self.t_suelta)
            if falta > 0:
                return False, f"faltan {falta:.0f} s desde la última suelta (E3.5)"
        if f and any(abs(f[d]) > self.umbral for d in dofs):
            cargados = [f"{DOF_NAMES[d]} {f[d]} g" for d in dofs if abs(f[d]) > self.umbral]
            return False, f"hay carga en las yemas: {', '.join(cargados)}"
        return True, "ok"

    def aplica(self, hand, f, dofs, forzar=False):
        ok, por_que = self.puede(f, dofs)
        if not ok and not forzar:
            return False, por_que
        hand.write_block(FORCE_CLB, [1])
        time.sleep(1.5)
        self.n += 1
        return True, "tarada"


# ── bitácora ──────────────────────────────────────────────────────────────
class Bitacora:
    """CSV por tanda, escrito al vuelo (el vigilante de memoria mata procesos que
    acumulan). Las columnas de control quedan vacías mientras no haya controlador."""

    COLS = ['t', 'frame', 'fresca_f', 'fresca_p', 'F_T', 'F_I', 'F_M', 'F_grip',
            'err_s', 'err_b', 'u_s', 'u_t', 'dq_T', 'dq_I', 'dq_M',
            'POS_T', 'POS_I', 'POS_M', 'cmd_T', 'cmd_I', 'cmd_M',
            'I_mA', 'temp', 'evento']

    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.fh = open(path, 'w', newline='')
        self.w = csv.writer(self.fh)
        self.w.writerow(self.COLS)
        self.path = path
        self.n = 0

    def fila(self, **kw):
        self.w.writerow([kw.get(c, '') for c in self.COLS])
        self.n += 1
        if self.n % 200 == 0:
            self.fh.flush()

    def cierra(self):
        self.fh.flush()
        self.fh.close()


def argumentos_comunes(p):
    """Los que comparten todas las fases del regulador."""
    p.add_argument('--ip', default='192.168.124.210')
    p.add_argument('--port', type=int, default=6000)
    p.add_argument('--device-id', type=int, default=1)
    p.add_argument('--timeout', type=float, default=1.0)
    p.add_argument('--rot', type=int, default=0,
                   help='ANGLE_SET de la rotación del pulgar. OBLIGATORIO anclarla: sin '
                        'ello el pulgar describe otra trayectoria')
    p.add_argument('--aux-every', type=int, default=8, help='cada cuántas lecturas se lee CURRENT')
    p.add_argument('--vel-cierre', type=int, default=25)
    p.add_argument('--vel-abrir', type=int, default=300)
    p.add_argument('--angulo-abierto', type=int, default=1000)
    # seguridad
    p.add_argument('--techo-fuerza', type=float, default=600.0,
                   help='red de seguridad, NO el tope de diseño. Debe quedar por debajo '
                        'de --fset-respaldo')
    p.add_argument('--fset-respaldo', type=int, default=700,
                   help='paro del firmware; por encima del techo software')
    p.add_argument('--corriente-max', type=int, default=700)
    p.add_argument('--corriente-ciclos', type=int, default=25)
    p.add_argument('--temp-max', type=int, default=50)
    p.add_argument('--timeout-s', type=float, default=600.0)
    # detectores
    p.add_argument('--resbalon-counts', type=int, default=10,
                   help='retroceso de POS que delata resbalón del actuador (normal: 0–2)')
    p.add_argument('--resbalon-ventana', type=float, default=0.5)
    p.add_argument('--escape-g', type=float, default=60.0)
    p.add_argument('--escape-frac', type=float, default=0.35)
    p.add_argument('--tara-espera', type=float, default=10.0)
    p.add_argument('--disparo-plazo', type=float, default=0.040,
                   help='si la fuerza del DOF no cambia en este plazo, el control avanza '
                        'igual: un valor repetido es el valor actual, no informacion vieja')
    p.add_argument('--outdir', default=os.path.join(_HERE, 'data'))
    return p
