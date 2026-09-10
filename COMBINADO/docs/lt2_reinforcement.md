# Armadura LT2 - Dataset y representacion

Modulo que incorpora al proyecto COMBINADO la **armadura levantada de
los planos LT2** (`2024_22-*`) como capa de datos y representacion,
**sin modificar** el modelo estructural combinado (que sigue dando
`rc=0` con los mismos resultados y las mismas coordenadas de montaje).
Completa el esquema ya existente para LT1 (`docs/lt1_reinforcement.md`).

---

## 1. Alcance y principios

- **Solo datos**: las reglas de armadura provienen exclusivamente de la
  serie LT2: `2024_22-200`/`201`/`202` (fundaciones y losas), `2024_22-300`
  a `2024_22-305` (muros por elevacion), `2024_22-400` (vigas de fundacion,
  especiales y de planta) y `2024_22-500` (escaleras).
- **Sin OCR**: los PDFs no entregan texto utilizable (0 caracteres) para
  200I/200S/201I/201S/202I/202S/400; los datos se transcriben de los
  dibujos. Solo las elevaciones 300-305 y la h=60/126… de la 501 son
  legibles como texto. Un valor no transcrito NUNCA se infiere: queda en
  `NEEDS_DRAWING_VALUE_CONFIRMATION` (diametro/espaciamiento `None`).
- **Sin tocar el modelo FE**: este paquete no crea nodos, elementos,
  apoyos, diafragmas ni cargas. La armadura se representa en una capa 3D
  separada (barras) y en tablas CSV.
- **Asociacion segura**: una regla se asocia a la geometria LT2 SOLO
  cuando los ejes mencionados existen en la grilla (`grid_x.csv`/`grid_y.csv`:
  A', A, B, C, C', D, D' y 1, 1A, 2, 2A, 3) o se trata de una zona general.
  El eje `1'` (y los 8A/8B, o las losas 01xx) NO existen en la grilla:
  las reglas que los nombran quedan `NEEDS_EXACT_ZONE_MAPPING` y no
  generan barras.
- **Coordenadas nativas**: LT2 se monta en el modelo combinado con sus
  coordenadas nativas (`to_combined` = identidad). A diferencia de LT1
  (que recibe `x+31.25`, `-y`), las barras LT2 se generan directamente
  en `x∈[0,31.475]`, `y∈[0,16.15]` (verificado con `run_combined`).

## 2. Arquitectura

```
COMBINADO/
  src/reinforcement/
    __init__.py                    version del dataset (1.2.0) con LT1+LT2
    reinforcement_types.py         + enums WallOrientation/WallReinforcementClass/
                                   StairPart y dataclasses WallReinforcementRecord/
                                   WallBoundaryBarGroup/WallDistributedReinforcement/
                                   WallLocalReinforcement/StairReinforcementRecord;
                                   BeamRecord.building
    lt2_geometry.py                lectura de LT2/data/unity/edificio_lt2.json
                                   + grid_x.csv/grid_y.csv (geometria LT2)
    lt2_reinforcement_data.py      transcripcion fundaciones 200 y losas 201/202
                                   (mesh/local) + columnas 16 Φ22 (FUENTE)
    lt2_beam_data.py               vigas de planta 400 (especiales y patrón)
    lt2_wall_data.py               elevaciones 300-305 por eje (70 registros)
    lt2_stair_data.py              escaleras 500 por parte/corte
    assign_lt1_reinforcement.py    ZoneResolver (compartido, se reutiliza)
    assign_lt2_reinforcement.py    asignacion LT2 a tags/panos/ejes
    lt2_reinforcement_geometry.py  barras 3D LT2 (solo mallas generales)
    validate_lt2_reinforcement.py  checks + 8 CSVs + invariancia (check_model_rc)
    validate_reinforcement.py      BASELINE_MODEL/check_model_rc compartidos
  tests/
    test_reinforcement_lt2.py      tests rapidos + lento de invarianza
  docs/lt2_reinforcement.md        este documento
  outputs/reinforcement/
    armadura_lt2_reglas.csv             todas las reglas con su resolucion
    armadura_lt2_barras.csv             barras 3D generadas (nativas)
    armadura_lt2_columnas.csv           una fila por columna LT2 (50× 16 Φ22)
    armadura_lt2_vigas.csv              una fila por barra/estribo de viga
    armadura_lt2_vigas_resumen.csv      resumen por referencia (capas/estribos)
    armadura_lt2_muros.csv              registros de muro por elevacion/eje
    armadura_lt2_escaleras.csv          escaleras por parte/corte
    armadura_lt2_necesita_confirmacion.csv  pendientes de confirmacion
```

## 3. Datos (resumen)

- **Columnas**: 50 columnas (tags 3001-3050) `16 Φ22 LONGITUDINAL`,
  estatus `EXACT`, origen `USER_CONFIRMED_DRAWING_DATA`. Sin
  estribos/recubrimiento transcritos -> `geometry_pending=True`
  (no generan barras 3D).
- **Fundaciones (200)**: 200I (inferior) malla general Φ12@20 en ejes
  H y V, traba asociada Φ10@20, cuadrados Φ18@10 (H) / Φ16@10 (V),
  excepcion eje 1' Φ16@10 y esquinas del eje A' Φ22@10; 200S
  (superior) malla general Φ12@20, esquinas del eje A' (Φ18@20 /
  Φ12@10 / Φ16@10) y la zona local "eje D (3 trabas)" Φ16@10.
- **Losa de piso (201)**: 201I mallas generales Φ8@18 (V) / Φ8@24
  (H), excepcion eje 1' Φ8@18 y losas de plano (0112/0113/0116,
  0101) dejadas como no mapeables; 201S franjas de ejes 1/2/A/B/C
  (Φ10@18/Φ10@36/Φ8@36/Φ10@36/Φ10@28), dos ejes laterales a C,
  esquina 3-A' Φ8@18, perímetro 2Φ16 y rectángulo rojo (2Φ16, sin
  zona exacta) entre 1A'-2 sobre el eje A'.
- **Losa 202 (4° piso/cubierta)**: 202I franjas inferiores eje C'
  Φ8@18 y eje 1' Φ10@20, general V Φ8@18, sector H Φ8@36 y sector
  H Φ8@18, resto Φ8@30; 202S generales H Φ8@30 / V Φ10@36, franjas
  de ejes A/B/C' (Φ8@36/Φ10@36/Φ10@20), cruces 2Φ16, perímetro 1Φ16
  y sector Φ8@30.
- **Vigas (400)**: `V.F.20/150.5 [8A-8B]`, `V.F.20/160 [C'-D']`,
  `V.I.15/24 [C'-D']`, `V.30/80 (0102/0102a)` y patrón `V.60/80`
  (pendiente). Las familias especiales tienen `kind=FOUNDATION_BEAM`
  o `SPECIAL` y NUNCA heredan la armadura del patrón V.60/80. Los
  beam_ids no son legibles en el plano -> segmentos con `beam_ids=[]`
  y referencia `physical_bar_id` (`LT2-8A8B-F'-base`, etc.).
- **Muros (300-305)**: 14 ejes de elevacion (1, 1'; 2; 8B, 3, 8A;
  A', A; B', B, E1, C'; D-D', C) × 5 registros = **70**. Parent
  inequívoco solo para A' (M001/M003), 1 (M002) y 3 (M004);
  el resto se registra como `RESOLVED_METADATA`. Todos con
  `geometry_pending=True`.
- **Escaleras (500)**: 12 registros por parte/corte (rampa Φ8@20 TIP,
  longitudinal Φ10@10/Φ10@20, descansos Φ10@10/Φ10@20, soporte 4Φ12,
  borde 2Φ12, detalles PL1/PL2/PL3). Las longitudes del corte C
  (L≈180/455/215) no se extrapolan a otros cortes.

## 4. Convenciones de transcripcion

- "ejes horizontales"/"horiz" -> `Direction.X`; "ejes verticales"/"vert"
  -> `Direction.Y`.
- Reglas de eje/hoja/excepcion dentro de su banda: se conservan como
  reglas separadas (nunca se fusionan con la malla general).
- Zonas con cota "L4-ROOF" o similares sin planaridad confirmada se
  registran como `NEEDS_EXACT_ZONE_MAPPING`.

## 5. Estado actual

| Metrica | Valor |
|---|---|
| Reglas LT2 | 153 |
| Resolucion | RESOLVED 47 · UNRESOLVED 16 · RESOLVED_METADATA 90 |
| Estatus | EXACT 53 · NEEDS_EXACT_ZONE_MAPPING 19 · NEEDS_DRAWING_VALUE_CONFIRMATION 80 · DETAIL_FROM_DRAWING_REQUIRED 1 |
| Asignador | mesh 27/15 · local 4/1 · walls 70 · columns 1 · beams 23 · stairs 12 |
| Barras 3D | 2395 (solo mallas generales resueltas) |
| Validacion | 0 errores / 0 warnings |
| Invarianza FE | `rc=0`, mismo P_total, nodos y apoyos |

## 6. Pendiente (no inventado)

- diámetros en 201S/202S/estribos de vigas sin dato legible;
- anchos de franja/cojines y recubrimientos de columnas;
- beam_ids de las vigas de planta 400;
- coordenadas de barras 3D para columnas/muros/vigas (metadata);
- lecturas de detalle PL1/PL2/PL3 de escaleras.