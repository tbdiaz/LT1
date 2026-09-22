# Auditoría de cargas tributarias de las conexiones V30

Se comparó el reparto de losa LT2 publicado con el mismo algoritmo de
`LT2/src/tributary_areas.py` (malla de 0,05 m y bordes resistentes), agregando
solo para el cálculo los tramos 9011–9020 de
`COMBINADO/data/conexiones_v30_lt2.csv`. El reparto original se reprodujo
contra `LT2/data/loads/tributary_areas_LT2.csv` con diferencia máxima menor
que 0,02 m² por receptor, atribuible a celdas de borde. No se cambiaron los
archivos de cargas LT2 ni se aplicó un caso nuevo en OpenSees.

## Hallazgo

En cada piso L1–L4, los dos tramos nuevos reciben aproximadamente 2,24510 y
2,24803 m² de losa, respectivamente. Con el valor existente
`qG = 6,0822 kN/m²`, corresponden 13,65517 y 13,67294 kN por piso. No es
carga adicional al edificio: se desplaza un total de **27,32812 kN por piso**
desde las cuatro vigas V40 adyacentes hacia los dos tramos V30. La suma de
cargas de cada piso permanece inalterada (diferencia numérica < 1e-8 kN).

| V40 original por piso | Variación G [kN] |
| --- | ---: |
| V40_01 | -6,63774 |
| V40_02 | -7,01744 |
| V40_03 | -7,03520 |
| V40_04 | -6,63774 |

Los 16 paños afectados son los cuatro del borde occidental de cada piso.
Ocho de ellos tienen estado `PENDING_VISUAL_CONFIRMATION` en el dataset LT2;
por tanto las cifras son una **estimación condicionada a esa geometría de
losa**, no una carga aprobada por lectura independiente de los planos.

Los tramos de ROOF (9019 y 9020) no reciben área de losa en el esquema
tributario vigente: la cubierta y su carga lineal están marcadas como
pendientes de aplicación en los datos LT2. No se les asignó carga supuesta.

## Estado del modelo

La redistribución se cerró en el modelo COMBINADO mediante
`COMBINADO/data/redistribucion_tributaria_v30_lt2.csv`. Para G y Q se agrega
la carga equivalente a 9011–9018 y se descarga, con signo opuesto, de las V40
2097–2112. La suma de `delta_area_m2` y de carga es cero en cada nivel; por
ello no cambia el peso global. ROOF permanece sin carga de losa documentada.

Las correcciones se aplican como `beamUniform` firmadas sobre la distribución
LT2 preexistente. Unity exporta las 24 filas de corrección y agrega sus áreas
por `elementTag`. Ocho paños conservan la marca histórica
`PENDING_VISUAL_CONFIRMATION`; la redistribución usa la geometría de paños
vigente y aprobada para cerrar esta entrega, sin afirmar una lectura
independiente adicional del plano. La auditoría se reproduce con
`python COMBINADO/src/auditar_tributarias_v30.py`.
