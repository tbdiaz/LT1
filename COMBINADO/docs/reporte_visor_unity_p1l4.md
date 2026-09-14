# Reporte — Adaptación del visor Unity al modelo combinado (P1L4)

Fecha: 2026-09-11
Ámbito: `unity/LT1Viewer` (scripts C# y editor) + `COMBINADO` (validación).

El visor Unity existente (antes limitado a `modelo_lt1.json`) se adaptó para
cargar y visualizar el modelo estructural **combinado LT1+LT2** exportado en
`modelo_combinado.json`. No se modificó ningún archivo de modelo, geometría,
cargas, materiales, secciones ni armaduras: toda la información mostrada
proviene exclusivamente del JSON exportado.

---

## 1. Fuente única de datos

- `ModelLoader` carga `StreamingAssets/modelo_combinado.json` (14540527 B,
  sha256 `0db8d908…`).
- `modelo_lt1.json` se conserva intacto en StreamingAssets por compatibilidad
  histórica, pero no es fuente de datos del visor.
- No existe ningún archivo `.unity` en el proyecto: la escena se genera por
  menú de editor (`LT1/Build LT1Viewer Scene`), como antes.

## 2. Esquema C# espejo del JSON (`CombinedModelData.cs`)

Clases `[Serializable]` por sección: `ModeloCombinado`, `CombinedMetadata`,
`CombinedUnits`, `CombinedMaterials`, `CombinedConcreto`, `CombinedAcero`,
`CombinedConectorV40`, `CombinedCaseSet`/`CombinedCaseInfo`/`CombinedCoef`,
`CombinedLevel`, `CombinedNode`, `CombinedSection`, `CombinedElement`
(incluye `orientacion`, `constraint`, `nivel_inferior`, `nivel_superior`),
`CombinedAxes`, `CombinedSupport`, `CombinedMaster`, `CombinedDiaphragm`,
`CombinedLink`, `CombinedBeamLoad` (incluye `nivel`, `w_kN_m`,
`tag_original`), `CombinedLateralLoad`, `CombinedTribRow`, `CombinedResults`.
JsonUtility no admite diccionarios: `results.forces/displacements/reactions/
equilibrio` se re-parsean del texto del JSON por caso (ver punto 4).

## 3. Construcción de la escena a partir del JSON combinado

Se mantienen los controladores legacy (`BeamMesh`, `ColumnMesh`, `WallMesh`,
etc.) alimentándolos con agregados `ModelRoot` derivados del combinado con
mapeos explícitos de categoría:

| Categoría visor | Tipos combinados | Cantidad |
|---|---|---|
| Beam | viga, viga_saliente, segmento_fachada | 389 |
| Column | columna, vertical_caja | 175 |
| Wall | muro, muro_corner, conector_v40_muro | 96 |

## 4. Casos de carga desde `results.cases`

- `CaseList` se toma exclusivamente de `results.cases` del JSON
  (`G`, `Q`, `EX`, `EY`, `COMBO_R`): no se ofrece ningún caso que no exista.
- `SetActiveCase(caseKey)` re-parsea del JSON crudo las fuerzas, los
  desplazamientos, las reacciones y el equilibrio del caso y rellena
  `analysis.*`, `elementForceI/J` y el equilibrio activo.
- Al cambiar de caso se dispara el evento estático `ModelLoader.CaseChanged`;
  la deformada y los diagramas re-capturan los valores del caso sin recapturar
  la geometría base.

## 5. Descripciones y combinación documentada

Cada caso expone su `descripcion` desde `metadata.casos`; para `COMBO_R` se
muestra la combinación real del JSON:
`R = 1G + 1Q + 1EX + 1EY`.

## 6. Trazabilidad completa elemento a elemento

`ElementRef` vincula `elementTag ↔ jsonIndex ↔ GameObject` (diccionario
`elementRefs`) y carga el `tipo`, `origen` (LT1/LT2), categoría, nodos I/J,
longitud, sección, `vecxz` y ejes locales exportados, además de los meta
campos (`nivel_inferior`, `nivel_superior`, `orientacion`, `constraint`).

## 7. Panel de selección

Al hacer clic en un elemento se muestra: tipo, tag, nodos I/J, niveles,
sección, material, `vecxz`, ejes locales (exportados o derivados),
restricciones de borde, caso activo, resultado y flag **SUPUESTO** cuando
aplica. Las claves de N/V en resultados referencian el elemento activo.

## 8. Ejes locales

`LocalAxesController` prioriza los ejes locales exportados en el JSON; si no
existen, los deriva de `vecxz` y el eje local Z vertical. Se corrige el signo
cuando el eje local X resulta opuesto a la dirección física del elemento.

## 9. Deformada por caso

`DeformedShapeController` captura posiciones base una sola vez y aplica los
desplazamientos del caso activo (re-capturados vía `CaseChanged`), respetando
el factor de amplificación configurado.

## 10. Diagramas M/N/V

`ForceDiagramController` dibuja momentos y axiles/cortantes por caso;
al congelar un caso (`freeze`) conserva el diagrama mientras se navega.

## 11. Cargas y equilibrio (tecla **L**)

`LoadInspector` muestra las cargas aplicadas del caso activo (G/Q/EX/EY),
la ficha de equilibrio parseada (`P`, `R`, error relativo), el conteo de
reacciones/masters y el resumen de áreas tributarias LT1 y LT2.

## 12. Restricciones de borde y conectividad

- 47 apoyos B1 (6 GDL) y masters 1001–1005 reconstruidos en
  `boundaryRestricciones` con su `boundaryOrigen` (apoyos / masters).
- 5 diafragmas y 12 constraint_links representados en el visor.
- El panel de selección indica si el elemento es de borde y detalla sus
  grados restringidos.

## 13. Inventario y tributarias

Datos verificados contra el JSON (validación estática):

- 461 nodos, 660 elementos, 47 apoyos, 5 masters, 5 diafragmas, 12 links.
- Cargas: G=27282, Q=27282, EX=4, EY=4 (independientes).
- Áreas tributarias: LT1=108 filas, LT2=320 filas (agregadas en el visor).

## 14. Capacidad P-M (preparada, sin datos)

La estructura de resultados contempla una pestaña de capacidad desplegable y
el campo `capacidades` (existentes en el esquema de resultados), pero el
JSON combinado no entrega aún esos datos: el visor lo reporta como **pendiente
de datos** y no muestra curvas inventadas. Por ello la etapa P1L4 (capacidad
P-M) **no se puede declarar completada**, solo la preparación del visor.

## 15. Validación estática

- `COMBINADO/src/validar_unity_viewer_estatico.py`: 25 comprobaciones OK
  (inventario, consistencia esquema C#↔JSON, casos↔results, balance de llaves
  por archivo .cs, sin clases duplicadas, sin referencias obsoletas a
  `pending_geometry`/`modelo_lt1.json`, sin escenas `.unity`).
- `COMBINADO/tests/test_unity_viewer_static.py`: nuevo wrapper pytest.
- Suite completa: **146 tests en verde**. El modelo estructural no fue tocado
  ni re-analizado en esta etapa.

## 16. Pendientes para la integradora

- **Prueba visual en Unity** (apertura del proyecto, generación de escena,
  capturas): no realizada aquí y por tanto no se afirma nada al respecto.
- Sin `git add/commit/push` (según restricción).
- Cuando existan datos de capacidad P-M, conectar el desplegable con los
  resultados correspondientes para cerrar P1L4.