# ============================================================================
# data/inventario.py
# Inventario estructural por plano, extraído de la capa de texto de los
# planos (nomenclaturas ORIGINALES del plano). Cantidades = ocurrencias de
# rótulo detectadas; NO son coordenadas. La posición de cada elemento queda
# en PENDIENTE_COORDENADA hasta correlacionarla con un eje/cota real.
# ============================================================================

# ---------------------------------------------------------------------------
# Evidencia de método (verificada en esta iteración):
#   - En la capa de texto extraíble de TODOS los planos (100-103, 300-303) no
#     existen cadenas de cota dimensionales (patrón x.yy): 0 ocurrencias.
#   - Por lo tanto las posiciones de los elementos no pueden traducirse a
#     metros con una cota real desde este archivo. Nada se inventa: cada
#     elemento se registra con estado PENDIENTE_COORDENADA.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CONVENCIÓN ÚNICA de niveles (fuente única plano -> nivel estructural).
#
# Convención documentada: en esta estructura, "PLANTA CIELO PISO N°" significa
# el plano estructural de la LOSA cuyo NIVEL SUPERIOR (cara superior de losa)
# está en z = PISO_N (data/geometria.py niveles_z). Se calibra con las dos
# ANOTACIONES EXPLÍCITAS "NIVEL SUPERIOR LOSA" presentes en los propios planos:
#   - folio 102, sub-plano "PLANTA CIELO PISO 3°" -> NIVEL SUPERIOR LOSA = 7.87 m
#     (= PISO_3). (Anotación OCR, registrada en esta iteración.)
#   - folio 103, "PLANTA CIELO PISO 4°" -> NIVEL SUPERIOR LOSA ≈ 11.83 m
#     (= PISO_4). (Anotación OCR, registrada.)
# Por desplazamiento de la misma convención (R1: rótulo N° -> LOSA en PISO_N):
#   - folio 102, vista principal "PLANTA CIELO PISO 2°" -> LOSA en z=3.91 m
#     (= PISO_2). No hay anotación explícita de LOSA para esta vista; la
#     asignación es por la convención R1 aplicada al rótulo.
#
# DISTINCIÓN PISO OCUPADO vs NIVEL ESTRUCTURAL DE CIELO:
#   - PISO ARQUITECTÓNICO/OCUPADO N°: entrepiso ocupable entre PISO_{N-1} y
#     PISO_N (p. ej. PISO 2° ocupa -0.05..3.91; PISO 3° ocupa 3.91..7.87).
#   - NIVEL ESTRUCTURAL DE CIELO: cara superior de la losa-techo de ese piso,
#     en z = PISO_N. Las vigas/losa del plano se sitúan en ese nivel; las
#     columnas que enmarcan esa losa son el tramo PISO_{N-1}→PISO_N.
#
# CADA PLANO PUEDE CONTENER MÁS DE UNA VISTA ESTRUCTURAL (folio 102 tiene dos:
# vista principal = CIELO PISO 2°, sub-plano parcial = CIELO PISO 3°). La clave
# "vista" resuelve esa ambigüedad y es la causa de las contradicciones que esta
# tabla elimina (ver REPORTE de la iteración).
# ---------------------------------------------------------------------------
CONVENCION_NIVELES = [
    {
        "num_plano": "100",
        "vista": "principal",
        "nombre_literal": "PLANTA NIVEL DE FUNDACIONES (grilla de V.F. + LOSA e=25)",
        "piso_arquitectonico": "fundaciones (base de la edificación)",
        "nivel_estructural": "FUNDACION_SUP",
        "z_m": -7.97,
        "rol_estructural": "losa e=25 y grilla de V.F.; apoyo (base) de las columnas "
                           "P.70x70 (nivel de apoyo del modelo)",
        "justificacion": "Contenido del plano (V.F., LOSA e=25) + nivel superior de "
                         "fundación del plano de elevación 300 (niveles_z)",
        "fuente": "2017_67-100 (1) + elevación 300",
    },
    {
        "num_plano": "101",
        "vista": "principal",
        "nombre_literal": "PLANTA CIELO 1° SUBTERRÁNEO (rótulo \"1º S\" en elevación 301)",
        "piso_arquitectonico": "1S (sótano; ocupa ≈ -7.97..-4.01)",
        "nivel_estructural": "PISO_1S",
        "z_m": -4.01,
        "rol_estructural": "losa/cielo del sótano en PISO_1S; muros de contención M.H.A., "
                           "M.I., V.S.I.; columnas tramo FUNDACION_SUP→PISO_1S y "
                           "PISO_1S→PISO_1 (esqueleto). Elementos sueltos PENDIENTE por posición.",
        "justificacion": "Rótulo \"1º S\" de la elevación 301 + contenido (muros de "
                         "contención, V.S.I., M.I.) coherente con subte",
        "fuente": "2017_67-101 + elevación 301",
    },
    {
        "num_plano": "102",
        "vista": "principal",
        "nombre_literal": "PLANTA CIELO PISO 2°",
        "piso_arquitectonico": "2° (ocupa -0.05..3.91)",
        "nivel_estructural": "PISO_2",
        "z_m": 3.91,
        "rol_estructural": "losa-techo del piso 2° en PISO_2 (z=3.91). Esqueleto retícula "
                           "principal PISO_2 + irregulars de la vista principal (M102_01/02/03, "
                           "V3045_01/02, M.H.A. e=25/e=30, ejes auxiliares Eb/Ec/Ga/H1/H2 y "
                           "filas 1''/2a, sector bajo eje 3). Columnas tramo PISO_1→PISO_2 y "
                           "PISO_2→PISO_3",
        "justificacion": "Rótulo OCR del bloque de títulos \"PLANTA CIELO PISO 2°\" aplicado a "
                         "la convención R1 (rótulo N° -> LOSA SUPERIOR en PISO_N, calibrada con "
                         "las anotaciones explícitas del propio folio PISO 3°=7.87 y plano 103 "
                         "PISO 4°≈11.83). No hay anotación explícita de LOSA para esta vista: "
                         "asignación INFERIDA por R1.",
        "fuente": "2017_67-102 (rótulo OCR del bloque de títulos) + convención R1",
    },
    {
        "num_plano": "102",
        "vista": "sub_plano",
        "nombre_literal": "PLANTA CIELO PISO 3° (sub-plano parcial, franja superior del folio 102)",
        "piso_arquitectonico": "3° (ocupa 3.91..7.87)",
        "nivel_estructural": "PISO_3",
        "z_m": 7.87,
        "rol_estructural": "losa-techo del piso 3° en PISO_3 (z=7.87): retícula principal del "
                           "bloque 1 del modelo (vigas V.60/80 y columnas P.70x70 tramo "
                           "PISO_2→PISO_3). Es la franja del folio usada por "
                           "comparacion_plano102.py para el control PISO_3.",
        "justificacion": "Rótulo OCR \"PLANTA CIELO PISO 3°\" con ANOTACIÓN EXPLÍCITA "
                         "NIVEL SUPERIOR LOSA = 7.87 m (= niveles_z['PISO_3'])",
        "fuente": "2017_67-102 (sub-plano, rótulo + anotación NIVEL SUPERIOR LOSA, OCR)",
    },
    {
        "num_plano": "103",
        "vista": "principal",
        "nombre_literal": "PLANTA CIELO PISO 4°",
        "piso_arquitectonico": "4° (ocupa 7.87..11.83)",
        "nivel_estructural": "PISO_4",
        "z_m": 11.83,
        "rol_estructural": "losa-techo del piso 4° en PISO_4 (z=11.83). Esqueleto retícula "
                           "PISO_4 + irregulars del plano 103 (M103_01/02/03). Columnas tramo "
                           "PISO_3→PISO_4",
        "justificacion": "Rótulo OCR \"PLANTA CIELO PISO 4°\" con ANOTACIÓN EXPLÍCITA "
                         "NIVEL SUPERIOR LOSA ≈ 11.83 m (= niveles_z['PISO_4'])",
        "fuente": "2017_67-103 (rótulo + anotación NIVEL SUPERIOR LOSA, OCR)",
    },
]

# nivel_por_plano: correlación del rótulo PRINCIPAL de cada plano con el nivel
# estructural (usada para registrar los elementos pendientes del inventario).
nivel_por_plano = {}
for _c in CONVENCION_NIVELES:
    if _c["vista"] == "principal" and _c["nivel_estructural"]:
        nivel_por_plano[_c["num_plano"]] = _c["nivel_estructural"]

fuente_correlacion_plano_nivel = {}
for _c in CONVENCION_NIVELES:
    if not _c["nivel_estructural"] or _c["vista"] != "principal":
        continue
    _txt = (f"Rótulo \"{_c['nombre_literal']}\" -> {_c['nivel_estructural']} "
            f"(z={_c['z_m']} m). {_c['justificacion']}. Fuente: {_c['fuente']}.")
    if any(x["num_plano"] == _c["num_plano"] and x["vista"] == "sub_plano"
           for x in CONVENCION_NIVELES):
        _sub = next(x for x in CONVENCION_NIVELES
                    if x["num_plano"] == _c["num_plano"] and x["vista"] == "sub_plano")
        _txt += (f" El folio además contiene el sub-plano \"{_sub['nombre_literal']}\" "
                 f"-> {_sub['nivel_estructural']} (z={_sub['z_m']} m): "
                 f"{_sub['justificacion']}.")
    fuente_correlacion_plano_nivel[_c["num_plano"]] = _txt


def convencion_plano(num_plano, vista="principal"):
    """Devuelve el registro de CONVENCION_NIVELES para un plano y vista."""
    for _c in CONVENCION_NIVELES:
        if _c["num_plano"] == num_plano and _c["vista"] == vista:
            return dict(_c)
    return None

# ---------------------------------------------------------------------------
# Fuentes documentales del proyecto (planos + documentos académicos).
# Registro trazable de qué entrega cada fuente. Revisado hasta esta etapa:
# NINGUNA fuente fija los valores elásticos del hormigón (f'c, E, G, nu).
#   - docs/P1L2.txt          : NO fija material; enumera 'materiales' como dato
#                              que el modelo debe incluir.
#   - docs/Enunciado general.txt: NO fija valores; fija la convención de
#                              modelación (línea 42: "sistema lineal elástico
#                              3D", elasticBeamColumn, rigidDiaphragm, muros
#                              lineales equivalentes).
#   - AGENTS.md              : NO fija valores; prohíbe inventar datos.
# Por lo tanto el material del modelo lineal elástico queda en estado
# MATERIAL_PENDIENTE_DE_CONVENCION_ACADEMICA hasta que se defina E y nu/G.
# ---------------------------------------------------------------------------
fuentes_documentales = {
    "2017_67-000-Model.pdf": {
        "rol": "DETALLES TIPICOS, SIMBOLOGIA Y NOMENCLATURA / CONSIDERACIONES GENERALES",
        "texto": "raster (0 chars)",
        "materiales_elasticos": "NO (ref. E.T.O.G. y plano 001, no provistos)",
    },
    "2017_67-001-Model.pdf": {
        "rol": "DETALLES TIPICOS DE ARMADO / CONFINAMIENTO DE MUROS (revisión visual confirmada)",
        "texto": "raster (0 chars)",
        "materiales_elasticos": "NO (no entrega propiedades elásticas)",
    },
    "2017_67-100 (1)-Model.pdf": {
        "rol": "PLANTA NIVEL DE FUNDACIONES",
        "texto": "etiquetas de sección (V.F., LOSA e=25)",
        "materiales_elasticos": "NO",
    },
    "2017_67-101-Model.pdf": {
        "rol": "PLANTA PISO 1S / muros de contención",
        "texto": "etiquetas de sección (V. 60/80, M.H.A., P. 70x70)",
        "materiales_elasticos": "NO",
    },
    "2017_67-102-Model.pdf": {
        "rol": "PLANTA PISO 3 (retícula principal, bloque plano 102)",
        "texto": "etiquetas de sección (V. 60/80, P. 70x70, P.M., V.M.)",
        "materiales_elasticos": "NO",
    },
    "2017_67-103-Model.pdf": {
        "rol": "PLANTA PISO 4+ (idem 102)",
        "texto": "etiquetas de sección",
        "materiales_elasticos": "NO",
    },
    "2017_67-300-Model.pdf": {
        "rol": "ELEVACIONES (ejes E..I', E'..F', J)",
        "texto": "mínimo (ochos de ejes, ESCALA 1:50)",
        "materiales_elasticos": "NO",
    },
    "2017_67-301-Model.pdf": {
        "rol": "ELEVACIONES (E', Eb, Ec; EJE 1A/1b/1C; V.F. 15/225...)",
        "texto": "mínimo (rótulos de elevaciones)",
        "materiales_elasticos": "NO",
    },
    "2017_67-302-Model.pdf": {
        "rol": "ELEVACIONES (ESCALA 1:50)",
        "texto": "mínimo",
        "materiales_elasticos": "NO",
    },
    "2017_67-303-Model.pdf": {
        "rol": "ELEVACIONES (ejes E..I', E'..F', J)",
        "texto": "mínimo",
        "materiales_elasticos": "NO",
    },
    "2017_67-700-Model.pdf": {
        "rol": "CARGA VIVA / NOTAS (raster)",
        "texto": "raster (0 chars)",
        "materiales_elasticos": "NO",
    },
    "docs/P1L2.txt": {
        "rol": "Enunciado LAB semana 2 (modelo completo + gravedad + Unity)",
        "texto": "texto",
        "materiales_elasticos": "NO fija valores; requiere 'materiales' como dato del modelo",
    },
    "docs/Enunciado general.txt": {
        "rol": "Enunciado proyecto (3D lineal elástico, elasticBeamColumn, rigidDiaphragm, tributary areas)",
        "texto": "texto",
        "materiales_elasticos": "NO fija valores; define la convención de modelación",
    },
    "AGENTS.md": {
        "rol": "Reglas del proyecto LT1",
        "texto": "texto",
        "materiales_elasticos": "NO fija valores; prohíbe inventar datos",
    },
}

# ---------------------------------------------------------------------------
# Inventario por plano.
# Cada ítem: (seccion_original, tipo, ocurrencias_de_rotulo)
# "ocurencias_de_rotulo" es la cantidad de rótulos con esa nomenclatura
# detectados en la capa de texto (cota inferior del nº de elementos).
#
# NOTA DE MÉTODO (verificación pdfminer, plan 102): en la capa de texto
# extraíble de los planos 102/103 SOLO existe "M.H.A. e= 20". Las etiquetas
# "e= 25" y "e= 30" del plano 102 fueron identificadas por OCR VISUAL (que se
# confirma contra el inventario previo) pero NO aparecen en la capa de texto.
# por eso el registro completo de muros (incluidos e=25/e=30) vive en
# data/geometria_irregular.py con su grado de trazabilidad por elemento.
# ---------------------------------------------------------------------------
inventario_por_plano = {
    "100": [
        ("LOSA e=25", "losa", 1),
        ("V.F. 20/220", "viga_fundacion", 3),
        ("V.F. 20/180", "viga_fundacion", 11),
        ("V.F. 20/160", "viga_fundacion", 4),
        ("V.F. 20/120", "viga_fundacion", 10),
        ("V.F. 15/225", "viga_fundacion", 1),
    ],
    "101": [
        ("P. 70x70", "columna_ha", 25),
        ("P. 30x30", "columna_ha", 3),
        ("P. 20x50", "columna_ha", 1),
        ("P.M.I.", "pilar_metal", 3),
        ("V. 60/80", "viga_ha", 28),
        ("V. 20/80", "viga_ha", 5),
        ("V. 20/130", "viga_ha", 3),
        ("V.I. 15/VAR", "viga_inferior_variable", 2),
        ("V.S.I. 20/150", "viga_superior_inv", 1),
        ("V.S.I. 15/125", "viga_superior_inv", 1),
        ("V.F. 15/100", "viga_fundacion", 1),
        ("M.H.A. e= 15", "muro_ha", 2),
        ("M.H.A. e= 20", "muro_ha", 10),
        ("M.H.A. e= 30", "muro_ha", 4),
        ("M.I. e= 20", "muro_interior", 1),
    ],
    "102": [
        ("P. 70x70", "columna_ha", 36),
        ("P.M. 300x300x20", "columna_metal", 3),
        ("P.M.I.", "pilar_metal", 8),
        ("V.M. 300x300x5 (ARR)", "viga_metal", 6),
        ("V. 60/80", "viga_ha", 57),
        ("V. 30/45", "viga_ha", 2),
        ("V. 60-30/80-40", "viga_ha_variable", 5),
        ("M.H.A. e= 20", "muro_ha", 6),
    ],
    "103": [
        ("P. 70x70", "columna_ha", 18),
        ("P.M. 300x300x20", "columna_metal", 8),
        ("V.M. 300x300x5 (ARR)", "viga_metal", 6),
        ("V. 60/80", "viga_ha", 31),
        ("+V.I. 20/90 (2ºETAPA)", "viga_inferior", 16),
        ("M.H.A. e= 20", "muro_ha", 3),
    ],
}

# ---------------------------------------------------------------------------
# Numeración real de columnas leída por plano (rótulos numéricos).
# En 101 solo algunos rótulos aparecen completos en el texto extraíble;
# 102 presenta dos series (200-211 y 300-309); 103 la serie 400-406.
# ---------------------------------------------------------------------------
columnas_numeradas_por_plano = {
    "101": {"serie": "100-114", "rotulos_detectados": [100, 107, 108, 109, 110, 114]},
    "102": {"serie_1": "200-211", "serie_2": "300-309",
            "rotulos_detectados": list(range(200, 212)) + list(range(300, 310))},
    "103": {"serie": "400-406", "rotulos_detectados": list(range(400, 407))},
}

# ---------------------------------------------------------------------------
# Coordenada/eje que falta por tipo para poder ubicar en metros.
# ---------------------------------------------------------------------------
coordenada_faltante_por_tipo = {
    "losa": "no requiere posición nodal (se transfiere por área tributaria)",
    "viga_fundacion": "eje(s) del trazado de la V.F.",
    "columna_ha": "eje X y eje Y de la intersección + tramo vertical",
    "columna_metal": "eje X y eje Y de la intersección + tramo vertical",
    "pilar_metal": "eje X y eje Y de la intersección + tramo vertical",
    "viga_ha": "par de nodos inicial/final (ejes) + nivel",
    "viga_metal": "par de nodos inicial/final (ejes) + nivel",
    "viga_ha_variable": "par de nodos inicial/final (ejes) + nivel",
    "viga_inferior": "par de nodos inicial/final (ejes) + nivel",
    "viga_inferior_variable": "par de nodos inicial/final (ejes) + nivel",
    "viga_superior_inv": "par de nodos inicial/final (ejes) + nivel",
    "muro_ha": "extremos sobre ejes (longitud y espesor) + nivel",
    "muro_interior": "extremos sobre ejes (longitud y espesor) + nivel",
}

# ---------------------------------------------------------------------------
# Lista concreta de elementos pendientes de coordenada.
# cada entrada: {plano, rotulo/seccion, coordenada/eje que falta}.
# ---------------------------------------------------------------------------
elementos_pendientes_coordenada = []
for _plano, _items in inventario_por_plano.items():
    for _seccion, _tipo, _n in _items:
        for _k in range(_n):
            elementos_pendientes_coordenada.append({
                "plano": _plano,
                "rotulo": _seccion,
                "coordenada_faltante": coordenada_faltante_por_tipo.get(_tipo, "por definir"),
                "nivel": nivel_por_plano[_plano],
                "estado": "PENDIENTE",
            })

# ---------------------------------------------------------------------------
# Numeración visible en PLANTA CIELO PISO 2 (círculos 200..221).
# Son identificadores ORIgINALES del plano; NO se usan como elementTag de
# OpenSees (separación id_plano / elementTag_opensees). Hasta correlación
# individual resuelta, los registros geométricos usan id_plano=None y
# conservan su clave de trazabilidad.
# ---------------------------------------------------------------------------
numeros_circulos_102 = list(range(200, 222))

# ---------------------------------------------------------------------------
# Coordenadas auxiliares que faltan para ubicar la geometría CONFIRMADA
# visualmente pero todavía sin posición exacta en metros.
# ---------------------------------------------------------------------------
coordenadas_aux_faltantes = {
    "Y_EXT_SUR_102": "RESUELTO: borde sur más profundo del PISO_2 = -20.270 m "
                     "(Y(3) - 4.12 m), CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO "
                     "sobre el plano 102. V2: saliente 1 (X 10.00-17.49) llega a "
                     "ese borde; saliente 2 (X 20.00-30.00) solo a -18.61 m.",
    "X_SUR_102": "PARCIALMENTE RESUELTO (v2): límites X de los salientes del PISO_2 "
                 "confirmados por el usuario (SALIENTE_1 X 10.00-17.49; SALIENTE_2 "
                 "X 20.00-30.00). La posición de P.M. 300x300x20 y los extremos de "
                 "V.30/45, V.60/VAR, V.60-30/80-40 siguen PENDIENTE.",
    "TRAMO_NUCLEO_E_F": "RESUELTO FUNDACION-PISO 4: 6 paños por planta, 30 "
                        "segmentos verticales cerrados (MUROS_CERRADOS_NIVELES, "
                        "longitudes 3.65/2.25/2.25 y 3.39/1.58/1.58). Continuidad "
                        "comprobada en las plantas cielo 1° subterráneo y PISO_1 "
                        "del plano 101, PISO_2/PISO_3 del 102 y PISO_4 del 103.",
    "ASOC_2A": "elementos alrededor del eje 2a (asociación tramo-ejes pendiente)",
}

# ---------------------------------------------------------------------------
# Geometría CONFIRMADA visualmente en PLANTA CIELO PISO 2° (plano 102) cuya
# posición todavía no puede expresarse con los ejes conocidos. Se registra
# como PENDIENTE; NO se crean nodos ni líneas hasta la correlación exacta.
# Fuente: revisión visual de alta resolución (2017_67-102 piso2).
# ---------------------------------------------------------------------------
_geometria_confirmada_102 = [
    # Sector núcleo E-F (muros M.H.A. + elementos alrededor de Eb/Ec, 1'', 2, 2a)
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "NUCLEO_E_F",
     "rotulo": "M.H.A. e= 20 (núcleo, tramo a correlacionar)",
     "coordenada_faltante": coordenadas_aux_faltantes["TRAMO_NUCLEO_E_F"]},
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "NUCLEO_E_F",
     "rotulo": "M.H.A. e= 25 (núcleo, tramo a correlacionar)",
     "coordenada_faltante": coordenadas_aux_faltantes["TRAMO_NUCLEO_E_F"]},
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "NUCLEO_E_F",
     "rotulo": "M.H.A. e= 30 (núcleo, tramo a correlacionar)",
     "coordenada_faltante": coordenadas_aux_faltantes["TRAMO_NUCLEO_E_F"]},
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "NUCLEO_E_F",
     "rotulo": "elementos adicionales alrededor del núcleo y del eje 2a",
     "coordenada_faltante": coordenadas_aux_faltantes["ASOC_2A"]},
    # Sector inferior central (sobresale por debajo del eje 3)
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "Y_EXT_SUR_102",
     "rotulo": "P.M. 300x300x20 (3 según inventario de rótulos)",
     "coordenada_faltante": "Y_EXT_SUR_102 + " + coordenadas_aux_faltantes["X_SUR_102"]},
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "Y_EXT_SUR_102",
     "rotulo": "V. 60/80 del sector",
     "coordenada_faltante": "Y_EXT_SUR_102 + par de nodos"},
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "Y_EXT_SUR_102",
     "rotulo": "V. 30/45 del sector (2 según inventario)",
     "coordenada_faltante": "Y_EXT_SUR_102 + par de nodos"},
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "Y_EXT_SUR_102",
     "rotulo": "V. 60/VAR del sector",
     "coordenada_faltante": "Y_EXT_SUR_102 + par de nodos"},
    {"plano": "102", "planta": "PLANTA CIELO PISO 2", "grupo": "Y_EXT_SUR_102",
     "rotulo": "V. 60-30/80-40 del sector (5 según inventario)",
     "coordenada_faltante": "Y_EXT_SUR_102 + par de nodos"},
]
for _e in _geometria_confirmada_102:
    _e["nivel"] = "PISO_2 (PLANTA CIELO PISO 2°)"
    _e["estado"] = "PENDIENTE"
    _e["fuente_correlacion"] = fuente_correlacion_plano_nivel["102"]
    elementos_pendientes_coordenada.append(_e)

# ---------------------------------------------------------------------------
# RESUELTOS_GEOMETRIA_V2 (plan 102, PISO_2): geometría que esta iteración v2
# cerró con cotas CONFIRMADAS_POR_INSPECCION_VISUAL_USUARIO + capa de texto.
# La lista _geometria_confirmada_102 (PENDIENTE) se conserva como registro
# histórico; estos elementos pasan aquí con su estado de cierre.
# ---------------------------------------------------------------------------
RESUELTOS_GEOMETRIA_V2 = [
    {"grupo": "NUCLEO_SUPERIOR_PISO_2", "rotulo": "M.H.A. e=20 sup + e=30 lat.",
     "cierre": "3.95 x 2.25 m (cotas del usuario); nodos NS_TL/TR/BL/BR; muros "
               "NSUP_01/02/03 en MUROS_CERRADOS_PISO_2.",
     "estado": "GEOMETRIA_CERRADA · posiciones INFERIDO_RESPALDADO · SIN convención OpenSees"},
    {"grupo": "NUCLEO_INFERIOR_PISO_2", "rotulo": "M.H.A. e=20 inf + e=25 lat.",
     "cierre": "alto 1.58 m (cota del usuario); ancho 3.64 m INFERIDO_RESPALDADO "
               "(e=25 en X 2.790/6.180); nodos NI_TL/TR/BL/BR; muros "
               "NINF_01/02/03 en MUROS_CERRADOS_PISO_2.",
     "estado": "GEOMETRIA_CERRADA · posiciones INFERIDO_RESPALDADO · SIN convención OpenSees"},
    {"grupo": "SALIENTE_1", "rotulo": "saliente X 10.00-17.49, Y -16.15 a -20.27",
     "cierre": "Cotas del usuario; esquinas sur S1_SW/S1_SE; borde norte = eje 3 "
               "(V.60/80 de borde en Y≈-16.11). Carga PENDIENTE.",
     "estado": "CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO · GEOMETRIA_MODELADA"},
    {"grupo": "SALIENTE_2", "rotulo": "saliente X 20.00-30.00, Y -16.15 a -18.61",
     "cierre": "Cotas del usuario; esquinas sur S2_SW/S2_SE; borde norte = eje 3. "
               "V.30/45 a -18.86 (0.25 m ± error) candidatas a borde sur; extremos "
               "PENDIENTE. Carga PENDIENTE.",
     "estado": "CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO · GEOMETRIA_MODELADA"},
]

# Nota de método para la filosofía pasadas/aberturas:
# "PASADA 45/30", "PASADA 60/30", "PASADAS Ø7.5" NO son elementos
# estructurales independientes. Se conservan como metadata de aberturas
# cuando corresponda; no generan nodos/vigas/columnas.
pasadas_102 = ["PASADA 45/30", "PASADA 60/30", "PASADAS Ø7.5"]

# ---------------------------------------------------------------------------
# PUNTO ÚNICO DE INYECCIÓN de posiciones verificadas.
# El constructor de geometría (src/modelo_lt1.py) lee SOLO esta estructura.
# Cuando una posición quede verificada con el plano (humana o por cota real),
# se agrega aquí una entrada.
# ---------------------------------------------------------------------------
posiciones_verificadas = {
    # -------------------------------------------------------------------
    # BLOQUE 1 — PLANO 2017_67-102 — RETÍCULA PRINCIPAL DEL SUB-PLANO
    # "PLANTA CIELO PISO 3°" (franja superior del folio 102, NIVEL SUPERIOR
    # LOSA = 7.87 m = PISO_3; ver CONVENCION_NIVELES).
    #   - pilares P.70x70 tramo PISO_2 -> PISO_3 (z 3.91 -> 7.87 m);
    #   - vigas V.60/80 en PISO_3 (z 7.87 m).
    # Retícula principal: X = E,F,G,H,I,I' ; Y = 1,2,3.
    # (La vista principal del folio, PLANTA CIELO PISO 2°, corresponde al
    # nivel PISO_2 z=3.91 m; sus elementos irregulares quedan en PISO_2.)
    # -------------------------------------------------------------------
}

_ejes_x_usados = ["E", "F", "G", "H", "I", "I'"]
_ejes_y_usados = ["1", "2", "3"]

for _x in _ejes_x_usados:
    for _y in _ejes_y_usados:
        posiciones_verificadas[f"col_{_x}_{_y}_102"] = {
            "tipo": "columna_ha",
            "seccion": "P. 70x70",
            "eje_x": _x,
            "eje_y": _y,
            "nivel_inferior": "PISO_2",
            "nivel_superior": "PISO_3",
            "material_estructural": "H.A.",
            "plano_fuente": "2017_67-102",
            "planta_fuente": "PLANTA CIELO PISO 3° (sub-plano del folio 102)",
            "estado_geometria": "VERIFICADA_VISUALMENTE_RETICULA_PRINCIPAL",
            "rotulo": None,
        }

for _y in _ejes_y_usados:
    for _xa, _xb in zip(_ejes_x_usados, _ejes_x_usados[1:]):
        posiciones_verificadas[f"vigax_{_xa}_{_xb}_Y{_y}_102"] = {
            "tipo": "viga_ha",
            "seccion": "V. 60/80",
            "nivel": "PISO_3",
            "eje_x_i": _xa,
            "eje_y_i": _y,
            "eje_x_j": _xb,
            "eje_y_j": _y,
            "material_estructural": "H.A.",
            "plano_fuente": "2017_67-102",
            "planta_fuente": "PLANTA CIELO PISO 3° (sub-plano del folio 102)",
            "estado_geometria": "VERIFICADA_VISUALMENTE_RETICULA_PRINCIPAL",
            "rotulo": None,
        }

for _x in _ejes_x_usados:
    for _ya, _yb in zip(_ejes_y_usados, _ejes_y_usados[1:]):
        posiciones_verificadas[f"vigay_{_ya}_{_yb}_X{_x}_102"] = {
            "tipo": "viga_ha",
            "seccion": "V. 60/80",
            "nivel": "PISO_3",
            "eje_x_i": _x,
            "eje_y_i": _ya,
            "eje_x_j": _x,
            "eje_y_j": _yb,
            "material_estructural": "H.A.",
            "plano_fuente": "2017_67-102",
            "planta_fuente": "PLANTA CIELO PISO 3° (sub-plano del folio 102)",
            "estado_geometria": "VERIFICADA_VISUALMENTE_RETICULA_PRINCIPAL",
            "rotulo": None,
        }

# ---------------------------------------------------------------------------
# BLOQUE 2 — PLANO 102 — MUROS M.H.A. e=20 del núcleo E-F (posiciones
# INFERIDO_RESPALDADO desde pdfminer).
# Tres etiquetas M.H.A. e=20 en la capa de texto del plano 102 quedan en la
# zona del edificio (y_pdf > 440). Su posición aproximada (precisión ~0.5 m)
# se correlaciona con los ejes verificados:
#   M102_01 (x_pdf=69.1, y_pdf=533.0) -> X≈0.75, Y≈-3.45 cerca de E/1''
#   M102_02 (x_pdf=93.6, y_pdf=533.0) -> X≈4.13, Y≈-3.45 cerca de Eb/1''
#   M102_03 (x_pdf=93.2, y_pdf=458.4) -> X≈4.07, Y≈-14.53 cerca de Eb/2a
# Estos corresponden a los tramos del núcleo (Y_EXT núcleo) entre 1''-2 y
# alrededor de 2a. Estado INFERIDO_RESPALDADO (precisión del mapeo ±0.5 m).
# NIVEL: vista principal "PLANTA CIELO PISO 2°" del folio 102 -> PISO_2
# (z=3.91 m) según CONVENCION_NIVELES (convención R1). La retícula del esqueleto
# del bloque 1 en PISO_3 (z=7.87 m) proviene del SUB-PLANO "PLANTA CIELO
# PISO 3°" del mismo folio (ver CONVENCION_NIVELES); NO corresponde a la vista
# principal de estos muros.
# POSICION RESPALDADA, LONGITUD PENDIENTE. NO crean elasticBeamColumn hasta
# extremos exactos (TRAMO_NUCLEO_E_F).
# ---------------------------------------------------------------------------
_muros_nucleo_102 = [
    ("M102_01", "E", "1''", 0.75, -3.45, "tramo N-S junto a fila 1'' (X=0.75, Y=-3.45)"),
    ("M102_02", "Eb", "1''", 4.13, -3.45, "tramo N-S junto a fila 1'' (X=4.13, Y=-3.45)"),
    ("M102_03", "Eb", "2a", 4.07, -14.53, "tramo N-S junto al eje 2a (X=4.07, Y=-14.53)"),
]
for _mid, _ex, _ey, _px, _py, _nota in _muros_nucleo_102:
    posiciones_verificadas[_mid] = {
        "tipo": "muro_ha",
        "seccion": "M.H.A. e= 20",
        "espesor_m": 0.20,
        "eje_x_i": _ex,
        "eje_y_i": _ey,
        "eje_x_j": None,       # tramo pendiente de extremo (TRAMO_NUCLEO_E_F)
        "eje_y_j": None,
        "nivel": "PISO_2",
        "material_estructural": "H.A.",
        "plano_fuente": "2017_67-102",
        "planta_fuente": "PLANTA CIELO PISO 2",
        "estado_geometria": "INFERIDO_RESPALDADO_PDFMINER",
        "posicion_modelo": {"X": _px, "Y": _py},
        "nota": _nota,
        "id_plano": _mid,
        "rotulo": "M.H.A. e= 20 (núcleo E-F)",
    }

# ---------------------------------------------------------------------------
# BLOQUE 2 — PLANO 103 — MUROS M.H.A. e=20 del núcleo E-F (posiciones
# INFERIDO_RESPALDADO desde pdfminer con el mapeo calibrado de 103).
# PLANTA CIELO PISO 4° (PISO_4, z=11.83 m). Los mismos tres muros del núcleo
# e=20 del plan 102, confirmados de forma CRUZADA entre planos:
#   M103_01 (x_pdf=270.9, y_pdf=366.2) -> (0.75, -3.45)  cerca de E/1''
#   M103_02 (x_pdf=298.4, y_pdf=281.4) -> (4.11, -14.53) cerca de Eb/2a
#   M103_03 (x_pdf=298.8, y_pdf=366.2) -> (4.16, -3.45)  cerca de Eb/1''
# Incertidumbre del mapeo 103 ±1.5-2 m (offset de rótulo). Validación mutua
# con el plan 102: mismo núcleo, misma geometría en ambos niveles.
# ---------------------------------------------------------------------------
_muros_nucleo_103 = [
    ("M103_01", 0.749, -3.447, "núcleo E-F, fila 1'' (X≈0.75, Y≈-3.45)"),
    ("M103_02", 4.107, -14.530, "núcleo E-F, eje 2a (X≈4.11, Y≈-14.53)"),
    ("M103_03", 4.156, -3.447, "núcleo E-F, fila 1'' (X≈4.16, Y≈-3.45)"),
]
for _mid, _px, _py, _nota in _muros_nucleo_103:
    posiciones_verificadas[_mid] = {
        "tipo": "muro_ha",
        "seccion": "M.H.A. e= 20",
        "espesor_m": 0.20,
        "eje_x_i": None,       # posición en coordenadas: ver "posicion_modelo"
        "eje_y_i": None,
        "eje_x_j": None,
        "eje_y_j": None,
        "nivel": "PISO_4",
        "material_estructural": "H.A.",
        "plano_fuente": "2017_67-103",
        "planta_fuente": "PLANTA CIELO PISO 4",
        "estado_geometria": "INFERIDO_RESPALDADO_PDFMINER",
        "posicion_modelo": {"X": _px, "Y": _py},
        "nota": _nota,
        "id_plano": _mid,
        "rotulo": "M.H.A. e= 20 (núcleo E-F)",
    }

# ---------------------------------------------------------------------------
# BLOQUE 2 — PLANO 102 (VISTA PRINCIPAL PLANTA CIELO PISO 2°) — V.30/45 del
# sector sur bajo eje 3 -> PISO_2 (z=3.91 m), ver CONVENCION_NIVELES.
# Dos rótulos V.30/45 (x_pdf≈216 y 251, y_pdf=429) mapean a X≈21.0 y 25.8,
# Y≈-18.86. Respecto a los salientes CONFIRMADOS (v2, SALIENTES_PISO_2):
# el saliente 2 abarca X 20.00-30.00 con borde sur en Y=-18.61; los rótulos
# quedan ~0.25 m más al sur (dentro del error ±0.2-0.4 m del mapeo), por lo
# que su candidatura como vigas de borde del saliente 2 es plausible pero
# requiere cota explícita. El saliente 1 (X 10-17.49) no contiene rótulos
# V.30/45.
# Posición del rótulo INFERIDA RESPALDADA (dentro del sector sur confirmado);
# los EXTREMOS de cada viga (par de nodos) siguen PENDIENTE -> NO crean nodos.
# ---------------------------------------------------------------------------
_v3045_102 = [
    ("V3045_01", "Ga", "sector sur", "viga 30/45 - rótulo X≈21.0, Y≈-18.86; extremos "
     "PENDIENTE (candidata a borde sur saliente 2, -18.61 dentro del error del mapeo)"),
    ("V3045_02", "H", "sector sur", "viga 30/45 - rótulo X≈25.8, Y≈-18.86; extremos "
     "PENDIENTE (candidata a borde sur saliente 2, -18.61 dentro del error del mapeo)"),
]
for _mid, _ex, _ey, _nota in _v3045_102:
    posiciones_verificadas[_mid] = {
        "tipo": "viga_ha",
        "seccion": "V. 30/45",
        "nivel": "PISO_2",
        "eje_x_i": _ex,
        "eje_y_i": _ey,
        "eje_x_j": None,
        "eje_y_j": None,
        "material_estructural": "H.A.",
        "plano_fuente": "2017_67-102",
        "planta_fuente": "PLANTA CIELO PISO 2",
        "estado_geometria": "INFERIDO_RESPALDADO_EXTREMOS_PENDIENTE",
        "nota": _nota,
        "id_plano": _mid,
        "rotulo": "V. 30/45 (sector sur bajo eje 3)",
    }
# =============================================================================
# ESQUELETO PRINCIPAL 3D (etapa: levantar el esqueleto vertical completo).
# Retícula principal ya verificada: X = E, F, G, H, I, I' ;  Y = 1, 2, 3.
# Se usa SOLO la retícula principal; los ejes auxiliares (Eb, Ec, Ga, H1, H2,
# 1'', 2a) NO generan marcos en esta etapa.
# Tramo PISO_2 -> PISO_3 (bloque 1) YA EXISTE y NO se repite aquí.
# Metadata: estado_geometria = "ESQUELETO_PRINCIPAL_VERIFICADO".
# =============================================================================
_ejes_x_principales = ["E", "F", "G", "H", "I", "I'"]
_ejes_y_principales = ["1", "2", "3"]

_tramos_columnas_esqueleto = [
    # (nivel_inferior, nivel_superior, offset_tag_seg*1000, estado, plano_fuente)
    ("PISO_1S", "PISO_1", 0, "ESQUELETO_PRINCIPAL_VERIFICADO",
     "RETICULA PRINCIPAL (ejes vigentes, elevaciones)"),
    ("PISO_1", "PISO_2", 1, "ESQUELETO_PRINCIPAL_VERIFICADO",
     "RETICULA PRINCIPAL (ejes vigentes, elevaciones)"),
    ("PISO_3", "PISO_4", 2, "ESQUELETO_PRINCIPAL_VERIFICADO",
     "RETICULA PRINCIPAL (ejes vigentes, elevaciones)"),
    # Tramo de base: la elevación 302 (EJE 2) muestra la columna P.70x70
    # CONTINUA de PISO_1S (-4.01) hasta FUNDACION_SUP (-7.97) cota 3.96 m, y la
    # PLANTA FUNDACIONES (100) grilla de V.F. -> la retícula principal baja
    # hasta el nivel superior de fundación (nivel de apoyo del modelo).
    ("FUNDACION_SUP", "PISO_1S", 3, "VERIFICADO_ELEVACION_302_FUNDACION",
     "ELEVACION 302 (EJE 2) col. P.70x70 -4.01->-7.97 + PLANTA FUNDACIONES "
     "(100) grilla V.F."),
]
_niveles_vigas_esqueleto = ["PISO_1", "PISO_2", "PISO_4"]
_pares_vigas_x_esqueleto = [("E", "F"), ("F", "G"), ("G", "H"), ("H", "I"), ("I", "I'")]
_pares_vigas_y_esqueleto = [("1", "2"), ("2", "3")]

posiciones_esqueleto_principal = {}

_i_esq_x = {e: i for i, e in enumerate(_ejes_x_principales)}
_i_esq_y = {e: i for i, e in enumerate(_ejes_y_principales)}

for _i_seg_t, (_n0, _n1, _offset, _estado, _plano_fuente) in enumerate(
        _tramos_columnas_esqueleto):
    for _x in _ejes_x_principales:
        for _y in _ejes_y_principales:
            _clave = f"col_esq_{_x}_{_y}_{_n0}->{_n1}"
            posiciones_esqueleto_principal[_clave] = {
                "tipo": "columna_ha",
                "seccion": "P. 70x70",
                "eje_x": _x,
                "eje_y": _y,
                "nivel_inferior": _n0,
                "nivel_superior": _n1,
                "material_estructural": "H.A.",
                "plano_fuente": _plano_fuente,
                "planta_fuente": "TODOS LOS NIVELES ESTRUCTURALES",
                "estado_geometria": _estado,
                "id_plano": None,
                "rotulo": "P. 70x70 (marco principal)",
                # Tag único: rango 110000+ reservado al esqueleto (el rango
                # 1000xx queda para el bloque 1 del plano 102). El offset por
                # tramo se conserva para no alterar tags ya emitidos.
                "element_tag": 110000 + _offset * 1000
                               + _i_esq_x[_x] * 10 + _i_esq_y[_y],
            }

for _nivel in _niveles_vigas_esqueleto:
    for _xa, _xb in _pares_vigas_x_esqueleto:
        for _y in _ejes_y_principales:
            _clave = f"viga_esq_{_nivel}_X_{_xa}-{_xb}_Y{_y}"
            posiciones_esqueleto_principal[_clave] = {
                "tipo": "viga_ha",
                "seccion": "V. 60/80",
                "nivel": _nivel,
                "eje_x_i": _xa,
                "eje_y_i": _y,
                "eje_x_j": _xb,
                "eje_y_j": _y,
                "material_estructural": "H.A.",
                "plano_fuente": "RETICULA PRINCIPAL (ejes vigentes, elevaciones)",
                "planta_fuente": "TODOS LOS NIVELES ESTRUCTURALES (marco principal)",
                "estado_geometria": "ESQUELETO_PRINCIPAL_VERIFICADO",
                "id_plano": None,
                "rotulo": "V. 60/80 (marco principal)",
            }

    for _ya, _yb in _pares_vigas_y_esqueleto:
        for _x in _ejes_x_principales:
            _clave = f"viga_esq_{_nivel}_Y_{_ya}-{_yb}_X{_x}"
            posiciones_esqueleto_principal[_clave] = {
                "tipo": "viga_ha",
                "seccion": "V. 60/80",
                "nivel": _nivel,
                "eje_x_i": _x,
                "eje_y_i": _ya,
                "eje_x_j": _x,
                "eje_y_j": _yb,
                "material_estructural": "H.A.",
                "plano_fuente": "RETICULA PRINCIPAL (ejes vigentes, elevaciones)",
                "planta_fuente": "TODOS LOS NIVELES ESTRUCTURALES (marco principal)",
                "estado_geometria": "ESQUELETO_PRINCIPAL_VERIFICADO",
                "id_plano": None,
                "rotulo": "V. 60/80 (marco principal)",
            }
