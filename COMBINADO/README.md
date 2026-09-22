# COMBINADO — modelo estructural integrado LT1 + LT2

Este directorio contiene el modelo OpenSeesPy combinado y sus resultados para
Unity. LT1 y LT2 permanecen como fuentes separadas; la integración específica
se mantiene dentro de `COMBINADO/`.

## Estado actual

- [x] Auditoría y transformación geométrica.
- [x] Modelo FE 3D combinado: 485 nodos y 694 elementos (incluye 10 tramos V30x80 de conexión al extremo oeste).
- [x] Interfaz, apoyos, diafragmas y rigid links.
- [x] Materiales, secciones, cargas G/Q/EX/EY y `COMBO_R`.
- [x] Redistribución tributaria V30 en L1–L4, conservando área y carga total
  por piso mediante 24 correcciones firmadas V40→V30.
- [x] Resultados OpenSees verificados y exportados a Unity.
- [x] Deformada, diagramas M/N/V/T, cargas, apoyos y áreas tributarias.
- [x] Demanda–capacidad P–M para columna 113022 y muro M001.

## Directorios

- `src/`: construcción, análisis, exportación, integración P–M y validadores.
- `data/`: geometría y datos explícitos separados de la lógica del modelo.
- `outputs/`: JSON, CSV, curvas y auditorías generadas.
- `docs/`: informes de integración y trazabilidad.
- `tests/`: pruebas automáticas del modelo y del visor.

## Convenciones

- Unidades: m, kN y kPa.
- Modelo: `ops.model('basic', '-ndm', 3, '-ndf', 6)`.
- Transformación LT1 al sistema global: `X' = X + 31.250`, `Y' = -Y`,
  `Z' = Z`; LT2 conserva sus coordenadas.
- Interfaz global: plano `X = 31.250 m`.

## Flujo reproducible

```powershell
python COMBINADO/src/exportar_unity_combinado.py
python COMBINADO/src/integrar_p1l4_unity.py
python COMBINADO/src/validar_unity_combinado.py
python COMBINADO/src/validar_unity_viewer_estatico.py
python -m pytest -q
```

`integrar_p1l4_unity.py` toma el JSON de `COMBINADO/outputs/unity` como fuente
única y sincroniza una copia idéntica en
`unity/LT1Viewer/Assets/StreamingAssets`.

## Trazabilidad

Cada elemento conserva origen, tag, nodos, sección, material y ejes locales.
Unity enlaza `elementTag -> objeto -> resultados -> sección/capacidad`. Los
datos confirmados y los supuestos de la comprobación P–M quedan declarados en
`results.pm` y en `outputs/p1l4/`.
