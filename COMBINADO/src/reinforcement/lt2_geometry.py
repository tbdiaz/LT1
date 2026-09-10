"""Geometria LT2 a partir de `LT2/data/unity/edificio_lt2.json` (solo lectura).

LT2 es el edificio OESTE del modelo combinado. En `run_combined.py` LT2
conserva sus coordenadas NATIVAS (x, y, z por nivel) y solo LT1 se
traslada (x' = x + 31.250, y' = -y). Por ello, para LT2 las coordenadas
combinadas coinciden con las nativas y NO se aplica offset ni inversion.

La grilla de ejes proviene de los archivos de ejecucion LT2
(`LT2/data/geometry/grid_x.csv` y `grid_y.csv`):
- eje_x (lineas verticales del plano): A'=0.000, A=3.750, B=11.250,
  C=21.250, C'=28.830, D=31.250, D'=31.475.
- eje_y (lineas horizontales del plano): 1=0.000, 1A=4.265, 2=8.900,
  2A=11.885, 3=16.150.

Unidades: metros (m), kN, kPa.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LT2_JSON: Path = (
    Path(__file__).resolve().parents[3] / "LT2" / "data" / "unity" / "edificio_lt2.json"
)
LT2_GEOM_CSV: Path = (
    Path(__file__).resolve().parents[3] / "LT2" / "data" / "geometry"
)


class Lt2Geometry:
    """Lectura y consulta de la geometria LT2 (JSON de unity + grilla).

    La correspondencia eje -> muro (M001-M008) NO se decide aqui: solo
    se exponen los datos del modelo. La asignacion de armadura de muros
    usa la documentacion de `walls_LT2.csv`, preservando solo las
    asociaciones inequivocas (eje 1 -> M002, eje 3 -> M004, eje A' ->
    M001/M003).
    """

    SHIFT_X: float = 0.0   # LT2 es el edificio nativo del combinado (sin offset)

    def __init__(self, path: Optional[Path] = None,
                 grid_dir: Optional[Path] = None) -> None:
        self.path: Path = (path or LT2_JSON).resolve()
        self.grid_dir: Path = (grid_dir or LT2_GEOM_CSV).resolve()
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self._load()

    def _load(self) -> None:
        self.levels: List[dict] = list(self.data["levels"])
        self.columns: List[dict] = list(self.data["columns"])
        self.beams: List[dict] = list(self.data["beams"])
        self.walls: List[dict] = list(self.data["walls"])
        self.slabs: List[dict] = list(self.data.get("slabs", []))
        self.supports: List[dict] = list(self.data.get("supports", []))

        self.z_by_level: Dict[str, float] = {
            lv["name"]: float(lv["z"]) for lv in self.levels
        }

        # Grilla de ejes desde los CSVs de ejecucion LT2.
        self.eje_x: Dict[str, float] = {}
        self.eje_y: Dict[str, float] = {}
        for row in self._read_grid_csv("grid_x.csv"):
            self.eje_x[str(row["axis_id"]).strip()] = float(row["x_m"])
        for row in self._read_grid_csv("grid_y.csv"):
            self.eje_y[str(row["axis_id"]).strip()] = float(row["y_m"])
        self.ejes_x_ordered: List[str] = sorted(self.eje_x, key=self.eje_x.get)
        self.ejes_y_ordered: List[str] = sorted(self.eje_y, key=self.eje_y.get)

        self._slab_by_panel: Dict[str, dict] = {s["panel_id"]: s for s in self.slabs}
        self._col_by_tag: Dict[int, dict] = {c["elementTag"]: c for c in self.columns}
        self._beam_by_tag: Dict[int, dict] = {b["elementTag"]: b for b in self.beams}
        self._wall_by_id: Dict[str, dict] = {w["wall_id"]: w for w in self.walls}

    def _read_grid_csv(self, name: str) -> List[dict]:
        import csv

        path = self.grid_dir / name
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    # ------------------------------------------------------------------
    # Coordenadas
    # ------------------------------------------------------------------
    def x_of(self, eje_x: str) -> float:
        return self.eje_x[eje_x]

    def y_of(self, eje_y: str) -> float:
        return self.eje_y[eje_y]

    def z_of(self, level: str) -> float:
        return self.z_by_level[level]

    def to_combined(self, x_native: float, y_native: float, z: float) -> Tuple[float, float, float]:
        """LT2 nativo == combinado (run_combined no transforma LT2)."""
        return (x_native, y_native, z)

    # ------------------------------------------------------------------
    # Columnas / vigas / muros / losas
    # ------------------------------------------------------------------
    def column_tags(self) -> List[int]:
        return sorted(c["elementTag"] for c in self.columns)

    def column_by_tag(self, tag: int) -> Optional[dict]:
        return self._col_by_tag.get(tag)

    def beam_tags(self) -> List[int]:
        return sorted(b["elementTag"] for b in self.beams)

    def beam_by_tag(self, tag: int) -> Optional[dict]:
        return self._beam_by_tag.get(tag)

    def wall_ids(self) -> List[str]:
        return sorted(self._wall_by_id)

    def wall_parent_ids(self) -> List[str]:
        return sorted({w["parent_id"] for w in self.walls})

    def wall_by_id(self, wall_id: str) -> Optional[dict]:
        return self._wall_by_id.get(wall_id)

    def wall_segments(self, parent_id: str) -> List[dict]:
        return [w for w in self.walls if w["parent_id"] == parent_id]

    # ------------------------------------------------------------------
    # Losas (slabs) como panos del modelo
    # ------------------------------------------------------------------
    def slabs_at_level(self, level: str) -> List[dict]:
        return [s for s in self.slabs if s.get("level") == level]

    def slab_bounds(self, slab: dict) -> Tuple[float, float, float, float]:
        pts = self._polygon_pts(slab["polygon"])
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), max(xs), min(ys), max(ys))

    def slab_axes(self, slab: dict) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        bounds = self.slab_bounds(slab)
        ex0 = self._axis_at_x(bounds[0])
        ex1 = self._axis_at_x(bounds[1])
        ey0 = self._axis_at_y(bounds[2])
        ey1 = self._axis_at_y(bounds[3])
        return (ex0, ex1, ey0, ey1)

    def _polygon_pts(self, polygon: str) -> List[Tuple[float, float]]:
        pts = []
        for tok in polygon.split(";"):
            x, y = tok.split(",")
            pts.append((float(x), float(y)))
        return pts

    def _axis_at_x(self, x: float) -> Optional[str]:
        for ax, v in self.eje_x.items():
            if abs(v - x) < 1e-6:
                return ax
        return None

    def _axis_at_y(self, y: float) -> Optional[str]:
        for ay, v in self.eje_y.items():
            if abs(v - y) < 1e-6:
                return ay
        return None

    def levels_with_slabs(self) -> List[str]:
        return sorted({s.get("level") for s in self.slabs})

    # alias compatibles con el flujo Lt1 (panos)
    @property
    def panos(self) -> List[dict]:
        return self.slabs

    def panos_at_level(self, level: str) -> List[dict]:
        return self.slabs_at_level(level)

    def pano_bounds(self, pano: dict) -> Tuple[float, float, float, float]:
        return self.slab_bounds(pano)

    def pano_by_id(self, pano_id: str) -> Optional[dict]:
        return self._slab_by_panel.get(pano_id)