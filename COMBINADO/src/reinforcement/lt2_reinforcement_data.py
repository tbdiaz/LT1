"""Dataset de armadura LT2 levantada desde los planos 200/201/202 y columnas.

TRANSCRIPCION FIEL del levantamiento manual de la serie de planos LT2
(200I/200S fundaciones; 201I/201S losas; 202I/202S losa cielo piso 4°),
sin reinterpretar. Los valores numericos (diametro/espaciamiento) se
conservan tal cual; las zonas que el plano no permite localizar
exactamente se marcan NEEDS_EXACT_ZONE_MAPPING y NO se asignan a
geometria.

CONVENCIONES DE DIRECCION EN LAS LOSAS/FUNDACIONES LT2:
- "ejes horizontales" / "direccion horizontal": barras PARALELAS a los
  ejes horizontales del plano -> Direction.X.
- "ejes verticales" / "direccion vertical": barras PARALELAS a los ejes
  verticales del plano -> Direction.Y.
- Regla de eje o excepcion: prevalece sobre la malla general en su
  franja; se conserva como regla separada (NO se fusiona).
- Las excepciones "losa 01xx toda la losa" no son adicionales: rigen en
  el area de esa losa (no se mapeo numero de losa -> grilla del modelo,
  por eso NEEDS_EXACT_ZONE_MAPPING).

Este modulo NO depende de OpenSeesPy ni del modelo combinado.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .reinforcement_types import (
    Classification,
    ColumnBarType,
    ColumnReinforcementRule,
    Direction,
    Layer,
    LocalBarRule,
    MeshRule,
    RuleId,
    Status,
    Zone,
    ZoneKind,
)

# ---------------------------------------------------------------------------
# Planos LT2 (sheet) -> nivel del modelo que cubre cada dibujo.
# 201: "CIELO 1° SUBTERRANEO A CIELO PISO 3°" cubre LOSA L1..L4.
# ---------------------------------------------------------------------------
DRAWING_TITLES_LT2: Dict[str, str] = {
    "200I": "FUNDACION INFERIOR (200I)",
    "200S": "FUNDACION SUPERIOR (200S)",
    "201I": "LOSA CIELO 1° SUB A CIELO PISO 3° (INFERIOR)",
    "201S": "LOSA CIELO 1° SUB A CIELO PISO 3° (SUPERIOR)",
    "202I": "LOSA CIELO PISO 4° (INFERIOR)",
    "202S": "LOSA CIELO PISO 4° (SUPERIOR)",
}

FLOOR_TO_LEVEL_LT2: Dict[str, str] = {
    "200I": "B1",
    "200S": "B1",
    "201I": "L1..L4",       # losas de cielo 1° sub a cielo piso 3° (4 paños)
    "201S": "L1..L4",
    "202I": "ROOF",         # losa cielo piso 4° = cubierta
    "202S": "ROOF",
}

LEVELS_201 = ("L1", "L2", "L3", "L4")


class _Seq:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}

    def next(self, sheet: str) -> int:
        self._n[sheet] = self._n.get(sheet, 0) + 1
        return self._n[sheet]


def _drawing(sheet: str) -> str:
    return f"2024_22-{sheet}-Model"


def _mesh(s: _Seq, sheet: str, layer: Layer, direction: Direction,
          zone_text: str, dia: int, spc: int, *,
          classification: Classification = Classification.MESH,
          status: Status = Status.EXACT,
          note: str = "", length_cm: Optional[int] = None) -> MeshRule:
    return MeshRule(
        id=RuleId("LT2", _drawing(sheet), sheet, s.next(sheet)),
        layer=layer,
        direction=direction,
        zone=Zone(kind=ZoneKind.FREE_TEXT, text=zone_text),
        diameter_mm=dia,
        spacing_cm=spc,
        classification=classification,
        status=status,
        floor=DRAWING_TITLES_LT2.get(sheet, sheet),
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
        id=RuleId("LT2", _drawing(sheet), sheet, s.next(sheet)),
        direction=direction,
        zone=Zone(kind=ZoneKind.FREE_TEXT, text=zone_text),
        bar_count=bar_count,
        diameter_mm=dia,
        classification=classification,
        status=status,
        floor=DRAWING_TITLES_LT2.get(sheet, sheet),
        length_cm=length_cm,
        spacing_cm=spacing_cm,
        note=note,
    )


# ---------------------------------------------------------------------------
# 200I / 200S - FUNDACIONES
# ---------------------------------------------------------------------------
def _fundaciones() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []

    # ---- 200I (armadura inferior) ----
    meshes.append(_mesh(s, "200I", Layer.LOWER, Direction.X,
                        "general: todos los ejes horizontales", 12, 20,
                        note="barras paralelas a los ejes horizontales (X); "
                             "malla inferior de fundaciones."))
    meshes.append(_mesh(s, "200I", Layer.LOWER, Direction.Y,
                        "general: todos los ejes verticales", 12, 20,
                        note="barras paralelas a los ejes verticales (Y)."))
    meshes.append(_mesh(s, "200I", Layer.LOWER, Direction.BOTH,
                        "general: traba asociada", 10, 20,
                        classification=Classification.LOCAL,
                        note="traba entre cuadrados de fundacion; Φ10@20."))
    meshes.append(_mesh(s, "200I", Layer.LOWER, Direction.X,
                        "cuadrados de fundacion: direccion horizontal", 18, 10,
                        note="refuerzo de los cuadrados, direccion horizontal."))
    meshes.append(_mesh(s, "200I", Layer.LOWER, Direction.Y,
                        "cuadrados de fundacion: direccion vertical", 16, 10,
                        note="refuerzo de los cuadrados, direccion vertical."))
    meshes.append(_mesh(s, "200I", Layer.LOWER, Direction.BOTH,
                        "eje 1' (excepcion)", 16, 10,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje 1' no existe en la grilla modelada LT2."))
    meshes.append(_mesh(s, "200I", Layer.LOWER, Direction.BOTH,
                        "esquinas del eje A'", 22, 10,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="refuerzo de esquinas sobre eje A'; excepcion."))

    # ---- 200S (armadura superior) ----
    meshes.append(_mesh(s, "200S", Layer.UPPER, Direction.X,
                        "general: todos los ejes horizontales", 12, 20))
    meshes.append(_mesh(s, "200S", Layer.UPPER, Direction.Y,
                        "general: todos los ejes verticales", 12, 20))
    meshes.append(_mesh(s, "200S", Layer.UPPER, Direction.BOTH,
                        "general: traba asociada", 10, 20,
                        classification=Classification.LOCAL,
                        note="traba entre cuadrados de fundacion; Φ10@20."))
    # Reglas de esquinas del eje A' de 200S: tres reglas INDEPENDIENTES
    # (no son equivalentes; cada una se conserva por separado).
    for dia, spc in ((18, 20), (12, 10), (16, 10)):
        meshes.append(_mesh(s, "200S", Layer.UPPER, Direction.BOTH,
                            f"esquinas del eje A' (Φ{dia}@{spc})", dia, spc,
                            status=Status.NEEDS_EXACT_ZONE_MAPPING,
                            note="regla de esquina independiente del eje A'; "
                                 "no se equivale a las otras."))
    # Eje D: 3 trabas Φ16@10 (eje D existe en la grilla: x=31.250).
    locals_.append(_local(s, "200S", "eje D (3 trabas)", 3, 16,
                          spacing_cm=10,
                          note="3 trabas sobre el eje D, Φ16@10 (eje D "
                               "resoluble como franja del modelo)."))
    return meshes, locals_


# ---------------------------------------------------------------------------
# 201I / 201S - LOSA CIELO 1° SUB A CIELO PISO 3°
# ---------------------------------------------------------------------------
def _losa_201() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []

    # ---- 201I (inferior) ----
    meshes.append(_mesh(s, "201I", Layer.LOWER, Direction.Y,
                        "general: direccion vertical", 8, 18,
                        note="malla inferior; direccion vertical (Y)."))
    meshes.append(_mesh(s, "201I", Layer.LOWER, Direction.X,
                        "general: direccion horizontal", 8, 24,
                        note="malla inferior; direccion horizontal (X)."))
    meshes.append(_mesh(s, "201I", Layer.LOWER, Direction.BOTH,
                        "eje 1' (excepcion)", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje 1' no existe en la grilla modelada LT2."))
    for losa in ("0112", "0113", "0116"):
        meshes.append(_mesh(s, "201I", Layer.LOWER, Direction.BOTH,
                            f"losa {losa} (toda la losa)", 8, 18,
                            status=Status.NEEDS_EXACT_ZONE_MAPPING,
                            note=f"losa {losa} Φ8@18 toda la losa; excepcion "
                                 "de la malla general en esa area (numero de "
                                 "losa no mapeado a la grilla del modelo)."))
    meshes.append(_mesh(s, "201I", Layer.LOWER, Direction.BOTH,
                        "losa 0113 (toda la losa)", 8, 36,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 0113 Φ8@36 toda la losa; excepcion."))
    meshes.append(_mesh(s, "201I", Layer.LOWER, Direction.Y,
                        "losa 0101: direccion vertical", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 0101 (excepcion); vertical."))
    meshes.append(_mesh(s, "201I", Layer.LOWER, Direction.X,
                        "losa 0101: direccion horizontal", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 0101 (excepcion); horizontal."))

    # ---- 201S (superior) ----
    locals_.append(_local(s, "201S", "perimetro (2Φ16)", 2, 16,
                          note="barras perimetrales de la losa superior."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "eje 2 (superior)", 10, 36,
                        status=Status.EXACT,
                        note="franja superior sobre el eje 2."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "esquina 3-A'", 8, 18,
                        note="esquina entre ejes 3 y A'."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "eje 1 (superior)", 10, 18,
                        note="franja superior sobre el eje 1."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "eje A (superior)", 8, 36,
                        note="franja superior sobre el eje A."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "eje B (superior)", 10, 36,
                        note="franja superior sobre el eje B."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "eje C (superior)", 10, 28,
                        note="franja superior sobre el eje C."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "dos ejes sin nombre laterales a C", 10, 28,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="dos ejes sin nombre, laterales al eje C; no "
                             "localizables en la grilla del modelo."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.Y,
                        "losa 0109: direccion vertical", 10, 14,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="losa 0109 (excepcion); vertical."))
    locals_.append(_local(s, "201S",
                          "rectangulo rojo con cruz entre 1A'-2 sobre eje A' (2Φ16)",
                          2, 16,
                          status=Status.NEEDS_EXACT_ZONE_MAPPING,
                          note="longitudinal 2Φ16 del rectangulo rojo con "
                               "cruz; eje 1A' no modelado (grilla tiene 1A)."))
    meshes.append(_mesh(s, "201S", Layer.UPPER, Direction.BOTH,
                        "estribos del rectangulo rojo entre 1A'-2 sobre eje A'",
                        8, 15,
                        classification=Classification.STIRRUP,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="estribos Φ8@15 del rectangulo rojo; refuerzo "
                             "especial local, NO malla general."))
    return meshes, locals_


# ---------------------------------------------------------------------------
# 202I / 202S - LOSA CIELO PISO 4° (CUBIERTA)
# ---------------------------------------------------------------------------
def _losa_202() -> Tuple[List[MeshRule], List[LocalBarRule]]:
    s = _Seq()
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []

    # ---- 202I (inferior) ----
    meshes.append(_mesh(s, "202I", Layer.LOWER, Direction.BOTH,
                        "eje C' (inferior)", 8, 18,
                        note="franja inferior sobre el eje C'."))
    meshes.append(_mesh(s, "202I", Layer.LOWER, Direction.BOTH,
                        "eje 1' (inferior)", 10, 20,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="eje 1' no existe en la grilla modelada LT2."))
    meshes.append(_mesh(s, "202I", Layer.LOWER, Direction.Y,
                        "general: ejes verticales", 8, 18,
                        note="malla inferior; ejes verticales (Y)."))
    # Los ejes horizontales de 202I se dividen en sectores Φ8@36 y Φ8@18;
    # la particion espacial NO se infiere: queda pendiente de plano.
    meshes.append(_mesh(s, "202I", Layer.LOWER, Direction.X,
                        "ejes horizontales: sector Φ8@36", 8, 36,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="sector de ejes horizontales Φ8@36; la particion "
                             "de sectores requiere el plano (NO asignar a "
                             "toda la direccion)."))
    meshes.append(_mesh(s, "202I", Layer.LOWER, Direction.X,
                        "ejes horizontales: sector Φ8@18", 8, 18,
                        status=Status.NEEDS_EXACT_ZONE_MAPPING,
                        note="sector de ejes horizontales Φ8@18; la particion "
                             "de sectores requiere el plano (NO asignar a "
                             "toda la direccion)."))
    meshes.append(_mesh(s, "202I", Layer.LOWER, Direction.BOTH,
                        "resto de la planta (general inferior)", 8, 30,
                        note="resto de la planta cubierto por la malla "
                             "general inferior Φ8@30."))

    # ---- 202S (superior) ----
    locals_.append(_local(s, "202S", "cuadrados con cruces (2Φ16)", 2, 16,
                          note="cuadrados con cruces de la losa superior."))
    locals_.append(_local(s, "202S", "perimetro (1Φ16)", 1, 16,
                          note="barras perimetrales."))
    meshes.append(_mesh(s, "202S", Layer.UPPER, Direction.X,
                        "general: ejes horizontales", 8, 30,
                        note="malla superior; ejes horizontales (X). Los"
                             " ejes listados a continuacion prevalecen sobre"
                             " la malla general en sus franjas."))
    meshes.append(_mesh(s, "202S", Layer.UPPER, Direction.BOTH,
                        "eje A (superior)", 8, 36,
                        note="franja superior sobre el eje A; prevalece sobre"
                             " la general en su franja."))
    meshes.append(_mesh(s, "202S", Layer.UPPER, Direction.BOTH,
                        "eje B (superior)", 10, 36,
                        note="franja superior sobre el eje B."))
    meshes.append(_mesh(s, "202S", Layer.UPPER, Direction.Y,
                        "general: ejes verticales", 10, 36,
                        note="malla superior; ejes verticales (Y)."))
    meshes.append(_mesh(s, "202S", Layer.UPPER, Direction.BOTH,
                        "eje C' (superior)", 10, 20,
                        note="franja superior sobre el eje C'."))
    return meshes, locals_


# ---------------------------------------------------------------------------
# COLUMNAS LT2 - armadura longitudinal (dato confirmado por usuario)
# ---------------------------------------------------------------------------
def _columnas() -> List[ColumnReinforcementRule]:
    s = _Seq()
    return [
        ColumnReinforcementRule(
            id=RuleId("LT2", "CONFIRMADO-USUARIO", "COL", s.next("COL")),
            bar_count=16,
            diameter_mm=22,
            bar_type=ColumnBarType.LONGITUDINAL,
            section="P70x70 (seccion del modelo LT2)",
            classification=Classification.COLUMN,
            status=Status.EXACT,
            source="USER_CONFIRMED_DRAWING_DATA",
            geometry_pending=True,
            note="Todas las columnas LT2: 16 Φ22 longitudinales. No se "
                 "inventan estribos, recubrimiento ni distribucion "
                 "transversal de las 16 barras (no definida); la geometria "
                 "3D queda pendiente hasta confirmar seccion/cubierta.",
        ),
    ]


# ---------------------------------------------------------------------------
# Dataset compilado
# ---------------------------------------------------------------------------
def load_lt2_reinforcement() -> Dict[str, List]:
    """Retorna todo el dataset LT2 agrupado por tipo."""
    meshes: List[MeshRule] = []
    locals_: List[LocalBarRule] = []
    for fn in (_fundaciones, _losa_201, _losa_202):
        m, l = fn()
        meshes.extend(x for x in m if isinstance(x, MeshRule))
        locals_.extend(x for x in l if isinstance(x, LocalBarRule))
    return {
        "mesh": meshes,
        "local": locals_,
        "columns": _columnas(),
        "walls": [],       # se cargan desde lt2_wall_data
        "beams": [],       # se cargan desde lt2_beam_data
        "stairs": [],      # se cargan desde lt2_stair_data
    }


if __name__ == "__main__":
    import sys

    data = load_lt2_reinforcement()
    print("Conteos por categoria (mesh/local/columns):")
    for key, rules in data.items():
        print(f"  {key}: {len(rules)}")
    print("Total:", sum(len(v) for v in data.values()))
    sys.exit(0)