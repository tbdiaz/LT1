"""Armadura longitudinal real de vigas LT1 desde planos 400/401/402.

TRANSCRIPCION FIEL del levantamiento de cada viga identificada en los
planos de vigas LT1. Convive con `lt1_reinforcement_data._vigas()`, que
queda marcado SUPERSEDED_BY_EXACT_BEAM_DRAWINGS como referencia historica.

CONVENCIONES:
- ``beam_id`` es el id del PLANO (V100, 0102, VF1, ...). Solo cuando el
  eje fisico este verificado en el modelo se rellena la correspondencia a
  elementTags (a traves de la geometria de la viga, no aqui).
- Una barra puede cruzar un apoyo (ej. apoyo eje 2 del conjunto 3-2-1):
  se conserva como UN segmento con continuity_across_support=True y
  beam_ids con ambos tramos; NO se corta en el elementTag.
- valores L≈ se conservan tal como se leyeron; cuando el dato del plano
  no es legible (busquedas de texto solo devuelven etiquetas) se marca
  NEEDS_DRAWING_VALUE_CONFIRMATION y no se inventa el numero.
- Estribos TP1/TP4 (plano 002): se guarda la referencia del detalle, NO
  se inventa la distribucion.
- VF (plano 402): categoria FOUNDATION_BEAM, varias capas, no se reduce
  a "2 B22".
- El unico registro no asociado a un beam_id es la seccion escalonada
  especial del plano 402 (LT1_SPECIAL_STEPPED_BEAM_SECTION): se detalla,
  pero NO corresponde ni a V60/80 ni a todo LT1; su asociacion a un
  elemento puntual queda pendiente de confirmacion en 402.

Este modulo NO depende de OpenSeesPy ni del modelo combinado.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .reinforcement_types import (
    BeamBarLayer,
    BeamKind,
    BeamRebarSegment,
    BeamRecord,
    BeamStirrupZone,
    RuleId,
    Status,
)

# ---------------------------------------------------------------------------
# Identificacion de los planos de vigas LT1
# ---------------------------------------------------------------------------
PLANO_400 = "400"
PLANO_401 = "401 (2)"
PLANO_402 = "402 (1)"

BEAM_DRAWINGS: Dict[str, str] = {
    PLANO_400: "2017_67-400-Model",
    PLANO_401: "2017_67-401 (2)-Model",
    PLANO_402: "2017_67-402 (1)-Model",
}

# Notacion de estribo doble del plano (no se reinterpreta el diametro).
ED = "ED"   # estribo doble

# ---------------------------------------------------------------------------
# Indice real de vigas por plano (V110 y V115+ NO existen en el plano 400).
# ---------------------------------------------------------------------------
BEAM_IDS_400: Tuple[str, ...] = (
    "0101", "0102", "V100", "V101", "V102", "V103", "V104", "V105",
    "V106", "V107", "V108", "V109", "V111", "V112", "V113", "V114",
)
BEAM_IDS_401: Tuple[str, ...] = (
    "V200", "V201", "V202", "V203", "V204", "V205", "V206", "V207",
    "V208", "V209", "V210", "V211", "V300", "V301", "V302", "V303",
    "V304", "V305",
)
BEAM_IDS_402: Tuple[str, ...] = (
    "V306", "V307", "V308", "V309", "V400", "V401", "V402", "V403",
    "V404", "V405", "V406", "VF1", "VF2", "VF3",
)

# Familias tipologicas detectadas en 401/402 (no se inventan valores).
FAM_A_NOTE = (
    "viga continua 3-2-1: seccion V60/80, F/F' base 2 B22, +F/+F' "
    "2 B22 y 4 B22 concentradas sobre apoyo eje 2, barras inferiores por "
    "tramo, longitudes diferentes por dibujo (TP1/TP4). NO todas iguales."
)
FAM_B_NOTE = (
    "viga de vano unico/especial: detalle individual en plano 401/402; "
    "no extrapolar. Algunas con B18 o B16."
)


class _Seq:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}

    def next(self, sheet: str) -> int:
        self._n[sheet] = self._n.get(sheet, 0) + 1
        return self._n[sheet]


def _seg(s: _Seq, sheet: str, beam_ids: List[str], phys: str,
         layer: BeamBarLayer, count: Optional[int], dia: int,
         **kw) -> BeamRebarSegment:
    return BeamRebarSegment(
        id=RuleId("LT1", BEAM_DRAWINGS[sheet], sheet, s.next(sheet)),
        beam_ids=beam_ids,
        physical_bar_id=phys,
        bar_layer=layer,
        bar_count=count,
        diameter_mm=dia,
        **kw,
    )


def _stir(s: _Seq, sheet: str, beam_ids: List[str], **kw) -> BeamStirrupZone:
    return BeamStirrupZone(
        id=RuleId("LT1", BEAM_DRAWINGS[sheet], sheet, s.next(sheet)),
        beam_ids=beam_ids,
        **kw,
    )


def _rec(sheet: str, beam_id: str, section: str, kind: BeamKind,
         **kw) -> BeamRecord:
    return BeamRecord(
        beam_id=beam_id,
        drawing=BEAM_DRAWINGS[sheet],
        sheet=sheet,
        section=section,
        kind=kind,
        **kw,
    )


# ---------------------------------------------------------------------------
# PLANO 400
# ---------------------------------------------------------------------------
def _plan400(s: _Seq) -> Tuple[List[BeamRebarSegment], List[BeamStirrupZone],
                               List[BeamRecord]]:
    segs: List[BeamRebarSegment] = []
    stirs: List[BeamStirrupZone] = []
    recs: List[BeamRecord] = []

    # ---- V0101: ejes 1b-8, V.20/VAR ----
    recs.append(_rec(
        PLANO_400, "0101", "V.20/VAR", BeamKind.SPECIAL,
        axes_text="ejes 1b-8 (luz ~810 cm)", group="",
        longitudinal="F' base 2B22 L~1150 ; +F' 2B22 L~800 (ext. der) ; "
                     "+F 2B22 L~600 (central) ; F base 2B22 L~1150",
        stirrups="detalle TP4 (plano 002); distribucion no transcrita",
        detail_reference="TP4_PLAN_002",
        note="variacion de la dimension 'VAR' no se inventa; "
             "detalle TP4_PLAN_002.",
    ))
    segs.append(_seg(s, PLANO_400, ["0101"], "0101-F'-base",
                     BeamBarLayer.TOP_BASE, 2, 22,
                     length_cm=1150, start_axis="1b", end_axis="8",
                     detail_reference="TP4_PLAN_002",
                     note="L~1150 cm segun trans. plan."))
    segs.append(_seg(s, PLANO_400, ["0101"], "0101-+F'-ext-der",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=800, end_axis="8",
                     note="+F' extremo derecho L~800 cm."))
    segs.append(_seg(s, PLANO_400, ["0101"], "0101-+F-central",
                     BeamBarLayer.BOTTOM_ADDITIONAL, 2, 22,
                     length_cm=600,
                     note="+F zona central L~600 cm."))
    segs.append(_seg(s, PLANO_400, ["0101"], "0101-F-base",
                     BeamBarLayer.BOTTOM_BASE, 2, 22,
                     length_cm=1150, start_axis="1b", end_axis="8",
                     detail_reference="TP4_PLAN_002",
                     note="F base L~1150 cm."))

    # ---- V0102: E'-F-G-Ga, V.S.I. 20/150 (profunda, B18) ----
    recs.append(_rec(
        PLANO_400, "0102", "V.S.I. 20/150", BeamKind.SPECIAL,
        axes_text="E'-F-G-Ga", group="",
        longitudinal="F'/sup: 2B18 L~460 izq / L~1200 continuo / L~800 der ; "
                     "F/inf: 2B18 L~800 / 1200 / 800",
        stirrups="verticales/refuerzos de extremo en ambos extremos (plano)",
        note="viga profunda especial (20/150); NO es V60/80 ni 2B22.",
    ))
    segs.append(_seg(s, PLANO_400, ["0102"], "0102-F'-izq",
                     BeamBarLayer.TOP_BASE, 2, 18,
                     length_cm=460, start_axis="E'", end_axis="F",
                     note="F' extremo izquierdo L~460 cm."))
    segs.append(_seg(s, PLANO_400, ["0102"], "0102-F'-continuo",
                     BeamBarLayer.TOP_BASE, 2, 18,
                     length_cm=1200, start_axis="E'", end_axis="Ga",
                     continuity_across_support=True,
                     note="2B18 continuo/intermedio L~1200 cm."))
    segs.append(_seg(s, PLANO_400, ["0102"], "0102-F'-der",
                     BeamBarLayer.TOP_BASE, 2, 18,
                     length_cm=800, end_axis="Ga",
                     note="F' extremo derecho L~800 cm."))
    segs.append(_seg(s, PLANO_400, ["0102"], "0102-F-izq",
                     BeamBarLayer.BOTTOM_BASE, 2, 18,
                     length_cm=800, start_axis="E'", end_axis="F",
                     note="F inferior L~800 cm."))
    segs.append(_seg(s, PLANO_400, ["0102"], "0102-F-continuo",
                     BeamBarLayer.BOTTOM_BASE, 2, 18,
                     length_cm=1200, start_axis="E'", end_axis="Ga",
                     continuity_across_support=True,
                     note="F inferior continuo L~1200 cm."))
    segs.append(_seg(s, PLANO_400, ["0102"], "0102-F-der",
                     BeamBarLayer.BOTTOM_BASE, 2, 18,
                     length_cm=800, end_axis="Ga",
                     note="F inferior extremo derecho L~800 cm."))

    # ---- V100-V101: conjunto 3-2-1, V.60/80 (continuidad sobre eje 2) ----
    v100v101_long = (
        "F' base: V100 2B22 L~1200 ; V101 2B22 L~700. +F': 2B22 L~700 "
        "(ext.izq), 2B22 L~1100 + 4B22 L~400 (apoyo intermedio), ")
    recs.append(_rec(
        PLANO_400, "V100", "V.60/80", BeamKind.CONTINUOUS,
        axes_text="3-2-1", group="conjunto V100-V101",
        longitudinal=(
            v100v101_long +
            "der 2B22 L~400-450, 4B22 L~800, 2B22 L~800. F: 2B22 L~700 "
            "(3-2) / L~1200 (2-1)",
        ),
        stirrups="zona TP.4 + zona TP.1 (detalle plano 002); "
                 "secuencia no inventada",
        detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
        note="barras que cruzan el apoyo eje 2 conservan continuidad "
             "fisica (NO se cortan en el elementTag).",
    ))
    recs.append(_rec(
        PLANO_400, "V101", "V.60/80", BeamKind.CONTINUOUS,
        axes_text="3-2-1", group="conjunto V100-V101",
        longitudinal=(
            "F' base 2B22 L~700 ; +F' der 2B22 L~400-450 / 4B22 L~800 / "
            "2B22 L~800 ; F 2B22 L~1200",
        ),
        stirrups="zona TP.4 + zona TP.1 (detalle plano 002)",
        detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
        note="tramo 2-1 del conjunto; continuidad con V100 sobre eje 2.",
    ))
    segs.append(_seg(s, PLANO_400, ["V100"], "V100-F'-base",
                     BeamBarLayer.TOP_BASE, 2, 22,
                     length_cm=1200, start_axis="3", end_axis="2",
                     note="F' base tramo 3-2 (V100) L~1200 cm."))
    segs.append(_seg(s, PLANO_400, ["V101"], "V101-F'-base",
                     BeamBarLayer.TOP_BASE, 2, 22,
                     length_cm=700, start_axis="2", end_axis="1",
                     note="F' base tramo 2-1 (V101) L~700 cm."))
    segs.append(_seg(s, PLANO_400, ["V100"], "V100-+F'-ext-izq",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=700, start_axis="3",
                     note="+F' apoyo/extremo izquierdo L~700 cm."))
    segs.append(_seg(s, PLANO_400, ["V100", "V101"], "V100V101-+F'-apoyo",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=1100, start_axis="2",
                     continuity_across_support=True,
                     note="+F' apoyo intermedio eje 2 L~1100 cm (continua)."))
    segs.append(_seg(s, PLANO_400, ["V100", "V101"], "V100V101-+F'-apoyo-4",
                     BeamBarLayer.TOP_ADDITIONAL, 4, 22,
                     length_cm=400, start_axis="2",
                     continuity_across_support=True,
                     note="+F' 4B22 apoyo intermedio L~400 cm (continua)."))
    segs.append(_seg(s, PLANO_400, ["V101"], "V101-+F'-der-a",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     end_axis="1", note="+F' der 2B22 L~400-450 cm (rango)."))
    segs.append(_seg(s, PLANO_400, ["V101"], "V101-+F'-der-b",
                     BeamBarLayer.TOP_ADDITIONAL, 4, 22,
                     length_cm=800, end_axis="1",
                     note="+F' der 4B22 L~800 cm."))
    segs.append(_seg(s, PLANO_400, ["V101"], "V101-+F'-der-c",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=800, end_axis="1",
                     note="+F' der 2B22 L~800 cm."))
    segs.append(_seg(s, PLANO_400, ["V100"], "V100-F-base",
                     BeamBarLayer.BOTTOM_BASE, 2, 22,
                     length_cm=700, start_axis="3", end_axis="2",
                     note="F tramo 3-2 (V100) 2B22 L~700 cm."))
    segs.append(_seg(s, PLANO_400, ["V101"], "V101-F-base",
                     BeamBarLayer.BOTTOM_BASE, 2, 22,
                     length_cm=1200, start_axis="2", end_axis="1",
                     note="F tramo 2-1 (V101) 2B22 L~1200 cm."))
    stirs.append(_stir(s, PLANO_400, ["V100", "V101"],
                       type="TP.4", spacing_cm=None,
                       detail_reference="TP.4_PLANO_002",
                       note="zona TP.4; distribucion segun plano 002 "
                            "(no inventada)."))
    stirs.append(_stir(s, PLANO_400, ["V100", "V101"],
                       type="TP.1", spacing_cm=None,
                       detail_reference="TP.1_PLANO_002",
                       note="zona TP.1; distribucion segun plano 002 "
                            "(no inventada)."))

    # ---- V102-V103: conjunto 3-2-1, V.60/80 (detalle propio) ----
    recs.append(_rec(
        PLANO_400, "V102", "V.60/80", BeamKind.CONTINUOUS,
        axes_text="3-2-1", group="conjunto V102-V103",
        longitudinal=(
            "F' 2B22 L~1200 (3-2) / L~700 (2-1). +F': 2B22 L~700, 2B22 "
            "L~1100, 4B22 L~400, 2B22 L~400, 4B22 L~800, 2B22 L~800. "
            "F 2B22 L~700 izq / 2B22 L~1200 der",
        ),
        stirrups="zona TP.1 + zona TP.4 (detalle plano 002)",
        detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
        note="detalle propio; NO es alias de V100-V101.",
    ))
    recs.append(_rec(
        PLANO_400, "V103", "V.60/80", BeamKind.CONTINUOUS,
        axes_text="3-2-1", group="conjunto V102-V103",
        longitudinal=(
            "F' 2B22 L~700 (2-1) ; +F' 2B22 L~400/4B22 L~800/2B22 L~800 ; "
            "F 2B22 L~1200 der",
        ),
        stirrups="zona TP.1 + zona TP.4 (detalle plano 002)",
        detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
        note="tramo 2-1 del conjunto V102-V103.",
    ))
    segs.append(_seg(s, PLANO_400, ["V102"], "V102-F'-base",
                     BeamBarLayer.TOP_BASE, 2, 22,
                     length_cm=1200, start_axis="3", end_axis="2",
                     note="F' base 3-2 (V102) L~1200 cm."))
    segs.append(_seg(s, PLANO_400, ["V103"], "V103-F'-base",
                     BeamBarLayer.TOP_BASE, 2, 22,
                     length_cm=700, start_axis="2", end_axis="1",
                     note="F' base 2-1 (V103) L~700 cm."))
    segs.append(_seg(s, PLANO_400, ["V102"], "V102-+F'-a",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=700, note="+F' 2B22 L~700 cm."))
    segs.append(_seg(s, PLANO_400, ["V102", "V103"], "V102V103-+F'-b",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=1100, continuity_across_support=True,
                     note="+F' 2B22 L~1100 cm apoyo eje 2."))
    segs.append(_seg(s, PLANO_400, ["V102", "V103"], "V102V103-+F'-c",
                     BeamBarLayer.TOP_ADDITIONAL, 4, 22,
                     length_cm=400, continuity_across_support=True,
                     note="+F' 4B22 L~400 cm apoyo eje 2."))
    segs.append(_seg(s, PLANO_400, ["V103"], "V103-+F'-d",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=400, end_axis="1",
                     note="+F' 2B22 L~400 cm."))
    segs.append(_seg(s, PLANO_400, ["V103"], "V103-+F'-e",
                     BeamBarLayer.TOP_ADDITIONAL, 4, 22,
                     length_cm=800, end_axis="1",
                     note="+F' 4B22 L~800 cm."))
    segs.append(_seg(s, PLANO_400, ["V103"], "V103-+F'-f",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     length_cm=800, end_axis="1",
                     note="+F' 2B22 L~800 cm."))
    segs.append(_seg(s, PLANO_400, ["V102"], "V102-F-izq",
                     BeamBarLayer.BOTTOM_BASE, 2, 22,
                     length_cm=700, start_axis="3", end_axis="2",
                     note="F 2B22 L~700 cm izq."))
    segs.append(_seg(s, PLANO_400, ["V103"], "V103-F-der",
                     BeamBarLayer.BOTTOM_BASE, 2, 22,
                     length_cm=1200, start_axis="2", end_axis="1",
                     note="F 2B22 L~1200 cm der."))
    stirs.append(_stir(s, PLANO_400, ["V102", "V103"], type="TP.1",
                       detail_reference="TP.1_PLANO_002",
                       note="distribucion segun plano 002 (no inventada)."))
    stirs.append(_stir(s, PLANO_400, ["V102", "V103"], type="TP.4",
                       detail_reference="TP.4_PLANO_002",
                       note="distribucion segun plano 002 (no inventada)."))

    # ---- V104-V105: conjunto 3-2-1, familia B22 ----
    recs.append(_rec(
        PLANO_400, "V104", "V.60/80", BeamKind.CONTINUOUS,
        axes_text="3-2-1", group="conjunto V104-V105",
        longitudinal="F' 2B22 ; +F' 2B22 y 4B22 por zona ; F 2B22 por tramo",
        stirrups="TP.1/TP.4 (plano 002)",
        detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
        note="valores por tramo no transcritos (leer plano 400).",
        confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
    ))
    recs.append(_rec(
        PLANO_400, "V105", "V.60/80", BeamKind.CONTINUOUS,
        axes_text="3-2-1", group="conjunto V104-V105",
        longitudinal="F' 2B22 ; +F' 2B22 y 4B22 por zona ; F 2B22 por tramo",
        stirrups="TP.1/TP.4 (plano 002)",
        detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
        note="valores por tramo no transcritos (leer plano 400).",
        confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
    ))
    for bid, ax in (("V104", "3"), ("V105", "3")):
        segs.append(_seg(s, PLANO_400, [bid], f"{bid}-F'-base",
                         BeamBarLayer.TOP_BASE, 2, 22,
                         start_axis=ax, end_axis="2",
                         confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
                         note="F' 2B22 tramo 3-2; L no transcrita."))
    segs.append(_seg(s, PLANO_400, ["V104", "V105"], "V104V105-+F'-2",
                     BeamBarLayer.TOP_ADDITIONAL, 2, 22,
                     start_axis="3", end_axis="1",
                     continuity_across_support=True,
                     confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
                     note="+F' 2B22 sobre apoyo eje 2; L no transcrita."))
    segs.append(_seg(s, PLANO_400, ["V104", "V105"], "V104V105-+F'-4",
                     BeamBarLayer.TOP_ADDITIONAL, 4, 22,
                     start_axis="3", end_axis="1",
                     continuity_across_support=True,
                     confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
                     note="+F' 4B22 sobre apoyo eje 2; L no transcrita."))
    for bid, ax in (("V104", "3"), ("V105", "2")):
        segs.append(_seg(s, PLANO_400, [bid], f"{bid}-F-base",
                         BeamBarLayer.BOTTOM_BASE, 2, 22,
                         start_axis=ax, end_axis="2" if bid == "V104" else "1",
                         confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
                         note="F 2B22 por tramo; L no transcrita."))

    # ---- V106: corta/especial, B16 (no asignar B22 por defecto) ----
    recs.append(_rec(
        PLANO_400, "V106", "V.60/80 (especial)", BeamKind.SPECIAL,
        axes_text="", group="",
        longitudinal="F 2B16 L~300 (minimo); resto de llamadas ilegibles",
        stirrups="no transcrito",
        note="viga corta/especial: NO B22 por defecto.",
        confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
    ))
    segs.append(_seg(s, PLANO_400, ["V106"], "V106-F-base",
                     BeamBarLayer.BOTTOM_BASE, 2, 16,
                     length_cm=300,
                     note="F 2B16 L~300 cm (dato transcrito)."))
    segs.append(_seg(s, PLANO_400, ["V106"], "V106-F'-base",
                     BeamBarLayer.TOP_BASE, None, 16,
                     confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
                     note="llamadas de V106 ilegibles; confirmar en plano."))

    # ---- V107: vano unico, B22, base 4B22 L~745 ----
    recs.append(_rec(
        PLANO_400, "V107", "V.60/80", BeamKind.SINGLE_SPAN,
        axes_text="", group="",
        longitudinal="F base 4B22 L~745 ; refuerzos adicionales segun detalle",
        stirrups="ED (ver plano 002)",
        note="no extrapolar 4B22 a otras vigas.",
    ))
    segs.append(_seg(s, PLANO_400, ["V107"], "V107-F-base",
                     BeamBarLayer.BOTTOM_BASE, 4, 22,
                     length_cm=745,
                     note="F base 4B22 L~745 cm (vano unico)."))
    segs.append(_seg(s, PLANO_400, ["V107"], "V107-+adicional",
                     BeamBarLayer.TOP_ADDITIONAL, None, 22,
                     confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
                     note="adicionales segun detalle; valores a confirmar."))

    # ---- V108 / V109: cortas H'-I, B22, barras L~700 ----
    for bid in ("V108", "V109"):
        recs.append(_rec(
            PLANO_400, bid, "V.60/80 (corta)", BeamKind.SPECIAL,
            axes_text="H'-I", group="",
            longitudinal="B22 predominante, barras principales L~700",
            stirrups="ED (ver plano 002)",
            note=f"{bid} registrada por separado (corta H'-I).",
        ))
        segs.append(_seg(s, PLANO_400, [bid], f"{bid}-principal",
                         BeamBarLayer.BOTTOM_BASE, 2, 22,
                         length_cm=700, start_axis="H'", end_axis="I",
                         note=f"{bid} barras principales L~700 cm."))

    # ---- V111: ejes 1-1AA-1A, corta/especial, B16 ----
    recs.append(_rec(
        PLANO_400, "V111", "V.60/80 (especial)", BeamKind.SPECIAL,
        axes_text="1-1AA-1A", group="",
        longitudinal="2B16 / 4B16 L~400",
        stirrups="no transcrito",
        note="viga corta/especial: NO es familia 2B22.",
    ))
    segs.append(_seg(s, PLANO_400, ["V111"], "V111-F-2",
                     BeamBarLayer.BOTTOM_BASE, 2, 16,
                     length_cm=400, start_axis="1", end_axis="1A",
                     note="2B16 L~400 cm."))
    segs.append(_seg(s, PLANO_400, ["V111"], "V111-F-4",
                     BeamBarLayer.BOTTOM_BASE, 4, 16,
                     length_cm=400, start_axis="1", end_axis="1A",
                     note="4B16 L~400 cm."))

    # ---- V112-V113: encuentro 3-2, B22/B18, no homogenizar ----
    for bid in ("V112", "V113"):
        recs.append(_rec(
            PLANO_400, bid, "V.60/80 (especial)", BeamKind.SPECIAL,
            axes_text="3-2", group="",
            longitudinal="B22 y B18; refuerzos sup/inf L~400-800",
            stirrups="detalle plano 002",
            detail_reference="TP.PLANO_002",
            note="encuentro especial en 3-2; no homogenizar con otras vigas.",
            confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        ))

    # ---- V114: corta, B16, L~400 ----
    recs.append(_rec(
        PLANO_400, "V114", "V.60/80 (especial)", BeamKind.SMALL_SPECIAL_BEAM,
        axes_text="", group="",
        longitudinal="B16 principalmente, barras L~400",
        stirrups="no transcrito",
        note="SMALL_SPECIAL_BEAM: no reemplazar por B22.",
    ))
    segs.append(_seg(s, PLANO_400, ["V114"], "V114-F",
                     BeamBarLayer.BOTTOM_BASE, None, 16,
                     length_cm=400,
                     note="B16 principal L~400 cm; nº de barras no legible."))

    return segs, stirs, recs


# ---------------------------------------------------------------------------
# PLANOS 401 / 402
# ---------------------------------------------------------------------------
def _plan401(s: _Seq) -> Tuple[List[BeamRebarSegment], List[BeamStirrupZone],
                               List[BeamRecord]]:
    segs: List[BeamRebarSegment] = []
    stirs: List[BeamStirrupZone] = []
    recs: List[BeamRecord] = []

    fam_a_401: Tuple[str, ...] = (
        "V200", "V201", "V202", "V203", "V204", "V205", "V206",
        "V210", "V211", "V300", "V301", "V302", "V303", "V304", "V305",
    )
    for bid in fam_a_401:
        recs.append(_rec(
            PLANO_401, bid, "V.60/80", BeamKind.CONTINUOUS,
            axes_text="3-2-1", group="continua 3-2-1 (familia A)",
            longitudinal=FAM_A_NOTE,
            stirrups="ED B10@10 / B10@20 ; TP1/TP4 plano 002",
            detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
            confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
            note="leer cada linea del plano 401; longitudes por dibujo.",
        ))

    fam_b_401: Tuple[str, ...] = (
        "V207", "V208", "V209",
    )
    for bid in fam_b_401:
        recs.append(_rec(
            PLANO_401, bid, "V.60/80 (vano unico/especial)",
            BeamKind.SINGLE_SPAN,
            axes_text="", group="familia B",
            longitudinal="detalle individual (posible B18/B16)",
            stirrups="ED (ver plano 002)",
            confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
            note="viga especial/vanos individuales entre G-H/F; "
                 "no extrapolar a B22.",
        ))
    return segs, stirs, recs


def _plan402(s: _Seq) -> Tuple[List[BeamRebarSegment], List[BeamStirrupZone],
                               List[BeamRecord]]:
    segs: List[BeamRebarSegment] = []
    stirs: List[BeamStirrupZone] = []
    recs: List[BeamRecord] = []

    fam_a_402: Tuple[str, ...] = ("V306", "V307", "V308",
                                  "V400", "V401", "V402", "V403", "V404",
                                  "V405")
    for bid in fam_a_402:
        recs.append(_rec(
            PLANO_402, bid, "V.60/80", BeamKind.CONTINUOUS,
            axes_text="3-2-1", group="continua 3-2-1 (familia A)",
            longitudinal=FAM_A_NOTE,
            stirrups="ED B10@10 / B10@20 ; TP1/TP4 plano 002",
            detail_reference="TP.1_PLANO_002; TP.4_PLANO_002",
            confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
            note="leer cada linea del plano 402; longitudes por dibujo.",
        ))

    fam_b_402: Tuple[str, ...] = ("V309", "V406")
    for bid in fam_b_402:
        recs.append(_rec(
            PLANO_402, bid, "V.60/80 (vano unico/especial)",
            BeamKind.SINGLE_SPAN,
            axes_text="", group="familia B",
            longitudinal="detalle individual (posible B18/B16)",
            stirrups="ED (ver plano 002)",
            confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
            note="viga especial/vanos individuales; no extrapolar a B22.",
        ))

    # VF1-VF3: vigas de fundacion, E'-Eb-Ec-F' (plano 402) ----
    for bid in ("VF1", "VF2", "VF3"):
        recs.append(_rec(
            PLANO_402, bid, "VF (fundacion, pieza profunda continua)",
            BeamKind.FOUNDATION_BEAM,
            axes_text="E'-Eb-Ec-F'", group="VF",
            longitudinal="varias capas longitudinales: B18 predominante, "
                         "continuas y adicionales a distintos niveles",
            stirrups="ED (ver plano 002)",
            note="NO reducir a '2 B22'; no mezclar con V100-V406.",
            confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        ))

    # Seccion escalonada especial del plano 402 ----
    recs.append(_rec(
        PLANO_402, "SECC_402", "escalonada ~60x80 (escalones ~40+40)",
        BeamKind.SPECIAL,
        axes_text="", group="LT1_SPECIAL_STEPPED_BEAM_SECTION",
        longitudinal="2B18 L~400 ; 4B16 L~335 x2 ; adicionales 2B10 y 1B10",
        stirrups="E B10@10 L~220 ; E B10@10 L~200 ; traba T B10@10 L~55",
        note="asociar SOLO al elemento/detalle correspondiente del plano "
             "402; NO aplicado a V60/80 ni a todo LT1.",
    ))
    segs.append(_seg(s, PLANO_402, [], "SECC_402-2B18",
                     BeamBarLayer.TOP_BASE, 2, 18,
                     length_cm=400,
                     note="seccion especial 402: 2B18 L~400."))
    segs.append(_seg(s, PLANO_402, [], "SECC_402-4B16-a",
                     BeamBarLayer.TOP_ADDITIONAL, 4, 16,
                     length_cm=335,
                     note="seccion especial 402: 4B16 L~335 (1a)."))
    segs.append(_seg(s, PLANO_402, [], "SECC_402-4B16-b",
                     BeamBarLayer.TOP_ADDITIONAL, 4, 16,
                     length_cm=335,
                     note="seccion especial 402: 4B16 L~335 (2a)."))
    segs.append(_seg(s, PLANO_402, [], "SECC_402-2B10",
                     BeamBarLayer.BOTTOM_ADDITIONAL, 2, 10,
                     note="seccion especial 402: adicional longitudinal "
                          "2B10 (L no transcrita)."))
    segs.append(_seg(s, PLANO_402, [], "SECC_402-1B10",
                     BeamBarLayer.BOTTOM_ADDITIONAL, 1, 10,
                     note="seccion especial 402: adicional longitudinal "
                          "1B10 (L no transcrita)."))
    stirs.append(_stir(s, PLANO_402, [], type="E", diameter_mm=10,
                       spacing_cm=10, detail_reference="SECC_402",
                       note="seccion especial 402: E B10@10 L~220."))
    stirs.append(_stir(s, PLANO_402, [], type="E", diameter_mm=10,
                       spacing_cm=10, detail_reference="SECC_402",
                       note="seccion especial 402: E B10@10 L~200."))
    stirs.append(_stir(s, PLANO_402, [], type="T", diameter_mm=10,
                       spacing_cm=10, detail_reference="SECC_402",
                       note="seccion especial 402: traba T B10@10 L~55."))

    return segs, stirs, recs


# ---------------------------------------------------------------------------
# Dataset compilado de vigas
# ---------------------------------------------------------------------------
def load_lt1_beam_data() -> Dict[str, List]:
    """Retorna el dataset de vigas LT1 agrupado por tipo.

    Keys: "segments" (BeamRebarSegment), "stirrups" (BeamStirrupZone),
    "records" (BeamRecord por beam_id del plano).
    """
    s = _Seq()
    segs: List[BeamRebarSegment] = []
    stirs: List[BeamStirrupZone] = []
    recs: List[BeamRecord] = []
    for fn in (_plan400, _plan401, _plan402):
        sg, st, rc = fn(s)
        segs.extend(sg)
        stirs.extend(st)
        recs.extend(rc)
    return {"segments": segs, "stirrups": stirs, "records": recs}


def all_beam_ids() -> List[str]:
    """Todos los beam_ids del plano (orden: 400, 401, 402)."""
    return list(BEAM_IDS_400 + BEAM_IDS_401 + BEAM_IDS_402)


if __name__ == "__main__":
    import sys

    data = load_lt1_beam_data()
    print("Conteos de vigas:")
    for key, items in data.items():
        print(f"  {key}: {len(items)}")
    print("Beam IDs en planos 400/401/402:", len(all_beam_ids()))
    sys.exit(0)