import struct
import threading
from pymodbus.client import ModbusTcpClient, ModbusSerialClient


class HandConnection:
    """Direct Modbus wrapper for the Inspire Hand RH56DFTP.

    Intentionally avoids DDS so the UI can run standalone without
    the unitree_sdk2 middleware.
    """

    def __init__(self):
        self.client = None
        self.device_id = 1
        self.connected = False
        self._lock = threading.Lock()

    # ── Connection ───────────────────────────────────────────────────

    def connect_tcp(self, ip='192.168.11.210', port=6000, device_id=1):
        try:
            self.client = ModbusTcpClient(ip, port=port)
            self.device_id = device_id
            if not self.client.connect():
                return False, "No se pudo establecer conexión TCP"
            self.connected = True
            self.clear_errors()
            return True, "Conectado OK"
        except Exception as e:
            return False, str(e)

    def connect_serial(self, port='/dev/ttyUSB0', baudrate=115200, device_id=1):
        try:
            self.client = ModbusSerialClient(
                port=port, baudrate=baudrate, timeout=1
            )
            self.device_id = device_id
            if not self.client.connect():
                return False, "No se pudo conectar al puerto serial"
            self.connected = True
            self.clear_errors()
            return True, "Conectado OK"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.connected = False

    # ── Low-level register helpers ───────────────────────────────────

    def _read_shorts(self, address, count):
        """Read `count` registers as signed 16-bit integers."""
        response = self.client.read_holding_registers(address, count, self.device_id)
        if response.isError():
            return None
        packed = struct.pack('>' + 'H' * count, *response.registers)
        return list(struct.unpack('>' + 'h' * count, packed))

    def _read_bytes_from_regs(self, address, reg_count):
        """Read `reg_count` registers and unpack as bytes (high then low)."""
        response = self.client.read_holding_registers(address, reg_count, self.device_id)
        if response.isError():
            return None
        result = []
        for reg in response.registers:
            result.append((reg >> 8) & 0xFF)
            result.append(reg & 0xFF)
        return result

    # ── High-level reads ─────────────────────────────────────────────

    def read_state(self):
        """Return dict with angle_act, force_act, and status for all 6 DOFs."""
        if not self.connected:
            return None
        try:
            with self._lock:
                angle_act  = self._read_shorts(1546, 6)           # ANGLE_ACT(0-5)
                force_act  = self._read_shorts(1582, 6)           # FORCE_ACT(0-5)
                status_raw = self._read_bytes_from_regs(1612, 3)  # STATUS(0-5) packed
            return {
                'angle_act': angle_act  or [0] * 6,
                'force_act': force_act  or [0] * 6,
                'status':    (status_raw[:6] if status_raw else [0] * 6),
            }
        except Exception as e:
            print(f"[HandConnection] read_state error: {e}")
            return None

    # ── High-level writes ────────────────────────────────────────────

    def set_angles(self, register_values):
        """Write ANGLE_SET for all 6 DOFs. Values in range 0-1000 (or -1 = no-op)."""
        if not self.connected:
            return False
        try:
            with self._lock:
                self.client.write_registers(1486, list(register_values), self.device_id)
            return True
        except Exception as e:
            print(f"[HandConnection] set_angles error: {e}")
            return False

    def set_speed(self, speed):
        """Write SPEED_SET for all 6 DOFs. speed: single int or list of 6 ints (0-1000)."""
        if not self.connected:
            return False
        values = [speed] * 6 if isinstance(speed, int) else list(speed)
        try:
            with self._lock:
                self.client.write_registers(1522, values, self.device_id)
            return True
        except Exception as e:
            print(f"[HandConnection] set_speed error: {e}")
            return False

    def read_forces(self):
        """Read FORCE_ACT for all 6 DOFs. Returns list[int] in grams, or None."""
        if not self.connected:
            return None
        try:
            with self._lock:
                result = self._read_shorts(1582, 6)
            return result or [0] * 6
        except Exception as e:
            print(f"[HandConnection] read_forces error: {e}")
            return None

    def clear_errors(self):
        if not self.connected or self.client is None:
            return
        try:
            with self._lock:
                self.client.write_register(1004, 1, self.device_id)
        except Exception:
            pass
