import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ruta_json = os.path.join("outputs", "unity", "modelo_lt1.json")
with open(ruta_json, "r", encoding="utf-8") as f:
    data = json.load(f)

problemas = []
advertencias = []
ok_items = []

nodes = data.get("nodes", [])
beams = data.get("beams", [])
columns = data.get("columns", [])
supports = data.get("supports", [])
diaphragms = data.get("diaphragms", [])
walls = data.get("walls", [])
constraints = data.get("constraint_links", [])
analysis = data.get("analysis", {})
trib = data.get("tributary_areas", [])
panos = data.get("panos", [])
meta = data.get("metadata", {})
capacidades = data.get("capacidades", [])

n_struct = [n for n in nodes if n.get("tipo") == "structural"]
n_masters = [n for n in nodes if n.get("tipo") == "master"]


def chk(cond, msg, ok_msg=None):
    if cond:
        ok_items.append(ok_msg or msg)
    else:
        problemas.append(msg)


def warn(cond, msg):
    if cond:
        advertencias.append(msg)


# --- Estructura base (P1L2/P1L3) -------------------------------------------
n_est = len(n_struct)
n_mas = len(n_masters)
chk(n_est == 144, f"nodos estructurales: {n_est} (esperados 144)",
    f"nodos estructurales: {n_est} OK")
chk(n_mas == 4, f"nodos master: {n_mas} (esperados 4)",
    f"nodos master: {n_mas} OK")
chk(len(nodes) == 148, f"nodos totales: {len(nodes)} (esperados 148)",
    f"nodos totales: {len(nodes)} OK")
chk(len(beams) == 108, f"vigas: {len(beams)} (esperadas 108)",
    f"vigas: {len(beams)} OK")
chk(len(columns) == 90, f"columnas: {len(columns)} (esperadas 90)",
    f"columnas: {len(columns)} OK")
chk(len(supports) == 24, f"apoyos: {len(supports)} (esperados 24)",
    f"apoyos: {len(supports)} OK")
chk(len(diaphragms) == 4, f"diafragmas: {len(diaphragms)} (esperados 4)",
    f"diafragmas: {len(diaphragms)} OK")
chk(len(walls) == 30, f"muros: {len(walls)} (esperados 30)",
    f"muros: {len(walls)} OK")
chk(len(constraints) == 24, f"constraint_links: {len(constraints)} (esperados 24)",
    f"constraint_links: {len(constraints)} OK")

beam_tags = [b["elementTag"] for b in beams]
col_tags = [c["elementTag"] for c in columns]
wall_tags = [w["elementTag"] for w in walls]
all_elem_tags = beam_tags + col_tags + wall_tags
chk(len(all_elem_tags) == 228, f"total elementos: {len(all_elem_tags)} (esperados 228)")
chk(len(set(all_elem_tags)) == 228,
    f"elementTags duplicados: {len(all_elem_tags) - len(set(all_elem_tags))}")

node_tags = [n["tag"] for n in nodes]
chk(len(set(node_tags)) == len(node_tags),
    f"nodeTags duplicados: {len(node_tags) - len(set(node_tags))}")

nan_inf_geom = False
for n in nodes:
    for coord in ["x", "y", "z"]:
        v = n.get(coord)
        if v is None or (isinstance(v, float) and not math.isfinite(v)):
            nan_inf_geom = True
            problemas.append(f"nodo {n['tag']}: {coord}={v} no finito")
chk(not nan_inf_geom, "coordenadas no finitas encontradas")

chk(all(100000 <= t < 200000 for t in col_tags),
    "column tags fuera de rango 100xxx",
    "column tags en rango 100xxx OK")
chk(all(200000 <= t < 300000 for t in beam_tags),
    "beam tags fuera de rango 200xxx",
    "beam tags en rango 200xxx OK")

chk(trib is not None, "tributary_areas ausente")
warn(len(trib) != 108, f"tributarias: {len(trib)} (esperadas 108)")

chk(meta.get("unidades") is not None, "metadata.unidades ausente",
    "metadata.unidades OK")
chk(meta.get("material"), "metadata.material ausente",
    "metadata.material OK")
chk(meta.get("limitaciones"), "metadata.limitations ausente",
    "metadata.limitaciones OK")

if analysis.get("estado") == "OK_COMPLETADO":
    chk(True, "", "analisis OK_COMPLETADO")
    p_aplicada = analysis.get("P_aplicada_kN", 0)
    chk(abs(p_aplicada - 19644.1) < 100,
        f"P aplicada: {p_aplicada} (esperado ~19644)")
    chk(analysis.get("err_rel", 1) < 1e-6,
        f"error equilibrio: {analysis.get('err_rel')}")
    chk(not analysis.get("nan_inf"), "NaN/Inf encontrado en resultados de analisis")
    chk(analysis.get("diafragmas_compatibles"), "diafragmas rigidos incompatibles")
else:
    problemas.append(f"analisis: {analysis.get('estado')}")

# --- P1L4: postproceso conectado a resultados ------------------------------
chk(analysis.get("caso"), "analysis.caso ausente", f"caso activo: {analysis.get('caso')} OK")
fe = analysis.get("fuerzas_elementos", [])
chk(len(fe) == 228, f"fuerzas_elementos: {len(fe)} (esperados 228)",
    f"fuerzas_elementos: {len(fe)} OK")

fe_tags = set()
fe_bad = []
for e in fe:
    fe_tags.add(e["elementTag"])
    if "F_i" not in e or "F_j" not in e:
        fe_bad.append((e["elementTag"], "sin F_i/F_j"))
        continue
    for fn, f in (("F_i", e["F_i"]), ("F_j", e["F_j"])):
        if len(f) != 6:
            fe_bad.append((e["elementTag"], f"{fn} len={len(f)}"))
        for v in f:
            if not math.isfinite(v):
                fe_bad.append((e["elementTag"], f"{fn} no finito"))
chk(not fe_bad, f"fuerzas_elementos invalidas: {fe_bad[:5]}",
    "fuerzas_elementos: 6 comp por extremo y finitas OK")

chk(fe_tags == set(all_elem_tags),
    f"tags de fuerzas no coinciden con geometria ({len(all_elem_tags) - len(fe_tags & set(all_elem_tags))} faltan)")

# nodos consistentes entre fuerzas y elementos
fe_node_mismatch = 0
for e in fe:
    node_i, node_j = e.get("node_i"), e.get("node_j")
    en = [b for b in beams + columns + walls if b["elementTag"] == e["elementTag"]]
    if not en:
        fe_node_mismatch += 1
    else:
        d = en[0]
        if d["node_i"] != node_i or d["node_j"] != node_j:
            fe_node_mismatch += 1
chk(fe_node_mismatch == 0, f"nodos de fuerzas inconsistentes: {fe_node_mismatch}",
    "fuerzas_elementos: nodo_i/j consistentes con beams/columns/walls OK")

chk(len(capacidades) >= 2, f"capacidades: {len(capacidades)} (esperadas >=2)",
    f"capacidades: {len(capacidades)} OK")

def _cap(tipo):
    for c in capacidades:
        if c.get("elemento_tipo") == tipo:
            return c
    return None

# P1L4 demanda-capacidad: NO se admite curva P-M basada en SUPUESTOS.
# (La Parte D de Semana 3 resolvio la columna 111000 con f'c=30/fy=420/4 cm/
# distribucion SUPUESTOS; esa curva no es dato del proyecto y NO se exporta.)
col_cap = _cap("columna")
muro_cap = _cap("muro")
chk(col_cap is not None and col_cap.get("elementTag") == 111000,
    "capacidad columna 111000 ausente", "capacidad columna tag 111000 OK")
if col_cap:
    chk(col_cap.get("estado") == "NO_DISPONIBLE",
        "columna 111000: estado != NO_DISPONIBLE (curva bajo SUPUESTOS no es "
        "dato del proyecto)",
        "columna 111000: NO_DISPONIBLE (sin curva SUPUESTA) OK")
    chk(not col_cap.get("curva_pm"),
        "columna 111000: curva_pm presente sin datos resistentes del proyecto",
        "columna 111000: curva_pm vacia (faltan f'c/fy/recubrimiento) OK")
    dem = col_cap.get("demanda") or {}
    chk(dem and isinstance(dem.get("N_kN"), (int, float)) and
        isinstance(dem.get("M_kN_m"), (int, float)),
        "demanda modelo columna ausente/invalida",
        f"demanda columna 111000 (modelo, informativa): N={dem.get('N_kN')} kN, "
        f"M={dem.get('M_kN_m')} kN·m OK")
    chk(dem.get("N_kN", 0) < 0,
        f"demanda columna con N>0 (convencion compresion<0): {dem.get('N_kN')}",
        "demanda columna compresion < 0 OK")
    chk(bool(col_cap.get("faltantes")),
        "columna 111000: NO_DISPONIBLE sin faltantes",
        "columna 111000: faltantes listados OK")
chk(muro_cap is not None and muro_cap.get("estado") == "NO_DISPONIBLE"
    and muro_cap.get("faltantes")
    and muro_cap.get("elementTag") == 400001,
    "capacidad muro NO_DISPONIBLE mal declarada",
    "capacidad muro: NO_DISPONIBLE con faltantes OK")
if muro_cap:
    chk(not muro_cap.get("curva_pm"),
        "muro con curva_pm sin datos legibles",
        "muro 400001: curva_pm vacia (armadura no legible + sin f'c/fy) OK")

# No NaN/Inf en capacidades ni fuerzas
nan_cap = [math.isnan(x) or math.isinf(x)
           for c in capacidades
           for p in c.get("curva_pm", [])
           for x in (p.get("P_kN"), p.get("M_kN_m"))]
chk(not any(nan_cap), "NaN/Inf en curva P-M")

os.makedirs("outputs", exist_ok=True)
ruta_ctrl = os.path.join("outputs", "control_unity_lt1.txt")
with open(ruta_ctrl, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("CONTROL UNITY LT1 · VALIDACION JSON + P1L4 POSTPROCESO\n")
    f.write("=" * 80 + "\n\n")
    f.write("1. ENTORNO UNITY\n")
    f.write("   Unity: NO instalado en esta maquina\n")
    f.write("   Proyecto preparado en: unity/LT1Viewer/\n")
    f.write("   El usuario debe abrir con Unity Hub (2022.3 LTS)\n\n")
    f.write("2. JSON EXPORTADO\n")
    f.write(f"   ruta: {os.path.abspath(ruta_json)}\n")
    f.write(f"   tamano: {os.path.getsize(ruta_json)} bytes\n\n")
    f.write("3. VALIDACIONES\n")
    for item in ok_items:
        f.write(f"   [OK] {item}\n")
    for item in problemas:
        f.write(f"   [PROBLEMA] {item}\n")
    for item in advertencias:
        f.write(f"   [AVISO] {item}\n")
    f.write(f"\n   total OK: {len(ok_items)} | problemas: {len(problemas)} | "
            f"avisos: {len(advertencias)}\n\n")
    f.write("4. P1L4 · RESULTADOS DISPONIBLES\n")
    f.write(f"   caso activo: {analysis.get('caso', 'N/D')} | "
            f"escenarios: {analysis.get('escenarios')}\n")
    f.write(f"   fuerzas por elemento: {len(fe)} de 228\n")
    f.write(f"   demandas exportadas: {len(capacidades)} capacidades\n")
    for c in capacidades:
        d = c.get("demanda") or {}
        f.write(f"   - {c.get('elemento_tipo')} tag {c.get('elementTag')}: "
                f"estado={c.get('estado')} | demanda N={d.get('N_kN')} kN, "
                f"M={d.get('M_kN_m')} kN·m ({d.get('caso')})\n")
    f.write(f"\n   convencion fuerzas: {analysis.get('convencion_fuerzas', 'N/D')}\n")
    f.write("\n5. SCRIPTS C# (unity/LT1Viewer/Assets/Scripts)\n")
    scripts_dir = os.path.join("unity", "LT1Viewer", "Assets", "Scripts")
    if os.path.isdir(scripts_dir):
        for fname in sorted(os.listdir(scripts_dir)):
            fpath = os.path.join(scripts_dir, fname)
            sz = os.path.getsize(fpath)
            f.write(f"   {fname:<30s} {sz:>6d} bytes\n")
    f.write("\n   Responsabilidades P1L4:\n")
    f.write("   - ModelData.cs: clases de resultados (fuerzas_elementos, capacidades)\n")
    f.write("   - StructuralResultsController.cs: panel seleccion con N/V/T/M + P-M\n")
    f.write("   - DeformedShapeController.cs: deformada (tecla D, escala +/-)\n")
    f.write("   - ForceDiagramController.cs: diagramas momento/axial/corte (tecla M)\n\n")
    f.write("6. PASOS MANUALES DEL USUARIO\n")
    f.write("   a) Regenerar JSON: python3 src/modelo_lt1.py  (copia a StreamingAssets)\n")
    f.write("   b) Abrir unity/LT1Viewer/ con Unity 2022.3 LTS\n")
    f.write("   c) Menu LT1 > Build LT1Viewer Scene y Play\n")
    f.write("   d) Click sobre viga/columna/muro ver resultados; D deformada; M diagramas\n\n")
    f.write("=" * 80 + "\n")
print(f"  [OK] control unity: {ruta_ctrl}")
print(f"  validaciones P1L4: OK={len(ok_items)} PROBLEMA={len(problemas)} "
      f"AVISO={len(advertencias)}")
if problemas:
    print("  PROBLEMAS:")
    for p in problemas:
        print("   -", p)
    sys.exit(1)
