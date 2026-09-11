# SEMANA 3 — Carga viva, sismo, superposición y capacidad RC

Modelo estructural del Edificio de Ingeniería (laboratorio digital, OpenSeesPy).
Bruto: `COMBINADO` (LT1 + LT2 combinados), casos base lineales de la Semana 2.
Unidades base: **m, kN, kPa**.

Este documento consolida la Semana 3 en 10 secciones: caso base, carga viva (A),
sismo pseudoestático (B), superposición (C), M-φ de columna (D.1), P-M de columna
(D.1), P-M de muro (D.2), verificación independiente RC, demanda–capacidad (D.3)
y uso de IA.

---

## 1. Caso base reutilizado

- Modelo combinado LT1+LT2 construido por `COMBINADO/src/run_combined.py`
  (`CombinedBuilder`), lineal elástico 3D, 6 GDL por nodo, diafragmas rígidos,
  muros como elementos lineales equivalentes (convención del curso).
- Casos de carga lineales independientes ya existentes (Semana 2):
  **G** (gravedad, patrones 1/2), y reutilizados en la Semana 3 tal cual:
  **Q** (carga viva, patrones 3/4), **EX** (sismo X, patrón 5), **EY** (sismo Y,
  patrón 6).
- Se mantiene la separación dato–lógica: geometría en
  `outputs/unity/modelo_lt1.json` y áreas tributarias de la Semana 2; la Parte A
  solo reparte cargas sobre esa geometría sin recalcular polígonos.

---

## 2. Parte A — Carga viva Q

Script: `COMBINADO/src/semana03_live_load.py`.

- **q_Q = 4.0 kPa = 4.0 kN/m² uniforme** en las superficies transitables de LT1 y
  LT2 (CIERRE DE PARTE A).
- Criterio (NCh1537.Of2009, Tabla 4): edificación **educacional**; salas de
  clases 3.0 kPa, pasillos 4.0 kPa. Al no existir planos arquitectónicos que
  zonifiquen los usos, se adopta **4.0 kPa uniforme** como **hipótesis
  conservadora de modelación** (no se afirma que NCh1537 exija 4.0 kPa en todas
  las superficies).
- Se mantiene **exacta** la geometría tributaria de la Semana 2; cada franja
  cierra a `area_franja * q_Q`.
- **Conservación** `sum(Q_transferida) == q_Q * A_tributaria` (err_rel ≈ 1e-11,
  PASS en todos los pisos y en el total).

| origen | área (m²) | Q_teórica (kN) | Q_transferida (kN) | err_rel | PASS |
|---|---|---|---|---|---|
| LT2 L1..L4 | 463.18 c/u | 1852.73 c/u | 1852.73 c/u | 2.3e-11 | PASS |
| LT1 PISO_1..4 | 686.38 c/u | 2745.50 c/u | 2745.50 c/u | ≤1.7e-16 | PASS |
| COMBINADO TOTAL | 4598.23 | 18392.91 | 18392.91 | 9.3e-12 | PASS |

- Análisis OpenSees (patrones 3=LT2-Q, 4=LT1-Q): `analyze` rc=0; `sum Rz =
  Q_total = 18392.91 kN` (err_abs 1.1e-8 kN); `sum|Rx| ≈ 3.7e-10 kN`,
  `sum|Ry| ≈ 9.6e-11 kN` (equilibrio global).

---

## 3. Parte B — Sismo pseudoestático (EX y EY)

Script: `COMBINADO/src/semana03_seismic.py`. Propiedades **PROVISIONALES**
(INPUT_REQUIRED, las definirá el profesor):

- coeficiente sísmico = **0.20** (referencia: ejemplo del enunciado "20% de g").
- fracción de carga viva en masa = **0.50** (enunciado).
- patrón lateral **uniforme**: `F_i = coef * W_i`, aplicado en el master node de
  cada piso (masters 1001..1004; ROOF master 1005 **sin masa** → W=0, sin F).

Peso sísmico por piso (`W_i = G_i + 0.5·Q_i`):

| piso | master | G_i (kN) | 0.5·Q_i (kN) | W_i (kN) | F_i = 0.20·W_i (kN) |
|---|---|---|---|---|---|
| L1 | 1001 | 8000.91 | 2299.11 | 10300.03 | 2060.01 |
| L2 | 1002 | 7915.59 | 2299.11 | 10214.71 | 2042.94 |
| L3 | 1003 | 7810.86 | 2299.11 | 10109.97 | 2022.00 |
| L4 | 1004 | 7996.55 | 2299.11 | 10295.66 | 2059.13 |
| ROOF | 1005 | 0 | 0 | 0 | 0 |
| **suma** | | 31723.92 | 9196.46 | 40920.37 | **8184.07** |

- Corte basal: `|sum R - F_total| / F_total` = 2.3e-12 (EX) y 2.9e-13 (EY),
  `analyze` rc=0. PASS ambos.
- Deformada master ROOF: EX desplaza +X (UX=0.0116 m); EY desplaza +Y
  (UY=0.00871 m). **Torsión apreciable** (máx |RZ| ≈ 1.2e-5 rad EX, 1.4e-4 rad EY),
  coherente con la excentricidad del sistema de muros.
- EX y EY son casos independientes (modelo propio cada uno); no se aplicaron
  G ni Q; patrones 1/2 de la Parte A no se tocaron.

---

## 4. Parte C — Superposición verificada en 3 combinaciones

Scripts: `semana03_superposition.py` (casos base por separado) y
`semana03_superposicion_3comb.py` (comparación de 3 combinaciones).

Para cada combinación `R = Σ λ_i·R_i` se comparan **dos** formas de obtenerla:

1. **Superposición**: respuestas de cada caso base corrido por separado
   (`superposition_cases.csv`), combinadas con los coeficientes λ.
2. **Corrida explícita**: un modelo con los patrones de la combinación
   aplicados simultáneamente.

Criterio de verificación (idéntico al mínimo del enunciado): desplazamiento del
master 1005 (ROOF), reacción del primer apoyo fijo y fuerza interna de la
columna LT2 3001. Tolerancia relativa 1e-6.

| combinación | cantidad | err_rel | PASS |
|---|---|---|---|
| C1 = 1.0G + 1.0Q | master ROOF 6 GDL | 9.8e-7 | PASS |
| C1 | reacción apoyo 6 GDL | 3.9e-8 | PASS |
| C1 | columna 3001 (12 GDL) | 3.7e-10 | PASS |
| C2 = 1.0G + 1.0EX | master ROOF 6 GDL | 1.0e-7 | PASS |
| C2 | reacción apoyo 6 GDL | 1.6e-9 | PASS |
| C2 | columna 3001 (12 GDL) | 4.3e-10 | PASS |
| C3 = 1.0G + 1.0Q + 1.0EX | master ROOF 6 GDL | 1.3e-7 | PASS |
| C3 | reacción apoyo 6 GDL | 2.0e-9 | PASS |
| C3 | columna 3001 (12 GDL) | 2.7e-10 | PASS |

- Los errores `err_abs` de orden 1e-6–1e-7 en reacciones provienen de que la
  superposición usa los vectores de caso **publicados redondeados** (a 6/9
  decimales) en `superposition_cases.csv`, mientras las corridas explícitas son
  de precisión completa; quedan ~3 órdenes por debajo de la tolerancia 1e-6.
- **Demostración del principio de superposición** para el sistema lineal: la
  igualdad (1)≈(2) en las 9 verificaciones confirma que la respuesta combinada
  es la suma lineal de los efectos de cada caso base (base para el Sidequest 2
  "Load Combination Explorer": cambiar λ sin reanalizar).

---

## 5. Parte D.1 — Curva momento–curvatura de columna

Script: `COMBINADO/src/semana03_capacity.py`. Sección usada: **LT1 tag 111000**
(las 90 columnas LT1 comparten sección y armadura).

Datos **reales** (planos): sección **70×70 cm** (`P. 70x70`), **16 Φ22**
(As = 6.082e-3 m², ρ = 0.0124), fuente `outputs/reinforcement/armadura_lt1_columnas.csv`
(estatus EXACT / USER_CONFIRMED_DRAWING_DATA).

Supuestos de modelación (los planos no los documentan; marcados **SUPUESTO**):

| concepto | valor |
|---|---|
| f'c | 30 MPa (30000 kPa) |
| fy | 420 MPa (420000 kPa) |
| Es / endurecimiento | 200 GPa, b = 0.01 |
| distancia cara → **eje** de barras | 0.04 m |
| distribución 16 Φ22 | 4 esquinas + 3 por cara, simétrica |
| hormigón | Concrete01 no confinado (fpc −30000, epsc0 −0.002, fpcu −6000, epsscu −0.006) |
| discretización | patrón de fibras 32×32 (0.70×0.70 m) |

Método: fiber section + `zeroLengthSection` (esquema canónico OpenSees
"Moment-Curvature"), carga axial constante + momento unitario y
`DisplacementControl` sobre la rotación; el factor de carga es el momento.

| P (kN) | κ_pico (rad/m) | M_pico (kN·m) |
|---|---|---|
| 0 | 0.0680 | 900.85 |
| −2500 | 0.0140 | 1390.62 |
| −5000 | 0.0080 | **1657.51** |
| −7500 | 0.0064 | 1610.63 |
| −10000 | 0.0044 | 1385.26 |

Máximo M = 1657.51 kN·m a P ≈ −5000 kN (zona balanceada); la capacidad en
flexión sube con la compresión axial hasta ese punto y baja hacia la compresión
pura. Curvas en `moment_curvature.csv`. Sensibilidad de la discretización en la
sección 8.

---

## 6. Parte D.1 — Curva de interacción P-M de columna

Mismos supuestos de la sección 5. Envolvente de la rama ascendente de cada
M-φ (un punto de carga axial por rama):

| punto | P (kN) | M (kN·m) |
|---|---|---|
| flexión pura | 0.00 | 900.85 |
| intermedio | −2500.00 | 1390.62 |
| intermedio | −5000.00 | 1657.51 |
| intermedio | −7500.00 | 1610.63 |
| intermedio | −10000.00 | 1385.26 |
| compresión pura P0 | **−17132.85** | 0.00 |

P0 (fibras) = −17132.85 kN con |M|máx = 2.2e-13 kN·m. La referencia de diseño
del curso `0.85·f'c·(Ag−As) + fy·As` = 14894.40 kN difiere +15% porque las
fibras usan la tensión real del material (sin el factor 0.85 del código) —
ver sección 8. Todo M>0 ocurre solo bajo compresión axial (la sección no
resiste tracción neta). Archivos: `pm_interaction.csv/.png`, `fiber_section.png`.

---

## 7. Parte D.2 — Curva de interacción P-M de muro LT1

Script: `COMBINADO/src/semana03_wall_pm.py`. Muro representativo: **tag 400001
(NSUP_01)**, e = 0.20 m × L = 3.650 m del núcleo PISO_2 (fuente
`outputs/control_muros_equivalentes_lt1.txt`). Flexión **en el plano** (eje
fuerte).

**IMPORTANTE**: los planos de elevación LT1 (`2017_67-300..303`) no permiten
leer la armadura real (barras dibujadas sin texto; estatus
NEEDS_DRAWING_VALUE_CONFIRMATION en `armadura_lt1_muros.csv`). Esta curva es
**PROVISIONAL**:

| concepto | valor | carácter |
|---|---|---|
| f'c | 30 MPa | **SUPUESTO** |
| fy | 420 MPa | **SUPUESTO** |
| Es / b | 200 GPa, b = 0.01 | **SUPUESTO** |
| cuantía vertical ρ_v | 0.0025 de e·L (2 cortinas Φ12, As = 1.810e-3 m²) | **SUPUESTO** |
| barra de cortina | Φ12 a 0.04 m cara→eje, simétrica al plano medio | **SUPUESTO** |
| hormigón | Concrete01 no confinado | **SUPUESTO** |

Método: idéntico al esquema M-φ de la Parte D.1, con la sección del muro
discretizada en fibras rectangulares (L×e, malla 40×8) y las cortinas de
armadura colocadas simétricas al plano medio (z = ±0.06 m); un punto (P, M)
por rama axial + compresión pura mediante empuje axial.

| punto | P (kN) | M (kN·m) |
|---|---|---|
| flexión pura | 0.00 | 1664.17 |
| intermedio | −2000.00 | 4405.01 |
| intermedio | −4000.00 | 6717.97 |
| intermedio | −6000.00 | 8360.49 |
| compresión pura P0 | **−22623.82** | 0.00 |

Archivos: `wall_section.png`, `wall_moment_curvature.csv/.png`,
`wall_pm_interaction.csv/.png`. Pendiente: reemplazar ρ_v por la armadura
**real** cuando se confirme (pliego/ETOG); solo cambian `bar_positions()` y se
re-ejecuta.

---

## 8. Verificación independiente con contenidos del curso de hormigón armado

Comparación manual de fórmulas del curso contra el resultado de fibras
(solo estado axial-flexural; ver limitaciones en el enunciado).

### 8.1 Columna 70×70 (resistencia axial nominal)

- Datos: Ag = 0.49 m², As = 16·Φ22 = 6.082e-3 m² (ρ = 0.0124), f'c = 30 MPa,
  fy = 420 MPa.
- `P0,ACI = 0.85·f'c·(Ag − As) + fy·As`
  = 0.85·30000·0.483918 + 420000·0.006082 = **14894.4 kN**.
- Fibras: **17132.9 kN** (+15.0%). Diferencia esperada: las fibras integran el
  bloque de tensiones real (Concrete01, pico 30 MPa en εc0 = −0.002) y el acero
  con endurecimiento, sin el factor de eficiencia 0.85 que la norma aplica a
  `0.85·f'c`. La cota ACI queda por debajo (conservadora), como corresponde.

### 8.2 Columna 70×70 (momento a flexión pura, cota de par de acero)

- Cara en tracción ≈ 5 Φ22 (2 esquinas + 3 centrales):
  As,t = 5·3.8013e-4 = 1.901e-3 m² → T = fy·As,t = 798.3 kN.
- Brazo entre acero compresión–tracción: d − d' = 0.70 − 0.04 − 0.04 =
  0.62 m.
- Par simple: M ≈ T·(d − d') = **495.0 kN·m**.
- Fibras (P=0): **900.9 kN·m**. El de fibras es mayor porque además del par de
  las caras, las barras intermedias del alma entran en tracción y el bloque de
  compresión del hormigón participa del equilibrio; la cota simple es un límite
  inferior válido.

### 8.3 Muro 400001 (resistencia axial nominal)

- Datos: Ag = e·L = 0.20·3.65 = 0.73 m², As = 1.810e-3 m² (ρ_v = 0.0025).
- `P0,ACI = 0.85·f'c·(Ag − As) + fy·As`
  = 0.85·30000·0.72819 + 420000·0.00181 = **19329.1 kN**.
- Fibras: **22623.8 kN** (+17.0%), misma explicación que la columna (tensión
  real vs factor 0.85).

Conclusión: los órdenes de magnitud y las tendencias de las curvas de fibras
son consistentes con las fórmulas del curso; las diferencias del 15–17 % en
compresión pura están explicadas por la formulación de material vs el factor de
código, y son del lado seguro.

---

## 9. Parte D.3 — Demanda global sobre capacidad de sección

Script: `COMBINADO/src/semana03_demanda.py`.

- Combinación representativa: **R = 1.0G + 1.0Q + 1.0EX** (EY con λ=0, igual
  que la Parte C), **corrida única** sobre el modelo combinado.
- Columnas: P_d = fuerza axial del `eleForce` local (compresión > 0, nodo
  bajo); M_d = resultante de flexión del extremo demandado. Las 90 columnas LT1
  comparten la curva D.1; se evalúan **75 activas** (15 de la interfaz
  descartadas por regla 3, ver `auditoria_elementos_interfaz.csv`).
- Muros: M_d = componente **en el plano** del muro (mapeo de ejes locales
  verificado empíricamente); capacidad = curva D.2 del muro 400001 **escalada
  por la longitud real de cada muro** (P y M escalan linealmente con L a e y
  ρ_v constantes).

Demanda más alta (columnas, worse-case de las 75):

| elemento | P_d (kN) | M_d (kN·m) | M_cap(P_d) (kN·m) | ratio |
|---|---|---|---|---|
| **110042** | 922.62 | 445.37 | 1081.60 | **0.412** |
| 110040 | 1127.25 | 457.31 | 1121.69 | 0.408 |
| 110041 | 2072.40 | 508.90 | 1306.85 | 0.389 |
| 113052 | 407.96 | 366.62 | 980.77 | 0.374 |
| 113050 | 457.09 | 355.65 | 990.40 | 0.359 |

Muros (en el plano, capacidad escalada por L):

| elemento | L (m) | P_d (kN) | M_d (kN·m) | M_cap (kN·m) | ratio |
|---|---|---|---|---|---|
| 400002 | 2.58 | 0.00 | 47.19 | 1174.50 | 0.040 |
| 400003 | 2.58 | 0.00 | 47.19 | 1174.50 | 0.040 |
| 400006 | 1.70 | 0.00 | 18.78 | 776.01 | 0.024 |
| 400005 | 1.70 | 0.00 | 18.78 | 776.01 | 0.024 |
| 400001 | 3.65 | 0.00 | 0.08 | 1664.17 | 0.000 |
| 400004 | 3.39 | 0.00 | 0.08 | 1545.63 | 0.000 |

**Lectura**: todos los ratios < 1 → las secciones absorben la demanda en esta
primera revisión, que es **lineal elástica (demanda) vs no lineal (capacidad)**,
sin factores φ ni γ, sin P-Δ ni segundo orden. La mayor demanda está en la
base (PISO_1→PISO_2). Las columnas dominan el control (ratio 0.41 en 110042);
los muros no son críticos en su plano (≤0.04). Válido SOLO bajo los supuestos
de la Parte D; la curva del muro es provisional.

Archivos: `demands_columns.csv`, `demands_walls.csv`, `demanda_vs_capacidad.csv`,
`demanda_capacidad.png`, `resumen_demanda.md`.

---

## 10. Uso de IA (OpenCode) y verificación crítica

- Flujo seguido **Issue → Plan → Build → Test → Review → Merge**: cada parte se
  implementó con un script dedicado, un criterio de aceptación verificable y un
  commit por etapa (`17588e3` A, `6e4ab18` A+B, `635b774` C, `5b07f36` D.1,
  esta semana: D.2/D.3 + superposición 3 combinaciones + reporte).
- `AGENTS.md` fija las reglas del proyecto: solo el modelo estructural LT1;
  **no inventar** geometría/materiales/cargas; OpenSeesPy; unidades m/kN/kPa;
  datos separados de lógica; cada etapa verificable antes de avanzar; no
  modificar información existente sin explicar el motivo.
- Decisiones marcadas explícitamente como **SUPUESTOS** donde los planos no
  documentan datos (f'c, fy, recubrimiento, distribución de barras, armadura
  del muro con estatus NEEDS_DRAWING_VALUE_CONFIRMATION). Ninguna se presentó
  como dato real.
- Verificaciones independientes ejecutadas:
  - **Conservación de carga** Q: `sum(Q_transferida) = q·A` (1e-11).
  - **Equilibrio sismo**: corte basal = ΣF con err 1e-12.
  - **Superposición 3 combinaciones** contra corridas explícitas (err ≤1e-6).
  - **Orden de `eleForce`** del `elasticBeamColumn` 3D verificado
    empíricamente con casos de carga unitarios aislados antes de extraer P, M
    en D.3 (evitó confusiones clásicas de índices locales).
  - **Sensibilidad de discretización** M-φ (véase abajo).
- **Sensibilidad de la malla de fibras** (D.4, `semana03_sensibilidad.py`,
  columna 70×70 a P = −5000 kN):

  | grilla | M_pico (kN·m) | err_rel vs 32×32 |
  |---|---|---|
  | 16×16 | 1657.541 | 2.1e-5 |
  | 32×32 | 1657.506 | 0 |
  | 64×64 | 1657.815 | 1.9e-4 |

  Cambio máx < 0.02 % → la discretización de la sección es suficiente; la malla
  32×32 adoptada está convergida.

- Registro de uso crítico de IA: el código generado por los agentes se revisó
  contra el enunciado y los planos; los valores de capacidad que dependen de
  supuestos se entregan **provisionales** y se dejarán pendientes hasta
  confirmar el pliego/E.T.O.G.

---

## Estado pendiente (NO inventar, requiere datos del profesor/planos)

1. **Confirmar q_Q por zonificación** (hoy 4.0 kPa uniforme, hipótesis
   conservadora).
2. **Coeficiente sísmico** (hoy 0.20 provisional).
3. **f'c / fy / recubrimiento / distribución de armadura** de columnas (hoy
   supuestos 30 MPa / 420 MPa / 4 cm).
4. **Armadura real de muros LT1** (hoy ρ_v = 0.0025 supuesto) y re-ejecutar la
   Parte D.2/D.3 con esos valores.