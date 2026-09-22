# Modelo combinado LT1 + LT2 — reporte de validacion

## 1. Transformacion e interfaz (APROBADA)

- LT1: X' = X + 31.250 ; Y' = -Y ; Z' = Z (sin rotacion).
- LT2: coordenadas nativas. Interfaz global en X = 31.250 m.
- Pares de nodos coincidentes: **18/18** (6 niveles x ejes 1/2/3, distancia 0.000 m).
- Un solo nodo fisico por posicion: se conserva el tag nativo LT2. Detalle: `interfaz_traceabilidad.csv`.

## 2. Retagging (sin colisiones)

- LT2: tags nativos (nodos 1..272, masters 1001..1005, vigas 2001+ (237), columnas 3001+ (50), muros 4001+ (80), secciones 5001+, transf 1/2/3).
- LT1: offset +100000 en nodos estructurales y muros; masters LT1 (600001-600004) NO se crean (sustituidos por masters combinados). Elementos con tags nativos (columnas 75, vigas 152, muros 30); transf 10001/10002/10003; timeSeries/pattern 1 (LT2) y 2 (LT1).

## 3. Elementos duplicados en la interfaz

- Duplicados geometricos detectados: **15 columnas LT1** (P70x70, ejes 1/2/3, 5 tramos) coinciden exactamente con columnas LT2 nativas (misma seccion, longitud y orientacion; mismo E 27.8e6 kPa confirmado).
- Decision (regla 3): conservar la **columna LT2 nativa** y descartar las 15 de LT1; la columna compartida queda con el E de LT2. No se pierde rigidez vertical (tramos iguales nivel a nivel).
- Vigas LT1 de borde en E (8) y muros LT2 en el borde: sin par, se conservan. Detalle: `auditoria_elementos_interfaz.csv`.

## 4. Diafragmas (un solo master por nivel)

- L1: master 1001 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- L2: master 1002 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- L3: master 1003 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- L4: master 1004 (LT2 nativo), 63 nodos oculares cada uno una sola vez.
- ROOF: master 1005 (LT2 nativo), 73 nodos oculares cada uno una sola vez.
- Los 24 nodos de muro LT1 se vinculan al master del nivel con ops.rigidLink('beam', master, nodo_muro) (estrategia C de LT1); NO son esclavos del rigidDiaphragm.

## 5. Apoyos

- LT2: 22 fijos (B1, empotrados).
- LT1: 15 fijos (los 3 de interfaz ya fijados como nodos LT2; sin ops.fix duplicado).
- **COMBINADO (cajas/pilastra/2ª escalera): 10 fijos nuevos en B1** (empotrados, misma convencion de fundacion que el resto del modelo; NO son restricciones artificiales: las cajas llegan a la cimentacion en la estructura real).
- Total apoyos fijos: **53** (6 GDL).

## 6. Muros LT2 (40 tramos -> 80 columnas equivalentes)

- Idealizacion: cada tramo vertical usa los **4 nodos reales del CSV** (esquinas de sus dos extremos en planta). Se crea un par de `elasticBeamColumn` (una por esquina) con **media seccion** cada una (transf 10001, vecxz (1,0,0)):
  A = e·L/2 ; muro en X: Iy = e·L^3/24, Iz = L·e^3/24 ; muro en Y: Iy = L·e^3/24, Iz = e·L^3/24 ;
  J = h·b^3/3·(1-0.63·(b/h)+0.052·(b/h)^5) / 2, b=min(e,L), h=max(e,L) (Saint-Venant).
- Los TOTALES por tramo coinciden con el muro academico LT1 (A=e·L, Ix=e·L^3/12, etc.): misma rigidez axial y flexional, sin dejar nodos flotantes en las esquinas (concepto validado contra modelo_lt1.json).
- Material del muro: LT2 (E=2.78e+07 kN/m², G=1.16e+07 kN/m²), su modulo propio.
- Elementos creados: 80 (tags 4001+, dos por tramo: 4001/4002, 4003/4004, ...).

## 7. Materiales (no unificados)

- LT1: E = 2.78e+07 kPa, G = 1.15833e+07 kPa (dato confirmado usuario, E=27800 MPa).
- LT2: E = 2.78e+07 kPa, G = 1.15833e+07 kPa.
- Cada modulo usa E=27800/27800 MPa (unificados); en las columnas compartidas de la interfaz rige el E de LT2 (regla 3).

## 8. Cargas de gravedad

- LT2 (patron 1): 27160 eleLoad -beamPoint sobre 184 vigas, P = 11268.662631 kN (sin cambios).
- LT1 (patron 2): 122 eleLoad -beamUniform (QG), P = **19817.597036 kN**.
  - P_lt1_referencia (JSON, I'=42.5 m) = **19644.141914 kN** (trazabilidad).
  - La correccion I'->45.0 alarga las 12 vigas I-I' de 2.5 m a 5.0 m; al aplicar QG por metro lineal, esas vigas cargan el doble: +173.455 kN. Los qG_kN_m de referencia se conservan (no se inventan cargas).
  - Las **11 vigas de fachada particionadas** por los salientes (tags 200033/060/063/011-14/084/87/90/93) ya NO reciben carga; su QG se redistribuye a los segmentos sustitutos (800201+) conservando la misma densidad qG (el total Σ qG·L se conserva exactamente: 0 perdidas, 0 warnings).
- **P_total = 31086.259667 kN** (P_lt1_modelo + P_lt2).
- Zonas pendientes (ROOF LT2, WALL_EDGE_PENDING) NO se cargan (se preserva el criterio de cada modelo). Nota franja I': el pano P51/P52 (I-I') pasa de 2.5 m a 5.0 m, +40.375 m²/piso; de esa franja extra, las 12 vigas I-I' recogen su parte (+6.25 m²·q por piso) y el resto se conserva con los valores de referencia (no se redistribuye a las vigas Y del eje I/I' para no inventar una nueva reparticion).

## 8bis. Areas tributarias por piso (verificacion)

- Σ A_tributaria (JSON) = A_losa panos = **686.375 m²** por piso (exacto en PISO_1..4).
- Con I' = 45.0 m la losa modelada pasa a **726.75 m²/piso**; las 12 vigas I-I' duplican su tributaria (+6.25 m²/piso) y el resto de la franja (+34.125 m²/piso) conserva los valores de referencia (documentado arriba).
- Salientes: no tienen `panos` en el JSON de referencia (las vigas 800101+ no soportan losa tributaria en ese esquema); se conserva el criterio de la referencia.

## 9. Validaciones

- Nodos fisicos totales: 485 (LT2 272 + LT1 no-interfaz 126 + masters 5 + nodos nuevos cajas/pilastra 50).
- Vigas: LT1 152 | LT2 237 | LT2 pendientes 0
- VI-05 (VI15xVAR) materializada POR SUPUESTO/MODELACION (cota superior de rigidez): b=0.15 m, h=1.20 m, E/G de LT2, nodos 226-227, tag 2235 (tag nativo; 2237 no esta disponible, corresponde a ROOF_VI_07). No es una seccion real confirmada; h_min y ley de variacion siguen desconocidas (ver COMBINADO/docs/diagnostico_vi15xvar.md).
- Columnas: LT1 75 | LT2 50
- Muros: LT1 30 | LT2 80
- Conectores V40->Muro (excent. 0.300 m): 10
- Duplicados descartados: 15 columnas LT1.
- Nodos compartidos de interfaz: 18.
- Apoyos fijos: 53. Diafragmas: 5.

### Analisis
- analyze() rc = **0** (OK, convergio)
- ΣRz = 31086.259667 kN
- |ΣRz - P_total| = 1.084845e-08 kN (rel 3.490e-13)
- Σ|Rx| = 8.206119e-11 kN, Σ|Ry| = 7.566191e-10 kN (equilibrio horizontal)
- Max |U| = 0.008164673 m en nodo 178
- Max |Uz| = 0.008163896 m en nodo 178

## 10. Sistema vertical de cajas de escalera y pilastra (COMBINADO, B1->ROOF)

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
- Nodos sin camino de rigidez a apoyos: 5 (BFS por elementos)
  - L1: 1 -> [1001]
  - L2: 1 -> [1002]
  - L3: 1 -> [1003]
  - L4: 1 -> [1004]
  - ROOF: 1 -> [1005]
- Interpretacion: los masters (1001-1005) y los nodos de muro LT1 (6000xx-6004xx) estan unidos por restricciones cinematicas (rigidDiaphragm / rigidLink 'beam'), no por elementos, por lo que no son mecanismos. El anillo VI de ROOF (226/227, 244-247, 256/257, 258/259) ya NO es la causa: el sistema vertical de cajas/pilastra materializado en COMBINADO (seccion 11) conecta esos nodos a las bases B1 (empotradas).
- Elementos con longitud cero: 0
- Nodos esclavos en mas de un diafragma: 0 (cada nodo ocular una sola vez; muros LT1 por rigidLink).

## 11. Conectores V40 -> M001/M003 (excentricidad e/2=0.300 m)

- Los extremos de las cadenas V40x80 (x=0.400) terminan sobre la cara ESTE de los muros M001/M003 (x=0.100 + e/2 = 0.400, e=0.600). Se modela la excentricidad con UN elemento `elasticBeamColumn` horizontal en X por extremo (10 en total), entre el nodo de cadena y el nodo del EJE del muro al mismo Y y Z. No se mueven nodos de muro; no se usa equalDOF; los conectores son elementos (no restricciones cinematica) y sus nodos son esclavos normales del rigidDiaphragm de su nivel (no redundancia).
- Nodos intermedios de cadena (y=4.265/8.9/11.885, sin apoyo fisico en muro) y vigas V30/VI cercanas: NO conectados.
- **Seccion de enlace (solo del COMBINADO, no altera LT1/LT2):** E = 2.78e9 kPa (= 100 x E_LT2), nu = 0.20, A = 1.00 m², Iy = Iz = 0.10 m⁴, J = 0.20 m⁴. Rigidez axial EA = 2.78e9 kN (>= ~110x la del muro media seccion y >= ~300x la de la V40); suficientemente rigida para transferir el corte/axial del enlace sin alterar las rigideces originales.

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
### Continuidad V30x80 en el extremo oeste
- 10 tramos de 1.50 m (tags 9011-9020) completan las vigas V30x80 indicadas por el usuario en L1, L2, L3, L4 y ROOF. Cada tramo comparte un extremo con su viga original y el otro con la cadena V40 del mismo piso.
- Geometria: `COMBINADO/data/conexiones_v30_lt2.csv`, contrastada con plantas LT2 2024_22-101/102. La tributacion V30 usa 24 correcciones firmadas que trasladan area/carga desde V40 hacia los tramos nuevos en L1-L4, conservando el total por piso. ROOF no se corrige porque no tiene carga de losa en la fuente.

## 12. Salientes sur LT1 (geometria CAD verificada)

- Nodos nuevos: **32** (tags 800001+)
- Vigas nuevas: **30** (borde sur + flancos, tags 800101+, seccion V.60/80)
- Segmentos de fachada particionados: **14** particiones (tags 800201+)
- Eje I' corregido: X = 42.50 -> 45.00 m (18 nodos desplazados en el eje I').
- Reglas de inclusion: SOLO geometria respaldada por CAD (FILAS_SUR, FLANCOS_X, VERIFICADO_CAD). Se EXCLUYEN: malla artificial, SPAN_INFERIDO, metales sin E (P.M./P.M.I./V.M.), diagonales y vigas sin respaldo.

| Nivel | Nodos | Vigas | Particiones |
|---|---|---|---|
| PISO_1 | 5 | 5 | 2 |
| PISO_2 | 9 | 10 | 3 |
| PISO_3 | 10 | 8 | 5 |
| PISO_4 | 8 | 7 | 4 |

### Diafragmas y conectividad (verificacion)

Los nodos saliente NO son esclavos del rigidDiaphragm (decision de diseno: se evita restriccion artificial; su carga sobre la losa no existe en el esquema tributario de referencia). Su camino de rigidez al diafragma se cierra POR VIGAS: cada nodo saliente -> viga saliente -> segmento de fachada -> nodo de fachada (slave del diafragma).

| Nivel LT1 | Nivel LT2 | Master | Nodos saliente | Max saltos de viga al diafragma |
|---|---|---|---|---|
| PISO_1 | L2 | 1002 | 5 | 2 |
| PISO_2 | L3 | 1003 | 9 | 2 |
| PISO_3 | L4 | 1004 | 10 | 2 |
| PISO_4 | ROOF | 1005 | 8 | 2 |

- Verificacion: 0 nodos saliente sin ruta de vigas hacia el diafragma (debe ser 0; tambien refrendado por los `Nodos sin camino a apoyos` = 5 preexistentes).
- Nodos sin camino de rigidez a apoyos: 5 (masters 1001..1005 + nodos de muro compartidos, excepciones preexistentes documentadas).

## 13. Elementos pendientes (NO modelados, sin inventar)

Se documenta la existencia, NO se modela (requiere plano/dato explícito si se decide incorporar):

- P.M. / P.M.I. / V.M.: metaleria en fachadas/salientes sin modulo E de referencia (excluidas de la regla VERIFICADO_CAD).
- V.60/VAR y V.60-30/80-40: vigas de seccion variable sin geometria de alma definida en plano.
- Nucleo PISO_4: zona sin plano de detalle en el nivel superior.
- Muros subterraneo (B2 y menores) y zonas sin plano de detalle declarado.
- Zona franja I' extrema (x_lt1 45.0..): losa P51/P52 duplicada en las 12 vigas I-I'; el resto de la franja (34.125 m²/piso) conserva los valores tributarios de referencia (ver seccion 8bis).

## 14. Validacion final (checks automaticos)

- 1. analyze rc = 0: **OK** (rc=0)
- 2. Cargas reparadas (0 warnings ElementalLoad): **OK** (25 segmentos con carga, 0 tags ausentes: [])
- 3. Elementos longitud cero: **OK** (0)
- 4. Vigas LI/II con ΔZ: **OK** (0); saliente con ΔZ: 0; conectores con ΔZ: 0
- 5. Columnas con desplazamiento horizontal: **OK** (0); cajas/pilastra off-vertical: 0
- 6. Diagonales en planta: **OK** (0)
- 7. Nodos saliente sin ruta a apoyos: **OK** (0: [])
- 8. LT2 intacto: **237 vigas** (tags nativos, sin cambios)
- 9. Eje I' en combinado = 45.0+31.25 = 76.25 m: **OK** (18 nodos I')
- 10. Error de equilibrio |ΣRz-P_total|/P_total: **OK** (3.490e-13)
- Resumen nodos: 0 sin conectividad, {'L1': [1001], 'L2': [1002], 'L3': [1003], 'L4': [1004], 'ROOF': [1005]} flotantes preexistentes, P_lt1=19817.597 kN, P_total=31086.260 kN.

## Archivos generados
- `outputs\interfaz_traceabilidad.csv`
- `outputs\auditoria_elementos_interfaz.csv`
- `outputs\vista_3d_combinado.png`
- `outputs\reporte_validacion_combinado.md`
- `outputs\verticales_cajas_pilastra.csv`
- `outputs\conectores_v40_muro.csv`
- `outputs\tributarias_lt1\tributarias_piso_1.png`
- `outputs\tributarias_lt1\tributarias_piso_2.png`
- `outputs\tributarias_lt1\tributarias_piso_3.png`
- `outputs\tributarias_lt1\tributarias_piso_4.png`
- `outputs\vista_3d_interactiva.html` (generado por `scripts/figura_interactiva.py`)

