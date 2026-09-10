"""Generacion de la capa de armadura 3D LT2 (representacion, NO elementos FE).

Solo las MALLAS GENERALES resueltas (zona kind GENERAL con rect
completo) generan barras: el ancho de las franjas sobre ejes no se
infiere, por lo que las bandas NO dibujan barras (requieren el plano).

CONVENCIONES:
- Coordenadas: LT2 nativo == combinado (run_combined no transforma LT2).
- Las reglas del plano 201 (L1..L4) se emiten en cada uno de los 4
  niveles de losa; las del plano 202 en ROOF; fundaciones 200 en B1.
- `cover_cm=None`: la malla se ubica en el plano medio de la losa y se
  marca `z_approximation=True`.
- Este modulo NO llama a opensees: solo calcula geometria.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .assign_lt2_reinforcement import Lt2ReinforcementAssigner
from .lt2_geometry import Lt2Geometry
from .lt2_reinforcement_data import FLOOR_TO_LEVEL_LT2, LEVELS_201
from .reinforcement_geometry import BarLayer
from .reinforcement_types import Direction, Layer, MeshRule, Resolution, ZoneKind


class Lt2ReinforcementGeometryBuilder:
    """Construye la capa de barras LT2 a partir de las reglas asignadas."""

    def __init__(self, assigner: Lt2ReinforcementAssigner,
                 geo: Optional[Lt2Geometry] = None,
                 cover_cm: Optional[float] = None,
                 slab_thickness_m: float = 0.15) -> None:
        self.assigner = assigner
        self.geo = geo or assigner.geo
        self.cover_cm = cover_cm
        self.slab_thickness_m = slab_thickness_m
        self.bars: List[BarLayer] = []

    # ------------------------------------------------------------------
    def _levels_for_sheet(self, sheet: str) -> List[str]:
        key = FLOOR_TO_LEVEL_LT2.get(sheet, "")
        if key == "L1..L4":
            return list(LEVELS_201)
        if key and key in self.geo.z_by_level:
            return [key]
        return []

    def _z_mid(self, level: str, rule: MeshRule) -> float:
        z = self.geo.z_of(level)
        h = self.slab_thickness_m
        if rule.layer in (Layer.LOWER, Layer.UPPER) or level == "B1":
            # sin recubrimiento confirmado: mitad de la losa (o cota base)
            return z + h / 2.0 if level != "B1" else z
        return z + h / 2.0

    def _emit_mesh(self, rule: MeshRule, level: str) -> None:
        x1, x2, y1, y2 = rule.zone.rect
        z = self._z_mid(level, rule)
        z0, z1 = z, z
        pano_ids = rule.zone.pano_ids or ["_"]
        dx = x2 - x1
        dy = y2 - y1
        for d in (Direction.X, Direction.Y):
            if rule.direction not in (d, Direction.BOTH):
                continue
            if d == Direction.X:
                n = max(1, int(round(dy / (rule.spacing_cm / 100.0))))
                for i in range(n):
                    y = y1 + dy * (i + 0.5) / n
                    self.bars.append(BarLayer(
                        code=str(rule.id), x0=x1, y0=y, z0=z0, x1=x2, y1=y, z1=z1,
                        diameter_mm=rule.diameter_mm, spacing_cm=rule.spacing_cm,
                        layer=rule.layer, direction="X", level=level,
                        pano_id=";".join(pano_ids),
                        z_approximation=self.cover_cm is None))
            else:
                n = max(1, int(round(dx / (rule.spacing_cm / 100.0))))
                for i in range(n):
                    x = x1 + dx * (i + 0.5) / n
                    self.bars.append(BarLayer(
                        code=str(rule.id), x0=x, y0=y1, z0=z0, x1=x, y1=y2, z1=z1,
                        diameter_mm=rule.diameter_mm, spacing_cm=rule.spacing_cm,
                        layer=rule.layer, direction="Y", level=level,
                        pano_id=";".join(pano_ids),
                        z_approximation=self.cover_cm is None))

    def build(self) -> List[BarLayer]:
        self.bars = []
        for rule in list(self.assigner.resolved["mesh"]):
            if rule.zone.rect is None or rule.zone.kind != ZoneKind.GENERAL:
                continue
            for level in self._levels_for_sheet(rule.id.sheet):
                self._emit_mesh(rule, level)
        return self.bars

    def to_rows(self) -> List[Dict]:
        return [b.to_dict() for b in self.bars]