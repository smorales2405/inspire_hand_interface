# Runbook — Verificación por muestreo (meñique, anular, medio)

Verificación **por muestreo** de que los dos hallazgos de la caracterización se
sostienen en los tres DOF no caracterizados. **No es una réplica de la campaña
completa** y no debe describirse como tal en la tesis: es el mínimo de corridas
que puede *falsar* H-A y H-B. Solo el dedo que falle escala a campaña completa.

Plan de origen: [`PROMPT_verificacion_muestreo_y_rigidez.md`](PROMPT_verificacion_muestreo_y_rigidez.md).
Campañas de referencia: [`RUNBOOK_pulgar.md`](RUNBOOK_pulgar.md), `exp1/exp1_results*.md`, `exp2/exp2_results*.md`.

## Las dos hipótesis bajo prueba

- **H-A — `k` es del actuador, no del dedo.** 3.042 (índice) vs 2.986 (pulgar),
  dos cinemáticas muy distintas. *Predicción: los tres dedos dan ≈ 3.0.*
- **H-B — la conmutación de velocidad es la mitigación que generaliza**, mientras
  que "usar `Fset` bajo" depende de la rigidez del contacto. *Predicción: modo B
  da ΔF pequeño en todos los dedos, y la distancia de frenado explica quién
  queda protegido por un `Fset` bajo y quién no.*

## Referencias medidas (mano derecha, misma unidad)

| | Índice (DOF 3) | Pulgar flexión (DOF 4) |
|---|---|---|
| `k` (ajuste por el origen, `v ≤ 500`) | **3.042** | **2.986** (−1.8 %) |

> Meñique (DOF 0), medido en esta campaña: **k = 3.046** (+0.2 %), deadtime
> 55.3 ms, R² 0.995, sobreimpulso 0.03 %.
| R² mínimo en `v ≤ 500` | 0.995 | 0.986 |
| Deadtime medio | 69.3 ms | 73.1 ms |
| Sobreimpulso de posición (máx) | 0.393 % | 0.022 % |
| Rigidez de contacto `k_c` | ~1.3–1.6 g/count | 4.2–4.9 g/count |
| **Distancia de frenado hasta 100 g** | **~220 counts** | **22–26 counts** |
| ΔF modo B (`Fset` 100→1000) | 2, 25, 39, 71, 92 g | 17, 34, 28, 36, 37 g |
| ¿`Fset=100` protege a toda velocidad? | **Sí** (ΔF ≤ 36 g) | **No** (hasta 936 g) |

> Los `k` y los criterios los imprime `exp1_analyze.py --k-ref 3.04`; `k_c` y la
> distancia de frenado, `exp2_force_overshoot.py --probe`.

## Reglas

- Un proceso, un hilo, un cliente Modbus, **GUI cerrada**. `/dev/ttyUSB0`
  (ojo: `exp1_step_response.py` tiene `ttyUSB1` por defecto — pásalo siempre).
- **Los vecinos se VIGILAN, no se anclan** (`--watch`, no `--hold`). Medido en el
  meñique el 2026-09-07: anclar el anular lo hace moverse **13–36 counts y tirar
  101–194 mA en cada parada**, y en `950` —bien dentro del rango— sigue igual
  (20–24 counts, 110–136 mA). Sin comandarlo se queda en **0–1 counts y 0 mA**.
  El firmware re-ejecuta el movimiento en **cada** escritura de `ANGLE_SET`, y su
  banda muerta de ~4 counts hace que nunca aterrice exacto, así que cada
  re-afirmación es un empujón real. `--watch` mira la **desviación** de fuerza
  sobre el baseline —nunca el valor absoluto, que tiene offset de sesión— sin
  comandar nada. Detalle: [`exp2/exp2_results_vecinos.md`](exp2/exp2_results_vecinos.md).
- El pulgar **sí** necesitaba `--hold 5:0`: ahí el ancla *define la postura del
  experimento*. Un vecino que solo estorba no necesita ancla ninguna.
- Techo de fuerza, timeout y apertura en abort siempre activos.
- Nada de constantes heredadas de otro dedo: `--start-angle` y `--approach-angle`
  salen del sondeo **de ese** dedo, en **ese** montaje.
- **Bloques:** el mismo bloque para los tres dedos si el alcance lo permite. Si un
  dedo necesita otro, va en `--mount` (`b2m1`, `b3m1`, …): sin esa etiqueta, su
  `k_c` no es comparable con el de los demás y no hay forma de saberlo después.

## Vecinos por dedo

| DOF | Dedo | Espacio libre (V0.1, V0.2, V1) | Con bloque (V0.3, V0.4, V2) | Carpetas |
|---|---|---|---|---|
| 0 | Meñique | sin `--hold` | `--watch 1` | `exp1/data_dof0`, `exp2/data_dof0`, `exp2/data_dof0_hybrid` |
| 1 | Anular | sin `--hold` | `--watch 0,2` | `exp1/data_dof1`, … |
| 2 | Medio | sin `--hold` | `--watch 1,3` | `exp1/data_dof2`, … |

En espacio libre no hay nada que vigilar: sin comandarlos, los vecinos no se
mueven (0–1 counts, 0 mA a lo largo de todo el recorrido del meñique). Con el
bloque montado sí, porque un bloque ancho puede transmitir la carga al vecino —
y eso es precisamente lo que el watchdog tiene que ver.

---

# Sesión A — sin bloque montado

Todo lo que no necesita el bloque, de una sentada. Repite el bloque de comandos
para `N = 0, 1, 2` cambiando `--watch` según la tabla.

### V0.0 + V0.1 — mapeo POS↔ANGLE y confirmación visual del dedo

**Mira la mano mientras corre.** El mapeo DOF→dedo viene del manual y solo está
verificado por vista en 3, 4 y 5; que 0 sea el meñique y 2 el medio está por
confirmar. En el pulgar esa comprobación ya cambió una conclusión publicada.

```bash
.venv/bin/python Caracterizacion/pose_check.py \
    --serial-port /dev/ttyUSB0 --dof N --watch <vecinos> \
    --angles 1000,750,500,250,0 \
    --csv Caracterizacion/exp1/data_dofN/pose_dofN.csv
```

Anota qué dedo se movió. La tabla `POS↔ANGLE` es obligatoria: la relación **no es
lineal** (el índice va de 2.08 a 1.62 counts/grado a lo largo del recorrido) y sin
ella el sondeo no puede dar los ángulos de `--start-angle` / `--approach-angle`.

### V0.2 — recorrido libre y curva residual

```bash
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --serial-port /dev/ttyUSB0 --dof N --probe --no-block
```

Da el tope mecánico (el sondeo con bloque debe parar **antes**) y la curva
`F(POS)` en espacio libre, que es lo que después separa contacto real de residual
de flexión. **Sin esta curva el onset se detecta tarde y `k_c` sale
sobreestimada** — el índice es el ejemplo: sin curva libre su `k_c` aparente es
5.9 g/count y con el onset correcto es 1.3.

### V1 — Exp 1 reducido: la constante `k`

```bash
.venv/bin/python Caracterizacion/exp1/exp1_step_response.py \
    --serial-port /dev/ttyUSB0 --dof N \
    --speeds 250,500 --trials 10

.venv/bin/python Caracterizacion/exp1/exp1_analyze.py \
    --outdir Caracterizacion/exp1/data_dofN --k-ref 3.04
```

`v=250` y `v=500` caen ambas en el tramo lineal, así que son **dos estimaciones
independientes** de la misma constante. El análisis imprime el veredicto de los
cuatro criterios. Opcional y barato: añadir `1000` a `--speeds` para ver la
saturación — sale como diagnóstico, **fuera** del criterio de R².

### (Recomendado) Retro-ajuste del índice

Con el bloque desmontado, un sondeo libre del índice cuesta 15 s y pone su `k_c`
y su distancia de frenado en el mismo pipeline que los demás:

```bash
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --serial-port /dev/ttyUSB0 --dof 3 --probe --no-block
```

Hoy el `1.6 g/count` publicado del índice sale de un onset fijado a ojo
(`POS ~1200`) sobre un sondeo **sin** curva libre. El número es defendible, pero
es el único de los cinco que no vendría del mismo procedimiento.

---

# Sesión B — con bloque, dedo por dedo

Monta el bloque frente al dedo `N` y no lo toques hasta terminar sus tres fases.

### V0.3 — sondeo de contacto

```bash
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --serial-port /dev/ttyUSB0 --dof N --watch <vecinos> --probe --mount m1
```

Reporta onset geométrico, stall, `k_c`, **distancia de frenado hasta 100 g** y los
dos ángulos listos para copiar (`--start-angle`, `--approach-angle`). Comprueba:

- el stall queda **holgadamente** antes del tope libre de V0.2 (si coincide, el
  dedo llegó a su propio final de carrera y **no** al bloque);
- el residual estimado en la pre-posición deja margen contra `Fset=100`.

### V0.4 — celda de validación

```bash
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --serial-port /dev/ttyUSB0 --dof N --watch <vecinos> --mount m1 \
    --start-angle <de V0.3> --cell --speed 250 --fset 500 --trials 3
```

Pasa si: **0 abortos**, `f_base_g` muy por debajo de 500, y la desviación de los
DOF anclados dentro del techo. Si `f_base_g` sube demasiado, retrasa la
pre-posición (el sondeo da el residual estimado como **cota inferior**: en el
pulgar el valor medido quedó ~20 g por encima).

### V2 — modo B reducido

```bash
.venv/bin/python Caracterizacion/exp2/exp2_force_overshoot.py \
    --serial-port /dev/ttyUSB0 --dof N --watch <vecinos> --mount m1 \
    --approach-angle <de V0.3> --hybrid --fsets 100,1000 --trials 5 \
    --outdir Caracterizacion/exp2/data_dofN_hybrid

.venv/bin/python Caracterizacion/exp2/exp2_analyze.py \
    --base Caracterizacion/exp2/data_dofN_hybrid --override '' \
    --out  Caracterizacion/exp2/data_dofN_hybrid
```

`Fset=100` no es arbitrario: es **la celda que delató la divergencia del pulgar**.
1000 acota el extremo superior. El filtro `drop_glitches` actúa aquí (v=25 ≤ 100)
con su criterio asimétrico intacto.

---

## Criterios de aceptación

**V1** (los cuatro; los imprime `exp1_analyze.py --k-ref 3.04`):

| Criterio | Umbral |
|---|---|
| `k` (ajuste por el origen, `v ≤ 500`) | ±5 % de 3.04 |
| R² del tramo lineal, **solo `v ≤ 500`** | ≥ 0.98 |
| Deadtime medio | 40–110 ms |
| Sobreimpulso de posición | < 1 % |

**V2:**

| Criterio | Umbral |
|---|---|
| ΔF mediana en `Fset = 100` | ≤ 100 g |
| ΔF mediana en `Fset = 1000` | ≤ 150 g |
| Abortos | 0 |
| Dependencia de `Fset` | ΔF no escala fuertemente con `Fset` |

Los tres umbrales marcados salen de corregir el plan original con los datos ya
medidos: el R² a `v=1000` haría fallar al propio pulgar (0.954); un ≤ 100 g único
deja 8 g de holgura contra el índice (92 g a `Fset=1000`); y el margen de
conmutación de 40 counts era conservador solo frente al pulgar (34) y no frente al
índice (124), de ahí el default de 120.

## V3 — decisión

- **V1 y V2 pasan** → el dedo queda **verificado por muestreo**. Se documenta así
  y **no** se corre la campaña completa.
- **Falla cualquier criterio** → escala **solo ese dedo** a campaña completa
  (Exp 1 de 5 velocidades × 20, sub-experimento de onset de 50 toques con
  `q_sw = ceil(3.3σ)` anclado en el onset **geométrico**, grid modo A de
  7 × 5 con N ≥ 10, y modo B de 5 `Fset` × 5). Un fallo no arrastra a los demás.

## Entregables

- `exp1/data_dofN/` y `exp2/data_dofN{,_hybrid}/` por dedo, mismo esquema de CSV.
- `verificacion_muestreo_results.md`: tabla de `k`, deadtime, `k_c`, distancia de
  frenado y ΔF de los **cinco** DOF; veredicto por dedo; conclusión sobre H-A/H-B.
- `compare_dof_figure.py` extendido a los DOF nuevos.

## Parámetros medidos

### Meñique (DOF 0)

| | Valor | Fase |
|---|---|---|
| Recorrido `POS` (`ANGLE_SET` 1000→0) | 96 … **1893** (1797 counts) | V0.2 |
| Mapa `POS↔ANGLE` | `exp1/data_dof0/pose_dof0.csv` (5 puntos) | V0.1 |
| Residual de flexión (crudo, sin tarar) | −57 g abierto → +141 g al tope | V0.2 |
| **`k`** | **3.046** counts/s por unidad (+0.2 % vs 3.04) | V1 |
| Deadtime medio | 55.3 ms | V1 |
| R² mínimo (`v ≤ 500`) | 0.9948 | V1 |
| Sobreimpulso de posición | 0.029 % máx | V1 |
| `--start-angle` / `--approach-angle` | TODO (salen de V0.3) | |

`k` sale de dos estimaciones independientes que coinciden al 0.1 %: 3.049
(`v=250`) y 3.045 (`v=500`).

## Estado

| Dedo | V0.1 | V0.2 | V1 | V0.3 | V0.4 | V2 | Veredicto |
|---|---|---|---|---|---|---|---|
| Meñique (0) | ✔ | ✔ | ✔ | ☐ | ☐ | ☐ | V1 pasa los 4 criterios |
| Anular (1) | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | — |
| Medio (2) | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | — |
