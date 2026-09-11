# ============================================================================
# data/q_zonal_lt1.py
# Derivación de la sobrecarga de USO (Q) zonal LT1 aplicada a las vigas.
# SOLO PREPARACIÓN DE DATOS — NO toca las Partes A/B de Semana 3.
#
# Método (idéntico al de G, sin recalcular geometría):
#   - Los 40 paños LT1 toman su SC_kPa del plan 700 (data/sc_zonas_lt1.py).
#   - Cada borde de paño reparte su área a la viga que lo bordea mediante el
#     mismo algoritmo de bisectrices de data/tributacion.py (el mismo que
#     generó `area_tributaria_m2` de modelo_lt1.json; verificado 1:1 en las
#     108 vigas).
#   - Q_zon de una viga = Σ SC_kPa(paño) × área_tributaria(borde).
#   - Conservación: Σ Q_viga == Σ SC_kPa × área_paño  (por nivel, exacta).
#   - Cargas LINEALES de SC (PISO_4 bahía I-I') NO se asignan a viga: quedan
#     pendientes (INPUT_REQUIRED) y se reportan aparte.
#
# Salidas: outputs/zonificacion_q/{sc_por_pano_lt1.csv,
#           q_zon_por_viga_lt1.csv, resumen_zonificacion_q.md}
# ============================================================================

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sc_zonas_lt1 import PANOS_SC, SC_KPA_POR_PANO, LINEALES_SC
from tributacion import tributacion_nivel


def _a_paños(json_panos):
    """Paños del JSON enriquecidos con SC_kPa del plan 700 (sin tocar q_G)."""
    por_pano = {p["pano_id"]: p for p in PANOS_SC}
    out = []
    for p in json_panos:
        pid = p["id"]
        sc = SC_KPA_POR_PANO[p["nivel"]].get(pid) if p["nivel"] in SC_KPA_POR_PANO else None
        out.append({
            "id": pid,
            "pano_id": pid,
            "bay_x": por_pano[pid]["bay_x"] if pid in por_pano else None,
            "row_y": por_pano[pid]["row_y"] if pid in por_pano else None,
            "nivel": p["nivel"],
            "eje_x0": p["eje_x0"], "eje_x1": p["eje_x1"],
            "eje_y0": p["eje_y0"], "eje_y1": p["eje_y1"],
            "Lx": p["Lx"], "Ly": p["Ly"],
            "area_m2": p["area_m2"],
            "q_G_kPa": p["q_G_kPa"],
            "SC_kPa": sc,
            "SC_kgf_m2": por_pano[pid]["SC_kgf_m2"] if pid in por_pano else None,
            "fuente": por_pano[pid]["fuente"] if pid in por_pano else "",
            "estado": por_pano[pid]["estado"] if pid in por_pano else "",
        })
    return out


def derivar_q_zon(json_path):
    """Deriva Q zonal LT1 por viga y retorna el detalle estructurado."""
    with open(json_path, encoding="utf-8") as fh:
        d = json.load(fh)

    nodos = {n["tag"]: (n["x"], n["y"], n["z"]) for n in d["nodes"]}
    vigas_por_nivel = {}
    for b in d["beams"]:
        vigas_por_nivel.setdefault(b["nivel"], []).append({
            "element_tag": b["elementTag"],
            "nivel": b["nivel"],
            "eje_x_i": b["eje_x_i"], "eje_x_j": b["eje_x_j"],
            "eje_y_i": b["eje_y_i"], "eje_y_j": b["eje_y_j"],
            "nodo_i": b["node_i"], "nodo_j": b["node_j"],
            "clave": None,
        })

    paños = _a_paños(d["panos"])
    paños_trib = [dict(p, SC_kPa=(p["SC_kPa"] if p["SC_kPa"] is not None else 0.0))
                  for p in paños]
    paños_por_nivel = {nv: [] for nv in {"PISO_1", "PISO_2", "PISO_3", "PISO_4"}}
    for p in paños_trib:
        paños_por_nivel[p["nivel"]].append(p)
    orden_niveles = ["PISO_1", "PISO_2", "PISO_3", "PISO_4"]

    niveles = {}
    beams = []
    for nv in orden_niveles:
        res = tributacion_nivel(nv, vigas_por_nivel[nv], nodos, paños_por_nivel[nv])
        vigas = []
        por_tag = {}
        for tag, c in res["vigas_carga"].items():
            L = c["longitud_m"]
            wq = (c["SC_peso_trib_kN"] / L) if L else 0.0
            vigas.append({
                "elementTag": tag,
                "nivel": nv,
                "orientacion": c["orientacion"],
                "eje_x_i": c["eje_x_i"], "eje_x_j": c["eje_x_j"],
                "eje_y_i": c["eje_y_i"], "eje_y_j": c["eje_y_j"],
                "longitud_m": L,
                "A_tributaria_m2": c["A_trib"],
                "SC_peso_trib_kN": c["SC_peso_trib_kN"],
                "w_Q_zon_kN_m": wq,
                "origen": ";".join(c["origen"]),
                "n_fuentes": len(c["origen"]),
            })
            por_tag[tag] = vigas[-1]

        area_sc = sum(p["area_m2"] for p in paños_por_nivel[nv] if p["SC_kPa"] is not None)
        q_panos = sum(p["SC_kPa"] * p["area_m2"]
                      for p in paños_por_nivel[nv] if p["SC_kPa"] is not None)
        q_vigas = sum(v["SC_peso_trib_kN"] for v in vigas)
        err = abs(q_panos - q_vigas) / q_panos if q_panos else float("nan")

        niveles[nv] = {
            "A_total_m2": res["A_total_m2"],
            "A_SC_area_m2": area_sc,
            "Q_zon_area_kN": q_panos,
            "Q_zon_vigas_kN": q_vigas,
            "error_relativo": err,
            "n_vigas": len(vigas),
            "vigas_con_Q": sum(1 for v in vigas if v["SC_peso_trib_kN"] > 1e-12),
            "bordes_sin_viga": res["bordes_sin_viga"],
        }
        beams.extend(vigas)

    uniforme_2 = sum((2.0 * p["area_m2"]) for p in paños)
    return {
        "paños": paños,
        "niveles": niveles,
        "beams": beams,
        "lineales": LINEALES_SC,
        "uniforme_ref_2kPa_kN": uniforme_2,
        "Q_zon_total_area_kN": sum(n["Q_zon_area_kN"] for n in niveles.values()),
        "Q_uniforme_total_kN": uniforme_2,
    }


def escribir_csv(pth, columnas, filas):
    with open(pth, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(columnas)
        for f in filas:
            w.writerow([f.get(c) for c in columnas])


def escribir_resumen(outdir, r):
    with open(os.path.join(outdir, "resumen_zonificacion_q.md"),
              "w", encoding="utf-8") as fh:
        fh.write("# Zonificación de SC (Q) LT1 — plan 700\n\n")
        fh.write("- Solo preparación de datos. **No se modifica la Parte A ni la Parte B.**\n")
        fh.write("- Geometría tributaria idéntica a G: bisectrices de `data/tributacion.py`, "
                 "verificada 1:1 contra `area_tributaria_m2` del JSON (108 vigas). "
                 "No se recalcula geometría.\n\n")
        fh.write("| nivel | A_losa (m²) | A con SC área (m²) | Q_zon área (kN) | Q_zon vigas (kN) | "
                 "err rel | vigas | vigas con Q |\n|---|---|---|---|---|---|---|---|\n")
        for nv, m in r["niveles"].items():
            fh.write(f"| {nv} | {m['A_total_m2']:.3f} | {m['A_SC_area_m2']:.3f} | "
                     f"{m['Q_zon_area_kN']:.3f} | {m['Q_zon_vigas_kN']:.3f} | "
                     f"{m['error_relativo']:.2e} | {m['n_vigas']} | {m['vigas_con_Q']} |\n")
        fh.write(f"\n**Q_zon total (área) LT1 = {r['Q_zon_total_area_kN']:.3f} kN**  \n")
        fh.write(f"Referencia uniforme 2.0 kPa (repositorio) = {r['Q_uniforme_total_kN']:.3f} kN\n\n")
        fh.write("## Cargas lineales de SC (NO asignadas a viga)\n\n")
        if r["lineales"]:
            for li in r["lineales"]:
                fh.write(f"- {li['nivel']} — {li['zona']}: **{li['kgf_m']} kgf/m "
                         f"= {li['kN_m']:.4f} kN/m** ({li['estado']}). "
                         f"Viga objetivo y longitud: INPUT_REQUIRED.\n")
        else:
            fh.write("- Ninguna.\n")
        fh.write("\n## Pendientes / INPUT_REQUIRED\n\n")
        fh.write("- N/d.\n")


def main():
    ap = argparse.ArgumentParser(description="Deriva Q zonal LT1 por viga (SC plan 700).")
    ap.add_argument("--json",
                    default=r"..\outputs\unity\modelo_lt1.json",
                    help="Ruta a modelo_lt1.json")
    ap.add_argument("--outdir", default=r"..\outputs\zonificacion_q",
                    help="Directorio de salida")
    args = ap.parse_args()

    json_path = os.path.normpath(os.path.join(os.path.dirname(__file__), args.json))
    outdir = os.path.normpath(os.path.join(os.path.dirname(__file__), args.outdir))
    os.makedirs(outdir, exist_ok=True)

    r = derivar_q_zon(json_path)

    escribir_csv(
        os.path.join(outdir, "sc_por_pano_lt1.csv"),
        ["nivel", "pano_id", "bay_x", "row_y", "eje_x0", "eje_x1",
         "eje_y0", "eje_y1", "Lx", "Ly", "area_m2", "SC_kgf_m2", "SC_kPa",
         "estado", "fuente"],
        r["paños"],
    )
    escribir_csv(
        os.path.join(outdir, "q_zon_por_viga_lt1.csv"),
        ["elementTag", "nivel", "orientacion", "eje_x_i", "eje_x_j",
         "eje_y_i", "eje_y_j", "longitud_m", "A_tributaria_m2",
         "SC_peso_trib_kN", "w_Q_zon_kN_m", "origen", "n_fuentes"],
        r["beams"],
    )
    escribir_resumen(outdir, r)

    print(f"SC por paño      -> {os.path.join(outdir, 'sc_por_pano_lt1.csv')}")
    print(f"Q_zon por viga   -> {os.path.join(outdir, 'q_zon_por_viga_lt1.csv')}")
    print(f"Resumen          -> {os.path.join(outdir, 'resumen_zonificacion_q.md')}")
    print(f"Q_zon total (área) LT1 = {r['Q_zon_total_area_kN']:.3f} kN")
    print(f"Q uniforme ref (2.0 kPa) = {r['Q_uniforme_total_kN']:.3f} kN")


if __name__ == "__main__":
    main()