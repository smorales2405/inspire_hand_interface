# Montajes de contacto — qué objeto tocaba cada dedo

Fotos en [`exp pictures/`](exp%20pictures/). Este documento existe porque **toda
cifra de contacto del proyecto** —`k_c`, distancia de frenado, ΔF— depende del
objeto y de **cómo** lo toca la yema, y hasta ahora eso solo estaba en la
memoria de quien montó los experimentos.

## Los dos objetos

| | `block1` | `block2` |
|---|---|---|
| Qué es | **Fuente de alimentación de portátil** (caja de plástico ABS) | **Pila de placas metálicas** atornilladas |
| Foto | `hand_block1.jpeg` | `hand_block2.jpeg` |
| Apoyo | Suelto sobre la palma, sin sujeción | Suelto sobre la palma |
| Comportamiento al golpe | **Se inclina** y vuelve a su posición | No se mueve, o muy poco |
| Campañas | índice, medio, anular, pulgar | anular (cara plana), meñique |

`block1` no es un bloque rígido: es una carcasa de plástico con un transformador
dentro, apoyada sin fijar. Que **se incline elásticamente** durante el impacto y
recupere la posición es coherente con eso, y es lo que se midió como
compliancia del montaje — no como deriva de la geometría.

## Cómo tocaba cada dedo

| Dedo | Objeto | Contacto | Foto |
|---|---|---|---|
| Índice (3) | `block1` | **borde superior (esquina)** | `block1_index_contact.jpeg` |
| Medio (2) | `block1` | **borde superior (esquina)** | `block1_middle_contact.jpeg` |
| Anular (1) | `block1` | **borde superior (esquina)** | `block1_ring_contact.jpeg` |
| Pulgar (4) | `block1` | **borde**, con el objeto **sobre las falanges** | `block1_thumb_contact.jpeg`, `hand_block1_for_thumb.jpeg` |
| Anular (1) | `block2` | **cara plana** | `block2_ring_contact.jpeg` |
| Meñique (0) | `block2` sin una placa | **cara plana** | `block2_little_contact.jpeg` |

### Consecuencia 1 — toda la rigidez publicada es de contacto en arista

Índice, medio, anular y pulgar tocaban el **borde** de `block1`. Una arista
concentra la carga en una línea en vez de repartirla sobre la yema, y eso es
coherente con que las `k_c` medidas salgan todas altas (11–21 g/count) y con que
las distancias de frenado sean de pocos counts. **No son cifras de un contacto
sobre cara plana**, y así hay que citarlas.

Dato que lo acota: al pasar el anular de arista (`block1`) a cara plana
(`block2`), `k_c` **no bajó** — 16.6 → 17.9 g/count. Repartir el contacto sobre
una cara no ablandó nada. Pero las dos medidas están además en poses distintas
(`POS 1411` contra `1720`), así que no aíslan el efecto de la geometría.

### Consecuencia 2 — el pulgar no apoyaba contra lo mismo que los demás

Para que el pulgar alcanzara el borde, `block1` tuvo que colocarse **encima de
las falanges proximales de los cuatro dedos**, no sobre la palma
(`hand_block1_for_thumb.jpeg`). **Y con la rotación del pulgar anclada en
oposición** (`--hold 5:0`, `ANGLE_SET(5)=0 ≈ 90°`): sin ese ancla el pulgar
describe otra trayectoria, roza el bloque durante toda la carrera y el sondeo da
`k_c` 0.73 en vez de 5.8. Si la salida dice `Anclado: —`, la medida del pulgar no
vale. Es decir: su objeto estaba sostenido por **dedos
compliantes**, mientras que el de los demás se apoyaba en la palma rígida.

Eso abre una explicación alternativa para el hallazgo 1 de
[`exp2/exp2_results_dof4.md`](exp2/exp2_results_dof4.md) —«el pulgar golpea más
suave, 0.3–0.6× el ΔF del índice, y la causa es menos inercia en movimiento»—:
**un apoyo más blando absorbe más impacto**. Las dos hipótesis predicen lo mismo
y los datos actuales no las separan. Lo decidiría medir el pulgar contra un
objeto apoyado en la palma, si se encuentra una postura en que lo alcance.

## Trazabilidad de los montajes

| Etiqueta `--mount` | Objeto | Dedo | Campaña |
|---|---|---|---|
| `m1`, `m3` | `block1` | pulgar | serial |
| `m1`, `m2` | `block1` | meñique | serial |
| `fijo` | `block1` | anular, medio | serial |
| `tcp1` | `block1` | pulgar, medio, anular | TCP |
| `tcp2`, `tcp2post` | `block2` | anular (cara plana) | TCP |
| `tcp3` | `block1` | anular (remontado) | TCP |
| `b2` | `block2` (pila corta) | meñique | TCP — pose extrema, descartada |
| `b2b` | `block2` **+1 placa** | meñique | TCP |
| `rig1` | bloque rígido **descartado** | medio | TCP (no alcanzaba) |
| `e3` | `block1` | índice | TCP — Exp 3, prerrequisito |
| `e3b`, `e3c` | `block1` **fallidos** | índice | el bloque se escapaba de lado (`k_c` 1.03 y 0.91) |
| `e3d` | `block1` | índice | TCP — Exp 3, E3.2 a `F₀=1000` |
| `e3e` | `block1` | índice | TCP — Exp 3, E3.1/E3.3/E3.4/E3.5 |
| `e4` | `block1` **fallido** | pulgar | sondeo lanzado **sin `--hold 5:0`** (`k_c` 0.73) |
| `e4r` | `block1` sobre las falanges | pulgar | TCP — Exp 3, E3.1/E3.2 |
| `e4s` | `block1` sobre las falanges | pulgar | TCP — Exp 3, E3.3/E3.4/E3.5 |

**Reproducibilidad del montaje del índice**, que fue el más difícil de asentar:

| Montaje | Onset | `k_c` | Frenado a 100 g |
|---|---|---|---|
| `e3` | 1448 | 12.44 | 14 |
| `e3b`, `e3c` | — | **1.03 / 0.91** | — (el bloque se iba) |
| `e3d` | 1442 | 12.67 | 16 |
| `e3e` | 1445 | 11.32 | 16 |

**Y del pulgar:**

| Montaje | Onset | `k_c` | Parada | Frenado |
|---|---|---|---|---|
| `m1`, `m3` | 775–780 | 5.66–5.96 | 840 | 22–26 |
| `e4` (sin ancla) | **513** | **0.73** | **1004** | 111 |
| `e4r` | 783 | 5.79 | 845 | 25 |
| `e4s` | 789 | 5.63 | 854 | 22 |

El criterio que se usó para dar un montaje por bueno antes de cada campaña fue
**reproducir los tres números del montaje de referencia** (onset, `k_c`, parada).
Los tres montajes fallidos se detectaron así, antes de gastar una tanda.

El bloque rígido que se probó y se descartó no aparece en las fotos: a ninguna
posición montable la yema lo tocaba antes del final de su recorrido.

> **Nota sobre comparabilidad.** Los ΔF solo son comparables entre sí dentro del
> mismo objeto, la misma pose de contacto y —como quedó demostrado en el anular—
> la misma tanda. Entre campañas distintas valen las magnitudes y las
> tendencias, no los valores absolutos.
