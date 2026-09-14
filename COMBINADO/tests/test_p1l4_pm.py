"""Tests P1L4 - capacidades P-M, recomposicion M001 y trazabilidad en el
modelo combinado (FASES 2-4 de P1L4).

Cubre:
- Recomposicion del muro M001 a partir del par 4001+4002: identidad
  N_muro = N1(4001)+N1(4002) == suma de reacciones Rz en los apoyos base
  (validado contra `results.reactions` del JSON, sin re-ejecutar OpenSees).
- Auditoria EY: desglose M_muro presente, verificado contra reacciones Mx
  de los apoyos, y eje fuerte/debil distintos y documentados.
- Datos de demanda por caso finitos y con convencion (N positivo =
  compresion) coherente con las reacciones.
- Chequeos demanda<->capacidad: columna dentro en todos los casos; muro
  FUERA (eje fuerte) bajo EY y DENTRO en su eje debil (EX incluido).
- Rigor: curvas P-M finitas, con compresion creciente y P0 > demandas.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
JSON_OUT = ROOT / "COMBINADO" / "outputs" / "unity" / "modelo_combinado.json"
JSON_SA = ROOT / "unity" / "LT1Viewer" / "Assets" / "StreamingAssets" \
    / "modelo_combinado.json"

CASOS = ["G", "Q", "EX", "EY", "COMBO_R"]


@pytest.fixture(scope="module")
def modelo():
    with open(JSON_OUT, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reactions(modelo):
    return modelo["results"]["reactions"]


def _apoyo(reactions, caso, tag):
    return reactions[caso][str(tag)][2]   # [Fx,Fy,Fz,Mx,My,Mz] -> Fz=Rz


def _apoyo_mx(reactions, caso, tag):
    return reactions[caso][str(tag)][3]   # Mx global


def test_recomposicion_m001_igual_a_reacciones(modelo, reactions):
    f = modelo["results"]["forces"]
    r1 = _apoyo(reactions, "G", "1")
    r3 = _apoyo(reactions, "G", "3")
    n4001 = float(f["G"]["4001"]["N1"])
    n4002 = float(f["G"]["4002"]["N1"])
    assert n4001 == pytest.approx(0.0, abs=1e-9)
    assert n4001 + n4002 == pytest.approx(r1 + r3, abs=1e-6)


def test_convencion_n_positivo_compresion_en_muro(modelo, reactions):
    f = modelo["results"]["forces"]
    g = f["G"]
    n_muro = float(g["4001"]["N1"]) + float(g["4002"]["N1"])
    assert n_muro == pytest.approx(_apoyo(reactions, "G", "1")
                                   + _apoyo(reactions, "G", "3"), abs=1e-6)
    assert n_muro > 0
    assert float(g["4001"]["N1"]) == 0.0
    assert float(g["4002"]["N1"]) == pytest.approx(
        _apoyo(reactions, "G", "3"), abs=1e-6)


def test_auditoria_ey_desglose_y_reacciones(modelo, reactions):
    """EY: Mz1(4001), Mz1(4002) son las reacciones Mx de los apoyos y el
    desglose integra M_muro(EY) = 8836 kN.m (demanda real)."""
    pm = modelo["results"]["pm"]["muro_M001"]
    v = pm["recomposicion"]["verificado_ey"]
    f = modelo["results"]["forces"]["EY"]
    assert float(f["4001"]["Mz1"]) == pytest.approx(
        _apoyo_mx(reactions, "EY", "1"), abs=1e-6)
    assert float(f["4002"]["Mz1"]) == pytest.approx(
        _apoyo_mx(reactions, "EY", "3"), abs=1e-6)
    m_muro = (float(f["4001"]["Mz1"]) + float(f["4002"]["Mz1"])
              + 1.46 * (float(f["4001"]["N1"]) - float(f["4002"]["N1"])))
    assert abs(m_muro) == pytest.approx(float(v["M_muro_kN_m"]), abs=1e-3)
    assert abs(m_muro) == pytest.approx(8836.237, rel=1e-4)
    assert float(v["N1_4001_kN"]) == pytest.approx(0.0, abs=1e-9)


def test_anomalia_4001_documentada(modelo):
    pm = modelo["results"]["pm"]["muro_M001"]
    assert pm["elementTags"] == [4001, 4002]
    txt = pm["recomposicion"]["por_que_N1_4001_es_0"].lower()
    assert "esquina a" in txt and "carga axial" in txt


def test_ejes_fuerte_debil_distintos_y_documentados(modelo):
    pm = modelo["results"]["pm"]["muro_M001"]
    cap = pm["capacidad"]
    assert len(cap["curva_fuerte"]) > 8
    assert len(cap["curva_debil"]) > 4
    # fuerte (lever ~2.92) >> debil (lever ~0.6) a igual N
    f0 = next(p for p in cap["curva_fuerte"] if p[0] == 0.0)[1]
    d0 = next(p for p in cap["curva_debil"] if p[0] == 0.0)[1]
    assert f0 > 3 * d0
    assert "decision" in pm["ejes"]


def test_columna_dentro_en_demanda(modelo):
    pm = modelo["results"]["pm"]["columna_113022"]
    for caso in CASOS:
        d = pm["demanda_por_caso"][caso]
        assert d["dentro"] is True
        assert d["M_demanda_kN_m"] < d["M_capacidad_kN_m"]


def test_muro_ey_fuera_en_eje_fuerte(modelo):
    pm = modelo["results"]["pm"]["muro_M001"]
    d = pm["demanda_por_caso"]["EY"]
    assert d["dentro_fuerte"] is False
    assert d["M_fuerte_demanda_kN_m"] > 5000
    # capacidad de eje fuerte en EY es ~5000, muy por debajo de la demanda
    assert d["M_fuerte_capacidad_kN_m"] < d["M_fuerte_demanda_kN_m"]


def test_muro_debil_dentro_ex(modelo):
    pm = modelo["results"]["pm"]["muro_M001"]
    d = pm["demanda_por_caso"]["EX"]
    assert d["dentro_debil"] is True
    assert d["My_debil_demanda_kN_m"] < d["M_debil_capacidad_kN_m"]


def test_muro_demanda_por_caso_5_casos(modelo):
    pm = modelo["results"]["pm"]["muro_M001"]
    assert set(pm["demanda_por_caso"]) == set(CASOS)


def test_curvas_pm_finitas_y_p0_fuera_de_escala(modelo):
    pm = modelo["results"]["pm"]
    for f in (pm["columna_113022"]["capacidad"]["curva"],
              pm["muro_M001"]["capacidad"]["curva_fuerte"],
              pm["muro_M001"]["capacidad"]["curva_debil"]):
        ps = [c[0] for c in f]
        assert ps == sorted(ps)
        assert all(math.isfinite(c[0]) and math.isfinite(c[1]) for c in f)
    assert abs(pm["muro_M001"]["capacidad"]["P0_kN_compresion"]) > 20000
    assert abs(pm["columna_113022"]["capacidad"]["P0_kN_compresion"]) > 15000
    max_dem = max(pm["columna_113022"]["demanda_por_caso"][c]["N_kN_compresion"]
                  for c in CASOS)
    max_wall = max(pm["muro_M001"]["demanda_por_caso"][c]["N_kN_compresion"]
                   for c in CASOS)
    assert abs(pm["columna_113022"]["capacidad"]["P0_kN_compresion"]) > max_dem
    assert abs(pm["muro_M001"]["capacidad"]["P0_kN_compresion"]) > max_wall


def test_grupo_muro_unico_fisico_documentado(modelo):
    """M001 (dos objetos Unity 4001/4002) se verifica como un unico muro."""
    pm = modelo["results"]["pm"]["muro_M001"]
    assert pm["objetos_unity"]["elementTags_para_agrupar"] == [4001, 4002]
    desc = pm["objetos_unity"]["descripcion"].lower()
    assert "un unico muro fisico" in desc


def test_pm_en_streaming_assets_sincronizado():
    with open(JSON_SA, "r", encoding="utf-8") as f:
        sa = json.load(f)
    with open(JSON_OUT, "r", encoding="utf-8") as f:
        out = json.load(f)
    assert sa["results"]["pm"] == out["results"]["pm"]