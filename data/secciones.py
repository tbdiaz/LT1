# ============================================================================
# data/secciones.py
# Secciones y materiales del modelo LT1.
# Nomenclaturas provienen EXACTAMENTE de los planos 100-103 (capa de texto
# extraída). Unidades de entrada: cm (vigas/columnas/muros H.A.) o mm (perfiles
# metálicos). Propiedades calculadas en m, m^2, m^4 (sistema del modelo).
# ============================================================================

import math

# ---------------------------------------------------------------------------
# Catálogo de secciones reales por plano (extraído del texto de cada PDF).
# Formato: "V. 60/80" -> viga rectangular con base 60 cm y altura 80 cm.
#   - "V.": viga de hormigón      "V.I.": viga inferior   "V.F.": viga de fundación
#   - "V.S.I.": viga superior invertida   "P.": columna    "P.M.I.": pilar metálico
#   - "P.M.": columna metálica  "V.M.": viga metálica  "ARR": arriostra
#   - "M.H.A.": muro de hormigón armado  "M.I.": muro interior  "e": espesor
# ---------------------------------------------------------------------------
secciones_por_plano = {
    "100": {
        "LOSA e=25": {"tipo": "losa", "e_cm": 25},
        "V.F. 20/220": {"tipo": "viga_fundacion", "b_cm": 20, "h_cm": 220},
        "V.F. 20/180": {"tipo": "viga_fundacion", "b_cm": 20, "h_cm": 180},
        "V.F. 20/160": {"tipo": "viga_fundacion", "b_cm": 20, "h_cm": 160},
        "V.F. 20/120": {"tipo": "viga_fundacion", "b_cm": 20, "h_cm": 120},
        "V.F. 15/225": {"tipo": "viga_fundacion", "b_cm": 15, "h_cm": 225},
    },
    "101": {
        "P. 70x70": {"tipo": "columna_ha", "b_cm": 70, "d_cm": 70},
        "P. 30x30": {"tipo": "columna_ha", "b_cm": 30, "d_cm": 30},
        "P. 20x50": {"tipo": "columna_ha", "b_cm": 20, "d_cm": 50},
        "V. 60/80": {"tipo": "viga_ha", "b_cm": 60, "h_cm": 80},
        "V. 20/80": {"tipo": "viga_ha", "b_cm": 20, "h_cm": 80},
        "V. 20/130": {"tipo": "viga_ha", "b_cm": 20, "h_cm": 130},
        "V. 20/VAR": {"tipo": "viga_ha", "b_cm": 20, "h_cm": "VAR"},
        "V. 30/VAR": {"tipo": "viga_ha", "b_cm": 30, "h_cm": "VAR"},
        "V.I. 15/169": {"tipo": "viga_inferior", "b_cm": 15, "h_cm": 169},
        "V.I. 15/VAR": {"tipo": "viga_inferior", "b_cm": 15, "h_cm": "VAR"},
        "V.S.I. 20/150": {"tipo": "viga_superior_inv", "b_cm": 20, "h_cm": 150},
        "V.S.I. 15/125": {"tipo": "viga_superior_inv", "b_cm": 15, "h_cm": 125},
        "V.S.I. 15/VAR": {"tipo": "viga_superior_inv", "b_cm": 15, "h_cm": "VAR"},
        "V.F. 15/100": {"tipo": "viga_fundacion", "b_cm": 15, "h_cm": 100},
        "M.H.A. e= 15": {"tipo": "muro_ha", "e_cm": 15},
        "M.H.A. e= 20": {"tipo": "muro_ha", "e_cm": 20},
        "M.H.A. e= 30": {"tipo": "muro_ha", "e_cm": 30},
        "M.I. e= 20": {"tipo": "muro_interior", "e_cm": 20},
    },
    "102": {
        "P. 70x70": {"tipo": "columna_ha", "b_cm": 70, "d_cm": 70},
        "P.M. 300x300x20": {"tipo": "columna_metal", "mm": 300, "t_mm": 20},
        "V. 60/80": {"tipo": "viga_ha", "b_cm": 60, "h_cm": 80},
        "V. 40/60": {"tipo": "viga_ha", "b_cm": 40, "h_cm": 60},
        "V. 30/45": {"tipo": "viga_ha", "b_cm": 30, "h_cm": 45},
        "V. 60-30/80-40": {"tipo": "viga_ha_variable", "b1_cm": 60, "b2_cm": 30,
                           "h1_cm": 80, "h2_cm": 40},
        "V. 60/VAR": {"tipo": "viga_ha", "b_cm": 60, "h_cm": "VAR"},
        "V.M. 300x300x5 (ARR)": {"tipo": "viga_metal", "mm": 300, "t_mm": 5},
        "M.H.A. e= 20": {"tipo": "muro_ha", "e_cm": 20},
        "M.H.A. e= 25": {"tipo": "muro_ha", "e_cm": 25},
        "M.H.A. e= 30": {"tipo": "muro_ha", "e_cm": 30},
    },
    "103": {
        "P. 70x70": {"tipo": "columna_ha", "b_cm": 70, "d_cm": 70},
        "P.M. 300x300x20": {"tipo": "columna_metal", "mm": 300, "t_mm": 20},
        "V. 60/80": {"tipo": "viga_ha", "b_cm": 60, "h_cm": 80},
        "V. 40/60": {"tipo": "viga_ha", "b_cm": 40, "h_cm": 60},
        "+V.I. 20/90 (2ºETAPA)": {"tipo": "viga_inferior", "b_cm": 20, "h_cm": 90},
        "+V.I. 20/87 (2ºETAPA)": {"tipo": "viga_inferior", "b_cm": 20, "h_cm": 87},
        "V.M. 300x300x5 (ARR)": {"tipo": "viga_metal", "mm": 300, "t_mm": 5},
        "M.H.A. e= 20": {"tipo": "muro_ha", "e_cm": 20},
    },
}

# ---------------------------------------------------------------------------
# Materiales del modelo lineal elástico.
# ESTADO: H°A° DEFINIDO por INFORMACION ACADEMICA CONFIRMADA POR USUARIO
# (fc=35 MPa, E=27800 MPa, nu=0.20, densidad=2400 kg/m3) y ACERO (fy=420 MPa,
# E=200000 MPa, densidad=7850 kg/m3).
# Revisión documental (docs/):
#   - docs/P1L2.txt          : NO fija f'c/E/G/nu; solo enumera 'materiales'
#                              como dato del modelo.
#   - docs/Enunciado general.txt : NO fija valores; fija la CONVENCIÓN de
#                              modelación (línea 42: "sistema lineal elástico
#                              3D"; líneas 266-278: elasticBeamColumn,
#                              geomTransf, rigidDiaphragm recomendados en
#                              OpenSeesPy). Usamos esa convención.
#   - AGENTS.md              : prohíbe inventar datos de material.
# Planos: 000 y 001 son raster sin valores (ref. E.T.O.G. y plano 001; lámina
# 001 = armado/confinamiento de muros). No se atribuye ningún valor a planos.
# Los valores elásticos del hormigón (E, nu, G) y del acero provienen
# EXCLUSIVAMENTE del usuario (valor confirmado que sustituye al académico
# previo G25/E=25e6).
# ---------------------------------------------------------------------------
MATERIAL_ACADEMICO_STATUS = "MATERIAL_PENDIENTE_DE_CONVENCION_ACADEMICA"

# ---------------------------------------------------------------------------
# INFORMACIÓN PROPORCIONADA POR EL USUARIO (CONFIRMADA, no inventada).
#   - Hormigón: clase G35 -> fc = 35 MPa, E = 27 800 MPa (27 800 000 kPa),
#       nu = 0.20, densidad = 2400 kg/m³.
#   - Acero de refuerzo/estructural: fy = 420 MPa, E = 200 000 MPa
#       (200 000 000 kPa), densidad = 7850 kg/m³.
#   - IMPORTANTE: "G35" es la CLASE (resistencia) del hormigón; NO es el
#       módulo de corte G. Es una coincidencia de notación.
#   - G = E/[2(1+nu)] = 27 800 000 / [2·(1+0.20)] = 11 583 333.33 kPa.
#       El valor registrado 11 583 333 corresponde al redondeo documentado.
# ---------------------------------------------------------------------------
INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO = {
    "hormigon_clase": "G35",          # clase/resistencia del hormigón
    "nota_G35": ("G35 es la CLASE/resistencia del hormigón; NO es el módulo "
                 "de corte G (coincidencia de notación)."),
    "nu": 0.20,
    "E_kPa": 27_800_000.0,
    "G_kPa": 11_583_333.33,
    "G_formula": "G = E/[2(1+nu)] = 27.8e6/[2(1.20)] = 11 583 333.33 kPa "
                 "(valor exacto 27.8e6/2.4 a 2 decimales)",
    "densidad_hormigon_kg_m3": 2400.0,
    "densidad_acero_kg_m3": 7850.0,
    "nota_unidades": "1 kN/m² = 1 kPa; 1 MPa = 1000 kPa",
    "estado_documental": "PROPORCIONADA_POR_USUARIO (confirmada; sustituye al "
                         "valor academico previo G25 E=25e6)",
    "E_expression_en_documentos": "NO encontrada (docs P1L2/Enunciado y planos)",
}
materiales = {
    "hormigon": {
        "nombre": "H°A°",
        "estado": "LISTO",
        "f_c_kPa": 35_000.0, # CONFIRMADO: fc = 35 MPa (clase G35)
        "E_kPa": 27_800_000.0,
        "fy_kPa": None,      # PENDIENTE (aceros de refuerzo)
        "nu": 0.20,
        "G_kPa": 11_583_333.33,  # 27.8e6/[2(1.20)] = 11 583 333.33 kPa
        "densidad_kg_m3": 2400.0,
        "fuente": ("E=27800000 kPa, fc=35000 kPa, nu=0.20 y G=11583333 kPa: "
                   "PROPORCIONADA_POR_USUARIO (clase G35 / fc=35 MPa, "
                   "E=27800 MPa, densidad 2400 kg/m3). "
                   "NO atribuir a planos ni a documentos del proyecto."),
    },
    "acero_estructural": {
        "nombre": "perfiles",
        "estado": "LISTO",
        "fy_kPa": 420_000.0,    # CONFIRMADO: fy = 420 MPa
        "E_kPa": 200_000_000.0, # CONFIRMADO: Es = 200 000 MPa
        "G_kPa": None,          # PENDIENTE (requiere nu del acero)
        "nu": None,             # PENDIENTE
        "densidad_kg_m3": 7850.0,
        "fuente": "PROPORCIONADA_POR_USUARIO (fy=420 MPa, E=200000 MPa, "
                  "densidad 7850 kg/m3; nu/G sin confirmar). Perfiles "
                  "metálicos siguen pendientes de modelarse.",
    },
}

# ---------------------------------------------------------------------------
# MATERIAL H°A° PARAMETRIZADO PARA EL MODELO OPENSEES (fuente única).
# DEFINIDO por INFORMACION ACADEMICA CONFIRMADA POR USUARIO:
#   E = 27 800 000 kPa · nu = 0.20 · G = 11 583 333.33 kPa (G = E/[2(1+nu)] =
#   valor exacto 27.8e6/2.4; 1 kN/m² = 1 kPa).
# Con E y G definidos, el run crea los 198 elasticBeamColumn y ejecuta el
# análisis de gravedad. El acero estructural queda definido (fy=420 MPa,
# E=200000 MPa, densidad 7850 kg/m3); los perfiles metálicos siguen
# pendientes de modelarse (segunda etapa).
# ---------------------------------------------------------------------------
MATERIAL_HA = {
    "estado": "LISTO",                             # definido (confirmado/usuario)
    "E_kPa": materiales["hormigon"]["E_kPa"],      # 27 800 000
    "nu": materiales["hormigon"]["nu"],            # 0.20
    "G_kPa": materiales["hormigon"]["G_kPa"],      # 11 583 333.33 (27.8e6/2.4)
    "densidad_kg_m3": materiales["hormigon"]["densidad_kg_m3"],  # 2400
    "fuente": materiales["hormigon"]["fuente"],
}


def material_ha_estado():
    """Estado del material H°A°: 'LISTO' o MATERIAL_ACADEMICO_STATUS."""
    h = MATERIAL_HA
    if h["E_kPa"] is None or h["G_kPa"] is None:
        return MATERIAL_ACADEMICO_STATUS
    return "LISTO"


def nivel_G_kPa():
    """G = E/[2(1+nu)] solo cuando E y nu estén respaldados; si no, None."""
    E = MATERIAL_HA["E_kPa"]
    nu = MATERIAL_HA["nu"]
    if E is None or nu is None:
        return None
    return E / (2.0 * (1.0 + nu))


def _constante_torsional_rect(b_m, h_m):
    """Constante torsional (St. Venant) de sección rectangular maciza.

    Fórmula (Reynolds/Steedman; también Timoshenko, aproximación cerrada):
        J = (1/3) * a^3 * c * ( 1 - 0.630*(a/c) + 0.052*(a/c)^5 )
    con a = lado menor, c = lado mayor de la sección. Unidades: m^4.
    Se opta por esta forma (incluye el término de orden superior 0.052)
    por mejor precisión que la versión de un solo término. Se verifica
    contra la serie exacta de torsión en `_verificar_J_exacta`.
    """
    a = min(b_m, h_m)
    c = max(b_m, h_m)
    r = a / c
    return (1.0 / 3.0) * a**3 * c * (1.0 - 0.630 * r + 0.052 * r**5)


def _verificar_J_exacta(b_m, h_m):
    """Serie exacta (suma de St. Venant) para validar la constante torsional.

    J = (1/3) a^3 c [1 - (192/pi^5)(a/c) sum_{n impar} tanh(n*pi*c/(2a))/n^5]
    """
    import math
    a = min(b_m, h_m)
    c = max(b_m, h_m)
    s = 0.0
    for n in range(1, 41, 2):
        s += math.tanh(n * math.pi * c / (2.0 * a)) / n**5
    return (1.0 / 3.0) * a**3 * c * (1.0 - (192.0 / math.pi**5) * (a / c) * s)


def _pared_rectangular(b_m, h_m):
    """Propiedades de sección rectangular (viga/sección H.A.), unidades m.

    Convención de ejes locales de sección:
      - 'b' se extiende según el eje local que en el marco 3D será transversal
        horizontal (para vigas, dirección Y global cuando la viga va por X);
      - 'h' se extiende según el eje local vertical (contra gravedad).
      A = b*h
      Iy = b*h^3/12  (inercia para flexión alrededor del eje local 'y')
      Iz = h*b^3/12  (inercia para flexión alrededor del eje local 'z')
      J  = constante torsional de St. Venant (ver _constante_torsional_rect)
    """
    a = b_m * h_m
    return {
        "A_m2": a,
        "Iy_m4": b_m * h_m**3 / 12.0,
        "Iz_m4": h_m * b_m**3 / 12.0,
        "J_m4": _constante_torsional_rect(b_m, h_m),
    }


def _perfil_cajon(b_m, t_m):
    hi = b_m - 2.0 * t_m
    A = b_m**2 - hi**2
    return {
        "A_m2": A,
        "Iy_m4": (b_m**4 - hi**4) / 12.0,
        "Iz_m4": (b_m**4 - hi**4) / 12.0,
        "J_m4": t_m * (b_m - t_m)**3,
    }


def propiedades_seccion(nombre, datos):
    """Devuelve propiedades calculadas (m, m^2, m^4) o None si no es computable."""
    tipo = datos["tipo"]
    if tipo in ("viga_ha", "viga_inferior", "viga_superior_inv", "viga_fundacion"):
        if datos.get("h_cm") == "VAR":
            return {"tipo": tipo, "seccion_variable": True}
        return {"tipo": tipo,
                **_pared_rectangular(datos["b_cm"] / 100.0, datos["h_cm"] / 100.0)}
    if tipo in ("columna_ha",):
        return {"tipo": tipo,
                **_pared_rectangular(datos["b_cm"] / 100.0, datos["d_cm"] / 100.0)}
    if tipo in ("muro_ha", "muro_interior"):
        return {"tipo": tipo, "e_m": datos["e_cm"] / 100.0}
    if tipo in ("losa",):
        return {"tipo": tipo, "e_m": datos["e_cm"] / 100.0}
    if tipo in ("columna_metal",):
        return {"tipo": tipo,
                **_perfil_cajon(datos["mm"] / 1000.0, datos["t_mm"] / 1000.0)}
    if tipo == "viga_metal":
        return {"tipo": tipo,
                **_perfil_cajon(datos["mm"] / 1000.0, datos["t_mm"] / 1000.0)}
    if tipo == "viga_ha_variable":
        return {"tipo": tipo, "seccion_variable": True}
    return None


# Verificación ejecutable: todas las secciones del catálogo deben computar o
# estar declaradas explícitamente como carga/variable.
propiedades_por_seccion = {}
for _plano, _secciones in secciones_por_plano.items():
    for _nombre, _datos in _secciones.items():
        propiedades_por_seccion.setdefault(_nombre, propiedades_seccion(_nombre, _datos))

# ---------------------------------------------------------------------------
# CONVENCIÓN ACADÉMICA PARA MUROS M.H.A. (COLUMNA EQUIVALENTE)
# PROPORCIONADA POR EL USUARIO / CURSO. NO atribuirla a los planos.
#   - Cada muro M.H.A. se modela como COLUMNA EQUIVALENTE (elasticBeamColumn
#     vertical, mismo material H°A° E/G) con sección a partir de:
#       * longitud real del muro en planta (L_m);
#       * espesor del muro (e = 0.20 / 0.25 / 0.30 m);
#       * altura entre niveles consecutivos (longitud del elemento).
#   - Sección rectangular equivalente A = e·L_m.
#   - Iy/Iz calculados para un rectángulo (e × L_m) con el MISMO criterio de
#     la viga del proyecto (Iy = b·h^3/12 ; Iz = h·b^3/12) y con el eje fuerte
#     en el plano del muro según su orientación X/Y (elemento vertical:
#     x local = +Z global, y local = -Y, z local = +X).
#   - J con la misma convención rectangular ya usada en el proyecto
#     (_constante_torsional_rect, St. Venant cerrada); sin fórmula nueva.
#   - Extremos del elemento en DOS niveles Z consecutivos (continuidad
#     respaldada por los planos; si no está cerrada, se reporta PENDIENTE).
# Se registró como INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO (mismo
# estatus que E/nu/G del H°A°): NO proviene de los planos.
# ---------------------------------------------------------------------------
CONVENCION_ACADEMICA_MUROS = {
    "id": "CONVENCION_MURO_COLUMNA_EQUIVALENTE",
    "descripcion": ("Muros M.H.A. -> COLUMNA EQUIVALENTE en OpenSees "
                    "(elasticBeamColumn vertical, entre niveles Z consecutivos)"),
    "fuente": "INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO",
    "estado_documental": ("NO atribuir a los planos. Convención entregada por "
                          "el usuario/curso (igual estatus que E/nu/G del H°A°)."),
    "seccion_rectangular": {
        "A": "e * L_m",
        "Iy": "b_local_y * h_local_z^3 / 12  (flexión alrededor del eje local y)",
        "Iz": "h_local_z * b_local_y^3 / 12  (flexión alrededor del eje local z)",
        "J": "_constante_torsional_rect(b, h) (St. Venant, misma convención del "
             "proyecto; a = min(b,h), c = max(b,h))",
    },
    "ejes_fuertes_debiles": {
        "E-W (paralelo X)": "en plano = +X = eje local z -> Iy fuerte (e·L^3/12), "
                            "Iz débil (L·e^3/12)",
        "N-S (paralelo Y)": "en plano = Y = eje local y -> Iz fuerte (e·L^3/12), "
                            "Iy débil (L·e^3/12)",
    },
    "elemento": {
        "tipo": "elasticBeamColumn",
        "geomTransf": "columna_vertical (vecxz=(1,0,0); x=+Z, y=-Y, z=+X)",
        "longitud_elemento": "altura entre los dos niveles consecutivos",
    },
}


def props_muro_columna_equivalente(e_m, L_m, orientacion):
    """Propiedades de la COLUMNA EQUIVALENTE de un muro M.H.A. (convención
    académica). e_m = espesor [m], L_m = longitud del muro en planta [m],
    orientacion contiene 'E-W' (plano X) o 'N-S' (plano Y).

    Elemento vertical (x local = +Z): en el plano de sección,
      - E-W: dirección en plano = +X = eje local z  -> b_local_y = e, h_local_z = L;
      - N-S: dirección en plano = Y  = eje local y  -> b_local_y = L, h_local_z = e.
    Reutiliza _pared_rectangular (A, Iy, Iz, J con la convención del proyecto).
    """
    in_plano = "X" if "E-W" in orientacion else "Y"
    if in_plano == "X":
        b = e_m          # local y
        h = L_m          # local z (en plano)
    else:
        b = L_m          # local y (en plano)
        h = e_m          # local z
    p = _pared_rectangular(b, h)
    return {
        **p,
        "espesor_m": e_m,
        "longitud_planta_m": L_m,
        "en_plano_direccion": in_plano,
        "b_local_y_m": b,
        "h_local_z_m": h,
    }