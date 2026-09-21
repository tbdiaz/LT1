# Armadura LT1 - Dataset y representacion

Modulo que incorpora al proyecto COMBINADO la **armadura levantada de los
planos LT1** como capa de datos y representacion, **sin modificar** el
modelo estructural combinado (que sigue dando `rc=0` con los mismos
resultados).

---

## 1. Alcance y principios

- **Solo datos**: las reglas de armadura provienen exclusivamente de la
  serie de planos LT1 `2017_67-*` (fundaciones 200, losas 201-205, muros
  300, vigas 400, escaleras 500).
- **Sin reinterpretacion**: la nomenclatura de los planos se conserva
  textual (ej. `E + 6T B10@10`, `D.M.V B10@12`); no se inventa su
  significado.
- **Sin tocar el modelo FE**: este paquete no crea nodos, elementos,
  apoyos, diafragmas ni cargas en OpenSeesPy. La armadura se representa
  en una capa 3D separada (barras graficas) y en tablas CSV.
- **Asociacion segura**: una regla se asocia a la geometria del modelo LT1
  SOLO cuando los ejes mencionados existen en `modelo_lt1.json` (eje_x:
  E, F, G, H, I, I'; eje_y: 1, 2, 3) o se trata de una zona general/tipo.
  En caso contrario la regla queda en el reporte como pendiente
  (`NEEDS_EXACT_ZONE_MAPPING`) y NO genera barras.

## 2. Arquitectura

```
COMBINADO/
  src/reinforcement/
    __init__.py                   unificacion y version del dataset
    reinforcement_types.py        enums Status/Layer/Direction/Classification
                                  y dataclasses MeshRule/LocalBarRule/WallRule/
                                  BeamRule/StairRule/BeamRebarSegment/
                                  BeamStirrupZone/BeamRecord con "to_dict"
    lt1_reinforcement_data.py     transcripcion fiel de los planos (FUENTE)
    lt1_wall_data.py              armadura ESPECIFICA de muros LT1 por
                                  elevacion/eje/nivel (planos 300-303)
    lt1_beam_data.py              armadura longitudinal de VIGAS por beam_id
                                  (planos 400/401/402); referencias TP1/TP4
    lt1_geometry.py               lectura de outputs/unity/modelo_lt1.json
                                  (ejes, nodos, panos, muros, vigas)
    assign_lt1_reinforcement.py   resolucion zona->rectangulo (ZoneResolver)
                                  y asignacion a panos/tags (assigner)
    reinforcement_geometry.py     generacion de barras 3D (BarLayer) con
                                  cover parametrizable
    validate_reinforcement.py     checks de datos + invariancia del modelo
  tests/
    test_reinforcement.py         tests rapidos + lento de invarianza
    test_reinforcement_walls_lt1.py  tests de la correccion de muros 300-303
  docs/lt1_reinforcement.md       este documento
  outputs/reinforcement/
    armadura_lt1_reglas.csv       todas las reglas con su resolucion
    armadura_lt1_barras.csv       barras 3D generadas (sistema combinado)
    armadura_lt1_columnas.csv     una fila por columna LT1 (16 B22)
    armadura_lt1_muros.csv        una fila por registro especifico de muro
                                  (elevaciones 300-303)
    armadura_lt1_necesita_confirmacion.csv  muros con valores a confirmar
    armadura_lt1_vigas.csv        una fila por barra/estribo de viga
    armadura_lt1_vigas_resumen.csv   resumen por beam_id (capas F, estribos)
    armadura_lt1_vigas_exact.csv     lista EXACT (leida del plano)
    armadura_lt1_vigas_necesita_confirmacion.csv  lista pendiente
```

## 3. Datos (resumen)

| Serie | Contenido | Estado |
|-------|-----------|--------|
| 200 | malla inferior/superior de fundacion (200-I/200-S) | EXACT / NEEDS_ZONE |
| 201 | losa cielo 1° subterraneo (superior = inferior) | EXACT / needs |
| 202 | losa cielo 1° piso (202-S sup / 202-I inf) | EXACT / needs |
| 203 | losa cielo 2° piso (inf/sup) | EXACT / needs |
| 204 | losa cielo 3° piso (inf/sup) | EXACT / needs |
| 205 | losa cielo 4° piso (inf/sup) | EXACT / needs |
| 300 | muros: armadura especifica por elevacion/eje/nivel (300-303), 165 registros | 164 NEEDS_DRAWING_VALUE_CONFIRMATION; 1 DETAIL_FROM_DRAWING_REQUIRED |
| COL | columnas LT1: 16 B22 longitudinales (1 regla) | EXACT / RESOLVED |
| 400 | vigas: familia representativa V.80/80 (2 reglas) | SUPERSEDED_BY_EXACT_BEAM_DRAWINGS |
| 500 | escaleras (2 reglas de metadata) | DETAIL_FROM_DRAWING |

Conteo total de reglas: **283** (95 mesh + 17 local + 165 muros por
elevacion + 1 muro superseded historico + 1 column + 2 beams + 2 stairs).

Las **columnas LT1** (90, todas seccion `P. 70x70`) reciben el dato
confirmado por el usuario **16 B22 longitudinales** (`ColumnReinforcementRule`,
bar_type=LONGITUDINAL, status=EXACT, source=USER_CONFIRMED_DRAWING_DATA).
La asociacion a los 90 elementTags es inequivoca (seccion unica) y queda
**RESOLVED**; la geometria 3D de las 16 barras queda **pendiente**
(`geometry_pending=True`) porque no se definen recubrimiento ni
distribucion transversal. No se inventan estribos.

Además, el dataset de **vigas reales por beam_id** (`lt1_beam_data.py`)
contiene 48 beam_ids de los planos 400/401/402 (16+18+14), 50 segmentos
longitudinales, 7 zonas de estribos y la **sección escalonada especial**
del plano 402 (`SECC_402`) con su detalle propio.

### Estados (Status)
- `EXACT` - zona del plano mapeada sin ambiguedad a la grilla del modelo.
- `SUPERSEDED_BY_EXACT_BEAM_DRAWINGS` - reglas de viga REPRESENTATIVE que
  quedan como referencia historica, reemplazadas por la armadura EXACTA
  por beam_id de los planos 400/401/402 (`lt1_beam_data.py`).
- `SUPERSEDED_BY_EXACT_WALL_ELEVATIONS` - el patron tipico de muros
  (antiguo `TYPICAL`) queda como referencia historica, reemplazado por los
  registros especificos de las elevaciones 300-303 (`lt1_wall_data.py`).
  La regla NO se asigna a geometria (bucket `superseded`).
- `NEEDS_EXACT_ZONE_MAPPING` - la zona menciona ejes fuera de la grilla
  LT1 (IB, H1-H2, 1BB, 1C, 8, Ga, J, 2a, 1'' y losas 111/219-221/313-315/
  322/324/404/415-416/426).
- `NEEDS_NOTATION_CONFIRMATION` - nomenclatura que parece estribo (viga/
  eje 1, viga/eje 3, Φ16@14 + Φ12@12 en 200-S). No reinterpretada.
- `NEEDS_DRAWING_VALUE_CONFIRMATION` - dato del plano no legible o no
  asociable sin ambiguedad; NO se rellena por inferencia. Es el estado de
  todos los registros de muro 300-303 (las cifras no son texto en el PDF).
- `DETAIL_FROM_DRAWING_REQUIRED` - escaleras y el detalle `CORTE A` del
  plano 300.

### Resolucion de zonas (asignacion, corrida de cierre)
```
mesh : resolved 61 | unresolved 34
local: resolved 15 | unresolved  2
walls: metadata 165 (RESOLVED_METADATA por elevacion; 0 elementTags FE) |
       superseded 1 (regla tipica historica, sin geometria)
cols : resolved  1 (RESOLVED, 90 tags, geometry_pending) | unresolved 0
beams: resolved  2 (RESOLVED_METADATA, SUPERSEDED) | unresolved 0
stairs: resolved 0 | unresolved 2 (DETAIL_FROM_DRAWING_REQUIRED)
```

### Muros: correccion final por elevaciones 300-303
Antes: una regla tipica unica "E + 6T B10@10 ; M.H.A e=20 ; D.M.V B10@12 ;
D.M.V B10@20" para TODOS los muros. Correccion: se contesta "solo
muestran un muro típico" con la armadura ESPECIFICA por muro:

- **Plano 300** (elevacion longitudinal principal, ejes `E',E,F',F,G,H,
  I',I,J`): 82 registros. Cuatro clases por eje sobre PISO_1S..CUBIERTA
  (BOUNDARY, DISTRIBUTED_VERTICAL, DISTRIBUTED_HORIZONTAL, LOCAL),
  STARTER desde FUNDACION_SUP..PISO_1S y LAP por cada frontera de nivel
  (PISO_1S-PISO_1 ... PISO_3-PISO_4) para preservar cambios por piso.
  Incluye `CORTE A` como DETAIL_FROM_DRAWING_REQUIRED.
- **Plano 301** (elevaciones 1'', 1A, 1C, 1b, 1AA, 1BB): 32 registros.
  1'' es multi-piso con cambios de armadura a lo largo de la altura
  (tramos por nivel + LAP). `1A` y `1BB` son de geometria
  inclinada/variable: `geometry_special=True`, classification
  SPECIAL_GEOMETRY, JAMAS se copia armadura de un muro vertical. `1b`
  es el muro longitudinal del nivel inferior (marcador 1°S). Las
  anotaciones legibles V.F. 15/225, V. 15/125, V. 15/VAR, V. 20/80 se
  conservan como transcripcion literal sin asignacion de ubicacion.
- **Plano 302** (elevacion completa, familia independiente): 6 registros
  (BOUNDARY, DIST_VERT, DIST_HORIZ, LOCAL, STARTER, LAP); sin ejes/niveles
  legibles en el PDF.
- **Plano 303** (elevacion larga, mismos ejes que 300): 45 registros
  (5 clases por eje); niveles no legibles -> tramos por confirmar.

Los valores (cantidad/diametro/espaciamiento/longitud/anclaje) NO son
texto en los PDFs (son trazos de dibujo): por regla del proyecto quedan
`None` con `status=NEEDS_DRAWING_VALUE_CONFIRMATION` y
`geometry_pending=True`. **No se inventa ningun valor, no se inventan
recubrimientos ni configuraciones transversales** (no hay barras 3D de
muro). La correspondencia eje->elementTag FE del modelo no es inequivoca
(la elevacion se desarrolla en E'..J; el modelo LT1 actual modela 6
paneles de nucleo en 5 tramos de altura, 30 elementos FE), por lo que
`element_tags` quedan VACIOS. `RESOLVED_METADATA` identifica la lamina
y zona del registro, no una asignacion fisica a esos 30 elementos.
La lista `armadura_lt1_necesita_confirmacion.csv` enumera los 165
registros con lo que falta confirmar en pliego.

### Vigas reales (planos 400/401/402)
- La armadura por beam_id se transcribe en `lt1_beam_data.py` con
  `BeamRebarSegment`/`BeamStirrupZone`/`BeamRecord` y se detalla en
  `COMBINADO/outputs/reinforcement/armadura_lt1_vigas*.csv`.
- Una barra que cruza un apoyo (conjuntos 3-2-1) se mantiene como UN
  segmento con `continuity_across_support=True` y NO se corta en el
  elementTag.
- Estribos `ED` (doble B10); cuando el plano solo referencia `TP.1`/
  `TP.4` del plano 002 se guarda `detail_reference` y NO se inventa la
  distribucion.
- Las vigas de fundacion `VF1-VF3` son categoria `FOUNDATION_BEAM` (B18
  predominante, varias capas); la seccion escalonada especial del plano
  402 se asocia unicamente a su elemento correspondiente, NO a V60/80.
- Valores ilegibles o no asociables quedan en
  `NEEDS_DRAWING_VALUE_CONFIRMATION` y en la lista
  `armadura_lt1_vigas_necesita_confirmacion.csv`.

### Niveles de losa (mapeo plano -> modelo, **TENTATIVO**)
| Plano | Titulo | Nivel modelo |
|-------|--------|--------------|
| 200-I / 200-S | fundaciones | FUNDACION_SUP |
| 201 | cielo 1° sub | PISO_1 |
| 202-S / 202-I | cielo 1° piso | PISO_1 |
| 203 | cielo 2° piso | PISO_2 |
| 204 | cielo 3° piso | PISO_3 |
| 205 | cielo 4° piso | PISO_4 |

> **Pendiente de confirmacion**: la correspondencia de cotas entre los
> planos y los niveles del modelo (FLOOR_TO_LEVEL) se asume por nombre.
> Antes de usar las cotas Z de las barras para calculos, revisar contra
> la cota real de cada plano (`FLOOR_TO_LEVEL_UNCONFIRMED`).

## 4. Invarianza estructural

El analisis combinado se re-ejecuta con la armadura cargada:

```
rc            = 0
P_total       = 31086.259667 kN   (igual al baseline)
sum Rz        = 31086.259667 kN   (|errz_rel| < 1e-12)
nodos fisicos = 485
apoyos        = 53
```

Verificado por `test_combined_model_invariante` (marcado `slow`) y
`test_baseline_consistente_con_runner`.

## 5. Representacion 3D (capa separada)

- `ReinforcementGeometryBuilder` genera `BarLayer` a partir de las reglas
  RESOLVED.
- Coordenadas en el **sistema combinado** (x' = x_lt1 + 31.25, y' = -y_lt1),
  salida en `outputs/data/armadura_lt1_barras.csv`.
- `cover_cm`: recubrimiento de la malla respecto al borde de la losa.
  Hasta ser confirmado, se usa `cover_cm=None`, las barras se colocan en
  el plano medio de la losa y se marca `z_approximation=True`.
- Franjas sobre ejes (BAND) se dibujan sobre la linea del eje; **el ancho
  de la franja se toma del plano**, no se infiere.
- Las reglas `NEEDS_EXACT_ZONE_MAPPING`, locales sin ejes, vigas
  SUPERSEDED/REPRESENTATIVE y escaleras NO generan barras.
- Las barras de viga (`BeamRebarSegment`) NO generan geometria 3D hasta
  que su eje fisico este verificado en el modelo (evita posicionar
  barras en el eje centroidal con apariencia de posicion real).

## 6. Como ejecutar

```bash
# tests rapidos (dataset + asignacion + barras + vigas)
python -m pytest -c COMBINADO/pytest.ini COMBINADO/tests/test_reinforcement.py -m "not slow"

# re-ejecucion del modelo combinado completo (lento, valida invarianza)
python -m pytest -c COMBINADO/pytest.ini COMBINADO/tests/test_reinforcement.py -m slow

# regenerar CSV de reglas, barras y vigas
python -c "import sys; sys.path.insert(0,'COMBINADO/src'); from reinforcement.validate_reinforcement import write_outputs; print(write_outputs(__import__('pathlib').Path('COMBINADO/outputs/reinforcement')))"
```

## 7. Decisiones registradas

1. Los **planos 202-S/202-I** cubren capa superior e inferior de la misma
   losa; el modelo tiene un pano por nivel, por lo que ambas columnas de
   la tabla apuntan al mismo nivel PISO_1.
2. Las firmas **"viga/eje 1"** y **"viga/eje 3"** del plano 204 se
   clasifican como STIRRUP / NEEDS_NOTATION_CONFIRMATION (parecen
   estribos, no malla); se conserva la lectura literal.
3. **Muro**: correccion final - se abandona la familia tipica unica
   (`SUPERSEDED_BY_EXACT_WALL_ELEVATIONS`, conservada como referencia
   historica en el bucket `superseded`, sin geometria) y se registra la
   armadura ESPECIFICA por elevacion/eje/nivel de los planos 300-303
   (`lt1_wall_data.py`, 165 registros). Los valores de barra no legibles
   quedan `None`/NEEDS_DRAWING_VALUE_CONFIRMATION; los muros inclinados
   (1A, 1BB) se marcan `geometry_special`; no se inventan recubrimientos,
   configuraciones ni correspondencias eje->tag FE.
4. **Vigas (serie 400)**: la transcripcion inicial REPRESENTATIVE queda
   marcada `SUPERSEDED_BY_EXACT_BEAM_DRAWINGS`; la armadura exacta por
   beam_id se registra en `lt1_beam_data.py` a partir de los planos
   400/401/402 (V0101, V0102, V100-V109, V111-V114, V200-V211, V300-V306,
   V400-V406, VF1-VF3 y seccion escalonada SECC_402). No se cortan barras
   en apoyos ni se inventan valores ilegibles (`NEEDS_DRAWING_VALUE_CONFIRMATION`).
5. **Escaleras**: sin elementos estructurales de escalera en el modelo
   LT1 -> no se muestra armadura; se exige detalle del dibujo.
6. La **asignacion por zona** se hace con la grilla de ejes del JSON de
   unity LT1 (nativos); el resultado geometrico se convierte a coordenadas
   combinadas solo al emitir barras.

## 8. Trazabilidad de una regla ejemplo

Regla `LT1:201:04` (plano 2017_67-201-Model):
```
floor      = LOSA CIELO 1° SUBTERRANEO
layer      = both
direction  = both
zone       = E-F/1-2  -> rect (0.00..10.00) x (-8.90..0.00) LT1 nativo
diameter   = 8 mm | spacing = 18 cm
pano_ids   = PISO_1_P11
status     = EXACT
resolution = RESOLVED
```

Salidas CSV incluyen estas columnas para cada regla, permitiendo
verificacion independiente de la lectura.
