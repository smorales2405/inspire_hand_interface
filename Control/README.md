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

- **A1 · andamiaje, seguridad y detectores** — ✔ **cerrado**, las cuatro compuertas
  pasadas con hardware.
- **A2 · lazo SISO de fuerza** — ✔ **cerrado en el pulgar** a `F* = 250 g`:
  protocolo intercalado, N = 10 por brazo, error en régimen **11 g contra 25 g**
  del firmware (p = 0.0074). **No cerrado en el índice**, y está medido por qué:
  a 250 g ese dedo está en zona muerta. Ver `regulador_results.md`.
- A3–A5 y Parte B: ver el plan.

## Cuándo avanza el control

La mano publica estado cada ~30.7 ms **por DOF** y **los seis van escalonados**
(E3.6a midió 1.9 ms entre índice y pulgar). No hay un «frame» común que detectar:
mirar si el bloque de 6 cambió **sobrecuenta** — se midieron 46–51 Hz contra los
32.6 reales, porque el bloque cambia cada vez que se actualiza cualquiera de los
seis.

Lo que sí es fiable es el valor de **ese** DOF, con una salvedad medida en banco:

| | cambios de fuerza | intervalo mediano |
|---|---|---|
| Sin carga | 6–11 Hz | **60.0 ms** = 2 × 30.7 |
| Con carga (330–1077 g) | **28.3 Hz** | **30.4 ms** |

Los intervalos son **múltiplos exactos del periodo**: el dedo publica siempre, pero
si el entero se repite la lectura parece «no fresca». Bajo carga —el régimen del
regulador— apenas pasa; en vacío, uno de cada dos frames.

Por eso `Disparador` avanza el control con **cambio de valor O plazo agotado**
(40 ms). El cambio da la cadencia natural de ~30 ms; el plazo evita que el lazo se
pare cuando el valor se repite, porque **un valor repetido no es información vieja,
es el valor actual**. Lo que no puede hacerse es integrar varias veces dentro del
mismo frame: eso es lo que inflaría `Ki`. Medido en vacío: **27 Hz de disparo**,
65–74 % de ellos por plazo.

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
