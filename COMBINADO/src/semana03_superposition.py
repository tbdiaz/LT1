# -*- coding: utf-8 -*-
"""SEMANA 3 - PARTE C: combinacion de carga  R = 1.0*G + 1.0*Q + 1.0*EX + 0.0*EY.

Compara DOS formas de obtener R sobre el modelo combinado LT1+LT2:

  (1) SUPERPOSICION lineal: los casos existentes G, Q, EX y EY se corren por
      separado (cada uno en un modelo limpio con la MISMA topologia, apoyos y
      diafragmas) y sus respuestas se suman con los coeficientes de la
      combinacion R = 1.0G + 1.0Q + 1.0EX + 0.0EY.

  (2) CORRIDA EXPLICITA equivalente: un solo modelo con TODOS los casos de R
      aplicados SIMULTANEAMENTE (patrones 1/2 G + 3/4 Q + 5 EX; EY con
      coeficiente 0.0 no se aplica).

Se verifica SOLO lo minimo exigido por el enunciado:
  - desplazamiento de 1 master node representativo  -> master 1005 (ROOF)
  - reaccion de 1 apoyo representativo              -> primer apoyo fijo
  - fuerza interna de 1 elemento representativo     -> columna LT2 3001

Para cada una se reporta: valor por superposicion, valor de la corrida
explicita, error relativo y PASS/FAIL. NO se hacen verificaciones adicionales,
NO se revisan planos, NO se audita el modelo; NO se toca la Parte A ni la
Parte B (este modulo solo APENDE el resumen con la seccion de la Parte C).

Casos reutilizados exactamente como estan definidos:
  G  -> patrones 1/2 (b.apply_loads(), mismo run_combined)
  Q  -> patrones 3/4 (reusado de semana03_live_load, q_Q de Parte A)
  EX -> patron 5  (build_weight_table/forces_per_floor/apply_lateral de
                   semana03_seismic, coef seismico de Parte B)
  EY -> patron 6  (idem, contribuye 0.0 por el coeficiente de la combinacion)

Salidas (SOLO dentro de COMBINADO/):
  outputs/semana03/superposition_cases.csv      (vector por caso corrido)
  outputs/semana03/superposition_results.csv    (comparacion minima 3 items)
  outputs/semana03/resumen_semana03.md          (APENDE Parte C sin tocar A/B)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import openseespy.opensees as ops

from run_combined import CombinedBuilder
from semana03_live_load import build_q_lt2, build_q_lt1, apply_q_patterns
from semana03_seismic import (build_weight_table, forces_per_floor,
                              apply_lateral)

ROOT = Path(__file__).resolve().parents[2]
COMB = ROOT / "COMBINADO"
OUT_S3 = COMB / "outputs" / "semana03"
RESUMEN_MD = OUT_S3 / "resumen_semana03.md"

# Combinacion lineal (enunciado): R = 1.0G + 1.0Q + 1.0EX + 0.0EY
COEF = {"G": 1.0, "Q": 1.0, "EX": 1.0, "EY": 0.0}
CASES = ["G", "Q", "EX", "EY"]

# Cantidades representativas (una sola por tipo, determinista en el modelo).
MASTER_REP = 1005              # master node ROOF (desplazamiento)
ELEM_REP_INDEX = 0             # primera columna LT2 creada (3001)

TOL_REL = 1e-6


def _build_fresh():
    b = CombinedBuilder()
    b.prepare()
    b.check_interface()
    b.build()
    return b


def _lateral_forces():
    forces, _f_total = forces_per_floor(build_weight_table())
    return forces


def _apply_others(b, cases):
    """Aplica los patrones de los casos solicitados sobre el modelo b."""
    for case in cases:
        if case == "G":
            b.apply_loads()
        elif case == "Q":
            lt2 = build_q_lt2(b)
            lt1 = build_q_lt1(b)
            apply_q_patterns(lt2, lt1)
        elif case in ("EX", "EY"):
            apply_lateral(b, _lateral_forces(), case)


def _vectors(b):
    """(disp_master, reaccion_apoyo, fuerza_elemento) del modelo analizado."""
    disp = tuple(float(v) for v in ops.nodeDisp(MASTER_REP))
    ops.reactions()
    reac = tuple(float(ops.nodeReaction(b.support_tags[0], i))
                 for i in range(1, 7))
    force = tuple(float(v) for v in ops.eleForce(b.created["lt2_cols"][
        ELEM_REP_INDEX]))
    return disp, reac, force


def run_case(case):
    """Corrida limpia de UN caso de carga (modelo nuevo)."""
    b = _build_fresh()
    _apply_others(b, [case])
    rc = b.run_analysis()
    if rc != 0:
        raise RuntimeError(
            f"SUPERPOSICION: caso {case} no converge (rc={rc}). "
            "INPUT_REQUIRED.")
    return (case, rc, b.support_tags[0],
            b.created["lt2_cols"][ELEM_REP_INDEX], _vectors(b))


def run_explicit():
    """Corrida EXPLICITA de R = 1.0G + 1.0Q + 1.0EX + 0.0EY.

    Un solo modelo con G, Q y EX aplicados simultaneamente; EY (coef 0) NO
    se aplica (es exactamente la combinacion pedida).
    """
    b = _build_fresh()
    _apply_others(b, ["G", "Q", "EX"])
    rc = b.run_analysis()
    if rc != 0:
        raise RuntimeError(
            f"SUPERPOSICION: corrida explicita no converge (rc={rc}). "
            "INPUT_REQUIRED.")
    return (rc, b.support_tags[0],
            b.created["lt2_cols"][ELEM_REP_INDEX], _vectors(b))


def err_rel(a, b):
    import math
    d = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    rel = d / max(math.sqrt(sum(x * x for x in a)), 1e-12)
    return d, rel


def compare(cases_rows, expl_row):
    """Superposicion (coef*caso) vs corrida explicita, por cantidad vector."""
    names = ["Desplazamiento master 1005 (ROOF, 6 GDL)",
             f"Reaccion apoyo {expl_row[1]} (6 GDL)",
             f"Fuerza interna columna {expl_row[2]} (12 GDL)"]
    rows = []
    for i, name in enumerate(names):
        n = len(cases_rows[0][4][i])
        sup = tuple(sum(COEF[c[0]] * c[4][i][k] for c in cases_rows)
                    for k in range(n))
        exc = tuple(expl_row[3][i])
        abs_, rel = err_rel(exc, sup)
        rows.append(dict(
            cantidad=name,
            superposicion=json.dumps([round(v, 9) for v in sup]),
            corrida_explicita=json.dumps([round(v, 9) for v in exc]),
            err_abs=round(abs_, 9),
            err_rel=rel,
            PASS="PASS" if rel <= TOL_REL else "FAIL"))
    return pd.DataFrame(rows)


def write_outputs(cases_df, comp_df, support_tag, elem_tag, coef=COEF):
    OUT_S3.mkdir(parents=True, exist_ok=True)
    cases_df.to_csv(OUT_S3 / "superposition_cases.csv", index=False)
    comp_df.to_csv(OUT_S3 / "superposition_results.csv", index=False)

    lin = ["", "## SEMANA 3 - PARTE C: combinacion R = 1.0G + 1.0Q + 1.0EX + "
           "0.0EY", "",
           "- Superposicion lineal de los casos existentes G (patrones 1/2), "
           "Q (3/4), EX (5) y EY (6), con coeficientes "
           "{G:1.0, Q:1.0, EX:1.0, EY:0.0}.",
           "- Corrida explicita equivalente: un solo modelo con G + Q + EX "
           "aplicados simultaneamente; EY (coef 0.0) NO se aplica.",
           f"- Verificacion MINIMA: desplazamiento del master {MASTER_REP} "
           f"(ROOF), reaccion del apoyo {support_tag}, fuerza interna de la "
           f"columna {elem_tag}.",
           "", "| cantidad | err_abs | err_rel | PASS |",
           "|---|---|---|---|"]
    for r in comp_df.itertuples(index=False):
        lin.append(f"| {r.cantidad} | {r.err_abs:.3e} | {r.err_rel:.2e} | "
                   f"{r.PASS} |")
    lin += ["", "Vectores completos por item: `superposition_results.csv` "
            "(superposicion vs corrida explicita) y `superposition_cases.csv` "
            "(respuesta de cada caso corrido).", ""]

    prev = RESUMEN_MD.read_text(encoding="utf-8").rstrip()
    marker = "## SEMANA 3 - PARTE C"
    if marker in prev:      # idempotente: descarta secciones C anexadas antes
        prev = prev.split(marker, 1)[0].rstrip()
    RESUMEN_MD.write_text(prev + "\n" + "\n".join(lin).lstrip("\n"),
                          encoding="utf-8")


def main():
    print("=" * 74)
    print("SEMANA 3 - PARTE C | R = 1.0G + 1.0Q + 1.0EX + 0.0EY | "
          "superposicion vs corrida explicita")
    print("=" * 74)
    print(f"  representativos: master {MASTER_REP} (ROOF) | apoyo = "
          "primer fijo | columna LT2 3001")

    rows = []
    for case in CASES:
        row = run_case(case)
        rows.append(row)
        print(f"\n  caso {case:>2} rc={row[1]} | apoyo {row[2]} | "
              f"columna {row[3]}")
        print(f"    master disp  = {[round(v, 9) for v in row[4][0]]}")
        print(f"    apoyo reacc. = {[round(v, 6) for v in row[4][1]]}")
        print(f"    col. fuerza  = {[round(v, 6) for v in row[4][2]]}")

    cases_df = pd.DataFrame([
        dict(caso=c[0], rc=c[1], apoyo_tag=c[2], elemento_tag=c[3],
             master_disp_6gdl=json.dumps([round(v, 9) for v in c[4][0]]),
             apoyo_reac_6gdl=json.dumps([round(v, 6) for v in c[4][1]]),
             columna_fuerza_12gdl=json.dumps([round(v, 6) for v in c[4][2]]))
        for c in rows])

    expl = run_explicit()
    print(f"\n  corrida EXPLICITA rc={expl[0]} | apoyo {expl[1]} | "
          f"columna {expl[2]}")
    print(f"    master disp  = {[round(v, 9) for v in expl[3][0]]}")
    print(f"    apoyo reacc. = {[round(v, 6) for v in expl[3][1]]}")
    print(f"    col. fuerza  = {[round(v, 6) for v in expl[3][2]]}")

    comp = compare(rows, expl)
    print("\nComparacion (superposicion vs corrida explicita):")
    print(comp.to_string(index=False))

    write_outputs(cases_df, comp, expl[1], expl[2])

    print("\nSalidas:")
    for p in sorted(OUT_S3.glob("superposition*")):
        print("  ", p.relative_to(ROOT))
    return 0 if (comp["PASS"] == "PASS").all() else 3


if __name__ == "__main__":
    import sys
    sys.exit(main())