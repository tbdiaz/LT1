# ============================================================================
# data/tributacion.py
# Paños de losa y áreas tributarias del esqueleto LT1.
# La losa NO se modela con elementos finitos: cada paño es solo información
# geométrica/carga (nivel, límites, área, espesor, q_G, SC, fuente) y la carga
# se transfiere a las vigas mediante áreas tributarias explícitas.
#
# Método tributario: partición por BISECTRICES (Voronoi de las vigas) sobre
# cada paño rectangular. Para un paño Lx×Ly con Lx >= Ly:
#   - vigas paralelas al lado LARGO (longitud Lx): A = Lx·Ly/2 − Ly²/4
#   - vigas paralelas al lado CORTO (longitud Ly): A = Ly²/4
# (si Lx < Ly, los papeles se intercambian).
# La suma de las 4 áreas de cada paño es exactamente Lx·Ly -> conservación
# exacta por paño (dentro de tolerancia numérica).
# ============================================================================

import math

# Límites de paños (retícula del esqueleto, ejes verificados):
#   X:  E=0 F=10 G=20 H=30 I=40 I'=42.5
#   Y:  1=0 2=-8.9 3=-16.15
PAÑOS_X = [("E", "F", 10.0), ("F", "G", 10.0), ("G", "H", 10.0),
           ("H", "I", 10.0), ("I", "I'", 2.5)]
PAÑOS_Y = [("1", "2", 8.9), ("2", "3", 7.25)]


def area_borde_paño(Lx, Ly, horizontal=True):
    """Área tributaria de un borde de paño rectangular (método de bisectrices).

    horizontal=True -> borde coincidente con viga paralela a X (longitud Lx),
    horizontal=False -> borde coincidente con viga paralela a Y (longitud Ly).
    """
    if horizontal:
        if Lx >= Ly:
            return Lx * Ly / 2.0 - Ly * Ly / 4.0
        return Lx * Lx / 4.0
    if Ly >= Lx:
        return Lx * Ly / 2.0 - Lx * Lx / 4.0
    return Ly * Ly / 4.0


def paños_por_nivel(nivel, q_G_kPa=None, sc_kPa=None, fuente_qG="", fuente_sc="",
                     e_m=0.20, qG_map=None):
    """Genera los paños de losa de un nivel.

    Si se proporciona qG_map (dict {pano_id: qG_kPa}), se usa q_G por-paño.
    Si no, se usa q_G_kPa uniforme (fallback para compatibilidad).
    qG_map tiene prioridad sobre q_G_kPa.
    """
    paños = []
    for _ix, (_xa, _xb, _lx) in enumerate(PAÑOS_X):
        for _iy, (_ya, _yb, _ly) in enumerate(PAÑOS_Y):
            _area = _lx * _ly
            _pid = f"{nivel}_P{_ix + 1}{_iy + 1}"
            _qg = qG_map[_pid] if (qG_map and _pid in qG_map) else (q_G_kPa or 0.0)
            _sc = sc_kPa if sc_kPa else 0.0
            paños.append({
                "id": _pid,
                "nivel": nivel,
                "eje_x0": _xa, "eje_x1": _xb, "Lx": _lx,
                "eje_y0": _ya, "eje_y1": _yb, "Ly": _ly,
                "area_m2": _area,
                "q_G_kPa": _qg,
                "SC_kPa": _sc,
                "e_m": e_m,
                "fuente_qG": "ZONAL" if (qG_map and _pid in qG_map) else fuente_qG,
                "fuente_SC": fuente_sc,
                "estado": "GEOMETRIA_REGULAR",
            })
    return paños


def _buscar_viga(vigas, nivel, **claves):
    """Busca en la lista de vigas del nivel la que coincide con todas las claves."""
    for v in vigas:
        if v["nivel"] != nivel:
            continue
        ok = True
        for k, val in claves.items():
            if v.get(k) != val:
                ok = False
                break
        if ok:
            return v
    return None


def tributacion_nivel(nivel, vigas, nodos, paños, q_G_kPa=None):
    """Calcula área tributaria y carga de losa por viga para un nivel.

    vigas: lista de registros de vigas_por_nivel[nivel].
    nodos: dict coord por nodeTag.
    q_G_kPa: fallback uniforme si paños no tienen q_G_kPa propio.
    Cada paño puede tener su propio q_G_kPa (per-panel), que tiene prioridad.
    """
    result = {}
    by_tag = {v["element_tag"]: v for v in vigas}
    asignado = {t: 0.0 for t in by_tag}
    origen = {t: [] for t in by_tag}
    carga_pano = {t: 0.0 for t in by_tag}
    sc_pano = {t: 0.0 for t in by_tag}
    bordes_sin_viga = []

    A_total = 0.0
    P_total = 0.0
    for p in paños:
        A_total += p["area_m2"]
        Lx, Ly = p["Lx"], p["Ly"]
        xa, xb, ya, yb = p["eje_x0"], p["eje_x1"], p["eje_y0"], p["eje_y1"]
        qg = p.get("q_G_kPa", q_G_kPa or 0.0)
        sc = p.get("SC_kPa", 0.0)
        P_pano = qg * p["area_m2"]
        P_total += P_pano
        # borde inferior/superior (vigas paralelas a X)
        for y_linea, tag_nombre in ((ya, "Y0"), (yb, "Y1")):
            v = _buscar_viga(vigas, nivel,
                             eje_x_i=xa, eje_x_j=xb,
                             eje_y_i=y_linea, eje_y_j=y_linea)
            A = area_borde_paño(Lx, Ly, horizontal=True)
            if v is None:
                bordes_sin_viga.append(f"{p['id']} borde X {tag_nombre} (Y={y_linea})")
                continue
            tag = v["element_tag"]
            asignado[tag] += A
            origen[tag].append(f"{p['id']}:{tag_nombre}")
            carga_pano[tag] += qg * A
            sc_pano[tag] += sc * A
        # borde izquierdo/derecho (vigas paralelas a Y)
        for x_linea, tag_nombre in ((xa, "X0"), (xb, "X1")):
            v = _buscar_viga(vigas, nivel,
                             eje_y_i=ya, eje_y_j=yb,
                             eje_x_i=x_linea, eje_x_j=x_linea)
            A = area_borde_paño(Lx, Ly, horizontal=False)
            if v is None:
                bordes_sin_viga.append(f"{p['id']} borde Y {tag_nombre} (X={x_linea})")
                continue
            tag = v["element_tag"]
            asignado[tag] += A
            origen[tag].append(f"{p['id']}:{tag_nombre}")
            carga_pano[tag] += qg * A
            sc_pano[tag] += sc * A

    # longitud real por viga desde nodos
    cargas = {}
    for tag, v in by_tag.items():
        (xi, yi, zi) = nodos[v["nodo_i"]]
        (xj, yj, zj) = nodos[v["nodo_j"]]
        L = math.hypot(xj - xi, yj - yi)
        cargas[tag] = {"A_trib": asignado[tag],
                       "P_losa_kN": carga_pano[tag],
                       "w_kN_m": (carga_pano[tag] / L) if L else 0.0,
                       "longitud_m": L,
                       "origen": origen[tag],
                       "element_tag": tag,
                       "nivel": nivel,
                       "clave": v.get("clave"),
                       "orientacion": "X" if v["eje_x_i"] != v["eje_x_j"] else "Y",
                       "nodo_i": v["nodo_i"], "nodo_j": v["nodo_j"],
                       "eje_x_i": v["eje_x_i"], "eje_x_j": v["eje_x_j"],
                       "eje_y_i": v["eje_y_i"], "eje_y_j": v["eje_y_j"],
                       "SC_peso_trib_kN": sc_pano[tag],
                       "q_G_kPa_usado": None}

    # registrar q_G por paño en cada viga
    for tag, c in cargas.items():
        if c["origen"]:
            pano_ids = [s.split(":")[0] for s in c["origen"]]
            qg_vals = set()
            for pid in pano_ids:
                for p in paños:
                    if p["id"] == pid:
                        qg_vals.add(round(p["q_G_kPa"], 4))
            c["q_G_kPa_usado"] = sorted(qg_vals) if qg_vals else [q_G_kPa or 0.0]

    P_vigas = sum(c["P_losa_kN"] for c in cargas.values())
    error = abs(P_total - P_vigas) / P_total if P_total else float("nan")

    return {
        "nivel": nivel,
        "paños": paños,
        "A_total_m2": A_total,
        "q_G_kPa": q_G_kPa,
        "P_losa_total_kN": P_total,
        "P_vigas_kN": P_vigas,
        "error_relativo": error,
        "vigas_carga": cargas,
        "bordes_sin_viga": bordes_sin_viga,
    }


def verificar_conservacion(metricas):
    """Verificaciones de conservación por nivel. Retorna dict {ok, resumen}."""
    resumen = {}
    ok = True
    for nivel, m in metricas.items():
        tol = 1e-9
        e = m["error_relativo"]
        resumen[nivel] = {
            "A_losa_m2": m["A_total_m2"],
            "q_G_kPa_representativo": m.get("q_G_kPa"),
            "P_losa_total_kN": m["P_losa_total_kN"],
            "P_vigas_kN": m["P_vigas_kN"],
            "error_relativo": e,
            "dentro_tolerancia": bool(e < tol),
            "vigas_con_carga": sum(1 for c in m["vigas_carga"].values()
                                   if c["P_losa_kN"] > 1e-12),
            "vigas_sin_carga": sum(1 for c in m["vigas_carga"].values()
                                   if c["P_losa_kN"] <= 1e-12),
            "bordes_sin_viga": m["bordes_sin_viga"],
        }
        if e >= tol:
            ok = False
    return {"ok": ok, "resumen": resumen}
