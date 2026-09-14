"""Tests del modelo combinado exportado a Unity (ETAPA P1L4).

Cobertura (sin abrir OpenSees; lee directamente los JSON ya generados):
- `modelo_combinado.json` pasa la validacion automatica completa
  (nodos, elementos, secciones, ejes locales, apoyos, diafragmas,
  cargas, areas tributarias y resultados/equilibrio por caso).
- Invarianza del corte de sierras: el JSON de StreamingAssets es
  identico (hash) al generado en COMBINADO/outputs/unity.
- `modelo_lt1.json` en StreamingAssets se conserva intacto.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

COMB_SRC = Path(__file__).resolve().parents[1] / "src"
ROOT = Path(__file__).resolve().parents[2]
if str(COMB_SRC) not in sys.path:
    sys.path.insert(0, str(COMB_SRC))

from validar_unity_combinado import Validator  # noqa: E402

JSON_OUT = ROOT / "COMBINADO" / "outputs" / "unity" / "modelo_combinado.json"
JSON_SA = ROOT / "unity" / "LT1Viewer" / "Assets" / "StreamingAssets" \
    / "modelo_combinado.json"
JSON_LT1_SA = ROOT / "unity" / "LT1Viewer" / "Assets" / "StreamingAssets" \
    / "modelo_lt1.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_modelo_combinado_validado():
    v = Validator(JSON_OUT)
    v.run()
    assert not v.fail, f"FALLOS: {v.fail[:20]}"
    assert len(v.ok) > 50000


def test_streaming_assets_sincronizado():
    assert JSON_SA.exists(), "falta modelo_combinado.json en StreamingAssets"
    assert _sha256(JSON_OUT) == _sha256(JSON_SA)


def test_modelo_lt1_conservado():
    lt1 = __import__("json").load(open(JSON_LT1_SA, "r", encoding="utf-8"))
    assert len(lt1.get("nodes", [])) > 0
    assert "beams" in lt1 and "columns" in lt1