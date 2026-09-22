# -*- coding: utf-8 -*-
"""SEMANA 3 - PARTE A: caso de carga viva Q sobre el modelo combinado LT1+LT2.

Caso INDEPENDIENTE: aplica SOLO la carga viva q_Q sobre la MISMA geometria
tributaria de la Semana 2 (no se aplica simultaneamente la carga muerta G).

Fuentes reutilizadas (se leen, NO se modifican):
  - LT2: data/loads/tributary_areas_LT2.csv            (areas tributarias)
         results/gravity_loads_applied_LT2.csv         (posiciones xloc)
  - LT1: outputs/unity/modelo_lt1.json                 (area_tributaria_m2)

CRITERIO DE q_Q (CIERRE DEFINITIVO DE PARTE A):
  - NCh1537.Of2009, Tabla 4, edificacion EDUCACIONAL:
      salas de clases : 3.0 kPa ;  pasillos : 4.0 kPa.
  - Los planos estructurales disponibles de LT1 y LT2 no permiten identificar
    ni separar con certeza las salas de clases y los pasillos (no existen
    planos arquitectonicos con la zonificacion de usos).
  - Por ello se adopta para esta entrega q_Q = 4.0 kPa = 4.0 kN/m2 UNIFORME en
    las superficies transitables de LT1 y LT2 (unico valor que la Tabla 4
    asigna a un espacio de circulacion en edificacion educacional).
  - 4.0 kPa es una HIPOTESIS CONSERVADORA DE MODELACION por la ausencia de
    planos arquitectonicos que permitan zonificar los usos. NO se afirma que
    NCh1537 exija 4.0 kPa para TODAS las superficies de un edificio
    educacional.
  - Se REEMPLAZA el q_Q provisional anterior (2.0 kPa). Las SC zonales del
    plano LT1 NO se integran al modelo de Semana 3 (propuesta descartada).

q_Q es una INTENSIDAD DE ENTRADA configurable (constante Q_Q en este modulo o
variable de entorno LT1_Q_Q_KPA); el modelo (geometria tributaria) no cambia.

Verificaciones incluidas (idem Semana 2 pero para Q):
  1) conservacion por nivel y por origen (LT1/LT2) y global:
        sum(Q_transferida) = q_Q * area_tributaria   (PASS/FAIL)
  2) convergencia OpenSees (analyze rc) y equilibrio global (sum Rz = Q_total).

Salidas (SOLO dentro de COMBINADO/):
  outputs/semana03/live_load_Q_applied_LT2.csv
  outputs/semana03/live_load_Q_applied_LT1.csv
  outputs/semana03/conservacion_Q.csv
  outputs/semana03/resumen_semana03.md

El analisis usa los patrones 3 (LT2-Q) y 4 (LT1-Q); los patrones 1/2 quedan
reservados al caso G y NO se tocan.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pandas as pd
import openseespy.opensees as ops

from run_combined import CombinedBuilder, JSON_LT1, LT2_LOADS

ROOT = Path(__file__).resolve().parents[2]
COMB = ROOT / "COMBINADO"
OUT_S3 = COMB / "outputs" / "semana03"

TRIB_LT2 = ROOT / "LT2" / "data" / "loads" / "tributary_areas_LT2.csv"

Q_G_LT2 = 6.0822  # qG de losa (kN/m2) L1-L4, dato de LT2 (se verifica)

# Intensidad de carga viva q_Q (CIERRE DEFINITIVO DE PARTE A):
#   NCh1537.Of2009 Tabla 4 (edificacion educacional): salas de clases
#   3.0 kPa, pasillos 4.0 kPa. Sin planos arquitectonicos para zonificar
#   los usos, se adopta q_Q = 4.0 kPa UNIFORME como HIPOTESIS CONSERVADORA
#   de modelacion sobre las superficies transitables de LT1 y LT2 (NCh1537
#   NO exige 4.0 kPa en todas las superficies de un edificio educacional).
#   Configurable por env (LT1_Q_Q_KPA).
Q_Q = float(os.environ.get("LT1_Q_Q_KPA", "4.0"))

TOL_REL = 1e-6        # tolerancia relativa de conservacion
NI_VEL = {            # LT1 -> nivel combinado
    "PISO_1": "L1", "PISO_2": "L2", "PISO_3": "L3", "PISO_4": "L4"}


def _elem_len(tag):
    """Longitud real del elemento en el modelo (tan cual aplica la carga)."""
    ns = tuple(ops.eleNodes(tag))
    if len(ns) != 2:
        raise RuntimeError(f"Q: elemento {tag} con {len(ns)} nodos.")
    c1, c2 = ops.nodeCoord(ns[0]), ops.nodeCoord(ns[1])
    return math.sqrt(sum((c1[i] - c2[i]) ** 2 for i in range(3)))


def build_q_lt2(builder):
    """beamPoint Q sobre las vigas LT2.

    Reusa las posiciones (xloc) del caso G (distribucion longitudinal
    exactamente identica) y escala la fuerza con la relacion q_Q/qG, de modo
    que cada franja cierra a area_franja * q_Q. La qG se verifica unica en el
    CSV de areas tributarias (fila por fila) y no se hardcodea como fuente.
    """
    trib = pd.read_csv(TRIB_LT2)
    moved = trib[trib.receiver_type == "BEAM"]
    qg = moved["qG_kN_m2"].unique()
    if len(qg) != 1 or abs(float(qg[0]) - Q_G_LT2) > 1e-9:
        raise RuntimeError(
            f"Q: qG de LT2 no es unico/esperado en {TRIB_LT2.name} "
            f"({qg}). INPUT_REQUIRED.")
    qg = float(qg[0])

    applied = pd.read_csv(LT2_LOADS)
    created = set(builder.created["lt2_beams"])
    req = set(int(t) for t in applied["element_tag"].unique())
    missing = req - created
    if missing:
        raise RuntimeError(
            f"Q LT2: tags de carga sin elemento creado: {sorted(missing)}. "
            "INPUT_REQUIRED.")

    rows = []
    for r in applied.itertuples(index=False):
        q_kN = float(r.load_kN) * (Q_Q / qg)
        rows.append(dict(
            level=r.level, beam_id=r.beam_id, element_tag=int(r.element_tag),
            L_m=float(r.L), xloc=float(r.xloc), s_m=float(r.s_m),
            q_kN=round(q_kN, 12),
            area_m2=round(float(r.load_kN) / qg, 12),
            load_type="beamPoint", w_kN_m=0.0))
    for r in builder.v30_redistribution_rows(Q_Q):
        rows.append(dict(
            level=r["nivel"], beam_id=r["beam_id"],
            element_tag=r["element_tag"], L_m=r["longitud_m"],
            xloc=0.0, s_m=0.0, q_kN=round(r["delta_load_kN"], 12),
            area_m2=round(r["delta_area_m2"], 12),
            load_type="beamUniform", w_kN_m=round(r["delta_w_kN_m"], 12)))
    return pd.DataFrame(rows)


def build_q_lt1(builder):
    """beamUniform Q sobre vigas LT1 (incl. redistribucion de fachada).

    w_Q (kN/m) = q_Q * area_tributaria / longitud_real del elemento, es decir
    total por viga = q_Q * A_trib EXACTO por construccion. Las vigas de
    fachada particionadas se cargan sobre sus segmentos finales conservando
    la misma densidad (procedimiento identico al caso G en run_combined).
    """
    removed = {rb["tag_original"] for rb in builder.removed_beams_loads}
    beams_by_tag = {b["elementTag"]: b for b in builder.json_lt1["beams"]}

    rows = []
    for b in builder.json_lt1["beams"]:
        tag = int(b["elementTag"])
        if tag in removed:
            continue
        a = float(b.get("area_tributaria_m2", 0.0) or 0.0)
        if a < 1e-12:
            continue
        l = _elem_len(tag)
        w = Q_Q * a / l
        rows.append(dict(
            nivel=b["nivel"], nivel_combinado=NI_VEL[b["nivel"]],
            tag_original=tag, element_tag=tag, tipo="viga",
            w_kN_m=round(w, 12), L_m=round(l, 12),
            q_kN=round(w * l, 12),
            area_m2=round(a, 12)))

    for rb in builder.removed_beams_loads:
        b = beams_by_tag.get(rb["tag_original"])
        if b is None:
            raise RuntimeError(
                f"Q LT1: viga original {rb['tag_original']} no encontrada. "
                "INPUT_REQUIRED.")
        a = float(b.get("area_tributaria_m2", 0.0) or 0.0)
        if a < 1e-12:
            continue
        l_orig = float(rb["L_original"])
        if l_orig < 1e-12:
            continue
        w = Q_Q * a / l_orig
        for seg in rb["segments"]:
            l_seg = float(seg["L"])
            rows.append(dict(
                nivel=rb["nivel"], nivel_combinado=NI_VEL[rb["nivel"]],
                tag_original=rb["tag_original"], element_tag=int(seg["tag"]),
                tipo="segmento_fachada",
                w_kN_m=round(w, 12), L_m=round(l_seg, 12),
                q_kN=round(w * l_seg, 12),
                area_m2=round(a * l_seg / l_orig, 12)))

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("Q LT1: sin cargas generadas.")
    return df


def apply_q_patterns(lt2, lt1):
    """Patrones independientes: 3 = LT2-Q, 4 = LT1-Q."""
    ops.timeSeries("Linear", 3)
    ops.pattern("Plain", 3, 3)
    for r in lt2.itertuples(index=False):
        if r.load_type == "beamUniform":
            ops.eleLoad("-ele", int(r.element_tag), "-type", "-beamUniform",
                        0.0, -float(r.w_kN_m))
        else:
            ops.eleLoad("-ele", int(r.element_tag), "-type", "-beamPoint",
                        0.0, -float(r.q_kN), float(r.xloc))
    ops.timeSeries("Linear", 4)
    ops.pattern("Plain", 4, 4)
    for r in lt1.itertuples(index=False):
        ops.eleLoad("-ele", int(r.element_tag), "-type", "-beamUniform",
                    0.0, -float(r.w_kN_m))


def conservation_table(lt2, lt1):
    """Tabla de conservacion por nivel/origen/global (fuente de areas)."""
    rows = []
    trib = pd.read_csv(TRIB_LT2)
    trib = trib[trib.receiver_type == "BEAM"]
    lt1_json = builder_json_areas()

    def add(origen, nivel, area, q_app):
        q_teo = Q_Q * area
        err = q_app - q_teo
        rel = abs(err) / max(q_teo, 1e-12)
        rows.append(dict(
            origen=origen, nivel=nivel, area_m2=round(area, 12),
            q_Q_kPa=Q_Q, Q_teorica_kN=round(q_teo, 12),
            Q_transferida_kN=round(q_app, 12),
            err_abs_kN=round(err, 12), err_rel=rel,
            PASS="PASS" if rel <= TOL_REL else "FAIL"))

    for lv in ["L1", "L2", "L3", "L4"]:
        add("LT2", lv,
            trib[trib.level == lv]["area_m2"].sum(),
            lt2[lt2.level == lv]["q_kN"].sum())
    for nv in NI_VEL:
        add("LT1", nv,
            lt1_json[lt1_json["nivel"] == nv]["area_m2"].sum(),
            lt1[lt1.nivel == nv]["q_kN"].sum())
    # por origen (total)
    add("LT2", "TOTAL", trib["area_m2"].sum(), lt2["q_kN"].sum())
    add("LT1", "TOTAL", lt1_json["area_m2"].sum(), lt1["q_kN"].sum())
    # global
    add("COMBINADO", "TOTAL",
        trib["area_m2"].sum() + lt1_json["area_m2"].sum(),
        lt2["q_kN"].sum() + lt1["q_kN"].sum())
    return pd.DataFrame(rows)


def builder_json_areas():
    with open(JSON_LT1, "r", encoding="utf-8") as f:
        d = json.load(f)
    return pd.DataFrame([
        dict(nivel=b["nivel"], area_m2=float(b.get("area_tributaria_m2", 0.0)
                                             or 0.0))
        for b in d["beams"]])


def run_and_check(builder, q_total):
    """Analiza SOLO el caso Q y verifica equilibrio en reacciones."""
    builder.run_analysis()
    rc = builder.rc
    ok = rc == 0
    if ok:
        ops.reactions()
        cols = ["node_tag", "Rx_kN", "Ry_kN", "Rz_kN"]
        reac = pd.DataFrame(
            [(t, ops.nodeReaction(t, 1), ops.nodeReaction(t, 2),
              ops.nodeReaction(t, 3)) for t in builder.support_tags],
            columns=cols)
        sum_rx = float(reac["Rx_kN"].sum())
        sum_ry = float(reac["Ry_kN"].sum())
        sum_rz = float(reac["Rz_kN"].sum())
        err_rz = abs(sum_rz - q_total)
        rel_rz = err_rz / max(q_total, 1e-12)
    else:
        reac = None
        sum_rx = sum_ry = sum_rz = err_rz = rel_rz = float("nan")
    return dict(rc=rc, equil_OK=ok, reac=reac,
                sum_Rx_kN=sum_rx, sum_Ry_kN=sum_ry, sum_Rz_kN=sum_rz,
                err_abs_kN=err_rz, err_rel=rel_rz)


def write_resumen(cons, lt2, lt1, eq):
    OUT_S3.mkdir(parents=True, exist_ok=True)
    lt2.to_csv(OUT_S3 / "live_load_Q_applied_LT2.csv", index=False)
    lt1.to_csv(OUT_S3 / "live_load_Q_applied_LT1.csv", index=False)
    cons.to_csv(OUT_S3 / "conservacion_Q.csv", index=False)

    fa = cons[cons["nivel"] == "TOTAL"].set_index("origen")
    lin = ["# SEMANA 3 - PARTE A: caso de carga viva Q",
           "",
           f"- q_Q = **{Q_Q} kPa = {Q_Q} kN/m2** (CIERRE DEFINITIVO DE "
           "PARTE A).",
           "",
           "## Criterio de q_Q (NCh1537.Of2009, Tabla 4)",
           "",
           "- Edificacion **EDUCACIONAL** segun NCh1537.Of2009 Tabla 4: "
           "salas de clases = 3.0 kPa; pasillos = 4.0 kPa.",
           "- Los planos estructurales disponibles de LT1 y LT2 no permiten "
           "identificar ni separar con certeza salas de clases y pasillos "
           "(no existen planos arquitectonicos que zonifiquen los usos).",
           f"- Se adopta para esta entrega **q_Q = {Q_Q} kPa = {Q_Q} "
           "kN/m2** UNIFORME en las superficies transitables de LT1 y LT2.",
           f"- **{Q_Q} kPa es una HIPOTESIS CONSERVADORA DE MODELACION** "
           "por la ausencia de planos arquitectonicos que permitan "
           "zonificar los usos. NO se afirma que NCh1537 exija 4.0 kPa "
           "para TODAS las superficies de un edificio educacional.",
           "- Se REEMPLAZA el q_Q provisional anterior (2.0 kPa); las SC "
           "zonales del plano LT1 NO se integran al modelo (propuesta "
           "descartada).",
           "- La geometria tributaria de la Semana 2 se mantiene EXACTA: no "
           "se recalcularon poligonos ni areas tributarias; cada franja de "
           "carga cierra a area_franja * q_Q.",
           "",
           "## Conservacion  sum(Q_transferida) = q_Q * area_tributaria",
           "",
           "| origen | area (m2) | Q_teorica (kN) | Q_transferida (kN) | "
           "err_abs (kN) | err_rel | PASS |",
           "|---|---|---|---|---|---|---|"]
    for _, r in cons.iterrows():
        lin.append(
            f"| {r['origen']} {r['nivel']} | {r['area_m2']:.6f} | "
            f"{r['Q_teorica_kN']:.6f} | {r['Q_transferida_kN']:.6f} | "
            f"{r['err_abs_kN']:.2e} | {r['err_rel']:.2e} | {r['PASS']} |")
    lin.append("")
    lin.append("## Analisis OpenSees (patrones 3 = LT2-Q, 4 = LT1-Q)")
    lin.append("")
    lin.append(f"- analyze rc = **{eq['rc']}** "
               f"({'converge' if eq['rc'] == 0 else 'NO converge'}).")
    lin.append(f"- Q_total aplicado = {Q_Q * (fa.loc['COMBINADO', 'area_m2']):.6f} kN")
    lin.append(f"- sum Rz = {eq['sum_Rz_kN']:.6f} kN; "
               f"|sum Rz - Q_total| = {eq['err_abs_kN']:.3e} kN "
               f"(rel {eq['err_rel']:.3e}).")
    lin.append(f"- sum |Rx| = {abs(eq['sum_Rx_kN']):.3e} kN; "
               f"sum |Ry| = {abs(eq['sum_Ry_kN']):.3e} kN.")
    lin.append("")
    # Conserva (sin recalcular) la seccion de Parte B ya existente en el
    # resumen: esta cierre de Parte A NO recalcula B, pero no debe borrarla.
    prev = OUT_S3 / "resumen_semana03.md"
    prev_text = prev.read_text(encoding="utf-8").rstrip() \
        if prev.exists() else ""
    marker = "## SEMANA 3 - PARTE B"
    if marker in prev_text:
        lines_prev = prev_text.splitlines()
        idx = next(i for i, ln in enumerate(lines_prev)
                   if ln.startswith(marker))
        b_lines = lines_prev[idx:]
        note = ("**NOTA (seccion PREVIA):** la Parte B que sigue fue "
                "calculada con el q_Q ANTERIOR = 2.0 kPa. NO se recalculo "
                "en este cierre de Parte A; queda PENDIENTE de actualizar "
                f"con q_Q = {Q_Q} kPa cuando lo indique el usuario.")
        b_section = ("\n" + b_lines[0] + "\n\n" + note + "\n\n"
                     + "\n".join(b_lines[1:]).rstrip() + "\n")
    else:
        b_section = ""
    (OUT_S3 / "resumen_semana03.md").write_text(
        "\n".join(lin).rstrip() + b_section, encoding="utf-8")


def main():
    print("=" * 72)
    print(f"SEMANA 3 - PARTE A | CARGA VIVA Q | q_Q = {Q_Q} kPa "
          "(NCh1537.Of2009 Tabla 4 - educacional; hipotesis conservadora)")
    print("=" * 72)

    b = CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()

    lt2 = build_q_lt2(b)
    lt1 = build_q_lt1(b)
    print(f"Q LT2 (beamPoint) : {len(lt2)} franjas "
          f"-> {lt2.q_kN.sum():.6f} kN")
    print(f"Q LT1 (beamUniform): {len(lt1)} cargas "
          f"-> {lt1.q_kN.sum():.6f} kN")

    apply_q_patterns(lt2, lt1)

    cons = conservation_table(lt2, lt1)
    print("\nConservacion  sum(Q_transferida) = q_Q * area:")
    print(cons.to_string(index=False))

    q_total = lt2.q_kN.sum() + lt1.q_kN.sum()
    eq = run_and_check(b, q_total)
    print("\nAnalisis OpenSees (patrones 3=LT2-Q, 4=LT1-Q):")
    print(f"  analyze rc       = {eq['rc']}")
    print(f"  Q_total aplicado = {q_total:.6f} kN")
    print(f"  sum Rz           = {eq['sum_Rz_kN']:.6f} kN")
    print(f"  |sum Rz - Q|     = {eq['err_abs_kN']:.3e} kN "
          f"(rel {eq['err_rel']:.3e})")
    print(f"  sum Rx = {eq['sum_Rx_kN']:.3e} kN | "
          f"sum Ry = {eq['sum_Ry_kN']:.3e} kN")

    write_resumen(cons, lt2, lt1, eq)
    print("\nSalidas:")
    for p in sorted(OUT_S3.glob("*")):
        print("  ", p.relative_to(ROOT), "->",
              p.stat().st_size if p.is_file() else "")
    return 0 if eq["rc"] == 0 else 3


if __name__ == "__main__":
    import sys
    sys.exit(main())
