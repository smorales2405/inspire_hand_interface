DOF_NAMES = [
    "Meñique",
    "Anular",
    "Medio",
    "Índice",
    "Pulgar (flex.)",
    "Pulgar (rot.)",
]

# (min_angle_deg, max_angle_deg)
# Register 0   → max_angle (finger open / extended)
# Register 1000 → min_angle (finger closed / bent)
DOF_ANGLE_RANGES = [
    (19.0,  176.7),   # 0: Little finger
    (19.0,  176.7),   # 1: Ring finger
    (19.0,  176.7),   # 2: Middle finger
    (19.0,  176.7),   # 3: Index finger
    (-13.0,  53.6),   # 4: Thumb bending
    (90.0,  165.0),   # 5: Thumb rotation
]


def register_to_degrees(register_val, dof_index):
    """Map a register value (0-1000) to physical degrees."""
    min_deg, max_deg = DOF_ANGLE_RANGES[dof_index]
    clamped = max(0, min(1000, register_val))
    return round(max_deg - (clamped / 1000.0) * (max_deg - min_deg), 1)


def degrees_to_register(degrees, dof_index):
    """Map physical degrees to a register value (0-1000)."""
    min_deg, max_deg = DOF_ANGLE_RANGES[dof_index]
    val = (max_deg - degrees) / (max_deg - min_deg) * 1000.0
    return int(max(0, min(1000, round(val))))
