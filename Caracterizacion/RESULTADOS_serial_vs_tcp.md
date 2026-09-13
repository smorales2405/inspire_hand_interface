# Comparación: RS-485 (serial) vs Modbus TCP

**Fecha:** 2026-09-12 · DOF 3 (índice) · mano Inspire RH56DFTP.
**Serial:** RS-485 @ 115 200 baud (`/dev/ttyUSB*`). **TCP:** Ethernet, `192.168.124.210:6000`.
Reproducible: `python Caracterizacion/compare_serial_tcp.py`.

**Objetivo:** verificar si cambian, respecto a serial, la **tasa de muestreo**, la
**latencia** y la **resolución** de las mediciones al pasar a Modbus TCP.

## Exp 0 — muestreo (solo lectura)

| Métrica | Serial | TCP | Cambio |
|---|---|---|---|
| Tasa media | 98 Hz | **797 Hz** | ~8× |
| dt mediana (p50) | 10.93 ms | **0.63 ms** | ~17× más fino |

TCP elimina el tiempo de cable serial; queda una cola (~5% de lecturas en 6–10 ms)
por la cadencia interna del firmware. Datos: `exp0/data/exp0_tcp.csv`.

## Exp 1 — respuesta al escalón

Tasa (modo pos): **87 → 580 Hz (~7×)**. `write_cost` del comando: **~12 → ~1 ms (~12×)**.

| v | Pendiente c/s (ser→tcp) | R² (ser→tcp) |
|---|---|---|
| 100 | 304 → 304 | 1.000 → 1.000 |
| 250 | 760 → 758 | 0.999 → 0.998 |
| 500 | 1521 → 1516 | 0.995 → 0.992 |
| 750 | 2280 → 2214 | 0.991 → 0.979 |
| 1000 | 2922 → 2934 | 0.980 → 0.980 |

La **pendiente∝velocidad y el R² son idénticos**; el **deadtime (~60–80 ms) no
cambia** (es del hardware). *Caveat:* a ~600 Hz el ruido de POS dispara falsos
onsets con el método por banda → usar el detector robusto (extrapolación).
Datos: `exp1/data_tcp/`.

## Exp 2 — sobreimpulso de fuerza en contacto (Fset = 500)

Tasa: **~65 → 587 Hz (~9×)**.

| v | F_max serial (g) | F_max TCP (g) |
|---|---|---|
| 100 | 702 | 783 |
| 250 | 1137 | 1002 |
| 500 | 2966 | 2282 |
| 750 | 3596 | 3417 |
| 1000 | 3417 | 3674 |

**Misma tendencia y magnitud** (crece con la velocidad, satura ~3400–3700 g); las
diferencias caen dentro de la variabilidad de impacto (N=3–5). El beneficio de
resolución se ve en la **consistencia del pico a v=1000** (TCP: σ=10 g sobre 3
trials; en serial el pico rápido quedaba subestimado/disperso). Datos:
`exp2/data_tcp/`.

## Conclusión

- **El transporte NO cambia la física del dedo:** pendiente∝v, R² y las magnitudes
  de sobreimpulso son iguales serial↔TCP → **la caracterización serial sigue
  siendo válida.**
- **La latencia intrínseca (deadtime ~60–80 ms) tampoco cambia** (es del hardware).
- **TCP mejora la adquisición:** tasa ~7–9×, resolución temporal ~17×, `write_cost`
  ~12× menor. Esto favorece el **control de fuerza en tiempo real** y la captura
  fiel de transitorios rápidos (pico `F_max`, y resolvería el σ_onset que en serial
  quedó limitado por cuantización).
