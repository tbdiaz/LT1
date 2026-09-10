"""Asignacion de las reglas de armadura LT1 a la geometria del modelo.

Resuelve cada zona textual de los planos (ej. "E-F/1-2", "Eje I", "resto
ejes Y") contra la grilla de ejes del modelo LT1 (`lt1_geometry`).

REGLAS SOBRE EL MAPEO:
- Una zona se marca RESOLVED solo si TODOS los ejes nombrados existen en
  la grilla del modelo y el rectangulo puede construirse sin ambiguedad.
- Si parte de los ejes no existen (IB, H1, 1BB, 8, Ga, J, 1...), la regla
  NO se aplica a geometria: queda PARTIAL/UNRESOLVED con su razon.
- Las franjas sobre un eje ("Eje I") se resuelven a la linea del eje pero
  el ANCHO de la franja no se infiere: queda PARTIAL (ancho del plano).
- Los muros: asociacion por family al los 6 muros LT1 (tags 400001-400006).
- Columnas: dato confirmado 16 B22 LONGITUDINAL para TODAS las columnas
  LT1; la asociacion a los 90 tags es inequivoca (seccion unica P.70x70)
  y queda RESOLVED con geometry_pending=True.
- Vigas: familia REPRESENTATIVE, NO asignada elemento a elemento (queda
  RESOLVED_METADATA con lista de tags de referencia).
- Escaleras: sin elementos estructurales escalera en LT1 -> UNRESOLVED.

Sin crear elementos FE: solo se asocian tags/ids y se reporta resolution.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from .lt1_geometry import Lt1Geometry
from .lt1_reinforcement_data import (
    FLOOR_TO_LEVEL,
    FLOOR_TO_LEVEL_UNCONFIRMED,
    load_lt1_reinforcement,
)
from .reinforcement_types import (
    BeamRule,
    ColumnReinforcementRule,
    LocalBarRule,
    MeshRule,
    Resolution,
    RuleId,
    StairRule,
    WallRule,
    Zone,
    ZoneKind,
)


GENERAL_KEYWORDS = ("general", "resto ejes", "mayoria", "predominante", "borde superior")

def _is_general_text(text: str) -> bool:
    return any(kw in text for kw in GENERAL_KEYWORDS)


class ZoneResolver:
    """Convierte texto de zona del plano en un `Zone` geometrico."""

    def __init__(self, geo: Lt1Geometry) -> None:
        self.geo = geo
        self.axis_x = set(self.geo.eje_x)
        self.axis_y = set(self.geo.eje_y)
        # mapa token normalizado -> clave canonica en la grilla
        self._canon_x = {a.lower(): a for a in self.geo.eje_x}
        self._canon_y = {a.lower(): a for a in self.geo.eje_y}
        self._canon = {**self._canon_x, **self._canon_y}

    def _norm(self, text: str) -> str:
        t = (text.replace("\u2013", "-").replace("\u2014", "-")
                .replace("\u2019", "'").replace("\u2018", "'").strip().lower())
        return t

    def resolve(self, rule_zone: Zone) -> Zone:
        """Resuelve una zona, rellenando rect/axis/pano_ids/note."""
        text = self._norm(rule_zone.text)
        zone = Zone(kind=rule_zone.kind, text=rule_zone.text)

        # zonas "generales / resto del nivel"
        if _is_general_text(text):
            zone.kind = ZoneKind.GENERAL
            return self._resolve_general(rule_zone, zone)

        # pares A-B: intentamos interpretar rangos X/Y
        x_rng, y_rng, bad_pairs = self._find_ranges(text)

        if bad_pairs and not (x_rng and y_rng):
            # hay ejes del plano que no estan en la grilla LT1: no geometria
            zone.note = (
                "pares con ejes no modelados LT1: "
                f"{', '.join(sorted(bad_pairs))}; no se aplica geometria."
            )
            return zone

        if x_rng and y_rng:
            zone.kind = ZoneKind.RECT
            x1 = self.geo.x_of(x_rng[0]); x2 = self.geo.x_of(x_rng[1])
            y1 = self.geo.y_of(y_rng[0]); y2 = self.geo.y_of(y_rng[1])
            zone.rect = (min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2))
            zone.note = (
                f"rectangulo {min(x1,x2):.2f}..{max(x1,x2):.2f} x "
                f"{min(y1,y2):.2f}..{max(y1,y2):.2f} m (ejes LT1)"
            )
            return zone

        # franja sobre un eje (banda), posible rango en el otro sentido
        ax = self._find_single_axis(text)
        if ax:
            zone.kind = ZoneKind.BAND
            if ax in self.geo.eje_y:
                y = self.geo.y_of(ax)
                zone.axis = ax
                if x_rng:
                    x1 = self.geo.x_of(x_rng[0]); x2 = self.geo.x_of(x_rng[1])
                    zone.rect = (min(x1, x2), max(x1, x2), y, y)
                else:
                    xs = sorted(self.geo.eje_x.values())
                    zone.rect = (xs[0], xs[-1], y, y)
                zone.note = (
                    f"franja sobre eje {ax}; ancho de franja no inferido, "
                    "requiere el plano (NEEDS_EXACT_ZONE_MAPPING)."
                )
            else:
                x = self.geo.x_of(ax)
                zone.axis = ax
                if y_rng:
                    y1 = self.geo.y_of(y_rng[0]); y2 = self.geo.y_of(y_rng[1])
                    zone.rect = (x, x, min(y1, y2), max(y1, y2))
                else:
                    ys = sorted(self.geo.eje_y.values())
                    zone.rect = (x, x, ys[0], ys[-1])
                zone.note = (
                    f"franja sobre eje {ax}; ancho de franja no inferido, "
                    "requiere el plano (NEEDS_EXACT_ZONE_MAPPING)."
                )
            return zone

        zone.note = "no se identificaron ejes/rectangulos modelados en LT1."
        return zone

    def _resolve_general(self, rule_zone: Zone, zone: Zone) -> Zone:
        zone.kind = ZoneKind.GENERAL
        # por defecto el contenedor del nivel modelado
        xs = sorted(self.geo.eje_x.values())
        ys = sorted(self.geo.eje_y.values())
        zone.rect = (xs[0], xs[-1], ys[0], ys[-1])
        zone.note = "zona general del nivel; extremos del modelo LT1."
        return zone

    # ------------------------------------------------------------------
    def _find_ranges(self, text: str):
        """Extrae rangos de ejes y reporta pares no resolubles.

        Returns:
            (x_rng, y_rng, bad_pairs) donde bad_pairs es un conjunto de
            tokens (ejes) mencionados en pares A-B que NO estan en la
            grilla del modelo LT1.
        """
        x_rng: Optional[Tuple[str, str]] = None
        y_rng: Optional[Tuple[str, str]] = None
        bad_pairs: set = set()

        for m in re.finditer(r"([A-Za-z0-9'']+)\s*-\s*([A-Za-z0-9'']+)", text):
            a = self._canon.get(m.group(1).lower())
            b = self._canon.get(m.group(2).lower())
            if a is None or b is None:
                for t in (m.group(1), m.group(2)):
                    tt = t.lower().replace("'", "'")
                    if tt not in self._canon:
                        # no es un eje modelo ni un token tipo 'eje H1'
                        if tt not in {"eje"}:
                            bad_pairs.add(tt)
                continue
            if x_rng and y_rng:
                break
            if a in self.axis_x and b in self.axis_x and not x_rng:
                x_rng = (a, b)
            elif a in self.axis_y and b in self.axis_y and not y_rng:
                y_rng = (a, b)

        return x_rng, y_rng, bad_pairs

    def _find_single_axis(self, text: str) -> Optional[str]:
        for m in re.finditer(r"[A-Za-z0-9'']+", text):
            tok = self._canon.get(m.group(0).lower())
            if tok is not None and len(tok) <= 2 and tok in self.geo.eje_x:
                return tok
            if tok is not None and tok in self.geo.eje_y:
                return tok
        # "eje i'" / "eje 2a" con prefijo explicito
        for m in re.finditer(r"eje\s+([A-Za-z0-9'']+)", text):
            tok = self._canon.get(m.group(1).lower())
            if tok in self.geo.eje_x or tok in self.geo.eje_y:
                return tok
        return None

    def _missing_axes(self, *ranges: Optional[Tuple[str, str]]) -> List[str]:
        missing: List[str] = []
        for rng in ranges:
            if not rng:
                continue
            for a in rng:
                if a not in self.axis_x and a not in self.axis_y:
                    if a not in missing:
                        missing.append(a)
        return missing


class Lt1ReinforcementAssigner:
    """Asigna todas las reglas LT1 y produce el reporte de resolucion."""

    def __init__(self, geo: Optional[Lt1Geometry] = None) -> None:
        self.geo = geo or Lt1Geometry()
        self.resolver = ZoneResolver(self.geo)
        self.data = load_lt1_reinforcement()
        self.level_unconfirmed: set = FLOOR_TO_LEVEL_UNCONFIRMED

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
    def run(self) -> "Lt1ReinforcementAssigner":
        self._assign_mesh()
        self._assign_local()
        self._assign_walls()
        self._assign_columns()
        self._assign_beams()
        self._assign_stairs()
        return self

    # ------------------------------------------------------------------
    def _assign_mesh(self) -> None:
        for rule in self.data["mesh"]:
            resolved_zone = self.resolver.resolve(rule.zone)
            zone, res = self._zone_and_resolution(rule, resolved_zone)
            rule.zone = zone
            rule.resolution = res
            if rule.floor in self.level_unconfirmed:
                rule.note = (rule.note + " " if rule.note else "") + \
                    "NIVEL_TENTATIVO (plano->modelo por nombre; revisar cota)."
            self._bucket(rule, "mesh")

    def _assign_local(self) -> None:
        for rule in self.data["local"]:
            resolved_zone = self.resolver.resolve(rule.zone)
            zone, res = self._zone_and_resolution(rule, resolved_zone)
            rule.zone = zone
            rule.resolution = res
            self._bucket(rule, "local")

    def _assign_walls(self) -> None:
        # familia tipica: se asocia a los 6 muros del modelo (tags nativos)
        for rule in self.data["walls"]:
            rule.zone = Zone(kind=ZoneKind.GENERAL,
                             text=rule.zone.text,
                             note=f"tags muros LT1: {self.geo.wall_tags()}")
            rule.resolution = Resolution.RESOLVED
            self.resolved["walls"].append(rule)

    def _assign_columns(self) -> None:
        # 16 B22 LONGITUDINAL confirmado para todas las columnas LT1
        # (seccion unica P.70x70 -> asociacion inequivoca a los 90 tags).
        tags = self.geo.column_tags()
        for rule in self.data["columns"]:
            rule.column_tags = tags
            rule.resolution = Resolution.RESOLVED
            rule.geometry_pending = True
            rule.note = (
                f"{rule.note} asociado a {len(tags)} columnas LT1 "
                f"(tags {tags[0] if tags else '-'}..{tags[-1] if tags else '-'}); "
                "geometria 3D pendiente (sin recubrimiento/distribucion)."
            )
            self.resolved["columns"].append(rule)

    def _assign_beams(self) -> None:
        # REPRESENTATIVE: no se asigna barra a barra. Referencia por tag.
        tags = self.geo.beam_tags()
        for rule in self.data["beams"]:
            rule.zone.note = (
                f"tags de referencia (NO asignados): {len(tags)} vigas LT1 "
                f"({tags[0] if tags else '-'}..{tags[-1] if tags else '-'})"
            )
            rule.resolution = Resolution.RESOLVED_METADATA
            self.resolved["beams"].append(rule)

    def _assign_stairs(self) -> None:
        for rule in self.data["stairs"]:
            rule.zone.note = (
                "LT1 sin elementos estructurales de escalera en el modelo; "
                "no hay tema geometrico. DETAIL_FROM_DRAWING_REQUIRED."
            )
            rule.resolution = Resolution.UNRESOLVED
            self.unresolved["stairs"].append(rule)

    # ------------------------------------------------------------------
    def _zone_and_resolution(self, rule, zone: Zone):
        if zone.rect is None:
            return zone, Resolution.UNRESOLVED if not zone.axis else Resolution.PARTIAL
        # tratar de encontrar panos en el nivel mapeado
        level = FLOOR_TO_LEVEL.get(rule.id.sheet, None)
        if level and zone.rect:
            matched = self._match_panos(zone, level)
            zone.pano_ids = matched
        return zone, Resolution.RESOLVED

    def _match_panos(self, zone: Zone, level: str) -> List[str]:
        if zone.kind == ZoneKind.GENERAL:
            return [p["id"] for p in self.geo.panos_at_level(level)]
        if len(zone.pano_ids):
            return zone.pano_ids
        if zone.kind == ZoneKind.RECT and zone.rect:
            ids = []
            for p in self.geo.panos_at_level(level):
                x0, x1, y0, y1 = self.geo.pano_bounds(p)
                eps = 1e-6
                if (abs(x0 - zone.rect[0]) < eps and abs(x1 - zone.rect[1]) < eps
                        and abs(y0 - zone.rect[2]) < eps and abs(y1 - zone.rect[3]) < eps):
                    ids.append(p["id"])
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
    # Reportes
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
                d["category"] = key
                rows.append(d)
        return rows


def assign_and_report(**_) -> Lt1ReinforcementAssigner:
    return Lt1ReinforcementAssigner().run()