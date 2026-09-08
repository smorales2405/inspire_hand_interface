# Verificación por muestreo — resultados

Verificación **por muestreo** de que los dos hallazgos de la caracterización se
sostienen en los DOF no caracterizados. **No es una réplica de la campaña
completa** y no debe describirse como tal: es el mínimo de corridas que puede
falsar H-A y H-B. Plan: [`RUNBOOK_verificacion_muestreo.md`](RUNBOOK_verificacion_muestreo.md).

Mano derecha, GUI cerrada, `/dev/ttyUSB0`. Fechas: 2026-09-07.

---

## H-A — `k` es una constante del actuador · **CONFIRMADA en 5 DOF**

| DOF | `k` | Δ vs 3.04 | Deadtime | R² mín (`v ≤ 500`) | Sobreimpulso | Campaña |
|---|---|---|---|---|---|---|
| 0 Meñique | **3.046** | +0.2 % | 55.3 ms | 0.9948 | 0.029 % | 2 vel × 10 |
| 1 Anular | **3.012** | −0.9 % | 76.7 ms | 0.9948 | 0.044 % | 2 vel × 10 |
| 2 Medio | **3.013** | −0.9 % | 79.7 ms | 0.9960 | 0.139 % | 2 vel × 10 |
| 3 Índice | 3.042 | +0.1 % | 69.3 ms | 0.9949 | 0.393 % | 5 vel × 20 |
| 4 Pulgar flex. | 2.986 | −1.8 % | 73.1 ms | 0.9859 | 0.022 % | 5 vel × 20 |

**Media 3.020 · σ 0.022 · rango 2.986–3.046 · 2.0 % de dispersión total.** Los
tres dedos nuevos pasan los cuatro criterios de V1.

Dentro de cada dedo, `v=250` y `v=500` dan estimaciones independientes que
coinciden al 0.1–0.8 %: la dispersión *entre* dedos es real, no ruido de ajuste,
y aun así cabe holgada dentro del ±5 %. El único que se aparta de forma
apreciable es el pulgar, que es también el único con cinemática y recorrido
distintos: la excepción refuerza la regla.

---

## H-B — la conmutación de velocidad generaliza

### Meñique (DOF 0) — **verificado, con un hallazgo nuevo**

Modo B (aproximación rápida a `POS 1345`, luego cierre a `v=25`), montaje `m2`,
N=5 por celda, 0 abortos, todos los trials con contacto confirmado:

| `Fset` | ΔF mediana | Rango | Fuerza externa mínima |
|---|---|---|---|
| 250 | **50 g** | 32–124 | 245 g |
| 1000 | **111 g** | 91–133 | 1055 g |

Criterio de V2 cumplido (≤ 150 g en `Fset=1000`, 0 abortos). Como referencia, la
celda de validación en **modo A** a `v=250, Fset=500` dio **ΔF = 819 g** en el
mismo montaje: el modo B lo colapsa aunque se le pida un `Fset` el doble de alto.

### El hallazgo: en el meñique `Fset = 100` **no es ejecutable**

No es que proteja mal — es que **no se puede pedir**. El residual de flexión del
propio dedo llega a **117 g en el onset de contacto**, por encima del umbral, así
que el firmware frena en el aire y el trial no llega nunca al bloque. Medido dos
veces, en los dos modos:

| Modo | `Fset` | `f_base` | `F_max` | Externa | Onset | ΔF aparente |
|---|---|---|---|---|---|---|
| A (`v=250`) | 100 | 98 g | 106 g | **8 g** | — | 6 g |
| B (`v=25`) | 100 | 104 g | 105 g | **1 g** | — | 5 g |
| A (`v=250`) | 500 | 100 g | 1319 g | 1219 g | 1342 | 819 g |

**Ese ΔF de 5–6 g es un espejismo**: leído sin mirar diría "protección perfecta",
cuando el dedo ni siquiera tocó el objeto. Es la tercera forma —y la más
radical— en que la mitigación "usa un `Fset` bajo" falla: en el índice funciona,
en el pulgar no protege, y en el meñique **no existe como opción**.

> **Cómo se detecta.** El campo `onset_pos` no vale como prueba de contacto: su
> umbral son 80 g sobre el baseline y los toques suaves no llegan — 31 de las 35
> filas `Fset=100` del índice no tienen onset **y sí tocaron** (`F_max` 100–143 g
> sobre un residual de ~9 g). La prueba es que **`F_max` se despegue del
> residual**. Implementado en `run_cell` (aviso por trial) y en
> `exp2_analyze.drop_contactless()` (descarte con motivo). Verificado: no
> descarta ningún trial de las campañas del índice ni del pulgar.

---

## La rigidez del montaje domina el sobreimpulso

Descubierto por accidente: el bloque estaba suelto durante el primer sondeo del
meñique y se sujetó después. **Misma geometría, misma celda, distinto apriete:**

| | Bloque suelto (`m1`) | Bloque sujeto (`m2`) |
|---|---|---|
| Onset geométrico | POS 1467 | POS 1465 |
| Recorrido onset → pico | 63 counts | **23 counts** |
| Rigidez `k_c` | 4.76 g/count | **12.87 g/count** |
| Distancia de frenado a 100 g | 9 counts | 11 counts |
| ΔF en `v=250, Fset=500` | 202 g | **819 g** |

El onset se mueve **2 counts**: la geometría es la misma. Lo que cambia es que el
montaje suelto absorbía recorrido, y con ello **2.7× de rigidez y 4× de
sobreimpulso**.

**Consecuencia para la tesis.** Esto es evidencia directa de la hipótesis del
Trabajo 2 —que la rigidez es propiedad del **contacto** y no del dedo— obtenida
sin cambiar de dedo ni de bloque, solo de apriete. Y obliga a una **advertencia
sobre la campaña del pulgar**: su bloque se movió al menos dos veces (tras los
175 trials y antes de P2.7). Sus ΔF y su `k_c` (~5.7 g/count) pueden ser
**subestimaciones**. No invalida su conclusión —un montaje más rígido solo
empeoraría el sobreimpulso, reforzando que `Fset=100` no protege— pero los
valores absolutos hay que darlos con esa reserva, o repetir el sondeo del pulgar
con el bloque sujeto.

---

## Estado

| Dedo | V0.1 | V0.2 | V1 | V0.3 | V0.4 | V2 | Veredicto |
|---|---|---|---|---|---|---|---|
| Meñique (0) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **Verificado por muestreo** |
| Anular (1) | ✔ | ✔ | ✔ | ☐ | ☐ | ☐ | V1 pasa; falta Sesión B |
| Medio (2) | ✔ | ✔ | ✔ | ☐ | ☐ | ☐ | V1 pasa; falta Sesión B |

### Parámetros del meñique (montaje `m2`)

| | Valor |
|---|---|
| Recorrido libre `POS` | 96 … 1893 |
| Onset geométrico | POS 1465 (`ANGLE_SET` 270 ≈ 62.1°) |
| `--start-angle` (modo A) | 423 (POS 1215, residual medido 100 g) |
| `--approach-angle` (modo B) | 343 (POS 1345) |
| `Fset` mínimo utilizable | ≈ 150 g |

### Datos

`exp1/data_dof0/` · `exp2/data_dof0/` (sondeos `_libre`, `_m1`, `_m2`,
`_m1_falsostall`) · `exp2/data_dof0_hybrid/` · `exp2/data_dof0_fset100_sin_contacto/`
· `exp2/data_dof0_hybrid_m1_descartado/` (montaje suelto, no usar).
