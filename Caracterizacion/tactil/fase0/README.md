# Fase 0 del táctil — Smoke test / mapa vivo

Compuerta blanda del **punto 2** (caracterización del táctil de la Inspire
RH56DFTP, 17 zonas / 1062 taxeles, crudo 0–4095, sensor **resistivo**). Antes de
invertir en las fases caras (A1 ruido/deriva, A2 histéresis, A3 calibración),
este script identifica **taxeles muertos/pegados/ruidosos** y mide la **tasa real
de muestreo** — el número que *gatea* qué es factible después.

Standalone: **no importa PyQt**. Un solo proceso, un solo hilo, un solo cliente
Modbus, lazo intercalado, `time.perf_counter()` para todos los timestamps. Al
salir deja la mano en **estado seguro** (dedos abiertos).

> ⚠️ **Correr siempre con la GUI CERRADA.** pymodbus no es thread-safe; la GUI
> abre su propio cliente sobre el mismo bus y falsearía las mediciones.

Reutiliza `../hand_modbus.py` (helper Modbus del punto 1) y una copia de la tabla
de zonas en `../tactile_zones.py` (fuente de verdad de direcciones/grids).

---

## Qué hace (en orden)

1. **Baseline en reposo** — `--frames` frames completos (def 300) con la mano
   quieta y **sin contacto** → media (`μ`) y desviación (`σ`) por taxel.
2. **Barrido manual guiado** — interactivo: presionas **una a una** las 17 zonas;
   por cada presión confirma que la zona **sube** y las otras **casi no** (matriz
   de cross-talk 17×17). Usa **re-baseline por zona**: antes de cada presión toma
   una **referencia fresca en reposo**, de modo que el `rise` no se contamina con
   el offset residual de zonas ya presionadas (cross-talk limpio). Cuánto se
   aparta esa referencia del baseline global mide la **no-recuperación acumulada**
   (adelanto de A1.3). Con `--global-baseline` vuelve al modo previo (baseline
   único, una sola presión por zona).
3. **Diagnóstico de taxeles** — marca **muertos** (no responden al presionar su
   zona), **pegado-alto** (`μ` clavado cerca del techo), **pegado-bajo/flatline**
   (`σ≈0` y sin respuesta) y **ruidosos** (`σ` sobre un cerco robusto).
4. **Tasa de muestreo** — Hz de **frame completo** (17 transacciones) y de **zona
   única**, con `dt` media + percentiles p50/p95/p99/max.

---

## Cómo correr

Usa el intérprete del venv del proyecto (trae pymodbus 3.6.9):

```bash
# Corrida completa (serial). Sigue las indicaciones del barrido en pantalla.
.venv/bin/python Caracterizacion/tactil/fase0/fase0_smoke_test.py \
    --transport serial --serial-port /dev/ttyUSB0 --baud 115200

# Solo la tasa (rápido, no interactivo, no mueve la mano):
.venv/bin/python Caracterizacion/tactil/fase0/fase0_smoke_test.py \
    --transport serial --serial-port /dev/ttyUSB0 --rate-only

# Baseline + tasa, sin el barrido manual (diagnóstico parcial):
.venv/bin/python Caracterizacion/tactil/fase0/fase0_smoke_test.py \
    --transport serial --serial-port /dev/ttyUSB0 --skip-barrido

# TCP en vez de serial:
.venv/bin/python Caracterizacion/tactil/fase0/fase0_smoke_test.py \
    --transport tcp --ip 192.168.11.210 --port 6000
```

Durante el **barrido** (re-baseline por zona, default), cada zona pide **dos**
pasos: primero **suelta todo** (reposo) y `[Enter]` para la referencia fresca —
verás el `residual` acumulado —, luego **presiona y mantén** la zona y `[Enter]`
para capturar (`s` salta esa zona, `q` termina). Verás en vivo `rise propio` vs
`peor otra zona`, y el `residual en reposo` — así confirmas que no hay cross-talk
grosero y a la vez mides la no-recuperación antes de seguir.

---

## Parámetros

| Flag | Def | Descripción |
|---|---|---|
| `--transport` | serial | `serial` o `tcp` |
| `--serial-port` / `--baud` | /dev/ttyUSB0 / 115200 | solo serial |
| `--ip` / `--port` | 192.168.11.210 / 6000 | solo TCP |
| `--frames` | 300 | frames de baseline en reposo |
| `--warmup` | 10 | lecturas de calentamiento descartadas |
| `--press-frames` | 15 | frames capturados por zona durante la presión |
| `--press-settle` | 3 | frames descartados al inicio de cada presión |
| `--ref-frames` | 6 | frames de referencia fresca en reposo antes de cada zona |
| `--global-baseline` | — | usa el baseline global (modo previo, sin re-baseline por zona) |
| `--rate-frames` | 200 | lecturas cronometradas de frame completo |
| `--rate-zone-frames` | 500 | lecturas cronometradas de zona única |
| `--rate-zone` | 10 | zona para el test de zona única (10 = Índice·Distal) |
| `--rate-only` | — | solo mide la tasa |
| `--skip-barrido` | — | salta el barrido manual |
| `--no-prompt` | — | no pausa antes del baseline |
| `--no-safe-open` | — | **no** abre los dedos al salir (por defecto sí) |
| `--outdir` | `fase0/data` | directorio de salida |
| `--tag` | — | sufijo para los CSV (p. ej. nº de corrida) |
| `--csv` | — | además guarda las series de `dt` de las tasas |

### Umbrales de diagnóstico (dependientes de medición → **TODO**)

Los defaults son **provisionales**; ajústalos tras ver la primera corrida. El
cerco de ruido es **robusto y derivado de los datos** (mediana + `k·1.4826·MAD`
de la `σ` medida), no una constante inventada.

| Flag | Def | Significado |
|---|---|---|
| `--contact-k` | 5.0 | respuesta = `rise > k·σ_taxel` |
| `--contact-floor` | 20 | piso absoluto de `rise` para contar como respuesta **[TODO]** |
| `--stuck-high` | 3900 | `μ ≥` esto → pegado-alto **[TODO]** (techo nominal 4095) |
| `--sigma-floor` | 0.5 | `σ ≤` esto y sin respuesta → pegado-bajo/flatline **[TODO]** |
| `--noisy-k` | 5.0 | cerco de ruido = `mediana(σ) + k·1.4826·MAD(σ)` |

---

## Salidas

En `--outdir` (def `Caracterizacion/tactil/fase0/data/`):

- **`baseline_taxels.csv`** — `taxel,zone,zone_name,row,col,addr,mu,sigma,min,max,status`.
  Una fila por taxel (1062). Es el **baseline por taxel** que fija el piso de
  umbral de contacto de toda la Fase A/B.
- **`taxel_diagnosis.csv`** — `taxel,…,mu,sigma,own_rise,cross_rise,status`. El
  **mapa de muertos/pegados/ruidosos**: filtra `status != ok` para la lista de
  taxeles a **excluir** de todo análisis posterior. `own_rise` = subida al
  presionar su zona; `cross_rise` = subida máxima cuando se presionaba otra zona.
- **`crosstalk_zonas.csv`** — matriz 17×17 `pressed\victim`: `[i][j]` = subida
  máxima en la zona *j* mientras se presionaba la zona *i*. La **diagonal** es la
  respuesta propia; los **off-diagonal** son el cross-talk entre zonas. Con
  re-baseline por zona, cada fila está referida a su propia referencia fresca.
- **`residual_zonas.csv`** — por zona: `ref_residual_max` (cuánto se apartó el
  reposo del baseline global antes de presionar esa zona → **no-recuperación
  acumulada**, adelanto de A1.3), `own_rise` y el `worst_cross_zone/val`. Solo
  con re-baseline por zona.
- (con `--csv`) `rate_full_dt.csv`, `rate_zone_dt.csv` — series de `dt` por
  lectura para graficar el jitter.

## Cómo leer la salida

- **Tasa**: `frame completo` es lo que gatea el baseline/deriva/calibración
  cuasi-estática; `zona única` es lo que habilita (o no) medir tiempos de
  respuesta en A2.3. Reporta media + percentiles; el `max` caracteriza el peor
  caso. La tasa de zona única **depende del nº de taxeles** de esa zona.
- **Diagnóstico**: revisa primero el conteo (`ok/dead/stuck_high/stuck_low/noisy/
  unknown`). Un taxel `unknown` es uno cuya zona no se presionó en el barrido
  (respuesta sin evaluar). Si `MAD(σ)≈0`, el cerco de ruido queda muy ajustado y
  puede sobre-marcar `noisy`: sube `--noisy-k`.
- **Cross-talk**: en el resumen por zona, `peor otra` en % del propio. Un `<-- alto`
  (>30%) señala acople entre zonas a mirar de cerca en la Fase B (B1).

---

## Después de correr

Pega la **salida completa de consola** y adjunta los CSV. Con eso:
- fijamos el **baseline** y la **lista de exclusión** de taxeles,
- confirmamos las **tasas** (frame vs zona) que gatean A1–A3/Fase B,
- y recién ahí pasamos a **Fase A1** (ruido/deriva). No implementamos A1/A2/A3
  hasta tener estos datos reales.

> Nota: este README es el "cómo correr". Los **resultados** medidos van a
> `fase0_results.md` (al estilo de `exp0_results.md`) una vez tengamos la corrida.
