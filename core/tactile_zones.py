# Tactile sensor zone definitions — derived from inspire_hand_defaut.py data_sheet.
# Each entry: (name_es, modbus_addr, n_registers, grid_shape)
#   n_registers = length_bytes // 2  (one signed-16 value per register)
#   grid_shape  = (rows, cols) to reshape the flat read into a 2-D matrix

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
