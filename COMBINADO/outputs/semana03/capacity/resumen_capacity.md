# SEMANA 3 - PARTE D: capacidad de columna LT1 (fiber section)

Analisis SOLO de seccion con OpenSeesPy. No se modificaron la Parte A, B ni C, ni `run_combined.py`.

## Columna usada

- **LT1 tag `111000`** (etiqueta del modelo combinado; las 90 columnas LT1 tienen la misma seccion y armadura, ver `outputs/reinforcement/armadura_lt1_columnas.csv`).
- Dimensiones: **70 x 70 cm** (seccion `P. 70x70` en `outputs/unity/modelo_lt1.json`).
- Armadura REAL (planos): **16 barras longitudinales Φ22 mm** (As = 0.006082 m², rho = 0.0124); fuente `outputs/reinforcement/armadura_lt1_columnas.csv` (bar_count=16, diameter_mm=22, status EXACT, source USER_CONFIRMED_DRAWING_DATA).

## SUPUESTOS DE MODELACION (los planos NO los documentan)

Los planos LT1 (2017_67-000/001, hojas de plantas y de columnas) no indican f'c, fy ni recubrimiento; el plano general 2017_67-000 remite los recubrimientos a la E.T.O.G., documento no disponible. Por eso la Parte D se resuelve con los siguientes supuestos, que NO son datos reales del proyecto:

| concepto | valor | caracter |
|---|---|---|
| f'c (hormigon) | 30 MPa = 30000 kPa | **SUPUESTO** |
| fy (acero) | 420 MPa = 420000 kPa | **SUPUESTO** |
| Es / endurecimiento acero | 200 GPa, b = 0.01 | **SUPUESTO** |
| distancia adoptada de 4 cm desde la cara al EJE de las barras | 0.04 m | **SUPUESTO** (no es recubrimiento libre) |
| distribucion de las 16 Φ22 | 4 esquinas + 3 por cara, simetrica en ambos ejes | **SUPUESTO** (los planos no la definen) |
| hormigon | Concrete01 no confinado (fpc=-30000, epsc0=-0.002, fpcu=-6000 kPa, epsscu=-0.006) | **SUPUESTO** (sin estribos documentados) |
| discretizacion | parche bruto 0.70x0.70 m en fibras (32x32); no se descuenta el area de acero | **SUPUESTO** (practica usual) |

## Metodo

Fiber section con elementos `Concrete01`/`Steel01` y `zeroLengthSection` (esquema canonico OpenSees 'Moment Curvature Example'): carga axial constante (timeSeries Constant) + momento de referencia unitario (Linear) y `DisplacementControl` sobre el GDL de rotacion; el factor de carga resultante es el momento. Para cada carga axial P se conserva la rama ascendente hasta el pico (capacidad). La compresion pura P0 se obtiene con un empuje axial (M ~ 0).

## M-phi

| P (kN) | kappa_pico (rad/m) | M_pico (kN·m) |
|---|---|---|
| -10000 | 0.00440 | 1385.26 |
| -7500 | 0.00640 | 1610.63 |
| -5000 | 0.00800 | 1657.51 |
| -2500 | 0.01400 | 1390.62 |
| 0 | 0.06800 | 900.85 |
- Maximo entre las ramas evaluadas: **M = 1657.51 kN·m** a P = -5000 kN.
- Interpretacion breve: la capacidad en flexion sube con la compresion axial hasta la zona balanceada (max ~ 1658 kN·m cerca de P = -5000 kN) y baja a partir de ahi hacia la compresion pura; curvas completas en `moment_curvature.csv`.

## P-M (primeros puntos)

| punto | P (kN) | M (kN·m) |
|---|---|---|
| P=0 (flexion pura) | 0.00 | 900.85 |
| P=-2500 kN (intermedio) | -2500.00 | 1390.62 |
| P=-5000 kN (intermedio) | -5000.00 | 1657.51 |
| P=-7500 kN (intermedio) | -7500.00 | 1610.63 |
| P=-10000 kN (intermedio) | -10000.00 | 1385.26 |
| P0 (compresion pura) | -17132.85 | 0.00 |
- P = 0 (flexion pura): M = 900.85 kN·m.
- M ~ 0 (compresion pura): P0 = -17132.85 kN, |M|max = 2.238e-13 kN·m en el empuje.
- Referencia de diseño (0.85·f'c·(Ag-As) + fy·As) = 14894.40 kN: el valor de fibras (-17132.85 kN) usa el material real (sin el factor 0.85 del codigo), por eso difiere.
- Interpretacion breve: el diagrama muestra el par (M, P) de capacidad; todo M supera 0 solo bajo compresion axial (la seccion no resiste traccion neta), y la maxima compresion ocurre con M practicamente nulo. Los puntos dependen directamente de los SUPUESTOS f'c, fy, distancia cara->eje y distribucion.

## Supuestos vs. datos reales

- Datos REALES del proyecto: seccion 70x70 y 16 Φ22 (planos).
- SUPUESTOS: f'c = 30 MPa, fy = 420 MPa, distancia adoptada de 4 cm desde la cara al eje de las barras y distribucion de las 16 barras. Si se confirman otros valores (E.T.O.G. o memoria de calculo), solo cambian las constantes `FC_KPA`, `FY_KPA`, `COVER_M`/`bar_positions()` y se reejecuta este modulo.

## Archivos

- `fiber_section.png` - seccion con fibras, barras y cotas.
- `moment_curvature.csv` / `moment_curvature.png` - ramas M-phi.
- `pm_interaction.csv` / `pm_interaction.png` - primeros puntos P-M.
