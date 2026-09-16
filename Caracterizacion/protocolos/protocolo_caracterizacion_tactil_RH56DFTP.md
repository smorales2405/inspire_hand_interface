# Protocolo de Caracterización del Táctil — Inspire RH56DFTP (Punto 2)

**Objetivo:** convertir las 17 zonas táctiles (crudo 0–4095, sin unidades) en una señal confiable, estable y calibrada, y luego cuantificar sus capacidades funcionales. Estructura **por fases con dependencia A→B**: primero se valida el sensor a nivel de señal (Fase A, base + compuerta), y solo entonces se miden capacidades funcionales (Fase B). Mismo principio "garbage-in" con que el Exp 0 gateó el punto 1.

> **Principio de sensado: RESISTIVO** (config. T1 de la línea RH56: 17 zonas). Eso fija las patologías a caracterizar: **deriva de resistencia inicial, histéresis, no linealidad y cross-talk** entre taxeles.

## Referencias por fase
- **Fase A (nivel sensor):** metodología de táctil piezoresistivo en mano diestra — set de métricas (rango, resolución, repetibilidad, tiempos de carga/descarga asimétricos) y el problema de deriva inicial. *MDPI Micromachines 15(12):1513 (PMC11677542).*
- **Deriva / re-cero dinámico:** baseline adaptativo en vez de cero fijo. *TensorTouch (arXiv 2506.08291).*
- **Rig de ground-truth (fuerza→SI):** brazo/indentadores + F/T de referencia muestreado a la misma tasa. *NUSense (arXiv 2410.23516).*
- **Fase B (nivel funcional):** qué capacidades reportar y contra qué compararte — resolución espacial, umbral de fuerza, discriminación de forma, con la **Inspire resistiva** ya caracterizada. *"Feel Robot Feels" (arXiv 2603.28542).*
- **Layout de arrays de la Inspire (referencia cruzada):** *"Grasp, Slide, Roll" (arXiv 2602.23206).*

---

## 0. Precondiciones

1. **GUI cerrada, un solo cliente Modbus, un solo proceso.** Igual que en el punto 1: dos lectores sobre el mismo bus se serializan y falsean el timing.
2. **`time.perf_counter()`** para todos los timestamps.
3. **Decodificación:** cada taxel es un registro de 16 bits; valor crudo 0–4095. Decodifica con signo por consistencia (`v -= 65536 if v >= 32768`), aunque en reposo/carga normal es positivo.
4. **Temperatura.** La deriva resistiva es térmica: registra el **registro de temperatura del actuador** (o una sonda ambiente) al inicio/fin de cada bloque, y arranca la Fase A1 **desde frío** (justo tras encender).
5. **Sin la GUI compitiendo**, reutiliza tus métodos existentes: `read_all_tactile_zones()` (frame completo) y `read_tactile_zone(zone_index)` (una zona, más rápido).

---

## 1. Mapa de zonas (de `core/tactile_zones.py`)

17 zonas, **1062 taxeles**, 1 registro/taxel, `read_holding_registers`.

| # | Zona | Addr | Regs | Grid | # | Zona | Addr | Regs | Grid |
|---|---|---|---|---|---|---|---|---|---|
| z0 | Meñique·Punta | 3000 | 9 | 3×3 | z9 | Índice·Punta | 4110 | 9 | 3×3 |
| z1 | Meñique·Distal | 3018 | 96 | 12×8 | z10 | Índice·Distal | 4128 | 96 | 12×8 |
| z2 | Meñique·Palmar | 3210 | 80 | 10×8 | z11 | Índice·Palmar | 4320 | 80 | 10×8 |
| z3 | Anular·Punta | 3370 | 9 | 3×3 | z12 | Pulgar·Punta | 4480 | 9 | 3×3 |
| z4 | Anular·Distal | 3388 | 96 | 12×8 | z13 | Pulgar·Distal | 4498 | 96 | 12×8 |
| z5 | Anular·Palmar | 3580 | 80 | 10×8 | z14 | Pulgar·Medio | 4690 | 9 | 3×3 |
| z6 | Medio·Punta | 3740 | 9 | 3×3 | z15 | Pulgar·Palmar | 4708 | 96 | 12×8 |
| z7 | Medio·Distal | 3758 | 96 | 12×8 | z16 | Palma | 4900 | 112 | 14×8 |
| z8 | Medio·Palmar | 3950 | 80 | 10×8 | | | | | |

**Realidad de muestreo (medir en Fase 0):** el frame completo son **17 transacciones Modbus secuenciales** → ~5 Hz. Una sola zona es mucho más rápida. Consecuencia de diseño: **todo se caracteriza cuasi-estáticamente**; la respuesta temporal (decenas–cientos de ms en resistivos) queda al límite de tu instrumentación → mídela por **zona única** o acéptala como límite del harness, no del sensor.

---

## FASE 0 — Smoke test / mapa vivo

Barato, tipo la validación de un trial del Exp 1. **Compuerta blanda:** identifica taxeles muertos/pegados y mide la tasa real antes de invertir en las fases caras.

**Procedimiento**
1. **Baseline en reposo:** lee ~200–500 frames completos con la mano quieta, sin contacto. Guarda media y desv. por taxel.
2. **Barrido manual:** presiona una a una las 17 zonas. Confirma que la zona presionada sube y las demás **no** (chequeo grueso de cross-talk entre zonas).
3. **Diagnóstico de taxeles:** marca **muertos** (nunca se mueven), **pegados** (fijos en alto/bajo) y **ruidosos** (σ anómala).
4. **Tasa:** mide Hz de frame completo (`read_all_tactile_zones`) y Hz de zona única (`read_tactile_zone`) con `perf_counter()`.

**Salidas**
- Mapa de taxeles muertos/pegados (los excluyes del análisis posterior).
- Baseline por taxel (media, σ) → fija el piso de umbral de contacto de todo lo demás.
- Hz frame-completo y Hz zona-única → **gatea** qué es factible en Fase A/B.

**Criterio:** parte ya la tienes en tu pestaña táctil de la GUI; aquí solo lo formalizas standalone y con timestamps.

---

## FASE A — Nivel sensor (base + compuerta)

### A1 — Baseline, ruido y deriva  *(detallado — es la compuerta)*

Este es tu "Exp 0 del táctil". Si la deriva es mala, cambia tu estrategia de re-cero y **cómo entra el táctil al estado multimodal** — y necesitas saberlo temprano, porque es lo que más puede contaminar tu ablación "sin táctil".

**A1.1 — Ruido en reposo**
- Lee frames completos ~2–5 min, mano quieta, sin contacto.
- Por taxel: media (baseline) y σ (ruido). Reporta la distribución de σ e identifica taxeles ruidosos.
- Fija el umbral de detección de contacto: `thr = max(k·σ_taxel, abs_floor)` (arranca `k≈5`; `abs_floor` empírico del ruido crudo). Mismo patrón que el `detect_onset` del punto 1.

**A1.2 — Deriva sin carga (térmica / asentamiento)**
- **Desde encendido en frío**, loguea frames en reposo durante 20–30 min.
- Por taxel/zona: baseline vs tiempo y vs temperatura. Cuantifica cuánto se corre el cero tras power-on (los resistivos derivan al calentar/asentar).

**A1.3 — Deriva bajo carga / creep y recuperación**
- Aplica un **peso constante conocido** sobre una zona (p. ej. yema del índice) y mantén 3–5 min.
- Mide: (a) *creep* — cómo cambia el crudo bajo fuerza constante; (b) *recuperación* — al retirar la carga, ¿vuelve al baseline?, ¿queda offset residual y en cuánto tiempo se disipa? (el problema de deriva de resistencia inicial de la referencia MDPI).

**Decisión / compuerta de A1**
Con la magnitud de deriva medida, elige la estrategia de re-cero y de entrada al estado:
- Deriva baja → **cero fijo de sesión** (un `forceClb`/baseline al inicio) basta.
- Deriva apreciable → **baseline por-toque o re-cero periódico** (idea de baseline adaptativo de TensorTouch): no asumas un cero estático a lo largo de la sesión.
Documenta esta decisión: condiciona el pipeline de logging multimodal de diciembre.

---

### A2 — Repetibilidad e histéresis  *(detallado)*

Caracteriza qué tan **consistente** y **dependiente del camino** es la respuesta cruda bajo carga cíclica. Es el paso que **decide el modelo de calibración de A3**: si la histéresis es alta, un crudo dado no mapea a una fuerza única (depende de si vienes cargando o descargando).

**Prerrequisitos de montaje (compartidos con A3)**
- **Jig de posicionamiento repetible:** el indentador debe cargar **los mismos taxeles** en cada ciclo, o medirás varianza de colocación, no del sensor (análogo al remontaje del bloque en el onset del punto 1).
- **Respuesta de zona:** define la señal como la **suma** (o media) del crudo sobre el parche de taxeles cargados — más robusta a colocación que un taxel pico. Fíjala y sé consistente en todo A2/A3.
- **Espera inter-ciclo:** usa el tiempo de recuperación medido en **A1.3**; si recargas antes de que el sensor vuelva al baseline, confundes creep/deriva con mala repetibilidad.
- Zona hacia arriba, carga cuasi-estática con pesos, dado tu muestreo.

**A2.1 — Repetibilidad a carga fija**
- Aplica el mismo peso conocido N≥20 veces (carga → hold ~2–3 s → lee → descarga → espera recuperación → repite). Hazlo a 3 niveles: bajo, medio, alto.
- Métrica: **error de repetibilidad** por nivel = desv./media (o (max−min)/media) de la respuesta de zona entre ciclos, en % del fondo de escala o % de lectura. Referencia MDPI: ~1.5%.

**A2.2 — Lazo de histéresis (carga vs descarga)**
- Escalera de cargas crecientes y luego decrecientes: 0 → w₁ → … → w_max → … → w₁ → 0, con hold cuasi-estático en cada escalón, leyendo el crudo.
- Traza crudo-vs-carga para la **rama de carga** y la **de descarga**.
- Métrica: **error de histéresis** = máxima diferencia entre ramas al mismo peso, en % del fondo de escala. Referencia típica ~5%.

**A2.3 — Tiempos de respuesta (carga/descarga, asimétricos)**
- Aquí sí necesitas velocidad → lee **zona única** (más rápida que el frame completo).
- Escalón de carga (aplica/quita el peso rápido): mide **tiempo de subida** a valor estable (carga) y **tiempo de decaimiento/recuperación** (descarga). En resistivos son **asimétricos** (referencia MDPI: ~80 ms carga, ~160 ms descarga).
- **Caveat instrumental:** aun por zona única tu tasa es limitada; el flanco rápido de carga puede quedar sub-muestreado. Reporta lo que resuelvas y marca el límite como del **harness**, no del sensor (igual que la cuantización de `POS_ACT` en el onset del punto 1).

**Decisión / compuerta de A2**
La magnitud de histéresis decide cómo calibras en A3:
- Histéresis baja → **una sola curva** crudo→fuerza sirve.
- Histéresis apreciable → calibra **solo la rama de carga** (y declara validez solo para cargas crecientes), o ajusta **modelos separados** carga/descarga, o acepta que el sensor da una **banda** de fuerza, no un punto. Esto define directamente cuán confiable es la fuerza táctil como escalar en tu estado multimodal.

---

### A3 — Calibración crudo(0–4095)→fuerza  *(detallado — monta aquí el rig que reusa la Fase B)*

Mapea crudo a **fuerza (N)** o **presión (kPa)** — el entregable que vuelve cuantitativo el canal táctil. Usa la **rama de carga** si A2 mostró histéresis.

**A3.1 — Rig de ground-truth y fixture** (patrón NUSense)
- Zona hacia arriba; **indentador plano de área conocida A** que cubre un conjunto conocido de taxeles; **pesos calibrados** (p. ej. 10, 20, 50, 100, 200, 500 g…) o mini celda de carga si quieres cargas arbitrarias/dinámicas.
- Fuerza: `F = m·g` (g=9.80665). Presión: `P = F / A`.
- **Jig compartido con A2** que garantice que el indentador cubre siempre los mismos taxeles.

**A3.2 — Curva de calibración estática** (por zona representativa)
- Cargas monótonas crecientes (rama de carga), hold cuasi-estático, registra crudo (respuesta de zona = suma sobre el parche).
- **Modelo:** los resistivos suelen ser **no lineales** (alta sensibilidad a baja fuerza, saturación a alta). No fuerces un lineal: ajusta el modelo que corresponda (log-lineal / potencia / por tramos) e identifica el **sub-rango cuasi-lineal** útil.
- Reporta: **sensibilidad** (Δcrudo/ΔN o por kPa), **linealidad (R²)** del modelo, **rango** (mínimo detectable → saturación) y **resolución** (mínima fuerza resoluble dado el ruido de A1.1).

**A3.3 — Variación por zona / tipo de grid**
- Repite A3.2 en **al menos una zona de cada tipo de grid** (3×3 punta, 12×8 distal, 10×8 palmar, 14×8 palma): la sensibilidad difiere por construcción y área.
- Produce una **tabla de calibración por zona** (modelo + coeficientes + rango válido).
- Opcional — **uniformidad intra-zona:** carga uniforme sobre una zona y mide la dispersión taxel-a-taxel del crudo → ganancia de corrección por taxel si hace falta.

**A3.4 — Validación**
- Aplica cargas conocidas **no usadas en el ajuste** y reporta el error (objetivo tipo ±10%).
- Cross-check del **estimado de fuerza total** (suma de fuerzas por taxel del parche) contra un peso conocido en un contacto multi-taxel.

**Salida de A3**
- Función crudo→fuerza/presión **por zona** (modelo + coeficientes), con rango válido y error esperado. Es la que usará tu estado multimodal para reportar fuerza táctil en unidades físicas.
- **Encadenamiento:** aplica primero la estrategia de re-cero de **A1** (resta el baseline vigente) y la rama de **A2** → recién ahí mapea. La calibración asume baseline estable y camino de carga definido.

---

## FASE B — Nivel funcional (benchmark tipo "Feel Robot Feels")  *(esbozo)*

Reutiliza el rig de A3; solo cambian geometría y posición del indentador.

- **B1 — Resolución espacial y cross-talk fino.** Indenta un punto/taxel y mide la dispersión de la respuesta a taxeles vecinos (point-spread). Discriminación de dos puntos. Compara con la resolución 12×8 reportada para la Inspire.
- **B2 — Umbral mínimo de fuerza detectable.** Menor carga que produce respuesta fiable sobre ruido, **por zona**.
- **B3 — Localización de contacto / discriminación de forma.** Indentadores de geometría distinta (punto, borde, área). ¿El array localiza el centroide y distingue formas básicas? (línea vs área vs punto, como en la tabla comparativa de "Feel Robot Feels").

---

## Detección de contacto (algoritmo común)

Mismo patrón que el punto 1, pero **por taxel**:

```python
import numpy as np

def taxel_contact(frame, baseline_mu, baseline_sigma, k=5.0, abs_floor=None):
    """frame, baseline_*: arrays (n_taxels,) del crudo. Devuelve máscara de contacto."""
    thr = k * baseline_sigma
    if abs_floor is not None:
        thr = np.maximum(thr, abs_floor)
    return (frame - baseline_mu) > thr
```

- `baseline_mu/sigma`: de A1.1 (o por-toque si A1 lo exige).
- Excluye del cómputo los taxeles muertos/pegados de la Fase 0.

---

## Logger (lazo único, sobre tus métodos)

```python
import time, csv, numpy as np
from core.tactile_zones import ZONES

def log_tactile(hand, dur_s, csv_path, load_g=None, mode="full"):
    """mode='full' -> read_all_tactile_zones (~5 Hz);
       mode='zone:<i>' -> read_tactile_zone(i) (rápido, p.ej. respuesta temporal)."""
    rows = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < dur_s:
        t = time.perf_counter()
        if mode == "full":
            data = hand.read_all_tactile_zones()      # list[list[int]]
            flat = [v for zone in data for v in zone]
        else:
            zi = int(mode.split(":")[1])
            flat = hand.read_tactile_zone(zi)
        rows.append((t - t0, load_g, *flat))          # load_g = ground-truth opcional
    # esquema: t_s, load_g, tax0, tax1, ...  (ancho fijo por 'mode')
    with open(csv_path, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    return rows
```

- Para A3/Fase B, la columna `load_g` es tu verdad de fuerza (peso aplicado en ese instante). Regístrala sincronizada con el frame.
- Frame completo para baseline/deriva/calibración cuasi-estática; **zona única** solo cuando persigas respuesta temporal.

---

## Análisis y salidas

- **Fase 0:** mapa muertos/pegados (CSV), baseline por taxel, Hz frame/zona.
- **A1:** heatmaps de σ (ruido) y de deriva por zona; curvas baseline-vs-tiempo; creep/recuperación; **decisión de re-cero documentada**.
- **A2:** curvas de histéresis (carga vs descarga) y tabla de repetibilidad/tiempos por zona.
- **A3:** ajustes crudo→N (o →kPa) con R², sensibilidad, rango, resolución, por tipo de zona.
- **Fase B:** point-spread/cross-talk, umbral de fuerza por zona, matriz de discriminación de forma.

---

## Checklist

- [ ] GUI cerrada; un único proceso sobre el bus.
- [ ] Fase 0: taxeles muertos/pegados mapeados; Hz frame y zona medidos y reportados.
- [ ] A1.1 ruido por taxel → umbral fijado; taxeles ruidosos marcados.
- [ ] A1.2 deriva sin carga desde frío (20–30 min) con temperatura.
- [ ] A1.3 creep + recuperación bajo peso constante.
- [ ] **Decisión de re-cero tomada y documentada** (cero fijo vs baseline adaptativo) → COMPUERTA hacia A2/A3/B.
- [ ] Jig de posicionamiento repetible montado (mismos taxeles cada ciclo) + respuesta de zona definida (suma/media del parche).
- [ ] A2.1 repetibilidad a 3 niveles (N≥20), con espera inter-ciclo = recuperación de A1.3.
- [ ] A2.2 lazo de histéresis (rama carga vs descarga) → **error de histéresis** reportado.
- [ ] A2.3 tiempos carga/descarga por zona única (asimétricos), con caveat instrumental.
- [ ] **Decisión de modelo de A3 tomada** según histéresis (curva única vs rama de carga vs bandas).
- [ ] Rig de ground-truth montado en A3 (pesos/celda + indentador de área conocida A).
- [ ] A3.2 modelo crudo→fuerza ajustado (no forzar lineal); sensibilidad, R², rango, resolución.
- [ ] A3.3 al menos una zona de cada tipo de grid caracterizada (3×3, 12×8, 10×8, 14×8) → tabla por zona.
- [ ] A3.4 validación con cargas fuera del ajuste (±10%) + cross-check de fuerza total.
- [ ] CSV crudo con timestamps `perf_counter()`; `load_g` sincronizado en A3/Fase B.
