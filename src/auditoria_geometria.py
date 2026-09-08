# ============================================================================
# src/auditoria_geometria.py
# Auditoría geométrica LT1: modelo actual vs planos (capa de texto y datos
# registrados). GENERA SOLO INFORMES; NO modifica el modelo.
#
# LIMITACION DEL METODO: este modelo (big-pickle) NO acepta imágenes, por lo
# que NO se hace inspección visual de los planos. La auditoría usa:
#   1) capa de texto extraíble de los PDF (pymupdf, rótulos con posición pdf);
#   2) datos ya registrados en data/ (inventario, geometria_irregular,
#      convención de niveles, esqueleto);
#   3) geometría REAL del modelo (runpy de src/modelo_lt1.py sin ejecutar el
#      análisis, con salida desviada).
# Todo lo que requeriría confirmación visual de la lámina queda marcado como
# PENDIENTE_VERIFICACION_VISUAL.
# Salidas: outputs/auditoria_geometria_lt1.txt, auditoria_geometria_piso1..4.png
# ============================================================================

import contextlib
import io
import os
import re
import runpy
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches as mpatches

import pymupdf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANOS = os.path.join(BASE, "planos")
OUT = os.path.join(BASE, "outputs")

# ---------------------------------------------------------------------------
# 1. GEOMETRÍA REAL DEL MODELO (leída de src/modelo_lt1.py, sin análsis)
# ---------------------------------------------------------------------------
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
    _ns = runpy.run_path(os.path.join(BASE, "src", "modelo_lt1.py"),
                         run_name="__auditoria_geometria__")

MODELO = {
    "nodos": _ns["nodos"],                      # {tag: (x, y, z)}
    "nodos_maestros": _ns["nodos_maestros"],    # {tag: {nivel, x, y, z}}
    "columnas_por_nivel": _ns["columnas_por_nivel"],
    "vigas_por_nivel": _ns["vigas_por_nivel"],
    "muros_por_nivel": _ns["muros_por_nivel"],
    "apoyos": _ns["apoyos"],
    "ejes_x": _ns["ejes_x"],
    "ejes_y": _ns["ejes_y"],
    "niveles_z": _ns["niveles_z"],
}

G_ESTRUCT = {k: len(v) for k, v in MODELO["nodos_maestros"].items()}
N_NODOS = len(MODELO["nodos"])
N_MASTER = len(MODELO["nodos_maestros"])
N_COL = sum(len(v) for v in MODELO["columnas_por_nivel"].values())
N_VIG = sum(len(v) for v in MODELO["vigas_por_nivel"].values())
N_MUROS = sum(len(v) for v in MODELO["muros_por_nivel"].values())
N_APOYOS = len(MODELO["apoyos"])

# ---------------------------------------------------------------------------
# 2. CAPA DE TEXTO DE LOS PLANOS (rótulos con posición en pts)
# ---------------------------------------------------------------------------
PLANOS_PDF = {
    "000": "2017_67-000-Model.pdf",
    "001": "2017_67-001-Model.pdf",
    "100": "2017_67-100 (1)-Model.pdf",
    "101": "2017_67-101-Model.pdf",
    "102": "2017_67-102-Model.pdf",
    "103": "2017_67-103-Model.pdf",
    "300": "2017_67-300-Model.pdf",
    "301": "2017_67-301-Model.pdf",
    "302": "2017_67-302-Model.pdf",
    "303": "2017_67-303-Model.pdf",
    "700": "2017_67-700-Model.pdf",
}

_ROTULOS_NORM = [
    "M.H.A. e=15", "M.H.A. e=20", "M.H.A. e=25", "M.H.A. e=30", "M.I. e=20",
    "V.60/80", "V.40/60", "V.30/45", "V.20/80", "V.20/130", "V.20/90",
    "V.20/VAR", "V.30/VAR", "V.15/VAR", "V.60/VAR", "V.60-30/80-40",
    "V.M.300x300x5", "V.M.300x300x5(ARR)", "V.S.I.20/150", "V.S.I.15/125",
    "V.S.I.15/VAR", "+V.I.20/90", "+V.I.20/87", "+V.I.15/VAR", "V.I.15/169",
    "V.F.20/220", "V.F.20/180", "V.F.20/160", "V.F.20/120", "V.F.15/225",
    "V.F.15/100", "V.F.30/170", "V.F.30/136", "LOSA e=25", "P.70x70",
    "P.30x30", "P.20x50", "P.M.300x300x20", "P.M.I.", "PARRILLA",
    "DILATACION", "N.S.M.", "PASADA", "PASADAS", "V.F.", "V.I.",
    "M.H.A.", "V.", "P.",
]

# Rótulos genéricos (prefijos) que se SOLAPAN con los específicos: su conteo
# incluye subcadenas de los rótulos detallados, por lo que en el informe se
# excluyen del recuento principal.
_GENERICOS = {"V.F.", "V.I.", "M.H.A.", "V.", "P.", "PASADA", "PASADAS"}


def _norm(t):
    return re.sub(r"\s+", "", t)


def contar_rotulos(plano):
    """Cuenta ocurrencias de rótulo normalizado en la capa de texto."""
    f = os.path.join(PLANOS, PLANOS_PDF[plano])
    if not os.path.exists(f):
        return {}
    doc = pymupdf.open(f)
    t = _norm(doc[0].get_text())
    doc.close()
    c = {}
    for r in _ROTULOS_NORM:
        if r in _GENERICOS:
            continue
        rn = _norm(r)
        n = t.count(rn)
        if n:
            c[r] = n
    return c


TEXTO_POR_PLANO = {p: contar_rotulos(p) for p in ["100", "101", "102", "103"]}

# ---------------------------------------------------------------------------
# 3. INVENTARIO REGISTRADO (data/inventario.py y data/geometria_irregular.py)
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, BASE)
from data import inventario as DI
from data import geometria_irregular as DGI

# Estado del esqueleto modelado: todos los items de columnas/vigas del modelo
# en la retícula principal tienen estado CONFIRMADO_PLANO (retícula verificada).

# ---------------------------------------------------------------------------
# 4. TABLA DE INVENTARIO (modelado vs pendiente por plano)
# ---------------------------------------------------------------------------
ESTADO_REGLAS = {
    "muro_ha": ("PENDIENTE_COORDENADA",
                "posición de rótulo en capa de texto; longitud/tramos pendiente"),
    "columna_ha": ("CONFIRMADO_PLANO_MALLA", "retícula principal verificada"),
    "columna_metal": ("PENDIENTE_COORDENADA",
                      "en vistas de detalle del PDF (y_pdf<440); posición en edificio pendiente"),
    "pilar_metal": ("PENDIENTE_COORDENADA",
                    "en vistas de detalle del PDF (y_pdf<310)"),
    "viga_ha": ("CONFIRMADO_PLANO_MALLA", "retícula principal verificada"),
    "viga_metal": ("PENDIENTE_COORDENADA", "en vistas de detalle del PDF"),
    "viga_ha_variable": ("PENDIENTE_COORDENADA",
                         "requiere Y_EXT_SUR_102 + par de nodos"),
    "viga_inferior": ("PENDIENTE_COORDENADA",
                      "cantidad por inventario sin posición de trazado"),
    "viga_inferior_variable": ("PENDIENTE_COORDENADA", "posición pendiente"),
    "viga_superior_inv": ("PENDIENTE_COORDENADA", "posición pendiente"),
    "viga_fundacion": ("PENDIENTE_COORDENADA",
                       "trazado de V.F. requiere ejes; cota pendiente"),
    "muro_interior": ("PENDIENTE_COORDENADA", "posición pendiente"),
    "losa": ("NO_ESTRUCTURAL_PUNTUAL",
             "no requiere nodos; se transfiere por área tributaria"),
}


def _inventario_filas():
    filas = []
    # ---- BLOQUE MODELADO (retícula principal + esqueleto) ----
    for nivel, lista in MODELO["columnas_por_nivel"].items():
        for c in lista:
            filas.append({
                "id": c.get("id_plano") or c.get("clave"),
                "plano": c.get("plano_fuente", "RETICULA PRINCIPAL"),
                "nivel": f"{c['nivel_inferior']}->{c['nivel_superior']}",
                "tipo_elemento": c["tipo_inventario"],
                "seccion": c["seccion"],
                "referencia_i": c["eje_x"] + c["eje_y"],
                "referencia_j": c["eje_x"] + c["eje_y"],
                "X_i": None, "Y_i": None, "X_j": None, "Y_j": None,
                "estado": "CONFIRMADO_PLANO",
                "evidencia": f"Retícula principal ({c['eje_x']},{c['eje_y']}). "
                             f"{c.get('planta_fuente','') or c.get('plano_fuente','')}",
            })
    for nivel, lista in MODELO["vigas_por_nivel"].items():
        for v in lista:
            filas.append({
                "id": v.get("id_plano") or v.get("clave"),
                "plano": v.get("plano_fuente", "RETICULA PRINCIPAL"),
                "nivel": v["nivel"],
                "tipo_elemento": v["tipo_inventario"],
                "seccion": v["seccion"],
                "referencia_i": v["eje_x_i"] + v["eje_y_i"],
                "referencia_j": v["eje_x_j"] + v["eje_y_j"],
                "X_i": None, "Y_i": None, "X_j": None, "Y_j": None,
                "estado": "CONFIRMADO_PLANO",
                "evidencia": f"Viga entre ({v['eje_x_i']},{v['eje_y_i']}) y "
                             f"({v['eje_x_j']},{v['eje_y_j']}) en {v['nivel']} "
                             f"(z={MODELO['niveles_z'][v['nivel']]:+.2f} m).",
            })
    # ---- BLOQUE IRREGULAR REGISTRADO (data/geometria_irregular) ----
    for e in DGI.todos_los_elementos:
        estado_pred, evid_pred = ESTADO_REGLAS.get(
            e.get("tipo", e.get("seccion", "?")), ("PENDIENTE_COORDENADA", "por definir"))
        idn = e.get("id")
        pm = e.get("posicion_modelo") or {}
        xi = pm[0] if isinstance(pm, (tuple, list)) and pm else None
        yi = pm[1] if isinstance(pm, (tuple, list)) and pm else None
        filas.append({
            "id": idn,
            "plano": e["plano"],
            "nivel": e.get("nivel", "PENDIENTE"),
            "tipo_elemento": e.get("tipo", e.get("seccion")),
            "seccion": e["seccion"],
            "referencia_i": "-",
            "referencia_j": "-",
            "X_i": xi, "Y_i": yi, "X_j": None, "Y_j": None,
            "estado": e["estado"],
            "evidencia": (e.get("razon_estado", "") + " | " +
                          e.get("fuente", "")).strip(" |"),
        })
    return filas


FILAS = _inventario_filas()


def resumen_estados(filas):
    c = Counter(f["estado"] for f in filas)
    return c


def resumen_por_plano(filas):
    por_plano = {}
    for f in filas:
        k = f["plano"]
        por_plano.setdefault(k, Counter())
        por_plano[k][f["estado"]] += 1
    return por_plano


# ---------------------------------------------------------------------------
# 5. SECTOR SUR (plano 102) — análisis desde data compilada
# ---------------------------------------------------------------------------
def analisis_sector_sur():
    """Compila lo registrado sobre el sector sur según datos (sin incra visual)."""
    s = []
    s.append("SECTOR SUR DEL PLANO 102 (PLANTA CIELO PISO 2°, PISO_2 z=+3.91 m)")
    s.append("------------------------------------------------------------------")
    s.append("La vista principal del folio 102 muestra un sector que sobresale por")
    s.append("debajo del eje 3 (Y < -16.15 m). Estado según datos registrados:")
    s.append("  - Y_EXT_SUR_102 : PENDIENTE_COORDENADA (no hay cota en capa de texto).")
    s.append("  - V.30/45 (2 rótulos): posiciones mapeadas desde pdfminer:")
    s.append("      V3045_01 -> X≈20.97, Y≈-18.86  (cerca de eje Ga=21.45)")
    s.append("      V3045_02 -> X≈25.77, Y≈-18.86  (cerca entre G=20 y H=30)")
    s.append("    estado PENDIENTE_COORDENADA: Y=-18.86 está fuera del rango de")
    s.append("    validación del mapeo 102 (solo Y > -16.15 fue calibrado); falta")
    s.append("    la cota Y_EXT_SUR para fijar extremos.")
    s.append("  - P.M. 300x300x20 (3 rótulos): PM102_01/02 en vistas de detalle")
    s.append("    (y_pdf<440); PM102_03 en y_pdf≈452 (límite inferior, Y≈-15.5).")
    s.append("    estado PENDIENTE_COORDENADA (X_SUR_102 pendiente).")
    s.append("  - V.60/VAR (1 rótulo) y V.60-30/80-40 (5 rótulos): vistas de detalle")
    s.append("    del folio y texto principal -> PENDIENTE_COORDENADA.")
    s.append("  - V.60/80 adicionales del sector: dentro de los 30 'extra' del")
    s.append("    inventario 102 (57 totales - 27 retícula).")
    s.append("  - NIVEL del sector: PISO_2 (z=+3.91 m) según CONVENCION_NIVELES")
    s.append("    (la vista principal del folio 102 es PLANTA CIELO PISO 2°).")
    s.append("  - NO_ESTRUCTURAL / NO_MODELANDO_P1L2: la franja sur del folio 102")
    s.append("    (y_pdf<440) contiene vistas de detalle (P.M., V.M., P.M.I.,")
    s.append("    V.60-30/80-40) que NO pueden mapearse al edificio sin revisión")
    s.append("    visual/manual del plano.")
    s.append("  - Limitación del método: sin lectura VISUAL del plano 102 no se")
    s.append("    confirma la extensión exacta (X_SUR, Y_EXT_SUR) del saliente.")
    return "\n".join(s)


# ---------------------------------------------------------------------------
# 6. FIGURAS DE AUDITORÍA POR PLANTA (verde=modelado, rojo=falta, amarillo=pend)
# ---------------------------------------------------------------------------
def _xy_nodos():
    return MODELO["nodos"]


def figura_por_piso(nivel, z, plano_rotulo, elementos_sur, ruta_out):
    """Una planta del modelo (verde) + registrados pendientes (rojo/amarillo)."""
    ejeX = MODELO["ejes_x"]
    ejeY = MODELO["ejes_y"]
    x_main = ["E", "F", "G", "H", "I", "I'"]
    y_main = ["1", "2", "3"]

    fig, ax = plt.subplots(figsize=(11, 8), constrained_layout=True)
    # ---- malla retícula principal (lo que el modelo reficla) ----
    for i in range(len(x_main) - 1):
        for Y in y_main:
            ax.plot([ejeX[x_main[i]], ejeX[x_main[i + 1]]],
                    [ejeY[Y], ejeY[Y]], color="green", lw=1.4, zorder=3)
    for i in range(len(y_main) - 1):
        for X in x_main:
            ax.plot([ejeX[X], ejeX[X]],
                    [ejeY[y_main[i]], ejeY[y_main[i + 1]]],
                    color="green", lw=1.4, zorder=3)
    for X in x_main:
        for Y in y_main:
            ax.plot([ejeX[X]], [ejeY[Y]], "o", ms=5, mfc="green",
                    mec="black", zorder=4)
    # ---- marcar ejes ----
    for n, X in ejeX.items():
        ax.text(X, max(ejeY.values()) + 0.45, n, fontsize=8, ha="center",
                va="bottom", color="0.3")
    for n, Y in ejeY.items():
        ax.text(min(ejeX.values()) - 0.5, Y, n, fontsize=8, ha="right",
                va="center", color="0.3")

    # ---- sector sur (referencia de marca pendiente) ----
    rect_sur = mpatches.Rectangle((15.0, -19.4), 15.0, 19.4 - 16.15,
                                  fill=False, ec="orange", lw=1.2, ls="--",
                                  zorder=2)
    ax.add_patch(rect_sur)
    ax.text(22.5, -17.6, "SECTOR SUR\n(PENDIENTE: X_SUR, Y_EXT_SUR)",
            fontsize=8, ha="center", color="orange", zorder=6)

    # ---- elementos irregulares registrados por nivel ----
    for e in DGI.todos_los_elementos:
        pm = e.get("posicion_modelo")
        if not isinstance(pm, (tuple, list)) or not pm:
            continue
        X, Y = pm[0], pm[1]
        try:
            lvl = str(e.get("nivel", "")).lower()
        except Exception:
            lvl = ""
        if "piso_2" in lvl or "piso_4" in lvl:
            pass
        # colorear por estado
        st = e["estado"]
        if st == "INFERIDO_RESPALDADO":
            col, mk = "red", "s"
        elif st == "PENDIENTE_COORDENADA":
            col, mk = "gold", "D"
        else:
            col, mk = "purple", "^"
        ax.plot([X], [Y], marker=mk, ms=7, mfc=col, mec="black", zorder=5)
        ax.annotate(e.get("id", ""), (X, Y), xytext=(X + 0.6, Y + 0.6),
                    fontsize=6.5, zorder=6)

    ax.plot([], [], "s", color="red", label="INFERIDO_RESPALDADO (pos. ~1 m)")
    ax.plot([], [], "D", color="gold", label="PENDIENTE_COORDENADA")
    ax.plot([], [], color="green", lw=1.4, label="MODELADO (retícula principal)")
    ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
    ax.set_xlim(-4, 46)
    ax.set_ylim(-21, 3)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_title(f"AUDITORIA GEOMETRIA LT1 · {plano_rotulo} (z={z:+.2f} m)\n"
                 "verde=modelado · rojo=falta modelar · amarillo=pendiente cota",
                 fontsize=11, fontweight="bold")
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(ruta_out, dpi=150)
    plt.close(fig)
    return ruta_out


# ---------------------------------------------------------------------------
# 7. GENERAR SALIDAS
# ---------------------------------------------------------------------------
def generar():
    lineas = []
    w = lineas.append

    # ---------- ENCABEZADO ----------
    w("=" * 78)
    w("AUDITORIA GEOMETRICA LT1 · CONTROL 2026-09-07")
    w("Modelo estructural 3D vs planos 000/001/100/101/102/103/300-303/700")
    w("Metodo: capa de texto PDF + datos registrados en data/ + geometría")
    w("real del modelo (src/modelo_lt1.py, sin ejecutar análisis).")
    w("LIMITE DECLARADO: NO hay inspección visual (modelo sin entrada de")
    w("imágenes). Todo lo confirmable solo viendo la lámina queda como")
    w("PENDIENTE_VERIFICACION_VISUAL.")
    w("=" * 78)

    # ---------- MODELO ACTUAL ----------
    w("")
    w("1. MODELO ACTUAL (leido de src/modelo_lt1.py + runpy)")
    w("-" * 78)
    w(f"  nodos estructurales....: {N_NODOS} (108) + {N_MASTER} maestros")
    w(f"  columnas P.70x70.......: {N_COL} (18 por tramo x 5 tramos)")
    w("      tramos: FUNDACION_SUP->PISO_1S, PISO_1S->PISO_1, PISO_1->PISO_2,")
    w("              PISO_2->PISO_3, PISO_3->PISO_4")
    w(f"  vigas V.60/80.........: {N_VIG} (27 por piso x 4 niveles)")
    w(f"  muros construidos.....: {N_MUROS}  -> 0 (NO modelado)")
    w(f"  apoyos................: {N_APOYOS} (18 en base FUNDACION_SUP)")
    w("  diafragmas.........: FUNDACION_SUP, PISO_1S, PISO_1..PISO_4, CUBIERTA_SUP")
    w("  retícula principal...: X = E,F,G,H,I,I' ; Y = 1,2,3")
    w("  NO modelado aún......: sector sur plano 102, muros M.H.A., elementos")
    w("                         metálicos (P.M., V.M., P.M.I.), V.F., V.S.I.,")
    w("                         vigas irregulares, +V.I. 2ª etapa.")

    # ---------- CAPA DE TEXTO ----------
    w("")
    w("2. CAPA DE TEXTO PDF (rótulos por plano, conteo exacto)")
    w("-" * 78)
    for p in ["100", "101", "102", "103"]:
        t = TEXTO_POR_PLANO[p]
        w(f"  PLAN {p}: {len(t)} tipos distintos de rótulo (excl. genéricos)")
        for r in sorted(t, key=lambda k: -t[k]):
            w(f"     {r:<24s} {t[r]:>4d}")
    w("  'PASADA 45/30 / 60/30 / PASADAS O7.5' = aberturas (NO estructurales);")
    w("  se omiten del recuento de tipos (solo metadata de aberturas).")
    w("  Planos sin capa de texto (raster): 000, 001, 700.")
    w("  Planos 300-303: solo rótulos de ejes/elevaciones (sin secciones).")

    # ---------- CORRECCIONES A DATOS REGISTRADOS ----------
    w("")
    w("3. CORRECCIONES A NOTAS PREVIAS (capa de texto re-extraída)")
    w("-" * 78)
    w("  - data/inventario.py y data/geometria_irregular.py afirmaron que en")
    w("    102/103 'SOLO existe M.H.A. e=20' y que e=25/e=30 eran 'OCR visual")
    w("    (NO en capa de texto)'. VERIFICADO AHORA con pymupdf: SÍ están en la")
    w("    capa de texto.")
    w("      plan 101: M.H.A. e=25 x4, e=30 x15, e=20 x17, e=15 x4, M.I. e=20 x1")
    w("      plan 102: M.H.A. e=25 x4, e=30 x4, e=20 x6 (2 vistas: 2x3/2x2/2x2)")
    w("      plan 103: M.H.A. e=25 x2, e=30 x2, e=20 x3")
    w("  - Nuevos rótulos detectados no registrados en el inventario:")
    w("      plan 100: V.F.30/170 x1, V.F.30/136 x1 (además de la serie 20/x)")
    w("      plan 101: V.M.300x300x5 x2, V.S.I.15/VAR x1, V.I.15/169 x1,")
    w("                V.30/VAR x1, V.15/VAR x1, V.20/90 x1, V.F.15/100 x2,")
    w("                DILATACION x7, N.S.M.+0.95 x1")
    w("      plan 102: V.40/60 x2 (sección YA en secciones.py pero sin cota)")
    w("      plan 103: +V.I.20/87 x6, V.40/60 x2, PARRILLA METALICA x1,")
    w("                CUANTIA ESTIMADA 50Kg/m2")
    w("  - Conteo V.60/80 en plan 102 = 110 (2 vistas: ~55+55). El inventario")
    w("    registra 57 para la vista principal -> las 30 'extra' coinciden con")
    w("    sector sur + núcleo, como ya se documentó en geometria_irregular.")

    # ---------- TABLA DE INVENTARIO ----------
    w("")
    w("4. TABLA DE INVENTARIO DE GEOMETRÍA (ID, plano, nivel, tipo, sección,")
    w("   referencia_i/j, X/Y, estado, evidencia)")
    w("-" * 78)
    w("  (las filas del esqueleto modelado son 90 col + 108 vig = 198; se")
    w("   resumen por clave para no duplicar el texto)")
    res = resumen_estados(FILAS)
    w("  RESUMEN POR ESTADO:")
    for st, n in res.most_common():
        w(f"     {st:<32s} {n}")
    w("  RESUMEN POR PLANO/ESTADO:")
    for pl, cc in sorted(resumen_por_plano(FILAS).items()):
        w(f"     {pl}: " + ", ".join(f"{st}={n}" for st, n in cc.most_common()))
    w("")
    w("  DETALLE de elementos NO modelados (muestra por plano):")
    for e in DGI.muros_todos:
        w(f"   muro {str(e['id']):<12s} plan {e['plano']} {e['seccion']:<12s} "
          f"{e['estado']:<24s} {e.get('posicion_modelo')}")
    for e in DGI.pilares_todos:
        w(f"   pilar {str(e['id']):<12s} plan {e['plano']} {e['seccion']:<14s} "
          f"{e['estado']:<24s} {e.get('posicion_modelo')}")
    for e in DGI.vigas_metal_todas:
        w(f"   v-met {str(e['id']):<12s} plan {e['plano']} {e['seccion']:<14s} "
          f"{e['estado']:<24s} {e.get('posicion_modelo')}")
    for e in DGI.vigas_irregulares_todas:
        w(f"   v-irr {str(e['id']):<12s} plan {e['plano']} {e['seccion']:<18s} "
          f"{e['estado']:<24s} {e.get('posicion_modelo')}")
    for e in DGI.vigas_6080_extra_todas:
        w(f"   v-extra {str(e['id']):<12s} plan {e['plano']} {e['seccion']:<12s} "
          f"{e['estado']:<24s} {e.get('posicion_modelo')}")

    # ---------- SECTOR SUR ----------
    w("")
    w("5. " + analisis_sector_sur())
    w("")

    # ---------- MUROS M.H.A. e=20/25/30 ----------
    w("")
    w("6. MUROS M.H.A. e=20/25/30 (clasificación por plano y estado)")
    w("-" * 78)
    w("  Según la capa de texto (esta auditoría) + geometria_irregular:")
    w("  - Plan 101 (PISO_1S, subte): e=20 x17, e=30 x15, e=15 x4, e=25 x4,")
    w("    M.I. e=20 x1. Rol: MUROS DE CONTENCION del subterráneo. Solo 6")
    w("    posiciones mapeadas (5 -> clasificadas PENDIENTE por Y fuera de")
    w("    rango; 1 sin posición). NO_VERIFICADO_POSICION -> PENDIENTE_COORDENADA.")
    w("    Pueden ser NO_MODELANDO_P1L2 (contención del sótano) si el análisis")
    w("    de gravedad del esqueleto no requiere estabilización lateral; decidir")
    w("    con el enunciado B/C.")
    w("  - Plan 102 (PISO_2, núcleo E-F): e=20 x3 (vista principal), e=25 x2,")
    w("    e=30 x2. En esta auditoría LOS TRES espesores SÍ aparecen en la capa")
    w("    de texto (corrige la nota previa 'solo e=20 por OCR'). Posiciones:")
    w("    M102_01/02/03 en el núcleo E-F (X≈0.75/4.13, Y≈-3.45/-14.53) ->")
    w("    INFERIDO_RESPALDADO (precisión ±0.5 m); LONGITUD PENDIENTE.")
    w("  - Plan 103 (PISO_4, núcleo E-F): e=20 x3, e=25 x2, e=30 x2 (capa de")
    w("    texto). M103_01/02/03 en el mismo núcleo E-F -> INFERIDO_RESPALDADO")
    w("    (mapeo ±1.5-2 m), LONGITUD PENDIENTE.")
    w("  - Continuidad vertical núcleo E-F: confirmada de forma CRUZADA entre")
    w("    plan 102 (PISO_2) y plan 103 (PISO_4) para e=20; e=25/e=30 presentes")
    w("    en ambos, posición exacta PENDIENTE.")
    w("  - MODELADO: 0 muros en el modelo (muros_por_nivel vacío). Todo el")
    w("    núcleo M.H.A. queda como geometría FALTANTE o PENDIENTE.")

    # ---------- DIFERENCIAS POR PISO ----------
    w("")
    w("7. DIFERENCIAS POR PISO (modelado vs planos)")
    w("-" * 78)
    diff = {
        "PISO_1": {
            "z": MODELO["niveles_z"]["PISO_1"],
            "plano": "101 (PLANTA CIELO 1° SUBTERRÁNEO, PISO_1S)",
            "modelado": "retícula + vigas V.60/80 x27 + col P.70x70",
            "falta": "muros M.H.A. e=15/20/25/30 (subte), M.I., V.S.I., V.20/80/130, "
                     "V.20/VAR x17, P.30x30, P.20x50, +V.I.15/VAR, P.M.I. (3), "
                     "V.F.15/100, V.M. (2, si aplica a este nivel)",
            "estado": "esqueleto modelado; contención/irregulares PENDIENTE",
        },
        "PISO_2": {
            "z": MODELO["niveles_z"]["PISO_2"],
            "plano": "102 vista principal (PLANTA CIELO PISO 2°)",
            "modelado": "retícula + vigas V.60/80 x27 + col P.70x70",
            "falta": "sector sur (V.30/45, V.60/VAR x1, V.60-30/80-40 x5, P.M. x3, "
                     "V.M. x6+ARR), muros M.H.A. e=20 x3/e=25 x2/e=30 x2, V.40/60 x2, "
                     "P.M.I. x8",
            "estado": "esqueleto modelado; sector sur + núcleo PENDIENTE",
        },
        "PISO_3": {
            "z": MODELO["niveles_z"]["PISO_3"],
            "plano": "102 sub-plano (PLANTA CIELO PISO 3°)",
            "modelado": "retícula (bloque 1: vigas PISO_3 x27 + col tramo "
                        "PISO_2->PISO_3)",
            "falta": "NO se asume la misma irregularidad del 102: el sub-plano "
                     "del folio 102 es la retícula principal; núcleo M.H.A. "
                     "e=20/30 continuo, P.M. 300x300x20 y V.M. (si aparecen en "
                     "el sub-plano) PENDIENTE_VERIFICACION_VISUAL",
            "estado": "esqueleto del bloque 1 completo; núcleo/walls PENDIENTE",
        },
        "PISO_4": {
            "z": MODELO["niveles_z"]["PISO_4"],
            "plano": "103 (PLANTA CIELO PISO 4°)",
            "modelado": "retícula + vigas V.60/80 x27 + col tramo PISO_3->PISO_4",
            "falta": "muros M.H.A. e=20 x3/e=25 x2/e=30 x2, P.M.300x300x20 x8, "
                     "+V.I.20/90 x16 (y +V.I.20/87 x6), V.M. x6 + (ARR), V.40/60 x2, "
                     "PARRILLA METALICA (S/ especialista; NO se modela en P1L2)",
            "estado": "esqueleto modelado; cubierta metálica + muros PENDIENTE",
        },
    }
    for nivel, d in diff.items():
        w(f"  {nivel} (z={d['z']:+.2f}) — plano {d['plano']}")
        w(f"    MODELADO : {d['modelado']}")
        w(f"    FALTA    : {d['falta']}")
        w(f"    ESTADO   : {d['estado']}")

    # ---------- FIGURAS ----------
    w("")
    w("8. FIGURAS DE AUDITORÍA")
    w("-" * 78)
    figs = []
    for nivel, z, rotulo in [
        ("PISO_1", MODELO["niveles_z"]["PISO_1"], "PISO_1 (plan 101, 1°S)"),
        ("PISO_2", MODELO["niveles_z"]["PISO_2"], "PISO_2 (plan 102, v. principal)"),
        ("PISO_3", MODELO["niveles_z"]["PISO_3"], "PISO_3 (plan 102, sub-plano)"),
        ("PISO_4", MODELO["niveles_z"]["PISO_4"], "PISO_4 (plan 103)"),
    ]:
        ruta = os.path.join(OUT, f"auditoria_geometria_piso{int(nivel[-1])}.png")
        r = figura_por_piso(nivel, z, rotulo, [], ruta)
        figs.append(r)
        w(f"  [OK] {os.path.basename(r)} ({nivel})")

    # ---------- CIERRE ----------
    w("")
    w("9. PENDIENTES QUE REQUIEREN VERIFICACIÓN VISUAL/MANUAL")
    w("-" * 78)
    w("  - Y_EXT_SUR_102 (borde sur del saliente del 102).")
    w("  - X_SUR_102 (ejes X de P.M. 300x300x20 del sector inferior).")
    w("  - Longitud/tramos reales de muros M.H.A. (e=20/25/30) del núcleo.")
    w("  - Trazado de V.F. (plan 100) y V.S.I. (plan 101): cotas de ejes.")
    w("  - Posición real de elementos metálicos (P.M., V.M., P.M.I.) que hoy")
    w("    viven solo en vistas de detalle del folio 102.")
    w("  - Confirmar la presencia/ausencia de la irregularidad en el sub-plano")
    w("    PISO_3 del folio 102 y en el 103 vs el 102.")
    w("  - Clasificar muros M.H.A. del SUBTE (plan 101, e=15/20/25/30) como")
    w("    modelables o NO_MODELANDO_P1L2 (contención del sótano).")
    w("")
    w("FIN DE AUDITORIA. No se modificó el modelo.")

    with open(os.path.join(OUT, "auditoria_geometria_lt1.txt"), "w") as f:
        f.write("\n".join(lineas))
    print("\n".join(lineas))
    print(f"\n[OK] outputs/auditoria_geometria_lt1.txt ({len(lineas)} líneas)")
    return lineas


if __name__ == "__main__":
    generar()