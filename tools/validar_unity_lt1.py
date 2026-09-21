#!/usr/bin/env python3
"""Validación estática del JSON del viewer Unity + escritura de
outputs/control_unity_lt1.txt (no toca OpenSees ni el modelo)."""
import json
import math
import sys
import io

RUTA_JSON = "outputs/unity/modelo_lt1.json"
RUTA_CONTROL = "outputs/control_unity_lt1.txt"


def main():
    buf = io.StringIO()
    w = buf.write
    w("=" * 78 + "\n")
    w("CONTROL ETAPA UNITY LT1 - VALIDACION ESTATICA DEL JSON\n")
    w("=" * 78 + "\n")

    with open(RUTA_JSON, encoding="utf-8") as f:
        d = json.load(f)
    w(f"JSON : {RUTA_JSON} (parseado OK)\n")

    ok = True
    checks = []

    def chk(name, cond, detalle=""):
        nonlocal ok
        check_ok = bool(cond)
        if not check_ok:
            ok = False
        checks.append((name, check_ok, detalle))

    n_est = sum(1 for n in d["nodes"] if n.get("tipo") == "structural")
    n_mas = sum(1 for n in d["nodes"] if n.get("tipo") == "master")
    chk("148 nodos totales", len(d["nodes"]) == 148,
        f"total={len(d['nodes'])} (estructural={n_est}, master={n_mas})")
    chk("144 estructurales / 4 masters",
        n_est == 144 and n_mas == 4,
        f"estructurales={n_est}, masters={n_mas}")

    n_vig = len(d["beams"])
    n_col = len(d["columns"])
    n_mur = len(d["walls"])
    n_rl = len(d["constraint_links"])
    n_apo = len(d["supports"])
    n_dia = len(d["diaphragms"])
    chk("108 vigas", n_vig == 108, str(n_vig))
    chk("90 columnas", n_col == 90, str(n_col))
    chk("30 muros equivalentes", n_mur == 30, str(n_mur))
    chk("24 rigidLink (constraint)", n_rl == 24, str(n_rl))
    chk("24 apoyos", n_apo == 24, str(n_apo))
    chk("4 diafragmas", n_dia == 4, str(n_dia))

    # elementos estructurales = beams + columns + walls (elasticBeamColumn)
    n_ele = n_vig + n_col + n_mur
    chk("228 elasticBeamColumn", n_ele == 228,
        f"beams+columns+walls = {n_vig}+{n_col}+{n_mur}={n_ele}")
    chk("rigidLink NO en elasticBeamColumn",
        ("constraint_links" in d and
         not any(k == "elasticBeamColumn" for k in
                 (d["constraint_links"][0].keys() if d["constraint_links"] else []))),
        "constraint_links es array independiente, sin campo elasticBeamColumn")

    # tags únicos
    def tags_unicos(nombre, arr):
        tags = []
        for it in arr:
            for k in ("elementTag", "nodeTag", "tag"):
                if k in it:
                    tags.append(it[k])
                    break
        return len(tags) == len(set(tags)), len(tags), len(set(tags))

    for nm, arr in (("nodes", d["nodes"]), ("beams", d["beams"]),
                    ("columns", d["columns"]), ("walls", d["walls"]),
                    ("supports", d["supports"])):
        u, t, s = tags_unicos(nm, arr)
        chk(f"tags unicos en {nm}", u, f"{t} tags / {s} unicos")

    # cruce de tags entre beams/columns/walls (elementTags no duplicados)
    ets = [it["elementTag"] for it in d["beams"] + d["columns"] + d["walls"]]
    chk("elementTags unicos globales",
        len(ets) == len(set(ets)), f"{len(ets)} / {len(set(ets))}")

    # coordenadas finitas
    coords_finitas = all(
        math.isfinite(float(c)) for n in d["nodes"]
        for c in (n["x"], n["y"], n["z"]))
    chk("coordenadas finitas (148 nodos)", coords_finitas)

    # pending_geometry presente
    pend = d.get("pending_geometry")
    chk("pending_geometry presente",
        isinstance(pend, list) and len(pend) >= 7, f"{len(pend) if pend else 0} items")
    ids = [p["id"] for p in (pend or [])]
    for req in ("muros_perimetrales_subterraneo_plan101", "V.30/45",
                "V.60/VAR", "V.60-30/80-40", "P.M.", "V.M.",
                "carga_salientes"):
        chk(f"pendiente listado: {req}", req in ids)

    # análisis
    a = d.get("analysis", {})
    chk("analisis OK_COMPLETADO", a.get("estado") == "OK_COMPLETADO",
        str(a.get("estado")))
    chk("P_gravedad ~ 19644.142 kN",
        abs(a.get("P_aplicada_kN", 0) - 19644.142) < 0.01,
        f"P={a.get('P_aplicada_kN')}")
    chk("SumaRz ~ 19644.142 kN",
        abs(a.get("suma_Rz_kN", 0) - 19644.142) < 0.01,
        f"SumaRz={a.get('suma_Rz_kN')}")
    chk("error relativo <= 1e-12",
        abs(a.get("err_rel", 1)) <= 1e-12,
        f"err_rel={a.get('err_rel')}")
    chk("max_desplazamiento finito",
        isinstance(a.get("max_desplazamiento_m"), (int, float)) and
        math.isfinite(a["max_desplazamiento_m"]),
        f"maxU={a.get('max_desplazamiento_m')}")
    chk("reacciones 24 / desplazamientos 148",
        len(a.get("reacciones", {})) == 24 and
        len(a.get("desplazamientos", {})) == 148,
        f"reac={len(a.get('reacciones',{}))}, desp={len(a.get('desplazamientos',{}))}")

    # estado del modelo
    m = d.get("metadata", {})
    chk("estado MODELO_ANALIZABLE...",
        m.get("estado_modelo") == "MODELO_ANALIZABLE_CON_GEOMETRIA_RESPALDADA_ACTUAL",
        str(m.get("estado_modelo")))

    w("\n")
    w(f"RESULTADO: {'PASA TODAS LAS VERIFICACIONES ESTATICAS' if ok else 'CON FALLOS'}\n")
    w("\n")
    n_ok = sum(1 for _, c, _ in checks if c)
    w(f"  verificaciones: {n_ok}/{len(checks)} OK\n")
    for name, c, det in checks:
        w(f"  [{'OK ' if c else 'FAIL'}] {name}" + (f"  ({det})" if det else "") + "\n")
    w("=" * 78 + "\n")
    w("NOTA: esta validacion NO ejecuta Unity. Unity valida compilacion y escena\n")
    w("por separado (batchmode) o manualmente por el usuario.\n")

    with open(RUTA_CONTROL, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(buf.getvalue())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
