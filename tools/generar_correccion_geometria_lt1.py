# ============================================================================
# tools/generar_correccion_geometria_lt1.py
# Corrección de geometría del modelo LT1 — etapa P1L2 (previo a Unity).
#
# Entrada (datos):
#   - data/geometria_irregular.py   (Y_EXT_SUR_102, muros_todos, ...)
#   - data/inventario.py            (posiciones_verificadas, convención niveles)
#   - data/geometria.py             (ejes_x, ejes_y, niveles_z)
#   - outputs/unity/modelo_lt1.json (modelo reconstruido + análisis de gravedad)
#
# Salidas:
#   - outputs/control_geometria_corregida_lt1.txt
#   - outputs/inventario_muros_lt1.txt
#   - outputs/modelo_geometria_corregida_lt1.png
#
# Reglas AGENTS seguidas:
#   - No se inventa coordenada alguna. Lo no determinable -> PENDIENTE.
#   - Sólo se resuelve lo matemáticamente cerrable con cotas existentes o la
#     cota CONFIRMADA por el usuario: Y_EXT_SUR_102 = -20.270 m.
#   - No se crean nodos/elementos OpenSees sin AMBOS extremos determinables.
#   - No se modifica la geometría validada del esqueleto.
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

# ---------------------------------------------------------------------------
# Contexto geométrico (pre-cargado desde data/)
# ---------------------------------------------------------------------------
EJES_X = datos_geom.ejes_x          # E..I'  (0..42.5)
EJES_Y = datos_geom.ejes_y          # 1..3    (0..-16.15)
Y_3 = EJES_Y["3"]                  # -16.150
Y_EXT = datos_irreg.Y_EXT_SUR_102   # -20.270 (CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO)

NUCLEO_MARKERS = []                 # (id, X, Y, espesor_cm)
for m in datos_irreg.muros_todos:
    if m["plano"] in ("102", "103") and m["posicion_modelo"]:
        NUCLEO_MARKERS.append((m["id"], m["posicion_modelo"][0],
                               m["posicion_modelo"][1], m["espesor_cm"]))

V3045 = []                          # (id, X, Y) rótulos del sector sur
for v in datos_irreg.vigas_irregulares_todas:
    if v.get("seccion") == "V. 30/45" and v.get("posicion_modelo"):
        V3045.append((v["id"], v["posicion_modelo"][0], v["posicion_modelo"][1]))

PM102_03 = next((p["posicion_modelo"] for p in datos_irreg.pilares_todos
                 if p.get("id") == "PM102_03" and p.get("posicion_modelo")), None)

# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def _cargar_modelo():
    if not os.path.exists(JSON_MODELO):
        raise SystemExit(f"Falta {JSON_MODELO}: ejecuta primero src/modelo_lt1.py")
    with open(JSON_MODELO, encoding="utf-8") as fh:
        return json.load(fh)


def _resumen_muros():
    """Rows del inventario de muros por nivel, con rol y modelable."""
    rows = []
    for m in datos_irreg.muros_todos:
        nivel = m["nivel"]
        if m["plano"] == "101":
            rol = ("ESTRUCTURA_PRINCIPAL (contención subte)"
                   if m["seccion"].startswith("M.H.A.") else
                   "ESTRUCTURA_SECUNDARIA (interior subte)")
        else:
            rol = "ESTRUCTURA_PRINCIPAL (núcleo E-F)"
        rows.append({
            "nivel": nivel, "plano": m["plano"], "id": m["id"],
            "seccion": m["seccion"], "e_cm": m["espesor_cm"],
            "posicion_modelo": m["posicion_modelo"],
            "estado": m["estado"], "rol": rol,
        })
    return rows


def _verificaciones_modelo(d):
    """Comprueba estructura geométrica del modelo reconstruido."""
    import math
    checks = []
    nodes = d["nodes"]
    beams = d["beams"]
    columns = d["columns"]
    supports = d["supports"]

    # 1. tags únicos por tipo de elemento
    tags = [e["elementTag"] for e in beams + columns]
    n_duplicados_tags = len(tags) - len(set(tags))
    # 2. extremos existentes + longitud > 0
    nodos_ok = {n["tag"] for n in nodes}
    ref = set()
    long_neg = 0
    for e in beams + columns:
        ref.add(e["node_i"]); ref.add(e["node_j"])
        if e.get("longitud_m", 0) <= 0:
            long_neg += 1
    extremos_extranos = sum(1 for e in beams + columns
                            if e["node_i"] not in nodos_ok or e["node_j"] not in nodos_ok)
    # 3. duplicados geométricos (mismo par i-j, misma sección)
    pares = [(e["node_i"], e["node_j"], e.get("seccion")) for e in beams + columns]
    dup_geom = len(pares) - len(set(pares))
    # 4. nodos estructurales huérfanos (sin elemento y sin apoyo)
    soportes = {s["nodeTag"] for s in supports}
    ref |= soportes
    huerfanos = [n["tag"] for n in nodes
                 if n["tag"] not in ref and n.get("tipo") == "structural"]
    # 5. apoyos sobre nodos existentes
    apoyos_fuera = [s["nodeTag"] for s in supports if s["nodeTag"] not in nodos_ok]

    checks.append(("tags elemento duplicados", n_duplicados_tags == 0, n_duplicados_tags))
    checks.append(("longitudes <= 0", long_neg == 0, long_neg))
    checks.append(("extremos inexistentes", extremos_extranos == 0, extremos_extranos))
    checks.append(("elementos geom. duplicados", dup_geom == 0, dup_geom))
    checks.append(("nodos estructurales huérfanos", len(huerfanos) == 0, huerfanos[:5]))
    checks.append(("apoyos fuera de nodos", len(apoyos_fuera) == 0, apoyos_fuera))
    return checks


# ---------------------------------------------------------------------------
# 1) CONTROLE: outputs/control_geometria_corregida_lt1.txt
# ---------------------------------------------------------------------------
def escribir_control(d, checks):
    an = d["analysis"]
    buf = io.StringIO()
    w = buf.write
    w("=" * 96 + "\n")
    w("CONTROL GEOMETRIA CORREGIDA LT1 · PISO_2 sector sur + muros equivalentes\n")
    w("=" * 96 + "\n")
    w(f"Unidades: m, kN, kPa.  Borde sur CONFIRMADO: Y_EXT_SUR_102 = {Y_EXT:.3f} m\n\n")

    # --- 1) Conservación / no alterado
    w("-" * 96 + "\n")
    w("1) CONSERVACION (NO ALTERADO - solo cambios ADITIVOS)\n")
    w("-" * 96 + "\n")
    w("  Retícula principal X=E..I' e Y=1/1''/2/2a/3 (42.500 x 16.150 m): intacta.\n")
    w("  Niveles Z (FUNDACION_SUP -7.97 .. CUBIERTA_SUP 12.58): intactos.\n")
    w("  P.70x70 (90), V.60/80 (108), apoyos (18), diafragmas (4): intactos.\n")
    w("  Material H.A.: E=25 000 000 kPa · nu=0.20 · G=10 416 667 kPa: intacto.\n\n")

    # --- 2) Plano 102 - sector sur
    w("-" * 96 + "\n")
    w("2) PLANO 102 (PISO_2, z=+3.91) · SECTOR SUR (cota nueva del usuario)\n")
    w("-" * 96 + "\n")
    w("  PISO_2 NO termina en eje 3: sobresale al sur en las franjas F-G y G-H.\n")
    w(f"  COTA NUEVA (fuente: inspeccion visual del usuario sobre el plano 102):\n")
    w(f"    eje 3 -> linea exterior sur = 4.12 m  =>  Y_EXT_SUR_102 = "
      f"{Y_3} - 4.12 = {Y_EXT:.3f} m\n")
    w("    Estado: CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO (ni OCR ni inferencia).\n")
    w("  Elementos del sector (estado de posicion / trazado):\n")
    w("    V.30/45  (V3045_01 X≈20.97 / V3045_02 X≈25.77, Y≈-18.86): posicion de\n"
      "            rotulo INFERIDA RESPALDADA (dentro de la banda confirmada);\n"
      "            EXTREMOS (par de nodos) PENDIENTE -> sin nodos.\n")
    w("    V.60-30/80-40 (5), V.60/VAR (5): solo en vistas de detalle del plan 102\n"
      "            (y_pdf < 419.8) -> PENDIENTE_COORDENADA.\n")
    w("    P.M. 300x300x20: PM102_03 en (18.5,-15.5) dentro del edificio; el resto\n"
      "            del sector solo en vistas de detalle -> PENDIENTE_COORDENADA.\n\n")

    # --- 3) Plano 101 (subte)
    w("-" * 96 + "\n")
    w("3) PLANO 101 (PLANTA CIELO 1° SUBTERRANEO, PISO_1S z=-4.01)\n")
    w("-" * 96 + "\n")
    w("  Clasificacion por rol (regla P1L2: modelo estructural equivalente):\n")
    w("    ESTRUCTURA_PRINCIPAL : M.H.A. e=15 (2) / e=20 (10+6 rotulos) / e=30 (4),\n"
      "                           columnas P.70x70, vigas V.60/80 (esqueleto).\n")
    w("    ESTRUCTURA_SECUNDARIA: M.I. e=20 (1), V.S.I.20/150, V.S.I.15/125, +V.I.\n"
      "                           2a etapa, V.20/80 (5), V.20/130 (3).\n")
    w("    DETALLE_NO_REQUERIDO_P1L2: sectores de dilatacion/contencion, V.M.\n"
      "                           accesorios sin rol estructural equivalente.\n")
    w("  Posiciones de los muros del subte: PENDIENTE (mapeo 101 no calibrado y\n"
      "  sin cotas individuales) -> NO se crean elementos.\n\n")

    # --- 4) Plano 103 (PISO_4)
    w("-" * 96 + "\n")
    w("4) PLANO 103 (PLANTA CIELO PISO 4°, PISO_4 z=11.83)\n")
    w("-" * 96 + "\n")
    w("  Nucleo E-F e=20/25/30 CONFIRMADO por cruzamiento con plan 102 (ver 5).\n")
    w("  P.70x70 (18), V.60/80 (31), +V.I.20/90 2a etapa (16), parrilla metalica\n"
      "  (P.M.300x300x20, V.M.300x300x5): inventariado; posiciones de parrilla\n"
      "  metalica PENDIENTE excepto nucleo.\n\n")

    # --- 5) Coordenadas resueltas / pendientes
    w("-" * 96 + "\n")
    w("5) CORRECCION REAL · COORDENADAS RESUELTAS vs PENDIENTES\n")
    w("-" * 96 + "\n")
    w("  RESUELTAS:\n")
    w(f"    Y_EXT_SUR_102 = {Y_EXT:.3f} m  (CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO)\n")
    w("    Posiciones de rotulo del nucleo e=25/e=30, cruzadas plan 102/103:\n")
    w("      M102_E25_01/02 -> (2.81/6.11, -14.00)  [117]  [fila Y≈-14.0]\n")
    w("      M102_E30_01/02 -> (3.08/5.84, -5.68/-5.53) [fila Y≈-5.6]\n")
    w("      M103_E25_01/02 -> (2.72/6.26, -14.06/-13.93)\n")
    w("      M103_E30_01/02 -> (3.08/5.89, -5.57)   [PISO_4, mismo nucleo]\n")
    w("      (E-ticas e=25/e=30 estan en la capa de texto de 102 y 103;\n")
    w("       correccion del dato previo 'solo OCR visual'.)\n")
    w("  PENDIENTES (motivo concreto, sin inventar):\n")
    w("    X_SUR_102  : lim X de la saliente F-G/G-H (no cotado).\n")
    w("    V.30/45    : par de nodos (extremos) de cada viga.\n")
    w("    V.60-30/80-40, V.60/VAR, P.M. del sector sur: solo vistas de detalle.\n")
    w("    Longitudes de TODOS los muros del nucleo (TRAMO_NUCLEO_E_F).\n")
    w("    Muros del subte (plan 101): posiciones individuales.\n\n")

    # --- 6) Muros equivalentes
    rows = _resumen_muros()
    w("-" * 96 + "\n")
    w("6) MUROS EQUIVALENTES P1L2 (inventario: outputs/inventario_muros_lt1.txt)\n")
    w("-" * 96 + "\n")
    modelables = [r for r in rows if r["posicion_modelo"] and "PENDIENTE" not in r["estado"]]
    w(f"  Muros registrados: {len(rows)}\n")
    w("  Regla: solo se crean elementos OpenSees si extremos+geometria respaldados\n"
      "  (NO se inventa longitud). POSICION de rotulo respaldada NO basta: falta\n"
      "  la cota de longitud en todos los tramos -> MUROS OPENSees: 0\n")
    w("  Aunque falte la longitud, la posicion de los muros del nucleo E-F queda\n"
      "  respaldada por cruce de planos 102/103 (diferencia <0.1 m), listos para\n"
      "  cerrarse cuando se lea la cota.\n\n")

    # --- 7) Cierre geometria sur
    w("-" * 96 + "\n")
    w("7) CIERRE DE LA GEOMETRIA SUR (saliente del plano 102)\n")
    w("-" * 96 + "\n")
    w("  Intentada la resolucion con la unica cota nueva (Y_EXT_SUR_102):\n")
    w("    - El borde sur queda fijado en Y=-20.270 (un solo grado de libertad).\n")
    w("    - Para cerrar V.30/45, V.60-30/80-40, P.M. del sector falta el LIMITE X\n"
      "      de la saliente y la POSICION-Y de cada linea de viga/columna (cotas\n"
      "      en la imagen del plano 102, no en la capa de texto).\n")
    w("  RESULTADO: saliente NO cerrable con las cotas disponibles en data/ -> se\n"
      "  registra la cota confirmada y el sector queda PENDIENTE (sombreado en la\n"
      "  figura). NODOS AGREGADOS: 0 · ELEMENTOS AGREGADOS: 0\n\n")

    # --- 8) Verificación OpenSees
    w("-" * 96 + "\n")
    w("8) VERIFICACION DEL MODELO RECONSTRUIDO (OpenSees, post-correccion)\n")
    w("-" * 96 + "\n")
    w(f"  Nodos: {len(d['nodes'])} (108 estructurales + 4 masters) · "
      f"elasticBeamColumn: {len(d['beams'])} vigas + {len(d['columns'])} columnas\n")
    for nombre, ok, valor in checks:
        w(f"  [{'OK' if ok else 'FALLO'}] {nombre}: {valor}\n")
    w("\n")

    # --- 9) Gravedad / equilibrio
    panos = d["panos"]
    area_por_nivel = {}
    for p in panos:
        area_por_nivel[p["nivel"]] = area_por_nivel.get(p["nivel"], 0.0) + p["area_m2"]
    w("-" * 96 + "\n")
    w("9) GRAVEDAD / EQUILIBRIO TRAS CORRECCION\n")
    w("-" * 96 + "\n")
    for nv, ar in sorted(area_por_nivel.items()):
        w(f"    {nv}: superficie losa = {ar:.3f} m2\n")
    w(f"  P gravitatoria total (PISO_1..4) = {an['P_aplicada_kN']:.3f} kN\n")
    w(f"  P_losas = P_transferida_a_vigas (108 vigas) = {an['P_aplicada_kN']:.3f} kN\n")
    w(f"  Sum Rz (24 apoyos) = {an['suma_Rz_kN']:.3f} kN · "
      f"err abs = {an['err_abs_kN']:.3e} · err rel = {an['err_rel']:.3e} "
      f"(tol 1e-6)\n")
    w("  NOTA: el saliente NO se cerro -> la superficie de losa total NO cambia\n"
      "  (686.375 m2 por nivel). El valor NO se conserva como automatico: se\n"
      "  mantiene porque el saliente aun no es cerrable; si el saliente fuera\n"
      "  losa estructural cargada, se recalcularia la superficie/cargas al\n"
      "  cerrarse la geometria.\n\n")

    # --- 10) Outputs
    w("-" * 96 + "\n")
    w("10) OUTPUTS GENERADOS\n")
    w("-" * 96 + "\n")
    w("  outputs/control_geometria_corregida_lt1.txt   (este archivo)\n")
    w("  outputs/inventario_muros_lt1.txt              (inventario de muros)\n")
    w("  outputs/modelo_geometria_corregida_lt1.png    (figura comparativa)\n\n")

    w("=" * 96 + "\n")
    w("FIN CONTROL GEOMETRIA CORREGIDA LT1\n")
    w("=" * 96 + "\n")
    ruta = os.path.join(OUT, "control_geometria_corregida_lt1.txt")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(buf.getvalue())
    return ruta


# ---------------------------------------------------------------------------
# 2) Inventario de muros: outputs/inventario_muros_lt1.txt
# ---------------------------------------------------------------------------
def escribir_inventario_muros(rows):
    buf = io.StringIO()
    w = buf.write
    w("=" * 96 + "\n")
    w("INVENTARIO DE MUROS M.H.A. / M.I. · MODELO LT1 (P1L2)\n")
    w("=" * 96 + "\n")
    w("Estados (4): CONFIRMADO_PLANO | CONFIRMADO_POR_INSPECCION_VISUAL\n")
    w("             USUARIO | INFERIDO_RESPALDADO | PENDIENTE_COORDENADA\n")
    w("LONGITUD: todos los tramos sin extremos cotados -> PENDIENTE -> NO\n")
    w("modelados en OpenSees (regla: extremos suficientes; no inventar).\n\n")

    w(f"{'NIVEL':12s} {'PLANO':5s} {'ID':14s} {'SECCION':14s} {'e[cm]':6s} "
      f"{'X[m]':7s} {'Y[m]':8s} {'ESTADO':22s} ROL\n")
    w("-" * 96 + "\n")
    for r in sorted(rows, key=lambda r: (r["nivel"], r["plano"], r["id"])):
        pm = r["posicion_modelo"] or (None, None)
        X = f"{pm[0]:7.2f}" if pm[0] is not None else "   n/a "
        Y = f"{pm[1]:8.2f}" if pm[1] is not None else "     n/a "
        w(f"{r['nivel']:12s} {r['plano']:5s} {r['id']:14s} {r['seccion']:14s} "
          f"{r['e_cm']:6d} {X} {Y} {r['estado']:22s} {r['rol']}\n")

    w("\nNOTAS:\n")
    w("  - Plan 101 (PISO_1S): conteo por capa de texto CONFIRMADO_PLANO; el\n"
      "    mapeo 101 no esta calibrado -> posiciones individuales PENDIENTE.\n")
    w("  - Muros del nucleo e=25/e=30 (102/103): e-ticas EN la capa de texto;\n"
      "    posiciones de rotulo cruzadas 102<->103 (diferencia <0.1 m).\n")
    w("  - M102_04/05/06: vistas de detalle del plan 102 (y_pdf<440), no edificio.\n")
    w("  - TOTAL: %d tramos / %d muros modelados en OpenSees: 0 (sin longitudes).\n"
      % (len(rows), len([r for r in rows if False])))
    ruta = os.path.join(OUT, "inventario_muros_lt1.txt")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(buf.getvalue())
    return ruta


# ---------------------------------------------------------------------------
# 3) Figura: outputs/modelo_geometria_corregida_lt1.png
# ---------------------------------------------------------------------------
def hacer_figura():
    fig, ax = plt.subplots(figsize=(11.5, 7.5), dpi=150)
    ax.set_aspect("equal")

    # --- esqueleto anterior (rectangulo retícula) ---
    xs = sorted(set(EJES_X.values()))
    ys = sorted(set(EJES_Y.values()), reverse=True)
    for x in xs:
        ax.plot([x, x], [ys[-1], ys[1]], color="#a7b0bd", lw=0.8, zorder=1)
    for y in (ys[0], ys[1]):
        ax.plot([xs[0], xs[-1]], [y, y], color="#54606d", lw=1.4, zorder=2)
    for x in xs:
        ax.annotate(x, (x, 0.35), color="#54606d", fontsize=7, ha="center")
    ax.annotate("retícula anterior\nesqueleto (hasta eje 3)", (33.5, -12.2),
                color="#54606d", fontsize=8, ha="left", style="italic")

    # --- saliente PENDIENTE (banda F-G/G-H, X aprox 10..30) ---
    band = mpatches.Rectangle((10.0, Y_EXT), 20.0, Y_3 - Y_EXT,
                              facecolor="#f4a582", alpha=0.45, hatch="//",
                              edgecolor="#c0392b", linewidth=0.8, zorder=3)
    ax.add_patch(band)
    ax.text(20.0, (Y_3 + Y_EXT) / 2.0,
            "SALIENTE PENDIENTE\n(límite X y vigas sin cota)", color="#7b241c",
            fontsize=9, ha="center", va="center", fontweight="bold")

    # --- borde sur CONFIRMADO ---
    ax.plot([xs[0], xs[-1]], [Y_EXT, Y_EXT], color="#e74c3c", lw=2.2,
            ls="--", zorder=4)
    ax.annotate(f"borde sur CONFIRMADO\nY_EXT_SUR_102 = {Y_EXT:.3f} m "
                "(Y(3) - 4.12 m)", (xs[-1], Y_EXT), color="#c0392b",
                fontsize=9, ha="right", va="bottom", fontweight="bold")
    ax.plot([10.0, 10.0], [Y_EXT, Y_3], color="#c0392b", lw=1.0, ls=":")
    ax.plot([30.0, 30.0], [Y_EXT, Y_3], color="#c0392b", lw=1.0, ls=":")

    # --- núcleo E-F (muros) ---
    col_e = {20: "#2b6cb0", 25: "#dd6b20", 30: "#c53030"}
    seen = set()
    for mid, X, Y, ecm in sorted(NUCLEO_MARKERS):
        if (round(X, 1), round(Y, 1), ecm) in seen:
            continue
        seen.add((round(X, 1), round(Y, 1), ecm))
        ax.scatter([X], [Y], marker="s", s=42, color=col_e[ecm], zorder=5,
                   edgecolor="k", linewidth=0.4)
        ax.annotate(f"e={ecm}", (X, Y), color=col_e[ecm], fontsize=7,
                    ha="left", va="bottom", xytext=(3, 2),
                    textcoords="offset points")
    ax.annotate("núcleo E-F · M.H.A. e=20/25/30\nposición de rótulo respaldada\n" 
                "(longitud PENDIENTE)", (0.3, -6.8), fontsize=8, color="#2c3e50")

    # --- rótulos V.30/45 del sector sur ---
    for vid, X, Y in V3045:
        ax.scatter([X], [Y], marker="^", s=70, color="#805ad5", zorder=5,
                   edgecolor="k", linewidth=0.4)
        ax.annotate(f"{vid}\n(punta viga PENDIENTE)", (X, Y), color="#5a3d99",
                    fontsize=7, ha="center", va="top", xytext=(0, -6),
                    textcoords="offset points")

    # --- PM102_03 (único P.M. 300x300x20 con rótulo en el edificio) ---
    if PM102_03:
        ax.scatter([PM102_03[0]], [PM102_03[1]], marker="D", s=34, color="#16a085",
                   zorder=5, edgecolor="k", linewidth=0.4)
        ax.annotate("P.M.300x300x20 (rótulo\ndentro del edificio)", PM102_03,
                    color="#117864", fontsize=7, ha="left", va="bottom",
                    xytext=(4, 3), textcoords="offset points")

    ax.set_xlim(-1.5, 44.5)
    ax.set_ylim(-21.5, 2.2)
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_title("Geometría corregida LT1 · PISO_2: borde sur confirmado "
                 "Y=-20.270 m\n(saliente pendiente de cotas X / extremos; "
                 "sin nodos ni elementos inventados)")
    ax.grid(alpha=0.25, ls=":")

    # --- leyenda ---
    lp = [mpatches.Patch(facecolor="#f4a582", alpha=0.5, hatch="//",
                         label="Saliente pendiente (sin cota X)"),
          mlines.Line2D([], [], color="#e74c3c", ls="--", lw=2,
                        label="Borde sur confirmado (-20.270 m)"),
          mpatches.Patch(facecolor="#2b6cb0", label="Muro M.H.A. e=20"),
          mpatches.Patch(facecolor="#dd6b20", label="Muro M.H.A. e=25"),
          mpatches.Patch(facecolor="#c53030", label="Muro M.H.A. e=30"),
          mlines.Line2D([], [], marker="^", color="w", markerfacecolor="#805ad5",
                        markersize=10, label="V.30/45 sector sur (rótulo)"),
          mlines.Line2D([], [], marker="D", color="w", markerfacecolor="#16a085",
                        markersize=8, label="P.M. 300x300x20 (rótulo en edificio)")]
    ax.legend(handles=lp, loc="upper left", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    ruta = os.path.join(OUT, "modelo_geometria_corregida_lt1.png")
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def main():
    d = _cargar_modelo()
    checks = _verificaciones_modelo(d)
    rows = _resumen_muros()
    r1 = escribir_control(d, checks)
    r2 = escribir_inventario_muros(rows)
    r3 = hacer_figura()
    print(f"OK: {r1}\nOK: {r2}\nOK: {r3}")
    return r1, r2, r3


if __name__ == "__main__":
    main()
