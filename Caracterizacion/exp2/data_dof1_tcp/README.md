# DOF 1 · campaña por Modbus TCP, bloque rígido

Transporte: `192.168.124.210:6000`. Mapa `POS↔ANGLE`: se **reutiliza** el de la
campaña serial (`exp1/data_dof1/pose_dof1.csv`), no se re-midió — el pulgar
reprodujo el suyo dentro de 1 count un mes y un transporte después, y el
recorrido libre de este dedo coincide con el de serial dentro de 3 counts.

Los ΔF de esta campaña **no son comparables en valor absoluto** con los de las
campañas anteriores: el bloque es otro, más rígido, y el apriete del montaje
domina el sobreimpulso (medido en este repo: mismo dedo y misma celda, 202 → 819 g
solo por sujetar el bloque).
