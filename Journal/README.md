# Journal — *Mechatronics*

Trabajo adicional para el envío a **Mechatronics** (SJR / Q / H-index).

| | |
|---|---|
| **Alcance** | Control de fuerza **sólo con el pulgar**. Los resultados de modo 1 + regulador pueden añadirse como material secundario. |
| **Fecha objetivo** | Entre mediados y finales de **noviembre de 2026** |
| **Hardware** | RH56DFTP derecha por Modbus TCP (`192.168.124.210:6000`). Existe una **segunda unidad, izquierda** (espejo). |

## Qué entra y qué no

El alcance a **sólo pulgar** deja la columna vertebral cuantitativa sobre el
montaje `block1`-en-falanges, que es el único que **no se cae y no necesita
recolocaciones**: se puede correr desatendido y repetir cuantas veces haga falta.

Queda **fuera** del artículo, y es una simplificación bienvenida:

- los tres intentos fallidos de banda adaptativa y selección de acción, que eran
  de la pinza en modo 1;
- A3 / B1 (pinza y modo 2) salvo como material secundario.

## Estado — **la lista la manda el artículo**, no la tabla de siete

Lo pendiente son los `\pending{}` de
`Mechatronics Journal/sections/07_results.tex`:

| línea | Pendiente | Estado |
|---|---|---|
| 133 | **Tres amplitudes de perturbación** (16, 28, 40 u), una sola tanda intercalada | código listo · **pendiente de hardware** |
| 18 | **Periodo de refresco de los seis actuadores**, en vacío y bajo carga (Exp. 4) | código listo · **pendiente de hardware** |
| 109 | **Segunda consigna** a ≈ 0.7 × la fuerza de resbalón medida | pendiente · hay que medir el borde antes |
| 109 | **Ablación**: refractario, banda muerta, acción integral | pendiente |
| 109 | **Réplica en la segunda mano (izquierda)** | diferido · **es espejo**, hay que verificar el mapeo de DOF |
| 53 | **Prueba de equivalencia en el pulgar**, margen pre-especificado **±0.10 N** | pendiente |
| 95 | **Calibración estática** de `FORCE_ACT` del pulgar contra pesos de **1.23 y 3.92 N** | pendiente · **el más barato y el más fundamental** |

Detalle y resultados: [`experimentos_adicionales.md`](experimentos_adicionales.md).

### Las estrategias C1–C5

De `MCI_PI_2_Beamer_SergioMorales/tablas/tabla_11.tex`:

| | |
|---|---|
| **C1** | Control de fuerza **nativo del firmware** |
| **C2** | Política **híbrida velocidad–fuerza en lazo abierto** |
| **C3** | **Regulador PI** con realimentación de fuerza intrínseca |
| C4 | C3 + integración táctil |
| C5 | C4 + supervisor adaptativo |

El brazo «firmware» de la compuerta A2 **no es C1**: se pre-posiciona rápido y
cierra a `v=25` con `FORCE_SET`, o sea la híbrida con la regulación delegada —
**C2**. La comparación publicada es **C3 frente a C2**.

## Resultados ya establecidos que el artículo hereda

De `../Control/regulador_results.md` y `../Caracterizacion/exp3/exp3_results.md`:

| | |
|---|---|
| **Compuerta A2** (pulgar, `F*`=250, N=10/brazo, intercalado) | \|error\| **11.0 g** (lazo) contra **25.0 g** (firmware), **p = 0.0074** |
| **Rechazo de perturbación** (N=10/brazo) | residual **+8 g** contra **+75 g**, **p = 0.0088** |
| **Sostener no cuesta corriente** | 31–92 mA moviéndose, **0 mA sosteniendo 160 g** |
| **Borde del actuador** (pulgar, esa pose) | cede a **459 g**, pico 575; rango por pose 455–745 g |
| **Rejilla de refresco** (E3.6a) | pulgar 30.6–30.7 ms, índice 30.5 ms, **desfase −1.9 ms** |
| **Cuanto del dedo** | pulgar ~23–27 g, índice ~60 g por escalón mínimo |
