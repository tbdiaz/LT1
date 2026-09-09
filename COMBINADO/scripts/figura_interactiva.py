# -*- coding: utf-8 -*-
"""Figura 3D INTERACTIVA del modelo combinado LT1 + LT2 (HTML con plotly).

Reutiliza la clase `CombinedBuilder` de `src/run_combined.py` para
reconstruir el modelo final (mismos datos LT1/LT2, misma transformacion de
interfaz X=31.250), corre el analisis y exporta `outputs/vista_3d_interactiva.html`.

El HTML es standalone (plotly embebido): rotacion, zoom, pan, leyenda
clicable, tooltips por elemento/nodo y slider para deformada escalada.

Uso:
    python COMBINADO/scripts/figura_interactiva.py

Salida:
    COMBINADO/outputs/vista_3d_interactiva.html
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "COMBINADO" / "src"
OUT = ROOT / "COMBINADO" / "outputs"

sys.path.insert(0, str(SRC))
import run_combined as rc  # noqa: E402

try:
    import plotly.graph_objects as go
    import plotly.io as pio
except Exception as ex:  # pragma: no cover
    print(f"ERROR: plotly no disponible: {ex}")
    sys.exit(1)


def _segments(tags, ops):
    """Lista de segmentos (tag, n1, n2, c1, c2). Omite elementos no-2D."""
    segs = []
    for t in tags:
        try:
            ns = list(ops.eleNodes(int(t)))
        except Exception:
            continue
        if len(ns) != 2:
            continue
        try:
            c1 = [float(v) for v in ops.nodeCoord(ns[0])]
            c2 = [float(v) for v in ops.nodeCoord(ns[1])]
        except Exception:
            continue
        segs.append((int(t), int(ns[0]), int(ns[1]), c1, c2))
    return segs


def _line_trace(segs, color, name, hover_mask=None):
    """Trace de lineas (None entre segmentos). """
    xs, ys, zs = [], [], []
    for _t, _n1, _n2, c1, c2 in segs:
        xs += [c1[0], c2[0], None]
        ys += [c1[1], c2[1], None]
        zs += [c1[2], c2[2], None]
    kw = dict(x=xs, y=ys, z=zs, mode="lines", name=name,
              line=dict(color=color, width=2.2), showlegend=True)
    if hover_mask:
        ht = []
        for t, n1, n2, c1, c2 in segs:
            lbl = hover_mask(t, n1, n2)
            ht += [lbl, lbl, None]
        kw["text"] = ht
        kw["hovertemplate"] = "%{text}<extra></extra>"
    else:
        kw["hoverinfo"] = "skip"
    return go.Scatter3d(**kw)


def _deformed(segs, disp, scale):
    out = []
    for tag, n1, n2, c1, c2 in segs:
        d1 = disp.get(n1, [0.0, 0.0, 0.0])
        d2 = disp.get(n2, [0.0, 0.0, 0.0])
        out.append((tag, n1, n2,
                    [c1[i] + scale * d1[i] for i in range(3)],
                    [c2[i] + scale * d2[i] for i in range(3)]))
    return out


def _disp_map(ops, tags):
    disp = {}
    for n in tags:
        try:
            d = ops.nodeDisp(n)
            if d is None:
                d = [0.0] * 6
            d = [float(v or 0.0) for v in d]
            disp[n] = [d[0], d[1], d[2]]
        except Exception:
            disp[n] = [0.0, 0.0, 0.0]
    return disp


def main():
    print("Construyendo modelo combinado (reutiliza run_combined.py)...")
    b = rc.CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()
    b.apply_loads()
    b.run_analysis()
    node_tags, _elem_tags = b.validate()
    ops = rc.ops

    cat = [
        ("lt2", b.created["lt2_beams"] + b.created["lt2_cols"]
         + b.created["lt2_walls"], "#1f77b4", "LT2 (nativo)"),
        ("lt1", b.created["lt1_beams"] + b.created["lt1_cols"]
         + b.created["lt1_walls"], "#ff7f0e", "LT1 (transformado)"),
        ("links", b.created["links"], "#2ca02c",
         "Conectores V40-Muro (9001+)"),
        ("box", [e["tag"] for e in b.box_verticals], "#d62728",
         "Verticales cajas/pilastra (70001+)"),
    ]
    segs = {k: _segments(list(tags), ops) for k, tags, _c, _l in cat}

    level_z = {round(rc._zname(b.levels, n), 6): n
               for n in b.levels["name"]}

    def _lv_of(z):
        zr = round(float(z), 6)
        if zr in level_z:
            return level_z[zr]
        sel = min(level_z, key=lambda k: abs(k - zr))
        return f"{level_z[sel]} (intermedio)"

    def _hover(kindname):
        def _fn(t, n1, n2):
            return (f"{kindname}<br>Elem {t}<br>Nodos {n1}-{n2}")
        return _fn

    traces = []

    # nodos
    tags_all = sorted(set(map(int, ops.getNodeTags())))
    disp = _disp_map(ops, tags_all)
    nx, ny, nz, nh = [], [], [], []
    for t in tags_all:
        try:
            c = [float(v) for v in ops.nodeCoord(t)]
        except Exception:
            continue
        nx.append(c[0]); ny.append(c[1]); nz.append(c[2])
        nh.append(f"Nodo {t}<br>{_lv_of(c[2])}<br>"
                  f"X={c[0]:.3f} Y={c[1]:.3f} Z={c[2]:.3f}")
    traces.append(go.Scatter3d(
        x=nx, y=ny, z=nz, mode="markers", name=f"Nodos ({len(nx)})",
        marker=dict(size=1.6, color="#777777"), text=nh,
        hovertemplate="%{text}<extra></extra>"))

    # interfaz
    if b.interface:
        ix = [p[2] for p in b.interface]
        iy = [p[3] for p in b.interface]
        iz = [p[4] for p in b.interface]
        traces.append(go.Scatter3d(
            x=ix, y=iy, z=iz, mode="markers", name=f"Interfaz ({len(ix)})",
            marker=dict(size=5, color="black", symbol="diamond"),
            hovertemplate="Interfaz X=31.250<br>"
                          "Y=%{y:.3f} Z=%{z:.3f}<extra></extra>"))

    # apoyos
    if b.support_tags:
        sx = [float(ops.nodeCoord(t)[0]) for t in b.support_tags]
        sy = [float(ops.nodeCoord(t)[1]) for t in b.support_tags]
        sz = [float(ops.nodeCoord(t)[2]) for t in b.support_tags]
        traces.append(go.Scatter3d(
            x=sx, y=sy, z=sz, mode="markers",
            name=f"Apoyos fijos ({len(sx)})",
            marker=dict(size=7, color="#8c564b", symbol="square"),
            text=[f"Base {t}" for t in b.support_tags],
            hovertemplate="%{text}<br>"
                          "X=%{x:.3f} Y=%{y:.3f} Z=%{z:.3f}<extra></extra>"))

    # anillo VI ROOF
    ring = [226, 227, 244, 245, 246, 247, 256, 257, 258, 259]
    rx = []; ry = []; rz = []
    for t in ring:
        try:
            c = [float(v) for v in ops.nodeCoord(t)]
        except Exception:
            continue
        rx.append(c[0]); ry.append(c[1]); rz.append(c[2])
    if rx:
        traces.append(go.Scatter3d(
            x=rx, y=ry, z=rz, mode="markers", name="Anillo VI ROOF",
            marker=dict(size=8, color="#e377c2", symbol="x"),
            text=[f"Nodo {t}" for t in ring],
            hovertemplate="%{text}<br>X=%{x:.3f} Y=%{y:.3f} Z=%{z:.3f}"
                          "<extra></extra>"))

    # lineas por familia
    line_traces = {}
    for k, _tags, color, name in cat:
        line_traces[k] = _line_trace(segs[k], color, name, _hover(name))

    # slider de deformada (escalas relativas al envolvente)
    max_u = 0.0
    if nx:
        max_u = max(((disp[n][0] ** 2 + disp[n][1] ** 2
                      + disp[n][2] ** 2) ** 0.5) for n in tags_all)
    if max_u > 0:
        bbox_diag = ((max(nx) - min(nx)) ** 2
                     + (max(ny) - min(ny)) ** 2
                     + (max(nz) - min(nz)) ** 2) ** 0.5
        base = 0.02 * bbox_diag / max_u
    else:
        base = 1.0
    scale_opts = [0.0, 0.5, 1.0, 2.0]

    def_traces = {k: [] for k, _tags, _c, _l in cat}
    for k, _tags, color, name in cat:
        for s in scale_opts:
            dsegs = _deformed(segs[k], disp, s * base)
            t = _line_trace(dsegs, color, f"{name} (def x{s})")
            t.line.update(width=1.2, dash="dot")
            def_traces[k].append(t)

    # orden: [def*4] + [lineas*4] + [nodos, interfaz, apoyos, ring]
    data = []
    for k in ["lt2", "lt1", "links", "box"]:
        for dt in def_traces[k]:
            dt.visible = False
            data.append(dt)
    for k in ["lt2", "lt1", "links", "box"]:
        data.append(line_traces[k])
    data.extend(traces)

    # visibilidad base (lineas y resto visibles; def ocultas)
    n_def = 4 * len(scale_opts)
    n_lines = 4
    base_vis = [False] * n_def + [True] * (len(data) - n_def)

    layout = go.Layout(
        title=dict(text="Modelo combinado LT1 + LT2 (rc=0) — interactiva",
                   x=0.5),
        scene=dict(
            xaxis=dict(title="X (m)", showbackground=True),
            yaxis=dict(title="Y (m)", showbackground=True),
            zaxis=dict(title="Z (m)", showbackground=True),
            aspectmode="data"),
        showlegend=True,
        legend=dict(x=1.02, y=1.0),
        margin=dict(l=0, r=0, t=40, b=0),
        sliders=[dict(
            active=0, pad=dict(t=10),
            currentvalue=dict(prefix="Deformada (escala): "),
            steps=[])])

    fig = go.Figure(data=data, layout=layout)

    steps = []
    for si, s in enumerate(scale_opts):
        vis = list(base_vis)
        for j in range(4):  # familia j -> trazas def en j*4+0..3
            idx0 = j * len(scale_opts) + si
            vis[idx0] = (s != 0.0)
        steps.append(dict(label=str(s), method="restyle",
                          args=["visible", vis]))
    fig.layout.sliders[0].steps = steps

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "vista_3d_interactiva.html"
    pio.write_html(fig, str(out), include_plotlyjs="inline",
                   auto_open=False)
    print(f"\nOK: figura interactiva -> {out.relative_to(ROOT)}")

    png = OUT / "vista_3d_interactiva.png"
    try:
        import kaleido  # noqa: F401
        pio.write_image(fig, str(png), width=1600, height=1200,
                        scale=2, validate=False)
        print(f"OK: imagen PNG -> {png.relative_to(ROOT)}")
    except Exception as ex:
        print(f"AVISO: no se pudo exportar el PNG (kaleido): {ex}")

    print(f"rc={b.rc}  nodos={len(tags_all)}  "
          f"apoyos={len(b.support_tags)}  "
          f"max|U|={max_u:.6f} m")


if __name__ == "__main__":
    main()