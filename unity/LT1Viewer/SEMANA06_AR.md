# Semana 6 — LAB de AR basica (AR Foundation + ARKit)

Esta etapa agrega una demostracion AR independiente al visor existente. No
modifica `modelo_combinado.json`, la geometria, las cargas ni los resultados.

## Dato estructural demostrado

- Fuente unica: `Assets/StreamingAssets/modelo_combinado.json`.
- Elemento: columna LT1, `elementTag = 113011`, nodos `100303 -> 110303`.
- Caso: `COMBO_R`.
- Resultado: `P = N1 = 3557.16 kN` (el valor en pantalla se lee en runtime
  desde `results.forces.COMBO_R.113011.N1`; no esta copiado en el script).
- Imagen de referencia: `Assets/StreamingAssets/pm_column_113022.png`, nombre
  AR `LT1_AR_REFERENCE`, ancho fisico configurado de `0.20 m`.

## Relacion de coordenadas

Para un punto OpenSees `pOS = (X,Y,Z)` en metros:

1. **OpenSees -> Unity:** `u = (X, Z, -Y)`. Conserva `X`, convierte la
   vertical estructural `Z` en `Y` de Unity y lleva `Y` estructural a `-Z`.
2. **Origen local del elemento:** `q = u - uI`, donde `uI` es el nodo I. Esto
   no cambia longitud ni orientacion; solo evita usar coordenadas globales
   grandes sobre la imagen.
3. **Escala/rotacion/traslacion local:**
   `qRegistrado = t + R * (s * q)`. La escena usa inicialmente
   `s = 0.035`, `R = (0,0,0) grados` y `t = (0,0.015,0) m`.
4. **Unity -> AR:** `pAR = TImagen * qRegistrado`. `TImagen` es la matriz de
   pose (posicion y rotacion) actualizada por ARKit para `ARTrackedImage`.

El `ARTrackedImage` detectado se usa como **image anchor**: el objeto
`ARContent_ElementTag_113011` se hace hijo de su `Transform`. Por eso el
elemento sigue la pose de la imagen y se oculta si el estado deja de ser
`Tracking`.

## Crear la escena en Unity

1. Abra `unity/LT1Viewer` con Unity `6000.5.0f1` y espere a que Package
   Manager instale AR Foundation, Apple ARKit, XR Plug-in Management, XR Core
   Utilities e Input System.
2. Inicie sesion/active la licencia de Unity si el editor lo solicita.
3. Ejecute `LT1 > Semana 6 > Crear o actualizar escena AR`.
4. El comando crea:
   - `Assets/Scenes/ARStructuralDemo.unity`;
   - `Assets/AR/LT1ARReferenceLibrary.asset`;
   - `AR Session`, `XR Origin (AR)`, camara AR, image manager, anchor manager
     y el controlador de demostracion;
   - la escena AR como primera escena de Build Settings, conservando la
     escena anterior.
5. Abra `ARStructuralDemo.unity` y seleccione `Semana6_AR_OpenSees`. En el
   Inspector se pueden explicar y ajustar `Ar Scale`, `Ar Euler Degrees` y
   `Ar Translation Metres`. No cambie el tag/caso/componente salvo que primero
   verifique que existen en el JSON.
6. Para una comprobacion de escritorio, presione Play y confirme que la
   interfaz indique que espera la imagen y que Console registre los nodos,
   la conversion Unity y el resultado. La deteccion real se comprueba en el
   iPhone (o con XR Simulation si se configura un entorno simulado).

## Preparar la imagen fisica

1. Abra `Assets/StreamingAssets/pm_column_113022.png`.
2. Imprimala **sin recortar, deformar ni ajustar al papel**, a `20.0 cm` de
   ancho. La altura debe mantener la proporcion original.
3. Pegue la impresion sobre una superficie plana, rigida, mate y bien
   iluminada. Los reflejos y dobleces reducen el tracking.

Si se imprime a otro ancho, cambie `widthMetres` en
`ARStructuralDemoBuilder.cs`, vuelva a ejecutar el constructor y recompile.

## Configurar y ejecutar en iPhone

La compilacion iOS final requiere macOS, Xcode, una cuenta Apple Developer y
un iPhone compatible con ARKit.

1. En el Mac, instale desde Unity Hub la misma version del editor y el modulo
   `iOS Build Support`; copie o clone el proyecto completo.
2. Abra el proyecto y ejecute primero el constructor de escena.
3. Ejecute `LT1 > Semana 6 > Configurar proyecto para iPhone`. Configura
   identificador `cl.p0mcoc.lt1.ar`, descripcion de uso de camara, iOS 13+,
   ARM64 e intenta asignar el ARKit Loader.
4. Verifique en `Edit > Project Settings > XR Plug-in Management > iOS` que
   **Apple ARKit** este marcado y `Initialize XR on Startup` este activo.
5. En `File > Build Profiles`, seleccione iOS. Confirme que
   `Assets/Scenes/ARStructuralDemo.unity` sea la escena 0 y pulse
   `Switch Platform` y luego `Build` para generar el proyecto Xcode.
6. Abra el `.xcodeproj` generado en Xcode. En `Signing & Capabilities`, elija
   el `Team`, use un Bundle Identifier unico si el propuesto ya existe y
   deje `Automatically manage signing` activo.
7. Conecte el iPhone, confie en el Mac, seleccione el dispositivo como destino
   y pulse Run. En el iPhone autorice la camara.
8. Apunte a la impresion completa. Al entrar en `Tracking` aparece la columna
   naranja con la etiqueta `elementTag 113011`, `COMBO_R` y `P (N1)` en kN.
   Mueva el telefono: el contenido debe permanecer registrado con la pose de
   la imagen.

## Archivos de implementacion

- `Assets/Scripts/ARStructuralDemo.cs`: lectura del JSON, conversion de
  coordenadas, pose/anchor, geometria y rotulos.
- `Assets/Editor/ARStructuralDemoBuilder.cs`: escena y reference image library.
- `Assets/Editor/IOSARBuild.cs`: ajustes reproducibles de iOS y ARKit.
