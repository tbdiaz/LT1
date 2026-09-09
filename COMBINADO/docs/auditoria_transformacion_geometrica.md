# Auditoría de transformación geométrica — LT1 + LT2
**Modelo combinado `COMBINADO/` · ETAPA DE ESTUDIO GEOMÉTRICO — NO se construyó todavía el modelo FE.**
Fuentes (solo lectura): `../data/geometria.py` (LT1) y `../LT2/data/geometry/*.csv` (LT2).

## 1. Disposición acordada
- **LT2 a la izquierda (oeste), LT1 a la derecha (este).** Unión lateral.
- Interfaz = borde **este de LT2** (eje D, planos 2024_22-101/102) y borde **oeste de LT1** (eje E, planos 2017_67-101/102/103).
- Ejes transversales comunes (confirmados por inspección visual): LT2 eje 1 ↔ LT1 eje 1 · LT2 eje 2 ↔ LT1 eje 2 · LT2 eje 3 ↔ LT1 eje 3.
- **No** se asume 1' ↔ 1'' ni correspondencia de 2a.
- Cotas Z coincidentes entre ambos modelos (ver sección 5).

## 2. Datos de origen
| Parámetro | LT1 | LT2 |
|---|---|---|
| Ejes X | E=0.0, Eb=3.6, Ec=6.4, F=10.0, G=20.0, Ga=21.45, H=30.0, H1=33.825, H2=38.825, I=40.0, I'=42.5 | A'=0.000, A=3.750, B=11.250, C=21.250, C'=28.830, D=31.250, D'=31.475 |
| Ejes Y | 1=0.0, 1''=-3.9, 2=-8.9, 2a=-13.845, 3=-16.15 | 1=0.000, 1A=4.265, 2=8.900, 2A=11.885, 3=16.150 |
| Niveles Z | FUNDACION_SUP=-7.97, PISO_1S=-4.01, PISO_1=-0.05, PISO_2=3.91, PISO_3=7.87, PISO_4=11.83, CUBIERTA_SUP=12.58 | B1=-7.97, L1=-4.01, L2=-0.05, L3=3.91, L4=7.87, ROOF=11.83 |

### Tags de nodos
- **LT1** (formula `tag = i_n*10000 + i_x*100 + i_y + 1`, `src/modelo_lt1.py`): eje E → `i_x=0`; ejes Y 1/2/3 → `i_y=0/2/4`; niveles FUNDACION_SUP..PISO_4 → `i_n=0..5`.
- **LT2** (orden `(z, x, y)`, `LT2/src/build_opensees_model.py`): nodos estructurales `1..272`.

## 3. Transformación propuesta
Se mantiene LT2 en sus coordenadas nativas y se transforma LT1:
```
X' = X + 31.250      (traslación en X: borde oeste de LT1, eje E=0, → interfaz X=31.250)
Y' = -Y              (reflexión: LT1 eje 2 (−8.900) → +8.900 = LT2 eje 2; eje 3 (−16.150) → +16.150 = LT2 eje 3)
Z' = Z              (datum idéntico, sin cambio)
```
**No se requiere rotación**: ambas edificaciones comparten la dirección de X (borde de interfaz vertical) y la reflexión en Y no actúa sobre X.

**Coordenada global de la interfaz propuesta: X = 31.250 m**
La línea de grilla `D' = 31.475` de LT2 **no** tiene nodos estructurales (no interviene en la interfaz).
Si en el plano de sitio se confirmara una junta de ancho `t` en la interfaz, bastaría con desplazar LT1 a `X' = X + 31.250 + t`.

## 4. Comprobación de coincidencia de ejes
| Correspondencia | LT2 (nativo) | LT1 → transformado | ¿Coinciden? |
|---|---|---|---|
| eje 1 | Y=+0.000 | Y'=-0.000 | SÍ |
| eje 2 | Y=+8.900 | Y'=+8.900 | SÍ |
| eje 3 | Y=+16.150 | Y'=+16.150 | SÍ |
| eje 1A ↔ eje 1'' | Y=+4.265 | Y'=+3.900 | NO (no se asume) |
| eje 2A ↔ eje 2a | Y=+11.885 | Y'=+13.845 | NO (no se asume) |

## 5. Cotas Z
| LT1 | LT2 | Z (m) |
|---|---|---|
| FUNDACION_SUP | B1 | -7.97 |
| PISO_1S | L1 | -4.01 |
| PISO_1 | L2 | -0.05 |
| PISO_2 | L3 | +3.91 |
| PISO_3 | L4 | +7.87 |
| PISO_4 | ROOF | +11.83 |

## 6. Nodos que llegan a la interfaz — LT2 (borde este, X=31.250)
- Nivel Z=-7.97: nodos [18, 19, 20, 21, 22] (X=31.250 · Y=0.0, 3.18, 6.275, 8.9, 16.15)
- Nivel Z=-4.01: nodos [66, 67, 68, 69, 70] (X=31.250 · Y=0.0, 3.18, 6.275, 8.9, 16.15)
- Nivel Z=-0.05: nodos [114, 115, 116, 117, 118] (X=31.250 · Y=0.0, 3.18, 6.275, 8.9, 16.15)
- Nivel Z=+3.91: nodos [162, 163, 164, 165, 166] (X=31.250 · Y=0.0, 3.18, 6.275, 8.9, 16.15)
- Nivel Z=+7.87: nodos [210, 211, 212, 213, 214] (X=31.250 · Y=0.0, 3.18, 6.275, 8.9, 16.15)
- Nivel Z=+11.83: nodos [268, 269, 270, 271, 272] (X=31.250 · Y=0.0, 3.18, 6.275, 8.9, 16.15)

## 7. Nodos que llegan a la interfaz — LT1 (borde oeste, eje E, X=0 → X'=31.250)
- FUNDACION_SUP (Z=-7.97): nodos [1, 3, 5] · Y nativo=+0.000, -8.900, -16.150 → transformados (X=31.250 · Y'=-0.000,+8.900,+16.150): (31.250, +0.000, -7.97) · (31.250, +8.900, -7.97) · (31.250, +16.150, -7.97)
- PISO_1S (Z=-4.01): nodos [10001, 10003, 10005] · Y nativo=+0.000, -8.900, -16.150 → transformados (X=31.250 · Y'=-0.000,+8.900,+16.150): (31.250, +0.000, -4.01) · (31.250, +8.900, -4.01) · (31.250, +16.150, -4.01)
- PISO_1 (Z=-0.05): nodos [20001, 20003, 20005] · Y nativo=+0.000, -8.900, -16.150 → transformados (X=31.250 · Y'=-0.000,+8.900,+16.150): (31.250, +0.000, -0.05) · (31.250, +8.900, -0.05) · (31.250, +16.150, -0.05)
- PISO_2 (Z=+3.91): nodos [30001, 30003, 30005] · Y nativo=+0.000, -8.900, -16.150 → transformados (X=31.250 · Y'=-0.000,+8.900,+16.150): (31.250, +0.000, +3.91) · (31.250, +8.900, +3.91) · (31.250, +16.150, +3.91)
- PISO_3 (Z=+7.87): nodos [40001, 40003, 40005] · Y nativo=+0.000, -8.900, -16.150 → transformados (X=31.250 · Y'=-0.000,+8.900,+16.150): (31.250, +0.000, +7.87) · (31.250, +8.900, +7.87) · (31.250, +16.150, +7.87)
- PISO_4 (Z=+11.83): nodos [50001, 50003, 50005] · Y nativo=+0.000, -8.900, -16.150 → transformados (X=31.250 · Y'=-0.000,+8.900,+16.150): (31.250, +0.000, +11.83) · (31.250, +8.900, +11.83) · (31.250, +16.150, +11.83)

## 8. Tabla NIVEL | EJE | NODO LT2 | XYZ LT2 | NODO LT1 | XYZ LT1 TRANSFORMADO | DISTANCIA
| NIVEL | EJE | NODO LT2 | XYZ LT2 (m) | NODO LT1 | XYZ LT1 TRANSFORMADO (m) | DISTANCIA (m) |
|---|---|---|---|---|---|---|
| FUNDACION_SUP / B1 | 1 | 18 | (31.250, +0.000, -7.97) | 1 | (31.250, -0.000, -7.97) | 0.000000 |
| FUNDACION_SUP / B1 | 2 | 21 | (31.250, +8.900, -7.97) | 3 | (31.250, +8.900, -7.97) | 0.000000 |
| FUNDACION_SUP / B1 | 3 | 22 | (31.250, +16.150, -7.97) | 5 | (31.250, +16.150, -7.97) | 0.000000 |
| PISO_1S / L1 | 1 | 66 | (31.250, +0.000, -4.01) | 10001 | (31.250, -0.000, -4.01) | 0.000000 |
| PISO_1S / L1 | 2 | 69 | (31.250, +8.900, -4.01) | 10003 | (31.250, +8.900, -4.01) | 0.000000 |
| PISO_1S / L1 | 3 | 70 | (31.250, +16.150, -4.01) | 10005 | (31.250, +16.150, -4.01) | 0.000000 |
| PISO_1 / L2 | 1 | 114 | (31.250, +0.000, -0.05) | 20001 | (31.250, -0.000, -0.05) | 0.000000 |
| PISO_1 / L2 | 2 | 117 | (31.250, +8.900, -0.05) | 20003 | (31.250, +8.900, -0.05) | 0.000000 |
| PISO_1 / L2 | 3 | 118 | (31.250, +16.150, -0.05) | 20005 | (31.250, +16.150, -0.05) | 0.000000 |
| PISO_2 / L3 | 1 | 162 | (31.250, +0.000, +3.91) | 30001 | (31.250, -0.000, +3.91) | 0.000000 |
| PISO_2 / L3 | 2 | 165 | (31.250, +8.900, +3.91) | 30003 | (31.250, +8.900, +3.91) | 0.000000 |
| PISO_2 / L3 | 3 | 166 | (31.250, +16.150, +3.91) | 30005 | (31.250, +16.150, +3.91) | 0.000000 |
| PISO_3 / L4 | 1 | 210 | (31.250, +0.000, +7.87) | 40001 | (31.250, -0.000, +7.87) | 0.000000 |
| PISO_3 / L4 | 2 | 213 | (31.250, +8.900, +7.87) | 40003 | (31.250, +8.900, +7.87) | 0.000000 |
| PISO_3 / L4 | 3 | 214 | (31.250, +16.150, +7.87) | 40005 | (31.250, +16.150, +7.87) | 0.000000 |
| PISO_4 / ROOF | 1 | 268 | (31.250, +0.000, +11.83) | 50001 | (31.250, -0.000, +11.83) | 0.000000 |
| PISO_4 / ROOF | 2 | 271 | (31.250, +8.900, +11.83) | 50003 | (31.250, +8.900, +11.83) | 0.000000 |
| PISO_4 / ROOF | 3 | 272 | (31.250, +16.150, +11.83) | 50005 | (31.250, +16.150, +11.83) | 0.000000 |

### Nodos LT2 en la interfaz SIN contraparte en LT1 (núcleo derecho)
- FUNDACION_SUP/B1: nodo 19 (31.25,3.18,-7.97) NÚCLEO_LT2
- FUNDACION_SUP/B1: nodo 20 (31.25,6.275,-7.97) NÚCLEO_LT2
- PISO_1S/L1: nodo 67 (31.25,3.18,-4.01) NÚCLEO_LT2
- PISO_1S/L1: nodo 68 (31.25,6.275,-4.01) NÚCLEO_LT2
- PISO_1/L2: nodo 115 (31.25,3.18,-0.05) NÚCLEO_LT2
- PISO_1/L2: nodo 116 (31.25,6.275,-0.05) NÚCLEO_LT2
- PISO_2/L3: nodo 163 (31.25,3.18,3.91) NÚCLEO_LT2
- PISO_2/L3: nodo 164 (31.25,6.275,3.91) NÚCLEO_LT2
- PISO_3/L4: nodo 211 (31.25,3.18,7.87) NÚCLEO_LT2
- PISO_3/L4: nodo 212 (31.25,6.275,7.87) NÚCLEO_LT2
- PISO_4/ROOF: nodo 269 (31.25,3.18,11.83) NÚCLEO_LT2
- PISO_4/ROOF: nodo 270 (31.25,6.275,11.83) NÚCLEO_LT2

## 9. Conclusiones
- Coincidencias **exactas** (Δ ≤ 1e-3 m) en los ejes 1, 2 y 3: **18/18** pares por nivel (6·3).  En todos la distancia es **0.000 m**: la línea de columnas LT1 (eje E) cae exactamente sobre la línea de columnas LT2 (eje D) en los ejes transversales comunes.
- Sin contraparte: 12 nodos de LT2 del núcleo derecho (Y=3.18 y 6.275) en los 6 niveles.
- No coinciden (y no se fusionan): eje 1A de LT2 vs 1'' de LT1 (ΔY=0.365 m) y eje 2A de LT2 vs 2a de LT1 (ΔY=1.960 m).
- Rangos globales de nodos modelados → X: LT2 [0.100, 31.250] · LT1 [31.250, 73.750]; Y: LT2 [-1.095, 17.240] · LT1 [-0.000, 16.150]; Z común [-7.97, 11.83].

## 10. Fuera de alcance de esta etapa
- No se conectaron nodos (sin equalDOF ni rigidLink de interfaz).
- No se alteraron diafragmas, apoyos ni cargas de LT1/LT2.
- No se resolvió la singularidad del análisis de gravedad de LT2.
- No se construyó el modelo FE combinado.
