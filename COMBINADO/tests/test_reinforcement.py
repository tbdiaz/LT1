"""Tests del modulo de armadura LT1.

Cobertura:
- Invarianza del modelo estructural combinado (rc=0, P_total, nodos,
  apoyos, sumRz) cuando se incorpora la capa de armadura.
- Consistencia del dataset LT1 (diametros/espaciamientos > 0).
- Reglas de direccion y capa bien almacenadas (X/Y, lower/upper/both).
- Resolucion de zonas: reglas con ejes modelados se resuelven; reglas que
  mencionan ejes fuera de la grilla (IB/1BB/8/etc.) NO se asignan.
- Los muros/beam/stairs se registran con su familia/estado esperado.
- Geometria de barras: capa separada con cover parametrizable y sin
  dependencias del modelo estructural.

El test `test_combined_model_invariante` re-ejecuta el analisis completo;
es el unico que abre OpenSeesPy (puede tardar unos minutos).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

COMB_SRC = Path(__file__).resolve().parents[1] / "src"
if str(COMB_SRC) not in sys.path:
    sys.path.insert(0, str(COMB_SRC))

import run_combined  # noqa: E402
from reinforcement import (  # noqa: E402
    assign_lt1_reinforcement as assign_mod,
)
from reinforcement.lt1_geometry import Lt1Geometry  # noqa: E402
from reinforcement.lt1_reinforcement_data import (  # noqa: E402
    FLOOR_TO_LEVEL,
    load_lt1_reinforcement,
)
from reinforcement.reinforcement_geometry import (  # noqa: E402
    ReinforcementGeometryBuilder,
)
from reinforcement.reinforcement_types import Resolution, Status  # noqa: E402
from reinforcement.validate_reinforcement import (  # noqa: E402
    BASELINE_MODEL,
    check_model_rc,
    validate_dataset,
)
from reinforcement.lt1_beam_data import (  # noqa: E402
    BEAM_IDS_400,
    BEAM_IDS_401,
    BEAM_IDS_402,
    all_beam_ids,
    load_lt1_beam_data,
)
from reinforcement.reinforcement_types import (  # noqa: E402
    BeamKind,
    BeamRebarSegment,
    BeamStirrupZone,
    ColumnBarType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def dataset() -> dict:
    return load_lt1_reinforcement()


@pytest.fixture(scope="session")
def assigner():
    return assign_mod.Lt1ReinforcementAssigner().run()


@pytest.fixture(scope="session")
def geo() -> Lt1Geometry:
    return Lt1Geometry()


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def test_diametro_y_espaciamiento_positivos(dataset):
    for r in dataset["mesh"]:
        assert r.diameter_mm > 0, f"diametro invalido {r.id}"
        assert r.spacing_cm > 0, f"espaciamiento invalido {r.id}"
    for r in dataset["local"]:
        assert r.diameter_mm > 0, f"diametro invalido {r.id}"


def test_direcciones_x_y_bien_almacenadas(dataset):
    for r in dataset["mesh"]:
        assert r.direction.value in ("X", "Y", "BOTH", "LOCAL")
    # al menos una regla general inferior X e Y en 202-I
    sheets = [r.id.sheet for r in dataset["mesh"]]
    assert "202-I" in sheets
    xs = [r for r in dataset["mesh"]
          if r.id.sheet == "202-I" and r.direction.value == "X"]
    ys = [r for r in dataset["mesh"]
          if r.id.sheet == "202-I" and r.direction.value == "Y"]
    assert xs and ys, "202-I debe tener malla X e Y diferenciadas"


def test_capas_lower_upper(dataset):
    layers = {r.layer.value for r in dataset["mesh"]}
    assert {"lower", "upper", "both"} & layers == layers
    sup = [r for r in dataset["mesh"]
           if r.id.sheet == "202-S" and r.layer.value == "upper"]
    inf = [r for r in dataset["mesh"]
           if r.id.sheet == "202-I" and r.layer.value == "lower"]
    assert sup and inf


def test_status_validos(dataset):
    valid = {s.value for s in Status}
    for rules in dataset.values():
        for r in rules:
            assert r.status.value in valid, f"status invalido {r.id}"


def test_vigas_supersedidas(dataset):
    for r in dataset["beams"]:
        assert r.status == Status.SUPERSEDED_BY_EXACT_BEAM_DRAWINGS


def test_muros_tipicos(dataset):
    assert len(dataset["walls"]) == 1
    assert dataset["walls"][0].status == Status.TYPICAL


def test_escaleras_requieren_detalle(dataset):
    for r in dataset["stairs"]:
        assert r.status == Status.DETAIL_FROM_DRAWING_REQUIRED


# ---------------------------------------------------------------------------
# Resolucion de zonas
# ---------------------------------------------------------------------------
def test_zonas_con_ejes_modelados_resueltas(assigner):
    res = assigner.resolved["mesh"]
    assert len(res) > 20, "deben resolverse las zonas E-F/1-2 etc. del plano"
    # contiene la zona general de fundacion y rectangulos E-F/1-2
    textos = [r.zone.text.lower() for r in res]
    assert any("e-f/1-2" in t for t in textos)
    # panos encontrados en 201 -> PISO_1_P11 / P12
    p11 = [r for r in res if "PISO_1_P11" in "".join(r.zone.pano_ids)]
    assert p11, "E-F/1-2 en 201 debe mapear al pano PISO_1_P11"


def test_zonas_fuera_de_grilla_no_asignadas(assigner):
    # 200-S: I-IB / 2-3  -> IB no existe
    ib = [r for r in assigner.unresolved["mesh"]
          if r.id.sheet == "200-S" and "IB" in r.zone.text]
    assert ib, "zona I-IB/2-3 debe quedar unresolved"
    # 202-S: eje IB
    eje_ib = [r for r in assigner.unresolved["mesh"]
              if r.id.sheet == "202-S" and "IB" in r.zone.text]
    assert eje_ib


def test_losas_plano_no_mapeadas(assigner):
    for r in assigner.unresolved["mesh"]:
        if "Losa" in r.zone.text or "losa" in r.zone.text:
            assert r.resolution == Resolution.UNRESOLVED
    # al menos una losa de plano queda pendiente (ej. Losa 426)
    losas = [r for r in assigner.unresolved["mesh"]
             if "426" in r.zone.text]
    assert losas


def test_muros_resueltos_con_tags(assigner, geo):
    assert len(assigner.resolved["walls"]) == 1
    w = assigner.resolved["walls"][0]
    assert w.resolution == Resolution.RESOLVED
    assert str(geo.wall_tags()[0]) in w.zone.note


def test_vigas_metadata_no_obligatoria(assigner):
    for r in assigner.resolved["beams"]:
        assert r.resolution == Resolution.RESOLVED_METADATA
        assert r.status == Status.SUPERSEDED_BY_EXACT_BEAM_DRAWINGS


# ---------------------------------------------------------------------------
# Geometria 3D (capa separada)
# ---------------------------------------------------------------------------
def test_generacion_barras(assigner, geo):
    bld = ReinforcementGeometryBuilder(assigner, geo=geo, cover_cm=3.0)
    bars = bld.build()
    assert len(bars) > 100
    # coordenadas en sistema combinado (x = +31.25)
    xs = {round(b.p0[0], 3) for b in bars}
    assert max(xs) > 31.25 + 40.0, "las barras deben estar en sistema combinado"


def test_cover_none_marca_aproximacion(assigner, geo):
    bld = ReinforcementGeometryBuilder(assigner, geo=geo, cover_cm=None)
    bars = bld.build()
    assert all(b.z_approximation for b in bars)


def test_cover_definido_sin_aproximacion(assigner, geo):
    bld = ReinforcementGeometryBuilder(assigner, geo=geo, cover_cm=3.0)
    bars = bld.build()
    assert all(not b.z_approximation for b in bars)


# ---------------------------------------------------------------------------
# Dataset de vigas (planos 400/401/402)
# ---------------------------------------------------------------------------
def test_indice_vigas_completo():
    assert ("V110" not in BEAM_IDS_400 and "V115" not in BEAM_IDS_400)
    assert "V200" in BEAM_IDS_401 and "V211" in BEAM_IDS_401
    assert "V306" in BEAM_IDS_402 and "VF3" in BEAM_IDS_402
    union = set(BEAM_IDS_400) | set(BEAM_IDS_401) | set(BEAM_IDS_402)
    assert len(all_beam_ids()) == len(union), "beam ids duplicados entre planos"


def test_beam_data_carga_segmentos_y_estribos():
    data = load_lt1_beam_data()
    assert data["segments"], "debe haber barras longitudinales"
    assert data["stirrups"], "debe haber zonas de estribos"
    for seg in data["segments"]:
        assert isinstance(seg, BeamRebarSegment)
        assert seg.diameter_mm > 0
    for z in data["stirrups"]:
        assert isinstance(z, BeamStirrupZone)


def test_estribos_tp_no_inventan_distribucion():
    data = load_lt1_beam_data()
    for z in data["stirrups"]:
        if z.detail_reference.startswith("TP."):
            assert z.spacing_cm is None, "no inventar espaciamiento con TP"


def test_beam_data_validacion():
    res = validate_beam_dataset_for_test()
    assert not res["errors"]


def validate_beam_dataset_for_test():
    from reinforcement.validate_reinforcement import validate_beam_dataset
    return validate_beam_dataset()


# ---------------------------------------------------------------------------
# Columnas LT1 (16 B22 longitudinal)
# ---------------------------------------------------------------------------
def test_columnas_16_b22_longitudinal(dataset):
    cols = dataset["columns"]
    assert cols, "debe existir la regla de columnas LT1"
    for r in cols:
        assert r.bar_count == 16
        assert r.diameter_mm == 22
        assert r.bar_type == ColumnBarType.LONGITUDINAL
        assert r.status == Status.EXACT
        assert r.source == "USER_CONFIRMED_DRAWING_DATA"


def test_columnas_no_inventan_estribos(dataset):
    for r in dataset["columns"]:
        assert r.geometry_pending is True, (
            "sin recubrimiento/distribucion la geometria 3D debe quedar pendiente"
        )


def test_columnas_asignadas_resolved(assigner):
    cols = assigner.resolved["columns"]
    assert len(cols) == 1
    r = cols[0]
    assert r.resolution == Resolution.RESOLVED
    assert len(r.column_tags) == 90, "todas las columnas LT1 deben asociarse"


def test_columnas_no_salen_como_barras_3d(assigner, geo):
    # la armadura de columnas no genera geometria 3D (pendiente)
    bars = ReinforcementGeometryBuilder(assigner, geo=geo, cover_cm=3.0).build()
    cols_found = [b for b in bars if "column" in b.code.lower()]
    # las barras provienen solo de losas (code=regla de mesh), ninguna COL
    assert not any(b.code.startswith("LT1:COL") for b in bars)


# ---------------------------------------------------------------------------
# Modelo estructural invariante
# ---------------------------------------------------------------------------
@pytest.mark.slow
def test_combined_model_invariante():
    r = check_model_rc()
    assert r["ok"], f"el modelo combinado cambio con la armadura: {r['diffs']}"
    assert r["actual"]["rc"] == 0
    assert r["actual"]["P_total"] == pytest.approx(BASELINE_MODEL["P_total"], rel=1e-6)
    assert r["actual"]["n_nodos_fisicos"] == BASELINE_MODEL["n_nodos_fisicos"]
    assert r["actual"]["n_apoyos"] == BASELINE_MODEL["n_apoyos"]


def test_baseline_consistente_con_runner():
    # el baseline almacenado debe ser el del modelo actual de run_combined
    b = run_combined.CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()
    b.apply_loads()
    rc = b.run_analysis()
    assert rc == 0
    assert b.P_total == pytest.approx(BASELINE_MODEL["P_total"], rel=1e-6)