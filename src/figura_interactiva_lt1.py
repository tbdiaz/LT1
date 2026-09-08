# ============================================================================
# figura_interactiva_lt1.py
# Genera outputs/figura_interactiva_lt1.html — vista 3D interactiva (Plotly)
# del modelo estructural LT1 clase A. Lee SOLO el JSON exportado
# (outputs/unity/modelo_lt1.json); no toca el modelo OpenSees ni la geometría.
# Interactividad: rotar/zoom/pan, leyenda con toggles por grupo, hover con tags.
# ============================================================================
import json, os, sys

import plotly.graph_objects as go

ruta_json = os.path.join("outputs", "unity", "modelo_lt1.json")
with open(ruta_json, "r", encoding="utf-8") as f:
    data = json.load(f)

# --- Mapping estructural (X,Z arriba) -> Plotly (X,Y,Z) ---------------------
# Mantenemos X = eje E->I', Y = eje 1->3 (decreciente), Z vertical arriba.
# Es decir: usamos las coordenadas tal cual (x, y, z) ya que Plotly permite
# cualquier orientación; solo aclaramos en el layout el sistema usado.

nodes = data["nodes"]
beams = data["beams"]
columns = data["columns"]
supports = data["supports"]
diaphragms = data["diaphragms"]
panos = data.get("panos", [])

node_pos = {n["tag"]: (n["x"], n["y"], n["z"]) for n in nodes}

traces = []

# --- NODOS estructurales ----------------------------------------------------
struct_nodes = [n for n in nodes if n.get("tipo") == "structural"]
if struct_nodes:
    traces.append(go.Scatter3d(
        x=[n["x"] for n in struct_nodes],
        y=[n["y"] for n in struct_nodes],
        z=[n["z"] for n in struct_nodes],
        mode="markers",
        name="Nodos estructurales",
        legendgroup="nodos",
        marker=dict(size=2.5, color="#2b6cb0", opacity=0.9),
        hovertemplate="Nodo %{customdata}<br>Nivel: %{text}"
                      "<br>x:%{x:.3f} y:%{y:.3f} z:%{z:.3f}<extra></extra>",
        customdata=[n["tag"] for n in struct_nodes],
        text=[n.get("nivel", "") for n in struct_nodes],
    ))

# --- NODOS MASTER (diafragma) ------------------------------------------------
masters = [n for n in nodes if n.get("tipo") == "master"]
if masters:
    traces.append(go.Scatter3d(
        x=[n["x"] for n in masters],
        y=[n["y"] for n in masters],
        z=[n["z"] for n in masters],
        mode="markers",
        name="Masters diafragma",
        legendgroup="masters",
        marker=dict(size=8, color="#ffd700", symbol="diamond",
                    line=dict(color="black", width=1.5)),
        hovertemplate="Master %{customdata}<br>Nivel: %{text}<extra></extra>",
        customdata=[n["tag"] for n in masters],
        text=[n.get("nivel", "") for n in masters],
    ))

# --- COLUMNAS: trazo único agrupado -----------------------------------------
col_traces = []
for c in columns:
    xi, yi, zi = node_pos[c["node_i"]]
    xj, yj, zj = node_pos[c["node_j"]]
    col_traces.append((xi, yi, zi, xj, yj, zj, c["elementTag"],
                       c["seccion"]))

col_x = []
col_y = []
col_z = []
col_custom = []
col_text = []
for (xi, yi, zi, xj, yj, zj, et, sec) in col_traces:
    col_x += [xi, xj, None]
    col_y += [yi, yj, None]
    col_z += [zi, zj, None]
    col_custom += [et, et, None]
    col_text += [sec, sec, None]

traces.append(go.Scatter3d(
    x=col_x, y=col_y, z=col_z,
    mode="lines",
    name="Columnas (90)",
    legendgroup="columnas",
    line=dict(color="#909090", width=7),
    hovertemplate="Columna tag %{customdata} · %{text}<extra></extra>",
    customdata=col_custom,
    text=col_text,
))

# --- VIGAS -------------------------------------------------------------------
beam_x = []
beam_y = []
beam_z = []
beam_custom = []
beam_text = []
for b in beams:
    xi, yi, zi = node_pos[b["node_i"]]
    xj, yj, zj = node_pos[b["node_j"]]
    trib = b.get("carga_total_tributaria_kN")
    trib_txt = f"{trib:.1f} kN" if trib is not None else "sin trib"
    beam_x += [xi, xj, None]
    beam_y += [yi, yj, None]
    beam_z += [zi, zj, None]
    beam_custom += [b["elementTag"], b["elementTag"], None]
    beam_text += [f"Nivel {b['nivel']} · {trib_txt}", f"Nivel {b['nivel']} · {trib_txt}", None]

traces.append(go.Scatter3d(
    x=beam_x, y=beam_y, z=beam_z,
    mode="lines",
    name="Vigas (108)",
    legendgroup="vigas",
    line=dict(color="#7a95b0", width=5),
    hovertemplate="Viga tag %{customdata}<br>%{text}<extra></extra>",
    customdata=beam_custom,
    text=beam_text,
))

# --- APOYOS -----------------------------------------------------------------
sup_pos = [node_pos[s["nodeTag"]] for s in supports]
traces.append(go.Scatter3d(
    x=[p[0] for p in sup_pos],
    y=[p[1] for p in sup_pos],
    z=[p[2] for p in sup_pos],
    mode="markers",
    name="Apoyos (18, empotrados)",
    legendgroup="apoyos",
    marker=dict(size=6, color="#cc3333", symbol="square",
                line=dict(color="black", width=1)),
    hovertemplate="Apoyo %{customdata}<br>%{text}<extra></extra>",
    customdata=[s["nodeTag"] for s in supports],
    text=["6 GDL empotrados" for _ in supports],
))

# --- DIAFRAGMAS (plano semitransparente) ------------------------------------
for d in diaphragms:
    nivel = d["nivel"]
    z_lvl = d["z"]
    slave_tags = d["slaves"]
    xs = [node_pos[t][0] for t in slave_tags]
    ys = [node_pos[t][1] for t in slave_tags]
    if not xs:
        continue
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xmin -= (xmax - xmin) * 0.02
    ymin -= (ymax - ymin) * 0.02
    xmax += (xmax - xmin) * 0.02
    ymax += (ymax - ymin) * 0.02
    traces.append(go.Mesh3d(
        x=[xmin, xmax, xmax, xmin],
        y=[ymin, ymin, ymax, ymax],
        z=[z_lvl, z_lvl, z_lvl, z_lvl],
        alphahull=0,
        opacity=0.12,
        color="green",
        name=f"Diafragma {nivel}",
        legendgroup="diafragmas",
        showlegend=True,
        hovertemplate=f"{nivel}<br>Master %{{customdata}}<br>{len(slave_tags)} slaves<extra></extra>",
        customdata=[d["master"]] * 4,
    ))

# --- LAYOUT -----------------------------------------------------------------
fig = go.Figure(data=traces)

# Rangos equitativos para vistas correctas
x_vals = [n["x"] for n in nodes]
y_vals = [n["y"] for n in nodes]
z_vals = [n["z"] for n in nodes]
fig.update_layout(
    title=dict(
        text="LT1 · Modelo estructural clase A (interactivo)<br>"
             "<sup>108 nodos · 90 columnas · 108 vigas · 18 apoyos · 4 diafragmas · "
             "gravedad P=20182.63 kN</sup>",
        x=0.5,
        font=dict(size=14),
    ),
    scene=dict(
        xaxis=dict(title="X [m]", range=[min(x_vals) - 1, max(x_vals) + 1]),
        yaxis=dict(title="Y [m]", range=[min(y_vals) - 1, max(y_vals) + 1]),
        zaxis=dict(title="Z [m] (vertical)", range=[min(z_vals) - 1, max(z_vals) + 1]),
        aspectmode="data",
        camera=dict(eye=dict(x=1.6, y=1.6, z=0.9)),
    ),
    legend=dict(
        x=0.02, y=0.98, xanchor="left", yanchor="top",
        bgcolor="rgba(255,255,255,0.7)",
        font=dict(size=10),
    ),
    margin=dict(l=0, r=0, t=60, b=0),
    hoverlabel=dict(font=dict(size=11)),
    font=dict(family="Helvetica, Arial, sans-serif"),
)

os.makedirs("outputs", exist_ok=True)
ruta_html = os.path.join("outputs", "figura_interactiva_lt1.html")
fig.write_html(ruta_html, include_plotlyjs="cdn", config={
    "displaylogo": False,
    "scrollZoom": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
})
print(f"  [OK] figura interactiva 3D: {ruta_html}  ({os.path.getsize(ruta_html)} bytes)")
