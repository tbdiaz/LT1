# P1L4 - FASE A: auditoria del caso EY en M001

Recomposicion del muro fisico M001 a partir del par 4001+4002 (idealizacion 'dos columnas equivalentes de media seccion').

## Desglose numerico de M_muro(EY)

| termino | valor | procedencia |
|---|---|---|
| Mz1(4001) | 4343.575161014324 kN.m | = reaccion Mx(apoyo node1) del mismo modelo |
| Mz1(4002) | 4372.675285072908 kN.m | = reaccion Mx(apoyo node3) del mismo modelo |
| N1(4001) | 0.0 kN | 0: esquina A sin canales axiales |
| N1(4002) | -82.18247978711408 kN | traccion neta (Rz(node3) del modelo) |
| par axial 1.46*(N4001-N4002) | 119.98642048918654 kN.m | Steiner (lever=1.46=L/2) |
| SUMA (M_muro EY) | 8836.23686657642 kN.m | |

## Verificaciones

1. Los Mz usados son las reacciones Mx de los apoyos (mismo valor exacto) => no hay combinacion de extremos incompatibles ni error de transformacion local/global.
2. N_muro = Rz(1)+Rz(3) con diferencia nula (tambien verificado en el test de recomposicion).
3. Ambos elementos (4001 y 4002) comparten local z=(1,0,0) y el mismo corte fisico: base B1 (extremo i).
4. Distancia 1.46 = (yB-yA)/2 con y_centro=0.365: verificada.
5. Equilibrio de momentos en los nodos 23 y 25 cierra (~0); las fuerzas en Y quedan en los diafragmas L1 (nodos no libres).
6. Sin doble contabilizacion: los Mz estan referidos al centroidide de cada media seccion y solo se trasladan las axiales (Steiner).
7. Convencion N positivo = compresion verificada con reacciones bajo G (Rz node3 = +244.11 = N1(4002)).

## Eje fuerte/debil (decision)

FiberSection2d usa la 1a coordenada del patch como brazo del momento. Con L=2.92 en 1a coord -> curva EJE FUERTE (en plano); con e=0.60 en 1a coord -> EJE DEBIL (fuera de plano). Demanda M_muro (en plano) se compara con la curva FUERTE y My_muro (fuera de plano) con la DEBIL. Capacidades nominales en el estado limite eps_cu=0.003 (evita artefacto de endurecimiento lineal de Steel01).

## Consecuencia del chequeo

M_muro(EY)=8836.23686657642 kN.m es la demanda real de la idealizacion (reaccion de fundacion del modelo). Con el acero minimo modelado (4 22/cara/extremo) la capacidad de eje fuerte en EY (N=-82 kN) es ~4966 kN.m => D/C ~ 1.78 (FUERA). No se afirma que mayor armadura de borde lo mitigue sin mostrar el calculo.
