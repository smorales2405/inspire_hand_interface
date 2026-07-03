# Exp 1 — Resultados: respuesta al escalón (espacio libre)

**Montaje:** Inspire RH56DFTP, DOF 3 (índice), movimiento **en el aire** (sin
objeto). Escalón de `ANGLE_SET` de abierto (1000) a 300; `FORCE_SET=3000` para
que el umbral de fuerza nunca dispare (movimiento puro). Muestreo `--read pos`
(~87 Hz) sobre `POS_ACT`, con `time.perf_counter()` por muestra.
**Campaña:** 5 velocidades × 20 trials, orden aleatorio. 100/100 asentaron, 0 abortos.

## Métricas por velocidad (mediana/media de 20 trials)

| SPEED_SET | Latencia L_band (ms) | Subida 10–90% (ms) | Estab. ±2% (ms) | Pendiente (counts/s) | R² | Sobreimpulso |
|---|---|---|---|---|---|---|
| 100  | 65.1 ± 16.9 | 3519 | 4366 | 304  | 1.000 | ~0 |
| 250  | 78.7 ± 17.4 | 1413 | 1793 | 760  | 0.999 | ~0 |
| 500  | 67.5 ± 16.4 | 696  | 945  | 1521 | 0.995 | ~0 |
| 750  | 70.7 ± 15.9 | 468  | 676  | 2280 | 0.991 | ~0 |
| 1000 | 64.3 ± 8.0  | 376  | 587  | 2922 | 0.980 | ~0 |

(Datos crudos: `exp1_out/analysis_by_speed.csv`, `exp1_out/analysis_per_trial.csv`.)

## Hallazgos

1. **Pendiente ∝ velocidad, lineal y sin deceleración.** La pendiente del tramo
   lineal escala como **≈ 3.04 × SPEED_SET** (304→2922 counts/s) con **R² ≥ 0.98**.
   El crecimiento es lineal (no hay pre-deceleración) — el resultado central que
   replica el paper.
2. **Sobreimpulso de posición ≈ 0** en espacio libre, a todas las velocidades.
3. **Deadtime comando→sensor ≈ 64 ms**, mejor estimado a v=1000 (64 ± 8 ms, el
   más limpio: a alta velocidad el cruce de la banda de detección ocurre casi al
   instante del movimiento real). Incluye el ~10 ms del round-trip Modbus del
   Exp 0 → ~54 ms de hardware.
4. **Nota metodológica:** `L_band` (cruce de banda) es ruidoso a baja velocidad
   por el cruce lento; la latencia por extrapolación (`L_extrap`) NO es un
   deadtime limpio (crece 43→119 ms) porque incluye ~½ del tiempo de aceleración,
   que crece con la velocidad. Ver `exp1_analyze.py`.

## Figura

`figures/exp1_step_response.html` (autocontenida) y los SVG
`figures/exp1_overlay_pos_vs_t.svg`, `exp1_slope_vs_speed.svg`,
`exp1_latency_vs_speed.svg`. Regenerar: `python characterization/exp1_make_figure.py`.
