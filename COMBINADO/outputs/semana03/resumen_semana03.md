# SEMANA 3 - PARTE A: caso de carga viva Q

- q_Q = **2.0 kPa** (PROVISIONAL / INPUT_REQUIRED; sin valor en slabs_LT2.csv ni en enunciados).

## Conservacion  sum(Q_transferida) = q_Q * area_tributaria

| origen | area (m2) | Q_teorica (kN) | Q_transferida (kN) | err_abs (kN) | err_rel | PASS |
|---|---|---|---|---|---|---|
| LT2 L1 | 463.182016 | 926.364032 | 926.364032 | -2.14e-08 | 2.31e-11 | PASS |
| LT2 L2 | 463.182016 | 926.364032 | 926.364032 | -2.14e-08 | 2.31e-11 | PASS |
| LT2 L3 | 463.182016 | 926.364032 | 926.364032 | -2.14e-08 | 2.31e-11 | PASS |
| LT2 L4 | 463.182016 | 926.364032 | 926.364032 | -2.14e-08 | 2.31e-11 | PASS |
| LT1 PISO_1 | 686.375000 | 1372.750000 | 1372.750000 | 0.00e+00 | 0.00e+00 | PASS |
| LT1 PISO_2 | 686.375000 | 1372.750000 | 1372.750000 | 0.00e+00 | 0.00e+00 | PASS |
| LT1 PISO_3 | 686.375000 | 1372.750000 | 1372.750000 | 0.00e+00 | 0.00e+00 | PASS |
| LT1 PISO_4 | 686.375000 | 1372.750000 | 1372.750000 | -0.00e+00 | 1.66e-16 | PASS |
| LT2 TOTAL | 1852.728064 | 3705.456128 | 3705.456128 | -8.57e-08 | 2.31e-11 | PASS |
| LT1 TOTAL | 2745.500000 | 5491.000000 | 5491.000000 | 0.00e+00 | 0.00e+00 | PASS |
| COMBINADO TOTAL | 4598.228064 | 9196.456128 | 9196.456128 | -8.57e-08 | 9.31e-12 | PASS |

## Analisis OpenSees (patrones 3 = LT2-Q, 4 = LT1-Q)

- analyze rc = **0** (converge).
- Q_total aplicado = 9196.456128 kN
- sum Rz = 9196.456128 kN; |sum Rz - Q_total| = 5.519e-09 kN (rel 6.001e-13).
- sum |Rx| = 1.851e-10 kN; sum |Ry| = 4.804e-11 kN.
