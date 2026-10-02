# Semana 6 — AR visual y correspondencia estructural

Fecha de revisión: 02-10-2026

Modelo evaluado: `COMBINADO_LT1_LT2`

Dispositivo objetivo: Samsung Galaxy A05

Implementación: Unity 6000.5.0f1, `WebCamTexture`, sin ARCore

Versión base: rama `p1l4`, commit `311a4e8`

Este informe documenta la demostración final basada en la detección de una
viga real de hormigón. En el flujo abreviado solicitado, **marker** significa
la región visual de esa viga; la versión vigente no utiliza el antiguo
marcador SVG.

## 1. Flujo AR

`marker → pose → anchor → transform → elemento → resultado`

| Etapa | Implementación |
| --- | --- |
| `marker` | La cámara trasera entrega frames mediante `WebCamTexture`. El detector busca una banda de hormigón con dos bordes longitudinales aproximadamente paralelos, espesor relativamente constante, región interior continua, longitud mayor que el espesor y tamaño significativo en pantalla. |
| `pose` | Del candidato se obtienen centro, eje longitudinal, longitud, espesor, ángulo y cuatro esquinas en coordenadas normalizadas de pantalla. No es una pose 6D métrica: la profundidad se fija en `1.20 m` para render. |
| `anchor` | Tras seis frames compatibles se confirma `DetectedBeamAnchor_ElementTag_800205`. Centro, giro y escala se suavizan con `α = 0.18`. Si la detección se pierde, la última referencia se conserva durante `1.0 s`. |
| `transform` | La geometría OpenSees se convierte a ejes Unity, se centra, rota según el eje detectado, escala según la longitud visible y traslada al centro de la viga. |
| `elemento` | Se dibuja el elemento estructural real `800205`, sección `V. 60/80`, entre los nodos `130305` y `800008`. |
| `resultado` | Solo con la viga confirmada se presenta el panel de `COMBO_R`, extremo I, usando el extracto trazable `semana06_element_800205.json`. |

El teléfono ejecuta captura, detección, estabilización, anchor visual,
transformación y render. OpenSees no se ejecuta en Android: geometría,
cargas y resultados fueron calculados y exportados previamente.

## 2. Transformación

### 2.1 OpenSees a Unity

Para un punto OpenSees en metros,

\[
\mathbf p_{OS}=\begin{bmatrix}X\\Y\\Z\end{bmatrix},
\qquad
\mathbf p_U=\mathbf C\mathbf p_{OS},
\qquad
\mathbf C=
\begin{bmatrix}
1&0&0\\
0&0&1\\
0&-1&0
\end{bmatrix}.
\]

Por tanto, Unity usa `(X, Z, -Y)`: mantiene `X`, usa `Z` estructural como
vertical Unity y lleva `Y` estructural a `-Z`.

La geometría que carga la app se centra en el punto medio del elemento:

\[
\mathbf m=\frac{\mathbf C\mathbf p_I+\mathbf C\mathbf p_J}{2},
\qquad
\mathbf q=\mathbf C\mathbf p_{OS}-\mathbf m.
\]

Esto evita trasladar al anchor las coordenadas globales grandes del edificio;
no altera la longitud ni la orientación relativa del elemento.

### 2.2 Imagen a anchor visual

Sea `c=(cx,cy)` el centro detectado en coordenadas de viewport, `a` el vector
unitario de su eje longitudinal y `z0=1.20 m` la profundidad gráfica fija.
Unity evalúa:

- `tA = ViewportToWorldPoint(cx, cy, z0)`, expresado localmente respecto de la
  cámara;
- `RA = FromToRotation(ex, a)`, para alinear el eje virtual con la viga;
- `s = Ldetectada_world / 7.49`, porque `7.49 m` es la longitud del elemento
  real exportado.

La composición final puede escribirse como:

\[
\mathbf p_{world}=
\mathbf T_{camara}\,
\mathbf T_{anchor}(\mathbf t_A,\mathbf R_A)\,
\mathbf T_{local}(\mathbf t_0,\mathbf R_0)\,
\mathbf S(s)\,
\mathbf q,
\]

donde `t0=(0,0,0.015) m` evita solapamiento visual y `R0=(0,0,0)`. El anchor
es hijo de la cámara y se actualiza desde la observación; por ello es una
referencia visual equivalente, no un anchor persistente de mundo de ARCore.

## 3. Precisión

No existe todavía una medición con verdad terreno, patrón calibrado o sensor
de profundidad. En consecuencia, no se declara un error en centímetros.

La estimación simple disponible usa los límites de compatibilidad exigidos
antes de confirmar o actualizar la viga:

| Magnitud | Límite configurado | Equivalencia simple |
| --- | ---: | --- |
| Movimiento del centro | `0.055` del viewport | para 640×480: aproximadamente 35 px en X o 26 px en Y |
| Cambio angular | `8°` | diferencia máxima entre ejes de candidatos compatibles |
| Cambio de longitud | `18%` | variación relativa máxima entre candidatos compatibles |
| Confirmación | `6 frames` | evita aceptar un candidato aislado |
| Suavizado | `α=0.18` | reduce saltos, pero introduce retardo |

Estos valores son un **límite operativo de aceptación**, no el error medio
medido. Para una prueba cuantitativa futura se debe marcar manualmente en cada
frame las cuatro esquinas verdaderas de la viga y calcular:

\[
e_{px}=\sqrt{\frac{1}{4}\sum_{k=1}^{4}
\lVert\mathbf c_k^{det}-\mathbf c_k^{ref}\rVert^2}.
\]

Si se conoce una longitud física visible `Lref` y su longitud proyectada
`lpx`, una aproximación planar local es `em ≈ epx·Lref/lpx`. Debe reportarse
separadamente por distancia, iluminación y ángulo de observación.

## 4. Resultados

### 4.1 Elemento real mostrado

| Campo | Valor |
| --- | --- |
| Modelo | combinado LT1 + LT2 |
| Origen del elemento | LT1 |
| `elementTag` | `800205` |
| Tipo | `segmento_fachada` |
| Sección | `V. 60/80` |
| Nodos | `130305 → 800008` |
| Longitud | `7.49 m` |
| Caso | `COMBO_R`, extremo I |

### 4.2 Valores presentados después de detectar la viga

| Subtítulo | Valor |
| --- | ---: |
| Fuerza axial | `0.000 kN` |
| Fuerza de corte | `123.110 kN` |
| Momento flector | `-186.462 kN·m` |
| Ux | `+4.217 mm` |
| Uy | `-0.056 mm` |
| Uz | `-1.340 mm` |
| Área tributaria | `17.309 m²` |
| G | `16.770 kN/m` |
| Q | `9.244 kN/m` |
| Demanda / Capacidad | `PENDIENTE` |

### 4.3 Evidencia de correspondencia

La cadena auditable es:

`modelo_combinado.json` → `export_semana06_element.py` →
`semana06_element_800205.json` → `Semana06BeamData` →
`MarkerStructuralDemo` → `OpenSees_Element_800205` → panel.

- El exportador selecciona por `elementTag == 800205`; no por posición ni por
  un índice visual.
- El extracto conserva nodos, sección, longitud, cargas, fuerzas y
  desplazamientos de los casos reales.
- `test_semana06_ar.py` compara el extracto con el modelo completo y verifica
  `COMBO_R`, nodos, cargas, trazabilidad, escena, anchor y panel.
- La prueba de Semana 6 contiene 11 verificaciones aprobadas.
- No existe P-M para `800205`; por eso la app muestra `PENDIENTE` y no inventa
  una curva.

## 5. QA final estructural

| Prueba | Estado |
| --- | --- |
| Equilibrio G | **OK** — `analyze rc=0`; `|ΣRz-P|=1.085×10⁻⁸ kN`, error relativo `3.490×10⁻¹³`. |
| Equilibrio Q | **OK** — `analyze rc=0`; `|ΣRz-Q|=3.962×10⁻⁹ kN`, error relativo `2.154×10⁻¹³`. |
| Corte basal EX | **OK** — `8021.852135 kN`; error relativo `1.82×10⁻¹²`. |
| Corte basal EY | **OK** — `8021.852135 kN`; error relativo `9.64×10⁻¹²`. |
| Superposición | **OK** — desplazamiento, reacción y fuerza interna coinciden con la corrida explícita; error relativo máximo `5.89×10⁻¹⁵`. |
| `M-phi` | **OK con supuestos declarados** — análisis de sección ejecutado; pico documentado `1866.02 kN·m` para `P=-7500 kN`. |
| `P-M` columna | **OK con supuestos declarados** — columna `113022`; los cinco casos evaluados quedan dentro de la curva exportada. |
| `P-M` muro | **OK como verificación; EY queda FUERA** — muro físico M001 agrupado con `4001+4002`; en EY, demanda fuerte `8740.85 kN·m` frente a capacidad `4904.69 kN·m`. |
| IDs Unity | **OK** — tags sin colisiones, 694 elementos exportados y trazabilidad `elementTag → GameObject → resultados`; validador estático `28/28`. |
| AR | **OK funcional con limitación de precisión** — APK ARM64 compilada, cámara y frames activos en Galaxy A05, seis frames de confirmación y 11 pruebas de integración; falta ensayo métrico contra verdad terreno. |

Los estados P-M validan el procedimiento y su trazabilidad; no eliminan los
supuestos declarados de materiales, recubrimiento y distribución de armadura.
En particular, `OK` no significa que todas las demandas queden dentro de
capacidad: el muro M001 bajo EY queda explícitamente fuera.

## 6. Errores conocidos

1. El anchor es visual y relativo a la cámara. No conoce la ubicación global
   del teléfono ni persiste como un anchor 3D de ARCore.
2. La profundidad de render es fija (`1.20 m`); no es la distancia medida a
   la viga. La escala representa el encuadre, no una medición topográfica.
3. Durante la retención de un segundo, el anchor permanece ligado a la cámara;
   si el teléfono se mueve con la viga oculta, puede deslizarse visualmente.
4. Iluminación pobre, sombras duras, bajo contraste, perspectiva extrema y
   oclusiones extensas pueden producir falsos negativos.
5. Cielos, dinteles, muros, muebles u otras bandas grandes pueden producir
   falsos positivos si satisfacen los criterios geométricos; no existe una
   clasificación semántica de hormigón.
6. El contorno y el elemento se suavizan. Esto reduce vibración, pero agrega
   retardo cuando la cámara o el objetivo se mueven.
7. El error AR no ha sido medido con una referencia calibrada. Los valores de
   la sección 3 son umbrales de aceptación, no exactitud certificada.
8. Para `800205` solo existen fuerzas de extremos I/J; no hay estaciones
   internas exportadas para reconstruir un diagrama continuo exacto.
9. La demanda-capacidad P-M de `800205` no está disponible. Faltan datos
   indispensables de armadura asociados inequívocamente a ese elemento; se
   mantiene `PENDIENTE`.
10. La QA global conserva hipótesis ya documentadas: `Q=4.0 kPa` uniforme por
    falta de zonificación arquitectónica, coeficiente sísmico `0.20`
    provisional y supuestos de sección en los análisis P-M.
11. El modelo no aplica cargas de losa en ROOF LT2 porque no existen en la
    fuente exportada; no se inventaron.
12. La APK es un artefacto de build ignorado por Git; debe recompilarse desde
    la escena y scripts versionados para reproducirla.

## 7. Plan final

### Núcleo

- Mantener congelados `elementTag 800205`, `COMBO_R`, extremo I y los valores
  estructurales verificados.
- Ejecutar antes de la entrega el exportador liviano, las 11 pruebas de Semana
  6 y los validadores del modelo combinado.
- Recompilar e instalar la APK desde el commit de entrega.
- Realizar un ensayo completo en el lugar: permiso, cámara, diagnóstico,
  confirmación, contorno, anchor, elemento y panel.
- Registrar fotografía o video de la correspondencia entre la viga real, el
  contorno detectado, el tag y el resultado.
- Exponer en la defensa la diferencia entre coordenadas OpenSees, Unity,
  viewport y anchor visual.

### Polish

- Incorporar un modo de calibración que guarde `epx`, ángulo y error de escala
  sobre frames etiquetados.
- Mejorar legibilidad del panel para diferentes densidades de pantalla y
  validar que ninguna fila quede recortada.
- Añadir una guía breve en pantalla sobre distancia, iluminación y encuadre.
- Guardar opcionalmente una captura con fecha, tag, caso y diagnóstico para la
  evidencia de QA.
- Renombrar en una futura refactorización `MarkerStructuralDemo` a un nombre
  coherente con la detección de viga, conservando las referencias de escena.

### Honors

- Estimar pose planar calibrada con intrínsecos de cámara y una dimensión
  física confirmada de la viga, reportando incertidumbre.
- Incorporar seguimiento temporal por puntos o flujo óptico para atravesar
  oclusiones parciales sin fijar el contenido a la cámara.
- Entrenar o integrar un segmentador de elementos estructurales que distinga
  vigas de instalaciones y mobiliario, manteniendo un modo geométrico de
  respaldo.
- Construir un set de evaluación con varias vigas, iluminaciones, distancias y
  perspectivas, y reportar precisión, recall, error angular y error de
  alineamiento.
- Cerrar la curva P-M de `800205` solo si se obtienen geometría, materiales,
  recubrimiento y armadura verificables para su sección real.
