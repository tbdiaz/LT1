#!/usr/bin/env python3
"""Comparación visual (inspección) Bloque 1: modelo PISO_3 vs plano 102.

SOLO VISUALIZACIÓN. No lee coordenadas estructurales de píxeles; la
transformación plano->modelo se usa exclusivamente para dibujar la
superposición. No modifica ningún archivo estructural.

Genera:
  outputs/comparacion_plano102_modelo.png   (plan | modelo, lado a lado)
  outputs/superposicion_plano102_modelo.png (plano de fondo + modelo encima,
                                             sólo si el ajuste es fiable)
"""
import contextlib
import io
import os

import numpy as np
import pymupdf

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

_DIR = os.path.dirname(os.path.abspath(__file__))
_PROY = os.path.dirname(_DIR)
_PDF = os.path.join(_PROY, "planos", "2017_67-102-Model.pdf")
_SAL = os.path.join(_PROY, "outputs")
MODELO = "src/modelo_lt1.py"

MODEL_X = ["E", "F", "G", "H", "I", "I'"]
MODEL_Y = ["1", "2", "3"]
XM = np.array([0.0, 10.0, 20.0, 30.0, 40.0, 42.5])
YM = np.array([0.0, -8.9, -16.15])

MAX_RESIDUAL_M = 0.6   # si el ajuste supera esto, no se dibuja superposición


def runpy_run_path():
    import runpy
    return runpy.run_path(os.path.join(_PROY, MODELO), run_name="__comparar_102__")


def cargar_modelo():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return runpy_run_path()


def separar_plantas(page):
    """Devuelve clip de la planta superior (PLANTA CIELO PISO 2, y<=214)."""
    r = page.rect
    return pymupdf.Rect(r.x0, 4.0, r.x1, 214.0), pymupdf.Rect(r.x0, 214.0, r.x1, r.y1)


def render_clip(page, clip, dpi=200):
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return img[..., :3] if pix.n >= 3 else img


def detectar_lineas_grilla(img, umbral_trazo=140):
    """Proyecciones de tinta -> líneas verticales/horizontales candidatas (px)."""
    luz_clara = img.max(axis=2).astype(np.int16)
    tinta = (luz_clara < umbral_trazo).astype(np.int16)
    H, W = tinta.shape

    colsum = tinta.sum(axis=0)
    rowsum = tinta.sum(axis=1)

    def picos(serie, minv, radio=3):
        out = []
        for i in range(len(serie)):
            if serie[i] < minv:
                continue
            v = min(radio, i)
            w = min(radio, len(serie) - 1 - i)
            if serie[i] == max(serie[i - v:i + w + 1]):
                out.append((i, int(serie[i])))
        return out

    vp = picos(colsum, int(H * 0.25))
    hp = picos(rowsum, int(W * 0.25))
    return vp, hp, colsum, rowsum


def ajustar_transformacion(vxs_px, hys_px, px_por_pt, dpi):
    """Ajusta modelo(m)->píxel con patrón de separaciones (10,10,10,10,2.5) y
    (8.9,7.25). Devuelve (transformación m->px, residual_m, info) o None."""
    from itertools import combinations

    pts = px_por_pt / dpi * 72.0   # px por pt (factor imagen)
    # vxs_px ya en px; convertir a pt
    vxs = np.array(vxs_px) / px_por_pt
    hys = np.array(hys_px) / px_por_pt

    mejor = None
    best_err = 1e18
    for si in combinations(range(len(vxs)), 6):
        xp = vxs[np.array(si)]
        gaps = np.diff(xp)
        if gaps.min() <= 0:
            continue
        ratio = gaps / np.array([10.0, 10.0, 10.0, 10.0, 2.5])
        if ratio.max() / ratio.min() > 1.05:
            continue
        for tj in combinations(range(len(hys)), 3):
            yp = hys[np.array(tj)]
            gy = np.diff(yp)
            if gy.min() <= 0:
                continue
            ry = gy / np.array([8.9, 7.25])
            if ry.max() / ry.min() > 1.05:
                continue
            sy = float(np.median(ry))
            if not (0.85 < sy / np.median(ratio) < 1.18):
                continue
            tx = np.polyfit(xp, XM, 1)
            ty = np.polyfit(yp, YM, 1)
            rx = np.abs(np.polyval(tx, xp) - XM)
            ry = np.abs(np.polyval(ty, yp) - YM)
            err = float(np.sqrt(np.mean(np.concatenate([rx, ry]) ** 2)))
            if err < best_err:
                best_err = err
                mejor = (tx, ty, si, tj, rx, ry)
    if mejor is None:
        return None
    tx, ty, si, tj, rx, ry = mejor
    escala_pt_m = float(np.median(
        np.diff(vxs[np.array(si)]) / np.array([10.0, 10.0, 10.0, 10.0, 2.5])))
    vxs_usados = set(vxs[np.array(si)])
    info = {
        "seis_x": [round(float(vxs[i]), 2) for i in si],
        "tres_y": [round(float(hys[j]), 2) for j in tj],
        "rx_m": np.round(rx, 4).tolist(),
        "ry_m": np.round(ry, 4).tolist(),
        "escala_pt_m": escala_pt_m,
        "restantes_x": sorted(round(float(v), 2) for v in vxs if v not in vxs_usados),
    }
    return (tx, ty), best_err, info


def modelo_datos(ns):
    nodos = ns["nodos"]
    ejes_x = ns["ejes_x"]
    ejes_y = ns["ejes_y"]
    z3 = ns["niveles_z"]["PISO_3"]
    vigas = [v for g in ns["vigas_por_nivel"].values() for v in g
             if v["nodo_i"] in nodos and v["nodo_j"] in nodos]
    cols = [c for g in ns["columnas_por_nivel"].values() for c in g
            if c["nodo_inferior"] in nodos and c["nodo_superior"] in nodos]
    nodos3 = [(t, x, y) for t, (x, y, z) in nodos.items() if abs(z - z3) < 1e-9]
    return nodos, ejes_x, ejes_y, vigas, cols, nodos3


def dibujar_modelo(ax, nodos, vigas, cols, nodos3, etiquetas=True, invertir=True):
    for v in vigas:
        (xi, yi, _), (xj, yj, _) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
        ax.plot([xi, xj], [yi, yj], color="tab:blue", lw=2.2)
    for c in cols:
        (xi, yi, _) = nodos[c["nodo_inferior"]]
        ax.plot([xi], [yi], marker="s", ms=10, color="tab:green",
                markeredgecolor="black", lw=1)
    for t, x, y in nodos3:
        ax.plot([x], [y], marker="o", ms=5, color="crimson")
    ax.set_aspect("equal")
    if invertir:
        ax.invert_yaxis()


def main():
    os.makedirs(_SAL, exist_ok=True)
    doc = pymupdf.open(_PDF)
    page = doc[0]

    clip_sup, clip_inf = separar_plantas(page)
    dpi = 200
    img_sup = render_clip(page, clip_sup, dpi=dpi)
    H, W = img_sup.shape[:2]
    px_por_pt = dpi / 72.0

    sup_sol = None

    vp, hp, colsum, rowsum = detectar_lineas_grilla(img_sup)
    vxs_px = [p[0] for p in vp]
    hys_px = [p[0] for p in hp]
    print("CONTROL GEOMETRICO VISUAL BLOQUE 1 - PLANO 102")
    print(f"  clip planta superior (pt): {clip_sup}  ->  imagen {W}x{H} px @ {dpi} dpi")
    print(f"  picos verticales (px): {vxs_px}")
    print(f"  picos horizontales(px): {hys_px}")

    ajuste = ajustar_transformacion(vxs_px, hys_px, px_por_pt, dpi)
    ns = cargar_modelo()
    nodos, ejes_x, ejes_y, vigas, cols, nodos3 = modelo_datos(ns)
    print(f"  modelo: {len(nodos)} nodos, {len(vigas)} vigas, {len(cols)} columnas "
          f"(PISO_3 z={ns['niveles_z']['PISO_3']} m)")

    # ---- 1) Comparación lado a lado (no requiere alineación) -------------
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(17, 9),
                                 gridspec_kw={"width_ratios": [1.05, 1]})
    a1.imshow(img_sup, interpolation="nearest")
    a1.set_title(f"PLANO 2017_67-102 - PLANTA CIELO PISO 2 (recorte {W}x{H} px)")
    a1.set_xticks([]); a1.set_yticks([])

    dibujar_modelo(a2, nodos, vigas, cols, nodos3)
    relim = (min(ejes_x.values()), max(ejes_x.values()),
             min(ejes_y.values()), max(ejes_y.values()))
    a2.set_xlim(relim[0], relim[1]); a2.set_ylim(relim[2], relim[3])
    for ex, x in ejes_x.items():
        a2.text(x, 0.6, ex, fontsize=9, ha="center")
    for ey, y in ejes_y.items():
        a2.text(0.7, y, ey, fontsize=9, va="center")
    a2.set_title(f"MODELO LT1 - PISO_3 (z={ns['niveles_z']['PISO_3']} m) - {len(nodos3)} nodos")
    a2.set_xlabel("X [m]"); a2.set_ylabel("Y [m]")
    fig.suptitle("CONTROL GEOMETRICO BLOQUE 1 - plano 102 vs modelo PISO_3", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    ruta_comp = os.path.join(_SAL, "comparacion_plano102_modelo.png")
    fig.savefig(ruta_comp, dpi=130)
    plt.close(fig)
    print(f"  [OK] {ruta_comp}")

    # ---- 2) Superposición (sólo si el ajuste es fiable) ------------------
    if ajuste is None:
        print("  [SKIP] no se encontró ajuste plano->modelo consistente "
              "(patrón 10/10/10/10/2.5 y 8.9/7.25 no detectado); se omite "
              "la superposición.")
        return 0
    (tx, ty), err, info = ajuste
    print(f"  ajuste plano->modelo: residual RMS = {err:.4f} m "
          f"(límite {MAX_RESIDUAL_M:.2f} m)")
    print(f"  escala dibujo ~ {info['escala_pt_m']:.3f} pt/m")
    print(f"  ejes X usados (pt): {info['seis_x']}")
    print(f"  ejes Y usados (pt): {info['tres_y']}")
    print(f"  residuales X (m): {info['rx_m']}")
    print(f"  residuales Y (m): {info['ry_m']}")
    if err > MAX_RESIDUAL_M:
        print("  [SKIP] residual mayor a límite; se omite la superposición.")
        return 0

    # transformación pixel->modelo: x_m = tx[0]*x_px + tx[1]
    def a_px2m(px):
        x_px_pt = px / px_por_pt
        return tx[0] * x_px_pt + tx[1]

    fig, ax = plt.subplots(figsize=(14, 10))
    ax.imshow(img_sup, interpolation="nearest", alpha=0.8)
    rango_x = (a_px2m(0), a_px2m(W))
    rango_y = (a_px2m(H), a_px2m(0))
    xm0, xm1 = sorted(rango_x)
    ym0, ym1 = sorted(rango_y)
    ax.set_xlim(0, W); ax.set_ylim(H, 0)   # mismos píxeles
    for v in vigas:
        (xi, yi, _), (xj, yj, _) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
        ax.plot([(xi - tx[1]) / tx[0] * px_por_pt, (xj - tx[1]) / tx[0] * px_por_pt],
                [(yi - ty[1]) / ty[0] * px_por_pt, (yj - ty[1]) / ty[0] * px_por_pt],
                color="cyan", lw=2.6, solid_capstyle="round")
    for c in cols:
        (xi, yi, _) = nodos[c["nodo_inferior"]]
        ax.plot([(xi - tx[1]) / tx[0] * px_por_pt],
                [(yi - ty[1]) / ty[0] * px_por_pt],
                marker="s", ms=12, color="magenta", markeredgecolor="black")
    for t, x, y in nodos3:
        ax.plot([(x - tx[1]) / tx[0] * px_por_pt],
                [(y - ty[1]) / ty[0] * px_por_pt],
                marker="o", ms=6, color="red")
    for ex, x in ejes_x.items():
        ax.text((x - tx[1]) / tx[0] * px_por_pt, 10, ex, fontsize=9,
                fontweight="bold", color="black",
                path_effects="")
    ax.set_title("SUPERPOSICION (solo visual) - plano 102 fondo + modelo "
                 "PISO_3 (vigas cian, columnas magenta, nodos rojos)")
    fig.tight_layout()
    ruta_sup = os.path.join(_SAL, "superposicion_plano102_modelo.png")
    fig.savefig(ruta_sup, dpi=130)
    plt.close(fig)
    print(f"  [OK] {ruta_sup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())