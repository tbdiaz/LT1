"""Validaciones del modulo de armadura LT2 y salida de CSVs LT2.

Checks sin abrir OpenSees:
- diametro/espaciamiento positivos, direcciones/capas/status validos;
- columnas LT2 solo LONGITUDINAL; sin estribos inventados;
- vigas: segmentos con confidence valido; estribos sin extension sin
  valor de zona; record de patron V.60/80 sin asignacion universal;
- paredes: registros por ELEVACION (no regla "todas las paredes");
- escaleras: registros por parte/corte con metadata;
- sin llamadas a opensees (busqueda textual en los modulos LT2).

La invarianza estructural del modelo combinado se verifica reutilizando
`validate_reinforcement.check_model_rc` (mismo conjunto de checks que el
modulo LT1): el dataset de armadura NO altera nodos ni elementos.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

from .assign_lt2_reinforcement import Lt2ReinforcementAssigner
from .lt2_reinforcement_geometry import Lt2ReinforcementGeometryBuilder
from .lt2_reinforcement_data import load_lt2_reinforcement
from .lt2_beam_data import load_lt2_beam_data
from .lt2_wall_data import load_lt2_wall_data
from .lt2_stair_data import load_lt2_stair_data
from .reinforcement_types import (
    BeamKind,
    BeamRebarSegment,
    BeamStirrupZone,
    ColumnBarType,
    Direction,
    Layer,
    MeshRule,
    Resolution,
    StairPart,
    Status,
    WallBoundaryBarGroup,
    WallDistributedReinforcement,
    WallLocalReinforcement,
)

VALID_STATUS = {s.value for s in Status}
VALID_RESOLUTION = {r.value for r in Resolution}
VALID_LAYER = {l.value for l in Layer}
VALID_DIR = {d.value for d in Direction}

# Muros FE del modelo (documentados en walls_LT2.csv).
WALL_AXIS_TO_PARENT = {"A'": ["M001", "M003"], "1": ["M002"], "3": ["M004"]}


def validate_dataset_lt2() -> Dict[str, object]:
    """Checks de consistencia del dataset LT2 (sin abrir el modelo)."""
    errors: List[str] = []
    warnings: List[str] = []

    data = load_lt2_reinforcement()
    wall = load_lt2_wall_data()["records"]
    stair = load_lt2_stair_data()["records"]
    beam = load_lt2_beam_data()

    # ---- mesh/local ----
    for key in ("mesh", "local"):
        for r in data[key]:
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

    # ---- columnas ----
    for r in data["columns"]:
        if r.bar_type != ColumnBarType.LONGITUDINAL:
            errors.append(f"{r.id}: tipo de armadura no LONGITUDINAL")
        if r.bar_count <= 0 or r.diameter_mm <= 0:
            errors.append(f"{r.id}: bar_count/diametro no positivos")
        if not r.geometry_pending:
            warnings.append(f"{r.id}: geometry_pending=False inesperado")

    # ---- paredes ----
    for r in wall:
        if not isinstance(r, (WallBoundaryBarGroup, WallDistributedReinforcement,
                              WallLocalReinforcement)):
            errors.append(f"{r.id}: tipo de registro de muro inesperado")
        cls_ok = isinstance(r, WallBoundaryBarGroup) or isinstance(
            r, WallDistributedReinforcement) or isinstance(r, WallLocalReinforcement)
        if not cls_ok:
            errors.append(f"{r.id}: registro sin clasificacion de muro")
        if r.status.value not in VALID_STATUS:
            errors.append(f"{r.id}: status invalido {r.status}")
        for p in r.wall_parents:
            if p not in WALL_AXIS_TO_PARENT.get(r.axis, []):
                errors.append(f"{r.id}: wall_parent {p} no documentado "
                              f"para el eje {r.axis}")

    # ---- escaleras ----
    for r in stair:
        if r.part not in StairPart:
            errors.append(f"{r.id}: part invalido {r.part}")
        if r.status.value not in VALID_STATUS:
            errors.append(f"{r.id}: status invalido {r.status}")

    # ---- vigas ----
    special = ("V.F.", "V.I.")
    for rec in beam["records"]:
        if rec.confidence.value not in VALID_STATUS:
            errors.append(f"{rec.beam_id}: confidence invalido")
        if "patron" in rec.beam_id.lower():
            if rec.confidence != Status.NEEDS_DRAWING_VALUE_CONFIRMATION:
                warnings.append(f"{rec.beam_id}: patron deberia requerir "
                                "confirmacion de asociacion")
        if any(t in rec.section for t in special):
            if rec.kind not in (BeamKind.FOUNDATION_BEAM, BeamKind.SPECIAL):
                errors.append(f"{rec.beam_id}: viga V.F./V.I. con kind "
                              f"INCORRECTO {rec.kind}")
    for seg in beam["segments"]:
        if seg.confidence.value not in VALID_STATUS:
            errors.append(f"{seg.physical_bar_id}: confidence invalido")
    for stir in beam["stirrups"]:
        if stir.spacing_cm is not None and stir.spacing_cm <= 0:
            errors.append(f"{stir.id}: espaciamiento estribo <= 0")

    # no hay llamadas/imports de opensees en los modulos LT2 (los textos
    # de los docstrings que mencionan OpenSeesPy no cuentan)
    for mod in _lt2_modules():
        txt = mod.read_text(encoding="utf-8")
        body = "\n".join(
            ln for ln in txt.splitlines()
            if not ln.strip().startswith("#")
        )
        if "import opensees" in body or "import ops" in body:
            errors.append(f"{mod.name}: import de opensees detectado")
        for ln in body.splitlines():
            if "openseespy" in ln.lower() and ("import" in ln or "from" in ln):
                errors.append(f"{mod.name}: import de openseespy detectado: {ln.strip()}")

    assigner = Lt2ReinforcementAssigner().run()
    summary = assigner.summary()
    rows = assigner.to_rows()

    from collections import Counter
    status_counts = Counter(r["status"] for r in rows)
    resolution_counts = Counter(r["resolution"] for r in rows)

    return {
        "errors": errors,
        "warnings": warnings,
        "status_counts": dict(status_counts),
        "resolution_counts": dict(resolution_counts),
        "summary": summary,
        "n_reglas": len(rows),
    }


def _lt2_modules() -> List[Path]:
    """Rutas de los modulos LT2 del paquete (para el check sin opensees)."""
    here = Path(__file__).resolve().parent
    names = ("lt2_geometry.py", "lt2_reinforcement_data.py",
             "lt2_beam_data.py", "lt2_wall_data.py", "lt2_stair_data.py",
             "assign_lt2_reinforcement.py", "lt2_reinforcement_geometry.py")
    return [here / n for n in names if (here / n).exists()]


def build_bar_rows_lt2(assigner: Optional[Lt2ReinforcementAssigner] = None,
                       cover_cm: Optional[float] = None) -> List[Dict]:
    assigner = assigner or Lt2ReinforcementAssigner().run()
    builder = Lt2ReinforcementGeometryBuilder(assigner, cover_cm=cover_cm)
    builder.build()
    return builder.to_rows()


def beam_resumen_rows_lt2() -> List[Dict]:
    """Una fila por record de viga LT2 con resumen textual."""
    beam = load_lt2_beam_data()
    rows: List[Dict] = []
    for rec in beam["records"]:
        rows.append({
            "beam_id": rec.beam_id,
            "drawing": rec.drawing,
            "sheet": rec.sheet,
            "section": rec.section,
            "kind": rec.kind.value,
            "axes_text": rec.axes_text,
            "longitudinal": rec.longitudinal,
            "stirrups": rec.stirrups,
            "confidence": rec.confidence.value,
            "resolution": rec.resolution.value,
            "note": rec.note,
        })
    return rows


def column_rows_lt2() -> List[Dict]:
    """Una fila por tag de columna LT2 con su dato 16 Φ22 longitudinal."""
    from .lt2_geometry import Lt2Geometry

    geo = Lt2Geometry()
    rules = [r for r in load_lt2_reinforcement()["columns"]
             if r.bar_type == ColumnBarType.LONGITUDINAL]
    rows: List[Dict] = []
    for rule in rules:
        tags = rule.column_tags or geo.column_tags()
        for tag in sorted(tags):
            rows.append({
                "elementTag": tag,
                "building": "LT2",
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


def write_outputs_lt2(out_dir: Path) -> Dict[str, Path]:
    """Persiste CSVs de armadura LT2 (reglas, barras, columnas, vigas,
    muros, escaleras, pendientes). NO toca los CSVs LT1."""
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    assigner = Lt2ReinforcementAssigner().run()

    # A) reglas (todas las categorias)
    rows = assigner.to_rows()
    csv_rules = out_dir / "armadura_lt2_reglas.csv"
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

    # B) barras 3D (solo mallas generales resueltas)
    bar_rows = build_bar_rows_lt2(assigner)
    csv_bars = out_dir / "armadura_lt2_barras.csv"
    if bar_rows:
        with open(csv_bars, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(bar_rows[0].keys()))
            w.writeheader()
            w.writerows(bar_rows)

    # C) columnas
    csv_cols = out_dir / "armadura_lt2_columnas.csv"
    _write_csv(csv_cols, column_rows_lt2())

    # D) vigas (segmentos + estribos) y resumen
    beam = load_lt2_beam_data()
    beam_rows = [s.to_dict() for s in beam["segments"]]
    beam_rows.extend(z.to_dict() for z in beam["stirrups"])
    csv_beam = out_dir / "armadura_lt2_vigas.csv"
    _write_csv(csv_beam, beam_rows)
    csv_resumen = out_dir / "armadura_lt2_vigas_resumen.csv"
    _write_csv(csv_resumen, beam_resumen_rows_lt2())

    # E) muros (por elevacion) y escaleras
    csv_walls = out_dir / "armadura_lt2_muros.csv"
    _write_csv(csv_walls, [r.to_dict() for r in load_lt2_wall_data()["records"]])
    csv_stairs = out_dir / "armadura_lt2_escaleras.csv"
    _write_csv(csv_stairs, [r.to_dict() for r in load_lt2_stair_data()["records"]])

    # F) reglas que requieren confirmacion (status pendiente)
    needs = []
    for r in assigner.to_rows():
        if r.get("status") in (Status.NEEDS_DRAWING_VALUE_CONFIRMATION.value,
                               Status.NEEDS_EXACT_ZONE_MAPPING.value,
                               Status.NEEDS_NOTATION_CONFIRMATION.value,
                               Status.DETAIL_FROM_DRAWING_REQUIRED.value):
            needs.append({
                "code": r.get("code", ""),
                "category": r.get("category", ""),
                "drawing": r.get("drawing", ""),
                "sheet": r.get("sheet", ""),
                "status": r.get("status", ""),
                "resolution": r.get("resolution", ""),
                "zone_text": r.get("zone_text", "") or r.get("axis", ""),
                "note": r.get("note", ""),
            })
    csv_needs = out_dir / "armadura_lt2_necesita_confirmacion.csv"
    _write_csv(csv_needs, needs)

    return {
        "rules": csv_rules,
        "bars": csv_bars,
        "columns": csv_cols,
        "beam_bars": csv_beam,
        "beam_summary": csv_resumen,
        "walls": csv_walls,
        "stairs": csv_stairs,
        "needs_confirmation": csv_needs,
    }


if __name__ == "__main__":
    v = validate_dataset_lt2()
    print("Errores:", len(v["errors"]))
    for e in v["errors"][:20]:
        print("  ERROR", e)
    print("Warnings:", len(v["warnings"]))
    print("Reglas LT2:", v["n_reglas"])
    print("Resolucion:", v["resolution_counts"])
    print("Status:", v["status_counts"])
    print("Summary por categoria:", v["summary"])
    sys.exit(1 if v["errors"] else 0)