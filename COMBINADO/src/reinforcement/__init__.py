"""Modulo de armadura LT1: datos, mapeo a geometria y representacion.

Este paquete NO crea ni modifica elementos estructurales del modelo
OpenSeesPy combinado. La armadura se mantiene como capa de datos y
representacion 3D separada, asociada a los elementos/zonas LT1 existentes
unicamente cuando la correspondencia es segura.

Submodulos:
- `lt1_reinforcement_data`: transcripcion fiel de los planos de armadura LT1.
- `lt1_geometry`: geometria del modelo LT1 (ejes, panos, muros, vigas).
- `assign_lt1_reinforcement`: resolucion de zonas y asociacion a geometria.
- `reinforcement_geometry`: generacion de barras 3D (capa separada).
- `validate_reinforcement`: checks de datos y de invariancia del modelo.
"""

from . import (
    assign_lt1_reinforcement,
    lt1_beam_data,
    lt1_geometry,
    lt1_reinforcement_data,
    reinforcement_geometry,
    reinforcement_types,
    validate_reinforcement,
)

__all__ = [
    "assign_lt1_reinforcement",
    "lt1_beam_data",
    "lt1_geometry",
    "lt1_reinforcement_data",
    "reinforcement_geometry",
    "reinforcement_types",
    "validate_reinforcement",
]

# Version del dataset (se incrementa al corregir transcripciones).
REINFORCEMENT_DATASET_VERSION = "1.1.0"