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
- Barra superior: caso activo, deformada, diagrama, cargas, áreas
  tributarias y carga móvil. Los botones verdes están activos.
- Panel derecho: al hacer clic en un elemento muestra tag, nodos, sección,
  material, restricciones, ejes locales y `N, Vy, Vz, T, My, Mz` en sus
  extremos i/j.
- Cámara de escritorio: botón derecho para orbitar, rueda para zoom, botón
  central para pan y botón izquierdo para seleccionar.
- Pantalla táctil: toque corto para seleccionar, arrastre con un dedo para
  orbitar y gesto de dos dedos para pan/zoom.

## Carga móvil

Seleccione una viga, active `CARGA MOVIL`, escriba `P [kN]`, presione
`APLICAR` y mueva `x/L`. La flecha roja sigue la posición. El panel muestra
el reparto lineal equivalente `Pi=P(1-x/L)`, `Pj=P(x/L)` y los errores de
conservación de fuerza y primer momento. No son las reacciones reales del
marco. Es una ayuda visual de Semana 5: no modifica el JSON ni reanaliza
OpenSees.

## SQ4 — carga móvil asociada al usuario

El panel derecho incluye un prototipo independiente de la carga puntual sobre
una viga. Al activar `USUARIO`, aparece un marcador amarillo que puede moverse
con `WASD`, las flechas del teclado o los cuatro botones de la interfaz.

- `NIVEL −/+` cambia entre los niveles 1 a 4.
- La posición se contrasta continuamente con los polígonos tributarios LT2 y
  con las franjas equivalentes LT1 construidas a partir de su área exportada.
- La interfaz informa el panel o región encontrado, resalta en rojo las vigas
  receptoras y muestra la carga del usuario asignada por viga.
- En puntos compartidos por varias regiones, la carga se reparte en partes
  iguales entre las vigas receptoras únicas.

La carga base de las regiones también se muestra como dato de trazabilidad.
SQ4 es una asignación visual: no modifica el JSON, no ejecuta OpenSees y no
actualiza diagramas ni demanda–capacidad.

## Laboratorio de modificaciones y reanálisis

El panel derecho incorpora un flujo reproducible para dos modificaciones:

1. Elegir un caso en la barra superior, escribir su **factor de carga** y
   presionar `APLICAR`.
2. Seleccionar una viga, columna o muro y presionar
   `DESACTIVAR ELEMENTO SELECCIONADO` (el mismo botón permite reactivarlo).

Estas acciones crean un escenario local y no modifican el JSON fuente. Las
flechas de carga se activan automáticamente y reflejan gráficamente el factor
con escala lineal (la visualización se limita a 4× para evitar flechas fuera
de pantalla), y el elemento desactivado
se oculta, pero las deformadas, esfuerzos, reacciones y comprobaciones P–M
siguen siendo los resultados del modelo base. Por eso la interfaz muestra
**REQUIERE REANÁLISIS** mientras exista cualquier modificación y etiqueta los
resultados como no actualizados. `RESTAURAR ESCENARIO BASE` elimina todos los
cambios y recupera la vigencia de los resultados originales.

## Superposición interactiva

El panel izquierdo contiene sliders independientes para `G`, `Q`, `EX` y
`EY`, con coeficientes entre −2.00 y +2.00. Al mover cualquiera, el viewer
combina inmediatamente los resultados base ya analizados:

- la deformada usa la suma de desplazamientos nodales;
- el inspector y los diagramas usan la suma de fuerzas de extremo;
- el punto de demanda P–M se reconstruye desde las fuerzas combinadas.

Para M001 se conserva la recomposición documentada de los elementos 4001 y
4002, leyendo `semilongitud_m` desde el JSON. La capacidad mostrada para un
punto combinado se interpola sobre la curva P–M exportada. `COMBO_R` carga
los coeficientes documentados del modelo y `CERO` anula los cuatro.

Esta operación es superposición de respuestas lineales existentes y no
requiere reanálisis mientras no se cambien geometría, rigidez, apoyos,
materiales, secciones ni activación de elementos. Las modificaciones del
apartado anterior siguen marcándose separadamente como **REQUIERE
REANÁLISIS**.

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

- Vigas: naranjo, espesor gráfico 0.55 m (amarillo solo mientras están seleccionadas).
- Columnas: gris, espesor gráfico 0.70 m (amarillo solo mientras están seleccionadas).
- Muros: rojo, espesor gráfico 0.72 m (amarillo solo mientras están seleccionados).
- Apoyos: rojo; nodos: cian.
- Cargas G/Q/COMBO: flechas verticales agregadas por viga.
- Cargas EX/EY: flechas laterales en nodos maestros.
- Áreas LT2: contorno del polígono exacto exportado desde el CSV.
- Redistribución V30: franja equivalente naranja para el área positiva
  transferida a los tramos nuevos; la descarga compensatoria se aplica en
  V40 y conserva el total por piso.
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

## APK Android

Con Android Build Support instalado, use `LT1 > Build Android APK` o:

```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.5.0f1\Editor\Unity.exe' `
  -batchmode -quit -projectPath '<ruta>\unity\LT1Viewer' `
  -executeMethod AndroidBuild.BuildFromCommandLine
```

La salida es `Builds/Android/LT1Viewer-semana05.apk` (API 26+, ARM64,
horizontal). En el equipo de revisión, la compilación final quedó bloqueada
porque Unity no tenía licencia activa y AndroidPlayer no terminó de
instalarse; no se declara un APK probado hasta resolver ambas condiciones.
