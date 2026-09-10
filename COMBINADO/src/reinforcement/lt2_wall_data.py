"""Armadura de muros LT2 desde las elevaciones 300-305.

A diferencia de LT1 (que definio una familia tipica unica para todos los
muros), las elevaciones LT2 se registran POR EJE/ELEVACION. Solo se
declara como EXACT lo que se distingue inequivocamente; cuando el grupo
existe pero la cifra no es legible se marca NEEDS_DRAWING_VALUE_CONFIRMATION
(sin inventar numeros), y la geometria 3D queda pendiente
(geometry_pending=True).

REGLAS DE LA TRANSCRIPCION:
- NO se aplica una regla universal a "todas las paredes" del modelo.
- NO se infiere continuidad entre pisos solo por alineacion grafica de la
  elevacion; cada tramo (level_start-level_end) se registra por separado
  cuando el plano lo muestra.
- Observado en las elevaciones: grupos longitudinales de borde de MAYOR
  diametro en sectores inferiores y grupos B22 en sectores superiores;
  armadura distribuida en el alma (vertical y horizontal), refuerzos
  locales en encuentros viga/losa, empalmes/anclajes y arranques desde
  la fundacion. La transicion de niveles y las cifras por grupo requieren
  el plano (no se leyeron valores exactos por elevacion).
- Mapeo eje -> muro(s) del modelo SOLO cuando es inequivoco
  (documentado en walls_LT2.csv):
      eje A' -> M001, M003 ;  eje 1 -> M002 ;  eje 3 -> M004
  Las demas elevaciones (1', 2, 8A, 8B, A, B, B', C, C', D-D', E1) se
  conservan como metadata sin asociar elementos FE (no hay un muro del
  modelo documentado para esos ejes).

Este modulo NO depende de OpenSeesPy ni del modelo combinado.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .reinforcement_types import (
    RuleId,
    Status,
    WallBoundaryBarGroup,
    WallDistributedReinforcement,
    WallLocalReinforcement,
    WallOrientation,
)

# Elevacion 300-305: eje(s) atendido(s) por cada hoja.
ELEVATION_AXES: Dict[str, List[str]] = {
    "300": ["1", "1'"],
    "301": ["2"],
    "302": ["8B", "3", "8A"],
    "303": ["A'", "A"],
    "304": ["B'", "B", "E1", "C'"],
    "305": ["D-D'", "C"],
}

# Correspondencias inequivocas eje -> muro del modelo (walls_LT2.csv).
WALL_AXIS_TO_PARENT: Dict[str, List[str]] = {
    "A'": ["M001", "M003"],
    "1": ["M002"],
    "3": ["M004"],
}

# Niveles relevantes del modelado LT2.
LEVEL_B1 = "B1"
LEVEL_L3 = "L3"
LEVEL_ROOF = "ROOF"

# Descripcion del hecho observado en las elevaciones (mismo texto en las
# notas; NO se repiten cifras porque no fueron legibles por elevacion).
_OBS_BOUNDARY = (
    "grupos de barras longitudinales de borde: mayor diametro en sectores "
    "inferiores y grupos B22 en sectores superiores; cantidad exacta y "
    "transicion por nivel requieren el plano (cifra no legible)."
)
_OBS_BOUNDARY_LOW = (
    "borde inferior: grupos longitudinales de mayor diametro (respecto de "
    "los superiores); arranques desde la fundacion presentes; cifra y "
    "transicion por nivel requieren el plano."
)
_OBS_BOUNDARY_UP = (
    "borde superior: grupos longitudinales B22; cantidad exacta por nivel "
    "requiere el plano (cifra no legible)."
)
_OBS_DIST_V = (
    "armadura distribuida vertical del alma; diametro/espaciamiento no "
    "legibles por elevacion -> sin valor inventado."
)
_OBS_DIST_H = (
    "armadura distribuida horizontal del alma; diametro/espaciamiento no "
    "legibles por elevacion -> sin valor inventado."
)
_OBS_LOCAL = (
    "refuerzos locales en encuentros con vigas/losas, empalmes/anclajes y "
    "arranques desde fundacion; detalles puntuales requieren el plano."
)


class _Seq:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}

    def next(self, sheet: str) -> int:
        self._n[sheet] = self._n.get(sheet, 0) + 1
        return self._n[sheet]


def _bed(s: _Seq, sheet: str, axis: str) -> WallBoundaryBarGroup:
    parents: List[str] = WALL_AXIS_TO_PARENT.get(axis, [])
    return WallBoundaryBarGroup(
        id=RuleId("LT2", f"2024_22-300-{sheet}-Model", sheet, s.next(sheet)),
        axis=axis,
        level_start=LEVEL_B1,
        level_end=LEVEL_ROOF,
        bar_count=None,
        diameter_mm=None,
        wall_parents=parents,
        status=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note=_OBS_BOUNDARY + (" Sin muro FE inequivoco para este eje." if not parents else ""),
    )


def _bed_band(s: _Seq, sheet: str, axis: str, low: bool) -> WallBoundaryBarGroup:
    parents: List[str] = WALL_AXIS_TO_PARENT.get(axis, [])
    return WallBoundaryBarGroup(
        id=RuleId("LT2", f"2024_22-300-{sheet}-Model", sheet, s.next(sheet)),
        axis=axis,
        level_start=LEVEL_B1 if low else LEVEL_L3,
        level_end=LEVEL_L3 if low else LEVEL_ROOF,
        bar_count=None,
        diameter_mm=22 if not low else None,
        face_edge="borde" ,
        wall_parents=parents,
        status=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note=(_OBS_BOUNDARY_LOW if low else _OBS_BOUNDARY_UP)
             + (" Sin muro FE inequivoco para este eje." if not parents else ""),
    )


def _dis(s: _Seq, sheet: str, axis: str,
         orientation: WallOrientation) -> WallDistributedReinforcement:
    parents: List[str] = WALL_AXIS_TO_PARENT.get(axis, [])
    return WallDistributedReinforcement(
        id=RuleId("LT2", f"2024_22-300-{sheet}-Model", sheet, s.next(sheet)),
        axis=axis,
        level_start=LEVEL_B1,
        level_end=LEVEL_ROOF,
        orientation=orientation,
        diameter_mm=None,
        spacing_cm=None,
        wall_parents=parents,
        status=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note=(_OBS_DIST_V if orientation == WallOrientation.VERTICAL
              else _OBS_DIST_H) + (
                  " Sin muro FE inequivoco para este eje." if not parents else ""
              ),
    )


def _loc(s: _Seq, sheet: str, axis: str) -> WallLocalReinforcement:
    parents: List[str] = WALL_AXIS_TO_PARENT.get(axis, [])
    return WallLocalReinforcement(
        id=RuleId("LT2", f"2024_22-300-{sheet}-Model", sheet, s.next(sheet)),
        axis=axis,
        level_start=LEVEL_B1,
        level_end=LEVEL_ROOF,
        bar_count=None,
        diameter_mm=None,
        wall_parents=parents,
        status=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note=_OBS_LOCAL + (
            " Sin muro FE inequivoco para este eje." if not parents else ""
        ),
    )


def load_lt2_wall_data() -> Dict[str, List]:
    """Registros de armadura de muros LT2 por elevacion (300-305).

    Retorna la lista plana de registros en ``records``. Para cada eje se
    conservan 4 registros: borde (B1-L3), borde (L3-ROOF), distribuido
    vertical, distribuido horizontal y local -> por eso 5 por eje.
    """
    s = _Seq()
    records: List = []
    for sheet, axes in ELEVATION_AXES.items():
        for axis in axes:
            records.append(_bed_band(s, sheet, axis, low=True))
            records.append(_bed_band(s, sheet, axis, low=False))
            records.append(_dis(s, sheet, axis, WallOrientation.VERTICAL))
            records.append(_dis(s, sheet, axis, WallOrientation.HORIZONTAL))
            records.append(_loc(s, sheet, axis))
    return {"records": records}


if __name__ == "__main__":
    import sys

    data = load_lt2_wall_data()
    print("Registros de muros LT2:", len(data["records"]))
    axes = sorted({r.axis for r in data["records"]})
    print("Ejes:", ", ".join(axes))
    sys.exit(0)