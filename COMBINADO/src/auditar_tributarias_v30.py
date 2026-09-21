"""Audita, sin modificar cargas, los nuevos tramos V30 contra el reparto LT2.

Repite el muestreo de 0.05 m de LT2/src/tributary_areas.py para los paños
adyacentes, primero con la geometría original y luego con los 10 tramos
incorporados a COMBINADO. Los resultados son una comparación, no un nuevo
caso de carga aprobado para OpenSees.
"""

from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LT2 = ROOT / "LT2"
CONNECTIONS = ROOT / "COMBINADO" / "data" / "conexiones_v30_lt2.csv"
STEP = 0.05


def load_tributary_module():
    spec = importlib.util.spec_from_file_location(
        "lt2_tributary_areas", LT2 / "src" / "tributary_areas.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def panel_areas(module, panel, beams):
    bounds = module.parse_poly(panel.polygon)
    holes = module.parse_holes(panel.holes)
    segments = module.collect_supporting_segments({"b": bounds}, beams)
    x0, y0, x1, y1 = bounds
    xs = np.arange(x0 + STEP / 2, x1, STEP)
    ys = np.arange(y0 + STEP / 2, y1, STEP)
    xgrid, ygrid = np.meshgrid(xs, ys)
    px, py = xgrid.ravel(), ygrid.ravel()
    keep = np.ones(len(px), dtype=bool)
    for hx0, hy0, hx1, hy1 in holes:
        keep &= ~((px >= hx0 - 1e-9) & (px <= hx1 + 1e-9)
                  & (py >= hy0 - 1e-9) & (py <= hy1 + 1e-9))
    indices = module.assign_panel_points(px[keep], py[keep], segments, holes)
    counts = np.bincount(indices, minlength=len(segments))
    result = defaultdict(float)
    for segment, count in zip(segments, counts):
        receiver = (segment["beam_id"] if segment["tipo"] == "beam"
                    else "WALL:" + segment["wall_id"])
        result[receiver] += count / counts.sum() * float(panel.area_m2)
    return result


def audit():
    module = load_tributary_module()
    beams = pd.read_csv(LT2 / "data" / "geometry" / "beams_LT2.csv")
    beams["tag"] = module.TAG_BEAM_BASE + beams.index
    panels = pd.read_csv(LT2 / "data" / "loads" / "slab_panels_LT2.csv")
    recorded = pd.read_csv(LT2 / "data" / "loads" / "tributary_areas_LT2.csv")
    connections = pd.read_csv(CONNECTIONS)
    added = pd.DataFrame({
        "beam_id": connections.beam_id,
        "x1_m": connections.x_i_m,
        "y1_m": connections.y_i_m,
        "x2_m": connections.x_j_m,
        "y2_m": connections.y_j_m,
        "level": connections.nivel,
        "tag": connections.element_tag,
    })
    extended = pd.concat([beams, added], ignore_index=True)
    rows = []
    for level in module.LEVELS:
        original_level = beams[beams.level == level]
        extended_level = extended[extended.level == level]
        for panel in panels[panels.level == level].itertuples(index=False):
            bounds = module.parse_poly(panel.polygon)
            x0, y0, x1, y1 = bounds
            affected = added[(added.level == level)
                             & (added.y1_m.isin((y0, y1)))
                             & (added.x1_m < x1) & (added.x2_m > x0)]
            if affected.empty:
                continue
            before = panel_areas(module, panel, original_level)
            after = panel_areas(module, panel, extended_level)
            source = defaultdict(float)
            for rec in recorded[recorded.panel_id == panel.panel_id].itertuples():
                receiver = (str(rec.beam_id) if rec.receiver_type == "BEAM"
                            else "WALL:" + str(rec.receiver_id))
                source[receiver] += float(rec.area_m2)
            for receiver in before.keys() | source.keys():
                # Los CSV publicados pueden diferir en unas celdas de 0.05 m
                # por desempates numericos en los bordes del muestreo.
                if abs(before.get(receiver, 0.0) - source.get(receiver, 0.0)) > 0.02:
                    raise AssertionError(
                        f"Reparto base no coincide con LT2: {panel.panel_id} "
                        f"{receiver}"
                    )
            if abs(sum(before.values()) - float(panel.area_m2)) > 1e-8:
                raise AssertionError(f"Área original no conservada: {panel.panel_id}")
            if abs(sum(after.values()) - float(panel.area_m2)) > 1e-8:
                raise AssertionError(f"Área nueva no conservada: {panel.panel_id}")
            for receiver in before.keys() | after.keys():
                delta = after.get(receiver, 0.0) - before.get(receiver, 0.0)
                if abs(delta) > 1e-8:
                    rows.append({
                        "nivel": level,
                        "panel_id": panel.panel_id,
                        "estado_panel": panel.status,
                        "receptor": receiver,
                        "area_antes_m2": before.get(receiver, 0.0),
                        "area_despues_m2": after.get(receiver, 0.0),
                        "delta_area_m2": delta,
                        "delta_G_kN": delta * float(panel.qG_kN_m2),
                    })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    result = audit()
    summary = result.groupby(["nivel", "receptor"], as_index=False)[
        ["delta_area_m2", "delta_G_kN"]].sum()
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.5f}"))
    print("Conservación por nivel (delta G kN):")
    print(result.groupby("nivel").delta_G_kN.sum().to_string(
        float_format=lambda x: f"{x:.9f}"))
    print("Paneles afectados:", result.panel_id.nunique())
