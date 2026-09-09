# Diagnóstico de la viga VI-05 (VI15xVAR) — rótulo `+V.I. H=MAX 120cm (VIGA 2° ETAPA)`

**Modelo combinado `COMBINADO/` · ETAPA DE ESTUDIO GEOMÉTRICO — NO se materializó VI-05.**
Fuente de evidencia (solo lectura): lámina `LT2\2024_22-102-Model.pdf`, detalle superior-derecho (rótulo, alzado y recuadro CORTE). Este documento **no modifica archivos LT2 originales**.

## 1. Veredicto del rótulo (LÁMINA 102)

- `+V.I. H=MAX 120cm (VIGA 2° ETAPA)` es un **rótulo genérico de familia**: el texto NO contiene el identificador `15/VAR` ni ningún ancho. En la lámina 102 conviven varias V.I. de 2ª ETAPA (15/70, 15/70 ext, 15/76, 15/VAR), y este rótulo del detalle no discrimina cuál de ellas ilustra.
- La identificación `+V.I.15/VAR (2ª ETAPA)` está en el **rótulo de planta de la banda CENTRO** (borde oeste del hueco de escalera, (2133,2476) px), que es el que asocia VI-05 (tramo vertical x≈0.998, y 2.90..7.92) con la sección de altura variable.

## 2. Veredicto del peralte

| Ítem | Estado | Evidencia |
|---|---|---|
| H_MAX = 1.20 m | **RESPALDADO por el plano** (cota escrita en el rótulo del detalle) | `H=MAX 120cm` (lám. 102) |
| Canto dibujado en el alzado = altura máxima | **NO DEMOSTRADO** | El alzado muestra verticales de y522.5 a y648.2 (~125.6 pt ≈ 89 cm @ 1:20), es decir **el canto trazado NO es 1.20 m**; no hay cota que lo ligue a H_MAX. No se usa la escala gráfica para inferir altura. |
| h_min | **NO EXISTE TODAVÍA** | No hay cota ni rótulo que la fije. |
| Ley de variación | **NO EXISTE TODAVÍA** | No hay cota ni rótulo que la defina. |

## 3. Evidencia en el recuadro CORTE (lám. 102, ESCALA 1:20)

- La sección CORTE contiene **P.H.I. 20×20** (ancho 28.3 pt = 20 cm) y un elemento central x2818.1–2835.1 (≈12 cm) con refuerzos `2Φ12 L=190` y `4Φ8 a10 L=80`, lit. "FE SEGUN LOSA".
- Las cotas `14 / 56 / 32 / 16` del recuadro **no están rotuladas como peralte** de la viga y **ninguna coincide con 120 cm**. No constituyen cadena de variación ni definen b/h de VI.
- **No se usa la escala gráfica (1:20) para inventar altura alguna** en esta etapa.

## 4. Estado de VI-05

- **VI-05 continúa como `INPUT_REQUIRED`**: pendiente de h_min, ubicación de h_max/h_min, tipo/ley de variación y longitud del tramo variable.
- No se materializa el elemento (sin b/h en `sections_LT2.csv`; fila `VI15xVAR`; `analysis_status=PENDING_VARIABLE_SECTION`).

## 5. Falta (para resolver VI-05)

| Dato buscado | Fuente a revisar | Estado |
|---|---|---|
| h_min | Lámina 400 y detalles asociados | PENDIENTE |
| Ubicación de h_max | Lámina 400 y detalles asociados | PENDIENTE |
| Ubicación de h_min | Lámina 400 y detalles asociados | PENDIENTE |
| ¿Variación lineal? | Lámina 400 y detalles asociados | PENDIENTE |
| Longitud del tramo variable | Lámina 400 y detalles asociados | PENDIENTE |
| Relación explícita 15/VAR ↔ esas cotas | Lámina 400 y detalles asociados | PENDIENTE |

*El cierre de la tabla requiere revisión de la lámina 400 (sec. 1 y 3) en una etapa separada.*

## 6. Revisión lámina 400 (`2024_22-400-Model.pdf`)

Fuente de evidencia (solo lectura): `C:\Users\natig\OneDrive\Escritorio\2026\P0MCOC\Proyecto 2\2024_22-400-Model.pdf` (no está en LT2; no se modifica). Método: OCR multi-resolución (página completa 467 entradas + teselas a 8×/10× por bandas y recuadros) y geometría vectorial.

### 6.1 La lámina 400 confirma la existencia del rótulo `+V.I.15/VAR (2ª ETAPA)`

- El rótulo aparece **dos veces** en la banda baja (y≈2060–2072 del render): (x1529–1650) y (x1760–1881). Coincide con el rótulo de planta de la banda CENTRO de la lámina 102 (borde oeste del hueco de escalera) que identifica a VI-05.
- El detalle es un **alzado/despiece de refuerzo** de la familia: `2Φ22 L=400/600/900/1000`, `3Φ22 L=900`, `(1°C)(40+36Φ)`/`(710+40)`, `V. 60/80` a ambos extremos, `CF 0.5cm`/`CF 1.0cm`, `405/405g`.

### 6.2 Las marcas 1, 2 y 3 no aportan cotas de peralte

- Existen dígitos aislados `3`@(1245,1953), `2`@(1656,1953) y `1`@(2160,1953) sobre el alzado (origen de la nota previa "sec.1 y 3").
- Corresponden a **posiciones/ejes del alzado** (marcas de corte del refuerzo). **No están acompañadas de ninguna cota vertical**; ningún recuadro de la lámina las liga a una altura.

### 6.3 Las dimensiones de la lámina 400 son longitudinales

- Los números presentes son cotas **de longitud** del alzado, no de peralte: 725 + 890 = 1615 (→ 16.15 m) — se lee el total `1615` a (1697,1991) — más 375 y 750.
- Búsqueda en las 467 entradas del OCR de toda la lámina: **ausencia total** de textos `H=`, `ALT`, `MAX`, `MIN`, `120` y de cotas de peralte.

### 6.4 La lámina 400 no define la sección variable

- **No entrega h_min.** No entrega h_max (el único respaldo de 1.20 m sigue siendo la cota escrita del rótulo `H=MAX 120cm` de la lámina 102). No indica **ubicación** de máximos/mínimos ni **ley de variación**.
- El recuadro central (y1440–1900) es únicamente un relleno rayado sin texto ni cotas.

### 6.5 Veredicto

- La lámina 400 **no permite definir analíticamente la sección variable de VI-05**: el rótulo `+V.I.15/VAR (2ª ETAPA)` confirma su existencia, pero sin h_min, h_max geométrico, ubicaciones ni ley no es posible dimensionar (ni b ni h) la viga.
- **VI-05 permanece `INPUT_REQUIRED` / `PENDING_VARIABLE_SECTION`** (sin b/h en `sections_LT2.csv`, fila `VI15xVAR`; no se materializa) hasta que aparezca evidencia explícita.

## 7. Hallazgo independiente de la lámina 102: `H=MAX 120cm`

- La cota escrita `H=MAX 120cm` de la lámina 102 sigue siendo el **único respaldo numérico de H_MAX = 1.20 m** y constituye un hallazgo independiente de la revisión de la lámina 400.
- Corresponde a la **familia de V.I. de 2ª ETAPA** (`+V.I. H=MAX 120cm (VIGA 2° ETAPA)`): el rótulo es genérico, no contiene el identificador `15/VAR` ni discrimina cuál de las V.I. (15/70, 15/70 ext, 15/76, 15/VAR) ilustra.
- **Por sí solo no permite definir VI-05**: no demuestra que ese H_MAX pertenezca al tramo de altura variable (el canto trazado del alzado ≈ 89 cm @ 1:20 es menor) ni aporta h_min, ubicaciones ni ley de variación.

## 8. Análisis de alternativas de modelación (investigación documental CERRADA)

**Estado confirmado:** VI-05 = `+V.I.15/VAR (2ª ETAPA)`; b = 0.15 m; para la familia V.I. de 2ª etapa existe `H_MAX = 1.20 m`; h_min y ley de variación **desconocidas**. No hay información suficiente para reproducir exactamente la sección variable. No se buscan más fuentes.

Contexto del modelo: material LT2 `CONC_G25` → E = 23.5e6 kPa, G ≈ 9.79e6 kPa (ambos ya `SUPUESTO_MODELO` a nivel de proyecto); vigas `elasticBeamColumn` con sección `Elastic` (A, I, J rectangulares, `_rect_props`/`_jrect`). Con b=0.15 y h=1.20: `EA = 4.23e6 kN`, `EI( eje fuerte ) = 5.08e5 kN·m²`, `GJ ≈ 3.65e4 kN·m²` — ≈4–5× más rígida a flexión que las VI 15x70 (EI≈1.01e5) / 15x76 (EI≈1.29e5).

### 8.1 Alternativa A — prismática b×1.20 (H_MAX), declarada cota superior

| | |
|---|---|
| **Supuesto** | peralte **constante 1.20 m** en todo el tramo; se descarta la variación h(x) |
| **Dato del plano** | b=0.15 (identidad 15/VAR) + H_MAX=1.20 (familia V.I. 2ª etapa, lám. 102) |
| **Desconocido que evita** | h_min y ley: no los necesita |
| **EA / EI / GJ** | sobrestimados (EI ∝ h³ es la cota superior: h(x) ≤ 1.20 en toda la longitud) |
| **Sobrestima/subestima** | más rígida que la real → capta más acción (conservador para VI-05) pero subestima demandas de vecinos y desplazamientos globales |
| **Ventajas** | simple; solo datos del plano; cota superior cerrada y defendible; misma técnica que el resto de VI |
| **Limitaciones** | no reproduce la variación; reparto de fuerzas local sobreestimado para la viga |
| **Veredicto** | **ADOPTADA** (ver §9) |

### 8.2 Alternativa B — sección equivalente por criterio mecánico

- Los criterios habituales (igualar flexibilidad integral `∫dx/I(x)`, o promedio en [h_min, H_MAX]) **requieren h_min y la ley ⇒ no formulables sin inventar h_min**.
- Lo único formulable sin inventar h_min es la cota superior (h*=H_MAX) → **degenera en A**; o un barrido paramétrico h*∈{0.68,…,1.20} que **es análisis de sensibilidad, no sección** (atribuye datos de otras VI a VI-05). 
- **Veredicto:** **NO ADOPTADA** (indefendible como valor único; no se hace el barrido por ahora).

### 8.3 Alternativa C — no materializar

- EA/EI/GJ = 0 en el tramo; camino de carga roto en el hueco de escalera; resultados globales no representativos. Cero supuestos, pero inviable para el objetivo académico de **analizar el modelo**.
- **Veredicto:** **NO ADOPTADA**.

## 9. Decisión adoptada — Alternativa A en el modelo combinado

- **VI-05 se materializa** como `elasticBeamColumn` prismática **b=0.15 m, h=1.20 m** con E y G de LT2 (23.5e6 / 9.79e6 kPa), conectando los nodos reales **226–227**.
- Etiquetada como **`SUPUESTO DE MODELACIÓN / COTA SUPERIOR DE RIGIDEZ`** (NO como sección real confirmada). h_min y ley de variación **siguen siendo desconocidos**; el modelo no los inventa: los declara fuera del alcance de esta representación.
- **Tag:** el tag nativo de `ROOF_VI_05` es **2235** (`TAG_BEAM_BASE + índice CSV 234`; `2001+234=2235`), verificado en `LT2\data\unity\edificio_lt2.json` (node_i=226, node_j=227). **El tag 2237 NO está disponible** (corresponde a `ROOF_VI_07`, VI15x76, viga válida materializada) → se usa **2235**.
- **Únicamente VI-05** usa la sección `VI15xVAR`; no existe otra sección VAR en `sections_LT2.csv` → materializar VI15xVAR materializa solo VI-05.
- **Sin** `fix`, `equalDOF`, `rigidLink` ni restricciones artificiales adicionales para converger.
- Separación plano vs. supuesto:
  - **Del plano:** b=0.15; rótulo `+V.I.15/VAR (2ª ETAPA)`; H_MAX=1.20 (familia); tramo 226–227 (L=5.02 m).
  - **Supuesto de modelación:** peralte único 1.20 m atribuido a VI-05 (declarado en `run_combined.py`, constantes `ASSUMED_SECTIONS`); más los supuestos preexistentes del modelo (E/G, elasticidad lineal).

## 10. Cierre geométrico del mecanismo de ROOF (sistema vertical de cajas y pilastra, B1→ROOF)

Tras materializar VI-05 (§9) el modelo seguía singular (**rc = −3, U(i,i)=0, i=19**): los nodos del anillo VI de ROOF (226/227, 244–247, 256/257, 258/259) formaban vigas sin camino de rigidez vertical a los apoyos. La verificación experimental (anclar SOLO esos 10 nodos → rc=0) confirmó que el mecanismo estaba **concentrado en ROOF** y no en ninguna otra parte del modelo.

Se resolvió materializando la **continuidad vertical B1→ROOF** de las cajas de escalera y la pilastra, **exclusivamente en COMBINADO** (implementación en `run_combined.py`, método `_build_box_verticals`; datos separados de la lógica). No se introdujo ninguna restricción cinemática artificial.

### 10.1 Familias modeladas

| Familia | Sistema | Geometría (fuente: `edificio_lt2.json`) | Espesor | Sección por elemento | Nodos ROOF |
|---|---|---|---|---|---|
| caja_oeste (bajo VI-05) | muro en Y, x=0.998 | y 2.90..7.92 (L_y=5.02 m) | e=0.30 m **ASSUMED_FOR_MODEL** (espesor de caja no acotado en plano) | A=e·L/2, Iy=L·e³/24, Iz=e·L³/24, J/2 | 226/227 |
| caja_este (bajo VI-06) | muro en Y, x=16.546 | y 2.90..7.92 (L_y=5.02 m) | e=0.30 m **ASSUMED_FOR_MODEL** | idem caja_oeste | 256/257 |
| pilastra (x≈7.947) | 4 columnas por esquina (244/245/246/247) | e_x=0.60 m **EXPLÍCITO del plano** (caras 7.650/8.250; gap N 7.646..8.246); L_y=5.02 m | cada columna = ¼ de sección bruta (A=e·L_y/4, Iy/4, Iz/4, J/4) | 244/245/246/247 |
| 2ª escalera (2º hueco este, bajo VI-07) | muro en X, y=7.92 | x 18.545..20.794 (L=2.249 m) | e=0.30 m **ASSUMED_FOR_MODEL** | idem caja_oeste (muro en X) | 258/259 |

- **Nodo 259 conservado en x=20.794** (borde norte real del 2º hueco, `digitalizacion_vi_roof_pendiente.md` §8.5): el muro en X une directamente 258–259, sin aproximar a las columnas interiores x≈20.550.

### 10.2 Implementación y verificación

- Convención de rigidez: misma que los muros LT2 (`_make_lt2_wall`): un `elasticBeamColumn` por esquina con media sección, transf 10001, material LT2 (E=23.5e6, G=9.79e6 kPa). Total por tramo = muro académico (A=e·L, Ix=e·L³/12, …).
- Tags nuevos (libres verificados): **nodos 700001..** (50, B1..L4 por esquina) y **elementos 70001..** (50, un tramo por nivel B1→ROOF). Los máximos ocupados eran: LT1 combinado ≤ 600205 (no-master 500205 + 100000) y elementos LT1 nativos ≤ 400006; el rango 7xxxx no colisiona.
- **Bases B1 empotradas (ops.fix 6 GDL, 10 nuevas)** = convención real de fundación del modelo (SUP_B1_*), NO restricción artificial. Apoyos totales: 47.
- Nodos intermedios B1..L4 sin agregar a los rigidDiaphragm.
- **Resultado: `rc = 0`** (converge). ΣRz = 31 723.92 kN = P_total (rel 6.97e-14); Σ|Rx| = 6.69e-10, Σ|Ry| = 3.26e-11 kN; máx |U| = 0.01684 m (nodo 178). Nodos sin camino a apoyos restantes: solo masters (1001–1005) y muros LT1 (6001xx/6002xx), unidos por restricciones cinemáticas del modelo (rigidDiaphragm/rigidLink), que **no son mecanismos**.
- Copia máquina: `outputs/verticales_cajas_pilastra.csv`. Figura: `outputs/vista_3d_combinado.png` (rojo, tags 70001+).