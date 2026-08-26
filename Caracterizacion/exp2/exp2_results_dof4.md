# Exp 2 (DOF 4) — Resultados: sobreimpulso de fuerza del PULGAR en contacto

**Montaje:** Inspire RH56DFTP, **DOF 4 (flexión del pulgar)** contra bloque rígido
fijo, con la **rotación (DOF 5) anclada** en oposición (`ANGLE_SET(5)=0 ≈ 90°`).
Sensor calibrado con `forceClb` al inicio y cada 20 trials. Pre-posición
`--start-angle 750` (`POS ≈ 501`, 279 counts de pista hasta el onset en `POS 771`).
**Grid modo A:** 7 velocidades × 5 `Fset` × 5 trials = **175**, orden aleatorio.
Métrica `ΔF = F_max − Fset` sobre la mediana por celda. Datos: `data_dof4/`.

## Mapa de ΔF (mediana, g)

| v \ Fset | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| 25   | 16   | 21    | 27   | 29    | 36   |
| 50   | 32   | 38    | 53   | 78    | 69   |
| 100  | 66   | 97    | 102  | 155   | 137  |
| 250  | 238  | 305   | 296  | 355   | 350  |
| 500  | 514  | 741   | 904  | 746   | 1072*|
| 750  | 1101 | 964   | 1344 | 1096  | 1028 |
| 1000 | 1397 | 1524* | 1169 | 1083* | 1403*|

`*` = celda con ≥1 abort (techo 2200 g). **8/175 abortos (5 %)** contra 59/175
(34 %) del índice.

## Hallazgos

1. **En absoluto el pulgar golpea MÁS SUAVE que el índice.** Para `Fset ≥ 250`
   su ΔF es **0.3–0.6×** el del índice en toda la matriz, y la saturación a alta
   velocidad se queda en **~1200 g** (máx de celda 1524) contra los ~2270 g
   (máx 3263) del índice. De ahí los 8 abortos frente a 59. Menos inercia en
   movimiento explica la diferencia.
2. **Pero NO existe el "setpoint seguro" del índice.** Ese fue el hallazgo más
   útil del DOF 3: con `Fset = 100` su ΔF se quedaba plano en **5–36 g a
   cualquier velocidad**, porque el firmware frenaba antes de que se formara el
   impacto. En el pulgar esa columna **no protege**: crece 16 → **1397 g** con
   la velocidad, hasta **39× peor** que el índice en la misma celda.
3. **Mecanismo probable: la rigidez del contacto** (medida en P2.3): 6.4 g/count
   en el pulgar contra 1.6 g/count en el índice. El índice necesita recorrer
   ~62 counts pasado el onset para acumular 100 g, y en ese trecho el firmware
   frena; al pulgar le bastan **~16 counts**, así que el umbral se cruza antes de
   que la reacción sirva de nada. Dicho de otro modo: **cualquier distancia de
   frenado se traduce en 4× más fuerza**. (Interpretación, no medición directa.)
4. **A alta velocidad ΔF es casi independiente de `Fset`** en el pulgar: a
   `v ≥ 750` varía solo un 34 % entre columnas (1083–1524 g). Es el mismo
   régimen dominado por el momento que ya mostraba el índice — pero en el pulgar
   abarca **todas** las columnas, incluida `Fset = 100`.
5. **Consecuencia para la política de agarre:** la mitigación "usa un `Fset`
   bajo" es **específica del dedo y del contacto, no generalizable**. En el
   índice bastaba; en el pulgar es inútil. Eso refuerza el argumento del paper:
   la mitigación robusta es la **conmutación de velocidad (modo B)**, que ataca
   la causa (el momento en el instante del contacto) y no el síntoma.

## Calidad de los datos

El análisis descarta los `F_max` que son **lecturas Modbus corruptas y no
impactos**, con un criterio físico conservador (ver `drop_glitches` en
`exp2_analyze.py`): a `v ≤ 100` el dedo no lleva energía cinética para un pico
inercial, así que un `F_max` aislado en una sola muestra y muy por encima de la
mediana de su celda no puede ser real. A `v ≥ 250` **no se filtra nada**, porque
ahí un pico de impacto genuino dura pocos ms y el muestreo a ~78 Hz lo capta
legítimamente en una sola muestra.

En esta campaña cayó **1 trial** (`v=25, Fset=1000`: `F_max = 2631 g` con los
vecinos en 71 g, a la velocidad más lenta, donde la fuerza sube ~5 g por
muestra). La mediana de la celda no cambia (36 g) — solo desaparece un `*` de
abort espurio.

## Pendiente

Modo B (híbrido) y sub-experimento de onset: fases P2.6 y P2.7 del
[`RUNBOOK_pulgar.md`](../RUNBOOK_pulgar.md). El `--approach-angle` sale de restar
`q_sw` al onset medido (`POS 771`).
