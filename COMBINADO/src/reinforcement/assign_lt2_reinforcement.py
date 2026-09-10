"""Asignacion de las reglas de armadura LT2 a la geometria del modelo.

Resuelve cada zona textual de los planos LT2 contra la grilla de ejes
del modelo (`lt2_geometry.Lt2Geometry`). Reutiliza `ZoneResolver`
(definido en `assign_lt1_reinforcement`) que resuelve rectangulos
A-B/x-y, franjas sobre un eje y zonas generales.

REGLAS DE MAPEO LT2:
- RESOLVED solo si TODOS los ejes nombrados existen en la grilla LT2
  (eje_x: A',A,B,C,C',D,D' ; eje_y: 1,1A,2,2A,3) y el rectangulo/franja
  se construye sin ambiguedad. Ejemplos: eje 1', ejes 8A/8B, losa 01xx
  -> no existen -> quedan PARTIAL/UNRESOLVED (honestidad).
- Franjas (BAND): el ancho NO se infiere (nota del resolver); la linea
  del eje se resuelve.
- Columnas: 16 Φ22 LONGITUDINAL para todas las columnas LT2 (50 tags,
  seccion unica P70x70 -> inequivoco) con geometry_pending=True.
- Muros: registros por ELEVACION (300-305), NO regla universal. El eje
  se asocia a muros del modelo solo si el vinculo es inequivoco
  (eje A' -> M001/M003, eje 1 -> M002, eje 3 -> M004): entonces
  RESOLVED; el resto queda RESOLVED_METADATA. geometry_pending=True.
- Vigas (plano 400): familias/segmentos observados; los beam_ids del
  plano NO son legibles -> RESOLVED_METADATA (nunca asignar el patron
  V.60/80 a todos los elementos).
- Escaleras (plano 500): sin elementos de escalera en LT2 ->
  RESOLVED_METADATA.

Sin crear elementos FE: solo se asocian tags/ids y se reporta resolution.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .assign_lt1_reinforcement import ZoneResolver
from .lt2_beam_data import load_lt2_beam_data
from .lt2_geometry import Lt2Geometry
from .lt2_reinforcement_data import (
    FLOOR_TO_LEVEL_LT2,
    LEVELS_201,
    load_lt2_reinforcement,
)
from .lt2_stair_data import load_lt2_stair_data
from .lt2_wall_data import load_lt2_wall_data
from .reinforcement_types import Resolution, Zone, ZoneKind

# Niveles del modelo LT2 ocupados por cada sheet (idem lt2_reinforcement_data).
_LEVELS_LT2 = ("B1", "L1", "L2", "L3", "L4", "ROOF")


class Lt2ReinforcementAssigner:
    """Asigna todas las reglas LT2 y produce el reporte de resolucion."""

    def __init__(self, geo: Optional[Lt2Geometry] = None) -> None:
        self.geo = geo or Lt2Geometry()
        self.resolver = ZoneResolver(self.geo)
        self.data = load_lt2_reinforcement()
        self.wall_data = load_lt2_wall_data()["records"]
        self.beam_data = load_lt2_beam_data()
        self.stair_data = load_lt2_stair_data()["records"]

        self.resolved: Dict[str, List] = {"mesh": [], "local": [], "walls": [],
                                          "columns": [], "beams": [],
                                          "stairs": []}
        self.unresolved: Dict[str, List] = {"mesh": [], "local": [], "walls": [],
                                            "columns": [], "beams": [],
                                            "stairs": []}
        self.partial: Dict[str, List] = {"mesh": [], "local": [], "walls": [],
                                         "columns": [], "beams": [],
                                         "stairs": []}

    # ------------------------------------------------------------------
    def run(self) -> "Lt2ReinforcementAssigner":
        self._assign_mesh()
        self._assign_local()
        self._assign_columns()
        self._assign_walls()
        self._assign_beams()
        self._assign_stairs()
        return self

    # ------------------------------------------------------------------
    def _levels_for_rule(self, rule) -> List[str]:
        key = FLOOR_TO_LEVEL_LT2.get(rule.id.sheet, rule.floor)
        if key == "L1..L4":
            return list(LEVELS_201)
        if key in _LEVELS_LT2:
            return [key]
        return []

    def _assign_mesh(self) -> None:
        for rule in self.data["mesh"]:
            resolved_zone = self.resolver.resolve(rule.zone)
            zone, res = self._zone_and_resolution(rule, resolved_zone)
            rule.zone = zone
            rule.resolution = res
            self._bucket(rule, "mesh")

    def _assign_local(self) -> None:
        for rule in self.data["local"]:
            resolved_zone = self.resolver.resolve(rule.zone)
            zone, res = self._zone_and_resolution(rule, resolved_zone)
            rule.zone = zone
            rule.resolution = res
            self._bucket(rule, "local")

    def _assign_columns(self) -> None:
        tags = self.geo.column_tags()
        for rule in self.data["columns"]:
            rule.column_tags = tags
            rule.resolution = Resolution.RESOLVED
            rule.geometry_pending = True
            rule.note = (
                f"{rule.note} Asociado a {len(tags)} columnas LT2 "
                f"(tags {tags[0] if tags else '-'}..{tags[-1] if tags else '-'}); "
                "geometria 3D pendiente (sin recubrimiento/distribucion)."
            )
            self.resolved["columns"].append(rule)

    def _assign_walls(self) -> None:
        model_parents = set(self.geo.wall_parent_ids())
        for rule in self.wall_data:
            parents = [p for p in rule.wall_parents if p in model_parents]
            rule.wall_parents = parents
            if parents:
                rule.resolution = Resolution.RESOLVED
                rule.note = (rule.note + " Muro(s) FE del modelo: "
                             + (", ".join(parents)) + ".")
            else:
                rule.resolution = Resolution.RESOLVED_METADATA
            rule.geometry_pending = True
            self.resolved["walls"].append(rule)

    def _assign_beams(self) -> None:
        # Familias/segmentos del plano 400: beam_ids no legibles ->
        # metadata; NO se asigna barra por barra a vigas del modelo.
        for rec in self.beam_data["records"]:
            rec.note = (rec.note + " beam_id del plano NO legible: la "
                        "correspondencia a elementos del modelo queda "
                        "pendiente (no se asigna).")
            rec.resolution = Resolution.RESOLVED_METADATA
            self.resolved["beams"].append(rec)
        for seg in self.beam_data["segments"]:
            seg.resolution = Resolution.RESOLVED_METADATA
            self.resolved["beams"].append(seg)
        for stir in self.beam_data["stirrups"]:
            stir.resolution = Resolution.RESOLVED_METADATA
            self.resolved["beams"].append(stir)

    def _assign_stairs(self) -> None:
        for rule in self.stair_data:
            rule.resolution = Resolution.RESOLVED_METADATA
            rule.note = (rule.note + " Sin elementos de escalera en el "
                         "modelo LT2: registrado como metadata del plano.")
            self.resolved["stairs"].append(rule)

    # ------------------------------------------------------------------
    def _zone_and_resolution(self, rule, zone: Zone):
        if zone.rect is None:
            return zone, Resolution.UNRESOLVED if not zone.axis else Resolution.PARTIAL
        levels = self._levels_for_rule(rule)
        if levels and zone.rect:
            zone.pano_ids = self._match_panos(zone, levels)
        return zone, Resolution.RESOLVED

    def _match_panos(self, zone: Zone, levels: List[str]) -> List[str]:
        if zone.kind == ZoneKind.GENERAL:
            ids = []
            for lv in levels:
                ids.extend(p["panel_id"] for p in self.geo.panos_at_level(lv))
            return ids
        if len(zone.pano_ids):
            return zone.pano_ids
        if zone.kind == ZoneKind.RECT and zone.rect:
            ids = []
            eps = 1e-6
            for lv in levels:
                for p in self.geo.panos_at_level(lv):
                    x0, x1, y0, y1 = self.geo.pano_bounds(p)
                    if (abs(x0 - zone.rect[0]) < eps and abs(x1 - zone.rect[1]) < eps
                            and abs(y0 - zone.rect[2]) < eps and abs(y1 - zone.rect[3]) < eps):
                        ids.append(p["panel_id"])
            return ids
        return []

    def _bucket(self, rule, key: str) -> None:
        if rule.resolution == Resolution.RESOLVED:
            self.resolved[key].append(rule)
        elif rule.resolution == Resolution.PARTIAL:
            self.partial[key].append(rule)
        else:
            self.unresolved[key].append(rule)

    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Dict[str, int]]:
        out: Dict[str, Dict[str, int]] = {}
        for key in ("mesh", "local", "walls", "columns", "beams", "stairs"):
            out[key] = {
                "resolved": len(self.resolved[key]),
                "partial": len(self.partial[key]),
                "unresolved": len(self.unresolved[key]),
            }
        return out

    def to_rows(self) -> List[Dict]:
        rows: List[Dict] = []
        for key in ("mesh", "local", "walls", "columns", "beams", "stairs"):
            for rule in (self.resolved[key] + self.partial[key] + self.unresolved[key]):
                d = rule.to_dict()
                if "status" not in d and "confidence" in d:
                    d["status"] = d["confidence"]
                d["category"] = key
                rows.append(d)
        return rows


def assign_and_report(**_) -> Lt2ReinforcementAssigner:
    return Lt2ReinforcementAssigner().run()