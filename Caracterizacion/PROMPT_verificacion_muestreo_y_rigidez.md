# Handoff a Claude Code — Verificación por muestreo (demás dedos) + Rigidez vs. geometría

> Pega este documento completo como primer mensaje en Claude Code. Está escrito
> para el repo `smorales2405/inspire_hand_interface`.

---

## Contexto

Este repo tiene la caracterización dinámica de la Inspire RH56DFTP ya cerrada para
**dos DOF**: índice (DOF 3) y flexión del pulgar (DOF 4). Ver
`Caracterizacion/exp1/exp1_results.md`, `exp1_results_dof4.md`,
`Caracterizacion/exp2/exp2_results.md`, `exp2_results_dof4.md` y
`Caracterizacion/RUNBOOK_pulgar.md`.

**Valores de referencia ya medidos:**

| | Índice (DOF 3) | Pulgar flexión (DOF 4) |
|---|---|---|
| Constante `SPEED_SET`→pendiente `k` | 3.04 counts/s por unidad | 2.99 (−1.6 %) |
| Deadtime comando→sensor | ≈ 69 ms (σ ~15) | ≈ 73 ms (σ ~15) |
| Sobreimpulso de posición | ~0.39 % | ~0.02 % |
| Rigidez de contacto | ≈ **1.6 g/count** | ≈ **6.4 g/count** |
| σ robusta de onset (v=1000) | ~37 counts | 10.0 counts |
| ΔF modo B (Fset 100→1000) | 2, 25, 39, 71, 92 g | 17, 34, 28, 36, 37 g |
| ¿`Fset=100` protege a toda velocidad? | **Sí** (ΔF ≤ 36 g) | **No** (hasta 1397 g) |

**Los dos hallazgos que estos trabajos deben poner a prueba:**

- **H-A:** `k` es una constante del actuador, no del dedo (3.04 vs 2.99 en dos DOF
  de cinemática muy distinta). *Predicción: los demás dedos deben dar ≈ 3.0.*
- **H-B:** la conmutación de velocidad (modo B) es la mitigación que **generaliza**,
  mientras que "usar `Fset` bajo" depende de la **rigidez del contacto** y no
  generaliza. *Predicción: modo B debe dar ΔF pequeño en todos los dedos.*

Hay **dos trabajos independientes** en este handoff. Ejecuta **TRABAJO 1** primero.

---

## Reglas de trabajo (aplican a todo)

- **Reutiliza, no reescribas.** `Caracterizacion/hand_modbus.py`,
  `exp1_step_response.py`, `exp2_force_overshoot.py`, `exp1_analyze.py`,
  `exp2_analyze.py`, `pose_check.py` ya soportan `--dof`. El objetivo es
  **parametrizar y correr**, no crear scripts nuevos salvo que sea imprescindible.
- Un solo proceso, un solo hilo, un solo cliente Modbus. GUI cerrada.
  `time.perf_counter()` para todos los timestamps.
- **DOF anclados:** al mover un dedo, vigila los demás con el patrón `--hold` ya
  existente. La vigilancia va sobre la **desviación respecto al baseline**, nunca
  sobre el valor absoluto (el sensor tiene offset de sesión de hasta ~180 g).
- Techo de fuerza, timeout y apertura en abort **siempre** activos. Al salir, deja
  la mano abierta y en estado seguro.
- No inventes constantes que dependan de una medición real (onset, `--start-angle`,
  residual, techo): márcalas `TODO` hasta tener datos.

---

## FASE RECON (no escribas código todavía)

1. Lee `Caracterizacion/hand_modbus.py`, `exp1/exp1_step_response.py`,
   `exp2/exp2_force_overshoot.py`, `exp2/exp2_analyze.py`, `pose_check.py` y
   `RUNBOOK_pulgar.md`.
2. Repórtame, **sin cambiar nada**:
   - El **mapeo DOF→dedo** real que usa el código (confirma cuáles son meñique,
     anular y medio; yo asumo 0/1/2 pero **verifícalo**, no lo des por hecho).
   - Qué flags aceptan hoy `exp1_step_response.py` y `exp2_force_overshoot.py`
     (`--dof`, `--hold`, `--probe`, `--start-angle`, `--approach-angle`,
     `--hybrid`, `--grid`, `--trials`, `--outdir`, `--read`, …).
   - Si los scripts de análisis (`exp1_analyze.py`, `exp2_analyze.py`) están
     parametrizados por DOF/carpeta o tienen rutas fijas que haya que generalizar.
   - Qué falta para correr un DOF nuevo de punta a punta sin editar código.
   - En `--probe`: exactamente qué reporta (onset, stall, fuerza, corriente) y si
     ya calcula la rigidez `ΔF/Δpos` o hay que añadirlo.
3. **Para y espera mi OK.**

---

# TRABAJO 1 — Verificación por muestreo en los demás dedos

**Objetivo:** confirmar con el **mínimo de corridas** que H-A y H-B se sostienen en
los dedos no caracterizados. Esto **no** es una réplica de la campaña completa: es
una verificación por muestreo, y así debe describirse en la tesis. Solo si falla
se escala a campaña completa.

**Dedos objetivo:** los tres restantes de la mano derecha (meñique, anular, medio).

> **Bloques:** hay tres bloques de distinto tamaño. Se usa el **mismo bloque para
> los tres dedos** siempre que el alcance lo permita; si un dedo necesita otro,
> se anota en `--mount` (p. ej. `--mount b2m1`), porque entonces su `k_c` y su
> distancia de frenado no son comparables con los de los demás sin decirlo.

### V0 — Preparación por dedo (obligatoria, no reutilizable entre dedos)

Cada DOF necesita su propia puesta a punto; **no se pueden reutilizar los números
del pulgar ni del índice**. Réplica reducida del runbook:

- **V0.1 — Mapa `POS`↔`ANGLE`** con `pose_check.py`. Necesario porque la relación
  **no es lineal** y el factor local °/count es propio de cada actuador.
- **V0.2 — Recorrido libre y curva residual(`POS`)**: barrido sin objeto que da la
  fuerza de flexión propia del dedo. Es lo que permite después distinguir contacto
  real de residual, y verificar que `residual(start_pos) < Fset`.
- **V0.3 — Sondeo de contacto con el bloque** (`--probe`, presión mínima). Da el
  **onset geométrico** (donde la fuerza se despega de la curva libre), el stall,
  la **rigidez de contacto** `ΔF/Δpos` y la **distancia de frenado** hasta 100 g,
  además de los `--start-angle` y `--approach-angle` ya en unidades de
  `ANGLE_SET`. Verifica que el stall queda holgadamente antes del tope mecánico
  (si no, el bloque está mal montado).

> **Añadido en el recon:** `--probe` ya calcula todo eso (antes solo daba el
> stall). La métrica que manda no es el `k_c` medio sino la **distancia de
> frenado**: counts desde el onset hasta que la fuerza externa llega a 100 g.
> El contacto del índice tiene **dos fases** —un tramo blando largo y otro duro
> corto— y promediarlas da una pendiente que no describe ninguna de las dos.
> Referencias medidas: índice ~220 counts, pulgar 22–26.
- **V0.4 — Fijar `--start-angle`** y correr **una celda de validación** (p. ej.
  `v=250, Fset=500, N=3`) confirmando: sin abortos, `f_base_g` muy por debajo de
  `Fset`, y desviación de los DOF anclados dentro del techo.

> **Simplificación deliberada del protocolo reducido:** **no** se re-corre la
> campaña de 50 toques de onset por dedo. El punto de conmutación se ancla en el
> **onset geométrico de V0.3** menos un margen fijo. La σ por dedo se mide
> **solo** si se escala a campaña completa.
>
> **Corregido (recon): el margen es 120 counts, no 40.** Los 40 se justificaban
> como "mayor que los 34 del pulgar", pero **el índice necesitó `q_sw ≈ 124`**
> (`exp2_results.md:68`): un margen fijo de 40 habría puesto la conmutación
> *después* del contacto en la campaña que estableció el modo B. A `v=25` la
> pendiente es ~76 counts/s, así que los 80 counts extra cuestan **~1 s por
> trial**, y además dejan el dedo menos flexionado en la pre-posición, o sea
> **menor residual** — la restricción que puede romper la celda `Fset=100`.
> Es el default de `--switch-margin`.

### V1 — Exp 1 reducido: confirmar la constante `k`

- **Dos velocidades: `v=250` y `v=500`.** Ambas caen en el régimen lineal donde se
  ajustó `k` (`v ≤ 500`), así que dan **dos estimaciones independientes** de la
  misma constante. Mismo escalón que las campañas previas (`ANGLE_SET` 1000→300),
  `FORCE_SET=3000`, sin objeto.
- **N = 10 trials por velocidad**, orden aleatorio.
- Métricas por trial (reusar `exp1_analyze.py`): pendiente en el tramo 20–80 % y
  R², latencia, subida, establecimiento, sobreimpulso de posición.
- *(Opcional, barato)* añadir `v=1000` si quieres además el chequeo de saturación.

**Criterios de aceptación de V1** (los tres deben cumplirse):

| Criterio | Umbral |
|---|---|
| `k` (ajuste por el origen, ambas velocidades) | dentro de **±5 %** de 3.04 counts/s |
| R² del tramo lineal, **solo `v ≤ 500`** | **≥ 0.98** |
| Deadtime medio | dentro de **40–110 ms** |
| Sobreimpulso de posición | **< 1 %** |

> **Corregido (recon): el R² se evalúa solo en `v ≤ 500`.** A `v=1000` el
> actuador satura y el propio pulgar da **R² = 0.954** (índice 0.980, justo en
> el borde): aplicar el umbral ahí haría fallar a un dedo que se comporta
> exactamente como la referencia. `exp1_analyze.py` lo hace con `--k-max-speed`
> (def 500) y reporta las velocidades altas como diagnóstico, fuera del
> criterio. El veredicto de los cuatro criterios lo imprime él mismo con
> `--k-ref 3.04`.

### V2 — Modo B reducido: confirmar que el híbrido generaliza

- **Dos `Fset`: 100 y 1000.** No son arbitrarios: `Fset=100` es **la celda que
  delató la divergencia del pulgar** (la más diagnóstica), y 1000 acota el extremo
  superior.
- Aproximación rápida hasta el punto de conmutación de V0.3 (onset geométrico
  − 40), luego cierre a `v=25`. **N = 5 por `Fset`.**
- Métricas: `ΔF = F_max − Fset` (mediana), `F_max`, `F_régimen`, abortos.
- Reutilizar el filtro `drop_glitches` de `exp2_analyze.py` **con su criterio
  asimétrico intacto** (solo filtra a `v ≤ 100`).

**Criterios de aceptación de V2:**

| Criterio | Umbral |
|---|---|
| ΔF mediana en `Fset = 100` | **≤ 100 g** |
| ΔF mediana en `Fset = 1000` | **≤ 150 g** |
| Abortos | **0** |
| Dependencia de `Fset` | ΔF no debe escalar fuertemente con `Fset` |

> **Corregido (recon): el umbral se separa por columna.** Un único ≤ 100 g deja
> **8 g de holgura** contra la referencia: el índice en modo B da mediana
> **92 g** a `Fset=1000` (rango 7–241), así que un dedo idéntico al índice
> podría fallar por ruido. En `Fset=100`, en cambio, las referencias son 2 g
> (índice) y 17 g (pulgar): ahí 100 g es holgadísimo y es además la celda
> diagnóstica, la que delató al pulgar.

### V3 — Decisión: ¿verificado o escalar?

- **Si V1 y V2 pasan en un dedo** → ese dedo queda **verificado por muestreo**.
  Documéntalo como tal; **no** se corre la campaña completa.
- **Si falla cualquier criterio en un dedo** → **escalar solo ese dedo** a
  **campaña completa**, replicando el runbook del pulgar íntegro:
  - Exp 1 completo: 5 velocidades × 20 trials.
  - Sub-experimento de onset: 50 toques a `v=1000`, σ robusta, `q_sw = ceil(3.3σ)`
    anclado en el **onset geométrico** (no en el detectado — ver el hallazgo de
    +111 counts de retardo del pulgar).
  - Exp 2 grid modo A: 7 velocidades × 5 `Fset` × **N ≥ 10** por celda.
  - Modo B: 5 `Fset` × 5 trials.
- Un fallo **no** obliga a escalar los demás dedos: escala solo el que falló.

### V4 — Entregables del Trabajo 1

- `Caracterizacion/exp1/data_dofN/` y `Caracterizacion/exp2/data_dofN_hybrid/`
  por dedo, con el mismo esquema de CSV que las campañas previas.
- Un `verificacion_muestreo_results.md` con: tabla de `k`, deadtime y ΔF de los
  cinco DOF juntos; el veredicto por dedo (verificado / escalado); y la conclusión
  sobre H-A y H-B.
- Actualizar `compare_dof_figure.py` para incluir los DOF nuevos.
- **Redacción:** describir esto como *verificación por muestreo*, nunca como
  "caracterización completa de todos los dedos".

---

# TRABAJO 2 — Rigidez de contacto vs. geometría (solo índice)

**Objetivo:** decidir si la rigidez de contacto es propiedad del **dedo** o del
**contacto**. Hoy tenemos 1.6 g/count (índice) vs 6.4 (pulgar) y lo atribuimos al
dedo — pero los dos tocan el bloque en geometrías distintas, así que la
atribución está confundida.

**Por qué importa para la tesis:** si la rigidez varía **dentro del mismo dedo** al
cambiar la geometría, entonces el hallazgo del pulgar se generaliza a *"la
protección por `Fset` bajo depende de la rigidez del contacto, y por tanto del
objeto"*. Para una tesis sobre agarre sin daño de objetos de **rigidez variable**,
ese enunciado es mucho más fuerte que "el pulgar difiere del índice".

### G1 — Diseño

**Un solo DOF (índice, DOF 3), un solo bloque** — el mismo rectangular rígido de
las campañas previas. Lo único que cambia es **cómo** se toca.

**3 geometrías**, elegidas para variar el ángulo de flexión en el contacto y el
punto de la falange:

| Geo | Descripción | Qué cambia |
|---|---|---|
| **G-A** | Bloque en la posición **original** del Exp 2 (referencia) | reproduce 1.6 g/count |
| **G-B** | Bloque **más cerca** de la palma → contacto con el dedo **más flexionado** | mayor ángulo de flexión, otro brazo de palanca, otro °/count local |
| **G-C** | Contacto sobre una **arista/borde** del bloque en vez de la cara plana | área de contacto mucho menor |

*(Si G-C resulta inestable o el bloque se mueve, sustitúyela por: bloque más
**lejos**, contacto con el dedo más extendido.)*

### G2 — Medición

Para **cada geometría**:

1. **Documenta el montaje con foto** antes de medir (mismo patrón que
   `Caracterizacion/tactil/load1/`). Guárdalas en
   `Caracterizacion/exp2/geometrias/`.
2. Corre `exp2_force_overshoot.py --dof 3 --probe` **N = 5 veces sin desmontar**
   → repetibilidad de la *medición*.
3. **Desmonta y vuelve a montar** la misma geometría, repite N = 5 → varianza de
   *montaje*. (Dos montajes por geometría.)
4. Registra por probe: `onset_pos`, `stall_pos`, fuerza en onset y en stall,
   corriente máxima, y el **`ANGLE` local en el contacto**.

**Rigidez:** `k_c = ΔF / Δpos` entre onset y stall. **Registra también el `POS`
(y el ángulo) del contacto**, porque es el confound que explica la variación: a
distinta flexión, el factor local °/count y el brazo de palanca cambian.

> Si `--probe` aún no calcula `k_c`, añádelo ahí (no en un script nuevo) y
> haz que lo reporte junto con onset y stall.

### G3 — Análisis y criterio de decisión

Tabla: geometría × (k_c medio ± σ intra-montaje, σ inter-montaje, `POS` de contacto).

| Resultado | Interpretación | Consecuencia para la tesis |
|---|---|---|
| `k_c` varía **≥ 2×** entre geometrías del **mismo dedo** | La rigidez es propiedad del **contacto**, no del actuador | **Reencuadrar:** "la protección por `Fset` bajo depende de la rigidez del contacto/objeto". Argumento fuerte para el regulador adaptativo. |
| `k_c` varía **< 1.5×** y la σ inter-montaje es pequeña | La rigidez sí es en buena medida del dedo | Mantener la atribución actual, pero declarar el rango de geometrías probado |
| Resultado intermedio | Ambos factores pesan | Reportar los dos y acotar la afirmación |

**Regla de honestidad:** si la σ inter-montaje resulta comparable a la variación
entre geometrías, el experimento **no discrimina** — dilo explícitamente en vez de
forzar una conclusión, y propón un jig más rígido.

### G4 — Entregables del Trabajo 2

- `Caracterizacion/exp2/geometrias/` con CSV crudos y fotos por geometría.
- `rigidez_vs_geometria_results.md`: tabla, figura `k_c` vs `POS` de contacto,
  veredicto según G3 y la **redacción propuesta** del reencuadre si aplica.
- Si el veredicto es "propiedad del contacto": propón el texto corregido del
  hallazgo 3 de `exp2_results_dof4.md`, que hoy dice "menos inercia / rigidez del
  dedo".

---

## Orden de ejecución

1. **FASE RECON** → para y espera OK.
2. **TRABAJO 2 (rigidez vs geometría)** — es más corto (solo probes, sin grids) y
   su resultado puede **reencuadrar la redacción** del Trabajo 1.
3. **TRABAJO 1**, dedo por dedo: V0 → V1 → V2 → V3. Espera mis datos entre fases.

**Entregable del primer mensaje: SOLO el reporte de la FASE RECON. Luego para.**
