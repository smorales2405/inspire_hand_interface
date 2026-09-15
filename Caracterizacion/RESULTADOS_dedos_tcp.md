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

### ⚠ RETRACTADO — el bloque se movió y confunde toda la comparación modo A / modo B

El usuario señaló que la punta del anular golpea el **borde superior** del bloque
y que el momento del dedo lo mueve un poco. Comprobado con el `onset_pos` que
cada trial registra, en orden cronológico real:

| Campaña | N | Onset mediana | Rango |
|---|---|---|---|
| Modo B, margen 120 | 25 | **1409** | 1406–1412 |
| Grid + modo A `v=25` | 25 | **1341** | 1315–1404 |
| Modo B m250, llegada 1000 | 5 | 1361 | 1341–1371 |
| Modo B m250, llegada 300 | 4 | 1365 | 1354–1369 |

**El bloque se desplazó 68 counts durante la sesión**, y lo hizo durante el grid
de 70 trials con 24 abortos. El modo B con margen 120 se midió **antes** (bloque
quieto: rango de 6 counts) y el modo A `v=25` **después** (bloque moviéndose:
rango de 89 counts, más de diez veces mayor).

Así que la diferencia «modo B 193 g contra modo A 100 g, p = 0.0025» **no separa
las dos políticas**: separa dos estados del montaje. Quedan retractadas las tres
conclusiones encadenadas de esta sección:

1. ~~el modo B es 2× peor que el cierre lento~~;
2. ~~ampliar el margen de conmutación no lo arregla~~;
3. ~~la causa es la velocidad de aproximación~~.

Los números están medidos y los CSV valen; lo que no vale es el contraste entre
tandas. (El brazo con llegada a 300 dio mediana 112 g contra 164 del de llegada
a 1000, que es **consistente** con la tercera hipótesis — pero ambos con N≤5 y con
el bloque ya desplazado, así que no la sostiene.)

**Lo que sí queda en pie:** el modo B con margen 120 y N=20 da **193 g con el
bloque quieto** (onset 1406–1412), y eso es una medida limpia. No cumple el
criterio de ≤ 150 g. Lo que no se puede decir es *por qué*.

### La lección de método: comparar dentro de una tanda aleatorizada

El grid **sí** aguanta esta deriva. Sus 70 trials se barajan **juntos**
(`random.Random(seed).shuffle`), así que un montaje que se mueve durante la
campaña afecta a las dos columnas por igual y la comparación `Fset=100` vs
`Fset=1000` sigue siendo válida. La réplica del hallazgo del medio **se mantiene**.

Mis comparaciones ad-hoc no tenían esa protección: eran tandas separadas,
ejecutadas en momentos distintos, con impactos duros de por medio. Esa es
exactamente la diferencia entre un diseño aleatorizado y una comparación
oportunista, y aquí ha costado tres conclusiones.

> Dentro del grid, el ΔF a `v=1000` no muestra dependencia significativa de la
> posición del bloque (Spearman ΔF vs `onset_pos`: ρ = −0.30, p = 0.69 en
> `Fset=100`; ρ = −0.83, p = 0.13 en `Fset=1000`), aunque con N=5 por celda eso
> es poco poder. La aleatorización es la que protege el resultado, no este test.

### Cómo se contestaría bien la pregunta del modo B

Una tanda **única y aleatorizada** que alterne modo A `v=25` y modo B, con sondeo
antes y después para cuantificar la deriva. Sin eso, cualquier diferencia entre
políticas medidas en momentos distintos es indistinguible del montaje. Y en este
dedo hace falta además revisar el contacto: golpear el **borde** del bloque en vez
de una cara plana es lo que le da el `k_c` más alto del conjunto (16.6 g/count) y
lo que lo hace moverse.

## Estado

| Dedo | T0 | T1 | T2 grid | T3 modo B |
|---|---|---|---|---|
| Medio (2) | ✔ | ✔ | ✔ | ✔ |
| Anular (1) | ✔ | ✔ | — | ✔ |
| Meñique (0) | ☐ | ☐ | — | ☐ |
