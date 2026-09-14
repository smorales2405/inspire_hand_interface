# Réplica de la caracterización del pulgar por Modbus TCP

**Fecha:** 2026-09-14 · DOF 4 (flexión del pulgar) con DOF 5 (rotación) anclado en
`ANGLE_SET 0` ≈ 90°, máxima oposición — la misma postura de la campaña serial.
**Transporte:** Ethernet `192.168.124.210:6000` (721 Hz en lectura cruda, dt p50
0.64 ms). Datos: `exp1/data_dof4_tcp/`, `exp2/data_dof4_tcp{,_onset,_hybrid}/`.
Montaje del bloque: `tcp1` (distinto del `m1`/`m3` de la campaña serial).

**Qué buscaba esta réplica:** la comparativa del índice
([`RESULTADOS_serial_vs_tcp.md`](RESULTADOS_serial_vs_tcp.md)) concluyó que el
transporte no cambia la física pero mejora la adquisición ~7–9×, y anticipaba que
esa resolución resolvería dos cosas que en serial quedaron limitadas por
muestreo: la σ del onset y la captura del pico `F_max`. **Las dos predicciones
resultaron falsas, y esa es la aportación principal de esta réplica.**

## Lo que reproduce

| | Serial | TCP |
|---|---|---|
| Mapa `POS↔ANGLE` (5 paradas) | 245/501/747/928/1103 | **246/500/746/928/1103** |
| Recorrido libre | POS 245–1103 | **245–1104** |
| `k` (ajuste por el origen, `v ≤ 500`) | 2.986 | **3.037** |
| Deadtime medio | 73.1 ms | **77.0 ms** |
| Sobreimpulso de posición | 0.022 % | **0.034 %** |
| Distancia de frenado hasta 100 g | 22–26 counts | **23 counts** |
| ΔF modo A, `v=1000` (`Fset` 100→1000) | 936/1524/1169/1083/1403 g | **890/1551/1366/1020/1544 g** |
| ΔF modo B (mediana por `Fset`) | 17/34/28/36/37 g | **18/23/41/45/46 g** |
| Colapso modo A→B a `v=1000` | 30–55× | **23–67×** |
| Abortos (grid de 175) | 8 | 11 |

El mapa geométrico coincide **dentro de 1 count** un mes y varios montajes
después. Las diferencias por celda de ΔF caen dentro de la variabilidad de
impacto con N=5. **El transporte no cambia la física del dedo**, que es lo que ya
decía la comparativa del índice.

## Tres correcciones

### 1. La σ del onset no era cuantización de muestreo: era recorte

Lo publicado en serial: σ robusta de 10.0 counts «a v=1000 la cuantización de
`POS` por muestra domina la σ medida; la repetibilidad mecánica intra-cluster es
mucho menor».

| | Serial (65 Hz) | TCP (600 Hz) |
|---|---|---|
| σ cruda | 28.8 counts | **40.2** |
| σ «robusta» | 10.0, tras excluir **10 de 50** por IQR | 40.2, **0 excluidos** |
| Rango | 875–965 | 813–972 |
| Salto típico entre valores contiguos | 2 counts | **2 counts** |

A diez veces la tasa la dispersión **sube**, y con la misma regla del IQR no
califica ningún trial como outlier. El salto entre valores ordenados contiguos es
de 2 counts en ambos transportes, así que la cuantización nunca dominó. No había
un núcleo estrecho con outliers de detección: había una distribución ancha a la
que se le cortaban las colas.

**La dispersión del onset es mecánica (~40 counts a `v=1000`) y no se reduce
muestreando más rápido.** El margen de conmutación medido es
`q_sw = ceil(3.3·40.2) = 133 counts`, a 13 counts del default de 120 que se había
fijado por el argumento de que conmutar antes solo cuesta tiempo.

### 2. El retardo de detección tampoco es de muestreo

Onset detectado menos onset geométrico: **+103 counts por TCP, +111 por serial**.
Prácticamente idéntico a 9× la tasa. La explicación publicada —«el margen de
fuerza, las 2 muestras seguidas y la lectura de POS posterior suman ~100 counts a
v=1000»— atribuía el retardo a tres términos de los que **dos son despreciables a
600 Hz** (2 muestras ≈ 3 ms ≈ 9 counts de avance) y el retardo sigue ahí. Lo que
manda es el **umbral de fuerza** (`--onset-margin`, 120 g): el dedo tiene que
comprimir el contacto hasta cruzarlo, y eso cuesta recorrido a cualquier tasa.

### 3. El pico `F_max` no es un transitorio rápido

La comparativa del índice atribuyó a resolución que «en serial el pico rápido
quedaba subestimado/disperso». Medida la anchura real del pico sobre los 175
trials del grid por TCP:

| `v` | anchura por encima de ½·`F_max` | vecino inmediato / pico |
|---|---|---|
| 25 | 486 muestras — 820 ms | 1.00 |
| 250 | 303 muestras — 542 ms | 1.00 |
| 1000 | 70 muestras — 114 ms | 1.00 |

El pico dura **cientos de milisegundos** a todas las velocidades; a 65 Hz se
captan decenas de muestras sobre él. No hay sesgo de captura que corregir, y la
mayor consistencia que se vio en aquel piloto de N=3 era variabilidad de impacto.

**Consecuencia para el filtro `drop_glitches`:** su excepción por velocidad («a
`v ≥ 250` no se filtra nada, porque a ~78 Hz un impacto real cabe en una
muestra») era consecuencia de la tasa, no de la física. Por encima de 200 Hz el
criterio pasa a ser la **anchura** del pico (≤ 2 muestras) y la excepción
desaparece; por debajo no se toca nada, y las campañas serial dan exactamente lo
mismo (verificado celda a celda).

## Dos hallazgos de método

**El asentamiento previo al escalón.** `open_and_settle` daba la pre-posición por
buena con `ANGLE_ACT` en ±6 counts, sin esperar a que `POS_ACT` se quedara
quieto. El firmware aterriza unos counts fuera y sigue reptando, y `ANGLE_ACT`
(0–1000) no tiene resolución para verlo mientras `POS_ACT` (0–2000) sí. A 600 Hz
se ve que POS sube 94→99 **doce ms antes del escalón**, dentro de la ventana de
baseline, y el detector de onset lo toma por el arranque del movimiento: dos de
cinco trials del índice a `v=1000` daban un deadtime de ~1 ms y la σ de la celda
subía a 37.9 ms contra los 8.0 de serial. Corregido exigiendo `POS_ACT` estable;
el baseline del pulgar por TCP queda en 123 muestras **todas en POS 246**.

**`TEMP` cambia de formato con el transporte.** Por RS-485, una temperatura por
registro (las campañas serial registraron 42–44 °C); por TCP, byte-empaquetado
con los tres últimos registros a cero (`1618 = 0x1818` → 24 °C y 24 °C), que es
lo que describe el manual. `read_temps` lo decide por **valor** y no por
transporte. Con eso, el grid registró la subida de **34 a 40 °C** del actuador a
lo largo de los 175 trials — algo que la campaña serial del pulgar no pudo medir.

## Lo que queda abierto

`k` pasa de 2.986 (serial) a 3.037 (TCP) en el mismo dedo. **No es cadencia**:
diezmando las trazas TCP a la cadencia de serial y reajustando con el mismo
analizador, `k` solo baja a 3.021. **No es deriva dentro de la campaña**:
Spearman de la pendiente contra el orden de ejecución no da nada en el tramo
lineal (ρ = −0.09/−0.21/+0.18, p = 0.72/0.38/0.44). Queda como candidato la
pre-posición limpia —el arreglo del asentamiento cambia desde dónde se miden los
niveles 20/80 %— o un cambio real del actuador en el mes transcurrido. Lo
zanjaría una re-corrida por serial con el arreglo puesto.

Las dos campañas pasan el ±5 %, y el efecto práctico es que **el pulgar se aparta
menos de la constante común de lo que sugería la campaña serial**: era el más
alejado de los cinco DOF (−1.8 %) y por TCP es el más cercano (−0.1 %).

## Conclusión

La réplica confirma que el transporte no cambia la física y **desmonta las tres
mejoras de medida que se le habían atribuido**: ni la σ del onset, ni el retardo
de detección, ni la captura del pico estaban limitados por muestreo. Lo que TCP
sí aportó fue hacer visibles dos defectos de método —la pre-posición sin asentar
y el formato de `TEMP`— y permitir medir la anchura real del impacto, que es lo
que ha dejado el filtro de glitches sobre una base física en vez de sobre una
regla empírica atada a 78 Hz.
