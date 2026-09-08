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
- Exportado desde Python (`src/modelo_lt1.py` → `exportar_modelo_unity()`)
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

## Mapeo de coordenadas
| OpenSeesPy | Unity |
|------------|-------|
| X (horizontal) | X |
| Y (horizontal decreciente) | -Z |
| Z (vertical arriba) | Y |