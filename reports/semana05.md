# Semana 5 — Laboratorio estructural interactivo

Fecha de revisión: 25-09-2026

Modelo evaluado: `COMBINADO_LT1_LT2`

Visor: `unity/LT1Viewer`, Unity 6000.5.0f1

Versión evaluada: rama `p1l4`, commit `a38463c`

Este informe registra únicamente funciones y datos reproducibles desde el
repositorio. El modelo combinado contiene 485 nodos, 694 elementos, 53
apoyos, cinco masters, cinco diafragmas, 24 `constraint_links` y los casos
`G`, `Q`, `EX`, `EY` y `COMBO_R`. La fuente de ejecución del visor es
`unity/LT1Viewer/Assets/StreamingAssets/modelo_combinado.json`, copia
sincronizada del maestro `COMBINADO/outputs/unity/modelo_combinado.json`.

## 1. Funciones implementadas

| Función | Estado | Evidencia, uso y alcance |
| --- | --- | --- |
| Navegación | **Implementada** | Escritorio: RMB órbita, rueda zoom, MMB pan. Táctil: un dedo órbita o selecciona mediante toque corto; dos dedos hacen pan/zoom. |
| Selección | **Implementada** | Raycast sobre vigas, columnas y muros. El panel informa `elementTag`, origen LT1/LT2, nodos I/J, nivel, longitud, sección, material, ejes, restricciones y resultados del caso activo. |
| Apoyos | **Implementada** | Capa con 53 apoyos B1 y visualización de restricciones. El inspector relaciona el elemento con restricciones en sus nodos, masters, diafragmas y vínculos rígidos cuando corresponde. |
| Ejes | **Implementada** | Capa de ejes locales X/Y/Z. Prioriza `ejes_locales` exportados y usa `vecxz` como respaldo, corrigiendo el signo respecto de la orientación física I→J. |
| Cargas | **Implementada con limitación de fuente** | Flechas verticales para G/Q/COMBO y laterales para EX/EY. Las vigas `ROOF` de LT2 no tienen cargas G/Q exportadas, por lo que no se inventan flechas en ese nivel. |
| Áreas tributarias | **Implementada** | LT2 usa polígonos exportados; LT1 muestra franjas equivalentes de ancho `A/L` porque su fuente no contiene vértices. La redistribución V30 conserva área y carga total por piso. |
| Deformada | **Implementada** | Usa desplazamientos nodales del caso activo o de la superposición. Se dibuja sobre la forma original con factor gráfico ajustable; dicho factor no modifica el resultado numérico. |
| Diagramas | **Implementada y reconstruida por equilibrio** | `Mz`, `My`, `N`, `Vy`, `Vz` y `T` en 3D y gráfica 2D. `My` usa cargas `beamUniform/beamPoint`; `Mz` usa `dMz/dx=-Vy`. Ya no se aproxima el momento cargado uniendo solamente los extremos. |
| Superposición | **Implementada e interactiva** | Sliders independientes G/Q/EX/EY en el rango −2…+2. Actualizan desplazamientos, deformada, fuerzas, diagramas, reacciones y punto P–M sin recargar geometría. |
| P–M | **Implementada con alcance acotado** | Disponible para columna 113022 y muro físico M001, agrupando 4001+4002. Presenta demanda, capacidad y condición DENTRO/FUERA. Curvas, fuentes y supuestos están declarados en `results.pm`. |
| Modificación del modelo | **Implementada como escenario; reanálisis no automático** | Permite cambiar intensidad del caso activo y activar/desactivar un elemento. Unity conserva los resultados base y muestra `REQUIERE REANÁLISIS`; no existe aún un puente de escritura Unity→OpenSees. |

Paleta actual: vigas naranjas, columnas grises y muros rojos. El elemento
seleccionado se resalta en amarillo. Colores y espesores son recursos
gráficos y no alteran secciones, rigideces ni geometría de OpenSees.

## 2. Modificación

Se implementaron dos modificaciones desde la interfaz. Ambas son completas
como definición de escenario y señalización de vigencia, pero **no ejecutan
automáticamente OpenSees**. El flujo estructural completo debe cerrarse de
forma manual y reproducible como se documenta a continuación.

### 2.1 Intensidad del caso de carga activo

#### Estado en Unity

1. **Interfaz/dato.** Se elige `G`, `Q`, `EX`, `EY` o una combinación, se
   ingresa un factor `α ≥ 0` y se presiona `APLICAR`.
2. `ScenarioModificationController` guarda `caso → α` en un diccionario de
   escenario, separado del JSON.
3. Las flechas se activan y escalan linealmente con `α` —con límite gráfico
   4× para evitar flechas fuera de pantalla—.
4. Deformada, esfuerzos, reacciones y P–M permanecen asociados al análisis
   base. La interfaz muestra `REQUIERE REANÁLISIS` y “resultados no
   actualizados”.

#### Flujo manual reproducible hasta resultados nuevos

`interfaz/dato → modelo → OpenSees → resultados → Unity`:

1. Registrar el caso y `α` mostrado por Unity.
2. En una copia controlada del generador, aplicar `α` al patrón
   correspondiente antes del análisis:
   - G: cargas de `CombinedBuilder.apply_loads()` en
     `COMBINADO/src/run_combined.py`;
   - Q: filas de `build_q_lt2/build_q_lt1` antes de `apply_q_patterns()` en
     `COMBINADO/src/semana03_live_load.py`;
   - EX/EY: fuerzas de piso antes de `apply_lateral()` en
     `COMBINADO/src/semana03_seismic.py`.
3. Construir un modelo OpenSees limpio y ejecutar el caso modificado. No se
   deben escalar únicamente los dibujos de Unity y presentarlos como un nuevo
   análisis.
4. Exportar fuerzas, desplazamientos, reacciones y equilibrio como un caso
   identificado con su factor.
5. Ejecutar la cadena común:

```powershell
python COMBINADO/src/exportar_unity_combinado.py
python COMBINADO/src/integrar_p1l4_unity.py
python COMBINADO/src/validar_unity_combinado.py
python COMBINADO/src/validar_unity_viewer_estatico.py
python -m pytest -q
```

6. Abrir Unity, seleccionar el caso regenerado y comprobar equilibrio,
   deformada, diagramas y P–M. Finalmente usar `RESTAURAR ESCENARIO BASE` para
   limpiar el estado local del laboratorio.

En el modelo lineal, escalar un único caso produce una respuesta proporcional,
pero el reanálisis sigue siendo obligatorio en la interfaz porque el cambio
no ha sido escrito al modelo ni auditado por el pipeline.

### 2.2 Activación/desactivación de un elemento

#### Estado en Unity

1. **Interfaz/dato.** Se selecciona una viga, columna o muro y se presiona
   `DESACTIVAR ELEMENTO SELECCIONADO`.
2. El tag se guarda en `inactiveElements` y el `GameObject` se oculta.
3. No se modifica la conectividad, la rigidez global ni el JSON; por tanto,
   los resultados anteriores dejan de ser representativos y se activa
   `REQUIERE REANÁLISIS`.
4. El mismo botón reactiva el objeto. `RESTAURAR ESCENARIO BASE` reactiva
   todos los tags y recupera la vigencia de los resultados originales.

#### Flujo manual reproducible hasta resultados nuevos

`interfaz/dato → modelo → OpenSees → resultados → Unity`:

1. Registrar el `elementTag` y su origen mediante el inspector.
2. Crear una configuración de análisis que excluya ese tag al construir el
   dominio OpenSees —o que use `ops.remove('element', tag)` antes de aplicar
   cargas—, manteniendo la fuente original sin sobrescribir.
3. Auditar las consecuencias antes de analizar:
   - conectividad de sus nodos;
   - estabilidad global y aparición de mecanismos;
   - cargas aplicadas directamente al elemento;
   - ruta o redistribución de dichas cargas.
4. Si el elemento es una viga cargada, la carga **no se reasigna por
   suposición**. Se requiere una regla tributaria explícita. Para una prueba
   sin redistribución se debe escoger un elemento sin carga directa y dejar
   documentado el alcance.
5. Ejecutar G/Q/EX/EY y combinaciones en un modelo limpio, verificar
   convergencia y equilibrio y exportar los nuevos resultados.
6. Ejecutar la cadena común de exportación, integración, validación y pruebas
   indicada en 2.1; después inspeccionar el tag y los elementos vecinos en
   Unity.

El flujo es reproducible para un operador, pero no está automatizado desde la
interfaz. Esta separación evita presentar como resultado estructural lo que
por ahora es solo una hipótesis visual.

## 3. Superposición interactiva

El modelo de esta etapa es lineal elástico. Para cada magnitud de respuesta
`R`, Unity calcula:

`R = aG·RG + aQ·RQ + aEX·REX + aEY·REY`.

La misma combinación se aplica a desplazamientos, fuerzas de extremo,
reacciones y cargas internas G/Q usadas para reconstruir los diagramas. El
punto de demanda P–M se vuelve a calcular desde las fuerzas combinadas. La
curva de capacidad no cambia porque no se modifica la sección.

Se verificaron tres estados usando la columna 113022 (`N1`, `My1`) y el
desplazamiento `Ux` del master 1004:

| Estado de sliders `(G,Q,EX,EY)` | `N1` columna 113022 [kN] | `My1` [kN·m] | `Ux` nodo 1004 [m] | Verificación |
| --- | ---: | ---: | ---: | --- |
| `(1,0,0,0)` | 1063,720949 | −0,615171 | −8,650908×10⁻⁵ | Coincide exactamente con el caso OpenSees G. |
| `(0,0,1,0)` | 1,569045 | 177,961584 | 4,516590×10⁻³ | Coincide exactamente con el caso OpenSees EX. |
| `(1,1,1,0)` | 1663,558517 | 176,860049 | 4,373433×10⁻³ | Coincide con `COMBO_R`; diferencias respecto del resultado exportado: `3×10⁻¹³ kN`, `3×10⁻¹³ kN·m` y `6×10⁻¹⁸ m`. |

Comprobación adicional de un estado no predefinido: para
`(1,2; 0,5; −0,3; 0,4)`, la suma numérica entrega
`N1=1574,912347 kN`, `My1=−50,843278 kN·m` y
`Ux1004=−1,493941×10⁻³ m`, valores que debe mostrar el laboratorio dentro de
la precisión `float` de Unity.

La superposición no sustituye un análisis cuando cambian geometría, apoyo,
material, sección o activación. Tampoco constituye por sí sola una envolvente
normativa: los coeficientes deben ser definidos y justificados por el grupo.

## 4. Sidequest carga móvil

Se implementaron dos visualizaciones relacionadas, ambas sin reanálisis.

### 4.1 Carga puntual sobre una viga seleccionada

- **Regla física de reparto equivalente:** para una carga `P` ubicada en
  `ξ=x/L`, `Pi=P(1−ξ)` y `Pj=Pξ`.
- **Panel:** permite ingresar `P [kN]`, aplicar y desplazar `x/L` entre 0 y 1.
- **Reparto:** informa las contribuciones equivalentes en los extremos I/J.
- **Conservación:** comprueba `Pi+Pj=P` y `Pj·L=P·x`; muestra errores de fuerza
  y primer momento.
- **Respuesta visual:** una flecha roja recorre la viga seleccionada.

Este reparto no son las reacciones reales del marco, una línea de influencia
ni una envolvente móvil. No modifica el JSON ni los diagramas.

### 4.2 SQ4 — carga móvil asociada al usuario

Al activar `USUARIO` aparece una persona esquemática. Puede desplazarse con
WASD, flechas o botones y cambiar entre niveles 1–4. La posición se contrasta
con los polígonos LT2 y con las franjas equivalentes LT1; el panel informa la
región, resalta en rojo las vigas receptoras y muestra la carga asignada. En
una zona compartida, la carga del usuario se divide en partes iguales entre
las vigas receptoras únicas, conservando la magnitud total ingresada.

SQ4 es una asignación visual de panel/receptor. No cambia los patrones
OpenSees, la deformada, los esfuerzos ni P–M.

## 5. UX estructural

| Pregunta | ¿La responde? | Evaluación actual |
| --- | --- | --- |
| ¿Dónde está el elemento? | **Sí** | Selección 3D, resaltado amarillo, tag, origen, nivel y nodos. Faltan búsqueda directa por tag y botón de encuadre/aislamiento. |
| ¿Cómo está apoyado? | **Parcialmente** | Capas de apoyos, masters, diafragmas y rigid links; inspector de restricciones nodales. No dibuja automáticamente la ruta completa hasta fundación. |
| ¿Qué lo carga? | **Sí, con limitaciones visibles** | Flechas, caso activo, áreas tributarias y asignación móvil. LT1 usa franja equivalente y ROOF LT2 no muestra carga porque no existe en la fuente exportada. |
| ¿Cómo se deforma? | **Sí** | Deformada por caso o superposición y escala gráfica ajustable. Las barras se representan por sus nodos extremos, no mediante una curva de desplazamiento interno. |
| ¿Qué fuerzas tiene? | **Sí** | Inspector N/V/T/M en I/J y diagramas. My es parabólico bajo `beamUniform` y por tramos bajo `beamPoint`; Mz se reconstruye por equilibrio. |
| ¿Cuánta capacidad tiene? | **Parcialmente** | P–M para columna 113022 y muro M001. No existe chequeo de capacidad para todos los elementos y los supuestos del bloque P–M deben exponerse. |

El viewer sí ayuda a localizar, relacionar cargas y observar respuesta. Sigue
siendo un postprocesador/laboratorio y no un editor estructural ni un sistema
general de diseño normativo.

## 6. Preparación móvil

**Teléfono compatible identificado:** Samsung Galaxy A54 5G como equipo de
prueba propuesto, todavía no ensayado. Su configuración documentada —Android
13 de fábrica, arquitectura de 64 bits, 6 GB de RAM y pantalla 1080×2340— es
compatible con el objetivo del proyecto: Android API 26+, ARM64 y gráficos
móviles compatibles con Unity 6.

Se creó el build móvil inicial reproducible en
`unity/LT1Viewer/Assets/Editor/AndroidBuild.cs`:

- escena `Assets/Scenes/LT1Viewer.unity`;
- identificador `cl.p0mcoc.lt1viewer`;
- API mínima 26;
- arquitectura ARM64;
- orientación horizontal;
- APK, no App Bundle;
- salida `Builds/Android/LT1Viewer-semana05.apk`;
- menú `LT1 > Build Android APK` y método batch
  `AndroidBuild.BuildFromCommandLine`.

La interfaz adapta tamaños en plataforma móvil y soporta toque corto,
órbita, pan y pinza de zoom.

**Estado verificable:** el script y la configuración inicial compilan, pero
no se declara un APK generado ni probado. El entorno local no tenía licencia
Unity activa para batch y AndroidPlayer/Android Build Support no terminó de
instalarse. Para cerrar esta parte se debe activar la licencia, instalar
Android Build Support + SDK/NDK + OpenJDK para Unity 6000.5.0f1, ejecutar el
build e instalarlo en el A54.

## 7. IA

La funcionalidad compleja desarrollada con apoyo de agente fue la
reconstrucción exacta de los diagramas de momento a partir de resultados de
OpenSees y cargas internas exportadas.

Antes, el visor interpolaba `Mi→Mj`. El agente identificó que esto era
incorrecto para elementos cargados y formuló:

`My(x)=My_i+Vz_i·x+Σ(w·x²/2)+Σ(P·max(0,x−a))`,

donde `w` representa `beamUniform` y `P,a` cada `beamPoint`. Para el otro eje
se usa `dMz/dx=−Vy`. La reconstrucción también combina las cargas G/Q con los
coeficientes de los sliders y coloca estaciones exactamente en cada `xloc`.

La verificación no se limitó a una inspección visual:

- 3.470 cierres seccionales entre los extremos I/J de los cinco casos;
- error máximo My: `1,48×10⁻¹² kN·m`;
- error máximo Mz: `4,55×10⁻¹³ kN·m`;
- error máximo Vz: `1,02×10⁻¹² kN`;
- `validar_unity_combinado.py`: 62.012 comprobaciones, 0 problemas;
- `validar_unity_viewer_estatico.py`: 28 comprobaciones, 0 problemas;
- compilación `Assembly-CSharp`: 0 errores;
- `pytest`: 162 pruebas aprobadas; dos avisos por la marca `slow`, sin fallos.

El agente también actualizó la documentación y las pruebas de la paleta para
evitar que una expectativa antigua —columnas verdes— contradijera la interfaz
solicitada —columnas grises, vigas naranjas y muros rojos—.

## Conclusión

El viewer cumple la interacción obligatoria, la superposición instantánea,
la inspección P–M acotada, dos modificaciones con aviso explícito de
reanálisis y el sidequest de carga móvil. Las modificaciones no cierran aún
el ciclo Unity→OpenSees automáticamente; el procedimiento manual queda
documentado y protege la trazabilidad. La preparación móvil dispone de código
de build y teléfono objetivo, pero la generación e instalación del APK sigue
pendiente por el entorno de Unity.
