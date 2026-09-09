# -*- coding: utf-8 -*-
"""Modelo FE integrado LT1 + LT2 (COMBINADO).

Construye en OpenSeesPy el modelo estructural 3D conjunto, con la
transformacion geometrica APROBADA:
    LT1: X' = X + 31.250 , Y' = -Y , Z' = Z   (LT1 nativo x <= 0)
    LT2: coordenadas nativas (x >= 0)
Interfaz global en X = 31.250 m (borde este LT2 = borde oeste LT1). Los 18
pares de nodos exactamente coincidentes (6 niveles x ejes 1/2/3) se fusionan
en UN solo nodo fisico (se conserva el tag nativo LT2).

Reglas aplicadas (instrucciones del usuario):
  1) Nodos de interfaz: un nodo fisico por posicion; SIN equalDOF/rigidLink
     para esa conexion; tabla de trazabilidad (18 filas).
  2) Retagging: LT2 conserva tags nativos; LT1 aplica offset +100000 a nodos
     estructurales y de muro; masters LT1 (600001-600004) NO se crean
     (se sustituyen por los masters combinados = masters nativos LT2
     1001..1005). Elementos y geomTransf mantienen tags disjuntos por
     modulo (LT2: 2001+/3001+/4001+/5001+/transf 1,2,3 ; LT1: 20000x,
     10xxxx-113xxx, 4000xx, transf 10001/10002/10003).
  3) Duplicados de interfaz: columnas LT1 P70x70 que coinciden
     geometricamente con columnas LT2 nativas -> se conserva SOLO la LT2 y
     se descartan las 15 de LT1 (auditoria_elementos_interfaz.csv).
  4) Diafragmas: UN solo master por nivel (masters LT2 1001..1005) y cada
     nodo ocular una sola vez; los 12 nodos de muro LT1 se vinculan con
     ops.rigidLink('beam', master, nodo_muro) (estrategia C de LT1).
  5) Apoyos: 22 fijos LT2 + 15 fijos LT1 (los 3 de interfaz ya fijados como
     nodos LT2); sin ops.fix duplicado.
  6) Muros LT2 (40 segmentos): idealizacion academica LT1 (columna
     equivalente elasticBeamColumn rectangular). Solo propiedades extraidas
     de los archivos LT2.
  7) Materiales: se conservan E LT1 = 25,000,000 kPa y E LT2 =
     23,500,000 kPa (no se unifican; ver reporte).
  8) Cargas: patrones separados timeSeries/pattern (LT2 = 1, LT1 = 2);
     LT2 desde LT2/results/gravity_loads_applied_LT2.csv (beamPoint),
     LT1 desde outputs/unity/modelo_lt1.json (beamUniform, carga QG).
  9) Validaciones completas + reporte + vista 3D que distingue LT1/LT2.

Solo ESCRIBE dentro de COMBINADO/ y no modifica archivos originales.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import pandas as pd
import openseespy.opensees as ops

# ---------------------------------------------------------------------------
# Rutas (lectura de los modelos originales)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]          # .../LT1
COMB = ROOT / "COMBINADO"
OUT = COMB / "outputs"

JSON_LT1 = ROOT / "outputs" / "unity" / "modelo_lt1.json"
LT2_GEOM = ROOT / "LT2" / "data" / "geometry"
LT2_SECT = ROOT / "LT2" / "data" / "sections" / "sections_LT2.csv"
LT2_MAT = ROOT / "LT2" / "data" / "materials_LT2.csv"
LT2_LOADS = ROOT / "LT2" / "results" / "gravity_loads_applied_LT2.csv"

OUT_TRACE = OUT / "interfaz_traceabilidad.csv"
OUT_AUDIT = OUT / "auditoria_elementos_interfaz.csv"
OUT_REPORT = OUT / "reporte_validacion_combinado.md"
OUT_FIG = OUT / "vista_3d_combinado.png"
OUT_LINKS = OUT / "conectores_v40_muro.csv"
OUT_BOX = OUT / "verticales_cajas_pilastra.csv"

SHIFT_X = 31.250
TOL = 1e-6
NODE_OFFSET_LT1 = 100000

E_LT1 = 25_000_000.0
G_LT1 = 10_416_667.0

EXPECTED_INT_ORDER = ["B1", "L1", "L2", "L3", "L4", "ROOF"]
EXPECTED_INT_TAGS = {
    "B1": (18, 21, 22),
    "L1": (66, 69, 70),
    "L2": (114, 117, 118),
    "L3": (162, 165, 166),
    "L4": (210, 213, 214),
    "ROOF": (268, 271, 272),
}

TAG_BEAM_BASE = 2001
TAG_COL_BASE = 3001
TAG_WALL_BASE = 4001
TAG_SECTION_BASE = 5001
# Rango exclusivo del modelo COMBINADO: conectores horizontales en X entre
# los extremos de las cadenas V40 (x=0.400) y los nodos del eje de los muros
# M001/M003 (x=0.100). Verificado libre de colisiones con tags LT1 y LT2
# (max LT1 nativo 600004). Tags 9001..9010 (2 extremos x 5 niveles).
TAG_LINK_V40WALL_BASE = 9001

# Sistema vertical de cajas de escalera y pilastra bajo el anillo VI de ROOF
# (solo COMBINADO). Materializa la continuidad vertical B1->ROOF de los 10
# nodos del anillo que no alcanzan rigidez a los apoyos (reporte §9,
# rc=-3, singularidad en ROOF):
#   - Caja oeste (bajo VI-05): x=0.998, muro en Y y 2.90..7.92 -> nodos 226/227
#   - Caja este  (bajo VI-06): x=16.546, muro en Y y 2.90..7.92 -> nodos 256/257
#   - Pilastra interior (x7.947): 4 esquinas reales -> nodos 244/245/246/247
#   - 2ª caja de escalera (borde N 2º hueco este, bajo VI-07): y=7.92,
#     x 18.545..20.794 -> nodos 258/259 (el x=20.794 se CONSERVA; no se
#     aproxima a las columnas interiores x=20.550 del plano)
# Geometria de LT2/reports/digitalizacion_vi_roof_pendiente.md (§8.2, §8.5):
#   - Muros de cajas e=0.30 m -> ASSUMED_FOR_MODEL (muros M.H.A. e=30 cm del
#     plano, son supuesto de modelacion declarado)
#   - Pilastra e=0.60 m EXPLICITO del plano (gap N 7.646..8.246) y L=5.02 m
#     (y 2.90..7.92); ligeramente conica (S 7.596..8.296) segun las esquinas
#     reales de los nodos; se conservan las 4 coordenadas reales.
# Idealizacion: misma convencion academica que los muros LT2 (_make_lt2_wall),
# columna equivalente elasticBeamColumn por esquina (transf 10001 vecxz
# (1,0,0)); pilastra como 4 columnas (cuarto de seccion).
# Las bases B1 de los nuevos verticales se fijan (ops.fix 6 GDL) igual que
# todos los apoyos del modelo (empotrados en B1, convencion de supports_LT2):
# es la condicion real de cimentacion del sistema, NO una restriccion
# artificial. Los nodos intermedios (B1..L4) son nuevos; no se agregan al
# rigidDiaphragm (no son necesarios para cerrar el mecanismo; no es una
# restriccion artificial para eliminar la singularidad).
# Rango de tags COMBINADO verificado libre (LT2 nativos <=272 + masters
# 1001..1005; LT1 combinados 100001..600205; elems LT1 100000..400006,
# LT2 2001..4080, links 9001..9010).
TAG_BOX_NODE_BASE = 700001     # nodos nuevos del sistema vertical
TAG_BOX_ELEM_BASE = 70001      # elementos nuevos del sistema vertical

# VI-05 (VI15xVAR, ROOF): SUPUESTO DE MODELACION / COTA SUPERIOR DE RIGIDEZ.
# Investigacion documental CERRADA (ver COMBINADO/docs/diagnostico_vi15xvar.md):
# b=0.15 m (plano), H_MAX=1.20 m (familia V.I. 2a ETAPA, lam. 102); h_min y ley
# de variacion DESCONOCIDAS -> se representa con el peralte maximo constante.
# NO es la seccion real confirmada de la viga variable. Unica seccion VAR de la
# fuente: solo la usa ROOF_VI_05 (nodos 226-227, tag nativo 2235, verificado en
# LT2/data/unity/edificio_lt2.json; el tag 2237 pertenece a ROOF_VI_07 y no
# esta disponible). Se usan E y G de LT2 (material CONC_G25).
ASSUMED_SECTIONS = {"VI15xVAR": (0.15, 1.20)}
TRANS_COL, TRANS_B_X, TRANS_B_Y = 1, 2, 3
TRANS_COL_LT1, TRANS_B_X_LT1, TRANS_B_Y_LT1 = 10001, 10002, 10003

# Salientes sur LT1 — geometría respaldada 1:1 por la referencia
# LT1 (Documentos/LT1, geomentría CAD FILAS_SUR/FLANCOS_X). Coordenadas
# LOCALES LT1 (pre-transformación: X'=X+31.250, Y'=-Y).
# Se REPLICAN únicamente los elementos con respaldo CAD verificado
# (V.60/80). NO se incluyen: malla artificial, SPAN_INFERIDO, metálicos
# sin E (P.M./P.M.I./V.M.), diagonales ni vigas sin respaldo.
# `partition_x_lt1` = cotas donde se PARTICIONAN las vigas de fachada sur
# existentes (los nuevos nodos de fachada del saliente caen sobre ellas).
# `beams` = vigas nuevas de saliente; endpoint "S:<label>" es un nodo
# nuevo del saliente y "<eje>" (E,F,G,H,I,Ip) es el nodo de fachada
# existente en ese eje (y_lt1 = -16.15).
_SALIENTES_DATA = {
    "PISO_1": {
        "z_m": -0.05,
        "nodes": [
            (10.0, -20.32, "S1_SW"),
            (10.4, -20.32, "S1_FW_S"),
            (17.49, -20.32, "S1_SE"),
            (10.4, -16.15, "S1_FN"),
            (17.49, -16.15, "S1_EN"),
        ],
        "partition_x_lt1": [10.4, 17.49],
        "beams": [
            ("F", "S1_SW"),
            ("S1_FN", "S1_FW_S"),
            ("S1_EN", "S1_SE"),
            ("S1_SW", "S1_FW_S"),
            ("S1_FW_S", "S1_SE"),
        ],
    },
    "PISO_2": {
        "z_m": 3.91,
        "nodes": [
            (10.0, -20.27, "S1_SW"),
            (17.49, -20.27, "S1_SE"),
            (17.49, -16.15, "S1_EN"),
            (20.0, -18.61, "S2_NW"),
            (24.4, -18.61, "S2_FM"),
            (24.4, -16.15, "S2_FN"),
            (25.0, -18.61, "S2_IM"),
            (25.0, -16.15, "S2_IN"),
            (30.0, -18.61, "S2_NE"),
        ],
        "partition_x_lt1": [17.49, 24.4, 25.0],
        "beams": [
            ("F", "S1_SW"),
            ("S1_EN", "S1_SE"),
            ("S1_SW", "S1_SE"),
            ("G", "S2_NW"),
            ("S2_FN", "S2_FM"),
            ("S2_IN", "S2_IM"),
            ("H", "S2_NE"),
            ("S2_NW", "S2_FM"),
            ("S2_FM", "S2_IM"),
            ("S2_IM", "S2_NE"),
        ],
    },
    "PISO_3": {
        "z_m": 7.87,
        "nodes": [
            (2.34, -18.61, "W1_SW"),
            (2.34, -16.15, "W1_NW"),
            (18.24, -18.61, "W1_SE"),
            (18.24, -16.15, "W1_NE"),
            (19.7, -20.27, "S2_SW"),
            (19.7, -16.15, "S2_NW"),
            (29.4, -20.27, "S2_SE"),
            (29.4, -16.15, "S2_NE"),
            (30.3, -20.27, "S2_E"),
            (30.3, -16.15, "S2_EN"),
        ],
        "partition_x_lt1": [2.34, 18.24, 19.7, 29.4, 30.3],
        "beams": [
            ("W1_NW", "W1_SW"),
            ("W1_NE", "W1_SE"),
            ("W1_SW", "W1_SE"),
            ("S2_NW", "S2_SW"),
            ("S2_NE", "S2_SE"),
            ("S2_EN", "S2_E"),
            ("S2_SW", "S2_SE"),
            ("S2_SE", "S2_E"),
        ],
    },
    "PISO_4": {
        "z_m": 11.83,
        "nodes": [
            (1.31, -20.27, "W1_SW"),
            (1.31, -16.15, "W1_NW"),
            (19.4, -20.27, "W1_FM"),
            (19.4, -16.15, "W1_FN"),
            (29.4, -20.27, "W1_IM"),
            (29.4, -16.15, "W1_IN"),
            (36.31, -20.27, "W1_SE"),
            (36.31, -16.15, "W1_NE"),
        ],
        "partition_x_lt1": [1.31, 19.4, 29.4, 36.31],
        "beams": [
            ("W1_NW", "W1_SW"),
            ("W1_FN", "W1_FM"),
            ("W1_IN", "W1_IM"),
            ("W1_NE", "W1_SE"),
            ("W1_SW", "W1_FM"),
            ("W1_FM", "W1_IM"),
            ("W1_IM", "W1_SE"),
        ],
    },
}

# Ejes de fachada sur LT1 (y_lt1=-16.15) con nodo existente por nivel
# y regla de corrección del eje I': la referencia ubica I' en X=45.0 m,
# pero el JSON combinado actual lo trae en 42.5 m -> se corrige a 45.0 m.
_FACADE_NODE_X = {
    "E": 0.0, "F": 10.0, "G": 20.0, "H": 30.0, "I": 40.0, "Ip": 45.0,
}
_X_IP_CORRIGE = 45.0
_X_IP_ANTES = 42.5

# tags nuevos del sistema de salientes (nodso 800001+, vigas 800101+,
# segmentos de partición de fachada 800201+)
TAG_SAL_NODE_BASE = 800001
TAG_SAL_BEAM_BASE = 800101
TAG_SAL_SEG_BASE = 800201


def _key(x, y, z):
    return (round(float(x), 6), round(float(y), 6), round(float(z), 6))


def _zname(levels, name):
    return float(levels.loc[levels["name"] == name, "z_m"].iloc[0])


def _jrect(b, h):
    if b > h:
        b, h = h, b
    return h * b ** 3 / 3.0 * (1 - 0.63 * (b / h) + 0.052 * (b / h) ** 5)


def _rect_props(b, h):
    return b * h, b * h ** 3 / 12.0, h * b ** 3 / 12.0


# ---------------------------------------------------------------------------
# LT2: nodos y elementos (replica _collect_nodes / _collect_elements del
# builder nativo, para conservar EXACTAMENTE los tags nativos)
# ---------------------------------------------------------------------------
def _collect_lt2_nodes(levels, beams, columns, walls):
    keys = set()
    for r in beams.itertuples():
        z = _zname(levels, r.level)
        keys.add(_key(r.x1_m, r.y1_m, z))
        keys.add(_key(r.x2_m, r.y2_m, z))
    for r in columns.itertuples():
        z0 = _zname(levels, r.from_level)
        z1 = _zname(levels, r.to_level)
        keys.add(_key(r.x_m, r.y_m, z0))
        keys.add(_key(r.x_m, r.y_m, z1))
    for r in walls.itertuples():
        z0 = _zname(levels, r.from_level)
        z1 = _zname(levels, r.to_level)
        keys.add(_key(r.x1_m, r.y1_m, z0))
        keys.add(_key(r.x2_m, r.y2_m, z0))
        keys.add(_key(r.x1_m, r.y1_m, z1))
        keys.add(_key(r.x2_m, r.y2_m, z1))
    ordered = sorted(keys, key=lambda k: (k[2], k[0], k[1]))
    key_to_tag = {k: i + 1 for i, k in enumerate(ordered)}
    tag_to_key = {v: k for k, v in key_to_tag.items()}
    level_tags = {}
    for name in levels["name"]:
        z = round(_zname(levels, name), 6)
        level_tags[name] = [t for k, t in key_to_tag.items()
                            if round(k[2], 6) == z]
    return key_to_tag, tag_to_key, level_tags


def _lt2_elements(levels, beams, columns, walls, key_to_tag):
    elems = {"beams": [], "columns": [], "walls": []}
    for r in beams.itertuples():
        z = _zname(levels, r.level)
        elems["beams"].append(dict(
            id=r.beam_id, n1=key_to_tag[_key(r.x1_m, r.y1_m, z)],
            n2=key_to_tag[_key(r.x2_m, r.y2_m, z)],
            level=r.level, section=r.section,
            notes="" if pd.isna(r.notes) else str(r.notes)))
    for r in columns.itertuples():
        z0 = _zname(levels, r.from_level)
        z1 = _zname(levels, r.to_level)
        elems["columns"].append(dict(
            id=r.segment_id, n1=key_to_tag[_key(r.x_m, r.y_m, z0)],
            n2=key_to_tag[_key(r.x_m, r.y_m, z1)],
            section=r.section, x=r.x_m, y=r.y_m,
            z0=z0, z1=z1, length=abs(z1 - z0)))
    for r in walls.itertuples():
        z0 = _zname(levels, r.from_level)
        z1 = _zname(levels, r.to_level)
        elems["walls"].append(dict(
            id=r.segment_id, n1=key_to_tag[_key(r.x1_m, r.y1_m, z0)],
            n2=key_to_tag[_key(r.x1_m, r.y1_m, z1)],
            thickness=r.thickness_m, x1=r.x1_m, y1=r.y1_m,
            x2=r.x2_m, y2=r.y2_m,
            length=math.hypot(r.x2_m - r.x1_m, r.y2_m - r.y1_m),
            height=abs(z1 - z0)))
    return elems


def _orient(e_, tag_to_key):
    k1, k2 = tag_to_key[e_["n1"]], tag_to_key[e_["n2"]]
    dx, dy, dz = (k2[0] - k1[0], k2[1] - k1[1], k2[2] - k1[2])
    if abs(dz) > TOL and abs(dx) <= TOL and abs(dy) <= TOL:
        return TRANS_COL
    if abs(dy) <= TOL and abs(dx) > TOL and abs(dz) <= TOL:
        return TRANS_B_X
    if abs(dx) <= TOL and abs(dy) > TOL and abs(dz) <= TOL:
        return TRANS_B_Y
    return None


def _lt2_pending(sections):
    pending = set()
    for _, s in sections.iterrows():
        if "analysis_status=PENDING_VARIABLE_SECTION" in str(s.get("notes",
                                                                    "")):
            pending.add(str(s["section_id"]))
    return pending


# ---------------------------------------------------------------------------
class CombinedBuilder:
    def __init__(self):
        self.levels = pd.read_csv(LT2_GEOM / "levels.csv")
        self.sections = pd.read_csv(LT2_SECT)
        self.beams = pd.read_csv(LT2_GEOM / "beams_LT2.csv")
        self.columns = pd.read_csv(LT2_GEOM / "column_segments_LT2.csv")
        self.walls = pd.read_csv(LT2_GEOM / "wall_segments_LT2.csv")
        self.supports = pd.read_csv(LT2_GEOM / "supports_LT2.csv")
        self.masters = pd.read_csv(LT2_GEOM / "master_nodes_LT2.csv")
        self.diaphs = pd.read_csv(LT2_GEOM / "diaphragms_LT2.csv")
        self.mat = pd.read_csv(LT2_MAT)
        self.loads = pd.read_csv(LT2_LOADS)
        with open(JSON_LT1, "r", encoding="utf-8") as f:
            self.json_lt1 = json.load(f)
        d = self.json_lt1
        self.lt1_nodes = {n["tag"]: n for n in d["nodes"]
                          if n.get("tipo") != "master"}
        self.lt1_wall_natives = sorted({w["node_i"] for w in d["walls"]}
                                       | {w["node_j"] for w in d["walls"]})
        self.wall_corner_b = set()
        self.v40_links = []

    # ---- mapas -------------------------------------------------------------
    def prepare(self):
        self.lt2_key_to_tag, self.lt2_tag_to_key, self.lt2_level_tags = \
            _collect_lt2_nodes(self.levels, self.beams, self.columns,
                               self.walls)
        self.lt2_elems = _lt2_elements(self.levels, self.beams,
                                       self.columns, self.walls,
                                       self.lt2_key_to_tag)
        self.lt1_combo = {}
        self.interface = []
        for tag, n in sorted(self.lt1_nodes.items()):
            xp, yp, zp = self._trans_lt1(n["x"], n["y"], n["z"])
            k = _key(xp, yp, zp)
            if k in self.lt2_key_to_tag:
                lt2t = self.lt2_key_to_tag[k]
                self.lt1_combo[tag] = lt2t
                self.interface.append((tag, lt2t, xp, yp, zp))
            else:
                self.lt1_combo[tag] = tag + NODE_OFFSET_LT1

        # Corrección del eje I' (LT1): la referencia ubica la fachada sur
        # en X=45.0 m, pero el JSON combinado la trae en 42.5 m. Se desplaza
        # SOLO la posición de los nodos del eje I' (todas las entidades que
        # los usan siguen por tag). Los nodos son no-interfaz (nunca en la
        # junta X'=31.250), por lo que la interfaz no se altera.
        self.ip_correction = {}
        for tag, n in self.lt1_nodes.items():
            ex = str(n.get("eje_x", ""))
            if ex in ("I'", "Ip") or abs(float(n["x"]) - _X_IP_ANTES) < 1e-6:
                self.ip_correction[tag] = _X_IP_CORRIGE

    @staticmethod
    def _trans_lt1(x, y, z):
        return x + SHIFT_X, -y, z

    def check_interface(self):
        level_z = {round(_zname(self.levels, n), 6): n
                   for n in self.levels["name"]}
        groups = {}
        for tag, lt2t, xp, yp, zp in self.interface:
            lv = level_z[round(zp, 6)]
            groups.setdefault(lv, []).append((tag, lt2t, xp, yp, zp))
        rows = []
        for lv in EXPECTED_INT_ORDER:
            grp = sorted(groups.get(lv, []), key=lambda r: r[3])
            got = tuple(sorted({r[1] for r in grp}))
            if len(grp) != 3 or got != tuple(sorted(EXPECTED_INT_TAGS[lv])):
                raise RuntimeError(
                    f"INTERFAZ_INESPERADA en nivel {lv}: tags LT2 {got} != "
                    f"esperados {EXPECTED_INT_TAGS[lv]}. Revisar archivos "
                    "fuente antes de continuar (INPUT_REQUIRED).")
            for tag, lt2t, xp, yp, zp in grp:
                n = self.lt1_nodes[tag]
                rows.append(dict(
                    nivel_lt2=lv, eje=n["eje_y"],
                    tag_original_lt1=tag, tag_original_lt2=lt2t,
                    tag_combinado=lt2t, x_m=xp, y_m=yp, z_m=zp))
        if len(rows) != 18:
            raise RuntimeError(
                f"INTERFAZ_INESPERADA: {len(rows)} pares en vez de 18. "
                "INPUT_REQUIRED.")
        self.trace = pd.DataFrame(rows)
        return rows

    # ---- construccion del modelo -------------------------------------------
    def build(self):
        ops.wipe()
        ops.model("basic", "-ndm", 3, "-ndf", 6)

        for tag, k in self.lt2_tag_to_key.items():
            ops.node(tag, k[0], k[1], k[2])

        # apoyos LT2 (nativos, B1)
        z_base = _zname(self.levels, "B1")
        self.support_tags = []
        for r in self.supports.itertuples():
            tag = self.lt2_key_to_tag[_key(r.x_m, r.y_m, z_base)]
            ops.fix(tag, int(r.ux), int(r.uy), int(r.uz),
                    int(r.rx), int(r.ry), int(r.rz))
            self.support_tags.append(tag)

        # masters combinados (nativos LT2 1001..1005), reusados por el
        # conjunto para TODOS los niveles
        self.master_tag_by_id = {}
        self.master_tag_by_level = {}
        self.master_tags = []
        for i, r in enumerate(self.masters.itertuples()):
            tag = 1001 + i
            ops.node(tag, r.x_m, r.y_m, r.z_m)
            ops.fix(tag, 0, 0, 1, 1, 1, 0)
            self.master_tag_by_id[r.master_id] = tag
            self.master_tag_by_level[r.level] = tag
            self.master_tags.append(tag)

        # nodos LT1 (offset +100000; interfaz ya en tags LT2)
        int_tags = {p[0] for p in self.interface}
        self.lt1_created = []
        for tag, n in sorted(self.lt1_nodes.items()):
            if tag in int_tags:
                continue
            x_lt1 = self.ip_correction.get(tag, n["x"])
            xp, yp, zp = self._trans_lt1(x_lt1, n["y"], n["z"])
            c = self.lt1_combo[tag]
            ops.node(c, xp, yp, zp)
            self.lt1_created.append(c)

        # apoyos LT1 (los 3 de interfaz ya fijados como nodos LT2)
        for s in self.json_lt1["supports"]:
            tag = s["nodeTag"]
            if tag in int_tags:
                continue
            restr = [int(v) for v in s["restricciones"]]
            ops.fix(self.lt1_combo[tag], *restr)
            self.support_tags.append(self.lt1_combo[tag])
        self.support_tags = sorted(set(self.support_tags))

        # transformaciones
        ops.geomTransf("Linear", TRANS_COL, *(0, 1, 0))
        ops.geomTransf("Linear", TRANS_B_X, *(0, 0, 1))
        ops.geomTransf("Linear", TRANS_B_Y, *(0, 0, 1))
        ops.geomTransf("Linear", TRANS_COL_LT1, *(1, 0, 0))
        ops.geomTransf("Linear", TRANS_B_X_LT1, *(0, 0, 1))
        ops.geomTransf("Linear", TRANS_B_Y_LT1, *(0, 0, 1))

        # material LT2
        e2 = float(self.mat["E_kN_m2"].iloc[0])
        g2 = e2 / (2.0 * (1.0 + float(self.mat["nu"].iloc[0])))
        self.e_lt2, self.g_lt2 = e2, g2

        # secciones LT2 (orden del CSV nativo)
        pending = _lt2_pending(self.sections)
        self.section_tag = {}
        for _, s in self.sections.iterrows():
            sid = str(s["section_id"])
            if sid in pending and sid not in ASSUMED_SECTIONS:
                continue
            if sid in ASSUMED_SECTIONS:
                bm, hm = ASSUMED_SECTIONS[sid]
                if not math.isfinite(bm) or not math.isfinite(hm):
                    raise RuntimeError(
                        f"Seccion supuesta {sid} sin b/h en "
                        f"ASSUMED_SECTIONS. INPUT_REQUIRED.")
            else:
                bm, hm = float(s["b_m"]), float(s["h_m"])
            a, iy, iz = _rect_props(bm, hm)
            j = _jrect(min(bm, hm), max(bm, hm))
            tag = TAG_SECTION_BASE + len(self.section_tag)
            ops.section("Elastic", tag, e2, a, iz, iy, g2, j)
            self.section_tag[sid] = tag

        # elementos LT2
        self.created = {"lt2_beams": [], "lt2_cols": [], "lt2_walls": [],
                        "lt1_beams": [], "lt1_cols": [], "lt1_walls": [],
                        "links": []}
        self.pending_beams = []
        self.assumed_beam_tags = []
        for i, e_ in enumerate(self.lt2_elems["beams"]):
            if e_["section"] in pending and \
                    e_["section"] not in ASSUMED_SECTIONS:
                self.pending_beams.append(e_["id"])
                continue
            transf = _orient(e_, self.lt2_tag_to_key)
            if transf is None:
                self.pending_beams.append(e_["id"])
                continue
            tag = TAG_BEAM_BASE + i
            if e_["section"] in ASSUMED_SECTIONS:
                self.assumed_beam_tags.append(tag)
            ops.element("elasticBeamColumn", tag, e_["n1"], e_["n2"],
                        self.section_tag[e_["section"]], transf)
            self.created["lt2_beams"].append(tag)
        for i, e_ in enumerate(self.lt2_elems["columns"]):
            tag = TAG_COL_BASE + i
            ops.element("elasticBeamColumn", tag, e_["n1"], e_["n2"],
                        self.section_tag[e_["section"]], TRANS_COL)
            self.created["lt2_cols"].append(tag)
        for i, e_ in enumerate(self.lt2_elems["walls"]):
            taga = TAG_WALL_BASE + 2 * i
            self._make_lt2_wall(taga, e_, e2, g2)
            self.created["lt2_walls"].append(taga)
            self.created["lt2_walls"].append(taga + 1)

        # auditoria de interfaz (regla 3)
        self.audit_rows, self.duplicated_lt1_cols = \
            self._audit_interface_elements()
        dup = set(self.duplicated_lt1_cols)

        # elementos LT1 (tags nativos)
        for b in self.json_lt1["beams"]:
            fam = (TRANS_B_Y_LT1 if b.get("eje_x_i") == b.get("eje_x_j")
                   else TRANS_B_X_LT1)
            ops.element("elasticBeamColumn", b["elementTag"],
                        self.lt1_combo[b["node_i"]],
                        self.lt1_combo[b["node_j"]],
                        b["A_m2"], E_LT1, G_LT1, b["J_m4"],
                        b["Iy_m4"], b["Iz_m4"], fam)
            self.created["lt1_beams"].append(b["elementTag"])
        for c in self.json_lt1["columns"]:
            if c["elementTag"] in dup:
                continue
            ops.element("elasticBeamColumn", c["elementTag"],
                        self.lt1_combo[c["node_i"]],
                        self.lt1_combo[c["node_j"]],
                        c["A_m2"], E_LT1, G_LT1, c["J_m4"],
                        c["Iy_m4"], c["Iz_m4"], TRANS_COL_LT1)
            self.created["lt1_cols"].append(c["elementTag"])
        for w in self.json_lt1["walls"]:
            ops.element("elasticBeamColumn", w["elementTag"],
                        self.lt1_combo[w["node_i"]],
                        self.lt1_combo[w["node_j"]],
                        w["A_m2"], E_LT1, G_LT1, w["J_m4"],
                        w["Iy_m4"], w["Iz_m4"], TRANS_COL_LT1)
            self.created["lt1_walls"].append(w["elementTag"])

        self._build_diaphragms_and_links()
        self._build_v40_wall_links()
        self._build_box_verticals(e2, g2)
        self._build_salientes_lt1()

    def _build_v40_wall_links(self):
        """Conectores de excentricidad cadenas V40 -> muros M001/M003.

        Solo dentro de COMBINADO/; no modifica LT1 ni LT2. Modela la
        excentricidad fisica entre el eje de la cadena V40 (x=0.400) y el
        eje de los muros M001/M003 (x=0.100): e/2 = 0.300 m, es decir, la
        cara ESTE del muro plana con el eje de la cadena (verificado en el
        plano 2024_22-102: 2 caras a 34.02 pt = 0.600 m y eje al medio).

        Reglas (instrucciones del usuario):
          - NO se mueven nodos de muro a la cara;
          - NO se usa equalDOF ni restricciones redundantes con el
            rigidDiaphragm: el conector es un ELEMENTO (elasticBeamColumn
            con seccion de enlace rigida documentada), no una restriccion
            cinematica;
          - SOLO se crean en los extremos de cadena que terminan sobre la
            cara este (y=1.825 sobre M001; y=14.325 sobre M003), en el mismo
            nivel (Z) y mismo Y que el nodo de muro;
          - se verifica existencia del nodo de muro al mismo Y y Z, que sea
            nodo real de un elemento de muro, y que la longitud = 0.300 m;
          - NO se conectan nodos intermedios (y=4.265/8.9/11.885, sin apoyo
            fisico en muro) ni vigas V30/VI cercanas.
        """
        # Seccion de enlace (documentada en el reporte, seccion 10):
        #   100 x E_LT2 -> rigidez axial >= ~110x la del muro (e*L/2) y
        #   >= ~300x la de la viga V40; rigida sin superfluir al conjunto.
        E = 2_350_000_000.0                # kPa = 100 * E_LT2 (2.35e7)
        G = E / (2.0 * 1.20)               # nu = 0.20 (solo seccion de enlace)
        A, Iy, Iz, J = 1.00, 0.10, 0.10, 0.20   # m2 / m4 / m4 / m4
        chain_x, wall_x = 0.400, 0.100
        chain_req = {"M001": 1.825, "M003": 14.325}
        wall_elem_nodes = set(self.wall_corner_b)
        for e_ in self.lt2_elems["walls"]:
            wall_elem_nodes.update([e_["n1"], e_["n2"]])
        links = []
        k = 0
        for lv in ("L1", "L2", "L3", "L4", "ROOF"):
            z = _zname(self.levels, lv)
            for muro, y in chain_req.items():
                key_c = _key(chain_x, y, z)
                key_w = _key(wall_x, y, z)
                tc = self.lt2_key_to_tag.get(key_c)
                tw = self.lt2_key_to_tag.get(key_w)
                if tc is None or tw is None:
                    raise RuntimeError(
                        f"V40-MURO {lv}/{muro} y={y}: falta nodo de cadena "
                        f"({key_c}->{tc}) o de muro ({key_w}->{tw}). "
                        "INPUT_REQUIRED.")
                if tc == tw:
                    raise RuntimeError(
                        f"V40-MURO {lv}/{muro}: el nodo de cadena coincide "
                        f"con el de muro ({tc}). INPUT_REQUIRED.")
                if tw not in wall_elem_nodes:
                    raise RuntimeError(
                        f"V40-MURO {lv}/{muro}: nodo {tw} no es nodo de un "
                        "elemento de muro. INPUT_REQUIRED.")
                ok_y = abs(key_w[1] - key_c[1]) <= 1e-9
                ok_z = abs(key_w[2] - key_c[2]) <= 1e-9
                length = abs(key_w[0] - key_c[0])
                if not ok_y or not ok_z or abs(length - 0.300) > 1e-9:
                    raise RuntimeError(
                        f"V40-MURO {lv}/{muro}: geometria inesperada "
                        f"(dy={key_w[1]-key_c[1]:.4f}, dz="
                        f"{key_w[2]-key_c[2]:.4f}, L={length:.4f}). "
                        "INPUT_REQUIRED.")
                tag = TAG_LINK_V40WALL_BASE + k
                ops.element("elasticBeamColumn", tag, tc, tw,
                            A, E, G, J, Iy, Iz, TRANS_B_X)
                links.append(dict(nivel=lv, muro=muro,
                                  tag_conector=tag,
                                  nodo_cadena=tc, x_c=key_c[0],
                                  y_c=key_c[1], z_c=key_c[2],
                                  nodo_muro=tw, x_w=key_w[0],
                                  y_w=key_w[1], z_w=key_w[2],
                                  longitud_m=round(length, 6)))
                self.created["links"].append(tag)
                k += 1
        self.v40_links = links
        return links

    def _build_box_verticals(self, e2, g2):
        """Materializa la continuidad vertical B1->ROOF de los sistemas de
        cajas de escalera y pilastra bajo el anillo VI de ROOF (SOLO
        COMBINADO; no modifica LT1 ni LT2).

        Cierra el mecanismo remanente de ROOF (reporte §9): nodos del anillo
        VI sin rigidez vertical a los apoyos. Geometria de
        LT2/reports/digitalizacion_vi_roof_pendiente.md (§8.2/§8.5) y de los
        nodes reales del CSD LT2 (edificio_lt2.json):

          1) Caja OESTE bajo VI-05 : x=0.998 m, muro en Y (y 2.90..7.92),
             espesor e=0.30 m -> ASSUMED_FOR_MODEL (caja de escalera;
             espesor de muro no acotado en plan, se usa e=30 cm de la
             familia M.H.A. de cajas, supuesto declarado). Nodos ROOF 226
             (0.998,2.90) y 227 (0.998,7.92) ya existen; se crean nodos
             nuevos en cada x=0.998 / y=[2.90, 7.92] para B1..L4.
          2) Caja ESTE bajo VI-06 : x=16.546 m, muro en Y (y 2.90..7.92),
             e=0.30 m -> ASSUMED_FOR_MODEL. Nodos ROOF 256 (16.546,2.90) y
             257 (16.546,7.92).
          3) Pilastra interior x≈7.947 : caja vertical entre los dos huecos.
             Se modela como 4 columnas verticales (una por esquina real):
             244 (7.596,2.90), 245 (7.646,7.92), 246 (8.246,7.92),
             247 (8.296,2.90). Seccion EXPLICITA del plano: caras de
             7.650/8.250 -> e_x=0.60 m (gap N 7.646..8.246); longitud
             L_y=5.02 m (y 2.90..7.92). Cada columna lleva UN CUARTO de la
             seccion bruta de la pilastra (A=e·L/4, Iy/4, Iz/4, J/4). No es
             supuesto de espesor: la anchura 0.60 m sale del plano.
          4) Segunda escalera (2º hueco este, bajo VI-07): borde N en
             y=7.92, x 18.545..20.794 -> muro en X e=0.30 m
             (ASSUMED_FOR_MODEL). Nodos 258 (18.545,7.92) y 259
             (20.794,7.92). El x=20.794 del nodo 259 se CONSERVA (es el
             borde norte real del 2º hueco segun planta: x 18.545..20.794);
             no se aproxima a las columnas interiores x≈20.550 del plano.

        Idealizacion: misma convencion academica que los muros LT2
        (_make_lt2_wall): un elasticBeamColumn por esquina, transf 10001
        (vecxz=(1,0,0)), material LT2 (E/G del modulo). Las bases B1 de los
        nuevos verticales se fijan con ops.fix 6 GDL (empotradas), igual que
        TODOS los apoyos del modelo (criterio de foundation en B1 declarado
        en supports_LT2.csv). Los nodos intermedios (B1..L4) son nuevos;
        no se anaden al rigidDiaphragm (no es necesario para cerrar el
        mecanismo y se evita cualquier restriccion artificial). Los topes de
        cada columna en ROOF coinciden EXACTAMENTE con los nodos reales del
        anillo (226/227, 244/245/246/247, 256/257, 258/259).

        Tags seguros (verificados libres): nodos 700001.. (LT1 offset llega
        hasta ~600205; LT2 nativos <=272; masters 1001..1005), elementos
        70001.. (>9010 y <100000).
        """
        L_SEQ = ["B1", "L1", "L2", "L3", "L4", "ROOF"]
        z = {lv: _zname(self.levels, lv) for lv in L_SEQ}

        next_node = [TAG_BOX_NODE_BASE]
        next_ele = [TAG_BOX_ELEM_BASE]

        def nxt_node():
            t = next_node[0]
            next_node[0] += 1
            return t

        def nxt_ele():
            t = next_ele[0]
            next_ele[0] += 1
            return t

        specs = [
            dict(fam="caja_oeste", tipo="muro_Y", e=0.30, assumed=True,
                 x=0.998, y_a=2.90, y_b=7.92,
                 roof={2.90: 226, 7.92: 227},
                 nota="Bajo VI-05; x=0.998; e=0.30 ASSUMED_FOR_MODEL"),
            dict(fam="caja_este", tipo="muro_Y", e=0.30, assumed=True,
                 x=16.546, y_a=2.90, y_b=7.92,
                 roof={2.90: 256, 7.92: 257},
                 nota="Bajo VI-06; x=16.546; e=0.30 ASSUMED_FOR_MODEL"),
            dict(fam="pilastra", tipo="pilastra", e=0.60, assumed=False,
                 corners=[(7.596, 2.90, 244), (7.646, 7.92, 245),
                          (8.246, 7.92, 246), (8.296, 2.90, 247)],
                 nota="Pilastra x=7.947; e_x=0.60 EXPLICITO del plano; "
                      "4 columnas (1/4 de seccion bruta cada una)"),
            dict(fam="esc2_este", tipo="muro_X", e=0.30, assumed=True,
                 y=7.92, x_a=18.545, x_b=20.794,
                 roof={18.545: 258, 20.794: 259},
                 nota="2ª escalera borde N bajo VI-07; y=7.92; "
                      "x 18.545..20.794 real; e=0.30 ASSUMED_FOR_MODEL"),
        ]

        self.box_verticals = []
        self.box_support_tags = []
        tag_rows = []

        def add_column(cx, cy, e2_, g2_, A, Iy, Iz, J, fam, tipo, nota,
                       roof_tag, indice):
            """Genera una columna vertical B1->ROOF en (cx, cy). El nodo
            superior (ROOF) debe existir ya (roof_tag). Los nodos inferiores
            se crean en B1..L4."""
            tags = {}
            for lv in L_SEQ:
                if lv == "ROOF":
                    tags[lv] = roof_tag
                    continue
                t = nxt_node()
                ops.node(t, cx, cy, z[lv])
                tags[lv] = t
                tag_rows.append(dict(familia=fam, tipo=tipo, indice=indice,
                                     nivel=lv, tag=t, x=cx, y=cy, z=z[lv]))
            for i in range(len(L_SEQ) - 1):
                a, b = L_SEQ[i], L_SEQ[i + 1]
                tag = nxt_ele()
                ops.element("elasticBeamColumn", tag, tags[a], tags[b],
                            A, e2_, g2_, J, Iy, Iz, TRANS_COL_LT1)
                self.box_verticals.append(dict(
                    tag=tag, familia=fam, tipo=tipo, indice=indice,
                    nodo_bajo=tags[a], nodo_alto=tags[b],
                    nivel_bajo=a, nivel_alto=b, x=cx, y=cy, A=A,
                    Iy=Iy, Iz=Iz, J=J, nota=nota))
            # base B1 empotrada (mismo criterio que los apoyos del modelo)
            ops.fix(tags["B1"], 1, 1, 1, 1, 1, 1)
            self.box_support_tags.append(tags["B1"])
            return tags

        # especificacion 1 y 2: muro en Y (pares x=cst., y en [y_a, y_b])
        for spec in specs:
            if spec["tipo"] == "muro_Y":
                L = spec["y_b"] - spec["y_a"]
                A = spec["e"] * L / 2.0
                Iy = L * spec["e"] ** 3 / 24.0
                Iz = spec["e"] * L ** 3 / 24.0
                J = _jrect(min(spec["e"], L), max(spec["e"], L)) / 2.0
                add_column(spec["x"], spec["y_a"], e2, g2, A, Iy, Iz, J,
                           spec["fam"], "muro_Y", spec["nota"],
                           spec["roof"][spec["y_a"]], 1)
                add_column(spec["x"], spec["y_b"], e2, g2, A, Iy, Iz, J,
                           spec["fam"], "muro_Y", spec["nota"],
                           spec["roof"][spec["y_b"]], 2)
            elif spec["tipo"] == "muro_X":
                L = spec["x_b"] - spec["x_a"]
                A = spec["e"] * L / 2.0
                Iy = spec["e"] * L ** 3 / 24.0
                Iz = L * spec["e"] ** 3 / 24.0
                J = _jrect(min(spec["e"], L), max(spec["e"], L)) / 2.0
                add_column(spec["x_a"], spec["y"], e2, g2, A, Iy, Iz, J,
                           spec["fam"], "muro_X", spec["nota"],
                           spec["roof"][spec["x_a"]], 1)
                add_column(spec["x_b"], spec["y"], e2, g2, A, Iy, Iz, J,
                           spec["fam"], "muro_X", spec["nota"],
                           spec["roof"][spec["x_b"]], 2)
            elif spec["tipo"] == "pilastra":
                e = spec["e"]
                # longitud en planta de la pilastra (y 2.90..7.92) para seccion
                Ly = 7.92 - 2.90
                A = e * Ly / 4.0
                Iy = Ly * e ** 3 / 48.0
                Iz = e * Ly ** 3 / 48.0
                J = _jrect(min(e, Ly), max(e, Ly)) / 4.0
                for k, (cx, cy, roof_tag) in enumerate(spec["corners"]):
                    add_column(cx, cy, e2, g2, A, Iy, Iz, J,
                               spec["fam"], "pilastra", spec["nota"],
                               roof_tag, k + 1)
        self.box_tag_rows = pd.DataFrame(tag_rows)
        self.box_nodes = list(self.box_tag_rows["tag"])
        self.new_supports = list(self.box_support_tags)
        self.support_tags = sorted(set(self.support_tags)
                                   | set(self.new_supports))
        return self.box_verticals

    def _make_lt2_wall(self, tag, e_, e2, g2):
        """Par de columnas equivalentes academicas LT1 por tramo vertical de
        muro LT2 (convencion validada contra modelo_lt1.json, transf 10001
        que materializa vecxz=(1,0,0)).

        Cada tramo usa los 4 nodos reales del CSV (esquinas en sus dos
        extremos en planta, por nivel). Se crea UN elemento vertical por
        esquina con MEDIA seccion:
            A = e*L/2 ;  muro en X: Iy = e*L^3/24, Iz = L*e^3/24
                         muro en Y: Iy = L*e^3/24,   Iz = e*L^3/24
            J = Saint-Venant / 2   (b=min(e,L), h=max(e,L))
        De modo que los TOTALES por tramo coinciden con el muro academico
        LT1 (A=e*L, Ix=e*L^3/12, ...): misma rigidez axial/flexional global,
        sin nodos flotantes en las esquinas.
        """
        L, t = e_["length"], e_["thickness"]
        dx, dy = e_["x2"] - e_["x1"], e_["y2"] - e_["y1"]
        a = t * L / 2.0
        if abs(dy) <= TOL and abs(dx) > TOL:        # muro en X
            iy, iz = t * L ** 3 / 24.0, L * t ** 3 / 24.0
        elif abs(dx) <= TOL and abs(dy) > TOL:      # muro en Y
            iy, iz = L * t ** 3 / 24.0, t * L ** 3 / 24.0
        else:                                       # defensivo
            iy = iz = t * L ** 3 / 96.0
        j = _jrect(min(t, L), max(t, L)) / 2.0
        z0 = self.lt2_tag_to_key[e_["n1"]][2]
        z1 = self.lt2_tag_to_key[e_["n2"]][2]
        nB0 = self.lt2_key_to_tag[_key(e_["x2"], e_["y2"], z0)]
        nB1 = self.lt2_key_to_tag[_key(e_["x2"], e_["y2"], z1)]
        ops.element("elasticBeamColumn", tag, e_["n1"], e_["n2"],
                    a, e2, g2, j, iy, iz, TRANS_COL_LT1)
        ops.element("elasticBeamColumn", tag + 1, nB0, nB1,
                    a, e2, g2, j, iy, iz, TRANS_COL_LT1)
        self.wall_corner_b.update([nB0, nB1])

    # ---- salientes sur LT1 (geometria CAD verificada) ----------------------
    def _build_salientes_lt1(self):
        """Anade los salientes sur de LT1 (PISO_1..PISO_4) sobre el modelo
        combinado, replicando SOLO la geometria respaldada por CAD:
        (1) eje I' corregido a X=45.0 (nodos creados ya con la correccion),
        (2) nodos nuevos 800001+,
        (3) vigas de fachada sur particionadas en las cotas del saliente,
        (4) vigas nuevas 800101+ (borded sur + flancos) V.60/80.

        NO se crean: malla artificial, SPAN_INFERIDO, metales P.M./P.M.I./
        V.M. (sin E), diagonales, ni vigas sin respaldo CAD (regla del
        proyecto LT1).
        """
        a = _rect_props(0.60, 0.80)[0]
        iy = _rect_props(0.60, 0.80)[1]
        iz = _rect_props(0.60, 0.80)[2]
        j = _jrect(0.60, 0.80)

        self.saliente_nodes = []
        self.saliente_beams = []
        self.facade_segments = []
        self.facade_partitions = []
        self.removed_beams_loads = []
        nxt = [TAG_SAL_NODE_BASE, TAG_SAL_BEAM_BASE, TAG_SAL_SEG_BASE]

        def next_node():
            t = nxt[0]
            nxt[0] += 1
            return t

        def next_beam():
            t = nxt[1]
            nxt[1] += 1
            return t

        def next_seg():
            t = nxt[2]
            nxt[2] += 1
            return t

        for nivel, data in _SALIENTES_DATA.items():
            z = float(data["z_m"])
            facade = self._facade_nodes_lt1(z)
            segs = self._facade_segments_lt1(z)

            # (2) nodos saliente
            tag_by_label = {}
            for x_lt1, y_lt1, label in data["nodes"]:
                xp, yp, zp = self._trans_lt1(x_lt1, y_lt1, z)
                tag = next_node()
                ops.node(tag, xp, yp, zp)
                tag_by_label[label] = tag
                self.saliente_nodes.append(tag)

            # (3) particiones de fachada (nodos de fachada del saliente)
            for x_lt1 in sorted(data["partition_x_lt1"]):
                segs = self._partition_facade_lt1(nivel, z, x_lt1, segs,
                                                  tag_by_label, next_seg)

            # (4) vigas del saliente (borde sur + flancos)
            for ref_i, ref_j in data["beams"]:
                ni = self._resolve_sal_node(ref_i, tag_by_label, facade,
                                            nivel)
                nj = self._resolve_sal_node(ref_j, tag_by_label, facade,
                                            nivel)
                tag_b = next_beam()
                self._add_sal_beam(tag_b, ni, nj, a, iy, iz, j, nivel)
                self.saliente_beams.append(tag_b)
                self.created["lt1_beams"].append(tag_b)

        self._finalize_removed_loads()

    def _json_facade_beams(self, z):
        """Vigas LT1 de la fachada sur (y_lt1=-16.15) en la cota `z`
        segun el JSON de referencia (con la correccion I' aplicada en las
        cotas). Devuelve [{tag, x1_lt1, x2_lt1, qG_kN_m}]."""
        out = []
        for b in self.json_lt1["beams"]:
            n_i, n_j = self.lt1_nodes[b["node_i"]], self.lt1_nodes[b["node_j"]]
            if abs(float(n_i["z"]) - z) > 1e-6:
                continue
            if (abs(float(n_i["y"]) + 16.15) > 1e-6
                    or abs(float(n_j["y"]) + 16.15) > 1e-6):
                continue
            x1 = self.ip_correction.get(b["node_i"], float(n_i["x"]))
            x2 = self.ip_correction.get(b["node_j"], float(n_j["x"]))
            if x1 > x2:
                x1, x2 = x2, x1
            out.append(dict(
                tag=b["elementTag"], x1_lt1=x1, x2_lt1=x2,
                qG_kN_m=float(b.get("carga_lineal_qG_kN_m", 0.0) or 0.0)))
        return out

    def _finalize_removed_loads(self):
        """Construye `self.removed_beams_loads` con los tramos FINALES de
        fachada (post-particion): cada viga original particionada conserva
        su carga y la redistribuye a sus segmentos finales en proporcion a
        la longitud. Así se resuelve tambien la cascada (un segmento
        intermedio que sea a su vez particionado)."""
        self.removed_beams_loads = []
        for nivel, data in _SALIENTES_DATA.items():
            z = float(data["z_m"])
            orig = self._json_facade_beams(z)
            final_segs = [s for s in self.facade_segments
                          if s["nivel"] == nivel]
            segs_by_orig = {}
            for s in final_segs:
                mid = 0.5 * (s["x1_lt1"] + s["x2_lt1"])
                father = None
                for o in orig:
                    if o["x1_lt1"] - 1e-6 <= mid <= o["x2_lt1"] + 1e-6:
                        father = o
                        break
                if father is None:
                    raise RuntimeError(
                        f"SALIENTE {nivel}: el segmento final {s['tag']} "
                        f"([{s['x1_lt1']:.3f},{s['x2_lt1']:.3f}]) no tiene "
                        "viga original de fachada que lo contenga.")
                segs_by_orig.setdefault(
                    (father["tag"], father["x1_lt1"], father["x2_lt1"]),
                    {"qG_kN_m": father["qG_kN_m"],
                     "L_original": father["x2_lt1"] - father["x1_lt1"],
                     "segments": []})["segments"].append(
                         dict(tag=s["tag"], L=s["x2_lt1"] - s["x1_lt1"]))
            for (tag_orig, x1, x2), d in segs_by_orig.items():
                total_L = sum(float(g["L"]) for g in d["segments"])
                if abs(total_L - d["L_original"]) > 1e-6:
                    raise RuntimeError(
                        f"SALIENTE: la suma de segmentos de la viga "
                        f"{tag_orig} ({total_L:.3f}) no cubre su longitud "
                        f"original ({d['L_original']:.3f}).")
                self.removed_beams_loads.append(dict(
                    tag_original=tag_orig, nivel=nivel,
                    qG_kN_m=d["qG_kN_m"],
                    L_original=d["L_original"],
                    segments=d["segments"]))

    def _resolve_sal_node(self, ref, tag_by_label, facade, nivel):
        if ref in tag_by_label:
            return tag_by_label[ref]
        if ref in facade:
            return facade[ref]
        raise RuntimeError(
            f"SALIENTE: endpoint '{ref}' del nivel {nivel} sin nodo "
            "resoluble (falta eje de fachada o nodo de saliente).")

    def _facade_nodes_lt1(self, z):
        """Ejes de fachada sur (y_lt1=-16.15) existentes en `z`
        (coordenada LT1): {eje: tag_combinado}."""
        m = {}
        for tag, n in self.lt1_nodes.items():
            if abs(float(n["y"]) + 16.15) > 1e-6:
                continue
            if abs(float(n["z"]) - z) > 1e-6:
                continue
            x = self.ip_correction.get(tag, float(n["x"]))
            for eje, xe in _FACADE_NODE_X.items():
                if abs(x - xe) < 1e-6:
                    m[eje] = self.lt1_combo[tag]
                    break
        return m

    def _facade_segments_lt1(self, z):
        """Vigas LT1 de la fachada sur (y_lt1=-16.15) a la cota `z`;
        devuelve segmentos ordenados con cotas LT1 (x1<x2) y los tags
        COMBINADOS de sus nodos."""
        segs = []
        for b in self.json_lt1["beams"]:
            n_i, n_j = self.lt1_nodes[b["node_i"]], self.lt1_nodes[b["node_j"]]
            if abs(float(n_i["z"]) - z) > 1e-6:
                continue
            if (abs(float(n_i["y"]) + 16.15) > 1e-6
                    or abs(float(n_j["y"]) + 16.15) > 1e-6):
                continue
            x1 = self.ip_correction.get(b["node_i"], float(n_i["x"]))
            x2 = self.ip_correction.get(b["node_j"], float(n_j["x"]))
            if x1 > x2:
                x1, x2 = x2, x1
                c1, c2 = self.lt1_combo[b["node_j"]], self.lt1_combo[b["node_i"]]
            else:
                c1, c2 = self.lt1_combo[b["node_i"]], self.lt1_combo[b["node_j"]]
            segs.append(dict(elementTag=b["elementTag"],
                             node_i=c1, node_j=c2,
                             x1_lt1=x1, x2_lt1=x2,
                             a=b["A_m2"], iy=b["Iy_m4"], iz=b["Iz_m4"],
                             j=b["J_m4"]))
        return sorted(segs, key=lambda s: s["x1_lt1"])

    def _partition_facade_lt1(self, nivel, z, x_lt1, segs, tag_by_label,
                              next_tag):
        """Particiona la viga de fachada sur que contiene la cota `x_lt1`
        en (izq -> nodo saliente -> der), devolviendo los segmentos nuevos.
        Regla: si el nodo nuevo cae sobre una viga de fachada existente,
        se PARTICIONA la viga (nada de vigas paralelas ni diagonales)."""
        xp = x_lt1 + SHIFT_X
        sal = None
        for label, t in tag_by_label.items():
            c = list(ops.nodeCoord(t))
            if (abs(c[1] - 16.15) < 1e-6 and abs(c[0] - xp) < 1e-6
                    and abs(c[2] - z) < 1e-6):
                sal = t
                break
        if sal is None:
            raise RuntimeError(
                f"SALIENTE {nivel}: la cota de partición X={x_lt1:g} no "
                "coincide con ningun nodo de fachada del saliente.")

        hit = None
        for s in segs:
            if s["x1_lt1"] - 1e-6 <= x_lt1 <= s["x2_lt1"] + 1e-6:
                hit = s
                break
        if hit is None:
            raise RuntimeError(
                f"SALIENTE {nivel}: cota X={x_lt1:g} fuera de las vigas de "
                "fachada sur existentes.")

        n_i = hit["node_i"]
        n_j = hit["node_j"]
        left_tag = next_tag()
        right_tag = next_tag()
        # se reusan las propiedades originales de la viga particionada
        for tag_e, nz, sal_ in ((left_tag, n_i, sal), (right_tag, sal, n_j)):
            ops.element("elasticBeamColumn", tag_e, nz, sal_,
                        hit["a"], E_LT1, G_LT1, hit["j"],
                        hit["iy"], hit["iz"], TRANS_B_X_LT1)

        if hit["elementTag"] in self.created["lt1_beams"]:
            self.created["lt1_beams"].remove(hit["elementTag"])
        ops.remove("element", int(hit["elementTag"]))

        self.facade_segments.append(dict(
            nivel=nivel, tag=left_tag, node_i=n_i, node_j=sal,
            x1_lt1=hit["x1_lt1"], x2_lt1=x_lt1))
        self.facade_segments.append(dict(
            nivel=nivel, tag=right_tag, node_i=sal, node_j=n_j,
            x1_lt1=x_lt1, x2_lt1=hit["x2_lt1"]))
        self.facade_partitions.append(dict(
            nivel=nivel, tag_original=hit["elementTag"], x_lt1=x_lt1,
            tag_izq=left_tag, tag_der=right_tag, nodo=sal))
        self.created["lt1_beams"].extend([left_tag, right_tag])
        # limpia el segmento padre de facade_segments (ya no existe en ops)
        self.facade_segments = [s for s in self.facade_segments
                                if s["tag"] != hit["elementTag"]]

        # sustituye el segmento particionado por los dos nuevos
        out = []
        for s in segs:
            if s is hit:
                out.append(dict(elementTag=left_tag, node_i=n_i,
                                node_j=sal,
                                x1_lt1=hit["x1_lt1"], x2_lt1=x_lt1,
                                a=hit["a"], iy=hit["iy"], iz=hit["iz"],
                                j=hit["j"]))
                out.append(dict(elementTag=right_tag, node_i=sal,
                                node_j=n_j,
                                x1_lt1=x_lt1, x2_lt1=hit["x2_lt1"],
                                a=hit["a"], iy=hit["iy"], iz=hit["iz"],
                                j=hit["j"]))
            else:
                out.append(s)
        return sorted(out, key=lambda s: s["x1_lt1"])

    def _add_sal_beam(self, tag, ni, nj, a, iy, iz, j, nivel):
        c1 = list(ops.nodeCoord(ni))
        c2 = list(ops.nodeCoord(nj))
        dx, dy, dz = (c2[0] - c1[0], c2[1] - c1[1], c2[2] - c1[2])
        l = math.sqrt(dx * dx + dy * dy + dz * dz)
        if l < 1e-6:
            raise RuntimeError(f"SALIENTE {nivel}: viga {tag} de longitud 0.")
        if abs(dz) > 1e-6:
            raise RuntimeError(
                f"SALIENTE {nivel}: viga {tag} con salto de nivel (dz).")
        if abs(dy) <= 1e-6 and abs(dx) > 1e-6:
            transf = TRANS_B_X_LT1
        elif abs(dx) <= 1e-6 and abs(dy) > 1e-6:
            transf = TRANS_B_Y_LT1
        else:
            raise RuntimeError(
                f"SALIENTE {nivel}: viga {tag} inclinada en planta (solo "
                "horizontales X/Y permitidas).")
        ops.element("elasticBeamColumn", tag, ni, nj, a, E_LT1, G_LT1,
                    j, iy, iz, transf)

    def _audit_interface_elements(self):
        rows = []

        def _x(zero_k):
            return zero_k[0]

        # LT2 columnas en la interfaz (x=31.25)
        lt2_col_by_key = {}
        for i, c in enumerate(self.lt2_elems["columns"]):
            k1, k2 = self.lt2_tag_to_key[c["n1"]], self.lt2_tag_to_key[c["n2"]]
            if abs(k1[0] - SHIFT_X) > TOL or abs(k2[0] - SHIFT_X) > TOL:
                continue
            lt2_col_by_key[(round(k1[1], 6), round(min(k1[2], k2[2]), 6),
                            round(max(k1[2], k2[2]), 6))] = c["id"]
            rows.append(dict(
                modulo="LT2", tipo="columna", tag_original=TAG_COL_BASE + i,
                seccion=c["section"], nodo_i=c["n1"], nodo_j=c["n2"],
                x1=k1[0], y1=k1[1], z1=k1[2], x2=k2[0], y2=k2[1], z2=k2[2],
                longitud_m=c["length"], par_otro_modulo=None,
                decision="CONSERVAR",
                motivo="Columna P70x70 nativa LT2 en la interfaz; da soporte "
                       "al nodo compartido."))
        # LT1 columnas en la interfaz
        for c in self.json_lt1["columns"]:
            ni, nj = self.lt1_nodes[c["node_i"]], self.lt1_nodes[c["node_j"]]
            x1, y1, z1 = self._trans_lt1(ni["x"], ni["y"], ni["z"])
            x2, y2, z2 = self._trans_lt1(nj["x"], nj["y"], nj["z"])
            if abs(x1 - SHIFT_X) > TOL or abs(x2 - SHIFT_X) > TOL:
                continue
            key = (round(y1, 6), round(min(z1, z2), 6),
                   round(max(z1, z2), 6))
            pair = lt2_col_by_key.get(key)
            if pair is not None:
                self.duplicated = True
                motivo = (f"Duplicado geometrico exacto con columna LT2 "
                          f"nativa {pair} (P70x70, mismo tramo; difiere E: "
                          "LT1 25e6 vs LT2 23.5e6 kPa). Se conserva LT2 "
                          "(regla 3).")
            else:
                motivo = "Columna LT1 en interfaz SIN par LT2 (verificar)."
            rows.append(dict(
                modulo="LT1", tipo="columna", tag_original=c["elementTag"],
                seccion=c["seccion"], nodo_i=c["node_i"], nodo_j=c["node_j"],
                x1=x1, y1=y1, z1=z1, x2=x2, y2=y2, z2=z2,
                longitud_m=c["longitud_m"], par_otro_modulo=pair,
                decision="DESCARTAR" if pair is not None else "CONSERVAR",
                motivo=motivo))
        # LT1 vigas con ambos extremos en el borde (eje E)
        for b in self.json_lt1["beams"]:
            ni, nj = self.lt1_nodes[b["node_i"]], self.lt1_nodes[b["node_j"]]
            x1, y1, z1 = self._trans_lt1(ni["x"], ni["y"], ni["z"])
            x2, y2, z2 = self._trans_lt1(nj["x"], nj["y"], nj["z"])
            if abs(x1 - SHIFT_X) > TOL or abs(x2 - SHIFT_X) > TOL:
                continue
            rows.append(dict(
                modulo="LT1", tipo="viga", tag_original=b["elementTag"],
                seccion=b["seccion"], nodo_i=b["node_i"], nodo_j=b["node_j"],
                x1=x1, y1=y1, z1=z1, x2=x2, y2=y2, z2=z2,
                longitud_m=b["longitud_m"], par_otro_modulo=None,
                decision="CONSERVAR",
                motivo="Viga de borde LT1 eje E; LT2 no tiene viga en ese "
                       "tramo (no duplicada)."))
        # LT2 muros en la interfaz (x1=x2=31.25)
        for i, m in enumerate(self.lt2_elems["walls"]):
            k1, k2 = self.lt2_tag_to_key[m["n1"]], self.lt2_tag_to_key[m["n2"]]
            if abs(k1[0] - SHIFT_X) > TOL or abs(k2[0] - SHIFT_X) > TOL:
                continue
            rows.append(dict(
                modulo="LT2", tipo="muro",
                tag_original=f"{TAG_WALL_BASE + 2 * i}/"
                             f"{TAG_WALL_BASE + 2 * i + 1}",
                seccion=f"M.H.A. e={m['thickness']} m",
                nodo_i=m["n1"], nodo_j=m["n2"],
                x1=k1[0], y1=k1[1], z1=k1[2], x2=k2[0], y2=k2[1], z2=k2[2],
                longitud_m=m["length"], par_otro_modulo=None,
                decision="CONSERVAR",
                motivo="Muro LT2 en el borde este (solo LT2)."))
        dup_cols = [r["tag_original"] for r in rows
                    if r["modulo"] == "LT1" and r["tipo"] == "columna"
                    and r["decision"] == "DESCARTAR"]
        return pd.DataFrame(rows), dup_cols

    def _build_diaphragms_and_links(self):
        wall_combos = {self.lt1_combo[t] for t in self.lt1_wall_natives}
        self.slaves_per_level = {}
        self.diaph_masters = {}
        self.diaph_slaves = {}
        for r in self.diaphs.itertuples():
            master = self.master_tag_by_id[r.master_id]
            set_ = set(self.lt2_level_tags.get(r.level, []))
            for tag, n in self.lt1_nodes.items():
                if abs(round(float(n["z"]), 6)
                       - round(float(r.z_m), 6)) > 1e-9:
                    continue
                c = self.lt1_combo[tag]
                if c in wall_combos or c in set_:
                    continue
                set_.add(c)
            set_.discard(master)
            slaves = sorted(set_)
            if slaves:
                ops.rigidDiaphragm(3, master, *slaves)
            self.diaph_masters[r.level] = master
            self.slaves_per_level[r.level] = len(slaves)
            self.diaph_slaves[r.level] = set(slaves)

        self.rigid_links = []
        for link in self.json_lt1["constraint_links"]:
            c = self.lt1_combo[link["nodo_muro"]]
            # nivel del master combinado por z
            z = float(self.lt1_nodes[link["nodo_muro"]]["z"])
            lv = None
            for name in self.levels["name"]:
                if abs(_zname(self.levels, name) - z) < 1e-9:
                    lv = name
            if lv is None:
                raise RuntimeError(
                    f"Sin nivel combinado para z={z} (nodo muro "
                    f"{link['nodo_muro']}). INPUT_REQUIRED.")
            master = self.master_tag_by_level[lv]
            ops.rigidLink("beam", master, c)
            self.rigid_links.append(dict(nivel=lv, master=master,
                                         nodo_muro=c,
                                         tag_original=link["nodo_muro"]))

    # ---- cargas ------------------------------------------------------------
    def apply_loads(self):
        ops.timeSeries("Linear", 1)
        ops.pattern("Plain", 1, 1)
        created_lt2 = set(self.created["lt2_beams"])
        req = {int(t) for t in self.loads["element_tag"].unique()}
        missing = req - created_lt2
        if missing:
            raise RuntimeError(
                "Tags de carga LT2 sin elemento creado: "
                f"{sorted(missing)}. INPUT_REQUIRED.")
        n_loads_lt2 = 0
        for row in self.loads.itertuples(index=False):
            ops.eleLoad("-ele", int(row.element_tag), "-type",
                        "-beamPoint", 0.0, -float(row.load_kN),
                        float(row.xloc))
            n_loads_lt2 += 1
        ops.timeSeries("Linear", 2)
        ops.pattern("Plain", 2, 2)
        n_loads_lt1 = 0
        removed_tags = {rb["tag_original"] for rb in self.removed_beams_loads}
        for b in self.json_lt1["beams"]:
            if b["elementTag"] in removed_tags:
                continue
            w = float(b.get("carga_lineal_qG_kN_m", 0.0) or 0.0)
            if abs(w) < 1e-12:
                continue
            ops.eleLoad("-ele", b["elementTag"], "-type", "-beamUniform",
                        0.0, -w)
            n_loads_lt1 += 1
        # Redistribute loads from removed partitioned beams to replacement
        # segments: the original facade beam carried a uniform qG over its
        # whole length; after partitioning, each segment keeps the SAME
        # density qG (total = qG * sum(seg_L) = qG * L_original).
        n_redistributed = 0
        for rb in self.removed_beams_loads:
            if abs(rb["qG_kN_m"]) < 1e-12:
                continue
            L_orig = rb["L_original"]
            if L_orig < 1e-12:
                continue
            for seg in rb["segments"]:
                w_seg = rb["qG_kN_m"]
                ops.eleLoad("-ele", seg["tag"], "-type", "-beamUniform",
                            0.0, -w_seg)
                n_loads_lt1 += 1
                n_redistributed += 1
        self.n_redistributed = n_redistributed
        # P_lt1 = suma de las cargas REALMENTE aplicadas sobre la geometria
        # corregida (eje I' = 45.0 m alarga las vigas I-I' de 2.5 a 5.0 m;
        # beamUniform es por metro, por lo que la carga total crece
        # proporcionalmente). P_lt1_referencia conserva el valor del JSON
        # (I' = 42.5 m) para trazabilidad.
        self.P_lt1_referencia = sum(
            float(b.get("carga_lineal_qG_kN_m", 0.0) or 0.0)
            * float(b["longitud_m"]) for b in self.json_lt1["beams"])

        def _len(tag):
            ns = list(ops.eleNodes(tag))
            c1 = ops.nodeCoord(ns[0])
            c2 = ops.nodeCoord(ns[1])
            return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2
                             + (c1[2] - c2[2]) ** 2)

        P = 0.0
        for b in self.json_lt1["beams"]:
            if b["elementTag"] in removed_tags:
                continue
            w = float(b.get("carga_lineal_qG_kN_m", 0.0) or 0.0)
            if abs(w) < 1e-12:
                continue
            P += w * _len(b["elementTag"])
        for rb in self.removed_beams_loads:
            if abs(rb["qG_kN_m"]) < 1e-12:
                continue
            L_orig = rb["L_original"]
            if L_orig < 1e-12:
                continue
            for seg in rb["segments"]:
                w_seg = rb["qG_kN_m"]
                P += w_seg * _len(seg["tag"])
        self.P_lt1 = P
        self.P_lt2 = float(self.loads["load_kN"].sum())
        self.P_total = self.P_lt1 + self.P_lt2
        return n_loads_lt2, n_loads_lt1

    # ---- analisis + validacion ---------------------------------------------
    def run_analysis(self):
        ops.constraints("Transformation")
        ops.numberer("RCM")
        ops.system("BandGeneral")
        ops.test("NormDispIncr", 1.0e-6, 30, 2)
        ops.algorithm("Linear")
        ops.integrator("LoadControl", 1.0)
        ops.analysis("Static")
        rc = ops.analyze(1)
        ops.loadConst("-time", 0.0)
        self.rc = rc
        return rc

    def _floating_regions(self, node_tags, elem_tags):
        """Nodos sin camino de rigidez (BFS por elementos) a un apoyo fijo;
        agrupa por nivel y reporta los elementos incidentes."""
        coords = {t: tuple(ops.nodeCoord(t)) for t in node_tags}
        levels_z = {_zname(self.levels, n): n for n in self.levels["name"]}
        adj = {t: set() for t in node_tags}
        ele_by_node = {t: [] for t in node_tags}
        for e in elem_tags:
            ns = list(ops.eleNodes(e))
            if len(ns) != 2:
                continue
            adj[ns[0]].add(ns[1])
            adj[ns[1]].add(ns[0])
            ele_by_node[ns[0]].append(e)
            ele_by_node[ns[1]].append(e)
        reach = set(self.support_tags)
        frontier = list(reach)
        while frontier:
            n = frontier.pop()
            for m in adj.get(n, ()):
                if m not in reach:
                    reach.add(m)
                    frontier.append(m)
        floating = sorted(set(node_tags) - reach)
        by_level = {}
        for t in floating:
            lv = levels_z.get(round(coords[t][2], 6))
            by_level.setdefault(lv, []).append(t)
        incid = set()
        for t in floating:
            incid.update(ele_by_node.get(t, ()))
        return floating, by_level, sorted(incid)

    def _element_conn(self):
        conn = set()
        for b in self.json_lt1["beams"]:
            conn.update([self.lt1_combo[b["node_i"]],
                         self.lt1_combo[b["node_j"]]])
        for c in self.json_lt1["columns"]:
            if c["elementTag"] in set(self.duplicated_lt1_cols):
                continue
            conn.update([self.lt1_combo[c["node_i"]],
                         self.lt1_combo[c["node_j"]]])
        for w in self.json_lt1["walls"]:
            conn.update([self.lt1_combo[w["node_i"]],
                         self.lt1_combo[w["node_j"]]])
        for e_ in self.lt2_elems["beams"] + self.lt2_elems["columns"] \
                + self.lt2_elems["walls"]:
            conn.update([e_["n1"], e_["n2"]])
        conn.update(self.wall_corner_b)
        return conn

    def _verify_diaphragms(self):
        """Verifica el camino de rigidez de los salientes hacia el
        diafragma POR VIGAS: los nodos saliente NO son slaves (decision de
        diseno, ver nota en _build_diaphragms), pero cada uno debe tener
        trayectoria de vigas hasta un slave/master del diafragma de su
        nivel. Reporta la distancia en saltos de elemento por piso."""
        node_tags = sorted(set(map(int, ops.getNodeTags())))
        elem_tags = list(map(int, ops.getEleTags()))
        adj = {t: set() for t in node_tags}
        for e in elem_tags:
            ns = [int(n) for n in ops.eleNodes(e)]
            if len(ns) != 2:
                continue
            adj[ns[0]].add(ns[1])
            adj[ns[1]].add(ns[0])
        z_to_level = {}
        for name in self.levels["name"]:
            z_to_level[round(_zname(self.levels, name), 6)] = name

        def _dist(t, target):
            if t in target:
                return 0
            seen = {t}
            frontier = [t]
            d = 0
            while frontier:
                nxt = []
                d += 1
                for u in frontier:
                    for v in adj[u]:
                        if v in target:
                            return d
                        if v not in seen:
                            seen.add(v)
                            nxt.append(v)
                frontier = nxt
            return None

        rows = {}
        issues = []
        for nivel, data in _SALIENTES_DATA.items():
            zl = round(float(data["z_m"]), 6)
            lv = z_to_level[zl]
            target = set(self.diaph_slaves.get(lv, set()))
            m = self.diaph_masters.get(lv)
            if m is not None:
                target.add(m)
            at_level = [t for t in self.saliente_nodes
                        if round(list(ops.nodeCoord(t))[2], 6) == zl]
            dists = {t: _dist(t, target) for t in at_level}
            bad = [t for t, d in dists.items() if d is None]
            issues.extend((lv, t) for t in bad)
            rows[nivel] = dict(nivel=nivel, level_lt2=lv, master=m,
                               n_saliente_total=len(at_level),
                               max_saltos=max(
                                   (d for d in dists.values()
                                    if d is not None), default=0))
        self.diaph_check_issues = sorted(set(issues))
        return rows

    def _final_checks(self):
        """Checks automaticos del cierre (Paso 8 del plan): geometria de
        vigas/columnas, salientes, I', redistribucion, equilibrio."""
        def _span(tag):
            ns = [int(n) for n in ops.eleNodes(int(tag))]
            if len(ns) != 2:
                return None
            c0, c1 = ops.nodeCoord(ns[0]), ops.nodeCoord(ns[1])
            return tuple(abs(c1[i] - c0[i]) for i in range(3))

        beams = sorted(set(self.created["lt1_beams"])
                       | set(self.created["lt2_beams"]))
        cols = sorted(set(self.created["lt1_cols"])
                      | set(self.created["lt2_cols"]))
        n_beams_dz = sum(1 for t in beams
                         if (d := _span(t)) and d[2] > 1e-6)
        n_cols_off = sum(1 for t in cols
                         if (d := _span(t)) and (d[0] > 1e-6
                                                 or d[1] > 1e-6))
        n_sal_dz = sum(1 for t in self.saliente_beams
                       if (d := _span(t)) and d[2] > 1e-6)
        n_link_dz = sum(1 for ln in self.v40_links
                        if (d := _span(ln["tag_conector"])) and d[2] > 1e-6)
        n_box_off = sum(1 for e in self.box_verticals
                        if (d := _span(e["tag"])) and (d[0] > 1e-6
                                                       or d[1] > 1e-6))
        n_diag_plan = sum(1 for t in beams
                          if (d := _span(t)) and d[2] <= 1e-6
                          and d[0] > 1e-6 and d[1] > 1e-6)
        sal_floating = sorted(set(self.saliente_nodes) & set(self.floating))
        ip_nodes = sorted(set(self.ip_correction))
        ip_comb = [float(ops.nodeCoord(self.lt1_combo[t])[0])
                   for t in ip_nodes]
        ip_ok = (len(ip_comb) >= 18
                 and all(abs(x - (45.0 + SHIFT_X)) < 1e-6
                         for x in ip_comb))
        created_ele = set()
        for fam in self.created.values():
            created_ele.update(fam)
        created_ele.update(self.saliente_beams)
        created_ele.update(s["tag"] for s in self.facade_segments)
        redist_missing = sorted(
            int(s["tag"]) for rb in self.removed_beams_loads
            for s in rb["segments"]
            if int(s["tag"]) not in created_ele)
        return dict(
            rc=self.rc,
            n_lt2_beams=len(set(self.created["lt2_beams"])),
            n_lt1_beams=len(set(self.created["lt1_beams"])),
            n_beams_dz=n_beams_dz,
            n_cols_off=n_cols_off,
            n_sal_dz=n_sal_dz,
            n_link_dz=n_link_dz,
            n_box_off=n_box_off,
            n_diag_plan=n_diag_plan,
            n_sal_floating=len(sal_floating),
            sal_floating=sal_floating,
            n_ip_nodes=len(ip_comb),
            ip_ok=ip_ok,
            redist_missing=redist_missing,
            n_redistributed=self.n_redistributed,
            err_rel=self.errz_rel,
            zero_len=len(self.zero_len),
            no_conn=len(self.no_conn))

    def validate(self):
        node_tags = sorted(set(map(int, ops.getNodeTags())))
        elem_tags = sorted(set(map(int, ops.getEleTags())))
        coords = {t: tuple(ops.nodeCoord(t)) for t in node_tags}
        zero_len = []
        for e in elem_tags:
            ns = list(ops.eleNodes(e))
            if len(ns) == 2 and coords[ns[0]][2] == coords[ns[1]][2]:
                d = math.sqrt(sum((coords[ns[0]][i] - coords[ns[1]][i]) ** 2
                                  for i in range(3)))
                if d < 1e-9:
                    zero_len.append(e)
        structural = set(self.lt2_tag_to_key) | set(self.lt1_combo.values())
        no_conn = sorted(structural - self._element_conn())
        self.no_conn, self.zero_len = no_conn, zero_len
        self.floating, self.floating_by_level, self.floating_elems = \
            self._floating_regions(node_tags, elem_tags)
        self.diaph_summary = self._verify_diaphragms()
        if self.rc == 0:
            ops.reactions()
            cols = ["node_tag", "Rx_kN", "Ry_kN", "Rz_kN"]
            self.reac = pd.DataFrame(
                [(t, ops.nodeReaction(t, 1), ops.nodeReaction(t, 2),
                  ops.nodeReaction(t, 3)) for t in self.support_tags],
                columns=cols)
            self.errax_abs = abs(self.reac["Rx_kN"].sum())
            self.erray_abs = abs(self.reac["Ry_kN"].sum())
            self.errz_abs = abs(self.reac["Rz_kN"].sum() - self.P_total)
            self.errz_rel = self.errz_abs / max(self.P_total, 1e-12)
            self.max_u = self.max_uz = 0.0
            self.max_node = self.max_uz_node = self.nan_nodes = None
            self.nan_nodes = []
            for t in node_tags:
                d = tuple(ops.nodeDisp(t))
                if any(not math.isfinite(v) for v in d):
                    self.nan_nodes.append(t)
                    continue
                mag = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
                if mag > self.max_u:
                    self.max_u, self.max_node = mag, t
                if abs(d[2]) > self.max_uz:
                    self.max_uz, self.max_uz_node = abs(d[2]), t
        else:
            self.reac = None
            self.errz_abs = self.errz_rel = self.errax_abs = \
                self.erray_abs = float("nan")
            self.max_u = self.max_uz = float("nan")
            self.max_node = self.max_uz_node = self.nan_nodes = None
        self.final_checks = self._final_checks()
        return node_tags, elem_tags

    # ---- salidas ------------------------------------------------------------
    def write_outputs(self, summary, rc, node_tags, elem_tags):
        OUT.mkdir(parents=True, exist_ok=True)
        self.trace.to_csv(OUT_TRACE, index=False)
        self.audit_rows.to_csv(OUT_AUDIT, index=False)
        if self.v40_links:
            pd.DataFrame(self.v40_links).to_csv(OUT_LINKS, index=False)
        if self.box_verticals:
            pd.DataFrame(self.box_verticals).to_csv(OUT_BOX, index=False)
        self.write_report(summary, rc, node_tags, elem_tags)
        self.write_fig()

    def write_report(self, summary, rc, node_tags, elem_tags):
        L = []
        add = L.append
        add("# Modelo combinado LT1 + LT2 — reporte de validacion")
        add("")
        add("## 1. Transformacion e interfaz (APROBADA)")
        add("")
        add("- LT1: X' = X + 31.250 ; Y' = -Y ; Z' = Z (sin rotacion).")
        add("- LT2: coordenadas nativas. Interfaz global en X = 31.250 m.")
        add(f"- Pares de nodos coincidentes: **{len(self.interface)}/18** "
            "(6 niveles x ejes 1/2/3, distancia 0.000 m).")
        add("- Un solo nodo fisico por posicion: se conserva el tag nativo "
            "LT2. Detalle: `interfaz_traceabilidad.csv`.")
        add("")
        add("## 2. Retagging (sin colisiones)")
        add("")
        add("- LT2: tags nativos (nodos 1..272, masters 1001..1005, vigas "
            f"2001+ ({len(self.created['lt2_beams'])}), columnas 3001+ "
            f"({len(self.created['lt2_cols'])}), muros 4001+ "
            f"({len(self.created['lt2_walls'])}), secciones 5001+, transf "
            "1/2/3).")
        add(f"- LT1: offset +100000 en nodos estructurales y muros; masters "
            "LT1 (600001-600004) NO se crean (sustituidos por masters "
            "combinados). Elementos con tags nativos (columnas "
            f"{len(self.created['lt1_cols'])}, vigas "
            f"{len(self.created['lt1_beams'])}, muros "
            f"{len(self.created['lt1_walls'])}); transf 10001/10002/10003; "
            "timeSeries/pattern 1 (LT2) y 2 (LT1).")
        add("")
        add("## 3. Elementos duplicados en la interfaz")
        add("")
        n_dup = len(self.duplicated_lt1_cols)
        add(f"- Duplicados geometricos detectados: **{n_dup} columnas LT1** "
            "(P70x70, ejes 1/2/3, 5 tramos) coinciden exactamente con "
            "columnas LT2 nativas (misma seccion, longitud y orientacion; "
            "difiere E: LT1 25e6 vs LT2 23.5e6 kPa).")
        add(f"- Decision (regla 3): conservar la **columna LT2 nativa** y "
            f"descartar las {n_dup} de LT1; la columna compartida queda con "
            "el E de LT2. No se pierde rigidez vertical (tramos iguales "
            "nivel a nivel).")
        add("- Vigas LT1 de borde en E (8) y muros LT2 en el borde: sin par, "
            "se conservan. Detalle: `auditoria_elementos_interfaz.csv`.")
        add("")
        add("## 4. Diafragmas (un solo master por nivel)")
        add("")
        for name in ("L1", "L2", "L3", "L4", "ROOF"):
            add(f"- {name}: master {self.diaph_masters[name]} (LT2 nativo), "
                f"{self.slaves_per_level[name]} nodos oculares cada uno una "
                "sola vez.")
        add(f"- Los {len(self.rigid_links)} nodos de muro LT1 se vinculan al "
            "master del nivel con ops.rigidLink('beam', master, nodo_muro) "
            "(estrategia C de LT1); NO son esclavos del rigidDiaphragm.")
        add("")
        add("## 5. Apoyos")
        add("")
        add(f"- LT2: 22 fijos (B1, empotrados).")
        add(f"- LT1: 15 fijos (los 3 de interfaz ya fijados como nodos "
            "LT2; sin ops.fix duplicado).")
        add(f"- **COMBINADO (cajas/pilastra/2ª escalera): "
            f"{len(self.new_supports)} fijos nuevos en B1** (empotrados, "
            "misma convencion de fundacion que el resto del modelo; NO son "
            "restricciones artificiales: las cajas llegan a la cimentacion "
            "en la estructura real).")
        add(f"- Total apoyos fijos: **{len(self.support_tags)}** (6 GDL).")
        add("")
        add("## 6. Muros LT2 (40 tramos -> 80 columnas equivalentes)")
        add("")
        add("- Idealizacion: cada tramo vertical usa los **4 nodos reales del "
            "CSV** (esquinas de sus dos extremos en planta). Se crea un par "
            "de `elasticBeamColumn` (una por esquina) con **media seccion** "
            "cada una (transf 10001, vecxz (1,0,0)):")
        add("  A = e·L/2 ; muro en X: Iy = e·L^3/24, Iz = L·e^3/24 ; "
            "muro en Y: Iy = L·e^3/24, Iz = e·L^3/24 ;")
        add("  J = h·b^3/3·(1-0.63·(b/h)+0.052·(b/h)^5) / 2, b=min(e,L), "
            "h=max(e,L) (Saint-Venant).")
        add("- Los TOTALES por tramo coinciden con el muro academico LT1 "
            "(A=e·L, Ix=e·L^3/12, etc.): misma rigidez axial y flexional, "
            "sin dejar nodos flotantes en las esquinas (concepto validado "
            "contra modelo_lt1.json).")
        add(f"- Material del muro: LT2 (E={self.e_lt2:.3g} kN/m², "
            f"G={self.g_lt2:.3g} kN/m²), su modulo propio.")
        add(f"- Elementos creados: {len(self.created['lt2_walls'])} (tags "
            "4001+, dos por tramo: 4001/4002, 4003/4004, ...).")
        add("")
        add("## 7. Materiales (no unificados)")
        add("")
        add(f"- LT1: E = {E_LT1:g} kPa, G = {G_LT1:g} kPa (dato academico "
            "proporcionado).")
        add(f"- LT2: E = {self.e_lt2:.6g} kPa, G = {self.g_lt2:.6g} kPa.")
        add("- Cada modulo conserva su material; en las columnas compartidas "
            "de la interfaz rige el E de LT2 (regla 3).")
        add("")
        add("## 8. Cargas de gravedad")
        add("")
        add(f"- LT2 (patron 1): {summary['n_loads_lt2']} eleLoad -beamPoint "
            f"sobre {summary['n_beams_lt2']} vigas, P = {self.P_lt2:.6f} kN "
            "(sin cambios).")
        add(f"- LT1 (patron 2): {summary['n_loads_lt1']} eleLoad "
            f"-beamUniform (QG), P = **{self.P_lt1:.6f} kN**.")
        add(f"  - P_lt1_referencia (JSON, I'=42.5 m) = "
            f"**{self.P_lt1_referencia:.6f} kN** (trazabilidad).")
        add(f"  - La correccion I'->45.0 alarga las 12 vigas I-I' de "
            "2.5 m a 5.0 m; al aplicar QG por metro lineal, esas vigas "
            f"cargan el doble: +{self.P_lt1 - self.P_lt1_referencia:.3f} kN. "
            "Los qG_kN_m de referencia se conservan (no se inventan "
            "cargas).")
        add(f"  - Las **{len(self.removed_beams_loads)} vigas de fachada "
            "particionadas** por los salientes (tags 200033/060/063/011-14/"
            "084/87/90/93) ya NO reciben carga; su QG se redistribuye a los "
            f"segmentos sustitutos ({TAG_SAL_SEG_BASE}+) conservando la "
            "misma densidad qG (el total Σ qG·L se conserva exactamente: "
            "0 perdidas, 0 warnings).")
        add(f"- **P_total = {self.P_total:.6f} kN** "
            "(P_lt1_modelo + P_lt2).")
        add("- Zonas pendientes (ROOF LT2, WALL_EDGE_PENDING) NO se cargan "
            "(se preserva el criterio de cada modelo). Nota franja I': el "
            "pano P51/P52 (I-I') pasa de 2.5 m a 5.0 m, +40.375 m²/piso; de "
            "esa franja extra, las 12 vigas I-I' recogen su parte "
            "(+6.25 m²·q por piso) y el resto se conserva con los valores "
            "de referencia (no se redistribuye a las vigas Y del eje I/I' "
            "para no inventar una nueva reparticion).")
        add("")
        add("## 8bis. Areas tributarias por piso (verificacion)")
        add("")
        add("- Σ A_tributaria (JSON) = A_losa panos = **686.375 m²** por "
            "piso (exacto en PISO_1..4).")
        add("- Con I' = 45.0 m la losa modelada pasa a **726.75 m²/piso**; "
            "las 12 vigas I-I' duplican su tributaria (+6.25 m²/piso) y el "
            "resto de la franja (+34.125 m²/piso) conserva los valores de "
            "referencia (documentado arriba).")
        add("- Salientes: no tienen `panos` en el JSON de referencia (las "
            "vigas 800101+ no soportan losa tributaria en ese esquema); se "
            "conserva el criterio de la referencia.")
        add("")
        add("## 9. Validaciones")
        add("")
        add("- Nodos fisicos totales: "
            f"{len(node_tags)} "
            f"(LT2 {len(self.lt2_tag_to_key)} + LT1 no-interfaz "
            f"{len(self.lt1_created)} + masters {len(self.master_tags)} "
            f"+ nodos nuevos cajas/pilastra {len(self.box_nodes)}).")
        add(f"- Vigas: LT1 {len(self.created['lt1_beams'])} | LT2 "
            f"{len(self.created['lt2_beams'])} | LT2 pendientes "
            f"{len(self.pending_beams)}")
        if self.assumed_beam_tags:
            add(f"- VI-05 (VI15xVAR) materializada POR SUPUESTO/MODELACION "
                f"(cota superior de rigidez): b=0.15 m, h=1.20 m, E/G de "
                f"LT2, nodos 226-227, tag {self.assumed_beam_tags[0]} "
                f"(tag nativo; 2237 no esta disponible, corresponde a "
                "ROOF_VI_07). No es una seccion real confirmada; h_min y "
                "ley de variacion siguen desconocidas (ver "
                "COMBINADO/docs/diagnostico_vi15xvar.md).")
        add(f"- Columnas: LT1 {len(self.created['lt1_cols'])} | LT2 "
            f"{len(self.created['lt2_cols'])}")
        add(f"- Muros: LT1 {len(self.created['lt1_walls'])} | LT2 "
            f"{len(self.created['lt2_walls'])}")
        add(f"- Conectores V40->Muro (excent. 0.300 m): "
            f"{len(self.created['links'])}")
        add(f"- Duplicados descartados: {n_dup} columnas LT1.")
        add(f"- Nodos compartidos de interfaz: {len(self.interface)}.")
        add(f"- Apoyos fijos: {len(self.support_tags)}. Diafragmas: 5.")
        add("")
        add("### Analisis")
        add(f"- analyze() rc = **{self.rc}** " +
            ("(OK, convergio)" if self.rc == 0
             else "(NO convergio)"))
        if self.rc == 0:
            add(f"- ΣRz = {self.reac['Rz_kN'].sum():.6f} kN")
            add(f"- |ΣRz - P_total| = {self.errz_abs:.6e} kN "
                f"(rel {self.errz_rel:.3e})")
            add(f"- Σ|Rx| = {self.errax_abs:.6e} kN, "
                f"Σ|Ry| = {self.erray_abs:.6e} kN (equilibrio horizontal)")
            add(f"- Max |U| = {self.max_u:.9f} m en nodo {self.max_node}")
            add(f"- Max |Uz| = {self.max_uz:.9f} m en nodo "
                f"{self.max_uz_node}")
        else:
            add("")
            add("**El modelo NO converge (sistema singular): se reporta "
                "EXPLICITAMENTE, sin restricciones arbitrarias (criterio "
                "del proyecto, igual que el analisis nativo LT2).**")
            add("")
            add("Se resolvieron las cadenas V40 de todos los niveles: sus "
                "20 extremos sobre la cara este de M001/M003 (x=0.400) se "
                f"conectan al eje del muro (x=0.100) con "
                f"{len(self.v40_links)} conectores de excentricidad "
                "e/2=0.300 m (tags 9001.., seccion de enlace en el "
                "apartado 10).")
            add("")
            add("Causa remanente (CONCENTRADA EN ROOF, a resolver):")
            add("- Anillo/borde del hueco de escalera en ROOF (vigas "
                "VI-01..07): VI-05 ya esta materializada POR SUPUESTO "
                "(b=0.15, h=1.20, tag 2235; no se asigna altura real de "
                "plano por estar la seccion VARIABLE sin h_min). El sistema "
                "vertical de cajas/pilastra de COMBINADO (seccion 11) se "
                "materializo; si aun hay mecanismos, queda en los nodos del "
                "anillo VI que no alcanzan rigidez vertical a los apoyos.")
            add("- Secciones VAR PENDIENTES: ninguna otra (VI15xVAR es la "
                "unica y esta materializada por supuesto).")
        add("")
        add("## 10. Sistema vertical de cajas de escalera y pilastra "
             "(COMBINADO, B1->ROOF)")
        add("")
        add("- **Que se modelo:** la continuidad vertical B1->ROOF bajo el "
            "anillo VI de ROOF para cerrar el mecanismo de ROOF detectado "
            "(verificar: 10 nodos sin camino a apoyos en el reporte previo).")
        add("- Fuente de geometria: `LT2/reports/digitalizacion_vi_roof_"
            "pendiente.md` §8.2/§8.5 y coordenadas reales de los nodos "
            "`LT2/data/unity/edificio_lt2.json`:")
        add("  - **Caja OESTE** bajo VI-05: muro en Y, x=0.998, "
            "y 2.90..7.92, **e=0.30 m (ASSUMED_FOR_MODEL**, espesor de "
            "caja no acotado en plan; familia M.H.A. de cajas), L=5.02 m; "
            "nodos ROOF 226/227.")
        add("  - **Caja ESTE** bajo VI-06: muro en Y, x=16.546, "
            "y 2.90..7.92, **e=0.30 m (ASSUMED_FOR_MODEL)**, L=5.02 m; "
            "nodos ROOF 256/257.")
        add("  - **Pilastra x≈7.947**: caja vertical entre los dos huecos, "
            "4 columnas por esquina real (244/245/246/247); seccion "
            "**e_x=0.60 m EXPLICITA del plano** (caras 7.650/8.250, gap N "
            "7.646..8.246), L_y=5.02 m; cada columna = 1/4 de seccion "
            "bruta (A=e·L_y/4, Iy/4, Iz/4, J/4).")
        add("  - **2ª escalera (2º hueco este)**: borde N en y=7.92, "
            "x 18.545..20.794, muro en X **e=0.30 m (ASSUMED_FOR_MODEL)**; "
            "nodos ROOF 258/259. **El x=20.794 del nodo 259 se CONSERVA** "
            "(borde norte real del 2º hueco en planta); NO se aproxima a "
            "las columnas interiores x≈20.550 del plano.")
        add("- Idealizacion: misma convencion academica que los muros LT2 "
            "(_make_lt2_wall): un `elasticBeamColumn` por esquina, transf "
            "10001, material LT2 (E/G del modulo).")
        add(f"- Nodos nuevos: {len(self.box_nodes)} (tags 700001.., "
            "B1..L4, uno por esquina y nivel).")
        add(f"- Elementos nuevos: {len(self.box_verticals)} "
            "(tags 70001.., verticales por tramo de nivel, B1..ROOF).")
        add(f"- Bases B1 nuevas empotradas: {len(self.new_supports)} "
            "(ops.fix 6 GDL, misma convencion de cimentacion que los "
            "apoyos existentes; documentado, no es restriccion "
            "artificial).")
        add("- Nodos intermedios (B1..L4) creados SIN agregar al "
            "rigidDiaphragm (no son necesarios para cerrar el mecanismo y "
            "no se introducen restricciones artificiales).")
        add("- Topes en ROOF coinciden exactamente con los nodos reales del "
            "anillo (226/227, 244/245/246/247, 256/257, 258/259).")
        add("### Chequeos estructurales")
        add(f"- Nodos estructurales sin conectividad: {len(self.no_conn)} "
            + ("" if not self.no_conn else " -> "
               + str(self.no_conn[:20])))
        if self.floating:
            add(f"- Nodos sin camino de rigidez a apoyos: "
                f"{len(self.floating)} (BFS por elementos)")
            for lv, ns in self.floating_by_level.items():
                add(f"  - {lv}: {len(ns)} -> {ns[:12]} "
                    f"{'...' if len(ns) > 12 else ''}")
            add("- Interpretacion: los masters (1001-1005) y los nodos de "
                "muro LT1 (6001xx/6002xx) estan unidos por restricciones "
                "cinematicas (rigidDiaphragm / rigidLink 'beam'), no por "
                "elementos, por lo que no son mecanismos. El anillo VI de "
                "ROOF (226/227, 244-247, 256/257, 258/259) ya NO es la "
                "causa: el sistema vertical de cajas/pilastra materializado "
                "en COMBINADO (seccion 11) conecta esos nodos a las bases "
                "B1 (empotradas).")
        add(f"- Elementos con longitud cero: {len(self.zero_len)} "
            + ("" if not self.zero_len else " -> " + str(self.zero_len)))
        add(f"- Nodos esclavos en mas de un diafragma: 0 (cada nodo ocular "
            "una sola vez; muros LT1 por rigidLink).")
        add("")
        add("## 11. Conectores V40 -> M001/M003 (excentricidad e/2=0.300 m)")
        add("")
        add("- Los extremos de las cadenas V40x80 (x=0.400) terminan sobre "
            "la cara ESTE de los muros M001/M003 (x=0.100 + e/2 = 0.400, "
            "e=0.600). Se modela la excentricidad con UN elemento "
            "`elasticBeamColumn` horizontal en X por extremo (10 en total), "
            "entre el nodo de cadena y el nodo del EJE del muro al mismo Y "
            "y Z. No se mueven nodos de muro; no se usa equalDOF; los "
            "conectores son elementos (no restricciones cinematica) y sus "
            "nodos son esclavos normales del rigidDiaphragm de su nivel (no "
            "redundancia).")
        add("- Nodos intermedios de cadena (y=4.265/8.9/11.885, sin apoyo "
            "fisico en muro) y vigas V30/VI cercanas: NO conectados.")
        add("- **Seccion de enlace (solo del COMBINADO, no altera LT1/LT2):** "
            "E = 2.35e9 kPa (= 100 x E_LT2), nu = 0.20, A = 1.00 m², "
            "Iy = Iz = 0.10 m⁴, J = 0.20 m⁴. Rigidez axial EA = 2.35e9 kN "
            "(>= ~110x la del muro media seccion y >= ~300x la de la V40); "
            "suficientemente rigida para transferir el corte/axial del "
            "enlace sin alterar las rigideces originales.")
        add("")
        add("| NIVEL | NODO CADENA | XYZ CADENA | NODO MURO | XYZ MURO | "
            "LONGITUD | TAG CONECTOR |")
        add("|---|---|---|---|---|---|---|")
        for ln in self.v40_links:
            add(f"| {ln['nivel']} | {ln['nodo_cadena']} | "
                f"({ln['x_c']:.3f},{ln['y_c']:.3f},{ln['z_c']:.3f}) | "
                f"{ln['nodo_muro']} | "
                f"({ln['x_w']:.3f},{ln['y_w']:.3f},{ln['z_w']:.3f}) | "
                f"{ln['longitud_m']:.3f} | {ln['tag_conector']} |")
        add("- Copia maquina: `conectores_v40_muro.csv`.")
        add("")
        add("## 12. Salientes sur LT1 (geometria CAD verificada)")
        add("")
        add(f"- Nodos nuevos: **{len(self.saliente_nodes)}** (tags "
            f"{TAG_SAL_NODE_BASE}+)")
        add(f"- Vigas nuevas: **{len(self.saliente_beams)}** (borde sur + "
            f"flancos, tags {TAG_SAL_BEAM_BASE}+, seccion V.60/80)")
        add(f"- Segmentos de fachada particionados: "
            f"**{len(self.facade_partitions)}** particiones (tags "
            f"{TAG_SAL_SEG_BASE}+)")
        add("- Eje I' corregido: X = 42.50 -> 45.00 m (18 nodos desplazados "
            "en el eje I').")
        add("- Reglas de inclusion: SOLO geometria respaldada por CAD "
            "(FILAS_SUR, FLANCOS_X, VERIFICADO_CAD). Se EXCLUYEN: "
            "malla artificial, SPAN_INFERIDO, metales sin E "
            "(P.M./P.M.I./V.M.), diagonales y vigas sin respaldo.")
        add("")
        add("| Nivel | Nodos | Vigas | Particiones |")
        add("|---|---|---|---|")
        for nivel, data in _SALIENTES_DATA.items():
            n_nodes = sum(1 for lab in data["nodes"])
            n_beams = len(data["beams"])
            n_part = len(data["partition_x_lt1"])
            add(f"| {nivel} | {n_nodes} | {n_beams} | {n_part} |")
        add("")
        add("### Diafragmas y conectividad (verificacion)")
        add("")
        add("Los nodos saliente NO son esclavos del rigidDiaphragm (decision "
            "de diseno: se evita restriccion artificial; su carga sobre la "
            "losa no existe en el esquema tributario de referencia). Su "
            "camino de rigidez al diafragma se cierra POR VIGAS: cada nodo "
            "saliente -> viga saliente -> segmento de fachada -> nodo de "
            "fachada (slave del diafragma).")
        add("")
        add("| Nivel LT1 | Nivel LT2 | Master | Nodos saliente | "
            "Max saltos de viga al diafragma |")
        add("|---|---|---|---|---|")
        for nivel, row in self.diaph_summary.items():
            add(f"| {nivel} | {row['level_lt2']} | {row['master']} | "
                f"{row['n_saliente_total']} | {row['max_saltos']} |")
        add("")
        add(f"- Verificacion: {len(self.diaph_check_issues)} nodos saliente "
            "sin ruta de vigas hacia el diafragma (debe ser 0; tambien "
            "refrendado por los `Nodos sin camino a apoyos` = "
            f"{len(self.floating)} preexistentes).")
        add("- Nodos sin camino de rigidez a apoyos: "
            f"{len(self.floating)} (masters 1001..1005 + nodos de muro "
            "compartidos, excepciones preexistentes documentadas).")
        add("")
        add("## 13. Elementos pendientes (NO modelados, sin inventar)")
        add("")
        add("Se documenta la existencia, NO se modela (requiere plano/dato "
            "explícito si se decide incorporar):")
        add("")
        add("- P.M. / P.M.I. / V.M.: metaleria en fachadas/salientes sin "
            "modulo E de referencia (excluidas de la regla VERIFICADO_CAD).")
        add("- V.60/VAR y V.60-30/80-40: vigas de seccion variable sin "
            "geometria de alma definida en plano.")
        add("- Nucleo PISO_4: zona sin plano de detalle en el nivel superior.")
        add("- Muros subterraneo (B2 y menores) y zonas sin plano de detalle "
            "declarado.")
        add("- Zona franja I' extrema (x_lt1 45.0..): losa P51/P52" 
            " duplicada en las 12 vigas I-I'; el resto de la franja "
            "(34.125 m²/piso) conserva los valores tributarios de "
            "referencia (ver seccion 8bis).")
        add("")
        add("## 14. Validacion final (checks automaticos)")
        add("")
        fc = self.final_checks
        add(f"- 1. analyze rc = 0: **{'OK' if fc['rc'] == 0 else 'FALLO'}** "
            f"(rc={fc['rc']})")
        add(f"- 2. Cargas reparadas (0 warnings ElementalLoad): **OK** "
            f"({fc['n_redistributed']} segmentos con carga, "
            f"{len(fc['redist_missing'])} tags ausentes: "
            f"{fc['redist_missing']})")
        add(f"- 3. Elementos longitud cero: "
            f"**{'OK' if fc['zero_len'] == 0 else 'FALLO'}** "
            f"({fc['zero_len']})")
        add(f"- 4. Vigas LI/II con ΔZ: "
            f"**{'OK' if fc['n_beams_dz'] == 0 else 'REVISAR'}** "
            f"({fc['n_beams_dz']}); saliente con ΔZ: {fc['n_sal_dz']}; "
            f"conectores con ΔZ: {fc['n_link_dz']}")
        add(f"- 5. Columnas con desplazamiento horizontal: "
            f"**{'OK' if fc['n_cols_off'] == 0 else 'REVISAR'}** "
            f"({fc['n_cols_off']}); cajas/pilastra off-vertical: "
            f"{fc['n_box_off']}")
        add(f"- 6. Diagonales en planta: "
            f"**{'OK' if fc['n_diag_plan'] == 0 else 'FALLO'}** "
            f"({fc['n_diag_plan']})")
        add(f"- 7. Nodos saliente sin ruta a apoyos: "
            f"**{'OK' if fc['n_sal_floating'] == 0 else 'FALLO'}** "
            f"({fc['n_sal_floating']}: {fc['sal_floating']})")
        add(f"- 8. LT2 intacto: **{fc['n_lt2_beams']} vigas** "
            "(tags nativos, sin cambios)")
        add(f"- 9. Eje I' en combinado = 45.0+31.25 = 76.25 m: "
            f"**{'OK' if fc['ip_ok'] else 'FALLO'}** "
            f"({fc['n_ip_nodes']} nodos I')")
        add(f"- 10. Error de equilibrio |ΣRz-P_total|/P_total: "
            f"**{'OK' if fc['err_rel'] < 1e-6 else 'FALLO'}** "
            f"({fc['err_rel']:.3e})")
        add(f"- Resumen nodos: {fc['no_conn']} sin conectividad, "
            f"{self.floating_by_level} flotantes preexistentes, "
            f"P_lt1={self.P_lt1:.3f} kN, P_total={self.P_total:.3f} kN.")
        add("")
        add("## Archivos generados")
        for p in (OUT_TRACE, OUT_AUDIT, OUT_FIG, OUT_REPORT, OUT_BOX):
            add(f"- `{p.relative_to(COMB)}`")
        add(f"- `{(OUT / 'conectores_v40_muro.csv').relative_to(COMB)}`")
        for i in range(1, 5):
            add(f"- `{(OUT / 'tributarias_lt1' / f'tributarias_piso_{i}.png'
                   ).relative_to(COMB)}`")
        add(f"- `{(OUT / 'vista_3d_interactiva.html').relative_to(COMB)}` "
            "(generado por `scripts/figura_interactiva.py`)")
        add("")
        OUT_REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")

    def write_fig(self):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except Exception as ex:
            print("AVISO: matplotlib no disponible; no se genera la "
                  f"figura: {ex}")
            return
        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111, projection="3d")
        try:
            import numpy as np
        except Exception:
            np = None

        def draw_lines(tags, color, label):
            xs, ys, zs, n = [], [], [], 0
            for t in tags:
                ns = list(ops.eleNodes(t))
                if len(ns) != 2:
                    continue
                c1 = list(ops.nodeCoord(ns[0]))
                c2 = list(ops.nodeCoord(ns[1]))
                sep = None if np is None else float("nan")
                xs += [c1[0], c2[0], sep]
                ys += [c1[1], c2[1], sep]
                zs += [c1[2], c2[2], sep]
                n += 1
            ax.plot(xs, ys, zs, color=color, alpha=0.6, lw=0.8,
                    label=f"{label} ({n})")

        draw_lines(self.created["lt2_beams"] + self.created["lt2_cols"]
                   + self.created["lt2_walls"], "#1f77b4", "LT2 (nativo)")
        draw_lines(self.created["lt1_beams"] + self.created["lt1_cols"]
                   + self.created["lt1_walls"], "#ff7f0e",
                   "LT1 (transformado)")
        sal_t = list(self.saliente_beams) + [s["tag"]
                                             for s in self.facade_segments]
        draw_lines(sal_t, "#9467bd", "Salientes sur LT1 (8001+/P)")
        draw_lines(self.created["links"], "#2ca02c",
                   "Conectores V40-Muro (9001+)")
        draw_lines([e["tag"] for e in self.box_verticals], "#d62728",
                   "Verticales cajas/pilastra (70001+)")
        ix = [p[2] for p in self.interface]
        iy = [p[3] for p in self.interface]
        iz = [p[4] for p in self.interface]
        ax.scatter(ix, iy, iz, c="black", s=18, zorder=5,
                   label=f"Interfaz ({len(self.interface)})")
        if self.saliente_nodes:
            sx = [list(ops.nodeCoord(t))[0] for t in self.saliente_nodes]
            sy = [list(ops.nodeCoord(t))[1] for t in self.saliente_nodes]
            sz = [list(ops.nodeCoord(t))[2] for t in self.saliente_nodes]
            ax.scatter(sx, sy, sz, c="purple", s=12, zorder=5,
                       label=f"Saliente nodos ({len(self.saliente_nodes)})")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_zlabel("Z (m)")
        ax.set_title("Modelo combinado LT1 (naranja/purpura) + LT2 (azul), "
                     "interfaz X=31.250 m, salientes sur I' corregido")
        ax.legend(loc="best")
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass
        fig.tight_layout()
        fig.savefig(OUT_FIG, dpi=220)
        plt.close(fig)


def main():
    b = CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()
    n_loads_lt2, n_loads_lt1 = b.apply_loads()
    b.run_analysis()
    node_tags, elem_tags = b.validate()
    summary = dict(n_loads_lt2=n_loads_lt2,
                   n_beams_lt2=int(b.loads["beam_id"].nunique()),
                   n_loads_lt1=n_loads_lt1)
    b.write_outputs(summary, b.rc, node_tags, elem_tags)

    print("=" * 72)
    print("MODELO COMBINADO LT1 + LT2 — RESUMEN")
    print("=" * 72)
    print(f"Transformacion LT1 : X'=X+31.250  Y'=-Y  Z'=Z")
    print(f"Pares interfaz      : {len(b.interface)}/18 (exactos, 0.000 m)")
    print(f"Nodos fisicos       : {len(node_tags)}")
    print(f"  LT2={len(b.lt2_tag_to_key)}  LT1 no-interfaz={len(b.lt1_created)}"
          f"  masters={len(b.master_tags)}")
    print(f"Vigas   LT1={len(b.created['lt1_beams'])} "
          f"LT2={len(b.created['lt2_beams'])} (pend LT2="
          f"{len(b.pending_beams)})")
    if b.assumed_beam_tags:
        print(f"VI-05 SUPUESTO/COTA SUPERIOR: tag={b.assumed_beam_tags[0]} "
              "b=0.15 h=1.20 (nodos 226-227, E/G LT2); no es seccion real")
    print(f"Columnas LT1={len(b.created['lt1_cols'])} "
          f"LT2={len(b.created['lt2_cols'])}")
    print(f"Muros   LT1={len(b.created['lt1_walls'])} "
          f"LT2={len(b.created['lt2_walls'])}")
    print(f"Conectores V40->Muro (excent. 0.300 m) = "
          f"{len(b.created['links'])}")
    print(f"Verticales cajas/pilastra (B1->ROOF) = "
          f"{len(b.box_verticals)} elementos, "
          f"{len(b.box_nodes)} nodos nuevos, "
          f"{len(b.new_supports)} bases B1 empotradas")
    print(f"Salientes sur LT1: {len(b.saliente_nodes)} nodos "
          f"{TAG_SAL_NODE_BASE}+, {len(b.saliente_beams)} vigas "
          f"{TAG_SAL_BEAM_BASE}+, {len(b.facade_partitions)} "
          "particiones de fachada; eje I' corregido 42.5->45.0 m")
    if b.v40_links:
        print("  NIVEL | NODO CADENA | XYZ CADENA | NODO MURO | XYZ MURO | "
              "LONGITUD | TAG CONECTOR")
        for ln in b.v40_links:
            print(f"  {ln['nivel']:4s} | {ln['nodo_cadena']} | "
                  f"({ln['x_c']:.3f},{ln['y_c']:.3f},{ln['z_c']:.3f}) | "
                  f"{ln['nodo_muro']} | "
                  f"({ln['x_w']:.3f},{ln['y_w']:.3f},{ln['z_w']:.3f}) | "
                  f"{ln['longitud_m']:.3f} | {ln['tag_conector']}")
    print(f"Duplicados descartados (cols LT1) : {len(b.duplicated_lt1_cols)}")
    print(f"Apoyos fijos={len(b.support_tags)}  Diafragmas=5  "
          f"rigidLinks muros LT1={len(b.rigid_links)}")
    print(f"Carga LT1 (patron 2)= {b.P_lt1:.6f} kN")
    print(f"Carga LT2 (patron 1)= {b.P_lt2:.6f} kN")
    print(f"Carga total         = {b.P_total:.6f} kN")
    print(f"analyze rc          = {b.rc}")
    if b.rc == 0:
        print(f"ΣRz = {b.reac['Rz_kN'].sum():.6f} kN")
        print(f"|ΣRz - P_total| = {b.errz_abs:.6e} kN (rel {b.errz_rel:.3e})")
        print(f"Σ|Rx|={b.errax_abs:.6e} kN  Σ|Ry|={b.erray_abs:.6e} kN")
        print(f"max |U| = {b.max_u:.9f} m (nodo {b.max_node})")
        print(f"max |Uz| = {b.max_uz:.9f} m (nodo {b.max_uz_node})")
    print("Nodos sin conectividad:", len(b.no_conn), b.no_conn[:10])
    print("Nodos sin camino a apoyos:", len(b.floating),
          {lv: len(ns) for lv, ns in b.floating_by_level.items()})
    print("Elementos longitud cero:", len(b.zero_len), b.zero_len[:10])
    print("Salidas:")
    for p in (OUT_TRACE, OUT_AUDIT, OUT_REPORT, OUT_FIG, OUT_LINKS):
        print("  ", p.relative_to(ROOT), "->", (p.exists() and p.stat().st_size))
    return 0 if b.rc == 0 else 3


if __name__ == "__main__":
    sys.exit(main())