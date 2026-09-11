# ============================================================================
# data/sc_zonas_lt1.py
# SC (sobrecarga de uso) zonal LT1 por paño. SOLO DATOS — no modifica nada.
# Fuente única: data/cargas.py (plan 700, lectura celda a celda).
# Unidades: SC expresada en kgf/m² (valor del plano) y kPa (kN/m²).
# paños con CARGA LINEAL tienen SC_kPa = None (PISO_4 P51 / bahía I-I' Y=1-2).
# Esta capa alimenta data/q_zonal_lt1.py y (futuro) la Parte A zonificada.
# ============================================================================

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from cargas import (
    MATRIZ_CARGAS_ZONAL,
    CARGAS_LINEALES,
    NIVELES_CON_LOSA,
    sc_por_pano,
    sc_kPa_por_pano,
    kgf_m2_a_kPa,
)

_ANCHO_COL = {1: 20.0, 2: 20.0, 3: 2.5}
_ALTO_ROW = {1: 8.9, 2: 7.25}


def _bay_to_col(bay_x):
    if bay_x in (1, 2):
        return 1
    if bay_x in (3, 4):
        return 2
    if bay_x == 5:
        return 3
    raise ValueError(f"bay_x={bay_x} fuera de rango")


def panos_sc():
    """Lista ordenada de los 40 paños LT1 con su SC del plan 700.

    Retorna dicts {nivel, pano_id, bay_x, row_y, eje_x0, eje_x1,
    eje_y0, eje_y1, Lx, Ly, area_m2, SC_kgf_m2, SC_kPa, estado, fuente}.
    SC_kgf_m2 / SC_kPa = None si la celda es CARGA LINEAL.
    """
    out = []
    ejes_x = ["E", "F", "G", "H", "I", "I'"]
    ejes_y = ["1", "2", "3"]
    for nv in NIVELES_CON_LOSA:
        mat = MATRIZ_CARGAS_ZONAL[nv]
        for bay_x in (1, 2, 3, 4, 5):
            for row_y in (1, 2):
                pid = f"{nv}_P{bay_x}{row_y}"
                col = _bay_to_col(bay_x)
                zona = mat["zonas"][(col, row_y)]
                sc_kg = sc_por_pano(nv, pid)
                out.append({
                    "nivel": nv,
                    "pano_id": pid,
                    "bay_x": bay_x,
                    "row_y": row_y,
                    "eje_x0": ejes_x[bay_x - 1],
                    "eje_x1": ejes_x[bay_x],
                    "eje_y0": ejes_y[row_y - 1],
                    "eje_y1": ejes_y[row_y],
                    "Lx": _ANCHO_COL[col],
                    "Ly": _ALTO_ROW[row_y],
                    "area_m2": _ANCHO_COL[col] * _ALTO_ROW[row_y],
                    "SC_kgf_m2": sc_kg,
                    "SC_kPa": sc_kPa_por_pano(nv, pid),
                    "estado": zona["estado"],
                    "fuente": zona["fuente"],
                })
    return out


PANOS_SC = panos_sc()

SC_KGF_M2_POR_PANO = {nv: {} for nv in NIVELES_CON_LOSA}
SC_KPA_POR_PANO = {nv: {} for nv in NIVELES_CON_LOSA}
for _p in PANOS_SC:
    SC_KGF_M2_POR_PANO[_p["nivel"]][_p["pano_id"]] = _p["SC_kgf_m2"]
    SC_KPA_POR_PANO[_p["nivel"]][_p["pano_id"]] = _p["SC_kPa"]


def lineales_sc():
    """Cargas LINEALES de SC del plan 700 (CARGAS_LINEALES que no son área).

    Retorna dicts {nivel, kgf_m, kN_m, zona, fuente, estado}.
    """
    return [
        {
            "nivel": li["nivel"],
            "kgf_m": li["magnitud_kgf_m"],
            "kN_m": kgf_m2_a_kPa(li["magnitud_kgf_m"]),
            "zona": li["zona"],
            "fuente": li["fuente"],
            "estado": li["estado"],
        }
        for li in CARGAS_LINEALES
        if li["tipo"] == "SC LINEAL"
    ]


LINEALES_SC = lineales_sc()


def Q_zon_area_por_nivel():
    """Q_zon LT1 por nivel con la SC de ÁREA del plan 700 (kN).

    Excluye cargas lineales (se reportan en LINEALES_SC).
    """
    total = {}
    resumen = []
    for nv in NIVELES_CON_LOSA:
        q = sum(p["SC_kPa"] * p["area_m2"]
                for p in PANOS_SC if p["nivel"] == nv and p["SC_kPa"] is not None)
        total[nv] = q
        resumen.append({
            "nivel": nv,
            "Q_zon_area_kN": q,
            "A_SC_zon_m2": sum(p["area_m2"] for p in PANOS_SC
                               if p["nivel"] == nv and p["SC_kPa"] is not None),
            "SC_pendientes": [p["pano_id"] for p in PANOS_SC
                              if p["nivel"] == nv and p["SC_kPa"] is None],
        })
    return {"por_nivel": total, "total_kN": sum(total.values()), "resumen": resumen,
            "lineales": LINEALES_SC}