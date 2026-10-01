"""Extrae el paquete liviano y trazable de Semana 6 para elementTag 800205."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "unity" / "LT1Viewer" / "Assets" / "StreamingAssets" / "modelo_combinado.json"
OUTPUT = ROOT / "unity" / "LT1Viewer" / "Assets" / "StreamingAssets" / "semana06_element_800205.json"
TAG = 800205


def main() -> None:
    model = json.loads(SOURCE.read_text(encoding="utf-8"))
    element = next(item for item in model["elements"] if item["elementTag"] == TAG)
    node_tags = (element["nodeI"], element["nodeJ"])
    nodes_by_tag = {item["nodeTag"]: item for item in model["nodes"]}

    loads = []
    for case_name, case_loads in model["loads"].items():
        if not isinstance(case_loads, list):
            continue
        for item in case_loads:
            if isinstance(item, dict) and item.get("element_tag") == TAG:
                loads.append(
                    {
                        "caseName": case_name,
                        "type": item.get("tipo", ""),
                        "w_kN_m": item.get("w_kN_m", 0.0),
                        "total_kN": item.get("q_kN", 0.0),
                        "tributaryArea_m2": item.get("area_m2", 0.0),
                        "hasTributaryArea": "area_m2" in item,
                    }
                )

    force_cases = []
    displacement_cases = []
    for case_name in model["results"]["cases"]:
        forces = model["results"]["forces"][case_name][str(TAG)]
        force_cases.append({"caseName": case_name, **forces})

        displacements = model["results"]["displacements"][case_name]
        u_i = displacements[str(node_tags[0])]
        u_j = displacements[str(node_tags[1])]
        displacement_cases.append(
            {
                "caseName": case_name,
                "nodeI": u_i,
                "nodeJ": u_j,
                "translationMagnitudeI_m": math.sqrt(sum(value * value for value in u_i[:3])),
                "translationMagnitudeJ_m": math.sqrt(sum(value * value for value in u_j[:3])),
            }
        )

    section = element["seccion"]
    compact_element = {
        "elementTag": element["elementTag"],
        "type": element["tipo"],
        "origin": element["origen"],
        "nodeI": element["nodeI"],
        "nodeJ": element["nodeJ"],
        "length_m": element["longitud_m"],
        "level": element["nivel"],
        "lt1Level": element["nivel_lt1"],
        "originalTag": element["tag_original"],
        "section": {
            "label": section["label"],
            "area_m2": section["A_m2"],
            "Iy_m4": section["Iy_m4"],
            "Iz_m4": section["Iz_m4"],
            "J_m4": section["J_m4"],
            "E_kPa": section["E_kPa"],
            "G_kPa": section["G_kPa"],
        },
    }
    compact_nodes = [
        {
            "nodeTag": nodes_by_tag[tag]["nodeTag"],
            "x": nodes_by_tag[tag]["x"],
            "y": nodes_by_tag[tag]["y"],
            "z": nodes_by_tag[tag]["z"],
            "origin": nodes_by_tag[tag]["origen"],
            "level": nodes_by_tag[tag]["nivel"],
        }
        for tag in node_tags
    ]

    payload = {
        "schemaVersion": 1,
        "sourceFile": "modelo_combinado.json",
        "elementTag": TAG,
        "element": compact_element,
        "nodes": compact_nodes,
        "loads": loads,
        "forceCases": force_cases,
        "displacementCases": displacement_cases,
        "diagramAvailability": {
            "endForcesAvailable": True,
            "internalStationResultsAvailable": False,
            "note": (
                "Solo existen fuerzas OpenSees en los extremos I/J; no se exportaron "
                "ordenadas internas para diagramas continuos."
            ),
        },
        "demandCapacity": {
            "available": False,
            "note": (
                "No existe verificacion demanda-capacidad asociada a elementTag 800205. "
                "results.pm contiene solamente muro_M001 y columna_113022."
            ),
        },
        "units": {
            "coordinates": "m",
            "force": "kN",
            "moment": "kN.m",
            "distributedLoad": "kN/m",
            "displacement": "m",
            "rotation": "rad",
        },
    }

    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{OUTPUT}: {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
