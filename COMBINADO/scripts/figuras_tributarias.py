# -*- coding: utf-8 -*-
"""Vistas por piso de las areas tributarias LT1 (PISO_1..PISO_4).

Reutiliza `CombinedBuilder` de `src/run_combined.py` para disponer de la
geometria real del modelo combinado (vigas JSON, segmentos de fachada 800201+,
vigas saliente 800101+ y la redistribucion de cargas por particion).

Por piso genera:
    COMBINADO/outputs/tributarias_lt1/tributarias_piso_{1..4}.png

Plan en LT1 (x_lt1 = X - 31.250, y_lt1 = -Y): ejes E(0) F(10) G(20) H(30)
I(40) I'(45) ; ejes 1(0) 2(-8.9) 3(-16.15); salientes hasta -20.32.

Uso:
    python COMBINADO/scripts/figuras_tributarias.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "COMBINADO" / "src"
OUT_DIR = ROOT / "COMBINADO" / "outputs" / "tributarias_lt1"

sys.path.insert(0, str(SRC))
import run_combined as rc  # noqa: E402

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
except Exception as ex:  # pragma: no cover
    print(f"ERROR: matplotlib no disponible: {ex}")
    sys.exit(1)


def _to_lt1(ops, tag):
    c = [float(v) for v in ops.nodeCoord(int(tag))]
    return c[0] - rc.SHIFT_X, -c[1], c[2]


def main():
    print("Construyendo modelo combinado (reutiliza run_combined.py)...")
    b = rc.CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()
    ops = rc.ops

    ip_x = b.ip_correction  # {node_tag_lt1: x_lt1} para I'

    def lt1_coords(tag):
        return _to_lt1(ops, tag)

    q_for_seg = {}
    for rb in b.removed_beams_loads:
        for s in rb["segments"]:
            q_for_seg[int(s["tag"])] = rb["qG_kN_m"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for k, (nivel, data) in enumerate(rc._SALIENTES_DATA.items(), start=1):
        z = float(data["z_m"])
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.set_title(
            f"LT1 areas tributarias - {nivel} (Z={z:.2f} m) - "
            "modelo combinado", fontsize=12)
        ax.set_xlabel("x_LT1 (m):  E=0  F=10  G=20  H=30  I=40  I'=45")
        ax.set_ylabel("y_LT1 (m):  1=0  2=-8.9  3=-16.15 (sur)")

        # losa principal (0..45) x (0..-16.15)
        ax.add_patch(plt.Rectangle((0, -16.15), 45, 16.15,
                                   facecolor="#eaf3fb", edgecolor="none",
                                   zorder=0))

        # retícula de panos P11..P52 (x cada 10 m, y en 8.9/7.25)
        for xg in (0, 10, 20, 30, 40, 45):
            ax.plot([xg, xg], [0, -16.15], color="#bcd0e0", lw=0.6, zorder=1)
        for yg in (0, -8.9, -16.15):
            ax.plot([0, 45], [yg, yg], color="#bcd0e0", lw=0.6, zorder=1)

        # contorno saliente (nodos del nivel)
        sal = []
        for t in b.saliente_nodes:
            x, y, zz = lt1_coords(t)
            if abs(zz - z) < 1e-6:
                sal.append((x, y))
        if sal:
            ex, ey = zip(*sal)
            ax.plot(ex, ey, color="#37474f", lw=1.4, ls="--", zorder=2,
                    label=f"Saliente PISO ({len(sal)} nodos)")

        # vigas LT1 con carga (color = qG), y sin carga (gris)
        cmap = plt.cm.viridis
        w_max = 1e-9
        loaded, unloaded, ip_beams = [], [], []
        for row in b.json_lt1["beams"]:
            n_i, n_j = b.lt1_nodes[row["node_i"]], b.lt1_nodes[row["node_j"]]
            if abs(float(n_i["z"]) - z) > 1e-6:
                continue
            x1 = ip_x.get(row["node_i"], float(n_i["x"]))
            x2 = ip_x.get(row["node_j"], float(n_j["x"]))
            y1, y2 = float(n_i["y"]), float(n_j["y"])
            w = float(row.get("carga_lineal_qG_kN_m", 0.0) or 0.0)
            rec = dict(x1=x1, x2=x2, y1=y1, y2=y2, w=w,
                       tag=row["elementTag"])
            if w > 1e-12:
                w_max = max(w_max, w)
                if abs(x1 - 45.0) < 1e-6 or abs(x2 - 45.0) < 1e-6:
                    ip_beams.append(rec)
                else:
                    loaded.append(rec)
            else:
                unloaded.append(rec)

        # segmentos de fachada (redistribucion de las 11 vigas eliminadas)
        seg_rows = []
        for s in b.facade_segments:
            if s["nivel"] != nivel:
                continue
            q = q_for_seg.get(int(s["tag"]), 0.0)
            w_max = max(w_max, q)
            seg_rows.append(dict(tag=s["tag"], x1=s["x1_lt1"],
                                 x2=s["x2_lt1"], q=q))

        # vigas saliente (sin carga de losa)
        sal_beams = []
        for t in b.saliente_beams:
            ns = [int(n) for n in ops.eleNodes(int(t))]
            zz = [float(ops.nodeCoord(n)[2]) for n in ns]
            if max(zz) - min(zz) > 1e-6:
                continue
            if abs(zz[0] - z) > 1e-6:
                continue
            (x1, y1, _), (x2, y2, _) = (lt1_coords(n) for n in ns)
            sal_beams.append(dict(tag=t, x1=x1, y1=y1, x2=x2, y2=y2))

        norm = plt.Normalize(vmin=0.0, vmax=w_max)

        for r in unloaded:
            ax.plot([r["x1"], r["x2"]], [r["y1"], r["y2"]],
                    color="#9e9e9e", lw=1.0, zorder=3)

        for r in loaded:
            ax.plot([r["x1"], r["x2"]], [r["y1"], r["y2"]],
                    color=cmap(norm(r["w"])), lw=2.2, zorder=4)

        for r in ip_beams:
            ax.plot([r["x1"], r["x2"]], [r["y1"], r["y2"]],
                    color=cmap(norm(r["w"])), lw=3.4, zorder=5,
                    solid_capstyle="round")

        for s in seg_rows:
            q = s["q"]
            if q <= 1e-12:
                continue
            ax.plot([s["x1"], s["x2"]], [-16.15, -16.15],
                    color="magenta" if q else "#607d8b", lw=3.0, zorder=6)
            ax.annotate(f"{s['tag']}: q={q:.2f}",
                        ((s["x1"] + s["x2"]) / 2, -16.15 + 0.35),
                        fontsize=7, color="magenta", ha="center",
                        zorder=7)

        for s in sal_beams:
            ax.plot([s["x1"], s["x2"]], [s["y1"], s["y2"]],
                    color="#37474f", lw=1.3, ls="-", zorder=3, alpha=0.85)

        # tags de vigas cargadas (columna sur y ejes I' / fachada)
        for r in loaded:
            if abs(r["y1"] + 16.15) < 1e-6:
                ax.annotate(str(r["tag"]), ((r["x1"] + r["x2"]) / 2,
                                            r["y1"] + 0.9),
                            fontsize=6.5, color="#444444", ha="center",
                            zorder=7)
        for r in ip_beams:
            ax.annotate(f"{r['tag']} (I': 2.5->5.0 m)",
                        ((r["x1"] + r["x2"]) / 2, r["y1"] - 0.55),
                        fontsize=7, color="black", ha="center",
                        fontweight="bold", zorder=7)

        # ejes
        for xg, xl in ((0, "E"), (10, "F"), (20, "G"), (30, "H"),
                       (40, "I"), (45, "I'")):
            ax.text(xg, 0.9, xl, fontsize=8, ha="center", color="#607d8b",
                    zorder=7)
        for yg, yl in ((0, "1"), (-8.9, "2"), (-16.15, "3")):
            ax.text(-1.4, yg, yl, fontsize=8, va="center", color="#607d8b",
                    zorder=7)

        # caja resumen
        trib = {int(t["elementTag"]): t
                for t in b.json_lt1["tributary_areas"] if t["nivel"] == nivel}
        A_ref = sum(t["A_tributaria_m2"] for t in trib.values())
        P_ref = sum(t["P_losa_kN"] for t in trib.values())
        txt = (f"{nivel}  |  A_losa panos = 686.375 m2  "
               f"|  ΣA_tributaria(JSON) = {A_ref:.3f} m2  "
               f"|  P_losa(JSON) = {P_ref:.1f} kN\n"
               "I' corregido 42.5->45.0 m: tramos I-I' de 2.5 a 5.0 m "
               "(x2=45 m, marcados); su QG por metro se duplica "
               "(+6.25 m2 eq. por piso). Franja extra 34.125 m2/piso "
               "conserva valores de referencia.")
        ax.text(0.02, 0.03, txt, transform=ax.transAxes, fontsize=8,
                va="bottom", ha="left", bbox=dict(boxstyle="round,pad=0.4",
                fc="#fdf6e3", ec="#d0b48a", alpha=0.95), zorder=8)

        cb = fig.colorbar(
            plt.cm.ScalarMappable(norm=norm, cmap=cmap),
            ax=ax, orientation="vertical", shrink=0.8, pad=0.01)
        cb.set_label("q_G carga (kN/m)")

        ax.legend(handles=[
            Line2D([0], [0], color="#f0f0f0", lw=2, marker="o",
                   markerfacecolor=cmap(norm(w_max)),
                   markeredgecolor="none", label="viga con carga LT1"),
            Line2D([0], [0], color=cmap(norm(w_max)), lw=3.4,
                   label="tramo I-I' (2.5->5.0 m)"),
            Line2D([0], [0], color="magenta", lw=3.0,
                   label="segmento fachada 800201+ (q redistribuida)"),
            Line2D([0], [0], color="#37474f", lw=1.3, ls="--",
                   label="vigas saliente / borde"),
            Line2D([0], [0], color="#9e9e9e", lw=1.0,
                   label="viga LT1 sin carga"),
        ], loc="upper right", fontsize=8)

        ax.set_xlim(-6, 48)
        ax.set_ylim(-21.0, 4)
        ax.set_aspect("equal")
        fig.tight_layout()
        out = OUT_DIR / f"tributarias_piso_{k}.png"
        fig.savefig(out, dpi=200)
        plt.close(fig)
        print(f"OK: {out.relative_to(ROOT)}  "
              f"(A_ref={A_ref:.2f} m2  P_ref={P_ref:.1f} kN)")


if __name__ == "__main__":
    main()