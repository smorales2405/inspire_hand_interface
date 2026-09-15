# Qué bifurca el contacto: nada. Es la cadencia del propio actuador

**Fecha:** 2026-09-14 · DOF 4 (flexión del pulgar), rotación anclada en oposición
· Modbus TCP · montaje `tcp2` (bloque re-montado; onset geométrico POS 781).
Datos: `data_dof4_tcp_bif_v25/`, `data_dof4_tcp_bif_v1000/` — 60 toques por
velocidad con traza completa de `POS_ACT`, `FORCE_ACT` y `CURRENT`.

## La pregunta

Los sub-experimentos de onset daban una posición de contacto con **dos grupos**
separados ~70–80 counts, en serial y por TCP, en tres montajes distintos. Con
solo la posición de primer contacto se veía la estructura pero no la causa.
Cuatro candidatas, cada una con su firma:

| Hipótesis | Firma esperada |
|---|---|
| Dos puntos de apoyo | persiste a `v=25`; cada grupo con su propia pendiente de contacto |
| Deslizamiento | caída de fuerza y pico de corriente antes del onset; raro a `v=25` |
| Juego del montaje | los toques caen en el mismo grupo en rachas consecutivas |
| Artefacto de medida | desaparece a `v=25` |

## El resultado

| | `v=25` | `v=1000` |
|---|---|---|
| N | 60 | 60 |
| σ del onset | **1.5 counts** | 24.9 |
| Rango | 807–815 | 824–930 |
| Grupos | **uno solo**, sin hueco | 55 en 824–863 · **hueco de 56** · 5 en 919–930 |

**A `v=25` no hay bifurcación.** La repetibilidad del contacto es de **σ = 1.5
counts** sobre 60 toques — un orden de magnitud mejor que cualquier cifra
publicada hasta hoy. La estructura es exclusiva de la alta velocidad, así que no
es geometría ni montaje.

Y no es deslizamiento: la fuerza sube **monótona** hasta el onset en los dos
grupos (caída máxima previa: 4 g en el grupo bajo, 6 g en el alto, dentro del
ruido del sensor). Los 5 toques del grupo alto están además repartidos por toda
la tanda (nº 3, 28, 42, 52, 55), no en una racha.

## La causa

En la traza de un toque a `v=1000`, `POS_ACT` va **533 → 537 → 553 → 672 → 745 →
828 → 911**. No es nuestro muestreo —se lee a 259 Hz— sino que **el registro no
cambia más a menudo**:

| | `v=25` | `v=1000` |
|---|---|---|
| Tasa de lectura | 258 Hz | 259 Hz |
| `POS_ACT` cambia cada | **30.6 ms** | **30.7 ms** |
| Avance por refresco cerca del contacto | **2 counts** | **82 counts** |

**La mano publica estado nuevo cada ~30.7 ms (≈33 Hz)**, y la cadencia es la
misma a cualquier velocidad, para `POS_ACT`, `FORCE_ACT` y `CURRENT` por igual.
Verificado en cuatro datasets independientes y en los dos transportes:

| Dataset | Se lee a | El valor cambia cada |
|---|---|---|
| Grid TCP, `v=1000` | 596 Hz | 30.5 ms → 33 Hz |
| Grid TCP, `v=25` | 579 Hz | 31.1 ms → 32 Hz |
| Modo B TCP | 575 Hz | 31.0 ms → 32 Hz |
| Grid **serial**, `v=1000` | 78 Hz | 31.1 ms → 32 Hz |

De ahí sale todo. Cerca del contacto a `v=1000` el dedo recorre **82 counts entre
refrescos**, así que el onset solo puede caer en uno de dos valores consecutivos
del registro — y **la separación medida entre los dos grupos es de 82 counts**.
No son dos posiciones de contacto: son **dos escalones del registro de posición**.
A `v=25` el mismo escalón vale 2 counts, y por eso ahí no hay estructura que ver.

Encaja también el reparto variable de los grupos entre campañas (20 %, 46 %,
8 % arriba): depende de en qué punto del ciclo de refresco caiga el contacto, que
cambia con la posición del bloque.

## Lo que esto retracta

**La explicación original de la campaña serial era correcta y la corrección de
esta mañana era errónea.** `exp2_results_dof4.md` decía «a v=1000 la cuantización
de `POS` por muestra domina la σ medida», y hoy se anotó que eso no se sostenía
porque a 9× la tasa de lectura la σ no bajaba. **El test estaba mal planteado:**
la cuantización no está en nuestro muestreo sino en el refresco del registro, que
ningún transporte puede acelerar — leíamos a 596 Hz un valor que cambia a 33 Hz.

Queda por tanto:

- La **repetibilidad mecánica del contacto es σ ≈ 1.5 counts**, no 10 ni 40.
- La σ de 40.2 que se reportó esta mañana como «dispersión mecánica» **no es
  mecánica**: es el paso del registro a esa velocidad.
- El **margen de conmutación de 120 counts sigue justificado**, pero por otra
  razón: no por dispersión del contacto, sino porque a alta velocidad el
  controlador **no puede saber dónde está el dedo mejor que ±82 counts**, por
  mucho que lea rápido. Es una cota de la plataforma, no del dedo.
- El **retardo de detección** se descompone por fin: a `v=25` vale +27 counts
  sobre el onset geométrico, que es exactamente el margen de fuerza
  (120 g ÷ 5.12 g/count ≈ 23 counts) más un par de refrescos. A `v=1000` vale
  +62, y los ~35 counts extra son el registro llegando tarde.

## Consecuencia para la plataforma

La tasa de realimentación útil de esta mano es **~33 Hz**, no los 98 Hz del
Exp 0 ni los 797 del enlace TCP: esas son tasas de **lectura**, y por encima de
33 Hz se releen valores que no han cambiado. Importa para el lazo de control del
agarre y para la integración con el humanoide: leer más rápido no da información
nueva, solo la entrega antes (hasta ~30 ms menos de espera, que sí es real).

Con 33 Hz, un pico de impacto de 114 ms —el más corto medido, a `v=1000`— se
muestrea con solo ~4 valores distintos. El `F_max` publicado puede por tanto
quedar algo por debajo del pico real; el sesgo está acotado por lo que cambie la
fuerza en 30 ms, y **ningún transporte lo corrige**.
