# Semana 5 — Viewer estructural, modificación y QA

Fecha de revisión: 22-09-2026  
Modelo evaluado: `COMBINADO_LT1_LT2`  
Visor: `unity/LT1Viewer`, Unity 6000.5.0f1

Este informe registra el estado que puede reproducirse desde el repositorio.
No se considera implementada una función solamente por estar prevista en la
interfaz. El modelo exportado contiene 485 nodos, 694 elementos, 53 apoyos,
cinco diafragmas y cinco casos: `G`, `Q`, `EX`, `EY` y `COMBO_R`.

Versión estructural y del visor evaluada: rama `p1l4`, commit `ea7e4d8`
(`Close Week 5 mobile viewer features`), publicado en `origin/p1l4`. Este
informe se incorpora al repositorio en un commit posterior sin modificar el
modelo evaluado.

## 1. Funciones implementadas

| Función | Estado | Evidencia y limitación |
| --- | --- | --- |
| Navegación | **Implementada en escritorio y táctil** | Mouse: órbita, zoom y pan. Pantalla táctil: un dedo orbita; dos dedos trasladan y hacen zoom por pinza. |
| Selección | **Implementada** | Raycast por clic o toque corto sobre vigas, columnas y muros; el panel derecho muestra `elementTag`, nodos, longitud, sección, material, restricciones y resultados del caso activo. |
| Apoyos | **Implementada** | Capa con 53 apoyos B1. Las restricciones relevantes también aparecen al seleccionar un elemento conectado. |
| Ejes | **Implementada** | Conmutador de ejes locales; prioriza los ejes exportados y usa `vecxz` como respaldo. |
| Cargas | **Implementada** | Flechas verticales para G/Q/COMBO y laterales para EX/EY. La corrección firmada V30 redistribuye G y Q desde V40 sin cambiar la carga total del piso. |
| Áreas tributarias | **Implementada** | LT2 dibuja los polígonos fuente y, en naranja, las franjas equivalentes positivas transferidas a V30. LT1 dibuja una franja rectangular equivalente `A/L`; estas franjas equivalentes no se presentan como polígonos originales. |
| Deformada | **Implementada** | Superposición sobre la geometría original, por caso activo y con factor gráfico ajustable. Usa desplazamientos nodales, por lo que una barra recta se representa por sus dos extremos. |
| Diagramas | **Implementada** | `Mz`, `My`, `N`, `Vy`, `Vz` y `T`, en 3D y como gráfica 2D en el panel del elemento. Interpola linealmente los valores de extremo; en vigas con carga distribuida no reconstruye la curva interior exacta. |
| Superposición | **Parcial** | El usuario cambia interactivamente entre resultados ya calculados. Existe `COMBO_R = 1G + 1Q + 1EX + 0EY`, pero no hay editor de coeficientes ni superposición arbitraria en tiempo real. |
| P–M | **Implementada con supuestos declarados** | Columna 113022 y muro físico M001 (objetos 4001+4002). Muestra curva, demanda, caso y DENTRO/FUERA. El muro M001 resulta fuera en EY con la capacidad provisional. |
| Modificación del modelo | **Manual reproducible** | Unity no edita el modelo ni ejecuta OpenSees. Se modifica el dato fuente, se regenera con Python, se valida y se sincroniza el JSON a Unity. |

Los espesores y colores de Unity son solo gráficos: vigas azules de 0,55,
columnas verdes de 0,70 y muros violetas de 0,72 unidades. No sustituyen las
propiedades de sección guardadas en el JSON/OpenSees.

## 2. Modificación

No hay modificación estructural automática desde el viewer. Los dos flujos
siguientes recorren la cadena completa de forma manual y reproducible.

### 2.1 Corrección del eje I′ de LT1

**Interfaz/dato.** En `COMBINADO/src/run_combined.py`, la entrada explícita
`_X_IP_ANTES = 42.5` y `_X_IP_CORRIGE = 45.0` registra la corrección del eje
I′. Es una entrada manual en código, no un formulario Unity. Debe trasladarse
a un CSV si se generaliza la edición.

**Modelo.** Se desplazan 18 nodos del eje I′. Las doce vigas I–I′ pasan de
2,50 a 5,00 m y su área tributaria equivalente aumenta en 6,25 m² por piso.
La geometría LT1 original no se sobrescribe: el cambio solo existe en
`COMBINADO`.

**OpenSees.** `CombinedBuilder` crea nuevamente los nodos y
`elasticBeamColumn`, aplica las cargas sobre la longitud corregida y ejecuta
un análisis limpio por caso.

**Resultados.** Se vuelven a calcular fuerzas locales, desplazamientos,
reacciones y equilibrio. No se reutilizan resultados anteriores después de
la modificación.

**Unity.** `exportar_unity_combinado.py` escribe la geometría y los cinco
casos en `COMBINADO/outputs/unity/modelo_combinado.json`;
`integrar_p1l4_unity.py` copia la fuente a `StreamingAssets`.

### 2.2 Salientes y partición de vigas de fachada LT1

**Interfaz/dato.** `_SALIENTES_DATA` contiene por nivel las coordenadas,
puntos de partición y conexiones respaldadas por la geometría CAD. Es un
flujo manual y actualmente el dato está dentro de `run_combined.py`.

**Modelo.** Se incorporan 30 `viga_saliente` (tags 800101–800130) y 25
`segmento_fachada` (rango 800201–800228). Once vigas originales de fachada
se retiran del dominio y se sustituyen por tramos conectados; no se crean
diagonales ni elementos sin respaldo.

**OpenSees.** Cada segmento se crea como `elasticBeamColumn`. La carga
uniforme de cada viga retirada se aplica con la misma densidad `qG` a todos
sus segmentos finales. Por tanto,
`qG·ΣL_segmentos = qG·L_original`: no se pierde ni se duplica carga.

**Resultados.** El builder comprueba longitud conservada, conectividad hacia
apoyos, convergencia y equilibrio. El exportador vuelve a obtener fuerzas y
desplazamientos para G, Q, EX, EY y COMBO_R.

**Unity.** Los nuevos tags se exportan con tipo, nodos, sección, ejes y
resultados. El visor los clasifica como vigas y permite seleccionarlos y
dibujar sus diagramas.

### 2.3 Ejecución común

Desde la raíz del repositorio:

```powershell
python COMBINADO/src/exportar_unity_combinado.py
python COMBINADO/src/integrar_p1l4_unity.py
python COMBINADO/src/validar_unity_combinado.py
python COMBINADO/src/validar_unity_viewer_estatico.py
python -m pytest -q
```

Después se abre `Assets/Scenes/LT1Viewer.unity`, se presiona Play y se
comprueba el elemento modificado por `elementTag`.

La incorporación posterior de las V30 9011–9020 también llega hasta
OpenSees/resultados/Unity. Para L1–L4 se aplican 24 correcciones uniformes
firmadas: ocho aportes positivos a V30 y dieciséis descargas compensatorias
en V40. En cada piso `ΣΔA=0`, por lo que `ΣΔG=ΣΔQ=0`. ROOF no recibe
corrección porque la fuente no le asigna carga de losa.

## 3. Superposición interactiva

El selector del HUD recarga fuerzas, desplazamientos, reacciones y equilibrio
del caso seleccionado. No suma estados en C#; `COMBO_R` fue resuelto y
exportado desde un modelo OpenSees limpio con los patrones G+Q+EX.

Se comprobaron tres estados directamente en el JSON maestro:

| Estado mostrado | Comprobación numérica | Resultado |
| --- | --- | --- |
| **G** | `ΣRz = 31.086,259667 kN` frente a `P = 31.086,259667 kN` | Error `1,09×10⁻⁸ kN`; equilibrio vertical correcto. |
| **EX** | `|ΣRx| = 8.021,852135 kN` frente a fuerza lateral `8.021,852135 kN` | Error `6,82×10⁻⁹ kN`; corte basal correcto. |
| **COMBO_R** | Para columna 113022, `N1`: 1063,734766 (G) + 598,277610 (Q) + 1,569045 (EX) = **1663,581421 kN** | Coincide con COMBO_R con diferencia `2,05×10⁻¹² kN`. |

Comprobación adicional de la superposición visual: en el nodo maestro 1004,
`Ux(G)+Ux(Q)+Ux(EX) = 0,004373838380 m`, igual a `Ux(COMBO_R)` con diferencia
`4,34×10⁻¹⁸ m`. En la viga 2081, `My2` suma
`−134,222338 − 88,275563 + 27,197963 = −195,299938 kN·m`, igual al valor
exportado para COMBO_R.

La superposición disponible no cubre `G+Q+EY`, sentidos sísmicos negativos ni
combinaciones normativas envolventes. Por ello COMBO_R no debe presentarse
como combinación crítica universal.

## 4. Sidequest carga móvil

**Implementada como sidequest visual y de reparto, sin reanálisis.** El usuario
selecciona una viga, activa `CARGA MOVIL`, ingresa `P [kN]` y mueve el control
`x/L` entre 0 y 1. La magnitud inicial es cero para no inventar una carga.

La regla es un reparto lineal equivalente entre los nodos extremos:
`Pi=P(1-x/L)` y `Pj=P(x/L)`. El panel muestra ambas cargas y comprueba en cada
posición la conservación de fuerza `Pi+Pj=P` y del primer momento
`Pj·L=P·x`. Una flecha roja se desplaza sobre el elemento seleccionado y el
panel identifica su tag. El alcance queda explícito en pantalla: no modifica
el JSON, no crea un nuevo caso y no vuelve a ejecutar OpenSees; por tanto, no
debe confundirse con las reacciones reales del marco, una línea de influencia
ni una envolvente móvil.

## 5. UX estructural

| Pregunta | ¿La responde? | Evaluación |
| --- | --- | --- |
| ¿Dónde está el elemento? | **Sí** | Selección 3D, resaltado amarillo, ID, origen, nivel, nodos y capas. Falta búsqueda directa por tag y botón de encuadre. |
| ¿Cómo está apoyado? | **Parcialmente** | Se muestran apoyos, diafragmas, rigid links y restricciones del elemento. No existe una vista aislada de la ruta completa de carga hasta fundación. |
| ¿Qué lo carga? | **Sí, con alcance indicado** | Flechas, área tributaria, carga agregada y redistribución V30 aplicada. LT1 y las correcciones V30 usan geometría equivalente claramente identificada. |
| ¿Cómo se deforma? | **Sí** | Deformada superpuesta, caso activo y escala ajustable. No presenta una escala métrica/leyenda ni curvatura interna del elemento. |
| ¿Qué fuerzas tiene? | **Sí** | N, Vy, Vz, T, My y Mz por extremo, diagramas 3D y gráfica del seleccionado. La gráfica interior es una interpolación de extremos. |
| ¿Cuánta capacidad tiene? | **Solo para dos objetos de estudio** | P–M para columna 113022 y muro M001. No hay capacidad para el resto y existen supuestos de recubrimiento/disposición de acero. |

El viewer cumple bien como postprocesador de inspección y trazabilidad. Aún no
es una herramienta de edición/diseño ni una comprobación normativa general.

## 6. Preparación móvil

**Teléfono objetivo identificado:** Samsung Galaxy A54 5G como dispositivo de
prueba propuesto, no ensayado. Su ficha oficial declara Android 13, procesador
Exynos 1380 de ocho núcleos, 6 GB de RAM y pantalla 1080×2340. Supera los
requisitos generales de Unity 6 para Android (Android 6/API 23+, ARM con Neon
o ARM64, OpenGL ES 3.0+/Vulkan y al menos 1 GB de RAM):
[requisitos Unity 6](https://docs.unity3d.com/6000.0/Documentation/Manual/system-requirements.html)
y [ficha Samsung](https://image-us.samsung.com/SamsungUS/samsungbusiness/pdf/spec-sheets/a54/HHP_A545G_DATA_USCC.pdf).

El proyecto tiene escena registrada, API mínima 26, ARM64, orientación
horizontal y un build reproducible mediante `LT1/Build Android APK` o
`AndroidBuild.BuildFromCommandLine`; la salida prevista es
`Builds/Android/LT1Viewer-semana05.apk`. El HUD aumenta botones y dimensiones
en plataforma móvil; un dedo permite toque/órbita y dos dedos pan/zoom.

**Estado del APK:** pendiente por entorno local. Unity 6000.5.0f1 informó que
no existe una licencia activa para el editor batch y AndroidPlayer aún no está
instalado. Se inició la instalación por Unity Hub, pero el Hub la interrumpió
por un error de E/S en su base local de cuenta. Por ello todavía no se afirma
que exista ni que se haya probado un APK. Deben activarse la licencia en Unity
Hub, completar Android Build Support + SDK/NDK + OpenJDK y ejecutar el método
de build; la prueba real en el A54 continúa pendiente.

## 7. IA

Una funcionalidad compleja desarrollada con apoyo de agente fue la cadena de
postproceso estructural de Semana 4: lectura del JSON combinado, cambio de caso
sin recargar geometría, deformada, seis diagramas de fuerzas y trazabilidad
`elementTag → GameObject → fuerzas/desplazamientos → sección → P–M`.

La verificación no se basó solo en observar la escena:

- `validar_unity_combinado.py`: **62.012 comprobaciones, 0 problemas** el
  21-09-2026.
- Las identidades de la sección 3 verifican equilibrio y linealidad de
  COMBO_R con los números exportados.
- Las pruebas P–M verifican cinco casos, recomposición del muro M001 y el
  estado fuera de capacidad del muro bajo EY.
- `validar_unity_viewer_estatico.py`: **27 comprobaciones, 0 problemas**.
  La escena temporal `Assets/_Recovery/0.unity` se conserva como trabajo
  recuperable y el validador la excluye explícitamente; la única escena fuente
  evaluada continúa siendo `Assets/Scenes/LT1Viewer.unity`.
- Compilación independiente de `Assembly-CSharp` y
  `Assembly-CSharp-Editor`: **0 errores**. El ensamblado de editor que contiene
  `AndroidBuild` terminó además con 0 advertencias; el runtime conserva avisos
  legacy de API/serialización que no impiden compilar.
- Ejecución actual de `pytest`: **162 aprobadas**, con dos avisos
  `PytestUnknownMarkWarning` por la marca `slow`. Los avisos no alteran el
  resultado de las pruebas.

## Conclusión frente a la rúbrica

El viewer, la redistribución V30, la interacción táctil y la carga móvil visual
quedan implementados y verificados estáticamente. La modificación/reanálisis
estructural continúa como flujo manual reproducible; COMBO_R y P–M mantienen
su alcance y supuestos explícitos. El único cierre que no puede declararse
logrado es generar e instalar/probar el APK: depende de activar la licencia y
completar los módulos Android del editor local. El código estructural y del
visor usado para esta evaluación queda trazado en el commit `ea7e4d8`.
