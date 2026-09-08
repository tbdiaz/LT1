import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches as mpatches
from matplotlib import lines as mlines
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from data import geometria as datos_geom
from data import geometria_irregular as datos_irreg
from data import inventario as datos_inv

PAGE_W = 792.0
PAGE_H = 612.0

RASTER_102 = "/var/folders/5d/kcmfnqr56p12myw6k66m_d080000gn/T/opencode/p001/plan102_hi.png"
RASTER_103 = "/var/folders/5d/kcmfnqr56p12myw6k66m_d080000gn/T/opencode/p001/scan_2017_67-103_p0.png"

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")

EJES_X = datos_geom.ejes_x
EJES_Y = datos_geom.ejes_y
MAIN_X = ["E", "F", "G", "H", "I", "I'"]
MAIN_Y = ["1", "2", "3"]

# coordenadas de planta (modelo) de las ciudades los putos respaldados
WALLS_102 = [("M102_01", 0.755, -3.448), ("M102_02", 4.129, -3.448),
             ("M102_03", 4.074, -14.532)]
WALLS_103 = [("M103_01", 0.749, -3.447), ("M103_02", 4.107, -14.53),
             ("M103_03", 4.156, -3.447)]
VIGAS_3045 = [("V3045_01", 20.974, -18.856), ("V3045_02", 25.767, -18.856)]

RECT_NUCLEO = ("SECTOR NUCLEO E-F", (0.0, -15.2, 6.4, -3.0))
RECT_SUR = ("SECTOR BAJO EJE 3", (15.0, -19.4, 30.0, -16.15))


def pg_full_scale(ruta_raster):
    im = Image.open(ruta_raster)
    return im, im.size[0] / PAGE_W, im.size[1] / PAGE_H


def pm_to_px(xpm, ypm, S, x0, y1):
    return (xpm - x0) * S, (y1 - ypm) * S


def dibujar_plan(ax, ruta_raster, crop, mapeo, titulo):
    m = datos_irreg.MAPEO_PDF[mapeo]
    bx, axx = m["b_x"], m["a_x"]
    by, ay = m["b_y"], m["a_y"]
    x0, x1, y0, y1 = crop
    im, S, Sy = pg_full_scale(ruta_raster)
    assert abs(S - Sy) < 1e-3, "raster no es proporcion de pagina"
    W = int((x1 - x0) * S)
    H = int((y1 - y0) * S)
    px0 = int(x0 * S)
    py0 = int((PAGE_H - y1) * S)
    crop_im = im.crop((px0, py0, px0 + W, py0 + H))
    ax.imshow(crop_im, extent=(0, W, 0, H), origin="upper", aspect="auto")
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)

    def xmodel(X):
        return (bx + axx * X - x0) * S

    def ymodel(Y):
        return (y1 - (by + ay * Y)) * S

    for nombre, X in sorted(EJES_X.items(), key=lambda kv: kv[1]):
        if not (x0 < (bx + axx * X) < x1):
            continue
        ax.axvline(xmodel(X), color="tab:blue", lw=0.8, ls=(0, (4, 3)), alpha=0.35)
        ax.text(xmodel(X), 2, nombre, color="tab:blue", fontsize=8,
                fontweight="bold", ha="center", va="top")
    for nombre, Y in sorted(EJES_Y.items(), key=lambda kv: kv[1]):
        if not (y0 < (by + ay * Y) < y1):
            continue
        ax.axhline(ymodel(Y), color="tab:blue", lw=0.8, ls=(0, (4, 3)), alpha=0.35)
        ax.text(6, ymodel(Y), nombre, color="tab:blue", fontsize=8,
                fontweight="bold", ha="left", va="center")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(titulo, fontsize=10)
    return xmodel, ymodel


def dibujar_modelo(ax, muros, vigas, rects, xlim, ylim, titulo, main_only=True):
    xs = [(n, EJES_X[n]) for n in MAIN_X] if main_only else sorted(EJES_X.items(), key=lambda kv: kv[1])
    ys = [(n, EJES_Y[n]) for n in MAIN_Y] if main_only else sorted(EJES_Y.items(), key=lambda kv: kv[1])
    for n, X in xs:
        ax.axvline(X, color="tab:blue", lw=0.8, ls=(0, (4, 3)), alpha=0.35)
        ax.text(X, ylim[1] + 0.35, n, color="tab:blue", fontsize=8,
                fontweight="bold", ha="center", va="bottom")
    for n, Y in ys:
        ax.axhline(Y, color="tab:blue", lw=0.8, ls=(0, (4, 3)), alpha=0.35)
        ax.text(xlim[0] + 0.25, Y, n, color="tab:blue", fontsize=8,
                fontweight="bold", ha="left", va="center")
    xs_p = [X for _, X in xs]
    ys_p = [Y for _, Y in ys]
    for i in range(len(xs_p) - 1):
        for Y in ys_p:
            ax.plot([xs_p[i], xs_p[i + 1]], [Y, Y], color="0.35", lw=1.4,
                    zorder=3)
    for i in range(len(ys_p) - 1):
        for X in xs_p:
            ax.plot([X, X], [ys_p[i], ys_p[i + 1]], color="0.35", lw=1.4,
                    zorder=3)
    for X in xs_p:
        for Y in ys_p:
            ax.plot([X], [Y], "o", ms=5, mfc="0.9", mec="0.15", zorder=4)
    for m_id, X, Y in muros:
        ax.plot(X, Y, marker=(4, 0, 45), ms=13, mfc="darkorange", mec="black",
                zorder=5, ls="", label="M.H.A. nucleo (pos. respaldada)")
        ax.annotate(f"{m_id}\nPOSICION RESPALDADA\nLONGITUD PENDIENTE",
                    (X, Y), xytext=(X + 0.8, Y + 0.9), fontsize=7, color="black",
                    zorder=6,
                    bbox=dict(boxstyle="round,pad=0.25", fc="lightyellow",
                              ec="darkorange", lw=0.8, alpha=0.95),
                    arrowprops=dict(arrowstyle="-", color="darkorange", lw=0.8))
    for v_id, X, Y in vigas:
        ax.plot(X, Y, marker=(4, 0, 45), ms=11, mfc="deeppink", mec="black",
                zorder=5, ls="", label="V.30/45 borde sur (referencia)")
        ax.annotate(f"{v_id}\n(pos. respaldada)", (X, Y),
                    xytext=(X + 0.8, Y - 1.3), fontsize=7, color="black",
                    zorder=6,
                    bbox=dict(boxstyle="round,pad=0.25", fc="mistyrose",
                              ec="deeppink", lw=0.8, alpha=0.95),
                    arrowprops=dict(arrowstyle="-", color="deeppink", lw=0.8))
    for label, (x0, y0, x1, y1) in rects:
        ax.add_patch(mpatches.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False,
                                        ec="0.2", lw=1.4, ls="--", zorder=4))
        ax.text((x0 + x1) / 2, y0 - 0.55, label, fontsize=8, fontweight="bold",
                ha="center", va="top", zorder=6, color="0.2")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_title(titulo, fontsize=10)
    return ax


def hacer_figura(plano_num, ruta_raster, crop, mapeo, muros, vigas, rects,
                 xlim, ylim, titulo_plan, titulo_modelo, notas, ruta_out,
                 figsize, main_only):
    fig, (ax_plan, ax_modelo) = plt.subplots(1, 2, figsize=figsize,
                                             constrained_layout=True)
    dibujar_plan(ax_plan, ruta_raster, crop, mapeo, titulo_plan)
    ax_modelo = dibujar_modelo(ax_modelo, muros, vigas, rects, xlim, ylim,
                               titulo_modelo, main_only)
    plano = {}
    for hnd, lb in zip(*ax_modelo.get_legend_handles_labels()):
        if lb and lb not in plano:
            plano[lb] = hnd
    if not main_only:
        plano["Ejes (grilla)"] = mlines.Line2D([], [], color="tab:blue",
                                              ls=(0, (4, 3)))
    ax_modelo.legend(handles=list(plano.values()), labels=list(plano.keys()),
                     loc="upper left", fontsize=7, framealpha=0.9)
    fig.suptitle(
        f"CONTROL VISUAL DE CORRELACION PLANO ↔ MODELO · LT1\n"
        f"{notas}",
        fontsize=11, fontweight="bold")
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(ruta_out, dpi=150)
    plt.close(fig)
    print(f"  [OK] {os.path.basename(ruta_out)}")


def main():
    N = datos_geom.niveles_z
    net_102 = datos_inv.convencion_plano("102", "principal")
    sub_102 = datos_inv.convencion_plano("102", "sub_plano")
    net_103 = datos_inv.convencion_plano("103", "principal")

    # ---- PLANO 102 ----
    hacer_figura(
        102,
        RASTER_102,
        (20.0, 560.0, 410.0, 592.0),
        "102",
        WALLS_102,
        VIGAS_3045,
        [RECT_NUCLEO, RECT_SUR],
        (-3.0, 46.0),
        (-21.0, 2.0),
        "PLANO 102 (vista principal PLANTA CIELO PISO 2°) · raster pág.0 @4x, "
        "recorte área planta estructural",
        f"MODELO LT1 XY · PISO_2 (z={N['PISO_2']:+.2f} m) · esqueleto retícula "
        "principal PISO_2 + referencias irregulares (M.H.A., V.30/45)",
        "CONVENCION NIVELES: vista principal folio 102 -> PISO_2 (z=3.91). Los M102 "
        "y V3045 pertenecen a ESTA vista (PISO_2). El folio incluye además el "
        "SUB-PLANO PLANTA CIELO PISO 3° (NIVEL SUPERIOR LOSA=7.87 m = PISO_3), que "
        f"es el origen de la retícula del bloque 1 del modelo en PISO_3 (z={N['PISO_3']:+.2f} m). "
        "Fuente única: data/inventario.CONVENCION_NIVELES. M.H.A. = SOLO puntos "
        "(POSICION RESPALDADA / LONGITUD PENDIENTE); no se crearon nodos ni elementos.",
        os.path.join(OUT_DIR, "correlacion_plano102_modelo.png"),
        (20, 9),
        main_only=False,
    )

    # ---- PLANO 103 ----
    hacer_figura(
        103,
        RASTER_103,
        (240.0, 700.0, 190.0, 430.0),
        "103",
        WALLS_103,
        [],
        [RECT_NUCLEO],
        (-3.0, 46.0),
        (-18.0, 2.0),
        "PLANO 103 (PLANTA CIELO PISO 4°) · raster pág.0, recorte área planta estructural",
        f"MODELO LT1 XY · PISO_4 (z={N['PISO_4']:+.2f} m) · esqueleto retícula "
        "principal + referencias irregulares (M.H.A.)",
        "PLANTA CIELO PISO 4° = LOSA SUPERIOR ≈ 11.83 m (= PISO_4, anotación explícita "
        "del rótulo; ver data/inventario.CONVENCION_NIVELES). Continuidad con 102: mismo "
        "núcleo E-F (M103_01/M103_02/M103_03). M.H.A. = SOLO puntos (POSICION RESPALDADA "
        "/ LONGITUD PENDIENTE).",
        os.path.join(OUT_DIR, "correlacion_plano103_modelo.png"),
        (20, 8),
        main_only=True,
    )
    print("  correlaciones listas en:", os.path.abspath(OUT_DIR))


if __name__ == "__main__":
    main()