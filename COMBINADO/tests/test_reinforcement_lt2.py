"""Tests del modulo de armadura LT2.

Cobertura:
- LT1 sigue consistente (regresion del paquete compartido).
- LT2 carga de forma independiente (geometria + dataset).
- Columnas LT2: 16 Φ22 LONGITUDINAL, 50 tags, geometry_pending=True
  (sin estribos/recubrimiento inventados).
- Planos 200/201/202: reglas presentes con diametro/espaciado correctos.
- Prioridades de resolucion: zonas con ejes modelados resueltas, reglas
  de eje/excepcion que nombran ejes fuera de la grilla (1', 8A/8B,
  losas 01xx) NO asignadas a geometria.
- Vigas 400: familias especiales (V.F./V.I.) sin armadura V.60/80;
  segmentos EXACT solo con dato legible; estribos sin zona inventada.
- Muros 300-305 por ELEVACION (70 registros); sin regla universal;
  wall_parents solo para ejes inequivocos (A', 1, 3).
- Escaleras 500: registros por parte/corte; longitudes del corte C no
  extrapoladas.
- Geometria de barras LT2 en coordenadas nativas (= combinadas), solo
  mallas generales resueltas.
- Invarianza del modelo estructural combinado (test lento, unico que
  abre OpenSeesPy).

El test `test_combined_model_invariante_lt2` re-ejecuta el analisis
completo (igual que en test_reinforcement.py: puede tardar unos minutos).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

COMB_SRC = Path(__file__).resolve().parents[1] / "src"
if str(COMB_SRC) not in sys.path:
    sys.path.insert(0, str(COMB_SRC))

from reinforcement import (  # noqa: E402
    assign_lt2_reinforcement as assign_mod,
)
from reinforcement.lt2_beam_data import load_lt2_beam_data  # noqa: E402
from reinforcement.lt2_geometry import Lt2Geometry  # noqa: E402
from reinforcement.lt2_reinforcement_data import (  # noqa: E402
    load_lt2_reinforcement,
)
from reinforcement.lt2_reinforcement_geometry import (  # noqa: E402
    Lt2ReinforcementGeometryBuilder,
)
from reinforcement.lt2_stair_data import load_lt2_stair_data  # noqa: E402
from reinforcement.lt2_wall_data import (  # noqa: E402
    WALL_AXIS_TO_PARENT,
    load_lt2_wall_data,
)
from reinforcement.reinforcement_types import (  # noqa: E402
    BeamKind,
    ColumnBarType,
    Resolution,
    StairPart,
    Status,
    ZoneKind,
)
from reinforcement.validate_lt2_reinforcement import (  # noqa: E402
    build_bar_rows_lt2,
    validate_dataset_lt2,
)
from reinforcement.validate_reinforcement import check_model_rc  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def data2() -> dict:
    return load_lt2_reinforcement()


@pytest.fixture(scope="session")
def assigner2():
    return assign_mod.Lt2ReinforcementAssigner().run()


@pytest.fixture(scope="session")
def geo2() -> Lt2Geometry:
    return Lt2Geometry()


# ---------------------------------------------------------------------------
# LT1 no cambia (regresion del paquete compartido)
# ---------------------------------------------------------------------------
def test_lt1_dataset_intacto():
    from reinforcement.lt1_reinforcement_data import load_lt1_reinforcement

    lt1 = load_lt1_reinforcement()
    assert len(lt1["columns"]) == 1
    assert len(lt1["walls"]) == 1
    assert lt1["columns"][0].bar_count == 16
    assert lt1["columns"][0].diameter_mm == 22


def test_lt1_validacion_sigue_limpia():
    from reinforcement.validate_reinforcement import validate_dataset

    res = validate_dataset()
    assert not res["errors"]
    assert res["n_reglas"] >= 118


# ---------------------------------------------------------------------------
# LT2: datos de planos 200/201/202
# ---------------------------------------------------------------------------
def test_lt2_geometria_carga(geo2):
    assert len(geo2.column_tags()) == 50
    assert len(geo2.beam_tags()) == 237
    assert set(geo2.wall_parent_ids()) >= {"M001", "M003", "M002", "M004"}
    assert set(geo2.eje_x) == {"A'", "A", "B", "C", "C'", "D", "D'"}
    assert set(geo2.eje_y) == {"1", "1A", "2", "2A", "3"}


def test_lt2_dataset_independiente(data2):
    assert data2["columns"]
    # mesh/local cubren 200-202
    sheets = {r.id.sheet for r in data2["mesh"]}
    assert {"200I", "200S", "201I", "201S", "202I", "202S"} <= sheets


def test_planos_200_reglas_generales(data2):
    gen200i_x = [r for r in data2["mesh"]
                 if r.id.sheet == "200I" and "ejes horizontales" in r.zone.text]
    gen200i_y = [r for r in data2["mesh"]
                 if r.id.sheet == "200I" and "ejes verticales" in r.zone.text]
    assert gen200i_x and gen200i_x[0].diameter_mm == 12
    assert gen200i_x[0].spacing_cm == 20
    assert gen200i_y and gen200i_y[0].diameter_mm == 12
    gen200s_x = [r for r in data2["mesh"]
                 if r.id.sheet == "200S" and "ejes horizontales" in r.zone.text]
    assert gen200s_x and gen200s_x[0].diameter_mm == 12
    # cuadrados de fundacion 200I
    cuadrado = [r for r in data2["mesh"]
                if r.id.sheet == "200I" and "cuadrados" in r.zone.text]
    assert {r.diameter_mm for r in cuadrado} in ({16, 18}, {18, 16})
    # 3 trabas del eje D en 200S (local)
    eje_d = [r for r in data2["local"] if r.id.sheet == "200S" and "eje D" in r.zone.text]
    assert eje_d and eje_d[0].bar_count == 3 and eje_d[0].diameter_mm == 16


def test_planos_201_reglas(data2):
    gen201i_v = [r for r in data2["mesh"]
                 if r.id.sheet == "201I" and "general" in r.zone.text and "vertical" in r.zone.text]
    gen201i_h = [r for r in data2["mesh"]
                 if r.id.sheet == "201I" and "general" in r.zone.text and "horizontal" in r.zone.text]
    assert gen201i_v and gen201i_v[0].diameter_mm == 8 and gen201i_v[0].spacing_cm == 18
    assert gen201i_h and gen201i_h[0].diameter_mm == 8 and gen201i_h[0].spacing_cm == 24
    # perimetro, ejes y esquina en 201S
    perim = [r for r in data2["local"] if r.id.sheet == "201S" and "perimetro" in r.zone.text]
    assert perim and perim[0].bar_count == 2 and perim[0].diameter_mm == 16
    esquina = [r for r in data2["mesh"] if r.id.sheet == "201S" and "3-A'" in r.zone.text]
    assert esquina and esquina[0].diameter_mm == 8 and esquina[0].spacing_cm == 18


def test_planos_202_reglas(data2):
    resto_testo = [r for r in data2["mesh"]
                   if r.id.sheet == "202I" and "resto" in r.zone.text]
    assert resto_testo and resto_testo[0].diameter_mm == 8 and resto_testo[0].spacing_cm == 30
    cruces = [r for r in data2["local"] if r.id.sheet == "202S" and "cruces" in r.zone.text]
    assert cruces and cruces[0].bar_count == 2 and cruces[0].diameter_mm == 16
    peri1 = [r for r in data2["local"] if r.id.sheet == "202S" and "perimetro" in r.zone.text]
    assert peri1 and peri1[0].bar_count == 1 and peri1[0].diameter_mm == 16
    c_code = [r for r in data2["mesh"] if r.id.sheet == "202S" and "eje C'" in r.zone.text]
    assert c_code and c_code[0].diameter_mm == 10


def test_lt2_resolucion_zonas(assigner2):
    # zonas generales y franjas de ejes modelados quedan resueltas
    res = assigner2.resolved["mesh"]
    assert len(res) >= 20
    textos = [r.zone.text.lower() for r in res]
    assert any("esquina 3-a'" in t for t in textos)
    # eje C' (202I/202S) se resuelve como franja (BAND)
    bandas = [r for r in res if "eje c'" in r.zone.text.lower()]
    assert bandas and all(r.zone.axis == "C'" for r in bandas)
    # eje 1' NO existe en la grilla -> unresolvable
    eje1p = [r for r in (assigner2.resolved["mesh"] + assigner2.unresolved["mesh"])
             if "eje 1'" in r.zone.text.lower()]
    assert eje1p and all(r.resolution == Resolution.UNRESOLVED for r in eje1p)


def test_lt2_losas_no_mapeables(assigner2):
    losas = [r for r in assigner2.unresolved["mesh"] if "losa" in r.zone.text]
    assert losas, "las losas 0112/0113/etc. no deben asignarse a geometria"
    assert all(r.resolution == Resolution.UNRESOLVED for r in losas)


# ---------------------------------------------------------------------------
# Columnas LT2
# ---------------------------------------------------------------------------
def test_columnas_lt2_16_phi22(data2):
    cols = data2["columns"]
    assert cols, "debe existir la regla de columnas LT2"
    for r in cols:
        assert r.bar_count == 16
        assert r.diameter_mm == 22
        assert r.bar_type == ColumnBarType.LONGITUDINAL
        assert r.status == Status.EXACT
        assert r.source == "USER_CONFIRMED_DRAWING_DATA"


def test_columnas_lt2_sin_estribos_inventados(data2, assigner2):
    for r in data2["columns"]:
        assert r.geometry_pending is True, "sin recubrimiento -> pendiente"
    cols = assigner2.resolved["columns"]
    assert len(cols) == 1
    assert cols[0].resolution == Resolution.RESOLVED
    assert len(cols[0].column_tags) == 50, "se asocian las 50 columnas LT2"
    assert cols[0].column_tags[0] == 3001
    assert cols[0].column_tags[-1] == 3050


def test_columnas_lt2_no_generan_barras_3d():
    bars = build_bar_rows_lt2()
    assert not any("COL" in b["code"] for b in bars)


# ---------------------------------------------------------------------------
# Vigas 400
# ---------------------------------------------------------------------------
def test_vigas_especiales_sin_v60_80():
    beam = load_lt2_beam_data()
    fams_especiales = [r for r in beam["records"]
                       if any(s in r.section for s in ("V.F.", "V.I."))]
    assert fams_especiales
    for r in fams_especiales:
        assert r.kind in (BeamKind.FOUNDATION_BEAM, BeamKind.SPECIAL), (
            f"{r.beam_id} es viga especial pero kind={r.kind}"
        )
    # ningun segmento especial usa B22 de la familia V.60/80
    for seg in beam["segments"]:
        if seg.classification.value == "BEAM_FOUNDATION":
            assert seg.diameter_mm in (18, 22, 16)
            assert not (seg.diameter_mm == 22 and seg.bar_count == 2
                        and "V60/80-patron" in seg.physical_bar_id)


def test_vigas_patron_no_universal():
    beam = load_lt2_beam_data()
    patron = [r for r in beam["records"] if "patron" in r.beam_id.lower()]
    assert patron
    assert patron[0].confidence == Status.NEEDS_DRAWING_VALUE_CONFIRMATION
    # segmentos del patron sin beam_id asignable
    alias = [s for s in beam["segments"] if s.physical_bar_id.startswith("V60/80-patron")]
    assert alias and all(not s.beam_ids for s in alias)


def test_estribos_sin_zona_inventada():
    beam = load_lt2_beam_data()
    for z in beam["stirrups"]:
        assert z.diameter_mm == 10
        assert z.start_station_cm is None and z.end_station_cm is None
        assert z.confidence == Status.NEEDS_DRAWING_VALUE_CONFIRMATION


# ---------------------------------------------------------------------------
# Muros 300-305 por elevacion
# ---------------------------------------------------------------------------
def test_muros_lt2_por_elevacion(assigner2):
    walls = assigner2.resolved["walls"]
    assert len(walls) == 70, "14 ejes x 5 registros"
    # sin regla universal: todas tienen note sobre la elevacion/eje
    axes = sorted({w.axis for w in walls})
    assert "A'" in axes and "1" in axes and "3" in axes
    assert "1'" in axes and "8A" in axes and "D-D'" in axes
    assert all(w.geometry_pending for w in walls)


def test_muros_solo_ejes_inequivocos_con_parents(assigner2):
    parents_ok = {"A'": {"M001", "M003"}, "1": {"M002"}, "3": {"M004"}}
    for w in assigner2.resolved["walls"]:
        if w.wall_parents:
            assert set(w.wall_parents) == parents_ok[w.axis], w.axis
        else:
            assert w.resolution == Resolution.RESOLVED_METADATA


def test_muros_documentacion_axis_parent():
    # el mapeo axis->parents coincide con la documentacion de walls_LT2.csv
    assert WALL_AXIS_TO_PARENT == {
        "A'": ["M001", "M003"], "1": ["M002"], "3": ["M004"],
    }


# ---------------------------------------------------------------------------
# Escaleras 500
# ---------------------------------------------------------------------------
def test_escaleras_partes_separadas(assigner2):
    stairs = assigner2.resolved["stairs"]
    assert len(stairs) == len(load_lt2_stair_data()["records"])
    parts = {s.part for s in stairs}
    assert StairPart.FLIGHT_RAMP in parts
    assert StairPart.LANDING in parts
    assert StairPart.SUPPORT_LOCAL in parts
    assert StairPart.DETAIL in parts
    # longitudes del corte C referencian el corte
    corte_c = [s for s in stairs if s.detail_reference == "CORTE C"]
    assert corte_c, "deben conservarse los valores del CORTE C"
    assert all("CORTE C" in s.note or "corte" in s.note.lower() for s in corte_c)


def test_escaleras_sin_elementos_inventados(assigner2):
    for s in assigner2.resolved["stairs"]:
        assert s.resolution == Resolution.RESOLVED_METADATA
        assert "escalera" in s.note.lower()


# ---------------------------------------------------------------------------
# Geometria 3D LT2
# ---------------------------------------------------------------------------
def test_barras_solo_mallas_generales():
    bars = build_bar_rows_lt2()
    assert len(bars) > 100
    # coordenadas nativas LT2 (sin offset X ni inversion de Y)
    for b in bars:
        assert 0.0 <= b["x0_m"] <= 31.475 + 1e-6
        assert 0.0 <= b["y0_m"] <= 16.15 + 1e-6
        assert 0.0 <= b["x1_m"] <= 31.475 + 1e-6
        assert 0.0 <= b["y1_m"] <= 16.15 + 1e-6
    levels = {b["level"] for b in bars}
    assert {"L1", "L2", "L3", "L4"} <= levels, "201 cubre L1..L4"
    assert "ROOF" in levels, "202 loza cielo piso 4° = ROOF"


def test_barras_dos_direcciones():
    bars = build_bar_rows_lt2()
    dirs = {b["direction"] for b in bars}
    assert dirs == {"X", "Y"}


# ---------------------------------------------------------------------------
# Validacion integral
# ---------------------------------------------------------------------------
def test_validacion_lt2_sin_errores():
    res = validate_dataset_lt2()
    assert not res["errors"], res["errors"][:5]
    assert not res["warnings"]
    assert res["n_reglas"] >= 150
    # statuses presentes
    sc = res["status_counts"]
    assert sc.get("EXACT", 0) > 0
    assert sc.get("NEEDS_DRAWING_VALUE_CONFIRMATION", 0) > 0
    assert sc.get("NEEDS_EXACT_ZONE_MAPPING", 0) > 0


# ---------------------------------------------------------------------------
# Modelo estructural invariante
# ---------------------------------------------------------------------------
@pytest.mark.slow
def test_combined_model_invariante_lt2():
    r = check_model_rc()
    assert r["ok"], f"el modelo combinado cambio con la armadura LT2: {r['diffs']}"
    assert r["actual"]["rc"] == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-m", "not slow", "-q"]))