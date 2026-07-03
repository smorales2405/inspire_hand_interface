# Caracterización dinámica — Inspire RH56DFTP

Código **standalone** para caracterizar la mano sobre hardware físico
(latencia, respuesta al escalón, sobreimpulso de fuerza). Vive **fuera de la
GUI**: no importa PyQt. Regla del proyecto: un solo proceso, un solo hilo, un
solo cliente Modbus, lazo intercalado, `time.perf_counter()` para todos los
timestamps.

FORCE_ACT está en **gramos-fuerza con signo** (int16, rango −4000..4000). A
Newton: `N = g * 9.80665 / 1000`.

> ⚠️ **Correr siempre con la GUI CERRADA.** El cliente pymodbus no es
> thread-safe y la GUI abre su propio cliente sobre el mismo bus; compartir
> transacciones falsearía las mediciones.

---

## Exp 0 — Baseline de muestreo (`exp0_sampling_baseline.py`)

Lee en lazo cerrado el bloque de los 6 registros `FORCE_ACT` (dirección
`1582`, 6 registros) **N** veces, mide el periodo `dt` de cada muestra con
`time.perf_counter()` y reporta la tasa media y el jitter.

**Objetivo:** confirmar que el bus sostiene **≥ 100 Hz**.

### Cómo correr

Usa el intérprete del venv del proyecto (ya trae pymodbus 3.6.9):

```bash
# TCP (valores por defecto: 192.168.11.210:6000, device_id 1, N=2000)
.venv/bin/python Caracterizacion/exp0/exp0_sampling_baseline.py --transport tcp

# TCP explícito
.venv/bin/python Caracterizacion/exp0/exp0_sampling_baseline.py \
    --transport tcp --ip 192.168.11.210 --port 6000 --n 2000

# Serial RTU
.venv/bin/python Caracterizacion/exp0/exp0_sampling_baseline.py \
    --transport serial --serial-port /dev/ttyUSB0 --baud 115200

# Guardar la serie de dt por muestra (para graficar en la tesis)
.venv/bin/python Caracterizacion/exp0/exp0_sampling_baseline.py \
    --transport tcp --csv exp0_dt.csv
```

### Parámetros

| Flag | Def | Descripción |
|---|---|---|
| `--n` | 2000 | Nº de lecturas cronometradas |
| `--warmup` | 10 | Lecturas de calentamiento descartadas (slow-start TCP / 1ra trama) |
| `--transport` | tcp | `tcp` o `serial` |
| `--device-id` | 1 | ID Modbus del esclavo |
| `--timeout` | 1.0 | Timeout Modbus (s). Un timeout aparece como un pico grande de `dt` |
| `--ip` / `--port` | 192.168.11.210 / 6000 | Solo TCP |
| `--serial-port` / `--baud` | /dev/ttyUSB0 / 115200 | Solo serial |
| `--csv` | — | Ruta opcional para volcar `index,dt_ms,ok` por muestra |

### Cómo leer la salida

- **Tasa media (Hz)** = `N / tiempo_total`. Debe ser **≥ 100** para pasar el
  objetivo. Por construcción, `tasa_media = 1 / media(dt)`.
- **Periodo `dt` (ms)**: `media`, `p50`, `p95`, `p99`, `max`, `min`. Los
  percentiles altos y el `max` caracterizan el jitter y los peores casos.
- **Errores**: nº de lecturas fallidas dentro de N. Si es `> 0`, la tasa y los
  percentiles las incluyen (un timeout se ve como un `dt` grande). Idealmente 0.
- **1ra lectura**: primera muestra decodificada en gramos y Newton, como
  sanity check del path de lectura (en reposo debería estar cerca de 0).

### Reportar resultados

Pega la salida completa de consola (y adjunta el CSV si lo generaste). Con eso
confirmamos el baseline y recién ahí pasamos al Exp 1.

---

## Exp 1 — Respuesta al escalón (espacio libre) (`exp1_step_response.py`)

Implementa el Exp 1 del `PROTOCOL_...md`: el dedo se mueve **en el aire** (sin
objeto). Escalón de `ANGLE_SET` de abierto (1000) a un objetivo **sin contacto**;
`FORCE_SET=3000` para que el umbral de fuerza nunca dispare (movimiento puro).
Mide latencia comando→sensor, subida y establecimiento sobre `POS_ACT`.

Un solo proceso/hilo/cliente (helper `hand_modbus.py`). Lazo intercalado: se
escribe el escalón una vez y se lee `POS_ACT` en lazo cerrado con
`perf_counter()`. **Para al asentar `POS_ACT`** (sin cambio > `--settle-pos-band`
durante `--settle-hold-s`), con tope máximo `--window-s` — así los trials lentos
no se truncan. Al salir (fin, Ctrl-C o aborto) **abre todos los dedos**.

Nota de hardware: `FORCE_ACT` tiene un **offset en reposo** (p. ej. ~206 g en el
índice abierto), no es cero. El contacto se juzga por **desvío sobre el baseline
en reposo** (`--contact-delta-g`), no por valor absoluto.

**Muestreo** (desviación deliberada del ejemplo del protocolo, que leía 3
bloques/iter → ~33 Hz):
- `--read pos` (def): solo `POS_ACT` (~87–98 Hz) + chequeo de `FORCE_ACT` cada
  `--safety-every` iters. Mejor resolución de latencia.
- `--read full`: `POS_ACT`+`FORCE_ACT`+`CURRENT` por muestra (~33 Hz).

### ⚠ Validar ANTES de la campaña

Un `--target-angle` mal elegido puede chocar el dedo contra la palma u otros
dedos. Corre **un solo trial** lento y confirma que no hay contacto:

```bash
.venv/bin/python Caracterizacion/exp1/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1 \
    --single --speed 100 --read full
```

Revisa en la salida `|FORCE_ACT|max` ≈ 0 (sin contacto). Ajusta `--target-angle`
(y/o `--dof`) hasta que el dedo se mueva libre en el aire sin tocar nada.

### Campaña completa (protocolo)

```bash
.venv/bin/python Caracterizacion/exp1/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1
```

Barre `--speeds 100,250,500,750,1000` × `--trials 20`, en **orden aleatorio**
(`--seed`). Genera una serie CSV por trial + `index.csv` con metadatos y métrica
rápida (latencia, Δpos, tasa) por trial. El análisis fino (onset, subida,
establecimiento, R², figuras) se hace **offline** sobre esos CSV, después.

### Parámetros clave

| Flag | Def | Nota |
|---|---|---|
| `--dof` | 3 | 3 = índice (empieza aquí por el paper) |
| `--target-angle` | 300 | **objetivo SIN contacto — verifica en tu montaje** |
| `--force-set` | 3000 | alto, para movimiento puro |
| `--speeds` | 100,250,500,750,1000 | barrido de `SPEED_SET` |
| `--trials` | 20 | por velocidad |
| `--read` | pos | `pos` (~90 Hz) o `full` (~33 Hz) |
| `--safety-force-g` | 1800 | techo `|FORCE_ACT|` absoluto → aborta y abre |
| `--window-s` | 10.0 | ventana **máxima** (para al asentar `POS_ACT`) |
| `--settle-pos-band` | 8 | rango de `POS_ACT` (counts) para dar por asentado |
| `--settle-hold-s` | 0.3 | tiempo sin movimiento para declarar asentado |
| `--contact-delta-g` | 150 | desvío de fuerza sobre baseline que sugiere contacto |
| `--single --speed V` | — | corre un trial (validación) |

Repite la campaña (2 pasadas) para verificar repetibilidad; registra la
temperatura por bloque e intercala descansos si sube (deriva térmica).

---

## Exp 2 — Sobreimpulso de fuerza en contacto (`exp2_force_overshoot.py`)

Exp 2 del protocolo: el índice cierra contra un **bloque rígido fijo** y se mide
el sobreimpulso `ΔF = F_max − Fset`. Por ahora está implementado **solo el
sondeo de contacto** (`--probe`); el grid (modos A/B × v × Fset) se añade
después, calibrado con los resultados del sondeo.

**Adaptación del hallazgo del Exp 1** (offset de `FORCE_ACT` dependiente de la
flexión): el contacto se detecta por **stall de `POS_ACT`** (el dedo deja de
avanzar al tocar), no por fuerza absoluta; y la fuerza externa real se obtendrá
restando la curva libre `F(POS_ACT)`.

### Sondeo de contacto — corre esto primero (con el bloque montado)

```bash
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 --probe
```

Cierre lento e instrumentado. **Presión mínima por diseño**: abre el dedo al
detectar contacto. Reporta: si la lectura de bloque ancho (POS+FORCE+CURRENT en
1 transacción) es usable, el offset de fuerza en reposo, el **POS de contacto**
(= ángulo de aproximación para el modo B híbrido), la fuerza de contacto, y los
máximos de fuerza/corriente. Guarda `exp2/data/probe_dof3.csv`.

Seguridad: `SPEED_SET=50`, `FORCE_SET=800` (> offset, para que el firmware no
frene en espacio libre → todo stall es contacto real), techo crudo
`--probe-ceiling 500` g, watchdog de corriente, timeout, y abre todos los dedos
al salir.

| Flag | Def | Nota |
|---|---|---|
| `--probe` | — | corre el sondeo |
| `--probe-speed` | 50 | `SPEED_SET` del cierre lento |
| `--probe-fset` | 800 | alto, para no frenar en espacio libre |
| `--probe-ceiling` | 500 | techo `|FORCE_ACT|` crudo de emergencia (g) |
| `--current-max` | 1200 | corriente máx antes de abortar (mA) |
| `--stall-hold` | 0.12 | tiempo detenido para declarar contacto (s) |

Manda el CSV del sondeo para caracterizar la curva libre `F(POS)` + el onset y
diseñar el grid.

### Sub-experimento — variabilidad del onset (`--onset`)

Fija el **margen de conmutación** del modo B: a v=1000 (peor caso) da N toques
suaves contra el bloque (retrae al detectar el primer contacto) y reporta σ del
`POS_ACT` de onset y `q_sw = ceil(k·σ)` + el `--approach-angle` recomendado.

```bash
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --transport serial --serial-port /dev/ttyUSB0 \
    --onset --outdir Caracterizacion/exp2/data_onset
```

Usa **baseline de fuerza por trial** (inmune a la deriva) y reporta estadística
robusta (excluye outliers de detección). Corre tras (re)montar el bloque, porque
la posición del contacto define el `--approach-angle` del modo B.

---

## Resultados y figuras

Interpretación por experimento:
- `exp0_results.md` — baseline de muestreo (98.3 Hz).
- `exp1_results.md` — respuesta al escalón (deadtime ~64 ms, pendiente ∝ velocidad).
- `exp2_results.md` — sobreimpulso de fuerza (dominado por velocidad; mitigación híbrida).

Figuras (autocontenidas, se abren en cualquier navegador) en `figures/`:
- `exp1_step_response.html` · `exp2_force_overshoot.html`
- SVG por gráfico (vector, para embeber en la tesis/LaTeX): `exp1_overlay_pos_vs_t.svg`,
  `exp1_slope_vs_speed.svg`, `exp1_latency_vs_speed.svg`, `exp2_overshoot_bars.svg`,
  `exp2_hybrid_comparison.svg`.

Regenerar todo desde los CSV (correr desde la raíz del repo):

```bash
.venv/bin/python Caracterizacion/exp1/exp1_analyze.py
.venv/bin/python Caracterizacion/exp1/exp1_make_figure.py
.venv/bin/python Caracterizacion/exp2/exp2_analyze.py
.venv/bin/python Caracterizacion/exp2/exp2_make_figure.py
.venv/bin/python Caracterizacion/figures_to_svg.py       # extrae los SVG standalone
```
