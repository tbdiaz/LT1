"""Armadura de escaleras LT2 desde el plano 500 (plantas y cortes).

TRANSCRIPCION FIEL del levantamiento del plano de escaleras LT2
(2024_22-500). NO se copian longitudes entre cortes distintos (A/B/C):
cada valor proviene del corte en el que se observo. La nomenclatura del
plano usa F/F' (inferior/superior) y longitudes dibujadas (L).

Los tramos/descansos NO tienen elementos estructurales en el modelo
combinado (LT2): por eso los registros quedan como metadata
(RESOLVED_METADATA) sin inventar elementTags.

Este modulo NO depende de OpenSeesPy ni del modelo combinado.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .reinforcement_types import (
    RuleId,
    StairPart,
    StairReinforcementRecord,
    Status,
)

PLANO_500 = "500"
BEAM_DRAWING_500 = "2024_22-500-Model"

# Recorridos de escalera del plano (según plantas).
STAIR_LEVELS = "1_SUB-1_PISO ; 1_PISO-4_PISO ; 4_PISO-CUBIERTA"

_NOTE_CORTE_C = (
    "valores del CORTE C del plano 500; NO se extrapolan a los cortes "
    "A/B (sus longitudes difieren)."
)


class _Seq:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}

    def next(self, sheet: str) -> int:
        self._n[sheet] = self._n.get(sheet, 0) + 1
        return self._n[sheet]


def _stair(s: _Seq, sheet: str, part: StairPart, notation: str, *,
           bar_count: Optional[int] = None, diameter_mm: Optional[int] = None,
           spacing_cm: Optional[int] = None, length_cm: Optional[int] = None,
           detail_reference: str = "", levels: str = STAIR_LEVELS,
           status: Status = Status.EXACT, note: str = "") -> StairReinforcementRecord:
    return StairReinforcementRecord(
        id=RuleId("LT2", BEAM_DRAWING_500, sheet, s.next(sheet)),
        part=part,
        notation=notation,
        bar_count=bar_count,
        diameter_mm=diameter_mm,
        spacing_cm=spacing_cm,
        length_cm=length_cm,
        detail_reference=detail_reference,
        levels=levels,
        status=status,
        note=note,
    )


def load_lt2_stair_data() -> Dict[str, List]:
    s = _Seq()
    records: List[StairReinforcementRecord] = []

    # ---- Refuerzo transversal de los tramos ----
    records.append(_stair(
        s, PLANO_500, StairPart.FLIGHT_RAMP, "Φ8@20 TIP (transversal)",
        diameter_mm=8, spacing_cm=20,
        note="refuerzo transversal de los tramos de escalera (TIP).",
    ))

    # ---- Longitudinal / principal (familias observadas en los cortes) ----
    records.append(_stair(
        s, PLANO_500, StairPart.FLIGHT_RAMP, "longitudinal/principal Φ10@10",
        diameter_mm=10, spacing_cm=10,
        note="armadura longitudinal principal observada en los cortes.",
    ))
    records.append(_stair(
        s, PLANO_500, StairPart.FLIGHT_RAMP, "longitudinal/principal Φ10@20",
        diameter_mm=10, spacing_cm=20,
        note="armadura longitudinal principal observada en los cortes.",
    ))

    # ---- CORTE C: rampa (L≈ cm) ----
    records.append(_stair(
        s, PLANO_500, StairPart.FLIGHT_RAMP, "F' Φ8@20 L≈180 (150+30)",
        diameter_mm=8, spacing_cm=20, length_cm=180,
        detail_reference="CORTE C",
        note="F' (superior) del tramo, L≈180 = 150+30. " + _NOTE_CORTE_C,
    ))
    records.append(_stair(
        s, PLANO_500, StairPart.FLIGHT_RAMP, "F Φ10@10 L≈455",
        diameter_mm=10, spacing_cm=10, length_cm=455,
        detail_reference="CORTE C",
        note="F (inferior) del tramo, L≈455. " + _NOTE_CORTE_C,
    ))
    records.append(_stair(
        s, PLANO_500, StairPart.FLIGHT_RAMP, "F=F' 2Φ12 L≈455",
        bar_count=2, diameter_mm=12, length_cm=455,
        detail_reference="CORTE C",
        note="2Φ12 continuas (F=F'), L≈455. " + _NOTE_CORTE_C,
    ))

    # ---- CORTE C: descanso (L≈ cm) ----
    records.append(_stair(
        s, PLANO_500, StairPart.LANDING, "F' Φ10@10 L≈215",
        diameter_mm=10, spacing_cm=10, length_cm=215,
        detail_reference="CORTE C",
        note="F' del descanso, L≈215. " + _NOTE_CORTE_C,
    ))
    records.append(_stair(
        s, PLANO_500, StairPart.LANDING, "F Φ10@20 L≈215",
        diameter_mm=10, spacing_cm=20, length_cm=215,
        detail_reference="CORTE C",
        note="F del descanso, L≈215. " + _NOTE_CORTE_C,
    ))
    records.append(_stair(
        s, PLANO_500, StairPart.LANDING, "F=F' 2+2Φ16 L≈215",
        bar_count=4, diameter_mm=16, length_cm=215,
        detail_reference="CORTE C",
        note="2+2Φ16 (F=F') del descanso, L≈215. " + _NOTE_CORTE_C,
    ))

    # ---- Conexiones / apoyos / bordes ----
    records.append(_stair(
        s, PLANO_500, StairPart.SUPPORT_LOCAL, "4Φ12 en encuentros rampa-descanso",
        bar_count=4, diameter_mm=12,
        note="refuerzo local en el encuentro rampa-descanso.",
    ))
    records.append(_stair(
        s, PLANO_500, StairPart.EDGE, "2Φ12 en bordes",
        bar_count=2, diameter_mm=12,
        note="barras de borde de los tramos.",
    ))

    # ---- Detalles PL1/PL2/PL3 del plano ----
    records.append(_stair(
        s, PLANO_500, StairPart.DETAIL, "detalles PL1 / PL2 / PL3",
        detail_reference="PL1; PL2; PL3",
        status=Status.DETAIL_FROM_DRAWING_REQUIRED,
        note="Detalles del plano 500 (separadores, empalmes, anclajes, "
             "espesores/alturas graficos). El modelo combinado NO tiene "
             "elementos de escalera: no se fabrican elementos FE.",
    ))

    return {"records": records}


if __name__ == "__main__":
    import sys

    data = load_lt2_stair_data()
    print("Registros de escaleras LT2:", len(data["records"]))
    sys.exit(0)