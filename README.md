# Inspire Hand RH56DFTP — Interfaz + Caracterización

Proyecto para la mano robótica **Inspire Hand RH56DFTP** (6 DOF, Modbus RTU/TCP),
organizado en dos partes:

- **`Interfaz/`** — GUI PyQt5 de control y visualización (control por DOF,
  lectura de fuerzas, sensores táctiles). Ver [`Interfaz/README.md`](Interfaz/README.md).
- **`Caracterizacion/`** — caracterización dinámica del hardware (latencia,
  respuesta al escalón, sobreimpulso de fuerza en contacto) para la tesis. Ver
  [`Caracterizacion/README.md`](Caracterizacion/README.md). Cada experimento es
  **auto-contenido**: código + datos + figuras + resultados.

## Setup

```bash
./setup.sh                 # crea .venv/ e instala requirements.txt (deps compartidas)
source .venv/bin/activate
```

## Uso

- **GUI:** `python3 Interfaz/main.py`
- **Caracterización:** scripts por experimento (ver `Caracterizacion/README.md`).

## Estructura

```
inspire_hand_interface/
├── requirements.txt · setup.sh          # deps compartidas (PyQt5, pymodbus, pyserial)
├── Documentation/                       # manuales del hardware (Inspire)
├── Interfaz/                            # GUI PyQt5
│   ├── main.py · core/ · ui/
│   └── README.md
└── Caracterizacion/
    ├── README.md · PROTOCOL_...md
    ├── hand_modbus.py                   # helper Modbus compartido (exp1, exp2)
    ├── figures_to_svg.py                # extrae SVG de las figuras
    ├── exp0/   → código · exp0_results.md · data/
    ├── exp1/   → código · exp1_results.md · data/ · figures/
    └── exp2/   → código · exp2_results.md · data/ · data_slow/ · data_hybrid/ · figures/
```

## Resultados de la caracterización

- **Exp 0** — baseline de muestreo: 98.3 Hz sostenidos.
- **Exp 1** — respuesta al escalón (espacio libre): deadtime ~64 ms, pendiente ∝
  velocidad (R² ≥ 0.98), sobreimpulso de posición ~0.
- **Exp 2** — sobreimpulso de fuerza en contacto: dominado por la velocidad de
  cierre (hasta ~3300 g), mitigado ~68× por el modo híbrido.

Cada `exp*/results.md` tiene la interpretación; las figuras (`exp*/figures/`)
están en HTML autocontenido + SVG para embeber en la tesis.

Hardware: Inspire Hand RH56DFTP. Manuales en `Documentation/`.
