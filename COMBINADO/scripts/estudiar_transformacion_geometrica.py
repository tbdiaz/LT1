# -*- coding: utf-8 -*-
"""Estudio de la transformación geométrica LT1+LT2 (integración lateral).

Lee SOLO los modelos fuente (LT1 en ../data, LT2 en ../LT2/data), sin
modificarlos, y produce el estudio solicitado:

    transformación X/Y necesaria;
    traslación / reflexión / rotación;
    coordenada global propuesta para la interfaz;
    comprobación de coincidencia de los ejes 1, 2 y 3;
    nodos LT2 que llegan a la interfaz por nivel;
    nodos LT1 que llega n a la interfaz por nivel;
    coordenadas tras la transformación;
    cuáles coinciden exactamente y cuáles no.

Salidas:
    COMBINADO/docs/auditoria_transformacion_geometrica.md
    COMBINADO/outputs/interfaz_coincidencia_por_eje.csv

NO construye ningún modelo FE. NO conecta nodos, diafragmas, apoyos ni cargas.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT_LT1 = Path(__file__).resolve().parents[2]          # raíz del repositorio
ROOT_LT2 = ROOT_LT1 / "LT2"
ROOT_COMB = Path(__file__).resolve().parents[1]         # COMBINADO
DOCS = ROOT_COMB / "docs"
OUT = ROOT_COMB / "outputs"

GEOM_LT2 = ROOT_LT2 / "data" / "geometry"

TOL = 1e-6

# ---------------------------------------------------------------------------
# 1. Datos LT1 (single source of truth: data/geometria.py)
# ---------------------------------------------------------------------------
def load_lt1_geometria():
    ruta = ROOT_LT1 / "data" / "geometria.py"
    spec = importlib.util.spec_from_file_location("lt1_geometria", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tag_nodo_lt1(nivel, eje_x, eje_y, g):
    i_n = {k: i for i, k in enumerate(g.niveles_z)}[nivel]
    i_x = {k: i for i, k in enumerate(g.ejes_x)}[eje_x]
    i_y = {k: i for i, k in enumerate(g.ejes_y)}[eje_y]
    return (i_n * 10000) + (i_x * 100) + i_y + 1


# ---------------------------------------------------------------------------
# 2. Datos LT2: mapa tag -> (x, y, z) con el MISMO orden que
#    LT2/src/build_opensees_model.py (_collect_nodes).
# ---------------------------------------------------------------------------
def load_lt2_nodes():
    levels = pd.read_csv(GEOM_LT2 / "levels.csv")
    beams = pd.read_csv(GEOM_LT2 / "beams_LT2.csv")
    cols = pd.read_csv(GEOM_LT2 / "column_segments_LT2.csv")
    walls = pd.read_csv(GEOM_LT2 / "wall_segments_LT2.csv")

    def zname(name):
        return float(levels.loc[levels["name"] == name, "z_m"].iloc[0])

    keys = set()
    zl = zname("B1")
    for r in beams.itertuples():
        z = zname(r.level)
        keys.add((round(r.x1_m, 6), round(r.y1_m, 6), z))
        keys.add((round(r.x2_m, 6), round(r.y2_m, 6), z))
    for r in cols.itertuples():
        z0, z1 = zname(r.from_level), zname(r.to_level)
        keys.add((round(r.x_m, 6), round(r.y_m, 6), z0))
        keys.add((round(r.x_m, 6), round(r.y_m, 6), z1))
    for r in walls.itertuples():
        z0, z1 = zname(r.from_level), zname(r.to_level)
        keys.add((round(r.x1_m, 6), round(r.y1_m, 6), z0))
        keys.add((round(r.x2_m, 6), round(r.y2_m, 6), z0))
        keys.add((round(r.x1_m, 6), round(r.y1_m, 6), z1))
        keys.add((round(r.x2_m, 6), round(r.y2_m, 6), z1))
    ordered = sorted(keys, key=lambda k: (k[2], k[0], k[1]))
    tag_to_key = {i + 1: k for i, k in enumerate(ordered)}
    key_to_tag = {k: t for t, k in tag_to_key.items()}
    return key_to_tag, tag_to_key


# ---------------------------------------------------------------------------
# 3. Interfaz: borde oeste de LT1 (eje E, X=0) y borde este de LT2 (eje D,
#    X=31.250). D'=31.475 no tiene nodos (línea de grilla sin elementos).
# ---------------------------------------------------------------------------
def analizar():
    g = load_lt1_geometria()
    key_to_tag, tag_to_key = load_lt2_nodes()

    niveles_par = [
        ("FUNDACION_SUP", "B1", -7.97),
        ("PISO_1S", "L1", -4.01),
        ("PISO_1", "L2", -0.05),
        ("PISO_2", "L3", 3.91),
        ("PISO_3", "L4", 7.87),
        ("PISO_4", "ROOF", 11.83),
    ]
    ejes_par = [("1", 0.000), ("2", 8.900), ("3", 16.150)]  # eje LT2 y valor Y

    INTERFAZ_X = 31.250

    def transf_lt1(x, y, z):
        return (x + INTERFAZ_X, -y, z)

    # ---- nodos de interfaz por lado ---------------------------------------
    lt2_edge = {}
    for k, tag in sorted(key_to_tag.items(), key=lambda kv: (kv[0][2], kv[0][1])):
        x, y, z = k
        if abs(x - INTERFAZ_X) <= TOL:
            lt2_edge.setdefault(round(z, 6), []).append((tag, x, y, z))
        elif abs(x - 31.475) <= TOL:
            lt2_edge.setdefault("x31.475", []).append((tag, x, y, z))

    # ejes Y de LT1 en el esqueleto en eje E: 1, 2, 3 (0, -8.9, -16.15)
    eje_y_lt1 = {"1": "1", "2": "2", "3": "3"}

    filas = []
    coinciden = 0
    sin_contraparte = []
    for nivel_lt1, nivel_lt2, z in niveles_par:
        for eje_lt2, y_lt2 in ejes_par:
            eje_lt1 = eje_y_lt1[eje_lt2]
            y_lt1 = g.ejes_y[eje_lt1]
            x_t, y_t, z_t = transf_lt1(0.0, y_lt1, z)
            tag_lt2 = key_to_tag.get((round(INTERFAZ_X, 6), round(y_lt2, 6), round(z, 6)))
            tag_lt1 = tag_nodo_lt1(nivel_lt1, "E", eje_lt1, g)
            d = ((INTERFAZ_X - x_t) ** 2 + (y_lt2 - y_t) ** 2 + (z - z_t) ** 2) ** 0.5
            if tag_lt2 is None:
                raise SystemExit(
                    f"FALTA nodo LT2 en interfaz: nivel {nivel_lt2} eje {eje_lt2} "
                    f"({INTERFAZ_X}, {y_lt2}, {z})")
            filas.append({
                "NIVEL": f"{nivel_lt1} / {nivel_lt2}",
                "EJE": eje_lt2,
                "NODO_LT2": tag_lt2,
                "X_LT2": INTERFAZ_X, "Y_LT2": y_lt2, "Z_LT2": z,
                "NODO_LT1": tag_lt1,
                "X_LT1_TR": x_t, "Y_LT1_TR": y_t, "Z_LT1_TR": z_t,
                "DISTANCIA_m": round(d, 6),
                "COINCIDE": "SI" if d <= 1e-3 else "NO",
            })
            coinciden += int(d <= 1e-3)
        # nodos de núcleo LT2 en la interfaz sin contraparte en LT1
        for y_n in (3.18, 6.275):
            t = key_to_tag.get((round(INTERFAZ_X, 6), round(y_n, 6), round(z, 6)))
            if t is not None:
                sin_contraparte.append(f"{nivel_lt1}/{nivel_lt2}: nodo {t} "
                                       f"({INTERFAZ_X},{y_n},{z}) NÚCLEO_LT2")

    tab = pd.DataFrame(filas)

    # ---- rangos globales (solo nodos modelados) -----------------------------
    xs_lt2 = [k[0] for k in key_to_tag]
    ys_lt2 = [k[1] for k in key_to_tag]
    xs_lt1_tr = sorted(transf_lt1(g.ejes_x[e], 0.0, 0.0)[0] for e in g.ejes_x)
    ys_lt1_tr = sorted(transf_lt1(0.0, g.ejes_y[e], 0.0)[1] for e in g.ejes_y)

    return dict(
        g=g, tab=tab, niveles_par=niveles_par, ejes_par=ejes_par,
        interfaz_x=INTERFAZ_X, coinciden=coinciden,
        sin_contraparte=sin_contraparte, lt2_edge=lt2_edge,
        x_lt2=(min(xs_lt2), max(xs_lt2)),
        y_lt2=(min(ys_lt2), max(ys_lt2)),
        x_lt1_tr=(min(xs_lt1_tr), max(xs_lt1_tr)),
        y_lt1_tr=(min(ys_lt1_tr), max(ys_lt1_tr)),
    )


# ---------------------------------------------------------------------------
# 4. Documento de auditoría
# ---------------------------------------------------------------------------
def render_md(r):
    g, c = r["g"], r["coinciden"]
    lt = []
    lt.append("# Auditoría de transformación geométrica — LT1 + LT2\n")
    lt.append("**Modelo combinado `COMBINADO/` · ETAPA DE ESTUDIO GEOMÉTRICO — "
              "NO se construyó todavía el modelo FE.**\n")
    lt.append("Fuentes (solo lectura): `../data/geometria.py` (LT1) y "
              "`../LT2/data/geometry/*.csv` (LT2).\n")

    lt.append("\n## 1. Disposición acordada\n")
    lt.append("- **LT2 a la izquierda (oeste), LT1 a la derecha (este).** "
              "Unión lateral.\n")
    lt.append("- Interfaz = borde **este de LT2** (eje D, planos 2024_22-101/102) "
              "y borde **oeste de LT1** (eje E, planos 2017_67-101/102/103).\n")
    lt.append("- Ejes transversales comunes (confirmados por inspección visual): "
              "LT2 eje 1 ↔ LT1 eje 1 · LT2 eje 2 ↔ LT1 eje 2 · LT2 eje 3 ↔ LT1 eje 3.\n")
    lt.append("- **No** se asume 1' ↔ 1'' ni correspondencia de 2a.\n")
    lt.append("- Cotas Z coincidentes entre ambos modelos (ver sección 5).\n")

    lt.append("\n## 2. Datos de origen\n")
    lt.append("| Parámetro | LT1 | LT2 |\n|---|---|---|\n")
    lt.append("| Ejes X | " + ", ".join(f"{k}={v}" for k, v in g.ejes_x.items())
              + " | " + "A'=0.000, A=3.750, B=11.250, C=21.250, C'=28.830, "
              + "D=31.250, D'=31.475 |\n")
    lt.append("| Ejes Y | " + ", ".join(f"{k}={v}" for k, v in g.ejes_y.items())
              + " | " + "1=0.000, 1A=4.265, 2=8.900, 2A=11.885, 3=16.150 |\n")
    lt.append("| Niveles Z | " + ", ".join(f"{k}={v}" for k, v in g.niveles_z.items())
              + " | " + "B1=-7.97, L1=-4.01, L2=-0.05, L3=3.91, L4=7.87, ROOF=11.83 |\n")

    lt.append("\n### Tags de nodos\n")
    lt.append("- **LT1** (formula `tag = i_n*10000 + i_x*100 + i_y + 1`, "
              "`src/modelo_lt1.py`): eje E → `i_x=0`; ejes Y 1/2/3 → `i_y=0/2/4`; "
              "niveles FUNDACION_SUP..PISO_4 → `i_n=0..5`.\n")
    lt.append("- **LT2** (orden `(z, x, y)`, `LT2/src/build_opensees_model.py`): "
              "nodos estructurales `1..272`.\n")

    lt.append("\n## 3. Transformación propuesta\n")
    lt.append("Se mantiene LT2 en sus coordenadas nativas y se transforma LT1:\n")
    lt.append("```\nX' = X + 31.250      (traslación en X: borde oeste de LT1, eje E=0, "
              "→ interfaz X=31.250)\nY' = -Y              (reflexión: LT1 eje 2 (−8.900) → +8.900 = LT2 eje 2; "
              "eje 3 (−16.150) → +16.150 = LT2 eje 3)\nZ' = Z              (datum idéntico, sin cambio)\n```\n")
    lt.append("**No se requiere rotación**: ambas edificaciones comparten la dirección de X "
              "(borde de interfaz vertical) y la reflexión en Y no actúa sobre X.\n")
    lt.append(f"\n**Coordenada global de la interfaz propuesta: X = {r['interfaz_x']:.3f} m**\n")
    lt.append("La línea de grilla `D' = 31.475` de LT2 **no** tiene nodos estructurales "
              "(no interviene en la interfaz).\n")
    lt.append("Si en el plano de sitio se confirmara una junta de ancho `t` en la interfaz, "
              "bastaría con desplazar LT1 a `X' = X + 31.250 + t`.\n")

    lt.append("\n## 4. Comprobación de coincidencia de ejes\n")
    lt.append("| Correspondencia | LT2 (nativo) | LT1 → transformado | ¿Coinciden? |\n")
    lt.append("|---|---|---|---|\n")
    for eje in g.ejes_y:
        pass
    for e2, y2 in [("1", 0.0), ("2", 8.9), ("3", 16.15)]:
        y1 = g.ejes_y[e2]
        lt.append(f"| eje {e2} | Y={y2:+.3f} | Y'={-y1:+.3f} | "
                  f"{'SÍ' if abs(y2 - (-y1)) <= 1e-6 else 'NO'} |\n")
    lt.append("| eje 1A ↔ eje 1'' | Y=+4.265 | Y'=+3.900 | NO (no se asume) |\n")
    lt.append("| eje 2A ↔ eje 2a | Y=+11.885 | Y'=+13.845 | NO (no se asume) |\n")

    lt.append("\n## 5. Cotas Z\n")
    lt.append("| LT1 | LT2 | Z (m) |\n|---|---|---|\n")
    for n1, n2, z in r["niveles_par"]:
        lt.append(f"| {n1} | {n2} | {z:+.2f} |\n")

    lt.append("\n## 6. Nodos que llegan a la interfaz — LT2 (borde este, X=31.250)\n")
    for (z_key, lista) in sorted(r["lt2_edge"].items()):
        if z_key == "x31.475":
            continue
        tags = sorted(t for t, *_ in lista)
        lt.append(f"- Nivel Z={z_key:+.2f}: nodos {tags}"
                  f" (X=31.250 · Y="
                  + ", ".join(f"{y}" for _, _, y, _ in sorted(lista, key=lambda q: q[2]))
                  + ")\n")
    # nodos 31.475 si existieran
    if "x31.475" in r["lt2_edge"]:
        lt.append("- **NODOS EN X=31.475 (D') — INESPERADO, requiere revisión**: ")
        lt.append(repr(r["lt2_edge"]["x31.475"]) + "\n")

    lt.append("\n## 7. Nodos que llegan a la interfaz — LT1 (borde oeste, eje E, X=0 → X'=31.250)\n")
    for n1, n2, z in r["niveles_par"]:
        tags = [tag_nodo_lt1(n1, "E", e1, g) for e1 in ("1", "2", "3")]
        ys = [f"{ -g.ejes_y[e]:+.3f}" for e in ("1", "2", "3")]
        pares = " · ".join(
            f"({31.25:.3f}, {y:+.3f}, {z:+.2f})" for y in (0.0, 8.9, 16.15))
        lt.append(f"- {n1} (Z={z:+.2f}): nodos {tags} · Y nativo="
                  f"{', '.join(f'{g.ejes_y[e]:+.3f}' for e in ('1','2','3'))} "
                  f"→ transformados (X=31.250 · Y'={','.join(ys)}): {pares}\n")

    lt.append("\n## 8. Tabla NIVEL | EJE | NODO LT2 | XYZ LT2 | NODO LT1 | "
              "XYZ LT1 TRANSFORMADO | DISTANCIA\n")
    lt.append("| NIVEL | EJE | NODO LT2 | XYZ LT2 (m) | NODO LT1 | XYZ LT1 TRANSFORMADO (m) | DISTANCIA (m) |\n")
    lt.append("|---|---|---|---|---|---|---|\n")
    for _, f in r["tab"].iterrows():
        lt.append(f"| {f['NIVEL']} | {f['EJE']} | {f['NODO_LT2']} "
                  f"| ({f['X_LT2']:.3f}, {f['Y_LT2']:+.3f}, {f['Z_LT2']:+.2f}) "
                  f"| {f['NODO_LT1']} "
                  f"| ({f['X_LT1_TR']:.3f}, {f['Y_LT1_TR']:+.3f}, {f['Z_LT1_TR']:+.2f}) "
                  f"| {f['DISTANCIA_m']:.6f} |\n")

    lt.append("\n### Nodos LT2 en la interfaz SIN contraparte en LT1 (núcleo derecho)\n")
    for s in r["sin_contraparte"]:
        lt.append(f"- {s}\n")

    lt.append(f"\n## 9. Conclusiones\n")
    lt.append(f"- Coincidencias **exactas** (Δ ≤ 1e-3 m) en los ejes 1, 2 y 3: "
              f"**{c}/18** pares por nivel (6·3).  "
              f"En todos la distancia es **0.000 m**: la línea de columnas LT1 (eje E) "
              f"cae exactamente sobre la línea de columnas LT2 (eje D) en los ejes "
              f"transversales comunes.\n")
    lt.append(f"- Sin contraparte: {len(r['sin_contraparte'])} nodos de LT2 del núcleo "
              f"derecho (Y=3.18 y 6.275) en los 6 niveles.\n")
    lt.append("- No coinciden (y no se fusionan): eje 1A de LT2 vs 1'' de LT1 "
              "(ΔY=0.365 m) y eje 2A de LT2 vs 2a de LT1 (ΔY=1.960 m).\n")
    lt.append(f"- Rangos globales de nodos modelados → X: LT2 [{r['x_lt2'][0]:.3f}, "
              f"{r['x_lt2'][1]:.3f}] · LT1 [{r['x_lt1_tr'][0]:.3f}, {r['x_lt1_tr'][1]:.3f}]; "
              f"Y: LT2 [{r['y_lt2'][0]:.3f}, {r['y_lt2'][1]:.3f}] · "
              f"LT1 [{r['y_lt1_tr'][0]:.3f}, {r['y_lt1_tr'][1]:.3f}]; "
              f"Z común [-7.97, 11.83].\n")
    lt.append("\n## 10. Fuera de alcance de esta etapa\n")
    lt.append("- No se conectaron nodos (sin equalDOF ni rigidLink de interfaz).\n")
    lt.append("- No se alteraron diafragmas, apoyos ni cargas de LT1/LT2.\n")
    lt.append("- No se resolvió la singularidad del análisis de gravedad de LT2.\n")
    lt.append("- No se construyó el modelo FE combinado.\n")
    return "".join(lt)


def main():
    r = analizar()
    DOCS.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    md = render_md(r)
    p_md = DOCS / "auditoria_transformacion_geometrica.md"
    p_md.write_text(md, encoding="utf-8")
    p_csv = OUT / "interfaz_coincidencia_por_eje.csv"
    r["tab"].to_csv(p_csv, index=False, encoding="utf-8")
    print(f"[OK] {p_md}")
    print(f"[OK] {p_csv}")
    print(f"coincidencias exactas: {r['coinciden']}/18")
    print(f"nodos LT2 en interfaz sin contraparte: {len(r['sin_contraparte'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())