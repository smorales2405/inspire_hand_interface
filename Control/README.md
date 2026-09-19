# Regulador de fuerza de agarre

Lazo cerrado de fuerza sobre la Inspire RH56DFTP. Implementa el
[plan v3](Planes/PLAN_regulador_PI.md), cuyas constantes salen todas del Exp 3
(`../Caracterizacion/exp3/exp3_results.md`).

**El firmware de la mano no regula fuerza**: durante 60 s de sostenimiento consume
**0 mA**. No hay par activo — lo que retiene la fuerza es la fricción de la
transmisión. Todo lo que el lazo quiera, lo pone el lazo.

## Ficheros

| | |
|---|---|
| `nucleo.py` | Lectura con frescura, guarda de seguridad, detectores de resbalón, política de tara, bitácora. Sin controlador. |
| `lazo.py` | Ejecutor. En A1, los modos de validación de la plataforma. |
| `data/` | CSV crudos por tanda. |

Un proceso, un hilo, **un cliente Modbus**. Sin PyQt. `time.perf_counter()`.

## Estado

- **A1 · andamiaje, seguridad y detectores** — código listo, verificado contra una
  mano simulada. **Pendiente de las compuertas con hardware.**
- A2–A5 y Parte B: ver el plan.

## Los dos niveles de novedad, y por qué hacen falta los dos

La mano publica estado cada ~30.7 ms **se lea a la tasa que se lea**. Integrar
sobre lecturas repetidas inflaría `Ki` en la proporción entre tasa de sondeo y de
refresco. Por eso el lazo distingue:

- **`frame`** — el bloque de 6 DOF cambió: llegó estado nuevo. Es lo que dispara el
  control. Fiable: con seis DOF algo casi siempre cambia. Medido contra el mock:
  **32.7 Hz**, que es exactamente la tasa de publicación.
- **`fresca_f[d]` / `fresca_p[d]`** — ese dedo concreto trae valor nuevo. Dice si
  aporta información, pero **subestima**: si el entero se repite entre dos frames
  cuenta como no fresco, y con ruido de ±1–2 g eso pasa ~1 de cada 4 veces
  (medido: 24–28 Hz por DOF contra 32.7 de frames). Para `POS` la subestimación es
  total y esperada — con un solo dedo moviéndose, el `POS` de los demás no cambia
  nunca.

## Los dos detectores de resbalón

Se confunden si solo se mira la fuerza, y **la reacción correcta es opuesta**:

| | `POS` | Fuerza | Reacción |
|---|---|---|---|
| **Resbalón del actuador** | retrocede contra su comando | cae | **aflojar**: ya se pasó del borde |
| **Objeto que se escapa** | sigue al comando | cae en **todos** los dedos a la vez | **apretar** o abortar |

`POS` es lo único que los separa. Un objeto que se mueve no puede empujar al dedo
contra su propio comando: si `POS` retrocede, el que cede es el mecanismo.

Umbral: **10 counts en 0.5 s**. El sostenimiento normal mueve `POS` 0–2 counts en
60 s (E3.4) y el resbalón ~50 en menos de medio segundo, así que entre ambos hay un
abismo y 10 es inequívoco.

**No hay tope de fuerza constante.** El borde depende de la pose —455 a 745 g en lo
medido— así que quien lo encuentra es el detector, no una constante. La guarda de
fuerza sigue existiendo, pero como último recurso.

## Uso (A1)

```bash
# tasas de sondeo, frames y frescura por DOF
.venv/bin/python Control/lazo.py --modo tasas --duracion 20

# trayectoria predefinida, sin realimentación
.venv/bin/python Control/lazo.py --modo passthrough --dof 3

# la guarda debe disparar con el dedo en el aire y el techo bajo
.venv/bin/python Control/lazo.py --modo guarda --dof 3 --techo-fuerza 150

# el detector de resbalón, con el objeto YA sujeto
.venv/bin/python Control/lazo.py --modo resbalon --dof 4 --objetivo 900

# la política de tara de E3.5
.venv/bin/python Control/lazo.py --modo tara
```

## Reglas que no se negocian

- **`--rot` ancla la rotación del pulgar.** Sin anclarla el pulgar describe otra
  trayectoria: un sondeo lanzado sin ancla dio `k_c` 0.73 en vez de 5.8.
- **`FORCE_SET` siempre por encima del rango de trabajo.** Si `FORCE_ACT` lo
  alcanza, el dedo deja de aceptar `ANGLE_SET` **en los dos sentidos**.
- **La tara exige mano abierta, descargada y ≥ 10 s desde la última suelta.** Tras
  sostener carga el cero queda corrido 21–46 g y tarda ~8 s en volver, con signo
  **por DOF** (índice −46 g, pulgar +21 g).
- **Salida por cualquier vía → la mano se abre.** `try/finally`, sin excepciones.
