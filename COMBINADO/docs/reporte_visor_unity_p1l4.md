# Reporte — Adaptación del visor Unity al modelo combinado (P1L4)

Fecha: 2026-09-16
Ámbito: `unity/LT1Viewer` (scripts C# y editor) + `COMBINADO` (validación).

El visor Unity existente (antes limitado a `modelo_lt1.json`) se adaptó para
cargar y visualizar el modelo estructural **combinado LT1+LT2** exportado en
`modelo_combinado.json`. No se modificó ningún archivo de modelo, geometría,
cargas, materiales, secciones ni armaduras: toda la información mostrada
proviene exclusivamente del JSON exportado.

---

## 1. Fuente única de datos

- `ModelLoader` carga `StreamingAssets/modelo_combinado.json`; el integrador
  copia exactamente el JSON maestro de `COMBINADO/outputs/unity` y las pruebas
  verifican igualdad SHA-256.
- `modelo_lt1.json` se conserva intacto en StreamingAssets por compatibilidad
  histórica, pero no es fuente de datos del visor.
- La escena fuente es `Assets/Scenes/LT1Viewer.unity` y también puede
  regenerarse con `LT1/Build LT1Viewer Scene`.

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
| Beam | viga, viga_saliente, segmento_fachada | 399 |
| Column | columna, vertical_caja | 175 |
| Wall | muro, muro_corner, conector_v40_muro | 108 |

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
`R = 1G + 1Q + 1EX + 0EY`.

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

## 10. Diagramas M/N/V/T

`ForceDiagramController` dibuja un componente con signo a la vez y permite
recorrer `Mz`, `My`, `N`, `Vy`, `Vz` y `T`. Usa la convención de sección
`i=-F_i`, `j=+F_j`; el perfil es lineal entre los resultados de extremo.

## 11. Cargas, áreas e interfaz

El HUD único reemplaza los paneles superpuestos. Permite activar cargas,
áreas, apoyos, deformada, diagramas y capas mediante botones. Las cargas
verticales se agregan por viga y EX/EY se dibujan en masters. LT2 usa sus
polígonos tributarios exportados; LT1 muestra una franja equivalente `A/L`
porque su fuente no contiene vértices.

## 12. Restricciones de borde y conectividad

- 53 apoyos B1 (6 GDL) y masters 1001–1005 reconstruidos en
  `boundaryRestricciones` con su `boundaryOrigen` (apoyos / masters).
- 5 diafragmas y 24 constraint_links representados en el visor.
- El panel de selección indica si el elemento es de borde y detalla sus
  grados restringidos.

## 13. Inventario y tributarias

Datos verificados contra el JSON (validación estática):

- 485 nodos, 694 elementos, 53 apoyos, 5 masters, 5 diafragmas, 24 links.
- Cargas: G=27282, Q=27282, EX=4, EY=4 (independientes).
- Áreas tributarias: LT1=108 filas, LT2=320 filas (agregadas en el visor).

## 14. Capacidad P-M

`results.pm` contiene curvas, demanda por caso y trazabilidad para la columna
113022 y el muro M001. Al seleccionar 113022, 4001 o 4002 se muestra curva,
punto de demanda, caso y DENTRO/FUERA. Los objetos 4001+4002 se agrupan como
un muro físico. Los datos confirmados y los supuestos de material, armado y
recubrimiento están declarados dentro del JSON y deben exponerse como tales.

## 15. Validación estática

- `COMBINADO/src/validar_unity_viewer_estatico.py`: 27 comprobaciones OK
  (inventario, consistencia esquema C#↔JSON, casos↔results, balance de llaves
  por archivo .cs, sin clases duplicadas, sin referencias obsoletas a
  referencias obsoletas y escena fuente controlada).
- `COMBINADO/tests/test_unity_viewer_static.py`: nuevo wrapper pytest.
- Suite completa: **158 tests en verde**.
- `validar_unity_combinado.py`: **61.612 verificaciones, 0 problemas**.
- Compilación `Assembly-CSharp`: **0 errores**.

## 16. Pendientes para la integradora

- **Prueba visual final en Unity**: pendiente en una sesión con licencia
  activa; el modo batch disponible no pudo completar el handshake de licencia.
- Los warnings de compilación son de APIs `FindObjectOfType` obsoletas y del
  analizador de serialización sobre diccionarios públicos; no hay errores.
