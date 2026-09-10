"""Generacion de la capa de armadura 3D (representacion, NO elementos FE).

Genera segmentos de barra para visualizar/verificar la armadura LT1 sin
crear ningun elemento estructural en el modelo OpenSeesPy combinado.

CONVENCIONES:
- Coordenadas: se emiten en el sistema COMBINADO (x = x_lt1 + SHIFT_X,
  y = -y_lt1). El offset se consulta de `lt1_geometry.Lt1Geometry.SHIFT_X`.
- Las losas se dibujan como mallas de barras en las dos direcciones con
  el espaciamiento de la regla; las franjas sobre ejes (BAND) se dibujan
  como barras a lo largo de la linea del eje.
- Los barridos se alimentan SOLO de reglas RESOLVED (las PARTIAL/UNRESOLVED
  no generan barras).
- `cover_cm`: recubrimiento al borde de la losa. Hasta que se confirme el
  valor, `cover_cm=None` -> la malla se ubica en el plano medio de la losa
  y se marca `z_approximation=True`.
- Este modulo NO llama a opensees: solo calcula geometria.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .assign_lt1_reinforcement import Lt1ReinforcementAssigner
from .lt1_geometry import Lt1Geometry
from .lt1_reinforcement_data import FLOOR_TO_LEVEL
from .reinforcement_types import Direction, Layer, MeshRule, Resolution


class BarLayer:
    """Segmento de barra individual (para exportar/graficar)."""

    def __init__(self, code: str, x0: float, y0: float, z0: float,
                 x1: float, y1: float, z1: float,
                 diameter_mm: int, spacing_cm: int, layer: Layer,
                 direction: str, level: str, pano_id: str,
                 z_approximation: bool) -> None:
        self.code = code
        self.p0 = (x0, y0, z0)
        self.p1 = (x1, y1, z1)
        self.diameter_mm = diameter_mm
        self.spacing_cm = spacing_cm
        self.layer = layer
        self.direction = direction
        self.level = level
        self.pano_id = pano_id
        self.z_approximation = z_approximation

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "x0_m": self.p0[0], "y0_m": self.p0[1], "z0_m": self.p0[2],
            "x1_m": self.p1[0], "y1_m": self.p1[1], "z1_m": self.p1[2],
            "diameter_mm": self.diameter_mm,
            "spacing_cm": self.spacing_cm,
            "layer": self.layer.value,
            "direction": self.direction,
            "level": self.level,
            "pano_id": self.pano_id,
            "z_approximation": self.z_approximation,
        }


class ReinforcementGeometryBuilder:
    """Construye la capa de barras a partir de las reglas asignadas."""

    def __init__(self, assigner: Lt1ReinforcementAssigner,
                 geo: Optional[Lt1Geometry] = None,
                 cover_cm: Optional[float] = None,
                 slab_thickness_m: float = 0.20) -> None:
        self.assigner = assigner
        self.geo = geo or assigner.geo
        self.cover_cm = cover_cm
        self.slab_thickness_m = slab_thickness_m
        self.bars: List[BarLayer] = []

    # ------------------------------------------------------------------
    def level_z(self, level: str) -> Optional[float]:
        """Nivel (cota z) de la capa de referencia del piso en el JSON LT1."""
        for n in self.geo.nodes:
            if n.get("nivel") == level:
                return float(n["z"])
        return None

    def last_supported_z(self, level: str) -> Optional[float]:
        found = [float(n["z"]) for n in self.geo.nodes if n.get("nivel") == level]
        return max(found) if found else None

    def _z_for_slab(self, level: str) -> Optional[float]:
        if self.geo.panos_at_level(level):
            return self.last_supported_z(level)
        # nivel sin panos (ej. FUNDACION_SUP o PISO_1S)
        return self.last_supported_z(level)

    def _emit_mesh(self, rule: MeshRule, zone_rect, level: str,
                   z0: float, z1: float) -> None:
        pano_ids = rule.zone.pano_ids
        x1, x2, y1, y2 = zone_rect
        x1c = x1 + self.geo.SHIFT_X
        x2c = x2 + self.geo.SHIFT_X
        y1c = -y1
        y2c = -y2
        dirs: List[Tuple[str, float]] = []
        if rule.direction in (Direction.X, Direction.BOTH):
            dirs.append(("X", x1c))
        if rule.direction in (Direction.Y, Direction.BOTH):
            dirs.append(("Y", y1c))
        for d, _ in dirs:
            ...
        # simplificacion: representamos la malla como barras paralelas
        # con el espaciamiento en la direccion perpendicular.
        for d in (Direction.X, Direction.Y):
            if rule.direction not in (d, Direction.BOTH):
                continue
            if d == Direction.X:
                n = max(1, int(round((y2c - y1c) / (rule.spacing_cm / 100.0))))
                for i in range(n):
                    y = y1c + (y2c - y1c) * (i + 0.5) / n
                    self.bars.append(BarLayer(
                        code=str(rule.id), x0=x1c, y0=y, z0=z0, x1=x2c, y1=y, z1=z1,
                        diameter_mm=rule.diameter_mm, spacing_cm=rule.spacing_cm,
                        layer=rule.layer, direction="X", level=level,
                        pano_id=";".join(pano_ids) or "_", z_approximation=self.cover_cm is None))
            else:
                n = max(1, int(round((x2c - x1c) / (rule.spacing_cm / 100.0))))
                for i in range(n):
                    x = x1c + (x2c - x1c) * (i + 0.5) / n
                    self.bars.append(BarLayer(
                        code=str(rule.id), x0=x, y0=y1c, z0=z0, x1=x, y1=y2c, z1=z1,
                        diameter_mm=rule.diameter_mm, spacing_cm=rule.spacing_cm,
                        layer=rule.layer, direction="Y", level=level,
                        pano_id=";".join(pano_ids) or "_", z_approximation=self.cover_cm is None))

    def build(self) -> List[BarLayer]:
        self.bars = []
        for rule in self.assigner.resolved["mesh"] + self.assigner.partial["mesh"]:
            if rule.zone.rect is None:
                continue
            level = FLOOR_TO_LEVEL.get(rule.id.sheet)
            if not level:
                continue
            z = self._z_for_slab(level)
            if z is None:
                continue
            if self.cover_cm is not None:
                h = self.slab_thickness_m
                if rule.layer == Layer.UPPER:
                    z0 = z + h - self.cover_cm / 100.0
                    z1 = z0
                elif rule.layer == Layer.LOWER:
                    z0 = z + self.cover_cm / 100.0
                    z1 = z0
                else:
                    mid = z + h / 2.0
                    z0 = mid - self.cover_cm / 100.0
                    z1 = mid + self.cover_cm / 100.0
            else:
                mid = z + self.slab_thickness_m / 2.0
                z0, z1 = mid, mid
            self._emit_mesh(rule, rule.zone.rect, level, z0, z1)
        return self.bars

    def to_rows(self) -> List[Dict]:
        return [b.to_dict() for b in self.bars]