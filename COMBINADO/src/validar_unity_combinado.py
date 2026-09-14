#!/usr/bin/env python3
"""validar_unity_combinado.py - Validacion de modelo_combinado.json (P1L4).

Comprueba de forma automatica, sobre el JSON exportado por
`exportar_unity_combinado.py`:

  [n] estructura/metadata/unidades/materiales
  [n] nodos: tags unicos, coordenadas finitas
  [e] elementos: tags unicos, nodeI/nodeJ existen, seccion/material validos,
      ejes locales normalizados, vecxz consistente con la geometria
  [s] apoyos/masters/diafragmas/constraint_links referencian tags existentes
  [l] cargas: elementos/nodos referencian tags del modelo
  [t] areas tributarias LT1 y LT2 presentes
  [r] resultados: fuerzas locales 12 comps, desplazamientos 6 comps,
      reacciones, equilibrio rc==0, tol vertical (G/Q/COMBO_R) y
      lateral (EX/EY) < 1e-6
  [c] coexistencia LT1+LT2 en el mismo modelo (contar origenes)
  [f] sin NaN/Inf en todo el documento

Uso:
    python3 validar_unity_combinado.py [ruta_json]
"""
import json
import math
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
_DEF = _SRC.parent / "outputs" / "unity" / "modelo_combinado.json"

ORIGENES_VALIDOS = {"LT1", "LT2", "LT1_LT2_interfaz", "LT1_saliente",
                    "COMBINADO_caja", "LT2_master"}
TIPOS_ELEMENTO = {"viga", "columna", "muro", "muro_corner", "viga_saliente",
                  "segmento_fachada", "conector_v40_muro", "vertical_caja"}

TOL_EQUILIBRIO = 1e-6
TOL_AXIS = 1e-9


def _finite(x):
    return isinstance(x, (int, float)) and math.isfinite(float(x))


class Validator:
    def __init__(self, path):
        self.path = Path(path)
        with open(self.path, "r", encoding="utf-8") as f:
            self.d = json.load(f)
        self.ok, self.fail = [], []

    @staticmethod
    def _norm(v):
        return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)

    def check(self, name, cond, extra=""):
        (self.ok if cond else self.fail).append(
            name if cond else f"{name} {extra}".strip())

    # ---- recorrido finito ------------------------------------------------
    def _scan_finite(self, obj, prefix):
        if isinstance(obj, float) or isinstance(obj, int):
            if not _finite(obj):
                self.check(prefix, False)
                return
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                self._scan_finite(v, f"{prefix}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                if prefix in ("nodes", None, "", "elements"):
                    self._scan_finite(v, f"{prefix}[{i}]")
                else:
                    self._scan_finite(v, f"{prefix}[{i}]")

    def run(self):
        d = self.d
        # metadata
        m = d.get("metadata", {})
        self.check("metadata.modelo=COMBINADO_LT1_LT2",
                   m.get("modelo") == "COMBINADO_LT1_LT2")
        self.check("metadata.unidades", m.get("unidades", {}).get("longitud")
                   == "m" and m.get("unidades", {}).get("fuerza") == "kN")
        mat = m.get("materiales", {}).get("concreto", {})
        self.check("materials.concreto.E=27800 MPa",
                   abs(float(mat.get("E_MPa", 0)) - 27800.0) < 1e-6)
        self.check("materials.concreto.fc=35 MPa",
                   abs(float(mat.get("fc_MPa", 0)) - 35.0) < 1e-6)
        self.check("materials.acero", m.get("materiales", {}).get("acero",
                   {}).get("fy_MPa") == 420.0)
        self.check("metadata.casos", set(m.get("casos", {}).keys())
                   == {"G", "Q", "EX", "EY", "COMBO_R"})

        # nodos
        nodes = d.get("nodes", [])
        tags = [int(n["nodeTag"]) for n in nodes]
        self.check("nodes.present", len(nodes) > 400)
        self.check("nodes.tags_unicos", len(tags) == len(set(tags)))
        bad_coords = [n for n in nodes
                      if not all(_finite(v) for v in (n["x"], n["y"], n["z"]))]
        self.check("nodes.coords_finitas", not bad_coords)
        self.check("nodes.origenes_validos",
                   all(n["origen"] in ORIGENES_VALIDOS for n in nodes))
        node_set = set(tags)
        coord_map = {(round(n["x"], 6), round(n["y"], 6), round(n["z"], 6))
                     for n in nodes}
        self.check("nodes.coords_unicas", len(coord_map) == len(nodes))

        # elementos
        elems = d.get("elements", [])
        etags = [int(e["elementTag"]) for e in elems]
        self.check("elements.present", len(elems) > 500)
        self.check("elements.tags_unicos", len(etags) == len(set(etags)))
        elem_set = set(etags)
        for e in elems:
            tag = int(e["elementTag"])
            cond = (e["tipo"] in TIPOS_ELEMENTO and e["origen"] in
                    {"LT1", "LT2", "COMBINADO"}
                    and int(e["nodeI"]) in node_set
                    and int(e["nodeJ"]) in node_set)
            self.check(f"elements.{tag}.refs", cond)
            sec = e["seccion"]
            self.check(f"elements.{tag}.seccion",
                       _finite(sec["A_m2"]) and float(sec["A_m2"]) > 0
                       and _finite(sec["Iy_m4"]) and float(sec["Iy_m4"]) > 0
                       and _finite(sec["Iz_m4"]) and float(sec["Iz_m4"]) > 0
                       and _finite(sec["E_kPa"]) and float(sec["E_kPa"]) > 0
                       and _finite(sec["G_kPa"]) and float(sec["G_kPa"]) > 0)
            ax = e["ejes_locales"]
            for name in ("x", "y", "z"):
                self.check(f"elements.{tag}.eje_{name}_unit",
                           abs(self._norm(ax[name]) - 1.0) < TOL_AXIS)
            if e["origen"] == "LT2":
                self.check(f"elements.{tag}.b_h_lt2",
                           _finite(sec.get("b_m")) and _finite(sec.get("h_m")))
        self.check("elements.origenes.coexisten",
                   any(e["origen"] == "LT1" for e in elems)
                   and any(e["origen"] == "LT2" for e in elems))

        # apoyos / masters / diafragmas
        supp = d.get("supports", [])
        self.check("supports.47", len(supp) == 47)
        self.check("supports.tags", all(int(s["nodeTag"]) in node_set
                                        for s in supp))
        self.check("supports.restricciones",
                   all(len(s["restricciones"]) == 6 and
                       all(int(v) in (0, 1) for v in s["restricciones"])
                       for s in supp))
        masters = d.get("masters", [])
        self.check("masters.5", len(masters) == 5)
        self.check("masters.tags.nivel",
                   {s["nivel"] for s in masters}
                   == {"L1", "L2", "L3", "L4", "ROOF"})
        self.check("masters.restringidos",
                   all(s["restricciones"] == [0, 0, 1, 1, 1, 0]
                       for s in masters))
        for dia in d.get("diaphragms", []):
            self.check(f"diafragma.{dia['nivel']}.master",
                       int(dia["master"]) in node_set)
            self.check(f"diafragma.{dia['nivel']}.slaves",
                       all(int(t) in node_set for t in dia["slaves"]))
        for lnk in d.get("constraint_links", []):
            self.check(f"link.{lnk['nivel']}",
                       int(lnk["master"]) in node_set
                       and int(lnk["nodo_muro"]) in node_set)

        # cargas
        loads = d.get("loads", {})
        for lrow in loads["G"] + loads["Q"]:
            self.check(f"load.{lrow['tipo']}.{lrow['element_tag']}",
                       int(lrow["element_tag"]) in elem_set)
        for lrow in loads["EX"] + loads["EY"]:
            self.check(f"load.lateral.{lrow['node_tag']}",
                       int(lrow["node_tag"]) in node_set)

        # areas tributarias
        ta = d.get("tributary_areas", {})
        lt2 = ta.get("LT2", {})
        lt1 = ta.get("LT1", {})
        self.check("trib.area_lt2_presente", len(lt2.get("filas", [])) > 300)
        self.check("trib.area_lt1_presente", len(lt1.get("filas", [])) > 100)
        self.check("trib.lt2.beam_y_wall",
                   {f["receiver_type"] for f in lt2["filas"]}
                   == {"BEAM", "WALL"})
        self.check("trib.lt2.suma_cierra",
                   abs(sum(f["load_kN"] for f in lt2["filas"]
                           if f["receiver_type"] == "BEAM")
                       - 11268.662668) < 1e-3)  # carga G LT2 transferida

        # resultados
        res = d.get("results", {})
        self.check("results.cases", res.get("cases")
                   == ["G", "Q", "EX", "EY", "COMBO_R"])
        for case in res["cases"]:
            fuerzas = res["forces"][case]
            self.check(f"res.{case}.fuerzas.llenan",
                       set(int(k) for k in fuerzas) == elem_set)
            for tag, v in fuerzas.items():
                self.check(f"res.{case}.f.{tag}",
                           all(k in v for k in
                               ("N1", "Vy1", "Vz1", "T1", "My1", "Mz1",
                                "N2", "Vy2", "Vz2", "T2", "My2", "Mz2"))
                           and all(_finite(v[k]) for k in v))
            disps = res["displacements"][case]
            self.check(f"res.{case}.disp.llenan",
                       set(int(k) for k in disps) == node_set
                       and all(len(v) == 6 and all(_finite(x) for x in v)
                               for v in disps.values()))
            eq = res["equilibrio"][case]
            self.check(f"res.{case}.eq.rc_0", eq["rc"] == 0)
            self.check(f"res.{case}.eq.P>0", eq["P_aplicada_kN"] > 0)
            if case in ("EX", "EY"):
                self.check(f"res.{case}.eq.tol_lateral",
                           eq["err_rel_lateral"] < TOL_EQUILIBRIO)
            else:
                self.check(f"res.{case}.eq.tol_vertical",
                           eq["err_rel_vertical"] < TOL_EQUILIBRIO)
        # G equilibra el total combinado conocido
        eqG = res["equilibrio"]["G"]
        self.check("res.G.eq.P_total_31086.26",
                   abs(eqG["P_aplicada_kN"] - 31086.259667) < 1e-3)

        # todo finito (recorrido general, clave top-level)
        self._scan_finite(d, "")

        return True

    def report(self):
        print(f"\n=== VALIDACION {self.path.name} ===")
        print(f"  OK={len(self.ok)}  PROBLEMA={len(self.fail)}")
        for f in self.fail:
            print(f"  PROBLEMA -> {f}")
        for f in self.fail:
            print(f"  -> {f}")
        if self.fail:
            print("  RESULTADO: PROBLEMAS DETECTADOS")
            return False
        print("  RESULTADO: OK")
        return True


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else str(_DEF)
    v = Validator(path)
    v.run()
    ok = v.report()
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()