# Exp 4 — Tasa de refresco de los registros, por DOF y por carga

Experimento añadido para el envío a *Mechatronics* (ver
[`../../Journal/experimentos_adicionales.md`](../../Journal/experimentos_adicionales.md), #5).

Verifica si los **~30.7 ms** son una propiedad común de la mano o un hallazgo de
los dos DOF donde se midió.

## Qué había antes

| fuente | medida |
|---|---|
| E3.6a | pulgar **30.6 / 30.7 ms**, índice **30.5 ms**, desfase **−1.90 / −1.80 ms** |
| E3.2 (17 581 muestras, 191 s) | medio bajo contacto sostenido: `POS` cambia cada **32.4 ms** |

## La advertencia que gobierna el diseño

E3.6a dejó escrito que **los otros cinco DOF no contestan la pregunta**: su `POS`
no cambia **ni una vez** en 191 s, y sus «cambios» de fuerza son **ruido cruzando
enteros**, no refrescos. El desfase aparente de +0.00 ms del DOF 3 en aquella
tanda es artefacto de eso — con instantes de ruido densos, cualquier referencia
encuentra coincidencia.

**Conclusión de método: a un DOF quieto y descargado no se le puede medir la
rejilla.** Hay que hacerlo producir señal. De ahí las cuatro condiciones.

## Condiciones

| | qué hace | qué mide |
|---|---|---|
| `quieto` | todo parado y descargado | el **control**: demuestra que aquí no hay rejilla observable |
| `movimiento` | cada DOF barre despacio (`v=12`), de uno en uno | la rejilla de `POS` por DOF, en vacío |
| `escalonado` | varios DOF barren a la vez | el **desfase** entre ellos |
| `carga` | el pulgar sostiene ~250 g contra el montaje | la rejilla de `FORCE` bajo carga |

El sondeo corre a ~250–380 Hz contra una rejilla esperada de ~32.6 Hz, o sea
**8–12× de sobremuestreo**.

## Cómo se estima el periodo

Los intervalos entre cambios **se agrupan en *T*, 2*T*, 3*T*…**, porque un entero
que se repite esconde un refresco. El estimador:

1. periodo base *T* = mediana de los intervalos **cortos** (≤ 1.5 × mediana), que
   son los que capturan un solo refresco;
2. validación: qué fracción de **todos** los intervalos cae a ±15 % de un múltiplo
   entero de *T*.

Una fracción alta confirma la rejilla; una baja significa que lo que se está
midiendo no es un refresco periódico.

## El claim honesto

Lo observable es **cada cuánto cambia el entero publicado**. Un entero repetido es
indistinguible de «no hubo refresco», así que esto **acota por arriba la rejilla
de publicación del registro** — no mide la tasa de muestreo interna del firmware.
El artículo tiene que decirlo así.

## Uso

```bash
# control: nada se mueve, nada carga
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion quieto --dur 30

# la rejilla por DOF, en vacio (el pulgar exige anclar la rotacion)
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion movimiento --dofs 0,1,2,3 --dur 25
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion movimiento --dofs 4 --rot 0 --dur 25

# el desfase entre DOF
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion escalonado --dofs 3,2,1 --dur 30

# bajo carga (exige block1 montado sobre las falanges)
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion carga --dofs 4 --rot 0 --dur 40
```

## Resultados · parciales (2026-10-27)

`block1` montado sobre las falanges, así que **los cuatro dedos cargan su peso**
(77 g meñique, 183 g anular con la mano abierta). El pulgar y la rotación sí
están libres. Lo medido hasta ahora es por tanto: el control con todo quieto, y
los dos DOF que el montaje no carga.

### Control · todo quieto, 30 s

| DOF | `POS` cambios | `FORCE` cambios | `T` base | mediana |
|---|---|---|---|---|
| Meñique | **0** | 210 | 31.2 ms | 61.9 ms |
| Anular | **0** | 157 | 31.9 ms | 61.8 ms |
| Medio | **0** | 352 | 31.3 ms | 55.9 ms |
| Índice | **0** | 154 | 31.5 ms | 59.8 ms |
| Pulgar flex. | **0** | 231 | 31.2 ms | 58.8 ms |
| Pulgar rot. | **0** | 234 | 31.1 ms | 59.4 ms |

**`POS` no cambia ni una vez en ninguno de los seis**, como E3.6a había
anticipado. Pero **`FORCE` sí da la rejilla**: `T` base **31.1–31.9 ms** en los
seis, y mediana **55.9–61.9 ms**, que reproduce los 59.6 ms que el artículo ya
reporta en vacío.

> **Esto matiza E3.6a.** Decía que los cambios de fuerza de un dedo quieto son
> «ruido cruzando enteros, **no refrescos**». Son ruido, sí — pero el registro es
> un entero que **sólo se reescribe en un instante de refresco**, así que el ruido
> está *muestreado en la rejilla* y los intervalos siguen llevando el periodo. Lo
> que no sirve con el dedo quieto es `POS`, porque no cambia nunca.

### En movimiento, sin carga · los SEIS actuadores · 25 s, `v = 12`

Cero aplicado con la mano abierta antes de empezar.

| DOF | `POS` | `CURRENT` | `FORCE` |
|---|---|---|---|
| Meñique | **30.4 ms** (82 %) | **30.2 ms** (87 %) | 36.7 ms (**24 %**) |
| Anular | **30.3** (81 %) | **30.3** (84 %) | 30.2 (81 %) |
| Medio | **30.2** (81 %) | **30.3** (86 %) | 31.8 (71 %) |
| Índice | **30.2** (81 %) | **30.2** (85 %) | 32.6 (54 %) |
| Pulgar flex. | **30.3** (80 %) | **30.3** (85 %) | 31.3 (66 %) |
| Pulgar rot. | **30.3** (86 %) | **30.4** (86 %) | 30.4 (82 %) |

**`POS` y `CURRENT` dan 30.2–30.4 ms en los seis**, con 80–87 % de los intervalos
en múltiplos enteros. La dispersión entre actuadores es de **0.2 ms, el 0.7 % del
periodo**: la rejilla es de la mano, no de un DOF concreto.

**`FORCE` es el registro poco fiable en vacío** (24–82 %, hasta 36.7 ms en el
meñique), y es coherente con lo que el artículo ya reporta: sin carga el entero se
repite y la mediana se duplica. El claim debe apoyarse en `POS` y `CURRENT`.

> **Un fallo de método corregido sobre la marcha.** La primera versión leía
> `CURRENT` una de cada 8 iteraciones, o sea a ~39 Hz contra una rejilla de ~32:
> **1.2× de muestreo**. Así salía `T` = 27.6 ms con sólo **60 %** de múltiplos.
> Leyéndolo en cada iteración —el sondeo baja a ~226 Hz, aún 7× la rejilla— sale
> 30.3 ms y **85 %**. Submuestrear el registro que se quiere medir invalida el
> intervalo.

### Escalonado · cinco actuadores a la vez

Periodo común **30.24 ms**, los cinco barriendo simultáneamente, `POS` con 83–85 %
de múltiplos. Desfase respecto al **pulgar**:

| | mediana | cuartiles | n |
|---|---|---|---|
| **Índice** | **−1.82 ms** | −3.50 / −0.73 | 703 |
| Medio | −4.22 ms | −10.24 / −2.72 | 736 |
| Anular | −7.54 ms | −11.49 / −3.81 | 649 |
| Meñique | −6.91 ms | −11.47 / **+9.97** | 760 |

**Índice−pulgar sale −1.82 ms contra los −1.85 ms publicados** (IQR 1.25–3.09,
341 refrescos): replicación directa.

Y aparece algo que no estaba: **el escalonado es monótono a lo largo de la mano**
—pulgar, índice, medio, anular— a razón de **~2.2 ms por actuador**. Los seis no
se refrescan en el mismo instante; lo hacen en secuencia.

> **El meñique no es de fiar.** Rompe la monotonía (−6.91 contra los −7.54 del
> anular) y sus cuartiles van de −11.5 a **+10.0**, casi un periodo entero. Con
> `T` = 30.24 ms, un desfase de −6.91 es indistinguible de **+23.33**: es
> aliasing de envoltura, no una medida. Hace falta otra tanda antes de publicarlo.

Un par adicional, medido con `block1` aún montado: **rotación−flexión del pulgar
= +1.98 ms** (cuartiles +1.24 / +5.80, n = 505), periodo común 30.28 ms.

### Bajo carga · el pulgar sosteniendo contra `block1`, 40 s

Tres niveles de fuerza, cada uno un hold **estático** —`ANGLE_SET` fijo, sin
regulador— con el pulgar apretando el bloque:

| hold | `FORCE` cambios | tasa | `T` base | mediana | q1 / q3 | múltiplos | `POS` | `CURRENT` |
|---|---|---|---|---|---|---|---|---|
| **145 g** (1.4 N) | 245 | 6.3 Hz | 32.6 ms | 61.3 ms | 31.1 / 155.1 | 50 % | **1** cambio | **0** |
| **244 g** (2.4 N) | 198 | 5.1 Hz | 31.4 ms | 58.3 ms | 30.4 / 145.5 | 58 % | **3** | **3** |
| **345 g** (3.4 N) | 192 | 5.0 Hz | 31.6 ms | 60.5 ms | 30.9 / 148.1 | 55 % | **0** | **0** |

El **periodo base se mantiene en 31.4–32.6 ms** en los tres, consistente con la
rejilla que dan `POS` y `CURRENT` en movimiento (30.2–30.4 ms). La rejilla no
depende de la carga.

> **Esto obliga a matizar una frase del artículo.** Dice que *«durante un hold
> cargado de 3.2–10.6 N la fuerza cambiaba en casi cada refresco, con un
> intervalo mediano de 30.4 ms»*. A 3.4 N —dentro de ese rango— el hold
> **estático** da mediana **60.5 ms** y sólo **55 %** de múltiplos: el entero se
> repite la mitad de las veces. Los 30.4 ms salen de holds **regulados**, donde
> el controlador mueve la consigna y perturba la fuerza en cada ciclo, así que el
> entero casi nunca se repite.
>
> La distinción no es cosmética: **«cambia en casi cada refresco» es una
> propiedad del lazo activo, no del hold cargado**. El claim sobre la rejilla
> —31.6 ms de periodo base— aguanta en ambos casos; el que necesita el
> calificativo es el de la mediana.

También conviene notar que `POS` y `CURRENT` **se congelan** durante el hold
estático (0–3 cambios en 40 s). Con el dedo bloqueado contra el montaje no hay
desplazamiento ni cambio de par que cruce un entero, así que en esta condición el
único registro que mide la rejilla es `FORCE` — justo al revés que en movimiento.

### Pendiente

- **Repetir el meñique** en el escalonado, para resolver la ambigüedad de envoltura.
- **Repetir un hold bajo regulador** para confirmar que ahí sí sale la mediana de
  30.4 ms, y cerrar así la frase del artículo con sus dos casos medidos.
