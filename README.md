# LT1 — modelo estructural, visor Unity y AR

Entrega final reproducible del modelo tridimensional OpenSeesPy LT1 integrado
con LT2, su postproceso en Unity y la demostración AR para Samsung Galaxy A05.
Las unidades estructurales base son metros, kilonewtons y kilopascales.

## Versiones verificadas

| Componente | Versión |
|---|---:|
| Python | 3.12.10 |
| OpenSeesPy | 3.8.0.0 (OpenSees 3.8.0) |
| Unity | 6000.5.0f1 |
| Plataforma móvil | Android ARM64, API mínima 26 |

Las dependencias Python fijadas están en `requirements.txt`. Unity requiere el
módulo **Android Build Support**, incluido SDK, NDK y OpenJDK.

## Preparación

Desde PowerShell, en la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Los planos y archivos fuente no deben reinterpretarse automáticamente. Antes
de editar geometría, secciones, apoyos o cargas, revise su procedencia y los
supuestos declarados en el informe final.

## Ejecutar el análisis y generar resultados

El exportador construye dominios OpenSees independientes para `G`, `Q`, `EX`,
`EY` y `COMBO_R`, ejecuta el análisis y escribe el JSON consumido por Unity:

```powershell
python .\COMBINADO\src\exportar_unity_combinado.py
```

Para regenerar las verificaciones de capacidad disponibles y sincronizarlas:

```powershell
python .\COMBINADO\src\semana03_capacity.py
python .\COMBINADO\src\p1l4_pm.py
python .\COMBINADO\src\integrar_p1l4_unity.py
```

El resultado principal queda en
`COMBINADO/outputs/unity/modelo_combinado.json` y se copia a
`unity/LT1Viewer/Assets/StreamingAssets/modelo_combinado.json`.

Si se modifican las fuentes LT1 o LT2, regenere primero sus insumos y luego el
exportador combinado. No basta con cambiar el dibujo en Unity: un cambio de
sección, apoyo, carga o elemento exige un nuevo análisis OpenSees.

## Abrir el viewer

1. Abra Unity Hub y agregue `unity/LT1Viewer` como proyecto.
2. Use Unity `6000.5.0f1`.
3. Abra `Assets/Scenes/LT1Viewer.unity`.
4. Presione **Play**.
5. Seleccione elementos con clic o toque y use el panel para cambiar caso,
   deformada, esfuerzos, cargas, áreas tributarias y P–M disponible.

El viewer enlaza siempre `elementTag → GameObject → resultados`. El P–M está
limitado a la columna `113022` y al muro físico `M001` (`4001 + 4002`).

## Compilar la aplicación Android

Con Unity cerrado, desde PowerShell:

```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.5.0f1\Editor\Unity.exe' `
  -batchmode -quit `
  -projectPath "$PWD\unity\LT1Viewer" `
  -executeMethod AndroidBuild.BuildFromCommandLine `
  -logFile "$PWD\unity\LT1Viewer\Builds\Android\build.log"
```

Producto generado:
`unity/LT1Viewer/Builds/Android/LT1-Semana06-A05.apk`.

Artefacto disponible al cierre: `26 625 675 bytes`, SHA-256
`107B56BB8A99D9F9754FEAC47E26242D700DF9F7BAD7BBE7763B648D9A613066`.

Instalación por USB, con depuración USB habilitada:

```powershell
adb install -r .\unity\LT1Viewer\Builds\Android\LT1-Semana06-A05.apk
```

También puede copiarse el APK al teléfono, abrirlo y autorizar la instalación
desde esa fuente. Al primer inicio se debe conceder permiso de cámara. La demo
no requiere ARCore: usa `WebCamTexture` y detección visual de una viga real.

## Ejecutar validaciones y tests

```powershell
python .\COMBINADO\src\validar_unity_combinado.py
python .\COMBINADO\src\validar_unity_viewer_estatico.py
python -m pytest -q
```

La entrega solo debe etiquetarse si los validadores y `pytest` terminan sin
errores. El detalle técnico, resultados y limitaciones está en
[`reports/final.md`](reports/final.md).
