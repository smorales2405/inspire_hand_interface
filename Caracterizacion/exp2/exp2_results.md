# Exp 2 — Resultados: sobreimpulso de fuerza en contacto

**Montaje:** Inspire RH56DFTP, DOF 3, **yema contra bloque rígido fijo**. Sensor
de fuerza **calibrado con `forceClb`** (reg 1009, palma abierta) al inicio de
sesión → `FORCE_ACT` ≈ **fuerza externa** (offset de reposo 241 g → ~0, residual
por flexión ~9 g). Métrica: **ΔF = F_max − Fset** (sobreimpulso), sobre la
mediana de 5 trials/celda (robusta a outliers/aborts).

## Modo A — velocidad constante: mapa de ΔF (mediana, g)

| v \ Fset | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| 25   | 7  | 29    | 64    | 73    | 69   |
| 50   | 15 | 81    | 112   | 100*  | 122  |
| 100  | 5  | 139   | 202   | 392   | 439  |
| 250  | 36 | 336   | 637   | 1108* | 1640*|
| 500  | 24 | 1604* | 2466* | 2194* | 2021*|
| 750  | 28 | 3005* | 3096* | 2726* | 2273*|
| 1000 | 36 | 3263* | 2917* | 2865* | 2502*|

`*` = celda con ≥1 abort (F_max superó el techo de seguridad de 2200 g). Datos:
`data/exp2_analysis_by_cell.csv`, `exp2_overshoot_grid.json`.

## Modo B — híbrido (aproximación rápida + contacto lento): ΔF (g)

| Fset | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| ΔF modo B | 2 | 25 | 39 | 71 | 92 |

(Datos: `data_hybrid/grid_index.csv`.)

## Hallazgos

1. **El sobreimpulso lo domina la velocidad de cierre.** A `Fset=500`: 64 g
   (v=25) → 3096 g (v=750). A alta velocidad la yema **impacta** el bloque y el
   pico es puro momento/inercia — **satura ~3000–3600 g casi independiente de
   Fset** (25/175 = 58 celdas superaron el techo de 2200 g).
2. **`Fset=100` es la zona segura:** ΔF ≤ 36 g a **toda** velocidad (el firmware
   frena antes de golpear).
3. **El modo B híbrido colapsa el sobreimpulso** al nivel de v=25 (ΔF ≤ 92 g)
   para todo Fset — **~68× menor** que el modo A rápido, con `F_max` que sigue a
   `Fset` limpiamente y **0 aborts**. Es la mitigación que propone el paper.
4. **El firmware NO sostiene el setpoint tras el impacto:** sobrepasa y se relaja
   a un contacto pasivo (corriente → 0) por debajo de Fset. Por eso ΔF es el pico
   de impacto, no un error de régimen.

## Sub-experimento — variabilidad del onset y margen de conmutación

A v=1000 (peor caso), 50 toques suaves del índice contra el bloque, midiendo el
`POS_ACT` de primer contacto (fuerza sobre el baseline propio de cada trial +
margen; **retrae al detectar** → toque suave, no impacto). Datos:
`data_onset/onset_trials.csv`. Corre con `exp2_force_overshoot.py --onset`.

- **Repetibilidad mecánica excelente**: σ intra-cluster ~5–8 counts (≈ el σ≈7.5
  del paper). El contacto ocurre de forma muy consistente (POS ≈ 1019).
- **σ medida a v=1000 ≈ 37 counts** (robusta, sin outliers de detección): a esa
  velocidad la **cuantización de `POS_ACT` por muestra** (~30–60 counts) domina la
  σ, no la física. La σ cruda (~118) estaba inflada por esa cuantización + 5–6
  outliers (lecturas Modbus atrasadas), y daba un q_sw irreal (389).
- **Margen de conmutación**: `q_sw = ceil(3.3·σ_robusta) ≈ 124 counts POS`.
- **Para el modo B**: entrar al cierre lento en `POS ≈ 895` (`--approach-angle ≈
  581`), antes del onset mínimo confiable (967). Como la posición del bloque
  cambia entre montajes, correr `--onset` tras (re)montar y usar el
  `--approach-angle` que reporta. (El default 475 del modo B ≈ POS 1120 queda
  *después* del onset para este montaje.)

## Figura

`figures/exp2_force_overshoot.html` (autocontenida) y los SVG
`figures/exp2_overshoot_bars.svg`, `exp2_hybrid_comparison.svg`. Regenerar:
`python Caracterizacion/exp2/exp2_analyze.py && python Caracterizacion/exp2/exp2_make_figure.py`.
