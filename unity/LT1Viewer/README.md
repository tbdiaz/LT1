# LT1 Viewer — postprocesador Unity del modelo COMBINADO

Visor de resultados OpenSees para LT1+LT2, preparado para la entrega P1L4.
La fuente en tiempo de ejecución es
`Assets/StreamingAssets/modelo_combinado.json`.

## Abrir y ejecutar

1. Abrir `unity/LT1Viewer` con Unity 6000.5.0f1.
2. Abrir `Assets/Scenes/LT1Viewer.unity`. Si la escena no existe, usar el
   menú `LT1 > Build LT1Viewer Scene`.
3. Esperar la compilación y presionar Play.

La escena también agrega en tiempo de ejecución los controladores nuevos si
fue creada con una versión anterior del builder.

## Interfaz y controles

- Panel izquierdo: capas de nodos, vigas, columnas, muros, apoyos,
  diafragmas, rigid links, IDs y ejes locales.
- Barra superior: caso activo, deformada, diagrama, cargas y áreas
  tributarias. Los botones verdes están activos.
- Panel derecho: al hacer clic en un elemento muestra tag, nodos, sección,
  material, restricciones, ejes locales y `N, Vy, Vz, T, My, Mz` en sus
  extremos i/j.
- Cámara: botón derecho para orbitar, rueda para zoom, botón central para pan
  y botón izquierdo para seleccionar.

## Resultados y convenciones

Los casos disponibles se leen de `results.cases`: `COMBO_R`, `EX`, `EY`,
`G` y `Q`. Al cambiar de caso se actualizan resultados, deformada, diagramas
y cargas.

El inspector presenta fuerzas internas de sección con la convención
`i = -F_i` y `j = +F_j`, conservando el signo de cada componente. Los
diagramas permiten elegir directamente `Mz`, `My`, `N`, `Vy`, `Vz` y `T`.
Se muestran como trazo 3D de alto contraste y como gráfica 2D dentro del
inspector derecho del elemento seleccionado; se
representan linealmente entre las fuerzas de extremo exportadas. Esto es exacto para un
elemento sin carga distribuida en el claro y una aproximación de extremos
para vigas cargadas.

La deformada usa los desplazamientos nodales reales del caso activo y un
factor gráfico ajustable con los botones `−` y `+`. Se superpone en rojo y
amarillo sobre la forma original; no modifica el modelo ni los resultados.

## Capas gráficas

- Vigas: azul, espesor gráfico 0.55 m.
- Columnas: verde, espesor gráfico 0.70 m (amarillo solo mientras están seleccionadas).
- Muros: violeta, espesor gráfico 0.72 m.
- Apoyos: rojo; nodos: cian.
- Cargas G/Q/COMBO: flechas verticales agregadas por viga.
- Cargas EX/EY: flechas laterales en nodos maestros.
- Áreas LT2: contorno del polígono exacto exportado desde el CSV.
- Áreas LT1: franja rectangular equivalente centrada, de área `A/L`, porque
  la fuente LT1 no contiene vértices de polígonos. Se declara como
  representación equivalente, no como geometría exacta.

Los espesores y colores son solo recursos visuales; no alteran secciones,
rigideces ni geometría OpenSees.

## Demanda–capacidad P–M

Al seleccionar la columna `113022` o cualquiera de los dos objetos Unity del
muro M001 (`4001`, `4002`), se muestra su curva P–M, el punto de demanda, el
caso activo y la condición DENTRO/FUERA. Los objetos 4001+4002 se agrupan para
la comprobación del muro físico M001.

Las curvas y demandas provienen de `results.pm`. El JSON documenta dentro de
cada bloque los datos confirmados y los supuestos empleados; la defensa debe
explicar esas salvedades y no presentarlas como información extraída del
plano. Unity presenta directamente las figuras auditadas
`pm_column_113022.png` y `pm_wall_M001.png`, con ejes, leyendas y demandas de
todos los casos; debajo identifica el caso activo.

## Trazabilidad

`elementTag OpenSees -> ElementRef/jsonIndex -> GameObject Unity ->
results.forces/displacements -> seccion -> results.pm`.

El generador estructural está en `COMBINADO/src/exportar_unity_combinado.py` y
la integración/sincronización P–M en `COMBINADO/src/integrar_p1l4_unity.py`.
Para validar:

```powershell
python COMBINADO/src/validar_unity_combinado.py
python COMBINADO/src/validar_unity_viewer_estatico.py
python -m pytest -q
```

## Mapeo de coordenadas

| OpenSees | Unity |
|---|---|
| X | X |
| Y | -Z |
| Z | Y |

La compilación C# se verificó sin errores. La apertura visual final debe
realizarse con una licencia Unity activa; el modo batch no pudo adquirir una
licencia en el entorno usado para esta revisión.
