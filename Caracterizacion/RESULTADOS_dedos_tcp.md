# Caracterización por Modbus TCP — meñique, anular y medio

**Fecha:** 2026-09-15 · **Transporte:** `192.168.124.210:6000` (mano derecha).
**Bloque:** el mismo de las campañas anteriores, montaje `tcp1`.
Datos: `exp1/data_dof{0,1,2}_tcp/`, `exp2/data_dof{0,1,2}_tcp{,_hybrid}/`.

Los tres dedos que en la campaña serial solo recibieron **verificación por
muestreo** se re-miden aquí por TCP. El **medio (DOF 2)** lleva el protocolo
completo; anular y meñique, la verificación reducida.

> **Por qué el medio es el que lleva el grid completo.** Es el único de los cinco
> DOF cuyo residual de flexión en el onset (43 g) deja `Fset = 100` **ejecutable
> con margen**. En el índice esa columna salió vacía —el dedo frenaba en el aire
> sin llegar al objeto— y en el meñique el ajuste ni siquiera es pedible (117 g
> de residual). Sin un dedo que llegue de verdad al objeto con el umbral más
> bajo, esa columna no se podía medir en ninguna parte.

## El bloque rígido no se pudo usar

Se intentó montar un bloque **más rígido**, para que no cediera al ser golpeado a
alta velocidad. **No alcanza**: a ninguna posición montable la yema lo tocaba
antes del final de su recorrido. En el medio el contacto caía en `POS 1884` con
el tope libre en **1916** —32 counts de margen, el dedo casi cerrado— y a esa
flexión su propio residual vale ya **148 g**, lo que dejaba `Fset = 100`
inejecutable: exactamente el problema que este dedo venía a resolver. El sondeo
queda como `exp2/data_dof2_tcp/probe_dof2_rig1.csv`.

Se volvió al bloque anterior. **Consecuencia:** esta campaña no mejora la rigidez
del contacto, y sus ΔF arrastran la misma reserva que las anteriores — el montaje
cede algo al impacto, así que son **cotas inferiores**.

---

# Medio (DOF 2) — protocolo completo

## T0 · geometría del contacto

| | TCP `tcp1` | Serial (mismo bloque) |
|---|---|---|
| Recorrido libre | POS 96–1916 | 91–1913 |
| Onset geométrico | **POS 1466** (`ANGLE_SET 289` ≈ 65°) | 1467 |
| `k_c` | **12.11 g/count** | 11.7 |
| Residual en el onset | **43 g** → `Fset` mín ~73 g | 30 g |
| Distancia de frenado a 100 g | **25 counts** | 11 |
| `--start-angle` | **445** (residual medido 3 g) | 445 |
| `--approach-angle` | **364** | 363 |

El onset reproduce el de serial **dentro de 1 count**, un mes, un transporte y
varios montajes después. `k_c` coincide. Celda de validación `v=250, Fset=500`:
`F_max` 1869 g, 1866 g de fuerza externa, 0 abortos.

> **Los `d_100` de las campañas serial están sesgados a la baja.** Aquí salen 25
> counts contra los 11 de serial, y no es el dedo: la curva libre de serial
> situaba el onset con la fuerza externa ya en 78 g, y la de TCP lo coge en
> **−4 g** (3093 muestras contra 406, así que el residual se interpola mucho
> mejor). Ninguna conclusión cambia —25 counts sigue lejos de los ~220 que se
> atribuyeron al índice— pero el número bueno es el nuevo.

## T1 · respuesta al escalón (5 velocidades × 20)

| Criterio | Valor | |
|---|---|---|
| `k` (ajuste por el origen, `v ≤ 500`) | **3.023** (−0.5 % vs 3.04) | PASA |
| R² mínimo en `v ≤ 500` | 0.9946 | PASA |
| Deadtime medio | 76.5 ms | PASA |
| Sobreimpulso de posición | 0.048 % máx | PASA |

> **Aporta al pendiente del pulgar.** En el pulgar `k` saltó 2.986 (serial) →
> 3.037 (TCP) y quedó sin explicar; uno de los candidatos era el arreglo de la
> **pre-posición asentada**, que afectaría a todos los dedos por igual porque las
> campañas serial se corrieron sin él. En el medio ese salto **no aparece**:
> 3.013 → 3.023, +0.3 % contra el +1.7 % del pulgar. Es un solo dedo y la
> diferencia cabe en la dispersión conocida, pero **empuja hacia la otra
> hipótesis**: que lo del pulgar sea propio de ese actuador y no un artefacto de
> método.

## T2 · grid modo A (7 velocidades × 5 `Fset` × 5)

ΔF mediana (g). `*` = celda con ≥1 aborto (pico sobre el techo de 2200 g).

| v \ `Fset` | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| 25 | 26 | 96 | 109 | 122 | 181 |
| 50 | 59 | 215 | 249 | 215 | 356 |
| 100 | 115 | 426 | 437 | 224 | 441 |
| 250 | 363 | 1723 | 838 | 1482* | 1236* |
| 500 | 1741* | 1574* | 2539* | 2454* | 2285* |
| 750 | 2797* | 2767* | 2581* | 2118* | 2204* |
| 1000 | **3453*** | 3312* | 3010* | 2784* | 2528* |

175 trials · **76 abortos** · 0 descartes de los filtros · **0 trials sin
contacto**. Temperatura del actuador 50 → 52 °C.

### El hallazgo: con el umbral más bajo el golpe es el más fuerte

Los 35 trials de la columna `Fset = 100` **tocaron todos el objeto** (fuerza
externa mínima 119 g, `f_settle` mínimo 59 g). Es la **primera columna
`Fset = 100` completa y válida** del proyecto.

Y no dice «el umbral bajo no protege», dice algo más fuerte: a `v = 1000`,
`Fset = 100` da **3453 g — el valor más alto de todo el mapa**. Bajar el umbral
**no reduce** el impacto; a alta velocidad lo empeora. La lectura física es que
el umbral solo manda mientras el dedo va lo bastante despacio para que el
firmware alcance a frenar. Pasado ese punto lo único que queda es el momento en
el instante del contacto — y con el umbral bajo el dedo llega ahí habiendo
acelerado más recorrido, porque el firmware no lo frena antes.

## T3 · modo B (aproximación rápida + cierre a `v=25`)

| `Fset` | Modo A `v=1000` | Modo B | Colapso |
|---|---|---|---|
| 100 | 3453 g | **18 g** | **192×** |
| 250 | 3312 g | 86 g | 39× |
| 500 | 3010 g | 108 g | 28× |
| 750 | 2784 g | 110 g | 25× |
| 1000 | 2528 g | 241 g | 10× |

25 trials, **0 abortos**, todos con contacto (externa mínima 121 g).

La conmutación de velocidad vuelve a funcionar, y su ventaja es **máxima
justo donde el umbral bajo es peor**: 192× a `Fset = 100`. Las dos mitades del
argumento encajan — el umbral no es una palanca de seguridad, la velocidad sí.

## Comparativa a `v = 1000` (ΔF mediana, g)

| | 100 | 250 | 500 | 750 | 1000 |
|---|---|---|---|---|---|
| **Medio** (TCP, `tcp1`) | **3453** | 3312 | 3010 | 2784 | 2528 |
| Pulgar (TCP, `tcp1`) | 890 | 1551 | 1366 | 1020 | 1544 |
| Índice (serial) | 295 † | 3263 | 2917 | 2865 | 2502 |

† Del índice solo sobrevive un trial en esa celda: el resto de su columna
`Fset=100` nunca llegó al bloque. Ver `exp2/exp2_results.md`.

Medio e índice —dos dedos de la misma familia mecánica— dan magnitudes muy
parecidas para `Fset ≥ 250`. El pulgar se queda en la mitad o menos, como ya
decía su campaña: menos inercia en movimiento.

---

# Anular (DOF 1) — verificación reducida

## V0 · geometría del contacto

| | TCP `tcp1` | Serial (mismo bloque) |
|---|---|---|
| Recorrido libre | POS 60–1842 | 61–1842 |
| Onset geométrico | **POS 1417** (`ANGLE_SET 282` ≈ 64°) | 1414 |
| `k_c` | **14.61 g/count** | 17.0 |
| Residual en el onset | **64 g** → `Fset` mín ~94 g | 50 g |
| `--start-angle` | **441** (residual medido 31 g) | 443 |
| `--approach-angle` | **359** | 360 |

Otra vez el onset cae donde la campaña serial, dentro de 3 counts. Celda de
validación `v=250, Fset=500`: `F_max` 1233 g, 1202 g de fuerza externa, 0 abortos.

> **El primer sondeo llegó al techo de fuerza** (603 g contra el techo de 550)
> antes de que el `POS` se detuviera, así que no dio `k_c`. Se repitió con
> `--probe-ceiling 750`. El onset se movió 1413 → 1417 entre los dos, 4 counts,
> que es la resolución esperable (ver abajo).
>
> **`d_100` no se puede medir en este contacto.** Sale 0 counts, y hay que leerlo
> como «por debajo de la resolución», no como cero: la mano publica estado nuevo
> cada 30.7 ms, así que a `v=50` el dedo avanza ~4.6 counts entre refrescos y,
> con `k_c ≈ 15 g/count`, la fuerza salta ~67 g de una muestra a la siguiente.
> La primera muestra que cruza el umbral de detección ya marca 104 g. Ningún
> transporte arregla esto; un sondeo a `v=25` daría el doble de resolución si
> hiciera falta el número.

## V1 · respuesta al escalón (`v` = 250, 500 × 10)

| Criterio | Valor | |
|---|---|---|
| `k` (ajuste por el origen) | **3.022** (−0.6 % vs 3.04) | PASA |
| R² mínimo | 0.9946 | PASA |
| Deadtime medio | 78.1 ms | PASA |
| Sobreimpulso de posición | 0.042 % máx | PASA |

Serial dio 3.012 en este dedo: **+0.3 %**, el mismo desplazamiento pequeño que el
medio, y muy lejos del +1.7 % del pulgar.

## V2 · modo B

| `Fset` | ΔF mediana | Rango | Externa mínima | |
|---|---|---|---|---|
| 100 | **40 g** | 35–52 | 128 g | PASA (≤ 100) |
| 1000 | **195 g** | 58–238 | 1031 g | **no cumple** (≤ 150) |

10 trials, 0 abortos, todos con contacto.

> **El criterio de `Fset=1000` no se cumple, y hay que decirlo.** 195 g contra el
> umbral de 150 que se fijó en la campaña serial. Pero ese umbral se calibró
> sobre la mediana del índice (92 g), y **el rango del índice era 7–241** con
> N=5: el del anular es 58–238. Con cinco trials por celda los dos solapan casi
> por completo, así que esto **no establece** que el modo B funcione peor aquí —
> establece que N=5 no distingue. El medio, con protocolo completo, dio 241 g en
> esa misma celda y un colapso de 10× frente al modo A. Para zanjarlo haría falta
> subir el N de esa celda, como se hizo en su día con la fila `Fset=100` del
> pulgar.

## V3 · pruebas adicionales sobre el anular

### La distancia de frenado, por fin medida: **6 counts**

| Sondeo | `v` | Onset | `F` en el onset | `k_c` | `d_100` |
|---|---|---|---|---|---|
| `tcp1` | 50 | 1417 | 104 g | 14.61 | **0** |
| `tcp1v25c` | 25 | 1411 | **12 g** | 16.63 | **6** |

El 0 era resolución, no física. A `v=50` la primera muestra que cruza el umbral
de detección ya marca 104 g, así que los 100 quedan detrás; a `v=25` el onset se
coge en 12 g y el número aparece. Hizo falta además subir `--contact-force-g`,
porque el sondeo abre en cuanto declara contacto y se paraba en 80 g externos.

Con 6 counts el anular es **el contacto más rígido medido** (medio 25, pulgar
23–31, índice ~15).

### Modo A, columnas `Fset` = 100 y 1000 (7 velocidades × 5)

| v \ `Fset` | 100 | 1000 |
|---|---|---|
| 25 | 38 | 101 |
| 50 | 71 | 362 |
| 100 | 136 | 498 |
| 250 | 431 | 1035* |
| 500 | 764 | 1250* |
| 750 | 2210* | 2368* |
| 1000 | **2619*** | 1615* |

70 trials · 24 abortos · 0 trials sin contacto · 1 descarte por lectura corrupta
(`v=500, Fset=100`, `F_max` 2533 g con vecinos ≤ 1 g).

**El hallazgo del medio replica.** A `v = 1000` el umbral más bajo vuelve a dar
el golpe más fuerte: **2619 g con `Fset=100` contra 1615 con `Fset=1000`**, 1.6×
peor. En el medio fue 3453 contra 2528, 1.4×. Dos dedos independientes, misma
dirección: **bajar el umbral de fuerza empeora el impacto a alta velocidad**.

### ¿Entrega el modo B el rendimiento del cierre lento? — **sí**

Medido con `--ab` (tanda única, políticas intercaladas, aleatorización por
bloques balanceados) en **las dos poses de contacto**, `Fset = 1000`, N=10 por
brazo, 0 abortos, 0 trials sin contacto:

| Pose | Onset | Modo A (cierre lento) | Modo B (aprox. rápida) | Δ | p |
|---|---|---|---|---|---|
| Borde (`tcp3`) | POS 1411 | 208 g | 157 g | −50 g | 0.35 |
| Cara plana (`tcp2`) | POS 1720 | 228 g | 194 g | −34 g | 0.195 |

**No hay diferencia detectable en ninguna de las dos**, y ambas apuntan
levemente a que el modo B es *mejor*. El modo B hace lo que promete: entrega el
rendimiento del cierre lento sin pagar su tiempo de aproximación.

### Por qué hizo falta llegar hasta aquí

Esta sección se equivocó tres veces antes de esto, y el historial importa porque
cada error tenía una causa distinta.

**El hallazgo inicial fue un artefacto de comparar tandas separadas.** Sobre la
pose de borde, en tandas distintas, dio modo B 193 g contra modo A 100 g con
p = 0.0025. Con el diseño intercalado **en esa misma pose y ese mismo bloque**,
el modo A da **208 g**. Lo que se movió no fue el modo B (193 → 157) sino el
**modo A: 100 → 208**, el doble.

La causa no fue que el bloque cambiara de sitio: el usuario precisó que se
**inclinaba** durante el contacto y volvía a su posición, que es compliancia
elástica y no deriva. La tanda del modo A se corrió justo después del grid de 70
trials con 24 abortos, con el actuador caliente; el `forceClb` deriva ~40 g por
minuto según ya documenta este repo, y `ΔF = F_max − Fset` hereda cualquier
sesgo del cero. Un cero desplazado a la baja produce exactamente un ΔF bajo.

**Y la retractación intermedia midió mal.** Se cuantificó la deriva del bloque
con el campo `onset_pos`, que **no es la posición del contacto**: es donde
dispara el detector de umbral del trial sobre la subida del residual de flexión,
y sigue a la pre-posición —

| Campaña | Política | `start POS` | `onset_pos` | Δ |
|---|---|---|---|---|
| Tanda A/B (cara plana) | A | 1468 | 1520 | +53 |
| Tanda A/B (cara plana) | B | 1603 | 1654 | +51 |
| Modo B margen 120 | B | 1297 | 1409 | +112 |
| Grid + modo A `v=25` | A | 1168 | 1341 | +173 |

— así que los «68 counts de deriva» eran la diferencia de pre-posición entre las
dos campañas (1297 contra 1168), no movimiento del bloque.

**También cae la hipótesis de la pose.** Con el modo A en 208 y 228 g en las dos
poses (y no en 100 y 228), la «ventaja del cierre lento que desaparece al
flexionar» no existe.

**Lo que queda, entonces:**

- El modo B entrega el rendimiento del cierre lento. **El margen de conmutación
  de 120 counts no está implicado**, y la mitigación central de la tesis no
  necesita revisión.
- El `Fset = 1000` en modo B sobre este dedo ronda los 157–194 g, por encima del
  criterio de ≤ 150 g fijado con el índice — pero el cierre lento puro tampoco lo
  cumple (208–228 g), así que **el criterio describe al índice, no al modo B**.
- **Comparar políticas exige una tanda intercalada.** Dos tandas separadas del
  mismo dedo, mismo bloque y misma pose difieren en un factor 2 por sí solas.

**Reproducibilidad del montaje:** la pieza de borde, desmontada y vuelta a montar,
volvió a `POS 1411` contra los 1410–1417 de antes — dentro de un count. Y la
pieza de cara plana derivó 1 count (1720 → 1721) a lo largo de su tanda.

> **Nota de método para todo el repo:** `onset_pos` en los índices de trial es un
> **cruce de umbral**, no una posición de contacto. Sirve para comparar trials
> que arrancan del mismo sitio; no para comparar campañas con pre-posiciones
> distintas, ni como medida de geometría. Para eso está el onset geométrico del
> sondeo.

## Estado

| Dedo | T0 | T1 | T2 grid | T3 modo B |
|---|---|---|---|---|
| Medio (2) | ✔ | ✔ | ✔ | ✔ |
| Anular (1) | ✔ | ✔ | — | ✔ |
| Meñique (0) | ☐ | ☐ | — | ☐ |
