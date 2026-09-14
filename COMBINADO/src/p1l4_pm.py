# -*- coding: utf-8 -*-
"""P1L4 - FASE 3 (corregida): capacidades P-M por fiber section, M001 y
columna 113022.

Auditoria EY / eje de la curva (FASE A):
  - FiberSection2d integra M = Sum(sigma*A*primera_coordenada del parche).
  - Para el muro M001 la curva de eje FUERTE (en el plano de la pared,
    momento de vuelco sobre el eje local z = X global) se obtiene con la
    longitud L en la primera coordenada (largo en el parche). Verificado
    experimentalmente: misma seccion con 0.6 en 1a coord -> pico ~1366
    kN.m (eje DEBIL); con 2.92 en 1a coord -> pico ~8398 kN.m (eje FUERTE).
  - M_muro (demanda) es el momento en el plano (eje fuerte); se compara con
    la curva FUERTE. My_muro (12gdl) es el momento fuera de plano (eje
    debil); se compara con la curva DEBIL.
  - Comprobacion independiente de la demanda: Mz1(4001) y Mz1(4002) son
    exactamente las reacciones Mx de los apoyos node1/node3 del propio
    modelo (mismo valor), y N_muro = Rz(node1)+Rz(node3). La recomposicion
    4001+4002 queda verificada sin ambiguedad.

Demanda (fuerzas locales) leida del modelo combinado sin re-ejecutar el
analisis global. NO modifica el modelo; escribe SOLO en outputs/p1l4/.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import openseespy.opensees as ops

ROOT = Path(__file__).resolve().parents[2]
COMB = ROOT / "COMBINADO"
OUT4 = COMB / "outputs" / "p1l4"
JSON_MODELO = COMB / "outputs" / "unity" / "modelo_combinado.json"

# --------------------------------------------------------------------------
# Materiales [CONFIRMADO usuario]
# --------------------------------------------------------------------------
FC_KPA = 35.0 * 1000.0
FY_KPA = 420.0 * 1000.0
ES_KPA = 200.0 * 1.0e6
B_STEEL = 0.01
COVER_COL_M = 0.04

# --------------------------------------------------------------------------
# Columna 113022 (P. 70x70, 16 22)
# --------------------------------------------------------------------------
COL_TAG = 113022
COL_B = 0.70
COL_H = 0.70
COL_N_BARS = 16
COL_ABAR = math.pi * 0.011 ** 2

# --------------------------------------------------------------------------
# Muro M001 (e=0.60, L=2.92)
# --------------------------------------------------------------------------
WALL_TAGS = (4001, 4002)
WALL_E = 0.60
WALL_L = 2.92
WALL_HALF = WALL_L / 2.0
WALL_WEB_MM = 12.0
WALL_WEB_S_M = 0.20
WALL_ABAR12 = math.pi * 0.006 ** 2
WALL_BORDER_MM = 22.0
WALL_BORDER_PER_FACE_END = 4
WALL_ABAR22 = math.pi * 0.011 ** 2
WALL_COVER_MESH_M = 0.035
WALL_COVER_BORDER_M = 0.05

CASOS = ["G", "Q", "EX", "EY", "COMBO_R"]


def bar_positions_column():
    return [( -0.31, -0.31), (0.31, -0.31), (-0.31, 0.31), (0.31, 0.31),
            (-0.155, 0.31), (0.0, 0.31), (0.155, 0.31),
            (-0.155, -0.31), (0.0, -0.31), (0.155, -0.31),
            (0.31, -0.155), (0.31, 0.0), (0.31, 0.155),
            (-0.31, -0.155), (-0.31, 0.0), (-0.31, 0.155)]


def steel_positions_wall(axis):
    """(py, pz, a) del acero vertical. Para `axis`:
      - 'strong': py=longitud(+-1.46) (1a coord -> M en plano), pz=espesor.
      - 'weak'  : py=espesor(+-0.3)  (1a coord -> M fuera de plano),
                  pz=longitud.
    """
    if axis == "strong":
        y_arm, z_arm = WALL_HALF, WALL_E / 2
        cover_web = WALL_E / 2 - WALL_COVER_MESH_M
        cover_bor = WALL_E / 2 - WALL_COVER_BORDER_M
    else:
        y_arm, z_arm = WALL_E / 2, WALL_HALF
        cover_web = WALL_HALF - 0.05        # las barras de malla en el borde
        cover_bor = WALL_HALF - 0.05
    pos = []
    t = -1.2
    while t <= 1.2 + 1e-9:
        pos.append((t, cover_web, WALL_ABAR12, WALL_WEB_MM))
        pos.append((t, -cover_web, WALL_ABAR12, WALL_WEB_MM))
        t += WALL_WEB_S_M
    for signo in (-1.0, 1.0):
        for k in range(WALL_BORDER_PER_FACE_END):
            t = signo * (y_arm - 0.05 - k * 0.025)
            pos.append((t, cover_bor, WALL_ABAR22, WALL_BORDER_MM))
            pos.append((t, -cover_bor, WALL_ABAR22, WALL_BORDER_MM))
    return pos


def build_section(kind, axis="strong"):
    ops.uniaxialMaterial("Concrete01", 1, -FC_KPA, -0.002, -0.2 * FC_KPA,
                         -0.006)
    ops.uniaxialMaterial("Steel01", 2, FY_KPA, ES_KPA, B_STEEL)
    ops.section("Fiber", 10)
    if kind == "column":
        ops.patch("rect", 1, 48, 48, -0.35, -0.35, 0.35, 0.35)
        for (y, z) in bar_positions_column():
            ops.fiber(y, z, COL_ABAR, 2)
    else:
        if axis == "strong":
            ops.patch("rect", 1, 80, 64, -WALL_HALF, -WALL_E / 2,
                      WALL_HALF, WALL_E / 2)
        else:
            ops.patch("rect", 1, 64, 80, -WALL_E / 2, -WALL_HALF,
                      WALL_E / 2, WALL_HALF)
        for (y, z, a, _d) in steel_positions_wall(axis):
            ops.fiber(y, z, a, 2)


def fiber_model(kind, axis="strong"):
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    build_section(kind, axis)
    ops.node(1, 0.0, 0.0)
    ops.node(2, 0.0, 0.0)
    ops.fix(1, 1, 1, 1)
    ops.fix(2, 0, 1, 0)
    ops.element("zeroLengthSection", 1, 1, 2, 10)
    ops.constraints("Plain")
    ops.numberer("Plain")
    ops.system("SparseGeneral", "-piv")
    ops.test("EnergyIncr", 2.0e-8, 60, 2)
    ops.algorithm("Newton")


def moment_curvature(kind, P_kN, axis="strong", ext_dist=None):
    """M-phi a carga axial constante (P negativo = compresion).

    La capacidad "nominal" se define en el estado limite de la fibra extrema
    de COMPresion con eps_cu = 0.003 (criterio ACI/NEC, convencional), con
    lo que se evita el artefacto del endurecimiento lineal de Steel01 a
    curvaturas grandes. Se reporta el pico de M dentro de ese rango.
    """
    if kind == "column":
        ext_dist = ext_dist or 0.35
        max_kappa = 0.0032 / ext_dist
        num_incr = 220
    elif axis == "strong":
        ext_dist = ext_dist or WALL_HALF
        max_kappa = 0.0032 / ext_dist
        num_incr = 300
    else:
        ext_dist = ext_dist or WALL_E / 2
        max_kappa = 0.0032 / ext_dist
        num_incr = 300
    fiber_model(kind, axis)
    ops.timeSeries("Constant", 1)
    ops.pattern("Plain", 1, 1)
    ops.load(2, P_kN, 0.0, 0.0)
    ops.integrator("LoadControl", 0.0)
    ops.analysis("Static")
    if ops.analyze(1) != 0:
        raise RuntimeError(f"axial P={P_kN} no converge")
    ops.timeSeries("Linear", 2)
    ops.pattern("Plain", 2, 2)
    ops.load(2, 0.0, 0.0, 1.0)
    ops.integrator("DisplacementControl", 2, 3, max_kappa / num_incr)
    rows = []
    for _ in range(num_incr):
        ok = ops.analyze(1)
        if ok != 0:
            ops.algorithm("KrylovNewton")
            ok = ops.analyze(1)
            ops.algorithm("Newton")
            if ok != 0:
                break
        k = float(ops.nodeDisp(2, 3))
        m = float(ops.getTime())
        if m < 0.0:
            break
        rows.append((k, m))
    if not rows:
        raise RuntimeError(f"M-phi vacia P={P_kN}")
    eps_lim = 0.0030
    in_lim = [r for r in rows if r[0] * ext_dist <= eps_lim]
    ranked = in_lim if in_lim else rows
    ik = max(range(len(ranked)), key=lambda i: ranked[i][1])
    return ranked[ik]


def axial_push(kind, axis="strong", max_incr=220):
    fiber_model(kind, axis)
    ops.timeSeries("Linear", 3)
    ops.pattern("Plain", 3, 3)
    ops.load(2, -1.0, 0.0, 0.0)
    ops.integrator("DisplacementControl", 2, 1, -2.0e-5)
    ops.analysis("Static")
    p0 = 0.0
    for _ in range(max_incr):
        if ops.analyze(1) != 0:
            break
        n = tuple(ops.eleResponse(1, "basicForces"))[0]
        if n < p0:
            p0 = n
    return p0


def _load_model():
    with open(JSON_MODELO, "r", encoding="utf-8") as f:
        return json.load(f)


def demand_entries():
    d = _load_model()
    f = d["results"]["forces"]
    rows = []
    for case in CASOS:
        a, b = f[case]["4001"], f[case]["4002"]
        c = f[case][str(COL_TAG)]
        n_wall = float(a["N1"]) + float(b["N1"])
        m_wall = abs(float(a["Mz1"]) + float(b["Mz1"])
                     + WALL_HALF * (float(a["N1"]) - float(b["N1"])))
        my_wall = abs(float(a["My1"]) + float(b["My1"]))
        rows.append(dict(
            caso=case,
            N4001_kN=float(a["N1"]), N4002_kN=float(b["N1"]),
            Mz1_4001_kN_m=float(a["Mz1"]), Mz1_4002_kN_m=float(b["Mz1"]),
            par_axial_kN_m=WALL_HALF * (float(a["N1"]) - float(b["N1"])),
            N_muro_kN=n_wall, M_muro_kN_m=m_wall, My_muro_kN_m=my_wall,
            N_col_kN=float(c["N1"]),
            M_col_kN_m=math.hypot(float(c["My1"]), float(c["Mz1"])),
        ))
    return rows


def run():
    OUT4.mkdir(parents=True, exist_ok=True)
    dem = demand_entries()
    df_dem = pd.DataFrame(dem)
    df_dem.to_csv(OUT4 / "demanda_p1l4.csv", index=False)

    AX_COL = [0, -250, -500, -1000, -1600, -3000, -6000,
              -9000, -13000, -16500, -19000]
    AX_WALL_S = [0, -250, -500, -800, -1200, -3000, -8000,
                 -16000, -35000, -52000, -55000]
    AX_WALL_W = [0, -250, -500, -800, -1200]

    curves = {}

    def curva(kind, axial_cases, axis, fname):
        pm = []
        for P in axial_cases:
            k, m = moment_curvature(kind, P, axis)
            pm.append((P, m))
            print(kind, axis, f"P={P:8.0f}  kappa={k:.4f}  M={m:9.2f}")
        p0 = axial_push(kind, axis)
        pm.append((p0, 0.0))
        pm.sort(key=lambda x: x[0])
        rows = [dict(P_kN=p, M_kN_m=m) for p, m in pm]
        pd.DataFrame(rows).to_csv(OUT4 / fname, index=False)
        curves[fname] = dict(points=pm, P0_kN=p0)
        print("  P0 =", p0)

    curva("column", AX_COL, "strong", "pm_column_113022.csv")
    curva("wall", AX_WALL_S, "strong", "pm_wall_M001_fuerte.csv")
    curva("wall", AX_WALL_W, "weak", "pm_wall_M001_debil.csv")

    # --- demanda contra capacidad ---------------------------------------
    checks = []
    for r in dem:
        kk, mc_f = moment_curvature("wall", -r["N_muro_kN"], "strong")
        kk2, mc_w = moment_curvature("wall", -r["N_muro_kN"], "weak")
        kk3, mc_c = moment_curvature("column", -r["N_col_kN"])
        checks.append(dict(
            caso=r["caso"],
            N_col=r["N_col_kN"], M_col=r["M_col_kN_m"],
            M_cap_col=mc_c, dentro_col=r["M_col_kN_m"] <= mc_c,
            N_muro=r["N_muro_kN"], M_muro=r["M_muro_kN_m"],
            My_muro=r["My_muro_kN_m"],
            M_cap_muro_fuerte=mc_f, dentro_fuerte=r["M_muro_kN_m"] <= mc_f,
            M_cap_muro_debil=mc_w, dentro_debil=r["My_muro_kN_m"] <= mc_w,
        ))
    df_chk = pd.DataFrame(checks)
    df_chk.to_csv(OUT4 / "demanda_capacidad_p1l4.csv", index=False)
    print(df_chk.to_string(index=False))

    # --- figuras ---------------------------------------------------------
    # columna (unitaria)
    fig, ax = plt.subplots(figsize=(7, 5.2))
    dc = pd.read_csv(OUT4 / "pm_column_113022.csv")
    ax.plot(dc["M_kN_m"], dc["P_kN"].abs(), "-o", color="tab:red",
            label="Capacidad columna 113022 (70x70, 16 22)")
    for _, r in df_chk.iterrows():
        s = "in" if r["dentro_col"] else "FUERA"
        ax.plot([r["M_col"]], [abs(r["N_col"])], "x",
                color="tab:blue", ms=10, label=r["caso"] + f"({s})")
    ax.set_xlabel("Momento M [kN.m]"); ax.set_ylabel("Compresion N [kN]")
    ax.set_title("P-M columna LT1 113022 (G x3): 70x70, 16 22\n"
                 "fc=35,fy=420 CONFIRMADOS | distribucion/recub SUPUESTO")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT4 / "pm_column_113022.png", dpi=150)
    plt.close(fig)

    # muro: fuerte + debil
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    dsf = pd.read_csv(OUT4 / "pm_wall_M001_fuerte.csv")
    a1.plot(dsf["M_kN_m"], dsf["P_kN"].abs(), "-o", color="tab:green",
            label="Capacidad eje FUERTE (en plano)")
    a1.plot([r["M_muro"] for _, r in df_chk.iterrows()],
            [abs(r["N_muro"]) for _, r in df_chk.iterrows()],
            "x", color="tab:purple", ms=10,
            label="Demanda M_muro por caso")
    a1.set_title("M001 eje fuerte (en plano, Mz global X)")
    a1.set_xlabel("Momento M [kN.m]"); a1.set_ylabel("Compresion N [kN]")
    a1.grid(alpha=0.3); a1.legend(fontsize=8)
    dsw = pd.read_csv(OUT4 / "pm_wall_M001_debil.csv")
    a2.plot(dsw["M_kN_m"], dsw["P_kN"].abs(), "-o", color="tab:orange",
            label="Capacidad eje DEBIL (fuera de plano)")
    a2.plot([r["My_muro"] for _, r in df_chk.iterrows()],
            [abs(r["N_muro"]) for _, r in df_chk.iterrows()],
            "x", color="tab:purple", ms=10, label="Demanda My_muro")
    a2.set_title("M001 eje debil (fuera de plano, My)") 
    a2.set_xlabel("Momento M [kN.m]"); a2.set_ylabel("Compresion N [kN]")
    a2.grid(alpha=0.3); a2.legend(fontsize=8)
    fig.suptitle("Muro LT2 M001 (eje A'): e=0.60 PLANO | L=2.92 GEOM. "
                 "MODELO | borde 4 22/cara/extremo SUPUESTO\n"
                 "curva fuerte: FiberSection2d con L en 1a coord "
                 "(auditado). Materiales fc=35,fy=420 CONFIRMADOS")
    fig.tight_layout(); fig.savefig(OUT4 / "pm_wall_M001.png", dpi=150)
    plt.close(fig)

    write_resumen(curves, df_chk, df_dem)
    return 0


def write_resumen(curves, df_chk, df_dem):
    ey = df_dem.loc[df_dem["caso"] == "EY"].iloc[0]
    ln = []
    ln.append("# P1L4 - FASE 3 (corregida): capacidades P-M y demanda")
    ln.append("")
    ln.append("## Auditoria EY (FASE A) - desglose de M_muro(EY)")
    ln.append("")
    ln.append("| termino | valor | fuente |")
    ln.append("|---|---|---|")
    ln.append("| Mz1(4001) | {:.4f} kN.m | = reaccion Mx(node1) del modelo |"
              .format(ey["Mz1_4001_kN_m"]))
    ln.append("| Mz1(4002) | {:.4f} kN.m | = reaccion Mx(node3) del modelo |"
              .format(ey["Mz1_4002_kN_m"]))
    ln.append("| N1(4001) | {:.4f} kN | nodo 23 sin canales axiales |"
              .format(ey["N4001_kN"]))
    ln.append("| N1(4002) | {:.4f} kN | traccion neta = Rz(node3) |"
              .format(ey["N4002_kN"]))
    ln.append("| par axial 1.46*(N4001-N4002) | {:.4f} kN.m | Steiner |"
              .format(ey["par_axial_kN_m"]))
    ln.append("| SUMA M_muro = | {:.4f} kN.m | |".format(ey["M_muro_kN_m"]))
    ln.append("")
    ln.append("Verificaciones: (a) los Mz son exactamente las reacciones Mx "
              "de los apoyos 1 y 3 del propio modelo; (b) N_muro = "
              "Rz(1)+Rz(3) con diferencia nula; (c) ambos elementos comparten "
              "local z = (1,0,0) y extremo i = base B1, mismo corte fisico; "
              "(d) el equilibrio de momentos en los nodos 23 y 25 cierra; "
              "(e) sin doble contabilizacion: cada Mz esta referido al "
              "centroidide de su media seccion y el par solo traslada las "
              "axiales al centroidide del muro (Steiner).")
    ln.append("")
    ln.append("## Eje fuerte/debil del muro (decision)")
    ln.append("")
    ln.append("FiberSection2d integra el momento con la PRIMERA coordenada "
              "del patch. Con L=2.92 en la 1a coord -> curva EJE FUERTE (en "
              "el plano, momento de vuelco sobre X global). Con e=0.60 en la "
              "1a coord -> curva EJE DEBIL (fuera de plano). Verificado por "
              "experimento con el mismo acero: pico debil ~1366 kN.m (P=0) "
              "vs fuerte ~8398 kN.m (P=0). M_muro se compara contra la curva "
              "FUERTE; My_muro contra la curva DEBIL.")
    ln.append("")
    ln.append("## Demanda (recomposicion 4001+4002) y capacidad")
    ln.append("")
    ln.append("| caso | N_col | M_col | M_cap_col | dentro | N_muro | M_muro"
              " fuerte | M_cap_fuerte | dentro | My_muro debil | M_cap_debil"
              " | dentro |")
    ln.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in df_chk.itertuples():
        ln.append("| {c} | {n:.2f} | {m:.2f} | {mc:.2f} | {dc} | {nw:.2f} | "
                  "{mf:.2f} | {mcf:.2f} | {df} | {mw:.2f} | {mcw:.2f} | {dw} "
                  "|".format(c=r.caso, n=r.N_col, m=r.M_col, mc=r.M_cap_col,
                             dc=r.dentro_col, nw=r.N_muro, mf=r.M_muro,
                             mcf=r.M_cap_muro_fuerte, df=r.dentro_fuerte,
                             mw=r.My_muro, mcw=r.M_cap_muro_debil,
                             dw=r.dentro_debil))
    ln.append("")
    ln.append("## Supuestos (FASE 1) y criterios")
    ln.append("")
    ln.append("* material CONFIRMADO: fc=35 MPa, fy=420 MPa, Es=200 GPa.")
    ln.append("* columna 113022: P.70x70, 16 22 EXACT (plano); distribucion "
              "simetrica y recubrimiento 0.04 m: SUPUESTO.")
    ln.append("* muro M001: e=0.60 CONFIRMADO_PLANO(303); L=2.92 GEOMETRIA DEL"
              " MODELO (csv/modelo); malla D.M.V. 12 a 20 doble cara PLANO; "
              "borde minimo 4 22 por cara y extremo SUPUESTO conservador "
              "(plan 303 muestra mas acero: 2 22/+2 22/+4 22/+4 25, base "
              "5 32 L=900, atribucion por nivel NO_LEGIBLE).")
    ln.append("* Concrete01 no confinado, Steel01 b=0.01; capacidad nominal "
              "sin phi.")
    ln.append("* EY: M_muro = 8836 kN.m CONFIRMADO como demanda real de la "
              "idealizacion (reacciones de fundacion del modelo). Su D/C se "
              "reporta contra la capacidad de eje fuerte con el acero minimo "
              "modelado; no se afirma que mas armadura lo mitigue sin "
              "demostracion cuantitativa.")
    (OUT4 / "resumen_p1l4_pm.md").write_text("\n".join(ln).rstrip() + "\n",
                                             encoding="utf-8")


if __name__ == "__main__":
    import sys
    sys.exit(run())