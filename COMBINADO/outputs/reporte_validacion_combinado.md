# Modelo combinado LT1 + LT2 — reporte de validacion

## 1. Transformacion e interfaz (APROBADA)

- LT1: X' = X + 31.250 ; Y' = -Y ; Z' = Z (sin rotacion).
- LT2: coordenadas nativas. Interfaz global en X = 31.250 m.
- Pares de nodos coincidentes: **18/18** (6 niveles x ejes 1/2/3, distancia 0.000 m).
- Un solo nodo fisico por posicion: se conserva el tag nativo LT2. Detalle: `interfaz_traceabilidad.csv`.

## 2. Retagging (sin colisiones)

- LT2: tags nativos (nodos 1..272, masters 1001..1005, vigas 2001+ (237), columnas 3001+ (50), muros 4001+ (80), secciones 5001+, transf 1/2/3).
- LT1: offset +100000 en nodos estructurales y muros; masters LT1 (600001-600004) NO se crean (sustituidos por masters combinados). Elementos con tags nativos (columnas 75, vigas 108, muros 6); transf 10001/10002/10003; timeSeries/pattern 1 (LT2) y 2 (LT1).

## 3. Elementos duplicados en la interfaz

- Duplicados geometricos detectados: **15 columnas LT1** (P70x70, ejes 1/2/3, 5 tramos) coinciden exactamente con columnas LT2 nativas (misma seccion, longitud y orientacion; difiere E: LT1 25e6 vs LT2 23.5e6 kPa).
- Decision (regla 3): conservar la **columna LT2 nativa** y descartar las 15 de LT1; la columna compartida queda con el E de LT2. No se pierde rigidez vertical (tramos iguales nivel a nivel).
- Vigas LT1 de borde en E (8) y muros LT2 en el borde: sin par, se conservan. Detalle: `auditoria_elementos_interfaz.csv`.

## 4. Diafragmas (un solo master por nivel)

- L1: master 1001 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- L2: master 1002 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- L3: master 1003 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- L4: master 1004 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- ROOF: master 1005 (LT2 nativo), 73 nodos oculares cada uno una sola vez.
- Los 12 nodos de muro LT1 se vinculan al master del nivel con ops.rigidLink('beam', master, nodo_muro) (estrategia C de LT1); NO son esclavos del rigidDiaphragm.

## 5. Apoyos

- LT2: 22 fijos (B1, empotrados).
- LT1: 15 fijos (los 3 de interfaz ya fijados como nodos LT2; sin ops.fix duplicado).
- **COMBINADO (cajas/pilastra/2ª escalera): 10 fijos nuevos en B1** (empotrados, misma convencion de fundacion que el resto del modelo; NO son restricciones artificiales: las cajas llegan a la cimentacion en la estructura real).
- Total apoyos fijos: **47** (6 GDL).

## 6. Muros LT2 (40 tramos -> 80 columnas equivalentes)

- Idealizacion: cada tramo vertical usa los **4 nodos reales del CSV** (esquinas de sus dos extremos en planta). Se crea un par de `elasticBeamColumn` (una por esquina) con **media seccion** cada una (transf 10001, vecxz (1,0,0)):
  A = e·L/2 ; muro en X: Iy = e·L^3/24, Iz = L·e^3/24 ; muro en Y: Iy = L·e^3/24, Iz = e·L^3/24 ;
  J = h·b^3/3·(1-0.63·(b/h)+0.052·(b/h)^5) / 2, b=min(e,L), h=max(e,L) (Saint-Venant).
- Los TOTALES por tramo coinciden con el muro academico LT1 (A=e·L, Ix=e·L^3/12, etc.): misma rigidez axial y flexional, sin dejar nodos flotantes en las esquinas (concepto validado contra modelo_lt1.json).
- Material del muro: LT2 (E=2.35e+07 kN/m², G=9.79e+06 kN/m²), su modulo propio.
- Elementos creados: 80 (tags 4001+, dos por tramo: 4001/4002, 4003/4004, ...).

## 7. Materiales (no unificados)

- LT1: E = 2.5e+07 kPa, G = 1.04167e+07 kPa (dato academico proporcionado).
- LT2: E = 2.35e+07 kPa, G = 9.79167e+06 kPa.
- Cada modulo conserva su material; en las columnas compartidas de la interfaz rige el E de LT2 (regla 3).

## 8. Cargas de gravedad

- LT2 (patron 1): 27160 eleLoad -beamPoint sobre 184 vigas, P = 11541.291565 kN.
- LT1 (patron 2): 108 eleLoad -beamUniform (QG), P = 20182.625066 kN.
- **P_total = 31723.916631 kN**.
- Zonas pendientes (ROOF LT2, salientes PISO_2 LT1, WALL_EDGE_PENDING) NO se cargan (se preserva el criterio de cada modelo).

## 9. Validaciones

- Nodos fisicos totales: 429 (LT2 272 + LT1 no-interfaz 102 + masters 5 + nodos nuevos cajas/pilastra 50).
- Vigas: LT1 108 | LT2 237 | LT2 pendientes 0
- VI-05 (VI15xVAR) materializada POR SUPUESTO/MODELACION (cota superior de rigidez): b=0.15 m, h=1.20 m, E/G de LT2, nodos 226-227, tag 2235 (tag nativo; 2237 no esta disponible, corresponde a ROOF_VI_07). No es una seccion real confirmada; h_min y ley de variacion siguen desconocidas (ver COMBINADO/docs/diagnostico_vi15xvar.md).
- Columnas: LT1 75 | LT2 50
- Muros: LT1 6 | LT2 80
- Conectores V40->Muro (excent. 0.300 m): 10
- Duplicados descartados: 15 columnas LT1.
- Nodos compartidos de interfaz: 18.
- Apoyos fijos: 47. Diafragmas: 5.

### Analisis
- analyze() rc = **0** (OK, convergio)
- ΣRz = 31723.916631 kN
- |ΣRz - P_total| = 2.211891e-09 kN (rel 6.972e-14)
- Σ|Rx| = 6.692795e-10 kN, Σ|Ry| = 3.256350e-11 kN (equilibrio horizontal)
- Max |U| = 0.016835411 m en nodo 178
- Max |Uz| = 0.016828445 m en nodo 178

## 11. Sistema vertical de cajas de escalera y pilastra (COMBINADO, B1->ROOF)

- **Que se modelo:** la continuidad vertical B1->ROOF bajo el anillo VI de ROOF para cerrar el mecanismo de ROOF detectado (verificar: 10 nodos sin camino a apoyos en el reporte previo).
- Fuente de geometria: `LT2/reports/digitalizacion_vi_roof_pendiente.md` §8.2/§8.5 y coordenadas reales de los nodos `LT2/data/unity/edificio_lt2.json`:
  - **Caja OESTE** bajo VI-05: muro en Y, x=0.998, y 2.90..7.92, **e=0.30 m (ASSUMED_FOR_MODEL**, espesor de caja no acotado en plan; familia M.H.A. de cajas), L=5.02 m; nodos ROOF 226/227.
  - **Caja ESTE** bajo VI-06: muro en Y, x=16.546, y 2.90..7.92, **e=0.30 m (ASSUMED_FOR_MODEL)**, L=5.02 m; nodos ROOF 256/257.
  - **Pilastra x≈7.947**: caja vertical entre los dos huecos, 4 columnas por esquina real (244/245/246/247); seccion **e_x=0.60 m EXPLICITA del plano** (caras 7.650/8.250, gap N 7.646..8.246), L_y=5.02 m; cada columna = 1/4 de seccion bruta (A=e·L_y/4, Iy/4, Iz/4, J/4).
  - **2ª escalera (2º hueco este)**: borde N en y=7.92, x 18.545..20.794, muro en X **e=0.30 m (ASSUMED_FOR_MODEL)**; nodos ROOF 258/259. **El x=20.794 del nodo 259 se CONSERVA** (borde norte real del 2º hueco en planta); NO se aproxima a las columnas interiores x≈20.550 del plano.
- Idealizacion: misma convencion academica que los muros LT2 (_make_lt2_wall): un `elasticBeamColumn` por esquina, transf 10001, material LT2 (E/G del modulo).
- Nodos nuevos: 50 (tags 700001.., B1..L4, uno por esquina y nivel).
- Elementos nuevos: 50 (tags 70001.., verticales por tramo de nivel, B1..ROOF).
- Bases B1 nuevas empotradas: 10 (ops.fix 6 GDL, misma convencion de cimentacion que los apoyos existentes; documentado, no es restriccion artificial).
- Nodos intermedios (B1..L4) creados SIN agregar al rigidDiaphragm (no son necesarios para cerrar el mecanismo y no se introducen restricciones artificiales).
- Topes en ROOF coinciden exactamente con los nodos reales del anillo (226/227, 244/245/246/247, 256/257, 258/259).
### Chequeos estructurales
- Nodos estructurales sin conectividad: 0 
- Nodos sin camino de rigidez a apoyos: 17 (BFS por elementos)
  - L1: 1 -> [1001] 
  - L2: 7 -> [1002, 600100, 600101, 600102, 600103, 600104, 600105] 
  - L3: 7 -> [1003, 600200, 600201, 600202, 600203, 600204, 600205] 
  - L4: 1 -> [1004] 
  - ROOF: 1 -> [1005] 
- Interpretacion: los masters (1001-1005) y los nodos de muro LT1 (6001xx/6002xx) estan unidos por restricciones cinematicas (rigidDiaphragm / rigidLink 'beam'), no por elementos, por lo que no son mecanismos. El anillo VI de ROOF (226/227, 244-247, 256/257, 258/259) ya NO es la causa: el sistema vertical de cajas/pilastra materializado en COMBINADO (seccion 11) conecta esos nodos a las bases B1 (empotradas).
- Elementos con longitud cero: 0 
- Nodos esclavos en mas de un diafragma: 0 (cada nodo ocular una sola vez; muros LT1 por rigidLink).

## 10. Conectores V40 -> M001/M003 (excentricidad e/2=0.300 m)

- Los extremos de las cadenas V40x80 (x=0.400) terminan sobre la cara ESTE de los muros M001/M003 (x=0.100 + e/2 = 0.400, e=0.600). Se modela la excentricidad con UN elemento `elasticBeamColumn` horizontal en X por extremo (10 en total), entre el nodo de cadena y el nodo del EJE del muro al mismo Y y Z. No se mueven nodos de muro; no se usa equalDOF; los conectores son elementos (no restricciones cinematica) y sus nodos son esclavos normales del rigidDiaphragm de su nivel (no redundancia).
- Nodos intermedios de cadena (y=4.265/8.9/11.885, sin apoyo fisico en muro) y vigas V30/VI cercanas: NO conectados.
- **Seccion de enlace (solo del COMBINADO, no altera LT1/LT2):** E = 2.35e9 kPa (= 100 x E_LT2), nu = 0.20, A = 1.00 m², Iy = Iz = 0.10 m⁴, J = 0.20 m⁴. Rigidez axial EA = 2.35e9 kN (>= ~110x la del muro media seccion y >= ~300x la de la V40); suficientemente rigida para transferir el corte/axial del enlace sin alterar las rigideces originales.

| NIVEL | NODO CADENA | XYZ CADENA | NODO MURO | XYZ MURO | LONGITUD | TAG CONECTOR |
|---|---|---|---|---|---|---|
| L1 | 29 | (0.400,1.825,-4.010) | 25 | (0.100,1.825,-4.010) | 0.300 | 9001 |
| L1 | 33 | (0.400,14.325,-4.010) | 26 | (0.100,14.325,-4.010) | 0.300 | 9002 |
| L2 | 77 | (0.400,1.825,-0.050) | 73 | (0.100,1.825,-0.050) | 0.300 | 9003 |
| L2 | 81 | (0.400,14.325,-0.050) | 74 | (0.100,14.325,-0.050) | 0.300 | 9004 |
| L3 | 125 | (0.400,1.825,3.910) | 121 | (0.100,1.825,3.910) | 0.300 | 9005 |
| L3 | 129 | (0.400,14.325,3.910) | 122 | (0.100,14.325,3.910) | 0.300 | 9006 |
| L4 | 173 | (0.400,1.825,7.870) | 169 | (0.100,1.825,7.870) | 0.300 | 9007 |
| L4 | 177 | (0.400,14.325,7.870) | 170 | (0.100,14.325,7.870) | 0.300 | 9008 |
| ROOF | 221 | (0.400,1.825,11.830) | 217 | (0.100,1.825,11.830) | 0.300 | 9009 |
| ROOF | 225 | (0.400,14.325,11.830) | 218 | (0.100,14.325,11.830) | 0.300 | 9010 |
- Copia maquina: `conectores_v40_muro.csv`.

## Archivos generados
- `outputs\interfaz_traceabilidad.csv`
- `outputs\auditoria_elementos_interfaz.csv`
- `outputs\vista_3d_combinado.png`
- `outputs\reporte_validacion_combinado.md`
- `outputs\verticales_cajas_pilastra.csv`
- `outputs\conectores_v40_muro.csv`

