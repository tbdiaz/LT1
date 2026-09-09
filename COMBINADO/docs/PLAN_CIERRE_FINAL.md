# Plan de cierre final — Modelo combinado LT1 + LT2

## Estado actual (actualizado 2026-09-09)

- **Paso 1 (cargas particionadas): COMPLETADO.** 11 vigas de fachada
  eliminadas ya no reciben carga; su qG se redistribuye a los segmentos
  800201+ con la MISMA densidad (total conservado; 0 warnings).
- **Paso 2 (tributarias): COMPLETADO.** ΣA_trib(JSON) = 686.375 m²/piso
  exacto (verificado). Correccion I'->45.0 m: solo las 12 vigas I-I'
  duplican su tributaria (+6.25 m² eq/piso); la franja restante
  (34.125 m²/piso) conserva los valores de referencia (ver seccion 8bis
  del reporte).
- **Paso 3/4 (cargas + equilibrio): COMPLETADO.** P_total = 31902.275 kN,
  |ΣRz−P|/P = 4.925e-13.
- **Paso 5 (diafragmas): COMPLETADO (verificado, con aclaracion).**
  Los nodos saliente NO son slaves del rigidDiaphragm (decision de
  diseno documentada, ver nota en `_build_diaphragms`); su camino de
  rigidez se cierra POR VIGAS hasta nodos slave/master. Verificacion
  automatica: 0 nodos saliente sin ruta (max 2 saltos de viga).
- **Paso 6 (pendientes): COMPLETADO.** Seccion 12 del reporte.
- **Paso 7 (salidas): COMPLETADO.** Reporte con secciones 8/8bis/11/12/13,
  tributarias_piso_{1-4}.png, vista_3d_combinado.png y
  vista_3d_interactiva.html regenerados.
- **Paso 8 (validacion): COMPLETADO.** 10/10 checks OK seccion 13.
- **Paso 9 (git): PENDIENTE** (solo status/diff; sin add/commit/push).

## Correcciones respecto al plan original

1. El JSON de referencia correcto es
   `PROYECTO_LT1_LT2/outputs/unity/modelo_lt1.json` (108 vigas, **sin**
   vigas saliente). El archivo de otro proyecto LT1 (con salientes 200109+)
   NO es la referencia.
2. Consecuencia: los salientes **NO tienen** losa tributaria en la
   referencia (la nota 2.3 "los salientes SÍ tienen losa" quedaba
   obsoleta). Los segmentos de fachada 800201+ reciben la carga
   redistribuida de las 11 vigas eliminadas; las vigas saliente 800101+
   no soportan carga.
3. La redistribucion conserva la DENSIDAD (w_seg = qG), NO
   w_seg = qG·L_seg/L_tot (la version proporcional-infrarrepresenta).
   El paso 1.2 del plan debe leerse con este criterio.

---

## Estado del modelo (historico, antes del cierre)

- `analyze() rc = 0` (converge)
- 11 warnings `ElementalLoad::setDomain` por vigas particionadas eliminadas
- Error relativo ΣRz vs P_total = 5.28% (1,675 kN) — causas identificadas abajo
- Salientes PISO_1-4 implementados (32 nodos, 30 vigas, 14 particiones)
- I' corregido a X_LT1 = 45.0 m

---

## Paso 1 — Reparar cargas de vigas particionadas

**Problema:** `_build_salientes_lt1()` elimina 11 vigas de fachada originales (tags 200033, 200060, 200063, 200011-14, 200084, 87, 90, 93) y crea segmentos sustitutos (tags 800201+). Pero `apply_loads()` itera sobre `self.json_lt1["beams"]` y aplica cargas a esos tags originales → 11 warnings.

**Solución:** Redistribuir la carga de cada viga eliminada a sus segmentos sustitutos proporcionalmente a la longitud.

### 1.1 Nuevo atributo en `_build_salientes_lt1()`

Al final del método, construir:
```python
self.removed_beams_loads = []  # lista de dicts
```

Para cada partición en `self.facade_partitions`, buscar la viga original en `self.json_lt1["beams"]` por `elementTag`, extraer `carga_lineal_qG_kN_m` y `longitud_m`, y registrar:

```python
{
    "tag_original": hit["elementTag"],
    "qG_kN_m": float(b["carga_lineal_qG_kN_m"]),
    "L_original": float(b["longitud_m"]),
    "segments": [
        {"tag": left_tag, "L": x_lt1 - hit["x1_lt1"]},
        {"tag": right_tag, "L": hit["x2_lt1"] - x_lt1},
    ]
}
```

### 1.2 Modificar `apply_loads()` (línea ~1246)

Antes del loop de cargas LT1, construir un `set` de tags eliminados:
```python
removed_tags = {rb["tag_original"] for rb in self.removed_beams_loads}
```

En el loop, saltar si `b["elementTag"] in removed_tags`.

Después del loop, para cada viga eliminada, aplicar la carga redistribuida:
```python
for rb in self.removed_beams_loads:
    for seg in rb["segments"]:
        w_seg = rb["qG_kN_m"] * seg["L"] / rb["L_original"]
        ops.eleLoad("-ele", seg["tag"], "-type", "-beamUniform", 0.0, -w_seg)
```

Verificar: `Σ(w_seg * L_seg) ≈ qG * L_original` para cada viga.

### 1.3 Impacto en P_total

El P_total se incrementa ligeramente (antes, las 11 vigas eliminadas no llevaban carga en el dominio; ahora sus segmentos sí). La corrección del error de equilibrio 5.28% depende de cuánta carga se recuperó.

**Archivos a modificar:** `src/run_combined.py`
- `_build_salientes_lt1()`: agregar `self.removed_beams_loads`
- `apply_loads()`: skip removed + redistribuir

---

## Paso 2 — Actualizar áreas tributarias

**Principio:** Las áreas tributarias del JSON de referencia se calcularon con I' en X=42.5 m. Con I' corregido a X=45.0 m, los tramos I→I' pasan de 2.5 m a 5.0 m. Las tributarias de los tramos adyacentes (H→I) se alteran.

**Enfoque:** Recalcular tributarias por piso desde la geometría actual del modelo combinado.

### 2.1 Geometría de la losa por piso

Para cada piso (PISO_1: z=-0.05, PISO_2: z=3.91, PISO_3: z=7.87, PISO_4: z=11.83):

- **Ejes X (LT1):** E=0, F=10, G=20, H=30, I=40, I'=45 (corregido)
- **Ejes Y (LT1):** 1: y=0, 2: y=-8.9, 3: y=-16.15
- **Zonas de losa:** La losa modelada se extiende entre los ejes de viga más exteriores en Y
  - Norte: y_LT1 = 0 → Y' = 0
  - Sur: y_LT1 = -16.15 → Y' = 16.15 (fachada)
  - Sur salientes: y_LT1 = -20.32 (PISO_1), -20.27 (PISO_2/3/4), -18.61 (flancos PISO_2/3)
  - **Nota:** Los salientes SÍ tienen losa (tienen `area_tributaria_m2 > 0` en la referencia)

### 2.2 Cálculo de tributarias

Para cada viga de fachada particionada (800201+):
- Longitud del segmento
- Tributaria = `qG * L / (q_losa)` donde q_losa = PP.LOSA + PP.ADIC (del JSON)
- Verificar que la suma de tributarias = área de losa

### 2.3 Salientes

Los salientes no cambian de geometría (ya están correctos). Sus áreas tributarias del JSON de referencia se conservan (no se alteran por la corrección I').

### 2.4 Verificación

```python
# Para cada piso
A_losa = (x_I' - x_E) * (y_1 - y_3) + area_salientes
A_trib_sum = sum(beam.area_tributaria for beams at this piso)
error = abs(A_trib_sum - A_losa) / A_losa
```

**Archivos a modificar:** `src/run_combined.py`
- Nuevo método `compute_tributary_areas()` o sección en `validate()`
- Output: tabla por piso

---

## Paso 3 — Actualizar cargas gravitacionales

Con las tributarias recalculadas, actualizar q_G por viga:
```
q_G = (area_tributaria * q_losa) / L
```

Donde q_losa = 7.4531 kPakN/m² (del JSON de referencia: promedio de PP.LOSA + PP.ADIC).

**Enfoque práctico:** Las cargas del JSON de referencia ya representan q_G correctas para la geometría original (I'=42.5). La corrección I' solo afecta:
- Tramos H→I (se acortan de 10 m a 10 m... no cambian en H→I)
- Tramos I→I' (se alargan de 2.5 m a 5.0 m)
- La tributaria de I→I' se duplica (5.0/2.5 = 2x)

**Acción:** Actualizar q_G de los tramos I→I' para reflejar la geometría corregida. El resto de vigas se mantiene con los q_G del JSON.

**Archivos a modificar:** `src/run_combined.py`

---

## Paso 4 — Equilibrio global

### 4.1 Ejecutar análisis
```python
b.run_analysis()  # rc = 0 esperado
```

### 4.2 Verificar equilibrio
```python
ops.reactions()
R_total = sum(ops.nodeReaction(t, 3) for t in b.support_tags)
error = abs(R_total - P_total) / P_total
```

### 4.3 Reportar por piso
Para cada piso, calcular:
- Área de losa
- Suma de áreas tributarias
- Carga gravitacional
- Error de conservación

**Archivos a modificar:** `src/run_combined.py` → `validate()` o nuevo método

---

## Paso 5 — Diafragmas y conectividad

### 5.1 Verificación
Los salientes ya están incluidos en los rigidDiaphragm (se agregan al set de nodos por nivel en `_build_diaphragms_and_links()`). Verificar:

```python
for nivel in ("PISO_1", "PISO_2", "PISO_3", "PISO_4"):
    # Todos los nodos saliente del nivel son slaves del diaphragm
    for tag in b.saliente_nodes:
        if z matches nivel:
            assert tag in slaves_of_level
```

### 5.2 Ausencia de restricciones duplicadas
Verificar que ningún nodo saliente tiene fix duplicado ni rigidLink redundante.

### 5.3 Documentar excepciones
Los nodos de saliente en y=-20.xx (borde exterior) no están en la fachada y no son muros → son slaves normales del diaphragm. Correcto.

**Archivos a modificar:** Solo verificación (sin cambios de código a menos que se encuentre error)

---

## Paso 6 — Elementos pendientes (sin cambios)

Documentar como pendientes (NO inventar):
- P.M. (columna 300x300x20)
- P.M.I.
- V.M. (viga metálica)
- V.60/VAR (sección variable)
- V.60-30/80-40
- Núcleo PISO_4
- Muros subterráneo
- Zonas sin plano de detalle

---

## Paso 7 — Actualizar salidas

### 7.1 Figure 3D estática
Regenerar `outputs/vista_3d_combinado.png` con los salientes.

### 7.2 Figura interactiva
Regenerar `outputs/modelo_interactivo.html` con Plotly.js (datos actualizados del modelo).

### 7.3 Vistas por piso (tributarias)
Crear directorio `outputs/tributarias_lt1/` con 4 imágenes:
- `tributarias_piso_1.png`
- `tributarias_piso_2.png`
- `tributarias_piso_3.png`
- `tributarias_piso_4.png`

Cada imagen muestra: vigas, salientes, zonas tributarias, tags, áreas.

### 7.4 Reporte de validación
Actualizar `outputs/reporte_validacion_combinado.md` con:
- Sección de cargas reparadas
- Tabla de tributarias por piso
- Equilibrio global
- LT2 intacto
- Pendientes

---

## Paso 8 — Validación final

Checks automáticos:
1. `analyze() rc = 0`
2. 0 warnings `ElementalLoad::setDomain`
3. 0 elementos longitud cero
4. 0 vigas con ΔZ ≠ 0
5. 0 columnas con desplazamiento horizontal
6. 0 diagonales en planta (salientes)
7. 0 nodos saliente sin conectividad
8. LT2: 237 vigas, mismos tags, sin cambios
9. I' = 76.25 m en combinado (= 45.0 + 31.25)
10. Error equilibrio < tolerancia

---

## Paso 9 — Git status

```bash
git status
git diff --stat
```

NO ejecutar git add/commit/push.

---

## Archivos a modificar

| Archivo | Cambios |
|---|---|
| `src/run_combined.py` | Load redistribution, tributarias, equilibrio, outputs |

## Archivos a generar

| Archivo | Descripción |
|---|---|
| `outputs/tributarias_lt1/tributarias_piso_{1-4}.png` | Vistas tributarias |
| `outputs/vista_3d_combinado.png` | Figura 3D actualizada |
| `outputs/modelo_interactivo.html` | Figura interactiva |
| `outputs/reporte_validacion_combinado.md` | Reporte actualizado |
