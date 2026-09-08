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
    ├── README.md · PROTOCOL_...md · RUNBOOK_pulgar.md
    ├── hand_modbus.py                   # helper Modbus compartido (exp1, exp2)
    ├── pose_check.py                    # Fase 0 de un DOF: ANGLE_SET → postura real
    ├── figures_to_svg.py                # extrae SVG de las figuras
    ├── exp0/   → código · exp0_results.md · data/
    ├── exp1/   → código · exp1_results.md · data/ · figures/
    └── exp2/   → código · exp2_results.md · data/ · data_slow/ · data_hybrid/ · figures/
```

Los experimentos toman `--dof` y `--hold` (anclar otro DOF): la campaña del
**índice** vive en `exp*/data/` y la de cualquier otro DOF en `exp*/data_dof<N>/`,
sin mezclarse. La réplica sobre la **flexión del pulgar** (DOF 4, con la rotación
anclada) está en [`Caracterizacion/RUNBOOK_pulgar.md`](Caracterizacion/RUNBOOK_pulgar.md).

## Resultados de la caracterización

- **Exp 0** — baseline de muestreo: 98.3 Hz sostenidos.
- **Exp 1** — respuesta al escalón (espacio libre): deadtime ~64 ms, pendiente ∝
  velocidad (R² ≥ 0.98), sobreimpulso de posición ~0.
- **Exp 2** — sobreimpulso de fuerza en contacto: dominado por la velocidad de
  cierre (hasta ~3300 g), mitigado ~35× por el modo híbrido.
- **Réplica en el pulgar (DOF 4)** — el protocolo completo repetido sobre la
  flexión del pulgar con la rotación anclada. Ver `exp1/exp1_results_dof4.md`,
  `exp2/exp2_results_dof4.md` y `figures/comparativa_indice_pulgar.html`.
- **Verificación por muestreo (DOF 0, 1, 2)** — meñique, anular y medio, con el
  mínimo de corridas que puede falsar los dos hallazgos. Los tres pasan. Ver
  `verificacion_muestreo_results.md` y `RUNBOOK_verificacion_muestreo.md`.

**Conclusión, los cinco DOF:** `SPEED_SET` calibra el actuador y no el ángulo
(k = 2.99–3.05, 2 % de dispersión). **Bajar el umbral de fuerza no protege en
ningún dedo**: o el umbral queda por debajo del residual de flexión del propio
dedo y el firmware frena en el aire sin llegar al objeto (índice, meñique), o el
dedo llega y el umbral no contiene el impacto (pulgar). La **conmutación de
velocidad** es la única mitigación que funciona, y funciona en los cinco.

> El hallazgo publicado antes —que `Fset=100` era una "zona segura" en el
> índice— **era un artefacto**: esos trials nunca tocaban el bloque. Corregido
> el 2026-09-07; ver el aviso al principio de `exp2/exp2_results.md`.

Cada `exp*/results.md` tiene la interpretación; las figuras (`exp*/figures/`)
están en HTML autocontenido + SVG para embeber en la tesis.

**Documento-resumen** (para asesor/jurado): `Caracterizacion/RESUMEN_caracterizacion.html`
— abstract, método, resultados con figuras y tablas de métricas. Reproducible con
`python Caracterizacion/make_summary.py`.

Hardware: Inspire Hand RH56DFTP. Manuales en `Documentation/`.
