"""Geometria LT1 a partir de `outputs/unity/modelo_lt1.json` (solo lectura).

Mapea los ejes, niveles, panos (losas), muros y vigas LT1 para poder
asociar armadura sin reutilizar los offsets del modelo combinado.

Unidades: metros (m), kN, kPa. Ejes en coordenadas NATIVAS LT1
(sistema en que quedan las cotas del plano).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Rutas (relativas a COMBINADO/ cuando no se da otro origen)
# ---------------------------------------------------------------------------
COMB_JSON_LT1: Path = Path(__file__).resolve().parents[3] / "outputs" / "unity" / "modelo_lt1.json"


class Lt1Geometry:
    """Lectura y consulta de la geometria LT1 del JSON de unity.

    La transformada combinada (offset X +31.25 m con el eje Y invertido)
    solo se aplica para representar sobre el modelo combinado; el mapeo
    de armadura se resuelve siempre en ejes LT1 nativos.
    """

    SHIFT_X: float = 31.25   # offset aplicado por run_combined a LT1 (verificacion)

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path: Path = (path or COMB_JSON_LT1).resolve()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.data = data
        self._load()

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------
    def _load(self) -> None:
        self.nodes: List[dict] = list(self.data["nodes"])
        self.beams: List[dict] = list(self.data["beams"])
        self.columns: List[dict] = list(self.data["columns"])
        self.walls: List[dict] = list(self.data["walls"])
        self.supports: List[dict] = list(self.data["supports"])
        self.panos: List[dict] = list(self.data.get("panos", []))

        self.eje_x: Dict[str, float] = {}
        self.eje_y: Dict[str, float] = {}
        for n in self.nodes:
            ex, ey = n.get("eje_x"), n.get("eje_y")
            if ex and ey:
                self.eje_x.setdefault(ex, float(n["x"]))
                self.eje_y.setdefault(ey, float(n["y"]))
        self.ejes_x_ordered: List[str] = sorted(self.eje_x, key=self.eje_x.get)
        self.ejes_y_ordered: List[str] = sorted(self.eje_y, key=lambda k: -self.eje_y[k])
        self.levels: List[str] = sorted({
            n.get("nivel") for n in self.nodes if n.get("nivel")
        })

        self._nodes_by_tag: Dict[int, dict] = {n["tag"]: n for n in self.nodes}
        self._wall_by_tag: Dict[int, dict] = {w["elementTag"]: w for w in self.walls}
        self._beam_by_tag: Dict[int, dict] = {b["elementTag"]: b for b in self.beams}

    # ------------------------------------------------------------------
    # Coordenadas
    # ------------------------------------------------------------------
    def x_of(self, eje_x: str) -> float:
        return self.eje_x[eje_x]

    def y_of(self, eje_y: str) -> float:
        return self.eje_y[eje_y]

    def to_combined(self, x_native: float, y_native: float, z: float) -> Tuple[float, float, float]:
        """Convierte coordenadas LT1 nativas a coordenadas combinadas.

        Convencion verificada en `run_combined.LT1_TRANSFORM`: la saliente
        LT1 se traslada con x' = x + SHIFT_X e y' = -y.
        """
        return (x_native + self.SHIFT_X, -y_native, z)

    # ------------------------------------------------------------------
    # Nodos
    # ------------------------------------------------------------------
    def node_by_tag(self, tag: int) -> Optional[dict]:
        return self._nodes_by_tag.get(tag)

    # ------------------------------------------------------------------
    # Panos (losas) del modelo
    # ------------------------------------------------------------------
    def pano_by_id(self, pano_id: str) -> Optional[dict]:
        for p in self.panos:
            if p["id"] == pano_id:
                return p
        return None

    def panos_at_level(self, level: str) -> List[dict]:
        return [p for p in self.panos if p.get("nivel") == level]

    def pano_bounds(self, pano: dict) -> Tuple[float, float, float, float]:
        x1 = self.x_of(pano["eje_x0"])
        x2 = self.x_of(pano["eje_x1"])
        y1 = self.y_of(pano["eje_y0"])
        y2 = self.y_of(pano["eje_y1"])
        return (min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2))

    def pano_axes(self, pano: dict) -> Tuple[str, str, str, str]:
        return (pano["eje_x0"], pano["eje_x1"], pano["eje_y0"], pano["eje_y1"])

    def levels_with_panos(self) -> List[str]:
        return sorted({p.get("nivel") for p in self.panos})

    # ------------------------------------------------------------------
    # Muros / vigas / columnas
    # ------------------------------------------------------------------
    def wall_tags(self) -> List[int]:
        return sorted(w["elementTag"] for w in self.walls)

    def wall_by_tag(self, tag: int) -> Optional[dict]:
        return self._wall_by_tag.get(tag)

    def beam_tags(self) -> List[int]:
        return sorted(b["elementTag"] for b in self.beams)

    def beam_by_tag(self, tag: int) -> Optional[dict]:
        return self._beam_by_tag.get(tag)

    def beams_by_seccion(self, seccion: str) -> List[dict]:
        return [b for b in self.beams if b.get("seccion") == seccion]

    def column_tags(self) -> List[int]:
        return sorted(c["elementTag"] for c in self.columns)