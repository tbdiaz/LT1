#!/usr/bin/env python3
"""integrar_p1l4_unity.py - FASE 4: integra capacidades P-M (resultado de
p1l4_pm.py) a modelo_combinado.json (COMBINADO y copia del viewer Unity).

NO modifica nodos/elementos/soportes/cargas/resultados existentes; SOLO
anade `results.pm`: curvas P-M (columna 113022; muro M001 eje fuerte y
debil), demanda por caso con chequeo fuerte/debil, caso activo (COMBO_R)
y trazabilidad elementTag<->objeto<->curva<->capacidad.

Fuentes (generadas por p1l4_pm.py en COMBINADO/outputs/p1l4/):
  - pm_column_113022.csv / pm_wall_M001_fuerte.csv / pm_wall_M001_debil.csv
  - demanda_capacidad_p1l4.csv
  - demanda_p1l4.csv (desglose de la recomposicion)

Uso:  python3 integrar_p1l4_unity.py
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_COMB = _ROOT / "COMBINADO"
_OUT = _COMB / "outputs" / "p1l4"
_JSON = _COMB / "outputs" / "unity" / "modelo_combinado.json"
_UNITY = _ROOT / "unity" / "LT1Viewer" / "Assets" / "StreamingAssets" \
    / "modelo_combinado.json"
_CASOS = ["G", "Q", "EX", "EY", "COMBO_R"]

_WALL_E_M = 0.60
_WALL_L_M = 2.92
_WALL_HALF_M = _WALL_L_M / 2.0
_EPS_CU = 0.003

_SUP_MURO = [
    "borde vertical = 4 22 por cara y extremo (minimo razonable de 303: "
    "2 22 + 2 22; el plano muestra ademas +4 22, +4 25, base 5 32 L=900) "
    "- SUPUESTO conservador",
    "malla D.M.V. 12 a 20 doble cara - CONFIRMADO_PLANO",
    "L=2.92 m = GEOMETRIA DEL MODELO (walls_LT2.csv / modelo combinado; "
    "no confirmado en plano 101)",
    "Concrete01 no confinado (trabas/estribos de 001/000 no aportan "
    "confinamiento en la fibra)",
    "recubrimientos malla 0.035 m / borde 0.05 m - SUPUESTO",
    "capacidad nominal en el estado limite de compresion extrema "
    "eps_cu=0.003 (criterio ACI/NEC); sin phi",
]

_SUP_COL = [
    "P.70x70 (P=0.70 m), 16 barras de 22 mm - armadura EXACT / "
    "USER_CONFIRMED_DRAWING_DATA (armadura_lt1_columnas.csv)",
    "distribucion simetrica (4 esquinas + 3 por cara) - SUPUESTO",
    "cara->eje de barra = 0.04 m - SUPUESTO",
    "Concrete01 no confinado - SUPUESTO",
    "capacidad nominal eps_cu=0.003; sin phi",
]


def _leer_csv(p):
    rows = []
    with open(p, "r", encoding="utf-8") as f:
        head = None
        for lin in f:
            lin = lin.strip()
            if not lin:
                continue
            if head is None:
                head = lin.split(",")
                continue
            rows.append(dict(zip(head, lin.split(","))))
    return rows


def _curva(p):
    """Curva P(M) completa: [[P_kN_compresion, M_kN_m], ...]."""
    out = []
    for r in _leer_csv(p):
        p_ = float(r["P_kN"]); m_ = float(r["M_kN_m"])
        out.append([round(p_, 2), round(m_, 2)])
    return out


def _p0(curva):
    return min(p for p, _ in curva)


def _capacidad_muro(rows):
    cap = {}
    for r in rows:
        cap[r["caso"]] = {
            "N_kN_compresion": round(float(r["N_muro"]), 3),
            "M_fuerte_demanda_kN_m": round(float(r["M_muro"]), 3),
            "M_fuerte_capacidad_kN_m": round(float(r["M_cap_muro_fuerte"]), 3),
            "dentro_fuerte": r["dentro_fuerte"] == "True",
            "My_debil_demanda_kN_m": round(float(r["My_muro"]), 3),
            "M_debil_capacidad_kN_m": round(float(r["M_cap_muro_debil"]), 3),
            "dentro_debil": r["dentro_debil"] == "True",
        }
    return cap


def _capacidad_col(rows):
    cap = {}
    for r in rows:
        cap[r["caso"]] = {
            "N_kN_compresion": round(float(r["N_col"]), 3),
            "M_demanda_kN_m": round(float(r["M_col"]), 3),
            "M_capacidad_kN_m": round(float(r["M_cap_col"]), 3),
            "dentro": r["dentro_col"] == "True",
        }
    return cap


def build_pm():
    f_col = _curva(_OUT / "pm_column_113022.csv")
    f_fuer = _curva(_OUT / "pm_wall_M001_fuerte.csv")
    f_debil = _curva(_OUT / "pm_wall_M001_debil.csv")
    rows = _leer_csv(_OUT / "demanda_capacidad_p1l4.csv")
    dem = _leer_csv(_OUT / "demanda_p1l4.csv")
    ey = next(r for r in dem if r["caso"] == "EY")
    return {
        "tipo": "capacidad_fiber_section_PM",
        "unidades": {"fuerza": "kN", "momento": "kN.m", "longitud": "m"},
        "convencion": {
            "N_positivo": "compresion",
            "M_positivo": "segun localForce de eleResponse",
            "nota": "N positivo=compresion verificado: Rz(apoyo node3 de "
                    "M001)=N1(4002) bajo G",
        },
        "materiales": {"fc_MPa": 35.0, "fy_MPa": 420.0, "Es_GPa": 200.0,
                       "origen": "CONFIRMADO (usuario)",
                       "eps_cu_estado_limite": _EPS_CU},
        "caso_activo": "COMBO_R",
        "combo_definido": "1.0*G + 1.0*Q + 1.0*EX + 0.0*EY",
        "casos_autorizados": _CASOS,
        "muro_M001": {
            "uso": "LT2, eje A', M.H.A. e=0.60 m (plan 2024_22-303)",
            "objetos_unity": {"descripcion": "M001 se representa en Unity "
                               "por los dos elementos muro_corner 4001 y "
                               "4002 (media seccion cada uno). Para la "
                               "verificacion P-M se tratan como UN unico "
                               "muro fisico: los dos objetos comparten el "
                               "mismo bloque P-M agrupado (ver resultados/"
                               "pm/muro_M001) y al seleccionar cualquiera "
                               "de ellos el panel muestra la verificacion "
                               "del muro completo M001.",
                               "elementTags_para_agrupar": [4001, 4002]},
            "elementTags": [4001, 4002],
            "recomposicion": {
                "formula_N": "N_muro = N1(4001) + N1(4002)",
                "formula_M": "M_muro = Mz1(4001)+Mz1(4002)+"
                             "1.46*(N1(4001)-N1(4002))",
                "desglose_EY": "ver auditoria_ey_m001.md",
                "semilongitud_m": _WALL_HALF_M,
                "verificado_ey": {
                    "Mz1_4001_kN_m": ey["Mz1_4001_kN_m"],
                    "Mz1_4002_kN_m": ey["Mz1_4002_kN_m"],
                    "N1_4001_kN": ey["N4001_kN"],
                    "N1_4002_kN": ey["N4002_kN"],
                    "par_axial_kN_m": ey["par_axial_kN_m"],
                    "M_muro_kN_m": ey["M_muro_kN_m"],
                },
                "por_que_N1_4001_es_0": "la esquina A del muro no recibe "
                    "carga axial en ningun caso: el nodo 23 solo conecta los "
                    "muros 4001/4003 y no hay vigas, columnas, conectores ni "
                    "peso propio de muros; es consecuencia valida de la "
                    "idealizacion del modelo (no un error de extraccion ni "
                    "de conectividad)",
                "verificacion_independiente": "Mz1(4001) y Mz1(4002) son "
                    "exactamente las reacciones Mx de los apoyos node1/node3 "
                    "del propio modelo; y N_muro = Rz(1)+Rz(3). ",
            },
            "geometria": {"e_m": _WALL_E_M, "L_m": _WALL_L_M,
                          "fuente_e": "CONFIRMADO_PLANO (303)",
                          "fuente_L": "GEOMETRIA DEL MODELO (csv/modelo)"},
            "supuestos": _SUP_MURO,
            "ejes": {
                "decision": "curva_fuerte = flexion EN EL PLANO (momento de "
                            "vuelco sobre X global) <-> demanda M_muro. "
                            "curva_debil = flexion FUERA DE PLANO <-> "
                            "demanda My_muro.",
                "detalle": "FiberSection2d integra el momento con la 1a "
                           "coordenada del patch; con L en la 1a coord -> "
                           "fuerte; con e en la 1a coord -> debil "
                           "(verificado experimentalmente).",
            },
            "capacidad": {
                "P0_kN_compresion": round(_p0(f_fuer), 2),
                "P0_kN_debil": round(_p0(f_debil), 2),
                "curva_fuerte": f_fuer,
                "curva_debil": f_debil,
                "eps_cu": _EPS_CU,
            },
            "demanda_por_caso": _capacidad_muro(rows),
        },
        "columna_113022": {
            "uso": "LT1, rejilla G x 3, P.70x70, 16 barras de 22 mm",
            "objetos_unity": {"descripcion": "columna representada por el "
                               "elemento 113022; verificacion P-M directa de "
                               "ese elemento.",
                               "elementTags": [113022]},
            "elementTags": [113022],
            "geometria": {"b_m": 0.70, "h_m": 0.70, "n_barras": 16,
                          "diam_mm": 22.0},
            "supuestos": _SUP_COL,
            "capacidad": {
                "P0_kN_compresion": round(_p0(f_col), 2),
                "curva": f_col,
                "eps_cu": _EPS_CU,
            },
            "demanda_por_caso": _capacidad_col(rows),
        },
        "metodologia": "P-M por fiber section (OpenSeesPy): para cada "
                       "compresion N se integra la seccion y el pico M en el "
                       "estado limite eps_cu=0.003 en la fibra extrema de "
                       "compresion. M_capacidad a la N de demanda se corre "
                       "en esa axial exacta; D/C = M_dem/M_cap. ",
    }


def _escribir_md_auditoria(pm):
    out = _OUT / "auditoria_ey_m001.md"
    ey = pm["muro_M001"]["recomposicion"]["verificado_ey"]
    ln = [
        "# P1L4 - FASE A: auditoria del caso EY en M001",
        "",
        "Recomposicion del muro fisico M001 a partir del par 4001+4002 "
        "(idealizacion 'dos columnas equivalentes de media seccion').",
        "",
        "## Desglose numerico de M_muro(EY)",
        "",
        "| termino | valor | procedencia |",
        "|---|---|---|",
        "| Mz1(4001) | " + str(ey["Mz1_4001_kN_m"]) + " kN.m | = reaccion "
        "Mx(apoyo node1) del mismo modelo |",
        "| Mz1(4002) | " + str(ey["Mz1_4002_kN_m"]) + " kN.m | = reaccion "
        "Mx(apoyo node3) del mismo modelo |",
        "| N1(4001) | " + str(ey["N1_4001_kN"]) + " kN | 0: esquina A sin "
        "canales axiales |",
        "| N1(4002) | " + str(ey["N1_4002_kN"]) + " kN | traccion neta "
        "(Rz(node3) del modelo) |",
        "| par axial 1.46*(N4001-N4002) | " + str(ey["par_axial_kN_m"]) +
        " kN.m | Steiner (lever=1.46=L/2) |",
        "| SUMA (M_muro EY) | " + str(ey["M_muro_kN_m"]) + " kN.m | |",
        "",
        "## Verificaciones",
        "",
        "1. Los Mz usados son las reacciones Mx de los apoyos (mismo valor "
        "exacto) => no hay combinacion de extremos incompatibles ni error "
        "de transformacion local/global.",
        "2. N_muro = Rz(1)+Rz(3) con diferencia nula (tambien verificado "
        "en el test de recomposicion).",
        "3. Ambos elementos (4001 y 4002) comparten local z=(1,0,0) y el "
        "mismo corte fisico: base B1 (extremo i).",
        "4. Distancia 1.46 = (yB-yA)/2 con y_centro=0.365: verificada.",
        "5. Equilibrio de momentos en los nodos 23 y 25 cierra (~0); las "
        "fuerzas en Y quedan en los diafragmas L1 (nodos no libres).",
        "6. Sin doble contabilizacion: los Mz estan referidos al "
        "centroidide de cada media seccion y solo se trasladan las axiales "
        "(Steiner).",
        "7. Convencion N positivo = compresion verificada con reacciones "
        "bajo G (Rz node3 = +244.11 = N1(4002)).",
        "",
        "## Eje fuerte/debil (decision)",
        "",
        "FiberSection2d usa la 1a coordenada del patch como brazo del "
        "momento. Con L=2.92 en 1a coord -> curva EJE FUERTE (en plano); "
        "con e=0.60 en 1a coord -> EJE DEBIL (fuera de plano). Demanda "
        "M_muro (en plano) se compara con la curva FUERTE y My_muro "
        "(fuera de plano) con la DEBIL. Capacidades nominales en el "
        "estado limite eps_cu=0.003 (evita artefacto de endurecimiento "
        "lineal de Steel01).",
        "",
        "## Consecuencia del chequeo",
        "",
        "M_muro(EY)=" + str(ey["M_muro_kN_m"]) + " kN.m es la demanda real "
        "de la idealizacion (reaccion de fundacion del modelo). Con el "
        "acero minimo modelado (4 22/cara/extremo) la capacidad de eje "
        "fuerte en EY (N=-82 kN) es ~4966 kN.m => D/C ~ 1.78 (FUERA). "
        "No se afirma que mayor armadura de borde lo mitigue sin mostrar "
        "el calculo.",
    ]
    (out).write_text("\n".join(ln).rstrip() + "\n", encoding="utf-8")


def run():
    if not (_OUT / "demanda_capacidad_p1l4.csv").exists():
        print("Falta outputs/p1l4. Ejecutar primero p1l4_pm.py")
        return 1
    pm = build_pm()
    _escribir_md_auditoria(pm)
    for path in (_JSON, _UNITY):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        d["results"]["pm"] = pm
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        print("integrado ->", path)
    return 0


if __name__ == "__main__":
    sys.exit(run())