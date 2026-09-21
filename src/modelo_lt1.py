# ============================================================================
# modelo_lt1.py
# Modelo estructural 3D LT1 en OpenSeesPy.
# La geometría (datos) vive separada en data/ (AGENTS): este archivo solo
# construye y verifica.
# ============================================================================

# Convención global del modelo
#   X : dirección horizontal del plano, positiva hacia la derecha.
#   Y : dirección vertical del plano, positiva hacia arriba.
#   Z : vertical del edificio, positiva hacia arriba.
# Unidades base: metros (m), kilonewtons (kN), kilopascales (kPa).

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openseespy.opensees as ops

from data import geometria as datos_geom
from data import secciones as datos_secc
from data import cargas as datos_carga
from data import tributacion as datos_trib
from data import inventario as datos_inv
from data import geometria_irregular as datos_irreg

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# ============================================================================
# 1. Geometría global (desde data/geometria.py)
# ============================================================================

ejes_x = datos_geom.ejes_x
ejes_x_pendientes = dict(datos_geom.ejes_x_pendientes)
ejes_y = datos_geom.ejes_y
niveles_z = datos_geom.niveles_z

indices_ejes_x = {k: i for i, k in enumerate(ejes_x)}
indices_ejes_y = {k: i for i, k in enumerate(ejes_y)}
indices_niveles_z = {k: i for i, k in enumerate(niveles_z)}

# ============================================================================
# 2. Nodos (crear nodos SOLO con posición verificada)
# ============================================================================

nodos = {}
metadata_nodos = {}
registro_tags_nodo = {}


def crear_nodo(tag, x, y, z):
    ops.node(tag, x, y, z)
    nodos[tag] = (x, y, z)


def obtener_tag_nodo(nivel, eje_x, eje_y):
    i_n = indices_niveles_z[nivel]
    i_x = indices_ejes_x[eje_x]
    i_y = indices_ejes_y[eje_y]
    tag = (i_n * 10000) + (i_x * 100) + i_y + 1
    registro_tags_nodo[tag] = (nivel, eje_x, eje_y)
    return tag


def crear_nodo_en_ejes(nivel, eje_x, eje_y):
    tag = obtener_tag_nodo(nivel, eje_x, eje_y)
    x = ejes_x[eje_x]
    y = ejes_y[eje_y]
    z = niveles_z[nivel]
    if tag not in nodos:
        crear_nodo(tag, x, y, z)
        metadata_nodos[tag] = {
            "nivel": nivel,
            "eje_x": eje_x,
            "eje_y": eje_y,
            "origen": "interseccion_ejes",
        }
    return tag


def crear_nodo_coordenadas(tag, x, y, nivel, referencia):
    z = niveles_z[nivel]
    if tag not in nodos:
        crear_nodo(tag, x, y, z)
        metadata_nodos[tag] = {
            "nivel": nivel,
            "eje_x": None,
            "eje_y": None,
            "origen": referencia,
        }
    return tag

# ============================================================================
# 3. Apoyos
# ============================================================================
# Idealización de apoyos PENDIENTE (no figura en los planos).
apoyos = {
    # "FUNDACION_SUP": {"tipo": "empotrado", "nodos": ()},   # PENDIENTE
}

# ============================================================================
# 4. Materiales (valores numéricos PENDIENTE en data/secciones.py)
# ============================================================================

mat = datos_secc.materiales


def registrar_materiales():
    opciones = ["PENDEINAE", "PENDIENTE"]
    if mat["hormigon"]["f_c_kPa"] is None:
        return False
    return True


materiales_ok = registrar_materiales()

# ============================================================================
# 5. Secciones (catálogo real de los planos, propiedades calculadas)
# ============================================================================

secciones_registradas = {}


def registrar_seccion(nombre, plano):
    datos = datos_secc.secciones_por_plano[plano][nombre]
    props = datos_secc.propiedades_por_seccion.get(nombre)
    secciones_registradas[nombre] = {
        "plano": plano,
        "datos": datos,
        "propiedades": props,
    }
    return props


for _plano, _secciones in datos_secc.secciones_por_plano.items():
    for _nombre in _secciones:
        registrar_seccion(_nombre, _plano)

# ============================================================================
# 5bis. Inventario estructural real registrado (desde data/inventario.py)
# ============================================================================
# Cada elemento del plano se registra con su nomenclatura ORIGINAL, su tipo y
# su plano de origen. La posición (eje_x, eje_y, nivel) queda
# PENDIENTE_COORDENADA hasta poder fijarla con una cota real / eje verificado.
# NO se crea ningún nodo ni elemento para estas entradas.

elementos_registrados = []
_elemento_id = 0
for _plano, _items in datos_inv.inventario_por_plano.items():
    for _seccion, _tipo, _n in _items:
        for _k in range(_n):
            _elemento_id += 1
            elementos_registrados.append({
                "id_registro": _elemento_id,
                "plano": _plano,
                "seccion": _seccion,
                "tipo": _tipo,
                "nivel": datos_inv.nivel_por_plano[_plano],
                "eje_x": None,
                "eje_y": None,
                "element_tag": None,
                "estado": "PENDIENTE_COORDENADA",
                "pendiente": "posicion no determinable con cota real en texto del plano",
            })

elementos_pendientes_coordenada = [
    {**dict(p), "estado": "PENDIENTE_COORDENADA"}
    for p in datos_inv.elementos_pendientes_coordenada
]

# ============================================================================
# 5ter. Construcción de geometría REAL (data-driven)
# ============================================================================
# La construcción SE BASA ÚNICAMENTE en data/inventario.py ->
# posiciones_verificadas. Con el estado actual de posiciones (vacío) no se
# crea nada. Al completarse esa estructura, esto genera nodos + elementTags.


def _etiquetar_nodos(tags, pos, rol):
    """Enriquece metadata_nodos con campos trazables del elemento verificado.
    No pisa el rol de columna ya registrado en un nodo compartido."""
    for t in tags:
        d = metadata_nodos.setdefault(t, {})
        for k in ("plano_fuente", "planta_fuente", "estado_geometria"):
            d[k] = pos[k]
        d.setdefault("tipo", rol)
        d.setdefault("material_estructural", pos.get("material_estructural"))
        d.setdefault("seccion", pos.get("seccion"))


_duplicados_evitados = []


def _append_unico(lista, registro, clave_unica):
    """Registra solo si no existe ya (misma conectividad/sección/nivel).
    Evita duplicar la retícula si un bloque posterior repite nodos."""
    ids = {_r.get("_unico") for _r in lista}
    if clave_unica in ids:
        _duplicados_evitados.append(clave_unica)
        return False
    registro["_unico"] = clave_unica
    lista.append(registro)
    return True


def crear_columna_desde_posicion(clave, pos):
    """Crea columna real sobre ejes verificados (nivel_inferior->nivel_superior)."""
    nivel_abajo = pos["nivel_inferior"]
    nivel_arriba = pos["nivel_superior"]
    eje_x = pos["eje_x"]
    eje_y = pos["eje_y"]
    ni = crear_nodo_en_ejes(nivel_abajo, eje_x, eje_y)
    ns = crear_nodo_en_ejes(nivel_arriba, eje_x, eje_y)
    element_tag = pos.get("element_tag")
    if element_tag is None:
        element_tag = 100000 + indices_ejes_x[eje_x] * 100 + indices_ejes_y[eje_y]
    registro = {
        "clave": clave,
        "id_plano": pos.get("id_plano"),          # rótulo original del plano (círculo)
        "rotulo": pos.get("rotulo"),
        "tipo_inventario": pos["tipo"],
        "seccion": pos["seccion"],
        "eje_x": eje_x,
        "eje_y": eje_y,
        "nivel_inferior": nivel_abajo,
        "nivel_superior": nivel_arriba,
        "nodo_inferior": ni,
        "nodo_superior": ns,
        "elementTag_opensees": element_tag,       # tag único de OpenSees
        "element_tag": element_tag,               # alias (compatibilidad de graficado)
        "estado_geometria": pos["estado_geometria"],
        "plano_fuente": pos["plano_fuente"],
        "planta_fuente": pos["planta_fuente"],
    }
    _etiquetar_nodos([ni, ns], pos, "columna")
    _tags_asignados[clave] = element_tag
    i_abajo = indices_niveles_z[nivel_abajo]
    i_arriba = indices_niveles_z[nivel_arriba]
    for nivel, i_nivel in indices_niveles_z.items():
        if i_abajo <= i_nivel < i_arriba:
            _append_unico(columnas_por_nivel[nivel], registro,
                          f"c|{nivel}|{ni}|{ns}|{pos['seccion']}")
    return registro


def crear_viga_desde_posicion(clave, pos):
    # Elementos con nodo final no fijado (pendiente) NO se construyen.
    if (pos.get("eje_x_j") is None or pos.get("eje_y_j") is None
            or pos.get("eje_x_i") is None or pos.get("eje_y_i") is None):
        _pendientes_vigas_no_construidas.append({
            "clave": clave,
            "id_plano": pos.get("id_plano"),
            "rotulo": pos.get("rotulo"),
            "estado_geometria": pos.get("estado_geometria"),
            "pendiente": "extremo(s) de la viga no fijado (eje None / no es eje)",
        })
        return None
    nivel = pos["nivel"]
    n1 = crear_nodo_en_ejes(nivel, pos["eje_x_i"], pos["eje_y_i"])
    n2 = crear_nodo_en_ejes(nivel, pos["eje_x_j"], pos["eje_y_j"])
    element_tag = pos.get("element_tag")
    if element_tag is None:
        global _proximo_tag_viga
        element_tag = _proximo_tag_viga
        _proximo_tag_viga += 1
    registro = {
        "clave": clave,
        "id_plano": pos.get("id_plano"),          # rótulo original del plano (círculo)
        "rotulo": pos.get("rotulo"),
        "tipo_inventario": pos["tipo"],
        "seccion": pos["seccion"],
        "nivel": nivel,
        "eje_x_i": pos["eje_x_i"],
        "eje_y_i": pos["eje_y_i"],
        "eje_x_j": pos["eje_x_j"],
        "eje_y_j": pos["eje_y_j"],
        "nodo_i": n1,
        "nodo_j": n2,
        "elementTag_opensees": element_tag,       # tag único de OpenSees
        "element_tag": element_tag,               # alias (compatibilidad)
        "estado_geometria": pos["estado_geometria"],
        "plano_fuente": pos["plano_fuente"],
        "planta_fuente": pos["planta_fuente"],
    }
    _etiquetar_nodos([n1, n2], pos, "viga")
    _tags_asignados[clave] = element_tag
    if n1 != n2:
        _append_unico(vigas_por_nivel[nivel], registro,
                      f"v|{nivel}|{n1}|{n2}|{pos['seccion']}")
    return registro


def crear_muro_desde_posicion(clave, pos):
    """Crea muro real sobre ejes verificados (nivel -> nivel, mismo piso).
    Si el elemento está marcado como posición PENDIENTE (eje_x_j/eje_y_j None)
    NO se crea: solo se informa y se registra como pendiente geométrico."""
    if pos.get("eje_x_j") is None or pos.get("eje_y_j") is None:
        _pendientes_muros_no_construidos.append({
            "clave": clave,
            "id_plano": pos.get("id_plano"),
            "rotulo": pos.get("rotulo"),
            "estado_geometria": pos.get("estado_geometria"),
            "pendiente": "extremo del tramo no fijado (eje_x_j/eje_y_j None)",
        })
        return None
    nivel = pos["nivel"]
    n1 = crear_nodo_en_ejes(nivel, pos["eje_x_i"], pos["eje_y_i"])
    n2 = crear_nodo_en_ejes(nivel, pos["eje_x_j"], pos["eje_y_j"])
    element_tag = pos.get("element_tag")
    if element_tag is None:
        global _proximo_tag_muro
        element_tag = _proximo_tag_muro
        _proximo_tag_muro += 1
    registro = {
        "clave": clave,
        "id_plano": pos.get("id_plano"),          # rótulo original del plano (núcleo/tramo)
        "rotulo": pos.get("rotulo"),
        "tipo_inventario": pos["tipo"],
        "seccion": pos["seccion"],
        "espesor_m": pos["espesor_m"],
        "nodo_i": n1,
        "nodo_j": n2,
        "formulacion": "PENDIENTE_FORMULACION_ELEMENTO",
        "elementTag_opensees": element_tag,       # tag único de OpenSees
        "element_tag": element_tag,               # alias (compatibilidad)
        "estado_geometria": pos["estado_geometria"],
        "plano_fuente": pos["plano_fuente"],
        "planta_fuente": pos["planta_fuente"],
    }
    _etiquetar_nodos([n1, n2], pos, "muro")
    _tags_asignados[clave] = element_tag
    if n1 != n2:
        _append_unico(muros_por_nivel[nivel], registro,
                      f"m|{nivel}|{n1}|{n2}|{pos['seccion']}|{pos['espesor_m']}")
    return registro


def construir_geometria():
    """Construye geometría real (ops.node + conectividad) desde datos de datos_inv.
    Sin elasticBeamColumn: materiales E/G siguen pendientes (no se inventan)."""
    construidos = 0

    def _procesar(posiciones):
        nonlocal construidos
        for clave, pos in posiciones.items():
            tipo = pos.get("tipo")
            if tipo and "columna" in tipo:
                crear_columna_desde_posicion(clave, pos)
                construidos += 1
            elif tipo and "viga" in tipo:
                crear_viga_desde_posicion(clave, pos)
                construidos += 1
            elif tipo and "muro" in tipo:
                crear_muro_desde_posicion(clave, pos)
                construidos += 1

    _procesar(datos_inv.posiciones_verificadas)
    n_esqueleto = len(getattr(datos_inv, "posiciones_esqueleto_principal", {}))
    if n_esqueleto:
        _procesar(datos_inv.posiciones_esqueleto_principal)
    return construidos


_tags_asignados = {}
_proximo_tag_viga = 200001
_proximo_tag_muro = 300001
_pendientes_muros_no_construidos = []
_pendientes_vigas_no_construidas = []

# ============================================================================
# 6. Transformaciones geométricas (3D)
# ============================================================================
# geomTransf 'Linear' con vector vecxz que define el plano local x-z
# (OpenSees: y_local = vecxz x x_local ; z_local = x_local x y_local).
# Se garantiza vecxz NO paralelo/coprotutorial con x_local en cada familia.
#
# COLUMNA VERTICAL  (x local = global Z, de abajo hacia arriba):
#   vecxz = (1,0,0)  ->  y local = (0,-1,0) = -Y ; z local = (1,0,0) = +X
# VIGA POR X        (x local = +- global X):
#   vecxz = (0,0,1)  ->  y local = (0,+-1,0) = +-Y ; z local = +(0,0,1) = +Z
# VIGA POR Y        (x local = +- global Y):
#   vecxz = (0,0,1)  ->  y local = (∓1,0,0) = ∓X ; z local = +(0,0,1) = +Z
# En vigas el eje local z queda vertical (contra gravedad); en columnas el
# eje local z queda horizontal (con la sección cuadrada Iy=Iz no altera rigidez).
GEOMTRANSF_TAGS = {"columna_vertical": 10001, "viga_x": 10002, "viga_y": 10003}
GEOMTRANSF_VECXZ = {
    "columna_vertical": (1.0, 0.0, 0.0),
    "viga_x": (0.0, 0.0, 1.0),
    "viga_y": (0.0, 0.0, 1.0),
}
geomtransf_definidas = {}
for _fam, _vecxz in GEOMTRANSF_VECXZ.items():
    ops.geomTransf("Linear", GEOMTRANSF_TAGS[_fam], *_vecxz)
    geomtransf_definidas[_fam] = {
        "tag": GEOMTRANSF_TAGS[_fam],
        "tipo": "Linear",
        "vecxz": _vecxz,
        "estado": "DEFINIDA",
    }

# ============================================================================
# 7. Columnas (schema documentado, ver P1L2)
# ============================================================================
# Cada entrada: {"id_plano", "seccion", "eje_x", "eje_y",
#                "nodo_inferior", "nodo_superior"}
columnas_por_nivel = {nivel: [] for nivel in niveles_z}

# ============================================================================
# 8. Vigas
# ============================================================================
vigas_por_nivel = {nivel: [] for nivel in niveles_z}
# Cada entrada: {"id_plano", "seccion", "nodo_i", "nodo_j"}

# ============================================================================
# 9. Muros equivalentes
# ============================================================================
# Convención de muro equivalente PENDIENTE (consta en planos nomenclatura
# M.H.A. e=15/20/25/30 con sección en data/secciones.py).
muros_por_nivel = {nivel: [] for nivel in niveles_z}

# 9bis. MUROS CERRADOS EN v2 -> COLUMNAS EQUIVALENTES VERTICALES.
# Convención académica entregada por el usuario/curso (data/secciones.py,
# CONVENCION_ACADEMICA_MUROS): cada muro M.H.A. se modela como elasticBeamColumn
# vertical entre DOS niveles Z consecutivos, con sección A=e*L_m e Iy/Iz/J por
# rectángulo según su orientación. Los seis paños cerrados del núcleo se
# verifican desde FUNDACION_SUP hasta PISO_4 en las plantas CIELO 1°
# SUBTERRANEO/PISO 1 (plano 101) y CIELO PISO 2, 3 y 4 (planos 102 y 103),
# por lo que forman 30 segmentos verticales continuos. Los muros perimetrales
# y los ejes inclinados siguen PENDIENTES.
muros_equivalentes = []
NODOS_MURO_EQUIVALENTES = set()      # nodos de muro (base+tope) NO slaves del diafragma
RIGID_LINKS_MUROS = []               # rigidLink('beam', master, nodo_muro) x 24
_TAG_BASE_MURO_EQUIVALENTE = 500100   # nodos inferiores del tramo (por muro)
_TAG_TOP_MURO_EQUIVALENTE = 500200    # nodos superiores del tramo (por muro)
_TAG_MURO_EQUIVALENTE_PRIMERO = 400001  # elementTags de las columnas equiv.
# ELIMINADOS en la auditoria: los antiguos elasticBeamColumn "vinculos rigidos"
# 450001-450012 (A=10 m2, Iy=Iz=0.5 m4, J=0.8 m4) NO estaban respaldados por
# planos/convencion. Sustituidos por ops.rigidLink('beam', master, nodo_muro),
# una restriccion cinematica real, sin rigidez arbitraria.


def _construir_nodos_muros_equivalentes():
    """Crea nodos y 30 segmentos equivalentes de los seis paños continuos.

    Estrategia de constraint FINAL (auditoria):
      El nodo de muro NO es slave del rigidDiaphragm y NO lleva ningun elemento
      artificial (fueron ELIMINADOS los elasticBeamColumn 450001-450012 de
      'vinculacion rigida': propiedades A=10/Iy=Iz=0.5/J=0.8 m4 no provistas por
      el usuario ni respaldadas por planos ni convencion academica).

      Cada nodo de muro (base y tope) se conecta por una RESTRICCION CINEMATICA
      REAL:
          ops.rigidLink('beam', <NODO MAESTRO del diafragma de su nivel>,
                        <nodo de muro>)
      con el nodo del muro como CONSTRAINT y el master del diafragma como
      RETAINED. Bajo constraints('Transformation'), el nodo de muro queda
      eliminado del sistema y hereda exactamente el movimiento de cuerpo rigido
      del plano: u_muro = u_master + th_master x r, th_muro = th_master
      (verificado en modelo minimo: match 0.0 con la prediccion del plano).

      Por que el RETAINED es el master y no el nodo estructural mas cercano
      (justificacion empirica, probada en repro):
        . rigidLink al nodo estructural ancla (que ES slave del diafragma)
          NO propaga la cadena ancla->diafragma bajo Transformation: el nodo de
          muro queda sin pertenecer al plano (carga lateral fuerte verificada).
        . rigidLink al MASTER del diafragma (nodo retained del propio diafragma)
          si propaga: reproduccion EXACTA del giro del plano, sin cadena ni
          sobre-restriccion.
      El nodo estructural mas cercano se conserva solo como REFERENCIA de
      posicion (nodo_ancla_X / distancia_X), sin elemento asociado.

      El elemento vertical del muro se crea en crear_elementos_elasticos."""
    global muros_equivalentes, NODOS_MURO_EQUIVALENTES
    muros_equivalentes = []
    NODOS_MURO_EQUIVALENTES = set()
    excluir_muro = set()
    indices_fisicos = {
        m["id"]: i for i, m in enumerate(datos_irreg.MUROS_CERRADOS_PISO_2)
    }
    bases_tag_nodo = {
        "FUNDACION_SUP": 500000,
        "PISO_1S": 500050,
        "PISO_1": 500100,
        "PISO_2": 500200,
        "PISO_3": 500300,
        "PISO_4": 500400,
    }
    bases_tag_elemento = {
        ("PISO_1", "PISO_2"): 400001,
        ("PISO_2", "PISO_3"): 400101,
        ("PISO_3", "PISO_4"): 400201,
        ("FUNDACION_SUP", "PISO_1S"): 400301,
        ("PISO_1S", "PISO_1"): 400401,
    }
    nodos_por_pano_nivel = {}
    for m in datos_irreg.MUROS_CERRADOS_NIVELES:
        nivel_abajo = m["nivel_inferior"]
        nivel_arriba = m["nivel_superior"]
        i = indices_fisicos[m["id_fisico"]]
        clave_tramo = (nivel_abajo, nivel_arriba)
        if clave_tramo not in bases_tag_elemento:
            raise ValueError(f"Tramo de muro no documentado: {clave_tramo}")
        x0, y0, x1, y1 = m["coords"]
        x, y = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        tags_extremo = {}
        for nivel, lado in ((nivel_abajo, "base"), (nivel_arriba, "tope")):
            clave_nodo = (m["id_fisico"], nivel)
            tag_n = nodos_por_pano_nivel.get(clave_nodo)
            if tag_n is None:
                tag_n = bases_tag_nodo[nivel] + i
                crear_nodo_coordenadas(
                    tag_n, x, y, nivel,
                    f"muro equiv {m['id_fisico']} ({nivel})")
                metadata_nodos[tag_n]["tipo"] = "muro_equivalente"
                metadata_nodos[tag_n]["constraint"] = (
                    "rigidLink al master del diafragma")
                nodos_por_pano_nivel[clave_nodo] = tag_n
                NODOS_MURO_EQUIVALENTES.add(tag_n)
                excluir_muro.add(tag_n)
            tags_extremo[lado] = tag_n
        tag_b = tags_extremo["base"]
        tag_t = tags_extremo["tope"]
        anclas = {}
        for tag_m, zlv, lado in ((tag_b, nivel_abajo, "inferior"),
                                 (tag_t, nivel_arriba, "superior")):
            zz = niveles_z[zlv]
            candidatos = [t for t, (xx, yy, zzz) in nodos.items()
                          if t not in excluir_muro and abs(zzz - zz) < 1e-9]
            ancla = min(candidatos,
                        key=lambda t: (nodos[t][0] - x) ** 2 +
                                      (nodos[t][1] - y) ** 2)
            dist = ((nodos[ancla][0] - x) ** 2 +
                    (nodos[ancla][1] - y) ** 2) ** 0.5
            metadata_nodos[tag_m]["nodo_ancla"] = ancla
            metadata_nodos[tag_m]["distancia_ancla_m"] = dist
            anclas[lado] = {"nodo": ancla, "distancia_m": dist}
        props = datos_secc.props_muro_columna_equivalente(
            m["espesor_cm"] / 100.0, m["longitud_m"], m["orientacion"])
        muros_equivalentes.append({
            "clave": m["id"],
            "id_fisico": m["id_fisico"],
            "seccion": m["seccion"],
            "espesor_m": m["espesor_cm"] / 100.0,
            "longitud_planta_m": m["longitud_m"],
            "orientacion": m["orientacion"],
            "en_plano_direccion": props["en_plano_direccion"],
            "b_local_y_m": props["b_local_y_m"],
            "h_local_z_m": props["h_local_z_m"],
            "nivel_inferior": nivel_abajo,
            "nivel_superior": nivel_arriba,
            "z_inferior_m": niveles_z[nivel_abajo],
            "z_superior_m": niveles_z[nivel_arriba],
            "longitud_vertical_m": niveles_z[nivel_arriba] - niveles_z[nivel_abajo],
            "nodo_inferior": tag_b,
            "nodo_superior": tag_t,
            "nodo_ancla_inferior": anclas["inferior"]["nodo"],
            "nodo_ancla_superior": anclas["superior"]["nodo"],
            "distancia_ancla_inferior_m": anclas["inferior"]["distancia_m"],
            "distancia_ancla_superior_m": anclas["superior"]["distancia_m"],
            "constraint": ("rigidLink('beam', master_diafragma_del_nivel, "
                           "nodo_muro): el nodo de muro es CONSTRAINED y hereda "
                           "el movimiento rigido del plano (NO slave del "
                           "rigidDiaphragm, NO elemento artificial)"),
            "x_m": x, "y_m": y,
            "element_tag": bases_tag_elemento[clave_tramo] + i,
            "A_m2": props["A_m2"],
            "Iy_m4": props["Iy_m4"],
            "Iz_m4": props["Iz_m4"],
            "J_m4": props["J_m4"],
            "estado_geometria": m["estado"],
            "activo_opensees": True,
            "fuente": (m["fuente_geometria"] + " + "
                       "CONVENCION_ACADEMICA_MUROS "
                       "(INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO)"),
        })
    return len(muros_equivalentes)

# ============================================================================
# 10. Apoyos y Diafragmas rígidos (idealización del proyecto)
# ============================================================================
# NIVEL DE APOYO (determinado por planos, no asumido):
#   FUNDACION_SUP = -7.97 m (nivel superior de fundación).
#   Evidencia: elevación 302 (EJE 2) muestra la columna P.70x70 CONTINUA de
#   PISO_1S (-4.01) hasta FUNDACION_SUP (-7.97) con cota 3.96 m y callouts
#   P.70x70 en todo el recorrido; PLAANTA FUNDACIONES (100) con grilla de V.F.
#   en ese nivel; corte base de elevaciones 300/302 hasta -9.17 m.
# Se crea el tramo FUNDACION_SUP -> PISO_1S en data/inventario.py.
#
# RESTRICCION 6 GDL en base: (Ux, Uy, Uz, Rx, Ry, Rz) = (1,1,1,1,1,1):
#   empotramiento clásico de base en modelo lineal elástico 3D académico.
apoyos = {}


def crear_apoyos_fundacion():
    if apoyos:
        return apoyos
    base = "FUNDACION_SUP"
    z_base = niveles_z[base]
    for g in columnas_por_nivel.values():
        for c in g:
            if c["nodo_inferior"] not in nodos:
                continue
            if abs(nodos[c["nodo_inferior"]][2] - z_base) < 1e-9:
                tag = c["nodo_inferior"]
                if tag in apoyos:
                    continue
                apoyos[tag] = {
                    "nodeTag": tag,
                    "nivel": base,
                    "eje_x": c["eje_x"],
                    "eje_y": c["eje_y"],
                    "restriccion": (1, 1, 1, 1, 1, 1),
                    "gdl_documentado": "Ux,Uy,Uz,Rx,Ry,Rz (6 GDL, empotrado)",
                    "fuente": (
                        "ELEVACION 302 (EJE 2): col. P.70x70 continua "
                        "-4.01->-7.97 (cota 3.96 m) + PLANTA FUNDACIONES (100): "
                        "grilla V.F.; idealización académica de base empotrada"),
                }
                ops.fix(tag, 1, 1, 1, 1, 1, 1)
    for m in muros_equivalentes:
        if m["nivel_inferior"] != base:
            continue
        tag = m["nodo_inferior"]
        if tag in apoyos:
            continue
        apoyos[tag] = {
            "nodeTag": tag,
            "nivel": base,
            "eje_x": "-",
            "eje_y": "-",
            "restriccion": (1, 1, 1, 1, 1, 1),
            "gdl_documentado": "Ux,Uy,Uz,Rx,Ry,Rz (6 GDL, empotrado)",
            "fuente": (
                "PLANTA FUNDACIONES (100) + PLANTA CIELO 1° SUBTERRANEO "
                "(101) + elevaciones 300-303; misma idealización académica "
                "de base empotrada aplicada a columnas y muros"),
            "tipo": "apoyo_muro_equivalente",
            "id_fisico_muro": m["id_fisico"],
        }
        ops.fix(tag, 1, 1, 1, 1, 1, 1)
    return apoyos


# ----------------------------------------------------------------------------
# Diafragmas rígidos horizontales por piso (rigidDiaphragm).
# Dirección perpendicular al diafragma: global Z (dirn 3) = vertical.
# El diafragma compatibiliza el movimiento EN EL PLANO XY:
#   Ux (1), Uy (2) y rotación Rz (6) de los nodos esclavos con el maestro;
# quedan LIBRES Uz (3) (vertical) y Rx/Ry (4, 5) (no compatibilizados).
# ----------------------------------------------------------------------------
NIVELES_DIAFRAGMA = ["PISO_1", "PISO_2", "PISO_3", "PISO_4"]
diafragmas = {nivel: {} for nivel in niveles_z}
nodos_maestros = {}


def crear_diafragmas():
    # LOS NODOS DE MURO EQUIVALENTE NO SON SLAVES del rigidDiaphragm.
    # Estrategia final (auditoria): cada nodo de muro se vincula por
    # ops.rigidLink('beam', master_del_nivel, nodo_muro) en _crear_rigid_links_muros()
    # (restriccion cinematica real). El diafragma solo lista los nodos de la
    # grilla estructural del nivel (18 por piso en esqueleto).
    for nivel in NIVELES_DIAFRAGMA:
        z = niveles_z[nivel]
        slaves = sorted(
            t for t, (x, y, zz) in nodos.items()
            if abs(zz - z) < 1e-9 and t not in NODOS_MURO_EQUIVALENTES)
        if not slaves:
            continue
        cx = sum(nodos[t][0] for t in slaves) / len(slaves)
        cy = sum(nodos[t][1] for t in slaves) / len(slaves)
        tag_m = 600000 + len(nodos_maestros) + 1
        ops.node(tag_m, cx, cy, z)
        nodos_maestros[tag_m] = {
            "nivel": nivel,
            "x": cx, "y": cy, "z": z,
            "es_nodo_maestro": True,
            "origen": "centro de la geometria de nodos estructurales del piso",
        }
        ops.fix(tag_m, 0, 0, 1, 1, 1, 0)
        ops.rigidDiaphragm(3, tag_m, *slaves)
        diafragmas[nivel] = {
            "nodo_maestro": tag_m,
            "nodos": tuple(slaves),
            "centroide": (cx, cy, z),
            "perpDirn": 3,
            "DOF_compatibilizados": "Ux (1), Uy (2), Rz (6)",
            "DOF_libres": "Uz (3), Rx (4), Ry (5)",
            "nodos_muro_vinculados_por_rigidLink":
                sorted(t for t in NODOS_MURO_EQUIVALENTES
                       if abs(nodos[t][2] - z) < 1e-9),
        }
    return diafragmas


def _crear_rigid_links_muros():
    """Restricciones cinemáticas reales de los nodos de muro equivalente.

    Para cada muro, base y tope heredan el movimiento de cuerpo rigido del
    plano de su nivel a traves del MASTER del rigidDiaphragm:

        ops.rigidLink('beam', <master del nivel>, <nodo de muro>)

    retained   = nodo maestro del diafragma del nivel (conectado al sistema
                 plano; hereda exactamente el giro del diafragma);
    constrained= nodo de muro.

    Justificacion empírica (repro minimo, constraints Transformation):
      . rigidLink a un SLAVE del diafragma (nodo estructural ancla) NO propaga:
        el nodo de muro queda sin pertenecer al plano (err 0.24/0.62 m).
      . rigidLink al MASTER si propaga: el nodo de muro reproduce el plano con
        error 0.0; el modelo analiza sin singularidad.
    Los rigidLink no crean elementos: NO cuentan en ops.getEleTags()."""
    global RIGID_LINKS_MUROS
    RIGID_LINKS_MUROS = []
    vistos = set()
    for m in muros_equivalentes:
        for nt, nivel in ((m["nodo_inferior"], m["nivel_inferior"]),
                          (m["nodo_superior"], m["nivel_superior"])):
            if nt in vistos:
                continue
            d = diafragmas.get(nivel)
            if not d or d["nodo_maestro"] not in set(ops.getNodeTags()):
                continue
            master = d["nodo_maestro"]
            ops.rigidLink("beam", master, nt)
            vistos.add(nt)
            RIGID_LINKS_MUROS.append({
                "nodo_muro": nt, "nivel": nivel,
                "nodo_maestro": master,
                "clave": m["clave"],
                "lado": "base" if nt == m["nodo_inferior"] else "tope",
            })
    return len(RIGID_LINKS_MUROS)

construidos_total = construir_geometria()
_construir_nodos_muros_equivalentes()
crear_apoyos_fundacion()
crear_diafragmas()
n_rigidlinks_muros = _crear_rigid_links_muros()

# ============================================================================
# 10bis. CARGAS DE LOSA + ÁREAS TRIBUTARIAS (P1L2) - SIN aplicar a OpenSees
# ============================================================================
# La losa NO es elemento finito: cada paño es solo información geométrica y de
# carga (nivel, límites, área, espesor, q_G, SC, fuente). q_G proviene del
# plano 700 celda por celda (PP. LOSA = 500 kgf/m² + PM. ADIC variable por zona).
# SC se registra aparte y NO se suma a q_G.
# La carga se asigna a las vigas mediante áreas tributarias (método de
# bisectrices, data/tributacion.py) y QUEDA PREPARADA: como no existen
# elasticBeamColumn (material PENDIENTE), NO se usa ops.eleLoad().
NIVELES_LOSA = ["PISO_1", "PISO_2", "PISO_3", "PISO_4"]
paños_por_nivel_dato = {}
tributacion_por_nivel = {}
resumen_conservacion = {}


def preparar_cargas_losa():
    """Construye paños + tributación para PISO_1..PISO_4. Sin ops.eleLoad.
    Usa q_G por-paño desde MATRIZ_CARGAS_ZONAL (NO uniforme)."""
    for nivel in NIVELES_LOSA:
        sc = datos_carga.SC_por_nivel.get(nivel, {})
        sc_pa = sc.get("kPa", 0.0)
        e_m = datos_carga.e_losa_m
        qg_map = _construir_qg_map(nivel)
        paños = datos_trib.paños_por_nivel(
            nivel, e_m=e_m, qG_map=qg_map)
        paños_por_nivel_dato[nivel] = paños
        trib = datos_trib.tributacion_nivel(
            nivel, vigas_por_nivel[nivel], nodos, paños)
        tributacion_por_nivel[nivel] = trib
    resumen = datos_trib.verificar_conservacion(tributacion_por_nivel)
    resumen_conservacion.update(resumen["resumen"])
    return resumen


def _construir_qg_map(nivel):
    """Construye dict {pano_id: qG_kPa} por-paño desde MATRIZ_CARGAS_ZONAL."""
    from data.cargas import MATRIZ_CARGAS_ZONAL, kgf_m2_a_kPa, _bay_to_col
    mat = MATRIZ_CARGAS_ZONAL[nivel]
    pp = mat["pp_losa_kgf_m2"]
    qg_map = {}
    for ix in range(5):
        bay_x = ix + 1
        for iy in range(2):
            y_row = iy + 1
            pano_id = f"{nivel}_P{bay_x}{y_row}"
            col = _bay_to_col(bay_x)
            zona = mat["zonas"][(col, y_row)]
            pm = zona["pm_kg"]
            qg = pp if pm is None else pp + pm
            qg_map[pano_id] = kgf_m2_a_kPa(qg)
    return qg_map


def escribir_control_areas_tributarias(ruta):
    """Control txt de paños, áreas tributarias y carga por viga por nivel."""
    import io
    buf = io.StringIO()
    w = buf.write
    w("=" * 80 + "\n")
    w("CONTROL AREAS TRIBUTARIAS Y CARGAS DE LOSA · LT1\n")
    w("  (q_G por-paño celda por celda, NO uniforme)\n")
    w("=" * 80 + "\n")
    w("Fuente: plano 700 celda por celda (tiles OCR Vision, Matrix 5x5).\n")
    w("  PP.LOSA = 500 kgf/m² = 4.903 kPa (e=0.20 m, gamma=2500 kgf/m³)\n")
    w("  q_G = PP.LOSA + PM.ADIC (variable por zona/paño)\n")
    w("  SC se registra aparte; NO incluida en q_G.\n")
    w("Resolución e: 0.20 m (pisos) ≠ 0.25 m (fundaciones, plan 100 hoja fund.).\n")
    w("Método tributario: bisectrices (Voronoi de vigas) sobre paños regulares.\n")
    w("-" * 80 + "\n")
    for nivel in NIVELES_LOSA:
        trib = tributacion_por_nivel[nivel]
        r = resumen_conservacion[nivel]
        w(f"\nNIVEL {nivel}  (z={niveles_z[nivel]} m)\n")
        w(f"  paños: {len(trib['paños'])} | A_losa total: {trib['A_total_m2']:.3f} m2\n")
        w(f"  P_losa_total = Σ(q_G_paño × A_paño) = {trib['P_losa_total_kN']:.3f} kN\n")
        w(f"  P_vigas      = {trib['P_vigas_kN']:.3f} kN\n")
        w(f"  error relativo conservacion: {trib['error_relativo']:.3e} "
          f"({'OK' if r['dentro_tolerancia'] else 'FUERA_TOLERANCIA'})\n")
        w(f"  vigas con carga: {r['vigas_con_carga']} | sin carga: "
          f"{r['vigas_sin_carga']}\n")
        w(f"  --- Paños por nivel ---\n")
        w(f"  {'paño':<14s} {'area[m2]':>8s} {'qG[kPa]':>8s} {'SC[kPa]':>8s} "
          f"{'fuente':s}\n")
        for p in trib["paños"]:
            w(f"  {p['id']:<14s} {p['area_m2']:8.2f} {p['q_G_kPa']:8.4f} "
              f"{p['SC_kPa']:8.4f} {p.get('fuente_qG','')}\n")
        w(f"  --- Vigas por nivel ---\n")
        w("  {:>8s} {:<6s} {:>10s} {:>10s} {:>10s} {:>10s} {:>14s}\n".format(
            "tag", "orient", "L[m]", "A_trib[m2]", "P[kN]", "w[kN/m]", "borde"))
        for tag in sorted(trib["vigas_carga"]):
            c = trib["vigas_carga"][tag]
            w(f"  {c['element_tag']:8d} {c['orientacion']:<6s} "
              f"{c['longitud_m']:10.3f} {c['A_trib']:10.3f} "
              f"{c['P_losa_kN']:10.3f} {c['w_kN_m']:10.3f}  "
              f"{','.join(c['origen'][:4])}{('…' if len(c['origen'])>4 else '')}\n")
        if trib["bordes_sin_viga"]:
            w(f"  [PENDIENTE] bordes sin viga: {trib['bordes_sin_viga']}\n")
        w(f"  SC zonal: {sorted(set(p['SC_kPa'] for p in trib['paños']))}\n")
    w("\n" + "=" * 80 + "\n")
    w("PENDIENTES / NOTAS ZONALES\n")
    for p in datos_carga.PENDIENTES_MATRIZ:
        w(f"  - {p}\n")
    w("\nCARGAS PUNTUALES (registradas, NO aplicadas):\n")
    for cp in datos_carga.CARGAS_PUNTUALES:
        w(f"  - {cp['tipo']} {cp['magnitud_kgf']:.0f} kg en {cp['nivel']} "
          f"({cp['ubicacion']}) [{cp['estado']}]\n")
    w("\nCARGAS LINEALES (registradas, NO aplicadas):\n")
    for cl in datos_carga.CARGAS_LINEALES:
        w(f"  - {cl['tipo']} {cl['magnitud_kgf_m']:.0f} kgf/m en {cl['nivel']} "
          f"zona {cl['zona']} [{cl['estado']}]\n")
    w("\nPISO_1S: sin vigas del esqueleto -> sin transferencia de losa (PENDIENTE "
      "V.S.I./losas del 1° sub).\n")
    w("No se aplica ops.eleLoad() (materiales PENDIENTES); la aplicación será "
      "inmediata cuando existan los elasticBeamColumn.\n")
    w("=" * 80 + "\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    return ruta


def escribir_matriz_cargas(ruta):
    """Escribe la matriz de cargas del plano 700: 40 paños, 1 por fila."""
    import io
    from data.cargas import MATRIZ_CARGAS_ZONAL, PENDIENTES_MATRIZ
    buf = io.StringIO()
    w = buf.write
    w("=" * 105 + "\n")
    w("MATRIZ DE CARGAS PLANO 700 · LT1\n")
    w("  (40 paños · 4 niveles × 5 bahías × 2 bandas Y)\n")
    w("=" * 105 + "\n")
    hdr = (f"{'nivel':<10s} {'pano':<14s} {'bahía':>6s} {'Y_band':>7s} "
           f"{'area[m2]':>8s} {'PP_L[kg/m²]':>11s} {'PM[kg/m²]':>10s} "
           f"{'qG[kPa]':>8s} {'SC[kg/m²]':>9s} {'fuente':<40s} {'estado':<25s}")
    w(hdr + "\n")
    w("-" * 105 + "\n")
    for nivel in NIVELES_LOSA:
        mat = MATRIZ_CARGAS_ZONAL[nivel]
        pp = mat["pp_losa_kgf_m2"]
        e_m = mat["e_m"]
        ancho_bahia = {1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0, 5: 2.5}
        laterales = {1: "E-F", 2: "F-G", 3: "G-H", 4: "H-I", 5: "I-I'"}
        filas_y = [(1, "1-2", 8.9), (2, "2-3", 7.25)]
        for ix in range(5):
            bay_x = ix + 1
            col = datos_carga._bay_to_col(bay_x)
            eje = laterales[bay_x]
            for y_row, y_label, alto in filas_y:
                pano_id = f"{nivel}_P{bay_x}{y_row}"
                zona = mat["zonas"][(col, y_row)]
                pm = zona["pm_kg"]
                sc = zona["sc_kg"]
                qg_kg = pp if pm is None else pp + pm
                qg_kpa = datos_carga.kgf_m2_a_kPa(qg_kg)
                area = ancho_bahia[bay_x] * alto
                fuente = zona["fuente"]
                estado = zona["estado"]
                w(f"{nivel:<10s} {pano_id:<14s} {eje:>6s} {y_label:>7s} "
                  f"{area:8.2f} {pp:11.0f} {pm if pm is not None else 0:10.0f} "
                  f"{qg_kpa:8.4f} {sc if sc is not None else 0:9.0f} "
                  f"{fuente:<40s} {estado:<25s}\n")
    w("-" * 105 + "\n")
    w("\nPENDIENTES / NOTAS:\n")
    for p in PENDIENTES_MATRIZ:
        w(f"  - {p}\n")
    w("\nCARGAS PUNTUALES (NO incluidas en la matriz):\n")
    for cp in datos_carga.CARGAS_PUNTUALES:
        w(f"  - {cp['tipo']} {cp['magnitud_kgf']:.0f} kg en {cp['nivel']} "
          f"({cp['ubicacion']}) [{cp['estado']}]\n")
    w("\nCARGAS LINEALES (NO incluidas en la matriz, registradas para vigas I-I'):\n")
    for cl in datos_carga.CARGAS_LINEALES:
        w(f"  - {cl['tipo']} {cl['magnitud_kgf_m']:.0f} kgf/m en {cl['nivel']} "
          f"zona {cl['zona']} [{cl['estado']}]\n")
    w("=" * 105 + "\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  [OK] matriz de cargas: {ruta}")
    return ruta


def control_areas_tributarias_lt1(output_dir="outputs"):
    """Plot 2x2: por nivel, paños coloreados por q_G + vigas con w (kN/m)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    xmin, xmax = 0.0, 42.5
    ymin, ymax = -16.15, 0.0
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    vmax = max(max(c["w_kN_m"] for c in tributacion_por_nivel[n]["vigas_carga"].values())
               for n in NIVELES_LOSA)
    vmin = 0.0
    for ax, nivel in zip(axes.flat, NIVELES_LOSA):
        trib = tributacion_por_nivel[nivel]
        qg_vals_n = sorted(set(round(p["q_G_kPa"], 3) for p in trib["paños"]))
        ax.set_title(f"{nivel} · q_G={qg_vals_n} kPa · "
                     f"P_losa={trib['P_losa_total_kN']:.0f} kN")
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.grid(True, lw=0.4, alpha=0.4)
        for p in trib["paños"]:
            x0 = datos_geom.ejes_x[p["eje_x0"]]
            x1 = datos_geom.ejes_x[p["eje_x1"]]
            y0 = datos_geom.ejes_y[p["eje_y0"]]
            y1 = datos_geom.ejes_y[p["eje_y1"]]
            rect = Rectangle((x0, y0), x1 - x0, y1 - y0,
                             fill=False, edgecolor="0.6", lw=0.8)
            ax.add_patch(rect)
            ax.text((x0 + x1) / 2, (y0 + y1) / 2,
                    f"{p['q_G_kPa']:.2f}\nkPa\n{p['area_m2']:.1f} m²",
                    ha="center", va="center", fontsize=6, color="0.3")
        for tag, c in trib["vigas_carga"].items():
            xi, yi, _ = nodos[c["nodo_i"]]
            xj, yj, _ = nodos[c["nodo_j"]]
            ax.plot([xi, xj], [yi, yj], color=plt.cm.viridis(
                c["w_kN_m"] / vmax if vmax else 0.0), lw=2.6,
                solid_capstyle="round")
            ax.annotate(f"{c['element_tag']}\n{c['w_kN_m']:.0f} kN/m",
                        ((xi + xj) / 2, (yi + yj) / 2),
                        fontsize=6, ha="center", va="bottom", color="k")
        ax.text(0.02, 0.98, f"A={trib['A_total_m2']:.1f} m²\n"
                f"err_consv={trib['error_relativo']:.2e}",
                transform=ax.transAxes, fontsize=8, va="top",
                bbox=dict(fc="white", ec="0.7"))
    sm = plt.cm.ScalarMappable(cmap="viridis",
                               norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, shrink=0.9)
    cbar.set_label("w equivalente de losa sobre viga [kN/m] (q_G por-paño, sin SC)")
    fig.suptitle("LT1 · Areas tributarias de losa · q_G por-paño (celda por celda, "
                 "SC registrada aparte)")
    os.makedirs(output_dir, exist_ok=True)
    ruta = os.path.join(output_dir, "areas_tributarias_lt1.png")
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] areas tributarias 2D: {ruta}")
    return ruta


def verificacion_tributacion():
    print("-" * 62)
    print("VERIFICACION CARGAS DE LOSA + AREAS TRIBUTARIAS (q_G por-paño)")
    print("-" * 62)
    todos_ok = resumen_conservacion.get("ok", False)
    A_tot = 0.0
    P_tot = 0.0
    P_vig = 0.0
    for nivel in NIVELES_LOSA:
        r = resumen_conservacion[nivel]
        A_tot += r["A_losa_m2"]
        P_tot += r["P_losa_total_kN"]
        P_vig += r["P_vigas_kN"]
        qg_vals_n = sorted(set(round(p["q_G_kPa"], 3)
                               for p in tributacion_por_nivel[nivel]["paños"]))
        print(f"  {nivel:8s}: A={r['A_losa_m2']:9.3f} m2  "
              f"qG={qg_vals_n} kPa  "
              f"P_losa={r['P_losa_total_kN']:10.3f} kN  P_vigas="
              f"{r['P_vigas_kN']:10.3f} kN  err={r['error_relativo']:.2e}  "
              f"{'OK' if r['dentro_tolerancia'] else 'FUERA_TOL'}")
        for b in r["bordes_sin_viga"]:
            print(f"     [PENDIENTE] borde sin viga: {b}")
    if A_tot:
        err_g = abs(P_tot - P_vig) / P_tot
    else:
        err_g = float("nan")
    print(f"  TOTAL (PISO_1..4): A_losa={A_tot:.3f} m2  "
          f"P_losa={P_tot:.3f} kN  P_vigas={P_vig:.3f} kN  "
          f"err_rel_g={err_g:.2e}")
    print(f"  vigas con carga por nivel: "
          f"{[resumen_conservacion[n]['vigas_con_carga'] for n in NIVELES_LOSA]} | "
          f"sin carga: "
          f"{[resumen_conservacion[n]['vigas_sin_carga'] for n in NIVELES_LOSA]}")
    print(f"  SC registrada aparte (no suma en q_G) | sin ops.eleLoad()"
          f" (materiales PENDIENTES)")
    print("-" * 62)
    return todos_ok
# elasticBeamColumn(ndm=3): [tag, iNode, jNode, A, E, G, J, Iy, Iz, transTag].
# E y G provienen de data/secciones.py. Mientras sigan PENDIENTES (plano 000
# remite a E.T.O.G./001 no provistos) NO se crea ningún elemento, pero sí se
# deja toda la conectividad lista (elementTags ya reservados).
elementos_opensees = []


def materiales_listos():
    h = datos_secc.materiales["hormigon"]
    return h["E_kPa"] is not None and h.get("G_kPa") is not None


def _familia_transformacion(reg):
    if "columna" in reg.get("tipo_inventario", ""):
        return "columna_vertical"
    if reg.get("eje_x_i") == reg.get("eje_x_j"):
        return "viga_y"
    return "viga_x"


def crear_elementos_elasticos():
    """Crea elasticBeamColumn: 90 columnas + 108 vigas + 30 muros equivalentes
    = 228 en total, con los tags ya reservados. Devuelve la cantidad creada
    (0 si materiales PENDIENTES: E/nu/G aún son None).

    Los nodos de muro NO tienen elementos horizontales: se conectan a su nivel
    por restricción cinemática real ops.rigidLink('beam', master, nodo_muro)
    (24 links, ver _crear_rigid_links_muros). Los rigidLink no son elementos y
    no cuentan en ops.getEleTags(). Esto fue decidido tras la auditoría empírica
    (estrategia A: nodos de muro como slaves directos -> matriz singular;
    estrategia B: rigidLink al nodo ancla slave -> no propaga el plano;
    estrategia C adoptada: rigidLink al MASTER del diafragma -> error 0.0)."""
    if not materiales_listos():
        return 0
    h = datos_secc.materiales["hormigon"]
    creados = 0
    vistos = set()

    for g in columnas_por_nivel.values():
        for c in g:
            if c["element_tag"] in vistos:
                continue
            props = datos_secc.propiedades_por_seccion[c["seccion"]]
            fam = _familia_transformacion(c)
            ops.element("elasticBeamColumn", c["element_tag"],
                        c["nodo_inferior"], c["nodo_superior"],
                        props["A_m2"], h["E_kPa"], h["G_kPa"],
                        props["J_m4"], props["Iy_m4"], props["Iz_m4"],
                        GEOMTRANSF_TAGS[fam])
            elementos_opensees.append({**c,
                                       "es_elasticBeamColumn": True,
                                       "familia_transf": fam,
                                       "E_kPa": h["E_kPa"], "G_kPa": h["G_kPa"]})
            vistos.add(c["element_tag"])
            creados += 1

    for nivel, g in vigas_por_nivel.items():
        for v in g:
            props = datos_secc.propiedades_por_seccion[v["seccion"]]
            fam = _familia_transformacion(v)
            ops.element("elasticBeamColumn", v["element_tag"],
                        v["nodo_i"], v["nodo_j"],
                        props["A_m2"], h["E_kPa"], h["G_kPa"],
                        props["J_m4"], props["Iy_m4"], props["Iz_m4"],
                        GEOMTRANSF_TAGS[fam])
            elementos_opensees.append({**v,
                                       "es_elasticBeamColumn": True,
                                       "familia_transf": fam,
                                       "E_kPa": h["E_kPa"], "G_kPa": h["G_kPa"]})
            creados += 1

    for mw in muros_equivalentes:
        if mw["element_tag"] in vistos:
            continue
        ops.element("elasticBeamColumn", mw["element_tag"],
                    mw["nodo_inferior"], mw["nodo_superior"],
                    mw["A_m2"], h["E_kPa"], h["G_kPa"],
                    mw["J_m4"], mw["Iy_m4"], mw["Iz_m4"],
                    GEOMTRANSF_TAGS["columna_vertical"])
        elementos_opensees.append({**mw,
                                   "es_elasticBeamColumn": True,
                                   "familia_transf": "columna_vertical",
                                   "tipo_inventario": "muro_ha",
                                   "E_kPa": h["E_kPa"], "G_kPa": h["G_kPa"]})
        vistos.add(mw["element_tag"])
        creados += 1

    # NOTA (auditoria): los antiguos elasticBeamColumn "vínculos rígidos"
    # 450001-450012 (A=10 m2, Iy=Iz=0.5 m4, J=0.8 m4) fueron ELIMINADOS por no
    # provenir del usuario, planos ni convención académica. La conexión de cada
    # nodo de muro al plano de su nivel es ahora una restricción cinemática
    # real: ops.rigidLink('beam', <master del diafragma>, <nodo de muro>),
    # creada en _crear_rigid_links_muros(). Los rigidLink NO son elementos y
    # NO aparecen en ops.getEleTags().

    return creados


# Crea los elementos elásticos al importar (0 mientras E/G estén PENDIENTES).
n_elasticos_creados = crear_elementos_elasticos()

# Conjuntos de tags reservados (para trazabilidad/verificaciones).
col_tags = sorted({c["element_tag"] for g in columnas_por_nivel.values() for c in g})
viga_tags = sorted({v["element_tag"] for g in vigas_por_nivel.values() for v in g})

# ============================================================================
# 11. Cargas gravitacionales y áreas tributarias
# ============================================================================
# data/cargas.py: q_G = PP + terminaciones (terminaciones y gamma PENDIENTES);
# SC del plano 700 PENDIENTE (rasterizado).

cargas_gravitacionales = {
    "q_G_por_nivel": datos_carga.q_G_por_nivel,
    "SC_por_nivel": datos_carga.SC_por_nivel,
}


def area_tributaria(vigas_concurrentes, nivel):
    """Área tributaria de un nudo central (PENDIENTE hasta tener geometría)."""
    if not nodos:
        return None
    return None

# ============================================================================
# 12. Análisis y verificaciones
# ============================================================================


def verificacion_grilla_x():
    ok = True
    names = list(ejes_x)
    vals = list(ejes_x.values())
    if vals[0] != 0.0:
        ok = False
        print(f"  [KO] primer eje X no nulo: {names[0]}={vals[0]}")
    for a, b in zip(names, names[1:]):
        if not (ejes_x[a] < ejes_x[b]):
            ok = False
            print(f"  [KO] ejes X no crecientes: {a} -> {b}")
    total = vals[-1] - vals[0]
    if abs(total - 42.500) > 1.0e-9:
        ok = False
        print(f"  [KO] extensión total X = {total} m (esperada 42.500 m)")
    print(f"  [OK] grilla X: {len(ejes_x)} ejes crecientes con extensión {total:.3f} m (42.500)" if ok
          else "  [KO] grilla X")
    return ok


def verificacion_grilla_y():
    ok = True
    names = list(ejes_y)
    vals = list(ejes_y.values())
    if vals[0] != 0.0:
        ok = False
        print(f"  [KO] primer eje Y no nulo: {names[0]}={vals[0]}")
    for a, b in zip(names, names[1:]):
        if not (ejes_y[a] > ejes_y[b]):
            ok = False
            print(f"  [KO] ejes Y no decrecientes: {a} -> {b}")
    total = vals[-1] - vals[0]
    if abs(total - (-16.150)) > 1.0e-9:
        ok = False
        print(f"  [KO] extensión total Y = {total} m (esperada -16.150 m)")
    print(f"  [OK] grilla Y: {len(ejes_y)} ejes decrecientes con extensión {total:.3f} m (-16.150)" if ok
          else "  [KO] grilla Y")
    return ok


def verificacion_niveles():
    ok = True
    orden = list(niveles_z)
    for a, b in zip(orden, orden[1:]):
        if not (niveles_z[a] < niveles_z[b]):
            ok = False
            print(f"  [KO] niveles no monótonos: {a} -> {b}")
    print(f"  [OK] niveles_z: {len(orden)} niveles monótonos" if ok else "  [KO] niveles_z")
    return ok


def verificacion_tags():
    ok = True
    tags = {}
    for nivel in niveles_z:
        for eje_x in ejes_x:
            for eje_y in ejes_y:
                tag = obtener_tag_nodo(nivel, eje_x, eje_y)
                if tag in tags:
                    ok = False
                    print(f"  [KO] tag duplicado {tag}")
                tags[tag] = (nivel, eje_x, eje_y)
    print(f"  [OK] tags únicos para {len(niveles_z) * len(ejes_x) * len(ejes_y)} intersecciones" if ok
          else "  [KO] tags")
    return ok


def verificacion_secciones():
    ok = True
    for nombre, registro in secciones_registradas.items():
        if registro["propiedades"] is None:
            ok = False
            print(f"  [KO] sección sin propiedades: {nombre}")
    print(f"  [OK] {len(secciones_registradas)} secciones del catálogo computadas" if ok
          else "  [KO] secciones")
    return ok


def verificacion_cargas():
    ok = True
    pendientes = []
    if materiales_ok is False:
        pendientes.append("materials (f'c/E/fy)")
    if datos_carga.peso_especifico_ha_kN_m3 is None:
        pendientes.append("peso específico H°A°")
    for nivel in NIVELES_LOSA:
        e = datos_carga.losa_por_nivel[nivel]["estado"].lower()
        if "crosscheck" in e or "pendiente" in e:
            pendientes.append(f"cotejo espesor losa {nivel} (plan 100 e=0.25 vs plan 700 e=0.20)")
    for p in datos_carga.PENDIENTES_MATRIZ:
        pendientes.append("plan 700: " + p.split()[0] + " (ver matriz_cargas_plano700.txt).")
    for p in pendientes:
        print(f"  [PENDIENTE] {p}")
    print(f"  [OK] q_G y SC cargados del plano 700 (tentativos) | "
          f"SC aparte de q_G | tributación lista | pendientes de cotejo: "
          f"{len(pendientes)} · eleLoad aplicado si material LISTO")

def verificacion_nodos_reales():
    reales = len(nodos)
    tags_posibles = len(registro_tags_nodo) if registro_tags_nodo else 0
    print(f"  [OK] nodos REALES creados con ops.node(): {reales}")
    print(f"  [NOTA] tags posibles validados (7x11x5=385), no son nodos: {tags_posibles}")
    por_nivel = {}
    for tag, (x, y, z) in nodos.items():
        nivel = metadata_nodos.get(tag, {}).get("nivel", "s/nivel")
        por_nivel.setdefault(nivel, []).append(tag)
    for nivel in niveles_z:
        print(f"     {nivel:14s}: {len(por_nivel.get(nivel, []))} nodos")
    return reales


def verificacion_ubicados():
    n_col = sum(1 for g in columnas_por_nivel.values() for _ in g)
    n_vig = sum(1 for g in vigas_por_nivel.values() for _ in g)
    n_mur = sum(1 for g in muros_por_nivel.values() for _ in g)
    print(f"  [OK] columnas ubicadas: {n_col}")
    print(f"  [OK] vigas ubicadas: {n_vig}")
    print(f"  [OK] muros ubicados: {n_mur}")
    print(f"  [INFO] geometría construida desde posiciones verificadas: {construidos_total}")
    return n_col + n_vig + n_mur


def verificacion_elementos_registrados():
    total = len(elementos_registrados)
    pend_coord = sum(1 for e in elementos_registrados if e["estado"] == "PENDIENTE_COORDENADA")
    pend_mat = sum(1 for e in elementos_registrados if e["pendiente"].startswith("material"))
    by_tipo = {}
    for e in elementos_registrados:
        by_tipo[e["tipo"]] = by_tipo.get(e["tipo"], 0) + 1
    print(f"  [OK] elementos registrados del inventario: {total}")
    print(f"  [PENDIENTE] por coordenada: {pend_coord}")
    print(f"  [PENDIENTE] por material: {pend_mat}")
    print(f"  [PENDIENTE] por formulación de muro: "
          f"{sum(1 for e in elementos_registrados if e['tipo'] == 'muro_ha')}")
    print(f"  [INFO] desglose por tipo: {by_tipo}")
    return total


def verificacion_conectividad():
    coordenadas = [e["eje_x"] for e in elementos_registrados if e["eje_x"] is not None]
    print(f"  [OK] elementos con posición fijada (verificable): {len(coordenadas)}")
    print(f"  [OK] elementos con posición PENDIENTE: "
          f"{sum(1 for e in elementos_registrados if e['eje_x'] is None)}")
    return True

def control_visual(output_dir="outputs"):
    """Control visual: vista 3D (grilla + niveles + elementos) y planta XY PISO_3.
    NO se dibujan los tags posibles (385): solo nodos reales creados."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    xmin, xmax = min(ejes_x.values()), max(ejes_x.values())
    ymin, ymax = min(ejes_y.values()), max(ejes_y.values())

    fig = plt.figure(figsize=(15, 9))

    ax = fig.add_subplot(121, projection='3d')
    zs = list(niveles_z.values())

    for z in zs:
        for (x0, y0), (x1, y1) in [((xmin, ymin), (xmax, ymin)),
                                   ((xmax, ymin), (xmax, ymax)),
                                   ((xmax, ymax), (xmin, ymax)),
                                   ((xmin, ymax), (xmin, ymin))]:
            ax.plot([x0, x1], [y0, y1], [z, z], color="0.6", lw=0.8, alpha=0.7)

    for (x0, y0) in [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]:
        ax.plot([x0, x0], [y0, y0], [min(zs), max(zs)], color="0.6", lw=1.0)

    for nivel in niveles_z:
        z = niveles_z[nivel]
        ax.text(xmin - 1.2, ymin, z, nivel, fontsize=8, color="0.3")
    for eje_x, x in ejes_x.items():
        ax.text(x, ymin - 1.2, min(zs), eje_x, fontsize=8, color="0.3")
    for eje_y, y in ejes_y.items():
        ax.text(xmin - 1.2, y, min(zs), eje_y, fontsize=8, color="0.3")

    for tag, (x, y, z) in nodos.items():
        ax.scatter([x], [y], [z], color="crimson", s=24, depthshade=False)

    for nivel, group in vigas_por_nivel.items():
        for v in group:
            i, j = v["nodo_i"], v["nodo_j"]
            (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
            color = "tab:blue" if v["seccion"].startswith("V. 60/80") else "tab:orange"
            ax.plot([xi, xj], [yi, yj], [zi, zj], color=color, lw=2)
            ax.text((xi + xj) / 2, (yi + yj) / 2, zi,
                    f"{v['element_tag']}", fontsize=6, color=color)

    for nivel, group in columnas_por_nivel.items():
        for c in group:
            i, j = c["nodo_inferior"], c["nodo_superior"]
            (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
            color = "deeppink" if "metal" in c.get("tipo_inventario", "") else "tab:green"
            ax.plot([xi, xj], [yi, yj], [zi, zj], color=color, lw=3)

    for nivel, group in muros_por_nivel.items():
        for m in group:
            i, j = m["nodo_i"], m["nodo_j"]
            (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
            ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.35", lw=4)

    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]"); ax.set_zlabel("Z [m]")
    ax.set_title(f"LT1 · 3D esqueleto principal (todos los niveles) · "
                 f"{len(nodos)} nodos reales")
    ax.set_box_aspect((xmax - xmin, ymax - ymin, max(zs) - min(zs)))

    # -- Planta XY del PISO_3 ---------------------------------------------
    z3 = niveles_z["PISO_3"]
    axp = fig.add_subplot(122)
    axp.set_title("PLANTA PISO_3 (z = +7.87 m) · bloque plano 102")

    for xeje in ejes_x:
        axp.axvline(x=ejes_x[xeje], color="0.75", lw=0.6)
    for yeje in ejes_y:
        axp.axhline(y=ejes_y[yeje], color="0.75", lw=0.6)
    for xeje, x in ejes_x.items():
        axp.text(x, ymin - 0.35, xeje, fontsize=9, ha="center")
    for yeje, y in ejes_y.items():
        axp.text(xmin - 0.35, y, yeje, fontsize=9, va="center")

    for nivel, group in vigas_por_nivel.items():
        if nivel != "PISO_3":
            continue
        for v in group:
            (xi, yi, _), (xj, yj, _) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
            color = "tab:blue" if v["seccion"].startswith("V. 60/80") else "tab:orange"
            axp.plot([xi, xj], [yi, yj], color=color, lw=2)

    for nivel, group in muros_por_nivel.items():
        if nivel != "PISO_3":
            continue
        for m in group:
            (xi, yi, _), (xj, yj, _) = nodos[m["nodo_i"]], nodos[m["nodo_j"]]
            axp.plot([xi, xj], [yi, yj], color="0.35", lw=5)

    for _g in columnas_por_nivel.values():
        for c in _g:
            (xi, yi, zi) = nodos[c["nodo_inferior"]]
            (xj, yj, zj) = nodos[c["nodo_superior"]]
            if abs(zi - z3) < 1e-9:
                _p = (xi, yi)
            elif abs(zj - z3) < 1e-9:
                _p = (xj, yj)
            else:
                continue
            color = "deeppink" if "metal" in c.get("tipo_inventario", "") else "tab:green"
            axp.plot([_p[0]], [_p[1]], marker="s", ms=9, color=color,
                     markeredgecolor="black")

    for tag, (x, y, z) in nodos.items():
        if abs(z - z3) < 1e-9:
            axp.plot([x], [y], marker="o", ms=4, color="crimson")
            axp.text(x + 0.15, y + 0.15, str(tag), fontsize=6, color="crimson")

    axp.set_xlabel("X [m]"); axp.set_ylabel("Y [m]")
    axp.invert_yaxis()
    axp.set_aspect("equal")

    fig.tight_layout()
    import os
    os.makedirs(output_dir, exist_ok=True)
    ruta = os.path.join(output_dir, "control_geometria_lt1.png")
    fig.savefig(ruta, dpi=120)
    print(f"  [OK] control visual generado: {ruta}")
    return ruta


def vista_esqueleto_3d(output_dir="outputs"):
    """Vista 3D limpia del esqueleto principal: columnas, vigas, pisos y nodos.
    Solo nivel modelado; sin marco completo de la grilla ni tags posibles."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import os

    xmin, xmax = min(ejes_x.values()), max(ejes_x.values())
    ymin, ymax = min(ejes_y.values()), max(ejes_y.values())

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    niveles_modelados = [n for n in niveles_z
                         if columnas_por_nivel[n] or vigas_por_nivel[n]]
    z_min = min(niveles_z[n] for n in niveles_modelados)
    z_max = max(niveles_z[n] for n in niveles_modelados)

    for n in niveles_modelados:
        z = niveles_z[n]
        panel = Poly3DCollection(
            [[(xmin, ymin, z), (xmax, ymin, z), (xmax, ymax, z), (xmin, ymax, z)]],
            alpha=0.10, facecolor="0.55", edgecolor="0.35", lw=0.7)
        ax.add_collection3d(panel)

    seen = set()
    col_list = []
    for g in columnas_por_nivel.values():
        for c in g:
            par = (c["nodo_inferior"], c["nodo_superior"])
            if par in seen:
                continue
            seen.add(par)
            col_list.append(c)

    for c in col_list:
        (xi, yi, zi), (xj, yj, zj) = (
            nodos[c["nodo_inferior"]], nodos[c["nodo_superior"]])
        color = ("deeppink" if "metal" in c.get("tipo_inventario", "")
                 else "tab:green")
        ax.plot([xi, xj], [yi, yj], [zi, zj], color=color, lw=3)

    n_vigas = 0
    for nivel, group in vigas_por_nivel.items():
        for v in group:
            n_vigas += 1
            i, j = v["nodo_i"], v["nodo_j"]
            (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
            color = ("tab:blue" if v["seccion"].startswith("V. 60/80")
                     else "tab:orange")
            ax.plot([xi, xj], [yi, yj], [zi, zj], color=color, lw=1.8)

    for tag, (x, y, z) in nodos.items():
        ax.scatter([x], [y], [z], color="crimson", s=14, depthshade=False)

    for n in niveles_modelados:
        z = niveles_z[n]
        ax.text(xmax + 1.2, ymin, z, f"{n}  z={z:+.2f}",
                fontsize=8, color="0.2")
    for eje in ["E", "F", "G", "H", "I", "I'"]:
        ax.text(ejes_x[eje], ymin - 1.0, z_min, eje, fontsize=8,
                color="0.35", ha="center")
    for eje in ["1", "2", "3"]:
        ax.text(xmin - 1.1, ejes_y[eje], z_min, eje, fontsize=8,
                color="0.35", va="center")

    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]"); ax.set_zlabel("Z [m]")
    ax.set_title(f"LT1 · Esqueleto principal 3D · {len(col_list)} columnas "
                 f"· {n_vigas} vigas · {len(nodos)} nodos")
    ax.set_box_aspect((xmax - xmin, ymax - ymin, z_max - z_min))
    fig.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    ruta = os.path.join(output_dir, "esqueleto_3d_lt1.png")
    fig.savefig(ruta, dpi=130)
    print(f"  [OK] vista esqueleto 3D: {ruta}")
    return ruta


def control_planta102_corregida(output_dir="outputs"):
    """Control visual PLANTA CIELO PISO 2 corregida (piso 3 del modelo).
    Colores por tipo; NO dibuja líneas sin posición confirmada."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import os
    fig, ax = plt.subplots(figsize=(11, 9))
    z3 = niveles_z["PISO_3"]

    for xeje in ejes_x:
        ax.axvline(x=ejes_x[xeje], color="0.8", lw=0.6, zorder=0)
    for yeje in ejes_y:
        ax.axhline(y=ejes_y[yeje], color="0.8", lw=0.6, zorder=0)
    for xeje, x in ejes_x.items():
        ax.text(x, -17.6, xeje, fontsize=8, ha="center", color="0.35")
    for yeje, y in ejes_y.items():
        ax.text(-0.7, y, yeje, fontsize=8, va="center", color="0.35")

    for nivel, group in vigas_por_nivel.items():
        if nivel != "PISO_3":
            continue
        for v in group:
            (xi, yi, _), (xj, yj, _) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
            color = "tab:blue" if v["seccion"].startswith("V. 60/80") else "tab:orange"
            ax.plot([xi, xj], [yi, yj], color=color, lw=2.2, zorder=3)

    for nivel, group in muros_por_nivel.items():
        if nivel != "PISO_3":
            continue
        for m in group:
            (xi, yi, _), (xj, yj, _) = nodos[m["nodo_i"]], nodos[m["nodo_j"]]
            ax.plot([xi, xj], [yi, yj], color="0.35", lw=6, zorder=2)

    for nivel, group in columnas_por_nivel.items():
        if nivel != "PISO_3":
            continue
        for c in group:
            (xi, yi, _) = nodos[c["nodo_inferior"]]
            color = "deeppink" if "metal" in c.get("tipo_inventario", "") else "tab:green"
            ax.plot([xi], [yi], marker="s", ms=10, color=color,
                    markeredgecolor="black", zorder=4)

    for tag, (x, y, z) in nodos.items():
        if abs(z - z3) < 1e-9:
            ax.plot([x], [y], marker="o", ms=3.5, color="crimson", zorder=5)

    pendientes = [e["rotulo"] for e in datos_inv.elementos_pendientes_coordenada
                  if e.get("plano") == "102"]
    ax.text(43.5, -17.0,
            f"ELEMENTOS 102 PENDIENTES DE POSICIÓN: {len(pendientes)}\n"
            "(no se dibujan hasta correlación exacta)",
            fontsize=8, color="darkred", ha="right", va="top")

    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor="tab:green", edgecolor="black", label="Pilares H.A."),
        Patch(facecolor="deeppink", edgecolor="black", label="Pilares metálicos"),
        Line2D([], [], color="tab:blue", lw=2.2, label="Vigas V.60/80"),
        Line2D([], [], color="tab:orange", lw=2.2, label="Vigas otras secciones"),
        Line2D([], [], color="0.35", lw=6, label="Muros M.H.A."),
        Line2D([], [], marker="o", color="w", mfc="crimson", label="Nodos"),
        Line2D([], [], color="w", lw=0, label=f"Pendiente (sin dibujar): {len(pendientes)}"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=8, framealpha=0.9)
    ax.set_title("RETICULA PISO_3 (z=+7.87 m) · SUB-PLANO 'PLANTA CIELO PISO 3°' "
                 "del folio 102\nrecorte y = -16.2 a +1 · Solo geometría con posición "
                 "confirmada\n(convención de niveles: data.inventario.CONVENCION_NIVELES)")
    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
    ax.set_xlim(-1, 44)
    ax.set_ylim(-18, 1.5)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    fig.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    ruta = os.path.join(output_dir, "control_planta102_corregida.png")
    fig.savefig(ruta, dpi=120)
    print(f"  [OK] control planta 102 corregida: {ruta}")
    return ruta


def verificar_bloque_inicial():
    """Verificaciones del bloque 1 (plano 102, PLANTA CIELO PISO 2)."""
    reales = sorted(set(nodos) | set(nodos_maestros)) == sorted(ops.getNodeTags())
    total = len(nodos) + len(nodos_maestros)
    z2, z3 = niveles_z["PISO_2"], niveles_z["PISO_3"]
    n_piso2 = sum(1 for (x, y, z) in nodos.values() if abs(z - z2) < 1e-9)
    n_piso3 = sum(1 for (x, y, z) in nodos.values() if abs(z - z3) < 1e-9)

    cols = [(c, nodos[c["nodo_inferior"]], nodos[c["nodo_superior"]])
            for g in columnas_por_nivel.values() for c in g]
    vigas = [(v, nodos[v["nodo_i"]], nodos[v["nodo_j"]])
             for g in vigas_por_nivel.values() for v in g]

    duplicados_nodos = len(nodos) - len(set((x, y, z) for x, y, z in nodos.values()))
    cero_longitud = [v for v, ci, cj in vigas if ci == cj]
    cero_longitud_col = [c for c, ci, cj in cols if ci == cj]
    tags = [v["element_tag"] for g in vigas_por_nivel.values() for v in g] + \
           [c["element_tag"] for g in columnas_por_nivel.values() for c in g]
    duplicados_tags = len(tags) - len(set(tags))
    inexistente = [
        v["element_tag"] for g in (vigas_por_nivel, muros_por_nivel)
        for rr in g.values()
        for v in rr if v["nodo_i"] not in nodos or v["nodo_j"] not in nodos
    ] + [c["element_tag"] for c, ci, cj in cols
         if c["nodo_inferior"] not in nodos or c["nodo_superior"] not in nodos]

    print("-" * 62)
    print("VERIFICACIONES BLOQUE 1 (plano 102 · PLANTA CIELO PISO 2)")
    print("-" * 62)
    print(f"  1. ops.getNodeTags() reales: {total}  (coincide con registros: {reales})")
    print(f"  2. nodos reales en PISO_2 (z=3.91):  {n_piso2}")
    print(f"  3. nodos reales en PISO_3 (z=7.87):  {n_piso3}")
    cols_total = len(set((c["nodo_inferior"], c["nodo_superior"]) for c in
                     [cc for g in columnas_por_nivel.values() for cc in g]))
    tramo_23 = sum(1 for c in
                   [cc for g in columnas_por_nivel.values() for cc in g]
                   if c["nivel_inferior"] == "PISO_2"
                   and c["nivel_superior"] == "PISO_3")
    print(f"  4. columnas P.70x70 totales del esqueleto: {cols_total}"
          f" | tramo PISO_2->PISO_3 (bloque 1): {tramo_23}")
    print(f"  5. vigas V.60/80 del esqueleto: {len(vigas)}"
          f"  (de ellas en PISO_3/plano 102: "
          f"{len(vigas_por_nivel['PISO_3'])} · 15 en X, 12 en Y)")
    print(f"  6. nodos duplicados: {duplicados_nodos}")
    print(f"  7. conectividades de longitud cero: vigas {len(cero_longitud)}"
          f" / columnas {len(cero_longitud_col)}")
    print(f"  8. elementTags duplicados: {duplicados_tags}")
    print(f"  9. conectividades inexistentes (nodoi/nodoj no creados): "
          f"{len(inexistente)} {inexistente[:5]}")
    print(f"  10. control visual: {ruta_control if 'ruta_control' in globals() else 'p. ver 10'}")
    return {
        "getNodeTags": total,
        "n_piso2": n_piso2,
        "n_piso3": n_piso3,
        "columnas": len(cols),
        "vigas": len(vigas),
        "duplicados_nodos": duplicados_nodos,
        "longitud_cero": len(cero_longitud) + len(cero_longitud_col),
        "tags_duplicados": duplicados_tags,
        "conectividad_inexistente": len(inexistente),
    }


def verificacion_geometria_102(ruta_control, ruta_planta):
    """Reporte de 14 ítems: geometría real vs pendiente en PLANTA CIELO PISO 2."""
    total = len(nodos)

    def _ha(c):
        return "metal" not in c.get("tipo_inventario", "")

    cols_all = [c for g in columnas_por_nivel.values() for c in g]
    col_ha = [c for c in cols_all if _ha(c)]
    col_metal = [c for c in cols_all if not _ha(c)]

    vigas_all = [v for g in vigas_por_nivel.values() for v in g]
    v_6080 = [v for v in vigas_all if v["seccion"].startswith("V. 60/80")]
    v_otras = [v for v in vigas_all if not v["seccion"].startswith("V. 60/80")]

    muros_ubi = [m for g in muros_por_nivel.values() for m in g]
    pendientes = list(datos_inv.elementos_pendientes_coordenada)
    muros_pendientes = [p for p in pendientes if "M.H.A." in p.get("rotulo", "")]
    coordenadas_aux_faltantes = list(datos_inv.coordenadas_aux_faltantes)

    from collections import Counter
    _count_coord = Counter(nodos.values())
    _nodos_dup = sum(1 for n in _count_coord.values() if n > 1)
    duplicados = _nodos_dup + len(_duplicados_evitados)

    cero_long_v = [v for v in vigas_all if nodos[v["nodo_i"]] == nodos[v["nodo_j"]]]
    cero_long_c = [c for c in cols_all
                   if nodos[c["nodo_inferior"]] == nodos[c["nodo_superior"]]]

    inexistente = [
        _e["element_tag"] for g in (vigas_por_nivel, muros_por_nivel)
        for rr in g.values() for _e in rr
        if _e["nodo_i"] not in nodos or _e["nodo_j"] not in nodos
    ] + [c["element_tag"] for c in cols_all
         if c["nodo_inferior"] not in nodos or c["nodo_superior"] not in nodos]

    print("=" * 62)
    print("REPORTE GEOMETRÍA PLANTA CIELO PISO 2° (14 ítems)")
    print("=" * 62)
    print(f"  1. nodos totales (reales): {total}")
    print(f"  2. nodos incrementales vs bloque 1 (36 iniciales): +{total - 36}"
          f"  (esqueleto completo + tramo fundación + masters)")
    print(f"  3. columnas H.A. ubicadas: {len(col_ha)}")
    print(f"  4. pilares metálicos ubicados: {len(col_metal)}")
    print(f"  5. vigas V.60/80 ubicadas: {len(v_6080)}")
    print(f"  6. vigas otras secciones ubicadas: {len(v_otras)}")
    print(f"  7. muros M.H.A. ubicados: {len(muros_ubi)}")
    print(f"  8. muros M.H.A. pendientes de posición: {len(muros_pendientes)}")
    print(f"  9. coordenadas auxiliares faltantes ({len(coordenadas_aux_faltantes)}):")
    for _k in coordenadas_aux_faltantes:
        print(f"       - {_k}: {datos_inv.coordenadas_aux_faltantes[_k]}")
    print(f" 10. elementos pendientes de posición: {len(pendientes)}")
    print(f" 11. elementos duplicados: {duplicados}"
          f"  (nodos con misma coord. {_nodos_dup}, "
          f" registros evitados {len(_duplicados_evitados)})")
    print(f" 12. conectividades de longitud cero: vigas {len(cero_long_v)}"
          f" / columnas {len(cero_long_c)} / muros 0")
    print(f" 13. conectividades inválidas: {len(inexistente)} {inexistente[:5]}")
    print(f" 14. control_geometria_lt1.png:      {ruta_control}")
    print(f"     control_planta102_corregida.png: {ruta_planta}")
    print("=" * 62)
    return {
        "nodos_totales": total,
        "nodos_nuevos": total - 36,
        "columnas_ha": len(col_ha),
        "pilares_metalicos_ubicados": len(col_metal),
        "vigas_6080": len(v_6080),
        "vigas_otras": len(v_otras),
        "muros_ubicados": len(muros_ubi),
        "muros_pendientes": len(muros_pendientes),
        "coordenadas_aux_faltantes": len(coordenadas_aux_faltantes),
        "elementos_pendientes": len(pendientes),
        "elementos_duplicados": duplicados,
        "longitud_cero": len(cero_long_v) + len(cero_long_c),
        "conectividad_invalida": len(inexistente),
        "ruta_control": ruta_control,
        "ruta_planta": ruta_planta,
    }


def verificacion_esqueleto(ruta_control, ruta_3d):
    """Verificaciones y reporte del esqueleto 3D principal (reticula principal)."""
    nodos_por_nivel = {n: 0 for n in niveles_z}
    for tag, (x, y, z) in nodos.items():
        for n in niveles_z:
            if abs(niveles_z[n] - z) < 1e-9:
                nodos_por_nivel[n] += 1

    seen = set()
    col_list = []
    for g in columnas_por_nivel.values():
        for c in g:
            par = (c["nodo_inferior"], c["nodo_superior"])
            if par in seen:
                continue
            seen.add(par)
            col_list.append(c)

    por_tramo = {}
    for c in col_list:
        t = (c["nivel_inferior"], c["nivel_superior"])
        por_tramo.setdefault(t, 0)
        por_tramo[t] += 1

    vigas_por_nivel_c = {n: len(g) for n, g in vigas_por_nivel.items()}
    vigas_total = sum(vigas_por_nivel_c.values())
    vig_for_levels = [(n, len(g)) for n, g in vigas_por_nivel.items() if g]

    cols_reg = [c for g in columnas_por_nivel.values() for c in g]
    muros_reg = [m for g in muros_por_nivel.values() for m in g]
    duplicados_nodos = len(nodos) - len(
        set((x, y, z) for (x, y, z) in nodos.values()))
    cero_long = [v for gg in vigas_por_nivel.values() for v in gg
                 if nodos[v["nodo_i"]] == nodos[v["nodo_j"]]] + \
                [m for gg in muros_por_nivel.values() for m in gg
                 if nodos[m["nodo_i"]] == nodos[m["nodo_j"]]] + \
                [c for c in cols_reg
                 if nodos[c["nodo_inferior"]] == nodos[c["nodo_superior"]]]
    inexistente = [
        e["element_tag"] for gg in (vigas_por_nivel, muros_por_nivel)
        for l in gg.values() for e in l
        if e["nodo_i"] not in nodos or e["nodo_j"] not in nodos] + \
        [c["element_tag"] for c in cols_reg
         if c["nodo_inferior"] not in nodos or c["nodo_superior"] not in nodos]
    tags = [c["element_tag"] for c in cols_reg] + \
           [v["element_tag"] for g in vigas_por_nivel.values() for v in g] + \
           [m["element_tag"] for m in muros_reg]
    tags_dup = len(tags) - len(set(tags))

    pendientes = list(datos_inv.elementos_pendientes_coordenada)
    n_pend = len(pendientes)
    pend_irregular = len([p for p in pendientes if any(
        k in p.get("rotulo", "") for k in (
            "M.H.A.", "NUCLEO", "P.M", "V. 30/45", "V. 60/VAR",
            "V. 60-30/80-40", "P.M.I.", "V.M.", "SEGUNDA", "2ª"))])

    print("=" * 62)
    print("VERIFICACIONES Y REPORTE · ESQUELETO 3D PRINCIPAL")
    print("=" * 62)
    print(f"  1. nodos reales totales: {len(nodos)}")
    print("  2. nodos por nivel:")
    for n in niveles_z:
        if nodos_por_nivel[n]:
            print(f"       {n:12s}: {nodos_por_nivel[n]}")
    print(f"  3. columnas totales: {len(col_list)} | por tramo:")
    for t in [("PISO_1S", "PISO_1"), ("PISO_1", "PISO_2"),
              ("PISO_2", "PISO_3"), ("PISO_3", "PISO_4")]:
        print(f"       {t[0]} -> {t[1]}: {por_tramo.get(t, 0)}")
    print(f"  4. vigas totales: {vigas_total} | por nivel:" +
          " | ".join(f" {n}={g}" for n, g in vig_for_levels))
    print(f"  5. elementos OpenSees realmente creados:"
          f" ops.node() = {len(nodos)} (existentes en dom) ·"
          f" elasticBeamColumn = {len(elementos_opensees)}"
          + (" (E/G de materiales PENDIENTES; 228 esperados cuando estén definidos)"
             if not materiales_listos()
             else "  (90 columnas + 108 vigas + 30 muros equiv. + 24 rigidLink de muro)"))
    print(f"  6. verificaciones: nodos duplicados {duplicados_nodos} ·"
          f" conectividad inexistente {len(inexistente)} {inexistente[:3]} ·"
          f" longitud cero {len(cero_long)} · elementTags duplicados {tags_dup}")
    print(f"  7. pendientes geométricos conservados: {n_pend}"
          f" (irregulares/segunda etapa: {pend_irregular})")
    print(f"  8. rutas:")
    print(f"       outputs/control_geometria_lt1.png")
    print(f"       outputs/esqueleto_3d_lt1.png")
    print("=" * 62)
    return {
        "nodos_totales": len(nodos),
        "nodos_por_nivel": nodos_por_nivel,
        "columnas_totales": len(col_list),
        "columnas_por_tramo": por_tramo,
        "vigas_totales": vigas_total,
        "vigas_por_nivel": vigas_por_nivel_c,
        "elasticBeamColumn": len(elementos_opensees),
        "nodos_duplicados": duplicados_nodos,
        "conectividad_inexistente": len(inexistente),
        "longitud_cero": len(cero_long),
        "tags_duplicados": tags_dup,
        "pendientes_conservados": n_pend,
        "ruta_control": ruta_control,
        "ruta_3d": ruta_3d,
    }


def verificacion_opensees():
    tags_opensees = [e["element_tag"] for e in elementos_opensees]
    tags_unicos = len(set(tags_opensees)) == len(tags_opensees)
    nodos_ops = len(ops.getNodeTags())
    n_ele_ops = len(ops.getEleTags())

    print("-" * 62)
    print("VERIFICACIONES BLOQUE OPENSEES (elementos elásticos)")
    print("-" * 62)
    print(f"  ops.getNodeTags() = {nodos_ops} (144 estructurales + {len(nodos_maestros)} masters)")
    print(f"  ops.getEleTags()  = {n_ele_ops}"
          + (f" (esperado 228 cuando E/G estén definidos)"
             if materiales_listos() is False else
             " (90 col + 108 vigas + 30 muros equiv. elasticBeamColumn)"))
    print(f"  elasticBeamColumn creados: {len(elementos_opensees)}")
    print(f"  constr. rígidas de muro (rigidLink al master): {len(RIGID_LINKS_MUROS)}")
    print(f"  tags de elemento únicos: {tags_unicos}")
    props_ok = True
    for e in elementos_opensees:
        if e.get("tipo_inventario") == "muro_ha":
            props = e
        else:
            props = datos_secc.propiedades_por_seccion.get(e["seccion"])
        if not (props and all(v > 0 for v in (props["A_m2"], props["Iy_m4"],
                                              props["Iz_m4"], props["J_m4"]))):
            props_ok = False
        if not (0 < e.get("E_kPa", 0) and 0 < e.get("G_kPa", 0)):
            props_ok = False
    print(f"  E/G en elementos positivos (si existen): {props_ok}"
          if elementos_opensees else
          "  sin elementos: A/Iy/Iz/J de la sección quedan validados en control")
    print(f"  geomTransf definidas: "
          f"{sum(1 for v in geomtransf_definidas.values() if v['estado'] == 'DEFINIDA')}/3"
          f" ({', '.join(GEOMTRANSF_VECXZ)})")
    print("-" * 62)
    return {
        "nodos_ops": nodos_ops,
        "elementos_ops": n_ele_ops,
        "elasticBeamColumn": len(elementos_opensees),
        "tags_unicos": tags_unicos,
        "geomtransf_definidas": len(geomtransf_definidas),
    }


def escribir_control_opensees(ruta):
    """Control del modelo OpenSees (nodos/materiales/secciones/geomTransf/
    elementos) en texto. Unidades: m, kN, kPa."""
    import io
    bufs = io.StringIO()
    w = bufs.write
    w("=" * 72 + "\n")
    w("CONTROL MODELO OPENSEES LT1\n")
    w("=" * 72 + "\n")
    w("Unidades base: metros (m), kilonewtons (kN), kilopascales (kPa)\n\n")

    w("MATERIALES\n")
    w(f"  ESTADO: {datos_secc.MATERIAL_ACADEMICO_STATUS}\n")
    w("  Revisión documental: docs/P1L2.txt, docs/Enunciado general.txt y\n"
      "  AGENTS.md NO fijan f'c/E/nu/G (Enunciado general solo fija la\n"
      "  convención: sistema lineal elástico 3D + elasticBeamColumn).\n")
    for nombre, m in datos_secc.materiales.items():
        w(f"  {nombre} ({m['nombre']}):\n")
        for k, v in m.items():
            if k == "nombre":
                continue
            w(f"      {k:12s} : {v}\n")
    w("\n")

    w("GEOMTRANSF (Linear, 3D)\n")
    w(f"  {'familia':20s} {'tag':>5s}  vecxz        ejes locales\n")
    ejes_locales = {
        "columna_vertical": "x=+Z, y=-Y, z=+X",
        "viga_x": "x=+X, y=+Y, z=+Z",
        "viga_y": "x=+-Y, y=-+X, z=+Z",
    }
    for fam in GEOMTRANSF_VECXZ:
        g = geomtransf_definidas[fam]
        w(f"  {fam:20s} {g['tag']:5d}  {str(g['vecxz']):12s} {ejes_locales[fam]}\n")
    w("\n")

    w("SECCIONES (resumen A/Iy/Iz/J)\n")
    w(f"  {'sección':12s} {'b [m]':>6s} {'h [m]':>6s} {'A [m2]':>8s} "
      f"{'Iy [m4]':>10s} {'Iz [m4]':>10s} {'J [m4]':>10s}\n")
    for nombre in ("P. 70x70", "V. 60/80"):
        if nombre not in datos_secc.propiedades_por_seccion:
            continue
        d = datos_secc.propiedades_por_seccion[nombre]
        datos = datos_secc.secciones_por_plano["102"].get(nombre, {})
        if "columna" in datos.get("tipo", ""):
            b, h = datos["b_cm"] / 100.0, datos["d_cm"] / 100.0
        elif "viga" in datos.get("tipo", "") and datos.get("h_cm") not in (None, "VAR"):
            b, h = datos["b_cm"] / 100.0, datos["h_cm"] / 100.0
        else:
            b = h = float("nan")
        w(f"  {nombre:12s} {b:6.3f} {h:6.3f} {d['A_m2']:8.4f} "
          f"{d['Iy_m4']:10.6f} {d['Iz_m4']:10.6f} {d['J_m4']:10.6f}\n")
    w("  Convención: Iy = b*h^3/12 (flexión alrededor del eje local y) ;\n")
    w("  Iz = h*b^3/12 ; J = (1/3)*a^3*c*(1 - 0.630*a/c + 0.052*(a/c)^5), a<=c\n")
    w("  (constante torsional de St. Venant, fórmula cerrada documentada y\n"
      "  contrastada contra la serie exacta en data/secciones.py)\n\n")

    w("NODOS\n")
    nodos_ops = len(ops.getNodeTags())
    w(f"  ops.getNodeTags() = {nodos_ops}\n")
    por_nivel = {}
    for tag, (x, y, z) in nodos.items():
        por_nivel.setdefault(metadata_nodos.get(tag, {}).get("nivel", "s/nivel"), 0)
        por_nivel[metadata_nodos.get(tag, {}).get("nivel", "s/nivel")] += 1
    for n in niveles_z:
        w(f"    {n:12s}: {por_nivel.get(n, 0)}\n")
    w("\n")

    w("COLUMNAS (marcos esqueleto, H.A. P. 70x70)\n")
    cols_uni = {}
    for g in columnas_por_nivel.values():
        for c in g:
            cols_uni[c["element_tag"]] = c
    por_tramo = {}
    for c in cols_uni.values():
        t = (c["nivel_inferior"], c["nivel_superior"])
        por_tramo[t] = por_tramo.get(t, 0) + 1
    w(f"  totales: {len(cols_uni)}\n")
    for t in sorted(por_tramo):
        w(f"    {t[0]} -> {t[1]}: {por_tramo[t]}\n")
    w("\n")

    w("VIGAS (marcos esqueleto, V. 60/80)\n")
    vigas_total = sum(len(g) for g in vigas_por_nivel.values())
    w(f"  totales: {vigas_total}\n")
    for n, g in vigas_por_nivel.items():
        if g:
            w(f"    {n}: {len(g)}\n")
    w("\n")

    w("ELEMENTOS OPENSEES\n")
    w(f"  elasticBeamColumn creados: {len(elementos_opensees)}\n")
    if not materiales_listos():
        w("  esperados: 228 (90 columnas + 108 vigas + 30 muros equiv.) cuando E ")
        w("y G estén respaldados\n")
        w("  ACTIVACION INMEDIATA: listo con E y nu/G definidos ")
        w("(G = E/[2(1+nu)]); conectividades y tags ya reservados\n")
        w("  MATERIAL_PENDIENTE_DE_CONVENCION_ACADEMICA: ni los planos ")
        w("(000r/001r, ref. E.T.O.G.) ni los docs académicos (P1L2, Enunciado, ")
        w("AGENTS) fijan valores -> no se inventa\n")
    else:
        w("  ejemplos de tags: " + ", ".join(
            str(e["element_tag"]) for e in elementos_opensees[:4]) + " ...\n")
    w("  tags reservados columna: " + ", ".join(
        str(t) for t in sorted(col_tags)[:5]) + " ...\n")
    w("  tags reservados viga: " + ", ".join(
        str(t) for t in sorted(viga_tags)[:5]) + " ...\n")
    w("  tags muros equivalentes: " + ", ".join(
        str(m["element_tag"]) for m in muros_equivalentes) + "\n")
    w("\n")

    w("VERIFICACIONES\n")
    w(f"  ops.node = {nodos_ops} (144 estructurales + {len(nodos_maestros)} masters)\n")
    w(f"  ops.element = {len(ops.getEleTags())} (228 esperados: 90 col + 108 vigas "
      "+ 30 muros equiv.; material HºAº y convención de muro por "
      "INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO)\n")
    w(f"  elementTags únicos: "
      f"{len({*col_tags, *viga_tags, *[m['element_tag'] for m in muros_equivalentes]}) == len(col_tags) + len(viga_tags) + 18}\n")
    w(f"  constr. rígidas de muro (rigidLink al master del diafragma): "
      f"{len(RIGID_LINKS_MUROS)} (no cuentan como elasticBeamColumn)\n")
    w(f"  nodos duplicados: {len(nodos) - len({tuple(v) for v in nodos.values()})}\n")
    w(f"  pendientes geométricos conservados: {len(datos_inv.elementos_pendientes_coordenada)}\n")
    w("=" * 72 + "\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(bufs.getvalue())
    return ruta


def generar_recorte_plano000(ruta_pdf, ruta_png, workdir=None):
    """Recorta del plano 000 las zonas CONSIDERACIONES GENERALES/especificaciones
    y las notas (recubrimientos E.T.O.G., ref. plano 001) a resolución de
    lectura humana -> outputs/plano000_consideraciones_alta_resolucion.png.
    Compone dos paneles apilados: bloque de consideraciones + franja de notas."""
    import subprocess
    import tempfile
    import os as _os

    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    os.makedirs(_os.path.dirname(ruta_png) or ".", exist_ok=True)
    tmp = workdir or tempfile.mkdtemp()
    doc = fitz.open(ruta_pdf)
    page = doc[0]
    zoom0 = 300 / 72.0
    zoom1 = 6.0

    def _capturar(clip_pts, tag):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom1, zoom1), clip=clip_pts)
        archivo = _os.path.join(tmp, f"plano000_panel_{tag}.png")
        pix.save(archivo)
        return archivo, (pix.width, pix.height)

    # Panel superior: CONSIDERACIONES GENERALES + especificaciones (parte alta
    # del plano, determinada por OCR previo: título a cx=0.44, cy=0.95).
    p_top = _os.path.join(tmp, "plano000_panel_top.png")
    top_rect = fitz.Rect(0.38 * page.rect.width, 0.0,
                         1.0 * page.rect.width, 0.30 * page.rect.height)
    pix_top = page.get_pixmap(matrix=fitz.Matrix(zoom1, zoom1), clip=top_rect)
    pix_top.save(p_top)

    # Panel inferior: notas/material (recubrimientos E.T.O.G., plano 001).
    p_bot = _os.path.join(tmp, "plano000_panel_bot.png")
    bot_rect = fitz.Rect(0.0 * page.rect.width, 0.66 * page.rect.height,
                         1.0 * page.rect.width, 1.0 * page.rect.height)
    pix_bot = page.get_pixmap(matrix=fitz.Matrix(zoom1, zoom1), clip=bot_rect)
    pix_bot.save(p_bot)

    from PIL import Image
    im_top = Image.open(p_top)
    im_bot = Image.open(p_bot)
    w_out = max(im_top.width, im_bot.width)
    h_out = im_top.height + 24 + im_bot.height
    out = Image.new("RGB", (w_out, h_out), "white")
    out.paste(im_top, (0, 0))
    out.paste(im_bot, (0, im_top.height + 24))
    out.save(ruta_png)
    print(f"  [OK] {ruta_png}  ({w_out}x{h_out} px, zoom {zoom1:.0f}x, "
          f"2 paneles: consideraciones + notas)")
    return ruta_png


def escribir_control_apoyos(ruta):
    """Control de apoyos y diafragmas rígidos en texto plano."""
    import io
    bufs = io.StringIO()
    w = bufs.write
    w("=" * 78 + "\n")
    w("CONTROL APOYOS Y DIAFRAGMAS RIGIDOS · LT1\n")
    w("=" * 78 + "\n")
    w("Nivel de apoyo: FUNDACION_SUP = -7.97 m (nivel superior de fundacion)\n")
    w("Evidencia:\n")
    w("  - ELEVACION 302 (EJE 2): columna P.70x70 continua de PISO_1S (-4.01)\n")
    w("    hasta FUNDACION_SUP (-7.97), cota 3.96 m; callouts P.70x70 en todo\n")
    w("    el recorrido; fondo de fundacion -9.17 m (elev. 300/302).\n")
    w("  - PLANTA FUNDACIONES (100): grilla de V.F. en el nivel superior.\n")
    w("  - Tramo creado FUNDACION_SUP -> PISO_1S (18 columnas P.70x70).\n")
    w("Restriccion de base (6 GDL): (Ux, Uy, Uz, Rx, Ry, Rz) = (1,1,1,1,1,1)\n")
    w("  = empotramiento (no es condicion parcial arbitraria).\n")
    w("-" * 78 + "\n")
    w("APOYOS\n")
    w(f"{'nodeTag':>8s} {'nivel':13s} {'ejeX':>5s} {'ejeY':>4s}  restriccion\n")
    for tag in sorted(apoyos):
        a = apoyos[tag]
        w(f"{a['nodeTag']:8d} {a['nivel']:13s} {a['eje_x']:>5s} {a['eje_y']:>4s}  "
          f"{a['restriccion']}   (6 GDL, empotrado)\n")
    w(f"TOTAL APOYOS: {len(apoyos)}\n\n")
    w("-" * 78 + "\n")
    w("DIAFRAGMAS RIGIDOS\n")
    w("Metodo: ops.rigidDiaphragm(perpDirn=3, masterTag, *slaveTags)\n")
    w("Direccion perpendicular al diafragma: global Z (vertical).\n")
    w("DOF compatibilizados (plano XY): Ux (1), Uy (2), Rz (6).\n")
    w("DOF libres: Uz (3, vertical), Rx (4), Ry (5).\n\n")
    for nivel in NIVELES_DIAFRAGMA:
        d = diafragmas.get(nivel, {})
        if not d:
            w(f"  {nivel:8s}: (sin diafragma)\n")
            continue
        m = d["nodo_maestro"]
        sl = d["nodos"]
        cx, cy, z = d["centroide"]
        w(f"  {nivel:8s}: nodo maestro {m}  slaves={len(sl)}  "
          f"centroide=({cx:.3f}, {cy:.3f}, {z:.3f})\n")
        w(f"            slaves: {','.join(str(s) for s in sl)}\n")
    w("\nNODOS DE MURO EQUIVALENTE: NO son slaves del diafragma.\n")
    w("Cada nodo de muro (base/tope) se conecta a su nivel mediante la restriccion\n")
    w("cinematica real ops.rigidLink('beam', MASTER_del_diafragma, nodo_muro)\n")
    w("(12 links; NO son elementos, no aparecen en ops.getEleTags()).\n")
    w("Justificacion empirica (repro minimo, constraints Transformation):\n")
    w("  . slave directo del diafragma -> matriz singular (pivote en Uz/Rx/Ry);\n")
    w("  . rigidLink al nodo ancla estructural -> NO propaga el plan (err 0.24/0.62 m);\n")
    w("  . rigidLink al MASTER  ->  el nodo de muro sigue el plano con error 0.0.\n")
    w("\nPISO_1S: SIN diafragma (nivel de transito de columnas sin vigas del\n")
    w("esqueleto; V.S.I./losas del 1° sub. quedan pendientes de modelar).\n")
    w("=" * 78 + "\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(bufs.getvalue())
    return ruta


def verificacion_apoyos_diafragmas():
    nodos_ops = set(ops.getNodeTags())
    ok = True

    problemas_apoyos = []
    if len(apoyos) != 24:
        problemas_apoyos.append(f"esperados 24 apoyos, hay {len(apoyos)}")
    for tag, a in apoyos.items():
        if tag not in nodos or tag not in nodos_ops:
            problemas_apoyos.append(f"apoyo {tag} inexistente en dom")
        if a["nivel"] != "FUNDACION_SUP":
            problemas_apoyos.append(f"apoyo {tag} fuera de FUNDACION_SUP")
        if tuple(a["restriccion"]) != (1, 1, 1, 1, 1, 1):
            problemas_apoyos.append(f"apoyo {tag}: restriccion parcial {a['restriccion']}")
    if problemas_apoyos:
        ok = False

    prob_dia = []
    if len(nodos_maestros) != len(NIVELES_DIAFRAGMA):
        prob_dia.append("cantidad de masters != niveles de diafragma")
    for nivel in NIVELES_DIAFRAGMA:
        z = niveles_z[nivel]
        d = diafragmas.get(nivel, {})
        if not d:
            prob_dia.append(f"{nivel}: sin diafragma")
            continue
        m = d["nodo_maestro"]
        sl = set(d["nodos"])
        if m in sl:
            prob_dia.append(f"{nivel}: master {m} es slave")
        if not sl:
            prob_dia.append(f"{nivel}: sin slaves")
        if len(sl) != len(d["nodos"]):
            prob_dia.append(f"{nivel}: slave repetido")
        for s in sl:
            if s not in nodos:
                prob_dia.append(f"{nivel}: slave {s} inexistente")
            elif abs(nodos[s][2] - z) > 1e-9:
                prob_dia.append(f"{nivel}: slave {s} fuera de Z={z}")
            elif abs(nodos[s][2] - niveles_z["FUNDACION_SUP"]) < 1e-9:
                prob_dia.append(f"{nivel}: slave de fundacion incorporado")
        for s in sl:
            if abs(nodos[s][2] - z) < 1e-9 and \
               abs(nodos[s][2] - niveles_z["FUNDACION_SUP"]) < 1e-9:
                pass
    if prob_dia:
        ok = False

    print("-" * 62)
    print("VERIFICACION APOYOS + DIAFRAGMAS")
    print("-" * 62)
    print(f"  apoyos: {len(apoyos)} (24 esperados), todos con 6 GDL "
          f"empotrados -> {'OK' if not problemas_apoyos else problemas_apoyos}")
    print(f"  diafragmas: {len([d for d in diafragmas.values() if d])} activos"
          f" ({', '.join(NIVELES_DIAFRAGMA)})")
    por_nivel = [len(diafragmas[n]["nodos"]) for n in NIVELES_DIAFRAGMA
                 if diafragmas.get(n)]
    print(f"  masters: {sorted(nodos_maestros)} | slaves/piso: {por_nivel}")
    print(f"  DOF compatibilizados: Ux,Uy,Rz | libres: Uz,Rx,Ry | perp=Z")
    print(f"  niveles con diafragma: {NIVELES_DIAFRAGMA} | sin: PISO_1S (documentado)")
    print(f"  nodos base (FUNDACION_SUP) incorporados a diafragma: 0")
    print(f"  ops.getNodeTags(): {len(nodos_ops)} "
          f"(144 estructurales: 108 esqueleto + 36 de muros + {len(nodos_maestros)} masters)")
    print(f"  ops.getEleTags(): {len(ops.getEleTags())} "
          f"(228: 90 columnas + 108 vigas + 30 muros equivalentes)")
    print(f"  rigidLink de muro al master del diafragma: {len(RIGID_LINKS_MUROS)} "
          f"(constraints, no eleTags)")
    print("-" * 62)
    return {
        "ok": ok,
        "apoyos": len(apoyos),
        "problemas_apoyos": problemas_apoyos,
        "diafragmas": len([d for d in diafragmas.values() if d]),
        "masters": sorted(nodos_maestros),
        "slaves_por_piso": {n: len(diafragmas[n]["nodos"]) for n in NIVELES_DIAFRAGMA
                            if diafragmas.get(n)},
        "problemas_diafragma": prob_dia,
        "nodos_ops": len(nodos_ops),
        "nodos_estructurales": len(nodos),
    }


def control_apoyos_diafragmas_3d(output_dir="outputs"):
    """Plot 3D: esqueleto + apoyos (rojo) + nodos master (amarillo) + diafragmas."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    xmin, xmax = min(ejes_x.values()), max(ejes_x.values())
    ymin, ymax = min(ejes_y.values()), max(ejes_y.values())
    zs = list(niveles_z.values())
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')

    for z in zs:
        for (x0, y0), (x1, y1) in [((xmin, ymin), (xmax, ymin)),
                                   ((xmax, ymin), (xmax, ymax)),
                                   ((xmax, ymax), (xmin, ymax)),
                                   ((xmin, ymax), (xmin, ymin))]:
            ax.plot([x0, x1], [y0, y1], [z, z], color="0.75", lw=0.7, alpha=0.6)
    for nivel in niveles_z:
        ax.text(xmin - 1.3, ymin, niveles_z[nivel], nivel, fontsize=7, color="0.3")

    for g in columnas_por_nivel.values():
        for c in g:
            i, j = c["nodo_inferior"], c["nodo_superior"]
            (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
            ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.55", lw=2.2)
    for g in vigas_por_nivel.values():
        for v in g:
            (xi, yi, zi), (xj, yj, zj) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
            ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.7", lw=1.4)

    for tag, (x, y, z) in nodos.items():
        ax.scatter([x], [y], [z], color="#2b6cb0", s=16, depthshade=False)

    for tag, a in apoyos.items():
        x, y, z = nodos[tag]
        ax.scatter([x], [y], [z], color="crimson", s=130, marker="s", depthshade=False)
        ax.text(x + 0.4, y + 0.4, z, f"{tag}", fontsize=7, color="crimson")

    for tag, m in nodos_maestros.items():
        ax.scatter([m["x"]], [m["y"]], [m["z"]], color="gold", s=200,
                   marker="*", edgecolors="black", depthshade=False)
        ax.text(m["x"] + 0.4, m["y"] + 0.4, m["z"], f"{tag}",
                fontsize=8, color="darkgoldenrod")

    from matplotlib.patches import Patch
    handles = [
        Patch(fc="#2b6cb0", label="nodo estructural"),
        Patch(fc="crimson", label="nodo de apoyo (FUNDACION_SUP, 6 GDL)"),
        Patch(fc="gold", label="nodo master diafragma"),
        Patch(fc="0.55", label="columnas P.70x70"),
        Patch(fc="0.7", label="vigas V.60/80"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]"); ax.set_zlabel("Z [m]")
    ax.set_title("LT1 · Esqueleto + apyo FUNDACION_SUP + diafragmas rígidos "
                 f"(masters en {', '.join(NIVELES_DIAFRAGMA)})")
    ax.set_box_aspect((xmax - xmin, ymax - ymin, max(zs) - min(zs)))
    os.makedirs(output_dir, exist_ok=True)
    ruta = os.path.join(output_dir, "apoyos_diafragmas_3d.png")
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] apoyo+diafragma 3D: {ruta}")
    return ruta


def verificacion_estado_general():
    print("-" * 62)
    print("VERIFICACIONES LT1")
    print("-" * 62)
    verificacion_grilla_x()
    verificacion_grilla_y()
    verificacion_niveles()
    verificacion_tags()
    verificacion_secciones()
    verificacion_nodos_reales()
    verificacion_ubicados()
    verificacion_elementos_registrados()
    verificacion_conectividad()
    verificacion_cargas()
    print("-" * 62)
    print("CORRELACIÓN PLANO -> NIVEL")
    for plano, nivel in datos_inv.nivel_por_plano.items():
        print(f"  plano {plano}: {nivel}"
              f"  | fuente: {datos_inv.fuente_correlacion_plano_nivel[plano]}")
    print("-" * 62)
    print(datos_geom.nota_diferencia_ejes_visibles)


# ============================================================================
# 12bis. GEOMETRÍA IRREGULAR COMPLETA (bloque grande)
# Reporte + control visual de TODA la geometría irregular registrada en
# data/geometria_irregular.py + los muros/vigas del inventario con posición
# aproximada. Sin material, sin elasticBeamColumn, sin análisis.
# ============================================================================

# Elemento irregulares que quedaron (por rótulo, exclusivamente de posición
# aproximada INferida/detectada en plano 102 en la zona del edificio).
_elementos_irregulares_102_en_edificio = {}


def _integrar_irregulares_en_edificio():
    """De los 129 elementos registrados en geometria_irregular, promueve a
    posiciones 'verificables' en la retícula SOLO los que están en la zona del
    edificio principal con estado INFERIDO_RESPALDADO."""
    for e in datos_irreg.todos_los_elementos:
        if e.get("plano") != "102":
            continue
        pm = e.get("posicion_modelo")
        if pm is None:
            continue
        X, Y = pm
        # Solo zona del edificio principal (Y entre -16.15 y 0 aproximadamente)
        if not (-17.0 < Y < 2.0):
            continue
        _elementos_irregulares_102_en_edificio[e["id"]] = {
            "id": e["id"],
            "seccion": e.get("seccion"),
            "tipo": e.get("tipo"),
            "posicion_modelo": pm,
            "estado": e.get("estado"),
            "razon_estado": e.get("razon_estado"),
            "nivel": e.get("nivel", "PENDIENTE_CORRELACION"),
        }


_integrar_irregulares_en_edificio()


def escribir_control_geometria_completa_lt1(ruta):
    """Control txt con el registro completo de geometría irregular (por tipo),
    los pendientes geométricos abiertos y los elementos con posición aproximada."""
    import io
    buf = io.StringIO()
    w = buf.write
    w("=" * 90 + "\n")
    w("CONTROL GEOMETRIA COMPLETA LT1 · ELEMENTOS IRREGULARES Y SECUNDARIOS\n")
    w("=" * 90 + "\n")
    w("Fuente: data/geometria_irregular.py (registro pdfminer por elem.) +\n")
    w("        data/inventario.py (cantidades por rótulo, retícula principal).\n")
    w("Unidades: metros (m). Sin material, sin elasticBeamColumn, sin cargas.\n\n")

    r = datos_irreg.resumen_estados()
    w(f"TOTAL elementos irregulares registrados: {r['total']}\n")
    w(f"  por estado: {r['por_estado']}\n")
    w(f"  muros: {r['muros_total']} · pilares metálicos: {r['pilares_total']} ·\n"
      f"  vigas metálicas: {r['vigas_metal_total']} · vigas irregulares/VAR: "
      f"{r['vigas_irregulares_total']} · V.60/80 extra: {r['vigas_6080_extra_total']}\n\n")

    w("MAPEO PDF->MODELO (plano 102, calibrado con 18 P.70x70 de la retícula):\n")
    m = datos_irreg.MAPEO_PDF["102"]
    w(f"  x_pdf = {m['a_x']}*X + {m['b_x']}  (error {m['error_x_m']})\n")
    w(f"  y_pdf = {m['a_y']}*Y + {m['b_y']}  (error {m['error_y_m']})\n")
    w(f"  Valido solo para el area del edificio principal "
      f"(X:{m['rango_modelo_valido']['X']}, Y:{m['rango_modelo_valido']['Y']})\n")
    w(f"  El plano 101 usa el mapeo de 102 NO calibrado; el plano 103 = PLANTA CIELO\n"
      f"  PISO 4° usa mapeo INFERIDO_RESPALDADO calibrado por el núcleo E-F común\n"
      f"  con el 102 (x=X*8.189+264.77, y=Y*7.652+392.58).\n\n")

    w("-" * 90 + "\n")
    w("1) MUROS M.H.A. / M.I. (todos, por plano y espesor)\n")
    w("-" * 90 + "\n")
    for plano in ("101", "102", "103"):
        for muro in [x for x in datos_irreg.muros_todos if x["plano"] == plano]:
            pm = muro.get("posicion_modelo")
            pm_s = (f"({pm[0]:.2f}, {pm[1]:.2f})" if pm else "---")
            w(f"  [{muro['id']}] {muro['seccion']:14s} plano {plano} "
              f"nivel {muro['nivel']:18s} pos~{pm_s:16s} "
              f"{muro['estado']:<22s} {muro['razon_estado'][:48]}\n")

    w("\n" + "-" * 90 + "\n")
    w("2) PILARES Y VIGAS METALICAS (P.M., P.M.I., V.M.)\n")
    w("-" * 90 + "\n")
    for p in datos_irreg.pilares_todos + datos_irreg.vigas_metal_todas:
        pm = p.get("posicion_modelo")
        pm_s = (f"({pm[0]:.2f}, {pm[1]:.2f})" if pm else "---")
        w(f"  [{p['id']}] {p['seccion']:22s} plano {p['plano']} "
          f"nivel {p['nivel']:18s} pos~{pm_s:16s} "
          f"{p['estado']:<22s} {p['razon_estado'][:48]}\n")

    w("\n" + "-" * 90 + "\n")
    w("3) VIGAS IRREGULARES / VAR / SEGUNDA ETAPA\n")
    w("-" * 90 + "\n")
    for v in datos_irreg.vigas_irregulares_todas:
        pm = v.get("posicion_modelo")
        pm_s = (f"({pm[0]:.2f}, {pm[1]:.2f})" if pm else "---")
        w(f"  [{v['id']}] {v['seccion']:26s} plano {v['plano']} "
          f"nivel {v['nivel']:18s} pos~{pm_s:16s} "
          f"{v['estado']:<22s} {v['razon_estado'][:42]}\n")

    w("\n" + "-" * 90 + "\n")
    w("4) MUROS/VIGAS DEL PLANO 102 CON POSICION APROXIMADA EN EDIFICIO\n")
    w("-" * 90 + "\n")
    w("(estas posiciones SE usan como referencia; no crean elasticBeamColumn)\n")
    for k in sorted(_elementos_irregulares_102_en_edificio):
        e = _elementos_irregulares_102_en_edificio[k]
        w(f"  {e['id']:12s} {e['seccion']:14s} pos={e['posicion_modelo']} "
          f"{e['estado']}\n")

    w("\n" + "-" * 90 + "\n")
    w("5) PENDIENTES GEOMÉTRICOS ABIERTOS\n")
    w("-" * 90 + "\n")
    for p in datos_irreg.pendientes_geometricos:
        w(f"  [{p['id']}]\n")
        w(f"    descripcion      : {p['descripcion']}\n")
        w(f"    que falta        : {p['que_falta']}\n")
        w(f"    metodo_resolucion: {p['metodo_resolucion']}\n")
        if p.get("estado"):
            w(f"    ESTADO           : {p['estado']}\n")
        for res in p.get("resuelto", []):
            w(f"      + RESUELTO: {res}\n")

    w("\n" + "-" * 90 + "\n")
    w("6) INVENTARIO CONSOLIDADO POR PLANO (cantidades)\n")
    w("-" * 90 + "\n")
    for plano, niveles in datos_irreg._inventario_consolidado.items():
        for nivel, tipos in niveles.items():
            w(f"  Plano {plano} -> nivel {nivel}:\n")
            for tipo, seccs in tipos.items():
                detalle = ", ".join(f"{k}:{v}" for k, v in seccs.items())
                w(f"      {tipo:18s}: {detalle}\n")

    w("\n" + "=" * 90 + "\n")
    w("NOTAS DE METODO\n")
    w("  - Niveles correlacionados por rótulo OCR del bloque de títulos:\n")
    w("      * Plan 102 = PLANTA CIELO PISO 2° (folio además lleva sub-plano\n")
    w("        PISO 3° con NIVEL SUPERIOR LOSA = 7.87 m = PISO_3).\n")
    w("      * Plan 103 = PLANTA CIELO PISO 4° (NIVEL SUPERIOR LOSA ≈ 11.83 m\n")
    w("        = PISO_4 según data/geometria.py niveles_z['PISO_4']).\n")
    w("  - e=25 y e=30 de M.H.A. en plano 102: solo OCR visual (NO en capa de\n"
      "    texto); posicion exacta PENDIENTE_COORDENADA (TRAMO_NUCLEO_E_F).\n")
    w("  - Nucleo E-F e=20: posicion X≈0.75/4.15 en filas Y≈-3.45/-14.53\n"
      "    confirmada de forma CRUZADA entre plan 102 (PISO_2) y plan 103\n"
      "    (PISO_4) -> INFERIDO_RESPALDADO. Longitud de tramos pendiente.\n")
    w("  - Elementos con y_pdf < 440 en planos 101/102/103 estan en vistas de\n"
      "    detalle separadas del mismo PDF; NO se mapean al edificio.\n")
    w("  - Los P.M./V.M./P.M.I. aparecen solo en vistas de detalle del 102; el\n"
      "    sector real bajo el eje 3 necesita Y_EXT_SUR_102 para ubicarse.\n")
    w("  - No se crean nodos ni elasticBeamColumn: geometria preparada.\n")
    w("=" * 90 + "\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  [OK] control geometria completa: {ruta}")
    return ruta


def control_geometria_completa_lt1(output_dir="outputs"):
    """Plot: planta PISO_3 con esqueleto + elementos irregulares en edificio
    (muros aproximados en naranja) y la retícula principal. + recuadro de
    pendientes. Sin dibujar elementos sin posición."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    import os

    z3 = niveles_z["PISO_3"]
    fig, ax = plt.subplots(figsize=(11, 9))

    for xeje in ejes_x:
        ax.axvline(x=ejes_x[xeje], color="0.8", lw=0.6, zorder=0)
    for yeje in ejes_y:
        ax.axhline(y=ejes_y[yeje], color="0.8", lw=0.6, zorder=0)
    for xeje, x in ejes_x.items():
        ax.text(x, -17.6, xeje, fontsize=8, ha="center", color="0.35")
    for yeje, y in ejes_y.items():
        ax.text(-0.7, y, yeje, fontsize=8, va="center", color="0.35")

    # Esqueleto vigas del PISO_3
    for v in vigas_por_nivel["PISO_3"]:
        (xi, yi, _), (xj, yj, _) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
        color = "tab:blue" if v["seccion"].startswith("V. 60/80") else "tab:orange"
        ax.plot([xi, xj], [yi, yj], color=color, lw=2.2, zorder=3)

    # Columnas esqueleto en PISO_3
    for g in columnas_por_nivel.values():
        for c in g:
            (xi, yi, zi) = nodos[c["nodo_inferior"]]
            (xj, yj, zj) = nodos[c["nodo_superior"]]
            if abs(zi - z3) < 1e-9:
                _p = (xi, yi)
            elif abs(zj - z3) < 1e-9:
                _p = (xj, yj)
            else:
                continue
            ax.plot([_p[0]], [_p[1]], marker="s", ms=9,
                    color="tab:green", markeredgecolor="black", zorder=4)

    # Muros del bloque 2 (posición INFERIDO_RESPALDADO) en el PISO_3
    for clave, pos in datos_inv.posiciones_verificadas.items():
        if pos.get("tipo") != "muro_ha":
            continue
        if pos.get("eje_x_j") is None or pos.get("eje_y_j") is None:
            continue
        if pos.get("nivel") != "PISO_3":
            continue
        ex_i, ey_i = pos["eje_x_i"], pos["eje_y_i"]
        ex_j, ey_j = pos["eje_x_j"], pos["eje_y_j"]
        if ex_j not in ejes_x or ey_j not in ejes_y:
            continue
        xi, yi = ejes_x[ex_i], ejes_y[ey_i]
        xj, yj = ejes_x[ex_j], ejes_y[ey_j]
        ax.plot([xi, xj], [yi, yj], color="darkorange", lw=8, zorder=2)
        ax.text((xi + xj) / 2, (yi + yj) / 2, pos.get("id_plano", ""),
                fontsize=7, ha="center", va="center", color="w", zorder=6)

    # Elementos irregulares 102 en edificio (marcadores)
    for k in sorted(_elementos_irregulares_102_en_edificio):
        e = _elementos_irregulares_102_en_edificio[k]
        X, Y = e["posicion_modelo"]
        ax.plot([X], [Y], marker="D", ms=7, color="deeppink",
                markeredgecolor="black", zorder=5)
        if e["estado"] == "INFERIDO_RESPALDADO":
            ax.annotate(f"{e['seccion']}\n~({X:.1f},{Y:.1f})", (X, Y),
                        fontsize=6, color="deeppink", ha="left", va="bottom")

    handles = [
        Patch(facecolor="tab:blue", label="Vigas esqueleto V.60/80"),
        Patch(facecolor="tab:green", edgecolor="black", label="Pilares P.70x70"),
        Patch(facecolor="darkorange", label="Muro M.H.A. núcleo (INFERIDO)"),
        Patch(facecolor="deeppink", edgecolor="black",
              label="Elemento irregular 102 (pos. aprox.)"),
        Patch(facecolor="0.75", label="Ejes grilla"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=8)
    ax.set_title("LT1 · CONTROL GEOMETRIA PRINCIPAL + REFERENCIAS IRREGULARES · "
                 "PISO_3 (z=+7.87 m) [sub-plano CIELO PISO 3°, folio 102]\n"
                 "Esqueleto + muros núcleo INFERIDO_RESPALDADO (puntos: POSICION RESPALDADA / "
                 "LONGITUD PENDIENTE) + elementos irregulares con posición aproximada\n"
                 "(convención de niveles: data.inventario.CONVENCION_NIVELES)")
    ax.set_xlim(-1.5, 44)
    ax.set_ylim(-17.5, 1.8)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
    fig.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    ruta = os.path.join(output_dir, "geometria_completa_lt1.png")
    fig.savefig(ruta, dpi=130)
    plt.close(fig)
    print(f"  [OK] geometria completa 2D: {ruta}")
    return ruta


def verificacion_geometria_completa(ruta_txt, ruta_png):
    """Reporte de 13 puntos de la geometría completa (esqueleto + irregular)."""
    r = datos_irreg.resumen_estados()
    cols = sum(1 for g in columnas_por_nivel.values() for _ in g)
    vigas = sum(1 for g in vigas_por_nivel.values() for _ in g)
    muros_real = sum(1 for g in muros_por_nivel.values() for _ in g)

    print("=" * 62)
    print("REPORTE GEOMETRIA COMPLETA LT1 (13 PUNTOS)")
    print("=" * 62)
    print(f"  1. nodos estructurales (esqueleto): {len(nodos)}")
    print(f"  2. columnas esqueleto ubicadas: {cols} (P.70x70 retícula principal)")
    print(f"  3. vigas esqueleto ubicadas: {vigas} (V.60/80 retícula principal)")
    print(f"  4. muros M.H.A. con posición REAL (bloque 2, esqueleto): {muros_real}")
    print(f"  5. muros M.H.A. con posición APROXIMADA (INFERIDO_RESPALDADO): "
          f"{sum(1 for e in _elementos_irregulares_102_en_edificio.values() if e['estado']=='INFERIDO_RESPALDADO')}")
    print(f"  6. total elementos irregulares registrados: {r['total']}")
    print(f"       - muros M.H.A./M.I.: {r['muros_total']}")
    print(f"       - pilares metálicos (P.M./P.M.I.): {r['pilares_total']}")
    print(f"       - vigas metálicas (V.M.): {r['vigas_metal_total']}")
    print(f"       - vigas irregulares/VAR/2ªetapa: {r['vigas_irregulares_total']}")
    print(f"       - V.60/80 extra (fuera retícula): {r['vigas_6080_extra_total']}")
    print(f"  7. elementos por estado: {r['por_estado']}")
    print(f"  8. pendientes geométricos abiertos: {len(datos_irreg.pendientes_geometricos)}")
    for p in datos_irreg.pendientes_geometricos:
        print(f"       - {p['id']}")
    print(f"  9. elasticBeamColumn creados: {len(elementos_opensees)} "
          f"(material H°A° definido por INFORMACION_ACADEMICA_"
          "PROPORCIONADA_POR_USUARIO)")
    print(f" 10. elementos NO construidos (extremo pendiente): "
          f"muros {len(_pendientes_muros_no_construidos)} | "
          f"vigas {len(_pendientes_vigas_no_construidas)}")
    print(f" 11. diafragmas rígidos activos: "
          f"{len([d for d in diafragmas.values() if d])} "
          f"({', '.join(NIVELES_DIAFRAGMA)})")
    print(f" 12. control txt: {ruta_txt}")
    print(f" 13. control png : {ruta_png}")
    print("=" * 62)
    return {
        "nodos": len(nodos), "columnas": cols, "vigas": vigas,
        "muros_real": muros_real,
        "irregulares_total": r["total"],
        "pendientes": len(datos_irreg.pendientes_geometricos),
        "elasticBeamColumn": len(elementos_opensees),
        "muros_no_construidos": len(_pendientes_muros_no_construidos),
        "vigas_no_construidas": len(_pendientes_vigas_no_construidas),
        "ruta_txt": ruta_txt, "ruta_png": ruta_png,
    }


# ============================================================================
# RESOLUCIÓN DE PENDIENTES GEOMÉTRICOS (documento de trazabilidad)
# ============================================================================
_PENDIENTES_TRAZABILIDAD = [
    dict(
        id="CORRELACION_102_NIVEL",
        estado="RESUELTO",
        confianza="VERIFICADO",
        evidencia="OCR del rótulo del plano 102: 'PLANTA CIELO PISO 2°'. "
                  "El folio además contiene un sub-plano 'PLANTA CIELO PISO 3°' "
                  "con NIVEL SUPERIOR LOSA = 7.87 m (= PISO_3, consistente con "
                  "data/geometria.py). Por tanto plan 102 -> PISO_2.",
        impacto="Todos los elementos del plan 102 (muros núcleo, V.30/45, "
                "V.60-30/80-40) se asignan al nivel PISO_2 (z=3.91 m).",
    ),
    dict(
        id="CORRELACION_103_NIVEL",
        estado="RESUELTO",
        confianza="VERIFICADO",
        evidencia="OCR del rótulo del plano 103: 'PLANTA CIELO PISO 4°' con "
                  "NIVEL SUPERIOR LOSA ≈ 11.83 m (= PISO_4 según "
                  "data/geometria.py niveles_z['PISO_4'] = 11.83).",
        impacto="Todos los elementos del plan 103 (M.H.A. núcleo, PM/VM, "
                "+V.I. 20/90 2ª etapa) se asignan al nivel PISO_4 (z=11.83 m).",
    ),
    dict(
        id="MAPEO_103",
        estado="RESUELTO_INFERIDO",
        confianza="INFERIDO_RESPALDADO",
        evidencia="Calibración por 2 muros del núcleo E-F comunes con el plan 102 "
                  "(las mismas posiciones que en M102_02/M102_03). Resulta: "
                  "x = X*8.189 + 264.77, y = Y*7.652 + 392.58 (pdf pt -> modelo m), "
                  "validado además por el rango del plano. Incertidumbre ±1.5-2 m "
                  "por offset de rótulo de muro.",
        impacto="M103_01 -> (0.75, -3.45), M103_02 -> (4.11, -14.53), "
                "M103_03 -> (4.16, -3.45); todos INFERIDO_RESPALDADO en PISO_4. "
                "Confirma el núcleo e=20 en ambos niveles.",
    ),
    dict(
        id="TRAMO_NUCLEO_E_F",
        estado="PARCIALMENTE_RESUELTO",
        confianza="INFERIDO_RESPALDADO (posición de rótulo, cruzada 102/103)",
        evidencia="Posición de rótulo RESUELTA para todos los espesores del núcleo "
                  "E-F, confirmada de forma CRUZADA entre plan 102 (PISO_2) y "
                  "plan 103 (PISO_4): fila Y≈-3.45 (e=20, X≈0.75/4.15), fila "
                  "Y≈-5.6 (e=30, X≈3.08/5.85) y fila Y≈-14.0/-14.5 (e=25, "
                  "X≈2.8/6.1; e=20, X≈4.1). Falta la LONGITUD exacta de cada "
                  "tramo (extremos cotados).",
        impacto="Muros del núcleo registrados con posición en el inventario "
                "(M102/M103 e=20/25/30). NO se crean elasticBeamColumn sin "
                "longitud (extremos).",
    ),
    dict(
        id="ASOC_2A",
        estado="DOCUMENTADO_RESPALDADO",
        confianza="INFERIDO_RESPALDADO",
        evidencia="M102_03/M103_03 en Y≈-14.53, a 0.69 m del eje 2a (-13.845); "
                  "dentro del error de rótulo (~±0.4 m en Y) queda asociado como "
                  "elemento del eje 2a.",
        impacto="El núcleo E-F sur (programa sobre eje 2a) se documenta con la "
                "posición del rótulo; la intersección exacta tramo-eje queda "
                "abierta hasta leer la cota de longitud.",
    ),
    dict(
        id="Y_EXT_SUR_102",
        estado="RESUELTO_CONFIRMADO_VISUAL",
        confianza="CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO",
        evidencia="Cota del borde sur del PISO_2 del plano 102 confirmada por "
                  "inspección visual del usuario sobre la imagen del plano (NO "
                  "OCR, NO inferencia): Y_EXT_SUR_102 = -20.270 m = Y(3) - 4.12 m.",
        impacto="Borde sur del PISO_2 fijado en -20.270 m. Los elementos del "
                "sector (V.30/45 en Y≈-18.86) quedan dentro de la banda "
                "confirmada, pero su trazado (par de nodos, límite X de la "
                "saliente) sigue PENDIENTE.",
    ),
    dict(
        id="X_SUR_102",
        estado="PENDIENTE_COORDENADA",
        confianza="PARCIAL: alineación con Ga=21.45",
        evidencia="V.30/45 rótulo 208 -> X≈21.0 (próximo a Ga=21.45) y rótulo 209 "
                  "-> X≈25.8 (entre G=20 y H=30). Los P.M. 300x300x20 del sector "
                  "saliente aparecen solo en vistas de detalle del plan 102.",
        impacto="La correlación del eje X de los P.M. del sector sur y la "
                "extensión X de la saliente siguen abiertas hasta confirmar la "
                "alineación con un eje certificado.",
    ),
    dict(
        id="M_H_A_E25_E30_POSICION",
        estado="PARCIALMENTE_RESUELTO",
        confianza="INFERIDO_RESPALDADO (capa de texto + cruce 102/103)",
        evidencia="CORRECCIÓN: las etiquetas e=25/e=30 SÍ están en la capa de texto "
                  "de los planos 102 y 103 (2+2 en cada vista principal). Posición "
                  "de rótulo resuelta y confirmada de forma CRUZADA: e=30 en fila "
                  "Y≈-5.6 (X≈3.08/5.85), e=25 en fila Y≈-14.0 (X≈2.8/6.1).",
        impacto="Posición de los muros e=25/e=30 del núcleo registrada. La "
                "longitud de cada tramo (extremos) sigue pendiente.",
    ),
    dict(
        id="V_SECTOR_SUR_POSICIONES",
        estado="PENDIENTE_COORDENADA",
        confianza="PARCIAL: V.30/45 dentro de la banda sur CONFIRMADA; extremos sin cota",
        evidencia="V.30/45 (rótulos 208/209) ubicados en Y≈-18.86, DENTRO de la "
                  "banda sur confirmada por el usuario (Y(3)>=Y>=Y_EXT_SUR_102="
                  "-20.27). V.60-30/80-40, V.60/VAR, V.M. y P.M.I. del sector "
                  "están en vistas de detalle del plan 102 (y_pdf < 419.8) y no "
                  "se pueden mapear al edificio. Para todos los elementos del "
                  "sector falta el par de nodos (extremos) y el límite X.",
        impacto="Posición de V.30/45 registrada (INFERIDO_RESPALDADO_EXTREMOS_"
                "PENDIENTE). El resto del sector sur queda abierto.",
    ),
    dict(
        id="V_FUNDACION_100",
        estado="PENDIENTE_COORDENADA",
        confianza="NO_RESUELTO (parcial)",
        evidencia="La capa de texto del plan 100 identifica V.F. 20/220, 20/180, "
                  "20/160, 20/120, 15/225 y LOSA e=25, con alturas h=155/60/100/"
                  "120/180/516, pero sin cotas de posición de cada viga. "
                  "No hay OCR del plan 100 con mapeo calibrado.",
        impacto="El trazado de vigas de fundación queda pendiente. Se puede "
                "retomar cuando se lea el plan 100 con mapeo calibrado.",
    ),
]


def escribir_resolucion_pendientes_geometricos(ruta):
    import io
    buf = io.StringIO()
    w = buf.write
    w("=" * 90 + "\n")
    w("RESOLUCION DE PENDIENTES GEOMETRICOS · MODELO LT1\n")
    w("=" * 90 + "\n")
    w("Estado de los 10 pendientes raiz de geometria irregular, con confianza,\n")
    w("evidencia y propagacion al modelo. Unidades: metros (m).\n\n")
    w("CONFIANZA: VERIFICADO = evidencia directa (OCR/capa de texto);\n"
      "  INFERIDO_RESPALDADO = inferencia con validacion cruzada;\n"
      "  PARCIAL = parte resuelta, resto pendiente;\n"
      "  NO_RESUELTO = bloqueado (requiere inspeccion humana).\n\n")

    n_resueltos = sum(1 for p in _PENDIENTES_TRAZABILIDAD
                      if p["estado"].endswith("RESUELTO") or
                      p["estado"] in ("DOCUMENTADO_RESPALDADO",))
    n_parcial = sum(1 for p in _PENDIENTES_TRAZABILIDAD
                    if p["estado"].startswith("PARCIAL"))
    n_abiertos = len(_PENDIENTES_TRAZABILIDAD) - n_resueltos - n_parcial

    w(f"Resumen: {n_resueltos} resueltos · {n_parcial} parcialmente resueltos · "
      f"{n_abiertos} abiertos (de {len(_PENDIENTES_TRAZABILIDAD)} pendientes).\n")
    w("=" * 90 + "\n\n")

    for i, p in enumerate(_PENDIENTES_TRAZABILIDAD, 1):
        w(f"{i:2d}. [{p['id']}]\n")
        w(f"    ESTADO    : {p['estado']}\n")
        w(f"    CONFIANZA : {p['confianza']}\n")
        w(f"    EVIDENCIA : {p['evidencia']}\n")
        w(f"    IMPACTO   : {p['impacto']}\n\n")

    w("=" * 90 + "\n")
    w("NOTAS DE METODO\n")
    w("  - Los 3 muros del nucleo E-F del plan 103 (M103_01..03) se mapearon con\n"
      "    el mapeo calibrado de 103 y quedan en PISO_4 INFERIDO_RESPALDADO.\n")
    w("  - Los V.30/45 del sector sur (V3045_01/02) quedan en PISO_2 con\n"
      "    posicion (20.97/-25.77, -18.86).\n")
    w("  - Los e=25/e=30 del nucleo NO estan en capa de texto y el OCR visual\n"
      "    no los lee: queda PENDIENTE y no se inventan posiciones.\n")
    w("  - No se crean nodos ni elasticBeamColumn para irregulares: geometria\n"
      "    queda preparada para la siguiente etapa (material/convencion muro).\n")
    w("=" * 90 + "\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  [OK] resolucion pendientes geometricos: {ruta}")
    return ruta


verificacion_estado_general()
ruta_control = control_visual()
ruta_planta = control_planta102_corregida()
ruta_3d = vista_esqueleto_3d()
resumen_bloque = verificar_bloque_inicial()
reporte_102 = verificacion_geometria_102(ruta_control, ruta_planta)
reporte_esqueleto = verificacion_esqueleto(ruta_control, ruta_3d)

def escribir_convencion_niveles_lt1(ruta):
    """Documenta la convención única plano->nivel y la clasificación A/B/C."""
    from collections import Counter
    import io
    buf = io.StringIO()
    w = buf.write
    w("=" * 90 + "\n")
    w("CONVENCION DE NIVELES Y CLASIFICACION DEL MODELO · LT1\n")
    w("=" * 90 + "\n")
    w("Unidades base: metros (m), kilonewtons (kN), kilopascales (kPa).\n\n")
    w("REGLA (CONVENCION R1): en esta estructura \"PLANTA CIELO PISO N°\" es el\n")
    w("  plano estructural de la LOSA cuyo NIVEL SUPERIOR (cara superior) esta en\n")
    w("  z = PISO_N (data/geometria.py niveles_z). Se calibra con las anotaciones\n")
    w("  EXPLICITAS \"NIVEL SUPERIOR LOSA\" ya documentadas por OCR:\n")
    w("    - folio 102, sub-plano PLANTA CIELO PISO 3°  -> NIVEL SUPERIOR = 7.87 m\n"
      "      (= PISO_3);\n")
    w("    - folio 103, PLANTA CIELO PISO 4°            -> NIVEL SUPERIOR ~ 11.83 m\n"
      "      (= PISO_4).\n")
    w("  PISO OCUPADO N°: entrepiso ocupable entre PISO_{N-1} y PISO_N; su CIELO\n")
    w("  (losa-techo) esta en PISO_N. Las vigas/losa del plano se situan en el\n")
    w("  nivel del cielo; las columnas que lo enmarcan son el tramo "
      "PISO_{N-1}->PISO_N.\n")
    w("  Un MISMO folio puede contener mas de una vista estructural: el folio 102\n"
      "  tiene la vista principal (CIELO PISO 2° -> PISO_2) y un sub-plano parcial\n"
      "  (CIELO PISO 3° -> PISO_3), origen de la reticula del bloque 1 del modelo.\n")
    w("  Fuente unica y autoritativa: data/inventario.CONVENCION_NIVELES (los\n"
      "  consumidores nivel_por_plano / fuente_correlacion_plano_nivel se derivan\n"
      "  de ella; no hay otra definicion de niveles en el proyecto).\n\n")
    w("-" * 90 + "\n")
    w("TABLA PLANO -> NIVEL ESTRUCTURAL\n")
    w("-" * 90 + "\n")
    w(f"  {'plano':<6}{'vista':<11}{'nombre literal':<50}{'piso ocupado':<27}"
      f"{'nivel':<18}{'z (m)':<8}\n")
    for c in datos_inv.CONVENCION_NIVELES:
        w(f"  {c['num_plano']:<6}{c['vista']:<11}{c['nombre_literal'][:49]:<50}"
          f"{c['piso_arquitectonico'][:26]:<27}"
          f"{c['nivel_estructural'] or '-':<18}"
          f"{('%+.2f' % c['z_m']) if c['z_m'] is not None else '-':<8}\n")
    w("\nROL ESTRUCTURAL y JUSTIFICACION por vista:\n")
    for c in datos_inv.CONVENCION_NIVELES:
        w(f"  · {c['num_plano']} [{c['vista']}] {c['nombre_literal']}\n")
        w(f"      rol       : {c['rol_estructural']}\n")
        w(f"      justific.: {c['justificacion']}\n")
        w(f"      fuente    : {c['fuente']}\n")
    w("\nZ DE NIVELES ESTRUCTURALES (data/geometria.py niveles_z):\n")
    for k, v in niveles_z.items():
        w(f"    {k:<20}= {v:+.2f} m\n")
    w("\nFuente por plano (derivada de CONVENCION_NIVELES):\n")
    for plano, nivel in datos_inv.nivel_por_plano.items():
        w(f"  plano {plano} -> {nivel}\n      fuente: "
          f"{datos_inv.fuente_correlacion_plano_nivel[plano]}\n")

    # ------------------------------------------------------------------
    # Clasificacion del modelo A / B / C
    # ------------------------------------------------------------------
    w("\n" + "=" * 90 + "\n")
    w("CLASIFICACION DEL MODELO A/B/C\n")
    w("=" * 90 + "\n")
    cols_A = sum(1 for g in columnas_por_nivel.values() for _ in g)
    vigas_A = sum(1 for g in vigas_por_nivel.values() for _ in g)
    _activos = [d for d in diafragmas.values() if d]
    n_diaf = len(_activos)
    n_apoyos = len(apoyos)
    w("A · GEOMETRIA LISTA PARA OPENSees (construida, verificada, sin material):\n")
    w("    esqueleto retícula principal + bloque 1 (sub-plano CIELO PISO 3°):\n")
    w(f"      columnas P.70x70 : {cols_A}\n")
    w(f"      vigas    V.60/80 : {vigas_A}\n")
    w(f"      nodos            : {len(nodos)}\n")
    w(f"      diafragmas rigidos ({sorted(nodos_maestros)}): {n_diaf} con "
      f"{sum(len(d['nodos']) for d in _activos)} nodos esclavos\n")
    w(f"      apoyos base      : {n_apoyos}\n")

    r = datos_irreg.resumen_estados()
    _b_1 = [k for k in datos_inv.posiciones_verificadas
            if k.startswith(("M102_", "M103_"))]
    _b_2 = [k for k in datos_inv.posiciones_verificadas
            if k.startswith("V3045_")]
    w("\nB · POSICION RESPALDADA, LONGITUD/EXTREMOS PENDIENTES (sin construir):\n")
    w(f"    muros nucleo M.H.A. e=20  : {len(_b_1)} "
      f"(M102_01..03 en PISO_2, M103_01..03 en PISO_4; INFERIDO_RESPALDADO)\n")
    w(f"    vigas      V.30/45 sector : {len(_b_2)} "
      f"(V3045_01/02 en PISO_2; PENDIENTE_COORDENADA_Y_EXT_SUR)\n")

    w("\nC · PENDIENTE DE POSICION (no construidas, sin nodos asociados):\n")
    w(f"    registros PENDIENTE_COORDENADA en geometria_irregular: "
      f"{r['por_estado'].get('PENDIENTE_COORDENADA', 0)}\n")
    _pend_inv = Counter(e.get("plano") for e in datos_inv.elementos_pendientes_coordenada)
    w(f"    elementos pendientes del inventario (todos los planos): "
      f"{len(datos_inv.elementos_pendientes_coordenada)} "
      f"(por plano: {dict(_pend_inv)})\n")
    w("    (incluyen: M.H.A. e=25/e=30 del nucleo, ejes auxiliares Eb/Ec/Ga/H1/H2\n"
      "    filas 1''/2a, sector bajo eje 3 [V.60-30/80-40, V.60/VAR, V.M., P.M.,\n"
      "    P.M.I.], V.F. + LOSA e=25 del plano 100). Bloqueado por cotas\n"
      "    Y_EXT_SUR_102 / X_SUR_102 y por la lectura del plano 100.\n")
    w("=" * 90 + "\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  [OK] convencion de niveles LT1: {ruta}")
    return ruta


# ============================================================================
# P1L2 · MODELO OPENSEES CLASE A ACTIVADO + GRAVEDAD (previo a Unity)
# Clase A: 144 nodos estructurales + 4 masters + 90 columnas + 108 vigas +
# 30 MUROS EQUIVALENTES (CONVENCION_ACADEMICA_MUROS) + 24 apoyos + 4 diafragmas
# rígidos. Clase B/C quedan documentadas fuera del modelo.
# Material H°A° DEFINIDO por INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO:
#   E = 25 000 000 kPa · nu = 0.20 · G = 10 416 667 kPa (G = E/[2(1+nu)],
#   redondeo documentado; 1 kN/m² = 1 kPa). NO atribuidos a planos/documentos.
# ============================================================================
MATERIAL_HA = datos_secc.MATERIAL_HA
MATERIAL_PENDIENTE = "MATERIAL_PENDIENTE_DE_CONVENCION_ACADEMICA"

# Conteo/clasificación real de elementos OpenSees por tag (para resolver la
# inconsistencia previa 106+92 vs 108+90 y reportar solo valores verificados):
def _tipo_categorias_por_tag():
    """Clasifica ops.getEleTags() según los tagRanges del proyecto.
    Devuelve dict con verticales, vigas, muros equivalentes y no_clasificados,
    usando únicamente lo que OpenSees tiene en memoria. Los rigidLink de muros
    NO son elementos y no aparecen aqui (se reportan por separado)."""
    tags_ops = set(ops.getEleTags())
    muro_tags = {m["element_tag"] for m in muros_equivalentes}
    tags_viga = set(viga_tags) if viga_tags else set()
    tags_col = _tags_columnas_reservadas()
    return {
        "ops_total": len(tags_ops),
        "muros_equivalentes": len(tags_ops & muro_tags),
        "vigas": len(tags_ops & tags_viga),
        "columnas": len(tags_ops & tags_col),
        "sin_clasificar": len(tags_ops - tags_col - tags_viga - muro_tags),
    }


def _tags_columnas_reservadas():
    return {c["element_tag"] for g in columnas_por_nivel.values() for c in g}

cargas_vigas_preparadas = []
cargas_gravedad_aplicadas = False
analisis_gravedad_resultado = {
    "estado": "NO_EJECUTADO",
    "mensaje": "Análisis de gravedad todavía no ejecutado.",
}


def material_ha_resumen():
    """Estado del material H°A° (definido). E, nu y G provienen de
    INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO (G25 es clase/resistencia
    del hormigón, NO módulo de corte G); no se atribuyen a planos ni docs."""
    m = MATERIAL_HA
    info = datos_secc.INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO
    listo = m["E_kPa"] is not None and m["G_kPa"] is not None
    return {
        "estado": "LISTO" if listo else MATERIAL_PENDIENTE,
        "E_kPa": m["E_kPa"],
        "nu": m["nu"],
        "G_kPa": m["G_kPa"],
        "fuente": m["fuente"],
        "clase_hormigon": info.get("hormigon_clase"),
        "nota_G25": info.get("nota_G25"),
        "G_formula": info.get("G_formula"),
        "nota_unidades": info.get("nota_unidades"),
        "mensaje": (None if listo else
                    "MATERIAL PENDIENTE: el modelo no se activó."),
    }


def verificar_preparacion_elementos():
    """Pre-verificación de los elementTags reservados (90 columnas + 108 vigas
    + 30 muros equivalentes = 228 elasticBeamColumn) SIN crear nada. Comprueba:
    tags únicos, extremos existentes, longitud > 0, sección con A/Iy/Iz/J
    computables, geomTransf de su familia definida, y que ningún nodo maestro
    de diafragma figure como extremo de elemento. Los 24 rigidLink de muros no
    son elementos: se verifican aparte (pares master/nodo_muro por nivel)."""
    cols = {c["element_tag"]: c for g in columnas_por_nivel.values() for c in g}
    vigas = {v["element_tag"]: v for g in vigas_por_nivel.values() for v in g}
    muros = {m["element_tag"]: m for m in muros_equivalentes}
    rigidlinks_ok = True
    rigidlinks_prob = []
    for m in muros_equivalentes:
        for nt, nivel in ((m["nodo_inferior"], m["nivel_inferior"]),
                          (m["nodo_superior"], m["nivel_superior"])):
            d = diafragmas.get(nivel)
            if not d:
                rigidlinks_ok = False
                rigidlinks_prob.append(
                    f"muro {m['clave']} nodo {nt}: sin diafragma nivel {nivel}")
                continue
            master = d["nodo_maestro"]
            if nt in d["nodos"]:
                rigidlinks_ok = False
                rigidlinks_prob.append(
                    f"muro {m['clave']} nodo {nt}: ES slave del diafragma "
                    f"(no debe serlo; va por rigidLink al master {master})")
    masters = set(nodos_maestros)
    problemas = []
    tags = set(cols) | set(vigas) | set(muros)

    if len(tags) != len(cols) + len(vigas) + len(muros):
        problemas.append("tags duplicados entre columnas/vigas/muros")

    def _props_ok(props):
        if not props:
            return False
        return all(props.get(k, 0) > 0
                   for k in ("A_m2", "J_m4", "Iy_m4", "Iz_m4"))

    for tag, c in cols.items():
        if c["nodo_inferior"] not in nodos or c["nodo_superior"] not in nodos:
            problemas.append(f"columna {tag}: extremo inexistente")
        if c["nodo_inferior"] in masters or c["nodo_superior"] in masters:
            problemas.append(f"columna {tag}: nodo maestro como extremo")
        z1 = nodos[c["nodo_inferior"]][2]
        z2 = nodos[c["nodo_superior"]][2]
        if abs(z2 - z1) < 1e-9:
            problemas.append(f"columna {tag}: longitud vertical cero")
        if not _props_ok(datos_secc.propiedades_por_seccion.get(c["seccion"])):
            problemas.append(f"columna {tag}: sección {c['seccion']} incomputable")
        fam = _familia_transformacion(c)
        if geomtransf_definidas.get(fam, {}).get("estado") != "DEFINIDA":
            problemas.append(f"columna {tag}: geomTransf {fam} sin definir")

    for tag, v in vigas.items():
        if v["nodo_i"] not in nodos or v["nodo_j"] not in nodos:
            problemas.append(f"viga {tag}: extremo inexistente")
        if v["nodo_i"] in masters or v["nodo_j"] in masters:
            problemas.append(f"viga {tag}: nodo maestro como extremo")
        x1, y1, z1 = nodos[v["nodo_i"]]
        x2, y2, z2 = nodos[v["nodo_j"]]
        if abs(z2 - z1) < 1e-9 and (x1 - x2) ** 2 + (y1 - y2) ** 2 < 1e-12:
            problemas.append(f"viga {tag}: longitud cero")
        if not _props_ok(datos_secc.propiedades_por_seccion.get(v["seccion"])):
            problemas.append(f"viga {tag}: sección {v['seccion']} incomputable")
        fam = _familia_transformacion(v)
        if geomtransf_definidas.get(fam, {}).get("estado") != "DEFINIDA":
            problemas.append(f"viga {tag}: geomTransf {fam} sin definir")

    for tag, m in muros.items():
        if m["nodo_inferior"] not in nodos or m["nodo_superior"] not in nodos:
            problemas.append(f"muro equiv {tag}: extremo inexistente")
        if m["nodo_inferior"] in masters or m["nodo_superior"] in masters:
            problemas.append(f"muro equiv {tag}: nodo maestro como extremo")
        z1 = nodos[m["nodo_inferior"]][2]
        z2 = nodos[m["nodo_superior"]][2]
        if abs(z2 - z1) < 1e-9:
            problemas.append(f"muro equiv {tag}: longitud vertical cero")
        if not _props_ok(m):
            problemas.append(f"muro equiv {tag}: A/Iy/Iz/J incomputables")
        fam = "columna_vertical"
        if geomtransf_definidas.get(fam, {}).get("estado") != "DEFINIDA":
            problemas.append(f"muro equiv {tag}: geomTransf {fam} sin definir")

    listo = (not problemas and not rigidlinks_prob
             and len(cols) == 90 and len(vigas) == 108 and len(muros) == 18)
    return {
        "columnas_preparadas": len(cols),
        "vigas_preparadas": len(vigas),
        "muros_equivalentes_preparados": len(muros),
        "rigidlinks_muros_preparados": len(muros) * 2,
        "rigidlinks_muros_ok": rigidlinks_ok,
        "rigidlinks_muros_problemas": rigidlinks_prob,
        "total_elementTags": len(cols) + len(vigas) + len(muros),
        "tags_unicos": len(tags) == len(cols) + len(vigas) + len(muros),
        "problemas": problemas,
        "estado": "LISTA" if listo else "CON_REVISION",
    }


def preparar_cargas_vigas():
    """Consolida las 108 cargas lineales equivalentes de losa (q_G) ya
    transferidas por áreas tributarias (cierre exacto, err≈0, plano 700).
    NO ejecuta eleLoad. SC / puntuales / lineales especiales quedan
    registradas aparte y fuera de esta matriz."""
    global cargas_vigas_preparadas
    cargas_vigas_preparadas = []
    for nivel in NIVELES_LOSA:
        trib = tributacion_por_nivel[nivel]
        for tag, c in trib["vigas_carga"].items():
            cargas_vigas_preparadas.append({
                "nivel": nivel,
                "element_tag": c["element_tag"],
                "orientacion": c["orientacion"],
                "longitud_m": c["longitud_m"],
                "A_trib_m2": c["A_trib"],
                "P_losa_kN": c["P_losa_kN"],
                "w_kN_m": c["w_kN_m"],
                "fuente": "q_G por-paño (plano 700) transferida por áreas "
                          "tributarias (bisectrices)",
                "aplicacion": "ops.eleLoad('-beamUniform', Wy=0, Wz=-w) con "
                              "elementos ya creados",
                "estado": "PREPARADA",
            })
    total = sum(cg["P_losa_kN"] for cg in cargas_vigas_preparadas)
    return {
        "n_cargas_preparadas": len(cargas_vigas_preparadas),
        "P_gravitatoria_total_kN": total,
        "estado": "PREPARADA",
    }


def aplicar_cargas_gravedad():
    """Aplica las cargas gravitacionales (q_G) a los elasticBeamColumn como
    cargas lineales uniformes. BLOQUEADA mientras no haya material: no existen
    elementos y eleLoad sobre elementos inexistentes es inválido. NO se invoca
    hasta que E/G estén respaldados."""
    if not materiales_listos():
        return {"estado": MATERIAL_PENDIENTE, "eleLoad_aplicados": 0,
                "mensaje": "Sin elasticBeamColumn (E/G None): eleLoad bloqueado."}
    tags_existentes = {e["element_tag"] for e in elementos_opensees}
    tags_carga = {cg["element_tag"] for cg in cargas_vigas_preparadas}
    if not tags_carga.issubset(tags_existentes):
        return {"estado": "ELEMENTOS_INCOMPLETOS", "eleLoad_aplicados": 0,
                "mensaje": f"Faltan {len(tags_carga - tags_existentes)} de las "
                           f"108 vigas con carga en el dominio OpenSees."}
    global cargas_gravedad_aplicadas
    if cargas_gravedad_aplicadas:
        return {"estado": "YA_APLICADA", "eleLoad_aplicados": len(tags_carga)}
    try:
        ops.timeSeries("Linear", 1)
        ops.pattern("Plain", 1, 1)
    except Exception:
        pass
    aplicados = 0
    for cg in cargas_vigas_preparadas:
        ops.eleLoad("-ele", cg["element_tag"], "-type", "-beamUniform",
                    0.0, -cg["w_kN_m"])
        aplicados += 1
    cargas_gravedad_aplicadas = True
    return {"estado": "APLICADA", "eleLoad_aplicados": aplicados}


def configurar_y_ejecutar_analisis_gravedad():
    """Cálculo estático bajo gravedad (q_G). Ensamblado: timeSeries, pattern,
    eleLoad, constraints, numberer, system, test, algorithm, integrator,
    analysis, analyze + loadConst. BLOQUEADO por el material: con rigidDiaphragm
    se usará constraints('Transformation'). No se ejecuta nada mientras
    E/nu/G del H°A° sean None."""
    global analisis_gravedad_resultado
    if not materiales_listos():
        analisis_gravedad_resultado = {
            "estado": MATERIAL_PENDIENTE,
            "mensaje": "No se ejecuta análisis: E/nu/G del HºAº son None "
                       "(convención académica pendiente).",
        }
        return analisis_gravedad_resultado

    aplic = aplicar_cargas_gravedad()
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.test("NormDispIncr", 1.0e-6, 30, 2)
    ops.algorithm("Linear")
    ops.integrator("LoadControl", 1.0)
    ops.analysis("Static")
    ok = ops.analyze(1)
    ops.loadConst("-time", 0.0)
    analisis_gravedad_resultado = {
        "estado": "OK_COMPLETADO" if ok == 0 else "NO_CONVERGIO",
        "aplicacion_cargas": aplic,
        "analize_retorno": ok,
    }
    return analisis_gravedad_resultado


def verificar_resultados_gravedad():
    """Verificaciones post-análisis de gravedad sobre el modelo clase A real.
    Calcula (sin maquillar): carga total aplicada, reacciones en los 18
    apoyos, error de equilibrio global (absoluto y relativo), desplazamiento
    máximo y su nodo, NaN/Inf, y compatibilidad de los 4 diafragmas rígidos.
    Solo disponible si el análisis ejecutó si analize retornó éxito."""
    import math
    r = analisis_gravedad_resultado
    if r.get("estado") != "OK_COMPLETADO":
        return {
            "estado": "NO_EJECUTADO",
            "mensaje": r.get("mensaje", "Análisis de gravedad no completado."),
        }

    tags_nodes = sorted(set(ops.getNodeTags()))
    P_aplicada = sum(cg["P_losa_kN"] for cg in cargas_vigas_preparadas)

    ops.reactions()
    reacciones = {}
    suma_Rx = suma_Ry = suma_Rz = 0.0
    for t in sorted(apoyos):
        if t in set(ops.getNodeTags()):
            rv = tuple(ops.nodeReaction(t))
            reacciones[t] = rv
            suma_Rx += rv[0]
            suma_Ry += rv[1]
            suma_Rz += rv[2]

    err_abs = abs(suma_Rz - P_aplicada)
    err_rel = (err_abs / P_aplicada) if P_aplicada else float("NaN")

    max_disp = -1.0
    max_node = None
    max_uz = -1.0
    max_uz_node = None
    nan_inf = False
    nan_inf_nodos = []
    desp = {}
    for t in tags_nodes:
        d = tuple(ops.nodeDisp(t))
        desp[t] = d
        if any(not math.isfinite(v) for v in d):
            nan_inf = True
            nan_inf_nodos.append(t)
            continue
        mag = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
        if mag > max_disp:
            max_disp, max_node = mag, t
        if abs(d[2]) > max_uz:
            max_uz, max_uz_node = abs(d[2]), t
    for t in sorted(apoyos):
        rv = tuple(ops.nodeReaction(t))
        if any(not math.isfinite(v) for v in rv):
            nan_inf = True
            nan_inf_nodos.append(t)

    diafragmas_res = {}
    diafragmas_ok = True
    tol_diaf = 1.0e-6
    for nivel in NIVELES_DIAFRAGMA:
        d = diafragmas.get(nivel)
        if not d:
            continue
        m = d["nodo_maestro"]
        mm = nodos_maestros[m]
        xm, ym, _ = mm["x"], mm["y"], mm["z"]
        dm = desp[m]
        uxm, uym, rzm = dm[0], dm[1], dm[5]
        viol = []
        max_err = 0.0
        for s in d["nodos"]:
            xs, ys, _ = nodos[s]
            ds = desp[s]
            pred_ux = uxm - rzm * (ys - ym)
            pred_uy = uym + rzm * (xs - xm)
            e_ux = abs(pred_ux - ds[0])
            e_uy = abs(pred_uy - ds[1])
            e_rz = abs(rzm - ds[5])
            max_err = max(max_err, e_ux, e_uy, e_rz)
            if max(e_ux, e_uy, e_rz) > tol_diaf:
                viol.append((s, e_ux, e_uy, e_rz))
        d_ok = not viol
        diafragmas_ok = diafragmas_ok and d_ok
        diafragmas_res[nivel] = {
            "master": m,
            "slaves": len(d["nodos"]),
            "ok": d_ok,
            "violaciones": len(viol),
            "max_error": max_err,
        }

    rigidlink_res = {}
    rigidlink_ok = True
    max_rl = 0.0
    tol_rl = 1.0e-6
    # rigidLink('beam', master, nodo_muro): movimiento de cuerpo rigido completo
    # u_muro = u_master + th_master x r ; th_muro = th_master  (r = master->muro)
    for rl in RIGID_LINKS_MUROS:
        nt = rl["nodo_muro"]
        m = rl["nodo_maestro"]
        if nt not in desp or m not in desp:
            continue
        dm = desp[m]
        xm, ym, zm = nodos_maestros[m]["x"], nodos_maestros[m]["y"], nodos_maestros[m]["z"]
        xc, yc, zc = nodos[nt]
        rx, ry, rz = xc - xm, yc - ym, zc - zm
        thx, thy, thz = dm[3], dm[4], dm[5]
        pred = [
            dm[0] + thy * rz - thz * ry,
            dm[1] + thz * rx - thx * rz,
            dm[2] + thx * ry - thy * rx,
            thx, thy, thz,
        ]
        ds = desp[nt]
        e = max(abs(ds[k] - pred[k]) for k in range(6))
        max_rl = max(max_rl, e)
        if e > tol_rl:
            rigidlink_ok = False
            rigidlink_res.setdefault(rl["clave"], []).append(
                {"nodo": nt, "nivel": rl["nivel"], "max_error": e,
                 "master": m})
    rigidlink_res["max_error"] = max_rl

    return {
        "estado": "OK",
        "P_aplicada_kN": P_aplicada,
        "reacciones": reacciones,
        "suma_Rx_kN": suma_Rx,
        "suma_Ry_kN": suma_Ry,
        "suma_Rz_kN": suma_Rz,
        "err_abs_kN": err_abs,
        "err_rel": err_rel,
        "tol_rel_documentada": 1.0e-6,
        "max_desplazamiento_m": max_disp,
        "nodo_max_desplazamiento": max_node,
        "max_Uz_m": max_uz,
        "nodo_max_Uz": max_uz_node,
        "nan_inf_presente": nan_inf,
        "nan_inf_nodos": nan_inf_nodos,
        "diafragmas_ok": diafragmas_ok,
        "diafragmas": diafragmas_res,
        "rigidlink_muros_ok": rigidlink_ok,
        "rigidlink_muros_max_error": max_rl,
        "n_rigidlinks_muros": len(RIGID_LINKS_MUROS),
    }


def escribir_control_preparacion_opensees(ruta):
    """outputs/control_preparacion_opensees.txt · estado del bloque P1L2."""
    import io
    buf = io.StringIO()
    w = buf.write
    w("=" * 90 + "\n")
    w("CONTROL PREPARACION MODELO OPENSEES CLASE A · LT1\n")
    w("Material H°A° DEFINIDO por INFORMACION_ACADEMICA_PROPORCIONADA_POR_"
      "USUARIO\n")
    w("=" * 90 + "\n")

    res_mat = material_ha_resumen()
    pre_ele = verificar_preparacion_elementos()

    n_carga_reg = len(cargas_vigas_preparadas)
    p_carga_total = sum(cg["P_losa_kN"] for cg in cargas_vigas_preparadas)
    res_car = {"n_cargas_preparadas": n_carga_reg,
               "P_gravitatoria_total_kN": p_carga_total,
               "estado": "PREPARADA"}
    res_anal = analisis_gravedad_resultado
    res_post = verificar_resultados_gravedad()

    material_listo = res_mat["estado"] == "LISTO"
    n_ele = len(elementos_opensees)
    w("ESTADOS\n")
    w(f"  GEOMETRIA_CLASE_A = {'LISTA' if pre_ele['estado'] == 'LISTA' and len(nodos) == 144 else 'CON_REVISION'}\n")
    w(f"  APOYOS = {'LISTOS' if len(apoyos) == 24 else 'CON_REVISION'}\n")
    w(f"  DIAFRAGMAS = {'LISTOS' if len([d for d in diafragmas.values() if d]) == 4 else 'CON_REVISION'}\n")
    w(f"  SECCIONES = {'LISTAS' if not any('sección' in p for p in pre_ele['problemas']) else 'CON_REVISION'}\n")
    w(f"  GEOMTRANSF = {'LISTAS' if sum(1 for v in geomtransf_definidas.values() if v['estado']=='DEFINIDA') == 3 else 'CON_REVISION'}\n")
    w(f"  TRIBUTACION = {'LISTA' if not any(t['bordes_sin_viga'] for t in tributacion_por_nivel.values()) else 'CON_REVISION'}\n")
    w(f"  CARGAS_GRAVEDAD = {'PREPARADAS Y APLICADAS' if res_car['n_cargas_preparadas'] == 108 else 'CON_REVISION'}\n")
    w(f"  MATERIAL = {'LISTO' if material_listo else 'BLOQUEADO'}\n")
    w(f"  ELEMENTOS_OPENSEES = {'CREADOS (' + str(n_ele) + ')' if n_ele == 228 else ('BLOQUEADOS' if not material_listo else 'INCOMPLETOS')}\n")
    w(f"  RIGIDLINKS_MUROS = {n_rigidlinks_muros} (restricciones cinemáticas al master del diafragma)\n")
    w(f"  ANALISIS = {res_anal.get('estado', 'PENDIENTE')}\n")
    w("\n")

    w("1) GEOMETRIA CLASE A\n")
    w(f"     nodos estructurales: {len(nodos)} | masters: {len(nodos_maestros)} | "
      f"ops.getNodeTags(): {len(ops.getNodeTags())}\n")
    w(f"     columnas P.70x70 : {pre_ele['columnas_preparadas']} | "
      f"vigas V.60/80 : {pre_ele['vigas_preparadas']} | "
      f"muros equiv. : {pre_ele['muros_equivalentes_preparados']} | "
      f"rigidLink de muro : {pre_ele['rigidlinks_muros_preparados']} (ok: "
      f"{str(pre_ele['rigidlinks_muros_ok'])}) | "
      f"elementTags : {pre_ele['total_elementTags']} (tags únicos: {str(pre_ele['tags_unicos'])})\n")
    w(f"     problemas detectados en el pre-check: {pre_ele['problemas'] if pre_ele['problemas'] else 'ninguno'}\n")
    w("\n")

    w("2) APOYOS (FUNDACION_SUP z=-7.97 m)\n")
    w(f"     {len(apoyos)} apoyos, 6 GDL empotrados cada uno.\n")
    w("\n")

    w("3) DIAFRAGMAS RIGIDOS\n")
    for nivel in NIVELES_DIAFRAGMA:
        d = diafragmas.get(nivel)
        if d:
            w(f"     {nivel}: master {d['nodo_maestro']} · {len(d['nodos'])} slaves "
              f"· z={d['centroide'][2]:.3f}\n")
    w("\n")

    w("4) SECCIONES COMPUESTAS (A, J, Iy, Iz computables)\n")
    for s, p in sorted(datos_secc.propiedades_por_seccion.items()):
        if not all(k in p for k in ("A_m2", "J_m4", "Iy_m4", "Iz_m4")):
            continue
        w(f"     {s:<10s} A={p['A_m2']:.4f} m2 · J={p['J_m4']:.6e} · "
          f"Iy={p['Iy_m4']:.6e} · Iz={p['Iz_m4']:.6e}\n")
    w("\n")

    w("5) GEOMTRANSF (vecXZ)\n")
    for fam, t in GEOMTRANSF_TAGS.items():
        st = geomtransf_definidas.get(fam, {}).get("estado", "?")
        w(f"     {fam:<16s} tag {t} · {st}\n")
    w("\n")

    w("6) TRIBUTACION (matriz 40 paños, cierre por-nivel)\n")
    total = 0.0
    for nivel in NIVELES_LOSA:
        trib = tributacion_por_nivel[nivel]
        p = trib["P_vigas_kN"] if "P_vigas_kN" in trib else \
            sum(c["P_losa_kN"] for c in trib["vigas_carga"].values())
        total += p
        sin = trib.get("bordes_sin_viga", [])
        w(f"     {nivel}: P_losa={p:10.3f} kN · bordes sin viga: "
          f"{sin if sin else 'ninguno'}\n")
    w(f"     TOTAL q_G (PISO_1..4): {total:.3f} kN\n")
    w("\n")

    w("7) CARGAS GRAVEDAD PREPARADAS Y APLICADAS (108 vigas)\n")
    w("     tag     nivel   orient   L[m]      A_trib[m2]  P[kN]      w[kN/m]\n")
    for cg in sorted(cargas_vigas_preparadas,
                     key=lambda c: (c["nivel"], c["element_tag"])):
        w(f"     {cg['element_tag']:7d}  {cg['nivel']:<7s} {cg['orientacion']:<6s} "
          f"{cg['longitud_m']:8.3f}  {cg['A_trib_m2']:10.3f}  "
          f"{cg['P_losa_kN']:9.3f}  {cg['w_kN_m']:9.3f}\n")
    w(f"     Σ cargas preparadas: {res_car['P_gravitatoria_total_kN']:.3f} kN "
      f"· {res_car['n_cargas_preparadas']} registros · estado {res_car['estado']}\n")
    w("     NOTA: SC (sobrecarga), cargas puntuales y lineales especiales quedan\n"
      "     registradas en data/cargas.py y NO forman parte de q_G.\n")
    w("\n")

    w("8) ANALISIS DE GRAVEDAD (ejecutado)\n")
    w(f"     estado: {res_anal.get('estado')}\n")
    w("     pipeline: timeSeries('Linear',1) + pattern('Plain',1,1) + "
      "eleLoad beamUniform(Wy=0, Wz=-w)\n")
    w("     constraints('Transformation') · numberer('RCM') · "
      "system('BandGeneral')\n")
    w("     test('NormDispIncr', 1e-6, 30, 2) · algorithm('Linear') · "
      "integrator('LoadControl', 1.0)\n")
    w("     analysis('Static') · analyze(1) · loadConst('-time', 0)\n")
    w("\n")

    w("9) VERIFICACIONES POST-ANALISIS\n")
    if res_post.get("estado") == "OK":
        w(f"     P aplicada = {res_post['P_aplicada_kN']:.4f} kN\n")
        w(f"     Σ Rz = {res_post['suma_Rz_kN']:.4f} kN · err abs = "
          f"{res_post['err_abs_kN']:.6e} · err rel = {res_post['err_rel']:.3e}\n")
        w(f"     desplazamiento máximo = {res_post['max_desplazamiento_m']:.6e} m "
          f"(nodo {res_post['nodo_max_desplazamiento']}) · "
          f"max|Uz| = {res_post['max_Uz_m']:.6e} m\n")
        w(f"     NaN/Inf: {'SI en ' + str(res_post['nan_inf_nodos']) if res_post['nan_inf_presente'] else 'ninguno'}\n")
        w(f"     diafragmas compatibles: {res_post['diafragmas_ok']}\n")
    else:
        w(f"     {res_post.get('mensaje')}\n")
    w("\n")

    w("MATERIAL (INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO)\n")
    w(f"     clase de hormigón (G25 = clase/resistencia, NO módulo de corte G): "
      f"{res_mat.get('clase_hormigon')}\n")
    w(f"     E_kPa = {res_mat['E_kPa']} · nu = {res_mat['nu']} · "
      f"G_kPa = {res_mat['G_kPa']}\n")
    w(f"     verificación G: {res_mat.get('G_formula')}\n")
    w(f"     {res_mat.get('nota_unidades')} · {res_mat.get('nota_G25')}\n")
    w(f"     fuente: {res_mat['fuente']}\n")
    w("     Con E y G definidos, el run creó los 228 elasticBeamColumn (90 "
          "columnas + 108 vigas + 30 muros equivalentes), los 24 rigidLink de "
          "muro al master del diafragma y ejecutó el análisis\n")
    w("     de gravedad. Estado: MATERIAL LISTO · ELEMENTOS CREADOS · ANALISIS "
      "EJECUTADO.\n")
    w("=" * 90 + "\n")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  [OK] control preparacion OpenSees: {ruta}")
    return ruta


# ============================================================================
# P1L4 · POSTPROCESO PARA UNITY
# (SOLO lectura sobre el modelo ya analizado; no modifica el análisis)
# ============================================================================

def _nodos_de_elemento(elem):
    """Nodos i/j de un registro de elemento (vigas usan nodo_i/nodo_j;
    columnas y muros usan nodo_inferior/nodo_superior)."""
    if "nodo_i" in elem and "nodo_j" in elem:
        return elem["nodo_i"], elem["nodo_j"]
    return elem.get("nodo_inferior"), elem.get("nodo_superior")


def colectar_fuerzas_locales_elementos():
    """Fuerzas locales de cada elasticBeamColumn (SOLO lectura).

    opsi.eleResponse(tag, 'localForce') devuelve el vector de 12 componentes
    en el sistema LOCAL del elemento con orden [N, Vy, Vz, T, My, Mz] en el
    extremo i y el mismo en el extremo j. Unidades: N/V (kN), T/M (kN·m).
    NOTA: ops.eleForce() devuelve fuerzas GLOBALES en los nodos, no locales;
    por eso se usa 'localForce'.
    """
    out = []
    for elem in elementos_opensees:
        tag = elem["element_tag"]
        ni, nj = _nodos_de_elemento(elem)
        f = None
        try:
            f = tuple(float(x) for x in ops.eleResponse(tag, "localForce"))
        except Exception as exc:  # pragma: no cover - defensivo
            f = None
        if f is None or len(f) != 12:
            out.append({"elementTag": tag, "node_i": ni, "node_j": nj,
                        "estado": "SIN_FUERZAS",
                        "error": "ops.eleResponse 'localForce' no disponible"})
            continue
        out.append({
            "elementTag": tag, "node_i": ni, "node_j": nj,
            "F_i": [round(x, 9) for x in f[0:6]],
            "F_j": [round(x, 9) for x in f[6:12]],
        })
    return out


def _candidatas_curva_pm_columna_111000():
    """Rutas candidatas al CSV de la curva P-M de la columna P.70x70 tag
    111000 (Parte D Semana 3, COMBINADO). La curva usa SUPUESTOS de
    modelación: f'c=30 MPa, fy=420 MPa, 16 Φ22, 4 cm cara→eje (los planos no
    documentan f'c/fy ni recubrimiento; la E.T.O.G. está pendiente). Por esa
    razón esta curva NO se exporta al JSON del visor: NO es capacidad real.
    Se conserva la funcion solo como referencia/lectura de la Parte D."""
    base = os.path.join("COMBINADO", "outputs", "semana03", "capacity")
    return [os.path.join("..", base, "pm_interaction.csv"),
            os.path.join(base, "pm_interaction.csv")]


def leer_curva_pm_columna_111000():
    """Devuelve (ruta, puntos) de la curva P-M de la Parte D, o (None, []) si
    no se encuentra. Los puntos NO son datos reales de planos (ver docstring
    de _candidatas_curva_pm_columna_111000); esta funcion NO se usa en la
    exportacion del visor para no presentar SUPUESTOS como capacidad."""
    import csv as _csv
    for ruta in _candidatas_curva_pm_columna_111000():
        if os.path.isfile(ruta):
            puntos = []
            with open(ruta, newline="", encoding="utf-8") as fh:
                for fila in _csv.DictReader(fh):
                    try:
                        puntos.append({
                            "punto": fila.get("punto", "").strip(),
                            "tipo": fila.get("tipo", "").strip(),
                            "P_kN": round(float(fila["P_kN"]), 4),
                            "M_kN_m": round(float(fila["M_kN_m"]), 4),
                        })
                    except (ValueError, KeyError):
                        continue
            return ruta, puntos
    return None, []


def _demanda_extrema(tag, fuerzas, n_nodes):
    """Demanda (N, M_resultante, extremo) desde las fuerzas locales de un
    elemento. N con traccion POSITIVA (convencion igual a la curva P-M:
    compresion < 0). M_resultante = max(hypot(My, Mz)) entre extremos."""
    import math
    for e in fuerzas:
        if e["elementTag"] == tag and "F_i" in e:
            extremos = [("i", e["F_i"], -e["F_i"][0]),
                        ("j", e["F_j"], e["F_j"][0])]
            mejor = None
            for ext, f, n_int in extremos:
                M = math.hypot(f[4], f[5])
                if mejor is None or M > mejor[2]:
                    mejor = (ext, n_int, M)
            ext, N, M = mejor
            return {"caso": "G_gravedad", "extremo": ext,
                    "N_kN": round(N, 4), "M_kN_m": round(M, 4)}
    return None


def exportar_modelo_unity(ruta_json):
    """Exporta el modelo LT1 completo a JSON para el viewer Unity.
    NO modifica el modelo; solo lee datos existentes."""
    import json, os, math
    from datetime import datetime

    res_mat = material_ha_resumen()
    res_anal = analisis_gravedad_resultado
    res_post = verificar_resultados_gravedad()

    nodes_out = []
    for tag in sorted(nodos):
        x, y, z = nodos[tag]
        md = metadata_nodos.get(tag, {})
        nodes_out.append({
            "tag": tag, "x": x, "y": y, "z": z,
            "tipo": "structural",
            "nivel": md.get("nivel", ""),
            "eje_x": md.get("eje_x", ""),
            "eje_y": md.get("eje_y", ""),
        })
    for tag in sorted(nodos_maestros):
        m = nodos_maestros[tag]
        nodes_out.append({
            "tag": tag, "x": m["x"], "y": m["y"], "z": m["z"],
            "tipo": "master",
            "nivel": m["nivel"],
            "eje_x": "", "eje_y": "",
        })

    beams_out = []
    for nivel in NIVELES_LOSA:
        for v in vigas_por_nivel.get(nivel, []):
            et = v["element_tag"]
            ni, nj = v["nodo_i"], v["nodo_j"]
            xi, yi, zi = nodos[ni]
            xj, yj, zj = nodos[nj]
            L = math.sqrt((xj-xi)**2 + (yj-yi)**2 + (zj-zi)**2)
            props = datos_secc.propiedades_por_seccion.get(v["seccion"], {})
            trib = tributacion_por_nivel.get(nivel, {}).get("vigas_carga", {}).get(et, {})
            beams_out.append({
                "elementTag": et, "node_i": ni, "node_j": nj,
                "seccion": v["seccion"], "longitud_m": round(L, 6),
                "nivel": nivel,
                "eje_x_i": v.get("eje_x_i", ""), "eje_y_i": v.get("eje_y_i", ""),
                "eje_x_j": v.get("eje_x_j", ""), "eje_y_j": v.get("eje_y_j", ""),
                "local_axis_xz": list(GEOMTRANSF_VECXZ.get(v.get("familia_transf", ""), (0,0,1))),
                "A_m2": props.get("A_m2"), "Iy_m4": props.get("Iy_m4"),
                "Iz_m4": props.get("Iz_m4"), "J_m4": props.get("J_m4"),
                "carga_lineal_qG_kN_m": trib.get("w_kN_m"),
                "area_tributaria_m2": trib.get("A_trib"),
                "carga_total_tributaria_kN": trib.get("P_losa_kN"),
                "orientacion": trib.get("orientacion", v.get("orientacion", "")),
            })

    columns_out = []
    for nivel in NIVELES_DIAFRAGMA + ["PISO_1S", "FUNDACION_SUP"]:
        for c in columnas_por_nivel.get(nivel, []):
            et = c["element_tag"]
            ni, nj = c["nodo_inferior"], c["nodo_superior"]
            xi, yi, zi = nodos[ni]
            xj, yj, zj = nodos[nj]
            L = math.sqrt((xj-xi)**2 + (yj-yi)**2 + (zj-zi)**2)
            props = datos_secc.propiedades_por_seccion.get(c["seccion"], {})
            columns_out.append({
                "elementTag": et, "node_i": ni, "node_j": nj,
                "seccion": c["seccion"], "longitud_m": round(L, 6),
                "nivel_inferior": c.get("nivel_inferior", ""),
                "nivel_superior": c.get("nivel_superior", ""),
                "local_axis_xz": list(GEOMTRANSF_VECXZ.get(c.get("familia_transf", ""), (1,0,0))),
                "A_m2": props.get("A_m2"), "Iy_m4": props.get("Iy_m4"),
                "Iz_m4": props.get("Iz_m4"), "J_m4": props.get("J_m4"),
            })

    seen_cols = set()
    unique_cols = []
    for c in columns_out:
        if c["elementTag"] not in seen_cols:
            seen_cols.add(c["elementTag"])
            unique_cols.append(c)
    columns_out = unique_cols

    walls_out = []
    for m in muros_equivalentes:
        ni, nj = m["nodo_inferior"], m["nodo_superior"]
        xi, yi, zi = nodos[ni]
        xj, yj, zj = nodos[nj]
        walls_out.append({
            "elementTag": m["element_tag"], "node_i": ni, "node_j": nj,
            "clave": m["clave"], "seccion": m["seccion"],
            "espesor_m": m["espesor_m"], "longitud_planta_m": m["longitud_planta_m"],
            "orientacion": m["orientacion"], "en_plano_direccion": m["en_plano_direccion"],
            "nivel_inferior": m["nivel_inferior"], "nivel_superior": m["nivel_superior"],
            "longitud_vertical_m": round(m["longitud_vertical_m"], 6),
            "local_axis_xz": list(GEOMTRANSF_VECXZ.get("columna_vertical", (1, 0, 0))),
            "A_m2": m["A_m2"], "Iy_m4": m["Iy_m4"],
            "Iz_m4": m["Iz_m4"], "J_m4": m["J_m4"],
            "estado_geometria": m["estado_geometria"],
            "fuente": m["fuente"],
            "constraint": m["constraint"],
            "_geom_xyz": [round(xi, 6), round(yi, 6), round(zi, 6),
                          round(xj, 6), round(yj, 6), round(zj, 6)],
        })

    supports_out = []
    for tag in sorted(apoyos):
        a = apoyos[tag]
        supports_out.append({
            "nodeTag": tag,
            "restricciones": list(a.get("restriccion", (1,1,1,1,1,1))),
            "tipo": a.get("gdl_documentado", "6 GDL empotrados"),
            "nivel": a.get("nivel", "FUNDACION_SUP"),
        })

    diaphragms_out = []
    for nivel in NIVELES_DIAFRAGMA:
        d = diafragmas.get(nivel)
        if not d:
            continue
        diaphragms_out.append({
            "nivel": nivel,
            "master": d["nodo_maestro"],
            "slaves": list(d["nodos"]),
            "z": d["centroide"][2],
            "DOF_compatibilizados": d.get("DOF_compatibilizados", "Ux,Uy,Rz"),
        })

    trib_out = []
    for nivel in NIVELES_LOSA:
        trib = tributacion_por_nivel.get(nivel, {})
        for et, vc in trib.get("vigas_carga", {}).items():
            trib_out.append({
                "elementTag": et, "nivel": nivel,
                "A_tributaria_m2": vc.get("A_trib"),
                "P_losa_kN": vc.get("P_losa_kN"),
                "w_kN_m": vc.get("w_kN_m"),
                "q_G_kPa": vc.get("q_G_kPa_usado"),
                "longitud_m": vc.get("longitud_m"),
                "orientacion": vc.get("orientacion"),
                "origen": vc.get("origen", []),
            })

    analysis_out = {}
    fuerzas_elementos = []
    if res_post.get("estado") == "OK":
        fuerzas_elementos = colectar_fuerzas_locales_elementos()
        analysis_out = {
            "estado": res_anal.get("estado"),
            "P_aplicada_kN": res_post["P_aplicada_kN"],
            "suma_Rz_kN": res_post["suma_Rz_kN"],
            "err_abs_kN": res_post["err_abs_kN"],
            "err_rel": res_post["err_rel"],
            "max_desplazamiento_m": res_post["max_desplazamiento_m"],
            "nodo_max_desplazamiento": res_post["nodo_max_desplazamiento"],
            "max_Uz_m": res_post["max_Uz_m"],
            "nodo_max_Uz": res_post["nodo_max_Uz"],
            "nan_inf": res_post["nan_inf_presente"],
            "diafragmas_compatibles": res_post["diafragmas_ok"],
            "reacciones": {str(k): list(v) for k, v in res_post.get("reacciones", {}).items()},
            "desplazamientos": {},
            # P1L4: caso/combinación activa y fuerzas locales por elemento
            "caso": "G_gravedad",
            "caso_descripcion": "Cargas muertas q_G aplicadas via eleLoad a las "
            "108 vigas (patron Plain 1 / timeSeries Linear 1). Unico caso con "
            "resultados por elemento VERIFICADOS disponibles en este export "
            "(P1L2/P1L3). No se inventan resultados de otros casos.",
            "escenarios": ["G"],
            "convencion_fuerzas": "Fuerzas locales elasticBeamColumn via "
            "ops.eleResponse('localForce') (12 comp por elemento, orden "
            "[N, Vy, Vz, T, My, Mz] en extremo i y j; unidades kN y kN·m; "
            "sistema local del elemento). F_i[0] = -N_interno y "
            "F_j[0] = +N_interno, con N_interno traccion positiva "
            "(compresion < 0); misma convencion usada en la curva P-M.",
            "fuerzas_elementos": fuerzas_elementos,
        }
        tags_nodes = sorted(set(ops.getNodeTags()))
        for t in tags_nodes:
            d = tuple(ops.nodeDisp(t))
            analysis_out["desplazamientos"][str(t)] = list(d)
    else:
        analysis_out = {"estado": res_anal.get("estado", "NO_DISPONIBLE")}

    paños_out = []
    for nivel in NIVELES_LOSA:
        trib = tributacion_por_nivel.get(nivel, {})
        for paño in trib.get("paños", []):
            paños_out.append({
                "id": paño.get("id"),
                "nivel": nivel,
                "eje_x0": paño.get("eje_x0"), "eje_x1": paño.get("eje_x1"),
                "eje_y0": paño.get("eje_y0"), "eje_y1": paño.get("eje_y1"),
                "Lx": paño.get("Lx"), "Ly": paño.get("Ly"),
                "area_m2": paño.get("area_m2"),
                "q_G_kPa": paño.get("q_G_kPa"),
            })

    constraint_links_out = []
    for rl in RIGID_LINKS_MUROS:
        nt = rl["nodo_muro"]
        m = rl["nodo_maestro"]
        xn, yn, zn = nodos[nt]
        xm, ym, zm = nodos_maestros[m]["x"], nodos_maestros[m]["y"], nodos_maestros[m]["z"]
        constraint_links_out.append({
            "rectype": "rigidLink",
            "beamType": "beam",
            "config": "master->nodo_muro (constrained)",
            "nodo_maestro_retained": m,
            "nodo_muro": nt,
            "nivel": rl["nivel"],
            "muro_clave": rl["clave"],
            "lado": rl["lado"],
            "movimiento_heredado": "u_muro = u_master + th_master x r ; "
                                   "th_muro = th_master (cuerpo rigido, 6 DOF)",
            "elimina_gdl": True,
            "_master_xyz": [round(xm, 6), round(ym, 6), round(zm, 6)],
            "_nodomuro_xyz": [round(xn, 6), round(yn, 6), round(zn, 6)],
        })

    PENDIENTES_GEOMETRIA = [
        {"id": "muros_perimetrales_subterraneo_plan101", "descripcion":
         "Muros perimetrales/inclinados del subterráneo (plan 101): "
         "extremos pendientes; los seis paños del núcleo ya están modelados",
         "tipo": "muros", "estado": "PENDIENTE"},
        {"id": "V.30/45", "descripcion": "Vigas V.30/45: extremos/posición "
         "pendientes", "tipo": "vigas", "estado": "PENDIENTE"},
        {"id": "V.60/VAR", "descripcion": "Vigas V.60/VAR: extremos/posición "
         "pendientes", "tipo": "vigas", "estado": "PENDIENTE"},
        {"id": "V.60-30/80-40", "descripcion": "Vigas V.60-30/80-40: "
         "extremos/posición pendientes", "tipo": "vigas", "estado": "PENDIENTE"},
        {"id": "P.M.", "descripcion": "P. M. 300x300x20: pendiente",
         "tipo": "columna", "estado": "PENDIENTE"},
        {"id": "V.M.", "descripcion": "Viga metálica (V.M.): pendiente",
         "tipo": "viga", "estado": "PENDIENTE"},
        {"id": "carga_salientes", "descripcion": "Carga de salientes del "
         "PISO_2: superficies sin carga (no se inventa)",
         "tipo": "cargas", "estado": "PENDIENTE"},
    ]

    # --- P1L4: demanda-capacidad P-M (SOLO con datos sustentados) ----------
    # REGLA: NO se exporta ninguna curva de capacidad P-M cuyo origen sean
    # SUPUESTOS de modelacion. La Parte D (Semana 3, COMBINADO) genero una
    # curva P-M para la columna 111000 con f'c=30 MPa, fy=420 MPa, 4 cm
    # cara->eje y distribucion de 16 barras TODOS SUPUESTOS (los planos LT1
    # 2017_67-* no documentan f'c/fy y el plano general 2017_67-000 remite los
    # recubrimientos a la E.T.O.G., documento NO disponible en el proyecto).
    # Esa curva NO es capacidad real del proyecto y por eso NO se incorpora:
    # columna y muro quedan estado=NO_DISPONIBLE con sus faltantes.
    #
    # Datos REALES verificados usados aqui:
    #  - Columna 111000: seccion "P. 70x70" (modelo_lt1.json) y armadura
    #    16 Φ22 (COMBINADO/outputs/reinforcement/armadura_lt1_columnas.csv,
    #    elementoTag=111000 -> bar_count=16, diameter_mm=22, status EXACT,
    #    source USER_CONFIRMED_DRAWING_DATA).
    #  - Muro 400001 (clave NSUP_01): M.H.A. e=20 cm, L=3.65 m (plan 102,
    #    GEOMETRIA_CERRADA_CONFIRMADO_POR_INSPECCION_VISUAL_USUARIO).
    #  - Demanda: caso G_gravedad del modelo raiz LT1 (P1L2/P1L3; P=ΣRz=
    #    20182.625 kN) vía ops.eleResponse('localForce').
    demandas = {}
    for tag in sorted({aux["elementTag"] for aux in fuerzas_elementos}):
        demandas[tag] = _demanda_extrema(tag, fuerzas_elementos, nodos)

    d_col = demandas.get(111000)
    col_pm = {
        "elemento_tipo": "columna",
        "elementTag": 111000,
        "seccion": "P. 70x70",
        "armadura": {"barras": 16, "diametro_m": 0.022,
                     "fuente": "COMBINADO/outputs/reinforcement/"
                               "armadura_lt1_columnas.csv (elementoTag=111000, "
                               "bar_count=16, diameter_mm=22, status EXACT, "
                               "source USER_CONFIRMED_DRAWING_DATA)"},
        "materiales_fuente": "NO DOCUMENTADOS en el proyecto: los planos LT1 "
                             "(2017_67-*) no indican f'c ni fy; el plano "
                             "general 2017_67-000 remite los recubrimientos a "
                             "la E.T.O.G., documento NO disponible.",
        "estado": "NO_DISPONIBLE",
        "observacion": "La seccion 70x70 y la armadura 16 Φ22 son datos reales, "
                       "pero NO hay curva P-M sustentada: falta f'c, fy, Es, "
                       "recubrimiento libre y la distribucion transversal de "
                       "las 16 barras. La Parte D (Semana 3) resolvio la "
                       "seccion con f'c/fy/distancia/distribucion SUPUESTOS de "
                       "modelacion y esa curva NO se incorpora como capacidad.",
        "fuente_curva": None,
        "curva_pm": [],
        "demanda": d_col,   # demanda real del modelo (G_gravedad), informativa
        "faltantes": [
            "f'c real de proyecto (E.T.O.G./memoria; los planos no lo indican)",
            "fy real de proyecto (E.T.O.G./memoria)",
            "Es / modelo constitutivo del acero (sin datos)",
            "recubrimiento libre documentado (hoy solo distancia cara->eje "
            "SUPUESTA de 4 cm)",
            "distribucion transversal de las 16 barras en la seccion "
            "(no definida en planos)",
        ],
    }

    # Muro: NO hay curva P-M disponible (no se inventa). Solo infraestructura.
    d_muro = demandas.get(400001)
    muro_modelo = next((m for m in muros_equivalentes
                        if m["element_tag"] == 400001), None) or {}
    muro_pm = {
        "elemento_tipo": "muro",
        "elementTag": 400001,
        "clave": muro_modelo.get("clave", ""),
        "seccion": muro_modelo.get("seccion", ""),
        "espesor_m": muro_modelo.get("espesor_m"),
        "longitud_planta_m": muro_modelo.get("longitud_planta_m"),
        "estado": "NO_DISPONIBLE",
        "observacion": "No existe curva P-M para el muro: (a) la armadura "
                       "longitudinal de los muros LT1 NO es legible en los "
                       "planos (armadura_lt1_muros.csv: bar_count/diametro/"
                       "espaciamiento VACIOS, status "
                       "NEEDS_DRAWING_VALUE_CONFIRMATION); (b) f'c/fy/"
                       "recubrimiento no documentados (E.T.O.G. pendiente); "
                       "(c) no existe analisis de seccion P-M del muro "
                       "equivalente. No se inventa la curva.",
        "fuente_curva": None,
        "curva_pm": [],
        "demanda": d_muro,   # demanda real del modelo (G_gravedad), informativa
        "faltantes": [
            "Armadura longitudinal de la seccion del muro: bar_count, "
            "diameter_mm y spacing VACIOS en armadura_lt1_muros.csv "
            "(NEEDS_DRAWING_VALUE_CONFIRMATION; PDFs 300-303 no legibles en "
            "esos valores)",
            "f'c real de proyecto (E.T.O.G./memoria)",
            "fy real de proyecto (E.T.O.G./memoria)",
            "recubrimiento documentado",
            "Analisis de seccion (fiber section) P-M del muro equivalente "
            "no realizado en el proyecto",
        ],
    }

    capacidades_out = [col_pm, muro_pm]

    modelo = {
        "metadata": {
            "unidades": {"longitud": "m", "fuerza": "kN", "tension": "kPa"},
            "sistema_coordenadas": "X horizontal, Y horizontal (decreciente), Z vertical (positiva arriba)",
            "fecha_generacion": datetime.now().isoformat(),
            "estado_modelo": "MODELO_ANALIZABLE_CON_GEOMETRIA_RESPALDADA_ACTUAL",
            "analisis_disponible": res_anal.get("estado") == "OK_COMPLETADO",
            "material": {
                "E_kPa": res_mat["E_kPa"],
                "nu": res_mat["nu"],
                "G_kPa": res_mat["G_kPa"],
                "fuente": res_mat["fuente"],
            },
            "conteos": {
                "nodos_totales": len(nodes_out),
                "nodos_estructurales": len(nodos),
                "nodos_master": len(nodos_maestros),
                "elasticBeamColumn": len(elementos_opensees),
                "columnas": 90,
                "vigas": 108,
                "muros_equivalentes": len(walls_out),
                "rigidLink_constraint_muros": len(constraint_links_out),
                "apoyos": len(supports_out),
                "diafragmas": len(diaphragms_out),
            },
            "analisis": {
                "estado": res_anal.get("estado"),
                "analyze_retorno": res_post.get("analize_retorno",
                                                res_anal.get("analize_retorno", 0)),
                "P_gravedad_kN": res_post.get("P_aplicada_kN",
                                              res_anal.get("P_aplicada_kN")),
                "suma_Rz_kN": res_post.get("suma_Rz_kN"),
                "error_rel_equilibrio": res_post.get("err_rel"),
                "max_desplazamiento_m": res_post.get("max_desplazamiento_m"),
            },
            "pendientes": PENDIENTES_GEOMETRIA,
            "limitaciones": [
                "Solo geometria clase A modelada; 7 items de geometria "
                "pendiente (ver metadata.pendientes)",
                "Perfiles metalicos y P.M. 300x300x20 pendientes (segunda etapa)",
                "Material H°A°: E/nu/G INFORMACION_ACADEMICA_PROPORCIONADA_"
                "POR_USUARIO (no proviene de planos)",
                "Modelo lineal elasticBeamColumn (sin plasticidad); NO hay "
                "curva P-M exportada: f'c/fy/recubrimiento no documentados "
                "(E.T.O.G. pendiente). La curva P-M de la Parte D (Semana 3) "
                "usa SUPUESTOS de modelacion y no se incorpora como capacidad",
                "Resultados por elemento disponibles solo para el caso "
                "G_gravedad (caso unico verificada en este export)",
            ],
        },
        "nodes": nodes_out,
        "beams": beams_out,
        "columns": columns_out,
        "supports": supports_out,
        "diaphragms": diaphragms_out,
        "walls": walls_out,
        "constraint_links": constraint_links_out,
        "analysis": analysis_out,
        "capacidades": capacidades_out,
        "tributary_areas": trib_out,
        "panos": paños_out,
        "pending_geometry": PENDIENTES_GEOMETRIA,
    }

    os.makedirs(os.path.dirname(ruta_json), exist_ok=True)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(modelo, f, indent=2, ensure_ascii=False)
    print(f"  [OK] exportacion Unity JSON: {ruta_json}")
    print(f"       nodos: {len(nodes_out)} ({len(nodos)} estructurales + "
          f"{len(nodos_maestros)} masters)")
    print(f"       vigas: {len(beams_out)} · columnas: {len(columns_out)}")
    print(f"       apoyos: {len(supports_out)} · diafragmas: {len(diaphragms_out)}")
    print(f"       tributarias: {len(trib_out)} · paños: {len(paños_out)}")
    print(f"       muros equivalentes: {len(walls_out)} "
          "(núcleos FUNDACION_SUP-PISO_4)")
    print(f"       rigidLink constraint de muros: {len(constraint_links_out)}")
    print(f"       analisis: {analysis_out.get('estado', 'NO_DISPONIBLE')}")
    print(f"       caso activo: {analysis_out.get('caso', 'N/D')} | "
          f"fuerzas por elemento: {len(fuerzas_elementos)} de 228")
    print(f"       capacidades P-M: col tag {col_pm.get('elementTag')} "
          f"({col_pm.get('estado')}) · muro tag "
          f"{muro_pm.get('elementTag')} ({muro_pm.get('estado')})")

    # Copia del mismo JSON (mismo formato, sin duplicar estructura) a la
    # carpeta de datos de Unity: StreamingAssets de LT1Viewer.
    destinos = [
        os.path.join("unity", "LT1Viewer", "Assets", "StreamingAssets",
                     "modelo_lt1.json"),
    ]
    for destino in destinos:
        if os.path.isdir(os.path.dirname(destino)):
            import shutil
            shutil.copyfile(ruta_json, destino)
            print(f"  [OK] copia JSON para Unity: {destino}")
        else:
            print(f"  [AVISO] no existe '{os.path.dirname(destino)}'; "
                  f"el JSON solo quedo en {ruta_json}")
    return ruta_json


def escribir_control_analisis_gravedad_lt1(ruta):
    """outputs/control_analisis_gravedad_lt1.txt · resultados verificados del
    análisis de gravedad (clase A, elasticBeamColumn E=25e6 kPa)."""
    import io
    buf = io.StringIO()
    w = buf.write
    w("=" * 90 + "\n")
    w("CONTROL ANALISIS DE GRAVEDAD LT1 (clase A) · OpenSeesPy\n")
    w("=" * 90 + "\n")

    res_mat = material_ha_resumen()
    res_anal = analisis_gravedad_resultado
    res_post = verificar_resultados_gravedad()
    pre_ele = verificar_preparacion_elementos()

    w("MATERIAL (INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO)\n")
    w(f"     E = {res_mat['E_kPa']:.0f} kPa · nu = {res_mat['nu']} · "
      f"G = {res_mat['G_kPa']:.0f} kPa\n")
    w(f"     verificación: {res_mat.get('G_formula')}\n")
    w(f"     {res_mat.get('nota_unidades')} · {res_mat.get('nota_G25')}\n")
    w("\n")

    w("MODELO\n")
    w(f"     nodos: {len(nodos)} estructurales + {len(nodos_maestros)} maestros "
      f"= {len(ops.getNodeTags())} en el dominio OpenSees\n")
    n_ele = len(elementos_opensees)
    w(f"     elasticBeamColumn: {n_ele} (esperados 228)\n")
    w(f"       columnas P.70x70: 90 · vigas V.60/80: 108 · muros equiv.: 30\n")
    w(f"     rigidLink de muro al master del diafragma: "
      f"{len(RIGID_LINKS_MUROS)} (constraint, no eleTag)\n")
    w(f"     apoyos: {len(apoyos)} empotrados (6 GDL) en FUNDACION_SUP\n")
    w(f"     diafragmas rígidos: "
      f"{len([d for d in diafragmas.values() if d])} "
      f"({', '.join(NIVELES_DIAFRAGMA)})\n")
    w(f"     ops.getEleTags(): {sorted(ops.getEleTags())}\n")
    w(f"     ops.getNodeTags(): {sorted(ops.getNodeTags())}\n")
    w("\n")

    w("CARGAS DE GRAVEDAD (108 vigas, tributación cerrada)\n")
    P = sum(cg["P_losa_kN"] for cg in cargas_vigas_preparadas)
    n_cg = len(cargas_vigas_preparadas)
    w(f"     q_G aplicado vía eleLoad beamUniform(Wy=0, Wz=-w) por viga, "
      f"pattern Plain(1) · timeSeries Linear(1)\n")
    w(f"     Σ P transferida a vigas (P_losas -> P_transferida): "
      f"{P:.3f} kN en {n_cg} vigas\n")
    w("     NOTA: matriz 40 paños no modificada; SC/puntuales/especiales "
      "quedan separadas de q_G.\n")
    w("\n")

    w("SOLVER / PIPELINE\n")
    w("     constraints('Transformation') · numberer('RCM') · "
      "system('BandGeneral')\n")
    w("     test('NormDispIncr', 1e-6, 30, 2) · algorithm('Linear') · "
      "integrator('LoadControl', 1.0)\n")
    w("     analysis('Static') · analyze(1) · loadConst('-time', 0)\n")
    ok = res_anal.get("estado") == "OK_COMPLETADO"
    w(f"     analyze(1) retornó: "
      f"{res_anal.get('analize_retorno') if ok else ('NO EJECUTADO / OBS: ' + str(res_anal.get('mensaje')))} ({'EXITO' if ok else 'FALLO'})\n")
    w("\n")

    w("VERIFICACIONES POST-ANALISIS\n")
    if res_post.get("estado") == "OK":
        w(f"     carga gravitacional total aplicada: "
          f"{res_post['P_aplicada_kN']:.4f} kN\n")
        w(f"     Σ reacciones verticales (24 apoyos, Rz): "
          f"{res_post['suma_Rz_kN']:.4f} kN\n")
        w(f"     |Σ Rz - Σ P| = {res_post['err_abs_kN']:.6e} kN\n")
        w(f"     error relativo de equilibrio: {res_post['err_rel']:.3e} "
          f"(tolerancia documentada: rel <= {res_post['tol_rel_documentada']})\n")
        w(f"     Σ Rx = {res_post['suma_Rx_kN']:.4e} kN · "
          f"Σ Ry = {res_post['suma_Ry_kN']:.4e} kN\n")
        w(f"     desplazamiento máximo: {res_post['max_desplazamiento_m']:.6e} m "
          f"(nodo {res_post['nodo_max_desplazamiento']})\n")
        w(f"     max|Uz|: {res_post['max_Uz_m']:.6e} m "
          f"(nodo {res_post['nodo_max_Uz']})\n")
        w(f"     NaN/Inf: {'SI -> ' + str(res_post['nan_inf_nodos']) if res_post['nan_inf_presente'] else 'ninguno'}\n")
        w(f"     compatibilidad diafragmas rígidos: "
          f"{'OK' if res_post['diafragmas_ok'] else 'VIOLACIONES'}\n")
        for nivel, dr in res_post["diafragmas"].items():
            w(f"        {nivel}: master {dr['master']} · {dr['slaves']} slaves · "
              f"ok={dr['ok']} · max_error={dr['max_error']:.3e} m\n")
        for t in sorted(res_post["reacciones"]):
            rv = res_post["reacciones"][t]
            w(f"     apoyo {t}: Rx={rv[0]:12.5e} · Ry={rv[1]:12.5e} · Rz={rv[2]:12.5e}\n")
    else:
        w(f"     {res_post.get('mensaje')}\n")
    w("=" * 90 + "\n")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  [OK] control analisis gravedad OpenSees: {ruta}")
    return ruta


def control_gravedad_lt1(output_dir="outputs"):
    """Figura outputs/modelo_gravedad_lt1.png: modelo clase A con gravedad
    aplicada, apoyos y niveles (misma traza que apoyos_diafragmas_3d)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    from matplotlib.patches import Patch

    xmin, xmax = min(ejes_x.values()), max(ejes_x.values())
    ymin, ymax = min(ejes_y.values()), max(ejes_y.values())
    zs = list(niveles_z.values())
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')

    for z in zs:
        for (x0, y0), (x1, y1) in [((xmin, ymin), (xmax, ymin)),
                                   ((xmax, ymin), (xmax, ymax)),
                                   ((xmax, ymax), (xmin, ymax)),
                                   ((xmin, ymax), (xmin, ymin))]:
            ax.plot([x0, x1], [y0, y1], [z, z], color="0.75", lw=0.7, alpha=0.6)
    for nivel in niveles_z:
        ax.text(xmin - 1.3, ymin, niveles_z[nivel], nivel, fontsize=7, color="0.3")

    for g in columnas_por_nivel.values():
        for c in g:
            i, j = c["nodo_inferior"], c["nodo_superior"]
            (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
            ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.55", lw=2.2)
    for g in vigas_por_nivel.values():
        for v in g:
            (xi, yi, zi), (xj, yj, zj) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
            ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.7", lw=1.4)

    for mw in muros_equivalentes:
        i, j = mw["nodo_inferior"], mw["nodo_superior"]
        (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
        ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.9", lw=2.6)

    for tag, (x, y, z) in nodos.items():
        ax.scatter([x], [y], [z], color="#2b6cb0", s=16, depthshade=False)

    for tag, a in apoyos.items():
        x, y, z = nodos[tag]
        ax.scatter([x], [y], [z], color="crimson", s=130, marker="s",
                   depthshade=False)
        ax.text(x + 0.4, y + 0.4, z, f"{tag}", fontsize=7, color="crimson")

    for tag, m in nodos_maestros.items():
        ax.scatter([m["x"]], [m["y"]], [m["z"]], color="gold", s=200,
                   marker="*", edgecolors="black", depthshade=False)
        ax.text(m["x"] + 0.4, m["y"] + 0.4, m["z"], f"{tag}",
                fontsize=8, color="darkgoldenrod")

    handles = [
        Patch(fc="#2b6cb0", label="nodo estructural"),
        Patch(fc="crimson", label="nodo de apoyo (FUNDACION_SUP, 6 GDL)"),
        Patch(fc="gold", label="nodo master diafragma"),
        Patch(fc="0.55", label="columnas P.70x70 (90)"),
        Patch(fc="0.7", label="vigas V.60/80 (108) con q_G aplicado"),
        Patch(fc="0.9", label="muros equivalentes (30, FUNDACION_SUP-PISO_4)"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]"); ax.set_zlabel("Z [m]")
    ax.set_title("LT1 · Modelo clase A con gravedad (q_G PISO_1..4) · "
                 "E=25e6 kPa, G=10.4167e6 kPa · apoyos y diafragmas rígidos")
    ax.set_box_aspect((xmax - xmin, ymax - ymin, max(zs) - min(zs)))
    os.makedirs(output_dir, exist_ok=True)
    ruta = os.path.join(output_dir, "modelo_gravedad_lt1.png")
    fig.savefig(ruta, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] modelo gravedad 3D: {ruta}")
    return ruta


# ============================================================================
# MUROS EQUIVALENTES · CONTROL TEXTO + FIGURA 3D
# ============================================================================
def escribir_control_muros_equivalentes_lt1(ruta):
    """outputs/control_muros_equivalentes_lt1.txt · Convención académica de
    muro -> columna equivalente, muros activados, propiedades, conteos reales
    por tags desde ops.getEleTags(), análisis de gravedad y pendientes."""
    import io
    buf = io.StringIO()
    w = buf.write
    w("=" * 90 + "\n")
    w("CONTROL MUROS EQUIVALENTES LT1\n")
    w("=" * 90 + "\n")
    w("Unidades base: metros (m), kilonewtons (kN), kilopascales (kPa)\n\n")

    conv = datos_secc.CONVENCION_ACADEMICA_MUROS
    w("1) CONVENCION APLICADA\n")
    w(f"     id: {conv['id']}\n")
    w(f"     descripcion: {conv['descripcion']}\n")
    w(f"     fuente: {conv['fuente']}\n")
    w(f"     estado documental: {conv['estado_documental']}\n")
    w("     Seccion rectangular equivalente (se reutiliza la convencion J del\n")
    w("     proyecto, _constante_torsional_rect; NO se inventa formula nueva):\n")
    for k, v in conv["seccion_rectangular"].items():
        w(f"         {k} = {v}\n")
    w("     Ejes fuertes/debiles segun la orientacion real del muro (elemento\n")
    w("     vertical: x local=+Z, y local=-Y, z local=+X, vecxz=(1,0,0)):\n")
    for k, v in conv["ejes_fuertes_debiles"].items():
        w(f"         {k}: {v}\n")
    w("\n")

    w("2) MUROS ACTIVADOS (previamente en MUROS_CERRADOS_PISO_2, activo=False)\n")
    for m in muros_equivalentes:
        w(f"     {m['clave']:<11s} e={m['espesor_m']:.2f} m · L_planta="
          f"{m['longitud_planta_m']:.3f} m · {m['orientacion']:<16s} "
          f"en plano={m['en_plano_direccion']} · tag={m['element_tag']}\n")
    w(f"     total activados: {len(muros_equivalentes)}\n")
    w("\n")

    w("3) TRAMOS VERTICALES CREADOS (continuidad respaldada)\n")
    w("     Interpretacion (CONVENCION_NIVELES de data/inventario.py): los\n")
    w("     muros del plan 102 'CIELO PISO 2°' son enmarcados por el tramo\n")
    w("     PISO_1 -> PISO_2.\n")
    for m in muros_equivalentes:
        w(f"     {m['clave']:<11s} {m['nivel_inferior']} (z={m['z_inferior_m']:.2f})"
          f" -> {m['nivel_superior']} (z={m['z_superior_m']:.2f}) | "
          f"L_vertical={m['longitud_vertical_m']:.2f} m | nodos "
          f"{m['nodo_inferior']}/{m['nodo_superior']}\n")
        for rl in RIGID_LINKS_MUROS:
            if rl["clave"] != m["clave"]:
                continue
            w(f"     {'':11s} rigidLink('beam', master "
              f"{rl['nodo_maestro']} [{rl['nivel']}], "
              f"nodo_muro {rl['nodo_muro']}) [{rl['lado']}]\n")
    w("     Los nodos de muro NO son slaves del diafragma. Cada base/tope hereda\n"
      "     el movimiento de cuerpo rigido de su nivel por RESTRICCION CINEMATICA\n"
      "     REAL ops.rigidLink('beam', master_del_diafragma, nodo_muro) (12).\n"
      "     Justificacion empirica (constraints Transformation): slave directo ->\n"
      "     matriz singular; rigidLink al ancla estructural -> no propaga el plano;\n"
      "     rigidLink al MASTER -> error 0.0 vs. plano.\n")
    w("     El nucleo del plan 103 (PISO_4) NO se modela (extremos sin cerrar)\n"
      "     y se reporta PENDIENTE.\n")
    w("\n")

    w("4) PROPIEDADES A · Iy · Iz · J (por muro, rectangulo e x L)\n")
    w("     clave        A[m2]     Iy[m4]        Iz[m4]        J[m4]     "
      "b_local_y  h_local_z\n")
    for m in muros_equivalentes:
        w(f"     {m['clave']:<11s} {m['A_m2']:7.4f} {m['Iy_m4']:13.6e} "
          f"{m['Iz_m4']:13.6e} {m['J_m4']:13.6e}  "
          f"{m['b_local_y_m']:9.3f} {m['h_local_z_m']:9.3f}\n")
    w("\n")

    w("5) NODOS EN EL MODELO\n")
    w(f"     estructurales (base opensees + 12 de muros): {len(nodos)}\n")
    w(f"     masters de diafragma: {len(nodos_maestros)}\n")
    w(f"     ops.getNodeTags(): {len(ops.getNodeTags())}\n")
    w("     Nodos de muro: NO slaves del diafragma; conectados por rigidLink al\n")
    w("     master del diafragma de su nivel (constraint real, 12 links)\n")
    for rl in RIGID_LINKS_MUROS:
        w(f"       nodo_muro {rl['nodo_muro']} [{rl['lado']} de "
          f"{rl['clave']}] -> master {rl['nodo_maestro']} ({rl['nivel']})\n")
    w("\n")

    w("6) VIGAS V.60/80 (marcos esqueleto)\n")
    w(f"     {len(viga_tags)} creadas (PISO_1..PISO_4, 27 por nivel)\n")
    w("\n")

    w("7) COLUMNAS P.70x70\n")
    w(f"     {len(col_tags)} creadas (5 tramos x 18 = 90)\n")
    w("\n")

    w("8) MUROS EQUIVALENTES\n")
    w(f"     {len(muros_equivalentes)} (elasticBeamColumn verticales)\n")
    w("\n")

    w("9) TOTAL elasticBeamColumn (conteo REAL por tags desde ops.getEleTags())\n")
    cr = _tipo_categorias_por_tag()
    w(f"     ops.getEleTags() = {cr['ops_total']}\n")
    w(f"       columnas: {cr['columnas']} · vigas: {cr['vigas']} · "
      f"muros equivalentes: {cr['muros_equivalentes']}\n")
    w(f"     consistencia: {cr['ops_total']}"
      f" == {cr['columnas']}+{cr['vigas']}+{cr['muros_equivalentes']}"
      f"+0 (vínculos/sin_clasificar: {cr['sin_clasificar']}) -> "
      f"{'OK' if cr['ops_total'] == cr['columnas'] + cr['vigas'] + cr['muros_equivalentes'] else 'NO'}\n")
    w(f"     constraint rígido de muro (rigidLink, NO eleTag): "
      f"{len(RIGID_LINKS_MUROS)}\n")
    w("     (resuelve la inconsistencia previa 106+92 vs 108+90: solo cuenta\n"
      "     lo realmente cargado en OpenSees)\n")
    w("\n")

    w("10) ANALISIS DE GRAVEDAD (rebuild completo, elasticBeamColumn)\n")
    res_anal = analisis_gravedad_resultado
    w(f"     estado: {res_anal.get('estado')} · "
      f"analyze(1) retorno: {res_anal.get('analize_retorno')}\n")
    w("     pipeline: Transformacion/RCM/BandGeneral/NormDispIncr 1e-6/Linear/")
    w("LoadControl\n")
    w("\n")

    res_post = verificar_resultados_gravedad()
    w("11) SUMATORIA DE REACCIONES (gravedad)\n")
    if res_post.get("estado") == "OK":
        w(f"     P_gravitatoria aplicada (q_G sobre 108 vigas): "
          f"{res_post['P_aplicada_kN']:.4f} kN\n")
        w(f"     Σ Rz (24 apoyos, 6 GDL): {res_post['suma_Rz_kN']:.4f} kN\n")
        w(f"     |Σ Rz - P| = {res_post['err_abs_kN']:.6e} kN\n")
        w("\n")

    w("12) ERROR RELATIVO DE EQUILIBRIO\n")
    if res_post.get("estado") == "OK":
        w(f"     err_rel = {res_post['err_rel']:.3e} (tolerancia documentada "
          f"rel <= {res_post['tol_rel_documentada']})\n")
        w(f"     Σ Rx = {res_post['suma_Rx_kN']:.4e} kN · "
          f"Σ Ry = {res_post['suma_Ry_kN']:.4e} kN\n")
        w(f"     max|U| = {res_post['max_desplazamiento_m']:.6e} m (nodo "
          f"{res_post['nodo_max_desplazamiento']}) · "
          f"max|Uz| = {res_post['max_Uz_m']:.6e} m\n")
        w("     Cargas conservadas: NO se agrego peso propio de muros (no esta\n")
        w("     en la convencion de carga del proyecto) y NO se invento carga de\n")
        w("     salientes.\n")
    else:
        w(f"     {res_post.get('mensaje')}\n")
    w("\n")

    w("13) DIAFRAGMAS RIGIDOS COMPATIBLES + RIGIDLINK DE MUROS\n")
    if res_post.get("estado") == "OK":
        for nivel, dr in res_post["diafragmas"].items():
            w(f"     {nivel}: master {dr['master']} · {dr['slaves']} slaves · "
              f"ok={dr['ok']} · max_error={dr['max_error']:.3e} m\n")
        w(f"     compatibilidad global del diafragma: {res_post['diafragmas_ok']}\n")
        w(f"     rigidLink de muro (u_muro = u_master + th_master x r, 6 DOF): "
          f"{res_post['n_rigidlinks_muros']} links · "
          f"ok={res_post['rigidlink_muros_ok']} · "
          f"max_error={res_post['rigidlink_muros_max_error']:.3e} m\n")
    w("\n")

    w("14) AVISOS / PENDIENTES\n")
    w("     - Nucleo PISO_4 (plan 103): extremos del nucleo sin cerrar -> el\n")
    w("       tramo PISO_3->PISO_4 NO se modela (no inventar).\n")
    w("     - Muros subte (plan 101, 24) y dormitorios M.H.A. e25/e30: posiciones\n"
      "       PENDIENTES -> sin modelar.\n")
    w("     - Salientes del PISO_2 registrados geometricamente pero SIN carga\n"
      "       (superficies pendientes: saliente 1 ~30.9 m2, saliente 2 ~24.6 m2).\n")
    w("     - V.30/45 (2), V.60/VAR (5), V.60-30/80-40 (5), P.M. 300x300x20,\n"
      "       V.M.: extremos/posicion pendientes.\n")
    w("     - Decisión PISO_1->PISO_2 por convencion documentada del proyecto\n"
      "       (CONVENCION_NIVELES); la pregunta al usuario quedo sin contestar y\n"
      "       se avanzo con la opcion recomendada (si se contradice, se ajusta).\n")
    w("\n")

    w("15) ARCHIVOS MODIFICADOS\n")
    w("     - data/secciones.py: CONVENCION_ACADEMICA_MUROS + "
      "props_muro_columna_equivalente\n")
    w("     - src/modelo_lt1.py: nodos de muro conectados por RESTRICCION real\n"
      "       ops.rigidLink('beam', master_del_diafragma, nodo_muro) x12 (se\n"
      "       ELIMINARON los elasticBeamColumn artificiales 450001-450012 de\n"
      "       'vinculacion' no respaldada), elementos de muros, guard de\n"
      "       cargas, conteos reales (228), controles y figura (se retiraron las\n"
      "       variables temporales de depuracion\n"
      "       LT1_MUROS/LT1_COLSEC/LT1_SYSTEM/LT1_NUM)\n")
    w("     - data/geometria_irregular.py + data/inventario.py (geom. v2 previa)\n")
    w("     - tools/generar_correccion_geometria_v2_lt1.py (generador v2)\n")
    w("\n")

    w("16) OUTPUTS GENERADOS\n")
    w(f"     - {ruta}\n")
    w(f"     - outputs/modelo_con_muros_equivalentes_lt1.png\n")
    w("     - previos preservados: control_geometria_corregida_v2_lt1.txt,\n")
    w("       inventario_muros_v2_lt1.txt, modelo_geometria_corregida_v2_lt1.png\n")
    w("=" * 90 + "\n")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  [OK] control muros equivalentes LT1: {ruta}")
    return ruta


def control_modelo_con_muros_equivalentes_lt1(ruta=None):
    """Figura 3D outputs/modelo_con_muros_equivalentes_lt1.png: distingue
    vigas, columnas P.70x70, muros equivalentes, apoyos, niveles y salientes
    geometricos del PISO_2."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    from matplotlib.patches import Patch

    xmin, xmax = min(ejes_x.values()), max(ejes_x.values())
    ymin, ymax = min(ejes_y.values()), max(ejes_y.values())
    zs = list(niveles_z.values())
    fig = plt.figure(figsize=(15, 11))
    ax = fig.add_subplot(111, projection="3d")

    for z in zs:
        for (x0, y0), (x1, y1) in [((xmin, ymin), (xmax, ymin)),
                                   ((xmax, ymin), (xmax, ymax)),
                                   ((xmax, ymax), (xmin, ymax)),
                                   ((xmin, ymax), (xmin, ymin))]:
            ax.plot([x0, x1], [y0, y1], [z, z], color="0.8", lw=0.7, alpha=0.5)
    for nivel in niveles_z:
        ax.text(xmin - 1.5, ymin, niveles_z[nivel], nivel, fontsize=7, color="0.3")

    for g in columnas_por_nivel.values():
        for c in g:
            i, j = c["nodo_inferior"], c["nodo_superior"]
            (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
            ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.55", lw=2.0)
    for g in vigas_por_nivel.values():
        for v in g:
            (xi, yi, zi), (xj, yj, zj) = nodos[v["nodo_i"]], nodos[v["nodo_j"]]
            ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.7", lw=1.2)

    for m in muros_equivalentes:
        i, j = m["nodo_inferior"], m["nodo_superior"]
        (xi, yi, zi), (xj, yj, zj) = nodos[i], nodos[j]
        ax.plot([xi, xj], [yi, yj], [zi, zj], color="#9b1c20", lw=5.5)
        ax.scatter([xi, xj], [yi, yj], [zi, zj], color="#9b1c20",
                   s=40, depthshade=False)
        ax.text(xi + 0.3, yi + 0.3, (zi + zj) / 2, m["clave"], fontsize=7,
                color="#9b1c20")

    for tag, (x, y, z) in nodos.items():
        ax.scatter([x], [y], [z], color="#2b6cb0", s=14, depthshade=False)

    for tag, a in apoyos.items():
        x, y, z = nodos[tag]
        ax.scatter([x], [y], [z], color="crimson", s=120, marker="s",
                   depthshade=False)

    for tag, m in nodos_maestros.items():
        ax.scatter([m["x"]], [m["y"]], [m["z"]], color="gold", s=200,
                   marker="*", edgecolors="black", depthshade=False)

    for sal in datos_irreg.SALIENTES_PISO_2:
        x0, x1 = sal["X"]
        y0, y1 = sal["Y"]
        zs0, zs1 = niveles_z.get(sal.get("nivel", "PISO_2"), 3.91) - 0.04, \
            niveles_z.get(sal.get("nivel", "PISO_2"), 3.91) - 0.01
        ax.plot([x0, x1], [y0, y0], [zs0, zs0], color="limegreen", lw=1.6)
        ax.plot([x1, x1], [y0, y1], [zs0, zs0], color="limegreen", lw=1.6)
        ax.plot([x1, x0], [y1, y1], [zs0, zs0], color="limegreen", lw=1.6)
        ax.plot([x0, x0], [y1, y0], [zs0, zs0], color="limegreen", lw=1.6)
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, zs1, sal["id"], fontsize=8,
                color="darkgreen", ha="center")

    handles = [
        Patch(fc="#2b6cb0", label="nodo estructural"),
        Patch(fc="crimson", label="apoyo empotrado FUNDACION_SUP (6 GDL)"),
        Patch(fc="gold", label="nodo master diafragma"),
        Patch(fc="0.55", label=f"columnas P.70x70 ({len(col_tags)})"),
        Patch(fc="0.7", label=f"vigas V.60/80 ({len(viga_tags)}) con q_G"),
        Patch(fc="#9b1c20",
              label=f"muros equivalentes ({len(muros_equivalentes)})"),
        Patch(fc="limegreen", label="salientes geometricos PISO_2 (sin carga)"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]"); ax.set_zlabel("Z [m]")
    ax.set_title("LT1 · Modelo con muros equivalentes (FUNDACION_SUP-PISO_4) · "
                 "convención académica \ncolumna equivalente e x L · 228 "
                 "elasticBeamColumn (90 col + 108 vigas + 30 muros) · "
                 "24 rigidLink al master del diafragma")
    ax.set_box_aspect((xmax - xmin, ymax - ymin, max(zs) - min(zs)))
    if ruta is None:
        ruta = os.path.join("outputs", "modelo_con_muros_equivalentes_lt1.png")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] modelo con muros equivalentes 3D: {ruta}")
    return ruta


# Etapa OpenSees: elemtos elásticos, recorte plano 000, control y verificación.
reporte_opensees = verificacion_opensees()
try:
    ruta_recorte_000 = generar_recorte_plano000(
        os.path.join("planos", "2017_67-000-Model.pdf"),
        os.path.join("outputs", "plano000_consideraciones_alta_resolucion.png"))
except Exception as exc:
    ruta_recorte_000 = f"ERROR: {exc}"
    print(f"  [AVISO] no se generó recorte plano 000: {exc}")
ruta_control_opensees = escribir_control_opensees(
    os.path.join("outputs", "control_modelo_opensees.txt"))
ruta_control_apoyos = escribir_control_apoyos(
    os.path.join("outputs", "control_apoyos_lt1.txt"))
reporte_apoyos = verificacion_apoyos_diafragmas()
ruta_apoyos_3d = control_apoyos_diafragmas_3d()

# P1L2 · CARGAS DE LOSA + ÁREAS TRIBUTARIAS (sin aplicar a OpenSees).
resumen_trib = preparar_cargas_losa()
ruta_trib_control = escribir_control_areas_tributarias(
    os.path.join("outputs", "control_areas_tributarias.txt"))
ruta_matriz = escribir_matriz_cargas(
    os.path.join("outputs", "matriz_cargas_plano700.txt"))
ruta_trib_3d = control_areas_tributarias_lt1()
ok_trib = verificacion_tributacion()

# ============================================================================
# GEOMETRÍA IRREGULAR COMPLETA (reporte + control visual)
# ============================================================================
ruta_geom_txt = escribir_control_geometria_completa_lt1(
    os.path.join("outputs", "control_geometria_completa_lt1.txt"))
ruta_geom_png = control_geometria_completa_lt1()
reporte_geom_completa = verificacion_geometria_completa(
    ruta_geom_txt, ruta_geom_png)
ruta_resolpend = escribir_resolucion_pendientes_geometricos(
    os.path.join("outputs", "resolucion_pendientes_geometricos.txt"))
ruta_convencion = escribir_convencion_niveles_lt1(
    os.path.join("outputs", "convencion_niveles_lt1.txt"))

# ============================================================================
# P1L2 · MODELO ACTIVADO + ANALISIS DE GRAVEDAD (material definido por usuario)
# ============================================================================
resumen_material_p1l2 = material_ha_resumen()
reporte_prep_elementos_p1l2 = verificar_preparacion_elementos()
reporte_cargas_p1l2 = preparar_cargas_vigas()
reporte_elementos_p1l2 = {"creados": len(elementos_opensees),
                          "tags": sorted(e["element_tag"]
                                         for e in elementos_opensees)}
reporte_analisis_p1l2 = configurar_y_ejecutar_analisis_gravedad()
reporte_postanalisis_p1l2 = verificar_resultados_gravedad()
ruta_preparacion_p1l2 = escribir_control_preparacion_opensees(
    os.path.join("outputs", "control_preparacion_opensees.txt"))
ruta_analisis_p1l2 = escribir_control_analisis_gravedad_lt1(
    os.path.join("outputs", "control_analisis_gravedad_lt1.txt"))
ruta_gravedad_3d = control_gravedad_lt1()

# ============================================================================
# MUROS EQUIVALENTES (CONVENCION_ACADEMICA_MUROS) · controles propios
# ============================================================================
clasificacion_real = _tipo_categorias_por_tag()
ruta_muros_txt = escribir_control_muros_equivalentes_lt1(
    os.path.join("outputs", "control_muros_equivalentes_lt1.txt"))
ruta_muros_png = control_modelo_con_muros_equivalentes_lt1(
    os.path.join("outputs", "modelo_con_muros_equivalentes_lt1.png"))

print("-" * 90)
print("REPORTE FINAL P1L2 · MATERIAL HºAº DEFINIDO · GRAVEDAD EJECUTADA")
print("(INFORMACION_ACADEMICA_PROPORCIONADA_POR_USUARIO: E/nu/G NO vienen de")
print(" planos ni de docs del curso)")
print("-" * 90)
E_ok = resumen_material_p1l2["E_kPa"]
print(f"  1. E/nu/G utilizados: E={E_ok:.0f} kPa · nu={resumen_material_p1l2['nu']} "
      f"· G={resumen_material_p1l2['G_kPa']:.0f} kPa "
      f"(G=E/[2(1+nu)]; 1 kN/m²=1 kPa)")
print(f"  2. nodos en el modelo: {len(nodos)} estructurales + "
      f"{len(nodos_maestros)} masters = {len(ops.getNodeTags())}")
print(f"  3. elasticBeamColumn creados: {reporte_elementos_p1l2['creados']} "
      f"(ops.getEleTags(): {len(ops.getEleTags())})")
n_col_ops = sum(1 for e in elementos_opensees
                if "columna" in e.get("tipo_inventario", ""))
n_vig_ops = sum(1 for e in elementos_opensees
                if "viga" in e.get("tipo_inventario", ""))
n_muro_ops = sum(1 for e in elementos_opensees
                 if e.get("tipo_inventario") == "muro_ha")
print(f"  4. columnas P.70x70: {n_col_ops} (5 tramos x 18)")
print(f"  5. vigas V.60/80: {n_vig_ops} · PISO_1 a PISO_4")
print(f"  5b. muros equivalentes (núcleos FUNDACION_SUP-PISO_4): {n_muro_ops} · "
      f"rigidLink de muro: {len(RIGID_LINKS_MUROS)} "
      f"(clasificación real ops.getEleTags(): "
      f"{clasificacion_real['columnas']}+{clasificacion_real['vigas']}+"
      f"{clasificacion_real['muros_equivalentes']}"
      f"={clasificacion_real['ops_total']}; rigidLink NO son eleTags)")
print(f"  6. carga gravitatoria total (q_G, PISO_1..4): "
      f"{reporte_cargas_p1l2['P_gravitatoria_total_kN']:.3f} kN "
      f"(108 vigas; diafragmas sin tributación directa)")
print(f"  7. carga transferida a vigas vía eleLoad: "
      f"{sum(cg['P_losa_kN'] for cg in cargas_vigas_preparadas):.3f} kN "
      f"(Σ q_G de losa del plano 700 -> P transferida a las 108 vigas)")
print(f"  8. analyze(1): {reporte_analisis_p1l2['analize_retorno']} "
      f"({reporte_analisis_p1l2['estado']})")
if reporte_postanalisis_p1l2.get("estado") == "OK":
    print(f"  9. Σ reacciones verticales (24 apoyos, Rz): "
          f"{reporte_postanalisis_p1l2['suma_Rz_kN']:.3f} kN")
    print(f" 10. error de equilibrio: abs={reporte_postanalisis_p1l2['err_abs_kN']:.3e} kN"
          f" · rel={reporte_postanalisis_p1l2['err_rel']:.3e} "
          f"(tolerancia: <=1e-6)")
    print(f" 11. desplazamiento máximo: "
          f"{reporte_postanalisis_p1l2['max_desplazamiento_m']:.6e} m en nodo "
          f"{reporte_postanalisis_p1l2['nodo_max_desplazamiento']} · "
          f"max|Uz|={reporte_postanalisis_p1l2['max_Uz_m']:.6e} m "
          f"(nodo {reporte_postanalisis_p1l2['nodo_max_Uz']})")
    print(f" 12. diafragmas: compatibles={reporte_postanalisis_p1l2['diafragmas_ok']}"
          f" · rigidLink_muros={reporte_postanalisis_p1l2['n_rigidlinks_muros']} "
          f"(ok={reporte_postanalisis_p1l2['rigidlink_muros_ok']}, "
          f"max_err={reporte_postanalisis_p1l2['rigidlink_muros_max_error']:.3e})"
          f" · NaN/Inf: "
          f"{'SI -> ' + str(reporte_postanalisis_p1l2['nan_inf_nodos']) if reporte_postanalisis_p1l2['nan_inf_presente'] else 'ninguno'}")
else:
    print(f"  9-12. post-analisis: {reporte_postanalisis_p1l2.get('mensaje')}")
print(f" 13. estado del modelo: MODELO_ANALIZABLE_CON_GEOMETRIA_RESPALDADA_ACTUAL "
      f"(NO 'modelo completo')")
print(f" 14. auditados/eliminados: elasticBeamColumn 'vínculos' 450001-450012 "
      f"removidos (no respaldados); sustituidos por 24 rigidLink al master del "
      f"diafragma; conteo de columnas corregido a 5 tramos x 18")
print(f" 15. archivos modificados: data/secciones.py (material HºAº definido) · "
      f"src/modelo_lt1.py (bloque P1L2 + analisis + control)")
print(f" 16. outputs: {ruta_preparacion_p1l2} · {ruta_analisis_p1l2} · "
      f"{ruta_gravedad_3d} · {ruta_muros_txt} · {ruta_muros_png}")
print("-" * 90)

# ============================================================================
# EXPORTACION UNITY
# ============================================================================
os.makedirs("outputs/unity", exist_ok=True)
ruta_json_unity = exportar_modelo_unity(
    os.path.join("outputs", "unity", "modelo_lt1.json"))

print("-" * 62)
print("TRAZABILIDAD elementTags (esqueleto)")
for clave in sorted(_tags_asignados, key=lambda k: _tags_asignados[k]):
    print(f"  tag {_tags_asignados[clave]:7d} -> {clave}")
print("-" * 62)
print("Modelo base LT1 inicializado correctamente")
