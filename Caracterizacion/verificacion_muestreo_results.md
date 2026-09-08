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

### Modo B en los dedos nuevos

Aproximación rápida hasta 120 counts antes del onset, luego cierre a `v=25`.
N=5 por celda, 0 abortos, contacto confirmado en los 20 trials.

| DOF | `Fset` | ΔF mediana | Rango | Externa mínima |
|---|---|---|---|---|
| 0 Meñique | 250 | **50 g** | 32–124 | 245 g |
| 0 Meñique | 1000 | **111 g** | 91–133 | 1055 g |
| 1 Anular | 100 | **46 g** | 33–78 | 129 g |
| 1 Anular | 1000 | **56 g** | 6–116 | 1000 g |

Criterio de V2 cumplido en los dos dedos. En el anular ΔF **apenas escala con
`Fset`** (46 → 56 g mientras `Fset` se multiplica por 10), que es la firma del
modo B: el sobreimpulso lo fija el momento en el instante del contacto, no el
umbral. Como referencia, la celda de validación en **modo A** a `v=250,
Fset=500` dio **819 g** (meñique) y **1086 g** (anular) en los mismos montajes.

### El hallazgo: en el meñique `Fset = 100` **no es ejecutable**

No es que proteja mal — es que **no se puede pedir**. El residual de flexión del
propio dedo llega a **117 g en el onset**, por encima del umbral, así que el
firmware frena en el aire y el trial no llega nunca al bloque. Medido dos veces,
en los dos modos:

| DOF | Modo | `Fset` | `f_base` | `F_max` | Externa | Onset | ΔF aparente |
|---|---|---|---|---|---|---|---|
| 0 | A (`v=250`) | 100 | 98 g | 106 g | **8 g** | — | 6 g |
| 0 | B (`v=25`) | 100 | 104 g | 105 g | **1 g** | — | 5 g |
| 0 | A (`v=250`) | 500 | 100 g | 1319 g | 1219 g | 1342 | 819 g |
| 1 | B (`v=25`) | 100 | 37 g | 110 g | **73 g** | 1393 | 10 g |

**Ese ΔF de 5–6 g del meñique es un espejismo**: leído sin mirar diría
"protección perfecta", cuando el dedo ni siquiera tocó el objeto. El anular, con
la mitad de residual, sí llega. Es la tercera forma —y la más radical— en que la
mitigación "usa un `Fset` bajo" falla: en el índice funciona, en el pulgar no
protege, y en el meñique **no existe como opción**.

> **Cómo se detecta.** El campo `onset_pos` no vale como prueba de contacto: su
> umbral son 80 g sobre el baseline y los toques suaves no llegan — 31 de las 35
> filas `Fset=100` del índice no tienen onset **y sí tocaron** (`F_max` 100–143 g
> sobre un residual de ~9 g). La prueba es que **`F_max` se despegue del
> residual**. Implementado en `run_cell` (aviso por trial) y en
> `exp2_analyze.drop_contactless()` (descarte con motivo). Verificado: no
> descarta ningún trial de las campañas del índice ni del pulgar.

### Geometría del contacto y umbral mínimo

| DOF | Onset | `k_c` | Frenado a 100 g | Residual en onset | `Fset` mínimo |
|---|---|---|---|---|---|
| 0 Meñique | POS 1458 | 11.0 g/count | 18 counts | 117 g | **~147 g** |
| 1 Anular | POS 1414 | 17.0 g/count | 12 counts | 50 g | **~80 g** |
| 4 Pulgar | POS 775 | 5.7–5.9 g/count | 28–31 counts | 23 g | ~53 g |
| 3 Índice | — | ~1.6 g/count † | ~220 counts † | ~9 g | — |

† El índice es el único que **no** pasa por este pipeline: no tiene sondeo
`--no-block`, así que su onset se fijó a ojo (`POS ~1200`) sobre un sondeo sin
curva libre de referencia. Un `--probe --no-block` de 15 s con el bloque
desmontado lo pondría en igualdad con los demás.

Los umbrales mínimos predichos por la curva libre coinciden con lo medido:
meñique 147 g (y `Fset=100` falló), anular 80 g (y `Fset=100` funcionó).

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
| Anular (1) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | **Verificado por muestreo** |
| Medio (2) | ✔ | ✔ | ✔ | ☐ | ☐ | ☐ | V1 pasa; falta Sesión B |

### Parámetros por dedo

| | Meñique (`m2`) | Anular (`fijo`) |
|---|---|---|
| Recorrido libre `POS` | 96 … 1893 | 61 … 1842 |
| Onset geométrico | POS 1458 (`ANGLE_SET` 274) | POS 1414 (`ANGLE_SET` 284) |
| `--start-angle` (modo A) | 427 (residual medido 100 g) | 443 (medido 36 g) |
| `--approach-angle` (modo B) | 348 | 360 |
| `Fset` mínimo utilizable | ≈ 147 g | ≈ 80 g |

La campaña del meñique corrió con `--approach-angle 343` (POS 1345), derivado
antes de la corrección de alineación: quedan 113 counts antes del onset en vez
de 120. Sin efecto — el margen existe para conmutar de sobra.

### Datos

`exp1/data_dof0/` · `exp2/data_dof0/` (sondeos `_libre`, `_m1`, `_m2`,
`_m1_falsostall`) · `exp2/data_dof0_hybrid/` · `exp2/data_dof0_fset100_sin_contacto/`
· `exp2/data_dof0_hybrid_m1_descartado/` (montaje suelto, no usar) ·
`exp1/data_dof1/` · `exp2/data_dof1/` · `exp2/data_dof1_hybrid/`.

## Dos correcciones al pipeline durante esta campaña

**Alineación de las curvas.** El cero se fijaba con el valor en reposo de cada
sondeo. Entre dos sondeos del anular separados por minutos, las curvas quedaron
desplazadas **16–20 g después de restar sus reposos** —el sesgo del sensor no es
un offset puro— y como el umbral de onset son 20 g, el detector situó el contacto
en `POS 460` en vez de en el bloque, **1000 counts más allá**. Ahora las dos
curvas se **alinean en un tramo temprano** donde el contacto es imposible, lo que
cancela cualquier deriva constante. Además `--probe` tara con `forceClb` al
empezar.

**Residual alineado ≠ residual absoluto.** La curva alineada sirve para *detectar
contacto* (compara dos corridas) pero está referida a ese tramo temprano, donde
el dedo ya acumuló ~45 g. Para decidir si un `Fset` es alcanzable hace falta el
valor **absoluto**, porque `forceClb` tara con la palma abierta y el firmware
compara contra eso. Con la alineada el meñique daba 53 g y `Fset=100` parecía
viable; el absoluto da 117 g y coincide con los 98–104 g medidos. Separado en
`absolute_residual()`.
