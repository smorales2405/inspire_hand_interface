# Vigilar un vecino no es anclarlo — por qué la campaña de los dedos no usa `--hold`

**Fecha:** 2026-09-07 · **DOF barrido:** 0 (meñique) · **Vecino:** 1 (anular)
· Mano derecha, GUI cerrada, `/dev/ttyUSB0`, sin bloque montado.

## Qué se observó

Al correr la Fase 0 del meñique con el anular anclado (`--hold 1:1000`), el
anular **oscilaba**. Como el watchdog de seguridad de las campañas se apoya en la
fuerza de los DOF anclados, había que saber si eso era acoplamiento mecánico
entre dedos —que contaminaría la medida— o un artefacto de nuestro propio patrón
de comandos.

## Diseño

`pose_check.py --watch` registra, en cada parada del barrido, cuánto recorrió el
`POS_ACT` del vecino, su desviación de fuerza sobre el inicio del tramo y su
corriente máxima. Los DOF de `--watch` **solo se observan, nunca se comandan**,
así que el mismo barrido corre con y sin ancla y la diferencia aísla la causa.

Tres corridas, mismas paradas (`1000,750,500,250,0`), `v=200`.

## Resultado

Recorrido del `POS_ACT` del anular · corriente máxima, por parada:

| Parada | `--hold 1:1000` | `--hold 1:950` | sin ancla |
|---|---|---|---|
| 1000 | 25 c · 141 mA | 22 c · 136 mA | 11 c · 107 mA † |
| 750 | **36 c · 186 mA** | 22 c · 122 mA | **0 c · 0 mA** |
| 500 | 19 c · 101 mA | 20 c · 110 mA | **1 c · 0 mA** |
| 250 | 13 c · 101 mA | 24 c · 111 mA | **0 c · 0 mA** |
| 0 | 13 c · 194 mA | 24 c · 114 mA | **0 c · 0 mA** |

† La primera parada hereda la apertura inicial: `open_vector` manda a *todos* los
dedos a `--open-angle` antes de empezar, así que ahí el vecino se mueve por orden
nuestra. Por eso el veredicto de `--watch` la excluye.

**No es acoplamiento.** Sin comandarlo, el anular está inmóvil (0–1 counts, 0 mA)
a lo largo de todo el recorrido del meñique.

**Y no es el tope mecánico.** Esa era la primera hipótesis: `ANGLE_SET 1000` es
inalcanzable —comandado a 1000, el dedo se queda en `ANGLE_ACT 999`— así que cada
re-afirmación reiniciaría un empuje contra el límite. Pero anclar en **950**, bien
dentro del rango, da lo mismo: 20–24 counts y 110–136 mA en cada parada. Ahí el
dedo se queda en `ANGLE_ACT 946`, **4 counts corto**.

**Lo que es:** el firmware **re-ejecuta el movimiento en cada escritura de
`ANGLE_SET`**, y su banda muerta de posición (~4 counts) hace que el dedo nunca
aterrice exactamente en el objetivo. Cada re-afirmación del ancla es, por tanto,
un empujón real: ~10 counts de ángulo y ~120 mA de corriente.

## Qué no afecta

El meñique mide **igual** en las tres corridas: `POS_ACT` en las cinco paradas
sale 94/602/1089/1500/1896 (con ancla), 94/603/1087/1498/1895 (sin ancla) y
93/602/1089/1500/1894 (ancla en 950) — **≤ 2 counts** de diferencia. El rebote del
vecino no perturba al DOF bajo prueba, así que las campañas previas siguen siendo
válidas. Lo que se evita es gastar 100–190 mA de corriente de bloqueo en cada
escritura durante cientos de trials.

## Consecuencia

Se separa **anclar** (comandar) de **vigilar** (observar):

- El pulgar necesitaba `--hold 5:0` porque ahí el ancla **define la postura del
  experimento**: sin ella, cada apertura global mandaría la rotación a 1000.
- Un vecino que solo estorba no necesita ancla. En espacio libre no hay ni
  siquiera nada que vigilar. Con el bloque montado sí —un bloque ancho puede
  transmitir la carga al vecino— y para eso está `--watch` en
  `exp2_force_overshoot.py`: su desviación de fuerza entra en el mismo watchdog
  que la de los DOF anclados, sin comandarlos.

## Pendiente

La campaña del pulgar re-afirmó `--hold 5:0` decenas de veces por trial. `0` sí
parece alcanzable para la rotación (`ANGLE_ACT` llegó a 0 exacto en P0.1), así
que probablemente no rebotaba, pero **nunca se miró**. Un
`pose_check.py --dof 4 --hold 5:0 --watch 5` de un minuto lo cerraría. No afecta a
la validez de esa campaña por lo dicho arriba.

## Datos

`exp1/data_dof0/pose_dof0_watch_hold.csv` (ancla en 1000),
`pose_dof0_watch_950.csv` (ancla en 950), `pose_dof0_watch_free.csv` (sin ancla).
Columnas `w1_pos_p2p`, `w1_dforce_g`, `w1_mA_max`.
