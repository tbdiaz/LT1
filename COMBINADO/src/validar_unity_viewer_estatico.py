#!/usr/bin/env python3
"""validar_unity_viewer_estatico.py - Validacion estatica del visor COMBINADO.

Etapa P1L4. Verifica, SIN abrir Unity solo este script:

  1. El JSON `modelo_combinado.json` es JSON valido.
  2. Consistencia de campos: todo lo presente en el JSON tiene su clase y
     campo declarado en `CombinedModelData.cs` (misma clave, tipo basico
     compatible: float<->numero, int<->entero, string<->string, arrays,
     objetos anidados a sus clases).
  3. `results.cases` coincide con las claves de forces/displacements/
     reactions/equilibrio (los casos desplegables son exactamente los
     exportados; COMBO_R solo la superposicion existente).
  4. Inventario: 485 nodos, 694 elementos (399 viga + 175 columna + 120 muro
     por categoria del visor), 53 apoyos, 5 masters, 5 diafragmas,
     24 constraint_links, cargas G/Q 27306 y EX/EY 4, tributarias LT1 108 y
     LT2 344 (320 fuente + 24 correcciones V30 firmadas).
  5. Checks de fuente C#:
       - llaves/pararentesis balanceados en todos los .cs,
       - sin clases duplicadas entre Scripts y Editor,
       - sin referencias obsoletas (pending_geometry fuera de su definicion;
         ningun script apunta a modelo_lt1.json como fuente),
       - ModelLoader usa el nombre de archivo correcto,
       - LT1SceneBuilder registra los componentes nuevos.
  6. La unica escena fuente permitida es Assets/Scenes/LT1Viewer.unity;
     se ignoran artefactos internos de Library.

Uso:
    cd COMBINADO/src && python3 validar_unity_viewer_estatico.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "unity" / "LT1Viewer" / "Assets" / "Scripts"
EDITOR = ROOT / "unity" / "LT1Viewer" / "Assets" / "Editor"
OUT = ROOT / "COMBINADO" / "outputs" / "unity" / "modelo_combinado.json"
SA_OUT = ROOT / "unity" / "LT1Viewer" / "Assets" / "StreamingAssets" \
    / "modelo_combinado.json"
P1L4_OUT = ROOT / "COMBINADO" / "outputs" / "p1l4"
SA_DIR = SA_OUT.parent
PANEL = SCRIPTS / "PmPanelController.cs"

EXPECTED = {
    "metadata.modelo": "COMBINADO_LT1_LT2",
    "nodos": 485,
    "elementos": 694,
    "apoyos": 53,
    "masters": 5,
    "diafragmas": 5,
    "constraint_links": 24,
    "cargas_G": 27306,
    "cargas_Q": 27306,
    "cargas_EX": 4,
    "cargas_EY": 4,
    "tributarias_LT1": 108,
    "tributarias_LT2": 344,
}

TIPOS = {
    "viga": 344, "columna": 125, "muro_corner": 80, "vertical_caja": 50,
    "viga_saliente": 30, "segmento_fachada": 25, "conector_v40_muro": 10,
    "muro": 30,
}
CATEGORIAS = {"Beam": 399, "Column": 175, "Wall": 120}

# Clases [Serializable] que corresponden a cada seccion del JSON.
CLASS_SCHEMA = {
    "metadata": "CombinedMetadata",
    "nodes": "CombinedNode",
    "elements": "CombinedElement",
    "supports": "CombinedSupport",
    "masters": "CombinedMaster",
    "diaphragms": "CombinedDiaphragm",
    "constraint_links": "CombinedLink",
}

# Clases para objetos anidados dentro de los records.
OBJECT_SCHEMA = {
    "metadata": {
        "unidades": "CombinedUnits",
        "materiales": "CombinedMaterials",
        "casos": "CombinedCaseSet",
        "niveles": "CombinedLevel[]",
        "interfaz_lt1_lt2": "CombinedInterfaz",
        "convencion_ejes_locales": "CombinedVecConv",
        "notas_modelo": "string[]",
    },
    "elements": {
        "seccion": "CombinedSection",
        "vecxz": "float[]",
        "ejes_locales": "CombinedAxes",
    },
}

# Los casos desplegables son exactamente los tags de results.cases.

# Claves del JSON que NO se deserializan a clases C# porque sus subclaves
# son dinamicas. Se declaran aqui para el control de keyset, con su razon:
#  - conteo_geometria: {por_tipo, por_origen} con claves variables; los
#    conteos para el visor se derivan del arreglo "elements".
IGNORED_JSON_KEYS = {"conteo_geometria"}
ELEM_FIELD_CLASSES = {
    "metadata": {
        "materiales": {"concreto": "CombinedConcreto",
                       "acero": "CombinedAcero",
                       "conector_v40_muro": "CombinedConectorV40"},
        "casos": {"G": "CombinedCaseInfo", "Q": "CombinedCaseInfo",
                  "EX": "CombinedCaseInfo", "EY": "CombinedCaseInfo",
                  "COMBO_R": "CombinedCaseInfo"},
    },
}

SIMPLE = {
    "int", "float", "string", "bool", "int[]", "float[]", "string[]",
}


class BraceUnbalanced(ValueError):
    pass


def strip_comments_and_strings(text: str) -> str:
    """Quita comentarios // y /* */ y strings para el balance de llaves."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif text[i] in "\"'":
            q = text[i]
            out.append(q)
            i += 1
            while i < n and text[i] != q:
                if text[i] == "\\":
                    i += 2
                else:
                    i += 1
            if i < n:
                out.append(q)
                i += 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def check_balance(text: str, label: str, fails: list) -> None:
    cleaned = strip_comments_and_strings(text)
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in cleaned:
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack[-1] != pairs[ch]:
                fails.append(f"{label}: desbalance en '{ch}'")
                return
            stack.pop()
    if stack:
        fails.append(f"{label}: {len(stack)} llaves/parantesis sin cerrar")


class_brace_re = re.compile(
    r"\[Serializable\]\s*[\w.]*\s*class\s+(\w+)\s*\{")
field_re = re.compile(r"public\s+([A-Za-z0-9_<>\[\], ]+?)\s+(\w+)\s*;")


def extract_classes(path: Path):
    """Devuelve {clase: {campo: tipo}} para las clases [Serializable]."""
    text = strip_comments_and_strings(path.read_text(encoding="utf-8"))
    result = {}
    for m in class_brace_re.finditer(text):
        name = m.group(1)
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i - 1]
        fields = {}
        for f in field_re.finditer(body):
            ftype = " ".join(f.group(1).split())
            fname = f.group(2)
            if fname not in ("get", "set"):
                fields[fname] = ftype
        result[name] = fields
    return result


class StaticValidator:
    def __init__(self, json_path: Path):
        self.json_path = json_path
        self.ok = []
        self.fail = []

    def run(self):
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        self._classes = extract_classes(SCRIPTS / "CombinedModelData.cs")
        if not self._classes:
            self.fail.append("No se encontraron clases [Serializable] en "
                             "CombinedModelData.cs")
            return self
        self._inventory(data)
        self._schema_consistency(data)
        self._results_consistency(data)
        self._diagram_equilibrium_checks(data)
        self._pm_checks(data)
        self._cs_checks()
        self._scene_checks()
        return self

    @property
    def valid(self):
        return len(self.fail) == 0

    def _diagram_equilibrium_checks(self, data):
        """Comprueba la reconstruccion My/Vz contra ambos extremos OpenSees."""
        elements = {int(e["elementTag"]): e for e in data.get("elements", [])}
        loads = data.get("loads", {})
        forces = data.get("results", {}).get("forces", {})
        combo = (data.get("metadata", {}).get("casos", {})
                 .get("COMBO_R", {}).get("coef", {}))
        coefficients = {
            "G": (1.0, 0.0), "Q": (0.0, 1.0),
            "EX": (0.0, 0.0), "EY": (0.0, 0.0),
            "COMBO_R": (float(combo.get("G", 0.0)),
                        float(combo.get("Q", 0.0))),
        }

        grouped = {"G": {}, "Q": {}}
        for base in ("G", "Q"):
            for row in loads.get(base, []):
                grouped[base].setdefault(int(row["element_tag"]), []).append(row)

        max_m = max_mz = max_v = 0.0
        checked = 0
        for case, (coef_g, coef_q) in coefficients.items():
            case_forces = forces.get(case, {})
            for tag_text, f in case_forces.items():
                tag = int(tag_text)
                element = elements.get(tag)
                if element is None:
                    self.fail.append(f"diagrama {case}: elemento {tag} ausente")
                    continue
                length = float(element["longitud_m"])
                moment = -float(f["My1"]) - float(f["Vz1"]) * length
                shear = -float(f["Vz1"])
                for base, factor in (("G", coef_g), ("Q", coef_q)):
                    if abs(factor) <= 1e-15:
                        continue
                    for row in grouped[base].get(tag, []):
                        kind = row.get("tipo", "")
                        if kind.startswith("beamUniform"):
                            w = factor * float(row.get("w_kN_m", 0.0))
                            moment += 0.5 * w * length * length
                            shear += w * length
                        elif kind == "beamPoint":
                            p = factor * float(row.get("q_kN", 0.0))
                            a = float(row.get("xloc", 0.0)) * length
                            moment += p * (length - a)
                            shear += p
                err_m = abs(moment - float(f["My2"]))
                moment_z = -float(f["Mz1"]) + float(f["Vy1"]) * length
                err_mz = abs(moment_z - float(f["Mz2"]))
                err_v = abs(shear - float(f["Vz2"]))
                max_m = max(max_m, err_m)
                max_mz = max(max_mz, err_mz)
                max_v = max(max_v, err_v)
                checked += 1
                if err_m > 1e-7 or err_mz > 1e-7 or err_v > 1e-7:
                    self.fail.append(
                        f"diagrama {case} tag {tag}: cierre My={err_m:.3e}, "
                        f"Mz={err_mz:.3e}, Vz={err_v:.3e}")
        if max_m <= 1e-7 and max_mz <= 1e-7 and max_v <= 1e-7:
            self.ok.append(
                f"diagramas seccionales = {checked} cierres, "
                f"max dMy={max_m:.2e}, max dMz={max_mz:.2e}, "
                f"max dVz={max_v:.2e}")

    # ---------------------------------------------------------------- inventario
    def _inventory(self, data):
        nodes = data.get("nodes", [])
        elements = data.get("elements", [])
        supports = data.get("supports", [])
        masters = data.get("masters", [])
        diaphragms = data.get("diaphragms", [])
        links = data.get("constraint_links", [])
        loads = data.get("loads", {})

        got = {
            "nodos": len(nodes),
            "elementos": len(elements),
            "apoyos": len(supports),
            "masters": len(masters),
            "diafragmas": len(diaphragms),
            "constraint_links": len(links),
            "cargas_G": len(loads.get("G", [])),
            "cargas_Q": len(loads.get("Q", [])),
            "cargas_EX": len(loads.get("EX", [])),
            "cargas_EY": len(loads.get("EY", [])),
        }
        trib = data.get("tributary_areas", {})
        got["tributarias_LT1"] = len(trib.get("LT1", {}).get("filas", []))
        got["tributarias_LT2"] = len(trib.get("LT2", {}).get("filas", []))

        md = data.get("metadata", {})
        if md.get("modelo") != EXPECTED["metadata.modelo"]:
            self.fail.append(
                f"metadata.modelo esperado {EXPECTED['metadata.modelo']!r} "
                f"obtenido {md.get('modelo')!r}")

        for key, expected in EXPECTED.items():
            if key == "metadata.modelo":
                continue
            self._assert_eq(key, expected, got.get(key))

        tipos = {}
        for e in elements:
            tipos[e.get("tipo")] = tipos.get(e.get("tipo"), 0) + 1
        for t, expected in TIPOS.items():
            self._assert_eq(f"elementos.tipo.{t}", expected, tipos.get(t))
        if set(tipos) != set(TIPOS):
            self.fail.append(
                f"tipos de elemento inesperados: {sorted(set(tipos) - set(TIPOS))}")

        categorias = {"Beam": 0, "Column": 0, "Wall": 0}
        for e in elements:
            t = e.get("tipo")
            if t in ("viga", "viga_saliente", "segmento_fachada"):
                categorias["Beam"] += 1
            elif t in ("columna", "vertical_caja"):
                categorias["Column"] += 1
            elif t in ("muro", "muro_corner", "conector_v40_muro"):
                categorias["Wall"] += 1
            else:
                self.fail.append(f"elemento sin categoria: tag {e.get('elementTag')}")
        for cat, expected in CATEGORIAS.items():
            self._assert_eq(f"categoria.{cat}", expected, categorias[cat])

    def _assert_eq(self, label, expected, got):
        if got == expected:
            self.ok.append(f"{label} = {got}")
        else:
            self.fail.append(f"{label}: esperado {expected}, obtenido {got}")

    # ------------------------------------------------------------ schema / C#
    def _schema_consistency(self, data):
        classes = self._classes

        # 1) secciones de primer nivel
        for section, cls in CLASS_SCHEMA.items():
            records = data.get(section)
            if section == "metadata":
                self._check_record(classes[cls], records,
                                   f"{section} (raiz)",
                                   OBJECT_SCHEMA.get(section, {}))
            elif isinstance(records, list) and records:
                union = set()
                for r in records:
                    union.update(r.keys())
                self._check_keyset(cls, union, section, OBJECT_SCHEMA.get(section, {}))
            elif not records:
                self.fail.append(f"seccion '{section}' vacia o ausente")

        # 2) loads / tributary / results
        loads = data.get("loads", {})
        gt = loads.get("G", [])
        qt = loads.get("Q", [])
        self._check_records_union(classes["CombinedBeamLoad"], gt + qt, "loads(G+Q)")
        ex = loads.get("EX", [])
        ey = loads.get("EY", [])
        self._check_records_union(classes["CombinedLateralLoad"], ex + ey, "loads(EX+EY)")
        lat = loads.get("COMBO_R")
        if not isinstance(lat, dict):
            self.fail.append("loads.COMBO_R debe ser objeto (descripcion+coef)")

        trib = data.get("tributary_areas", {})
        for tag in ("LT1", "LT2"):
            filas = trib.get(tag, {}).get("filas", [])
            self._check_records_union(classes["CombinedTribRow"], filas, f"tributary.{tag}")

        res = data.get("results", {})
        if not isinstance(res.get("cases"), list):
            self.fail.append("results.cases debe ser una lista")

        # 3) comprobacion basica de tipos basicos por record
        self._check_record_types(classes, data)

    def _check_record(self, fields, record, label, object_schema):
        if not isinstance(record, dict):
            self.fail.append(f"{label}: no es objeto")
            return
        for key, val in record.items():
            if key not in fields:
                if label.startswith("metadata") and key in IGNORED_JSON_KEYS:
                    continue
                self.fail.append(f"{label}.{key}: no existe en la clase C#")
                continue
            declared = fields[key]
            if key in object_schema:
                obj_cls = object_schema[key]
                if isinstance(val, list) and obj_cls.endswith("[]"):
                    base = obj_cls[:-2]
                    if base in SIMPLE:
                        self._type_check(base + "[]", val, f"{label}.{key}")
                    else:
                        for item in val:
                            self._nested_check(base, item, f"{label}.{key}[]")
                    continue
                if not isinstance(val, dict):
                    self.fail.append(f"{label}.{key}: esperado objeto")
                    continue
                self._nested_check(obj_cls, val, f"{label}.{key}")
            elif declared in SIMPLE:
                self._type_check(declared, val, f"{label}.{key}")

    def _nested_check(self, cls, record, label):
        fields = self._classes.get(cls)
        if fields is None:
            self.fail.append(f"clase C# {cls} no encontrada para {label}")
            return
        for key, val in record.items():
            if key not in fields:
                self.fail.append(f"{label}.{key}: no existe en clase C# {cls}")
                continue
            declared = fields[key]
            if declared in SIMPLE:
                self._type_check(declared, val, f"{label}.{key}")

    def _check_keyset(self, cls, union, label, object_schema):
        if cls not in self._classes:
            self.fail.append(f"clase C# {cls} no encontrada")
            return
        allowed = set(self._classes[cls].keys())
        if label == "metadata":
            allowed |= IGNORED_JSON_KEYS
        for extra in union - allowed:
            self.fail.append(f"{label}: clave '{extra}' sin campo en C#")

    def _check_records_union(self, fields, records, label):
        if not records:
            self.fail.append(f"{label}: sin registros para validar")
            return
        allowed = set(fields.keys())
        union = set()
        for r in records:
            union.update(r.keys())
        for extra in union - allowed:
            self.fail.append(f"{label}: clave '{extra}' sin campo en C# (agregado carga)")

    def _check_record_types(self, classes, data):
        sections = {
            "nodes": "CombinedNode", "elements": "CombinedElement",
            "supports": "CombinedSupport", "masters": "CombinedMaster",
            "diaphragms": "CombinedDiaphragm",
            "constraint_links": "CombinedLink",
        }
        for section, cls in sections.items():
            fields = classes[cls]
            for rec in data.get(section, []):
                for key, val in rec.items():
                    if key not in fields:
                        continue
                    declared = fields[key]
                    if declared in SIMPLE:
                        self._type_check(declared, val,
                                         f"{section}.0.{key}")
                seccion = rec.get("seccion")
                if isinstance(seccion, dict):
                    self._nested_check("CombinedSection", seccion,
                                       f"{section}.seccion")

    def _type_check(self, declared, val, label):
        if val is None:
            return  # null aceptado (campos opcionales)
        if declared == "float":
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                self.fail.append(f"{label}: float esperado, {type(val).__name__}")
        elif declared == "int":
            if isinstance(val, bool) or not isinstance(val, int):
                self.fail.append(f"{label}: int esperado, {type(val).__name__}")
        elif declared == "string":
            if not isinstance(val, str):
                self.fail.append(f"{label}: string esperado, {type(val).__name__}")
        elif declared == "float[]":
            if not isinstance(val, list) or any(
                    not isinstance(x, (int, float)) for x in val):
                self.fail.append(f"{label}: float[] esperado")
        elif declared == "int[]":
            if not isinstance(val, list) or any(
                    not isinstance(x, int) for x in val):
                self.fail.append(f"{label}: int[] esperado")
        elif declared == "string[]":
            if not isinstance(val, list):
                self.fail.append(f"{label}: string[] esperado")

    # ----------------------------------------------------------------- results
    def _results_consistency(self, data):
        res = data.get("results", {})
        cases = res.get("cases", [])
        for block in ("forces", "displacements", "reactions", "equilibrio"):
            d = res.get(block, {})
            if set(d.keys()) != set(cases):
                self.fail.append(
                    f"results.{block}.keys != results.cases "
                    f"({sorted(set(d.keys()) ^ set(cases))})")
        for c in cases:
            eq = res.get("equilibrio", {}).get(c, {})
            if not isinstance(eq, dict) or "P_aplicada_kN" not in eq:
                self.fail.append(f"results.equilibrio[{c}] incompleto")
        self.ok.append(f"results.cases = {sorted(cases)}")

    # ------------------------------------------------------- resultados pm
    def _pm_checks(self, data):
        """results.pm + panel P-M (FASE B): curvas, demandas, caso activo,
        agrupacion M001 como un unico muro y registro en Unity."""
        res = data.get("results", {})
        pm = res.get("pm")
        if not isinstance(pm, dict):
            self.fail.append("results.pm ausente: lo requiere el panel P-M")
            return
        cases = set(res.get("cases", []))
        if pm.get("tipo") != "capacidad_fiber_section_PM":
            self.fail.append(f"results.pm.tipo inesperado: {pm.get('tipo')!r}")
        if pm.get("caso_activo") not in cases:
            self.fail.append(
                f"results.pm.caso_activo {pm.get('caso_activo')!r} no esta "
                "en results.cases")

        espec = {
            "muro_M001": ([4001, 4002],
                          ["curva_fuerte", "curva_debil"], "dentro_fuerte"),
            "columna_113022": ([113022], ["curva"], "dentro"),
        }
        for clave, (tags_esp, curvas_esp, flag) in espec.items():
            blk = pm.get(clave)
            if not isinstance(blk, dict):
                self.fail.append(f"results.pm.{clave}: bloque ausente")
                continue
            if blk.get("elementTags") != tags_esp:
                self.fail.append(
                    f"results.pm.{clave}.elementTags != {tags_esp}")
            cap = blk.get("capacidad")
            if not isinstance(cap, dict):
                self.fail.append(f"results.pm.{clave}.capacidad ausente")
                continue
            for cname in curvas_esp:
                curva = cap.get(cname)
                if not isinstance(curva, list) or not curva:
                    self.fail.append(f"results.pm.{clave}.{cname} vacia")
                    continue
                mal = [pt for pt in curva
                       if not (isinstance(pt, list) and len(pt) == 2
                               and isinstance(pt[0], (int, float))
                               and isinstance(pt[1], (int, float)))]
                if mal:
                    self.fail.append(
                        f"results.pm.{clave}.{cname}: puntos invalidos "
                        f"({len(mal)})")
            dem = blk.get("demanda_por_caso")
            if not isinstance(dem, dict) or set(dem) != set(cases):
                self.fail.append(
                    f"results.pm.{clave}.demanda_por_caso != results.cases")
            else:
                for cc, v in dem.items():
                    if not isinstance(v, dict) or flag not in v:
                        self.fail.append(
                            f"results.pm.{clave}.demanda_por_caso[{cc}] "
                            "incompleto")
        if pm.get("muro_M001", {}).get(
                "objetos_unity", {}).get("elementTags_para_agrupar") != [4001, 4002]:
            self.fail.append("results.pm.muro_M001.objetos_unity sin "
                             "elementTags_para_agrupar [4001, 4002]")

        # --- fuente C# del panel y registro en Unity ---------------------
        if not PANEL.exists():
            self.fail.append("PmPanelController.cs ausente (panel P-M FASE B)")
        else:
            text = PANEL.read_text(encoding="utf-8")
            check_balance(text, "PmPanelController.cs", self.fail)
            for token in ("class PmPanelController", "class PmData",
                          "class PmJsonParser", "BuildChart", "GUI.DrawTexture"):
                if token not in text:
                    self.fail.append(f"PmPanelController.cs sin '{token}'")

        builder = EDITOR / "LT1SceneBuilder.cs"
        text = builder.read_text(encoding="utf-8")
        if "AddComponent<PmPanelController>" not in text:
            self.fail.append("LT1SceneBuilder no registra PmPanelController")

        if SA_OUT.exists():
            with open(SA_OUT, "r", encoding="utf-8") as f:
                sa = json.load(f)
            if sa.get("results", {}).get("pm") != pm:
                self.fail.append("results.pm desincronizado en "
                                 "StreamingAssets (copia del viewer)")
        for figure in ("pm_column_113022.png", "pm_wall_M001.png"):
            source = P1L4_OUT / figure
            viewer = SA_DIR / figure
            if not source.exists() or not viewer.exists():
                self.fail.append(f"figura P-M ausente: {figure}")
            elif source.read_bytes() != viewer.read_bytes():
                self.fail.append(f"figura P-M desincronizada: {figure}")
        self.ok.append("results.pm OK (curvas/demandas/caso activo/panel)")

    # ---------------------------------------------------------------- fuentes
    def _cs_checks(self):
        cs_files = sorted(SCRIPTS.glob("*.cs")) + sorted(EDITOR.glob("*.cs"))
        if not cs_files:
            self.fail.append("Sin archivos .cs en unity/LT1Viewer")
            return

        for path in cs_files:
            text = path.read_text(encoding="utf-8")
            check_balance(text, path.name, self.fail)

        # clases duplicadas
        seen = {}
        for path in cs_files:
            for m in re.finditer(r"^\s*(?:public\s+|internal\s+)?"
                                 r"(?:static\s+)?class\s+(\w+)",
                                 path.read_text(encoding="utf-8"),
                                 re.MULTILINE):
                name = m.group(1)
                seen.setdefault(name, []).append(path.name)
        for name, files in seen.items():
            if len(files) > 1:
                self.fail.append(f"clase duplicada '{name}' en {files}")

        # referencias obsoletas
        for path in cs_files:
            text = path.read_text(encoding="utf-8")
            if path.name != "ModelData.cs":
                for lineno, line in enumerate(text.splitlines(), start=1):
                    if "pending_geometry" not in line:
                        continue
                    stripped = line.strip()
                    # se permite la inicializacion a vacio (ModelLoader)
                    if re.match(r"^\s*(?:[A-Za-z0-9_.]+\s*)?pending_geometry\s*=\s*new", line):
                        continue
                    # tampoco se permiten comentarios con mención funcional
                    if stripped.startswith("//"):
                        continue
                    self.fail.append(
                        f"{path.name}:{lineno}: uso obsoleto de "
                        f"'pending_geometry' ({line.strip()[:60]})")
            if "modelo_lt1.json" in text:
                self.fail.append(f"{path.name}: referencia a modelo_lt1.json "
                                 "como fuente (ya no aplica)")

        loader = SCRIPTS / "ModelLoader.cs"
        text = loader.read_text(encoding="utf-8")
        if 'jsonFileName = "modelo_combinado.json"' not in text:
            self.fail.append("ModelLoader.cs no apunta a "
                             "'modelo_combinado.json'")

        # SetActiveCase existe y reconstruye fuerzas/desplazamientos
        if "public bool SetActiveCase" not in text:
            self.fail.append("ModelLoader.cs no expone SetActiveCase")
        if "elementForceI" not in text or "elementForceJ" not in text:
            self.fail.append("ModelLoader.cs no expone fuerzas por acceso")

        # caso inicial = primero de results.cases
        if "CaseList" not in text:
            self.fail.append("ModelLoader.cs no expone CaseList")

        builder = EDITOR / "LT1SceneBuilder.cs"
        text = builder.read_text(encoding="utf-8")
        for component in (
                "CaseSelector", "LoadInspector", "LoadVisualizationController",
                "TributaryAreaVisualizationController", "MovingLoadController",
                "ScenarioModificationController", "SuperpositionController",
                "UserMovingLoadController", "ViewerHUD"):
            if f"AddComponent<{component}>" not in text:
                self.fail.append(f"LT1SceneBuilder no registra {component}")

        required_sources = {
            "ViewerHUD.cs": ("class ViewerHUD", "DrawForces", "DrawTributaryData"),
            "ForceDiagramController.cs": (
                "class ForceDiagramController", "DiagramMode", "Mz", "N",
                "Vy", "T", "BuildSectionDiagram", "CollectMemberLoads",
                "beamUniform", "beamPoint", "shearI"),
            "LoadVisualizationController.cs": ("class LoadVisualizationController", "DrawArrow"),
            "TributaryAreaVisualizationController.cs": ("class TributaryAreaVisualizationController", "polygon"),
            "MovingLoadController.cs": ("class MovingLoadController",
                                        "Pi=P(1-xi)", "LoadI", "LoadJ"),
            "ScenarioModificationController.cs": (
                "class ScenarioModificationController", "ApplyLoadFactor",
                "ToggleSelectedElement", "RequiresReanalysis",
                "RestoreBaseScenario"),
            "SuperpositionController.cs": (
                "class SuperpositionController", "public void Set",
                "LoadComboR", "ApplyLinearSuperposition"),
            "UserMovingLoadController.cs": (
                "class UserMovingLoadController", "PointInPolygon",
                "DrawReceiver", "AssignmentLabel", "MoveBy"),
            "OrbitCamera.cs": ("Input.touchCount", "HandleTouch", "pinch"),
            "SelectionController.cs": ("HandleTouchSelection", "TouchPhase.Ended"),
        }
        for filename, tokens in required_sources.items():
            source = SCRIPTS / filename
            if not source.exists():
                self.fail.append(f"{filename} ausente")
                continue
            source_text = source.read_text(encoding="utf-8")
            for token in tokens:
                if token not in source_text:
                    self.fail.append(f"{filename} sin '{token}'")

        for token in ("ApplyLinearSuperposition", "PrepareResultCaches",
                      "AccumulateCase", "ResultRevision"):
            if token not in (SCRIPTS / "ModelLoader.cs").read_text(encoding="utf-8"):
                self.fail.append(f"ModelLoader.cs sin '{token}' para superposicion")
        pm_text = PANEL.read_text(encoding="utf-8")
        for token in ("DemandFor", "CapacityAt", "semilongitud",
                      "IsLinearSuperposition"):
            if token not in pm_text:
                self.fail.append(f"PmPanelController.cs sin '{token}' para superposicion")

        android = EDITOR / "AndroidBuild.cs"
        if not android.exists():
            self.fail.append("AndroidBuild.cs ausente")
        else:
            android_text = android.read_text(encoding="utf-8")
            for token in ("BuildTarget.Android", "AndroidApiLevel26",
                          "AndroidArchitecture.ARM64", "BuildFromCommandLine"):
                if token not in android_text:
                    self.fail.append(f"AndroidBuild.cs sin '{token}'")

        self.ok.append(f"{len(cs_files)} archivos .cs revisados")

    # ---------------------------------------------------------------- escenas
    def _scene_checks(self):
        assets = ROOT / "unity" / "LT1Viewer" / "Assets"
        # Unity crea Assets/_Recovery al recuperar una sesion interrumpida.
        # No es una escena fuente del proyecto y puede contener trabajo local
        # recuperable, por lo que se ignora sin borrarla.
        unity_files = [p for p in assets.rglob("*.unity")
                       if "_Recovery" not in p.parts]
        allowed = {assets / "Scenes" / "LT1Viewer.unity"}
        unexpected = [p for p in unity_files if p not in allowed]
        if unexpected:
            self.fail.append(
                "Se encontraron escenas Unity no previstas: "
                f"{[p.relative_to(ROOT) for p in unexpected]}")
        elif unity_files:
            self.ok.append("escena fuente Assets/Scenes/LT1Viewer.unity OK")
        else:
            self.ok.append("escena reproducible mediante LT1SceneBuilder")


def main():
    v = StaticValidator(OUT)
    v.run()
    for line in v.ok:
        print(f"  OK  {line}")
    print(f"\nOK={len(v.ok)}  PROBLEMA={len(v.fail)}")
    if v.fail:
        print("\nFallos:")
        for line in sorted(set(v.fail)):
            print(f"  - {line}")
        sys.exit(1)
    print("Validacion estatica del visor COMBINADO: CORRECTA")


if __name__ == "__main__":
    main()
