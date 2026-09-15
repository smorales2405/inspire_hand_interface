# DOF 0 · campaña por Modbus TCP

Transporte: `192.168.124.210:6000`. Mapa `POS↔ANGLE`: se **reutiliza** el de la
campaña serial (`exp1/data_dof0/pose_dof0.csv`), no se re-midió — el pulgar
reprodujo el suyo dentro de 1 count un mes y un transporte después, y el
recorrido libre de este dedo coincide con el de serial dentro de 3 counts.

## El bloque

Se intentó usar un bloque **más rígido**, para que no cediera al ser golpeado a
alta velocidad. **No se pudo montar**: a ninguna posición alcanzable la yema lo
tocaba antes del final de su recorrido. En el medio el contacto caía en
`POS 1884` con el tope libre en 1916 —32 counts de margen, el dedo casi cerrado—
y a esa flexión su propio residual ya vale 148 g, lo que dejaba `Fset = 100`
inejecutable. Ese sondeo se conserva como `probe_dof2_rig1.csv`.

Así que se volvió al **bloque de las campañas anteriores** (`tcp1`). Consecuencia:
esta campaña **no mejora** la rigidez del contacto respecto a las anteriores, y
sus ΔF arrastran la misma reserva — el montaje cede un poco al impacto, así que
son cotas inferiores. Lo que sí aporta es que todo lo demás (transporte,
pre-posición asentada, curvas libres propias) está al día.
