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
A 3 unidades todos van a 9–10 de 10; por debajo, ninguno es dependible.

> **Válido a `F₀ = 250`.** A 1000 g el pulgar cerrando cae a 5/10 con 3 unidades
> y necesita 5 — ver el cierre de E3.2 más abajo. El valor único que cubre los
> tres dedos y las dos cargas es **5 unidades cerrando, 3 abriendo**.

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

**Los pasos pequeños empeoran con la carga** — *en este dedo*. Una unidad
cerrando cae de 10/10 a 6/10; dos unidades abriendo, de 6/10 a 3/10. Más carga es
más fricción, y el umbral para arrancar el dedo sube.

> La campaña del índice (más abajo) da **lo contrario**, así que esto no es una
> regla de la mano sino del medio. Lo que sobrevive a los dos dedos es el paso
> mínimo de 3 unidades.

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

### E3.2 a `F₀ = 1000` (índice) — el que sí resuelve bajo carga

80 trials, incrementos hasta 5, 0 abortos, contacto establecido en 1007 g
(POS 1498), 42 °C de principio a fin. Montaje `e3d`: onset POS 1442,
`k_c` 12.67 g/count, frenado 16 counts — el mismo contacto que la campaña de
`F₀ = 250`, reproducido tras dos montajes fallidos en los que el bloque se
escapaba de lado.

| Paso | Sentido | `F₀=250` | `F₀=1000` |
|---|---|---|---|
| 1 | cerrar | 6/10 · +16 g | 7/10 · +14 g |
| 1 | abrir | 6/10 · −5 g | **10/10** · −89 g |
| 2 | cerrar | 8/10 · +17 g | **10/10** · +92 g |
| 2 | abrir | 10/10 · −67 g | 10/10 · −163 g |
| **3** | **cerrar** | **10/10 · +64 g** | **10/10 · +108 g** |
| **3** | **abrir** | **9/10 · −55 g** | **10/10 · −154 g** |
| 5 | cerrar | 10/10 · +156 g | 10/10 · +309 g |
| 5 | abrir | 10/10 · −145 g | 10/10 · −244 g |

**«Los pasos pequeños empeoran con la carga» no generaliza — era del medio.** En
el índice pasa lo contrario: 1 unidad abriendo sube de 6/10 a **10/10**, y 2
unidades cerrando de 8/10 a **10/10**. La única casilla que sigue floja es 1
unidad cerrando (6/10 → 7/10), y lo está a los dos niveles.

Lo que sí generaliza es la regla: **3 unidades es fiable en los dos dedos y a los
dos niveles de carga** — en el índice a `F₀ = 1000` sale 10/10 en ambos sentidos,
mejor incluso que a 250.

**La asimetría de sentido crece con la carga.** Ajustando por el origen sobre
todos los trials de ≤ 5 unidades:

| `F₀` | Sentido | counts/unidad | g/unidad | `k_local` |
|---|---|---|---|---|
| 250 | cerrar | 1.29 | 24.3 | 18.8 g/count |
| 250 | abrir | 1.84 | 27.8 | 15.0 g/count |
| 1000 | cerrar | 1.38 | 51.3 | **37.3 g/count** |
| 1000 | abrir | 2.23 | 56.5 | **25.3 g/count** |

El dedo **devuelve más recorrido del que toma**: a 1000 g, 2.23 counts por unidad
abriendo contra 1.38 cerrando, un 60 % más. Está precargado contra el bloque y
parte de la apertura la paga la elasticidad acumulada, no el motor. Cerrando hay
que vencer fricción *y* rigidez; abriendo, la rigidez ayuda.

> Para el regulador esto significa que **el mismo escalón no vale en los dos
> sentidos**. Con ganancia simétrica, cada corrección hacia abajo se pasa ~60 %
> respecto a la equivalente hacia arriba.

**Y confirma el criterio de E3.1 en un segundo dedo.** Entre 250 y 1000 la
rigidez local del índice sube **2.0× cerrando y 1.7× abriendo**. El medio daba
3×. Dos dedos, misma dirección, y el umbral del plan (≥ 2×) queda cruzado: el
*gain scheduling* va sobre **rigidez local estimada en línea**, no sobre una
constante por dedo.

**Precisión a 3 unidades, por nivel** (mediana de |ΔF|):

| `F₀` | Índice cerrar | Índice abrir | Medio cerrar | Medio abrir |
|---|---|---|---|---|
| 250 g | 64 g | 55 g | 171 g | 72 g |
| 1000 g | 108 g | 154 g | 221 g | 225 g |

Los dos dedos resuelven peor cuanto más aprietan, pero **el índice mantiene la
ventaja bajo carga**: a 1000 g resuelve ~1.5–2× mejor que el medio. El orden
pulgar > índice > medio que salió a 250 g se sostiene.

---


### E3.2 a `F₀ = 1000` (pulgar) — se rompe la regla de las 3 unidades

80 trials, incrementos hasta 5, 0 abortos, contacto establecido en 1019 g
(POS 906), 44 → 46 °C. Rotación anclada en oposición (`--hold 5:0`), montaje
`e4r`: onset POS 783, `k_c` 5.79 g/count, parada en POS 845 — reproduce
`m1`/`m3` (775–780, 5.66–5.96, 840).

> **Nota de método.** El primer sondeo de este montaje salió con `k_c` 0.73 y
> onset en POS 513: el pulgar rozaba el bloque durante toda la carrera. No era el
> montaje: el sondeo se lanzó **sin anclar el DOF 5**. Sin oponer la rotación el
> pulgar describe otra trayectoria. **Cualquier prueba del pulgar exige
> `--hold 5:0`**, y la salida hay que leerla: si dice `Anclado: —`, está mal.

| Paso | Sentido | `F₀=250` | `F₀=1000` |
|---|---|---|---|
| 1 | cerrar | 1/10 · +0 g | 2/10 · +2 g |
| 1 | abrir | 1/10 · +0 g | **10/10** · −26 g |
| 2 | cerrar | 6/10 · +8 g | 5/10 · +18 g |
| 2 | abrir | 5/10 · −1 g | 10/10 · −38 g |
| **3** | **cerrar** | **9/10 · +17 g** | **5/10** · +11 g |
| 3 | abrir | 10/10 · −20 g | 10/10 · −42 g |
| 5 | cerrar | 10/10 · +18 g | **10/10 · +64 g** |
| 5 | abrir | 10/10 · −41 g | 10/10 · −68 g |

**A 1000 g el pulgar deja de cerrar con 3 unidades** (9/10 → 5/10) y necesita 5.
Y a la vez **abre con una sola** (1/10 → 10/10). Un factor **5×** entre los dos
sentidos, en el mismo dedo y el mismo punto de operación.

---

## E3.2 — cierre: lo que sobrevive a los tres dedos y a las dos cargas

**El escalón mínimo fiable (≥ 9/10) no es una constante.** Depende del dedo, del
sentido y de la carga:

| Dedo | `F₀` | Cerrar | Abrir |
|---|---|---|---|
| Pulgar | 250 | 3 u · 17 g | 3 u · 20 g |
| Pulgar | 1000 | **5 u · 64 g** | **1 u · 26 g** |
| Índice | 250 | 3 u · 64 g | 2 u · 67 g |
| Índice | 1000 | 2 u · 92 g | **1 u · 89 g** |
| Medio | 250 | 1 u · 41 g | 3 u · 72 g |
| Medio | 1000 | 2 u · 200 g | 3 u · 225 g |

Lo que se puede llevar al regulador:

1. **3 unidades basta a `F₀ = 250` en los tres dedos.** Es la regla de la campaña
   de 250 y sigue en pie — pero solo ahí.
2. **A 1000 g el peor caso es 5 unidades cerrando** (pulgar). Un escalón de cierre
   de **5 unidades** es el único valor único que cubre los tres dedos y las dos
   cargas. Abriendo, 3 unidades cubre todo.
3. **La resolución se degrada al subir la consigna, en los tres dedos**, entre 1.4×
   (índice) y 5× (medio).
4. **El orden pulgar > índice > medio se mantiene bajo carga**: 26–64 g contra
   89–92 y 200–225. La decisión del modo 1 —el pulgar hace el ajuste fino, el
   índice sostiene— aguanta a las dos cargas.

**Lo que NO generaliza** (y estaba escrito como si lo hiciera): el sentido del
efecto de la carga. En pulgar e índice la carga **facilita abrir**; en el medio lo
**dificulta** (1 u abriendo cae de 4/10 a 2/10). Tampoco generaliza qué sentido es
el barato: pulgar e índice abren con 1 unidad a 1000 g, el medio necesita 3.

### Rigidez local: el criterio de E3.1, resuelto en tres dedos

Ajuste por el origen sobre todos los trials de ≤ 5 unidades:

| Dedo | `F₀` | Sentido | counts/u | g/u | `k_local` |
|---|---|---|---|---|---|
| Pulgar | 250 | cerrar | 0.59 | 4.4 | 7.4 |
| Pulgar | 250 | abrir | 0.97 | 8.2 | 8.4 |
| Pulgar | 1000 | cerrar | 0.38 | 10.6 | **28.0** |
| Pulgar | 1000 | abrir | 0.83 | 14.8 | **17.7** |
| Índice | 250 | cerrar | 1.29 | 24.3 | 18.8 |
| Índice | 250 | abrir | 1.84 | 27.8 | 15.0 |
| Índice | 1000 | cerrar | 1.38 | 51.3 | **37.3** |
| Índice | 1000 | abrir | 2.23 | 56.5 | **25.3** |
| Medio | 250 | cerrar | 1.84 | 56.0 | 30.4 |
| Medio | 250 | abrir | 1.15 | 31.1 | 27.2 |
| Medio | 1000 | cerrar | 2.50 | 72.7 | 29.1 |
| Medio | 1000 | abrir | 1.07 | 49.0 | **45.8** |

Factor `k_local(1000)/k_local(250)`: pulgar **3.8× / 2.1×**, índice **2.0× / 1.7×**,
medio **1.0× / 1.7×** (cerrar / abrir).

**Cinco de las seis combinaciones dedo×sentido suben con la carga, y tres cruzan
el umbral de 2× del plan.** El criterio de E3.1 queda contestado en la dirección
que pedía: el *gain scheduling* va sobre **rigidez local estimada en línea**, no
sobre una constante por dedo — y tampoco sobre una constante por dedo y carga,
porque el sentido también la cambia.

> La cifra de «3×» que esta página daba antes para el medio salía de un solo
> tamaño de escalón (3 unidades). El ajuste sobre todos los trials de ≤ 5 da
> **1.7× abriendo y 1.0× cerrando**. La conclusión no cambia —el medio sigue
> variando con la carga en un sentido— pero el número bueno es el del ajuste.

### La asimetría de sentido, y que no tiene un signo común

`counts/unidad` no es igual en los dos sentidos, y a 1000 g la diferencia es
grande: pulgar 0.38 cerrando contra 0.83 abriendo (2.2×), índice 1.38 contra 2.23
(1.6×) — **devuelven más recorrido del que toman**. El medio va al revés: 2.50
cerrando contra 1.07 abriendo.

Para el regulador, las dos versiones dicen lo mismo: **la ganancia no puede ser
simétrica**. Pero el factor hay que medirlo por dedo, no suponerlo.

---

## E3.1 — Rigidez local `k_local(F₀)` · **pulgar hecho, índice pendiente de montaje**

**Redimensionado respecto al plan.** El plan pide escalones de «+2, +5, +10 counts
de `POS`» y niveles `F₀` de 100, 250, 500 y 1000 g. Dos cambios, los dos forzados
por lo medido:

- **Escalones en unidades de comando: 3, 5 y 10.** El cuanto efectivo son 3
  unidades (E3.2), y 1 unidad de comando vale 0.4–2.5 counts de `POS` según dedo,
  sentido y carga. «+2 counts de `POS`» no es una orden que la mano acepte.
- **Sin el nivel de 100 g.** El residual de flexión vale 49 g en el pulgar y 78 g
  en el índice; a 100 g de consigna la fuerza *externa* sería ~20 g, dentro del
  ruido. Los niveles medibles son 250, 500 y 1000.

Los niveles de 250 y 1000 ya estaban medidos en E3.2 con el mismo script, el mismo
montaje y el mismo protocolo, así que E3.1 solo añadió **`F₀ = 500`**.

### El pulgar: la rigidez sube, pero satura

60 trials a `F₀ = 500`, 0 abortos, contacto en 518 g (POS 858), 44 °C plano,
montaje `e4r` con `--hold 5:0`.

`k_local` en g/count, ajuste por el origen sobre los escalones **3 y 5** (los
comunes a los tres niveles):

| `F₀` | Cerrar | Abrir |
|---|---|---|
| 250 g | 7.5 | 8.4 |
| **500 g** | **22.9** | **21.7** |
| 1000 g | 27.7 | 17.8 |

**La curva no es una rampa, satura.** Cerrando, de 250 a 500 sube **3.1×**; de 500
a 1000, solo **1.2×**. Abriendo llega a su máximo en 500 y baja. Comparado con la
secante `k_c = 5.79` del sondeo, la local es **4–5× mayor** en el rango de
trabajo: **el `k_c` secante no es el número correcto para control**, como el plan
sospechaba.

> **Consecuencia para el regulador:** el *gain scheduling* importa sobre todo
> **por debajo de 500 g**, donde la planta triplica su ganancia en un tramo de
> 250 g. Por encima de 500 la ganancia es casi constante y un valor fijo basta.
> Es decir: el tramo peligroso no es apretar fuerte, es **la aproximación**.

### El estimador no puede ir por escalones de sondeo

`k_local = ΔF/Δpos` de **un solo escalón no es medible**: `POS_ACT` está
cuantizado a 1 count y los escalones pequeños mueven muy poco.

Sobre los 600 trials de E3.1 + E3.2:

- **15 % tienen `Δpos = 0`** → el cociente es indefinido.
- **38 % tienen `|Δpos| < 3 counts`** → el cociente lo domina la cuantización.

Se ve en la dispersión del cociente crudo: el pulgar a 500 g abriendo da 18.2
g/count con 3 unidades, 25.3 con 5 y 34.0 con 10; el medio a 250 g abriendo da
69.0 con 2 unidades y 13.2 con 10. **No es rigidez que cambie, es ruido de
división.** Por eso todas las cifras de esta página salen de un **ajuste por el
origen sobre varios tamaños de escalón**, nunca de un escalón suelto.

Un escalón de sondeo suficientemente grande para medir bien (`Δpos ≳ 5 counts`)
pide 5–10 unidades, y a 1000 g eso mete **300–400 g** de perturbación — más que la
precisión que el lazo pretende dar. **El sondeo dedicado se descarta.**

**Lo que queda:** estimar `k_local` de **las propias correcciones del regulador**,
acumuladas en ventana (mínimos cuadrados recursivos de `ΔF` contra `Δpos` sobre
las últimas N acciones), con la ganancia congelada mientras `Σ|Δpos|` no supere
el umbral de unos 5 counts. Sale gratis y no perturba.

### Pendiente

`F₀ = 500` en el **índice**, para tener su curva de tres puntos. Requiere volver a
montar `block1` sobre la palma (`block1_index_contact.jpeg`).

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
| E3.2 · `F₀ = 1000` (índice) | ✔ |
| E3.2 · `F₀ = 1000` (pulgar) | ✔ |
| E3.1 `k_local(F₀)` · pulgar | ✔ (250 / 500 / 1000) |
| E3.1 `k_local(F₀)` · índice | pendiente — falta `F₀ = 500`, requiere block1 en la palma |
| E3.3 planta en contacto | pendiente |
| E3.4 + E3.5 decaimiento y deriva | pendiente |
| E3.6a sincronía | abierta — necesita ≥2 DOF en movimiento |
| E3.6b acoplamiento | pendiente |

**Nota para `F₀ = 1000`:** con el `g/unidad` medido (~40–60 cerrando), un escalón
de 10 unidades desde 1000 g llevaría la fuerza a ~1400–1600 g, en el techo propio
de 1500. Esa tanda debe correr con incrementos hasta 5, no hasta 10.

**Nota para E3.1:** su criterio de decisión ya está contestado por E3.2 en los
tres dedos (ver «Rigidez local» arriba): `k_local` varía 1.0–3.8× con la carga y
cambia con el sentido, así que el *gain scheduling* va sobre estimación en línea.
Lo que E3.1 aporta ahora es el **estimador**, no la decisión.

Además, el plan pide escalones de «+2 counts de `POS`». No es
ejecutable: el cuanto de comando medido son **3 unidades de `ANGLE_SET`**, que en
el índice y el medio valen 1.3–2.2 counts de `POS` cada una. E3.1 debe correr con
escalones de **3, 5 y 10 unidades de comando** y leer la rigidez del ajuste
`ΔF` contra `Δpos`, que es lo que E3.2 ya hace por dentro.
