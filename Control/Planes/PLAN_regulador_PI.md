# Regulador de fuerza de agarre en lazo cerrado · **Plan v3**

> Handoff a Claude Code. Repo `smorales2405/inspire_hand_interface`, Modbus TCP
> `192.168.124.210:6000`, mano derecha.
>
> **Esta v3 reemplaza a la v1 y la v2.** El Exp 3 completo (incluido E3.6) invalidó
> el supuesto central de las dos: que el lazo se cierra sobre la fuerza de cada
> dedo. Si tienes v1 o v2 en contexto, **descártalas**.

---

## 0. Qué cambió, y por qué obliga a reescribir

| # | v2 asumía | El Exp 3 midió | Impacto |
|---|---|---|---|
| **1** | Un lazo de fuerza **por dedo** | En pinza, el objeto **se traslada 0.46 mm** mientras el dedo avanza 0.45–0.60. El cruce es solo 14–34 %: el dedo **no comprime, empuja** | **Las coordenadas del lazo cambian.** §3 |
| **2** | (no contemplado) | En modo 2, índice y medio se acoplan **en negativo** (−38 %). Dos lazos de fuerza independientes **se realimentan positivamente en el error** | Modo 2 **exige** control coordinado. Parte B |
| **3** | Incremento mínimo de 1 count → 6–17 g | **5 unidades cerrando / 3 abriendo**; resolución **20 g (pulgar) a 90 g (índice)** | Banda muerta y ganancias. §2 |
| **4** | Techo fijo (~585 g) | **455–745 g según pose**; no hay número único. Pero el resbalón mueve `POS` **~50 counts en <0.5 s** | **Vigilar `POS`, no programar un tope.** §2, A1 |
| **5** | Integrador persigue fuerza que decae | **0 mA durante 60 s** en 34 ciclos: el firmware no aplica par. Decae 5–10 % y **se agota** | **Fuga en el integrador**, no guarda de posición |
| **6** | Deriva del cero = térmica | Térmica 6–7 g; **salto por historia de carga 21–46 g**, y **con signo opuesto por DOF** | Re-tara por tiempo (≥10 s), offset por DOF |
| **7** | Sincronía entre DOF, riesgo abierto | **1.9 ms de desfase** (6 % del frame, 3 % del retardo del lazo) | **No es problema.** Lazos simultáneos |
| **8** | `k_local` del banco sirve para sintonizar | Las `k_local` de 7–39 g/count son **contra apoyo rígido**; en pinza la ganancia es menor en la proporción en que el objeto se mueva | El estimador en línea **no es un lujo** |

Y una buena noticia que ahorra trabajo: **la estructura de la matriz de acoplamiento
es del agarre, no del objeto.** Bola de espuma y cubo de PLA dan la misma estructura;
solo cambia la ganancia (1.2–1.5×). Se mide una vez y se re-estima la ganancia en línea.

---

## 1. Lo que el regulador debe hacer

El firmware **no regula fuerza**: durante 60 s de sostenimiento consume **0 mA**.
No hay par activo — lo que retiene la fuerza es la fricción de la transmisión.
**Todo lo que el lazo quiera, lo pone el lazo.**

**Hito de cabecera (Fase A2):** misma consigna, mismo contacto — el firmware
sobrepasa y decae; el lazo alcanza y **mantiene**. Obtenido con el protocolo
intercalado de §8.

---

## 2. Las constantes medidas (esto va al código)

### Rango de consigna
| | Valor | Prueba |
|---|---|---|
| Suelo (índice / pulgar) | ~80 g / ~79 g (residual 78 / 49 g) | Prerreq., sondeo `e4r` |
| Sostenible 60 s | 450 g con 5–10 % de caída | E3.4, 34 ciclos |
| **Techo** | **455–745 g, depende de la pose** | E3.3 + `exp3_ceiling_check` |
| Detección de resbalón | `POS` retrocede **~50 counts en <0.5 s** (normal: 0–2) | Comprobación en pinza |

**No programes un tope constante.** El borde se mueve con la pose; el resbalón se
anuncia solo y a gritos.

### Acción de control
| | Valor | Prueba |
|---|---|---|
| **Escalón mínimo fiable** | **5 u cerrando, 3 u abriendo** | E3.2, 3 dedos × 2 niveles |
| Resolución (pulgar / índice / medio) | **~20 / ~60–90 / ~170–225 g** | E3.2 |
| Escalones equivalentes en pinza | **pulgar 12 u ≈ índice 4 u ≈ medio 3 u** | E3.6b/c |
| `k_local` (contra apoyo rígido) | 7–39 g/count según dedo, sentido y fuerza | E3.1 |

**Reparto en modo 1: el pulgar hace el ajuste fino, el índice sostiene.** El pulgar
resuelve 3× mejor (mapa `POS↔ANGLE` comprimido × contacto más blando).

### Dinámica
| | Índice | Pulgar |
|---|---|---|
| Retardo comando → fuerza | 52 ms | 61 ms |
| `τ` | ≲ 46 ms | ≲ 65 ms |
| `L/τ` | 1.1 | 0.9 |
| **Retardo total del lazo** | **52–82 ms** | **61–92 ms** |

**Planta dominada por el retardo** (`L/τ ≈ 1`): subir `Kp` no acelera, oscila.
**Periodo de control ≥ 30 ms** — la mano publica cada 30.7 ms pase lo que pase.

### Tara
- **Nunca tarar antes de 10 s tras soltar** (salto de 21–46 g, recuperación +6 g/s).
- Re-tara térmica casi innecesaria (6–7 g contra 20–90 g de resolución).
- **El offset es por DOF y con signo opuesto** (índice −46 g, pulgar +21 g).

### Restricción dura
**`FORCE_SET` siempre por encima del rango de trabajo.** Si `FORCE_ACT` lo alcanza,
el dedo **deja de aceptar `ANGLE_SET` en los dos sentidos**: el paro del firmware
secuestra la posición. El techo real debe ser el del lazo.

---

## 3. La arquitectura: coordenadas de apriete, no fuerza por dedo

Este es el cambio estructural. E3.6b lo estableció: **el comando de un dedo no
comprime el objeto contra el otro, lo empuja**, y el objeto se va con él. Por eso
el cruce es solo 14–34 % y por eso un lazo de fuerza por dedo **gasta la mayor
parte de su acción moviendo el objeto dentro de la pinza**.

Las coordenadas naturales del modo 1 son:

- **Apriete** (`u_s`): los dos dedos en sentidos **opuestos** → cambia la fuerza de agarre.
- **Traslación** (`u_t`): los dos en el **mismo** sentido → mueve el objeto sin cambiar la fuerza.

**Dos lazos, no dos lazos de fuerza:**

| Lazo | Variable regulada | Salida | Qué consigue |
|---|---|---|---|
| **Apriete** | `F_grip` | `u_s` | La fuerza de agarre |
| **Balance** | `F_T − F_I` (desbalance) | `u_t` | Mantiene el objeto centrado |

**`F_grip = min(F_T, F_I)`** como primaria: es el menor normal el que limita la
resistencia al deslizamiento. Registra también la media para comparar; si `min`
resulta ruidosa, la media es la alternativa.

> **Trampa medida, y hay que manejarla.** E3.6b anotó que *«sin sostener nada, las
> fuerzas de los dos dedos no son comparables entre sí»*: 124/127 g en una tanda y
> 123/195 g en otra, con el mismo procedimiento. Así que **el lazo de balance no
> debe llevar `F_T − F_I` a cero**, sino **al desbalance registrado al establecer
> el agarre**. Llevarlo a cero movería el objeto persiguiendo un offset de sensor.

Mapeo a comandos, con las equivalencias de E3.6b/c (pulgar 12 u ≈ índice 4 u):

```
Δq_T = g_T · ( u_s + u_t )
Δq_I = g_I · ( u_s − u_t )      # signos según qué sentido cierra cada dedo
g_T / g_I ≈ 3    (12 u pulgar ≈ 4 u índice)
```

Luego se aplica el **cuanto por sentido** (5 u cerrando / 3 u abriendo) y el
redondeo, por dedo.

---

# PARTE A — MODO 1 (pulgar + índice)

## Reglas de trabajo (toda la Parte A y B)

- **Por fases, con hardware en el lazo.** Tú escribes, yo corro, te devuelvo datos.
  **No avances de fase sin mis resultados.**
- **Módulo nuevo en `Control/`, sin PyQt.** Un proceso, un hilo, un cliente Modbus.
  `time.perf_counter()`.
- **Reutiliza**: `Caracterizacion/hand_modbus.py`; la guarda de seguridad de
  `exp2_force_overshoot.py`; y sobre todo **la máquina de fases de
  `exp3/exp3_coupling.py`** (agarre con persona en el lazo → operación → soltar),
  que ya resuelve establecer el agarre.
- **Muestra fresca**: sondea rápido, **actualiza el control solo cuando el registro
  cambia**. Integrar sobre duplicados infla `Ki` ~18×. Loguea la tasa de frescas.
- **`--hold 5:0` obligatorio en todo lo que toque el pulgar.** Sin anclar la
  rotación describe otra trayectoria; si la salida dice `Anclado: —`, está mal.
- Salida por cualquier vía → **abrir la mano**. `try/finally`.
- CSV por trial: `t`, `fresh`, `F_T`, `F_I`, `F_grip`, `err_s`, `err_b`, `u_s`,
  `u_t`, `Δq` por dedo, `POS` por dedo, `CURRENT`, `TEMP`, flags.

---

## A0 — Recon (sin código)

Ya conoces la caracterización; esto es solo lo que el módulo nuevo necesita:

1. Lee `exp3/exp3_coupling.py` (máquina de fases, re-ajuste **por dedo**,
   dimensionado de escalones), `exp3/exp3_ceiling_check.py` (detección del
   resbalón), `exp3/exp3_hold_drift.py` (política de tara),
   `Caracterizacion/hand_modbus.py` y `herramientas/camara.py`.
2. Repórtame: cómo establece el agarre `exp3_coupling.py` y qué de eso es
   reutilizable tal cual; cómo detecta el resbalón `exp3_ceiling_check.py`; si hay
   detección de muestra fresca ya implementada; y qué techos de guarda se usan.
3. **Para y espera mi OK.**

---

## A1 — Andamiaje, seguridad y detección de resbalón

Controlador **desactivado**. Lo que se construye es la infraestructura.

- Lazo con sondeo rápido + **actualización solo en muestra fresca**; reporta tasa
  de sondeo, de frescas y jitter.
- **Modo `--passthrough`**: trayectoria predefinida sin realimentación.
- **Guarda de seguridad** con techo de fuerza, corriente, timeout y apertura.
- **Detector de resbalón del actuador** (nuevo, y es el que sustituye al tope fijo):
  `POS` retrocede contra su propio comando > **10 counts** en < 0.5 s.
  Normal es 0–2; el resbalón es ~50. El umbral de 10 es inequívoco.
- **Detector de deslizamiento del objeto** (distinto del anterior, y se confunden):

  | | `POS` | Fuerza |
  |---|---|---|
  | **Resbalón del actuador** | retrocede contra el comando | cae |
  | **Objeto que se escapa** | sin cambio (o sigue el comando) | cae en **los dos** dedos a la vez |

  Los dos se ven como caída de fuerza; **`POS` es lo que los separa**. La reacción
  es opuesta: ante resbalón del actuador, **aflojar** (ya se pasó del borde); ante
  objeto que se escapa, **apretar** (o abortar).
- **Política de tara**: tara solo con la mano abierta y descargada **≥ 10 s**.
  Bloquea la tara si el último `release` fue hace menos.

**Compuerta A1:**
1. Tasa de frescas ≈ 33 Hz y el detector no cuenta duplicados.
2. Guarda dispara con techo bajo y dedo lejos del objeto.
3. **Detector de resbalón validado**: llevar un dedo por encima del techo contra el
   cubo y confirmar que dispara antes de que el lazo pueda reaccionar mal.
4. Ctrl-C deja la mano abierta.

---

## A2 — Lazo SISO contra bloque · **figura de cabecera**

**Contra el bloque apoyado, no en pinza.** Ahí es donde están medidas E3.1–E3.5, y
la comparación con el firmware es limpia porque el objeto no se mueve.

```
solo si hay muestra fresca:
  e[k]    = F* − F[k]
  P[k]    = Kp·e[k]
  I[k]    = λ·I[k−1] + Ki·e[k]·dt_fresh        # λ < 1 → FUGA
  Δq[k]   = cuantiza( P[k] + I[k] )            # 5 u cerrar / 3 u abrir
  q[k]    = clip( q[k−1] + Δq[k], lim )
```

- **`dt_fresh` es el tiempo entre muestras frescas (~30 ms)**, no el del sondeo.
- **Fuga en el integrador (`λ`), no guarda de posición.** E3.4: la caída se agota en
  pocos segundos y el actuador **no cede** (0 a −2 counts). Un integrador sin fuga
  perseguiría indefinidamente una caída que ya paró.
- **Banda muerta** de al menos el cuanto del dedo (~20 g pulgar, ~90 g índice).
- **Cuantización asimétrica**: el mismo escalón no vale en los dos sentidos.
- **Sintonía conservadora**: `L/τ ≈ 1`. Empieza con P puro, sube `Kp` hasta el
  primer indicio de oscilación, retrocede, y recién entonces añade `Ki`. Bitácora.
- Sintoniza en **índice** y en **pulgar** por separado; `F* = 250` y `450 g`.

> **El índice no puede ganar esta compuerta a `F* = 250`, y está medido.** Su
> ganancia depende del punto de trabajo: a ~150 g un escalón de cierre de 3 u
> mueve la fuerza **+1, +4, −4, +1, +1, −2 g** (nada, el paso se absorbe en la
> holgura), mientras que a ~357 g el mismo paso vale **+66 g**. O sea: a 250 g el
> dedo está en zona muerta y el PI no puede afinar hacia arriba, y donde sí
> responde la resolución es ~60 g. El pulgar (~20 g por cuanto) es el dedo con
> resolución para esta consigna. Esto es justo el caso de uso del estimador de
> A4: la ganancia no es constante del dedo, es función del punto de trabajo.

**Compuerta A2 — protocolo intercalado (§8), N ≥ 10 por brazo:**
- **Brazo A (firmware):** consigna por `FORCE_SET`, modo A a `v = 25`.
- **Brazo B (lazo):** misma consigna con el PI.

Métricas: sobreimpulso, asentamiento, **error en régimen tras 60 s**.
**Criterio:** el lazo mantiene `F*` donde el firmware decae 5–10 %.

> ~~y lo hace **consumiendo corriente**, que es la prueba directa de que hay par
> activo donde antes había 0 mA~~ — **retirado, y medido por qué.** El índice
> consume 31–92 mA moviéndose y **exactamente 0 mA sosteniendo 160 g**: la mano
> retiene por fricción de una transmisión no retrodrivable. Un PI que manda
> posiciones y se detiene acaba a 0 mA igual que el firmware, así que el criterio
> no es alcanzable para **ninguno** de los dos brazos y no separa nada. La
> ventaja del lazo sólo puede estar en dónde se para y en volver a corregir
> cuando la fuerza deriva. Ver `../regulador_results.md`, «bloque piloto».

> **Sé honesto con el cuanto.** Si la resolución del dedo es 90 g y `F* = 250`, un
> criterio de ±10 % (25 g) es **físicamente inalcanzable**. Reporta el error en
> régimen **en unidades de cuanto**, no solo en gramos.

---

## A3 — Pinza real: coordenadas apriete / balance

Aquí entra §3. Objeto: **bola de espuma de 7 cm** (la de E3.6b, para comparar).

- **Fase de agarre** reutilizando `exp3_coupling.py`: persona sostiene, mano tara,
  cierra a `v=25`, congela cada dedo al tocar. Registra el **desbalance inicial**
  `F_T − F_I` — es la referencia del lazo de balance, no el cero.
- **Lazo de apriete** sobre `F_grip = min(F_T, F_I)` → `u_s`.
- **Lazo de balance** sobre `F_T − F_I` → `u_t`, con referencia el desbalance inicial.
- **Ganancia del balance mucho menor que la del apriete**: mueve el objeto, y su
  urgencia es baja. Empieza con el balance **desactivado** y actívalo después.
- **Escalones equivalentes**: pulgar 12 u ≈ índice 4 u. Aplica `g_T/g_I ≈ 3`.

**Compuerta A3:**
1. `F_grip` se mantiene 60 s dentro de la banda muerta.
2. **La traslación del objeto baja respecto a un lazo por dedo.** Mide con
   `exp3_track_object.py` y la cámara a ras de mesa (la cenital es ciega a ese
   movimiento — sin subpíxel el resultado siempre sale "no se mueve").
3. Comparación explícita: **dos lazos de fuerza por dedo** contra **apriete+balance**,
   intercalados. La métrica que los separa no es la fuerza, es **cuánto se mueve el
   objeto**.

---

## A4 — Estimador de ganancia en línea (RLS) + scheduling

- **`k_local` del banco NO se traslada a la pinza.** En pinza la ganancia efectiva
  es menor en la proporción en que el objeto se mueva. El estimador es la **única**
  forma de tener el número correcto.
- **Mínimos cuadrados recursivos** de `ΔF` contra `Δpos` sobre las últimas N
  acciones **del propio lazo**. Nada de escalones de sondeo: sobre 600 trials, el
  15 % dan `Δpos = 0` y el 38 % menos de 3 counts, y un escalón lo bastante grande
  para medir bien inyecta 300–400 g.
- **Congela la ganancia mientras `Σ|Δpos| < ~5 counts.**
- **Scheduling continuo, sin punto de ruptura fijo**: el codo está en sitios
  opuestos (pulgar se endurece bajo 500 g, índice encima).

> **Matiz que conviene recoger en la memoria.** Filtrando al rango **sostenible**,
> los dos dedos no se comportan igual: el pulgar triplica su `k_local` entre 242 y
> 476 g (7.5 → 22.9), mientras el índice está **plano** entre 132 y 332 g
> (21.6 → 17.4) — su endurecimiento a 39.0 aparece a ~838 g, por encima del techo y
> en transitorio. **El scheduling es sobre todo una necesidad del pulgar**, que es
> justamente quien hace el ajuste fino. El argumento es más preciso que
> "1.7–3.7× en los dos dedos", y un jurado que cruce E3.1 con el techo hará esa cuenta.

**Compuerta A4:** un solo controlador, **sin resintonizar**, cumple A3 con la bola
**y** con el cubo de PLA.

---

## A5 — Validación multi-objeto y el borde

- **Bola de espuma** (7 cm, 21.6 g), **cubo de PLA** (6 cm, 60.5 g) y un
  **objeto deformable real**. La mandarina se deslizó a 150 g y necesita ~300: el
  **umbral de agarre depende del objeto**, y ese es el caso de uso de la tesis.
- **Búsqueda del umbral de agarre**: bajar `F*` hasta que empiece a deslizar,
  detectar por el detector de A1 y subir. Es la demostración de agarre sin daño.
- **El borde superior**: llevar `F*` hacia el techo y confirmar que el detector de
  resbalón dispara y el lazo **afloja** en vez de insistir.

---

# PARTE B — MODO 2 (pulgar + índice + medio)

## B0 — Qué falta del medio, y qué no

El medio solo tiene **E3.2**. De lo que falta:

- **E3.1, E3.3, E3.4** se pueden extrapolar de sus hermanos (misma familia mecánica,
  `k` 3.02–3.05 en los cinco DOF) — con la reserva anotada.
- **E3.5 no se extrapola**: el signo del salto del cero tras sostener carga es **por
  DOF** y no se predice (índice −46, pulgar +21). El del medio se desconoce.
  **No bloquea**: la política de re-tara es una regla de tiempo (≥10 s) y funciona
  sea cual sea el signo. Solo hace falta medirlo si vas a **compensar** el offset.

**Recomendación:** arranca la Parte B sin más caracterización. Si en B2 aparece un
sesgo persistente en el reparto, entonces mide E3.5 en el medio.

---

## B1 — Coordenadas suma / reparto

**El modo 2 no es "el modo 1 con un dedo más": cambia la física.**

| Mueve | Sentido | → Pulgar | → Índice | → Medio |
|---|---|---|---|---|
| Pulgar | cerrar | — | +9 % | +20 % |
| Pulgar | abrir | — | +47 % | +44 % |
| Índice | cerrar | +8 % | — | **−38 %** |
| Índice | abrir | +2 % | — | **−16 %** |
| Medio | cerrar | +7 % | **−37 %** | — |
| Medio | abrir | +3 % | **−9 %** | — |

**Índice y medio se acoplan en negativo** (signo opuesto a la diagonal en 6/6, 6/6,
6/6 y 5/6 trials). Con el objeto inmovilizado por el tercer dedo, empujar uno no
puede moverlo: la carga **se redistribuye** entre los dos, que comparten la misma
reacción del pulgar.

> **Dos lazos de fuerza independientes sobre índice y medio se pelean de frente:**
> subir la consigna de uno **baja** la fuerza real del otro, que responde subiendo,
> que baja la del primero. No es lentitud — es realimentación positiva en el lazo
> del error. **Esto no se sintoniza: se rediseña.**

**Índice y medio comparten un solo grado de libertad de carga frente al pulgar.**
Las coordenadas son tres:

| Lazo | Variable | Salida | Qué consigue |
|---|---|---|---|
| **Apriete** | `F_grip` = `F_T` contra `(F_I + F_M)` | `u_s` | La fuerza de agarre |
| **Reparto** | `F_I − F_M` | `u_r` | Evita que el objeto se ladee |
| **Traslación** | desbalance frente al pulgar | `u_t` | Centra el objeto |

- El lazo de **apriete** actúa sobre pulgar y sobre la **suma** de índice+medio,
  nunca sobre cada uno por separado.
- El lazo de **reparto** es el que sustituye a los dos lazos independientes.
  Referencia: el reparto **registrado al establecer el agarre**, no 50/50 — E3.6c
  midió que añadir el medio **descarga el índice** (73 g contra 127–195 en modo 1),
  así que el reparto natural es desigual.
- **Ganancia del reparto baja**: decide el ladeo, no la seguridad del agarre.

**Dimensionado**: pulgar 12 u, índice 4 u, medio 3 u (E3.6c).
**Secuencia de agarre**: el medio **llega el último y por dependencia geométrica**
(tocó a 6.78 s contra 6.16 del índice) — solo alcanza el objeto una vez que el
índice está en su sitio. La máquina de agarre debe esperarlo, no asumir simultaneidad.

**Compuerta B1:**
1. `F_grip` sostenida 60 s dentro de banda.
2. **El reparto no diverge.** La prueba decisiva: correr también la versión ingenua
   (dos lazos de fuerza independientes sobre índice y medio) y **mostrar que oscila
   o diverge**. Ese contraste es un resultado de tesis, no un fallo — documenta la
   degradación, no la arregles.
3. Objeto sin ladearse (seguimiento subpíxel).

---

## B2 — Validación del modo 2

- **Bola de espuma** y **cubo de PLA**, mismo `F*` y mismos escalones.
  La estructura de la matriz es la misma con los dos; solo la ganancia sube 1.2–1.5×.
  **Si la estructura cambia, algo está mal en el montaje.**
- **Objetos alargados**: el cargador de móvil (82.4 g) exigió **745/179/637 g** para
  no girar, contra 295/179/341 del cubo (60.5 g). Las tres yemas agarran casi en
  línea, así que un objeto alargado casi no tiene brazo para resistir el par. Es un
  caso duro y vale la pena incluirlo.
- **Comparación modo 1 vs modo 2 sobre el mismo objeto** (el cubo):
  modo 1 pide 279+507 = 786 g con pico de **507 g** e inestable;
  modo 2 pide 295+179+341 = 815 g con pico de **341 g** y estable.
  **Mismo total, pico por dedo un 33 % menor, rotación cerrada.** Es el argumento
  cuantitativo de por qué el modo 2 existe, y sale gratis de esta validación.

---

## 8. Protocolo de comparación (obligatorio en A2, A3, A4, B1)

Dos tandas separadas del **mismo dedo, mismo objeto y misma pose** difirieron en un
**factor 2** por deriva del cero entre tandas. Un hallazgo del repo se publicó, se
retractó y se volvió a establecer por esto.

1. **Una sola tanda**, políticas **intercaladas**.
2. Aleatorización por **bloques balanceados**.
3. Re-tara según política (≥10 s tras soltar) y **registra temperatura**.
4. Reporta **rango además de mediana**, y `p`.
5. **Nunca** compares contra un número de otra tanda o de otro día.
6. En pinza, **la cámara a ras de mesa con seguimiento subpíxel** es parte del
   instrumento, no un extra: sin subpíxel, la medida de traslación siempre sale
   "no se mueve".

---

## 9. Entregables

- `Control/` standalone: lazo con muestra fresca, PI con fuga y banda muerta,
  cuantización asimétrica, guarda + **doble detector de resbalón**, estimador RLS,
  coordenadas apriete/balance (modo 1) y apriete/reparto/traslación (modo 2).
- `Control/README.md` con los modos.
- `Control/regulador_results.md`: bitácora de sintonía, **figura de cabecera**,
  A3 con la comparación de traslación, degradación documentada de la versión
  ingenua en B1, y la comparación modo 1 vs modo 2 sobre el cubo.
- CSV crudos en `Control/data/`.

---

## 10. Orden y compuertas

```
A0 recon
 └─► A1 andamiaje + seguridad + detectores de resbalón
      └─► A2 SISO contra bloque ......... FIGURA DE CABECERA
           └─► A3 pinza: apriete + balance
                └─► A4 estimador RLS + scheduling
                     └─► A5 validación multi-objeto y borde
                          └─► B0 (decisión: ¿medir E3.5 del medio?)
                               └─► B1 apriete + reparto + traslación
                                    └─► B2 validación modo 2
```

Cada flecha es una **compuerta con hardware**: yo corro, te devuelvo datos, tú
decides. No adelantes fases.

**Entregable del primer mensaje: SOLO el reporte de A0. Luego para.**
