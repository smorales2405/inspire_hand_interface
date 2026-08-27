# Exp 2 (DOF 4) — Resultados: sobreimpulso de fuerza del PULGAR en contacto

**Montaje:** Inspire RH56DFTP, **DOF 4 (flexión del pulgar)** contra bloque rígido
fijo, con la **rotación (DOF 5) anclada** en oposición (`ANGLE_SET(5)=0 ≈ 90°`).
Sensor calibrado con `forceClb` al inicio y cada 20 trials. Pre-posición
`--start-angle 750` (`POS ≈ 501`, 279 counts de pista hasta el onset en `POS 771`).
**Grid modo A:** 7 velocidades × 5 `Fset` × 5 trials = **175**, orden aleatorio,
todos en el mismo montaje del bloque (`mount = m1` en `grid_index.csv`).
El bloque se desmontó y volvió a montar después; el montaje `m3` resultante tiene
el onset geométrico en `POS 778–784` contra los 777 de `m1`, **por debajo de la
precisión del propio sondeo (~6 counts, medida con dos lecturas del mismo
montaje)**, así que ambos son la misma geometría a efectos de agrupar trials.
Métrica `ΔF = F_max − Fset` sobre la mediana por celda. Datos: `data_dof4/`.

## Mapa de ΔF (mediana, g)

| v \ Fset | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| 25   | **14**   | 21    | 27   | 29    | 36   |
| 50   | **26**   | 38    | 53   | 78    | 69   |
| 100  | **74**   | 97    | 102  | 155   | 137  |
| 250  | **228**  | 305   | 296  | 355   | 350  |
| 500  | **508**  | 741   | 904  | 746   | 1072*|
| 750  | **1114** | 964   | 1344 | 1096  | 1028 |
| 1000 | **936** | 1524* | 1169 | 1083* | 1403*|

`*` = celda con ≥1 abort (techo 2200 g). **8/175 abortos (5 %)** contra 59/175
(34 %) del índice.

> **La fila `Fset = 100` se amplió a N=20** (105 trials adicionales, montaje `m3`;
> el resto de la matriz sigue en N=5). Es la fila que sostiene el hallazgo
> principal, así que merecía el N. Ver *Ampliación* más abajo: el único valor que
> cambió de forma apreciable fue `v=1000`, de 1397 (N=5) a **936** (N=20).

## Hallazgos

1. **En absoluto el pulgar golpea MÁS SUAVE que el índice.** Para `Fset ≥ 250`
   su ΔF es **0.3–0.6×** el del índice en toda la matriz, y la saturación a alta
   velocidad se queda en **~1200 g** (máx de celda 1524) contra los ~2270 g
   (máx 3263) del índice. De ahí los 8 abortos frente a 59. Menos inercia en
   movimiento explica la diferencia.
2. **Pero NO existe el "setpoint seguro" del índice.** Ese fue el hallazgo más
   útil del DOF 3: con `Fset = 100` su ΔF se quedaba plano en **5–36 g a
   cualquier velocidad**, porque el firmware frenaba antes de que se formara el
   impacto. En el pulgar esa columna **no protege**: crece 14 → **936 g** con
   la velocidad, hasta **26× peor** que el índice en la misma celda.
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

## Ampliación de la fila `Fset = 100` a N=20

105 trials adicionales (15 por velocidad) en el montaje `m3`, sumados a los 5
originales de `m1`. Los dos montajes son la misma geometría: el onset geométrico
del sondeo da `POS 777` (`m1`) y `778`–`784` (`m3`, dos lecturas), y **la
precisión del propio sondeo es de ~6 counts**, así que la diferencia entre
montajes queda por debajo del ruido de medirla.

| v | `m1` (N=5) | `m3` (N=15) | σ de `m3` | **N=20** |
|---|---|---|---|---|
| 25 | 16 | 14 | 3 | **14** |
| 50 | 32 | 25 | 10 | **26** |
| 100 | 66 | 84 | 26 | **74** |
| 250 | 238 | 210 | 50 | **228** |
| 500 | 514 | 504 | 59 | **508** |
| 750 | 1101 | 1127 | 301 | **1114** |
| 1000 | 1397 | 931 | 224 | **936** |

Seis de las siete celdas reproducen dentro de la dispersión de la propia celda.
**La excepción es `v=1000`**, donde la muestra de 5 de `m1` (846, 913, 1397,
1471, 1572) capturó los valores altos de una distribución con σ ≈ 300, mientras
que los 15 de `m3` se agrupan entre 812 y 1059. Un test de permutación exacto
sobre las medias da **p = 0.047**: diferencia apenas significativa, del tipo que
un N=5 produce por azar con esa varianza. **El valor de referencia pasa de 1397
a 936 g.** El hallazgo no cambia —sigue siendo 26× el del índice en la misma
celda— pero la cifra ahora descansa en N=20 y no en cinco impactos.

### La "deriva" no existía — pero la cola sí

Al mirar los 105 trials por mitades pareció haber una caída del sobreimpulso a lo
largo de la tanda (a `v=1000`, 1035 → 880). **Puesto a prueba, no resiste:** un
test de permutación exacto sobre esas dos mitades da **p = 0.140**. Era una
diferencia de medias reportada sin contrastar — el mismo error que el `N=5`.

Para zanjarlo se corrieron **40 trials dedicados** a `v=1000, Fset=100`
(`data_dof4_termico/`): 30 seguidos desde frío y 10 más tras 5 minutos de
descanso, registrando la temperatura del actuador por trial.

- **Sin tendencia con el número de trial:** Spearman `ρ = −0.216`, `p = 0.181`.
- **La temperatura no es un factor:** el actuador pasó de **28 a 30 °C** en 30
  impactos seguidos. Dos grados. Y tras el descanso el `ΔF` **no se recuperó**
  (855 g), que es lo que habría hecho si el efecto fuera térmico.

**Lo que sí hay es una cola pesada.** Sobre `N=55` en esa celda (los 40 dedicados
más los 15 del grid del mismo montaje):

| | ΔF |
|---|---|
| mediana | 898 g |
| p90 | 1054 g |
| **máximo** | **1934 g** |

**El 7 % de los impactos supera 1.5× la mediana**, y el peor llega a **2.2×**. No
son lecturas corruptas: la fuerza se sostiene varias muestras y decae con la
misma forma que en los impactos normales. Eso explica también por qué el `N=5`
original parecía alto — capturó parte de esa cola.

**Consecuencia práctica:** a máxima velocidad el número que importa para
dimensionar el riesgo **no es la mediana sino la cola**. Un objeto que aguante
900 g fallaría en ~1 de cada 14 agarres. Es un argumento más a favor de la
conmutación de velocidad, que elimina el impacto en lugar de acotarlo en promedio.

*(El registro de temperatura por trial —`temp_c`, exigido por el §0.6 del
protocolo— faltaba y se añadió. El resultado es negativo, pero medido: el
actuador del pulgar apenas se calienta en estas campañas.)*

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

## Sub-experimento — onset y margen de conmutación

50/50 toques válidos a v=1000 contra el bloque (retracción al detectar). Datos:
`data_dof4_onset/onset_trials.csv`.

- **Repetibilidad mecánica excelente:** σ robusta = **10.0 counts** (el índice
  dio ~37 con el mismo método; el paper, ~7.5).
- **El onset medido a v=1000 llega tarde por construcción.** Detectado en
  `POS 888` contra el onset **geométrico** de `POS 777` del sondeo lento.
  ⚠ **Ojo con la procedencia:** el bloque se movió entre el grid (P2.5) y este
  sub-experimento, así que esos dos números son de montajes distintos (`m1` y
  `m2`) y su diferencia mezcla dos efectos. Se separan con el onset a **v=25**,
  donde el retardo de detección es de ~1 count por muestra:

  | | `POS` de onset a v=25 | montaje |
  |---|---|---|
  | grid (P2.5) | 808 (σ 6, N=25) | `m1` |
  | modo B (P2.6) | 821 (σ 4, N=25) | `m2` |

  El bloque se desplazó **~13 counts**, no más. De los +111 brutos, **~98 son
  retardo real** y ~13 son el movimiento. El presupuesto teórico del retardo
  sigue cuadrando: margen 120 g ÷ 6.4 g/count ≈ 19 counts, más las 2 muestras
  consecutivas que exige el detector (≈67 a 78 Hz y 2620 counts/s), más la
  lectura de `POS` posterior (≈34) ≈ **120 previstos**. La conclusión no cambia:
  **la detección a alta velocidad llega sistemáticamente tarde y no sirve como
  referencia de conmutación.**
- Por eso el punto de conmutación se ancla en el onset **geométrico** y la σ se
  usa solo para el margen: `q_sw = ceil(3.3·σ) = 34 counts` →
  **conmutar en `POS 777 − 34 = 743`, `--approach-angle 504`**. Restar `q_sw` al
  valor detectado habría dado `POS 854`, **~64 counts pasado el contacto real**
  del montaje `m2` (≈790).
- **Por qué el modo B funcionó pese al cambio de montaje:** conmutó en `POS 743`
  contra un contacto real en ≈790 — **47 counts de margen**, suficiente porque el
  desplazamiento (13) fue mucho menor que el margen. Es un resultado válido, pero
  el margen que lo salvó no estaba planificado: si el bloque se hubiera movido
  50 counts hacia el dedo, el modo B habría impactado a velocidad máxima.

## Modo B — híbrido (aproximación rápida + cierre lento)

Aproximación a `open_speed` hasta `--approach-angle 504` (`POS ≈ 743`), luego
cierre a v=25. 5 `Fset` × 5 trials = 25, **0 abortos**. Datos:
`data_dof4_hybrid/` (montaje `m2`).

| `Fset` | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| **ΔF modo B** | 17 | 34 | 28 | 36 | 37 |
| modo A a v=25 | 16 | 21 | 27 | 29 | 36 |
| modo A a v=1000 | 936 | 1524 | 1169 | 1083 | 1403 |
| **reducción vs v=1000** | **55×** | 45× | 42× | 30× | 38× |
| `F_max` | 117 | 284 | 528 | 786 | 1037 |
| `F_régimen` | 88 | 239 | 421 | 684 | 935 |

1. **El híbrido recupera exactamente el rendimiento de v=25** (17–37 g contra
   16–36 g) mientras se aproxima a velocidad máxima. El sobreimpulso deja de
   depender del `Fset`: la componente de impacto desaparece.
2. **`F_max` sigue al setpoint limpiamente** en todo el rango, y `F_régimen`
   queda más cerca del objetivo que en el índice — o sea que en modo B el
   firmware sí sostiene aproximadamente la fuerza pedida.
3. **La mayor ganancia está justo donde el modo A fallaba peor:** `Fset = 100`,
   la celda sin protección del pulgar, es la que más mejora (**82×**).
4. **Contraste con el índice:** allí el híbrido era *una* de dos mitigaciones
   (el `Fset` bajo también funcionaba). En el pulgar es **la única**. El
   resultado cierra el argumento: la conmutación de velocidad ataca la causa —el
   momento en el instante del contacto— y por eso generaliza entre dedos,
   mientras que bajar el `Fset` depende de la rigidez del contacto y no.

| `Fset` | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| ΔF modo B — pulgar | 17 | 34 | 28 | 36 | 37 |
| ΔF modo B — índice | 2 | 25 | 39 | 71 | 92 |

## Pendiente

Fase P3: figuras del pulgar y sección comparativa índice vs pulgar en el
documento-resumen.
