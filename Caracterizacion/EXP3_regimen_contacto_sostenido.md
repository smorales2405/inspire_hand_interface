# Exp 3 — Régimen de contacto sostenido

**Handoff a Claude Code.** Continúa la caracterización dinámica de la Inspire
RH56DFTP por Modbus TCP (`192.168.124.210:6000`, mano derecha).

> Asumo que ya conoces el repo y las campañas previas: Exp 0/1/2, los cinco DOF,
> la migración a TCP, el hallazgo de la cadencia de ~33 Hz, la retractación del
> "setpoint seguro" del índice y el hallazgo de la rigidez del montaje. **No hace
> falta fase de recon.** Reutiliza `Caracterizacion/hand_modbus.py`,
> `exp2/exp2_force_overshoot.py` (guarda de seguridad, `--probe`, `--ab`) y
> `pose_check.py`.

---

## 1. Por qué existe este experimento

El siguiente paso de la tesis es un **regulador de fuerza de agarre en lazo
cerrado**: un PI externo que convierte el error de fuerza en **incrementos de
posición** y los aplica de forma continua, porque el firmware de la mano no es un
regulador sino un **paro de un solo disparo** (sobrepasa y se relaja a contacto
pasivo). Ese lazo operará así:

- **ya en contacto**, nunca en impacto;
- a **`v <= 25`**, con incrementos de ~2 counts por tick;
- actualizando **solo en muestra fresca** (~33 Hz, ~30.7 ms);
- **sosteniendo** la fuerza durante segundos o minutos.

**El problema:** todo el Exp 2 caracteriza el **impacto** — qué pasa cuando el
dedo llega rápido y el firmware intenta frenar. El regulador **reemplaza** ese
régimen. El régimen en el que el PI realmente vive está **casi sin caracterizar**,
y sin esos números la sintonía sería a ciegas.

### Lo que este experimento NO es

**No completes los grids de 175 celdas del anular ni del meñique.** Son decenas de
horas de banco para describir mejor un comportamiento que el controlador va a
sustituir. El rendimiento marginal para la tesis es bajo. Exp 3 es corto: sondeos
y tandas de N pequeño, sin grids.

**Ventaja de seguridad:** todo Exp 3 corre a `v <= 25` desde contacto establecido,
así que es intrínsecamente mucho menos violento que los grids de impacto. El
riesgo cambia de naturaleza: ya no es el golpe, es el **calentamiento y la carga
sostenida**.

---

## 2. Alcance: la restricción cinemática manda

Observación de banco, verificada con la mano física: **con el pulgar totalmente
rotado en oposición, solo alcanza al índice**. No hay forma de que el pulgar
flexionado toque el medio sin un objeto de por medio; para que haya pinza contra
el medio hace falta que el índice participe.

Esto **no es una peculiaridad del montaje**: es una propiedad documentada de esta
familia de manos. Tan, Xie & Correll (arXiv 2603.08988) reportan que el rango
alcanzable es **(0, 110) mm para la pinza de 2 dedos** pero **(7, 100) mm para las
de 3, 4 y 5 dedos** — con dos dedos el cierre llega a 0 mm (se tocan), con tres o
más el mínimo es 7 mm. Y su Figura 1 muestra que el workspace del pulgar tiene una
**región de intersección muy limitada** con los demás dedos. Es citable.

### Los tres modos de agarre reales

| Modo | Dedos | Tipo de cierre |
|---|---|---|
| **1** | Pulgar + índice | Oposición activa (2 actuadores enfrentados) |
| **2** | Pulgar + índice + medio | Oposición activa (3 actuadores) |
| **3** | Índice / medio / anular / meñique contra la **palma** | **Unilateral** (la palma es pasiva) |

**El modo 3 es un problema de control distinto.** En 1 y 2 hay dos o tres dedos
con sensor de fuerza midiendo sobre el mismo objeto, y sus lazos pueden pelearse.
En el 3 cada dedo presiona contra una superficie **pasiva**: no hay actuador
enfrentado, solo el táctil palmar (z16) como testigo, y cada lazo es independiente
salvo por el objeto.

**Alcance decidido:** el regulador se diseña para los **modos 1 y 2** (agarres de
precisión con oposición), que son los relevantes para ensamblaje con piezas
delicadas y donde está el aporte de control. El modo 3 queda como demostración
adicional, no como objetivo de diseño.

### Qué DOF se caracterizan aquí

**Pareja principal: índice (DOF 3) + pulgar (DOF 4).** Son el par en oposición de
los modos 1 y 2 — en el modo 2 el medio se suma, pero el par opositor sigue siendo
el mismo.

La justificación técnica: las pruebas de Exp 3 son de dos familias.

- **Propiedades del actuador** (E3.2 cuanto mínimo, E3.5 deriva del cero): índice,
  medio, anular y meñique ya demostraron ser la misma familia mecánica (`k` entre
  3.02 y 3.05 en los cinco DOF). Medir los cuatro aporta poco.
- **Propiedades del contacto** (E3.1 rigidez local, E3.3 planta en contacto): varían
  con el objeto y el montaje **mucho más** que entre dedos hermanos — el propio
  repo lo demostró al apretar el soporte del meñique (4.76 -> 12.87 g/count).

El **pulgar es obligatorio** en todas: es el único mecánicamente distinto (otro
rango, la rigidez más baja del conjunto ~5.7 g/count, y el único cuya `k` se movió
un 1.7 % entre transportes).

**Spot-check en el medio (DOF 2):** correr **solo E3.2** también en el medio. Es
el único con protocolo completo por TCP, `k_c` bien medido (12.11) y piso de `F*`
bajo (~73 g). Cuesta una tanda y permite **afirmar** que el cuanto mínimo
generaliza a la familia en vez de suponerlo — el mismo patrón de verificación por
muestreo que ya funcionó.

---

## 3. PRERREQUISITO BLOQUEANTE — sondeo libre del índice

**Esto va primero, antes que cualquier otra prueba.**

El índice es hoy el DOF **peor caracterizado de los cinco**: su `k_c` pasó de 1.6 a
8.45 g/count, su onset geométrico se fijó a ojo (`POS ~1200`) sobre un sondeo sin
curva libre de referencia, y es el único que no pasó por el pipeline de los demás.

Mientras solo era un dedo más, eso era "la medición pendiente de mayor valor".
**Ahora que el índice representa a los cuatro dedos de su familia y es la mitad del
par en oposición, es un prerrequisito.** Todas las demás pruebas dependen de su
onset, su `k_c` y su curva de residual.

**Procedimiento:**
1. `--probe --no-block` con el bloque **desmontado** -> curva libre del índice
   (residual de flexión vs `POS`).
2. `--probe` con el bloque **sujeto** (apretado, no suelto — ver el hallazgo del
   meñique) -> onset geométrico, `k_c`, distancia de frenado.
3. Derivar: residual en el onset, **piso de `F*`**, `--start-angle`,
   `--approach-angle`.
4. Celda de validación (`v=250, Fset=500`) confirmando 0 abortos y `f_base` muy por
   debajo de `Fset`.

**Entregable:** fila del índice completa y comparable en la tabla de geometría de
contacto de los cinco DOF.

**P2 (opcional, barato):** re-sondeo del **pulgar con el bloque sujeto**. Su bloque
se movió al menos dos veces, así que sus `k_c` y ΔF son **cotas inferiores**. Un
sondeo con el montaje apretado les quita esa reserva.

---

## 4. Reglas de trabajo

- **Por fases, con hardware en el lazo.** Tú escribes el código, yo lo corro en la
  mano y te devuelvo los datos. **No avances de prueba sin mis resultados.**
- Un proceso, un hilo, un cliente Modbus. GUI cerrada. `time.perf_counter()`.
- **Guarda de seguridad activa siempre**: techo de fuerza, corriente, timeout,
  apertura en abort. Reutiliza el patrón ya probado, no inventes uno nuevo.
- **Vigilancia térmica nueva y obligatoria** (§5): estas pruebas sostienen carga.
- **Muestra fresca:** sondea rápido pero registra el flag `fresh` (el registro
  cambió) en cada muestra. Varias métricas de Exp 3 **solo tienen sentido contadas
  en muestras frescas**.
- DOF anclados vigilados por **desviación respecto al baseline**, nunca por valor
  absoluto.
- `forceClb` (reg 1009, palma abierta) al inicio de cada tanda; registra
  temperatura al inicio y al final.
- Constantes que dependan de medición: `TODO`, nunca inventadas.
- Salida por cualquier vía -> **abrir la mano**. `try/finally`.

---

## 5. Seguridad específica de carga sostenida

Exp 2 llegó a 50–52 °C con impactos breves. Aquí se mantiene fuerza durante
minutos, así que:

- **Techo de temperatura**: aborta y abre si `TEMP` supera un límite (parámetro,
  `TODO`; arranca conservador respecto a los 52 °C ya vistos).
- **Vigilancia de corriente sostenida**: corriente alta continuada indica el
  actuador aguantando contra el objeto. Define un límite y un tiempo máximo.
- **Enfriamiento entre tandas**: abre la mano y espera entre repeticiones largas.
  Registra `TEMP` antes y después de cada una.
- **Límite de posición duro**: en todas las pruebas que empujan contra el objeto,
  fija un `POS` máximo absoluto por encima del onset y **nunca lo cruces**, pase lo
  que pase con la fuerza.

---

## 6. Nota de unidades (afecta sobre todo a E3.1 y E3.2)

Se **lee** `POS_ACT` (0–2000) y se **escribe** `ANGLE_SET` (0–1000), y el mapa **no
es lineal**. Toda la rigidez `k_c` medida hasta hoy está en **counts de `POS`**.
Por tanto **una unidad de comando ~ 2 counts de posición**, y con
`k_c ~ 8–17 g/count` eso son **~16–34 g por unidad de comando**.

Usa la tabla local de `pose_check.py` para convertir en la pose de contacto (el
factor es local, no global). **Reporta siempre en qué unidad está cada número.**

---

# Las pruebas

> **DOF por defecto en todas: índice (3) y pulgar (4).** Única excepción: E3.2
> añade el medio (2) como spot-check.

## E3.1 — Rigidez incremental `k_c(F)`  <- la más importante

**El problema.** El `k_c` que tenemos es una **secante**: `ΔF/Δpos` medida de un
tirón desde el onset hasta el stall. El PI no ve eso; ve la **derivada local** en
su punto de operación. En contactos reales la rigidez crece con la carga (contacto
hertziano, o un montaje que deja de ceder), así que la local y la secante **no
coinciden**, y la local **varía dentro de un mismo agarre**.

**Procedimiento** (por DOF):
1. Cerrar despacio (`v <= 25`) hasta establecer contacto a `F0`.
2. Esperar estabilización (>= 10 muestras frescas ~ 300 ms).
3. Aplicar un escalón pequeño de posición, esperar estabilización, registrar.
4. Volver al nivel anterior y repetir.

- **Niveles `F0`:** 100, 250, 500, 1000 g *(respetando el piso de residual de cada
  DOF, que para el índice sale del prerrequisito §3)*.
- **Escalones:** +2, +5, +10 counts de `POS` (convierte a unidades de comando, §6).
- **N = 5** por combinación `(F0, escalón)`, orden aleatorizado.

**Métricas:** `k_local = ΔF/Δpos` por escalón; curva `k_local` vs `F0` por DOF;
comparación **`k_local` vs el `k_c` secante** del mismo dedo.

**Decisión:**
- Si `k_local` varía **>= 2x** entre `F0 = 100` y `F0 = 1000` **dentro del mismo
  contacto** -> el gain scheduling del regulador debe ir sobre la **rigidez local
  estimada en línea**, no sobre una constante por dedo; y el `k_c` secante **no es
  el número correcto para control**.
- Si es aproximadamente constante -> una constante por contacto basta, y el
  estimador en línea puede ser lento.

---

## E3.2 — Incremento mínimo efectivo (el cuanto real de comando)

**El problema.** La resolución de fuerza del regulador es
`incremento mínimo x k_c`. Si el incremento mínimo fuera 1 count de `POS`, serían
8–17 g. Pero por §6 el cuanto de comando es ~2 counts, y con stiction el cuanto
**efectivo** puede ser peor. Este número **acota la precisión alcanzable del
regulador**, así que hay que medirlo, no asumirlo.

**DOF: índice (3), pulgar (4) y — como spot-check — medio (2).**

**Procedimiento:**
1. Contacto establecido a `F0` en {250, 1000} g.
2. Comandar incrementos de **1, 2, 3, 5, 10 unidades de `ANGLE_SET`**.
3. Registrar si `POS_ACT` cambia, si `FORCE_ACT` cambia, y cuánto.
4. Repetir **en ambos sentidos** (cerrando y abriendo) — el retorno revela juego
   mecánico e histéresis del actuador, que el PI sufrirá al **corregir a la baja**.
5. **N = 10** por combinación (hace falta N para decidir si un incremento pequeño es
   *fiable* y no solo *ocasional*).

**Métricas:** fracción de intentos con movimiento detectable por tamaño de
incremento; `ΔF` medio y mínimo resultante; asimetría cerrar-vs-abrir.

**Entregable:** **incremento mínimo fiable** y el **cuanto de fuerza** resultante,
por DOF y por nivel de carga. Con eso, la tabla de **precisión de fuerza
alcanzable** y la respuesta a: *¿hasta qué `F*` bajo tiene sentido pedirle
precisión al lazo?*

**Criterio del spot-check:** si el medio da el mismo incremento mínimo que el
índice, se declara que el cuanto **generaliza a la familia**. Si difiere, hay que
medirlo por dedo.

> Resultado contraintuitivo que conviene reportar si aparece: **un contacto más
> blando da control de fuerza más fino**, porque el mismo cuanto de posición se
> traduce en menos gramos.

---

## E3.3 — Respuesta al escalón de fuerza *en contacto*

**El problema.** El deadtime de 60–80 ms se midió **en aire**. La dinámica que el
PI controla es otra: de cambio de comando a cambio de `FORCE_ACT` **estando ya en
contacto**. Ese es el modelo de planta con el que se sintoniza.

**Procedimiento:**
1. Contacto establecido a `F0` en {250, 1000} g.
2. Escalón de posición **moderado** (suficiente para una respuesta clara, ~10–20
   counts; ajústalo con `k_c` para no pasarte del techo).
3. Registrar con `fresh` marcado hasta estabilización.
4. **N = 10** por nivel.

**Métricas:** retardo comando->primer cambio de fuerza (**en muestras frescas y en
ms**); constante de tiempo de la subida; si asienta o sigue derivando; comparación
con el deadtime en aire.

**Entregable:** modelo de planta de primer orden con retardo para la sintonía, y el
**retardo total del lazo** = deadtime en contacto + hasta un periodo de publicación.

---

## E3.4 — Decaimiento a comando constante (fluencia y relajación)

**El problema.** Si con el comando congelado la fuerza **decae**, el integrador del
PI empujará indefinidamente y **caminará la posición hacia dentro del objeto** —
exactamente lo que no se quiere con piezas delicadas.

**Procedimiento:**
1. Cierre lento hasta `F0` en {250, 1000} g.
2. **Congelar `ANGLE_SET`.**
3. Registrar **60 s** de `FORCE_ACT`, `POS_ACT`, `CURRENT`, `TEMP`.
4. Abrir, enfriar, repetir. **N = 5** por nivel.

**Métricas:** curva de decaimiento (magnitud total, constante de tiempo, si llega a
meseta); si `POS_ACT` se mueve con el comando fijo (retroceso del actuador);
corriente durante el sostenimiento.

**Decisión:** si el decaimiento es apreciable, el regulador necesita **al menos una**
de estas — banda muerta alrededor de `F*`, **fuga en el integrador**, o guarda de
límite de posición que impida caminar hacia dentro. La prueba dice cuál y con qué
magnitud.

---

## E3.5 — Deriva del cero durante sostenimiento

**El problema.** El `forceClb` deriva con la temperatura. En impactos breves apenas
importa; en un regulador que sostiene fuerza **la deriva del cero se convierte
directamente en error de fuerza**, y el integrador la persigue.

**Procedimiento** (ciclo repetido ~20–30 min, desde actuador **frío**):
1. Abrir, esperar 5 s, registrar **baseline sin contacto** y `TEMP`.
2. Cerrar despacio a `F0 = 500 g`, sostener 60 s.
3. Abrir, esperar 5 s, registrar baseline y `TEMP` de nuevo.
4. Repetir hasta que la temperatura se estabilice.

*(Comparte montaje con E3.4; se puede correr en la misma sesión.)*

**Métricas:** baseline sin contacto vs tiempo y vs `TEMP` (g/min); deriva de la
fuerza sostenida en el mismo periodo; comparación con y sin re-tara.

**Entregable:** **cadencia de re-tara** que el regulador debe aplicar, y si hace
falta compensación por temperatura además de la re-tara.

---

## E3.6 — Acoplamiento en los modos de pinza reales

Reescrito sobre la restricción cinemática de §2: no se prueban parejas
arbitrarias, sino **los dos modos de agarre que la mano realmente permite**.

**E3.6a — Sincronía del refresco (análisis, sin banco).** Antes de tocar nada: con
los logs multi-DOF **que ya existen**, mira los instantes de cambio de los
registros de cada DOF. ¿Los ~33 Hz refrescan los 6 DOF en el **mismo frame** o
**escalonados**? Si van sincronizados, el control multi-dedo es limpio; si van
escalonados, cada lazo ve el estado en un instante distinto y hay que compensarlo.
**Es gratis y se hace primero.**

**E3.6b — Matriz de acoplamiento, modo 1 (pulgar + índice).**
1. Objeto sujeto por pulgar e índice en oposición, contacto establecido en ambos.
2. Escalonar el comando de **uno**, registrar el cambio de fuerza en **ambos**.
3. Repetir invirtiendo el dedo movido. **N = 5** por dirección.

**E3.6c — Modo 2 (pulgar + índice + medio).** Igual, con los tres dedos. Nota
importante que sale de §2: aquí el **medio solo alcanza el objeto porque el índice
también está presente**, así que la geometría de contacto del medio depende de la
del índice. Regístralo.

**Métricas:** matriz `∂F_j / ∂pos_i`; acoplamiento relativo al término diagonal;
si el acoplamiento del modo 2 es mayor que el del modo 1.

**Decisión:** si el acoplamiento cruzado supera ~10–20 % de la diagonal, hace falta
desacoplamiento o control coordinado, no N lazos SISO independientes.

**Modo 3 (dedos contra la palma):** fuera del alcance de diseño (§2). Si se mide,
es como demostración: cierre **unilateral**, sin actuador enfrentado, con el táctil
palmar (z16) como único testigo del otro lado del contacto.

---

## 7. Entregables

- Módulo en `Caracterizacion/exp3/` reutilizando el transporte y la guarda
  existentes; un script por prueba, parametrizado por `--dof`, `--f0`, `--step`,
  `--trials`.
- CSV crudo por trial con el flag `fresh` y `TEMP`.
- `exp3_results.md` con, como mínimo:
  - **fila del índice completa** (prerrequisito §3) en la tabla de los cinco DOF;
  - curva `k_local` vs `F0` y su contraste con el `k_c` secante;
  - **tabla de precisión de fuerza alcanzable** (incremento mínimo fiable x `k_c`)
    y el veredicto del spot-check del medio;
  - modelo de planta en contacto (retardo + constante de tiempo);
  - decaimiento a comando fijo y la mitigación que implica;
  - deriva del cero y la cadencia de re-tara recomendada;
  - sincronía del refresco multi-DOF y las matrices de acoplamiento de los modos 1
    y 2.
- Una sección final **"implicaciones para el regulador"**: qué de esto obliga a
  cambiar el diseño del lazo (scheduling sobre rigidez local, fuga del integrador,
  banda muerta, re-tara, desacoplamiento).
- Una sección **"modos de agarre"** que documente la restricción cinemática de §2
  con la referencia de Tan et al. — es contexto reutilizable para la tesis.

---

## 8. Orden y compuertas

```
§3 PRERREQUISITO: sondeo libre del índice (+ P2 pulgar, opcional)
  --> E3.6a sincronía (análisis de logs existentes, gratis)
  --> E3.2 cuanto mínimo (índice, pulgar, medio)   <- gatea la precisión alcanzable
  --> E3.1 rigidez local (índice, pulgar)          <- gatea el diseño del scheduling
  --> E3.3 planta en contacto (índice, pulgar)
  --> E3.4 + E3.5 (misma sesión: decaimiento y deriva del cero)
  --> E3.6b modo 1  -->  E3.6c modo 2
```

**El sondeo del índice va primero** porque todo lo demás depende de su onset, su
`k_c` y su piso de `F*`, y hoy esos números no son de fiar.

**E3.2 va antes que E3.1** a propósito: si el cuanto efectivo resulta mucho mayor
de lo esperado, los escalones de +2 counts de E3.1 no son ejecutables y hay que
redimensionarlos.

Cada flecha es una **compuerta con hardware**: yo corro, te devuelvo datos, tú
decides. No adelantes pruebas.

**Empieza por el prerrequisito §3** (sondeo libre del índice) y propón el
procedimiento para que yo lo corra.
