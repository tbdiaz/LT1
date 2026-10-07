# Honors Track — Semana 7

Fecha de implementación: 2026-10-06

Proyecto: modelo combinado LT1 + LT2, con demostración Android en Samsung
Galaxy A05 sin ARCore.

## Condición previa: núcleo

El Honors se presenta solamente después del núcleo de Semana 6. La evidencia
del núcleo, sus errores conocidos y la QA estructural están en
`reports/semana06.md`. Esta extensión no cambia cámara, detector, anchor,
transformación, `elementTag 800205` ni los valores estructurales exportados.

## Extensión implementada: H3 — AR estructural avanzada

Después de confirmar la viga durante seis frames compatibles, la aplicación
mantiene el elemento 800205 registrado sobre la viga real y habilita tres
capas interactivas:

1. **Diagrama My de COMBO_R.** Se reconstruye en 65 estaciones con las fuerzas
   reales de extremo y las cargas distribuidas reales G+Q:

   `My(x) = My_i + Vz_i·x + q·x²/2`

   con la convención de sección `i=-F_i`, `j=+F_j`. Para el 800205:

   - `My_i = +186.461847 kN·m`;
   - `Vz_i = -123.109764 kN`;
   - `q = 16.770291 + 9.243750 = 26.014041 kN/m`;
   - `L = 7.49 m`;
   - extremo reconstruido `My_j = -5.935136 kN·m`;
   - cierre respecto del resultado OpenSees exportado: menor que `1×10⁻⁹
     kN·m`.

   No se afirma disponer de estaciones OpenSees internas: la parábola se
   obtiene por equilibrio exacto para las cargas uniformes exportadas.

2. **Deformada nodal ×100.** Superpone en magenta los desplazamientos
   `COMBO_R` de los nodos I y J, transformados con la misma convención
   OpenSees→Unity. Entre ambos nodos se muestra interpolación lineal; no se
   presenta como curvatura interna calculada.

3. **Área tributaria equivalente.** Dibuja una banda amarilla de área
   `17.308922 m²`. Su ancho se calcula como `A/L = 2.310938 m`, por lo que la
   representación conserva exactamente el área exportada. Es una banda
   equivalente registrada al elemento, no un polígono levantado desde el
   edificio real.

Las capas se encienden y apagan con los botones `DIAGRAMA My`,
`DEFORMADA ×100` y `ÁREA TRIBUTARIA`. El panel mantiene visibles el tag, las
fuerzas, desplazamientos, cargas y el estado `P-M: PENDIENTE`.

## Procedimiento de demostración

1. Ejecutar la escena `Assets/Scenes/MarkerStructuralDemo.unity` en el A05.
2. Apuntar a una viga horizontal de hormigón hasta ver `VIGA DETECTADA`.
3. Verificar que el contorno verde coincida con la región detectada.
4. Activar `DIAGRAMA My` y explicar fuerzas de extremo, carga y cierre.
5. Activar `DEFORMADA ×100` y explicar que solo se dispone de desplazamientos
   nodales para el extracto Android.
6. Activar `ÁREA TRIBUTARIA` y explicar la equivalencia `A/L`.
7. Desactivar cada capa para demostrar interacción, manteniendo el mismo
   anchor y `elementTag 800205`.
8. Mostrar que demanda/capacidad continúa pendiente y explicar que no se
   inventó armadura para este elemento.

## Estado respecto de H1–H5

| Objetivo | Estado verificable | Evaluación prudente |
| --- | --- | --- |
| H1 — Cardboard VR | No implementado. | 0 |
| H2 — AR avanzada | Anchor visual con seis frames, suavizado, retención de 1 s y límites de error operativos. No hay múltiples markers, pose métrica ni persistencia mundial. | Parcial |
| H3 — AR estructural avanzada | Diagrama My, deformada nodal y área tributaria interactivos sobre el elemento físico detectado. Falta selección de varios elementos y P-M del 800205. | Funcional en condiciones controladas |
| H4 — Reanálisis OpenSees en vivo | No implementado; el laboratorio de escenarios del visor declara correctamente `REQUIERE REANÁLISIS`. | 0 |
| H5 — Capacidad avanzada | Existen P-M uniaxiales auditadas para columna y muro en el visor general, pero no una extensión avanzada nueva de Semana 7. | No reclamar Honors |

La asignación definitiva de puntos corresponde al profesor. Este documento no
presenta funcionalidades parciales como si cumplieran un objetivo completo.

## Verificación reproducible

```powershell
pytest -q COMBINADO/tests/test_semana06_ar.py
pytest -q COMBINADO/tests/test_semana07_honors.py
pytest -q COMBINADO/tests
```

Las pruebas Honors verifican:

- cierre del diagrama contra `My2` real;
- conservación del área tributaria;
- presencia de las tres capas interactivas;
- permanencia explícita de `P-M: PENDIENTE`.

## Limitaciones conocidas

- La referencia espacial continúa siendo visual y relativa a la cámara; no es
  una pose 6D métrica ni un anchor persistente de ARCore.
- Solo se registra y selecciona el elemento 800205 en esta demo liviana.
- La deformada entre extremos es una interpolación de desplazamientos nodales.
- El área tributaria es una banda equivalente, porque el extracto LT1 no
  contiene el polígono real.
- No existe una curva de capacidad verificable para el 800205; falta armadura
  asociada inequívocamente al elemento.

