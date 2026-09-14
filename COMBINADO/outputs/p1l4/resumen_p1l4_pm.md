# P1L4 - FASE 3 (corregida): capacidades P-M y demanda

## Auditoria EY (FASE A) - desglose de M_muro(EY)

| termino | valor | fuente |
|---|---|---|
| Mz1(4001) | 4343.5752 kN.m | = reaccion Mx(node1) del modelo |
| Mz1(4002) | 4372.6753 kN.m | = reaccion Mx(node3) del modelo |
| N1(4001) | 0.0000 kN | nodo 23 sin canales axiales |
| N1(4002) | -82.1825 kN | traccion neta = Rz(node3) |
| par axial 1.46*(N4001-N4002) | 119.9864 kN.m | Steiner |
| SUMA M_muro = | 8836.2369 kN.m | |

Verificaciones: (a) los Mz son exactamente las reacciones Mx de los apoyos 1 y 3 del propio modelo; (b) N_muro = Rz(1)+Rz(3) con diferencia nula; (c) ambos elementos comparten local z = (1,0,0) y extremo i = base B1, mismo corte fisico; (d) el equilibrio de momentos en los nodos 23 y 25 cierra; (e) sin doble contabilizacion: cada Mz esta referido al centroidide de su media seccion y el par solo traslada las axiales al centroidide del muro (Steiner).

## Eje fuerte/debil del muro (decision)

FiberSection2d integra el momento con la PRIMERA coordenada del patch. Con L=2.92 en la 1a coord -> curva EJE FUERTE (en el plano, momento de vuelco sobre X global). Con e=0.60 en la 1a coord -> curva EJE DEBIL (fuera de plano). Verificado por experimento con el mismo acero: pico debil ~1366 kN.m (P=0) vs fuerte ~8398 kN.m (P=0). M_muro se compara contra la curva FUERTE; My_muro contra la curva DEBIL.

## Demanda (recomposicion 4001+4002) y capacidad

| caso | N_col | M_col | M_cap_col | dentro | N_muro | M_muro fuerte | M_cap_fuerte | dentro | My_muro debil | M_cap_debil | dentro |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G | 1063.49 | 8.36 | 1025.37 | True | 244.11 | 408.37 | 5379.09 | True | 18.84 | 1573.50 | True |
| Q | 598.18 | 5.00 | 909.44 | True | 160.58 | 268.62 | 5273.39 | True | 12.54 | 1551.79 | True |
| EX | 0.13 | 348.97 | 754.75 | True | 0.11 | 600.36 | 5070.21 | True | 942.07 | 1510.04 | True |
| EY | 30.02 | 115.47 | 762.67 | True | -82.18 | 8836.24 | 4965.94 | False | 8.41 | 1488.34 | True |
| COMBO_R | 1661.80 | 341.14 | 1168.56 | True | 404.80 | 76.63 | 5582.41 | True | 910.69 | 1615.26 | True |

## Supuestos (FASE 1) y criterios

* material CONFIRMADO: fc=35 MPa, fy=420 MPa, Es=200 GPa.
* columna 113022: P.70x70, 16 22 EXACT (plano); distribucion simetrica y recubrimiento 0.04 m: SUPUESTO.
* muro M001: e=0.60 CONFIRMADO_PLANO(303); L=2.92 GEOMETRIA DEL MODELO (csv/modelo); malla D.M.V. 12 a 20 doble cara PLANO; borde minimo 4 22 por cara y extremo SUPUESTO conservador (plan 303 muestra mas acero: 2 22/+2 22/+4 22/+4 25, base 5 32 L=900, atribucion por nivel NO_LEGIBLE).
* Concrete01 no confinado, Steel01 b=0.01; capacidad nominal sin phi.
* EY: M_muro = 8836 kN.m CONFIRMADO como demanda real de la idealizacion (reacciones de fundacion del modelo). Su D/C se reporta contra la capacidad de eje fuerte con el acero minimo modelado; no se afirma que mas armadura lo mitigue sin demostracion cuantitativa.
