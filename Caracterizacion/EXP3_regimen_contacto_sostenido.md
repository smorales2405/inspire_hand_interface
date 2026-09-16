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
- a **`v ≤ 25`**, con incrementos de ~2 counts por tick;
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

**Ventaja de seguridad:** todo Exp 3 corre a `v ≤ 25` desde contacto establecido,
así que es intrínsecamente mucho menos violento que los grids de impacto. El
riesgo cambia de naturaleza: ya no es el golpe, es el **calentamiento y la carga
sostenida**.

---

## 2. Reglas de trabajo

- **Por fases, con hardware en el lazo.** Tú escribes el código, yo lo corro en la
  mano y te devuelvo los datos. **No avances de prueba sin mis resultados.**
- Un proceso, un hilo, un cliente Modbus. GUI cerrada. `time.perf_counter()`.
- **Guarda de seguridad activa siempre**: techo de fuerza, corriente, timeout,
  apertura en abort. Reutiliza el patrón ya probado, no inventes uno nuevo.
- **Vigilancia térmica nueva y obligatoria** (§3): estas pruebas sostienen carga.
- **Muestra fresca:** sondea rápido pero registra el flag `fresh` (el registro
  cambió) en cada muestra. Varias métricas de Exp 3 **solo tienen sentido contadas
  en muestras frescas**.
- DOF anclados vigilados por **desviación respecto al baseline**, nunca por valor
  absoluto.
- `forceClb` (reg 1009, palma abierta) al inicio de cada tanda; registra
  temperatura al inicio y al final.
- Constantes que dependan de medición: `TODO`, nunca inventadas.
- Salida por cualquier vía → **abrir la mano**. `try/finally`.

---

## 3. Seguridad específica de carga sostenida

Exp 2 llegó a 50–52 °C con impactos breves. Aquí se mantiene fuerza durante
minutos, así que:

- **Techo de temperatura**: aborta y abre si `TEMP` supera un límite (parámetro,
  `TODO`; arranca conservador respecto a los 52 °C ya vistos).
- **Vigilancia de corriente sostenida**: corriente alta continuada indica el
  actuador aguantando contra el objeto. Define un límite y un tiempo máximo.
- **Enfriamiento entre tandas**: abre la mano y espera entre repeticiones largas.
  Registra `TEMP` antes y después de cada una.
- **Límite de posición duro**: en todas las pruebas que empujan contra el objeto,
  fija un `POS` máximo absoluto por encima del onset y **nunca lo cruces**, pase
  lo que pase con la fuerza.

---

## 4. Nota de unidades (afecta sobre todo a E3.1 y E3.2)

Se **lee** `POS_ACT` (0–2000) y se **escribe** `ANGLE_SET` (0–1000), y el mapa
**no es lineal**. Toda la rigidez `k_c` medida hasta hoy está en **counts de
`POS`**. Por tanto **una unidad de comando ≈ 2 counts de posición**, y con
`k_c ≈ 12–17 g/count` eso son **~24–34 g por unidad de comando** en los dedos
rígidos.

Usa la tabla local de `pose_check.py` para convertir en la pose de contacto (el
factor es local, no global). **Reporta siempre en qué unidad está cada número** y
da los resultados en ambas cuando sea relevante.

---

# Las pruebas

## E3.1 — Rigidez incremental `k_c(F)`  ← la más importante

**El problema.** El `k_c` que tenemos es una **secante**: `ΔF/Δpos` medida de un
tirón desde el onset hasta el stall. El PI no ve eso; ve la **derivada local** en
su punto de operación. En contactos reales la rigidez crece con la carga (contacto
hertziano, o un montaje que deja de ceder), así que la local y la secante **no
coinciden**, y la local **varía dentro de un mismo agarre**.

**Procedimiento** (por DOF):
1. Cerrar despacio (`v ≤ 25`) hasta establecer contacto a `F₀`.
2. Esperar estabilización (≥ 10 muestras frescas ≈ 300 ms).
3. Aplicar un escalón pequeño de posición, esperar estabilización, registrar.
4. Volver al nivel anterior y repetir.

- **Niveles `F₀`:** 100, 250, 500, 1000 g *(respetando el piso de residual de cada
  DOF — en el meñique `F₀ = 100` no es pedible)*.
- **Escalones:** +2, +5, +10 counts de `POS` (convierte a unidades de comando, §4).
- **N = 5** por combinación `(F₀, escalón)`, orden aleatorizado.
- **DOF:** medio (2) primero; luego anular (1) y pulgar (4) para cubrir el rango de
  rigidez conocido (5.7 → 16.6 g/count).

**Métricas:** `k_local = ΔF/Δpos` por escalón; curva `k_local` vs `F₀` por DOF;
comparación **`k_local` vs el `k_c` secante** ya publicado del mismo dedo.

**Decisión:**
- Si `k_local` varía **≥ 2×** entre `F₀ = 100` y `F₀ = 1000` **dentro del mismo
  contacto** → el gain scheduling del regulador debe ir sobre la **rigidez local
  estimada en línea**, no sobre una constante por dedo; y el `k_c` secante **no es
  el número correcto para control**.
- Si es aproximadamente constante → una constante por contacto basta, y el
  estimador en línea puede ser lento.

---

## E3.2 — Incremento mínimo efectivo (el cuanto real de comando)

**El problema.** La resolución de fuerza del regulador es
`incremento mínimo × k_c`. Si el incremento mínimo fuera 1 count de `POS`, serían
6–17 g. Pero por §4 el cuanto de comando es ~2 counts, y con stiction el cuanto
**efectivo** puede ser peor. Este número **acota la precisión alcanzable del
regulador**, así que hay que medirlo, no asumirlo.

**Procedimiento:**
1. Contacto establecido a `F₀` ∈ {250, 1000} g.
2. Comandar incrementos de **1, 2, 3, 5, 10 unidades de `ANGLE_SET`**.
3. Registrar si `POS_ACT` cambia, si `FORCE_ACT` cambia, y cuánto.
4. Repetir **en ambos sentidos** (cerrando y abriendo) — el retorno revela juego
   mecánico e histéresis del actuador, que el PI sufrirá al corregir a la baja.
5. **N = 10** por combinación (hace falta N para decidir si un incremento pequeño
   es *fiable* y no solo *ocasional*).

**Métricas:** fracción de intentos con movimiento detectable por tamaño de
incremento; `ΔF` medio y mínimo resultante; asimetría cerrar-vs-abrir.

**Entregable:** **incremento mínimo fiable** y el **cuanto de fuerza** resultante,
por DOF y por nivel de carga. Con eso, la tabla de **precisión de fuerza
alcanzable** y la respuesta a: *¿hasta qué `F*` bajo tiene sentido pedirle
precisión al lazo?*

> Resultado contraintuitivo que conviene reportar si aparece: **un contacto más
> blando da control de fuerza más fino**, porque el mismo cuanto de posición se
> traduce en menos gramos.

---

## E3.3 — Respuesta al escalón de fuerza *en contacto*

**El problema.** El deadtime de 60–80 ms se midió **en aire**. La dinámica que el
PI controla es otra: de cambio de comando a cambio de `FORCE_ACT` **estando ya en
contacto**. Ese es el modelo de planta con el que se sintoniza.

**Procedimiento:**
1. Contacto establecido a `F₀` ∈ {250, 1000} g.
2. Escalón de posición **moderado** (suficiente para una respuesta de fuerza clara,
   ~10–20 counts; ajústalo con `k_c` para no pasarte del techo).
3. Registrar con `fresh` marcado hasta estabilización.
4. **N = 10** por nivel; DOF medio (2) y pulgar (4).

**Métricas:** retardo comando→primer cambio de fuerza (**en muestras frescas y en
ms**); constante de tiempo de la subida de fuerza; si asienta o sigue derivando;
comparación con el deadtime en aire.

**Entregable:** modelo de planta de primer orden con retardo para la sintonía, y el
**retardo total del lazo** = deadtime en contacto + hasta un periodo de publicación.

---

## E3.4 — Decaimiento a comando constante (fluencia y relajación)

**El problema.** Si con el comando congelado la fuerza **decae**, el integrador del
PI empujará indefinidamente y **caminará la posición hacia dentro del objeto** —
exactamente lo que no se quiere con piezas delicadas.

**Procedimiento:**
1. Cierre lento hasta `F₀` ∈ {250, 1000} g.
2. **Congelar `ANGLE_SET`.**
3. Registrar **60 s** de `FORCE_ACT`, `POS_ACT`, `CURRENT`, `TEMP`.
4. Abrir, enfriar, repetir. **N = 5** por nivel; DOF medio (2) y anular (1).

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
2. Cerrar despacio a `F₀ = 500 g`, sostener 60 s.
3. Abrir, esperar 5 s, registrar baseline y `TEMP` de nuevo.
4. Repetir hasta que la temperatura se estabilice.

*(Comparte montaje con E3.4; se puede correr en la misma sesión.)*

**Métricas:** baseline sin contacto vs tiempo y vs `TEMP` (g/min); deriva de la
fuerza sostenida en el mismo periodo; comparación con y sin re-tara.

**Entregable:** **cadencia de re-tara** que el regulador debe aplicar, y si hace
falta compensación por temperatura además de la re-tara.

---

## E3.6 — Acoplamiento cruzado entre dedos  *(gate de multi-dedo, no de un dedo)*

**El problema.** El objetivo final es controlar los cinco dedos. Hasta ahora los
vecinos se **anclaron y vigilaron**, que no es lo mismo que moverlos a la vez. Si
hay acoplamiento mecánico por la palma o el objeto, N lazos independientes se
pelean entre sí.

**E3.6a — Sincronía del refresco (análisis, sin banco).** Antes de tocar nada:
con los logs multi-DOF **que ya existen**, mira los instantes de cambio de los
registros de cada DOF. ¿Los ~33 Hz refrescan los 6 DOF en el **mismo frame** o
**escalonados**? Si van sincronizados, el control multi-dedo es limpio; si van
escalonados, cada lazo ve el estado en un instante distinto y hay que compensarlo.
**Es gratis y se hace primero.**

**E3.6b — Matriz de acoplamiento.** Objeto agarrado por **2 dedos** (pinza medio +
pulgar) para empezar:
1. Establecer contacto en ambos.
2. Escalonar el comando de **uno**, registrar el cambio de fuerza en **todos**.
3. Repetir invirtiendo el dedo movido. **N = 5** por dirección.
4. Si hay acoplamiento claro, extender a 3 dedos.

**Métricas:** matriz `∂F_j / ∂pos_i`; acoplamiento relativo al término diagonal.

**Decisión:** si el acoplamiento cruzado supera ~10–20 % de la diagonal, hace falta
desacoplamiento o control coordinado, no N lazos SISO.

---

## 5. Pendientes que este experimento aprovecha para cerrar

**P1 — Sondeo libre del índice (DOF 3).** Es la medición pendiente de mayor valor
del repo: su `k_c` pasó de 1.6 a 8.45 g/count y su onset se fijó a ojo, sin curva
libre de referencia. Si el índice va a estar en el lazo, necesita el mismo pipeline
que los otros cuatro: `--probe --no-block` (curva libre) + `--probe` con el bloque
**sujeto**. Da `k_c`, onset geométrico, residual y piso de `F*` comparables.

**P2 — Re-sondeo del pulgar con el bloque sujeto.** Su bloque se movió al menos dos
veces, así que sus `k_c` y ΔF son **cotas inferiores**. Un sondeo con el montaje
apretado les quita esa reserva. Barato.

---

## 6. Entregables

- Módulo en `Caracterizacion/exp3/` reutilizando el transporte y la guarda
  existentes; un script por prueba, parametrizado por `--dof`, `--f0`, `--step`,
  `--trials`.
- CSV crudo por trial con el flag `fresh` y `TEMP`.
- `exp3_results.md` con, como mínimo:
  - curva `k_local` vs `F₀` por DOF y su contraste con el `k_c` secante;
  - **tabla de precisión de fuerza alcanzable** (incremento mínimo fiable × `k_c`);
  - modelo de planta en contacto (retardo + constante de tiempo);
  - decaimiento a comando fijo y la mitigación que implica;
  - deriva del cero y la cadencia de re-tara recomendada;
  - sincronía del refresco multi-DOF y, si se corrió, la matriz de acoplamiento.
- Una sección final **"implicaciones para el regulador"**: qué de esto obliga a
  cambiar el diseño del lazo (scheduling sobre rigidez local, fuga del integrador,
  banda muerta, re-tara, desacoplamiento).

---

## 7. Orden y compuertas

```
E3.6a sincronía (análisis de logs existentes, gratis)
  ──► E3.2 cuanto mínimo   ← gatea la precisión alcanzable
  ──► E3.1 rigidez local   ← gatea el diseño del scheduling
  ──► E3.3 planta en contacto
  ──► E3.4 + E3.5 (misma sesión: decaimiento y deriva del cero)
  ──► P1 índice · P2 pulgar
  ──► [E3.6b acoplamiento — solo si se va a multi-dedo]
```

**E3.2 va antes que E3.1** a propósito: si el cuanto efectivo resulta mucho mayor
de lo esperado, los escalones de +2 counts de E3.1 no son ejecutables y hay que
redimensionarlos.

Cada flecha es una **compuerta con hardware**: yo corro, te devuelvo datos, tú
decides. No adelantes pruebas.

**Empieza por E3.6a** (es análisis de datos que ya existen, sin banco) y luego
propón el script de E3.2 para que yo lo corra.
