# LT1 Viewer - Unity

Visor 3D del modelo estructural LT1 (OpenSeesPy).

## Requisitos
- Unity 2022.3 LTS (o superior) con licencia compatible.
  NOTA: revisiones "Extended LTS" requieren licencia Industry/Enterprise.
  Usar una LTS normal (p. ej. 2022.3.2x) para licencia Personal.

## Abrir el proyecto
1. Abrir Unity Hub
2. Click "Open" → navegar a `unity/LT1Viewer/`
3. Esperar a que Unity importe los assets (crea los `.meta` y compila los scripts; los `.cs` ya compilan con 0 errores)
4. Si pregunta por render pipeline, elegir **Built-in** (no URP/HDRP)

## Ejecutar la escena
- Automático: menú `LT1 > Build LT1Viewer Scene` (Assets/Editor/LT1SceneBuilder.cs) crea
  `Assets/Scenes/LT1Viewer.unity` con cámara, luz y el GameObject "LT1Viewer" con todos los componentes.
- Manual (si no se usa el builder): crear escena vacía → GameObject vacío "LT1Viewer"
  con componentes ModelLoader, StructuralViewer, SelectionController, VisibilityController,
  OrbitCamera, IdLabelController, LocalAxesController y TributaryAreaInspector;
  Main Camera con OrbitCamera (tag MainCamera) y Directional Light.
- Igualmente puede usarse cualquier otro objeto como cámara si el proyecto ya tiene una escena de arranque.
- Presionar Play.

## Controles de cámara
| Acción | Input |
|--------|-------|
| Órbita | Click izquierdo + arrastrar |
| Zoom | Rueda del mouse |
| Pan | Click medio + arrastrar |
| Reset vista | Tecla R |

## Toggles de visibilidad
| Tecla | Grupo |
|-------|-------|
| 1 | Nodos |
| 2 | Vigas |
| 3 | Columnas |
| 4 | Muros equivalentes (6, geometría clase A) |
| 5 | Apoyos |
| 6 | Diafragmas |
| 7 | Constraint Links (rigidLink de muros, punteados) |
| 8 / P | Panel "Geometría pendiente" (no modelada) |
| N | IDs de nodos |
| E | IDs de elementos (vigas, columnas y muros) |
| A | Ejes locales (vigas, columnas y muros) |

## Resultados estructurales (P1L4)
| Tecla | Acción |
|-------|--------|
| D | Deformada ON/OFF (escala ajustable con **+** / **-**) |
| M | Diagramas de esfuerzos del elemento seleccionado (ON/OFF) |

- Al seleccionar una viga/columna/muro se muestra (esquina inferior derecha)
  el **panel de resultados locales** con N, Vy, Vz, T, My, Mz en los extremos
  i y j, nodos asociados y el **elementTag de OpenSeesPy ↔ objeto Unity**.
- Convención: N interno con compresión < 0 y tracción > 0; en el JSON
  `F_i[0] = -N` y `F_j[0] = +N` (ver `convencion_fuerzas`).
- **Deformada (D):** usa `analysis.desplazamientos` del JSON (m). Los nodos,
  vigas, columnas, muros y constraintLinks se mueven/se reorientan;
  los diafragmas permanecen en su plano (rigidez de plano) — limitación.
- **Diagramas (M):** perfiles 3D sobre el elemento seleccionado
  (magenta = M resultante hypot(My,Mz); verde = N interno; naranja =
  V resultante hypot(Vy,Vz)). El perfil es **lineal entre extremos**
  (valores reales de `analysis.fuerzas_elementos`): exacto para columnas y
  muros sin carga en el claro, y aproximado para vigas con q_G (la viga real
  tiene diagrama parabólico).

## Demanda-Capacidad P-M (P1L4) — requisito PENDIENTE POR DATOS
> **Estado: NO CUMPLIDO POR DATOS FALTANTES.** El enunciado exige curva P-M,
> punto de demanda y caso activo para al menos una columna y un muro. Se
> implementó la infraestructura (JSON `capacidades` + panel), pero **no existe
> curva de capacidad sustentada** para ninguna pieza. NO se exporta ninguna
> curva basada en supuestos.

- Al seleccionar la **columna 111000** o el **muro 400001**, el panel
  superior derecho muestra la **demanda real del modelo** (caso `G_gravedad`):
  columna N = -519.6 kN / M = 123.6 kN·m (extremo i); muro N ≈ 0 / M = 123.6
  kN·m. Es el resultado verificado de `src/modelo_lt1.py`
  (`ops.eleResponse('localForce')`, P = ΣRz = 20182.625 kN).
- **Ambas piezas están `NO_DISPONIBLE`** y el panel lista sus **datos
  faltantes** en lugar de dibujar una curva inventada.
- La curva P-M de la **Parte D (Semana 3)** para la columna 111000 usó
  `f'c = 30 MPa`, `fy = 420 MPa`, `4 cm cara→eje` y una distribución de las
  16 Φ22 **TODOS SUPUESTOS de modelación** (los planos LT1 no documentan
  f'c/fy y remiten el recubrimiento a la E.T.O.G., no disponible). Esa curva
  **no se incorpora al JSON como capacidad** del proyecto.
- Datos reales disponibles (proveniencia): sección `P. 70x70` (JSON) y
  armadura 16 Φ22 (`COMBINADO/outputs/reinforcement/armadura_lt1_columnas.csv`,
  `elementTag=111000`, EXACT). Muro: geometría NSUP_01 e=20 cm, L=3.65 m
  (plan 102, confirmada por usuaria); **armadura longitudinal NO legible**
  (`armadura_lt1_muros.csv`: bar_count/diámetro/espaciado vacíos,
  NEEDS_DRAWING_VALUE_CONFIRMATION).
- Trazabilidad: `elementTag` JSON ↔ objeto Unity ↔ `fuerzas_elementos` ↔
  `capacidades` (todo proviene del mismo `src/modelo_lt1.py`).
- **Para completar el requisito falta** (en planos/E.T.O.G./memoria): f'c,
  fy, recubrimiento y distribución transversal de la columna; y para el muro
  además la armadura longitudinal legible y su análisis de sección P-M.

## Selección e inspección
- **Click izquierdo** en una viga, columna o muro para seleccionarlo
- Panel de viga/columna: tipo, tag, nodos i/j, sección, longitud, nivel
- Si es viga: datos tributarios (área, q_G, carga total, carga lineal)
- Panel de muro equivalente: ID/clave, tag, nodos, sección equivalente,
  espesor, longitud en planta, orientación y tramo vertical (PISO_1→PISO_2).
  Es un elemento resistente lineal `elasticBeamColumn` (no un shell FE).
- Click en espacio vacío para deseleccionar

## Constraint Links (rigidLink de muros)
- Cada muro equivalente conecta sus nodos base y tope al nodo maestro del
  diafragma correspondiente mediante `ops.rigidLink('beam', master, nodo_muro)`.
- En el visor aparecen como líneas punteadas cian (toggle 7) para no confundirse
  con elementos resistentes reales.
- El panel de selección (al hacer click sobre un rigidLink) muestra retainedNode,
  constrainedNode y tipo `beam`.

## Geometría pendiente (no modelada)
Listada en el panel "Geometría pendiente" (tecla P) y en `pending_geometry` del JSON:
- Núcleo PISO_4 (plan 103): extremos sin cerrar
- Muros subterráneo (plan 101)
- V.30/45 · V.60/VAR · V.60-30/80-40
- P.M. 300x300x20 · V.M.
- Carga de salientes (PISO_2)

No se inventa geometría para representarlos; permanecen como pendientes explícitas.

## Fuente de datos
- `Assets/StreamingAssets/modelo_lt1.json`
- Exportado desde Python (`src/modelo_lt1.py` → `exportar_modelo_unity()`),
  que copia automáticamente el JSON generado a `StreamingAssets`.
- Para regenerar: `python3 src/modelo_lt1.py` (raíz del repo) y revisar
  `outputs/unity/modelo_lt1.json`.
- NO es la fuente de verdad geométrica (eso es OpenSeesPy)

## Estado del modelo (etapa P1L2)
- Estado: **MODELO_ANALIZABLE_CON_GEOMETRIA_RESPALDADA_ACTUAL**
- 124 nodos (120 estructurales + 4 masters) · 204 `elasticBeamColumn`
  (90 columnas + 108 vigas + 6 muros equivalentes) · 12 `rigidLink` ·
  18 apoyos · 4 diafragmas
- Análisis de gravedad: analyze OK, P = ΣRz = 20182.625 kN, error relativo
  ≈ 9.01e-16, sin NaN/Inf

## Limitaciones
- Solo geometría **clase A** modelada; 8 items de geometría pendiente (ver arriba)
- Perfiles metálicos pendientes (segunda etapa)
- Material H°A°: E=25,000,000 kPa, ν=0.20, G=10,416,667 kPa
  (INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO)
- Resultados de fuerza incluidos solo del caso **G_gravedad** (único caso con
  fuerzas por elemento verificadas en este export); sismo/viento/combinaciones
  de semana 3 pertenecen al modelo COMBINADO (LT1+LT2) y no están aquí.
- Diagramas M/N/V con perfil lineal extremo a extremo (aprox. para vigas con q_G).
- Deformada: diafragmas permanecen en su plano (rigidez de plano) al activarse.
- **No hay curva P-M exportada** (columna y muro NO_DISPONIBLE): f'c/fy/
  recubrimiento no documentados (E.T.O.G. pendiente) y armadura de muros no
  legible en los planos. El requisito P1L4 de demanda-capacidad queda
  **pendiente por datos faltantes** (ver sección Demanda-Capacidad).

## Mapeo de coordenadas
| OpenSeesPy | Unity |
|------------|-------|
| X (horizontal) | X |
| Y (horizontal decreciente) | -Z |
| Z (vertical arriba) | Y |