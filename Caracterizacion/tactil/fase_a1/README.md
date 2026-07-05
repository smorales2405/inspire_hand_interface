# Fase A1 — Nivel sensor: baseline, ruido y deriva (táctil)

La **compuerta** de la Fase A. Caracteriza el sensor a nivel de señal antes de
medir capacidades funcionales (Fase B). Tres sub-experimentos, cada uno
hardware-in-the-loop:

- **A1.1 — Ruido en reposo** (`a1_noise.py`) — **[implementado]** fija el piso
  del umbral de contacto.
- **A1.2 — Deriva sin carga desde frío** (20–30 min, con temperatura) — *pendiente*.
- **A1.3 — Creep y recuperación bajo carga constante** — *pendiente* (la más
  crítica: Fase 0 ya vio ~6% FS de no-recuperación).

Standalone (sin PyQt): un proceso/hilo/cliente Modbus, `time.perf_counter()`,
estado seguro al salir. **Correr con la GUI CERRADA.** Reutiliza
`../hand_tactile.py` (+ `../../hand_modbus.py`).

Temperatura: se loguea el bloque **`TEMP` (reg 1618, manual 2.6.19)** — 6
actuadores, 0–100 °C, 1 byte c/u — como proxy térmico de la deriva resistiva.

---

## A1.1 — Ruido en reposo y piso de umbral (`a1_noise.py`)

Captura larga en reposo (**sin contacto**) → media y **σ (ruido)** por taxel.
**Excluye** los taxeles muertos/pegados del screening de Fase 0 (lee
`taxel_diagnosis.csv`; siempre excluye z6, muerta por hardware). Fija el umbral
de detección de contacto:

```
thr = max(k·σ_taxel, abs_floor)      # k≈5 (param)
```

- `k·σ_taxel`: para taxeles con ruido medible.
- `abs_floor`: **empírico de los datos** — `⌈p99.9 de la excursión max |v−μ|⌉`
  sobre los taxeles buenos. Cubre el ruido raro de los taxeles que en reposo
  leen σ≈0 (la mayoría). No es constante inventada.

### Cómo correr

```bash
# ~3 min en reposo (default). Mano quieta y sin tocar nada.
.venv/bin/python Caracterizacion/tactil/fase_a1/a1_noise.py \
    --transport serial --serial-port /dev/ttyUSB0 --baud 115200 --secs 180
```

| Flag | Def | Descripción |
|---|---|---|
| `--secs` | 180 | duración de la captura en reposo (~3 min) |
| `--frames` | — | si se da, captura N frames en vez de por tiempo |
| `--k` | 5.0 | k de `k·σ` y del cerco de ruido |
| `--diag` | `../fase0/data/taxel_diagnosis.csv` | screening de Fase 0 para la exclusión |
| `--warmup` | 10 | lecturas de calentamiento descartadas |
| `--no-prompt` | — | no pausa antes de capturar |
| `--no-safe-open` | — | no abre los dedos al salir (por defecto sí) |
| `--outdir` / `--tag` | `fase_a1/data` / — | salida |

### Salida

- Consola: nº de taxeles buenos, distribución de **σ** (min/med/p95/p99/max),
  cerco robusto y taxeles ruidosos, distribución de **excursión**, el
  **`abs_floor` recomendado** y cuántos taxeles quedarían gobernados por el piso
  vs `k·σ`, y la **temperatura** inicio/fin (ΔT).
- CSV `data/a1_noise_taxels.csv`: `taxel,zone,…,mu,sigma,min,max,excursion_max,
  excluded,noisy,thr`. Es el **baseline de ruido + umbral por taxel** que usan
  A1.2/A1.3 y el pipeline multimodal.

### Cómo leer

- La `σ` en counts (0–4095). Si `MAD(σ)=0` (casi todo el array en σ=0), el cerco
  robusto colapsa y marca *noisy* a cualquier σ>0: mira la **distribución de σ**
  y el **`abs_floor`**, que son los números que importan.
- El `abs_floor` es la sensibilidad práctica del canal: una carga debe superar
  ese Δcounts para contar como contacto en los taxeles quietos.

---

## Después de A1.1

Pega la salida de consola + adjunta `a1_noise_taxels.csv`. Con el piso de ruido
y el umbral fijados, se implementan **A1.2** (deriva desde frío) y **A1.3**
(creep/recuperación) — cuyos umbrales de detección dependen de este `abs_floor`.
La **decisión de re-cero** (cero fijo vs baseline adaptativo) se toma al cerrar
A1, con A1.3 como evidencia principal.
