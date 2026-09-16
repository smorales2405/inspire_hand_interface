# Exp 3 — Régimen de contacto sostenido · resultados

Plan: [`../EXP3_regimen_contacto_sostenido.md`](../EXP3_regimen_contacto_sostenido.md).
Transporte TCP `192.168.124.210:6000`. Montaje: **`block1`** (la fuente de
alimentación, contacto sobre arista — ver [`../MONTAJES.md`](../MONTAJES.md)),
remontado para esta serie y re-sondeado: onset **POS 1487**, residual 45 g.

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
| E3.2 · `F₀ = 250` (medio) | ✔ |
| E3.2 · `F₀ = 1000` (medio) | pendiente — **espera térmica** (44 °C, límite de arranque 45) |
| E3.1 rigidez local | pendiente (gateada por E3.2) |
| E3.3 planta en contacto | pendiente |
| E3.4 + E3.5 decaimiento y deriva | pendiente |
| E3.6a sincronía | abierta — necesita ≥2 DOF en movimiento |
| E3.6b acoplamiento | pendiente |

**Nota para `F₀ = 1000`:** con el `g/unidad` medido (~40–60 cerrando), un escalón
de 10 unidades desde 1000 g llevaría la fuerza a ~1400–1600 g, en el techo propio
de 1500. Esa tanda debe correr con incrementos hasta 5, no hasta 10.
