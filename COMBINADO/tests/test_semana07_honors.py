import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNITY = ROOT / "unity" / "LT1Viewer"
LIGHT_JSON = (UNITY / "Assets" / "StreamingAssets"
              / "semana06_element_800205.json")
SOURCE = UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs"


def test_h3_my_diagram_closes_with_real_end_forces_and_real_loads():
    data = json.loads(LIGHT_JSON.read_text(encoding="utf-8"))
    combo = next(row for row in data["forceCases"]
                 if row["caseName"] == "COMBO_R")
    q = sum(row["w_kN_m"] for row in data["loads"]
            if row["caseName"] in ("G", "Q"))
    length = data["element"]["length_m"]

    # Misma convencion del visor: seccion i=-F_i, seccion j=+F_j.
    my_i = -combo["My1"]
    vz_i = -combo["Vz1"]
    reconstructed_j = my_i + vz_i * length + 0.5 * q * length**2
    assert abs(reconstructed_j - combo["My2"]) < 1e-9


def test_h3_tributary_strip_preserves_the_exported_area():
    data = json.loads(LIGHT_JSON.read_text(encoding="utf-8"))
    live = next(row for row in data["loads"] if row["caseName"] == "Q")
    width = live["tributaryArea_m2"] / data["element"]["length_m"]
    assert abs(width - 2.3109375) < 1e-9
    assert abs(width * data["element"]["length_m"]
               - live["tributaryArea_m2"]) < 1e-12


def test_h3_ar_layers_are_interactive_and_keep_missing_pm_explicit():
    source = SOURCE.read_text(encoding="utf-8")
    assert "CreateMomentDiagram(combo);" in source
    assert "sectionMomentI = -combo.My1" in source
    assert "sectionShearI = -combo.Vz1" in source
    assert "momentDiagramClosureError" in source
    assert 'new GameObject("H3_DeformadaNodal_COMBO_R_x100")' in source
    assert 'new GameObject("H3_AreaTributariaEquivalente_" + elementTag)' in source
    assert "tributaryArea_m2 / length" in source
    assert 'DrawOverlayToggle("DIAGRAMA My"' in source
    assert 'DrawOverlayToggle("DEFORMADA ×100"' in source
    assert 'DrawOverlayToggle("ÁREA TRIBUTARIA"' in source
    assert '"P-M: PENDIENTE"' in source

