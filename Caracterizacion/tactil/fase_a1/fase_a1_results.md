# Fase A1 — Resultados: nivel sensor (ruido, deriva, creep/recuperación)

**Fecha:** 2026-07-05
**Transporte:** serial `/dev/ttyUSB0` @ 115200 baud, device_id 1
Táctil Inspire RH56DFTP, sensor **resistivo**. GUI cerrada, un solo cliente.

La compuerta de la Fase A: validar el sensor a nivel de señal antes de calibrar
(A2/A3). Tres sub-experimentos hardware-in-the-loop. Se excluyen los taxeles
muertos de Fase 0 (z6 Medio·Punta muerta por hardware) donde aplica.

---

## A1.1 — Ruido en reposo y umbral de contacto (`a1_noise.py`)

180 s en reposo, 532 frames (3.0 Hz), 958 taxeles buenos (104 excluidos de Fase 0).

- **Piso de ruido ~cero:** 891/958 (93%) con **σ = 0** en 3 min. σ p95 = 0.86,
  p99 = 5.16, **máx = 14.53 counts** (0.35% del fondo de escala). El ruido se
  concentra en ~67 taxeles (7%) que además cargan un offset en reposo; z13
  (Pulgar·Distal) el más ruidoso.
- **Umbral de contacto:** `thr = max(k·σ_taxel, abs_floor)`, `k = 5`, con
  **`abs_floor = 41 counts` (~1% FS)**, empírico (`⌈p99.9 de la excursión⌉`).
  954/958 taxeles quedan gobernados por el piso. Es conservador (lo fija el peor
  0.1%); un piso sobre solo los taxeles quietos daría ~16 counts (más sensible).

## A1.2 — Deriva sin carga desde frío (`a1_drift.py`)

25 min en reposo **arrancando en frío** (índice 28 → 36 °C, ΔT +8), 4400 frames.

- **Deriva del cero SIN carga: NEGLIGIBLE.** 913/958 (95.3%) con `Δ = 0` exacto;
  mediana y `gmed` (robusta) = 0 todo el tiempo. Deriva global **+0.47 counts**
  en 25 min. Correlaciona con la temperatura (r = 0.85) pero sobre una señal de
  ~½ count → físicamente irrelevante vs `abs_floor = 41`.
- Solo 2/958 taxeles superan `abs_floor`, y son **eventos aislados de un taxel**
  (z9 Índice·Punta 0→176, escalón al min ~2 = contacto espurio; z8 +46), no un
  corrimiento sistémico.
- **Temperatura resuelta:** `TEMP` = 6 registros (1618..1623), 1 temp/reg
  (confirmado con lectura cruda). Índice = reg 1621.

## A1.3 — Creep y recuperación bajo carga constante (`a1_creep.py`)

Zona **palma (z16)**, peso **256 g (2.51 N)**, lectura de zona única (~32 Hz),
respuesta = suma del crudo sobre baseline en el parche cargado (7 taxeles).

**Montaje (lección aprendida):** el peso debe ser de **base plana y no sobresalir
de la zona**. Un objeto cilíndrico o más largo que la palma **hace puente** sobre
el marco rígido y **no carga el sensor** (dio 0 counts). Con el modo `--monitor`
se verifica en vivo el contacto y dónde responde la zona antes de correr. La
exclusión de Fase 0 **no** se aplica aquí (en zonas grandes quitaba taxeles de
cobertura que la carga sí apoya).

**Resultado (contacto bien apoyado):**
- **Creep despreciable: ≈ +1 % en 4 min** (respuesta plana ~1450, oscilando ±5%).
- **Recuperación inmediata y completa:** al retirar el peso, la respuesta cae de
  ~1450 a 0 en **~0.2–0.4 s** (al límite del muestreo de 32 Hz), con **residual
  exactamente 0**, sostenido los 4 min siguientes.

> **Confound identificado:** una primera corrida dio "creep +29%", pero era
> **asentamiento mecánico** de la carga (arrancó mal apoyada en 857 y subió a
> 1107 en 4 min). Bien apoyada, el creep real es ~1%. La medición de creep es
> sensible a la calidad del contacto → montar el peso estable desde el inicio.

**Reconciliación con Fase 0:** Fase 0 vio ~250 counts de residual (no-recuperación)
tras un press **duro** (~2400 counts) en la yema del meñique. A1.3 con carga
**moderada** en la palma recupera del todo. → El residual es **dependiente de
carga/zona**: aparece a fuerzas altas / en yemas, no a cargas moderadas.

---

## Decisión de re-cero (compuerta de la Fase A1)

Evidencia:
- A1.2 — el baseline **sin tocar** es estable (deriva ~½ count sobre ΔT +8 °C).
- A1.3 — bajo carga moderada, **creep ~1%** y **recuperación completa** (residual 0).

**Decisión: un CERO FIJO de sesión es adecuado** para el canal táctil (un
`baseline`/tara al inicio, restado como valor fijo). No hace falta baseline
adaptativo por-toque para mantener el cero.

**Salvedades (margen de seguridad):**
- Fase 0 mostró residual tras contactos **duros** en yemas → conviene un
  **re-cero oportunista periódico** (refrescar el baseline cuando la mano esté
  ociosa/sin contacto) como red de seguridad barata, sin llegar al adaptativo pleno.
- Para la **calibración A3**: el creep es despreciable una vez asentado el
  contacto, así que el crudo mapea bien a fuerza — pero **leer a un tiempo de
  permanencia consistente** (el asentamiento inicial de A1.3 ocurre en los
  primeros segundos) y con contacto estable.

---

## Archivos

En `data/`: `a1_noise_taxels.csv` (μ/σ/umbral por taxel), `a1_drift_taxels.csv`
+ `a1_drift_timeseries.csv` (deriva por taxel y vs tiempo/temperatura),
`a1_creep_timeseries_z16.csv` (curva carga→creep→retiro→recuperación). Montaje de
A1.3 en `../load1/`. Reproducible con los tres scripts (ver `README.md`).
