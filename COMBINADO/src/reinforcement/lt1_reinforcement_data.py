"""Dataset de armadura LT1 levantada desde los planos.

TRANSCRIPCION FIEL del levantamiento manual de la serie de planos LT1.
Cada regla conserva: dibujo, nivel/floor, capa (lower/upper), direccion,
zona textual EXACTA del plano, diametro, espaciamiento, clasificacion y
estado de confianza (conservando la lectura del plano sin reinterpretar).

CONVENCIONES DE LA TRANSCRIPCION:
- phase: "\u0424" unicode (fi). Se conserva en textos; los campos
  numericos son integers en mm y cm.
- Cuando el plano dice "malla general" se usa Layer.BOTH, Direction.BOTH
  (malla de ambas caras, tanto sentido), salvo que la zona especifique
  capa superior/inferior (202-S/202-I, 203-205 superior/inferior).
- Los refuerzos locales (F=, cruces, cuadrado central, rectangulo
  central, bordes) NO reemplazan la malla: van como LOCAL y se resaltan.
- Estribos detectados en losa (viga/eje, zostra, "Eje") se clasifican
  STIRRUP con NEEDS_NOTATION_CONFIRMATION: no reinterpretar.
- Vigas (serie 400) se transcribieron inicialmente como familia
  REPRESENTATIVE; quedan marcadas SUPERSEDED_BY_EXACT_BEAM_DRAWINGS tras
  levantar la armadura EXACTA por viga de los planos 400/401/402
  (lt1_beam_data). Sus BeamRule aqui son SOLO referencia historica.
- Escaleras (serie 500): metadata con DETAIL_FROM_DRAWING_REQUIRED.
- Muros (serie 300): el patron tipico inicial queda
  SUPERSEDED_BY_EXACT_WALL_ELEVATIONS; los registros especificos por
  elevacion/eje/nivel de 300-303 viven en `lt1_wall_data`.

Este modulo NO depende de OpenSeesPy ni del modelo combinado.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .reinforcement_types import (
    BeamRule,
    Classification,
    ColumnBarType,
    ColumnReinforcementRule,
    Direction,
    Layer,
    LocalBarRule,
    MeshRule,
    RuleId,
    StairRule,
    Status,
    WallRule,
    Zone,
    ZoneKind,
)

# ---------------------------------------------------------------------------
# Planos (sheet) -> nivel del LT1 "cielo" que cubre cada dibujo.
# Mapeo DECIDIDO: 200 fundacion base; 201 losa cielo 1° sub = primer piso
# habitado (PISO_1); 202 cielo 1° piso = PISO_1 (misma losa superior/inf);
# 203=2°, 204=3°, 205=4°. Las losas superior/inferior del MISMO plano se
# asientan sobre el mismo nivel.
# ---------------------------------------------------------------------------
FLOOR_TO_LEVEL: Dict[str, str] = {
    "200-I": "FUNDACION_SUP",
    "200-S": "FUNDACION_SUP",
    "201": "PISO_1",
    "202-S": "PISO_1",
    "202-I": "PISO_1",
    "203": "PISO_2",
    "204": "PISO_3",
    "205": "PISO_4",
}

FLOOR_TO_LEVEL_UNCONFIRMED = {"201", "202-S", "202-I", "203", "204", "205"}

DRAWING_TITLES: Dict[str, str] = {
    "200-I": "FUNDACION INFERIOR",
    "200-S": "FUNDACION SUPERIOR",
    "201": "LOSA CIELO 1° SUBTERRANEO",
    "202-S": "LOSA CIELO 1° PISO (SUPERIOR/INFERIOR)",
    "202-I": "LOSA CIELO 1° PISO (SUPERIOR/INFERIOR)",
    "203": "LOSA CIELO 2° PISO",
    "204": "LOSA CIELO 3° PISO",
    "205": "LOSA CIELO 4° PISO",
    "300": "MUROS (patron tipico reemplazado por elevaciones 300-303)",
    "400": "VIGAS (familia representativa)",
    "500": "ESCALERAS",
}

# Abreviaturas de los planos de vigas (no se reinterpretan).
BEAM_FAMILY_TYPICAL = "V.80/80 (incluye V100/V101)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class _Seq:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}

    def next(self, sheet: str) -> int:
        self._n[sheet] = self._n.get(sheet, 0) + 1
        return self._n[sheet]


def _mesh(s: _Seq, sheet: str, layer: Layer, direction: Direction,
          zone_text: str, dia: int, spc: int, *,
          classification: Classification = Classification.MESH,
          status: Status = Status.EXACT,
          note: str = "", length_cm: Optional[int] = None) -> MeshRule:
    return MeshRule(
        id=RuleId("LT1", f"2017_67-{sheet}-Model", sheet, s.next(sheet)),
        layer=layer,
        direction=direction,
        zone=Zone(kind=ZoneKind.FREE_TEXT, text=zone_text),
        diameter_mm=dia,
        spacing_cm=spc,
        classification=classification,
        status=status,
        floor=DRAWING_TITLES.get(sheet, sheet),
        length_cm=length_cm,
        note=note,
    )


def _local(s: _Seq, sheet: str, zone_text: str, bar_count: Optional[int],
           dia: int, *,
           classification: Classification = Classification.LOCAL,
           status: Status = Status.EXACT,
           direction: Direction = Direction.BOTH,
           note: str = "", length_cm: Optional[int] = None,
           spacing_cm: Optional[int] = None) -> LocalBarRule:
    return LocalBarRule(
        id=RuleId("LT1", f"2017_67-{sheet}-Model", sheet, s.next(sheet)),
        direction=direction,
        zone=Zone(kind=ZoneKind.FREE_TEXT, text=zone_text),
        bar_count=bar_count,
        diameter_mm=dia,
        classification=classification,
        status=status,
        floor=DRAWING_TITLES.get(sheet, sheet),
        length_cm=length_cm,
        spacing_cm=spacing_cm,
        note=note,
    )


# ---------------------------------------------------------------------------
# SERIE 200 - FUNDACIONES
# ---------------------------------------------------------------------------
def _fundaciones() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []

    # ---- 200-I (malla inferior de fundacion) ----
    meshes.append(_mesh(s, "200-I", Layer.BOTH, Direction.BOTH,
                        "malla general inferior", 12, 20))
    meshes.append(_mesh(s, "200-I", Layer.BOTH, Direction.BOTH,
                        "E-F/1-2", 12, 12))
    meshes.append(_mesh(s, "200-I", Layer.BOTH, Direction.BOTH,
                        "E-F/2-3", 22, 13))
    meshes.append(_mesh(s, "200-I", Layer.BOTH, Direction.BOTH,
                        "H-IB/hasta 1BB", 12, 20,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="ejes H-IB y 'hasta 1BB' requieren exacta del plano"))
    meshes.append(_mesh(s, "200-I", Layer.BOTH, Direction.BOTH,
                        "H1-H2/1-1BB", 12, 20,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="ejes H1-H2 / 1-1BB requieren exacta del plano"))

    # Locales 200-I
    locals_.append(_local(s, "200-I", "local F", None, 12,
                          note="local interior sobre eje F"))
    locals_.append(_local(s, "200-I", "local F", None, 18,
                          note="local interior sobre eje F"))
    locals_.append(_local(s, "200-I", "local F (dos direcciones)", None, 18,
                          note="barra de refuerzo alrededor de apoyo, dos direcciones"))
    locals_.append(_local(s, "200-I", "local F =L=490cm (50+390+50)", None, 18,
                          length_cm=490,
                          note="longitud explicita del plano 50+390+50 cm"))

    # ---- 200-S (malla superior de fundacion) ----
    meshes.append(_mesh(s, "200-S", Layer.BOTH, Direction.BOTH,
                        "malla general superior", 12, 20))
    meshes.append(_mesh(s, "200-S", Layer.BOTH, Direction.BOTH,
                        "E-F/8-1", 12, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje '8' fuera de la grilla modelada LT1"))
    meshes.append(_mesh(s, "200-S", Layer.BOTH, Direction.BOTH,
                        "1-1C/H1-1B", 12, 12,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="ejes 1C/H1/1B fuera de la grilla modelada LT1"))
    meshes.append(_mesh(s, "200-S", Layer.BOTH, Direction.BOTH,
                        "1-1C/H1-1B", 12, 10,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="ejes 1C/H1/1B fuera de la grilla modelada LT1"))
    meshes.append(_mesh(s, "200-S", Layer.BOTH, Direction.BOTH,
                        "E-F/2-3", 16, 14,
                        classification=Classification.STIRRUP,
                        status=Status.NEEDS_NOTATION_CONFIRMATION,
                        note="podria tratarse de estribos, no de malla"))
    meshes.append(_mesh(s, "200-S", Layer.BOTH, Direction.BOTH,
                        "E-F/2-3", 12, 12,
                        classification=Classification.STIRRUP,
                        status=Status.NEEDS_NOTATION_CONFIRMATION,
                        note="podria tratarse de estribos, no de malla"))
    meshes.append(_mesh(s, "200-S", Layer.BOTH, Direction.BOTH,
                        "I-IB/2-3", 12, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje IB fuera de la grilla modelada LT1"))
    return meshes, locals_


# ---------------------------------------------------------------------------
# SERIE 201 - LOSA CIELO 1° SUBTERRANEO (SUP = INF)
# ---------------------------------------------------------------------------
def _losa_201() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "malla general (equivalente sup=inf)", 8, 18))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "3-2/E-F", 8, 18))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "3-2/E-F", 10, 14))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "E-F/1-2", 8, 18))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "E-F/1-2", 8, 14))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "E-F/1-2", 8, 16))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "E-F/1-2", 10, 18))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "eje 1", 8, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja sobre eje 1; ancho de franja del plano"))
    meshes.append(_mesh(s, "201", Layer.BOTH, Direction.BOTH,
                        "1-8/E-Ga", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="ejes 8 y Ga fuera de la grilla modelada LT1"))
    return meshes, []


# ---------------------------------------------------------------------------
# SERIE 202 - LOSA CIELO 1° PISO
# ---------------------------------------------------------------------------
def _losa_202() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []

    # ---- 202-S (malla superior) ----
    meshes.append(_mesh(s, "202-S", Layer.UPPER, Direction.BOTH,
                        "malla general superior", 10, 10))
    meshes.append(_mesh(s, "202-S", Layer.UPPER, Direction.BOTH,
                        "eje I", 12, 12,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja sobre eje I"))
    meshes.append(_mesh(s, "202-S", Layer.UPPER, Direction.BOTH,
                        "eje IB", 10, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje IB fuera de la grilla modelada LT1"))
    meshes.append(_mesh(s, "202-S", Layer.UPPER, Direction.BOTH,
                        "eje I'", 10, 15,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja interna/externa de I'; mapeo exacto de plano"))
    meshes.append(_mesh(s, "202-S", Layer.UPPER, Direction.BOTH,
                        "eje I'", 10, 12,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja interna/externa de I'; mapeo exacto de plano"))
    meshes.append(_mesh(s, "202-S", Layer.UPPER, Direction.BOTH,
                        "eje 2a", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje 2a secundario fuera de la grilla modelada LT1"))
    meshes.append(_mesh(s, "202-S", Layer.UPPER, Direction.BOTH,
                        "sector eje 3 hacia abajo + F-G, losa 111", 16, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="zona 'hacia abajo del eje 3' no modelada en LT1"))

    # ---- 202-I (malla inferior) ----
    meshes.append(_mesh(s, "202-I", Layer.LOWER, Direction.X,
                        "malla general inferior X", 10, 18))
    meshes.append(_mesh(s, "202-I", Layer.LOWER, Direction.Y,
                        "malla general inferior Y", 8, 18))
    meshes.append(_mesh(s, "202-I", Layer.LOWER, Direction.X,
                        "F-G bajo eje 3", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="'bajo eje 3' no modelado en LT1"))
    meshes.append(_mesh(s, "202-I", Layer.LOWER, Direction.Y,
                        "F-G bajo eje 3", 10, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="'bajo eje 3' no modelado en LT1"))
    meshes.append(_mesh(s, "202-I", Layer.LOWER, Direction.BOTH,
                        "E-F/1-2 base", 8, 18))
    meshes.append(_mesh(s, "202-I", Layer.LOWER, Direction.BOTH,
                        "E-F/1-2 base", 8, 18))
    locals_: List[LocalBarRule] = [
        _local(s, "202-I", "E-F/1-2 local rect", 2, 16,
               note="local sobre la malla base"),
        _local(s, "202-I", "E-F/2-3 central X", 2, 16,
               direction=Direction.X),
        _local(s, "202-I", "E-F/2-3 central Y", 1, 16,
               direction=Direction.Y),
    ]
    return meshes, locals_


# ---------------------------------------------------------------------------
# SERIE 203 - LOSA CIELO 2° PISO
# ---------------------------------------------------------------------------
def _losa_203() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []

    # ---- 203 INFERIOR ----
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.Y,
                        "malla inferior Y predominante", 8, 18))
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.X,
                        "malla X 1-2", 10, 18))
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.X,
                        "malla X 2-3", 10, 20))
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.BOTH,
                        "eje 1", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja sobre eje 1"))
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.X,
                        "Losa 219 (entre F-G, hacia abajo eje 3)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 219 / 'hacia abajo de eje 3' no modelada"))
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.Y,
                        "Losa 219 (entre F-G, hacia abajo eje 3)", 10, 12,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 219 / 'hacia abajo de eje 3' no modelada"))
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.X,
                        "Losas 220 y 221", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losas 220/221 no mapeadas a grilla modelada"))
    meshes.append(_mesh(s, "203", Layer.LOWER, Direction.Y,
                        "Losas 220 y 221", 8, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losas 220/221 no mapeadas a grilla modelada"))

    locals_: List[LocalBarRule] = [
        _local(s, "203", "esquina/borde eje 1 (F=F')", 1, 16,
               note="1Φ16 en esquinas y bordes del eje 1"),
        _local(s, "203", "E-F/1-2 cuadrado central", 2, 16),
        _local(s, "203", "E-F/2-3 X", 1, 16, direction=Direction.X),
        _local(s, "203", "E-F/2-3 Y", 2, 16, direction=Direction.Y),
    ]

    # ---- 203 SUPERIOR ----
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "eje I (1-2)", 12, 12))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "eje I (2-3)", 12, 14))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "ejes I',H,G,F,E", 10, 10))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "eje 1", 10, 16,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja sobre eje 1"))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "eje 2", 10, 12))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "eje 3", 10, 12))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.X,
                        "Losas 220 y 221 (X)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losas 220/221 no mapeadas a grilla modelada"))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.Y,
                        "Losas 220 y 221 (Y)", 8, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losas 220/221 no mapeadas a grilla modelada"))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.X,
                        "Losa 219 (X)", 12, 12,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 219 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.Y,
                        "Losa 219 (Y)", 10, 10,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 219 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "E-F/1-2 cuadrado central", 10, 15))
    meshes.append(_mesh(s, "203", Layer.UPPER, Direction.BOTH,
                        "E-F/2-3 rectangulo central", 8, 18))
    return meshes, locals_


# ---------------------------------------------------------------------------
# SERIE 204 - LOSA CIELO 3° PISO
# ---------------------------------------------------------------------------
def _losa_204() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []

    # ---- 204 INFERIOR ----
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.BOTH,
                        "viga/eje 1", 8, 18,
                        classification=Classification.STIRRUP,
                        status=Status.NEEDS_NOTATION_CONFIRMATION,
                        note="parece estribo, no malla"))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.BOTH,
                        "viga/eje 3", 8, 16,
                        classification=Classification.STIRRUP,
                        status=Status.NEEDS_NOTATION_CONFIRMATION,
                        note="parece estribo, no malla"))
    locals_.append(_local(s, "204", "borde superior", 1, 16))
    locals_.append(_local(s, "204", "E-F/2-3 rectangulo central", 2, 16))
    locals_.append(_local(s, "204", "E-F/1-2 cuadrado central", 2, 16))

    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.X,
                        "Losas 313 y 314 (X)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losas 313/314 no mapeadas a grilla modelada"))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.X,
                        "Losa 324 (X)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 324 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.Y,
                        "Losa 324 (Y)", 10, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 324 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.BOTH,
                        "entre 1-2, eje J", 8, 20,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje J fuera de la grilla modelada LT1"))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.BOTH,
                        "entre 1-2, eje I'", 8, 20,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja interior/exterior I'"))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.BOTH,
                        "resto ejes Y", 8, 18))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.X,
                        "Losa 315 (X)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 315 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "204", Layer.LOWER, Direction.Y,
                        "Losa 315 (Y)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 315 no mapeada a grilla modelada"))

    # ---- 204 SUPERIOR ----
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.BOTH, "eje 2", 10, 15))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.BOTH, "eje 3", 10, 15))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.BOTH, "eje 1", 8, 12))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.Y,
                        "Losa 311 (Y)", 10, 16))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.Y,
                        "Losa 322 (Y)", 10, 16))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.Y,
                        "Losa 324 (Y)", 16, 14))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.BOTH,
                        "Losa 315", 8, 18))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.X,
                        "Losa 311/322/324/315 (X)", 8, 12,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="X de losa 311-315/324 se lee del plano; ancho exacto pendiente"))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.BOTH,
                        "E-F/2-3 rectangulo central", 8, 12))
    meshes.append(_mesh(s, "204", Layer.UPPER, Direction.BOTH,
                        "E-F/1-2 cuadrado central", 10, 15))
    return meshes, locals_


# ---------------------------------------------------------------------------
# SERIE 205 - LOSA CIELO 4° PISO
# ---------------------------------------------------------------------------
def _losa_205() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []

    # ---- 205 INFERIOR ----
    meshes.append(_mesh(s, "205", Layer.LOWER, Direction.X,
                        "malla general inferior X", 8, 14))
    meshes.append(_mesh(s, "205", Layer.LOWER, Direction.Y,
                        "malla general inferior Y", 8, 18))
    meshes.append(_mesh(s, "205", Layer.LOWER, Direction.BOTH,
                        "ejes J e I'", 8, 20,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje J fuera de la grilla modelada LT1"))
    meshes.append(_mesh(s, "205", Layer.LOWER, Direction.X,
                        "Losa 426 (X)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 426 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "205", Layer.LOWER, Direction.Y,
                        "Losa 426 (Y)", 8, 13,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 426 no mapeada a grilla modelada"))
    locals_.append(_local(s, "205", "cuadrados con cruces 1Φ16", 1, 16))
    locals_.append(_local(s, "205", "losa 404 sector eje 2a (semicuadrado)", 2, 16,
                          status=Status.NEEDS_EXACT_ZONE_MAPPING,
                          note="losa 404/eje 2a fuera de la grilla modelada"))
    locals_.append(_local(s, "205", "eje 1''", 2, 16,
                          status=Status.NEEDS_EXACT_ZONE_MAPPING,
                          note="eje 1'' no esta en la grilla modelada LT1"))

    # ---- 205 SUPERIOR ----
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.X,
                        "Losa 426 (X)", 12, 13,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 426 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.Y,
                        "Losa 426 (Y)", 10, 15,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 426 no mapeada a grilla modelada"))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "eje 1", 8, 15,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="franja sobre eje 1"))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "parte exterior eje 1", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="borde exterior del eje 1; profundidad del plano"))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.X,
                        "Losas 415 y 416 (X)", 8, 12))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.Y,
                        "Losas 415 y 416 (Y)", 10, 11))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "cuadrados con cruz", 8, 15))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "eje I (1-2)", 10, 13))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "eje I (2-3)", 10, 15))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH, "eje 2", 10, 15))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "eje H (1-2)", 10, 13))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "eje H (2-3)", 10, 15))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH, "eje G", 10, 13))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH, "eje F", 10, 16))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "eje 1''", 8, 13,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje 1'' no esta en la grilla modelada LT1"))
    meshes.append(_mesh(s, "205", Layer.UPPER, Direction.BOTH,
                        "eje 2a", 10, 16,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje 2a no esta en la grilla modelada LT1"))
    return meshes, locals_


# ---------------------------------------------------------------------------
# SERIE 300 - MUROS
# ---------------------------------------------------------------------------
def _muros() -> List[WallRule]:
    s = _Seq()
    return [
        WallRule(
            id=RuleId("LT1", "2017_67-300-Model", "300", s.next("300")),
            zone=Zone(kind=ZoneKind.GENERAL, text="todos los muros LT1 (tipicos)"),
            notation="E + 6T B10@10 ; M.H.A e=20 ; D.M.V B10@12 ; D.M.V B10@20",
            status=Status.SUPERSEDED_BY_EXACT_WALL_ELEVATIONS,
            note="Nomenclatura literal del plano levantada en la transcripcion "
                 "inicial como patron tipico unico para todos los muros LT1. "
                 "SUSPENDIDA como fuente activa de asignacion: NO todos los "
                 "muros tienen la misma armadura. Reemplazada por los "
                 "registros especificos por elevacion/eje/nivel de las "
                 "elevaciones 300-303 (`lt1_wall_data`). Conservada SOLO "
                 "como referencia historica/trazabilidad; no genera geometria.",
        )
    ]


# ---------------------------------------------------------------------------
# COLUMNAS LT1 - armadura longitudinal (dato confirmado por usuario)
# ---------------------------------------------------------------------------
def _columnas() -> List[ColumnReinforcementRule]:
    s = _Seq()
    return [
        ColumnReinforcementRule(
            id=RuleId("LT1", "CONFIRMADO-USUARIO", "COL", s.next("COL")),
            bar_count=16,
            diameter_mm=22,
            bar_type=ColumnBarType.LONGITUDINAL,
            section="P. 70x70 (seccion del modelo LT1)",
            classification=Classification.COLUMN,
            status=Status.EXACT,
            source="USER_CONFIRMED_DRAWING_DATA",
            geometry_pending=True,
            note="Todas las columnas LT1: 16 B22 longitudinales. No se "
                 "inventan estribos, recubrimiento ni distribucion transversal "
                 "de las 16 barras (no definida); la geometria 3D queda "
                 "pendiente hasta confirmar seccion/cubierta.",
        ),
    ]


# ---------------------------------------------------------------------------
# SERIE 400 - VIGAS (familia representativa)
# ---------------------------------------------------------------------------
def _vigas() -> List[BeamRule]:
    s = _Seq()
    return [
        BeamRule(
            id=RuleId("LT1", "2017_67-400-Model", "400", s.next("400")),
            zone=Zone(kind=ZoneKind.FREE_TEXT,
                      text="familia tipica de vigas (tramo medio)"),
            family=BEAM_FAMILY_TYPICAL,
            longitudinal_mm="2 B22 (longitudinales)",
            stirrup_notation="ED B10@10 / ED B10@20 ; 17ED B10@10 en sectores",
            status=Status.SUPERSEDED_BY_EXACT_BEAM_DRAWINGS,
            note="Registrada como familia REPRESENTATIVE en la trans. inicial; "
                 "SUSPENDIDA como fuente de asignacion porque diverge de la "
                 "armadura real por viga de los planos 400/401/402. Conservada "
                 "como referencia historica; NO se usa para geometria.",
        ),
        BeamRule(
            id=RuleId("LT1", "2017_67-400-Model", "400", s.next("400")),
            zone=Zone(kind=ZoneKind.FREE_TEXT,
                      text="seccion transversal especial (2 B18 + 4 B16 + 2/1 B10)"),
            family=BEAM_FAMILY_TYPICAL,
            longitudinal_mm="2 B18 + 4 B16 + (2 B10 / 1 B10)",
            stirrup_notation="E B10@10",
            status=Status.SUPERSEDED_BY_EXACT_BEAM_DRAWINGS,
            note="Casos especiales del plano (V0102, seccion escalonada 402). "
                 "SUSPENDIDA como familia tipica; los detalles reales por viga "
                 "se registran en lt1_beam_data (planos 400/401/402).",
        ),
    ]


# ---------------------------------------------------------------------------
# SERIE 500 - ESCALERAS
# ---------------------------------------------------------------------------
def _escaleras() -> List[StairRule]:
    s = _Seq()
    return [
        StairRule(
            id=RuleId("LT1", "2017_67-500-Model", "500", s.next("500")),
            zone=Zone(kind=ZoneKind.FREE_TEXT,
                      text="escaleras LT1 (metadatos)"),
            status=Status.DETAIL_FROM_DRAWING_REQUIRED,
            note="longitudinal sobre rampas, descansos, refuerzos en "
                 "encuentros/apoyos; se detalla en plantas y cortes del plano. "
                 "No se dibujan barras sin el detalle.",
        ),
        StairRule(
            id=RuleId("LT1", "2017_67-500-Model", "500", s.next("500")),
            zone=Zone(kind=ZoneKind.FREE_TEXT, text="escaleras LT1 (2ª via)"),
            status=Status.DETAIL_FROM_DRAWING_REQUIRED,
            note="misma serie 500; verificar rampas y descansos en el plano.",
        ),
    ]


# ---------------------------------------------------------------------------
# Dataset compilado
# ---------------------------------------------------------------------------
def load_lt1_reinforcement() -> Dict[str, List]:
    """Retorna todo el dataset LT1 agrupado por tipo."""
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []
    for fn in (_fundaciones, _losa_201, _losa_202, _losa_203,
               _losa_204, _losa_205):
        m, l = fn()
        meshes.extend(x for x in m if isinstance(x, MeshRule))
        locals_.extend(x for x in l if isinstance(x, LocalBarRule))
    return {
        "mesh": meshes,
        "local": locals_,
        "walls": _muros(),
        "columns": _columnas(),
        "beams": _vigas(),
        "stairs": _escaleras(),
    }


if __name__ == "__main__":
    import sys

    data = load_lt1_reinforcement()
    print("Conteos por categoria:")
    for key, rules in data.items():
        print(f"  {key}: {len(rules)}")
    print("Total reglas:", sum(len(v) for v in data.values()))
    sys.exit(0)