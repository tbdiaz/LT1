"""Validacion ESTATICA del visor COMBINADO (ETAPA P1L4).

Sin abrir Unity ni OpenSees: comprueba que los scripts C# del visor estan
preparados para `modelo_combinado.json` sin errores de compilacion obvios y
con coherencia entre el esquema C# y el JSON exportado. Verifica:
- Inventario del JSON combinado (nodos, elementos por tipo, categorias Beam/
  Column/Wall, apoyos, masters, diafragmas, cargas y tributarias LT1+LT2).
- Consistencia de esquema: cada clave del JSON existe como campo de la clase
  [Serializable] en CombinedModelData.cs, y los tipos basicos coinciden.
- Independencia del visor: ModelLoader apunta a modelo_combinado.json, no se
  lee modelo_lt1.json/pending_geometry como fuente, no hay clases C#
  duplicadas, balance de llaves por archivo y sin escenas .unity (la escena
  se genera por editor).
"""  # noqa: D205

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

COMB_SRC = Path(__file__).resolve().parents[1] / "src"
if str(COMB_SRC) not in sys.path:
    sys.path.insert(0, str(COMB_SRC))

from validar_unity_viewer_estatico import StaticValidator  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "COMBINADO" / "outputs" / "unity" / "modelo_combinado.json"


def test_visor_estatico_correcto():
    v = StaticValidator(OUT)
    v.run()
    assert not v.fail, f"FALLOS visor: {sorted(set(v.fail))[:20]}"
    assert len(v.ok) >= 10, "demasiado pocas comprobaciones"


def test_columnas_verdes_en_visor():
    """La paleta de las columnas no debe volver al naranja anterior."""
    loader = (ROOT / "unity" / "LT1Viewer" / "Assets" / "Scripts"
              / "ModelLoader.cs").read_text(encoding="utf-8")
    match = re.search(
        r"columnMaterial\s*=\s*CreateMaterial\(new Color\("
        r"([0-9.]+)f,\s*([0-9.]+)f,\s*([0-9.]+)f\)\)", loader)
    assert match, "No se encontró el material visual de columnas"
    red, green, blue = map(float, match.groups())
    assert green > red and green > blue, "Las columnas no están en verde"


def test_vigas_v30_del_extremo_conectadas_en_cinco_niveles():
    """Cada tag indicado por el usuario comparte nodo con el nuevo tramo."""
    model = json.loads(OUT.read_text(encoding="utf-8"))
    nodes = {n["nodeTag"]: n for n in model["nodes"]}
    elems = {e["elementTag"]: e for e in model["elements"]}
    parents = (2081, 2083, 2085, 2087, 2089,
               2091, 2093, 2095, 2205, 2207)
    assert len(model["elements"]) == 694
    for offset, parent_tag in enumerate(parents):
        parent = elems[parent_tag]
        connector = elems[9011 + offset]
        assert connector["tag_original"] == parent_tag
        assert connector["nodeJ"] == parent["nodeI"]
        assert connector["nivel"] == parent["nivel"]
        assert connector["seccion_id"] == "V30x80"
        assert abs(connector["longitud_m"] - 1.5) < 1e-9
        origin = nodes[connector["nodeI"]]
        assert origin["x"] == 0.4
        assert origin["y"] == nodes[parent["nodeI"]]["y"]
        assert any(
            e["origen"] == "LT2" and e["tipo"] == "viga"
            and connector["nodeI"] in (e["nodeI"], e["nodeJ"])
            for e in model["elements"]
        )
        for case in model["results"]["cases"]:
            assert str(connector["elementTag"]) in model["results"]["forces"][case]


def test_redistribucion_v30_conserva_area_y_carga_por_nivel():
    """V30 recibe la carga retirada de V40 sin cambiar el peso del piso."""
    model = json.loads(OUT.read_text(encoding="utf-8"))
    rows = [r for r in model["tributary_areas"]["LT2"]["filas"]
            if r.get("status") == "REDISTRIBUIDO_COMBINADO"]
    assert len(rows) == 24
    for level in ("L1", "L2", "L3", "L4"):
        floor = [r for r in rows if r["level"] == level]
        assert len(floor) == 6
        assert abs(sum(r["area_m2"] for r in floor)) < 1e-9
        assert abs(sum(r["load_kN"] for r in floor)) < 1e-8
        assert len([r for r in floor if r["element_tag"] >= 9011]) == 2

    for case in ("G", "Q"):
        loads = [r for r in model["loads"][case]
                 if r.get("tipo") == "beamUniform_redist_V30"]
        assert len(loads) == 24
        assert abs(sum(r["q_kN"] for r in loads)) < 1e-8
        assert all(abs(r["w_kN_m"]) > 0 for r in loads)


def test_carga_movil_tactil_y_build_android_declarados():
    scripts = ROOT / "unity" / "LT1Viewer" / "Assets" / "Scripts"
    editor = ROOT / "unity" / "LT1Viewer" / "Assets" / "Editor"
    moving = (scripts / "MovingLoadController.cs").read_text(encoding="utf-8")
    orbit = (scripts / "OrbitCamera.cs").read_text(encoding="utf-8")
    selection = (scripts / "SelectionController.cs").read_text(encoding="utf-8")
    android = (editor / "AndroidBuild.cs").read_text(encoding="utf-8")
    assert "magnitudeKn * (1f - xi)" in moving
    assert "magnitudeKn * xi" in moving
    assert "forceError" in moving and "momentError" in moving
    assert "Input.touchCount" in orbit and "pinch" in orbit
    assert "TouchPhase.Ended" in selection and "movement <= 22f" in selection
    assert "AndroidApiLevel26" in android
    assert "AndroidArchitecture.ARM64" in android
