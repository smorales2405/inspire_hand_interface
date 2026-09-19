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
