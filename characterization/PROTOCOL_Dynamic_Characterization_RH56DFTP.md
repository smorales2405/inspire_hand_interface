# Protocolo de Caracterización Dinámica — Inspire RH56DFTP

**Objetivo:** medir, sobre tu propio hardware, (a) la **latencia comando→sensor**, (b) la **respuesta al escalón** en espacio libre, y (c) el **sobreimpulso de fuerza en contacto** en función de la velocidad comandada y del umbral de fuerza. Salida final: dos figuras tipo Fig. 2 del paper + tu propio margen de conmutación para la política híbrida.

> Se monta sobre `core/hand_connection.py`. Los nombres de método (`read_*`, `write_*`) son ilustrativos: adáptalos a tu wrapper real.

---

## 0. Precondiciones (críticas para que las mediciones valgan)

1. **Bus Modbus dedicado.** Ejecuta la caracterización como script *standalone*, **no** con la GUI abierta. Tu hilo táctil corre a ~5 Hz y compite por el mismo cliente Modbus: dos lectores sobre una sola conexión se serializan y arruinan el timing. Un solo proceso, un solo cliente, un solo hilo.
2. **Un solo hilo, lazo intercalado.** No uses un hilo lector + un hilo escritor. Usa **un único lazo** que lee de forma continua y, en el instante de disparo, inyecta la escritura del comando. Así todo queda determinista y sobre el mismo cliente.
3. **Reloj monotónico.** Usa `time.perf_counter()` (no `time.time()`), que no salta con NTP.
4. **Decodificación con signo.** `FORCE_ACT` tiene rango −4000…4000 (short con signo). pymodbus devuelve uint16; convierte: `v = v - 65536 if v >= 32768 else v`.
5. **Conversión a Newton.** `FORCE_ACT` está en **gramos-fuerza**: `F_N = g * 9.80665 / 1000`.
6. **Temperatura.** Registra el **registro de temperatura del actuador** (sección 2.6.19 del manual) al inicio/fin de cada bloque. Los servos lineales derivan al calentarse; si la temperatura sube de forma apreciable durante la sesión, intercala descansos.
7. **Orden aleatorizado.** Aleatoriza el orden de las condiciones (velocidad, setpoint) para que la deriva térmica no se confunda con un efecto de la variable.
8. **Linux + máquina poco cargada.** Cierra otras apps; el jitter del SO impacta directo en tu resolución de latencia.

---

## 1. Mapa de registros — dedo índice (DOF 3)

Empieza con el **índice (DOF 3)** para reflejar el paper. Luego repite para medio (DOF 2) y flexión del pulgar (DOF 4) si quieres cobertura.

| Señal | Registro (manual) | Rango | Uso |
|---|---|---|---|
| `ANGLE_SET(3)` | 1492–1493 | −1, 0–1000 | Comando de movimiento (1000 = abierto, 0 = cerrado) |
| `SPEED_SET(3)` | 1528–1529 | 0–1000 | Velocidad de la articulación |
| `FORCE_SET(3)` | 1504–1505 | 0–3000 (g) | Umbral de fuerza (firmware detiene el dedo al alcanzarlo) |
| `POS_ACT(3)` | 1540–1541 | 0–2000 | Posición real del actuador (lectura, resolución fina) |
| `ANGLE_ACT(3)` | 1552–1553 | 0–1000 | Ángulo real (lectura) |
| `FORCE_ACT(3)` | 1588–1589 | −4000…4000 (g) | Fuerza real (lectura) |
| `CURRENT(3)` | 1600–1601 | 0–2000 (mA) | Corriente del actuador (lectura, vigilancia) |

> Usa el mapeo que ya tienes en `hand_connection.py` / `angle_converter.py`. Para maximizar la tasa de muestreo, lee en **un solo bloque** los 6 `FORCE_ACT` (1582–1593) o los 6 `POS_ACT` (1534–1545) según el experimento, y quédate con el índice.

---

## Experimento 0 — Baseline de muestreo y latencia de comunicación

Antes de medir nada del actuador, caracteriza tu canal. La "latencia" que midas después **incluye** el ida-y-vuelta de Modbus, y necesitas saber cuánto.

**Procedimiento**
1. Lee el bloque de 6 `FORCE_ACT` (12 bytes) en un lazo cerrado, N = 2000 iteraciones.
2. Guarda el `dt` de cada lectura con `perf_counter()`.

**Reporta:** tasa media (Hz), y percentiles p50/p95/p99 y máximo de `dt`.

**Criterio de aceptación:** apunta a **≥ 100 Hz** (periodo ≤ 10 ms). Si no lo alcanzas por TCP, reduce el bloque leído, revisa la red, o pasa a RS-485 a 115200. Tu resolución temporal de latencia ≈ tu periodo de muestreo, así que esto fija la calidad de todo lo demás.

```python
import time
dts = []
for _ in range(2000):
    t0 = time.perf_counter()
    _ = hand.read_block(1582, 6)   # 6x FORCE_ACT
    dts.append(time.perf_counter() - t0)
# rate = len(dts)/sum(dts); reportar percentiles de dts
```

---

## Experimento 1 — Respuesta al escalón y latencia comando→sensor (espacio libre)

**Sin objeto.** El dedo se mueve en el aire. Mide latencia, tiempo de subida, tiempo de establecimiento y confirma la ausencia de pre-deceleración (la patología que causa el sobreimpulso).

**Parámetros**
- DOF: 3 (índice).
- Velocidades: `v ∈ {100, 250, 500, 750, 1000}` (añade 25 y 50 si quieres el extremo lento).
- Comando: de **abierto (1000)** a un objetivo de gran recorrido pero **sin contacto** (p. ej. `ANGLE_SET = 300`; ajústalo para que el índice no toque palma ni otros dedos en el aire).
- `FORCE_SET(3) = 3000` (alto), para que el umbral de fuerza **nunca** dispare y midas movimiento puro.
- Trials: **20 por velocidad**, orden aleatorizado entre velocidades.

**Secuencia por trial**
1. Abrir: `ANGLE_SET(3)=1000`; esperar a que `ANGLE_ACT(3)≈1000` (settle).
2. `SPEED_SET(3)=v`; `FORCE_SET(3)=3000`.
3. Iniciar el **lazo de logging de alto ritmo** (ver §“Logger”), leyendo `POS_ACT(3)` (+ `FORCE_ACT(3)`, `CURRENT(3)`).
4. Registrar **baseline** ~200 ms con el dedo quieto.
5. En el instante de disparo, emitir `ANGLE_SET(3)=300` y marcar `t0 = perf_counter()` **justo después** de que retorne la escritura. Guardar también el costo de la escritura (`t_after − t_before`) como incertidumbre.
6. Seguir logueando hasta que `POS_ACT` se estabilice (sin cambio ≥ 300 ms), ventana total ~2 s.

**Métricas por trial**
- **Latencia** `L = t_onset − t0`, con `t_onset` = primer instante en que `POS_ACT` se sale de la banda de baseline (ver §“Detección de onset”).
- **Tiempo de subida** (10 %→90 % del desplazamiento final).
- **Tiempo de establecimiento** (entrada permanente en ±2 % del valor final).
- **Pendiente de la región lineal** (counts/s) y **R²** de un ajuste lineal en el tramo 20–80 %. R² alto ⇒ confirma crecimiento lineal sin deceleración. La pendiente debe escalar ~lineal con `v`.
- **Sobreimpulso de posición** (si lo hubiera).

**Salida:** media ± desv. por velocidad de `L`, subida y establecimiento; overlay `POS_ACT` vs `t` de todas las velocidades (réplica de Fig. 2 izquierda).

> **Reporta L corregida y sin corregir:** `L_dispositivo ≈ L − (latencia de comunicación del Exp. 0)`.

---

## Experimento 2 — Sobreimpulso de fuerza en contacto

**Con objeto rígido.** Un bloque rígido (el paper usa un cubo de 4 cm) montado de forma que el índice presione contra él en una posición de ángulo repetible.

**Dos modos de control**

- **(a) Velocidad directa constante:** `SPEED_SET(3)=v` fijo; `FORCE_SET(3)=Fset`; comandar `ANGLE_SET(3)=0` (cerrar contra el bloque). El firmware intentará detener al alcanzar `Fset`.
- **(b) Híbrido:** `SPEED_SET=1000`, comandar `ANGLE_SET` a un **ángulo de aproximación justo antes del contacto**; al alcanzarlo, `SPEED_SET=25` y comandar `ANGLE_SET=0`. Loguear `FORCE_ACT` todo el tiempo.

**Grid**
- `v ∈ {25, 50, 100, 250, 500, 750, 1000}`
- `Fset ∈ {100, 250, 500, 750, 1000}` g  (≈ 1–10 N; cubre el rango útil para piezas delicadas)
- Trials: **20 por celda** `(v, Fset)`.

**Métrica principal:** `ΔF = F_max − Fset` por trial (sobreimpulso). Reporta media ± desv. por celda.
**Métricas secundarias:** tiempo hasta detención; `F_max`; y `POS_ACT` en el instante de primer contacto (para el sub-experimento de onset).

**Salida:** barras de `ΔF` vs velocidad, agrupadas por `Fset`, con barras de error (réplica de Fig. 2 derecha). El modo híbrido debería caer cerca de `v=25` constante.

**Seguridad (obligatorio en este experimento)**
- Techo de fuerza de emergencia: si `|FORCE_ACT| > F_safety` (p. ej. 1500–2000 g), abortar el trial y abrir (`ANGLE_SET=1000`).
- Timeout duro por trial.
- Vigila `CURRENT(3)`: corriente sostenida cerca del máximo = posible bloqueo mecánico ⇒ abrir.

---

## Sub-experimento — Variabilidad de onset y tu margen de conmutación

Para fijar el offset de tu política híbrida con **tu** hardware (el paper obtiene σ ≈ 7.5 y usa `q_sw = q_g + 25 ≈ 3.3σ`):

1. A `v=1000` (peor caso), conducir el índice contra el bloque.
2. Definir **onset de contacto** = `POS_ACT(3)` (o ángulo) en el primer instante en que `FORCE_ACT` supera el umbral de ruido.
3. Repetir **50–100 veces**.
4. Calcular `σ_onset`. Fijar el margen de conmutación `= ceil(k · σ_onset)` con `k ≈ 3.3` (cobertura > 99 % bajo supuesto ~gaussiano).

Ese margen es el offset que usarás en el modo híbrido para garantizar que entras en baja velocidad **antes** de la zona incierta de contacto.

---

## Detección de onset (algoritmo común)

```python
import numpy as np

def detect_onset(t, x, baseline_window_s=0.15, k=5.0, abs_floor=4.0, m=3):
    """Primer índice donde x se sale de la banda de baseline de forma sostenida.
       abs_floor: 4 counts para POS_ACT; ~30 g para FORCE_ACT."""
    t = np.asarray(t); x = np.asarray(x)
    base_mask = t <= (t[0] + baseline_window_s)
    mu = x[base_mask].mean()
    sigma = x[base_mask].std()
    thr = max(k * sigma, abs_floor)
    over = np.abs(x - mu) > thr
    # exigir m muestras consecutivas para descartar picos espurios
    for i in range(len(over) - m):
        if over[i:i+m].all():
            return i, t[i], mu, thr
    return None
```

- **POS_ACT:** `abs_floor ≈ 4` counts.
- **FORCE_ACT:** mide primero tu ruido real en reposo (desv. por dedo). El paper estima ~0.12 N (≈ 12 g) en el sensor de dedo; un `abs_floor ≈ 30 g` o `k·σ` es razonable.

---

## Logger de alto ritmo (lazo único intercalado)

```python
import time, csv

def run_trial(hand, dof, speed, force_set, target_angle,
              baseline_s=0.2, total_s=2.0, csv_path="trial.csv"):
    hand.write_speed(dof, speed)
    hand.write_force_set(dof, force_set)

    samples = []        # (t, pos_act, force_g, current_mA)
    cmd_issued = False
    t_cmd = None
    t_start = time.perf_counter()

    while time.perf_counter() - t_start < total_s:
        t = time.perf_counter()

        # Disparo del comando una sola vez, tras el baseline
        if not cmd_issued and (t - t_start) >= baseline_s:
            tb = time.perf_counter()
            hand.write_angle(dof, target_angle)   # escritura del escalón
            t_cmd = time.perf_counter()           # t0 para la latencia
            write_cost = t_cmd - tb               # incertidumbre de la escritura
            cmd_issued = True

        # Lectura mínima y rápida (1 bloque)
        block = hand.read_block(1582, 6)          # 6x FORCE_ACT, o usa POS_ACT
        force_raw = block[dof]
        force_g = force_raw - 65536 if force_raw >= 32768 else force_raw
        pos = hand.read_pos_act(dof)              # idealmente en el mismo bloque
        cur = hand.read_current(dof)

        # Seguridad
        if abs(force_g) > 1800:                   # techo de emergencia (g)
            hand.write_angle(dof, 1000)           # abrir
            break

        samples.append((t, pos, force_g, cur))

    # Guardar
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "pos_act", "force_g", "current_mA",
                    "t_cmd", "write_cost_s", "speed", "force_set"])
        for (t, pos, fg, cur) in samples:
            w.writerow([t - t_start, pos, fg, cur,
                        (t_cmd - t_start) if t_cmd else "",
                        write_cost, speed, force_set])
    return samples, (t_cmd - t_start if t_cmd else None), write_cost
```

> Lo ideal es **una sola transacción Modbus por iteración** que cubra todo lo que necesitas (lee un bloque contiguo y desempaca). Lecturas separadas para `pos`, `force`, `current` triplican el periodo y bajan tu tasa. Reorganiza según los bloques contiguos de tu wrapper.

---

## Análisis y figuras

1. **Por trial:** aplica `detect_onset`, calcula `L`, subida, establecimiento (Exp. 1) o `ΔF`, `F_max`, onset de posición (Exp. 2).
2. **Por condición:** media ± desv. (N=20). Guarda una tabla agregada (CSV).
3. **Figuras:**
   - *Exp. 1:* overlay `POS_ACT` vs `t` por velocidad → debe verse latencia + crecimiento lineal sin deceleración.
   - *Exp. 2:* barras `ΔF` vs velocidad agrupadas por `Fset`, + columna del modo híbrido.
4. **Reporta siempre la tasa de muestreo efectiva** alcanzada (del Exp. 0): condiciona la resolución de `L`.

---

## Checklist de ejecución

- [ ] GUI cerrada; un único proceso sobre el bus.
- [ ] Exp. 0 corrido; tasa ≥ 100 Hz confirmada y reportada.
- [ ] Ruido de `FORCE_ACT` en reposo medido por dedo (fija `abs_floor`).
- [ ] `FORCE_SET` alto en Exp. 1 (movimiento puro).
- [ ] Techo de fuerza y timeout activos en Exp. 2.
- [ ] Orden de condiciones aleatorizado; temperatura registrada por bloque.
- [ ] Cada condición repetida (2 pasadas) para verificar repetibilidad.
- [ ] CSV crudo por trial guardado; agregados y figuras generados.
- [ ] `σ_onset` a v=1000 calculado; margen de conmutación derivado.
