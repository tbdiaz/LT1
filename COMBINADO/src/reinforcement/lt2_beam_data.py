"""Armadura longitudinal de vigas LT2 desde el plano de vigas 400.

TRANSCRIPCION FIEL del levantamiento del plano de vigas LT2
(2024_22-400). A diferencia del dataset LT1 (que se levanto viga por
viga con beam_ids del plano), en el plano 400 los beam_ids NO son
legibles por texto; solo se distinguen FAMILIAS y segmentos de armadura
por zonas/ejes. Por eso:

- Se registra una barra como EXACT solo cuando el dato se leyo sin
  ambiguedad (diametro, cantidad y longitud dibujada "L≈").
- Un segmento NO se asocia a beam_id cuando el numero de viga no es
  legible: los segmentos con ``beam_ids=[]`` explicitan que la viga NO
  se puede nombrar (reference de familia/zona en physical_bar_id).
- NO se extrapola el patron V.60/80 a "todas las vigas": se conserva
  como patrón observado (NEEDS_DRAWING_VALUE_CONFIRMATION) sin asignar.
- Vigas de fundacion y especiales (V.F., V.I.) NO reciben la armadura
  V.60/80.
- Estribos ED: las familias ED B10@10 / ED B10@20 se observan repetidas,
  pero sin extension/cantidad legible NO se convierte a zonas: quedan
  con confidence=NEEDS_DRAWING_VALUE_CONFIRMATION y spacing pasado como
  observado (sin estaciones).

Este modulo NO depende de OpenSeesPy ni del modelo combinado.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .reinforcement_types import (
    BeamBarLayer,
    BeamKind,
    BeamRebarSegment,
    BeamRecord,
    BeamStirrupZone,
    Classification,
    RuleId,
    Status,
)

# ---------------------------------------------------------------------------
# Planos de vigas LT2
# ---------------------------------------------------------------------------
PLANO_400 = "400"
BEAM_DRAWING_400 = "2024_22-400-Model"


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
        id=RuleId("LT2", BEAM_DRAWING_400, sheet, s.next(sheet)),
        beam_ids=beam_ids,
        physical_bar_id=phys,
        bar_layer=layer,
        bar_count=count,
        diameter_mm=dia,
        **kw,
    )


def _stir(s: _Seq, sheet: str, **kw) -> BeamStirrupZone:
    return BeamStirrupZone(
        id=RuleId("LT2", BEAM_DRAWING_400, sheet, s.next(sheet)),
        beam_ids=[],
        **kw,
    )


def _v_rec(sheet: str, beam_id: str, section: str, kind: BeamKind,
           **kw) -> BeamRecord:
    return BeamRecord(
        beam_id=beam_id,
        drawing=BEAM_DRAWING_400,
        sheet=sheet,
        section=section,
        kind=kind,
        building="LT2",
        **kw,
    )


# ---------------------------------------------------------------------------
# Dataset de vigas plano 400
# ---------------------------------------------------------------------------
def _vigas_400() -> Tuple[List[BeamRecord], List[BeamRebarSegment],
                          List[BeamStirrupZone]]:
    s = _Seq()
    records: List[BeamRecord] = []
    segments: List[BeamRebarSegment] = []
    stirrups: List[BeamStirrupZone] = []

    # ---- A) V.F.20/150.5 entre ejes 8A-8B (vigas de fundacion) ----
    records.append(_v_rec(
        PLANO_400,
        "VF.20/150.5 [8A-8B]",
        "V.F.20/150.5",
        BeamKind.FOUNDATION_BEAM,
        axes_text="ejes 8A-8B",
        longitudinal="F' sup: 2Φ18 L≈550 ; F inf: 2Φ18 L≈550",
        confidence=Status.EXACT,
        note="Viga de fundacion (V.F.). FOUNDATION/SPECIAL: NO recibe la "
             "armadura V.60/80.",
    ))
    segments.append(_seg(s, PLANO_400, [], "LT2-8A8B-F'-base",
                         BeamBarLayer.TOP_BASE, 2, 18,
                         length_cm=550,
                         classification=Classification.BEAM_FOUNDATION,
                         beam_kind=BeamKind.FOUNDATION_BEAM,
                         confidence=Status.EXACT,
                         start_axis="8A", end_axis="8B",
                         note="F' 2Φ18 L≈550 (sup)."))
    segments.append(_seg(s, PLANO_400, [], "LT2-8A8B-F-base",
                         BeamBarLayer.BOTTOM_BASE, 2, 18,
                         length_cm=550,
                         classification=Classification.BEAM_FOUNDATION,
                         beam_kind=BeamKind.FOUNDATION_BEAM,
                         confidence=Status.EXACT,
                         start_axis="8A", end_axis="8B",
                         note="F 2Φ18 L≈550 (inf)."))

    # ---- B) V.60/80 familia principal (patron observado, NO universal) ----
    records.append(_v_rec(
        PLANO_400,
        "V.60/80 (patron)",
        "V.60/80",
        BeamKind.CONTINUOUS,
        axes_text="varios conjuntos continuos (NO regla universal)",
        longitudinal=(
            "F/F' base 2Φ22 + adicionales +2Φ22; longitudes visibles "
            "400/450/550/600/750/900/1000 cm; izquierda 2Φ22 L≈600 + +2Φ22 "
            "L≈400 ; apoyo 2Φ22 L≈1000 + +2Φ22 L≈900 ; derecha 2Φ22 L≈750 "
            "+ +2Φ22 L≈450"
        ),
        confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note="Patron observado en varios conjuntos continuos del plano 400. "
             "NO se extrapola a todas las vigas V.60/80: los beam_ids del "
             "plano no son legibles y la asociacion de cada segmento a una "
             "viga especifica queda pendiente de confirmacion.",
    ))
    # Segmentos del patron con beam_ids vacio (viga no nombrable).
    pattern = [
        (BeamBarLayer.TOP_BASE, 2, 22, 600, "ext-izq", "apoyo izq/extremo izq"),
        (BeamBarLayer.TOP_ADDITIONAL, 2, 22, 400, "ext-izq-adi", "adicional extremo izq"),
        (BeamBarLayer.TOP_BASE, 2, 22, 1000, "apoyo", "sobre apoyo"),
        (BeamBarLayer.TOP_ADDITIONAL, 2, 22, 900, "apoyo-adi", "adicional sobre apoyo"),
        (BeamBarLayer.TOP_BASE, 2, 22, 750, "ext-der", "extremo derecho"),
        (BeamBarLayer.TOP_ADDITIONAL, 2, 22, 450, "ext-der-adi", "adicional extremo der"),
    ]
    for layer, cnt, dia, ln, tag, note in pattern:
        segments.append(_seg(
            s, PLANO_400, [], f"V60/80-patron-{tag}",
            layer, cnt, dia,
            length_cm=ln,
            confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
            note=f"patron observado; {note}. beam_id no legible.",
        ))

    # ---- C) V.30/80 (0102 / 0102a) ----
    records.append(_v_rec(
        PLANO_400, "0102 / 0102a", "V.30/80", BeamKind.SINGLE_SPAN,
        axes_text="luz 375+375=750 (dos vanos)",
        longitudinal="F': sup 3Φ22 L≈900 ; F: inf 3Φ22 L≈900",
        confidence=Status.EXACT,
        note="V.30/80 de los vanos 0102/0102a.",
    ))
    segments.append(_seg(s, PLANO_400, ["0102", "0102a"], "0102-F'-sup",
                         BeamBarLayer.TOP_BASE, 3, 22,
                         length_cm=900,
                         confidence=Status.EXACT,
                         note="F' 3Φ22 L≈900 (sup)."))
    segments.append(_seg(s, PLANO_400, ["0102", "0102a"], "0102-F-inf",
                         BeamBarLayer.BOTTOM_BASE, 3, 22,
                         length_cm=900,
                         confidence=Status.EXACT,
                         note="F 3Φ22 L≈900 (inf)."))

    # ---- D) V.F.20/160 entre C'-D' (vigas de fundacion) ----
    records.append(_v_rec(
        PLANO_400, "VF.20/160 [C'-D']", "V.F.20/160", BeamKind.FOUNDATION_BEAM,
        axes_text="ejes C'-D'",
        longitudinal="F' sup: 2Φ22 L≈400 ; F inf: 2Φ22 L≈450",
        confidence=Status.EXACT,
        note="Viga de fundacion (V.F.). FOUNDATION/SPECIAL: NO recibe la "
             "armadura V.60/80.",
    ))
    segments.append(_seg(s, PLANO_400, [], "LT2-C'D'-F'-base",
                         BeamBarLayer.TOP_BASE, 2, 22,
                         length_cm=400,
                         classification=Classification.BEAM_FOUNDATION,
                         beam_kind=BeamKind.FOUNDATION_BEAM,
                         confidence=Status.EXACT,
                         start_axis="C'", end_axis="D",
                         note="F' 2Φ22 L≈400 (sup)."))
    segments.append(_seg(s, PLANO_400, [], "LT2-C'D'-F-base",
                         BeamBarLayer.BOTTOM_BASE, 2, 22,
                         length_cm=450,
                         classification=Classification.BEAM_FOUNDATION,
                         beam_kind=BeamKind.FOUNDATION_BEAM,
                         confidence=Status.EXACT,
                         start_axis="C'", end_axis="D",
                         note="F 2Φ22 L≈450 (inf)."))

    # ---- E) V.I.15/24 entre C'-D' (viga invertida especial) ----
    records.append(_v_rec(
        PLANO_400, "VI.15/24 [C'-D']", "V.I.15/24", BeamKind.SPECIAL,
        axes_text="ejes C'-D'",
        longitudinal="F'/F: 2Φ16 L≈350 (sup+inf)",
        confidence=Status.EXACT,
        note="Viga invertida especial (V.I.). INVERTED/SPECIAL: NO recibe "
             "la armadura V.60/80.",
    ))
    segments.append(_seg(s, PLANO_400, [], "LT2-C'D'-VI-F'-base",
                         BeamBarLayer.TOP_BASE, 2, 16,
                         length_cm=350,
                         beam_kind=BeamKind.SPECIAL,
                         confidence=Status.EXACT,
                         start_axis="C'", end_axis="D",
                         note="V.I.15/24 F' 2Φ16 L≈350 (sup)."))
    segments.append(_seg(s, PLANO_400, [], "LT2-C'D'-VI-F-base",
                         BeamBarLayer.BOTTOM_BASE, 2, 16,
                         length_cm=350,
                         beam_kind=BeamKind.SPECIAL,
                         confidence=Status.EXACT,
                         start_axis="C'", end_axis="D",
                         note="V.I.15/24 F 2Φ16 L≈350 (inf)."))

    # ---- F) 405 / 405a: V.60/80 principal + V.I.15/VAR (2ª ETAPA) ----
    records.append(_v_rec(
        PLANO_400, "405 / 405a", "V.60/80 + V.I.15/VAR (2ª ETAPA)",
        BeamKind.SPECIAL,
        axes_text="405 / 405a",
        longitudinal="V.60/80 principal + V.I.15/VAR superpuesto (2ª ETAPA)",
        confidence=Status.EXACT,
        note="La V.I.15/VAR de 2ª etapa se SUPERPONE como refuerzo local; "
             "NO reemplaza la V.60/80 del elemento.",
    ))

    # ---- Estribos (familias observadas sin extension legible) ----
    stirrups.append(_stir(
        s, PLANO_400, type="ED", diameter_mm=10, spacing_cm=10,
        confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note="Familia ED Φ10@10 observada en el plano 400; extension/"
             "cantidad no legible -> NO se convierte a zona.",
    ))
    stirrups.append(_stir(
        s, PLANO_400, type="ED", diameter_mm=10, spacing_cm=20,
        confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note="Familia ED Φ10@20 observada en el plano 400; extension/"
             "cantidad no legible -> NO se convierte a zona.",
    ))
    stirrups.append(_stir(
        s, PLANO_400, type="ED", diameter_mm=10, spacing_cm=10,
        confidence=Status.NEEDS_DRAWING_VALUE_CONFIRMATION,
        note="Familia ED Φ10@10 local (sectores puntuales del plano 400); "
             "extension no legible -> NO se convierte a zona.",
    ))
    return records, segments, stirrups


def load_lt2_beam_data() -> Dict[str, List]:
    records, segments, stirrups = _vigas_400()
    return {
        "records": records,
        "segments": segments,
        "stirrups": stirrups,
    }


if __name__ == "__main__":
    import sys

    beam = load_lt2_beam_data()
    print("Registros LT2:", len(beam["records"]))
    print("Segmentos LT2:", len(beam["segments"]))
    print("Estribos LT2:", len(beam["stirrups"]))
    sys.exit(0)