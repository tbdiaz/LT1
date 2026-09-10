# -*- coding: utf-8 -*-
"""SEMANA 3 - PARTE B: sismo pseudoestatico (casos independientes EX y EY).

Casos INDEPENDIENTES: cada uno aplica SOLO la fuerza lateral pseudoestatica
(definida por el profesor en el enunciado) sobre el modelo combinado LT1+LT2.
No se aplica simultaneamente G, Q ni el otro caso sismico.

Peso sismico por piso (reusa la informacion real del modelo):
    W_i = G_i + 0.5*Q_i                      (Q con fraccion de masa live_load_mass_fraction)
    G_i = peso gravitacional tributario del piso i (fuentes existentes):
          LT2: results/gravity_loads_applied_LT2.csv (suma por level)
          LT1: outputs/unity/modelo_lt1.json (carga_total_tributaria_kN por PISO_n)
    Q_i = carga viva del piso i (REUTILIZA el caso Q de la Parte A:
          outputs/semana03/live_load_Q_applied_LT{1,2}.csv, sumas por nivel)
    Se verifica  sum(Q_i) = Q_total de la Parte A (leido de
    conservacion_Q.csv; corresponde al cierre de Parte A con q_Q = 4.0 kPa).

Fuerza lateral por piso (patron configurables):
    F_i = seismic_coefficient * W_i           (patron uniforme por defecto)

Paramentros PROVISIONAL / INPUT_REQUIRED (el patron y parametros seran
definidos por el profesor; el codigo acomoda cualquier solicitud):
    - seismic_coefficient = 0.20  (solo EJEMPLO del enunciado, NCh433 referencia)
    - live_load_mass_fraction = 0.50
    - patron lateral = "uniforme"  (F_i = coef * W_i)
  Ambos se pueden cambiar por variable de entorno o editando las constantes.

Aplicacion: fuerza aplicada en el master node del diafragma de cada piso
(punto de centro de masa supuesto / diafragma rigido). Se REUTILIZAN los
masters existentes (1001..1005, LT2 nativos) - no se crean diafragmas nuevos.
El ROOF (1005) tiene diafragma pero SIN masa seismica definida (no existen
G_i ni Q_i de techo en el modelo tributario); decision confirmada de ocupar
solo L1-L4: W_ROOF = 0 y no recibe F_i (si se reporta su desplazamiento).

Verificaciones EX y EY:
    A) carga lateral total F_total = sum(F_i)  (+ F_i por piso)
    B) corte basal: |sum de reacciones basales en X (EX) / Y (EY)| vs F_total
    C) sentido de la deformada (desplazamientos de TODOS los masters)
    D) torsion de piso (RZ de cada master, sin forzar cero)
    E) convergencia (analyze rc)

Salidas (SOLO dentro de COMBINADO/):
  outputs/semana03/seismic_weight_by_floor.csv
  outputs/semana03/seismic_forces.csv
  outputs/semana03/EX_master_displacements.csv
  outputs/semana03/EY_master_displacements.csv
  outputs/semana03/seismic_equilibrium.csv
  outputs/semana03/resumen_semana03.md  (ACTUALIZA conservando la Parte A)

Analisis usa patrones 5 (EX) y 6 (EY), cada uno en su propio modelo limpio
(ops.wipe al inicio de build), por lo que los casos son independientes. Los
patrones 1/2 (G) y 3/4 (Q) NO se tocan.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
import openseespy.opensees as ops

from run_combined import CombinedBuilder, JSON_LT1

ROOT = Path(__file__).resolve().parents[2]
COMB = ROOT / "COMBINADO"
OUT_S3 = COMB / "outputs" / "semana03"

LT2_GEOM_CSV = ROOT / "LT2" / "data" / "geometry"
MASTERS_LT2_CSV = LT2_GEOM_CSV / "master_nodes_LT2.csv"
LT2_LOADS_CSV = ROOT / "LT2" / "results" / "gravity_loads_applied_LT2.csv"
Q_LT2_CSV = OUT_S3 / "live_load_Q_applied_LT2.csv"
Q_LT1_CSV = OUT_S3 / "live_load_Q_applied_LT1.csv"
RESUMEN_MD = OUT_S3 / "resumen_semana03.md"

# ---------------------------------------------------------------------------
# Paramentros sismicos  ->  PROVISIONAL / INPUT_REQUIRED
# ---------------------------------------------------------------------------
# 0.20 = SOLO el ejemplo del enunciado (aceleracion basal "20% de g" segun
# NCh433). El patron y parametros finales los definira el profesor.
seismic_coefficient = float(os.environ.get("LT1_SEISMIC_COEF", "0.20"))
# fraccion de la carga viva Q considerada como masa sismica (enunciado: 50%).
live_load_mass_fraction = float(os.environ.get("LT1_SEISMIC_Q_FRAC", "0.50"))
# patron/distribucion lateral por piso. Solo "uniforme" implementado;
# extension: F_i = coef * factor_i * W_i.
lateral_pattern = os.environ.get("LT1_SEISMIC_PATTERN", "uniforme")

TOL_REL = 1e-6            # tolerancia relativa de las verificaciones


def q_total_parte_a():
    """Q_total de la Parte A desde conservacion_Q.csv (fuente unica actual).

    Evita hardcodear el valor: lo toma directamente del resultado del cierre
    de Parte A (q_Q = 4.0 kPa) y controla que los archivos aplicados (que
    aqui se reutilizan) sigan siendo coherentes con el ultimo caso Q.
    """
    p = OUT_S3 / "conservacion_Q.csv"
    if not p.exists():
        raise RuntimeError(
            f"SISMO: falta conservacion_Q.csv de la Parte A en {p}. "
            "Ejecutar primero semana03_live_load.py.")
    df = pd.read_csv(p)
    m = df[(df["origen"] == "COMBINADO") & (df["nivel"] == "TOTAL")]
    if len(m) != 1:
        raise RuntimeError(
            "SISMO: la fila COMBINADO/TOTAL de conservacion_Q.csv no es "
            "unica. INPUT_REQUIRED.")
    return float(m["Q_transferida_kN"].iloc[0])
NZ_FLOORS = ["L1", "L2", "L3", "L4"]   # pisos con masa sismica definida
ROOF_LEVEL = "ROOF"                    # diafragma sin masa (W=0, se reporta)
ROOF_TOR_SIGN = 1e-6      # rad: umbral para considerar torsion "apreciable"


def g_by_floor():
    """G_i por piso desde las fuentes reales (sin recalcular areas)."""
    lt2_g = (pd.read_csv(LT2_LOADS_CSV)
             .groupby("level")["load_kN"].sum().to_dict())
    lt1_g = defaultdict(float)
    with open(JSON_LT1, "r", encoding="utf-8") as f:
        beams = json.load(f)["beams"]
    for b in beams:
        lt1_g[b["nivel"]] += float(b.get("carga_total_tributaria_kN", 0.0)
                                   or 0.0)
    return lt2_g, dict(lt1_g)


def q_by_floor():
    """Q_i por piso REUTILIZANDO el caso Q de la Parte A (archivos aplicados)."""
    lt2_q = (pd.read_csv(Q_LT2_CSV).groupby("level")["q_kN"].sum()
             .to_dict())
    lt1_q = (pd.read_csv(Q_LT1_CSV).groupby("nivel_combinado")["q_kN"].sum()
             .to_dict())
    return lt2_q, lt1_q


def master_tags_by_level():
    """Mapa nivel -> tag master (1001..1005) igual que CombinedBuilder.build()."""
    m = pd.read_csv(MASTERS_LT2_CSV)
    return {row.level: 1001 + i for i, row in enumerate(m.itertuples(index=False))}


def build_weight_table():
    """Tabla piso -> master, G_i, Q_i, 0.5Q_i, W_sismico_i (L1..L4 + ROOF)."""
    lt2_g, lt1_g = g_by_floor()
    lt2_q, lt1_q = q_by_floor()
    tag_by_level = master_tags_by_level()

    rows = []
    for lv in NZ_FLOORS:
        lt1n = "PISO_%s" % lv[1]
        rows.append(dict(
            piso=lv, master_tag=tag_by_level[lv],
            G_LT2_kN=lt2_g.get(lv, 0.0), G_LT1_kN=lt1_g.get(lt1n, 0.0),
            Q_LT2_kN=lt2_q.get(lv, 0.0),
            Q_LT1_kN=lt1_q.get(lv, 0.0)))
    rows.append(dict(   # ROOF: diafragma sin masa definida en el modelo
        piso=ROOF_LEVEL, master_tag=tag_by_level[ROOF_LEVEL],
        G_LT2_kN=0.0, G_LT1_kN=0.0, Q_LT2_kN=0.0, Q_LT1_kN=0.0))

    df = pd.DataFrame(rows)
    df["G_i_kN"] = df["G_LT2_kN"] + df["G_LT1_kN"]
    df["Q_i_kN"] = df["Q_LT2_kN"] + df["Q_LT1_kN"]
    df["half_Q_i_kN"] = live_load_mass_fraction * df["Q_i_kN"]
    df["W_sismico_kN"] = df["G_i_kN"] + df["half_Q_i_kN"]
    return df


def forces_per_floor(weights):
    """F_i por piso segun patron. Solo 'uniforme' implementado por ahora."""
    if lateral_pattern != "uniforme":
        raise RuntimeError(
            f"SISMO: patron lateral '{lateral_pattern}' no implementado. "
            "INPUT_REQUIRED.")
    rows = [dict(piso=r.piso, master_tag=int(r.master_tag),
                 W_sismico_kN=float(r.W_sismico_kN),
                 F_i_kN=seismic_coefficient * float(r.W_sismico_kN))
            for r in weights.itertuples(index=False)
            if float(r.W_sismico_kN) > 1e-12]
    f_total = sum(float(r["F_i_kN"]) for r in rows)
    return pd.DataFrame(rows), f_total


def apply_lateral(builder, forces, direction):
    """Patron independiente: 5 = EX (fuerzas +X), 6 = EY (fuerzas +Y)."""
    tag = 5 if direction == "EX" else 6
    ops.timeSeries("Linear", tag)
    ops.pattern("Plain", tag, tag)
    for r in forces.itertuples(index=False):
        tag = int(r.master_tag)
        fx = float(r.F_i_kN)
        if direction == "EX":
            ops.load(tag, fx, 0.0, 0.0, 0.0, 0.0, 0.0)
        else:
            ops.load(tag, 0.0, fx, 0.0, 0.0, 0.0, 0.0)


def run_case(direction, forces, weight_table):
    """Modelo limpio + carga lateral + analisis + reacciones + desplazamientos."""
    b = CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()
    apply_lateral(b, forces, direction)
    rc = b.run_analysis()

    sum_rx = sum_ry = sum_rz = float("nan")
    disp = []
    if rc == 0:
        ops.reactions()
        sum_rx = float(sum(ops.nodeReaction(t, 1) for t in b.support_tags))
        sum_ry = float(sum(ops.nodeReaction(t, 2) for t in b.support_tags))
        sum_rz = float(sum(ops.nodeReaction(t, 3) for t in b.support_tags))
        for r in weight_table.itertuples(index=False):
            t = int(r.master_tag)
            disp.append(dict(
                piso=r.piso, master_tag=t,
                UX_m=float(ops.nodeDisp(t, 1)), UY_m=float(ops.nodeDisp(t, 2)),
                RZ_rad=float(ops.nodeDisp(t, 6))))
    return b, rc, sum_rx, sum_ry, sum_rz, pd.DataFrame(disp)


def equilibrium_row(direction, f_total, rc, sum_rx, sum_ry, sum_rz):
    """B) corte basal comparado con F_total (reacciones de signo contrario)."""
    mag = abs(sum_rx) if direction == "EX" else abs(sum_ry)
    err_abs = abs(mag - f_total)
    err_rel = err_abs / max(f_total, 1e-12)
    ok = rc == 0 and err_rel <= TOL_REL
    return dict(caso=direction, F_total_kN=round(f_total, 12),
                corte_basal_kN=round(mag, 12),
                err_abs_kN=round(err_abs, 12), err_rel=err_rel,
                PASS="PASS" if ok else "FAIL",
                sum_Rx_kN=round(sum_rx, 12), sum_Ry_kN=round(sum_ry, 12),
                sum_Rz_kN=round(sum_rz, 12), analyze_rc=rc)


def analyze_sign(disp, direction):
    """C) sentido de la deformada: dominio UX (EX) o UY (EY) en los masters."""
    col = "UX_m" if direction == "EX" else "UY_m"
    vals = [float(v) for v in disp[col] if abs(float(v)) > 1e-12]
    if not vals:
        return "indefinido (desplazamientos ~= 0)"
    dom = sum(1 for v in vals if v > 0)
    tot = len(vals)
    if dom / tot > 0.8:
        return "+%s coherente" % ("X" if direction == "EX" else "Y")
    if (tot - dom) / tot > 0.8:
        return "-%s (opuesto)" % ("X" if direction == "EX" else "Y")
    return "mixto (no dominante un signo)"


def torsion_summary(disp):
    m = disp["RZ_rad"].abs().max()
    aprec = bool(m > ROOF_TOR_SIGN)
    return m, ("TORSION APRECIABLE" if aprec else "torsion practicamente nula")


def write_outputs(weights, forces, f_total, res_ex, res_ey,
                  disp_ex, disp_ey):
    OUT_S3.mkdir(parents=True, exist_ok=True)
    weights.to_csv(OUT_S3 / "seismic_weight_by_floor.csv", index=False)
    forces.to_csv(OUT_S3 / "seismic_forces.csv", index=False)
    disp_ex.to_csv(OUT_S3 / "EX_master_displacements.csv", index=False)
    disp_ey.to_csv(OUT_S3 / "EY_master_displacements.csv", index=False)
    pd.DataFrame([res_ex, res_ey]).to_csv(
        OUT_S3 / "seismic_equilibrium.csv", index=False)

    g_total = float(weights["G_i_kN"].sum())
    q_total = float(weights["Q_i_kN"].sum())
    w_total = float(weights["W_sismico_kN"].sum())

    nz = weights[weights["W_sismico_kN"] > 1e-12]
    lin = []
    lin.append("")
    lin.append("## SEMANA 3 - PARTE B: sismo pseudoestatico (EX y EY)")
    lin.append("")
    lin.append("- seismic_coefficient = **%.2f** (PROVISIONAL / INPUT_REQUIRED; "
               "solo el EJEMPLO del enunciado '20%% de g' NCh433; lo definira "
               "el profesor)." % seismic_coefficient)
    lin.append("- live_load_mass_fraction = **%.2f** (enunciado; configurable)."
               % live_load_mass_fraction)
    lin.append("- patron lateral = **%s**  (F_i = coef * W_i)." % lateral_pattern)
    lin.append("- W_i = G_i + %.1f*Q_i. G_i = peso gravitacional tributario del "
               "piso (PP losa + terminaciones; LT2: sumas por level de "
               "`gravity_loads_applied_LT2.csv`, LT1: `carga_total_tributaria_kN` "
               "de `modelo_lt1.json`). NO recalculadas areas tributarias; NO se "
               "incluye p.p. de vigas/columnas/muros." % live_load_mass_fraction)
    lin.append("- Q_i reutiliza los archivos aplicados del caso Q (Parte A).")
    lin.append("- Fuerza aplicada en el master node de cada piso (masters "
               "existentes 1001..1005 reutilizados).")
    lin.append("- ROOF (master 1005): sin masa sismica definida en el modelo "
               "tributario -> W_ROOF = 0, sin F_ROOF (decision confirmada). "
               "SI se reporta su desplazamiento.")
    lin.append("")
    lin.append("### Peso sismico por piso")
    lin.append("")
    lin.append("| piso | master | G_i (kN) | Q_i (kN) | 0.5*Q_i (kN) | "
               "W_sismico (kN) |")
    lin.append("|---|---|---|---|---|---|")
    for r in weights.itertuples(index=False):
        lin.append(f"| {r.piso} | {int(r.master_tag)} | {float(r.G_i_kN):.6f} | "
                   f"{float(r.Q_i_kN):.6f} | {float(r.half_Q_i_kN):.6f} | "
                   f"{float(r.W_sismico_kN):.6f} |")
    lin.append(f"| **sum** | | **{g_total:.6f}** | **{q_total:.6f}** | "
               f"**{q_total * live_load_mass_fraction:.6f}** "
               f"| **{w_total:.6f}** |")
    lin.append("")
    lin.append(f"- sum(Q_i) = {q_total:.6f} kN  vs  Q_total Parte A = "
               f"{q_total_parte_a():.6f} kN")
    q_ok = ("OK" if abs(q_total - q_total_parte_a()) /
            max(q_total_parte_a(), 1e-12) <= TOL_REL else "REVISAR")
    lin.append(f"  -> {q_ok}")
    lin.append(f"- sum(G_i) = {g_total:.6f} kN (peso usado para formar la masa "
               "sismica; componentes: PP losa + terminaciones).")
    lin.append("")
    lin.append("### Fuerzas laterales  (F_i = coef * W_i, patron 'uniforme')")
    lin.append("")
    lin.append("| piso | master | W_i (kN) | F_i (kN) |")
    lin.append("|---|---|---|---|")
    for r in forces.itertuples(index=False):
        lin.append(f"| {r.piso} | {int(r.master_tag)} | "
                   f"{float(r.W_sismico_kN):.6f} | {float(r.F_i_kN):.6f} |")
    lin.append(f"| **F_total** | | | **{f_total:.6f}** |")
    lin.append("")
    lin.append("### Corte basal y convergencia (ver seismic_equilibrium.csv)")
    lin.append("")
    lin.append("| caso | F_total (kN) | corte_basal (kN) | err_abs (kN) | "
               "err_rel | PASS | analyze rc |")
    lin.append("|---|---|---|---|---|---|---|")
    for r in (dict(res_ex), dict(res_ey)):
        lin.append(f"| {r['caso']} | {r['F_total_kN']:.6f} | "
                   f"{r['corte_basal_kN']:.6f} | {r['err_abs_kN']:.3e} | "
                   f"{r['err_rel']:.2e} | {r['PASS']} | {r['analyze_rc']} |")
    lin.append("")
    lin.append("### Desplazamientos de master nodes (signo de la deformada)")
    lin.append("")
    for caso, disp in (("EX", disp_ex), ("EY", disp_ey)):
        m, tor = torsion_summary(disp)
        sent = analyze_sign(disp, caso)
        lin.append("")
        lin.append(f"#### {caso} (fuerzas en +{'X' if caso == 'EX' else 'Y'})")
        lin.append(f"- Sentido de la deformada: **{sent}**.")
        lin.append(f"- Torsion por piso: **{tor}** (max |RZ| = {m:.3e} rad).")
        lin.append("")
        lin.append("| piso | master | UX (m) | UY (m) | RZ (rad) |")
        lin.append("|---|---|---|---|---|")
        for r in disp.itertuples(index=False):
            lin.append(f"| {r.piso} | {int(r.master_tag)} | "
                       f"{float(r.UX_m):.6e} | {float(r.UY_m):.6e} | "
                       f"{float(r.RZ_rad):.6e} |")
    lin.append("")
    lin.append("Nota: EX y EY son casos independientes (cada uno con su propio "
               "modelo y patron: 5 = EX, 6 = EY); no se aplicaron G, Q ni "
               "superposicion. Los patrones 1/2 (G) y 3/4 (Q) de la Parte A no "
               "se modificaron.")
    lin.append("")

    prev = RESUMEN_MD.read_text(encoding="utf-8").rstrip()
    marker = "## SEMANA 3 - PARTE B"
    if marker in prev:      # hace idempotente: quita secciones B anexadas antes
        prev = prev.split(marker, 1)[0].rstrip()
    RESUMEN_MD.write_text(prev + "\n" + "\n".join(lin).lstrip("\n"),
                          encoding="utf-8")


def main():
    print("=" * 74)
    print(f"SEMANA 3 - PARTE B | SISMO PSEUDOESTATICO | "
          f"coef={seismic_coefficient} | q_frac={live_load_mass_fraction} | "
          f"patron={lateral_pattern}")
    print("  Todos los parametros sismicos son PROVISIONAL / INPUT_REQUIRED")
    print("=" * 74)

    b = CombinedBuilder()
    b.prepare()
    b.check_interface()

    weights = build_weight_table()
    forces, f_total = forces_per_floor(weights)

    q_total = float(weights["Q_i_kN"].sum())
    g_total = float(weights["G_i_kN"].sum())
    ref_a = q_total_parte_a()
    q_rel = abs(q_total - ref_a) / max(ref_a, 1e-12)
    if q_rel > TOL_REL:
        raise RuntimeError(
            f"SISMO: sum(Q_i)={q_total:.6f} no coincide con Q_total Parte A "
            f"({ref_a:.6f}). INPUT_REQUIRED.")
    print(f"\nsum(G_i) = {g_total:.6f} kN | sum(Q_i) = {q_total:.6f} kN "
          f"(OK vs Parte A) | sum(W_i) = {weights.W_sismico_kN.sum():.6f} kN")

    print("\nPeso sismico por piso:")
    print(weights.to_string(index=False))
    print("\nFuerzas laterales por piso (F_i = coef * W_i):")
    print(forces.to_string(index=False))
    print(f"  F_total = {f_total:.6f} kN")

    res = {}
    disp = {}
    for direction in ("EX", "EY"):
        b2, rc, srx, sry, srz, d = run_case(direction, forces, weights)
        res[direction] = equilibrium_row(direction, f_total, rc, srx, sry, srz)
        disp[direction] = d
        r = res[direction]
        print(f"\n--- {direction} -------------------------------------------------")
        print(f"  analyze rc        = {r['analyze_rc']}")
        print(f"  F_total           = {r['F_total_kN']:.6f} kN")
        print(f"  corte basal (|sum|) = {r['corte_basal_kN']:.6f} kN")
        print(f"  err_abs           = {r['err_abs_kN']:.3e} kN "
              f"(rel {r['err_rel']:.2e}) -> {r['PASS']}")
        print(f"  sum Rx = {r['sum_Rx_kN']:.6e} | sum Ry = {r['sum_Ry_kN']:.6e} "
              f"| sum Rz = {r['sum_Rz_kN']:.6e}")
        print("  Master displacements:")
        print(d.to_string(index=False))
        m, tor = torsion_summary(d)
        print(f"  Torsion: max|RZ| = {m:.3e} rad -> {tor}")
        print(f"  Sentido deformada: {analyze_sign(d, direction)}")

    print("\nResumen de corte basal:")
    print(pd.DataFrame([res["EX"], res["EY"]]).to_string(index=False))

    write_outputs(weights, forces, f_total, res["EX"], res["EY"],
                  disp["EX"], disp["EY"])

    print("\nSalidas:")
    for p in sorted(OUT_S3.glob("*")):
        print("  ", p.relative_to(ROOT), "->",
              p.stat().st_size if p.is_file() else "")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())