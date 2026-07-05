# Tactile sensor zone definitions — Inspire RH56DFTP (config. T1, 17 zonas).
#
# COPIA de Interfaz/core/tactile_zones.py, mantenida FUERA de la GUI para que
# la caracterizacion del tactil (Caracterizacion/tactil/) sea standalone y no
# importe PyQt. Fuente de verdad de direcciones/grids. Si cambia el mapa en la
# GUI, actualiza esta copia.
#
# Cada entrada: (name_es, modbus_addr, n_registers, grid_shape)
#   n_registers = 1 registro (16 bits) por taxel, crudo 0-4095, decodificado con signo
#   grid_shape  = (rows, cols) para reordenar la lectura plana en matriz 2-D

ZONES = [
    # ── Meñique (little finger) ──────────────────────────────────────
    ("Meñique — Punta",   3000,  9, ( 3, 3)),   # z0
    ("Meñique — Distal",  3018, 96, (12, 8)),   # z1
    ("Meñique — Palmar",  3210, 80, (10, 8)),   # z2
    # ── Anular (ring finger) ─────────────────────────────────────────
    ("Anular — Punta",    3370,  9, ( 3, 3)),   # z3
    ("Anular — Distal",   3388, 96, (12, 8)),   # z4
    ("Anular — Palmar",   3580, 80, (10, 8)),   # z5
    # ── Medio (middle finger) ────────────────────────────────────────
    ("Medio — Punta",     3740,  9, ( 3, 3)),   # z6
    ("Medio — Distal",    3758, 96, (12, 8)),   # z7
    ("Medio — Palmar",    3950, 80, (10, 8)),   # z8
    # ── Índice (index finger) ────────────────────────────────────────
    ("Índice — Punta",    4110,  9, ( 3, 3)),   # z9
    ("Índice — Distal",   4128, 96, (12, 8)),   # z10
    ("Índice — Palmar",   4320, 80, (10, 8)),   # z11
    # ── Pulgar (thumb) ───────────────────────────────────────────────
    ("Pulgar — Punta",    4480,  9, ( 3, 3)),   # z12
    ("Pulgar — Distal",   4498, 96, (12, 8)),   # z13
    ("Pulgar — Medio",    4690,  9, ( 3, 3)),   # z14
    ("Pulgar — Palmar",   4708, 96, (12, 8)),   # z15
    # ── Palma ────────────────────────────────────────────────────────
    ("Palma",             4900, 112, (14, 8)),  # z16
]

N_ZONES = len(ZONES)   # 17
