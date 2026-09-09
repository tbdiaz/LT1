# COMBINADO — Modelo integrado LT1 + LT2 (en preparación)

Este directorio corresponde al **futuro modelo estructural independiente** que
resulta de la unión de los dos modelos existentes:

| Módulo | Ubicación | Rol en el conjunto |
| --- | --- | --- |
| LT1 | `../` (raíz del repositorio) | Módulo **derecho** (este) |
| LT2 | `../LT2/` | Módulo **izquierdo** (oeste) |

Los dos modelos originales son las *fuentes*. **No se modifican**; todos los
archivos nuevos específicos de la integración se crean dentro de `COMBINADO/`.

## Estado actual (se informa en cada commit)

- [x] Estructura de carpetas creada.
- [x] Auditoría de transformación geométrica (ver `docs/`).
- [ ] Modelo FE combinado (pendiente — NO construido).
- [ ] Conexión de interfaz (equalDOF / rigidLink / diafragmas entre módulos) — pendiente.
- [ ] Unificación de materiales, muros (idealización de muro equivalente) y cargas — pendiente.
- [ ] Visualización Unity del combinado — pendiente (iría en `unity/`).

## Estructura

- `docs/` — auditorías y estudios previos a la integración.
- `scripts/` — herramientas de estudio/ensamblado del combinado (lectora de LT1/LT2).
- `outputs/` — resultados, CSV, JSON y figuras del combinado (nunca de LT1/LT2).
- `unity/` — visualización Unity del combinado (futuro).

## Convenciones comunes

- Unidades base: metros (m), kilonewtons (kN), kilopascales (kPa).
- `OpenSeesPy`, `ops.model('basic','-ndm',3,'-ndf',6)`.
- El datum vertical es coincidente entre LT1 y LT2 (verificados en la auditoría).
- La transformación aplicada a LT1 para el sistema global es:
  `X' = X + 31.250`, `Y' = -Y`, `Z' = Z` (LT2 conserva sus coordenadas).
  Interfaz global propuesta: plano vertical `X = 31.250 m`.

## Trazabilidad

Toda la información proviene de los modelos fuente:

- **LT1**: `data/geometria.py`, `data/inventario.py`, `data/secciones.py`,
  `data/cargas.py`, `data/tributacion.py`, `src/modelo_lt1.py`.
- **LT2**: `LT2/data/geometry/*.csv`, `LT2/data/sections/sections_LT2.csv`,
  `LT2/src/build_opensees_model.py`.

Ver `docs/auditoria_transformacion_geometrica.md` para el detalle de la
correspondencia de ejes, nodos de interfaz y distancias.