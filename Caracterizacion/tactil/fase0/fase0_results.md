# Fase 0 — Resultados del smoke test / mapa vivo (táctil)

**Fecha:** 2026-07-05
**Transporte:** serial `/dev/ttyUSB0` @ 115200 baud, device_id 1
**Comando:** `fase0_smoke_test.py --transport serial --serial-port /dev/ttyUSB0 --baud 115200`
**Barrido:** re-baseline **por zona** (referencia fresca en reposo antes de cada
presión). Mano derecha, GUI cerrada.

Compuerta blanda del punto 2: mapear taxeles muertos/pegados y medir la tasa real
antes de invertir en A1–A3. **17 zonas, 1062 taxeles**, 1 registro/taxel, crudo
0–4095, decodificado con signo.

---

## 1. Tasa de muestreo

| Lectura | Hz | dt media (ms) | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| Frame completo (17 zonas) | **2.9** | 341.0 | 341.0 | 342.9 | 343.3 | 343.4 |
| Zona única z10 (96 tax) | **32.4** | 30.9 | 30.9 | 31.8 | 32.1 | 33.3 |

Muy estable (jitter < 3 ms). El frame completo son **17 transacciones Modbus
secuenciales** → ~20 ms/zona → 2.9 Hz. La zona única depende de su nº de taxeles
(z10 = 96).

**Consecuencia (gatea todo lo demás):**
- Frame completo **2.9 Hz** (Nyquist ~1.45 Hz) → todo lo de A1/A3 se caracteriza
  **cuasi-estáticamente** (baseline, deriva, calibración con pesos).
- Zona única **32.4 Hz** (Nyquist ~16 Hz) → es lo que habilita **A2.3** (tiempos
  de respuesta). Resuelve el flanco de **descarga** (~160 ms típico en resistivos)
  pero el de **carga** (~80 ms) queda al **límite del harness** (dt ~31 ms ≈ 2–3
  muestras en el flanco). Es límite de instrumentación, no del sensor.

## 2. Baseline en reposo

- **1021 / 1062 taxeles leen μ=0, σ=0 exactos** → piso de ruido resistivo = cero
  limpio. **No hay pegado-alto** (μ máx = 364 ≪ techo 4095).
- **41 taxeles** cargan actividad en reposo (μ ≤ 364, σ ≤ 119); son exactamente
  los que el screening marca *noisy*. Población pequeña y localizada, no ruido de
  todo el array. La caracterización fina de ruido/umbral es de **A1.1**.

## 3. Respuesta al presionar

- **919 taxeles ok**; las puntas responden fuerte: z0=2690, z3=2886, z9=2062,
  z12=2894 (rise sobre referencia). El sensor funciona.
- **z6 Medio·Punta (9 tax) MUERTA** (hardware, esta mano derecha):
  no lee nada ni con la Interfaz abierta. Se saltó en el barrido → aparece como
  `unknown` (9). **Excluir sus 9 taxeles de todo análisis, permanente.**

## 4. Cross-talk entre zonas (tras re-baseline por zona)

Máximos acoples off-diagonal (rise en otra zona / respuesta propia):

| Presionada → víctima | rise | % propia |
|---|---|---|
| z3 Anular·Punta → z4 Anular·Distal | 153 | 5.3% |
| z9 Índice·Punta → z10 Índice·Distal | 98 | 4.8% |
| z13 Pulgar·Distal → z0 Meñique·Punta | 54 | 4.7% |
| z12 Pulgar·Punta → z11 Índice·Palmar | 48 | 1.7% |

**Cross-talk bajo (≤ 5.3%)**, dominado por adyacencia **mismo dedo, punta↔distal**
(acople mecánico esperado), no bleed eléctrico. Los acoples entre-dedos son
< 3.5%. Benigno para sensado a nivel de zona.

> El re-baseline por zona **eliminó** las columnas persistentes (~250) que
> contaminaban la matriz en la corrida previa: **no eran cross-talk sino
> no-recuperación** (ver §5).

## 5. No-recuperación / residual (adelanto de A1.3)

La referencia fresca antes de cada zona reveló la señal escondida: tras presionar
**z0 (Meñique·Punta)** al inicio (pico 2690), sus taxeles quedaron **~250 counts
(~6% del fondo de escala) por encima del baseline durante TODO el resto del
barrido** — `ref_residual_zone = z0` para las 16 zonas siguientes (367 justo
después, decayendo a una meseta ~230–260). **No recupera** en la escala de tiempo
del barrido (minutos).

**Implicación para la compuerta de re-cero (preliminar):** un **cero fijo de
sesión no basta** — apunta a **baseline adaptativo / re-cero por-toque** (estilo
TensorTouch). Pendiente de cuantificar bien en **A1.3** (creep/recuperación con
peso constante y tiempos); esto es la señal cualitativa temprana.

## 6. Diagnóstico de taxeles (screening) y caveats

| status | n | lectura |
|---|---|---|
| ok | 919 | responden y baseline limpio |
| stuck_low | 93 | **mayormente cobertura**, no muertos (ver abajo) |
| noisy | 39 | = los 41 con actividad en reposo; σ ≤ 30 salvo 1 (σ=119) |
| unknown | 9 | z6 (saltada = muerta por hardware) |
| dead | 2 | artefacto de baseline (ver abajo) |

**Caveats (importantes, condicionan qué es certificable en Fase 0):**
- **`stuck_low` = cobertura, no muerte.** Se concentran en zonas grandes: Palma
  36/112, Medio·Distal 17/96, Índice·Distal 10/96, Índice·Palmar 10/80. Un dedo
  humano presiona un **parche**, no los 80–112 taxeles. Certificar taxeles
  muertos individuales en zonas grandes necesita el **indentador + jig** de
  A3/B1. El mapa por-taxel de Fase 0 es **screening a nivel de zona**, no lista
  final de exclusión (salvo la zona z6, confirmada por hardware).
- **`dead` = 2, ambos en z3 Anular·Punta** (r2c0, r2c1) con **rise negativo**
  (−31, −348) y baseline alto (μ=182, 364): tenían offset al capturar el baseline
  y leyeron **por debajo** durante la presión → firma de **deriva del baseline**,
  no elementos muertos. A1.2 lo aclara.
- **Pulgar·Medio (z14) 7/9 sin responder**: zona 3×3 chica; probable cobertura
  parcial. Re-verificar en A1/B1.

---

## Decisión / compuerta → qué habilita la Fase A

1. **Tasa aceptada:** 2.9 Hz frame / 32.4 Hz zona. A1/A3 **cuasi-estáticos**;
   A2.3 por **zona única**, con el flanco de carga marcado como límite del harness.
2. **Exclusión firme:** z6 Medio·Punta (9 tax) — muerta por hardware.
3. **Piso de umbral de contacto:** baseline por taxel en `baseline_taxels.csv`
   (μ, σ); para A1.1, `thr = max(k·σ, abs_floor)` con `k≈5` y `abs_floor` a fijar
   con los datos de A1.1 (2–5 min en reposo).
4. **Cross-talk bajo** (≤5.3%, mismo-dedo) → no bloquea; se cuantifica fino en B1.
5. **Re-cero:** señal temprana de **no-recuperación** (~6% FS, z0) → **A1.3 es
   crítica**; hipótesis de trabajo = baseline adaptativo (confirmar).

## Archivos

En `data/`: `baseline_taxels.csv` (μ/σ por taxel), `taxel_diagnosis.csv` (mapa de
estados), `crosstalk_zonas.csv` (matriz 17×17, referida a baseline fresco por
zona), `residual_zonas.csv` (no-recuperación + respuesta propia + peor cross-talk).
Reproducible con `fase0_smoke_test.py` (ver `README.md`).
