# Exp 3 — Régimen de contacto sostenido · resultados

Plan: [`../EXP3_regimen_contacto_sostenido.md`](../EXP3_regimen_contacto_sostenido.md).
Transporte TCP `192.168.124.210:6000`. Montaje: **`block1`** (la fuente de
alimentación, contacto sobre arista — ver [`../MONTAJES.md`](../MONTAJES.md)),
remontado para esta serie y re-sondeado: onset **POS 1487**, residual 45 g.

---

## Prerrequisito §3 — El índice, completo por fin

El índice era el DOF peor caracterizado: `k_c` de 1.6 a 8.45 g/count según cómo se
mirara, onset fijado a ojo, y el único sin curva libre propia en el pipeline. Con
los modos de agarre 1 y 2 pasa a ser la mitad del par en oposición, así que dejó
de ser un pendiente y se convirtió en bloqueante.

| | Valor |
|---|---|
| Recorrido libre | POS **99 … 1913** (serial dio 98–1913) |
| Onset geométrico (montaje `e3`) | POS **1448** (`ANGLE_SET 298` ≈ 66.5°) |
| `k_c` | **12.44 g/count** |
| Distancia de frenado a 100 g | **14 counts** |
| Residual en el onset (curva fría) | 79 g |
| `--start-angle` / `--approach-angle` | **452 / 372** |
| Validación `v=250, Fset=500` | `F_max` 1351 g · 1260 g externos · 0 abortos |

**El re-análisis del sondeo archivado se sostiene.** Contra la curva libre nueva da
onset 1416 y `k_c` 8.28; contra la vieja, 1416 y 8.45. La distancia de frenado sale
**15 counts** contra los **14** del sondeo nuevo — en otro montaje y nueve días
después. Ese número es el sólido del índice; el `k_c` arrastra la dispersión de
siempre (dónde caiga la muestra del onset respecto al refresco de 33 Hz).

### El residual no se puede predecir de la curva libre

La curva libre se mide **con el dedo en movimiento**; el `f_base` del regulador se
mide **con el dedo parado** en la pre-posición. No coinciden, y la diferencia no es
pequeña ni consistente:

| Dedo | POS | Curva libre | `f_base` medido | Δ |
|---|---|---|---|---|
| Índice | 1200 | 18 g | **91 g** | **+73** |
| Medio (`block1`) | 1237 | 7 g | 3 g | −4 |
| Medio (`block2`) | 1481 | 45 g | 122 g | +77 |
| Anular | 1169 | 33 g | 36 g | +3 |
| Meñique | 1481 | 85 g | 122 g | +37 |

**Consecuencia directa para el regulador: el piso de `F*` hay que medirlo en la
pose de operación, no derivarlo de la curva libre.** La curva sirve para detectar
el contacto (es una diferencia entre dos corridas y los sesgos se cancelan); no
sirve para predecir cuánta fuerza propia tendrá el dedo parado ahí.

> **Corrección.** En el commit anterior atribuí a la **temperatura** los ~60 g de
> diferencia entre la curva libre del índice tomada en frío (32 °C) y la de la
> campaña serial. Con esta tabla, la explicación **estático-vs-movimiento** da
> igual de bien y probablemente mejor, porque aparece dentro de una misma sesión y
> con la mano igual de fría. Las dos siguen siendo candidatas y están confundidas;
> **E3.5 puede separarlas** midiendo el residual estático a varias temperaturas.

---

## E3.2 — Incremento mínimo efectivo · DOF 2 (medio), `F₀ = 250 g`

100 trials (5 incrementos × 2 sentidos × N=10), orden aleatorizado, 0 abortos.
Contacto establecido en **256 g** (`POS 1502`, comando `ANGLE_SET 266`).
Temperatura 42 → 44 °C.

| Paso | Sentido | Movió | Δpos mediana | ΔF mediana | ΔF mínimo | g/unidad |
|---|---|---|---|---|---|---|
| 1 | cerrar | **10/10** | 3.0 | +41 g | +32 | 41 |
| 1 | abrir | **4/10** | 0.0 | +0 g | +0 | — |
| 2 | cerrar | 10/10 | 4.0 | +59 g | +44 | 30 |
| 2 | abrir | **6/10** | −1.0 | −69 g | +0 | 34 |
| 3 | cerrar | 10/10 | 6.5 | +171 g | +114 | 57 |
| 3 | abrir | 10/10 | −2.5 | −72 g | −39 | 24 |
| 5 | cerrar | 10/10 | 8.0 | +304 g | +170 | 61 |
| 5 | abrir | 10/10 | −7.0 | −188 g | −89 | 38 |
| 10 | cerrar | 10/10 | 16.0 | +409 g | +276 | 41 |
| 10 | abrir | 10/10 | −15.5 | −204 g | −136 | 20 |

### Los tres resultados

**1. El incremento mínimo fiable es asimétrico: 1 unidad cerrando, 3 abriendo.**
Cerrando, una sola unidad de `ANGLE_SET` mueve el dedo en los 10 intentos. Abriendo,
una unidad solo funciona **4 de 10 veces** y dos unidades **6 de 10**; hace falta
llegar a 3 para que sea fiable. El regulador puede apretar con el paso mínimo pero
**no puede aflojar con él**.

**2. Aflojar cuesta la mitad que apretar.** Para el mismo tamaño de comando, el
cambio de fuerza al abrir es ~½ del que produce al cerrar (ratio 2.0 a 10 unidades,
2.4 a 3). Es histéresis del accionamiento: al invertir el sentido, parte del
comando se consume en el juego mecánico.

**3. El cuanto de posición es ~3 counts, no 1.6.** El factor nominal en esta pose
es 1.60 counts de `POS` por unidad de comando, y a 10 unidades se cumple
(16 counts). Pero **un comando de 1 unidad mueve 3 counts**: por debajo de ese
salto el dedo no se mueve en absoluto. Es stiction — el dedo o no arranca, o
arranca de golpe.

### Precisión de fuerza alcanzable (medio, `F₀ = 250`, contacto sobre arista)

| | Paso mínimo fiable | Cuanto de fuerza |
|---|---|---|
| Apretando | 1 unidad | **~40 g** (mínimo observado 32) |
| Aflojando | 3 unidades | **~70 g** (mínimo observado 39) |

**La resolución de fuerza del lazo en este dedo y contacto es de decenas de
gramos, no de gramos.** Pedirle al PI que mantenga 250 g ± 10 g no es alcanzable
con este actuador y este contacto.

### Implicaciones para el regulador

- **Banda muerta obligatoria**, de al menos el cuanto de aflojar (~70 g) alrededor
  de `F*`. Por debajo de eso el lazo oscila entre dos escalones sin poder asentar.
- **Asimetría → deriva al apriete.** Un PI simétrico aprieta con paso 1 y afloja
  con paso 3, y cada aflojada devuelve la mitad de fuerza que una apretada del
  mismo tamaño. Sin compensación, el punto de operación **deriva hacia arriba**.
  Hace falta ganancia distinta por sentido, o un paso mínimo de 3 unidades en
  ambos (renunciando a resolución al apretar).
- **`FORCE_SET` siempre por encima del rango de trabajo** (ver abajo).

### Hallazgo del intento fallido: el paro del firmware secuestra la posición

En la primera corrida `FORCE_SET` quedó en 750 g (`F₀`+500) y la fuerza llegó a
~800. Desde ese momento **el dedo dejó de aceptar `ANGLE_SET` en los dos
sentidos**: comandos de 10 unidades para *abrir* no movieron nada, y el `POS` se
quedó congelado en 1518 durante el resto de la tanda.

**Para el PI es una restricción dura: si la fuerza alcanza `FORCE_SET`, el lazo
pierde la autoridad de posición por completo, incluso para aflojar.** `FORCE_SET`
tiene que quedar siempre por encima del rango de trabajo del regulador, y el
techo real debe ser el del propio lazo, no el del firmware.

*(La causa del sobreimpulso era del lazo de búsqueda: evaluaba la fuerza sin
esperar a que el dedo LLEGARA al comando, así que a `v=25` el comando corría por
delante. Corregido con espera de llegada de `POS_ACT`; con el arreglo el contacto
se establece en 256 g contra los 250 pedidos.)*

### E3.2 en el índice — qué generaliza y qué no

100 trials, `F₀ = 250`, montaje `e3`, 0 abortos, 36 → 38 °C. Contacto en 254 g.

| Paso | Sentido | Índice: movió | ΔF | Medio: movió | ΔF |
|---|---|---|---|---|---|
| 1 | cerrar | **6/10** | +16 g | 10/10 | +41 g |
| 1 | abrir | 6/10 | −5 g | **4/10** | +0 g |
| 2 | cerrar | 8/10 | +17 g | 10/10 | +59 g |
| 2 | abrir | 10/10 | −67 g | 6/10 | −69 g |
| 3 | cerrar | 10/10 | +64 g | 10/10 | +171 g |
| 3 | abrir | 9/10 | −55 g | 10/10 | −72 g |
| 10 | cerrar | 10/10 | +309 g | 10/10 | +409 g |
| 10 | abrir | 10/10 | −156 g | 10/10 | −204 g |

**Generaliza: el incremento mínimo fiable es 3 unidades.** Una unidad no es
dependible en ninguno de los dos dedos (6/10 en el índice cerrando, 4/10 en el
medio abriendo). A partir de 3 unidades los dos van a 9–10 de 10.

**No generaliza: la dirección de la asimetría.** En el medio lo fiable es cerrar
(10/10 a 1u) y lo dudoso abrir (4/10); en el índice es al revés a 2 unidades
(10/10 abriendo contra 8/10 cerrando). Lo que informé como «1 unidad cerrando,
3 abriendo» era **del medio, no de la familia**.

**Tampoco generaliza el cuanto de fuerza, y por una razón que sí se entiende.**
El índice resuelve 16–31 g por unidad y el medio 30–61: el índice es el doble de
fino. Sigue a la rigidez del contacto — `k_c` 12.4 contra 26.2 — que es
exactamente el resultado contraintuitivo que el plan anticipaba: **un contacto
más blando da control de fuerza más fino**.

### El modelo de unidades funciona

| Dedo | counts/unidad | `k_c` | Predicho | Medido (10u) |
|---|---|---|---|---|
| Índice | 1.60 | 12.4 | 20 g | **31 g** |
| Medio | 1.60 | 26.2 | 42 g | **41 g** |

El medio clava la predicción; el índice sale 1.5× por encima, dentro de la
dispersión de su `k_c` (8.3–12.4 según el sondeo). **El modelo sirve para
dimensionar, no para sustituir la medida.**

Y entonces la predicción que importa: el pulgar tiene **0.75 counts por unidad**
—no 1.60, porque su mapa `POS↔ANGLE` es mucho más comprimido— y `k_c ≈ 5.7`.
Eso da **~4 g por unidad de comando**, un orden de magnitud por debajo del medio.
Si se confirma, el pulgar es el único dedo donde el lazo puede aspirar a precisión
de gramos, y eso condiciona cómo se reparte el trabajo entre los dos lazos del
modo 1.

### Precisión alcanzable, revisada

Con el paso mínimo fiable de **3 unidades**:

| Dedo | Cerrando | Abriendo |
|---|---|---|
| Índice | 64 g | 55 g |
| Medio | 171 g | 72 g |
| Pulgar | *(predicho ~12 g)* | — |

### E3.2 en el pulgar — la predicción se confirma

Montaje `e3`: `block1` **encima de las falanges**, rotación anclada en oposición
(`--hold 5:0`). El sondeo previo reproduce la geometría del pulgar mejor que
ningún otro dedo: **onset POS 780** contra 775–777 de las campañas de hace dos
días y de hace un mes, `k_c` **5.96** contra 5.66–5.92. 100 trials, 0 abortos,
28 → 32 °C.

### La tabla de los tres dedos

| Paso | Sentido | Pulgar | Índice | Medio |
|---|---|---|---|---|
| 1 | cerrar | **1/10** · +0 g | 6/10 · +16 g | 10/10 · +41 g |
| 1 | abrir | **1/10** · +0 g | 6/10 · −5 g | 4/10 · +0 g |
| 2 | cerrar | 6/10 · +8 g | 8/10 · +17 g | 10/10 · +59 g |
| 2 | abrir | 5/10 · −1 g | 10/10 · −67 g | 6/10 · −69 g |
| **3** | **cerrar** | **9/10 · +17 g** | **10/10 · +64 g** | **10/10 · +171 g** |
| **3** | **abrir** | **10/10 · −20 g** | **9/10 · −55 g** | **10/10 · −72 g** |
| 5 | cerrar | 10/10 · +18 g | 10/10 · +156 g | 10/10 · +304 g |
| 10 | cerrar | 10/10 · +42 g | 10/10 · +309 g | 10/10 · +409 g |

**El incremento mínimo fiable son 3 unidades de `ANGLE_SET`, en los tres dedos.**
A 3 unidades todos van a 9–10 de 10; por debajo, ninguno es dependible. Es el
resultado que generaliza, y es el que el regulador debe adoptar.

**El cuanto de fuerza no generaliza, y esa es la información útil:**

| Dedo | g/unidad | `k_c` | counts/u | **Resolución a 3 unidades** |
|---|---|---|---|---|
| **Pulgar** | **4–8** | 5.96 | 0.75 | **~18 g** |
| Índice | 16–31 | 12.44 | 1.60 | ~60 g |
| Medio | 24–57 | 26.25 | 1.60 | ~72–171 g |

El pulgar resuelve fuerza **3× mejor que el índice y 5–9× mejor que el medio**, y
lo hace por dos factores que se multiplican: su mapa `POS↔ANGLE` está comprimido
(0.75 counts por unidad de comando contra 1.60) y su contacto es el más blando
(5.96 g/count contra 12.4 y 26.2). La predicción del modelo de unidades era
**~4 g/unidad** y se mide **4–8**.

> El pulgar paga ese fino con **fiabilidad de comando**: a 1 unidad solo se mueve
> 1 de 10 veces, peor que los otros dos. Pero el producto que importa —paso
> mínimo fiable × g por unidad— sigue saliéndole a favor por un factor de 3.

### Implicación para el modo 1: los dos lazos no son intercambiables

En la pinza pulgar+índice, **el pulgar es el que puede hacer el ajuste fino y el
índice el que sostiene**. Repartir el trabajo al revés desperdicia un factor 3 de
resolución. Y fija el objetivo realista del regulador: **~20 g de precisión si el
trim lo lleva el pulgar**, no los ~60 que daría el índice ni los ~170 del medio.

### E3.2 a `F₀ = 1000` (medio) — el cuanto empeora con la carga

80 trials, incrementos hasta 5 (a 10 unidades el escalón llevaría la fuerza al
techo de 1500 g), 0 abortos, contacto establecido en 1024 g.

| Paso | Sentido | `F₀=250` | `F₀=1000` |
|---|---|---|---|
| 1 | cerrar | **10/10** · +41 g | **6/10** · +26 g |
| 1 | abrir | 4/10 · +0 g | **2/10** · −1 g |
| 2 | cerrar | 10/10 · +59 g | 10/10 · +200 g |
| 2 | abrir | 6/10 · −69 g | **3/10** · −2 g |
| 3 | cerrar | 10/10 · +171 g | 10/10 · +221 g |
| 3 | abrir | 10/10 · −72 g | 10/10 · **−225 g** |
| 5 | cerrar | 10/10 · +304 g | 10/10 · +307 g |
| 5 | abrir | 10/10 · −188 g | 10/10 · −245 g |

**Los pasos pequeños empeoran con la carga.** Una unidad cerrando cae de 10/10 a
6/10; dos unidades abriendo, de 6/10 a 3/10. Más carga es más fricción, y el
umbral para arrancar el dedo sube.

**Pero 3 unidades sigue siendo fiable a los dos niveles** (10/10 en todos los
casos). La regla del paso mínimo aguanta el rango de carga.

**Y el cuanto de fuerza crece: la rigidez local depende del punto de operación.**
A 3 unidades abriendo, el medio pasa de 24 a **75 g por unidad** — un factor 3.
En rigidez local eso es **15 → 47 g/count**.

> **Esto ya contesta, de forma preliminar, el criterio de decisión de E3.1.** El
> plan dice: si `k_local` varía **≥ 2×** entre `F₀ = 100` y `F₀ = 1000` dentro del
> mismo contacto, el *gain scheduling* del regulador debe ir sobre la **rigidez
> local estimada en línea**, no sobre una constante por dedo. Entre 250 y 1000 ya
> varía **3×**. E3.1 lo medirá con escalones dedicados, pero la dirección está
> puesta.

**Precisión alcanzable, por nivel de fuerza** (medio, paso de 3 unidades):

| `F₀` | Cerrando | Abriendo |
|---|---|---|
| 250 g | 171 g | 72 g |
| 1000 g | 221 g | 225 g |

La precisión del lazo **se degrada al subir la consigna**. No es un lazo con una
resolución fija: resuelve peor cuanto más aprieta.

---

## E3.6a — Sincronía del refresco · **abierta, y ahora se sabe qué hace falta**

El plan la daba por gratis «con los logs multi-DOF que ya existen». **No existen**:
todos los CSV de trial del repo guardan un solo dedo, y el Exp 0 registró el
periodo de las lecturas, no los valores. Por eso el registrador del Exp 3 guarda
`POS_ACT` y `FORCE_ACT` de los seis DOF — cuesta lo mismo, el bloque de 6 shorts
se lee entero igualmente.

Del log de E3.2 (17 581 muestras, 191 s, 92 Hz de lectura):

- **DOF 2, el que se mueve: `POS` cambia cada 32.4 ms.** Confirma los ~30.7 ms ya
  medidos, ahora en un punto de operación nuevo (contacto sostenido a `v=25`).
- **Los otros cinco no contestan la pregunta.** Su `POS` no cambia **ni una vez**
  en 191 s, y sus «cambios» de fuerza son ruido cruzando enteros, no refrescos.
  El desfase aparente de +0.00 ms del DOF 3 es artefacto de eso: con instantes de
  ruido densos, cualquier referencia encuentra coincidencia.

**Lo que hace falta:** un dataset con **≥ 2 DOF moviéndose a la vez**. Sale gratis
de E3.6b (la pinza pulgar+medio) o de una prueba trivial de dos dedos en aire.
Conviene además subir la tasa de lectura para ese caso: 92 Hz da 10.9 ms de
resolución sobre un frame de 30 ms, suficiente para ver un escalonado grande pero
no para medirlo fino.

---

## Estado

| Prueba | Estado |
|---|---|
| Prerrequisito §3 · índice | ✔ |
| E3.2 · `F₀ = 250` (medio) | ✔ |
| E3.2 · `F₀ = 250` (índice) | ✔ |
| E3.2 · `F₀ = 250` (pulgar) | ✔ |
| E3.2 · `F₀ = 1000` (medio) | ✔ |
| E3.2 · `F₀ = 1000` (índice, pulgar) | pendiente de montaje |
| E3.2 · `F₀ = 1000` (medio) | pendiente — **espera térmica** (44 °C, límite de arranque 45) |
| E3.1 rigidez local | pendiente (gateada por E3.2) |
| E3.3 planta en contacto | pendiente |
| E3.4 + E3.5 decaimiento y deriva | pendiente |
| E3.6a sincronía | abierta — necesita ≥2 DOF en movimiento |
| E3.6b acoplamiento | pendiente |

**Nota para `F₀ = 1000`:** con el `g/unidad` medido (~40–60 cerrando), un escalón
de 10 unidades desde 1000 g llevaría la fuerza a ~1400–1600 g, en el techo propio
de 1500. Esa tanda debe correr con incrementos hasta 5, no hasta 10.
