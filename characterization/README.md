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
.venv/bin/python characterization/exp0_sampling_baseline.py --transport tcp

# TCP explícito
.venv/bin/python characterization/exp0_sampling_baseline.py \
    --transport tcp --ip 192.168.11.210 --port 6000 --n 2000

# Serial RTU
.venv/bin/python characterization/exp0_sampling_baseline.py \
    --transport serial --serial-port /dev/ttyUSB0 --baud 115200

# Guardar la serie de dt por muestra (para graficar en la tesis)
.venv/bin/python characterization/exp0_sampling_baseline.py \
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
.venv/bin/python characterization/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1 \
    --single --speed 100 --read full
```

Revisa en la salida `|FORCE_ACT|max` ≈ 0 (sin contacto). Ajusta `--target-angle`
(y/o `--dof`) hasta que el dedo se mueva libre en el aire sin tocar nada.

### Campaña completa (protocolo)

```bash
.venv/bin/python characterization/exp1_step_response.py \
    --transport serial --serial-port /dev/ttyUSB1 --outdir exp1_out
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
