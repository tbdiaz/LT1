# SEMANA 3 - PARTE A: caso de carga viva Q

- q_Q = **4.0 kPa = 4.0 kN/m2** (CIERRE DEFINITIVO DE PARTE A).

## Criterio de q_Q (NCh1537.Of2009, Tabla 4)

- Edificacion **EDUCACIONAL** segun NCh1537.Of2009 Tabla 4: salas de clases = 3.0 kPa; pasillos = 4.0 kPa.
- Los planos estructurales disponibles de LT1 y LT2 no permiten identificar ni separar con certeza salas de clases y pasillos (no existen planos arquitectonicos que zonifiquen los usos).
- Se adopta para esta entrega **q_Q = 4.0 kPa = 4.0 kN/m2** UNIFORME en las superficies transitables de LT1 y LT2.
- **4.0 kPa es una HIPOTESIS CONSERVADORA DE MODELACION** por la ausencia de planos arquitectonicos que permitan zonificar los usos. NO se afirma que NCh1537 exija 4.0 kPa para TODAS las superficies de un edificio educacional.
- Se REEMPLAZA el q_Q provisional anterior (2.0 kPa); las SC zonales del plano LT1 NO se integran al modelo (propuesta descartada).
- La geometria tributaria de la Semana 2 se mantiene EXACTA: no se recalcularon poligonos ni areas tributarias; cada franja de carga cierra a area_franja * q_Q.

## Conservacion  sum(Q_transferida) = q_Q * area_tributaria

| origen | area (m2) | Q_teorica (kN) | Q_transferida (kN) | err_abs (kN) | err_rel | PASS |
|---|---|---|---|---|---|---|
| LT2 L1 | 463.182016 | 1852.728064 | 1852.728064 | -4.27e-08 | 2.30e-11 | PASS |
| LT2 L2 | 463.182016 | 1852.728064 | 1852.728064 | -4.27e-08 | 2.30e-11 | PASS |
| LT2 L3 | 463.182016 | 1852.728064 | 1852.728064 | -4.27e-08 | 2.30e-11 | PASS |
| LT2 L4 | 463.182016 | 1852.728064 | 1852.728064 | -4.27e-08 | 2.30e-11 | PASS |
| LT1 PISO_1 | 686.375000 | 2745.500000 | 2745.500000 | 0.00e+00 | 0.00e+00 | PASS |
| LT1 PISO_2 | 686.375000 | 2745.500000 | 2745.500000 | 0.00e+00 | 0.00e+00 | PASS |
| LT1 PISO_3 | 686.375000 | 2745.500000 | 2745.500000 | 0.00e+00 | 0.00e+00 | PASS |
| LT1 PISO_4 | 686.375000 | 2745.500000 | 2745.500000 | -0.00e+00 | 1.66e-16 | PASS |
| LT2 TOTAL | 1852.728064 | 7410.912256 | 7410.912256 | -1.71e-07 | 2.30e-11 | PASS |
| LT1 TOTAL | 2745.500000 | 10982.000000 | 10982.000000 | 0.00e+00 | 0.00e+00 | PASS |
| COMBINADO TOTAL | 4598.228064 | 18392.912256 | 18392.912256 | -1.71e-07 | 9.28e-12 | PASS |

## Analisis OpenSees (patrones 3 = LT2-Q, 4 = LT1-Q)

- analyze rc = **0** (converge).
- Q_total aplicado = 18392.912256 kN
- sum Rz = 18392.912256 kN; |sum Rz - Q_total| = 1.091e-08 kN (rel 5.932e-13).
- sum |Rx| = 3.703e-10 kN; sum |Ry| = 9.585e-11 kN.
## SEMANA 3 - PARTE B: sismo pseudoestatico (EX y EY)

**NOTA (seccion PREVIA):** la Parte B que sigue fue calculada con el q_Q ANTERIOR = 2.0 kPa. NO se recalculo en este cierre de Parte A; queda PENDIENTE de actualizar con q_Q = 4.0 kPa cuando lo indique el usuario.


- seismic_coefficient = **0.20** (PROVISIONAL / INPUT_REQUIRED; solo el EJEMPLO del enunciado '20% de g' NCh433; lo definira el profesor).
- live_load_mass_fraction = **0.50** (enunciado; configurable).
- patron lateral = **uniforme**  (F_i = coef * W_i).
- W_i = G_i + 0.5*Q_i. G_i = peso gravitacional tributario del piso (PP losa + terminaciones; LT2: sumas por level de `gravity_loads_applied_LT2.csv`, LT1: `carga_total_tributaria_kN` de `modelo_lt1.json`). NO recalculadas areas tributarias; NO se incluye p.p. de vigas/columnas/muros.
- Q_i reutiliza los archivos aplicados del caso Q (Parte A).
- Fuerza aplicada en el master node de cada piso (masters existentes 1001..1005 reutilizados).
- ROOF (master 1005): sin masa sismica definida en el modelo tributario -> W_ROOF = 0, sin F_ROOF (decision confirmada). SI se reporta su desplazamiento.

### Peso sismico por piso

| piso | master | G_i (kN) | Q_i (kN) | 0.5*Q_i (kN) | W_sismico (kN) |
|---|---|---|---|---|---|
| L1 | 1001 | 8000.912831 | 4598.228064 | 2299.114032 | 10300.026863 |
| L2 | 1002 | 7915.594976 | 4598.228064 | 2299.114032 | 10214.709008 |
| L3 | 1003 | 7810.859954 | 4598.228064 | 2299.114032 | 10109.973986 |
| L4 | 1004 | 7996.548871 | 4598.228064 | 2299.114032 | 10295.662903 |
| ROOF | 1005 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| **sum** | | **31723.916631** | **18392.912256** | **9196.456128** | **40920.372759** |

- sum(Q_i) = 18392.912256 kN  vs  Q_total Parte A = 18392.912256 kN
  -> OK
- sum(G_i) = 31723.916631 kN (peso usado para formar la masa sismica; componentes: PP losa + terminaciones).

### Fuerzas laterales  (F_i = coef * W_i, patron 'uniforme')

| piso | master | W_i (kN) | F_i (kN) |
|---|---|---|---|
| L1 | 1001 | 10300.026863 | 2060.005373 |
| L2 | 1002 | 10214.709008 | 2042.941802 |
| L3 | 1003 | 10109.973986 | 2021.994797 |
| L4 | 1004 | 10295.662903 | 2059.132581 |
| **F_total** | | | **8184.074552** |

### Corte basal y convergencia (ver seismic_equilibrium.csv)

| caso | F_total (kN) | corte_basal (kN) | err_abs (kN) | err_rel | PASS | analyze rc |
|---|---|---|---|---|---|---|
| EX | 8184.074552 | 8184.074552 | 1.884e-08 | 2.30e-12 | PASS | 0 |
| EY | 8184.074552 | 8184.074552 | 2.385e-09 | 2.91e-13 | PASS | 0 |

### Desplazamientos de master nodes (signo de la deformada)


#### EX (fuerzas en +X)
- Sentido de la deformada: **+X coherente**.
- Torsion por piso: **TORSION APRECIABLE** (max |RZ| = 1.205e-05 rad).

| piso | master | UX (m) | UY (m) | RZ (rad) |
|---|---|---|---|---|
| L1 | 1001 | 4.080164e-03 | 7.145412e-07 | -6.254626e-06 |
| L2 | 1002 | 9.150421e-03 | -7.662278e-06 | -1.204532e-05 |
| L3 | 1003 | 1.020360e-02 | -3.521133e-05 | -1.008082e-05 |
| L4 | 1004 | 1.109905e-02 | -6.476274e-05 | -9.129564e-06 |
| ROOF | 1005 | 1.160229e-02 | -9.220282e-05 | -8.076673e-06 |

#### EY (fuerzas en +Y)
- Sentido de la deformada: **+Y coherente**.
- Torsion por piso: **TORSION APRECIABLE** (max |RZ| = 1.403e-04 rad).

| piso | master | UX (m) | UY (m) | RZ (rad) |
|---|---|---|---|---|
| L1 | 1001 | -7.674708e-06 | 1.665559e-03 | -9.203566e-06 |
| L2 | 1002 | -1.960155e-05 | 4.506881e-03 | -4.267427e-05 |
| L3 | 1003 | -2.754436e-05 | 6.586995e-03 | -9.515114e-05 |
| L4 | 1004 | -5.205323e-05 | 7.966014e-03 | -1.256267e-04 |
| ROOF | 1005 | -7.752533e-05 | 8.706510e-03 | -1.402859e-04 |

Nota: EX y EY son casos independientes (cada uno con su propio modelo y patron: 5 = EX, 6 = EY); no se aplicaron G, Q ni superposicion. Los patrones 1/2 (G) y 3/4 (Q) de la Parte A no se modificaron.
## SEMANA 3 - PARTE C: combinacion R = 1.0G + 1.0Q + 1.0EX + 0.0EY

- Superposicion lineal de los casos existentes G (patrones 1/2), Q (3/4), EX (5) y EY (6), con coeficientes {G:1.0, Q:1.0, EX:1.0, EY:0.0}.
- Corrida explicita equivalente: un solo modelo con G + Q + EX aplicados simultaneamente; EY (coef 0.0) NO se aplica.
- Verificacion MINIMA: desplazamiento del master 1005 (ROOF), reaccion del apoyo 1, fuerza interna de la columna 3001.

| cantidad | err_abs | err_rel | PASS |
|---|---|---|---|
| Desplazamiento master 1005 (ROOF, 6 GDL) | 0.000e+00 | 2.12e-14 | PASS |
| Reaccion apoyo 1 (6 GDL) | 0.000e+00 | 6.10e-15 | PASS |
| Fuerza interna columna 3001 (12 GDL) | 0.000e+00 | 2.15e-15 | PASS |

Vectores completos por item: `superposition_results.csv` (superposicion vs corrida explicita) y `superposition_cases.csv` (respuesta de cada caso corrido).
