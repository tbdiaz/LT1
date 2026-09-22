#!/usr/bin/env python3
"""exportar_unity_combinado.py - Exportacion unica del modelo COMBINADO LT1+LT2.

Etapa P1L4. Genera `COMBINADO/outputs/unity/modelo_combinado.json` a partir del
modelo REAL construido por `run_combined.CombinedBuilder` (no de una union
manual de JSONs). El archivo contiene, por cada caso de carga y la
combinacion existente:

  * geometria : nodos (tag/coordenadas/origen/nivel), elementos
    (tag/tipo/origen/nodeI/nodeJ/seccion/material/vecxz/ejes locales),
    apoyos, masters, diafragmas, constraint_links.
  * cargas aplicadas por caso (con los mismos patrones que semana03).
  * areas tributarias LT1 (JSON) y LT2 (CSV).
  * resultados OpenSees: fuerzas locales [N,Vy,Vz,T,My,Mz] por extremo y caso,
    desplazamientos por nodo, reacciones y equilibrio por caso.

Casos (modelo limpio por caso, exactamente como semana03):
    G       = patrones 1/2  (run_combined.apply_loads)         [gravedad]
    Q       = patrones 3/4  (semana03_live_load)               [viva q=4.0 kPa]
    EX      = patron 5      (semana03_seismic)                 [sismo +X]
    EY      = patron 6      (semana03_seismic)                 [sismo +Y]
    COMBO_R = patrones 1,2,3,4,5 (R = 1.0G + 1.0Q + 1.0EX + 0.0EY)

NO modifica run_combined, semana03_*, capacidad, geometria ni cargas.
NO borra modelo_lt1.json. NO toca la logica de Unity.

Uso:
    cd COMBINADO/src && python3 exportar_unity_combinado.py
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import openseespy.opensees as ops  # noqa: E402

from run_combined import (  # noqa: E402
    ASSUMED_SECTIONS, COMB, E_LT1, G_LT1, JSON_LT1, NODE_OFFSET_LT1,
    ROOT, SHIFT_X, CombinedBuilder, _SALIENTES_DATA, _jrect, _rect_props,
    _zname,
)
from semana03_live_load import (  # noqa: E402
    Q_G_LT2, apply_q_patterns, build_q_lt1, build_q_lt2,
)
from semana03_seismic import (  # noqa: E402
    apply_lateral, build_weight_table, forces_per_floor,
)

TAG_BEAM_BASE = 2001
TAG_COL_BASE = 3001
TAG_WALL_BASE = 4001

# vecxz reales de las geomTransf registradas en run_combined.build()
VEC_TRANS_COL = (0, 1, 0)          # LT2 columnas (transf tag 1)
VEC_TRANS_B_X = (0, 0, 1)          # LT2 vigas X (transf tag 2)
VEC_TRANS_B_Y = (0, 0, 1)          # LT2 vigas Y (transf tag 3)
VEC_TRANS_COL_LT1 = (1, 0, 0)      # LT1 columnas/muros + verticales (10001)
VEC_TRANS_B_LT1 = (0, 0, 1)        # LT1 vigas + salientes + segmentos (10002/3)

OUT = COMB / "outputs" / "unity" / "modelo_combinado.json"
TRIB_LT2 = ROOT / "LT2" / "data" / "loads" / "tributary_areas_LT2.csv"

CASOS = ["G", "Q", "EX", "EY", "COMBO_R"]

CONVENCION_EJES = {
    "x": "unitario de nodeI a nodeJ",
    "vecxz": "vector de referencia de la geomTransf (ver elemento.vecxz)",
    "z": "normalizado(vecxz - (vecxz . x) x)",
    "y": "z x x",
}
CONV_SECCION = (
    "ops.section('Elastic', tag, E, A, Iz_arg, Iy_arg, G, J); LT2 calcula "
    "A, Iy=b*h^3/12, Iz=h*b^3/12 (_rect_props) y J (_jrect); Iy_m4/Iz_m4 "
    "del JSON siguen esa misma convencion"
)
CONV_FUERZAS = (
    "[N, Vy, Vz, T, My, Mz] en el extremo i seguido de [N, Vy, Vz, T, My, "
    "Mz] en el extremo j, en coordenadas locales del elemento (eleResponse "
    "'localForce' de elasticBeamColumn)."
)


def _key_raw(x, y, z):
    return (round(float(x), 6), round(float(y), 6), round(float(z), 6))


def _z_to_level(levels):
    return {round(_zname(levels, n), 6): n for n in levels["name"]}


def _drop(vx, vy, vz, x):
    proj = vx * x[0] + vy * x[1] + vz * x[2]
    return (vx - proj * x[0], vy - proj * x[1], vz - proj * x[2])


def _local_axes(c1, c2, vecxz):
    """Ejes locales segun la convencion Linear CrdTransf de OpenSees."""
    dx, dy, dz = c2[0] - c1[0], c2[1] - c1[1], c2[2] - c1[2]
    l = math.hypot(dx, math.hypot(dy, dz))
    if l < 1e-12:
        raise RuntimeError("elemento de longitud 0")
    x = (dx / l, dy / l, dz / l)
    z0x, z0y, z0z = _drop(vecxz[0], vecxz[1], vecxz[2], x)
    nz = math.hypot(z0x, math.hypot(z0y, z0z))
    if nz < 1e-12:
        raise RuntimeError("vecxz paralelo a x del elemento")
    z = (z0x / nz, z0y / nz, z0z / nz)
    y = (z[1] * x[2] - z[2] * x[1],
         z[2] * x[0] - z[0] * x[2],
         z[0] * x[1] - z[1] * x[0])
    return x, y, z


def _elem_len(ni, nj, coords):
    c1, c2 = coords[ni], coords[nj]
    return math.hypot(c2[0] - c1[0], math.hypot(c2[1] - c1[1], c2[2] - c1[2]))


def _rect_sec(b_m, h_m):
    a, iy, iz = _rect_props(b_m, h_m)
    j = _jrect(min(b_m, h_m), max(b_m, h_m))
    return a, iy, iz, j


def _parse_poly(s):
    s = s.replace("|", ";")  # 4 poligonos fuente traen | en vez de ;;
    tokens = [p.strip() for p in s.replace(";", ",").split(",")]
    pts = []
    for k in range(0, len(tokens) - 1, 2):
        pts.append([round(float(tokens[k]), 4), round(float(tokens[k + 1]), 4)])
    return pts


class ExportadorCombinado:
    """Captura geometria y resultados del combinado y escribe el JSON."""

    def __init__(self):
        self.z2lv = {}
        self.coords = {}
        self.node_origin = {}
        self.nivel_of_node = {}
        self.p_f_ex = 0.0

    # ---- helpers -----------------------------------------------------------
    def _fresh_builder(self):
        b = CombinedBuilder()
        b.prepare()
        b.check_interface()
        b.build()
        return b

    def _nivel_by_z(self, z):
        return self.z2lv.get(round(float(z), 6))

    # ---- geometria ---------------------------------------------------------
    def _index_nodes(self, b):
        lt2_keys = set(b.lt2_tag_to_key)
        masters = set(b.master_tags)
        interfaz = {int(lt2t) for _t, lt2t, _x, _y, _z in b.interface}
        box = set(b.box_nodes)
        sal = set(b.saliente_nodes)
        lt1_combined = {int(c) for c in b.lt1_combo.values()
                        if c not in lt2_keys and c not in masters}

        coords, origen, nivel = {}, {}, {}
        for t in ops.getNodeTags():
            t = int(t)
            coords[t] = [float(v) for v in ops.nodeCoord(t)]
            nivel[t] = self._nivel_by_z(coords[t][2])
            if t in masters:
                origen[t] = "LT2_master"
            elif t in box:
                origen[t] = "COMBINADO_caja"
            elif t in sal:
                origen[t] = "LT1_saliente"
            elif t in interfaz:
                origen[t] = "LT1_LT2_interfaz"
            elif t in lt2_keys:
                origen[t] = "LT2"
            elif t in lt1_combined:
                origen[t] = "LT1"
            else:
                origen[t] = "OTRO"
        self.coords, self.node_origin, self.nivel_of_node = coords, origen, nivel
        return coords, origen, nivel

    def _lt2_section_dims(self, b, sid):
        if sid in ASSUMED_SECTIONS:
            return ASSUMED_SECTIONS[sid]
        sub = b.sections[b.sections.section_id == sid]
        if not sub.empty:
            bm, hm = float(sub.b_m.iloc[0]), float(sub.h_m.iloc[0])
            if bm > 0.0 and hm > 0.0:
                return bm, hm
        return (None, None)

    def _lt2_sec_meta(self, b, sid, e2, g2):
        bm, hm = self._lt2_section_dims(b, sid)
        a, iy, iz, j = _rect_sec(bm, hm)
        return dict(label=str(sid), b_m=bm, h_m=hm, A_m2=a,
                    Iy_m4=iy, Iz_m4=iz, J_m4=j, E_kPa=e2, G_kPa=g2)

    def _lt1_sec_meta(self, rec):
        return dict(label=rec.get("seccion", ""), b_m=None, h_m=None,
                    A_m2=float(rec["A_m2"]), Iy_m4=float(rec["Iy_m4"]),
                    Iz_m4=float(rec["Iz_m4"]), J_m4=float(rec["J_m4"]),
                    E_kPa=E_LT1, G_kPa=G_LT1)

    def _elements(self, b):
        e2, g2 = b.e_lt2, b.g_lt2
        coords = self.coords
        out = []

        def add(tag, tipo, origen, seccion, vecxz, meta):
            tag = int(tag)
            nids = [int(t) for t in ops.eleNodes(tag)]
            if len(nids) != 2:
                raise RuntimeError(
                    f"EXPORT: elemento {tag} con {len(nids)} nodos.")
            ni, nj = nids
            l = _elem_len(ni, nj, coords)
            x, y, z = _local_axes(coords[ni], coords[nj], vecxz)
            out.append(dict(
                elementTag=tag, tipo=tipo, origen=origen,
                nodeI=ni, nodeJ=nj,
                longitud_m=round(l, 9),
                seccion=seccion, vecxz=list(vecxz),
                ejes_locales=dict(x=x, y=y, z=z), **meta))

        # ---- LT2 ----
        for tag in b.created["lt2_beams"]:
            i = int(tag) - TAG_BEAM_BASE
            rec = b.lt2_elems["beams"][i]
            sec = self._lt2_sec_meta(b, rec["section"], e2, g2)
            ni, nj = int(rec["n1"]), int(rec["n2"])
            ddx = abs(self.coords[nj][0] - self.coords[ni][0])
            ddy = abs(self.coords[nj][1] - self.coords[ni][1])
            transf_tag = 2 if ddx >= ddy else 3
            add(tag, "viga", "LT2", sec,
                VEC_TRANS_B_X,
                dict(nivel=rec["level"], beam_id=rec["id"],
                     transf_tag=transf_tag,
                     seccion_id=str(rec["section"])))
        for tag in b.created["lt2_cols"]:
            i = int(tag) - TAG_COL_BASE
            rec = b.lt2_elems["columns"][i]
            nv0 = self._nivel_by_z(coords[int(rec["n1"])][2])
            nv1 = self._nivel_by_z(coords[int(rec["n2"])][2])
            sec = self._lt2_sec_meta(b, rec["section"], e2, g2)
            add(tag, "columna", "LT2", sec, VEC_TRANS_COL,
                dict(nivel=nv0, nivel_bajo=nv0, nivel_alto=nv1,
                     columna_id=rec["id"], transf_tag=1,
                     seccion_id=str(rec["section"])))
        for tag in b.created["lt2_walls"]:
            i = (int(tag) - TAG_WALL_BASE) // 2
            rec = b.lt2_elems["walls"][i]
            t_ = rec["thickness"]
            l_ = rec["length"]
            nv0 = self._nivel_by_z(coords[int(rec["n1"])][2])
            nv1 = self._nivel_by_z(coords[int(rec["n2"])][2])
            sec = dict(label="M.H.A. e=%g m (col. equiv. 1/2 seccion)" % t_,
                       b_m=t_, h_m=l_, A_m2=t_ * l_ / 2.0,
                       Iy_m4=l_ * t_ ** 3 / 24.0, Iz_m4=t_ * l_ ** 3 / 24.0,
                       J_m4=_jrect(t_, l_) / 2.0, E_kPa=e2, G_kPa=g2,
                       espesor_m=t_)
            add(tag, "muro_corner", "LT2", sec,
                VEC_TRANS_COL_LT1,
                dict(nivel=nv0, corner="A" if (int(tag) - TAG_WALL_BASE) % 2
                     == 0 else "B", muro_id=rec["id"], transf_tag=10001,
                     nivel_bajo=nv0, nivel_alto=nv1))

        # ---- LT1 (vigas originales, salientes y segmentos de fachada) ----
        beams_json = {int(x["elementTag"]): x for x in b.json_lt1["beams"]}
        saliente_set = set(b.saliente_beams)
        seg2orig = self._facade_segment_origins(b)
        for tag in b.created["lt1_beams"]:
            tag = int(tag)
            n_i, n_j = [int(t) for t in ops.eleNodes(tag)]
            if tag in saliente_set:
                a, iy, iz, j = _rect_sec(0.60, 0.80)
                sec = dict(label="V.60/80", b_m=0.60, h_m=0.80,
                           A_m2=a, Iy_m4=iy, Iz_m4=iz, J_m4=j,
                           E_kPa=E_LT1, G_kPa=G_LT1)
                add(tag, "viga_saliente", "LT1", sec,
                    VEC_TRANS_B_LT1,
                    dict(nivel=self._nivel_by_z(coords[n_i][2]),
                         nivel_lt1=self._saliente_nivel_of(n_i),
                         transf_tag=10002, seccion_id="V60x80"))
            elif tag in seg2orig:
                orig = beams_json[seg2orig[tag]]
                sec = self._lt1_sec_meta(orig)
                add(tag, "segmento_fachada", "LT1", sec,
                    VEC_TRANS_B_LT1,
                    dict(nivel=self._nivel_by_z(coords[n_i][2]),
                         nivel_lt1=orig.get("nivel"), transf_tag=10002,
                         tag_original=seg2orig[tag],
                         seccion_id=orig.get("seccion", "")))
            else:
                rec = beams_json[tag]
                vecxz = VEC_TRANS_B_LT1
                fam = (10003 if rec.get("eje_x_i") == rec.get("eje_x_j")
                       else 10002)
                sec = self._lt1_sec_meta(rec)
                add(tag, "viga", "LT1", sec,
                    vecxz, dict(nivel=rec.get("nivel"), transf_tag=fam,
                                orientacion=rec.get("orientacion"),
                                seccion_id=rec.get("seccion", "")))

        cols_json = {int(x["elementTag"]): x for x in b.json_lt1["columns"]}
        for tag in b.created["lt1_cols"]:
            tag = int(tag)
            rec = cols_json[tag]
            sec = self._lt1_sec_meta(rec)
            add(tag, "columna", "LT1", sec,
                VEC_TRANS_COL_LT1,
                dict(nivel=rec.get("nivel"), transf_tag=10001,
                     nivel_inferior=rec.get("nivel_inferior"),
                     nivel_superior=rec.get("nivel_superior"),
                     seccion_id=rec.get("seccion", "")))

        walls_json = {int(x["elementTag"]): x for x in b.json_lt1["walls"]}
        for tag in b.created["lt1_walls"]:
            tag = int(tag)
            rec = walls_json[tag]
            sec = self._lt1_sec_meta(rec)
            sec["espesor_m"] = float(rec.get("espesor_m", 0.0) or 0.0)
            add(tag, "muro", "LT1", sec,
                VEC_TRANS_COL_LT1,
                dict(nivel=rec.get("nivel_superior") or rec.get("nivel"),
                     nivel_inferior=rec.get("nivel_inferior"),
                     nivel_superior=rec.get("nivel_superior"),
                     transf_tag=10001,
                     clave=rec.get("clave", ""),
                     fuente=rec.get("fuente", ""),
                     estado_geometria=rec.get("estado_geometria", ""),
                     constraint=rec.get("constraint", ""),
                     seccion_id=rec.get("seccion", "")))

        # ---- solo COMBINADO ----
        E_l = 2_780_000_000.0
        G_l = E_l / (2.0 * 1.20)
        for r in b.v40_links:
            sec = dict(label="ENLACE V40-MURO", b_m=None, h_m=None,
                       A_m2=1.00, Iy_m4=0.10, Iz_m4=0.10, J_m4=0.20,
                       E_kPa=E_l, G_kPa=G_l)
            add(r["tag_conector"], "conector_v40_muro", "COMBINADO", sec, VEC_TRANS_B_X,
                dict(nivel=r["nivel"], muro=r["muro"], transf_tag=2,
                     nodo_muro=int(r["nodo_muro"])))
        for r in b.v30_connections:
            sec = self._lt2_sec_meta(b, r["seccion"], e2, g2)
            add(r["tag"], "viga", "COMBINADO", sec, VEC_TRANS_B_X,
                dict(nivel=r["nivel"], beam_id=r["beam_id"],
                     tag_original=r["parent"], transf_tag=2,
                     seccion_id=r["seccion"], fuente=r["fuente"]))
        for v in b.box_verticals:
            sec = dict(label="VERTICAL %s" % v["tipo"].upper(),
                       b_m=None, h_m=None, A_m2=v["A"], Iy_m4=v["Iy"],
                       Iz_m4=v["Iz"], J_m4=v["J"], E_kPa=e2, G_kPa=g2,
                       nota=v["nota"])
            add(v["tag"], "vertical_caja", "COMBINADO", sec, VEC_TRANS_COL_LT1,
                dict(nivel=v["nivel_bajo"], transf_tag=10001,
                     familia=v["familia"], tipo_v=v["tipo"],
                     nivel_bajo=v["nivel_bajo"], nivel_alto=v["nivel_alto"]))

        tags = {e["elementTag"] for e in out}
        registered = (set(b.created["lt2_beams"]) | set(b.created["lt2_cols"])
                      | set(b.created["lt2_walls"]) | set(b.created["lt1_beams"])
                      | set(b.created["lt1_cols"]) | set(b.created["lt1_walls"])
                      | set(b.created["links"])
                      | set(r["tag"] for r in b.v30_connections)
                      | set(v["tag"] for v in b.box_verticals))
        if tags != registered:
            raise RuntimeError(
                "EXPORT: inventario exportado != registros del builder.")
        if tags != set(int(t) for t in ops.getEleTags()):
            raise RuntimeError(
                "EXPORT: inventario exportado != ops.getEleTags().")
        return sorted(out, key=lambda e: e["elementTag"])

    def _final_segments_of_level(self, b, nivel):
        return [s for s in b.facade_segments if s["nivel"] == nivel]

    def _facade_segment_origins(self, b):
        seg2orig = {}
        for nivel, data in _SALIENTES_DATA.items():
            z = float(data["z_m"])
            orig = b._json_facade_beams(z)
            for s in self._final_segments_of_level(b, nivel):
                mid = 0.5 * (s["x1_lt1"] + s["x2_lt1"])
                father = None
                for o in orig:
                    if o["x1_lt1"] - 1e-6 <= mid <= o["x2_lt1"] + 1e-6:
                        father = o
                        break
                if father is None:
                    raise RuntimeError(
                        f"EXPORT: segmento {s['tag']} de {nivel} sin viga "
                        "original de fachada.")
                seg2orig[int(s["tag"])] = int(father["tag"])
        return seg2orig

    def _saliente_nivel_of(self, node_tag):
        z = round(self.coords[int(node_tag)][2], 6)
        for nivel, data in _SALIENTES_DATA.items():
            if abs(round(float(data["z_m"]), 6) - z) < 1e-6:
                return nivel
        return None

    # ---- apoyos / masters / diafragmas -----------------------------------
    def _supports(self, b):
        out = []
        z_base = _zname(b.levels, "B1")
        for r in b.supports.itertuples(index=False):
            tag = int(b.lt2_key_to_tag[_key_raw(r.x_m, r.y_m, z_base)])
            out.append(dict(nodeTag=tag, origen="LT2",
                            restricciones=[int(r.ux), int(r.uy), int(r.uz),
                                           int(r.rx), int(r.ry), int(r.rz)],
                            nivel="B1"))
        for tag in b.box_support_tags:
            out.append(dict(nodeTag=int(tag), origen="COMBINADO_caja",
                            restricciones=[1, 1, 1, 1, 1, 1], nivel="B1"))
        for s in b.json_lt1["supports"]:
            t = int(b.lt1_combo[int(s["nodeTag"])])
            out.append(dict(nodeTag=t, origen="LT1",
                            restricciones=s.get("restricciones") or
                            [1, 1, 1, 1, 1, 1],
                            nivel="B1"))
        seen, uniq = set(), []
        for o in out:
            if o["nodeTag"] in seen:
                continue
            seen.add(o["nodeTag"])
            uniq.append(o)
        return sorted(uniq, key=lambda o: o["nodeTag"])

    def _masters(self, b):
        out = []
        for r in b.masters.itertuples(index=False):
            tag = int(b.master_tag_by_id[r.master_id])
            out.append(dict(nodeTag=tag, nivel=r.level, x_m=float(r.x_m),
                            y_m=float(r.y_m), z_m=float(r.z_m),
                            restricciones=[0, 0, 1, 1, 1, 0],
                            metodo=r.method))
        return sorted(out, key=lambda o: o["nodeTag"])

    def _diaphragms(self, b):
        out = []
        for lv in b.diaph_masters:
            master = int(b.diaph_masters[lv])
            slaves = sorted(int(t) for t in b.diaph_slaves[lv])
            out.append(dict(nivel=lv, master=master, slaves=slaves,
                            z_m=round(self.coords[master][2], 9),
                            dof_compatibilizados="Ux(1), Uy(2), Rz(6)"))
        return sorted(out, key=lambda o: o["nivel"])

    def _constraint_links(self, b):
        return [dict(nivel=r["nivel"], master=int(r["master"]),
                     nodo_muro=int(r["nodo_muro"]),
                     tag_original=int(r["tag_original"]))
                for r in b.rigid_links]

    # ---- cargas (reproducen los patrones de cada caso) -------------------
    def _loads_g(self, b):
        """Igual a apply_loads(): patron 1 (LT2 beamPoint) + patron 2 (LT1)."""
        def _ops_len(tag):
            ns = list(ops.eleNodes(int(tag)))
            c1 = ops.nodeCoord(int(ns[0]))
            c2 = ops.nodeCoord(int(ns[1]))
            return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2
                             + (c1[2] - c2[2]) ** 2)

        rows = []
        for r in b.loads.itertuples(index=False):
            rows.append(dict(patron=1, origen="LT2", tipo="beamPoint",
                             element_tag=int(r.element_tag),
                             level=r.level, beam_id=r.beam_id,
                             L_m=float(r.L), xloc=float(r.xloc),
                             q_kN=float(r.load_kN)))
        for r in b.v30_redistribution_rows(Q_G_LT2):
            rows.append(dict(
                patron=1, origen="COMBINADO", tipo="beamUniform_redist_V30",
                element_tag=int(r["element_tag"]), level=r["nivel"],
                beam_id=r["beam_id"], L_m=float(r["longitud_m"]),
                w_kN_m=float(r["delta_w_kN_m"]),
                q_kN=float(r["delta_load_kN"]),
                area_m2=float(r["delta_area_m2"]),
                estado=r["estado"]))
        removed_tags = {rb["tag_original"] for rb in b.removed_beams_loads}
        for beam in b.json_lt1["beams"]:
            t = int(beam["elementTag"])
            if t in removed_tags:
                continue
            w = float(beam.get("carga_lineal_qG_kN_m", 0.0) or 0.0)
            if abs(w) < 1e-12:
                continue
            l = _ops_len(t)
            rows.append(dict(patron=2, origen="LT1", tipo="beamUniform",
                             element_tag=t, nivel=beam.get("nivel"),
                             w_kN_m=float(beam["carga_lineal_qG_kN_m"]),
                             L_m=round(l, 9), q_kN=round(w * l, 9)))
        for rb in b.removed_beams_loads:
            if abs(rb["qG_kN_m"]) < 1e-12:
                continue
            for seg in rb["segments"]:
                rows.append(dict(patron=2, origen="LT1",
                                 tipo="beamUniform_segmento",
                                 element_tag=int(seg["tag"]),
                                 tag_original=int(rb["tag_original"]),
                                 nivel=rb["nivel"],
                                 w_kN_m=float(rb["qG_kN_m"]),
                                 L_m=round(float(seg["L"]), 9),
                                 q_kN=round(float(rb["qG_kN_m"]) *
                                            float(seg["L"]), 9)))
        return rows

    def _loads_q(self, b):
        lt2 = build_q_lt2(b)
        lt1 = build_q_lt1(b)
        rows = []
        for r in lt2.itertuples(index=False):
            rows.append(dict(
                patron=3,
                origen=("COMBINADO" if r.load_type == "beamUniform"
                        else "LT2"),
                tipo=("beamUniform_redist_V30" if
                      r.load_type == "beamUniform" else "beamPoint"),
                element_tag=int(r.element_tag), level=r.level,
                beam_id=r.beam_id, L_m=float(r.L_m), xloc=float(r.xloc),
                w_kN_m=float(r.w_kN_m), q_kN=float(r.q_kN),
                area_m2=float(r.area_m2)))
        for r in lt1.itertuples(index=False):
            rows.append(dict(
                patron=4, origen="LT1",
                tipo=("beamUniform_segmento" if r.tipo == "segmento_fachada"
                      else "beamUniform"),
                element_tag=int(r.element_tag),
                tag_original=int(r.tag_original),
                nivel=r.nivel, w_kN_m=float(r.w_kN_m),
                L_m=float(r.L_m), q_kN=float(r.q_kN),
                area_m2=float(r.area_m2)))
        return rows

    def _lateral_forces(self):
        forces, f_total = forces_per_floor(build_weight_table())
        return forces, float(f_total)

    # ---- resultados -------------------------------------------------------
    def _forces_dict(self, ele_tags):
        out = {}
        for t in ele_tags:
            v = [float(x) for x in ops.eleResponse(int(t), "localForce")]
            if len(v) != 12:
                raise RuntimeError(f"EXPORT: localForce de {t} len={len(v)}.")
            out[int(t)] = dict(N1=v[0], Vy1=v[1], Vz1=v[2], T1=v[3],
                               My1=v[4], Mz1=v[5], N2=v[6], Vy2=v[7],
                               Vz2=v[8], T2=v[9], My2=v[10], Mz2=v[11])
        return out

    def _disps_dict(self, node_tags):
        return {int(t): [float(x) for x in ops.nodeDisp(int(t))]
                for t in node_tags}

    def _reactions_and_equilibrium(self, b, constrained, cfg):
        ops.reactions()
        sums = [0.0] * 6
        reac = {}
        for t in constrained:
            vals = [float(ops.nodeReaction(int(t), i)) for i in range(1, 7)]
            reac[int(t)] = vals
            for k in range(6):
                sums[k] += vals[k]
        vert = sums[2]
        lat = abs(sums[0]) if cfg["lat_axis"] == "Rx" else abs(sums[1])
        vert_ref = cfg["vert_ref"]
        lat_ref = cfg["lat_ref"]
        p_total = cfg["p_total"]

        def _rel(calc, ref):
            denom = max(abs(ref), abs(p_total), 1e-12)
            return abs(calc - ref) / denom

        return dict(
            rc=b.rc,
            P_aplicada_kN=p_total,
            sum_Rx_kN=sums[0], sum_Ry_kN=sums[1], sum_Rz_kN=sums[2],
            vert_ref_kN=vert_ref,
            lat_axis=cfg["lat_axis"], lat_ref_kN=lat_ref,
            corte_basal_kN=lat,
            err_abs_vertical_kN=abs(vert - vert_ref),
            err_rel_vertical=_rel(vert, vert_ref),
            err_abs_lateral_kN=abs(lat - lat_ref),
            err_rel_lateral=_rel(lat, lat_ref)), reac

    def _run_case(self, case, ele_tags, node_tags, cfg):
        b = self._fresh_builder()
        if case == "G":
            b.apply_loads()
            cfg["p_total"] = b.P_total
            cfg["vert_ref"] = b.P_total
            cfg["lat_ref"] = 0.0
        elif case == "Q":
            apply_q_patterns(build_q_lt2(b), build_q_lt1(b))
            cfg["p_total"] = float(self.loads_q_p)
            cfg["vert_ref"] = float(self.loads_q_p)
            cfg["lat_ref"] = 0.0
        elif case == "EX":
            forces, f_t = self._lateral_forces()
            apply_lateral(b, forces, "EX")
            cfg["p_total"] = f_t
            cfg["vert_ref"] = 0.0
            cfg["lat_ref"] = f_t
        elif case == "EY":
            forces, f_t = self._lateral_forces()
            apply_lateral(b, forces, "EY")
            cfg["p_total"] = f_t
            cfg["vert_ref"] = 0.0
            cfg["lat_ref"] = f_t
        elif case == "COMBO_R":
            b.apply_loads()
            apply_q_patterns(build_q_lt2(b), build_q_lt1(b))
            forces, f_t = self._lateral_forces()
            apply_lateral(b, forces, "EX")
            cfg["p_total"] = b.P_total + float(self.loads_q_p)
            cfg["vert_ref"] = b.P_total + float(self.loads_q_p)
            cfg["lat_ref"] = f_t
        else:
            raise RuntimeError(f"case desconocido {case}")
        rc = b.run_analysis()
        if rc != 0:
            raise RuntimeError(
                f"EXPORT: caso {case} no converge (rc={rc}). INPUT_REQUIRED.")
        equilibrio, reacciones = self._reactions_and_equilibrium(
            b, sorted(b.support_tags), cfg)
        return dict(
            fuerzas=self._forces_dict(ele_tags),
            desplazamientos=self._disps_dict(node_tags),
            reacciones=reacciones,
            equilibrio=equilibrio)

    # ---- areas tributarias ------------------------------------------------
    def _tributary_lt2(self):
        import pandas as pd
        trib = pd.read_csv(TRIB_LT2)
        rows = []
        for r in trib.itertuples(index=False):
            ngon = 0
            if isinstance(r.polygon, str) and r.polygon.strip():
                ngon = len(_parse_poly(r.polygon))
            elem = None
            if r.receiver_type == "BEAM":
                try:
                    elem = int(float(r.element_tag))
                except Exception:
                    elem = None
            rows.append(dict(
                tributary_id=str(r.tributary_id), level=str(r.level),
                panel_id=str(r.panel_id),
                receiver_type=str(r.receiver_type),
                receiver_id=str(r.receiver_id),
                beam_id=(str(r.beam_id) if isinstance(r.beam_id, str)
                         else None),
                element_tag=elem, area_m2=float(r.area_m2),
                qG_kN_m2=float(r.qG_kN_m2), load_kN=float(r.load_kN),
                polygon=(str(r.polygon) if isinstance(r.polygon, str)
                         and r.polygon.strip() else None),
                status=str(r.status), n_puntos_poligono=ngon))
        # Filas de correccion firmadas: al agregarlas por elementTag, Unity
        # muestra el area final de V40 y las nuevas V30. No se inventa un
        # poligono: la geometria se presenta como franja equivalente.
        redist = pd.read_csv(
            ROOT / "COMBINADO" / "data" /
            "redistribucion_tributaria_v30_lt2.csv")
        for i, r in enumerate(redist.itertuples(index=False), start=1):
            rows.append(dict(
                tributary_id=f"V30_REDIST_{i:03d}", level=str(r.nivel),
                panel_id="AUDITORIA_V30", receiver_type="BEAM",
                receiver_id=str(r.beam_id), beam_id=str(r.beam_id),
                element_tag=int(r.element_tag),
                area_m2=float(r.delta_area_m2),
                qG_kN_m2=float(r.qG_kN_m2),
                load_kN=float(r.delta_area_m2) * float(r.qG_kN_m2),
                polygon=None, status=str(r.estado),
                n_puntos_poligono=0))
        return rows

    def _tributary_lt1(self):
        with open(JSON_LT1, "r", encoding="utf-8") as f:
            d = json.load(f)
        rows = []
        for t in d.get("tributary_areas", []):
            qg = t.get("q_G_kPa")
            rows.append(dict(
                element_tag=int(t["elementTag"]), nivel=t.get("nivel"),
                A_tributaria_m2=float(t.get("A_tributaria_m2", 0.0) or 0.0),
                P_losa_kN=float(t.get("P_losa_kN", 0.0) or 0.0),
                w_kN_m=float(t.get("w_kN_m", 0.0) or 0.0),
                q_G_kPa=(float(qg[0]) if isinstance(qg, list) and qg else None),
                longitud_m=float(t.get("longitud_m", 0.0) or 0.0),
                orientacion=t.get("orientacion"),
                origen=";".join(t.get("origen", []))))
        return rows

    # ---- metadatos -----------------------------------------------------------
    def _metadata(self, b, conteo_el, conteo_orig):
        return dict(
            modelo="COMBINADO_LT1_LT2",
            etapa="P1L4",
            unidades=dict(longitud="m", fuerza="kN", presion="kPa",
                          modulo="kPa"),
            fecha_generacion=datetime.now(timezone.utc).isoformat(),
            generado_por=str(Path(__file__).name),
            origen_fuente=("COMBINADO/src/run_combined.py "
                           "(CombinedBuilder: prepare/check_interface/build/"
                           "apply_loads/run_analysis)"),
            transformacion_lt1=("X'=X+%.3f ; Y'=-Y ; Z'=Z ; tags LT1 no-"
                                "interfaz = tag+%d ; eje I' corregido "
                                "42.5->45.0 m" % (SHIFT_X, NODE_OFFSET_LT1)),
            interfaz_lt1_lt2=dict(total_pares=len(b.interface),
                                  regla="18 pares en B1,L1..L4,ROOF "
                                        "(3 por nivel); tag combinado = tag "
                                        "LT2"),
            niveles=[{"name": n, "z_m": _zname(b.levels, n)}
                     for n in b.levels["name"]],
            conteo_geometria=dict(por_tipo=conteo_el, por_origen=conteo_orig),
            materiales=dict(
                concreto=dict(fc_MPa=35.0, E_MPa=27800.0,
                              G_MPa=11583.33333, nu=0.2,
                              densidad_kg_m3=2400.0,
                              fuente="USUARIO_CONFIRMADO (E=27800 MPa, "
                                     "rho=2400 kg/m3, fc=35 MPa)"),
                acero=dict(fy_MPa=420.0, E_MPa=200000.0,
                           densidad_kg_m3=7850.0,
                           fuente="USUARIO_CONFIRMADO (fy=420 MPa)"),
                conector_v40_muro=dict(E_kPa=2_780_000_000.0,
                                       G_kPa=2_780_000_000.0 / 2.4,
                                       A_m2=1.0, Iy_m4=0.1, Iz_m4=0.1,
                                       J_m4=0.2,
                                       nota="elemento de ENLACE (solo "
                                            "COMBINADO), seccion 100xE_LT2")),
            casos=dict(
                G=dict(patrones=[1, 2],
                       descripcion="gravedad (qG por viga LT2 + LT1)",
                       qG_LT2_losa_kPa=Q_G_LT2),
                Q=dict(patrones=[3, 4], descripcion="carga viva",
                       q_Q_kPa=4.0),
                EX=dict(patrones=[5], descripcion="sismo +X en masters "
                       "1001..1005"),
                EY=dict(patrones=[6], descripcion="sismo +Y en masters "
                       "1001..1005"),
                COMBO_R=dict(patrones=[1, 2, 3, 4, 5],
                             coef=dict(G=1.0, Q=1.0, EX=1.0, EY=0.0),
                             descripcion="R = 1.0G + 1.0Q + 1.0EX + "
                                         "0.0EY")),
            convencion_ejes_locales=CONVENCION_EJES,
            convencion_fuerzas_locales=CONV_FUERZAS,
            convencion_seccion_opensees=CONV_SECCION,
            notas_modelo=[
                "ROOF LT2: forjado sin espesor verificado visualmente -> "
                "sin qG (PENDING_VISUAL_CONFIRMATION); no hay cargas "
                "aplicadas en ROOF.",
                "LT2 L1..L4 y ROOF: diafragma rigido en Ux,Uy,Rz con master "
                "1001..1005 (no en B1).",
                "B1: apoyos LT2+LT1+cajas fijos 6 GDL (empotrados).",
                "Conectores V40<->muro (10) y verticales de cajas/pilastra "
                "(50) son SOLO del modelo COMBINADO; no existen en LT1/LT2 "
                "aislados.",
            ])

    # ---- main ---------------------------------------------------------------
    def run(self):
        b0 = self._fresh_builder()
        self.z2lv = _z_to_level(b0.levels)
        self._index_nodes(b0)
        node_tags = sorted(int(t) for t in ops.getNodeTags())
        elements = self._elements(b0)
        nodes_p0 = [dict(nodeTag=int(t), x=self.coords[t][0],
                         y=self.coords[t][1], z=self.coords[t][2],
                         origen=self.node_origin[t],
                         nivel=self.nivel_of_node[t]) for t in node_tags]

        loads_g = self._loads_g(b0)
        loads_q = self._loads_q(b0)
        self.loads_q_p = sum(float(r["q_kN"]) for r in loads_q)
        forces_ex, f_ex = self._lateral_forces()
        self.p_f_ex = f_ex

        ele_tags = [e["elementTag"] for e in elements]

        results = {}
        cfgs = {
            "G": dict(lat_axis="Rx"),
            "Q": dict(lat_axis="Rx"),
            "EX": dict(lat_axis="Rx"),
            "EY": dict(lat_axis="Ry"),
            "COMBO_R": dict(lat_axis="Rx"),
        }
        for case in CASOS:
            print(f"[EXPORT] caso {case} ...", flush=True)
            results[case] = self._run_case(case, ele_tags, node_tags,
                                           cfgs[case])

        conteo_el, conteo_orig = {}, {}
        for e in elements:
            conteo_el[e["tipo"]] = conteo_el.get(e["tipo"], 0) + 1
            conteo_orig[e["origen"]] = conteo_orig.get(e["origen"], 0) + 1

        payload = dict(
            metadata=self._metadata(b0, conteo_el, conteo_orig),
            nodes=nodes_p0,
            elements=elements,
            supports=self._supports(b0),
            masters=self._masters(b0),
            diaphragms=self._diaphragms(b0),
            constraint_links=self._constraint_links(b0),
            loads=dict(
                G=loads_g,
                Q=loads_q,
                EX=[dict(patron_tag=5, piso=r["piso"],
                         node_tag=int(r["master_tag"]),
                         W_sismico_kN=float(r["W_sismico_kN"]),
                         fx_kN=float(r["F_i_kN"]), fy_kN=0.0)
                    for r in forces_ex.to_dict("records")],
                EY=[dict(patron_tag=6, piso=r["piso"],
                         node_tag=int(r["master_tag"]),
                         W_sismico_kN=float(r["W_sismico_kN"]),
                         fx_kN=0.0, fy_kN=float(r["F_i_kN"]))
                    for r in forces_ex.to_dict("records")],
                COMBO_R=dict(
                    descripcion="patrones 1,2,3,4,5 = G + Q + EX "
                                "(coef EY=0.0)",
                    coef=dict(G=1.0, Q=1.0, EX=1.0, EY=0.0))),
            tributary_areas=dict(
                LT2=dict(fuente=str(TRIB_LT2.relative_to(ROOT)),
                         filas=self._tributary_lt2()),
                LT1=dict(fuente="outputs/unity/modelo_lt1.json -> "
                                "tributary_areas",
                         filas=self._tributary_lt1())),
            results=dict(
                cases=CASOS,
                forces={c: results[c]["fuerzas"] for c in CASOS},
                displacements={c: results[c]["desplazamientos"]
                               for c in CASOS},
                reactions={c: results[c]["reacciones"] for c in CASOS},
                equilibrio={c: results[c]["equilibrio"] for c in CASOS}))

        OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUT.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        tmp.replace(OUT)
        print(f"[EXPORT] escrito {OUT} ({OUT.stat().st_size} bytes)")
        return payload


def main():
    exp = ExportadorCombinado()
    payload = exp.run()
    print("\n[EXPORT] equilibrio por caso:")
    for c, v in payload["results"]["equilibrio"].items():
        print(f"  {c:7s} rc={v['rc']} P={v['P_aplicada_kN']:.6f} "
              f"vert_err_rel={v['err_rel_vertical']:.3e} "
              f"lat({v['lat_axis']})_err_rel={v['err_rel_lateral']:.3e}")


if __name__ == "__main__":
    main()
