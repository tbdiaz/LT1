# ============================================================================
# data/geometria.py
# Datos geométricos del modelo LT1. Unidades: metros (m).
# Todos los valores provienen de los planos del proyecto (ver "ORIGEN").
# ============================================================================

# ---------------------------------------------------------------------------
# Ejes verticales del plano (dirección X del modelo)
# Verificados por lectura de cotas del plano 100.
# ---------------------------------------------------------------------------
ejes_x = {
    "E": 0.000,
    "Eb": 3.600,
    "Ec": 6.400,
    "F": 10.000,
    "G": 20.000,
    "Ga": 21.450,
    "H": 30.000,
    "H1": 33.825,
    "H2": 38.825,
    "I": 40.000,
    "I'": 42.500,
}

# Ejes horizontales adicionales vistos en las elevaciones pero sin cota
# validada en planta. Diferencia de ejes visibles según vista (elevación vs
# planta); pendiente de correlación cuando corresponda. No se incorporan a
# ejes_x hasta que su posición esté correlacionada con el plano.
ejes_x_pendientes = {
    "E'": None,
    "F'": None,
    "J": None,
}

# ---------------------------------------------------------------------------
# Ejes horizontales del plano (dirección Y del modelo)
# Verificados por lectura de cotas del plano 100 (corrección documentada:
# 2a=-13.845 y 3=-16.150).
# ---------------------------------------------------------------------------
ejes_y = {
    "1": 0.000,
    "1''": -3.900,
    "2": -8.900,
    "2a": -13.845,
    "3": -16.150,
}

# ---------------------------------------------------------------------------
# Niveles Z (metros) verificados del plano de elevación 300.
# FUNDACION_SUP = nivel superior de fundaciones; CUBIERTA_SUP = superior de cubierta.
# ---------------------------------------------------------------------------
niveles_z = {
    "FUNDACION_SUP": -7.97,
    "PISO_1S": -4.01,
    "PISO_1": -0.05,
    "PISO_2": 3.91,
    "PISO_3": 7.87,
    "PISO_4": 11.83,
    "CUBIERTA_SUP": 12.58,
}

alturas_entrepiso = {
    "FUNDACION_SUP_a_PISO_1S": -7.97 + 4.01,   # 3.96
    "PISO_1S_a_PISO_1": -4.01 + 0.05,          # 3.96
    "PISO_1_a_PISO_2": -0.05 + 3.91,           # 3.96
    "PISO_2_a_PISO_3": 7.87 - 3.91,            # 3.96
    "PISO_3_a_PISO_4": 11.83 - 7.87,           # 3.96
    "PISO_4_a_CUBIERTA_SUP": 12.58 - 11.83,    # 0.75
}

# Diferencia de ejes visibles según vista. La elevación estructural 300/303
# rotula E', E, F, F', G, H, I, I', J; la grilla de planta 100 verifica
# E, Eb, Ec, F, G, Ga, H, H1, H2, I, I'. Una elevación muestra solo los ejes
# que cortan su plano, por lo que esto NO es una contradicción ni una
# discrepancia estructural: es una diferencia de ejes visibles según vista,
# pendiente de correlación cuando corresponda (p. ej. al fijar muros/vigas de
# fachada).
nota_diferencia_ejes_visibles = (
    "DIFERENCIA DE EJES VISIBLES SEGUN VISTA: la elevación 300/303 rotula "
    "E', E, F, F', G, H, I, I', J; la planta 100 verifica E, Eb, Ec, F, G, "
    "Ga, H, H1, H2, I, I'. No constituye contradicción: cada vista muestra "
    "los ejes que le corresponden. Pendiente de correlación cuando "
    "corresponda."
)

# ---------------------------------------------------------------------------
# Tags de columnas por plano (numeración real leída de cada plano).
# ---------------------------------------------------------------------------
tags_columnas_por_plano = {
    "101": [100, 107, 108, 109, 110, 114],
    "102_serie_200": list(range(200, 212)),
    "102_serie_300": list(range(300, 310)),
    "103_serie_400": [400, 401, 402, 403, 404, 405, 406],
}