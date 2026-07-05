"""Minimal standalone Modbus I/O for the Inspire RH56DFTP characterization.

No PyQt. Single client; block reads/writes with signed int16 decoding, mirroring
the proven pattern in core/hand_connection.py but kept OUTSIDE the GUI per the
characterization rules. Reused by exp1/exp2 (exp0 stays self-contained).

Register block start addresses come from the manual (RH56DFTP). Each block holds
6 shorts (one per DOF); DOF k is element [k] of the read/written list. Reading a
whole 6-short block at the start address and indexing the DOF is the pattern
that is verified to work on this hand.
"""
from __future__ import annotations

import struct

from pymodbus.client import ModbusTcpClient, ModbusSerialClient

# ── Register map (block start addr; 6 shorts each) ────────────────────────
ANGLE_SET = 1486   # W    -1 (no-op / hold), 0-1000
FORCE_SET = 1498   # W    0-3000  (g, force threshold)
SPEED_SET = 1522   # W    0-1000
POS_ACT   = 1534   # R    0-2000  (actuator position, fine resolution)
ANGLE_ACT = 1546   # R    0-1000
FORCE_ACT = 1582   # R    -4000..4000  (g, signed)
CURRENT   = 1594   # R    0-2000  (mA)
TEMP      = 1618   # R    temperatura por actuador: 3 regs = 6 bytes, 1 byte/DOF, 0-100 C
#                        (manual sec. 2.6.19; 1618 meñique..1621 indice, 1622/1623 pulgar)

NDOF = 6
G_TO_N = 9.80665 / 1000.0   # grams-force -> Newton


class HandModbus:
    """Single-client Modbus wrapper: signed block reads and writes."""

    def __init__(self, client, device_id=1):
        self.client = client
        self.device_id = device_id

    # ── Connection ────────────────────────────────────────────────────
    @classmethod
    def open_tcp(cls, ip, port, device_id=1, timeout=1.0):
        c = ModbusTcpClient(ip, port=port, timeout=timeout)
        return cls(c, device_id) if c.connect() else None

    @classmethod
    def open_serial(cls, port, baud, device_id=1, timeout=1.0):
        c = ModbusSerialClient(port=port, baudrate=baud, timeout=timeout)
        return cls(c, device_id) if c.connect() else None

    # ── Block I/O ─────────────────────────────────────────────────────
    def read_block(self, addr, count=NDOF):
        """Read `count` regs as signed int16. Returns list[int] or None."""
        try:
            r = self.client.read_holding_registers(addr, count, self.device_id)
        except Exception:
            return None
        if r.isError():
            return None
        packed = struct.pack('>' + 'H' * count, *r.registers)
        return list(struct.unpack('>' + 'h' * count, packed))

    def read_bytes(self, addr, reg_count):
        """Lee reg_count regs y los desempaca como bytes (alto, luego bajo).

        Para bloques byte-empaquetados (STATUS, TEMP): 1 byte por DOF. None si error.
        """
        try:
            r = self.client.read_holding_registers(addr, reg_count, self.device_id)
        except Exception:
            return None
        if r.isError():
            return None
        out = []
        for reg in r.registers:
            out.append((reg >> 8) & 0xFF)
            out.append(reg & 0xFF)
        return out

    def read_temps(self):
        """Temperatura de los 6 actuadores (C, 0-100) o None. Reg TEMP (3 regs = 6 bytes)."""
        b = self.read_bytes(TEMP, 3)
        return b[:NDOF] if b else None

    def write_block(self, addr, values):
        """Write signed ints as uint16 (so -1 -> 0xFFFF). Returns bool ok."""
        regs = [int(v) & 0xFFFF for v in values]
        try:
            r = self.client.write_registers(addr, regs, self.device_id)
        except Exception:
            return False
        return not r.isError()

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass
