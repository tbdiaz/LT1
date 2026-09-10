# -*- coding: utf-8 -*-
"""SEMANA 3 - PARTE D: capacidad de la seccion 70x70 de columna LT1 (tag 111000).

Analisis SOLO de seccion (fiber section) en OpenSeesPy sobre la columna LT1
tag 111000 del modelo combinado. Seccion "P. 70x70" (outputs/unity/
modelo_lt1.json) y armadura real 16 barras longitudinales de 22 mm
(outputs/reinforcement/armadura_lt1_columnas.csv).

Los planos LT1 (2017_67-*) NO documentan ni el hormigon (f'c), ni el acero
(fy), ni el recubrimiento de columnas; el plano general 2017_67-000 solo
remite los recubrimientos a la E.T.O.G., documento no disponible en el
proyecto. Por lo tanto TODO lo siguiente son SUPUESTOS DE MODELACION
explicitos y marcados como tales, NO datos reales del proyecto:

  [SUPUESTO] f'c            = 30 MPa  = 30000 kPa
  [SUPUESTO] fy             = 420 MPa = 420000 kPa   (Es = 200 GPa)
  [SUPUESTO] distancia adoptada de 4 cm desde la CARA del hormigon al EJE
             de las barras (NO es recubrimiento libre a la superficie de la
             barra; no se modelan estribos).
  [SUPUESTO] distribucion   = 16 barras Φ22 simetricas alrededor del
             perimetro (4 esquinas + 3 por cara, simetria respecto de ambos
             ejes centroidales).
  [SUPUESTO] hormigon no confinado Concrete01 (fpc=-30000 kPa, epsc0=-0.002,
             fpcu=-6000 kPa, epsscu=-0.006). La seccion de hormigon se
             discretiza en fibras sobre el parche BRUTO 0.70x0.70 (no se
             descuenta el area de las barras; practica usual en fibras).

El modulo ejecuta SOLO la Parte D: materiales uniaxiales, fiber section,
discretizacion, 16 barras, figura de la seccion, analisis momento-curvatura
M-phi (esquema canonico de OpenSees "Moment Curvature Example": carga axial
constante + momento de referencia lineal, DisplacementControl sobre el GDL de
rotacion; el factor de carga ES el momento), grafico M-phi, primeros puntos
del diagrama P-M (P = 0, M ~ 0 de compresion pura, y dos o mas puntos
intermedios), grafico P-M y resultados en outputs/semana03/capacity/.

NO modifica la Parte A, B ni C de Semana 3, ni run_combined.py; escribe SOLO
dentro de COMBINADO/outputs/semana03/capacity/.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import openseespy.opensees as ops

ROOT = Path(__file__).resolve().parents[2]
COMB = ROOT / "COMBINADO"
OUT_D = COMB / "outputs" / "semana03" / "capacity"

# ---------------------------------------------------------------------------
# Columna LT1 tag 111000 (seccion "P. 70x70" del modelo unificado)
# ---------------------------------------------------------------------------
COLUMN_TAG = 111000
B_CM = 70.0                       # ancho seccion      (0.70 m)
H_CM = 70.0                       # alto seccion       (0.70 m)

# ---------------------------------------------------------------------------
# SUPUESTOS DE MODELACION (los planos NO los documentan)
# ---------------------------------------------------------------------------
FC_MPA = 30.0        # [SUPUESTO] f'c  = 30 MPa
FY_MPA = 420.0       # [SUPUESTO] fy   = 420 MPa
ES_GPA = 200.0       # [SUPUESTO] modulo de elasticidad del acero
STRAIN_HARDEN_B = 0.01   # [SUPUESTO] pendiente de endurecimiento Steel01

N_BARS = 16          # armadura REAL (planos): 16 barras longitudinales
DIAM_MM = 22.0       # armadura REAL (planos): diametro 22 mm
COVER_M = 0.04       # [SUPUESTO] distancia adoptada: cara -> EJE de la barra

FC_KPA = FC_MPA * 1000.0
FY_KPA = FY_MPA * 1000.0
ES_KPA = ES_GPA * 1.0e6
A_BAR = math.pi * (0.011) ** 2       # seccion de una barra Φ22 [m2]

# Materiales uniaxiales (tags fijos)
MAT_CONC = 1
MAT_STEEL = 2
SEC_TAG = 10

# Discretizacion del parche de hormigon (fibras)
NY = 32
NZ = 32

# Analisis M-phi
MAX_KAPPA = 0.10          # curvatura maxima [rad/m]
N_INCR = 250              # incrementos de curvatura
# Cargas axiales (compresion = valor negativo, convencion OpenSees) para las
# ramas M-phi; cubren P=0, dos+ puntos intermedios y las cercanas a P0.
AXIAL_CASES = [0.0, -2500.0, -5000.0, -7500.0, -10000.0]


def bar_positions():
    """16 barras Φ22 simetricas alrededor del perimetro (SUPUESTO)."""
    yc = 0.35 - COVER_M
    zc = 0.35 - COVER_M
    pos = []
    for y in (-yc, yc):                 # 4 esquinas
        for z in (-zc, zc):
            pos.append((y, z))
    for y in (-0.155, 0.0, 0.155):      # 3 intermedias en c/u de las caras
        pos.append((y, zc))
        pos.append((y, -zc))
    for z in (-0.155, 0.0, 0.155):
        pos.append((yc, z))
        pos.append((-yc, z))
    assert len(pos) == N_BARS
    assert len(set(pos)) == N_BARS
    for (y, z) in pos:                   # simetria respecto de ambos ejes
        assert (-y, z) in set(pos) and (y, -z) in set(pos)
    return pos


def _build_model():
    """Modelo 2D minimo: 2 nodos + zeroLengthSection con la fiber section."""
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    ops.uniaxialMaterial("Concrete01", MAT_CONC,
                         -FC_KPA, -0.002, -0.2 * FC_KPA, -0.006)
    ops.uniaxialMaterial("Steel01", MAT_STEEL, FY_KPA, ES_KPA,
                         STRAIN_HARDEN_B)
    ops.section("Fiber", SEC_TAG)
    ops.patch("rect", MAT_CONC, NY, NZ, -0.35, -0.35, 0.35, 0.35)
    for (y, z) in bar_positions():
        ops.fiber(y, z, A_BAR, MAT_STEEL)
    ops.node(1, 0.0, 0.0)
    ops.node(2, 0.0, 0.0)
    ops.fix(1, 1, 1, 1)                  # nodo 1 fijo
    ops.fix(2, 0, 1, 0)                  # nodo 2: solo axial + rotacion
    ops.element("zeroLengthSection", 1, 1, 2, SEC_TAG)
    ops.constraints("Plain")
    ops.numberer("Plain")
    ops.system("SparseGeneral", "-piv")
    ops.test("EnergyIncr", 2.0e-8, 60, 2)
    ops.algorithm("Newton")


def moment_curvature(P_kN, max_kappa=MAX_KAPPA, num_incr=N_INCR):
    """M-phi a carga axial CONSTANTE (esquema canonico OpenSees).

    - patron 1: carga axial P con timeSeries 'Constant' (no escala con el
      factor de carga).
    - patron 2: momento de referencia 1.0 con timeSeries 'Linear'; en
      DisplacementControl el factor de carga ES el momento resultante.
    Devuelve lista (kappa[rad/m], M[kN·m]) de la rama ascendente hasta el
    pico (capacidad), que es el punto a usar en el diagrama P-M.
    """
    _build_model()
    ops.timeSeries("Constant", 1)
    ops.pattern("Plain", 1, 1)
    ops.load(2, P_kN, 0.0, 0.0)
    ops.integrator("LoadControl", 0.0)
    ops.analysis("Static")
    rc = ops.analyze(1)
    if rc != 0:
        raise RuntimeError(
            f"CAPACIDAD: paso de carga axial P={P_kN} no convergio (rc={rc}).")

    ops.timeSeries("Linear", 2)
    ops.pattern("Plain", 2, 2)
    ops.load(2, 0.0, 0.0, 1.0)           # [SUPUESTO] momento de referencia
    ops.integrator("DisplacementControl", 2, 3, max_kappa / num_incr)
    rows = []
    for _ in range(num_incr):
        rc = ops.analyze(1)
        if rc != 0:
            break                        # tras el pico: fin de la rama
        kappa = float(ops.nodeDisp(2, 3))
        m = float(ops.getTime())         # factor de carga = momento
        if m < 0.0:
            break                        # solucion espuria post-pico
        rows.append((kappa, m))
    if not rows:
        raise RuntimeError(
            f"CAPACIDAD: M-phi vacia para P={P_kN}. INPUT_REQUIRED.")
    # rama ascendente hasta el pico (capacidad de la seccion)
    ipeak = max(range(len(rows)), key=lambda i: rows[i][1])
    return rows[:ipeak + 1]


def axial_push(max_incr=240):
    """Compresion PURA (M ~ 0): capacidad axial P0 de la seccion.

    DisplacementControl sobre el GDL axial con momento de referencia nulo; por
    simetria de las barras no se desarrolla momento. El pico |N| es P0.
    """
    _build_model()
    ops.timeSeries("Linear", 3)
    ops.pattern("Plain", 3, 3)
    ops.load(2, -1.0, 0.0, 0.0)          # referencia axial unitaria (compresion)
    ops.integrator("DisplacementControl", 2, 1, -2.0e-5)
    ops.analysis("Static")
    p0 = 0.0
    m_abs_max = 0.0
    for _ in range(max_incr):
        rc = ops.analyze(1)
        if rc != 0:
            break
        n, m = tuple(ops.eleResponse(1, "basicForces"))[:2]
        if n < p0:
            p0 = n                       # pico de compresion (mas negativo)
        m_abs_max = max(m_abs_max, abs(m))
    if p0 >= 0.0:
        raise RuntimeError("CAPACIDAD: compresion pura sin pico (P0 no "
                           "detectado). INPUT_REQUIRED.")
    return p0, m_abs_max


def figure_section():
    """Figura de la seccion: fibras de hormigon, barras y cotas."""
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    ax.add_patch(plt.Rectangle((-0.35, -0.35), 0.70, 0.70,
                               fill=True, facecolor="#e6e6e6",
                               edgecolor="black", lw=1.5, zorder=1))
    for i in range(1, NY):               # fibras (lineas de la discretizacion)
        y = -0.35 + i * (0.70 / NY)
        ax.plot([y, y], [-0.35, 0.35], color="#bfbfbf", lw=0.5, zorder=2)
    for j in range(1, NZ):
        z = -0.35 + j * (0.70 / NZ)
        ax.plot([-0.35, 0.35], [z, z], color="#bfbfbf", lw=0.5, zorder=2)
    for (y, z) in bar_positions():       # barras Φ22
        ax.add_patch(plt.Circle((y, z), 0.011, fill=True, fc="tab:orange",
                                ec="black", lw=0.8, zorder=3))
    ax.add_patch(plt.Rectangle((-0.31, -0.31), 0.62, 0.62, fill=False,
                               edgecolor="tab:blue", lw=1.2, ls="--", zorder=4))
    ax.annotate("", xy=(-0.35, -0.49), xytext=(0.35, -0.49),
                arrowprops=dict(arrowstyle="<->", lw=1.0))
    ax.text(0.0, -0.53, "70 cm", ha="center", va="top")
    ax.annotate("", xy=(-0.49, -0.35), xytext=(-0.49, 0.35),
                arrowprops=dict(arrowstyle="<->", lw=1.0))
    ax.text(-0.53, 0.0, "70 cm", ha="center", va="center", rotation=90)
    ax.annotate("", xy=(-0.45, 0.31), xytext=(-0.45, 0.35),
                arrowprops=dict(arrowstyle="<->", lw=1.2, color="tab:blue"))
    ax.text(-0.47, 0.33, "4 cm", ha="right", va="center", fontsize=8,
            color="tab:blue")
    ax.text(-0.47, 0.44, "cara->eje 4 cm (SUPUESTO)", ha="right", fontsize=8,
            color="tab:blue")
    ax.set_xlim(-0.72, 0.48)
    ax.set_ylim(-0.62, 0.56)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_title("Columna LT1 tag 111000 - 70x70 cm | 16 Φ22\n"
                 "(f'c, fy, dist. cara->eje y distribucion = SUPUESTOS)",
                 fontsize=10)
    import matplotlib.patches as mpatches
    ax.legend(handles=[mpatches.Patch(facecolor="tab:orange",
                                       edgecolor="black",
                                       label="Φ22 (SUPUESTO)"),
                       plt.Line2D([0], [0], color="tab:blue", ls="--",
                                  label="dist. adoptada 4 cm cara->eje "
                                         "(SUPUESTO)")],
              loc="lower right", fontsize=8)
    fig.tight_layout()
    out = OUT_D / "fiber_section.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def run_all():
    """Ejecuta la Parte D completa y escribe los resultados."""
    OUT_D.mkdir(parents=True, exist_ok=True)

    # --- 5/6/7: M-phi a carga axial constante (carga P = 0 y 4 compresiones)
    mc_rows = []
    peak_points = []                     # (P, M_peak) para el diagrama P-M
    for P in AXIAL_CASES:
        curve = moment_curvature(P)
        kappa_pk, m_pk = curve[-1]
        peak_points.append((P, m_pk))
        mc_rows.extend([dict(caso=f"P={P:.0f}", P_kN=P,
                             kappa_rad_m=k, M_kN_m=m) for (k, m) in curve])
        print(f"  M-phi  P={P:8.0f} kN | kappa_pk={kappa_pk:.5f} rad/m | "
              f"M_pk={m_pk:9.2f} kN·m")
    df_mc = pd.DataFrame(mc_rows)
    df_mc["kappa_rad_m"] = df_mc["kappa_rad_m"].round(8)
    df_mc["M_kN_m"] = df_mc["M_kN_m"].round(6)
    df_mc.to_csv(OUT_D / "moment_curvature.csv", index=False)

    # --- figura de la seccion
    fiber_png = figure_section()
    print(f"  seccion -> {fiber_png.relative_to(ROOT)}")

    # --- grafico M-phi
    fig, ax = plt.subplots(figsize=(7, 5))
    for P, grp in df_mc.groupby("P_kN"):
        ax.plot(grp["kappa_rad_m"], grp["M_kN_m"],
                label=f"P = {P:.0f} kN (SUPUESTO de analisis)")
    ax.set_xlabel("Curvatura  phi [rad/m]")
    ax.set_ylabel("Momento  M [kN·m]")
    ax.set_title("Momento-Curvatura - columna LT1 111000 (70x70 cm, 16 Φ22)\n"
                 "f'c=30 MPa, fy=420 MPa (SUPUESTOS DE MODELACION)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    mc_png = OUT_D / "moment_curvature.png"
    fig.savefig(mc_png, dpi=150)
    plt.close(fig)
    print(f"  grafico -> {mc_png.relative_to(ROOT)}")

    # --- 8: punto M ~ 0 (compresion pura P0)
    p0, m_abs_max = axial_push()
    print(f"  compresion pura P0 = {p0:9.2f} kN | |M|max = {m_abs_max:.3e}")

    # --- diagrama P-M: P=0, P0 (M~0) y los intermedios
    pm = [
        dict(punto="P=0 (flexion pura)", tipo="PURE_FLEXURE",
             P_kN=0.0, M_kN_m=peak_points[0][1]),
    ]
    for (P, m) in peak_points[1:]:
        pm.append(dict(punto=f"P={P:.0f} kN (intermedio)", tipo="INTERMEDIO",
                       P_kN=P, M_kN_m=m))
    pm.append(dict(punto="P0 (compresion pura)", tipo="PURE_COMPRESSION",
                   P_kN=p0, M_kN_m=0.0))
    df_pm = pd.DataFrame(pm)
    df_pm["M_kN_m"] = df_pm["M_kN_m"].round(6)
    df_pm.to_csv(OUT_D / "pm_interaction.csv", index=False)
    print(df_pm.to_string(index=False))

    # --- grafico P-M (compresion positiva hacia arriba)
    fig, ax = plt.subplots(figsize=(7, 5))
    P_plot = df_pm["P_kN"].abs()
    ax.plot(df_pm["M_kN_m"], P_plot, "-o", color="tab:red",
            label="Capacidad P-M (SUPUESTOS)")
    for _, r in df_pm.iterrows():
        ax.annotate(r["punto"], (r["M_kN_m"], abs(r["P_kN"])),
                    textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.set_xlabel("Momento  M [kN·m]")
    ax.set_ylabel("Carga axial  P (compresion) [kN]")
    ax.set_title("Interaccion P-M - columna LT1 111000 (70x70 cm, 16 Φ22)\n"
                 "f'c=30 MPa, fy=420 MPa (SUPUESTOS DE MODELACION)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    pm_png = OUT_D / "pm_interaction.png"
    fig.savefig(pm_png, dpi=150)
    plt.close(fig)
    print(f"  grafico -> {pm_png.relative_to(ROOT)}")

    write_resumen(df_mc, df_pm, fiber_png, mc_png, pm_png, p0, m_abs_max)
    return 0


def write_resumen(df_mc, df_pm, fiber_png, mc_png, pm_png, p0, m_abs_max):
    """Resumen en outputs/semana03/capacity/resumen_capacity.md."""
    as_tot = N_BARS * A_BAR
    rho = as_tot / (0.70 * 0.70)
    p0_code = 0.85 * FC_KPA * (0.49 - as_tot) + FY_KPA * as_tot
    mc_top = df_mc.sort_values("M_kN_m", ascending=False).iloc[0]
    lin = [
        "# SEMANA 3 - PARTE D: capacidad de columna LT1 (fiber section)",
        "",
        "Analisis SOLO de seccion con OpenSeesPy. No se modificaron la "
        "Parte A, B ni C, ni `run_combined.py`.",
        "",
        "## Columna usada",
        "",
        f"- **LT1 tag `{COLUMN_TAG}`** (etiqueta del modelo combinado; las 90 "
        "columnas LT1 tienen la misma seccion y armadura, ver "
        "`outputs/reinforcement/armadura_lt1_columnas.csv`).",
        f"- Dimensiones: **70 x 70 cm** (seccion `P. 70x70` en "
        "`outputs/unity/modelo_lt1.json`).",
        f"- Armadura REAL (planos): **16 barras longitudinales Φ22 mm** "
        f"(As = {as_tot:.6f} m², rho = {rho:.4f}); fuente "
        "`outputs/reinforcement/armadura_lt1_columnas.csv` (bar_count=16, "
        "diameter_mm=22, status EXACT, "
        "source USER_CONFIRMED_DRAWING_DATA).",
        "",
        "## SUPUESTOS DE MODELACION (los planos NO los documentan)",
        "",
        "Los planos LT1 (2017_67-000/001, hojas de plantas y de columnas) no "
        "indican f'c, fy ni recubrimiento; el plano general 2017_67-000 "
        "remite los recubrimientos a la E.T.O.G., documento no disponible. "
        "Por eso la Parte D se resuelve con los siguientes supuestos, que NO "
        "son datos reales del proyecto:",
        "",
        "| concepto | valor | caracter |",
        "|---|---|---|",
        "| f'c (hormigon) | 30 MPa = 30000 kPa | **SUPUESTO** |",
        "| fy (acero) | 420 MPa = 420000 kPa | **SUPUESTO** |",
        "| Es / endurecimiento acero | 200 GPa, b = 0.01 | **SUPUESTO** |",
        "| distancia adoptada de 4 cm desde la cara al EJE de las barras | 0.04 m | **SUPUESTO** (no es recubrimiento libre) |",
        "| distribucion de las 16 Φ22 | 4 esquinas + 3 por cara, simetrica "
        "en ambos ejes | **SUPUESTO** (los planos no la definen) |",
        "| hormigon | Concrete01 no confinado (fpc=-30000, epsc0=-0.002, "
        "fpcu=-6000 kPa, epsscu=-0.006) | **SUPUESTO** (sin estribos "
        "documentados) |",
        "| discretizacion | parche bruto 0.70x0.70 m en fibras (32x32); no "
        "se descuenta el area de acero | **SUPUESTO** (practica usual) |",
        "",
        "## Metodo",
        "",
        "Fiber section con elementos "
        "`Concrete01`/`Steel01` y `zeroLengthSection` (esquema canonico "
        "OpenSees 'Moment Curvature Example'): carga axial constante "
        "(timeSeries Constant) + momento de referencia unitario (Linear) y "
        "`DisplacementControl` sobre el GDL de rotacion; el factor de carga "
        "resultante es el momento. Para cada carga axial P se conserva la "
        "rama ascendente hasta el pico (capacidad). La compresion pura P0 se "
        "obtiene con un empuje axial (M ~ 0).",
        "",
        "## M-phi",
        "",
        "| P (kN) | kappa_pico (rad/m) | M_pico (kN·m) |",
        "|---|---|---|",
    ]
    for P, grp in df_mc.groupby("P_kN"):
        last = grp.iloc[-1]
        lin.append(f"| {last['P_kN']:.0f} | {last['kappa_rad_m']:.5f} | "
                   f"{last['M_kN_m']:.2f} |")
    lin += [
        f"- Maximo entre las ramas evaluadas: **M = {mc_top['M_kN_m']:.2f} "
        f"kN·m** a P = {mc_top['P_kN']:.0f} kN.",
        "- Interpretacion breve: la capacidad en flexion sube con la "
        "compresion axial hasta la zona balanceada (max ~ 1658 kN·m cerca de "
        "P = -5000 kN) y baja a partir de ahi hacia la compresion pura; "
        "curvas completas en `moment_curvature.csv`.",
        "",
        "## P-M (primeros puntos)",
        "",
        "| punto | P (kN) | M (kN·m) |",
        "|---|---|---|",
    ]
    for _, r in df_pm.iterrows():
        lin.append(f"| {r['punto']} | {r['P_kN']:.2f} | {r['M_kN_m']:.2f} |")
    lin += [
        f"- P = 0 (flexion pura): M = {df_pm.iloc[0]['M_kN_m']:.2f} kN·m.",
        f"- M ~ 0 (compresion pura): P0 = {p0:.2f} kN, |M|max = "
        f"{m_abs_max:.3e} kN·m en el empuje.",
        f"- Referencia de diseño (0.85·f'c·(Ag-As) + fy·As) = "
        f"{p0_code:.2f} kN: el valor de fibras ({p0:.2f} kN) usa el "
        "material real (sin el factor 0.85 del codigo), por eso difiere.",
        "- Interpretacion breve: el diagrama muestra el par (M, P) de "
        "capacidad; todo M supera 0 solo bajo compresion axial (la seccion "
        "no resiste traccion neta), y la maxima compresion ocurre con M "
        "practicamente nulo. Los puntos dependen directamente de los "
        "SUPUESTOS f'c, fy, distancia cara->eje y distribucion.",
        "",
        "## Supuestos vs. datos reales",
        "",
        "- Datos REALES del proyecto: seccion 70x70 y 16 Φ22 (planos).",
        "- SUPUESTOS: f'c = 30 MPa, fy = 420 MPa, distancia adoptada de 4 cm "
        "desde la cara al eje de las barras y distribucion de las 16 barras. " 
        "Si se confirman otros valores (E.T.O.G. o memoria de calculo), solo "
        "cambian las constantes `FC_KPA`, `FY_KPA`, `COVER_M`/"
        "`bar_positions()` y se reejecuta este modulo.",
        "",
        "## Archivos",
        "",
        "- `fiber_section.png` - seccion con fibras, barras y cotas.",
        "- `moment_curvature.csv` / `moment_curvature.png` - ramas M-phi.",
        "- `pm_interaction.csv` / `pm_interaction.png` - primeros puntos P-M.",
    ]
    (OUT_D / "resumen_capacity.md").write_text("\n".join(lin).rstrip() + "\n",
                                               encoding="utf-8")
    print(f"  resumen -> {(OUT_D / 'resumen_capacity.md').relative_to(ROOT)}")


def main():
    print("=" * 76)
    print("SEMANA 3 - PARTE D | CAPACIDAD DE SECCION - columna LT1 "
          f"tag {COLUMN_TAG} (70x70 cm, 16 Φ22)")
    print("f'c=30 MPa / fy=420 MPa / dist. adoptada 4 cm cara->eje / distribucion: "
          "SUPUESTOS DE MODELACION")
    print("=" * 76)
    rc = run_all()
    print("\nSalidas:")
    for p in sorted(OUT_D.glob("*")):
        print("  ", p.relative_to(ROOT), "->", p.stat().st_size)
    return rc


if __name__ == "__main__":
    import sys
    sys.exit(main())