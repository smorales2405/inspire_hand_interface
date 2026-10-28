# Experimentos adicionales — diseño y resultados

Revisión de los siete experimentos propuestos, con el diseño que resulta de
cruzarlos con lo ya medido. **Tres cambian de diseño** y **uno no era ejecutable
como estaba propuesto**.

## Reconciliación con la lista real del artículo

La tabla de siete y los `\pending{}` de `07_results.tex` **no coinciden**:

| tabla de siete | artículo | |
|---|---|---|
| #1 segunda consigna | línea 109, **a 0.7 × la fuerza de resbalón** | ✔ coincide con el diseño corregido de abajo |
| #2 tres amplitudes | línea 133, **16 / 28 / 40 u** | ⚠ las unidades valen sólo para el montaje original: el acoplamiento cayó a 0.72 g/u al remontar |
| #3 equivalencia híbrido vs. lento | línea 53, en el **pulgar**, margen **±0.10 N** | ✔ margen ya pre-especificado |
| #4 rigidez del entorno | **no está en el artículo** | fuera de alcance; sería una adición |
| #5 tasa de refresco | línea 18, **los seis actuadores** | ✔ **hecho**: los seis medidos, 30.2–30.4 ms |
| #6 temperatura | **no está pendiente: ya está medido** | 32→42 °C mueve el cero sólo ±0.08 N |
| #7 segunda unidad | línea 109, mano **izquierda** | ✔ |
| — | **Ablación** de refractario, banda y acción integral | **nuevo**, no estaba en la tabla |
| — | **Calibración estática** contra 1.23 y 3.92 N | **nuevo**, y no estaba en la lista enviada |

Dos consecuencias:

- **#6 queda cerrado** por el propio artículo, y de paso explica por qué los
  índices no tenían palanca: el efecto térmico sobre el cero es ±0.08 N, un orden
  por debajo del salto por descarga (−0.45 N en el índice).
- **La calibración estática es el hueco más barato y más grave.** Mientras no
  exista, todas las fuerzas del artículo están en las unidades internas de la
  mano y ningún newton es trazable.

### La ablación es el añadido más fuerte

Los tres términos tienen historia mecanística ya documentada, así que las
predicciones se pueden registrar **antes** de correr:

| término | por qué está | predicción al quitarlo |
|---|---|---|
| **Refractario** (0.20 s) | se añadió porque la primera tanda en hardware se fue a **+90 %** | vuelve el sobreimpulso: el lazo decide antes de ver |
| **Banda muerta** (≈ cuanto del dedo) | **tres** intentos de mejorarla fallaron, todos por repartir mal entre un dedo fino y uno basto | oscilación: se le pide precisión mejor que su escalón mínimo |
| **Acción integral** | estuvo **muerta** hasta A4 por el bug de `dt = 0` | con `Ki = 0` queda error en régimen; el efecto real sólo es medible desde A4 |

---

## #2 · Perturbaciones de magnitud múltiple

**Por qué.** Hasta ahora hay **un solo punto**: 32 u de flexión del soporte →
residual +75 g (firmware) contra +8 g (lazo), p = 0.0088. Un punto no es una
curva, y la contribución del lazo podría depender de esa amplitud concreta.

**Diseño.** Tres amplitudes en **una sola tanda**, con las condiciones
`(brazo × amplitud)` aleatorizadas en bloques balanceados:

| amplitud | ΔF esperado |
|---|---|
| 16 u | ≈ +20 g |
| 28 u | ≈ +43 g |
| 40 u | ≈ +70 g |

Las estimaciones salen del acoplamiento medido: **1.75 g por unidad tras ~8 u de
holgura**. Por debajo de ~12 u la holgura domina y el punto sale degenerado, así
que 16 u es el mínimo útil. A 40 u el pico queda en ~320 g sobre una base de 250,
**bien por debajo del borde de 459 g**.

**N = 8 por condición**, 48 trials, ~68 min desatendido. El N sale de análisis de
potencia sobre los datos existentes (ver abajo), no de una convención.

### Dos cosas que hay que decir en el artículo

**La perturbación sólo tiene autoridad en un sentido.** Flexionar el soporte
carga (+56 g en 32 u, monótono); extender descarga sólo **−23 g en 45 u y
satura** —el bloque no baja con los dedos que se retiran porque lo retiene la
fricción del pulgar—. Así que la curva perturbación→residual sólo se puede
poblar en la rama de **carga**. Un revisor lo preguntará.

**La aleatorización va restringida.** Con el bloque libre, la cola de un bloque
puede alinearse con la cabeza del siguiente: con 3 amplitudes salía una racha de
**5 trials del mismo brazo**, que es lo que obligó a abortar y relanzar la
compuerta A2. `--racha-max 2` lo acota; verificado sobre 5 semillas.

### El acoplamiento depende del montaje — medido, no supuesto

Antes de lanzar la tanda se volvió a medir el acoplamiento soporte→pulgar, porque
`block1` se había desmontado y remontado entremedias. **Se derrumbó a menos de la
mitad:**

| | montaje original | remontaje 2026-10-27 |
|---|---|---|
| Contacto a 250 g | `ANGLE_SET` ≈ 394 | `ANGLE_SET` ≈ 236 |
| Acoplamiento | **1.75 g/u** | **~0.72 g/u** a 40 u |
| 32 u de flexión | **+56 g** | — |
| 40 u de flexión | — | **+29 g** |

Medida completa en el remontaje, punto de trabajo `ANGLE` = 236, *F* = 238 g:

| flexión del soporte | *F* pulgar | Δ | g/u acumulado |
|---|---|---|---|
| −8 u | 240 g | +2 g | 0.25 |
| −16 u | 245 g | +7 g | 0.44 |
| −24 u | 252 g | +14 g | 0.58 |
| −32 u | 260 g | +22 g | 0.69 |
| −40 u | 267 g | +29 g | 0.72 |

Con este acoplamiento las amplitudes del artículo darían **+7 / +18 / +29 g** en
vez de +20 / +43 / +70: **las dos primeras por debajo de la banda muerta de
24 g**. El lazo no tendría que actuar y el contraste contra el firmware
desaparecería. La tanda de 68 min habría salido vacía — este chequeo previo es lo
que lo evitó.

> **Caveat para el artículo, independientemente de cómo se resuelva.** La
> autoridad del actuador de perturbación **depende de la geometría del montaje**:
> 1.75 contra 0.72 g/u entre dos montajes nominalmente iguales del mismo bloque.
> La perturbación hay que especificarla en **ΔF medido**, no en unidades de
> comando, o el experimento no es reproducible. Un revisor que intente replicarlo
> con «40 unidades» no obtendrá la misma perturbación.

Dos salidas: **(a)** reasentar `block1` hasta recuperar el contacto en `ANGLE`
≈ 394 y con él los 1.75 g/u, manteniendo literales las 16/28/40 u del artículo;
o **(b)** escalar las amplitudes en este montaje a ~36/68/105 u para alcanzar los
mismos gramos, lo que obliga a cambiar la línea 133 de `07_results.tex`. Se
prefiere (a), porque el punto único ya publicado (32 u → +75 / +8 g) se midió en
esa geometría y las tres amplitudes sólo son comparables con él si el
acoplamiento coincide.

### Resultados

*Pendiente: la tanda espera a que el acoplamiento quede restaurado.*

---

## #5 · Tasa de refresco por DOF y carga

**Por qué.** El claim «30.7 ms es propiedad de la mano» se apoya hoy en **dos
DOF** (pulgar 30.6–30.7 ms, índice 30.5 ms, desfase −1.9 ms) más el medio bajo
contacto (32.4 ms).

**Lo que gobierna el diseño.** E3.6a dejó la advertencia decisiva: *«los otros
cinco no contestan la pregunta — su `POS` no cambia **ni una vez** en 191 s, y
sus cambios de fuerza son ruido cruzando enteros, no refrescos»*. A un DOF quieto
y descargado **no se le puede medir la rejilla**. Hay que hacerlo producir señal.

**Cuatro condiciones** (`exp4_tasa_refresco.py`):

| | qué hace | qué mide |
|---|---|---|
| `quieto` | todo parado y descargado | el **control**: demuestra que aquí no hay rejilla observable |
| `movimiento` | cada DOF barre despacio, de uno en uno | la rejilla de `POS` por DOF, en vacío |
| `escalonado` | dos o más DOF barren a la vez | el desfase entre ellos |
| `carga` | el pulgar sostiene contra el montaje | la rejilla de `FORCE` bajo carga |

El análisis estima el **periodo base** con los intervalos cortos —los que sí
capturan un solo refresco— y luego comprueba qué fracción del total cae cerca de
un múltiplo entero, porque los intervalos se agrupan en *T*, 2*T*, 3*T*… cuando
el entero se repite.

### El claim honesto es sobre el registro, no sobre el firmware

Lo observable es **cada cuánto cambia el entero publicado**. Un entero repetido
es indistinguible de «no hubo refresco», así que esto **acota la rejilla de
publicación**, no la tasa de muestreo interna del firmware. Escribirlo así o es
atacable.

### Resultados · 2026-10-27 (detalle en `Caracterizacion/exp4/exp4_results.md`)

**En movimiento, sin carga, los seis actuadores:** `POS` **30.2–30.4 ms**
(80–86 % de intervalos en múltiplos enteros) y `CURRENT` **30.2–30.4 ms**
(84–87 %). La dispersión entre los seis es de **0.2 ms, el 0.7 % del periodo**:
la rejilla es de la mano, no de un DOF. Esto convierte el claim de dos DOF en un
claim de seis, que era el objetivo del experimento.

**Escalonado, cinco actuadores a la vez:** periodo común 30.24 ms.
**Índice−pulgar = −1.82 ms contra los −1.85 ms publicados** — replicación
directa. Y aparece un hallazgo nuevo: **el escalonado es monótono a lo largo de
la mano**, ~2.2 ms por actuador (pulgar → índice → medio → anular). Los seis no
se refrescan a la vez, lo hacen en secuencia. El **meñique queda fuera** por
aliasing de envoltura (cuartiles de −11.5 a +10.0, casi un periodo entero).

**Quieto:** `POS` no cambia **ni una vez en 30 s en ninguno de los seis**, lo que
confirma la advertencia de E3.6a. Pero `FORCE` sí da la rejilla incluso quieto
(`T` = 31.1–31.9 ms), porque el entero sólo se reescribe en un instante de
refresco y el ruido que lo cruza queda *muestreado en la rejilla*. E3.6a decía
que esos cambios «no son refrescos»; son ruido, pero llegan **en** los refrescos.

**Bajo carga:** la rejilla aguanta (`T` = 31.4–32.6 ms a 1.4, 2.4 y 3.4 N) pero
`POS` y `CURRENT` **se congelan** y la mediana de `FORCE` sube a 58–61 ms con
sólo 50–58 % de múltiplos.

> **Hay que matizar una frase ya escrita.** El artículo dice que en un hold
> cargado de 3.2–10.6 N la fuerza cambiaba «en casi cada refresco, con mediana de
> 30.4 ms». Eso vale para un hold **regulado**, donde el controlador perturba la
> fuerza cada ciclo; en un hold **estático** a 3.4 N la mediana es 60.5 ms. El
> periodo base no cambia, así que el claim de la rejilla aguanta — lo que necesita
> el calificativo es la mediana.

---

## #1 · Más de una consigna — **el diseño propuesto no era ejecutable**

`F* = 450` cae **dentro de la región de fallo**: en A5 el pulgar **cedió a 459 g**
en ese montaje (pico 575). Una tanda a 450 no mediría regulación, mediría el
detector de resbalón disparando y el lazo aflojando.

Hay un segundo motivo: el brazo del firmware usa `FORCE_SET = F*`, y a consignas
altas su sobreimpulso lo mete en el enclavamiento ya documentado —si `FORCE_ACT`
supera `FORCE_SET`, el dedo deja de aceptar `ANGLE_SET` **en los dos sentidos**—.
A 450 se estaría comparando contra un brazo **bloqueado**, no contra el firmware
funcionando.

**Diseño corregido:** medir el borde en el montaje concreto (`--modo borde`, ya
existe) y fijar `F*₂ ≈ 0.7 × borde`, que con 459 da **≈ 320–350 g**. N = 10 por
brazo, como en A2.

---

## #4 · Rigidez del entorno — **los datos preliminares contradicen la premisa**

| contacto | ganancia del índice |
|---|---|
| bola de espuma | **12.6 g/u** |
| cubo de PLA rígido | **12.2 g/u** |

Casi idénticas, con objetos de rigidez radicalmente distinta. La hipótesis que
sale de ahí es fuerte y es un claim **sobre la mano**: *la compliance dominante
es la de la yema y la transmisión, no la del objeto*.

Eso cambia el diseño: el resultado esperado es **ausencia de efecto**, así que hay
que plantearlo como **equivalencia** con margen definido a priori, no como
búsqueda de diferencia. Si no, se acaba en «p no significativo», que no afirma
nada. Margen natural: **medio cuanto del dedo**, porque diferencias por debajo de
la resolución del actuador no son físicamente distinguibles.

Material disponible: **V-slot de aluminio** (extremo rígido), `block1` (carcasa de
plástico), bola de espuma. Buen contraste.

---

## #6 · Temperatura y deriva — **rediseñado; los datos actuales no pueden responderlo**

Comprobado sobre los índices existentes:

| tanda | valores distintos de temperatura |
|---|---|
| Compuerta A2 | **3** (38–42 °C) |
| Perturbación | **1** (44 °C) |

Las correlaciones con el error salen **r = −0.14 … +0.06**. Eso **no es evidencia
de ausencia de efecto**: es que no hay palanca.

**Y el mecanismo ya se conoce: la mano no se autocalienta sosteniendo porque
consume 0 mA.** El calor viene del movimiento, o sea de las aproximaciones, no de
los sostenimientos. Un experimento de temperatura real tiene que **forzar el ciclo
de trabajo** (muchas aproximaciones seguidas) y medir después si el cero y la
ganancia se desplazan.

**Lo que sí dicen los datos actuales, y conviene reportar:** las correlaciones con
el **orden del trial** son **−0.33 … +0.19**, o sea sin deriva detectable dentro
de una tanda. Eso valida el protocolo de bloques balanceados, y sale gratis.

---

## #3 · Equivalencia híbrido vs. cierre lento

Cheap y defendible si sobra tiempo. El margen de equivalencia **δ_eq debería
derivarse de la resolución del actuador** —medio cuanto, ~12 g en el pulgar— no
elegirse a ojo: diferencias por debajo del escalón mínimo no son físicamente
distinguibles. Ese argumento es más fuerte ante un revisor que cualquier δ
convencional.

---

## #7 · Segunda unidad — **es izquierda, o sea espejo**

No es «repetir el script». El mapeo de DOF y el montaje se invierten, así que
antes de comparar nada hay que **verificar la correspondencia de índices** y
replicar la geometría en espejo. Diferido.

---

## Análisis de potencia — respondido con los datos existentes

| efecto | firmware | lazo | separación | N necesario |
|---|---|---|---|---|
| **Perturbación** (\|err\|) | 59.5 g (IQR 41–64) | 12.5 g (IQR 8–14) | **rangos sin solapar** | **6 / brazo** |
| **Regulación** (\|err\|) | 25.0 g (IQR 19–31) | 11.0 g (IQR 4–18) | con solape | **10 / brazo** |

Con separación completa, la permutación exacta a dos colas tiene p mínima
2/C(2n,n): n=5 da 0.0079 (justo), n=6 da 0.0022 (con holgura). Por eso **N = 8
por condición en #2** (margen sobre 6) y **N = 10 por brazo en #1** (el efecto de
regulación solapa y 10 fue lo que dio p = 0.0074).
