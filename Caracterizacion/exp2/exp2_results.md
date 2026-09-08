# Exp 2 — Resultados: sobreimpulso de fuerza en contacto

**Montaje:** Inspire RH56DFTP, DOF 3, **yema contra bloque rígido fijo**. Sensor
de fuerza **calibrado con `forceClb`** (reg 1009, palma abierta) al inicio de
sesión → `FORCE_ACT` ≈ **fuerza externa + residual de flexión**. Métrica:
**ΔF = F_max − Fset** (sobreimpulso), sobre la mediana de los trials válidos de
cada celda (mediana robusta a outliers/aborts).

> ### ⚠ Corregido 2026-09-07 — la fila `Fset = 100` no medía impactos
>
> Con el bloque desmontado se tomó por fin el **sondeo de recorrido libre** del
> índice (`data/probe_dof3_libre.csv`), que faltaba desde el principio. Con él
> se corrigen dos premisas de este documento:
>
> - **El residual por flexión no es ~9 g.** La curva libre da **70 g en POS 600,
>   125 g en POS 1400 y 232 g en el tope**. El «~9 g» venía del diagnóstico
>   `--zero`, medido en una postura poco flexionada.
> - **El onset de contacto no está en POS ~1200 sino en 1416.** El 1200 se fijó
>   a ojo sobre un sondeo sin curva libre de referencia; el tramo 1200→1400 que
>   se leyó como «contacto blando» es el residual del propio dedo.
>
> Consecuencia: con `Fset = 100` el firmware frena **en el aire**, sobre el
> residual, y el dedo **nunca llega al bloque**. La fila entera termina en
> `POS 791–851` —el mismo punto a todas las velocidades, que es la firma de
> frenar contra el residual— mientras que todas las filas `Fset ≥ 250` llegan a
> `POS 1412–1569`. El «ΔF plano a cualquier velocidad» no era protección: era
> **ausencia de impacto**.
>
> Las tablas de abajo ya están regeneradas con los trials sin contacto
> descartados. Nada más de la campaña cambia.

## Modo A — velocidad constante: mapa de ΔF (mediana, g)

| v \ Fset | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| 25   | 1     | 29    | 54    | 73    | 69   |
| 50   | 1     | 86    | 112   | 105   | 122  |
| 100  | **—** | 139   | 202   | 392   | 439  |
| 250  | **—** | 336   | 637   | 1108* | 1640*|
| 500  | **—** | 1604* | 2466* | 2194* | 2021*|
| 750  | **—** | 3005* | 3096* | 2726* | 2273*|
| 1000 | **295** | 3263* | 2917* | 2865* | 2502*|

`*` = celda con ≥1 abort (F_max superó el techo de seguridad de 2200 g).
**—** = el dedo **no llegó al objeto** en ninguno de los 5 trials (ver el aviso
de arriba). Datos: `data/exp2_analysis_by_cell.csv`, `exp2_overshoot_grid.json`.
Reproducible con `exp2_analyze.py --geom-onset 1416`.

> *Corregido 2026-08-26:* la celda `v=25, Fset=500` pasa de 64 a **54 g**. Un
> trial tenía un `F_max` de 1873 g con los vecinos en 404 g, a la velocidad más
> lenta — una lectura Modbus corrupta, no un impacto. `exp2_analyze.py` ahora la
> descarta con un criterio físico explícito (`drop_glitches`: solo a `v ≤ 100`,
> donde el dedo no lleva energía cinética para un pico inercial; a `v ≥ 250` no
> filtra nada porque ahí el pico real sí dura una sola muestra). Es la **única**
> celda del mapa que cambia; el resto queda idéntico.

## Modo B — híbrido (aproximación rápida + contacto lento): ΔF (g)

| Fset | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| ΔF modo B | **—** | 25 | 39 | 71 | 92 |

**—**: los cinco trials `Fset=100` paran en `POS 1212–1226`, ~200 counts antes
del bloque. Tampoco tocan. (Datos: `data_hybrid/grid_index.csv`.)

## Hallazgos

1. **El sobreimpulso lo domina la velocidad de cierre.** A `Fset=500`: 54 g
   (v=25) → 3096 g (v=750). A alta velocidad la yema **impacta** el bloque y el
   pico es puro momento/inercia — **satura ~3000–3600 g casi independiente de
   Fset** (25/175 = 58 celdas superaron el techo de 2200 g).
2. **`Fset=100` NO es una zona segura: es un ajuste inalcanzable.** El residual
   de flexión del propio índice cruza los 100 g en `POS ~800`, seiscientos
   counts antes del bloque, así que el firmware frena en el aire y el dedo no
   toca nada. De `v=100` a `v=750` no hay ni un trial con contacto. A `v ≤ 50`
   el dedo llega justo y roza con suavidad real (ΔF ≈ 1 g). Y a `v=1000` el
   momento lo mete dentro: **ΔF = 295 g**. Es decir, **a la única velocidad a la
   que un agarre rápido ocurre de verdad, `Fset=100` no protege**.

   *(Este punto decía antes «ΔF ≤ 36 g a toda velocidad — el firmware frena
   antes de golpear». Los 5–36 g eran el firmware frenando contra el propio
   dedo, sin objeto delante.)*
3. **El modo B híbrido colapsa el sobreimpulso** al nivel de v=25 (ΔF ≤ 92 g)
   para todo `Fset` alcanzable — **~35× menor** que el modo A rápido, con
   `F_max` que sigue a `Fset` limpiamente y **0 aborts**. Es la mitigación que
   propone el paper, y la **única** que sobrevive a la corrección de arriba.
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
  613`), antes del onset mínimo confiable (967).

> ⚠ *Caveat añadido 2026-08-26 (descubierto al caracterizar el pulgar):* este
> `POS 895` sale de restar `q_sw` al onset **detectado** a v=1000, que llega
> sistemáticamente **tarde** — el margen de fuerza, las 2 muestras consecutivas
> del detector y la lectura de `POS` posterior suman, para el índice, un
> presupuesto de ~187 counts. La referencia correcta es el onset **geométrico**
> del sondeo lento en el **mismo montaje**, y aquí no existe: el
> `probe_dof3.csv` disponible es de otro montaje del bloque (da 1420, con un
> sesgo de −401 contra el sub-experimento, imposible por retardo). Trátese
> `895` como **cota superior** y re-derívese con `--probe` + `--onset` sobre el
> montaje real antes de usarlo. El modo B ya corrido no se ve afectado: usó
> `--approach-angle 475`, muy por delante.
  *(Corregido 2026-08-25: el valor publicado antes, 581, salía de linealizar
  `POS↔ANGLE`. La tabla medida `data/pose_dof3.csv` muestra que la relación no es
  lineal —2.08 counts/grado al abrir contra 1.62 al cerrar— y da 613. El `POS`
  de conmutación, que es la magnitud primaria, no cambia.)* Como la posición del bloque
  cambia entre montajes, correr `--onset` tras (re)montar y usar el
  `--approach-angle` que reporta. (El default 475 del modo B ≈ POS 1120 queda
  *después* del onset para este montaje.)

## Figura

`figures/exp2_force_overshoot.html` (autocontenida) y los SVG
`figures/exp2_overshoot_bars.svg`, `exp2_hybrid_comparison.svg`. Regenerar:
`python Caracterizacion/exp2/exp2_analyze.py && python Caracterizacion/exp2/exp2_make_figure.py`.
