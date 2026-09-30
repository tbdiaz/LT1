import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNITY = ROOT / "unity" / "LT1Viewer"
JSON_PATH = UNITY / "Assets" / "StreamingAssets" / "modelo_combinado.json"


def test_ar_demo_uses_existing_combined_element_and_result():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    element = next(e for e in data["elements"] if e["elementTag"] == 800205)
    node_tags = {n["nodeTag"] for n in data["nodes"]}

    assert element["origen"] == "LT1"
    assert element["tipo"] == "segmento_fachada"
    assert element["nodeI"] in node_tags
    assert element["nodeJ"] in node_tags
    assert "800205" in data["results"]["forces"]["COMBO_R"]
    assert isinstance(data["results"]["forces"]["COMBO_R"]["800205"]["My1"], (int, float))


def test_ar_coordinate_chain_and_traceability_are_explicit():
    source = (UNITY / "Assets" / "Scripts" / "ARStructuralDemo.cs").read_text(encoding="utf-8")

    assert "return new Vector3(x, z, -y);" in source
    assert "contentRoot.transform.SetParent(imageAnchor, false);" in source
    assert "contentRoot.transform.localPosition = arTranslationMetres;" in source
    assert "Quaternion.Euler(arEulerDegrees)" in source
    assert "Vector3.one * arScale" in source
    assert "elementTag" in source and "loadCase" in source and "resultUnits" in source
    assert "TrackingState.Tracking" in source
    assert "public int elementTag = 800205;" in source
    assert 'public string resultComponent = "My1";' in source


def test_ar_packages_and_ios_builder_are_present():
    manifest = json.loads((UNITY / "Packages" / "manifest.json").read_text(encoding="utf-8"))
    deps = manifest["dependencies"]

    # Versiones bundled/minimas declaradas por Unity 6000.5.0f1. Mantenerlas
    # alineadas evita que XR Management antiguo solicite el modulo VR retirado.
    assert deps["com.unity.xr.arfoundation"] == "6.5.0"
    assert deps["com.unity.xr.arkit"] == "6.5.0"
    assert deps["com.unity.xr.core-utils"] == "2.6.0"
    assert deps["com.unity.xr.management"] == "4.5.4"
    assert deps["com.unity.inputsystem"] == "1.19.0"
    assert "com.unity.modules.vr" not in deps
    assert (UNITY / "Assets" / "Editor" / "ARStructuralDemoBuilder.cs").is_file()
    assert (UNITY / "Assets" / "Editor" / "IOSARBuild.cs").is_file()
    assert (UNITY / "SEMANA06_AR.md").is_file()
