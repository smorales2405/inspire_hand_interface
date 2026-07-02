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
