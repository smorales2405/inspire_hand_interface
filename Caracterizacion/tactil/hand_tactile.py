"""I/O tactil standalone para la caracterizacion de la Inspire RH56DFTP.

Sin PyQt. Envuelve el helper compartido HandModbus (../hand_modbus.py) con
lecturas por zona sobre las 17 zonas de tactile_zones.py. Un solo cliente, un
solo hilo, lazo intercalado — mismas reglas que los experimentos del punto 1.

Cada taxel = 1 registro de 16 bits, crudo 0-4095, decodificado CON SIGNO por
consistencia con core/hand_connection.py (en uso normal es positivo; un decode
negativo delata un taxel anomalo/pegado).

A diferencia del read_all_tactile_zones de la GUI (que rellena con ceros una
zona fallida), aqui una zona fallida queda como None, para que la Fase 0 pueda
distinguir un error de bus de un cero genuino (taxel muerto/pegado).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))    # Caracterizacion/ -> hand_modbus

from hand_modbus import HandModbus, ANGLE_SET, SPEED_SET   # noqa: E402
from tactile_zones import ZONES, N_ZONES                   # noqa: E402

# Techo nominal del crudo de un taxel (sensor de 12 bits). El nivel REAL de
# saturacion es empirico -> TODO: confirmarlo con datos de Fase 0 (un taxel
# clavado aqui == pegado-alto / stuck-high).
TAXEL_RAW_MAX = 4095

# ── Indice plano de taxeles (fuente de verdad de todo el analisis) ─────────
# TAXELS[i] = (zone_idx, zone_name, row, col, addr) del taxel global i.
# ZONE_SLICES[zi] = (start, stop) del taxel global para la zona zi.
TAXELS = []
ZONE_SLICES = []
_pos = 0
for _zi, (_name, _addr, _n, (_rows, _cols)) in enumerate(ZONES):
    ZONE_SLICES.append((_pos, _pos + _n))
    for _k in range(_n):
        _r, _c = divmod(_k, _cols)
        TAXELS.append((_zi, _name, _r, _c, _addr + _k))
    _pos += _n
N_TAXELS = _pos    # 1062


def taxel_label(i):
    """Etiqueta legible de un taxel global: 'z10[203] Índice — Distal r5c3'."""
    zi, name, r, c, _addr = TAXELS[i]
    return f"z{zi}[{i}] {name} r{r}c{c}"


class TactileHand:
    """Lector tactil por zona sobre un unico cliente HandModbus."""

    def __init__(self, hm: HandModbus):
        self.hm = hm

    # ── Conexion ───────────────────────────────────────────────────────
    @classmethod
    def open_serial(cls, port, baud, device_id=1, timeout=1.0):
        hm = HandModbus.open_serial(port, baud, device_id, timeout)
        return cls(hm) if hm else None

    @classmethod
    def open_tcp(cls, ip, port, device_id=1, timeout=1.0):
        hm = HandModbus.open_tcp(ip, port, device_id, timeout)
        return cls(hm) if hm else None

    # ── Lecturas ───────────────────────────────────────────────────────
    def read_zone(self, zi):
        """Una zona -> list[int] (con signo) o None si falla el bus."""
        _name, addr, n, _grid = ZONES[zi]
        return self.hm.read_block(addr, n)

    def read_frame(self):
        """Las 17 zonas -> lista de 17 sub-listas; una zona fallida queda None."""
        return [self.read_zone(zi) for zi in range(N_ZONES)]

    def read_frame_flat(self):
        """Las 17 zonas como UNA lista plana[N_TAXELS], o None si alguna fallo.

        Devuelve (flat_or_None, n_zonas_fallidas). Lee siempre las 17 zonas
        (para que el timing sea el de un frame completo real).
        """
        zones = self.read_frame()
        failed = sum(1 for z in zones if z is None)
        if failed:
            return None, failed
        flat = [v for z in zones for v in z]
        return flat, 0

    def read_temps(self):
        """Temperatura de los 6 actuadores (C, 0-100) o None. Proxy termico para deriva."""
        return self.hm.read_temps()

    # ── Estado seguro ──────────────────────────────────────────────────
    def open_fingers(self, speed=300):
        """Deja la mano en postura segura: todos los dedos extendidos (abiertos)."""
        self.hm.write_block(SPEED_SET, [speed] * 6)
        return self.hm.write_block(ANGLE_SET, [1000] * 6)

    def close(self):
        self.hm.close()
