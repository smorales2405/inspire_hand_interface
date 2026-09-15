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

## Estado

| Dedo | T0 | T1 | T2 grid | T3 modo B |
|---|---|---|---|---|
| Medio (2) | ✔ | ✔ | ✔ | ✔ |
| Anular (1) | ☐ | ☐ | — | ☐ |
| Meñique (0) | ☐ | ☐ | — | ☐ |
