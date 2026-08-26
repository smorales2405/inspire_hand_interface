# Runbook — Caracterización dinámica de la FLEXIÓN DEL PULGAR (DOF 4)

Réplica del [`PROTOCOL_Dynamic_Characterization_RH56DFTP.md`](PROTOCOL_Dynamic_Characterization_RH56DFTP.md)
—ya ejecutado sobre el índice (DOF 3)— aplicado ahora a la **flexión del pulgar
(DOF 4)**, con la **rotación del pulgar (DOF 5) anclada en su tope de oposición**
(`ANGLE_SET(5) = 0`, medido en P0.1) para que la única variable cinemática sea la
flexión.

El propio protocolo lo anticipa (§1: *«Luego repite para medio (DOF 2) y flexión
del pulgar (DOF 4) si quieres cobertura»*). Lo que sigue es la instanciación
concreta, por fases, con el hardware en el lazo.

---

## Qué cambia respecto del índice

| | Índice (hecho) | Pulgar (este runbook) |
|---|---|---|
| DOF bajo prueba | 3 | **4** (flexión) |
| DOF anclado | — | **5** (rotación) en `ANGLE_SET 0` ≈ 90°, `--hold 5:0` |
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

> El criterio es la **desviación sobre el baseline en reposo del propio DOF
> anclado**, nunca su valor absoluto. Ese sensor tiene offset propio (−88 g en la
> rotación del pulgar, medido en P0.1) y además se mueve con la postura del DOF
> bajo prueba: en P1.1 el absoluto llegó a 195 g **sin contacto alguno**. Cada
> trial mide su propio baseline antes del escalón y registra
> `FORCE_ACT` del DOF anclado en el CSV (`force_hold_g`), así que el
> acoplamiento queda documentado en vez de disfrazado de colisión.

Antes de cada campaña el script imprime `ANGLE_ACT` real del DOF anclado y avisa
si **no** llegó a su ángulo (tope mecánico o colisión).

---

## ✔ Correspondencia registro↔ángulo — RESUELTA (P0.1, 2026-08-25)

El manual (secc. 2.6.11, p. 21-22) publica los **rangos** angulares pero **no
dice qué extremo de `ANGLE_SET` corresponde a cada ángulo**. Quedó resuelto así:

- **Dedos:** el manual dice «`ANGLE_ACT(3)=1000`, i.e. *fully open*» y las
  campañas del Exp 1 lo verifican → **1000 = extendido = 176°**.
- **Rotación del pulgar (DOF 5):** medido con `pose_check.py`. `ANGLE_SET 1000`
  deja la rotación **abierta** (lateral) y `ANGLE_SET 0` la lleva al **tope de
  cierre** (oposición). En la figura del manual (p. 22/27) el ángulo β se mide
  desde el **plano metacarpiano**: 90° = pulgar perpendicular al plano = máxima
  **oposición**; 165° = pulgar casi tendido en el plano = **abierto**. Por tanto
  **`ANGLE_SET 1000 = 165°` y `ANGLE_SET 0 = 90°`**.
- **Flexión del pulgar (DOF 4):** misma regla + figura del manual (p. 21/27,
  θ crece al extender) → **1000 = 70° (extendido), 0 = −13° (flexionado)**.
  Se confirma de vista en P0.2.

> ⚠ **Corrección respecto del planteo inicial.** La postura de trabajo elegida
> —el tope de oposición, `ANGLE_SET(5) = 0`— es **90°**, no 165°. Los 165° son el
> extremo **opuesto** (pulgar abierto/lateral), donde la yema no enfrenta a los
> dedos y no podría presionar el bloque. La postura es la correcta para el
> experimento; lo que hay que corregir es la **etiqueta en grados** al redactar.

Regla única, ya cargada en `hand_modbus.DOF_DEG_ENDPOINTS`: **`ANGLE_SET 1000` =
extremo abierto = ángulo mayor del rango; `ANGLE_SET 0` = extremo cerrado =
ángulo menor.** Todos los reportes imprimen ya los grados.

> **Nota aparte:** `Interfaz/core/angle_converter.py` (la GUI) usa la dirección
> **invertida** (comenta «registro 0 → dedo abierto») y un rango distinto para la
> flexión del pulgar (53.6° vs los 70° del manual). Eso afecta solo a los grados
> que **muestra** la GUI, no al control ni a estas mediciones — pero conviene
> corregirlo antes de citar grados en la tesis.

---

## Fase P0 — Postura de referencia (10 min, sin bloque)

**Objetivo:** fijar (a) qué valor de `ANGLE_SET(5)` es la postura de trabajo de
la rotación, y (b) hasta dónde flexiona libre el pulgar en esa postura.

### P0.1 — ✔ HECHA (2026-08-25)

```bash
.venv/bin/python Caracterizacion/pose_check.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 5 --angles 1000,750,500,250,0 --dwell-s 3
```

| `ANGLE_SET` | `ANGLE_ACT` | `POS_ACT` | `FORCE_g` | parada | postura observada |
|---|---|---|---|---|---|
| 1000 | 986 | 51 | −245 | detenido | rotación **abierta** (≈165°) |
| 750 | 738 | 467 | −79 | detenido | |
| 500 | 489 | 884 | −75 | detenido | |
| 250 | 238 | 1303 | −106 | detenido | |
| **0** | **0** | **1556** | **−88** | detenido | **tope de oposición (≈90°) ← postura de trabajo** |

Las cinco paradas dieron `detenido` y `mA = 0`: la rotación recorre **libre**, sin
colisión. Recorrido de `POS_ACT(5)`: 51 … 1556 (1505 counts).
`FORCE_ACT(5)` tiene un **offset negativo en reposo** (−245 g abierto, ~−90 g en
el resto) **sin contacto** — se elimina con la tara `forceClb` de la fase P2.1, y
queda muy por debajo del techo de la vigilancia del DOF anclado.

**Resultado: el ancla es `--hold 5:0`.**

### P0.2 — ✔ HECHA (2026-08-25)

```bash
.venv/bin/python Caracterizacion/pose_check.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --angles 1000,750,500,250,0 --dwell-s 3 \
    --csv Caracterizacion/exp1/data_dof4/pose_dof4.csv
```

| `ANGLE_SET` | grados | `ANGLE_ACT` | `POS_ACT` | `FORCE_g` | mA | parada |
|---|---|---|---|---|---|---|
| 1000 | 70.0° | 1000 | 245 | 13 | 0 | detenido |
| 750 | 49.2° | 753 | 501 | 39 | 0 | detenido |
| 500 | 28.5° | 504 | 747 | 49 | 0 | detenido |
| 250 | 7.8° | 254 | 928 | 53 | 0 | detenido |
| 0 | −13.0° | 3 | 1103 | 67 | 0 | detenido |

(Tabla en `exp1/data_dof4/pose_dof4.csv`.)

**Tres resultados:**

1. **La flexión recorre TODO su rango libre, sin auto-colisión.** Las cinco
   paradas dieron `detenido` con `mA = 0` y fuerza ≤ 67 g — incluso a
   `ANGLE_SET 0` (flexión completa) el pulgar no toca la palma ni los dedos en
   esta rotación. Es más margen del que tenía el índice, que sí chocaba y obligó
   a limitar el objetivo del Exp 1.
2. **`FORCE_ACT(4)` tiene el mismo offset dependiente de la flexión que el
   índice, pero ~5× menor**: 13 g extendido → 67 g flexionado (+54 g en todo el
   recorrido, contra los ~110 g del índice), sin contacto externo. Buena noticia
   para el Exp 2: el residual tras `forceClb` será pequeño.
3. **Carrera corta y NO lineal.** `POS_ACT` va de 245 a 1103 = **858 counts**,
   bastante menos que el índice. Y el avance se comprime al flexionar: ~1.02
   counts por unidad de `ANGLE_SET` en la primera mitad contra ~0.71 en la
   segunda. Por eso el sub-experimento de onset ya **no** interpola entre dos
   anclas (hasta 58 counts de error de `ANGLE_SET`): usa esta tabla completa,
   interpolada a tramos. La encuentra sola en `exp1/data_dof4/pose_dof4.csv`, o
   se le pasa con `--pos-angle-csv`.

**Parámetros que fija esta fase para el Exp 1:**

- `--target-angle 300` — deliberadamente **el mismo comando que el índice**
  (escalón 1000→300), para que la comparación entre dedos sea con el mismo
  estímulo. Cae entre dos paradas libres (250 y 500) y da ~655 counts de
  recorrido, sin llegar al extremo del rango (evita que la deceleración de fin
  de carrera contamine el establecimiento).
- `--safety-force-g 400` — el máximo medido en espacio libre es 67 g (y ~88 g en
  la rotación anclada), así que 400 g deja ~6× de margen y aun así corta muy
  pronto ante una colisión inesperada. Mucho más protector que los 1800 g por
  defecto, que en espacio libre nunca dispararían a tiempo. Si P1.1 aborta sin
  causa visible, se sube — para eso está la validación de un solo trial.

---

## Fase P1 — Exp 1: respuesta al escalón en espacio libre

El Exp 0 (baseline de muestreo) **no se repite**: lee el bloque completo de 6
`FORCE_ACT` y es independiente del DOF. Los 98.3 Hz medidos siguen valiendo.

```bash
# P1.1 — validación de UN trial. Confirma |FORCE_ACT|max ≈ 0 (sin contacto).
.venv/bin/python Caracterizacion/exp1/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1 \
    --dof 4 --hold 5:0 --target-angle 300 \
    --single --speed 100 --read full --safety-force-g 400
```

Revisa: `desvío final` de `FORCE_ACT` ≈ +54 g sobre su baseline (el offset por
flexión medido en P0.2, no contacto), `máx |F|` de los DOF anclados pequeño, y
que **asentó**. `Δpos` esperado ≈ 655 counts.

```bash
# P1.2 — campaña del protocolo: 5 velocidades × 20 trials, orden aleatorio.
.venv/bin/python Caracterizacion/exp1/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1 \
    --dof 4 --hold 5:0 --target-angle 300 --safety-force-g 400
```

Escribe en `exp1/data_dof4/` (serie por trial + `index.csv`). Análisis offline:

```bash
.venv/bin/python Caracterizacion/exp1/exp1_analyze.py --outdir Caracterizacion/exp1/data_dof4
```

### ✔ P1 HECHA (2026-08-25) — ver [`exp1/exp1_results_dof4.md`](exp1/exp1_results_dof4.md)

100/100 asentaron, 0 abortos, 86.4 Hz, `Δpos = 649 ± 0.9` counts. Resumen:

- **k = 2.99 counts/s** por unidad de `SPEED_SET`, contra 3.04 del índice:
  `SPEED_SET` calibra el actuador, no el ángulo.
- **El pulgar satura a `v=1000`** (−12.3 % bajo la recta `k·v`, R² 0.954; el
  índice −3.9 %, R² 0.980) — techo de velocidad, con un caveat de resolución.
- **Deadtime 73 ms**, indistinguible de los 69 ms del índice → es del bus +
  firmware, no de la mecánica.
- **Sobreimpulso de posición ≈ 0** (máx 0.02 %).
- El ancla se sostuvo: desviación de `FORCE_ACT(5)` ≤ 13 g en 100 trials.

---

## Fase P2 — Exp 2: sobreimpulso de fuerza en contacto

Requiere montar el **bloque rígido** al alcance de la yema del pulgar en la
postura anclada. Antes de montarlo:

```bash
# P2.1 — diagnóstico de la tara de fuerza EN LA POSTURA ANCLADA.
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --zero --zero-flex-angle 300

# P2.2 — recorrido LIBRE de referencia (todavía sin bloque).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --probe --no-block
```

### ✔ P2.1 HECHA (2026-08-25)

| | índice (DOF 3) | pulgar (DOF 4) |
|---|---|---|
| `FORCE_ACT` en reposo, antes de la tara | 241 g | **11 g** |
| tras `forceClb` | ~0 g | **0 g** |
| residual por flexión (libre, `ANGLE_SET 300`) | ~9 g | **51 g** (a `POS 892`) |

La tara funciona igual de bien, pero el reparto cambia: el pulgar arranca casi
sin offset de reposo y en cambio acumula **~5× más residual por flexión** que el
índice. Eso importa porque **`FORCE_SET` se compara contra la lectura CRUDA**:
en la posición de contacto el firmware ya "ve" ~51 g antes de tocar nada, así
que el umbral efectivo en fuerza externa es `Fset − residual`. Para `Fset = 100`
eso es ~49 g — la mitad. En el índice la corrección era de 9 g y se podía
ignorar; aquí **no**.

Consecuencias, ya implementadas:

- Cada trial del Exp 2 registra `f_base_g` (el residual medido en su propia
  pre-posición, inmune a la deriva) en `grid_index.csv`, y `--cell` lo imprime
  junto con el umbral externo efectivo.
- `ΔF = F_max − Fset` **sigue siendo válido tal cual**: ambos términos están en
  el marco crudo y el residual es ~constante durante el impacto, así que se
  cancela. Lo que hay que corregir al interpretar es *dónde queda el umbral en
  fuerza externa*, no la magnitud del sobreimpulso.
- La curva completa `residual(POS)` sale de **P2.2**: es la diferencia
  `F(POS) − F(abierto)`, que no depende de la tara. ### ✔ P2.2 HECHA (2026-08-25)

Recorrido libre `POS 245 → 1104` (859 counts), parada por tope mecánico, fuerza
máxima cruda 69 g, corriente máx 118 mA. Coincide con P0.2 (1103). **Ese 1104 es
la referencia**: el sondeo *con* bloque debe detenerse por debajo; si coincide,
el bloque está fuera del alcance del pulgar.

Curva `residual(POS)` en espacio libre (`= F(POS) − F(abierto)`, independiente de
la tara). Datos: `exp2/data_dof4/probe_dof4_libre.csv`.

| `POS` | `ANGLE` | grados | residual | umbral externo efectivo `Fset − residual` |
|---|---|---|---|---|
| | | | | `100` · `250` · `500` · `750` · `1000` |
| 274 | 972 | 67.7° | 17 g | 83 · 233 · 483 · 733 · 983 |
| 427 | 822 | 55.2° | 35 g | 65 · 215 · 465 · 715 · 965 |
| 626 | 623 | 38.7° | 36 g | 64 · 214 · 464 · 714 · 964 |
| 824 | 394 | 19.7° | 42 g | 58 · 208 · 458 · 708 · 958 |
| 919 | 262 | 8.7° | 47 g | 53 · 203 · 453 · 703 · 953 |
| 1025 | 111 | −3.8° | 52 g | 48 · 198 · 448 · 698 · 948 |
| 1104 | 0 | −13.0° | 58 g | 42 · 192 · 442 · 692 · 942 |

El residual salta a ~17 g en los primeros 30 counts y luego crece despacio,
~+20 g en los 700 counts restantes. Se queda entre **17 y 58 g** en todo el
recorrido.

**Lectura para el grid:** el sesgo relativo depende del `Fset`. Para
`Fset ≥ 500` es ≤ 12 % y se puede reportar el nominal; para `Fset = 100` el
umbral externo real es ~**50 g**, la mitad del nominal. La celda sigue siendo
válida (es la más suave del barrido, igual que en el índice), pero **hay que
etiquetarla por su valor efectivo**, no por el comandado. El `f_base_g` que
registra cada trial da esa corrección medida en la pre-posición exacta.

> ⚠ **Restricción de diseño para P2.3/P2.5.** El residual está presente **ya en
> la pre-posición**, antes de tocar nada. Si `residual(start_pos) ≥ Fset`, el
> firmware frena en el aire y el trial no llega nunca al bloque. Con
> `Fset = 100` el margen es de 58 g en `POS 824` pero baja a 48 g en `POS 1025`.
> Al elegir `--start-angle` tras el sondeo con bloque, verificar que
> `f_base_g` reportado quede holgadamente por debajo de 100.

**Ahora monta el bloque.**

```bash
# P2.3 — sondeo de contacto (presión mínima: abre al detectar).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --probe
```

Da el **POS de contacto** → de ahí salen `--start-angle` (pre-posición justo
antes del contacto, modo A) y `--approach-angle` (modo B). Los valores del
índice (680 y 475) **no sirven**: dependen del montaje y del DOF.

```bash
# P2.4 — una celda de validación antes del grid.
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --start-angle <START> \
    --cell --speed 100 --fset 500 --safety-force-g 1500

# P2.5 — grid modo A (velocidad constante). Piloto N=5 por celda.
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --start-angle <START> --grid --trials 5

# P2.6 — modo B (híbrido: aproximación rápida + cierre lento).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --approach-angle <APPR> --hybrid --trials 5 \
    --outdir Caracterizacion/exp2/data_dof4_hybrid

# P2.7 — sub-experimento de onset (margen de conmutación del modo B).
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --dof 4 --hold 5:0 --start-angle <START> --onset --onset-trials 50 \
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
| ancla de rotación `--hold 5:<reg>` | — | **0** (≈90°, oposición) ✔ | P0.1 |
| `--target-angle` (Exp 1, sin contacto) | 300 | **300** (mismo comando) ✔ | P0.2 |
| `--start-angle` (pre-posición modo A) | 680 | **?** | P2.3 |
| `--approach-angle` (modo B) | 475 | **?** | P2.7 |
| `--safety-force-g` | 2200 | **400** en Exp 1; en Exp 2 empezar en **1500** | P0.2 / P2.4 |
| offset de `FORCE_ACT` tras `forceClb` | 241 → 0 g | **?** | P2.1 |
| `q_sw` (margen de conmutación) | 124 counts | **?** | P2.7 |
| pendiente / `SPEED_SET` | 3.04 counts/s | **?** (menor, ver datasheet) | P1.2 |

---

## Seguridad — específico del pulgar

- **Auto-colisión.** A diferencia del índice (que cierra al aire), el pulgar en
  oposición puede topar contra la palma o los dedos. Por eso P0.2 y
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
