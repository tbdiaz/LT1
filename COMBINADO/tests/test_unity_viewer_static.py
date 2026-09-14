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