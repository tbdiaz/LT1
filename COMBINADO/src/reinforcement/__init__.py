"""Modulo de armadura LT1/LT2: datos, mapeo a geometria y representacion.

Este paquete NO crea ni modifica elementos estructurales del modelo
OpenSeesPy combinado. La armadura se mantiene como capa de datos y
representacion 3D separada, asociada a los elementos/zonas existentes
unicamente cuando la correspondencia es segura.

Submodulos LT1:
- `lt1_reinforcement_data`: transcripcion fiel de los planos de armadura LT1.
- `lt1_geometry`: geometria del modelo LT1 (ejes, panos, muros, vigas).
- `assign_lt1_reinforcement`: resolucion de zonas y asociacion a geometria.
- `reinforcement_geometry`: generacion de barras 3D (capa separada).
- `validate_reinforcement`: checks de datos y de invariancia del modelo.

Submodulos LT2:
- `lt2_reinforcement_data`: transcripcion de fundaciones/columnas LT2.
- `lt2_geometry`: geometria LT2 (grilla, columnas, muros, losas).
- `lt2_wall_data` / `lt2_beam_data` / `lt2_stair_data`: muros, vigas y
  escaleras LT2 por elevacion/plano/parte.
- `assign_lt2_reinforcement` / `lt2_reinforcement_geometry` /
  `validate_lt2_reinforcement`: mapeo y representacion LT2.
"""

from . import (
    assign_lt1_reinforcement,
    assign_lt2_reinforcement,
    lt1_beam_data,
    lt1_geometry,
    lt1_reinforcement_data,
    lt2_beam_data,
    lt2_geometry,
    lt2_reinforcement_data,
    lt2_reinforcement_geometry,
    lt2_stair_data,
    lt2_wall_data,
    reinforcement_geometry,
    reinforcement_types,
    validate_lt2_reinforcement,
    validate_reinforcement,
)

__all__ = [
    "assign_lt1_reinforcement",
    "assign_lt2_reinforcement",
    "lt1_beam_data",
    "lt1_geometry",
    "lt1_reinforcement_data",
    "lt2_beam_data",
    "lt2_geometry",
    "lt2_reinforcement_data",
    "lt2_reinforcement_geometry",
    "lt2_stair_data",
    "lt2_wall_data",
    "reinforcement_geometry",
    "reinforcement_types",
    "validate_lt2_reinforcement",
    "validate_reinforcement",
]

# Version del dataset (se incrementa al corregir transcripciones).
REINFORCEMENT_DATASET_VERSION = "1.2.0"