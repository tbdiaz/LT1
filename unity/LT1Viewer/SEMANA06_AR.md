# Semana 6 — AR visual para Samsung Galaxy A05

Esta demostración reconoce una viga real de hormigón con la cámara y registra
sobre ella el elemento estructural `800205`. No usa ARCore, marcador SVG,
giroscopio ni servicios externos.

## Tecnología

`MarkerStructuralDemo` abre la cámara trasera mediante `WebCamTexture`, conserva
su relación de aspecto y procesa continuamente el mismo frame que se muestra en
pantalla. El detector busca una banda con:

- dos bordes longitudinales aproximadamente paralelos;
- espesor relativamente constante;
- longitud claramente mayor que el espesor;
- región interior continua;
- orientación predominantemente horizontal, permitiendo perspectiva;
- tamaño significativo en la imagen.

Los candidatos pequeños y delgados, como cables, tuberías, luminarias y
bandejas, se penalizan. La detección se confirma tras seis frames compatibles,
se suaviza y conserva durante un segundo si existe una oclusión breve.

## Anchor visual y coordenadas

El objeto `DetectedBeamAnchor_ElementTag_800205` es una referencia espacial
equivalente a un anchor. Guarda el centro, dirección y longitud visual de la
viga confirmada. Es un registro monocular relativo a la imagen, no una pose 3D
global ni una localización del teléfono dentro del edificio.

La cadena de transformación es:

1. OpenSees expresa los nodos como `(X,Y,Z)` en metros.
2. Unity usa `u = (X,Z,-Y)`.
3. Se resta el nodo I para obtener coordenadas locales del elemento.
4. El centro detectado produce la traslación del anchor.
5. La dirección longitudinal produce su rotación.
6. La longitud visible dividida por `7.49 m` produce la escala dinámica.
7. Se aplica la traslación local configurada `(0,0,0.015) m` para evitar
   solapamiento visual.

Conceptualmente:

`pAR = Tanchor + Ranchor * Sanchor * pLocal`

El anchor se actualiza mediante suavizado. Si la viga desaparece durante más
de un segundo se invalida, se ocultan el elemento y sus resultados, y la app
vuelve a `Buscando viga...`.

## Datos estructurales

La app no carga el modelo completo en Android. El script
`COMBINADO/scripts/export_semana06_element.py` extrae desde
`modelo_combinado.json` solamente los datos reales de `800205` y genera:

`Assets/StreamingAssets/semana06_element_800205.json`

Trazabilidad principal:

- origen: LT1 dentro del modelo combinado LT1 + LT2;
- elemento: `800205`, tipo `segmento_fachada`;
- sección: `V. 60/80`;
- nodos: `130305 -> 800008`;
- longitud: `7.49 m`;
- caso mostrado: `COMBO_R`, extremo I.

El panel aparece solamente después de confirmar la viga y presenta:

| Subtítulo | Valor |
|---|---:|
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

No se inventa una curva P-M: el modelo exportado no contiene una verificación
demanda-capacidad para `800205`.

## Cumplimiento de Semana 6

| # | Requisito | Implementación |
|---|---|---|
| 1 | Iniciar experiencia AR | abre la cámara trasera con `WebCamTexture` |
| 2 | Detectar referencia | detecta la región rectangular de la viga real |
| 3 | Obtener pose | obtiene centro, dirección, tamaño y ángulo visual |
| 4 | Usar anchor equivalente | crea `DetectedBeamAnchor_ElementTag_800205` |
| 5 | Transformar coordenadas | aplica escala, rotación y traslación |
| 6 | Mostrar elemento real | superpone el elemento `800205` |
| 7 | Mantener `elementTag` | conserva y muestra `800205` |
| 8 | Mostrar resultado OpenSees | presenta fuerzas, desplazamientos y cargas reales de `COMBO_R` |

En el teléfono se ejecutan la cámara, detección, confirmación temporal,
suavizado, transformación y render. La geometría, cargas y resultados fueron
calculados previamente; OpenSees no se ejecuta en Android.

## Crear y revisar la escena

1. Abra `unity/LT1Viewer` con Unity `6000.5.0f1`.
2. Ejecute `LT1 > Semana 6 A05 > Crear escena viga horizontal` si necesita
   regenerarla.
3. Abra `Assets/Scenes/MarkerStructuralDemo.unity`.
4. Verifique `elementTag = 800205`, `loadCase = COMBO_R`, seis frames de
   confirmación y un segundo de retención.
5. No active ARCore para este APK.

## Generar el APK

Instale desde Unity Hub Android Build Support, SDK/NDK y OpenJDK para Unity
`6000.5.0f1`. Luego ejecute `LT1 > Semana 6 A05 > Compilar APK` o:

```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.5.0f1\Editor\Unity.exe' `
  -batchmode -quit -projectPath '<ruta>\unity\LT1Viewer' `
  -executeMethod AndroidBuild.BuildFromCommandLine `
  -logFile '<ruta>\unity\LT1Viewer\Logs\Semana06-A05-Build.log'
```

Salida: `Builds/Android/LT1-Semana06-A05.apk`.

La compilación usa Android API 26+, ARM64, IL2CPP y orientación vertical. El
APK se considera un artefacto generado y no se versiona en Git.

## Instalación y prueba

Con depuración USB habilitada:

```powershell
adb devices
adb install -r LT1-Semana06-A05.apk
```

Para probar:

1. conceda permiso de cámara;
2. apunte a una viga horizontal de hormigón bien iluminada;
3. encuadre una longitud y un espesor significativos;
4. compruebe que aumenten `frames procesados` y `candidatos encontrados`;
5. espere seis detecciones compatibles;
6. verifique el contorno, `VIGA DETECTADA`, el elemento `800205` y el panel;
7. cubra brevemente una parte de la viga para demostrar la retención del
   anchor.

No se debe imprimir ni mostrar el antiguo marcador SVG: la versión actual usa
la viga real como referencia visual.
