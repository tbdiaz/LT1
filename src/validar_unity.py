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
analysis = data.get("analysis", {})
trib = data.get("tributary_areas", [])
panos = data.get("panos", [])
meta = data.get("metadata", {})

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

chk(len(n_struct) == 108, f"nodos estructurales: {len(n_struct)} (esperados 108)", f"nodos estructurales: {len(n_struct)} OK")
chk(len(n_masters) == 4, f"nodos master: {len(n_masters)} (esperados 4)", f"nodos master: {len(n_masters)} OK")
chk(len(nodes) == 112, f"nodos totales: {len(nodes)} (esperados 112)", f"nodos totales: {len(nodes)} OK")
chk(len(beams) == 108, f"vigas: {len(beams)} (esperadas 108)", f"vigas: {len(beams)} OK")
chk(len(columns) == 90, f"columnas: {len(columns)} (esperadas 90)", f"columnas: {len(columns)} OK")
chk(len(supports) == 18, f"apoyos: {len(supports)} (esperados 18)", f"apoyos: {len(supports)} OK")
chk(len(diaphragms) == 4, f"diafragmas: {len(diaphragms)} (esperados 4)", f"diafragmas: {len(diaphragms)} OK")
chk(len(walls) == 0, f"muros: {len(walls)} (esperados 0 - pendientes)", f"muros: 0 (correcto, pendientes)")

beam_tags = [b["elementTag"] for b in beams]
col_tags = [c["elementTag"] for c in columns]
all_elem_tags = beam_tags + col_tags
chk(len(all_elem_tags) == 198, f"total elementos: {len(all_elem_tags)} (esperados 198)")
chk(len(set(all_elem_tags)) == 198, f"elementTags duplicados: {len(all_elem_tags) - len(set(all_elem_tags))}")

node_tags = [n["tag"] for n in nodes]
chk(len(set(node_tags)) == len(node_tags), f"nodeTags duplicados: {len(node_tags) - len(set(node_tags))}")

nan_inf = False
for n in nodes:
    for coord in ["x", "y", "z"]:
        v = n.get(coord)
        if v is None or (isinstance(v, float) and not math.isfinite(v)):
            nan_inf = True
            problemas.append(f"nodo {n['tag']}: {coord}={v} no finito")
chk(not nan_inf, "coordenadas no finitas encontradas")

chk(all(100000 <= t < 200000 for t in col_tags),
    f"column tags fuera de rango 100xxx", "column tags en rango 100xxx OK")
chk(all(200000 <= t < 300000 for t in beam_tags),
    f"beam tags fuera de rango 200xxx", "beam tags en rango 200xxx OK")

chk(trib is not None, "tributary_areas ausente")
warn(len(trib) != 108, f"tributarias: {len(trib)} (esperadas 108)")

chk(meta.get("unidades") is not None, "metadata.unidades ausente", "metadata.unidades OK")
chk(meta.get("sistema_coordenadas"), "metadata.coordinate system ausente", "metadata.sistema_coordenadas OK")
chk(meta.get("material"), "metadata.material ausente", "metadata.material OK")
chk(meta.get("limitaciones"), "metadata.limitations ausente", "metadata.limitaciones OK")

if analysis.get("estado") == "OK_COMPLETADO":
    chk(True, "", "analisis OK_COMPLETADO")
    chk(analysis.get("P_aplicada_kN", 0) > 20000, f"P aplicada: {analysis.get('P_aplicada_kN')} (esperado ~20182)")
    chk(analysis.get("err_rel", 1) < 1e-6, f"error equilibrio: {analysis.get('err_rel')}")
    chk(not analysis.get("nan_inf"), "NaN/Inf encontrado en resultados de analisis")
    chk(analysis.get("diafragmas_compatibles"), "diafragmas rígidos incompatibles")
else:
    problemas.append(f"analisis: {analysis.get('estado')}")

os.makedirs("outputs", exist_ok=True)
ruta_ctrl = os.path.join("outputs", "control_unity_lt1.txt")
with open(ruta_ctrl, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("CONTROL UNITY LT1 · VALIDACION JSON + ESTRUCTURA PROYECTO\n")
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
    f.write(f"\n   total OK: {len(ok_items)} | problemas: {len(problemas)} | avisos: {len(advertencias)}\n\n")
    f.write("4. ESTRUCTURA PROYECTO\n")
    for root, dirs, files in os.walk("unity/LT1Viewer"):
        depth = root.replace("unity/LT1Viewer", "").count(os.sep)
        indent = "   " + "  " * depth
        f.write(f"{indent}{os.path.basename(root)}/\n")
        for fname in sorted(files):
            f.write(f"{indent}  {fname}\n")
    f.write("\n5. SCRIPTS C#\n")
    scripts_dir = os.path.join("unity", "LT1Viewer", "Assets", "Scripts")
    if os.path.isdir(scripts_dir):
        for fname in sorted(os.listdir(scripts_dir)):
            fpath = os.path.join(scripts_dir, fname)
            sz = os.path.getsize(fpath)
            f.write(f"   {fname:<30s} {sz:>6d} bytes\n")
    f.write("\n   Responsabilidades:\n")
    f.write("   - ModelData.cs: clases de datos [Serializable] mapeadas al JSON\n")
    f.write("   - ModelLoader.cs: carga modelo_lt1.json, construye escena (nodos/vigas/columnas/apoyos/diafragmas)\n")
    f.write("   - StructuralViewer.cs: orquestador principal + paneles informativos\n")
    f.write("   - OrbitCamera.cs: orbitar/zoom/pan/reset\n")
    f.write("   - VisibilityController.cs: toggles 1-6 (Nodes/Beams/Columns/Walls/Supports/Diaphragms)\n")
    f.write("   - IdLabelController.cs: IDs de nodos (N) y elementos (E)\n")
    f.write("   - LocalAxesController.cs: ejes locales (A)\n")
    f.write("   - SelectionController.cs: seleccion por raycast + info basica\n")
    f.write("   - TributaryAreaInspector.cs: panel area tributaria al seleccionar viga\n\n")
    f.write("\n6. PASOS MANUALES DEL USUARIO\n")
    f.write("   a) Instalar Unity 2022.3 LTS via Unity Hub\n")
    f.write("   b) Abrir proyecto: unity/LT1Viewer/\n")
    f.write("   c) Crear escena: Assets/Scenes/LT1Viewer.unity\n")
    f.write("   d) Crear GameObject vacio 'LT1Viewer'\n")
    f.write("   e) Agregar componente StructuralViewer.cs\n")
    f.write("   f) Presionar Play\n")
    f.write("   g) Verificar en Console: 'LT1 Viewer - 112 nodes...'\n\n")
    f.write("=" * 80 + "\n")
print(f"  [OK] control unity: {ruta_ctrl}")
print(f"  validaciones: OK={len(ok_items)} PROBLEMA={len(problemas)} AVISO={len(advertencias)}")
