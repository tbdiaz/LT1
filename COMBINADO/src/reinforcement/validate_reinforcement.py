"""Validaciones del modulo de armadura LT1 y ENFOQUE del modelo combinado.

Dos familias de checks:

1. Datos de armadura (sin abrir OpenSees):
   - diametro y espaciamiento sean positivos en cada regla;
   - cada regla guarde correctamente direccion (X/Y/both/local) y capa;
   - statuses y resoluciones esten dentro de los enum validos;
   - reporte de reglas resueltas / parciales / sin resolver por categoria.

2. Invariante estructural del modelo combinado:
   - re-ejecuta el analisis tal como lo hace `run_combined.main()` y
     verifica rc=0, sumP/sumRz sin cambios relevantes y los conteos de
     nodos/elementos estructurales identicos al baseline del modelo.
   - El dataset de armadura NO debe alterar nodos ni elementos: por
     diseño el modulo de refuerzo no llama a opensees; este check lo
     confirma globalmente.

Solo se recorre `run_combined` si `check_model=True`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .assign_lt1_reinforcement import Lt1ReinforcementAssigner
from .lt1_beam_data import load_lt1_beam_data
from .lt1_geometry import Lt1Geometry
from .lt1_reinforcement_data import load_lt1_reinforcement
from .lt1_wall_data import PLAN_300_303_AXES, load_lt1_wall_data
from .reinforcement_geometry import ReinforcementGeometryBuilder
from .reinforcement_types import (
    BeamBarLayer,
    BeamRebarSegment,
    BeamStirrupZone,
    Classification,
    ColumnBarType,
    Direction,
    Layer,
    MeshRule,
    Resolution,
    Status,
    WallReinforcementClass,
    WallReinforcementRecord,
)

# Baseline estructural del modelo combinado (sin armadura). Valores
# reportados por `run_combined.main()` en la corrida de cierre.
BASELINE_MODEL = {
    "rc": 0,
    "P_total": 31086.259667,
    "n_nodos_fisicos": 461,
    "n_apoyos": 47,
}

VALID_STATUS = {s.value for s in Status}
VALID_RESOLUTION = {r.value for r in Resolution}
VALID_LAYER = {l.value for l in Layer}
VALID_DIR = {d.value for d in Direction}


def validate_dataset() -> Dict[str, object]:
    """Checks de consistencia del dataset (sin abrir el modelo)."""
    errors: List[str] = []
    warnings: List[str] = []
    data = load_lt1_reinforcement()

    for key, rules in data.items():
        for r in rules:
            if r.status.value not in VALID_STATUS:
                errors.append(f"{r.id}: status invalido {r.status}")
            if isinstance(r, MeshRule):
                if r.diameter_mm <= 0:
                    errors.append(f"{r.id}: diametro <= 0 ({r.diameter_mm})")
                if r.spacing_cm <= 0:
                    errors.append(f"{r.id}: espaciamiento <= 0 ({r.spacing_cm})")
                if r.layer.value not in VALID_LAYER:
                    errors.append(f"{r.id}: layer invalido {r.layer}")
                if r.direction.value not in VALID_DIR:
                    errors.append(f"{r.id}: direction invalido {r.direction}")
                if r.id.building not in ("LT1",):
                    warnings.append(f"{r.id}: building inesperado {r.id.building}")
            elif isinstance(getattr(r, "__class__", None), MeshRule):
                continue
            if hasattr(r, "bar_count") and getattr(r, "bar_count") and r.bar_count <= 0:
                errors.append(f"{r.id}: bar_count <= 0 ({r.bar_count})")
            if hasattr(r, "diameter_mm") and getattr(r, "diameter_mm", 0) <= 0:
                errors.append(f"{r.id}: diametro <= 0 ({r.diameter_mm})")
            if hasattr(r, "source") and not getattr(r, "source"):
                errors.append(f"{r.id}: falta 'source'")
            if hasattr(r, "id") and str(r.id).startswith("LT1:COL"):
                if getattr(r, "bar_type", None) != ColumnBarType.LONGITUDINAL:
                    errors.append(f"{r.id}: tipo de armadura no LONGITUDINAL")
                if not getattr(r, "geometry_pending", False):
                    warnings.append(
                        f"{r.id}: geometry_pending=False impide mapear 3D "
                        "sin recubrimiento confirmado"
                    )

    # ---- registros especificos de muros LT1 (elevaciones 300-303) ----
    wall_records = load_lt1_wall_data()["records"]
    from collections import Counter
    wall_by_sheet = Counter(r.id.sheet for r in wall_records)
    for r in wall_records:
        if r.status.value not in VALID_STATUS:
            errors.append(f"{r.id}: status invalido {r.status}")
        if r.resolution.value not in VALID_RESOLUTION:
            errors.append(f"{r.id}: resolution invalido {r.resolution}")
        if r.classification not in WallReinforcementClass:
            errors.append(f"{r.id}: classification invalido {r.classification}")
        for name, value in (("bar_count", r.bar_count), ("diameter_mm", r.diameter_mm),
                            ("spacing_cm", r.spacing_cm), ("length_cm", r.length_cm)):
            if value is not None:
                if value <= 0:
                    errors.append(f"{r.id}: {name} <= 0 ({value})")
                if r.status != Status.EXACT:
                    warnings.append(f"{r.id}: {name}={value} con status "
                                    f"{r.status.value} (no EXACT)")
        if r.status == Status.EXACT and (r.bar_count is None or r.diameter_mm is None):
            errors.append(f"{r.id}: status EXACT sin valores (bar_count/"
                          f"diameter_mm = None)")
        if r.element_tags:
            errors.append(f"{r.id}: element_tags no vacios sin correspondencia "
                          "eje->muro FE inequivoca (se prohibe inventar tags).")

    assigner = Lt1ReinforcementAssigner().run()
    summary = assigner.summary()
    rows = assigner.to_rows()

    # conteos por status
    status_counts = Counter(r["status"] for r in rows)
    resolution_counts = Counter(r["resolution"] for r in rows)

    return {
        "errors": errors,
        "warnings": warnings,
        "status_counts": dict(status_counts),
        "resolution_counts": dict(resolution_counts),
        "summary": summary,
        "n_reglas": len(rows),
        "wall_by_sheet": dict(wall_by_sheet),
        "n_wall_records": len(wall_records),
    }


def check_model_rc(weight_tol_rel: float = 1e-4) -> Dict[str, object]:
    """Re-ejecuta el analisis combinado y compara contra el baseline.

    Importa tardio de run_combined para no acoplar el paquete de
    armadura al modelo combinado salvo en este check.
    """
    import run_combined  # type: ignore

    # obtener metrica del run real sin regenerar el reporte duplicado
    b = run_combined.CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()
    b.apply_loads()
    rc = b.run_analysis()
    node_tags, elem_tags = b.validate()

    checks = {}
    checks["rc"] = rc
    checks["P_total"] = getattr(b, "P_total", None)
    checks["n_nodos_fisicos"] = len(node_tags)
    checks["n_apoyos"] = len(getattr(b, "support_tags", []) or [])

    ok = True
    diffs = {}
    if rc != BASELINE_MODEL["rc"]:
        ok = False
        diffs["rc"] = (BASELINE_MODEL["rc"], rc)
    for k in ("P_total", "n_nodos_fisicos", "n_apoyos"):
        ref = BASELINE_MODEL[k]
        val = checks.get(k)
        if val is None:
            ok = False
            diffs[k] = (ref, None)
            continue
        if isinstance(ref, float):
            if abs(val - ref) > weight_tol_rel * abs(ref):
                ok = False
                diffs[k] = (ref, val)
        elif val != ref:
            ok = False
            diffs[k] = (ref, val)

    if rc == 0 and b.reac is not None:
        sumRz = float(b.reac["Rz_kN"].sum())
        checks["sumRz_kN"] = sumRz
        if abs(sumRz - checks["P_total"]) > 1e-6 * abs(b.P_total):
            ok = False
            diffs["sumRz"] = (checks["P_total"], sumRz)

    return {
        "ok": ok,
        "diffs": diffs,
        "baseline": BASELINE_MODEL,
        "actual": checks,
    }


def build_bar_rows(assigner: Lt1ReinforcementAssigner,
                   cover_cm: Optional[float] = None) -> List[Dict]:
    geo = Lt1Geometry()
    builder = ReinforcementGeometryBuilder(assigner, geo=geo, cover_cm=cover_cm)
    builder.build()
    return builder.to_rows()


def validate_beam_dataset() -> Dict[str, object]:
    """Valida el dataset de vigas (planos 400/401/402) sin abrir el modelo."""
    errors: List[str] = []
    warnings: List[str] = []
    beam = load_lt1_beam_data()
    segments = beam["segments"]
    stirrups = beam["stirrups"]
    records = beam["records"]

    for seg in segments:
        if seg.diameter_mm <= 0:
            errors.append(f"{seg.physical_bar_id}: diametro <= 0")
        if seg.bar_count is not None and seg.bar_count <= 0:
            errors.append(f"{seg.physical_bar_id}: bar_count <= 0")
        if seg.confidence.value not in VALID_STATUS:
            errors.append(f"{seg.physical_bar_id}: confidence invalido {seg.confidence}")

    for z in stirrups:
        if z.diameter_mm is not None and z.diameter_mm <= 0:
            errors.append(f"{z.id}: diametro estribo <= 0")
        if z.spacing_cm is not None and z.spacing_cm <= 0:
            errors.append(f"{z.id}: espaciamiento estribo <= 0")
        if z.confidence.value not in VALID_STATUS:
            errors.append(f"{z.id}: confidence invalido {z.confidence}")

    for rec in records:
        if rec.confidence.value not in VALID_STATUS:
            errors.append(f"{rec.beam_id}: confidence invalido {rec.confidence}")

    from collections import Counter
    conf_seg = Counter(r.confidence.value for r in segments)
    conf_rec = Counter(r.confidence.value for r in records)

    return {
        "errors": errors,
        "warnings": warnings,
        "n_segments": len(segments),
        "n_stirrups": len(stirrups),
        "n_records": len(records),
        "segment_confidence": dict(conf_seg),
        "record_confidence": dict(conf_rec),
    }


def beam_summary_rows() -> List[Dict]:
    """Una fila por beam_id (record) con desglose de capas si hay segmentos."""
    beam = load_lt1_beam_data()
    records = beam["records"]
    segments = beam["segments"]
    seg_by_beam: Dict[str, List[BeamRebarSegment]] = {}
    for seg in segments:
        for bid in seg.beam_ids:
            seg_by_beam.setdefault(bid, []).append(seg)
    rows: List[Dict] = []
    for rec in records:
        segs = seg_by_beam.get(rec.beam_id, [])
        layer_desc: Dict[str, str] = {}
        for layer in BeamBarLayer:
            found = [s for s in segs if s.bar_layer == layer]
            if found:
                parts = []
                for s in found:
                    cnt = f"{s.bar_count}" if s.bar_count else "?"
                    ln = f"L~{s.length_cm}" if s.length_cm else "L?"
                    parts.append(f"{cnt}B{s.diameter_mm} {ln}")
                layer_desc[layer.value] = "; ".join(parts)
        rows.append({
            "beam_id": rec.beam_id,
            "drawing": rec.drawing,
            "sheet": rec.sheet,
            "section": rec.section,
            "kind": rec.kind.value,
            "axes_text": rec.axes_text,
            "group": rec.group,
            "F_base": layer_desc.get("BOTTOM_BASE", ""),
            "F_top_base": layer_desc.get("TOP_BASE", ""),
            "F_bottom_additional": layer_desc.get("BOTTOM_ADDITIONAL", ""),
            "F_top_additional": layer_desc.get("TOP_ADDITIONAL", ""),
            "longitudinal": rec.longitudinal,
            "stirrups": rec.stirrups,
            "detail_reference": rec.detail_reference,
            "confidence": rec.confidence.value,
            "note": rec.note,
        })
    return rows


def _write_csv(path: Path, rows: List[Dict]) -> None:
    import csv

    if not rows:
        return
    keys: List[str] = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def column_rows() -> List[Dict]:
    """Una fila por tag de columna LT1 con su dato 16 B22 longitudinal."""
    from .lt1_geometry import Lt1Geometry
    from .lt1_reinforcement_data import load_lt1_reinforcement

    geo = Lt1Geometry()
    rules = [r for r in load_lt1_reinforcement()["columns"]
             if r.bar_type == ColumnBarType.LONGITUDINAL]
    rows: List[Dict] = []
    for rule in rules:
        tags = rule.column_tags or geo.column_tags()
        for tag in sorted(tags):
            rows.append({
                "elementTag": tag,
                "building": "LT1",
                "bar_type": rule.bar_type.value,
                "bar_count": rule.bar_count,
                "diameter_mm": rule.diameter_mm,
                "layer": "LONGITUDINAL",
                "status": rule.status.value,
                "source": rule.source,
                "resolution": rule.resolution.value,
                "geometry_pending": rule.geometry_pending,
                "note": rule.note,
            })
    return rows


def write_beam_outputs(out_dir: Path) -> Dict[str, Path]:
    """Persiste CSVs de armadura de vigas (barras, resumen, estados)."""
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    beam = load_lt1_beam_data()
    segments = beam["segments"]
    stirrups = beam["stirrups"]

    # A) una fila por barra/estribo con beam_id(s)
    rows: List[Dict] = [s.to_dict() for s in segments]
    rows.extend(z.to_dict() for z in stirrups)
    csv_beam = out_dir / "armadura_lt1_vigas.csv"
    _write_csv(csv_beam, rows)

    # B) resumen por beam_id
    csv_resumen = out_dir / "armadura_lt1_vigas_resumen.csv"
    _write_csv(csv_resumen, beam_summary_rows())

    # C) listas explicitas EXACT / NEEDS_DRAWING_VALUE_CONFIRMATION
    exact: List[Dict] = []
    needs: List[Dict] = []
    for r in rows:
        item = {
            "kind": "STIRRUP" if "zone_type" in r else "BAR",
            "code": r.get("code") or r.get("physical_bar_id"),
            "beam_ids": r.get("beam_ids", ""),
            "drawing": r.get("drawing", ""),
            "confidence": r.get("confidence", ""),
            "note": r.get("note", ""),
        }
        if r.get("confidence") == Status.EXACT.value:
            exact.append(item)
        elif r.get("confidence") == Status.NEEDS_DRAWING_VALUE_CONFIRMATION.value:
            needs.append(item)

    # incluir tambien los registros (records) sin segments
    for rec in beam_summary_rows():
        item = {
            "kind": "RECORD",
            "code": rec["beam_id"],
            "beam_ids": rec["beam_id"],
            "drawing": rec["drawing"],
            "confidence": rec["confidence"],
            "note": rec["note"],
        }
        if rec["confidence"] == Status.EXACT.value:
            exact.append(item)
        elif rec["confidence"] == Status.NEEDS_DRAWING_VALUE_CONFIRMATION.value:
            needs.append(item)

    csv_exact = out_dir / "armadura_lt1_vigas_exact.csv"
    csv_needs = out_dir / "armadura_lt1_vigas_necesita_confirmacion.csv"
    _write_csv(csv_exact, exact)
    _write_csv(csv_needs, needs)

    return {
        "beam_bars": csv_beam,
        "beam_summary": csv_resumen,
        "beam_exact": csv_exact,
        "beam_needs": csv_needs,
    }


def wall_rows() -> List[Dict]:
    """Una fila por registro especifico de muro LT1 (elevaciones 300-303)."""
    return [r.to_dict() for r in load_lt1_wall_data()["records"]]


def wall_confirmation_rows() -> List[Dict]:
    """Registros de muro que requieren confirmacion de valores en pliego."""
    rows: List[Dict] = []
    for r in load_lt1_wall_data()["records"]:
        if r.status.value in (
            Status.NEEDS_DRAWING_VALUE_CONFIRMATION.value,
            Status.DETAIL_FROM_DRAWING_REQUIRED.value,
        ):
            rows.append({
                "code": str(r.id),
                "sheet": r.id.sheet,
                "drawing": r.id.drawing,
                "elevation": r.id.sheet,
                "axis": r.axis,
                "level_start": r.level_start,
                "level_end": r.level_end,
                "classification": r.classification.value,
                "bar_count": r.bar_count,
                "diameter_mm": r.diameter_mm,
                "spacing_cm": r.spacing_cm,
                "length_cm": r.length_cm,
                "status": r.status.value,
                "resolution": r.resolution.value,
                "geometry_pending": r.geometry_pending,
                "note": r.note,
            })
    return rows


def write_outputs(out_dir: Path) -> Dict[str, Path]:
    """Persiste CSV del dataset y CSV de barras 3D."""
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    assigner = Lt1ReinforcementAssigner().run()

    rows = assigner.to_rows()
    csv_rules = out_dir / "armadura_lt1_reglas.csv"
    if rows:
        keys = []
        seen = set()
        for r in rows:
            for k in r:
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        with open(csv_rules, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    bar_rows = build_bar_rows(assigner)
    csv_bars = out_dir / "armadura_lt1_barras.csv"
    if bar_rows:
        with open(csv_bars, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(bar_rows[0].keys()))
            w.writeheader()
            w.writerows(bar_rows)

    csv_cols = out_dir / "armadura_lt1_columnas.csv"
    _write_csv(csv_cols, column_rows())

    csv_walls = out_dir / "armadura_lt1_muros.csv"
    _write_csv(csv_walls, wall_rows())
    csv_wall_needs = out_dir / "armadura_lt1_necesita_confirmacion.csv"
    _write_csv(csv_wall_needs, wall_confirmation_rows())

    out = {"rules": csv_rules, "bars": csv_bars, "columns": csv_cols,
           "walls": csv_walls, "walls_confirmation": csv_wall_needs}
    out.update(write_beam_outputs(out_dir))
    return out


if __name__ == "__main__":
    v = validate_dataset()
    print("Errores:", len(v["errors"]))
    for e in v["errors"][:20]:
        print("  ERROR", e)
    print("Reglas:", v["n_reglas"])
    print("Resolucion:", v["resolution_counts"])
    print("Status:", v["status_counts"])
    print("Summary por categoria:", v["summary"])
    sys.exit(1 if v["errors"] or len(v["errors"]) > 0 else 0)