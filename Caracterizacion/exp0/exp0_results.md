# Exp 0 — Resultados del baseline de muestreo (FORCE_ACT)

**Fecha:** 2026-07-02
**Transporte:** serial `/dev/ttyUSB1` @ 115200 baud, device_id 1
**Adaptador:** FTDI FT232 (`0403:6001`), `latency_timer = 1 ms` (ya optimizado)
**Comando:** `exp0_sampling_baseline.py --transport serial --serial-port /dev/ttyUSB1 --baud 115200 --n 2000 --csv exp0_dataN.csv`
**Corridas:** 3 × N=2000 (6000 lecturas), mano conectada y en reposo, GUI cerrada.

## Métricas

| Corrida | Hz | mean dt | sd | min | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|
| data1 | 98.2 | 10.183 | 2.870 | 6.051 | 11.017 | 13.756 | 14.746 | 14.966 |
| data2 | 98.8 | 10.121 | 2.899 | 6.061 | 10.894 | 13.784 | 14.415 | 15.391 |
| data3 | 97.8 | 10.224 | 2.873 | 6.075 | 10.908 | 13.817 | 14.759 | 14.923 |
| **Agregado** | **98.3** | **10.176** | **2.881** | **6.051** | **10.931** | **13.785** | **14.750** | **15.391** |

(dt en ms). **0 errores en 6000 lecturas.** Spread entre corridas < 1 Hz → altamente reproducible.

## Distribución

`dt` es **bimodal** con un hueco casi vacío en 8–10 ms:
- ~36% rápidas (~6.0–7.5 ms).
- ~resto lentas y dispersas (~10.5–14 ms, con varios sub-picos).

## Diagnóstico

- El techo **no** lo impone el harness (1 hilo, 1 transacción por lectura, sin overhead) ni el adaptador USB (`latency_timer` ya en 1 ms).
- `min ≈ 6 ms` = piso real de respuesta del hardware. Tiempo de cable a 115200 (25 bytes, 8N1) ≈ 2.2 ms.
- El grupo lento disperso es la firma de **batido/aliasing** entre el lazo del host y la cadencia interna con que el firmware de la mano refresca `FORCE_ACT` / atiende Modbus: si la petición pierde el tick interno, espera uno extra (→ 10–14 ms).
- Levers reales desde el host para subir la tasa: mayor baudrate (reduce ~2 ms de cable) o transporte TCP. No se persiguieron (ver decisión).

## Decisión

**Baseline aceptado en 98.3 Hz.** Para caracterizar respuesta al escalón y sobreimpulso de fuerza (dinámica mecánica de decenas–cientos de ms), 98.3 Hz es adecuado (Nyquist ~49 Hz ≫ ancho de banda mecánico). Cada muestra lleva timestamp `time.perf_counter()`, por lo que el muestreo es irregular pero exactamente fechado → válido para ajuste de τ, tiempo de subida y overshoot (interpolando si hace falta).

Series crudas por muestra (en la raíz del repo): `exp0_data1.csv`, `exp0_data2.csv`, `exp0_data3.csv` (`index,dt_ms,ok`).
