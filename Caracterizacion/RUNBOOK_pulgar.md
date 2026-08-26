# Runbook — Caracterización dinámica de la FLEXIÓN DEL PULGAR (DOF 4)

Réplica del [`PROTOCOL_Dynamic_Characterization_RH56DFTP.md`](PROTOCOL_Dynamic_Characterization_RH56DFTP.md)
—ya ejecutado sobre el índice (DOF 3)— aplicado ahora a la **flexión del pulgar
(DOF 4)**, con la **rotación del pulgar (DOF 5) anclada en su ángulo máximo
(≈165°)** para que la única variable cinemática sea la flexión.

El propio protocolo lo anticipa (§1: *«Luego repite para medio (DOF 2) y flexión
del pulgar (DOF 4) si quieres cobertura»*). Lo que sigue es la instanciación
concreta, por fases, con el hardware en el lazo.

---

## Qué cambia respecto del índice

| | Índice (hecho) | Pulgar (este runbook) |
|---|---|---|
| DOF bajo prueba | 3 | **4** (flexión) |
| DOF anclado | — | **5** (rotación) a ≈165°, `--hold 5:<reg>` |
| Rango angular (manual) | 20°–176° | **−13°–70°** (flexión) |
| Vel. angular (datasheet) | >200 °/s (4 dedos) | **>130 °/s** (pulgar) |
| Carpetas de datos | `exp1/data`, `exp2/data…` | `exp1/data_dof4`, `exp2/data_dof4…` (automático) |

Dos consecuencias que **hay que esperar** y no confundir con errores:

1. **El pulgar es más lento por diseño.** El datasheet le da >130 °/s frente a
   >200 °/s de los cuatro dedos. La pendiente del Exp 1 seguirá siendo ∝
   `SPEED_SET`, pero con **otra constante** que la del índice (≈3.04 counts/s
   por unidad de `SPEED_SET`). Eso es un resultado, no una anomalía.
2. **Recorrido más corto.** La flexión del pulgar barre ~83° contra los ~156° de
   un dedo, así que el `Δpos` total y los tiempos de subida serán menores.

### El ancla (`--hold`) — cómo funciona

`--hold 5:<reg>` hace que **cada** escritura de `ANGLE_SET` incluya el ángulo de
la rotación en el mismo bloque de 6 shorts (coste cero: el bloque se escribe
igual). El ancla por tanto:

- se re-afirma ~decenas de veces por trial, así que no puede derivar;
- **sobrevive a las aperturas globales** del script (`abrir todos los dedos` ya
  no manda la rotación a 1000);
- se mantiene también al salir por Ctrl-C o por aborto de seguridad;
- se **vigila por fuerza**: si la flexión empuja contra la rotación, la carga
  aparece en `FORCE_ACT(5)` y no en `FORCE_ACT(4)`, y el trial aborta
  (`⚠ABORT (fuerza_hold)`). Techo propio: `--safety-force-hold-g`.

Antes de cada campaña el script imprime `ANGLE_ACT` real del DOF anclado y avisa
si **no** llegó a su ángulo (tope mecánico o colisión).

---

## ⚠ Lo que hay que MEDIR antes de empezar (no está en el manual)

El manual (secc. 2.6.11, p. 21) publica los **rangos** angulares pero **no dice
qué extremo de `ANGLE_SET` corresponde a cada ángulo**. Para los dedos quedó
resuelto («`ANGLE_ACT(3)=1000`, i.e. *fully open*» + las campañas del Exp 1 →
1000 = extendido = 176°). Para el pulgar **no está resuelto**, así que el código
se niega a suponerlo: `reg_to_deg()` devuelve `None` para los DOF 4 y 5 hasta que
lo midas, y `--hold 5:165d` (forma en grados) falla con un mensaje que apunta
aquí. Se usa la forma en registro: `--hold 5:0` o `--hold 5:1000`.

> **Nota aparte:** `Interfaz/core/angle_converter.py` (la GUI) usa la dirección
> **invertida** (comenta «registro 0 → dedo abierto») y un rango distinto para la
> flexión del pulgar (53.6° vs los 70° del manual). Eso afecta solo a los grados
> que **muestra** la GUI, no al control ni a estas mediciones — pero conviene
> corregirlo antes de citar grados en la tesis.

---

## Fase P0 — Postura de referencia (10 min, sin bloque)

**Objetivo:** fijar (a) qué valor de `ANGLE_SET(5)` es la rotación a 165°, y
(b) hasta dónde flexiona libre el pulgar en esa postura.

```bash
# P0.1 — ¿qué extremo del registro es 165°? MIRA la mano en cada parada.
.venv/bin/python Caracterizacion/pose_check.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 5 --angles 1000,750,500,250,0 --dwell-s 3
```

Anota qué postura ves en `ANGLE_SET=1000` y en `ANGLE_SET=0`. La rotación a
**165°** es el extremo de máxima rotación lateral del pulgar (el que lo aleja
más del plano metacarpiano). Llámalo `<ROT>` de aquí en adelante.

```bash
# P0.2 — con la rotación anclada, ¿hasta dónde llega la flexión SIN tocar nada?
.venv/bin/python Caracterizacion/pose_check.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --angles 1000,750,500,250,0 --dwell-s 3 \
    --csv Caracterizacion/exp1/data_dof4/pose_dof4.csv
```

**Qué mirar en la salida:**

- La columna `parada`: `detenido` en todas = el pulgar recorre libre. Un
  `techo_fuerza` o `corriente` en las paradas bajas = **auto-colisión** (el
  pulgar topa contra la palma o los dedos en esa rotación).
- `POS_ACT` en cada parada → es el mapa `ANGLE_SET ↔ POS_ACT` del pulgar, que
  necesitarás en las fases siguientes.
- `FORCE_g` ≈ 0 en todas las paradas libres.

**Salida de la fase:** `<ROT>`, el `POS_ACT` libre máximo, y el **`ANGLE_SET`
más cerrado que sigue siendo libre** — ese será el `--target-angle` del Exp 1
(el índice usó 300; el pulgar tendrá el suyo).

⏸ **Pausa: mándame la tabla.** Con ella completo `DOF_DEG_ENDPOINTS[4]` y `[5]`
en `hand_modbus.py` (para que los grados aparezcan en todos los reportes) y fijo
los parámetros de la Fase P1.

---

## Fase P1 — Exp 1: respuesta al escalón en espacio libre

El Exp 0 (baseline de muestreo) **no se repite**: lee el bloque completo de 6
`FORCE_ACT` y es independiente del DOF. Los 98.3 Hz medidos siguen valiendo.

```bash
# P1.1 — validación de UN trial. Confirma |FORCE_ACT|max ≈ 0 (sin contacto).
.venv/bin/python Caracterizacion/exp1/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1 \
    --dof 4 --hold 5:<ROT> --target-angle <TGT> \
    --single --speed 100 --read full --safety-force-g 1200
```

Revisa: `desvío final` de `FORCE_ACT` cerca de su baseline, `máx |F|` de los DOF
anclados ≈ 0, y que **asentó**. Si hay contacto, sube `<TGT>` y repite.

```bash
# P1.2 — campaña del protocolo: 5 velocidades × 20 trials, orden aleatorio.
.venv/bin/python Caracterizacion/exp1/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1 \
    --dof 4 --hold 5:<ROT> --target-angle <TGT> --safety-force-g 1200
```

Escribe en `exp1/data_dof4/` (serie por trial + `index.csv` con las columnas
nuevas `hold` y `max_abs_force_hold_g`). Análisis offline:

```bash
.venv/bin/python Caracterizacion/exp1/exp1_analyze.py --outdir Caracterizacion/exp1/data_dof4
```

⏸ **Pausa: mándame la salida.** Métricas esperadas: deadtime ~independiente de
la velocidad, pendiente ∝ `SPEED_SET` con R² alto, sobreimpulso de posición ≈ 0.

---

## Fase P2 — Exp 2: sobreimpulso de fuerza en contacto

Requiere montar el **bloque rígido** al alcance de la yema del pulgar en la
postura anclada. Antes de montarlo:

```bash
# P2.1 — diagnóstico de la tara de fuerza EN LA POSTURA ANCLADA.
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --zero --zero-flex-angle <TGT>

# P2.2 — recorrido LIBRE de referencia (todavía sin bloque).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --probe --no-block
```

`--zero` debe dejar el reposo calibrado ≈0 g y un residual por flexión pequeño
(en el índice: 241 g → 0, residual ~9 g). `--probe --no-block` da el `POS` libre
máximo: el sondeo **con** bloque tiene que detenerse **antes** de ese valor —
si coincide, el bloque está fuera de alcance.

**Ahora monta el bloque.**

```bash
# P2.3 — sondeo de contacto (presión mínima: abre al detectar).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --probe
```

Da el **POS de contacto** → de ahí salen `--start-angle` (pre-posición justo
antes del contacto, modo A) y `--approach-angle` (modo B). Los valores del
índice (680 y 475) **no sirven**: dependen del montaje y del DOF.

```bash
# P2.4 — una celda de validación antes del grid.
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --start-angle <START> \
    --cell --speed 100 --fset 500 --safety-force-g 1500

# P2.5 — grid modo A (velocidad constante). Piloto N=5 por celda.
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --start-angle <START> --grid --trials 5

# P2.6 — modo B (híbrido: aproximación rápida + cierre lento).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --approach-angle <APPR> --hybrid --trials 5 \
    --outdir Caracterizacion/exp2/data_dof4_hybrid

# P2.7 — sub-experimento de onset (margen de conmutación del modo B).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:<ROT> --start-angle <START> --onset --onset-trials 50 \
    --outdir Caracterizacion/exp2/data_dof4_onset
```

Análisis del grid:

```bash
.venv/bin/python Caracterizacion/exp2/exp2_analyze.py \
    --base Caracterizacion/exp2/data_dof4 --override '' \
    --out  Caracterizacion/exp2/data_dof4
```

⏸ **Pausa entre P2.3, P2.4 y P2.5.** El grid completo son ~175 trials de impacto
contra un bloque: no se lanza sin que la celda de validación se vea sana.

---

## Fase P3 — Análisis, figuras y documento

Con los datos del pulgar en mano: figuras propias (`exp1_make_figure.py` y
`exp2_make_figure.py` están escritas contra las carpetas del índice; se
parametrizan cuando existan los datos y se conozcan las cifras reales) y una
sección comparativa **índice vs pulgar** en `RESUMEN_caracterizacion.html`.

---

## Parámetros por (re)determinar — nada heredado del índice

| Parámetro | Índice | Pulgar | Se fija en |
|---|---|---|---|
| `<ROT>` (ANGLE_SET(5) = 165°) | — | **?** | P0.1 |
| `--target-angle` (Exp 1, sin contacto) | 300 | **?** | P0.2 |
| `--start-angle` (pre-posición modo A) | 680 | **?** | P2.3 |
| `--approach-angle` (modo B) | 475 | **?** | P2.7 |
| `--safety-force-g` | 2200 | empezar en **1500** y subir con evidencia | P2.4 |
| offset de `FORCE_ACT` tras `forceClb` | 241 → 0 g | **?** | P2.1 |
| `q_sw` (margen de conmutación) | 124 counts | **?** | P2.7 |
| pendiente / `SPEED_SET` | 3.04 counts/s | **?** (menor, ver datasheet) | P1.2 |

---

## Seguridad — específico del pulgar

- **Auto-colisión.** A diferencia del índice (que cierra al aire), el pulgar en
  rotación 165° puede topar contra la palma o los dedos. Por eso P0.2 y
  `--probe --no-block` van **antes** de montar el bloque.
- **Techo de fuerza conservador al principio** (`--safety-force-g 1200`–`1500`),
  se sube solo con evidencia del sondeo. El datasheet da ≥30 N (~3060 g) de
  fuerza de agarre en yema, pero eso es el límite del hardware, no del montaje.
- **Vigilancia del DOF anclado** activa por defecto (mismo techo). Si la rotación
  carga estáticamente en esa postura y dispara abortos falsos, súbele el techo
  propio con `--safety-force-hold-g` en vez de bajar el del DOF bajo prueba.
- **GUI cerrada**, un solo proceso sobre el bus (regla del proyecto).
- Todos los modos abren los dedos al salir —fin, Ctrl-C o aborto— **manteniendo**
  el ancla de rotación.
