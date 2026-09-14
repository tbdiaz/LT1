# ============================================================================
# data/cargas.py
# Cargas gravitacionales del modelo LT1. Unidades: kPa (kN/m^2).
# P1L2: q_G = peso propio de losa + terminaciones, con áreas tributarias
# explícitas (sin modelar la losa como elemento finito).
# SC se registra aparte y NO se suma a q_G.
# Fuente: plano 700 (PLANTAS DE CARGAS CIELO 1° SUBTE. a 4° PISO).
# Lectura celda por celda desde tiles de alta resolución (Matrix 5x5).
# ============================================================================

G_MS2 = 9.80665


def kgf_m2_a_kPa(kgf_m2):
    return kgf_m2 * G_MS2 / 1000.0


# ---------------------------------------------------------------------------
# RESOLUCIÓN ESPESETESOR: e = 0.20 m (PISOS) vs 0.25 m (FUNDACIONES)
# ---------------------------------------------------------------------------
# Plan 100 "LOSA e=25" → hoja FUNDACIONES → e = 0.25 m (losa de fundación, -7.97 m).
# Plan 700 PP.LOSA = 500 kgf/m² → e = 500/2500 = 0.20 m (losas de piso, PISO_1..4).
# Son ELEMENTOS DISTINTOS. No hay contradicción.
#
# ACTUALIZACION MATERIALES (usuario): densidad hormigon confirmada = 2400 kg/m3.
#   - PP.LOSA = e x 2400 = 0.20 x 2400 = 480 kgf/m2 (era 500 con gamma=2500).
#   - gamma_losa_kgf_m3 = 2400.0 ; peso_especifico = 24.5166 -> 23.53596 kN/m3.
# Se conserva la trazabilidad al plano 700 (PP.LOSA=500 con gamma=2500) en
# info_plano_700, pero el valor de modelado pasa a usar la densidad confirmada.
# ---------------------------------------------------------------------------
e_losa_m = 0.20
pp_losa_kgf_m2 = 480.0
gamma_losa_kgf_m3 = 2400.0
peso_especifico_ha_kN_m3 = gamma_losa_kgf_m3 * G_MS2 / 1000.0   # 23.53596

# ---------------------------------------------------------------------------
# INFORMACIÓN GENERAL PLANO 700
# ---------------------------------------------------------------------------
info_plano_700 = {
    "plano": "2017_67-700",
    "titulo": "PLANTAS DE CARGAS CIELO 1° SUBT. a 4° PISO",
    "definicion_pp_losa_plano": "PP. LOSA = e(m) x 2500 Kg/m3 (traza del plano)",
    "gamma_losa_plano_kgf_m3": 2500.0,   # valor del plano 700 (trazabilidad)
    "gamma_losa_confirmada_kgf_m3": gamma_losa_kgf_m3,  # 2400 (usuario)
    "e_losa_pisos_m": e_losa_m,
    "pp_losa_plano_kgf_m2": 500.0,       # valor del plano 700 (trazabilidad)
    "pp_losa_confirmado_kgf_m2": pp_losa_kgf_m2,  # 480 (densidad confirmada 2400)
    "fecha": "22/02/2018 · DESARROLLO PRELIMINAR PROPUESTA X CONSTRUCCION",
    "metodo_lectura": "OCR Vision (tools/ocr_file.py) sobre tiles Matrix(5,5)",
    "resolucion_e": (
        "e=0.20 m corresponde a losas de piso (plan 700, PP.LOSA=500 con "
        "gamma=2500). e=0.25 m (plan 100 'LOSA e=25') corresponde a la losa "
        "de FUNDACIONES (hoja de fundaciones, nivel -7.97 m). Son elementos "
        "distintos. PP.LOSA de modelado = e x 2400 = 480 kgf/m2 por la "
        "densidad confirmada por el usuario; el plano 700 queda como traza."
    ),
}

# ---------------------------------------------------------------------------
# MATRIZ DE CARGAS ZONAL (leída celda por celda desde tiles)
# ---------------------------------------------------------------------------
# Cada piso tiene 3 columnas de celdas (zonas X) y 1-2 filas (zonas Y).
# Col 1 = bays 1,2 (E-G, 20 m)
# Col 2 = bays 3,4 (G-I, 20 m)
# Col 3 = bay 5 (I-I', 2.5 m)
# Row 1 = Y=1-2 (8.9 m)
# Row 2 = Y=2-3 (7.25 m)
#
# Cada celda contiene: PP.LOSA (= e×2400, densidad confirmada), PM.ADIC (kgf/m²), SC (kgf/m²).
# PP.LOSA es =480 en todas las celdas (e=0.20 m uniforme, densidad hormigon
# confirmada 2400 kg/m3). Traza del plano 700: PP.LOSA=500 con gamma=2500
# (ver info_plano_700["pp_losa_plano_kgf_m2"]). El valor de modelado pasa a
# 480 por la cascada de densidad confirmada por el usuario.
# SC queda REGISTRADA APARTE, NO se suma a q_G.
#
# q_G por paño = PP.LOSA + PM.ADIC (ambos en kgf/m², convertidos a kPa).

# Zonas del plano 700: {(col, row): {pm_kg, sc_kg, fuente, estado}}
# "pm_kg": None si la celda es CARGA LINEAL (no hay carga area de terminaciones).
MATRIZ_CARGAS_ZONAL = {
    "PISO_1": {
        "e_m": 0.20, "pp_losa_kgf_m2": 480,
        "zonas": {
            (1, 1): {"pm_kg": 260, "sc_kg": 500,
                      "fuente": "tile t01 col1 fila unica",
                      "estado": "OCR CONSISTENTE"},
            (1, 2): {"pm_kg": 260, "sc_kg": 500,
                      "fuente": "tile t01 col1 (1 sola fila visible, misma para ambas direcciones Y)",
                      "estado": "INFERIDO_POR_CONTINUIDAD_GRAFICA"},
            (2, 1): {"pm_kg": 260, "sc_kg": 300,
                      "fuente": "tile t01 col2",
                      "estado": "OCR CONSISTENTE"},
            (2, 2): {"pm_kg": 260, "sc_kg": 300,
                      "fuente": "tile t01 col2",
                      "estado": "INFERIDO_POR_CONTINUIDAD_GRAFICA"},
            (3, 1): {"pm_kg": 260, "sc_kg": 250,
                      "fuente": "tile t01 col3",
                      "estado": "OCR CONSISTENTE"},
            (3, 2): {"pm_kg": 260, "sc_kg": 250,
                      "fuente": "tile t01 col3",
                      "estado": "INFERIDO_POR_CONTINUIDAD_GRAFICA"},
        },
    },
    "PISO_2": {
        "e_m": 0.20, "pp_losa_kgf_m2": 480,
        "zonas": {
            (1, 1): {"pm_kg": 260, "sc_kg": 500,
                      "fuente": "tile t02 fila1 col1",
                      "estado": "OCR CONSISTENTE"},
            (1, 2): {"pm_kg": 260, "sc_kg": 400,
                      "fuente": "tile t02 fila2 col1",
                      "estado": "OCR CONSISTENTE"},
            (2, 1): {"pm_kg": 260, "sc_kg": 300,
                      "fuente": "tile t02 fila1 col2",
                      "estado": "OCR CONSISTENTE"},
            (2, 2): {"pm_kg": 200, "sc_kg": 200,
                      "fuente": "tile t02 fila2 col2",
                      "estado": "OCR CONSISTENTE"},
            (3, 1): {"pm_kg": 260, "sc_kg": 250,
                      "fuente": "tile t02 fila1 col3",
                      "estado": "OCR CONSISTENTE"},
            (3, 2): {"pm_kg": 260, "sc_kg": 250,
                      "fuente": "tile t02 fila2 col3 (celda OCULTA; sin OCR legible)",
                      "estado": "NO_RESOLUBLE_PENDIENTE"},
        },
    },
    "PISO_3": {
        "e_m": 0.20, "pp_losa_kgf_m2": 480,
        "zonas": {
            (1, 1): {"pm_kg": 200, "sc_kg": 200,
                      "fuente": "tile t12 fila1 col1",
                      "estado": "OCR CONSISTENTE"},
            (1, 2): {"pm_kg": 260, "sc_kg": 400,
                      "fuente": "tile t11 fila2 col1",
                      "estado": "OCR CONSISTENTE"},
            (2, 1): {"pm_kg": 260, "sc_kg": 300,
                      "fuente": "tile t12 fila1 col2",
                      "estado": "OCR CONSISTENTE"},
            (2, 2): {"pm_kg": 200, "sc_kg": 200,
                      "fuente": "tile t11 fila2 col2",
                      "estado": "OCR CONSISTENTE"},
            (3, 1): {"pm_kg": 260, "sc_kg": 500,
                      "fuente": "tile t12 fila1 col3",
                      "estado": "OCR CONSISTENTE"},
            (3, 2): {"pm_kg": 260, "sc_kg": 500,
                      "fuente": "tile t11 fila2 col3 (OCR leyó '= 2800', continuidad col3 fila1→fila2 del mismo piso = 260)",
                      "estado": "INFERIDO_POR_CONTINUIDAD_GRAFICA"},
        },
    },
    "PISO_4": {
        "e_m": 0.20, "pp_losa_kgf_m2": 480,
        "zonas": {
            (1, 1): {"pm_kg": 350, "sc_kg": 100,
                      "fuente": "tile t10 fila1 col1 (dentro del plan, Y=1-2)",
                      "estado": "OCR CONSISTENTE"},
            (1, 2): {"pm_kg": 260, "sc_kg": 500,
                      "fuente": "tile t10 fila2 col1 (fuera del plan, Y=2-3)",
                      "estado": "OCR CONSISTENTE"},
            (2, 1): {"pm_kg": 200, "sc_kg": 200,
                      "fuente": "tile t10 fila1 col2",
                      "estado": "OCR CONSISTENTE"},
            (2, 2): {"pm_kg": 260, "sc_kg": 300,
                      "fuente": "tile t10 fila2 col2",
                      "estado": "OCR CONSISTENTE"},
            (3, 1): {"pm_kg": None, "sc_kg": None,
                      "fuente": "tile t10 fila1 col3: OCR literal 'CARGA LINEAL', PM=7600 kgf/m, SC=800 kgf/m (NO es carga area)",
                      "estado": "CONFIRMADO_VISUALMENTE_CARGA_LINEAL"},
            (3, 2): {"pm_kg": 260, "sc_kg": 250,
                      "fuente": "tile t10 fila2 col3",
                      "estado": "OCR CONSISTENTE"},
        },
    },
}

# Celdas pendientes / OCR oculto / inferidos:
PENDIENTES_MATRIZ = [
    "PISO_2 zona (col3, row2): celda OCULTA sin OCR legible -> NO_RESOLUBLE_PENDIENTE. "
    "Se mantiene PM=260, SC=250 como hipótesis conservadora NO definitiva. "
    "NO usar como dato definitivo hasta confirmar en el plano 700.",
    "PISO_3 zona (col3, row2): OCR leyó '= 2800 Kg/m'; INFERIDO_POR_CONTINUIDAD_GRAFICA "
    "a PM=260 por continuidad col3 fila1->fila2 del mismo piso. Requiere confirmación visual.",
    "PISO_4 zona (col3, row1): CONFIRMADO_VISUALMENTE como CARGA LINEAL "
    "(texto literal del plano: PM=7600 kgf/m, SC=800 kgf/m). "
    "No hay q_G de área en esa celda: solo PP.LOSA = 500 kgf/m² (traza plano 700). "
    "El PP.LOSA de modelado pasa a 480 kgf/m² (densidad confirmada 2400; cascada). "
    "La carga lineal se registra aparte para vigas de la bahía I-I'.",
    "PISO_1 fila2 (col1..3): el plano muestra 1 sola fila de celdas (abarcan ambas direcciones Y); "
    "fila2 INFERIDO_POR_CONTINUIDAD_GRAFICA = fila1.",
]

# ---------------------------------------------------------------------------
# CARGAS PUNTUALES Y LINEALES (registradas aparte, no aplicadas todavía)
# ---------------------------------------------------------------------------
CARGAS_PUNTUALES = [
    {"tipo": "PM.ADIC PUNTUAL", "magnitud_kgf": 13000, "nivel": "PISO_2",
     "ubicacion": "celda superior derecha (tile t02, y≈0.49)",
     "estado": "PENDIENTE_UBICACION_EXACTA"},
    {"tipo": "PM.ADIC PUNTUAL", "magnitud_kgf": 7000, "nivel": "PISO_2",
     "ubicacion": "celda superior derecha (tile t02, y≈0.47)",
     "estado": "PENDIENTE_UBICACION_EXACTA"},
    {"tipo": "PM.ADIC PUNTUAL", "magnitud_kgf": 10000, "nivel": "PISO_3",
     "ubicacion": "celda superior derecha (tile t12, y≈0.50)",
     "estado": "PENDIENTE_UBICACION_EXACTA"},
    {"tipo": "PM.ADIC PUNTUAL", "magnitud_kgf": 6000, "nivel": "PISO_3",
     "ubicacion": "celda superior derecha (tile t12, y≈0.49)",
     "estado": "PENDIENTE_UBICACION_EXACTA"},
]

CARGAS_LINEALES = [
    {"tipo": "PM.ADIC LINEAL", "magnitud_kgf_m": 7600, "nivel": "PISO_4",
     "zona": "col3 row1 (bahía I-I', Y=1-2)",
     "fuente": "tile t10 CARGA LINEAL",
     "estado": "PENDIENTE_CONFIRMACION"},
    {"tipo": "SC LINEAL", "magnitud_kgf_m": 800, "nivel": "PISO_4",
     "zona": "col3 row1 (bahía I-I', Y=1-2)",
     "fuente": "tile t10 CARGA LINEAL",
     "estado": "PENDIENTE_CONFIRMACION"},
]


# ---------------------------------------------------------------------------
# FUNCIONES DE ACCESO A POR PAÑO
# ---------------------------------------------------------------------------
def _bay_to_col(bay_x):
    """Mapea bay_x (1-5) a columna de zona (1-3)."""
    if bay_x in (1, 2):
        return 1
    if bay_x in (3, 4):
        return 2
    if bay_x == 5:
        return 3
    raise ValueError(f"bay_x={bay_x} fuera de rango")


def qG_por_pano(nivel, pano_id):
    """Retorna q_G [kgf/m²] para un paño dado (PP.LOSA + PM.ADIC).

    Si la zona es CARGA LINEAL (pm_kg=None), retorna solo PP.LOSA.
    """
    suffix = pano_id.split("_P")[-1]
    bay_x = int(suffix[0])
    y_row = int(suffix[1])
    col = _bay_to_col(bay_x)
    zona = MATRIZ_CARGAS_ZONAL[nivel]["zonas"][(col, y_row)]
    pp = MATRIZ_CARGAS_ZONAL[nivel]["pp_losa_kgf_m2"]
    pm = zona["pm_kg"]
    if pm is None:
        return pp
    return pp + pm


def qG_kPa_por_pano(nivel, pano_id):
    """Retorna q_G [kPa] para un paño dado."""
    return kgf_m2_a_kPa(qG_por_pano(nivel, pano_id))


def sc_por_pano(nivel, pano_id):
    """Retorna SC [kgf/m²] para un paño dado (None si es CARGA LINEAL)."""
    suffix = pano_id.split("_P")[-1]
    bay_x = int(suffix[0])
    y_row = int(suffix[1])
    col = _bay_to_col(bay_x)
    return MATRIZ_CARGAS_ZONAL[nivel]["zonas"][(col, y_row)]["sc_kg"]


def sc_kPa_por_pano(nivel, pano_id):
    """Retorna SC [kPa] para un paño dado."""
    v = sc_por_pano(nivel, pano_id)
    return kgf_m2_a_kPa(v) if v is not None else None


# ---------------------------------------------------------------------------
# q_G POR NIVEL (valor representativo para verificaciones globales)
# ---------------------------------------------------------------------------
# Se calcula como el promedio ponderado por area de las zonas del nivel.
NIVELES_CON_LOSA = ["PISO_1", "PISO_2", "PISO_3", "PISO_4"]
_ANCHO_COL = {1: 20.0, 2: 20.0, 3: 2.5}
_ALTO_ROW = {1: 8.9, 2: 7.25}
_A_TOTAL = sum(_ANCHO_COL[c] * _ALTO_ROW[r] for c in (1, 2, 3) for r in (1, 2))


def _qG_representativo_por_nivel(nivel):
    """Promedio ponderado de q_G por nivel (kPa)."""
    total = 0.0
    mat = MATRIZ_CARGAS_ZONAL[nivel]
    for col in (1, 2, 3):
        for row in (1, 2):
            zona = mat["zonas"][(col, row)]
            pp = mat["pp_losa_kgf_m2"]
            pm = zona["pm_kg"]
            qg = pp if pm is None else pp + pm
            total += kgf_m2_a_kPa(qg) * _ANCHO_COL[col] * _ALTO_ROW[row]
    return total / _A_TOTAL


q_G_por_nivel = {}
SC_por_nivel = {}
for _n in NIVELES_CON_LOSA:
    q_G_por_nivel[_n] = {
        "kPa": _qG_representativo_por_nivel(_n),
        "kgf_m2": kgf_m2_a_kPa(_qG_representativo_por_nivel(_n)) * 1000 / G_MS2,
        "fuente": "promedio ponderado por zona de plan 700",
        "estado": "REPRESENTATIVO_ZONAL",
    }
    # SC representativa: SC de la zona con mayor área (col1+col2, row promedio)
    _sc_vals = [MATRIZ_CARGAS_ZONAL[_n]["zonas"][(c, r)]["sc_kg"]
                for c in (1, 2, 3) for r in (1, 2)
                if MATRIZ_CARGAS_ZONAL[_n]["zonas"][(c, r)]["sc_kg"] is not None]
    SC_por_nivel[_n] = {
        "kPa": kgf_m2_a_kPa(max(_sc_vals)) if _sc_vals else 0.0,
        "kgf_m2": max(_sc_vals) if _sc_vals else 0.0,
        "variantes_leidas_kgf_m2": sorted(set(_sc_vals)),
        "fuente": "plan 700", "estado": "REGISTRADA_APARTE",
    }

# PISO_1S (solo registro, sin tributación)
SC_por_nivel["PISO_1S"] = {
    "kPa": kgf_m2_a_kPa(500.0), "kgf_m2": 500.0,
    "variantes_leidas_kgf_m2": [500],
    "fuente": "tile t00 (SUBTE)", "estado": "REGISTRADA_APARTE",
}


def peso_propio_losa(nivel):
    """Peso propio de losa (kPa) para un nivel. e=0.20 m (plan 700)."""
    return peso_especifico_ha_kN_m3 * e_losa_m


# Mantener compatibilidad con cargas previas
terminaciones_kPa = kgf_m2_a_kPa(260.0)
losa_por_nivel = {
    n: {"e_m": e_losa_m, "estado": "RESUELTO: e=0.20 plan700, e=0.25 plan100=fundaciones"}
    for n in ["PISO_1S"] + NIVELES_CON_LOSA
}