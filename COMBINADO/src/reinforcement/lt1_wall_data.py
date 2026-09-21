"""Armadura de muros LT1 desde las elevaciones 300-303.

Este modulo REEMPLAZA la antigua regla tipica de muros LT1 (una unica
familia aplicada a "todas las paredes"). Los registros son ESPECIFICOS
por elevacion/eje/tramo de niveles y por clase de refuerzo.

FUENTES PRIMARIAS (leidas como PDF, transcritas sin OCR):
    LT1/planos/2017_67-300-Model.pdf
    LT1/planos/2017_67-301-Model.pdf
    LT1/planos/2017_67-302-Model.pdf
    LT1/planos/2017_67-303-Model.pdf

QUE ES LEGIBLE EN LOS PDFs (texto extraido):
- Plano 300: ejes E', E, F, F', G, H, I, I', J y "ESCALA 1:50".
- Plano 301: titulos de elevaciones EJE 1C, EJE 1A, EJE 1b; marcadores
  de nivel "1º" y "1ºS"; ejes E, E', Eb, Ec, IB, IA, I, I', H2, H1;
  anotaciones de vigas V.F. 15/225, V. 15/125, V. 15/VAR, V. 20/80.
- Plano 302: "ESCALA 1:50" (sin ejes/niveles legibles; elevacion completa
  de una familia independiente).
- Plano 303: ejes E', E, F, F', G, H, I, I', J y "ESCALA 1:50".
Las cifras de las barras de muro (cantidad, diametro, espaciamiento,
longitud, anclaje) NO son texto en el PDF: estan dibujadas. Por regla del
proyecto NO se infieren: se registran como None y el registro queda
NEEDS_DRAWING_VALUE_CONFIRMATION / DETAIL_FROM_DRAWING_REQUIRED con
geometry_pending=True.

CLASIFICACIONES (extensión de WallReinforcementClass):
    BOUNDARY, DISTRIBUTED_VERTICAL, DISTRIBUTED_HORIZONTAL, LOCAL,
    STARTER (arranque desde fundacion), LAP (empalme por nivel),
    SPECIAL_GEOMETRY (muros inclinados/de geometria variable: EJE 1A y
    EJE 1BB del plano 301).

NOTAS DE HONESTIDAD:
- NO se copia armadura de un eje a otro (E-F vs G-H vs I-J).
- NO se aproximan 1A/1BB a muro rectangular tipico (geometry_special).
- NO se asocian elementTags FE: el modelo LT1 representa seis paños de núcleo
  en cinco tramos verticales (30 elementos, 400001-400406), pero la
  correspondencia entre cada registro de elevación y cada paño/tramo FE no es
  inequívoca; la armadura pertenece al muro físico de la elevación.
- Los valores no legibles se listan explicitamente en el reporte.

Este modulo NO depende de OpenSeesPy ni del modelo combinado.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .reinforcement_types import (
    Resolution,
    RuleId,
    Status,
    WallOrientation,
    WallReinforcementClass,
    WallReinforcementRecord,
)

# ---------------------------------------------------------------------------
# Documentacion: planos y ejes
# ---------------------------------------------------------------------------
# Elevaciones 300 y 303: misma elevacion longitudinal principal LT1 a traves
# de estos ejes (texto legible en ambos PDFs).
PLAN_300_303_AXES: List[str] = ["E'", "E", "F", "F'", "G", "H", "I", "I'", "J"]

# Plano 301: elevaciones especiales e independientes (documentadas en el
# dominio del problema; solo algunas son legibles como texto en el PDF).
PLAN_301_ELEVATIONS: List[str] = ["1''", "1A", "1C", "1b", "1AA", "1BB"]

# Ejes inclinados/geometria variable: NO aproximar a muro tipico.
PLAN_301_GEOMETRY_SPECIAL: List[str] = ["1A", "1BB"]

# Anotaciones legibles del plano 301 (no se les asigno elevacion con
# certeza; se conservan como transcripcion literal).
LEGIBLE_ANNOTATIONS_301: List[str] = [
    "V.F. 15/225", "V. 15/125", "V. 15/VAR", "V. 20/80",
]

# Niveles del modelo LT1 usados para acotar los tramos (documentados en el
# modelo y en los planos): arranques desde FUNDACION_SUP; la elevacion 300
# cubre 1°S, 1°, 2°, 3°, 4° y el sector superior (CUBIERTA).
LEVEL_FUND = "FUNDACION_SUP"
LEVEL_1S = "PISO_1S"
LEVEL_1 = "PISO_1"
LEVEL_2 = "PISO_2"
LEVEL_3 = "PISO_3"
LEVEL_4 = "PISO_4"
LEVEL_CUBIERTA = "CUBIERTA"

# Tramos inter-nivel para empalmes documentados del edificio (empalmes por
# nivel presentes en las elevaciones de varios pisos).
LAP_SEGMENTS: List[tuple] = [
    (LEVEL_1S, LEVEL_1),
    (LEVEL_1, LEVEL_2),
    (LEVEL_2, LEVEL_3),
    (LEVEL_3, LEVEL_4),
]

_OBS_BOUNDARY = (
    "grupos de barras longitudinales de borde con cambios de cantidad y/o "
    "diametro entre pisos; cantidad/diametro y transiciones por nivel NO "
    "legibles en el PDF -> confirmar en pliego (no se infieren)."
)
_OBS_DIST_V = (
    "armadura distribuida vertical del alma; diametro/espaciamiento no "
    "legibles en el PDF -> sin valores inventados."
)
_OBS_DIST_H = (
    "armadura distribuida horizontal del alma; diametro/espaciamiento no "
    "legibles en el PDF -> sin valores inventados."
)
_OBS_LOCAL = (
    "refuerzos locales en encuentros viga-muro/losa, anclajes y detalles "
    "de extremos; posicion y valores no legibles -> confirmar."
)
_OBS_STARTER = (
    "refuerzo de arranque desde fundacion; cantidad/diametro/longitud de "
    "desarrollo no legibles -> confirmar."
)
_OBS_LAP = (
    "empalme de barra por nivel; longitud de empalme y ubicacion no "
    "legibles -> confirmar."
)
_OBS_SPECIAL = (
    "muro de geometria variable/inclinada; NO se aproxima a un muro "
    "rectangular tipico y su armadura no se copia de muros verticales "
    "(geometry_special=True)."
)

# Nota comun cuando un tramo de nivel no es legible en el PDF.
_LEVELS_NOT_LEGIBLE = (
    "limites/segmentos de nivel no legibles en el PDF (solo ejes/ESCALA "
    "1:50); no se inventan tramos: revisar por piso."
)


class _Seq:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}

    def next(self, sheet: str) -> int:
        self._n[sheet] = self._n.get(sheet, 0) + 1
        return self._n[sheet]


def _rec(s: _Seq, sheet: str, axis: str, level_start: str, level_end: str,
         classification: WallReinforcementClass,
         orientation: WallOrientation = WallOrientation.VERTICAL,
         note: str = "",
         status: Status = Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
         geometry_special: bool = False) -> WallReinforcementRecord:
    return WallReinforcementRecord(
        id=RuleId("LT1", f"2017_67-{sheet}-Model", sheet, s.next(sheet)),
        axis=axis,
        level_start=level_start,
        level_end=level_end,
        orientation=orientation,
        classification=classification,
        bar_count=None,
        diameter_mm=None,
        spacing_cm=None,
        length_cm=None,
        note=note,
        status=status,
        source="DRAWING_ELEVATION",
        geometry_special=geometry_special,
        geometry_pending=True,
        resolution=Resolution.RESOLVED_METADATA,
    )


# ---------------------------------------------------------------------------
# Plano 300: elevacion longitudinal principal (niveles 1°S..cubierta)
# ---------------------------------------------------------------------------
def _plano_300(s: _Seq) -> List[WallReinforcementRecord]:
    records: List[WallReinforcementRecord] = []
    for axis in PLAN_300_303_AXES:
        records.append(_rec(
            s, "300", axis, LEVEL_1S, LEVEL_CUBIERTA,
            WallReinforcementClass.BOUNDARY, note=_OBS_BOUNDARY))
        records.append(_rec(
            s, "300", axis, LEVEL_1S, LEVEL_CUBIERTA,
            WallReinforcementClass.DISTRIBUTED_VERTICAL,
            orientation=WallOrientation.VERTICAL, note=_OBS_DIST_V))
        records.append(_rec(
            s, "300", axis, LEVEL_1S, LEVEL_CUBIERTA,
            WallReinforcementClass.DISTRIBUTED_HORIZONTAL,
            orientation=WallOrientation.HORIZONTAL, note=_OBS_DIST_H))
        records.append(_rec(
            s, "300", axis, LEVEL_1S, LEVEL_CUBIERTA,
            WallReinforcementClass.LOCAL, note=_OBS_LOCAL
            + " Refuerzos alrededor de vigas (zonas VI/VF) cuando corresponden."))
        records.append(_rec(
            s, "300", axis, LEVEL_FUND, LEVEL_1S,
            WallReinforcementClass.STARTER, note=_OBS_STARTER))
        for l0, l1 in LAP_SEGMENTS:
            records.append(_rec(
                s, "300", axis, l0, l1,
                WallReinforcementClass.LAP, note=_OBS_LAP + f" {l0}-{l1}."))
    # detalle de seccion presente en la lamina
    records.append(WallReinforcementRecord(
        id=RuleId("LT1", "2017_67-300-Model", "300", s.next("300")),
        axis="CORTE A",
        level_start="",
        level_end="",
        classification=WallReinforcementClass.LOCAL,
        bar_count=None,
        diameter_mm=None,
        status=Status.DETAIL_FROM_DRAWING_REQUIRED,
        source="DRAWING_ELEVATION",
        note="CORTE A del plano 300 (detalle de seccion): distribucion "
             "transversal / refuerzo especial. Valores no legibles -> "
             "DETAIL_FROM_DRAWING_REQUIRED (no se modela sin el detalle).",
        geometry_pending=True,
        resolution=Resolution.RESOLVED_METADATA,
    ))
    return records


# ---------------------------------------------------------------------------
# Plano 301: elevaciones especiales e independientes
# ---------------------------------------------------------------------------
def _elevation_301_series(s: _Seq, sheet: str) -> List[WallReinforcementRecord]:
    records: List[WallReinforcementRecord] = []
    ann = " ; ".join(LEGIBLE_ANNOTATIONS_301)

    # --- EJE 1'' : varios pisos y cambios de armadura a lo largo de la
    # altura (NO una sola regla para toda la altura).
    records.append(_rec(
        s, sheet, "1''", LEVEL_1S, LEVEL_4,
        WallReinforcementClass.BOUNDARY, note=_OBS_BOUNDARY
        + " El eje se extiende por varios pisos con cambios de armadura a lo "
          "largo de la altura; limites exactos por nivel requieren el plano."))
    records.append(_rec(
        s, sheet, "1''", LEVEL_1S, LEVEL_4,
        WallReinforcementClass.DISTRIBUTED_VERTICAL,
        orientation=WallOrientation.VERTICAL, note=_OBS_DIST_V))
    records.append(_rec(
        s, sheet, "1''", LEVEL_1S, LEVEL_4,
        WallReinforcementClass.DISTRIBUTED_HORIZONTAL,
        orientation=WallOrientation.HORIZONTAL, note=_OBS_DIST_H))
    records.append(_rec(
        s, sheet, "1''", LEVEL_1S, LEVEL_4,
        WallReinforcementClass.LOCAL,
        note=_OBS_LOCAL + f" Anotaciones legibles del plano: {ann}."))
    records.append(_rec(
        s, sheet, "1''", LEVEL_FUND, LEVEL_1S,
        WallReinforcementClass.STARTER, note=_OBS_STARTER))
    for l0, l1 in LAP_SEGMENTS:
        records.append(_rec(
            s, sheet, "1''", l0, l1,
            WallReinforcementClass.LAP, note=_OBS_LAP + f" {l0}-{l1}."))

    # --- EJE 1A : geometria inclinada/variable (marcador de nivel "1º").
    records.append(_rec(
        s, sheet, "1A", LEVEL_1, "",
        WallReinforcementClass.SPECIAL_GEOMETRY,
        note=_OBS_SPECIAL + " Marcador de nivel legible: 1° (PISO_1).",
        geometry_special=True))
    records.append(_rec(
        s, sheet, "1A", LEVEL_1, "",
        WallReinforcementClass.BOUNDARY,
        note=_OBS_BOUNDARY + _OBS_SPECIAL, geometry_special=True))
    records.append(_rec(
        s, sheet, "1A", LEVEL_1, "",
        WallReinforcementClass.DISTRIBUTED_VERTICAL,
        orientation=WallOrientation.VERTICAL,
        note=_OBS_DIST_V + _OBS_SPECIAL, geometry_special=True))
    records.append(_rec(
        s, sheet, "1A", LEVEL_1, "",
        WallReinforcementClass.DISTRIBUTED_HORIZONTAL,
        orientation=WallOrientation.HORIZONTAL,
        note=_OBS_DIST_H + _OBS_SPECIAL, geometry_special=True))
    records.append(_rec(
        s, sheet, "1A", LEVEL_1, "",
        WallReinforcementClass.LOCAL,
        note=_OBS_LOCAL + _OBS_SPECIAL, geometry_special=True))

    # --- EJE 1BB : geometria inclinada/variable (sin niveles legibles).
    for cls in (WallReinforcementClass.SPECIAL_GEOMETRY,
                WallReinforcementClass.BOUNDARY,
                WallReinforcementClass.DISTRIBUTED_VERTICAL,
                WallReinforcementClass.DISTRIBUTED_HORIZONTAL,
                WallReinforcementClass.LOCAL):
        ori = (WallOrientation.VERTICAL if cls
               in (WallReinforcementClass.BOUNDARY,
                   WallReinforcementClass.DISTRIBUTED_VERTICAL)
               else WallOrientation.HORIZONTAL)
        notes = {
            WallReinforcementClass.SPECIAL_GEOMETRY: _OBS_SPECIAL,
            WallReinforcementClass.BOUNDARY: _OBS_BOUNDARY + _OBS_SPECIAL,
            WallReinforcementClass.DISTRIBUTED_VERTICAL: _OBS_DIST_V + _OBS_SPECIAL,
            WallReinforcementClass.DISTRIBUTED_HORIZONTAL: _OBS_DIST_H + _OBS_SPECIAL,
            WallReinforcementClass.LOCAL: _OBS_LOCAL + _OBS_SPECIAL,
        }
        records.append(_rec(
            s, sheet, "1BB", "", "", cls, orientation=ori,
            note=notes[cls] + " " + _LEVELS_NOT_LEGIBLE,
            geometry_special=True))

    # --- EJE 1C : elevacion independiente (nombre legible; sin niveles).
    for cls, ori, obs in (
        (WallReinforcementClass.BOUNDARY, WallOrientation.VERTICAL, _OBS_BOUNDARY),
        (WallReinforcementClass.DISTRIBUTED_VERTICAL, WallOrientation.VERTICAL, _OBS_DIST_V),
        (WallReinforcementClass.DISTRIBUTED_HORIZONTAL, WallOrientation.HORIZONTAL, _OBS_DIST_H),
        (WallReinforcementClass.LOCAL, WallOrientation.VERTICAL, _OBS_LOCAL),
    ):
        records.append(_rec(s, sheet, "1C", "", "", cls,
                            orientation=ori,
                            note=obs + " " + _LEVELS_NOT_LEGIBLE))

    # --- EJE 1b : muro longitudinal en nivel inferior (marcador "1°S").
    records.append(_rec(
        s, sheet, "1b", LEVEL_1S, LEVEL_1S,
        WallReinforcementClass.BOUNDARY, note=_OBS_BOUNDARY
        + " Muro longitudinal en nivel inferior (marcador 1°S legible)."))
    records.append(_rec(
        s, sheet, "1b", LEVEL_1S, LEVEL_1S,
        WallReinforcementClass.DISTRIBUTED_VERTICAL,
        orientation=WallOrientation.VERTICAL, note=_OBS_DIST_V))
    records.append(_rec(
        s, sheet, "1b", LEVEL_1S, LEVEL_1S,
        WallReinforcementClass.DISTRIBUTED_HORIZONTAL,
        orientation=WallOrientation.HORIZONTAL, note=_OBS_DIST_H))
    records.append(_rec(
        s, sheet, "1b", LEVEL_1S, LEVEL_1S,
        WallReinforcementClass.LOCAL, note=_OBS_LOCAL))
    records.append(_rec(
        s, sheet, "1b", LEVEL_FUND, LEVEL_1S,
        WallReinforcementClass.STARTER, note=_OBS_STARTER))

    # --- EJE 1AA : elevacion independiente (sin niveles legibles).
    for cls, ori, obs in (
        (WallReinforcementClass.BOUNDARY, WallOrientation.VERTICAL, _OBS_BOUNDARY),
        (WallReinforcementClass.DISTRIBUTED_VERTICAL, WallOrientation.VERTICAL, _OBS_DIST_V),
        (WallReinforcementClass.DISTRIBUTED_HORIZONTAL, WallOrientation.HORIZONTAL, _OBS_DIST_H),
        (WallReinforcementClass.LOCAL, WallOrientation.VERTICAL, _OBS_LOCAL),
    ):
        records.append(_rec(s, sheet, "1AA", "", "", cls,
                            orientation=ori,
                            note=obs + " " + _LEVELS_NOT_LEGIBLE))

    return records


# ---------------------------------------------------------------------------
# Plano 302: elevacion completa, familia independiente
# ---------------------------------------------------------------------------
def _plano_302(s: _Seq) -> List[WallReinforcementRecord]:
    # Sin ejes ni niveles legibles en el PDF: se registra la elevacion como
    # familia independiente de muros LT1.
    records: List[WallReinforcementRecord] = []
    for cls, ori, obs in (
        (WallReinforcementClass.BOUNDARY, WallOrientation.VERTICAL, _OBS_BOUNDARY),
        (WallReinforcementClass.DISTRIBUTED_VERTICAL, WallOrientation.VERTICAL, _OBS_DIST_V),
        (WallReinforcementClass.DISTRIBUTED_HORIZONTAL, WallOrientation.HORIZONTAL, _OBS_DIST_H),
        (WallReinforcementClass.LOCAL, WallOrientation.VERTICAL, _OBS_LOCAL),
        (WallReinforcementClass.STARTER, WallOrientation.VERTICAL, _OBS_STARTER),
        (WallReinforcementClass.LAP, WallOrientation.VERTICAL, _OBS_LAP),
    ):
        records.append(_rec(
            s, "302", "", "", "", cls, orientation=ori,
            note=f"Familia independiente de la elevacion 302. {obs} "
                 f"{_LEVELS_NOT_LEGIBLE} Los vanos/pisos, barras que parten "
                 f"o terminan, y refuerzos de nudo se leen por elevacion."))
    return records


# ---------------------------------------------------------------------------
# Plano 303: elevacion larga E',E,...,J (varios niveles)
# ---------------------------------------------------------------------------
def _plano_303(s: _Seq) -> List[WallReinforcementRecord]:
    records: List[WallReinforcementRecord] = []
    for axis in PLAN_300_303_AXES:
        records.append(_rec(
            s, "303", axis, "", "",
            WallReinforcementClass.BOUNDARY,
            note=_OBS_BOUNDARY + " Elevacion larga con varios niveles; " + _LEVELS_NOT_LEGIBLE))
        records.append(_rec(
            s, "303", axis, "", "",
            WallReinforcementClass.DISTRIBUTED_VERTICAL,
            orientation=WallOrientation.VERTICAL,
            note=_OBS_DIST_V + " " + _LEVELS_NOT_LEGIBLE))
        records.append(_rec(
            s, "303", axis, "", "",
            WallReinforcementClass.DISTRIBUTED_HORIZONTAL,
            orientation=WallOrientation.HORIZONTAL,
            note=_OBS_DIST_H + " " + _LEVELS_NOT_LEGIBLE))
        records.append(_rec(
            s, "303", axis, "", "",
            WallReinforcementClass.LOCAL,
            note=_OBS_LOCAL + " Refuerzos de extremo/interiores/nudos segun elevacion; "
            + _LEVELS_NOT_LEGIBLE))
        records.append(_rec(
            s, "303", axis, LEVEL_FUND, LEVEL_1S,
            WallReinforcementClass.STARTER, note=_OBS_STARTER
            + " Sectores inferiores/fundacion de la elevacion."))
    return records


# ---------------------------------------------------------------------------
# Dataset compilado
# ---------------------------------------------------------------------------
def load_lt1_wall_data() -> Dict[str, List]:
    """Registros especificos de muro LT1 por elevacion (300-303).

    Retorna la lista plana de registros en ``records`` y, en ``metadata``,
    la documentacion de las fuentes y de lo legible/ilegible de cada plano.
    """
    s = _Seq()
    records: List[WallReinforcementRecord] = []
    records.extend(_plano_300(s))
    records.extend(_elevation_301_series(s, "301"))
    records.extend(_plano_302(s))
    records.extend(_plano_303(s))
    return {
        "records": records,
        "metadata": {
            "legible_annotations_301": LEGIBLE_ANNOTATIONS_301,
            "plano_300_303_axes": PLAN_300_303_AXES,
            "plano_301_elevations": PLAN_301_ELEVATIONS,
            "niveles_modelo": [
                LEVEL_FUND, LEVEL_1S, LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4,
                LEVEL_CUBIERTA,
            ],
        },
    }


if __name__ == "__main__":
    import sys

    data = load_lt1_wall_data()
    print("Registros especificos de muro LT1:", len(data["records"]))
    by_sheet: Dict[str, int] = {}
    for r in data["records"]:
        by_sheet[r.id.sheet] = by_sheet.get(r.id.sheet, 0) + 1
    print("Por plano:", by_sheet)
    sys.exit(0)
