"""Tipos base del módulo de armadura LT1.

Este módulo define los estados de confianza, clasificaciones y las
estructuras de datos utilizadas para representar la armadura levantada
desde los planos (sin reinterpretar).

Reglas del proyecto:
- No inventar geometria, dimensiones, niveles, secciones, materiales,
  cargas ni condiciones de apoyo.
- Toda la informacion estructural proviene de los planos entregados.
- Este modulo NO crea elementos estructurales de OpenSeesPy: la armadura
  es una capa de representacion/verificacion separada del modelo FE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Status(str, Enum):
    """Estado de confianza de una regla de armadura.

    - EXACT: zona puntual confirmada en el plano y mapeada sin ambiguedad.
    - TYPICAL: patron tipico/repetitivo aplicado a un tipo de elemento.
    - REPRESENTATIVE: familia representativa; NO aplicada a todos los
      elementos (ej. vigas).
    - NEEDS_EXACT_ZONE_MAPPING: la zona del plano no pudo mapearse
      exactamente al modelo (ej. ejes fuera del modelo, bandas sin ancho).
    - NEEDS_NOTATION_CONFIRMATION: la nomenclatura del plano requiere
      confirmacion antes de interpretarse (ej. estribos vs malla,
      abreviaturas de muros).
    - DETAIL_FROM_DRAWING_REQUIRED: el detalle debe tomarse del plano,
      no se inventa (ej. escaleras).
    """

    EXACT = "EXACT"
    TYPICAL = "TYPICAL"
    REPRESENTATIVE = "REPRESENTATIVE"
    SUPERSEDED_BY_EXACT_BEAM_DRAWINGS = "SUPERSEDED_BY_EXACT_BEAM_DRAWINGS"
    NEEDS_EXACT_ZONE_MAPPING = "NEEDS_EXACT_ZONE_MAPPING"
    NEEDS_NOTATION_CONFIRMATION = "NEEDS_NOTATION_CONFIRMATION"
    NEEDS_DRAWING_VALUE_CONFIRMATION = "NEEDS_DRAWING_VALUE_CONFIRMATION"
    DETAIL_FROM_DRAWING_REQUIRED = "DETAIL_FROM_DRAWING_REQUIRED"


class Layer(str, Enum):
    """Capa de la losa dentro del patron de armadura (malla)."""

    LOWER = "lower"
    UPPER = "upper"
    BOTH = "both"


class Direction(str, Enum):
    """Direccion de las barras dentro de la capa o zona."""

    X = "X"
    Y = "Y"
    BOTH = "BOTH"
    LOCAL = "LOCAL"


class Classification(str, Enum):
    """Clasificacion de cada regla segun el plano."""

    MESH = "MESH"              # malla/asielo de losa (mat tanto superior como inferior)
    LOCAL = "LOCAL"            # refuerzo local (adicional, no reemplaza la malla)
    WALL = "WALL"              # armadura de muro (serie 300)
    BEAM_LONGITUDINAL = "BEAM_LONGITUDINAL"
    BEAM_STIRRUP = "BEAM_STIRRUP"
    BEAM_REPRESENTATIVE = "BEAM_REPRESENTATIVE"
    BEAM_FOUNDATION = "BEAM_FOUNDATION"        # vigas de fundacion VF (plano 402)
    STAIR = "STAIR"            # escaleras (serie 500)
    STIRRUP = "STIRRUP"        # estribo identificado en plano (no reinterpretar)
    COLUMN = "COLUMN"          # columna LT1 (armadura longitudinal)


class BeamBarLayer(str, Enum):
    """Capa longitudinal de una barra de viga segun su funcion.

    - TOP_BASE: armadura base superior (F').
    - TOP_ADDITIONAL: refuerzo superior adicional (+F').
    - BOTTOM_BASE: armadura base inferior (F).
    - BOTTOM_ADDITIONAL: refuerzo inferior adicional (+F).
    """

    TOP_BASE = "TOP_BASE"
    TOP_ADDITIONAL = "TOP_ADDITIONAL"
    BOTTOM_BASE = "BOTTOM_BASE"
    BOTTOM_ADDITIONAL = "BOTTOM_ADDITIONAL"


class BeamKind(str, Enum):
    """Clasificacion tipologica de una viga segun el plano.

    - CONTINUOUS: viga continua entre 3 apoyos (ej. 3-2-1).
    - SINGLE_SPAN: viga de un vano.
    - SPECIAL: viga corta/especial con armadura propia.
    - FOUNDATION_BEAM: viga de fundacion (serie VF del plano 402).
    - SMALL_SPECIAL_BEAM: viga corta con detalles propios (ej. V114).
    """

    CONTINUOUS = "CONTINUOUS"
    SINGLE_SPAN = "SINGLE_SPAN"
    SPECIAL = "SPECIAL"
    FOUNDATION_BEAM = "FOUNDATION_BEAM"
    SMALL_SPECIAL_BEAM = "SMALL_SPECIAL_BEAM"


class ColumnBarType(str, Enum):
    """Tipo de armadura en columnas segun su funcion longitudinal.

    - LONGITUDINAL: barras longitudinales de la columna (ej. 16 B22).
    """

    LONGITUDINAL = "LONGITUDINAL"


class ZoneKind(str, Enum):
    """Tipo de zona asociada a una regla.

    - GENERAL: se aplica a toda la losa del nivel / family completa.
    - RECT: rectangulo delimitado por dos pares de ejes (ej. E-F / 1-2).
    - BAND: franja a lo largo de un eje (ej. Eje I).
    - FREE_TEXT: zona descrita por texto libre del plano (ej. "bajo eje 3").
    """

    GENERAL = "GENERAL"
    RECT = "RECT"
    BAND = "BAND"
    FREE_TEXT = "FREE_TEXT"


@dataclass
class RuleId:
    """Identificador trazable de una regla."""

    building: str          # "LT1" (extensible: "LT2")
    drawing: str           # nombre del plano, ej. "2017_67-200-I-Model"
    sheet: str             # ej. "200-I"
    seq: int               # secuencia dentro del plano (1, 2, ...)

    @property
    def code(self) -> str:
        return f"{self.building}:{self.sheet}:{self.seq:02d}"

    def __str__(self) -> str:
        return self.code


@dataclass
class Zone:
    """Zona textual y (si se resolvio) geometrica en coordenadas LT1.

    - ``x`` e ``y`` se dan en metros y en el sistema de ejes LT1 nativo
      que define `lt1_geometry.EJES_X` / `EJES_Y`.
    - ``resolved`` es True solo cuando todos los ejes nombrados existen
      en el modelo y el rectangulo puede construirse sin ambiguedad.
    """

    kind: ZoneKind
    text: str                       # texto literal de la zona del plano, ej. "E-F / 1-2"
    rect: Optional[Tuple[float, float, float, float]] = None   # (x1, x2, y1, y2) en ejes LT1
    axis: Optional[str] = None      # eje para bandas/franjas (ej. "I")
    pano_ids: List[str] = field(default_factory=list)  # ids de panos del modelo que coinciden
    note: str = ""                  # notas de resolucion propias de esta zona

    @property
    def resolved(self) -> bool:
        return self.rect is not None


class Resolution(str, Enum):
    """Como se resolvio el mapeo de la regla."""

    RESOLVED = "RESOLVED"                         # geometria completa y asignada
    RESOLVED_METADATA = "RESOLVED_METADATA"       # asignada solo como metadata (sin geometria)
    UNRESOLVED = "UNRESOLVED"                     # zona no localizable en el modelo
    PARTIAL = "PARTIAL"                           # eje/rectangulo parcialmente identificable


@dataclass
class MeshRule:
    """Regla de malla de losa (serie 200-205)."""

    id: RuleId
    layer: Layer
    direction: Direction
    zone: Zone
    diameter_mm: int
    spacing_cm: int
    classification: Classification = Classification.MESH
    status: Status = Status.EXACT
    floor: str = ""                # nivel/plano textual, ej. "LOSA CIELO 1 PISO"
    length_cm: Optional[int] = None
    note: str = ""
    resolution: Resolution = Resolution.RESOLVED

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "floor": self.floor,
            "layer": self.layer.value,
            "direction": self.direction.value,
            "zone_text": self.zone.text,
            "zone_kind": self.zone.kind.value,
            "x1_m": self.zone.rect[0] if self.zone.rect else None,
            "x2_m": self.zone.rect[1] if self.zone.rect else None,
            "y1_m": self.zone.rect[2] if self.zone.rect else None,
            "y2_m": self.zone.rect[3] if self.zone.rect else None,
            "axis": self.zone.axis,
            "pano_ids": ";".join(self.zone.pano_ids),
            "diameter_mm": self.diameter_mm,
            "spacing_cm": self.spacing_cm,
            "length_cm": self.length_cm,
            "classification": self.classification.value,
            "status": self.status.value,
            "resolution": self.resolution.value,
            "note": self.note,
        }


@dataclass
class LocalBarRule:
    """Refuerzo local sobre una zona (no reemplaza la malla)."""

    id: RuleId
    direction: Direction
    zone: Zone
    bar_count: Optional[int]
    diameter_mm: int
    classification: Classification = Classification.LOCAL
    status: Status = Status.EXACT
    floor: str = ""
    length_cm: Optional[int] = None
    spacing_cm: Optional[int] = None
    note: str = ""
    resolution: Resolution = Resolution.RESOLVED

    def to_dict(self) -> Dict[str, object]:
        d = self._base_dict()
        d.update({
            "bar_count": self.bar_count,
            "diameter_mm": self.diameter_mm,
            "spacing_cm": self.spacing_cm,
            "length_cm": self.length_cm,
        })
        return d

    def _base_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "floor": self.floor,
            "direction": self.direction.value,
            "zone_text": self.zone.text,
            "zone_kind": self.zone.kind.value,
            "x1_m": self.zone.rect[0] if self.zone.rect else None,
            "x2_m": self.zone.rect[1] if self.zone.rect else None,
            "y1_m": self.zone.rect[2] if self.zone.rect else None,
            "y2_m": self.zone.rect[3] if self.zone.rect else None,
            "axis": self.zone.axis,
            "pano_ids": ";".join(self.zone.pano_ids),
            "classification": self.classification.value,
            "status": self.status.value,
            "resolution": self.resolution.value,
            "note": self.note,
        }


@dataclass
class WallRule:
    """Familia tipica de armadura de muro (serie 300).

    Conserva la nomenclatura EXACTA del plano y la aplica como patron
    tipico a todos los muros LT1 del modelo.
    """

    id: RuleId
    zone: Zone
    notation: str                        # nomenclatura literal, ej. "E + 6T B10@10"
    status: Status = Status.TYPICAL
    note: str = ""
    resolution: Resolution = Resolution.RESOLVED

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "zone_text": self.zone.text,
            "notation": self.notation,
            "status": self.status.value,
            "resolution": self.resolution.value,
            "note": self.note,
        }


@dataclass
class BeamRule:
    """Informacion de armadura de viga proveniente del plano.

    Las vigas en el plano LT1 se reportan como familia REPRESENTATIVE
    (V.80/80). Esta tabla NO se asigna barra a barra a los elementos.
    """

    id: RuleId
    zone: Zone
    family: str                       # ej. "V.80/80"
    longitudinal_mm: str              # ej. "2 B22"
    stirrup_notation: str             # ej. "ED B10@10 / ED B10@20"
    status: Status = Status.REPRESENTATIVE
    note: str = ""
    resolution: Resolution = Resolution.RESOLVED_METADATA

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "zone_text": self.zone.text,
            "family": self.family,
            "longitudinal": self.longitudinal_mm,
            "stirrups": self.stirrup_notation,
            "status": self.status.value,
            "resolution": self.resolution.value,
            "note": self.note,
        }


@dataclass
class StairRule:
    """Metadata de armadura de escaleras (serie 500).

    No se inventan diametros ni espaciamientos: requieren detalle del
    dibujo. Sin elementos estructurales de escalera en el modelo LT1,
    solo se registra la existencia y categoria.
    """

    id: RuleId
    zone: Zone
    status: Status = Status.DETAIL_FROM_DRAWING_REQUIRED
    note: str = ""
    resolution: Resolution = Resolution.UNRESOLVED

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "zone_text": self.zone.text,
            "status": self.status.value,
            "resolution": self.resolution.value,
            "note": self.note,
        }


@dataclass
class ColumnReinforcementRule:
    """Armadura de columna LT1 (ej. longitudinal 16 B22).

    Representa la armadura LONGITUDINAL declarada para TODAS las columnas
    LT1. No se inventan estribos, recubrimientos ni la distribucion exacta
    de las 16 barras en la seccion: se registra como metadata y se asocia
    a los tags de las columnas del modelo cuando el mapeo es inequivoco.

    - ``bar_type``: longitud de las barras (LONGITUDINAL).
    - ``source``: procedencia del dato (ej. "USER_CONFIRMED_DRAWING_DATA").
    - ``geometry_pending``: si la posicion fisica transversal requiere
      recubrimiento/geometria no confirmada, se conserva metadata y la
      geometria 3D queda pendiente (True).
    """

    id: RuleId
    bar_count: int
    diameter_mm: int
    bar_type: ColumnBarType = ColumnBarType.LONGITUDINAL
    section: str = ""
    classification: Classification = Classification.COLUMN
    status: Status = Status.EXACT
    source: str = "USER_CONFIRMED_DRAWING_DATA"
    column_tags: List[int] = field(default_factory=list)
    resolution: Resolution = Resolution.RESOLVED
    geometry_pending: bool = True
    note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "section": self.section,
            "bar_type": self.bar_type.value,
            "bar_count": self.bar_count,
            "diameter_mm": self.diameter_mm,
            "classification": self.classification.value,
            "status": self.status.value,
            "source": self.source,
            "column_tags": ";".join(str(t) for t in self.column_tags),
            "n_columns": len(self.column_tags),
            "resolution": self.resolution.value,
            "geometry_pending": self.geometry_pending,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# Armadura de vigas (planos 400/401/402): datos por barra y estribado
# ---------------------------------------------------------------------------
BeamAxis = Optional[Tuple[str, str]]   # (eje_inicio, eje_fin) ej. ("3", "2")


@dataclass
class BeamRebarSegment:
    """Una barra/refuerzo longitudinal de viga a lo largo de un tramo.

    No corta la barra en los limites de ``beam_ids``: la lista puede
    contener mas de un elementTag/beam cuando la barra cruza un apoyo
    (ej. V100-V101). Solo se considera geometrico cuando el eje fisico
    de la viga existe en el modelo.
    """

    id: RuleId
    beam_ids: List[str]                  # beam ids (plan) o elementTags del modelo
    physical_bar_id: str                 # id fisico de la barra (ej. "V100-F'-2")
    bar_layer: BeamBarLayer              # TOP_BASE/TOP_ADDITIONAL/BOTTOM_BASE/BOTTOM_ADDITIONAL
    bar_count: Optional[int]             # numero de barras (2, 4, ...); None si no legible
    diameter_mm: int                     # diametro en mm
    length_cm: Optional[int] = None      # L dibujada (cm); None si no legible
    start_axis: Optional[str] = None     # eje inicio del tramo (plano)
    end_axis: Optional[str] = None       # eje fin del tramo (plano)
    start_station_cm: Optional[float] = None   # progresiva inicio (cm), si el plano la da
    end_station_cm: Optional[float] = None     # progresiva fin (cm)
    anchor_left_cm: Optional[float] = None     # anclaje/prolongacion izquierda (cm)
    anchor_right_cm: Optional[float] = None    # anclaje/prolongacion derecha (cm)
    continuity_across_support: bool = False    # cruza el apoyo => no cortar en beam_ids
    detail_reference: str = ""                 # ej. "TP4_PLAN_002" (detalle 002)
    confidence: Status = Status.EXACT
    source: str = "EXACT_DRAWING"
    classification: Classification = Classification.BEAM_LONGITUDINAL
    beam_kind: BeamKind = BeamKind.CONTINUOUS
    note: str = ""
    resolution: Resolution = Resolution.RESOLVED_METADATA

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "beam_ids": ";".join(self.beam_ids),
            "physical_bar_id": self.physical_bar_id,
            "bar_layer": self.bar_layer.value,
            "bar_count": self.bar_count,
            "diameter_mm": self.diameter_mm,
            "length_cm": self.length_cm,
            "start_axis": self.start_axis,
            "end_axis": self.end_axis,
            "start_station_cm": self.start_station_cm,
            "end_station_cm": self.end_station_cm,
            "anchor_left_cm": self.anchor_left_cm,
            "anchor_right_cm": self.anchor_right_cm,
            "continuity_across_support": self.continuity_across_support,
            "detail_reference": self.detail_reference,
            "confidence": self.confidence.value,
            "source": self.source,
            "classification": self.classification.value,
            "beam_kind": self.beam_kind.value,
            "note": self.note,
            "resolution": self.resolution.value,
        }


@dataclass
class BeamStirrupZone:
    """Region longitudinal de estribos sobre una viga.

    Cuando el plano solo referencia un detalle tipo (TP1/TP4 del plano
    002), ``detail_reference`` queda seteado y NO se inventa la
    distribucion (spacing permanece None).
    """

    id: RuleId
    beam_ids: List[str]                  # beam ids (plan) o elementTags del modelo
    start_station_cm: Optional[float] = None   # progresiva inicio (cm)
    end_station_cm: Optional[float] = None     # progresiva fin (cm)
    type: str = "ED"                     # ej. "ED" (estribo doble), "E", "T"
    diameter_mm: Optional[int] = 10      # None si no legible
    spacing_cm: Optional[int] = None     # ej. 10 o 20; None si solo hay TP ref
    count: Optional[int] = None          # ej. 17 (17ED...); None si no dado
    detail_reference: str = ""           # ej. "TP4_PLAN_002"
    confidence: Status = Status.EXACT
    source: str = "EXACT_DRAWING"
    note: str = ""
    resolution: Resolution = Resolution.RESOLVED_METADATA

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": str(self.id),
            "building": self.id.building,
            "drawing": self.id.drawing,
            "sheet": self.id.sheet,
            "beam_ids": ";".join(self.beam_ids),
            "zone_type": self.type,
            "diameter_mm": self.diameter_mm,
            "spacing_cm": self.spacing_cm,
            "count": self.count,
            "start_station_cm": self.start_station_cm,
            "end_station_cm": self.end_station_cm,
            "detail_reference": self.detail_reference,
            "confidence": self.confidence.value,
            "source": self.source,
            "note": self.note,
            "resolution": self.resolution.value,
        }


@dataclass
class BeamRecord:
    """Registro resumen de una viga identificada en los planos 400/401/402.

    ``beam_id`` es el id del PLANO (ej. "V100", "0102", "VF1"). La
    correspondencia a elements/axes del modelo se resuelve por separado
    (eje fisico); mientras no exista esa correspondencia ``geometric``
    queda False.
    """

    beam_id: str
    drawing: str
    sheet: str                       # ej. "400", "401 (2)", "402 (1)"
    section: str                     # ej. "V.60/80", "V.S.I. 20/150", "V.20/VAR"
    kind: BeamKind
    axes_text: str = ""              # ej. "Conjunto 3-2-1", "1b-8"
    group: str = ""                  # ej. "conjunto V100-V101"
    longitudinal: str = ""           # resumen F/F'/+/+F'
    stirrups: str = ""               # resumen estribos o referencia de detalle
    detail_reference: str = ""
    confidence: Status = Status.EXACT
    note: str = ""
    resolution: Resolution = Resolution.RESOLVED_METADATA

    def to_dict(self) -> Dict[str, object]:
        return {
            "beam_id": self.beam_id,
            "building": "LT1",
            "drawing": self.drawing,
            "sheet": self.sheet,
            "axes_text": self.axes_text,
            "group": self.group,
            "section": self.section,
            "kind": self.kind.value,
            "longitudinal": self.longitudinal,
            "stirrups": self.stirrups,
            "detail_reference": self.detail_reference,
            "confidence": self.confidence.value,
            "resolution": self.resolution.value,
            "note": self.note,
        }