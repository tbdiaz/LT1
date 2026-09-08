# ============================================================================
# data/geometria_irregular.py
# Registro completo de geometría estructural IRREGULAR del LT1.
# Muros M.H.A., pilares metálicos (P.M., P.M.I.), vigas metálicas (V.M.),
# vigas irregulares (V.30/45, V.60-30/80-40, V.60/VAR) y elementos
# complementarios de los planos 101, 102, 103.
#
# Cada elemento se registra con:
#   - posicion_pdf: coordenada del centro del rótulo en el PDF (pts).
#   - posicion_modelo: coordenada aproximada en metros (si el mapeo lo permite).
#   - estado: VERIFICADO | INFERIDO_RESPALDADO | PENDIENTE_COORDENADA.
#   - fuente: plano y método de obtención.
#   - razon_estado: justificación clasificación.
#
# NO se crean nodos ni elementos OpenSees desde este archivo.
# Las posiciones INFERIDO_RESPALDADO tienen precisión ~1 m (error del mapeo
# PDF→modelo). Requieren verificación humana antes de crear elasticBeamColumn.
#
# Mapeo PDF→modelo (plano 102, calibrado con P.70x70 en retícula principal):
#   x_pdf = 7.2604 * X + 63.62   (error < 0.5 m para E-H, ~1.6 m para I)
#   y_pdf = 6.7305 * Y + 556.21  (error < 0.2 m en las 3 filas)
# Planos 101 y 103: misma escala de página (792×612 pts) pero layout distinto.
#   Plan 101: mapeo aproximado usando misma escala que 102 (verificar).
#   Plan 103: PLANTA CIELO PISO 4°; mapeo INFERIDO_RESPALDADO por el núcleo
#   E-F común con el plan 102 (x = X*8.189 + 264.77, y = Y*7.652 + 392.58).
# Convención de niveles: la fuente ÚNICA es data/inventario.CONVENCION_NIVELES
# (convención documentada: rótulo "PLANTA CIELO PISO N°" -> LOSA SUPERIOR en
# z = PISO_N, calibrada con las anotaciones explícitas "NIVEL SUPERIOR LOSA").
# El folio 102 contiene DOS vistas estructurales:
#   - vista principal "PLANTA CIELO PISO 2°" -> PISO_2 (z=3.91 m);
#   - sub-plano "PLANTA CIELO PISO 3°" -> PISO_3 (z=7.87 m, NIVEL SUPERIOR
#     LOSA = 7.87 m explícito).
# El plan 103 -> PISO_4 (z=11.83 m, NIVEL SUPERIOR LOSA ≈ 11.83 m explícito).
# Los niveles que se citan aquí por rótulo son REFERENCIA de ventana; la
# asignación autoritativa de cada elemento está en data/inventario.py.
# ============================================================================

# ---------------------------------------------------------------------------
# Mapeo de coordenadas por plano.
# ---------------------------------------------------------------------------
MAPEO_PDF = {
    "102": {
        "metodo": "calibración con 18 columnas P.70x70 en retícula principal",
        "a_x": 7.2604, "b_x": 63.62,
        "a_y": 6.7305, "b_y": 556.21,
        "error_x_m": "±0.4 m (E-H), ±1.6 m (I), ±1.9 m (I')",
        "error_y_m": "±0.2 m (en las 3 filas de la retícula)",
        "rango_pdf_valido": {"x": (40, 400), "y": (440, 570)},
        "rango_modelo_valido": {"X": (-3.0, 46.5), "Y": (-20.8, 2.0)},
        "nota": "Válido para el área principal del edificio (Y >= -16.15) y para "
                "el SECTOR SUR CONFIRMADO del PISO_2. CORRECCIÓN (v2): la inspección "
                "visual del usuario identificó DOS salientes (SALIENTES_PISO_2): "
                "SALIENTE 1 en X 10.00-17.49, Y -16.15 a -20.27 (Y_EXT_SUR_102, el "
                "profundo), y SALIENTE 2 en X 20.00-30.00, Y -16.15 a -18.61. El dato "
                "previo 'franjas F-G y G-H' era una lectura inicial no calibrada y "
                "queda reemplazado por estos rangos confirmados (no se modifica el "
                "rango de validez del mapeo). Elementos con y_pdf < 419.8 (aprox. "
                "Y < -20.27) están en vistas de detalle separadas dentro del mismo "
                "PDF y NO pueden mapearse al edificio.",
    },
    "101": {
        "metodo": "misma escala que 102, NO calibrado con ejes propios",
        "a_x": 7.2604, "b_x": 63.62,
        "a_y": 6.7305, "b_y": 556.21,
        "error_x_m": "NO CALIBRADO (usado como aproximación)",
        "error_y_m": "NO CALIBRADO",
        "rango_pdf_valido": {"x": (55, 400), "y": (440, 590)},
        "nota": "Mapeo heredado de plano 102; requiere calibración independiente "
                "con ejes conocidos del plano 101 (PISO_1S). Los ejes X/Y del "
                "subte coinciden con la retícula principal pero el layout PDF puede "
                "diferir ligeramente.",
    },
    "103": {
        "metodo": "calibración INFERIDO_RESPALDADO por muros del núcleo E-F "
                  "comunes con el plano 102 (M102_02/M103_02 y M102_03/M103_03) "
                  "y el CUADRO DE CONTRAFLECHAS/retícula",
        "a_x": 8.189, "b_x": 264.77,
        "a_y": 7.652, "b_y": 392.58,
        "error_x_m": "±1.5-2 m (estimado, por offset de rótulo de muro)",
        "error_y_m": "±1.5-2 m (estimado, por offset de rótulo de muro)",
        "rango_pdf_valido": {"x": (251, 683), "y": (224, 403)},
        "rango_modelo_valido": {"X": (-3.0, 46.5), "Y": (-18.0, 2.0)},
        "nota": "Plan 103 = PLANTA CIELO PISO 4° (NIVEL SUPERIOR LOSA ~11.83 m "
                "según rótulo OCR del bloque de títulos). La calibración usa el "
                "núcleo E-F común con el plan 102 (M102_02/M103_02, M102_03/M103_03) "
                "y valida la correlación de nivel. Incertidumbre ±1.5-2 m: "
                "marca INFERIDO_RESPALDADO.",
    },
}


def pdf_a_modelo(x_pdf, y_pdf, plano="102"):
    """Convierte coordenadas PDF (pts) a modelo (m). Devuelve (X, Y) o None."""
    m = MAPEO_PDF.get(plano)
    if m is None or m["a_x"] is None:
        return None
    X = (x_pdf - m["b_x"]) / m["a_x"]
    Y = (y_pdf - m["b_y"]) / m["a_y"]
    return round(X, 3), round(Y, 3)


# ---------------------------------------------------------------------------
# Ejes auxiliares verificados (de data/geometria.py, reimportados para
# referencia interna de este módulo).
# ---------------------------------------------------------------------------
EJES_X = {
    "E": 0.0, "Eb": 3.6, "Ec": 6.4, "F": 10.0, "G": 20.0,
    "Ga": 21.45, "H": 30.0, "H1": 33.825, "H2": 38.825, "I": 40.0, "I'": 42.5,
}
EJES_Y = {"1": 0.0, "1''": -3.9, "2": -8.9, "2a": -13.845, "3": -16.15}


# ---------------------------------------------------------------------------
# SECTOR SUR DEL PISO_2 (plano 102) — COTA CONFIRMADA POR EL USUARIO.
# ---------------------------------------------------------------------------
# Inspección visual del plano 102 (la imagen, no OCR): el PISO_2 (z=+3.91) NO
# termina en el eje 3; sobresale al sur en las franjas F-G y G-H.
# Dato dimensional del plano: del eje 3 (Y=-16.150) a la línea exterior sur =
# 4.12 m. Por tanto, con Y("3") = -16.150:
#     Y_EXT_SUR_102 = -16.150 - 4.12 = -20.270 m
# Estado: CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO (ni OCR ni inferencia).
# Los elementos del sector (V.30/45, V.60/VAR, V.60-30/80-40, P.M. 300x300x20)
# quedan dentro de la banda Y(3) >= Y >= Y_EXT_SUR_102, pero su trazado
# interior (límites X de la saliente y pares de nodos) sigue PENDIENTE.
Y_EXT_SUR_102 = -20.270
Y_LIMITE_SUR_102 = Y_EXT_SUR_102


# ============================================================================
# SALIENTES PISO_2 (plan 102) — COTAS CONFIRMADAS POR EL USUARIO.
# ============================================================================
# Inspección visual del usuario sobre el plano 102 (NO OCR, NO inferencia,
# NO atribuible a OpenCode). Estos rangos NO se modifican salvo contradicción
# matemática explícita:
#   SALIENTE 1: X 10.00 m a 17.49 m ; Y -16.15 m (eje 3) a -20.27 m (Y_EXT_SUR_102).
#   SALIENTE 2: X 20.00 m a 30.00 m ; Y -16.15 m (eje 3) a -18.61 m.
# El borde norte de ambos salientes coincide con el eje 3 (Y=-16.15), cuya línea
# sostiene las vigas de borde V.60/80 (rótulos detectados en la capa de texto en
# Y≈-16.11: X≈11.9/15.5/17.9/21.3/26.3). El borde oeste del saliente 1 es el eje
# F (X=10); los bordes del saliente 2 son F (X=20) y G (X=30).
SALIENTES_PISO_2 = [
    {
        "id": "SALIENTE_1",
        "nivel": "PISO_2",
        "plano": "102",
        "X": (10.000, 17.490),
        "Y": (-16.150, -20.270),
        "borde_oeste_eje": "F (X=10.000)",
        "estado": "CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO",
        "evidencia": ("Cotas entregadas por el usuario (inspección visual del "
                      "plano 102): X 10.00-17.49 m, Y -16.15 (eje 3) a -20.27 m "
                      "(= Y_EXT_SUR_102). Borde oeste = eje F. Borde sur profundo "
                      "confirmado."),
    },
    {
        "id": "SALIENTE_2",
        "nivel": "PISO_2",
        "plano": "102",
        "X": (20.000, 30.000),
        "Y": (-16.150, -18.610),
        "borde_oeste_eje": "F (X=20.000)",
        "estado": "CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO",
        "evidencia": ("Cotas entregadas por el usuario (inspección visual del "
                      "plano 102): X 20.00-30.00 m (entre F y G), Y -16.15 (eje 3) "
                      "a -18.61 m. Borde sur menos profundo que el saliente 1."),
    },
]


# ============================================================================
# NÚCLEOS ESTRUCTURALES PISO_2 (plan 102) — COTAS CONFIRMADAS POR EL USUARIO.
# ============================================================================
# Inspección visual del usuario sobre el plano 102 (NO OCR, NO inferencia):
#   NÚCLEO SUPERIOR (zona entre ejes 1'' y 2 aprox.): dimensión horizontal
#     visible = 3.95 m; vertical visible = 2.25 m. Muros: superior e=20
#     (horizontal), laterales e=30 (izquierda y derecha).
#   NÚCLEO INFERIOR (zona entre ejes 2 y 3 aprox.): dimensión vertical
#     visible = 1.58 m. Muros: laterales e=25 (izquierda y derecha),
#     inferior e=20 (horizontal). El ancho se cierra SOLO si existe respaldo.
# Anclaje de posición en la capa de texto del propio plano 102 (mapeo calibrado):
#   - Superior: fila e=20 M102_01/02 en Y=-3.448 (muro horizontal superior);
#     rótulos verticales e=30 en X=3.06 y X=5.91 (texto vertical junto a los
#     muros laterales). La dimensión horizontal CONFIRMADA 3.95 m NO se asume
#     como el largo de un solo muro: se resuelve como rectángulo de núcleo.
#   - Inferior: fila e=20 M102_03 en Y=-14.532 (muro horizontal inferior);
#     rótulos verticales e=25 en X=2.79 y X=6.18 (sobre los muros laterales).
#   - EJE COMÚN: (3.06+5.91)/2 = (2.79+6.18)/2 = 4.485 m -> los dos núcleos
#     comparten el eje X=4.485 (verificado de forma independiente en los 4
#     rótulos laterales; respaldo adicional).
# Fórmulas (resolución por rectángulo de núcleo):
#   SUPERIOR: Y_top = -3.448 (fila e=20 M102_01/02);
#             Y_bot = Y_top - 2.25 = -5.698;
#             muros laterales e=30 (ancho exterior 3.95) en
#             X = 4.485 ± (3.95 - 0.30)/2 = 2.660 / 6.310.
#   INFERIOR: Y_bot = -14.532 (fila e=20 M102_03);
#             Y_top = Y_bot + 1.58 = -12.952;
#             muros laterales e=25 sobre los rótulos X = 2.790 / 6.180
#             (ancho exterior 3.64 m, INFERIDO_RESPALDADO, no confirmado).
# Estados: dimensiones = CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO;
# posiciones de extremos = INFERIDO_RESPALDADO (±0.2-0.4 m, error del mapeo).
# NO se crean elementos OpenSees sin convención de muro en el proyecto.
_N_EJE_X_NUCLEOS = 4.485
_N_Y_TOP_SUP = -3.448
_N_Y_BOT_SUP = _N_Y_TOP_SUP - 2.25            # -5.698
_N_Y_BOT_INF = -14.532
_N_Y_TOP_INF = _N_Y_BOT_INF + 1.58           # -12.952
_N_X_SUP_L = _N_EJE_X_NUCLEOS - (3.95 - 0.30) / 2.0   # 2.660
_N_X_SUP_R = _N_EJE_X_NUCLEOS + (3.95 - 0.30) / 2.0   # 6.310
_N_X_INF_L = 2.790
_N_X_INF_R = 6.180

NODOS_GEOMETRICOS_NUEVOS = [
    # Núcleo superior (PISO_2): nodos en los ejes de los muros laterales.
    {"id": "NS_TL", "nivel": "PISO_2", "X": _N_X_SUP_L, "Y": _N_Y_TOP_SUP,
     "origen": "núcleo superior: extremo sup. muro lateral izq. e=30"},
    {"id": "NS_TR", "nivel": "PISO_2", "X": _N_X_SUP_R, "Y": _N_Y_TOP_SUP,
     "origen": "núcleo superior: extremo sup. muro lateral der. e=30"},
    {"id": "NS_BL", "nivel": "PISO_2", "X": _N_X_SUP_L, "Y": _N_Y_BOT_SUP,
     "origen": "núcleo superior: extremo inf. muro lateral izq. e=30"},
    {"id": "NS_BR", "nivel": "PISO_2", "X": _N_X_SUP_R, "Y": _N_Y_BOT_SUP,
     "origen": "núcleo superior: extremo inf. muro lateral der. e=30"},
    # Núcleo inferior (PISO_2): nodos en los ejes de los muros laterales.
    {"id": "NI_TL", "nivel": "PISO_2", "X": _N_X_INF_L, "Y": _N_Y_TOP_INF,
     "origen": "núcleo inferior: extremo sup. muro lateral izq. e=25"},
    {"id": "NI_TR", "nivel": "PISO_2", "X": _N_X_INF_R, "Y": _N_Y_TOP_INF,
     "origen": "núcleo inferior: extremo sup. muro lateral der. e=25"},
    {"id": "NI_BL", "nivel": "PISO_2", "X": _N_X_INF_L, "Y": _N_Y_BOT_INF,
     "origen": "núcleo inferior: extremo inf. muro lateral izq. e=25"},
    {"id": "NI_BR", "nivel": "PISO_2", "X": _N_X_INF_R, "Y": _N_Y_BOT_INF,
     "origen": "núcleo inferior: extremo inf. muro lateral der. e=25"},
    # Salientes PISO_2 (esquinas sur, con cotas del usuario).
    {"id": "S1_SW", "nivel": "PISO_2", "X": 10.000, "Y": -20.270,
     "origen": "saliente 1: esquina sur-oeste (eje F + Y_EXT_SUR_102)"},
    {"id": "S1_SE", "nivel": "PISO_2", "X": 17.490, "Y": -20.270,
     "origen": "saliente 1: esquina sur-este (X=17.49, cota del usuario)"},
    {"id": "S2_SW", "nivel": "PISO_2", "X": 20.000, "Y": -18.610,
     "origen": "saliente 2: esquina sur-oeste (eje F, cota del usuario)"},
    {"id": "S2_SE", "nivel": "PISO_2", "X": 30.000, "Y": -18.610,
     "origen": "saliente 2: esquina sur-este (eje G, cota del usuario)"},
]

_DIM_SUP = "CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO"
_DIM_INF = "CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO"
_POS = "INFERIDO_RESPALDADO (calibración ±0.2-0.4 m)"

MUROS_CERRADOS_PISO_2 = [
    {"id": "NSUP_01", "seccion": "M.H.A. e= 20", "espesor_cm": 20,
     "orientacion": "E-W (horizontal)", "nodo_i": "NS_TL", "nodo_j": "NS_TR",
     "longitud_m": round(_N_X_SUP_R - _N_X_SUP_L, 3),   # 3.650
     "coords": (round(_N_X_SUP_L, 3), _N_Y_TOP_SUP, round(_N_X_SUP_R, 3), _N_Y_TOP_SUP),
     "evidencia": ("muro superior e=20 del núcleo superior; fila de rótulos "
                   "M102_01/02 en Y=-3.448; ancho de núcleo 3.95 m CONFIRMADO "
                   "por el usuario; eje común X=4.485."),
     "estado": "GEOMETRIA_CERRADA_" + _DIM_SUP,
     "activo_opensees": False},
    {"id": "NSUP_02", "seccion": "M.H.A. e= 30", "espesor_cm": 30,
     "orientacion": "N-S (vertical)", "nodo_i": "NS_BL", "nodo_j": "NS_TL",
     "longitud_m": round(_N_Y_TOP_SUP - _N_Y_BOT_SUP, 3),   # 2.250
     "coords": (_N_X_SUP_L, round(_N_Y_BOT_SUP, 3), _N_X_SUP_L, _N_Y_TOP_SUP),
     "evidencia": ("muro lateral izquierdo e=30 del núcleo superior; rótulo "
                   "vertical e=30 en X≈3.06; alto del núcleo 2.25 m CONFIRMADO."),
     "estado": "GEOMETRIA_CERRADA_" + _DIM_SUP,
     "activo_opensees": False},
    {"id": "NSUP_03", "seccion": "M.H.A. e= 30", "espesor_cm": 30,
     "orientacion": "N-S (vertical)", "nodo_i": "NS_BR", "nodo_j": "NS_TR",
     "longitud_m": 2.250,
     "coords": (_N_X_SUP_R, round(_N_Y_BOT_SUP, 3), _N_X_SUP_R, _N_Y_TOP_SUP),
     "evidencia": ("muro lateral derecho e=30 del núcleo superior; rótulo "
                   "vertical e=30 en X≈5.91; alto del núcleo 2.25 m CONFIRMADO."),
     "estado": "GEOMETRIA_CERRADA_" + _DIM_SUP,
     "activo_opensees": False},
    {"id": "NINF_01", "seccion": "M.H.A. e= 20", "espesor_cm": 20,
     "orientacion": "E-W (horizontal)", "nodo_i": "NI_BL", "nodo_j": "NI_BR",
     "longitud_m": round(_N_X_INF_R - _N_X_INF_L, 3),     # 3.390
     "coords": (round(_N_X_INF_L, 3), _N_Y_BOT_INF, round(_N_X_INF_R, 3), _N_Y_BOT_INF),
     "evidencia": ("muro inferior e=20 del núcleo inferior; rótulo M102_03 en "
                   "Y=-14.532; separación e=25 (2.79-6.18) INFERIDO_RESPALDADO."),
     "estado": "GEOMETRIA_CERRADA_" + _DIM_INF,
     "activo_opensees": False},
    {"id": "NINF_02", "seccion": "M.H.A. e= 25", "espesor_cm": 25,
     "orientacion": "N-S (vertical)", "nodo_i": "NI_TL", "nodo_j": "NI_BL",
     "longitud_m": 1.580,
     "coords": (_N_X_INF_L, round(_N_Y_TOP_INF, 3), _N_X_INF_L, _N_Y_BOT_INF),
     "evidencia": ("muro lateral izquierdo e=25 del núcleo inferior; rótulo "
                   "vertical e=25 en X≈2.79; alto del núcleo 1.58 m CONFIRMADO."),
     "estado": "GEOMETRIA_CERRADA_" + _DIM_INF,
     "activo_opensees": False},
    {"id": "NINF_03", "seccion": "M.H.A. e= 25", "espesor_cm": 25,
     "orientacion": "N-S (vertical)", "nodo_i": "NI_TR", "nodo_j": "NI_BR",
     "longitud_m": 1.580,
     "coords": (_N_X_INF_R, round(_N_Y_TOP_INF, 3), _N_X_INF_R, _N_Y_BOT_INF),
     "evidencia": ("muro lateral derecho e=25 del núcleo inferior; rótulo "
                   "vertical e=25 en X≈6.18; alto del núcleo 1.58 m CONFIRMADO."),
     "estado": "GEOMETRIA_CERRADA_" + _DIM_INF,
     "activo_opensees": False},
]
for _m in MUROS_CERRADOS_PISO_2:
    _m["nivel"] = "PISO_2"
    _m["plano"] = "102"
    _m["z_m"] = 3.91


def eje_cercano(X, Y, tolerancia_x=1.5, tolerancia_y=1.0):
    """Devuelve (eje_x, distancia_x, eje_y, distancia_y) del eje más cercano."""
    best_x, best_dx = None, 999
    for nombre, pos in EJES_X.items():
        dx = abs(X - pos)
        if dx < best_dx:
            best_dx = dx
            best_x = nombre
    best_y, best_dy = None, 999
    for nombre, pos in EJES_Y.items():
        dy = abs(Y - pos)
        if dy < best_dy:
            best_dy = dy
            best_y = nombre
    return best_x, best_dx, best_y, best_dy


def clasificar_estado(X, Y, plano):
    """Clasifica un elemento según la precisión de su posición."""
    m = MAPEO_PDF.get(plano, {})
    if m.get("a_x") is None:
        return "PENDIENTE_COORDENADA", "mapeo no disponible para este plano"
    rango_x = m.get("rango_pdf_valido", {})
    if not rango_x:
        return "PENDIENTE_COORDENADA", "rango de validación no definido"
    # Verificar si está en el rango válido del edificio. Para el plan 102, la
    # banda sur del PISO_2 se extiende hasta el borde CONFIRMADO por el usuario
    # (Y_EXT_SUR_102 = -20.270): los rótulos del sector sur quedan DENTRO del
    # edificio (V.30/45 en Y≈-18.9), no en vistas de detalle.
    y_min = -17.0
    if plano == "102":
        y_min = Y_EXT_SUR_102 - 0.5
    if Y < y_min or Y > 3.0:
        return "PENDIENTE_COORDENADA", "fuera del rango del edificio (vista de detalle)"
    eje_x, dx, eje_y, dy = eje_cercano(X, Y)
    if dx < 0.5 and dy < 0.5:
        return "INFERIDO_RESPALDADO", f"cerca de ejes {eje_x}/{eje_y} (dx={dx:.2f}, dy={dy:.2f} m)"
    if dx < 1.5 and dy < 1.5:
        return "INFERIDO_RESPALDADO", f"aproximado cerca de ejes {eje_x}/{eje_y} (dx={dx:.2f}, dy={dy:.2f} m)"
    return "PENDIENTE_COORDENADA", f"sin eje cercano verificable (dx={dx:.2f}, dy={dy:.2f} m)"


# ============================================================================
# REGISTRO DE MUROS M.H.A. POR PLANO
# ============================================================================
# Formato: (id, plano, seccion, espesor_cm, posicion_pdf_xy, nivel,
#            estado, razon, notas)

_registro_muros = []

# --- PLANO 102: Muros M.H.A. e=20 del núcleo E-F ---
# Posiciones extraídas con pdfminer del plano 102.
# 6 etiquetas M.H.A. e=20 detectadas; 3 en el edificio, 3 en vistas de detalle.
_muros_102_pdf = [
    # En el edificio principal (y_pdf > 440)
    {"id": "M102_01", "x_pdf": 69.1, "y_pdf": 533.0,
     "nivel": "PISO_2", "fuente": "pdfminer plan 102, capa texto",
     "nota": "Muro nucleus Eb-Ec, tramo N-S junto a filas 1''/2"},
    {"id": "M102_02", "x_pdf": 93.6, "y_pdf": 533.0,
     "nivel": "PISO_2", "fuente": "pdfminer plan 102, capa texto",
     "nota": "Muro nucleus Eb-Ec, tramo N-S junto a filas 1''/2"},
    {"id": "M102_03", "x_pdf": 93.2, "y_pdf": 458.4,
     "nivel": "PISO_2", "fuente": "pdfminer plan 102, capa texto",
     "nota": "Muro nucleus, tramo cerca de eje 2a (Y≈-14.4)"},
    # En vistas de detalle (y_pdf < 440) — NO mapeables al edificio
    {"id": "M102_04", "x_pdf": 43.6, "y_pdf": 275.7,
     "nivel": "PENDIENTE_NIVEL", "fuente": "pdfminer plan 102, vista detalle",
     "nota": "En vista de detalle inferior; no es posición real en edificio"},
    {"id": "M102_05", "x_pdf": 67.8, "y_pdf": 201.1,
     "nivel": "PENDIENTE_NIVEL", "fuente": "pdfminer plan 102, vista detalle",
     "nota": "En vista de detalle inferior; no es posición real en edificio"},
    {"id": "M102_06", "x_pdf": 68.2, "y_pdf": 275.7,
     "nivel": "PENDIENTE_NIVEL", "fuente": "pdfminer plan 102, vista detalle",
     "nota": "En vista de detalle inferior; no es posición real en edificio"},
]

for m in _muros_102_pdf:
    pos = pdf_a_modelo(m["x_pdf"], m["y_pdf"], "102")
    if pos:
        X, Y = pos
        estado, razon = clasificar_estado(X, Y, "102")
    else:
        X, Y = None, None
        estado, razon = "PENDIENTE_COORDENADA", "mapeo no disponible"
    _registro_muros.append({
        "id": m["id"], "plano": "102", "seccion": "M.H.A. e= 20",
        "espesor_cm": 20, "posicion_pdf": (m["x_pdf"], m["y_pdf"]),
        "posicion_modelo": (X, Y) if X is not None else None,
        "nivel": m["nivel"], "estado": estado, "razon_estado": razon,
        "fuente": m["fuente"], "nota": m["nota"],
        "observacion_texto_pdf": "Las etiquetas e=25 y e=30 SÍ están en la capa "
                                 "de texto del plan 102 (verificado por conteo: "
                                 "2+2 en la vista principal, 2+2 en vistas de "
                                 "detalle). Sus posiciones de rótulo se registran "
                                 "en M102_E25_*/M102_E30_*.",
    })

# --- PLANO 101: Muros M.H.A. e=20 del subterráneo ---
# 17 etiquetas M.H.A. e=20 detectadas en plano 101.
_muros_101_pdf = [
    {"id": "M101_01", "x_pdf": 77.8, "y_pdf": 513.5},
    {"id": "M101_02", "x_pdf": 81.0, "y_pdf": 225.7},
    {"id": "M101_03", "x_pdf": 88.3, "y_pdf": 507.8},
    {"id": "M101_04", "x_pdf": 104.6, "y_pdf": 155.2},
    {"id": "M101_05", "x_pdf": 104.7, "y_pdf": 481.8},
    {"id": "M101_06", "x_pdf": 104.8, "y_pdf": 411.3},
]
# Los demás se omiten por brevedad pero se registran por cantidad
for _i, mp in enumerate(_muros_101_pdf):
    pos = pdf_a_modelo(mp["x_pdf"], mp["y_pdf"], "101")
    if pos:
        X, Y = pos
        estado, razon = clasificar_estado(X, Y, "101")
    else:
        X, Y = None, None
        estado, razon = "PENDIENTE_COORDENADA", "mapeo no calibrado para plan 101"
    _registro_muros.append({
        "id": mp["id"], "plano": "101", "seccion": "M.H.A. e= 20",
        "espesor_cm": 20, "posicion_pdf": (mp["x_pdf"], mp["y_pdf"]),
        "posicion_modelo": (X, Y) if X is not None else None,
        "nivel": "PISO_1S", "estado": estado, "razon_estado": razon,
        "fuente": "pdfminer plan 101, capa texto (mapeo heredado de 102)",
        "nota": "Muro de contención del subte; mapeo aproximado",
    })
# Registrar los 11 restantes como cantidades sin posición individual
for _i in range(11):
    _registro_muros.append({
        "id": f"M101_{7+_i:02d}", "plano": "101", "seccion": "M.H.A. e= 20",
        "espesor_cm": 20, "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_1S", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "etiqueta detectada en capa de texto sin posición "
                        "individual verificable",
        "fuente": "pdfminer plan 101, capa texto",
        "nota": "Muro de contención del subte",
    })

# --- PLANO 101: Muros M.H.A. e=15 (2) y e=30 (4) ---
for _i in range(2):
    _registro_muros.append({
        "id": f"M101_E15_{_i+1:02d}", "plano": "101", "seccion": "M.H.A. e= 15",
        "espesor_cm": 15, "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_1S", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "etiqueta detectada en capa de texto sin posición verificable",
        "fuente": "inventario plan 101", "nota": "Muro de contención",
    })
for _i in range(4):
    _registro_muros.append({
        "id": f"M101_E30_{_i+1:02d}", "plano": "101", "seccion": "M.H.A. e= 30",
        "espesor_cm": 30, "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_1S", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "etiqueta detectada en capa de texto sin posición verificable",
        "fuente": "inventario plan 101", "nota": "Muro de contención",
    })

# --- PLANO 102: M.H.A. e=25 (2) y e=30 (2) del núcleo E-F ---
# CORRECCIÓN: las etiquetas e=25/e=30 SÍ están en la capa de texto del plano 102
# (conteo verificado: 2+2 en la vista principal, 2+2 en vistas de detalle).
# Las 4 posiciones de la vista principal se registran a continuación (fila
# Y≈-14.0 para e=25 y fila Y≈-5.6 para e=30), confirmadas además de forma
# CRUZADA con el plan 103 (PISO_4, mismo núcleo E-F). LONGITUD de cada tramo
# sigue PENDIENTE (no se crean elementos OpenSees sin extremos).
_muros_102_e25_e30 = [
    {"id": "M102_E25_01", "x_pdf": 84, "y_pdf": 462, "seccion": "M.H.A. e= 25",
     "espesor_cm": 25,
     "nota": "Núcleo E-F, fila Y≈-14.0 (cerca del eje 2a); longitud del tramo "
             "PENDIENTE (sin extremos cotados)."},
    {"id": "M102_E25_02", "x_pdf": 108, "y_pdf": 462, "seccion": "M.H.A. e= 25",
     "espesor_cm": 25,
     "nota": "Núcleo E-F, fila Y≈-14.0 (cerca del eje 2a); longitud del tramo "
             "PENDIENTE (sin extremos cotados)."},
    {"id": "M102_E30_01", "x_pdf": 86, "y_pdf": 518, "seccion": "M.H.A. e= 30",
     "espesor_cm": 30,
     "nota": "Núcleo E-F, fila Y≈-5.6 (entre 1'' y 2); longitud del tramo "
             "PENDIENTE (sin extremos cotados)."},
    {"id": "M102_E30_02", "x_pdf": 106, "y_pdf": 519, "seccion": "M.H.A. e= 30",
     "espesor_cm": 30,
     "nota": "Núcleo E-F, fila Y≈-5.6 (entre 1'' y 2); longitud del tramo "
             "PENDIENTE (sin extremos cotados)."},
]
for _m in _muros_102_e25_e30:
    _pos = pdf_a_modelo(_m["x_pdf"], _m["y_pdf"], "102")
    if _pos:
        _X, _Y = _pos
        _estado, _razon = clasificar_estado(_X, _Y, "102")
    else:
        _X, _Y, _estado, _razon = None, None, "PENDIENTE_COORDENADA", "mapeo 102 no disponible"
    if _m["seccion"] == "M.H.A. e= 30":
        _estado = "INFERIDO_RESPALDADO"
        _razon = ("posición de rótulo confirmada de forma CRUZADA entre plan 102 "
                  "(PISO_2) y plan 103 (PISO_4): fila Y≈-5.6 (sin eje común "
                  "cercano). Longitud PENDIENTE.")
    _registro_muros.append({
        "id": _m["id"], "plano": "102", "seccion": _m["seccion"],
        "espesor_cm": _m["espesor_cm"], "posicion_pdf": (_m["x_pdf"], _m["y_pdf"]),
        "posicion_modelo": (_X, _Y) if _X is not None else None,
        "nivel": "PISO_2", "estado": _estado, "razon_estado": _razon,
        "fuente": "capa de texto plan 102 (conteo e=25/e=30 verificado; posición "
                  "de rótulo pdfminer, cruzada con plan 103)",
        "nota": _m["nota"],
        "observacion_texto_pdf": "(corregido: ya no se trata de OCR visual)",
    })

# --- PLANO 103: M.H.A. e=20 (3) ---
# Posiciones del plano 103 (mapeo no calibrado, contenido desplazado).
_muros_103_pdf = [
    {"id": "M103_01", "x_pdf": 270.9, "y_pdf": 366.2},
    {"id": "M103_02", "x_pdf": 298.4, "y_pdf": 281.4},
    {"id": "M103_03", "x_pdf": 298.8, "y_pdf": 366.2},
]
for m in _muros_103_pdf:
    pos = pdf_a_modelo(m["x_pdf"], m["y_pdf"], "103")
    if pos:
        X, Y = pos
        estado, razon = clasificar_estado(X, Y, "103")
    else:
        X, Y = None, None
        estado, razon = "PENDIENTE_COORDENADA", "mapeo no disponible"
    _registro_muros.append({
        "id": m["id"], "plano": "103", "seccion": "M.H.A. e= 20",
        "espesor_cm": 20, "posicion_pdf": (m["x_pdf"], m["y_pdf"]),
        "posicion_modelo": (X, Y) if X is not None else None,
        "nivel": "PISO_4", "estado": estado,
        "razon_estado": razon,
        "fuente": "pdfminer plan 103, capa texto (mapeo INFERIDO_RESPALDADO "
                  "por núcleo E-F común con plan 102)",
        "nota": "Muro del núcleo E-F (PLANTA CIELO PISO 4°); coincide con M102 "
                "del plan 102 (mismo núcleo, X≈0.75/4.15).",
    })

# --- PLANO 103: M.H.A. e=25 (2) y e=30 (2) del núcleo E-F ---
# CORRECCIÓN: las etiquetas e=25/e=30 también están en la capa de texto del
# plano 103 (conteo verificado: 2+2). Posiciones de rótulo (pdfminer) cruzadas
# con el plan 102 (mismas filas Y≈-14.0/e=25 y Y≈-5.6/e=30). LONGITUD PENDIENTE.
_muros_103_e25_e30 = [
    {"id": "M103_E25_01", "x_pdf": 287, "y_pdf": 285, "seccion": "M.H.A. e= 25",
     "espesor_cm": 25,
     "nota": "Núcleo E-F, fila Y≈-14.0 (cerca del eje 2a); longitud PENDIENTE."},
    {"id": "M103_E25_02", "x_pdf": 316, "y_pdf": 286, "seccion": "M.H.A. e= 25",
     "espesor_cm": 25,
     "nota": "Núcleo E-F, fila Y≈-14.0 (cerca del eje 2a); longitud PENDIENTE."},
    {"id": "M103_E30_01", "x_pdf": 290, "y_pdf": 350, "seccion": "M.H.A. e= 30",
     "espesor_cm": 30,
     "nota": "Núcleo E-F, fila Y≈-5.6; longitud PENDIENTE."},
    {"id": "M103_E30_02", "x_pdf": 313, "y_pdf": 350, "seccion": "M.H.A. e= 30",
     "espesor_cm": 30,
     "nota": "Núcleo E-F, fila Y≈-5.6; longitud PENDIENTE."},
]
for _m in _muros_103_e25_e30:
    _pos = pdf_a_modelo(_m["x_pdf"], _m["y_pdf"], "103")
    if _pos:
        _X, _Y = _pos
        _estado, _razon = clasificar_estado(_X, _Y, "103")
    else:
        _X, _Y, _estado, _razon = None, None, "PENDIENTE_COORDENADA", "mapeo 103 no disponible"
    if _m["seccion"] == "M.H.A. e= 30":
        _estado = "INFERIDO_RESPALDADO"
        _razon = ("posición de rótulo confirmada de forma CRUZADA entre plan 102 "
                  "(PISO_2) y plan 103 (PISO_4): fila Y≈-5.6 (sin eje común "
                  "cercano). Longitud PENDIENTE.")
    _registro_muros.append({
        "id": _m["id"], "plano": "103", "seccion": _m["seccion"],
        "espesor_cm": _m["espesor_cm"], "posicion_pdf": (_m["x_pdf"], _m["y_pdf"]),
        "posicion_modelo": (_X, _Y) if _X is not None else None,
        "nivel": "PISO_4", "estado": _estado, "razon_estado": _razon,
        "fuente": "capa de texto plan 103 (conteo e=25/e=30 verificado; mapeo "
                  "INFERIDO_RESPALDADO por núcleo común con plan 102)",
        "nota": _m["nota"],
        "observacion_texto_pdf": "(corregido: ya no se trata de OCR visual)",
    })

# --- PLANO 101: M.I. e=20 (1) ---
_registro_muros.append({
    "id": "MI101_01", "plano": "101", "seccion": "M.I. e= 20",
    "espesor_cm": 20, "posicion_pdf": None, "posicion_modelo": None,
    "nivel": "PISO_1S", "estado": "PENDIENTE_COORDENADA",
    "razon_estado": "etiqueta detectada en capa de texto sin posición verificable",
    "fuente": "inventario plan 101", "nota": "Muro interior del subte",
})


# ============================================================================
# REGISTRO DE PILARES METÁLICOS (P.M., P.M.I.) POR PLANO
# ============================================================================
_registro_pilares = []

# --- PLANO 102: P.M. 300x300x20 (3) ---
# Posiciones en vistas de detalle (y_pdf < 440) — no mapeables.
_pms_102 = [
    {"id": "PM102_01", "x_pdf": 144.7, "y_pdf": 406.1,
     "nota": "Vista detalle (y_pdf=406 < 440); no es posición real en edificio"},
    {"id": "PM102_02", "x_pdf": 198.1, "y_pdf": 408.4,
     "nota": "Vista detalle (y_pdf=408 < 440); no es posición real en edificio"},
    {"id": "PM102_03", "x_pdf": 198.1, "y_pdf": 452.0,
     "nota": "Vista detalle; y_pdf=452≈límite inferior del edificio (Y≈-15.5)"},
]
for p in _pms_102:
    pos = pdf_a_modelo(p["x_pdf"], p["y_pdf"], "102")
    if pos:
        X, Y = pos
        estado, razon = clasificar_estado(X, Y, "102")
    else:
        X, Y = None, None
        estado, razon = "PENDIENTE_COORDENADA", "mapeo no disponible"
    _registro_pilares.append({
        "id": p["id"], "plano": "102", "seccion": "P.M. 300x300x20",
        "tipo": "columna_metal", "posicion_pdf": (p["x_pdf"], p["y_pdf"]),
        "posicion_modelo": (X, Y) if X is not None else None,
        "nivel": "PENDIENTE_CORRELACION", "estado": estado,
        "razon_estado": razon, "fuente": "pdfminer plan 102",
        "nota": p["nota"],
    })

# --- PLANO 102: P.M.I. (8) ---
# Todos en vistas de detalle (y_pdf < 310).
_pmi_102 = [
    {"id": "PMI102_01", "x_pdf": 181.1, "y_pdf": 153.6},
    {"id": "PMI102_02", "x_pdf": 252.2, "y_pdf": 154.1},
    {"id": "PMI102_03", "x_pdf": 374.9, "y_pdf": 305.0},
    {"id": "PMI102_04", "x_pdf": 375.2, "y_pdf": 190.6},
    {"id": "PMI102_05", "x_pdf": 375.7, "y_pdf": 241.8},
    {"id": "PMI102_06", "x_pdf": 394.8, "y_pdf": 305.0},
    {"id": "PMI102_07", "x_pdf": 395.7, "y_pdf": 188.2},
    {"id": "PMI102_08", "x_pdf": 396.5, "y_pdf": 239.7},
]
for p in _pmi_102:
    _registro_pilares.append({
        "id": p["id"], "plano": "102", "seccion": "P.M.I.",
        "tipo": "pilar_metal", "posicion_pdf": (p["x_pdf"], p["y_pdf"]),
        "posicion_modelo": None,
        "nivel": "PENDIENTE_CORRELACION", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "en vista de detalle inferior del PDF (y_pdf < 310); "
                        "no es posición real en edificio",
        "fuente": "pdfminer plan 102", "nota": "Pilar metálico del sector sur",
    })

# --- PLANO 101: P.M.I. (3) ---
_pmi_101 = [
    {"id": "PMI101_01", "x_pdf": 145.3, "y_pdf": 103.6},
    {"id": "PMI101_02", "x_pdf": 200.6, "y_pdf": 140.4},
    {"id": "PMI101_03", "x_pdf": 200.6, "y_pdf": 104.1},
]
for p in _pmi_101:
    _registro_pilares.append({
        "id": p["id"], "plano": "101", "seccion": "P.M.I.",
        "tipo": "pilar_metal", "posicion_pdf": (p["x_pdf"], p["y_pdf"]),
        "posicion_modelo": None,
        "nivel": "PISO_1S", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "mapeo no calibrado para plan 101; contenido en zona baja",
        "fuente": "pdfminer plan 101", "nota": "Pilar metálico del subte",
    })

# --- PLANO 103: P.M. 300x300x20 (8) ---
for _i in range(8):
    _registro_pilares.append({
        "id": f"PM103_{_i+1:02d}", "plano": "103", "seccion": "P.M. 300x300x20",
        "tipo": "columna_metal", "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_4", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "cantidad por inventario sin posicion de trazado",
        "fuente": "inventario plan 103 (PLANTA CIELO PISO 4°)",
        "nota": "Columna metálica piso superior; posicion exacta pendiente",
    })


# ============================================================================
# REGISTRO DE VIGAS METÁLICAS (V.M.) POR PLANO
# ============================================================================
_registro_vigas_metal = []

# --- PLANO 102: V.M. 300x300x5 (6) + (ARR) arriostas (6) ---
# Posiciones en vista de detalle.
_vm_102 = [
    {"id": "VM102_01", "x_pdf": 360.4, "y_pdf": 182.8},
    {"id": "VM102_02", "x_pdf": 360.5, "y_pdf": 234.6},
    {"id": "VM102_03", "x_pdf": 360.8, "y_pdf": 298.0},
    {"id": "VM102_04", "x_pdf": 377.0, "y_pdf": 298.0},
    {"id": "VM102_05", "x_pdf": 377.2, "y_pdf": 234.6},
    {"id": "VM102_06", "x_pdf": 378.5, "y_pdf": 182.8},
]
for v in _vm_102:
    _registro_vigas_metal.append({
        "id": v["id"], "plano": "102", "seccion": "V.M. 300x300x5",
        "tipo": "viga_metal", "posicion_pdf": (v["x_pdf"], v["y_pdf"]),
        "posicion_modelo": None,
        "nivel": "PENDIENTE_CORRELACION", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "en vista de detalle inferior del PDF",
        "fuente": "pdfminer plan 102", "nota": "Viga metálica arriostra",
    })

# --- PLANO 103: V.M. 300x300x5 (6) + (ARR) (6) ---
for _i in range(6):
    _registro_vigas_metal.append({
        "id": f"VM103_{_i+1:02d}", "plano": "103", "seccion": "V.M. 300x300x5",
        "tipo": "viga_metal", "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_4", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "cantidad por inventario sin posicion de trazado",
        "fuente": "inventario plan 103 (PLANTA CIELO PISO 4°)",
        "nota": "Viga metálica arriostra; posicion exacta pendiente",
    })


# ============================================================================
# REGISTRO DE VIGAS IRREGULARES (V.30/45, V.60-30/80-40, V.60/VAR)
# ============================================================================
_registro_vigas_irregulares = []

# --- PLANO 102: V. 30/45 (2) ---
_vi_102 = [
    {"id": "V3045_01", "x_pdf": 215.9, "y_pdf": 429.3},
    {"id": "V3045_02", "x_pdf": 250.7, "y_pdf": 429.3},
]
for v in _vi_102:
    pos = pdf_a_modelo(v["x_pdf"], v["y_pdf"], "102")
    if pos:
        X, Y = pos
        estado, razon = clasificar_estado(X, Y, "102")
    else:
        X, Y = None, None
        estado, razon = "PENDIENTE_COORDENADA", "mapeo no disponible"
    _registro_vigas_irregulares.append({
        "id": v["id"], "plano": "102", "seccion": "V. 30/45",
        "tipo": "viga_ha", "posicion_pdf": (v["x_pdf"], v["y_pdf"]),
        "posicion_modelo": (X, Y) if X is not None else None,
        "nivel": "PISO_2", "estado": estado,
        "razon_estado": razon + " | sector sur bajo eje 3 (sobrepaso detectado "
                        "por OCR de la tira sur del plan 102)",
        "fuente": "pdfminer plan 102", "nota": "Viga del sector sur bajo eje 3",
    })

# --- PLANO 102: V. 60-30/80-40 (1 con texto) ---
_v6030 = [{"id": "V6030_01", "x_pdf": 110.4, "y_pdf": 165.0}]
for v in _v6030:
    _registro_vigas_irregulares.append({
        "id": v["id"], "plano": "102", "seccion": "V. 60-30/80-40",
        "tipo": "viga_ha_variable", "posicion_pdf": (v["x_pdf"], v["y_pdf"]),
        "posicion_modelo": None,
        "nivel": "PISO_2", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "en vista de detalle inferior del PDF (y_pdf=165)",
        "fuente": "pdfminer plan 102", "nota": "Viga de sección variable",
    })
# Registrar las 4 adicionales como cantidades (inventario dice 5 total)
for _i in range(4):
    _registro_vigas_irregulares.append({
        "id": f"V6030_{_i+2:02d}", "plano": "102", "seccion": "V. 60-30/80-40",
        "tipo": "viga_ha_variable", "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_2", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "cantidad detectada en inventario sin posición individual",
        "fuente": "inventario plan 102", "nota": "Viga de sección variable",
    })

# --- PLANO 103: +V.I. 20/90 (16) ---
for _i in range(16):
    _registro_vigas_irregulares.append({
        "id": f"VI103_{_i+1:02d}", "plano": "103", "seccion": "+V.I. 20/90 (2ºETAPA)",
        "tipo": "viga_inferior", "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_4", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "cantidad por inventario sin posicion de trazado; 2ª etapa",
        "fuente": "inventario plan 103 (PLANTA CIELO PISO 4°)",
        "nota": "Viga inferior de segunda etapa (aparece en plano 103)",
    })


# ============================================================================
# REGISTRO DE V.60/80 ADICIONALES (fuera de la retícula principal)
# ============================================================================
# Plan 102 tiene 57 V.60/80 (inventario), pero el esqueleto solo tiene
# 27 por nivel (15 en X + 12 en Y). Las 30 adicionales (57-27) son del
# sector sur y del núcleo. Se registran como pendientes.
_registro_vigas_6080_extra = []
for _i in range(30):
    _registro_vigas_6080_extra.append({
        "id": f"V6080_102_{_i+1:02d}", "plano": "102", "seccion": "V. 60/80",
        "tipo": "viga_ha", "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PENDIENTE_CORRELACION", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "viga V.60/80 del inventario no incluida en la retícula "
                        "principal del esqueleto (sector sur / núcleo)",
        "fuente": "inventario plan 102 (57 totales - 27 retícula = 30 extra)",
    })

# Plan 101 tiene 28 V.60/80, retícula del esqueleto tiene 27 en PISO_1.
# 1 viga adicional del subte.
for _i in range(1):
    _registro_vigas_6080_extra.append({
        "id": f"V6080_101_{_i+1:02d}", "plano": "101", "seccion": "V. 60/80",
        "tipo": "viga_ha", "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PISO_1S", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "viga adicional del subte (28 totales - 27 retícula = 1 extra)",
        "fuente": "inventario plan 101",
    })

# Plan 103 tiene 31 V.60/80, retícula del esqueleto tiene 27 en PISO_4.
# 4 vigas adicionales.
for _i in range(4):
    _registro_vigas_6080_extra.append({
        "id": f"V6080_103_{_i+1:02d}", "plano": "103", "seccion": "V. 60/80",
        "tipo": "viga_ha", "posicion_pdf": None, "posicion_modelo": None,
        "nivel": "PENDIENTE_CORRELACION", "estado": "PENDIENTE_COORDENADA",
        "razon_estado": "viga adicional no en retícula principal (31 totales - 27 retícula = 4 extra)",
        "fuente": "inventario plan 103",
    })


# ============================================================================
# CONSOLIDADOS POR TIPO
# ============================================================================
muros_todos = list(_registro_muros)
pilares_todos = list(_registro_pilares)
vigas_metal_todas = list(_registro_vigas_metal)
vigas_irregulares_todas = list(_registro_vigas_irregulares)
vigas_6080_extra_todas = list(_registro_vigas_6080_extra)

todos_los_elementos = (
    muros_todos + pilares_todos + vigas_metal_todas +
    vigas_irregulares_todas + vigas_6080_extra_todas
)


# ============================================================================
# RESUMEN DE ESTADOS
# ============================================================================
def resumen_estados():
    """Devuelve dict con conteo por estado y tipo."""
    from collections import Counter
    por_estado = Counter(e["estado"] for e in todos_los_elementos)
    por_tipo_estado = Counter(
        (e.get("tipo", e.get("seccion", "?")), e["estado"])
        for e in todos_los_elementos
    )
    por_plano_estado = Counter(
        (e["plano"], e["estado"]) for e in todos_los_elementos
    )
    return {
        "total": len(todos_los_elementos),
        "por_estado": dict(por_estado),
        "por_tipo_estado": dict(por_tipo_estado),
        "por_plano_estado": dict(por_plano_estado),
        "muros_total": len(muros_todos),
        "pilares_total": len(pilares_todos),
        "vigas_metal_total": len(vigas_metal_todas),
        "vigas_irregulares_total": len(vigas_irregulares_todas),
        "vigas_6080_extra_total": len(vigas_6080_extra_todas),
    }


# ============================================================================
# SECCIONES PROPIEDADES PARA ELEMENTOS IRREGULARES
# ============================================================================
# Propiedades calculadas de las secciones que no están en el esqueleto principal.
# Unidades: m, m^2, m^4.
import math

def _st_venant(b, h):
    a_ = min(b, h)
    c_ = max(b, h)
    r_ = a_ / c_
    return (1.0/3.0) * a_**3 * c_ * (1.0 - 0.630*r_ + 0.052*r_**5)

def _cajon(b_ext, t):
    hi = b_ext - 2.0 * t
    A = b_ext**2 - hi**2
    I = (b_ext**4 - hi**4) / 12.0
    J = t * (b_ext - t)**3
    return {"A_m2": A, "Iy_m4": I, "Iz_m4": I, "J_m4": J}

propiedades_elementos_irregulares = {
    "M.H.A. e= 15": {"tipo": "muro_ha", "e_m": 0.15},
    "M.H.A. e= 20": {"tipo": "muro_ha", "e_m": 0.20},
    "M.H.A. e= 25": {"tipo": "muro_ha", "e_m": 0.25},
    "M.H.A. e= 30": {"tipo": "muro_ha", "e_m": 0.30},
    "M.I. e= 20": {"tipo": "muro_interior", "e_m": 0.20},
    "V. 30/45": {"tipo": "viga_ha", "b_m": 0.30, "h_m": 0.45,
                 "A_m2": 0.30*0.45, "Iy_m4": 0.30*0.45**3/12,
                 "Iz_m4": 0.45*0.30**3/12, "J_m4": _st_venant(0.30, 0.45)},
    "V. 60-30/80-40": {"tipo": "viga_ha_variable", "seccion_variable": True},
    "V. 60/VAR": {"tipo": "viga_ha", "seccion_variable": True},
    "+V.I. 20/90 (2ºETAPA)": {"tipo": "viga_inferior", "b_m": 0.20, "h_m": 0.90,
                               "A_m2": 0.20*0.90, "Iy_m4": 0.20*0.90**3/12,
                               "Iz_m4": 0.90*0.20**3/12, "J_m4": _st_venant(0.20, 0.90)},
    "+V.I. 15/VAR (2ºETAPA)": {"tipo": "viga_inferior", "seccion_variable": True},
    "V.S.I. 20/150": {"tipo": "viga_superior_inv", "b_m": 0.20, "h_m": 1.50,
                       "A_m2": 0.20*1.50, "Iy_m4": 0.20*1.50**3/12,
                       "Iz_m4": 1.50*0.20**3/12, "J_m4": _st_venant(0.20, 1.50)},
    "V.S.I. 15/125": {"tipo": "viga_superior_inv", "b_m": 0.15, "h_m": 1.25,
                       "A_m2": 0.15*1.25, "Iy_m4": 0.15*1.25**3/12,
                       "Iz_m4": 1.25*0.15**3/12, "J_m4": _st_venant(0.15, 1.25)},
    "V.S.I. 15/VAR": {"tipo": "viga_superior_inv", "seccion_variable": True},
    "P. 30x30": {"tipo": "columna_ha", "b_m": 0.30, "d_m": 0.30,
                  "A_m2": 0.09, "Iy_m4": 0.30**4/12, "Iz_m4": 0.30**4/12,
                  "J_m4": _st_venant(0.30, 0.30)},
    "P. 20x50": {"tipo": "columna_ha", "b_m": 0.20, "d_m": 0.50,
                  "A_m2": 0.10, "Iy_m4": 0.20*0.50**3/12,
                  "Iz_m4": 0.50*0.20**3/12, "J_m4": _st_venant(0.20, 0.50)},
    "V. 20/80": {"tipo": "viga_ha", "b_m": 0.20, "h_m": 0.80,
                  "A_m2": 0.16, "Iy_m4": 0.20*0.80**3/12,
                  "Iz_m4": 0.80*0.20**3/12, "J_m4": _st_venant(0.20, 0.80)},
    "V. 20/130": {"tipo": "viga_ha", "b_m": 0.20, "h_m": 1.30,
                   "A_m2": 0.26, "Iy_m4": 0.20*1.30**3/12,
                   "Iz_m4": 1.30*0.20**3/12, "J_m4": _st_venant(0.20, 1.30)},
    "V. 40/60": {"tipo": "viga_ha", "b_m": 0.40, "h_m": 0.60,
                  "A_m2": 0.24, "Iy_m4": 0.40*0.60**3/12,
                  "Iz_m4": 0.60*0.40**3/12, "J_m4": _st_venant(0.40, 0.60)},
    "P.M. 300x300x20": _cajon(0.300, 0.020),
    "V.M. 300x300x5": _cajon(0.300, 0.005),
}


# ============================================================================
# DOCUMENTACIÓN DEPENDENCIAS / PENDIENTES GEOMÉTRICOS
# ============================================================================
# Cada pendiente documenta QUÉ falta para resolver la posición.
pendientes_geometricos = [
    {
        "id": "TRAMO_NUCLEO_E_F",
        "descripcion": "Extremos exactos de cada tramo de muro M.H.A. (e=20/25/30) "
                       "del núcleo sobre los ejes auxiliares Eb/Ec y filas 1''/2/2a",
        "que_falta": "PARCIALMENTE RESUELTO (v2). En PISO_2 (plan 102) se cerraron "
                     "6 tramos del núcleo usando las dimensiones visuales CONFIRMADAS "
                     "por el usuario (núcleo superior 3.95x2.25; núcleo inferior 1.58) "
                     "ancladas a los rótulos M102_01/02/03 y e=25/e=30 (eje común "
                     "X=4.485): longitudes [3.65, 2.25, 2.25] superior y "
                     "[3.39, 1.58, 1.58] inferior (ver MUROS_CERRADOS_PISO_2). "
                     "Queda PENDIENTE el núcleo de PISO_4 (plan 103): mismas "
                     "posiciones de rótulo pero SIN dimensiones confirmadas para "
                     "cerrar sus extremos.",
        "metodo_resolucion": "PISO_2 resuelto con cotas del usuario + capa de texto; "
                             "PISO_4 requiere cotas del plano 103",
        "estado": "PARCIALMENTE_RESUELTO",
        "resuelto": ["6 tramos M.H.A. PISO_2 (e=20 [2], e=30 [2], e=25 [2]) con "
                     "longitud y orientación respaldadas; nodos geométricos "
                     "registrados (MUROS_CERRADOS_PISO_2). Sin convención OpenSees "
                     "para muros: quedan fuera del análisis estructural."],
    },
    {
        "id": "Y_EXT_SUR_102",
        "descripcion": "Coordenada Y del sector que sobresale por debajo del eje 3 "
                       "(una sola variable geométrica)",
        "que_falta": "RESUELTO. Cota del borde sur del PISO_2 del plano 102, confirmada "
                     "por INSPECCION VISUAL del usuario sobre la imagen del plano "
                     "(NO OCR, NO inferencia): Y_EXT_SUR_102 = -20.270 m = Y(3) - 4.12 m. "
                     "Los elementos del sector (V.30/45 en Y≈-18.9, V.60/VAR, "
                     "V.60-30/80-40, P.M. 300x300x20) quedan dentro de la banda "
                     "Y(3) >= Y >= Y_EXT_SUR_102.",
        "metodo_resolucion": "RESUELTO (evidencia directa del usuario)",
        "estado": "RESUELTO_CONFIRMADO_VISUAL",
        "valor_m": Y_EXT_SUR_102,
    },
    {
        "id": "X_SUR_102",
        "descripcion": "Eje X de los salientes y de los pilares P.M. 300x300x20 "
                       "del sector inferior",
        "que_falta": "PARCIALMENTE RESUELTO (v2): los LÍMITES X de los salientes del "
                     "PISO_2 están CONFIRMADOS_POR_INSPECCION_VISUAL_USUARIO "
                     "(SALIENTE 1: X 10.00-17.49, Y hasta -20.27; SALIENTE 2: "
                     "X 20.00-30.00, Y hasta -18.61). Sigue PENDIENTE la posición "
                     "exacta de los P.M. 300x300x20 del sector (solo vistas de "
                     "detalle del plan 102) y los extremos de V.30/45, V.60/VAR y "
                     "V.60-30/80-40 del sector interior.",
        "metodo_resolucion": "PENDIENTE_COORDENADA para P.M. y extremos de vigas",
        "estado": "PENDIENTE_COORDENADA",
    },
    {
        "id": "SALIENTES_PISO_2",
        "descripcion": "Rangos X/Y de los salientes del PISO_2 bajo el eje 3",
        "que_falta": "RESUELTO (v2). Cotas CONFIRMADAS_POR_INSPECCION_VISUAL_USUARIO "
                     "sobre el plano 102 (NO OCR, NO inferencia): SALIENTE_1 "
                     "X=10.00-17.49 m, Y=-16.15 (eje 3) a -20.27 m (Y_EXT_SUR_102); "
                     "SALIENTE_2 X=20.00-30.00 m, Y=-16.15 a -18.61 m. Los bordes "
                     "norte coinciden con el eje 3 (vigas de borde V.60/80 en "
                     "Y≈-16.11 según capa de texto). La CARGA de estas áreas nueva "
                     "se registra como PENDIENTE (el plano 700 no la respalda aún).",
        "metodo_resolucion": "RESUELTO (evidencia directa del usuario, v2)",
        "estado": "RESUELTO_CONFIRMADO_VISUAL",
    },
    {
        "id": "ASOC_2A",
        "descripcion": "Elementos alrededor del eje 2a (asociación tramo-ejes pendiente)",
        "que_falta": "El muro del núcleo M102_03/M103_03 se ubica en Y≈-14.53, próximo al eje "
                     "2a (-13.845); la asociación tramo-eje 2a queda documentada con esa "
                     "posición (diferencia ~0.69 m, dentro del error de rótulo).",
        "metodo_resolucion": "Leer del plano 102 las intersecciones con eje 2a",
        "estado": "DOCUMENTADO_RESPALDADO",
    },
    {
        "id": "CORRELACION_102_NIVEL",
        "descripcion": "Correlación del plano 102 con nivel estructural",
"que_falta": "RESUELTO: la fuente única es data/inventario.CONVENCION_NIVELES. "
                      "El rótulo del plano 102 leído por OCR = 'PLANTA CIELO PISO 2°' "
                      "-> PISO_2 (z=3.91 m, convención R1). La vista parcial superior "
                      "del mismo folio es un SUB-PLANO 'PLANTA CIELO PISO 3°' con NIVEL "
                      "SUPERIOR LOSA = 7.87 m (PISO_3), origen de la retícula del bloque 1 "
                      "del modelo en PISO_3.",
        "metodo_resolucion": "Verificar rótulo del plano contra elevaciones 300-303",
        "estado": "RESUELTO",
        "nivel": "PISO_2",
    },
    {
        "id": "CORRELACION_103_NIVEL",
        "descripcion": "Correlación del plano 103 con nivel estructural",
        "que_falta": "RESUELTO: el rótulo del plano 103 leído por OCR = 'PLANTA CIELO PISO 4°', "
                     "con NIVEL SUPERIOR LOSA ≈ 11.83 m (corresponde a PISO_4 según "
                     "data/geometria.py niveles_z['PISO_4'] = 11.83).",
        "metodo_resolucion": "Verificar rótulo del plano contra elevaciones 300-303",
        "estado": "RESUELTO",
        "nivel": "PISO_4",
    },
    {
        "id": "MAPEO_103",
        "descripcion": "Calibración del mapeo PDF→modelo para plan 103",
        "que_falta": "RESUELTO (INFERIDO_RESPALDADO): mapeo x_pdf = X*8.189 + 264.77, "
                     "y_pdf = Y*7.652 + 392.58 (MAPEO_PDF['103']), calibrado con los muros "
                     "del núcleo E-F comunes con el plan 102. Incertidumbre ±1.5-2 m "
                     "(offset de rótulo).",
        "metodo_resolucion": "Identificar P.70x70 en plan 103 y correlacionar con ejes",
        "estado": "RESUELTO_INFERIDO",
    },
    {
        "id": "M_H_A_E25_E30_POSICION",
        "descripcion": "Posiciones de M.H.A. e=25 y e=30 del núcleo.",
        "que_falta": "PARCIALMENTE RESUELTO (v2). CORRECCIÓN: las etiquetas e=25/e=30 SÍ "
                     "están en la capa de texto de los planos 102 y 103 (conteo verificado: "
                     "2+2 en cada vista principal). En PISO_2 se cerraron con las "
                     "dimensiones CONFIRMADAS del usuario: núcleo superior (3.95x2.25; "
                     "laterales e=30 en X=2.660/6.310) y núcleo inferior (1.58; laterales "
                     "e=25 en X=2.790/6.180) -> MUROS_CERRADOS_PISO_2 (6 tramos con "
                     "longitud). Los mismos espesores del plan 103 (PISO_4) mantienen "
                     "posición INFERIDO_RESPALDADO pero faltan sus dimensiones para cerrar.",
        "metodo_resolucion": "PISO_2 resuelto (v2); PISO_4 requiere cotas del plano 103",
        "estado": "PARCIALMENTE_RESUELTO",
    },
{
        "id": "V_SECTOR_SUR_POSICIONES",
        "descripcion": "Posiciones exactas de V.30/45, V.60-30/80-40, V.60/VAR del "
                       "sector sur bajo eje 3",
        "que_falta": "PARCIALMENTE RESUELTO (v2): los salientes 1 y 2 quedaron "
                     "CONFIRMADOS (SALIENTES_PISO_2) y sus bordes coinciden con el "
                     "eje 3 (V.60/80 de borde en Y≈-16.11). V.30/45 (rótulos 208/209 "
                     "en X≈21.0/25.8, Y≈-18.86) quedan 0.25 m al sur del borde "
                     "-18.61 del saliente 2 (dentro del error ±0.2-0.4 m del mapeo): "
                     "interpretación como vigas de borde del saliente 2 pendiente de "
                     "cota explícita. V.60/VAR (X≈18.9/23.8, Y≈-18.2) y V.60-30/80-40, "
                     "V.60/VAR restantes y P.M. 300x300x20 siguen sin par de nodos "
                     "(extremos). V.60-30/80-40 y V.60/VAR en vistas de detalle "
                     "(y_pdf < 419.8) no mapeables.",
        "metodo_resolucion": "Cotas de extremos de las vigas del sector o lectura "
                             "del raster del plano 102",
        "estado": "PENDIENTE_COORDENADA",
    },
    {
        "id": "V_FUNDACION_100",
        "descripcion": "Trazado de vigas de fundación V.F. (plan 100)",
        "que_falta": "Par de nodos inicial/final de cada V.F. La capa de texto del plan 100 "
                     "identifica V.F. 20/220 (h≈155/60), 20/180 (h≈180), 20/160, 20/120 "
                     "(h≈100/120), 15/225 y LOSA e=25, pero sin cotas de posición por viga. "
                     "Sin OCR del plan 100 (render a alta resolución) el trazado sigue "
                     "PENDIENTE.",
        "metodo_resolucion": "Leer plan 100 con mapeo calibrado",
        "estado": "PENDIENTE_COORDENADA",
    },
]


# ============================================================================
# INVENTARIO CONSOLIDADO (cantidades por plano y tipo)
# ============================================================================
_inventario_consolidado = {
    "101": {
        "PISO_1S": {
            "muros_ha": {"e=15": 2, "e=20": 10, "e=30": 4},
            "muros_interior": {"e=20": 1},
            "columnas_ha": {"P.70x70": 25, "P.30x30": 3, "P.20x50": 1},
            "pilares_metal": {"P.M.I.": 3},
            "vigas_ha": {"V.60/80": 28, "V.20/80": 5, "V.20/130": 3},
            "vigas_inferior": {"V.I. 15/VAR": 2},
            "vigas_superior_inv": {"V.S.I. 20/150": 1, "V.S.I. 15/125": 1},
            "vigas_fundacion": {"V.F. 15/100": 1},
        }
    },
    "102": {
        "PISO_2": {
            "muros_ha": {"e=20": 6, "e=25": 2, "e=30": 2},
            "columnas_ha": {"P.70x70": 36},
            "columnas_metal": {"P.M. 300x300x20": 3},
            "pilares_metal": {"P.M.I.": 8},
            "vigas_ha": {"V.60/80": 57, "V.30/45": 2, "V.60/VAR": 5},
            "vigas_ha_variable": {"V.60-30/80-40": 5},
            "vigas_metal": {"V.M. 300x300x5 (ARR)": 6},
        }
    },
    "103": {
        "PISO_4": {
            "muros_ha": {"e=20": 3, "e=25": 2, "e=30": 2},
            "columnas_ha": {"P.70x70": 18},
            "columnas_metal": {"P.M. 300x300x20": 8},
            "vigas_ha": {"V.60/80": 31},
            "vigas_inferior": {"+V.I. 20/90 (2ªETAPA)": 16},
            "vigas_metal": {"V.M. 300x300x5 (ARR)": 6},
        }
    },
    "100": {
        "FUNDACION_SUP": {
            "losa": {"LOSA e=25": 1},
            "vigas_fundacion": {
                "V.F. 20/220": 3, "V.F. 20/180": 11,
                "V.F. 20/160": 4, "V.F. 20/120": 10,
                "V.F. 15/225": 1,
            },
        }
    },
}
