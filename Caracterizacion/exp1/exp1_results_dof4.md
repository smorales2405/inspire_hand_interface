# Exp 1 (DOF 4) — Resultados: respuesta al escalón de la FLEXIÓN DEL PULGAR

**Montaje:** Inspire RH56DFTP, **DOF 4 (flexión del pulgar)** en el aire (sin
objeto), con la **rotación del pulgar (DOF 5) anclada** en su tope de oposición
(`ANGLE_SET(5)=0 ≈ 90°`) durante toda la campaña. Escalón de `ANGLE_SET` de
abierto (1000) a 300 — **el mismo comando que se usó en el índice**, para
comparar con idéntico estímulo. `FORCE_SET=3000`; techo de seguridad 400 g
(el máximo medido en espacio libre en P0.2 fue 67 g). Muestreo `--read pos`
(86.4 Hz) sobre `POS_ACT` con `time.perf_counter()`.
**Campaña:** 5 velocidades × 20 trials, orden aleatorio. **100/100 asentaron,
0 abortos.** Datos: `data_dof4/`.

## Métricas por velocidad (media ± σ, N=20)

| SPEED_SET | Latencia L_band (ms) | Subida 10–90% (ms) | Estab. ±2% (ms) | Pendiente (counts/s) | R² | Sobreimpulso |
|---|---|---|---|---|---|---|
| 100  | 64.5 ± 21.5 | 1705 | 2108 | 302  | 0.999 | ~0 |
| 250  | 79.0 ± 14.4 | 680  | 892  | 751  | 0.995 | ~0 |
| 500  | 76.0 ± 15.6 | 330  | 506  | 1490 | 0.986 | ~0 |
| 750  | 71.8 ± 15.5 | 239  | 387  | 2238 | 0.971 | ~0 |
| 1000 | 74.4 ± 15.1 | 213  | 379  | 2620 | 0.954 | ~0 |

(`data_dof4/analysis_by_speed.csv`, `analysis_per_trial.csv`.)

Repetibilidad del recorrido: `Δpos = 649 ± 0.9` counts sobre los 100 trials
(`POS` inicial 244 ± 0.5) — el escalón se reproduce con menos de 1 count de
dispersión.

## Hallazgos

1. **La misma constante velocidad→pendiente que el índice.** Ajustando por el
   origen con `v ≤ 500`: **k = 2.99 counts/s** por unidad de `SPEED_SET`, contra
   **3.04** del índice (−1.6 %). `SPEED_SET` calibra el **actuador**, no el
   ángulo: dos DOF de cinemática y recorrido muy distintos comparten la misma
   ganancia en counts/s.
2. **Pero el pulgar satura antes.** A `v=1000` la pendiente cae **12.3 % por
   debajo** de la recta `k·v` (el índice solo 3.9 %) y el R² baja a **0.954**
   (índice 0.980). Es la firma de un techo de velocidad, coherente con el
   datasheet, que da >130 °/s al pulgar contra >200 °/s a los cuatro dedos.
   ⚠ *Caveat de resolución:* a `v=1000` el tramo de ajuste 20–80 % contiene
   solo ~12 muestras en el pulgar (vs ~23 en el índice), porque la carrera es
   la mitad a la misma tasa de bus. Parte del déficit puede ser resolución.
   Para separarlo, repetir **solo v=1000** con más recorrido (`--target-angle
   100`) y ver si el déficit persiste.
3. **Deadtime comando→sensor ≈ 73 ms, indistinguible del índice (≈ 69 ms)** con
   σ ~15 ms en ambos y sin tendencia con la velocidad. Confirma que el retardo
   es del **bus + firmware**, no de la mecánica del dedo — el resultado del
   índice se replica en un actuador distinto.
4. **Sobreimpulso de posición ≈ 0** a todas las velocidades (máx 0.02 %, aún más
   limpio que el 0.39 % del índice). No hay pre-deceleración.
5. **Subida y establecimiento son ~la mitad que en el índice** (p. ej. 213 vs
   376 ms a v=1000), pero **no porque el pulgar sea más rápido**: recorre 649
   counts contra 1345 del índice para el mismo comando, a la misma velocidad en
   counts/s. Es distancia, no rapidez.
6. **El ancla se sostuvo.** La desviación de `FORCE_ACT(5)` sobre su propio
   baseline fue **≤ 13 g** en los 100 trials (techo 400 g), o sea que flexionar
   el pulgar no carga el actuador de rotación. El valor **absoluto** llegaba a
   191 g, pero es offset del sensor: su baseline midió **−180 g** en esta sesión
   y **−88 g** en P0.1, con la misma postura y sin contacto. Un umbral absoluto
   habría sido inservible; por eso la vigilancia es relativa al baseline.

## Velocidad angular (conversión a °/s)

Los counts/s **no** son comparables entre DOF sin convertir: la relación
`POS_ACT ↔ ANGLE_SET` es propia de cada actuador y **no es lineal en ninguno de
los dos**. Medida con `pose_check.py` (counts por unidad de `ANGLE_SET`):

| tramo `ANGLE_SET` | índice | pulgar |
|---|---|---|
| 1000→750 | 2.08 | 1.02 |
| 750→500 | 2.00 | 0.98 |
| 500→250 | 1.62 | 0.72 |
| 250→0 | — | 0.70 |

Ambos actuadores comprimen su avance ~25–30 % al flexionarse. Tomando el factor
local del tramo 20–80 % de cada campaña — **0.0783 °/count** el índice
(`data/pose_dof3.csv`) y **0.0842 °/count** el pulgar (`data_dof4/pose_dof4.csv`):

| SPEED_SET | pulgar (°/s) | índice (°/s) | P/I |
|---|---|---|---|
| 100 | 25 | 24 | 1.07 |
| 250 | 63 | 59 | 1.06 |
| 500 | 126 | 119 | 1.05 |
| 750 | 189 | 178 | 1.06 |
| 1000 | 221 | 229 | 0.97 |

Hasta `v=750` el **pulgar es ~6 % más rápido en grados por segundo** que el
índice, pese a tener la misma ganancia en counts/s: su carrera de actuador es
más corta pero cubre proporcionalmente más ángulo. El orden **se invierte a
`v=1000`**, donde el pulgar satura y el índice no — el mismo efecto del hallazgo
2, visto ahora en unidades físicas. Ambos superan a `v=1000` lo que promete el
datasheet (>130 °/s pulgar, >200 °/s cuatro dedos).

## Figura

Pendiente. Se genera cuando estén los datos del Exp 2 del pulgar, junto con la
sección comparativa índice vs pulgar del documento-resumen.
