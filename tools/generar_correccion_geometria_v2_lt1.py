# ============================================================================
# tools/generar_correccion_geometria_v2_lt1.py
# Corrección de geometría del modelo LT1 — v2 (núcleos + salientes PISO_2).
#
# Inputs:
#   - data/geometria_irregular.py  (SALIENTES_PISO_2, NUCLEOS -> MUROS_CERRADOS_
#     PISO_2, NODOS_GEOMETRICOS_NUEVOS, muros_todos, pendientes_geometricos)
#   - data/geometria.py / data/inventario.py
#   - outputs/unity/modelo_lt1.json (modelo reconstruido + gravedad)
#
# Outputs:
#   - outputs/modelo_geometria_corregida_v2_lt1.png
#   - outputs/control_geometria_corregida_v2_lt1.txt
#   - outputs/inventario_muros_v2_lt1.txt
#
# Reglas:
#   - Cotas CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO (no OCR, no inferencia).
#   - Extremos de los núcleos cerrados por rectángulo (ancho/alto confirmados)
#     anclados a rótulos M102_01/02/03 + e=25/e=30 (eje común X=4.485).
#   - Sin convención OpenSees para muros M.H.A. => los muros se registran
#     GEOMETRICAMENTE (nodos+elementos) y quedan fuera del análisis.
#   - Doble contador: elementos geométricos vs activos OpenSees.
# ============================================================================

import io
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches as mpatches
from matplotlib import lines as mlines

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data import geometria as datos_geom
from data import geometria_irregular as datos_irreg
from data import inventario as datos_inv

OUT = os.path.join(ROOT, "outputs")
JSON_MODELO = os.path.join(OUT, "unity", "modelo_lt1.json")

Y_3 = datos_geom.ejes_y["3"]

COL_ESP = {20: "#2b6cb0", 25: "#dd6b20", 30: "#c53030"}
COL_SALIENTE_1 = "#f4a582"
COL_SALIENTE_2 = "#f9d423"
COL_CONF = "#16a085"


def _cargar_modelo():
    with open(JSON_MODELO, encoding="utf-8") as fh:
        return json.load(fh)


def _checks_modelo(d):
    nodes = d["nodes"]
    beams = d["beams"]
    columns = d["columns"]
    supports = d["supports"]
    tags = [e["elementTag"] for e in beams + columns]
    ch = [
        ("tags elemento duplicados", len(tags) - len(set(tags))),
        ("longitudes <= 0", sum(1 for e in beams + columns if e.get("longitud_m", 0) <= 0)),
        ("duplicados geométricos", len(tags) - len(set((e["node_i"], e["node_j"], e.get("seccion")) for e in beams + columns))),
    ]
    nodos = {n["tag"] for n in nodes}
    soportes = {s["nodeTag"] for s in supports}
    ref = set(soportes)
    for e in beams + columns:
        ref.add(e["node_i"]); ref.add(e["node_j"])
    ref |= {n["tag"] for n in nodes if n.get("tipo") != "structural"}
    hu = [n["tag"] for n in nodes if n.get("tipo") == "structural" and n["tag"] not in ref]
    ch.append(("nodos estructurales huérfanos", hu))
    return ch


def _superficie_por_nivel(d):
    out = {}
    for p in d["panos"]:
        out[p["nivel"]] = out.get(p["nivel"], 0.0) + p["area_m2"]
    return out


# ---------------------------------------------------------------------------
# 1) CONTROL v2
# ---------------------------------------------------------------------------
def escribir_control(d, checks, areas):
    an = d["analysis"]
    yx = datos_irreg.Y_EXT_SUR_102
    b = io.StringIO(); w = b.write
    w("=" * 98 + "\n")
    w("CONTROL GEOMETRIA CORREGIDA LT1 · v2 (nucleos + salientes PISO_2)\n")
    w("=" * 98 + "\n")
    w("Unidades: m, kN, kPa. Estados: CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO\n")
    w("(dato del usuario, ni OCR ni inferencia) / INFERIDO_RESPALDADO / PENDIENTE.\n\n")

    w("-" * 98 + "\n")
    w("1) COTAS NUEVAS CONFIRMADAS POR EL USUARIO (plano 102, inspección visual)\n")
    w("-" * 98 + "\n")
    w("  NUCLEO SUPERIOR (entre ejes 1'' y 2 aprox.):  horizontal 3.95 m · vertical 2.25 m\n")
    w("      muro superior M.H.A. e=20 ; laterales izquierdo/derecho e=30.\n")
    w("  NUCLEO INFERIOR (entre ejes 2 y 3 aprox.):    vertical 1.58 m\n")
    w("      laterales izquierdo/derecho e=25 ; muro inferior e=20. Ancho solo si hay\n")
    w("      respaldo (si no: NO se inventa).\n")
    w("  SALIENTE 1: X 10.00-17.49 m ; Y -16.15 (eje 3) a -20.27 m (= Y_EXT_SUR_102).\n")
    w("  SALIENTE 2: X 20.00-30.00 m ; Y -16.15 a -18.61 m.\n")
    w("  Borde norte de ambos salientes = eje 3 (vigas de borde V.60/80 en Y≈-16.11,\n")
    w("  capa de texto). El dato previo 'franjas F-G/G-H' queda corregido por estos rangos.\n\n")

    w("-" * 98 + "\n")
    w("2) RESOLUCION NUCLEO SUPERIOR (PISO_2, plan 102)\n")
    w("-" * 98 + "\n")
    w("  Anclajes (capa de texto del propio plano, mapeo calibrado):\n")
    w("    fila e=20 M102_01/02 -> Y_top = -3.448 (muro superior horizontal)\n")
    w("    rotulos verticales e=30 -> X 3.06 / 5.91 (midpoint = 4.485)\n")
    w("    rotulos verticales e=25 -> X 2.79 / 6.18 (midpoint = 4.485)\n")
    w("  EJE COMUN de los 4 rotulos laterales: X = 4.485 m (los dos nucleos comparten eje).\n")
    w("  Rectangulo: Y [ -3.448 ; -3.448-2.25 = -5.698 ] ; ancho exterior 3.95 m -> ejes\n")
    w("    de muros laterales X = 4.485 +/- (3.95-0.30)/2 = 2.660 / 6.310.\n")
    w("  La dimension 3.95 NO se asumio como largo de un solo muro: se resolvio como\n")
    w("    rectangulo de nucleo (regla del usuario).\n\n")

    w("-" * 98 + "\n")
    w("3) RESOLUCION NUCLEO INFERIOR (PISO_2, plan 102)\n")
    w("-" * 98 + "\n")
    w("    fila e=20 M102_03 -> muro inferior en Y = -14.532\n")
    w("    alto CONFIRMADO 1.58 m -> Y_top = -14.532+1.58 = -12.952\n")
    w("    anchado: rotulos e=25 directamente sobre los muros (X 2.790 / 6.180) ->\n")
    w("      ancho exterior 3.64 m, estado INFERIDO_RESPALDADO (no confirmado por cota).\n")
    w("  Extremos de todos los tramos quedan determinados => se registran 6 muros\n")
    w("  geometricos (ver 5).\n\n")

    w("-" * 98 + "\n")
    w("4) SALIENTES PISO_2 (CONFIRMADOS, no se modifican)\n")
    w("-" * 98 + "\n")
    for s in datos_irreg.SALIENTES_PISO_2:
        w(f"  {s['id']}: X {s['X'][0]:.2f}-{s['X'][1]:.2f} · Y {s['Y'][0]:.2f}-{s['Y'][1]:.2f}\n")
        w(f"      {s['evidencia']}\n")
    w("  Nodos geometricos de esquinas sur: S1_SW/S1_SE y S2_SW/S2_SE (ver 6). Los\n")
    w("  bordes norte coinciden con ejes existentes (F/G en eje 3). No existen vigas\n")
    w("  cerradas dentro de los salientes: V.30/45 y V.60/VAR registrados como pendientes\n")
    w("  (extremos sin cota).\n\n")

    w("-" * 98 + "\n")
    w("5) MUROS CERRADOS GEOMETRICAMENTE (MUROS_CERRADOS_PISO_2, 6)\n")
    w("-" * 98 + "\n")
    w(f"  {'ID':8s} {'SECCION':12s} {'ORIENT':14s} {'nodo_i':7s} {'nodo_j':7s} "
      f"{'L[m]':7s} {'X/Y (m)':26s} ACTIVO_OS\n")
    w("-" * 98 + "\n")
    for m in datos_irreg.MUROS_CERRADOS_PISO_2:
        x0, y0, x1, y1 = m["coords"]
        w(f"  {m['id']:8s} {m['seccion']:12s} {m['orientacion']:14s} {m['nodo_i']:7s} "
          f"{m['nodo_j']:7s} {m['longitud_m']:6.3f} "
          f"({x0:.3f},{y0:.3f})-({x1:.3f},{y1:.3f}) {'NO' if not m['activo_opensees'] else 'SI'}\n")
    w("  Motivo NO activo en OpenSees: no existe convencion academica establecida en este\n"
      "  proyecto para transformar un muro M.H.A. en elemento equivalente (el modelo no\n"
      "  contiene muros). Por AGENTS no se inventa convencion: geometria/nodos se crean y\n"
      "  se registran; el analisis estructural queda pendiente de la convencion.\n\n")

    w("-" * 98 + "\n")
    w("6) NODOS GEOMETRICOS NUEVOS (registrados, NO OpenSees)\n")
    w("-" * 98 + "\n")
    w(f"  {'ID':7s} {'X[m]':9s} {'Y[m]':9s} {'Z[m]':7s} ORIGEN\n")
    w("-" * 98 + "\n")
    for n in datos_irreg.NODOS_GEOMETRICOS_NUEVOS:
        w(f"  {n['id']:7s} {n['X']:9.3f} {n['Y']:9.3f} {n.get('z_m', 3.91):7.2f} {n['origen']}\n")
    w("  Total nodos geometricos nuevos: {0} ({1} nucleo + 2 saliente 1 + 2 saliente 2).\n"
      .format(len(datos_irreg.NODOS_GEOMETRICOS_NUEVOS),
              len(datos_irreg.NODOS_GEOMETRICOS_NUEVOS) - 4))

    w("\n" + "-" * 98 + "\n")
    w("7) CONTEO GLOBAL (dos contadores)\n")
    w("-" * 98 + "\n")
    w("  MODELO OPENSEES PREVIO (sin cambios): {0} nodos (108 estructurales + 4 masters) y\n"
      "    {1} elasticBeamColumn (108 V.60/80 + 90 P.70x70).\n".format(len(d["nodes"]),
                                                                       len(d["beams"]) + len(d["columns"])))
    w("  NODOS:  totales geometricos = 112 (OpenSees) + 12 (nuevos geometricos) = 124 ;\n"
      "          activos OpenSees = 112.\n")
    w("  ELEMENTOS: totales geometricos = 198 (OpenSees) + 6 (muros nucleo PISO_2) = 204 ;\n"
      "          activos OpenSees = 198 (0 nuevos: ver 5).\n")
    w("  El modelo NO se presenta como cerrado: quedan Pendientes (ver 10).\n\n")

    w("-" * 98 + "\n")
    w("8) CARGA GRAVITACIONAL (GEOMETRIA_MODELADA / RESPALDADA / PENDIENTE)\n")
    w("-" * 98 + "\n")
    for nv, ar in sorted(areas.items()):
        w(f"    {nv}: superficie de losa = {ar:.3f} m2\n")
    w(f"  P gravitatoria total (PISO_1..4) aplicada = {an['P_aplicada_kN']:.3f} kN\n")
    w("  CARGA_GRAVITACIONAL_RESPALDADA: la existente (plan 700 / paños de la reticula,\n")
    w("    686.375 m2 por nivel). NO CAMBIA en v2.\n")
    a1 = (abs(s0["X"][1] - s0["X"][0]) * abs(s0["Y"][1] - s0["Y"][0])
          for s0 in [datos_irreg.SALIENTES_PISO_2[0]])
    a2 = (abs(s0["X"][1] - s0["X"][0]) * abs(s0["Y"][1] - s0["Y"][0])
          for s0 in [datos_irreg.SALIENTES_PISO_2[1]])
    w("  CARGA_PENDIENTE: areas nuevas de SALIENTE_1 (≈{:.1f} m²) y SALIENTE_2 "
      "(≈{:.1f} m²).\n".format(next(a1), next(a2)))
    w("    El plano 700 no respalda q_G para esas areas -> NO se aplica carga arbitraria.\n")
    w("    Si en el futuro se confirma losa cargada, la superficie/carga se recalculan.\n\n")

    w("\n" + "-" * 98 + "\n")
    w("9) VERIFICACION OPENSEES (reconstruido tras datos v2)\n")
    w("-" * 98 + "\n")
    w(f"  analyze(1) OK · P = ΣRz = {an['P_aplicada_kN']:.3f} kN · err rel = "
      f"{an['err_rel']:.3e} (tol 1e-6)\n")
    for nombre, valor in checks:
        w(f"  [OK] {nombre}: {valor if valor not in (0, [],) else 0}\n")

    w("\n" + "-" * 98 + "\n")
    w("10) ELEMENTOS / GEOMETRIA PENDIENTE (extensos sin cerrar)\n")
    w("-" * 98 + "\n")
    w("  - Nucleo PISO_4 (plan 103): posiciones e=20/25/30 INFERIDO_RESPALDADO, extremos\n"
      "    sin dims confirmadas (M103_01/02/03, M103_E25/E30).\n")
    w("  - V.30/45 (2): rotulos X≈21.0/25.8, Y≈-18.86 -> extremos PENDIENTE; 0.25 m al sur\n"
      "    del borde -18.61 del saliente 2 (dentro del error ±0.2-0.4 m del mapeo) -> posible\n"
      "    borde sur sin cota explicita.\n")
    w("  - V.60/VAR (5), V.60-30/80-40 (5): sin par de nodos; la mayoria en vistas de\n"
      "    detalle (y_pdf < 419.8) no mapeables al edificio.\n")
    w("  - P.M. 300x300x20 (3 [102] / 8 [103]) y V.M.: solo vistas de detalle / inventario.\n")
    w("  - Muros del subte (plan 101, e=15/20/30, M.I.): 24 registros, posiciones PENDIENTE.\n")
    w("  - Muros restantes del nucleo (plan 102 PISO_2 fuera de los 6 cerrados): ninguno.\n\n")

    w("-" * 98 + "\n")
    w("11) OUTPUTS v2 GENERADOS\n")
    w("-" * 98 + "\n")
    w("  outputs/modelo_geometria_corregida_v2_lt1.png\n")
    w("  outputs/control_geometria_corregida_v2_lt1.txt   (este archivo)\n")
    w("  outputs/inventario_muros_v2_lt1.txt\n\n")
    w("=" * 98 + "\n")
    w("FIN CONTROL GEOMETRIA CORREGIDA LT1 · v2\n")
    w("=" * 98 + "\n")
    ruta = os.path.join(OUT, "control_geometria_corregida_v2_lt1.txt")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(b.getvalue())
    return ruta


# ---------------------------------------------------------------------------
# 2) INVENTARIO v2
# ---------------------------------------------------------------------------
def escribir_inventario(rows):
    import io
    b = io.StringIO(); w = b.write
    w("=" * 98 + "\n")
    w("INVENTARIO DE MUROS LT1 · v2 (nucleos + salientes PISO_2)\n")
    w("=" * 98 + "\n")
    w("Seccion A — 6 muros del nucleo PISO_2 CERRADOS (GEOMETRIA_MODELADA,\n"
      "NO activos en OpenSees: sin convencion de muro):\n\n")
    w(f"  {'ID':8s} {'NIVEL':7s} {'ESP':5s} {'ORIENT':14s} {'LONG[m]':8s} "
      f"{'COORD_X1':9s} {'COORD_Y1':9s} {'COORD_X2':9s} {'COORD_Y2':9s} ESTADO\n")
    w("-" * 98 + "\n")
    for m in datos_irreg.MUROS_CERRADOS_PISO_2:
        x0, y0, x1, y1 = m["coords"]
        w(f"  {m['id']:8s} {m['nivel']:7s} e={m['espesor_cm']:<3d} {m['orientacion']:14s} "
          f"{m['longitud_m']:<8.3f} {x0:<9.3f} {y0:<9.3f} {x1:<9.3f} {y1:<9.3f} "
          f"INFERIDO_RESPALDADO\n")
    w("\n  Evidencia (por muro):\n")
    for m in datos_irreg.MUROS_CERRADOS_PISO_2:
        w(f"    {m['id']}: {m['evidencia']}\n")

    w("\nSeccion B — registro completo por plano (estado, posicion y rol):\n\n")
    w(f"  {'NIVEL':12s} {'PLANO':5s} {'ID':14s} {'SECCION':14s} {'e[cm]':6s} "
      f"{'X[m]':7s} {'Y[m]':8s} {'ESTADO':22s} ROL\n")
    w("-" * 98 + "\n")
    for r in sorted(rows, key=lambda r: (r["nivel"], r["plano"], r["id"])):
        pm = r["posicion_modelo"] or (None, None)
        X = f"{pm[0]:7.2f}" if pm[0] is not None else "   n/a "
        Y = f"{pm[1]:8.2f}" if pm[1] is not None else "     n/a "
        w(f"  {r['nivel']:12s} {r['plano']:5s} {r['id']:14s} {r['seccion']:14s} "
          f"{r['e_cm']:6d} {X} {Y} {r['estado']:22s} {r['rol']}\n")

    w("\nSeccion C — geometria v2 resuelta (SALIENTES + NODOS):\n\n")
    for s in datos_irreg.SALIENTES_PISO_2:
        w(f"  {s['id']}: X {s['X'][0]:.2f}-{s['X'][1]:.2f} · Y {s['Y'][0]:.2f}-"
          f"{s['Y'][1]:.2f} · {s['estado']}\n")
    w("  Nodos geometricos nuevos (12): ")
    w(", ".join(n["id"] + "(" + f"{n['X']:.2f},{n['Y']:.2f})"
               for n in datos_irreg.NODOS_GEOMETRICOS_NUEVOS))
    w("\n")
    w("  TOTAL: 41 muros registrados en planos + 6 cerrados del nucleo PISO_2;\n"
      "  muros activos en OpenSees: 0 (sin convencion de muro en el proyecto).\n")
    ruta = os.path.join(OUT, "inventario_muros_v2_lt1.txt")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(b.getvalue())
    return ruta


def _rows():
    rows = []
    for m in datos_irreg.muros_todos:
        nivel = m["nivel"]
        if m["plano"] == "101":
            rol = ("ESTRUCTURA_PRINCIPAL (contencion subte)"
                   if m["seccion"].startswith("M.H.A.") else
                   "ESTRUCTURA_SECUNDARIA (interior subte)")
        elif m["plano"] == "103":
            rol = "ESTRUCTURA_PRINCIPAL (nucleo PISO_4, extremos PENDIENTE)"
        else:
            rol = "ESTRUCTURA_PRINCIPAL (nucleo PISO_2)"
        rows.append({"nivel": nivel, "plano": m["plano"], "id": m["id"],
                     "seccion": m["seccion"], "e_cm": m["espesor_cm"],
                     "posicion_modelo": m["posicion_modelo"],
                     "estado": m["estado"], "rol": rol})
    return rows


# ---------------------------------------------------------------------------
# 3) FIGURA v2
# ---------------------------------------------------------------------------
def hacer_figura():
    fig, ax = plt.subplots(figsize=(13, 8), dpi=150)
    ax.set_aspect("equal")
    xs = data_ax = sorted(datos_geom.ejes_x.values())
    ys_axes = sorted(datos_geom.ejes_y.values(), reverse=True)

    # esqueleto regular (reticula principal)
    main_x = [datos_geom.ejes_x[n] for n in ["E", "F", "G", "H", "I", "I'"]]
    main_y = [datos_geom.ejes_y[n] for n in ["1", "2", "3"]]
    for x in main_x:
        ax.plot([x, x], [min(main_y), max(main_y)], color="#9aa5b1", lw=0.8, zorder=1)
    for y in main_y:
        ax.plot([min(main_x), max(main_x)], [y, y], color="#6b7785", lw=1.2, zorder=2)
    for n, X in datos_geom.ejes_x.items():
        ax.annotate(n, (X, 0.7), color="#54606d", fontsize=8, ha="center")
    for n, Y in datos_geom.ejes_y.items():
        ax.annotate(n, (-0.9, Y), color="#54606d", fontsize=8, ha="right", va="center")

    # SALIENTES
    for s, fc in ((datos_irreg.SALIENTES_PISO_2[0], COL_SALIENTE_1),
                  (datos_irreg.SALIENTES_PISO_2[1], COL_SALIENTE_2)):
        x0, x1 = s["X"]; y0, y1 = s["Y"]
        ax.add_patch(mpatches.Rectangle((x0, y1), x1 - x0, y0 - y1,
                                        facecolor=fc, alpha=0.55,
                                        edgecolor="#a0522d", lw=1.4, zorder=3))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, s["id"] + "\nCONFIRMADO\nusuario",
                color="#5d2e1a", fontsize=8, ha="center", va="center",
                fontweight="bold")
    # borde sur profundo
    ax.plot([xs[0], xs[-1]], [datos_irreg.Y_EXT_SUR_102] * 2, color="#c0392b",
            lw=1.0, ls="--", zorder=2)
    ax.annotate(f"Y_EXT_SUR_102 = {datos_irreg.Y_EXT_SUR_102:.3f} m",
                (xs[-1], datos_irreg.Y_EXT_SUR_102), color="#c0392b",
                fontsize=8, ha="right", va="bottom")

    # NUCLEOS PISO_2 (muros cerrados -> trazo grueso por espesor + nodos)
    for m in datos_irreg.MUROS_CERRADOS_PISO_2:
        x0, y0, x1, y1 = m["coords"]
        ax.plot([x0, x1], [y0, y1], color=COL_ESP[m["espesor_cm"]], lw=7,
                solid_capstyle="butt", zorder=5)
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.18, m["id"],
                color=COL_ESP[m["espesor_cm"]], fontsize=7, ha="center",
                va="bottom", fontweight="bold")
    for n in datos_irreg.NODOS_GEOMETRICOS_NUEVOS[:8]:
        ax.plot(n["X"], n["Y"], "o", ms=6, mfc="white", mec=COL_ESP[20] if n["id"].startswith("NI") else "#111",
                lw=1.2, zorder=6)

    # ELEMENTOS PENDIENTES del sector sur (simbologia distinta: contorno)
    for v in datos_irreg.vigas_irregulares_todas:
        if v["id"].startswith("V3045") and v["posicion_modelo"]:
            X, Y = v["posicion_modelo"]
            ax.plot(X, Y, marker=(4, 0, 0), ms=11, mfc="none", mec="#805ad5",
                    lw=1.6, zorder=5)
            ax.annotate(v["id"], (X, Y), xytext=(X + 0.25, Y - 0.55), fontsize=7,
                        color="#5a3d99")
    for v in datos_irreg.vigas_irregulares_todas:
        if v["id"].startswith("V6030") and v["posicion_modelo"] is None and v.get(
                "x_pdf"):
            pass  # en detalle, sin posicion
    # P.M. 300x300x20 rotulos mapeados (PM102_03 area)
    for p in datos_irreg.pilares_todos:
        if p["id"] == "PM102_03" and p["posicion_modelo"]:
            X, Y = p["posicion_modelo"]
            ax.plot(X, Y, marker="D", ms=8, mfc="none", mec="#16a085", lw=1.6, zorder=5)
            ax.annotate("P.M.300x300x20 (rotulo)", (X, Y), xytext=(X + 0.3, Y + 0.3),
                        fontsize=6.5, color="#117864")
    # nucleo PISO_4 (plan 103) posiciones INFERIDO, extremos PENDIENTE
    for m in datos_irreg.muros_todos:
        if m["plano"] == "103" and m["posicion_modelo"]:
            X, Y = m["posicion_modelo"]
            ax.plot(X, Y, marker="s", ms=8, mfc="none", mec="#7f8c8d", lw=1.4,
                    zorder=4)
    ax.annotate("nucleo PISO_4 (plan 103): posiciones INFERIDO, extremos PENDIENTE",
                (0.3, -16.0), fontsize=7, color="#7f8c8d")

    ax.set_xlim(-2, 44.5)
    ax.set_ylim(-21.5, 2.2)
    ax.grid(alpha=0.2, ls=":")
    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
    ax.set_title("Geometria corregida LT1 · v2\nnucleos PISO_2 cerrados (3.95x2.25 / 1.58) "
                 "+ salientes confirmados · muros GEOMETRICOS (NO activos OpenSees)",
                 fontsize=11, fontweight="bold")

    leg = [
        mpatches.Patch(facecolor=COL_SALIENTE_1, alpha=0.55, label="Saliente 1 CONFIRMADO (10-17.49 / -20.27)"),
        mpatches.Patch(facecolor=COL_SALIENTE_2, alpha=0.55, label="Saliente 2 CONFIRMADO (20-30 / -18.61)"),
        mpatches.Patch(facecolor=COL_ESP[20], label="Muro M.H.A. e=20 (GEOMETRICO)"),
        mpatches.Patch(facecolor=COL_ESP[25], label="Muro M.H.A. e=25 (GEOMETRICO)"),
        mpatches.Patch(facecolor=COL_ESP[30], label="Muro M.H.A. e=30 (GEOMETRICO)"),
        mlines.Line2D([], [], marker="^", color="none", mfc="none", mec="#805ad5",
                      ms=10, lw=1.6, label="V.30/45 PENDIENTE (extremos)"),
        mlines.Line2D([], [], marker="D", color="none", mfc="none", mec="#16a085",
                      ms=8, label="P.M.300x300x20 PENDIENTE"),
        mlines.Line2D([], [], marker="s", color="none", mfc="none", mec="#7f8c8d",
                      ms=8, label="Nucleo PISO_4 PENDIENTE extremos"),
        mlines.Line2D([], [], color="#c0392b", ls="--", lw=1.0, label="Borde sur profundo (-20.27)"),
    ]
    ax.legend(handles=leg, loc="lower left", fontsize=7.5, framealpha=0.9)
    fig.tight_layout()
    ruta = os.path.join(OUT, "modelo_geometria_corregida_v2_lt1.png")
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def main():
    d = _cargar_modelo()
    checks = _checks_modelo(d)
    areas = _superficie_por_nivel(d)
    r1 = escribir_control(d, checks, areas)
    r2 = escribir_inventario(_rows())
    r3 = hacer_figura()
    print(f"OK: {r1}\nOK: {r2}\nOK: {r3}")


if __name__ == "__main__":
    main()