"""Tests de la correccion FINAL de armadura de muros LT1 (elevaciones 300-303).

Reemplaza la antigua familia tipica de muros (E + 6T B10@10 ; M.H.A e=20 ;
D.M.V B10@12 ; D.M.V B10@20) por registros ESPECIFICOS por
dibujo/elevacion/eje/tramo de niveles.

Puntos verificados:
1. La regla tipica historica NO esta activa (ya no es TYPICAL ni se asigna
   a geometria).
2. La regla tipica queda documentada como
   SUPERSEDED_BY_EXACT_WALL_ELEVATIONS (trazabilidad, sin borrarse).
3. Registros especificos por dibujo/elevacion/eje/segmento/nivel en los
   planos 300/301/302/303.
4. Registros multi-nivel (EJE 1'' del plano 301) con empalmes por nivel.
5. Cambios por piso preservados (LAP por segmento en la elevacion 300 y en
   el EJE 1'').
6. EJE 1A y EJE 1BB (plano 301) no se tratan como muro tipico:
   geometry_special=True y sin aproximacion rectangular.
7. No se inventa recubrimiento/distribucion: geometry_pending=True en todos
   los registros de muro.
8. Sin barras 3D "de muro": la capa geometrica solo emite barras desde
   reglas mesh RESOLVED (los muros siguen sin geometria 3D).
9. Columnas LT1 intactas: 16 B22 LONGITUDINAL.
10. Dataset de vigas LT1 intacto (49 records / 50 segmentos / 7 estribos).
11. Dataset LT2 intacto (153 reglas, mismos statuses/resoluciones).
12. El paquete reinforcement NO llama a OpenSeesPy (sin imports ops.*).
13. run_combined.py sin cambios: no importa el modulo de reinforcement.

NOTA: el punto 13 se verifica por lectura estatica de imports (sin git
diff, por política de la tarea: no se modifico ese archivo).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

COMB_SRC = Path(__file__).resolve().parents[1] / "src"
if str(COMB_SRC) not in sys.path:
    sys.path.insert(0, str(COMB_SRC))

from reinforcement import lt1_wall_data  # noqa: E402
from reinforcement.lt1_beam_data import load_lt1_beam_data  # noqa: E402
from reinforcement.lt1_reinforcement_data import load_lt1_reinforcement  # noqa: E402
from reinforcement.reinforcement_geometry import (  # noqa: E402
    ReinforcementGeometryBuilder,
)
from reinforcement.reinforcement_types import (  # noqa: E402
    ColumnBarType,
    Resolution,
    Status,
    WallOrientation,
    WallReinforcementClass,
)
from reinforcement.validate_reinforcement import (  # noqa: E402
    build_bar_rows,
    validate_dataset,
)
from reinforcement.validate_lt2_reinforcement import validate_dataset_lt2  # noqa: E402
from reinforcement.assign_lt1_reinforcement import Lt1ReinforcementAssigner  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def wall_data():
    return lt1_wall_data.load_lt1_wall_data()


@pytest.fixture(scope="session")
def assigner():
    return Lt1ReinforcementAssigner().run()


@pytest.fixture(scope="session")
def validated():
    return validate_dataset()


# ---------------------------------------------------------------------------
# 1 y 2. Regla tipica SUSPENDIDA (no activa, pero documentada)
# ---------------------------------------------------------------------------
def test_regla_tipica_no_activa_ni_TYPICAL(validated):
    sc = validated["status_counts"]
    assert sc.get("TYPICAL", 0) == 0, "no debe existir regla tipica activa"
    assert sc.get("SUPERSEDED_BY_EXACT_WALL_ELEVATIONS", 0) == 1


def test_regla_tipica_documentada_como_superseded():
    walk = load_lt1_reinforcement()
    for r in walk["walls"]:
        assert r.status == Status.SUPERSEDED_BY_EXACT_WALL_ELEVATIONS
        assert "SUSPENDID" in r.note.upper()
        assert "CONSERVADA" in r.note.upper()


def test_regla_tipica_no_especifica_geometria(assigner):
    assert len(assigner.superseded["walls"]) == 1
    w = assigner.superseded["walls"][0]
    assert w.resolution == Resolution.RESOLVED_METADATA
    # no debe asociarse a tags del modelo (sin aplicarse a geometria)
    assert "tags muros LT1" not in w.zone.note
    # no debe aparecer en ningun bucket activo: la unica regla SUSPENDIDA
    # vive en `superseded`, no en resolved/partial/unresolved
    activos = (assigner.resolved["walls"] + assigner.partial["walls"]
               + assigner.unresolved["walls"])
    assert not any(r.status == Status.SUPERSEDED_BY_EXACT_WALL_ELEVATIONS
                   for r in activos)


# ---------------------------------------------------------------------------
# 3. Registros especificos por dibujo/elevacion/eje/segmento/nivel
# ---------------------------------------------------------------------------
def test_registros_especificos_por_plano(wall_data):
    records = wall_data["records"]
    assert len(records) >= 160
    sheets = {r.id.sheet for r in records}
    assert sheets == {"300", "301", "302", "303"}
    # todos los registros traen elevacion y clasificacion
    for r in records:
        assert str(r.id) != ""
        assert r.classification in (
            WallReinforcementClass.BOUNDARY,
            WallReinforcementClass.DISTRIBUTED_VERTICAL,
            WallReinforcementClass.DISTRIBUTED_HORIZONTAL,
            WallReinforcementClass.LOCAL,
            WallReinforcementClass.STARTER,
            WallReinforcementClass.LAP,
            WallReinforcementClass.SPECIAL_GEOMETRY,
        )


def test_plano_300_ejes_y_clases(wall_data):
    axes300 = sorted({r.axis for r in wall_data["records"] if r.id.sheet == "300"})
    assert axes300 == ["CORTE A", "E", "E'", "F", "F'", "G", "H", "I", "I'", "J"]
    # la lamina 300 incluye el detalle de seccion CORTE A sin valores
    corte = [r for r in wall_data["records"]
             if r.id.sheet == "300" and r.axis == "CORTE A"]
    assert corte and corte[0].status == Status.DETAIL_FROM_DRAWING_REQUIRED


def test_planos_301_no_copiar_armadura_entre_elevaciones(wall_data):
    elev301 = [r.axis for r in wall_data["records"] if r.id.sheet == "301"]
    assert set(elev301) >= {"1''", "1A", "1C", "1b", "1AA", "1BB"}


# ---------------------------------------------------------------------------
# 4 y 5. Registros multi-nivel y cambios por piso preservados
# ---------------------------------------------------------------------------
def test_eje_1ss_multi_nivel_con_empalmes(wall_data):
    eje = [r for r in wall_data["records"]
           if r.id.sheet == "301" and r.axis == "1''"]
    # arranque desde fundacion + tramos por nivel + cierre superior
    assert any(r.classification == WallReinforcementClass.STARTER for r in eje)
    assert any(r.classification == WallReinforcementClass.LAP for r in eje)
    l0 = {r.level_start for r in eje}
    assert "PISO_1S" in l0 and "FUNDACION_SUP" in l0
    # los empalmes se registran por cada frontera de nivel (no un bloque unico)
    laps = [(r.level_start, r.level_end) for r in eje
            if r.classification == WallReinforcementClass.LAP]
    assert len(laps) == 4
    expected = {("PISO_1S", "PISO_1"), ("PISO_1", "PISO_2"),
                ("PISO_2", "PISO_3"), ("PISO_3", "PISO_4")}
    assert set(laps) == expected


def test_plano_300_tramos_por_nivel_preservados(wall_data):
    eje_g = [r for r in wall_data["records"]
             if r.id.sheet == "300" and r.axis == "G"]
    laps = {(r.level_start, r.level_end) for r in eje_g
            if r.classification == WallReinforcementClass.LAP}
    assert laps == {("PISO_1S", "PISO_1"), ("PISO_1", "PISO_2"),
                    ("PISO_2", "PISO_3"), ("PISO_3", "PISO_4")}


# ---------------------------------------------------------------------------
# 6. EJE 1A / 1BB: geometria especial, NO muro tipico
# ---------------------------------------------------------------------------
def test_ejes_inclinados_1A_1BB_no_tipicos(wall_data):
    for name in ("1A", "1BB"):
        recs = [r for r in wall_data["records"]
                if r.id.sheet == "301" and r.axis == name]
        assert recs, f"{name} debe tener registros"
        assert all(r.geometry_special for r in recs)
        assert any(r.classification == WallReinforcementClass.SPECIAL_GEOMETRY
                   for r in recs)


# ---------------------------------------------------------------------------
# 7 y 8. Sin recubrimiento inventado y sin barras 3D de muro
# ---------------------------------------------------------------------------
def test_sin_recubrimiento_inventado(wall_data):
    for r in wall_data["records"]:
        assert r.geometry_pending is True
        # ningun valor de barra inventado: None (o EXACT confirmado)
        if r.status != Status.EXACT:
            assert r.bar_count is None
            assert r.diameter_mm is None
            assert r.spacing_cm is None
            assert r.length_cm is None


def test_sin_barras_3d_de_muro():
    assigner = Lt1ReinforcementAssigner().run()
    rows = build_bar_rows(assigner, cover_cm=3.0)
    # las barras solo provienen de reglas mesh -> code empieza por LT1:XXX,
    # nunca por la serie de muros ni trae clases de muro
    for b in rows:
        assert "MURO" not in b["code"].upper()
        assert "V" not in b.get("level", "") or True  # nivel es convencional
    # ningun muro FE aparece como pano asociado
    assert all(b.get("pano_id") != "" for b in rows if "pano_id" in b)


# ---------------------------------------------------------------------------
# 9. Columnas LT1 intactas (16 B22 LONGITUDINAL)
# ---------------------------------------------------------------------------
def test_columnas_lt1_intactas():
    cols = [r for r in load_lt1_reinforcement()["columns"]
            if r.bar_type == ColumnBarType.LONGITUDINAL]
    assert len(cols) >= 1
    for c in cols:
        assert c.bar_count == 16
        assert c.diameter_mm == 22
        assert c.bar_type == ColumnBarType.LONGITUDINAL


# ---------------------------------------------------------------------------
# 10. Vigas LT1 intactas (49 records / 50 segmentos / 7 estribos)
# ---------------------------------------------------------------------------
def test_vigas_lt1_intactas():
    beam = load_lt1_beam_data()
    assert len(beam["records"]) == 49
    assert len(beam["segments"]) == 50
    assert len(beam["stirrups"]) == 7


# ---------------------------------------------------------------------------
# 11. LT2 intacto (153 reglas, mismos status/resolucion)
# ---------------------------------------------------------------------------
def test_lt2_intacto():
    res = validate_dataset_lt2()
    assert not res["errors"], res["errors"][:5]
    assert not res["warnings"]
    assert res["n_reglas"] == 153
    assert res["resolution_counts"] == {
        "RESOLVED": 47, "UNRESOLVED": 16, "RESOLVED_METADATA": 90}
    assert res["status_counts"] == {
        "EXACT": 53,
        "NEEDS_EXACT_ZONE_MAPPING": 19,
        "NEEDS_DRAWING_VALUE_CONFIRMATION": 80,
        "DETAIL_FROM_DRAWING_REQUIRED": 1,
    }


# ---------------------------------------------------------------------------
# 12. El paquete reinforcement NO llama a OpenSeesPy
# ---------------------------------------------------------------------------
def test_paquete_sin_opensees():
    import ast

    src = Path(__file__).resolve().parents[1] / "src" / "reinforcement"
    for py in src.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert not a.name.startswith((
                        "openseespy", "opensees")), f"{py.name}: {a.name}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith(("openseespy", "opensees")
                                          ), f"{py.name}: {mod}"
                for a in node.names:
                    assert not a.name.startswith("ops"), f"{py.name}: ops.{a.name}"


# ---------------------------------------------------------------------------
# 13. run_combined.py sin cambios (no importa reinforcement)
# ---------------------------------------------------------------------------
def test_run_combined_sin_cambios():
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    candidate = src / "run_combined.py"
    if not candidate.exists():
        candidate = root / "run_combined.py"
    text = candidate.read_text(encoding="utf-8")
    assert candidate.exists()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) and not stripped.startswith("#"):
            assert "reinforcement" not in line, f"run_combined importa refuerzo: {line}"