# Regulador de fuerza — bitácora

Resultados del [plan v3](Planes/PLAN_regulador_PI.md). Las constantes de partida
salen del Exp 3 (`../Caracterizacion/exp3/exp3_results.md`).

---

## A1 · Andamiaje, seguridad y detectores — ✔ cerrado

Las cuatro compuertas pasadas con hardware.

| Compuerta | Resultado |
|---|---|
| Tasas | sondeo 349 Hz · disparo **26–27 Hz por DOF**, sin duplicados |
| Guarda | dispara a **121 g** con el dedo en el aire |
| Resbalón | **dos corridas**: detectado a 10 y 16 counts; el pulgar resbaló en **1024 y 1018 g** |
| Ctrl-C | SIGINT deja la mano abierta y a 0 g |

### El disparo del control va por DOF, no por «frame» de bloque

El diseño inicial disparaba el control con «el bloque de 6 DOF cambió», suponiendo
publicación atómica. **La mano no publica los seis a la vez** — E3.6a ya había
medido 1.9 ms de desfase entre índice y pulgar — así que el bloque cambia cada vez
que se actualiza **cualquiera** de los seis y la tasa sale inflada: **46–51 Hz
medidos contra 32.6 de publicación**.

Medido, con el intervalo entre cambios siempre múltiplo exacto del periodo:

| | cambios de fuerza | intervalo mediano |
|---|---|---|
| Sin carga | 6–11 Hz | **60.0 ms** = 2 × 30.7 |
| Con carga (330–1077 g) | **28.3 Hz** | **30.4 ms** |

El dedo publica siempre; si el entero se repite la lectura parece «no fresca», y
eso ocurre uno de cada dos frames en vacío y casi nunca bajo carga. El disparador
definitivo avanza con **cambio de valor O plazo agotado (40 ms)**: un valor
repetido no es información vieja, es el valor actual. Lo que no puede hacerse es
integrar varias veces dentro del mismo frame. Medido: **27 Hz de disparo**.

### El punto de resbalón es repetible dentro de una pose

1024 y 1018 g en dos corridas independientes sobre el mismo agarre. Varía con la
pose —455 a 745 g en lo medido— pero no de un intento a otro.

---

## A2 · Lazo SISO contra bloque · **en curso**

Índice contra `block1` de pie, `F* = 250 g`, rotación **sin anclar** (así se
caracterizó el índice en E3.1–E3.5, y A2 compara contra esas medidas).

### El hallazgo: hace falta un periodo refractario

El pseudocódigo del plan no lo contemplaba y la primera tanda en hardware lo
exigió. El lazo decide cada ~35 ms, pero la fuerza tarda `L + τ ≈ 100 ms` en
responder y ~111 ms en asentar (E3.3). Sin esperar, el controlador **encadena tres
o cuatro escalones antes de ver el efecto del primero**, y con un cuanto de ~80 g
por escalón eso son 300 g ya comprometidos.

| `Kp = 0.05`, P puro | Sin refractario | Con refractario 200 ms |
|---|---|---|
| Pico | **476 g (+90 %)** | **340 g (+36 %)** |
| Error en régimen | 134 g | **11 g** (máx 13) |
| En unidades de banda | 2.09 × | **0.17 ×** |
| Entra en banda | nunca | **1.1 s** |
| Desenlace | **resbalón del actuador al segundo** | 30 s estables |

> **No se arregla bajando `Kp`.** El cuanto mínimo del dedo pone un suelo a lo que
> cada acción vale: aunque `Kp` sea pequeño, la acción o es cero o es un escalón
> entero. Lo que había que arreglar era **decidir antes de ver**.

Con 11 g de error en un dedo cuyo cuanto de comando vale ~64–80 g, el lazo resuelve
**mejor que su propio escalón mínimo** — porque la banda muerta lo para antes de
que el cuanto lo obligue a oscilar.

### Comparación con el firmware · **orientación, no el resultado formal**

| | Firmware (`FORCE_SET = 250`) | Lazo PI |
|---|---|---|
| Pico | +15 % | +36 % |
| **Error en régimen** | **−38 g** | **−11 g** |

El firmware sobrepasa poco y **decae por debajo**; el lazo sobrepasa más en la
aproximación y **se queda 3.5× más cerca**.

> **Esto NO es todavía el resultado de la compuerta A2.** Son tandas separadas, y
> el §8 del plan lo prohíbe por una razón medida: dos tandas del mismo dedo, mismo
> objeto y misma pose difirieron en un **factor 2** por deriva del cero entre
> tandas. Falta el **protocolo intercalado**, N ≥ 10 por brazo, en una sola tanda.

### Pendiente de A2

1. Bitácora de sintonía: subir `Kp` hasta el primer indicio de oscilación y
   retroceder; después añadir `Ki`.
2. Reducir el sobreimpulso de aproximación (+36 %), que es donde el lazo pierde
   contra el firmware. Candidato: limitar el primer escalón, o entrar más cerca.
3. `F* = 450 g` además de 250, y el **pulgar** además del índice.
4. **Protocolo intercalado** y la figura de cabecera.

---

## Nota de método: el «onset geométrico» del sondeo es frágil

Al verificar el montaje de A2, el sondeo reportó onset POS 482 y `k_c` 0.38
g/count, contra 1445 y 11.32 del montaje bueno `e3e`. **El montaje era correcto**:
las trazas crudas se superponen punto por punto, y la rigidez medida sobre el
tramo donde la fuerza de verdad despega sale 5.35 contra 4.31 g/count.

La causa: el onset se calcula restando una curva libre archivada y cruzando un
umbral fijo de 30 g. A POS 443 esta tanda leyó **31 g** y `e3e` leyó **29**. Dos
gramos, y el onset reportado salta 1000 counts y el `k_c` cambia 30×. Los valores
de `k_c` archivados salen de ese mismo cálculo y hay que citarlos con esa reserva;
lo robusto es comparar la traza cruda y el POS de parada.

---

## A2 · el protocolo intercalado

El §8 del plan prohíbe comparar brazos medidos en tandas distintas, y no por
purismo: dos tandas del mismo dedo, objeto y pose difirieron en un **factor 2**
por deriva del cero (Exp 2). `lazo.py --modo comparar` mete los dos brazos en
**una sola tanda**:

- **orden aleatorizado por bloques balanceados** — `--pares N` da N trials de cada
  brazo, barajados con `--seed`. Balanceado para que una deriva lenta reparta su
  efecto entre los dos brazos en vez de cargarlo sobre el que fue segundo;
- **misma tara y misma espera** antes de cada trial (≥ 10 s tras soltar, E3.5), con
  la mediana de 5 muestras en vez de una sola lectura;
- **misma pre-posición para los dos brazos.** El firmware arrancaba desde la mano
  abierta mientras el lazo se pre-posicionaba, así que se gastaba parte del trial
  viajando: eso compara **quién llega antes**, no quién sostiene la consigna;
- **temperatura anotada por trial**, y si la tara fue aceptada o no;
- **los trials abortados quedan en el índice**, con `nota=abortado`. Un aborto que
  desaparece deja un `N` que no se puede auditar.

El análisis va aparte, en `a2_comparar.py`, con **prueba de permutación**: son
N ~ 10, la métrica es una mediana y el brazo del lazo está truncado por la banda
muerta, así que no hay motivo para suponer normalidad. Se reporta **mediana y
rango**, nunca la media sola. Mezclar bloques exige `--mezclar-bloques` a
propósito.

```bash
# una tanda: N por brazo, intercalados
.venv/bin/python Control/lazo.py --modo comparar --dof 3 --rot -1 --ref 250 \
    --pares 10 --hold-s 60 --kp 0.05 --ki 0 --banda 64 --refractario 0.20 \
    --angulo-aprox 456 --frac-aprox 0.6 --objetivo-angulo 100 \
    --techo-fuerza 600 --fset-respaldo 700 --bloque a
.venv/bin/python Control/a2_comparar.py Control/data/a2_intercalado_dof3_F250.csv
```

### Cinco bugs que salieron al montarlo

Tres los cazó el mock antes de tocar hardware; el cuarto es de diseño
experimental y salió al leer el primer resultado del mock; el quinto salió ya en
la mano.

**1 · El actuador recibía `dt = 0`, así que `Ki` no hacía nada.** `bucle` llamaba
a `Disparador.toca()` para todos los DOF **antes** del actuador, y `toca()` muta
`t_ultimo`. La segunda llamada —la del actuador, sobre la misma muestra— veía
`dt = 0`, y `self.I += ki * e * dt` es idénticamente cero. Invisible mientras
corrimos con `Ki = 0`, y justo lo que tocaba sintonizar ahora.

Además el actuador **perdía todos los disparos por plazo**: en las muestras sin
cambio de valor, `bucle` ya había consumido el disparo y el actuador veía `False`.
El control quedaba a la tasa de cambio de valor, que es lo contrario de para lo
que existe `Disparador`. Medido: **8.8 Hz antes, 32.2 Hz después**, y en vacío el
**51 %** de los disparos del índice son por plazo.

Arreglo: el actuador es el **dueño** del disparo de su DOF (`ctx.dof_control`), y
`bucle` solo cuenta los demás. Comprobado con **I puro** (`--kp 0 --ki 0.5`), que
antes era estructuralmente incapaz de moverse: lleva el error de 150 g a **6 g**.

> Los 11 g de error de la tanda anterior siguen siendo válidos —se midieron con
> `Ki = 0`, donde este bug no actúa— pero **los 8.8 Hz de aquel informe eran del
> bug**, no del diseño.

**2 · La rampa de aproximación medía su espera contra el reloj equivocado.** El
dwell comparaba `t - ctx.t0` (inicio de **toda la tanda**) contra un `t_prox` que
arrancaba en 0. La rampa soltaba de golpe tantos pasos como segundos llevara la
tanda: inofensivo en una tanda de un solo trial —por eso pasó A1— y un golpe
contra el objeto en el sexto trial de una intercalada, donde el desfase ya son
minutos. Ahora el dwell se cuenta desde que arranca **esa** rampa.

**3 · El estado cruzaba de un trial al siguiente.** El `timeout` de la guarda
corría desde que se creó el `Contexto`, así que habría abortado la tanda a mitad
por un timeout falso; y la historia de los detectores cruzaba la apertura de la
mano. Ahora cada trial reinicia guarda y detectores, y lo hace **después** de la
tara —con el dedo ya en reposo—, porque reiniciar justo tras abrir deja dentro de
la ventana el propio viaje de apertura.

**4 · El detector de resbalón estaba armado sin contacto.** Su firma —`POS`
retrocede contra su propio comando— la cumple trivialmente cualquier dedo que aún
venga viajando del comando anterior, y abortaba trials en la aproximación. Sin
carga no hay nada de lo que protegerse: el actuador no puede ceder contra una
fuerza que no existe. Ahora se arma solo por encima de `--contacto-min` (80 g) y
olvida la historia mientras tanto, para que la ventana entre limpia en cuanto haya
contacto. La guarda de fuerza sí sigue activa todo el tiempo.

Como efecto lateral, la guarda ahora **dice por qué** aborta: antes, un aborto
dentro de la aproximación se tragaba el motivo y solo se veía «no se alcanzó el
contacto de partida».

**5 · La política de tara se mordía la cola.** `Tara.puede` rechazaba tarar si
`abs(fuerza) > 40 g`, y el índice estaba a **−45 g** de deriva de cero con la mano
abierta y descargada. O sea: la deriva bloqueaba la tara que existe para quitarla,
y no había forma de salir del estado.

Una yema en contacto **empuja**, y eso lee positivo. Un valor negativo no puede ser
contacto. Ahora solo cuenta la carga positiva, con el mismo umbral conservador de
40 g de ese lado. Tras el arreglo la tara entra y deja los seis DOF a 0 g.

> **Caveat sobre la tanda anterior de A2, ya medido.** `--modo pi` no tara, así
> que aquellos 11 g de error en régimen se midieron contra el cero que hubiera en
> ese momento. Repetida la **misma configuración** con el cero recién tarado, el
> error en régimen sale **59 g**, no 11. La diferencia (~48 g) coincide con la
> deriva que arrastraba el índice ese día (−45 g). El número del lazo frente al
> del firmware sigue siendo comparable —los dos vivían con el mismo cero— pero el
> **valor absoluto** de `F*` de aquella tanda no es de fiar. El protocolo
> intercalado tara antes de cada trial precisamente por esto.

> El arreglo del disparo también se confirma en la mano, no solo en el mock:
> **26.7 Hz** de control en la misma configuración que antes daba 8.8.

---

## A2 · bloque piloto: por qué la compuerta no se gana en el índice a 250 g

Antes de gastar 30 min en N=10 por brazo, un piloto de **2 pares** (`bloque=piloto`,
`Control/data/a2_intercalado_dof3_F250.csv`), con tara aceptada en los cuatro
trials:

| | firmware | lazo |
|---|---|---|
| \|error\| en régimen | mediana **22.5 g** (rango 8–37) | mediana **35.5 g** (rango 14–57) |
| Pico | 300 g | 232 g |
| Corriente en régimen | **0 mA** | **0 mA** |

Los rangos se solapan por completo y el lazo **no** gana. Con n=2 no hay
afirmación estadística posible, pero sí dos hallazgos físicos que sí son sólidos.

### 1 · Sostener no cuesta corriente — tampoco al lazo

Medido directamente sobre el registro `CURRENT`: el índice consume **31–92 mA
mientras se mueve y exactamente 0 mA sosteniendo 160 g**. La mano retiene por
fricción de la transmisión, que no es retrodrivable.

Eso **invalida la mitad del criterio de A2** tal y como está escrito en el plan:

> «el lazo mantiene `F*` … y lo hace **consumiendo corriente**, que es la prueba
> directa de que hay par activo donde antes había 0 mA»

Un PI que manda posiciones y se detiene acaba igual de a 0 mA que el firmware. No
hay par activo que demostrar: para tenerlo habría que mandar deliberadamente más
allá del contacto y dejar el motor calado, que es justo lo que hace `FORCE_SET`.
La ventaja del lazo sólo puede estar en **dónde se para** y en **volver a
corregir cuando la fuerza deriva** — nunca en la corriente.

> Un bug de registro lo enmascaraba: la bitácora anotaba `I_mA` del `dofs[0]` (el
> pulgar) en vez del DOF regulado, y daba 0 mA en **todas** las filas, incluida la
> aproximación. Corregido.

### 2 · La ganancia del índice tiene una zona muerta que depende de la fuerza

Escalones de `ANGLE_SET` aplicados desde reposo, con `FORCE_SET` alto para que no
enclave:

| Fuerza de partida | Paso | ΔF |
|---|---|---|
| ~150 g | 3 u (cierra) | **+1, +4, −4, +1, +1, −2 g** — no transmite |
| ~150 g | 2 u (abre) | **−11, −1, −54, −36 g** — se desploma |
| ~357 g | 3 u (cierra) | **+66 g**, luego **+58 g** |

Cerrando poco a poco cerca de un sostenimiento flojo, la fuerza **no sube**: POS
avanza 30 counts y ΔF es ruido. Abriendo, cae a decenas de gramos por paso. El
paso pequeño se absorbe en la holgura y la fricción, y sólo al soltar se libera la
carga acumulada. A 357 g, en cambio, el mismo paso de 3 u vale ~60 g.

Consecuencia para el control: **a `F* = 250` el índice está en la zona muerta** y
el PI no puede afinar hacia arriba, así que su error en régimen es básicamente
donde la aproximación lo dejó — de ahí el rango 14–57 g. Y en la zona que sí
responde, la resolución es ~60 g por escalón. En ninguno de los dos regímenes el
índice sostiene 250 g mejor que ±30 g.

Esto es exactamente el caso para el estimador de ganancia de A4: la ganancia no es
una constante del dedo, es función del punto de trabajo.

### Qué hacer con la compuerta

- **El criterio de corriente se retira** del plan, con la medida que lo justifica.
- El dedo con resolución suficiente es el **pulgar** (~20 g por cuanto, contra
  ~60 g del índice). Es además el dedo que importa en la pinza.

---

## Compuerta A2 · **pasada** (pulgar, `F* = 250 g`)

Una sola tanda, N = 10 por brazo, aleatorización por bloques
(`L F L F F L L F F L F L F L F L L F L F`), tara aceptada en los 20 trials,
60 s de sostenimiento, 42 °C al cierre. `Control/data/a2_intercalado_dof4_F250.csv`.

| | firmware (`FORCE_SET`) | lazo PI | p |
|---|---|---|---|
| **\|error\| en régimen** | **25.0 g** (rango 8–33) | **11.0 g** (rango 0–19) | **0.0074** |
| Error con signo | −25 g · **los 10 negativos** | −11 g | 0.0074 |
| Pico | 272.5 g (265–278) | **253.0 g** (241–264) | 0.0008 |
| Corriente en régimen | 0 mA | 0 mA | 1.0 |

Prueba de permutación a dos colas sobre la diferencia de medianas, 20000
permutaciones (`a2_comparar.py`).

**El criterio se cumple:** el firmware decae **25 g sobre 250, o sea el 10.0 %** —
justo el techo del 5–10 % que el plan predijo— y **los diez trials decaen**, sin
excepción. El lazo se queda en 11 g, **4.4 %**.

En las unidades que el plan exige, el cuanto del dedo (≈23 g en el pulgar):

- lazo **0.48 × cuanto** — resuelve **mejor que su propio escalón mínimo**,
- firmware **1.09 × cuanto**.

Y el lazo además **sobreimpulsa menos** (253 contra 272 g), que era donde perdía en
el índice: allí entraba con +36 %, aquí con +1 %.

### Un trial truncado, y qué se hace con él

El trial 10 (lazo) duró 34 s en vez de 60: lo cortó el detector de resbalón con
`+137 counts`. **No fue un resbalón.** Es un glitch de **una sola muestra** — una
lectura aislada dio `POS 988` entre vecinas de `851`, y la siguiente ya volvía a
851 con la fuerza clavada en 250 g. El detector comparaba la muestra más vieja de
la ventana contra la más nueva, así que un dato suelto bastaba para fabricar un
resbalón y abortar un trial de 60 s.

Corregido: ahora compara **medianas de los extremos** de la ventana. Un resbalón
real dura ~0.5 s y ~50 counts, así que sobrevive de sobra a promediar las puntas.
Verificado en banco: ignora glitches de una y de cinco muestras, y sigue
disparando con un retroceso real de 50 counts en 0.3 s.

Como ese trial no cumple el «error en régimen **tras 60 s**» del criterio, la
compuerta se reporta **también sin él**, y la conclusión no se mueve:

| sin el trial 10 | firmware | lazo | p |
|---|---|---|---|
| \|error\| | 25.0 g (8–33), n=10 | **12.0 g** (3–19), n=9 | **0.0098** |
| Pico | 272.5 g | 253.0 g | 0.0031 |

### Lo que esta compuerta NO dice

- **No dice que el lazo aporte par activo.** Los dos brazos sostienen a 0 mA; el
  criterio de corriente está retirado del plan, con la medida que lo justifica.
  Lo que el lazo hace mejor es **dónde se para**, no con cuánta fuerza aprieta.
- **No vale para el índice**, donde está medido que a `F* = 250` el dedo está en
  zona muerta. Sólo vale para el **pulgar** a esta consigna.
- **No cubre `F* = 450`** ni la perturbación en marcha: el firmware aquí decae y
  ya está, pero nadie ha empujado el objeto para ver si el lazo **re-corrige**,
  que es la otra mitad de lo que un lazo debería dar.

---

## Perturbación para la re-corrección · el soporte como actuador

En el montaje de A2 (`block1` sobre las falanges, pulgar contra el canto) **no hay
un segundo dedo oponiéndose**, así que la perturbación no puede venir de apretar
más: viene de **mover el soporte**. Los cuatro dedos sostienen el bloque y están
ociosos, así que sirven de actuador de perturbación — repetible, con magnitud
elegida y **sin manos humanas en la trayectoria**.

Medido con el pulgar regulado a 250 g y el soporte pre-flexionado a 950:

| Flexión del soporte | ΔF en el pulgar | POS del pulgar |
|---|---|---|
| −8 u | +4 g (holgura) | +0 |
| −12 u | +10 g | −1 |
| −20 u | +26 g | −1 |
| −28 u | +43 g | −2 |
| **−32 u** | **+56 g** | **−2** |

≈ **1.75 g por unidad** tras absorber ~8 u de holgura. El `POS` del pulgar no se
mueve: **el bloque entra contra el dedo**, el dedo no avanza. Eso es justo lo que
debe ser una perturbación — actúa sobre el objeto, no sobre el actuador regulado.

### La autoridad es de un solo sentido, y eso decide el diseño

El primer intento fue al revés —extender el soporte para **descargar** el pulgar—
y no funciona:

| | autoridad |
|---|---|
| Flexionar (carga) | **+56 g en 32 u**, monótono |
| Extender (descarga) | **−23 g en 45 u**, y **satura**: −13 g en las primeras 15 u, luego se aplana |

El bloque no baja con los dedos que se retiran porque el pulgar lo retiene por
fricción. Es la misma histéresis no retrodrivable que ya aparece en todo lo demás.
Con 23 g de autoridad —apenas la banda muerta— no se puede perturbar nada.

**Consecuencia:** la perturbación es **flexionar el soporte**, y por tanto se prueba
la re-corrección en el sentido de **fuerza excesiva**: el lazo debe **abrir** para
volver a `F*`. No es un premio de consolación, es el sentido que más importa para
la seguridad —un objeto que se aprieta más de lo previsto es como se rompe— y
además es donde el firmware está **estructuralmente incapacitado**: con
`FORCE_SET = F*`, en cuanto `FORCE_ACT` lo supera el dedo deja de aceptar
`ANGLE_SET` **en los dos sentidos**, así que no es que no corrija, es que queda
**enclavado** en la fuerza alta.

### Métrica

Normalizada por la perturbación medida, no por la nominal:

```
recuperación = 1 − |error 15 s después del escalón| / |salto de fuerza en el escalón|
```

El firmware debería dar ~0 por construcción. Sirve igual si algún día la
perturbación la da una mano humana, que no puede ser repetible: el sensor dice
cuánto se perturbó.

---

## Re-corrección tras perturbación · **el lazo rechaza el 88 %, el firmware el 10 %**

Protocolo intercalado con escalón de perturbación: soporte pre-flexionado a 950,
el pulgar regulado a `F* = 250 g`, y a los **25 s** del sostenimiento los cuatro
dedos de soporte flexionan **32 unidades** y se quedan ahí. Idéntico en los dos
brazos: es la perturbación, no el tratamiento. N = 10 por brazo, una sola tanda,
bloques balanceados. `Control/data/a2_intercalado_dof4_F250_pert32.csv`.

| | firmware | lazo PI | p |
|---|---|---|---|
| **Residual sobre su propia base, 20 s después** | **+75 g** (rango 60–83) | **+8 g** (rango 2–25) | **0.0088** |
| Pico de la excursión | +87 g (82–92) | +62 g (48–73) | 0.0027 |
| Rechazo | **10 %** | **88 %** | |

(Los valores son sin los trials 18 y 19; con los 20, +76.5 contra +7.5 g y
p = 0.0010.) **Los rangos no se solapan.**

El firmware no es que corrija mal: **no corrige**. Su 10 % es relajación pasiva,
la misma de E3.4. Y hay una razón estructural: con `FORCE_SET = F*`, en cuanto
`FORCE_ACT` lo supera el dedo **deja de aceptar `ANGLE_SET` en los dos sentidos**,
así que queda **enclavado** en la fuerza alta. El lazo vuelve a su línea de base.

### La métrica se corrigió dos veces, y el piloto lo destapó

**No normalizar por el salto de fuerza.** El mismo escalón de 32 u dio +33 g al
lazo y +83 g al firmware, porque **el lazo ya está abriendo dentro de la ventana
de medida**: el salto es *respuesta*, no perturbación. Normalizar por él premia al
que reacciona rápido con un divisor más pequeño. La perturbación es el escalón de
32 unidades, idéntico por construcción.

**No medir contra `F*`, sino contra la propia base.** Medirlo contra `F*` mezcla
el rechazo de la perturbación con el error en régimen que el brazo ya arrastraba
(el firmware parte de ~230 g, no de 250). Y la primera versión acreditaba como
«recuperación» la relajación pasiva: daba un 55 % a un brazo que no manda nada.

### Geometría real del contacto (verificada por cámara)

`block1` **no está apoyado plano sobre las cuatro falanges**: está de pie,
inclinado ~20–25°, **acuñado entre dos contactos estrechos** — la punta de la yema
distal del pulgar contra su **canto superior**, y la falange proximal del
índice/medio contra el **canto inferior** opuesto. Como se sostiene sobre dos
líneas, **puede rotar**: la perturbación no lo traslada, lo **bascula** contra la
punta del pulgar. Eso explica las ~8 u de holgura antes de que la fuerza responda.

Rastreo subpíxel (plantilla: el conector IEC, solidario con el objeto):

| | pico-a-pico |
|---|---|
| Sosteniendo, sin perturbar | 0.175 px mediana · **0.395 px máx** |
| Durante el escalón | **2.83 px máx** — 7× el ruido, ~1 % del ancho del bloque |

> El veredicto automático de `exp3_track_object.py` dijo «0.2×, en el ruido»
> porque compara **medianas** de ventanas, y esto es **un solo** escalón: casi
> todas las ventanas caen después de que se asiente. Para un evento único el
> estadístico es el máximo, no la mediana.

### Una lectura corrupta encadenó dos fallos

En el trial 18 la guarda saltó con **3187 g**, imposible para este sensor. Abortó
el trial a los 37 s **y** el final abrupto dejó 144 g en la yema, lo que hizo
**rechazar la tara del trial 19**, que corrió con el cero corrido. Un dato suelto,
dos trials tocados.

La guarda de fuerza ahora exige **persistencia** (`--fuerza-ciclos`, 3 por
defecto), igual que ya hacía la de corriente. A ~400 Hz son <10 ms: no compromete
la seguridad y es inmune al dato suelto. Verificado en banco: ignora el glitch de
una muestra y sigue abortando una sobrecarga sostenida.

Es el **tercer** fallo de la misma familia (POS 988 en la compuerta A2, 3187 g
aquí): toda comparación muestra-a-muestra contra un umbral necesita persistencia.
