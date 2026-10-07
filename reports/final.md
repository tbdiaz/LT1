# Informe final — LT1

Fecha de cierre técnico: 7 de octubre de 2026  
Software verificado: Python 3.12.10, OpenSeesPy 3.8.0.0 y Unity 6000.5.0f1  
Unidades base: m, kN y kPa

## 1. Resumen

Se desarrolló un modelo estructural 3D en OpenSeesPy, manteniendo LT1 y LT2
como fuentes diferenciadas y uniéndolos mediante una interfaz explícita. El
flujo exporta geometría, cargas, restricciones y resultados verificables a un
viewer Unity. La entrega incluye análisis `G`, `Q`, `EX`, `EY` y `COMBO_R`,
deformada, diagramas, áreas tributarias, superposición lineal, capacidad P–M
acotada y una demo AR sin ARCore para el Samsung Galaxy A05.

El modelo exportado contiene 485 nodos, 694 elementos, 53 apoyos, cinco
masters, cinco diafragmas y 24 vínculos cinemáticos. Las comprobaciones finales
no detectan tags duplicados, nodos estructurales desconectados ni elementos de
longitud nula.

## 2. Edificio e idealización

La estructura se idealiza con elementos de barra para vigas y columnas y con
la representación equivalente documentada para muros. Los diafragmas rígidos
vinculan los grados de libertad de cada piso con su nodo master; los `rigid
links` son vínculos locales adicionales y no son sinónimo de diafragma. La
interfaz LT1–LT2 conserva los tags y declara conectores específicos donde la
continuidad no podía representarse compartiendo directamente un nodo.

El análisis global es lineal elástico. Las curvas de sección `M-phi` y `P-M`
son análisis no lineales separados y no convierten el modelo global en uno no
lineal.

## 3. Geometría y datos

La geometría se mantiene separada de la lógica analítica. El inventario final
es: 344 vigas, 125 columnas, 80 esquinas de muro, 50 verticales de caja, 30
vigas salientes, 25 segmentos de fachada, 10 conectores V40–muro y 30 elementos
de muro. Para el viewer se agrupan en 399 `Beam`, 175 `Column` y 120 `Wall`.

Las secciones, materiales, niveles, nodos y conectividad provienen de las
fuentes del proyecto. Los datos no legibles o ausentes no se completaron como
si fueran confirmados: cada hipótesis relevante se declara en las secciones 9,
11 y 19.

## 4. Cargas gravitacionales y áreas tributarias

El caso `G` se arma a partir del peso y las cargas permanentes implementadas en
los builders LT1/LT2. Su resultante vertical es `31 086.259667 kN`. Se exportan
27 306 registros de carga G.

LT2 conserva 344 polígonos/registros tributarios exportados (incluidas 24
correcciones V30 firmadas); LT1 aporta 108 registros. Cuando la fuente LT1 no
contiene el polígono, Unity muestra una franja equivalente de ancho `A/L`, sin
presentarla como geometría medida. La redistribución V30 conserva área y carga
total por piso.

## 5. Carga viva

El caso `Q` produce una resultante vertical de `18 392.912256 kN` y exporta
27 306 registros. Se utilizó `Q = 4.0 kPa` uniforme como hipótesis conservadora
porque no estaba disponible una zonificación arquitectónica completa. Este
valor debe sustituirse si se entrega la clasificación de uso por recinto. Las
vigas `ROOF` de LT2 sin carga Q en la fuente no reciben una carga inventada.

## 6. Sismo pseudoestático

`EX` y `EY` aplican fuerzas laterales por nivel en las dos direcciones globales.
La resultante de referencia es `8 021.852135 kN` en cada dirección. El
coeficiente sísmico `0.20` y la fracción de masa viva de `50 %` son
provisionales y están declarados como tales; no constituyen un diseño sísmico
normativo final.

## 7. Superposición

La combinación implementada es:

`COMBO_R = 1.0 G + 1.0 Q + 1.0 EX + 0.0 EY`.

Se comparó una corrida directa de la combinación con la suma de corridas
independientes en seis desplazamientos del master 1005, seis reacciones del
apoyo 1 y doce fuerzas del elemento 3001. Los errores relativos máximos fueron
`5.89×10⁻15`, `3.06×10⁻15` y `3.66×10⁻16`, respectivamente, bajo tolerancia
`10⁻6`. Es una verificación representativa, no una comparación exhaustiva de
cada grado de libertad.

## 8. Análisis global y verificaciones

Cada caso se construye en un dominio OpenSees limpio. Los cierres obtenidos al
regenerar la entrega son:

| Caso | Resultante | Error relativo de equilibrio |
|---|---:|---:|
| G vertical | 31 086.259667 kN | 3.491×10⁻13 |
| Q vertical | 18 392.912256 kN | 3.918×10⁻13 |
| EX lateral | 8 021.852135 kN | 8.496×10⁻13 |
| EY lateral | 8 021.852135 kN | 1.037×10⁻11 |
| COMBO_R vertical | 49 479.171923 kN | 5.700×10⁻13 |
| COMBO_R lateral X | 8 021.852135 kN | 1.341×10⁻13 |

También se verificaron 3 470 cierres de diagramas seccionales: error máximo
`ΔMy=1.48×10⁻12`, `ΔMz=4.55×10⁻13` y `ΔVz=1.02×10⁻12`.

## 9. Fiber Sections

La sección de capacidad de columna representativa es `P.70×70`, con 16 barras
Φ22 y área total `0.006082 m²`. Se usaron fibras de hormigón y acero con
`Concrete01` y `Steel01`. `f'c=35 MPa`, `fy=420 MPa` y `Es=200 GPa` fueron
confirmados para este estudio. La distancia de `0.04 m` al eje de barras, la
distribución simétrica y parámetros constitutivos no contenidos en planos son
supuestos explícitos; por ello el resultado es una comprobación académica de
sección, no un certificado de diseño.

## 10. `M-phi`

El ensayo mantiene carga axial constante y aplica curvatura mediante
`DisplacementControl`; el factor de carga entrega el momento. Los máximos de la
rama ascendente son:

| P [kN] | M máximo [kN·m] |
|---:|---:|
| −10 000 | 1 710.40 |
| −7 500 | 1 866.02 |
| −5 000 | 1 783.56 |
| −2 500 | 1 435.44 |
| 0 | 922.26 |

La compresión pura calculada es `P0 = −19 582.85 kN`.

## 11. `P-M` columna y muro

La columna verificada es `113022`, sección `P.70×70`, armadura 16Φ22. El muro
físico `M001` agrupa los tags `4001 + 4002`, espesor confirmado `0.60 m` y
longitud geométrica `2.92 m`. Para el muro, la malla doble 12@20 está indicada
en plano, pero la asignación completa de acero de borde por nivel no era
legible; se utilizó la hipótesis conservadora documentada en
`COMBINADO/outputs/p1l4/resumen_p1l4_pm.md`.

Las curvas son capacidades nominales de sección, sin factor `φ`. No se
generaron curvas para elementos cuya armadura no está documentada.

## 12. Demanda-capacidad

En `COMBO_R`, la columna 113022 tiene `N=1 663.58 kN`, demanda resultante
`M=177.78 kN·m` y capacidad interpolada `1 168.98 kN·m`: queda dentro. El muro
M001 tiene demanda fuerte `919.82 kN·m` frente a `6 056.68 kN·m` y demanda
débil `462.14 kN·m` frente a `1 713.09 kN·m`: queda dentro.

La excepción crítica es M001 bajo `EY`: demanda en eje fuerte
`8 740.85 kN·m` frente a capacidad nominal `4 904.69 kN·m`, por lo que queda
fuera. Esta conclusión depende de los supuestos de armadura señalados y exige
revisión de planos/diseño antes de una conclusión profesional.

## 13. Unity como pre/postprocesador

Unity lee `modelo_combinado.json`, genera los objetos por `elementTag` y
permite consultar geometría, sección, ejes locales, restricciones, cargas,
desplazamientos, fuerzas y capacidad disponible. El programa es un
postprocesador de resultados y un editor de escenarios. No reemplaza el solver:
si cambia rigidez, topología, apoyo o carga, muestra `REQUIERE REANÁLISIS`.

## 14. Visualización de apoyos, cargas, ejes y diagramas

El viewer muestra 53 apoyos, masters, diafragmas y vínculos rígidos; flechas de
G/Q y EX/EY; ejes globales y locales; áreas tributarias; deformada con factor
gráfico; y diagramas `N`, `Vy`, `Vz`, `T`, `My` y `Mz`. Los diagramas usan las
fuerzas de extremo OpenSees y las cargas de miembro exportadas. La escala de
visualización no cambia los valores físicos.

## 15. Modificación del modelo

La interfaz permite cambiar un factor de carga o desactivar visualmente un
elemento para formular un escenario. El flujo correcto es registrar el cambio,
editar la fuente correspondiente, reconstruir un dominio OpenSees limpio,
ejecutar, verificar equilibrio y reexportar. Los resultados originales no se
presentan como válidos para una geometría o rigidez modificada.

## 16. AR

La demo móvil usa `WebCamTexture`, sin ARCore, para compatibilidad con Galaxy
A05. Procesa los frames de la cámara trasera, busca dos bordes longitudinales
aproximadamente paralelos que definan una viga de espesor estable, exige seis
frames compatibles, suaviza pose/tamaño/giro (`α=0.18`) y conserva la última
referencia durante `1.0 s` ante oclusiones breves.

El flujo es `viga detectada → pose 2D → anchor equivalente a 1.20 m → escala,
rotación y traslación → elemento 800205 → resultado`. La conversión base es
OpenSees `(X,Y,Z)` a Unity `(X,Z,−Y)`. Sobre la viga se registra el elemento
real `800205`, sección `V.60/80`, nodos `130305–800008`, con resultados
`COMBO_R` del extremo I. El análisis no corre en el teléfono: el APK consume un
extracto estructural previamente verificado.

Resultados visibles: `N=0.000 kN`, `V=123.110 kN`, `M=−186.462 kN·m`,
`Ux=+4.217 mm`, `Uy=−0.056 mm`, `Uz=−1.340 mm`, área tributaria
`17.309 m²`, `G=16.770 kN/m` y `Q=9.244 kN/m`. P–M se presenta como
`PENDIENTE`; no se inventó armadura para 800205.

## 17. Sidequests implementados

- Superposición interactiva de casos lineales en Unity.
- Carga móvil y asignación visual a receptores tributarios.
- Modificación de escenarios con aviso obligatorio de reanálisis.
- Losas y cierres estéticos separados de la fuente estructural.
- Demo móvil de viga real, diagrama My, deformada nodal ×100 y banda
  tributaria equivalente.

## 18. QA y tests

| Prueba | Estado final |
|---|---|
| Equilibrio G | OK |
| Equilibrio Q | OK |
| Corte basal EX | OK |
| Corte basal EY | OK |
| Superposición | OK, tres estados representativos |
| `M-phi` | OK con supuestos declarados |
| `P-M` columna | OK con supuestos declarados |
| `P-M` muro | OK como cálculo; M001/EY fuera |
| IDs Unity | OK, 694 elementos trazables |
| AR | Funcional en Galaxy A05; precisión métrica pendiente |

Los comandos reproducibles se incluyen en el README. Los validadores revisan
inventario, esquema JSON/C#, equilibrio de diagramas, sincronización de P–M,
fuentes Unity y comportamiento de Semana 6/7.

El producto ejecutable entregado es `LT1-Semana06-A05.apk`, de
`26 625 675 bytes`, SHA-256
`107B56BB8A99D9F9754FEAC47E26242D700DF9F7BAD7BBE7763B648D9A613066`.
Fue previamente instalado y probado en el Galaxy A05. En el cierre se verificó
el código y el artefacto existente; una recompilación aislada no pudo terminar
mientras otra instancia de Unity mantenía abierto el proyecto, limitación
operacional cubierta por el comando de compilación reproducible del README.

## 19. Limitaciones

1. `Q=4.0 kPa`, coeficiente sísmico `0.20` y 50 % de masa viva son hipótesis
   provisionales por falta de datos normativos/arquitectónicos completos.
2. Los conectores V40–muro usan propiedades muy rígidas asumidas y declaradas.
3. La sección `VI15xVAR=(0.15,1.20)` es una aproximación documentada.
4. Permanecen sin modelar elementos metálicos sin `E`, secciones variables sin
   definición suficiente, detalles superiores de núcleo y áreas subterráneas
   de muro sin geometría verificable.
5. La deformada de barras interpola nodos extremos; no contiene desplazamientos
   internos de una discretización de fibra.
6. P–M solo existe para 113022 y M001, es nominal y contiene supuestos de
   recubrimiento/disposición de acero.
7. Unity no reanaliza OpenSees en vivo.
8. La AR usa visión monocular y profundidad fija; no entrega localización
   métrica del teléfono ni persistencia espacial entre sesiones.
9. El detector de viga puede verse afectado por perspectiva, iluminación,
   textura y oclusiones; falta contrastarlo con verdad terreno.
10. El área AR de 800205 es una banda equivalente porque la fuente LT1 no
    contiene el polígono completo.

## 20. Uso de IA

### Tareas delegadas

Se delegaron al agente de IA la inspección del repositorio, generación y
refactor de scripts, integración OpenSees–JSON–Unity, diagnóstico de cámara y
selección móvil, creación de pruebas, ejecución de validadores, documentación y
automatización de compilación. Las decisiones estructurales y la aceptación de
supuestos permanecen bajo responsabilidad del equipo.

### Errores detectados y corregidos

- inicialización, orientación y render de `WebCamTexture` en Android;
- carga bloqueada del JSON completo en móvil, reemplazada por extracto trazable;
- detector desconectado de la textura activa;
- raycast/selección de elementos en Unity;
- regresión que ofrecía P–M para elementos no verificados;
- referencia visual a `modelo_lt1.json` confundida por el validador con fuente
  estructural, ahora distinguida y comprobada;
- estados de carga indefinidos reemplazados por diagnósticos finitos.

### Verificaciones y contribución real

El agente ejecutó el análisis, comparó equilibrio, comprobó superposición,
validó inventarios/tags, sincronizó resultados y produjo código, tests,
documentación y APK. No sustituyó datos faltantes con resultados ficticios: los
vacíos de armadura, materiales o geometría se marcan como supuestos o
pendientes. La revisión final de planos, criterios normativos y conclusiones de
diseño corresponde a los estudiantes y al docente.

## 21. Contribución individual

El historial Git identifica a **Natalia Godoy** como autora de la integración
registrada. Antes de entregar, cada integrante adicional debe completar una
fila propia; no se infieren contribuciones que no estén documentadas.

| Estudiante | Contribuciones | Módulo revisado | Error detectado | Concepto aprendido |
|---|---|---|---|---|
| Natalia Godoy | Integración y validación del modelo; viewer Unity; demo AR; documentación | OpenSees combinado, Unity/Android y QA | Bloqueos de cámara/datos y pérdida de selección/P–M | Trazabilidad `elementTag`, equilibrio, transforms y anchors |
| **[Completar si existe otro integrante]** | **[Completar]** | **[Completar]** | **[Completar]** | **[Completar]** |

## 22. Honors Track

Se implementó parcialmente H3 — AR estructural avanzada: diagrama `My`
reconstruido con cierre menor que `1×10⁻9 kN·m`, deformada nodal ×100 y área
tributaria equivalente sobre el elemento 800205. Es funcional en condiciones
controladas, pero no incluye selección de varios elementos ni P–M de 800205.

H1 (Cardboard VR), H4 (reanálisis OpenSees en vivo) y H5 (capacidad avanzada)
no están implementados. H2 aporta estabilidad temporal del anchor, pero no
incluye múltiples markers ni persistencia entre sesiones; por tanto no se
declara completo. El detalle y sus tests están en `03_HONORS_TRACK.md`.
