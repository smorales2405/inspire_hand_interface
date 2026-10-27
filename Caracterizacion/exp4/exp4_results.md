# Exp 4 — Tasa de refresco de los registros, por DOF y por carga

Experimento añadido para el envío a *Mechatronics* (ver
[`../../Journal/experimentos_adicionales.md`](../../Journal/experimentos_adicionales.md), #5).

Verifica si los **~30.7 ms** son una propiedad común de la mano o un hallazgo de
los dos DOF donde se midió.

## Qué había antes

| fuente | medida |
|---|---|
| E3.6a | pulgar **30.6 / 30.7 ms**, índice **30.5 ms**, desfase **−1.90 / −1.80 ms** |
| E3.2 (17 581 muestras, 191 s) | medio bajo contacto sostenido: `POS` cambia cada **32.4 ms** |

## La advertencia que gobierna el diseño

E3.6a dejó escrito que **los otros cinco DOF no contestan la pregunta**: su `POS`
no cambia **ni una vez** en 191 s, y sus «cambios» de fuerza son **ruido cruzando
enteros**, no refrescos. El desfase aparente de +0.00 ms del DOF 3 en aquella
tanda es artefacto de eso — con instantes de ruido densos, cualquier referencia
encuentra coincidencia.

**Conclusión de método: a un DOF quieto y descargado no se le puede medir la
rejilla.** Hay que hacerlo producir señal. De ahí las cuatro condiciones.

## Condiciones

| | qué hace | qué mide |
|---|---|---|
| `quieto` | todo parado y descargado | el **control**: demuestra que aquí no hay rejilla observable |
| `movimiento` | cada DOF barre despacio (`v=12`), de uno en uno | la rejilla de `POS` por DOF, en vacío |
| `escalonado` | varios DOF barren a la vez | el **desfase** entre ellos |
| `carga` | el pulgar sostiene ~250 g contra el montaje | la rejilla de `FORCE` bajo carga |

El sondeo corre a ~250–380 Hz contra una rejilla esperada de ~32.6 Hz, o sea
**8–12× de sobremuestreo**.

## Cómo se estima el periodo

Los intervalos entre cambios **se agrupan en *T*, 2*T*, 3*T*…**, porque un entero
que se repite esconde un refresco. El estimador:

1. periodo base *T* = mediana de los intervalos **cortos** (≤ 1.5 × mediana), que
   son los que capturan un solo refresco;
2. validación: qué fracción de **todos** los intervalos cae a ±15 % de un múltiplo
   entero de *T*.

Una fracción alta confirma la rejilla; una baja significa que lo que se está
midiendo no es un refresco periódico.

## El claim honesto

Lo observable es **cada cuánto cambia el entero publicado**. Un entero repetido es
indistinguible de «no hubo refresco», así que esto **acota por arriba la rejilla
de publicación del registro** — no mide la tasa de muestreo interna del firmware.
El artículo tiene que decirlo así.

## Uso

```bash
# control: nada se mueve, nada carga
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion quieto --dur 30

# la rejilla por DOF, en vacio (el pulgar exige anclar la rotacion)
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion movimiento --dofs 0,1,2,3 --dur 25
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion movimiento --dofs 4 --rot 0 --dur 25

# el desfase entre DOF
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion escalonado --dofs 3,2,1 --dur 30

# bajo carga (exige block1 montado sobre las falanges)
.venv/bin/python Caracterizacion/exp4/exp4_tasa_refresco.py --condicion carga --dofs 4 --rot 0 --dur 40
```

## Resultados

*Pendiente de hardware.*
