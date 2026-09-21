# Auditoría de enfierradura LT1 — 19-09-2026

## Alcance y fuentes

Se revisó el dataset de armadura LT1 y se inspeccionaron visualmente láminas de la serie **2017_67**: detalles típicos de muros [001](<../planos armadura/2017_67-001-Model.pdf>), malla inferior de fundaciones [200-I](<../planos armadura/2017_67-200-I-Model.pdf>), malla inferior/superior de losa de cuarto piso [205](<../planos armadura/2017_67-205-Model.pdf>) y armadura de vigas [400](<../planos armadura/2017_67-400-Model.pdf>), [401](<../planos armadura/2017_67-401 (2)-Model.pdf>) y [402](<../planos armadura/2017_67-402 (1)-Model.pdf>). Las elevaciones específicas de muro 300–303 están en [planos](../../planos/), no en `planos armadura`. Los archivos `2024_22-*` corresponden a LT2 y no se usaron para asignar armadura LT1.

Esta es una comprobación **dirigida**, no una transcripción numérica independiente de todas las marcas y cotas de las trece láminas de armadura. Se contrastó el alcance de las láminas con el dataset, se ejecutaron sus validadores y se comprobó la asignación a la geometría actual. Una validación de software sin errores no equivale a certificar que cada cuantía o detalle coincide con el dibujo.

## Hallazgos comprobados

| Componente | Registro actual | Verificación / límite |
| --- | --- | --- |
| Columnas | 90 columnas LT1 `P. 70x70`; regla longitudinal `16 B22` aplicada a los 90 `elementTags` | El dato está registrado como **confirmado previamente por el usuario**, no como lectura independiente de la lámina 001. Faltan recubrimiento, distribución transversal y estribos; no hay geometría 3D de esas barras. |
| Muros | 165 registros por elevaciones 300–303: 82 + 32 + 6 + 45 | Son metadatos por lámina/eje/nivel. **Ninguno** tiene asignado `elementTag` FE. Hay 30 elementos de muro del núcleo actual (6 paneles × 5 tramos); no se debe copiar una regla típica a todos. 164 registros requieren confirmar valores del dibujo y 1 requiere detalle del dibujo. |
| Vigas | 48 identificadores de viga y una sección especial; 50 tramos longitudinales y 7 zonas de estribos | Las láminas 400–402 contienen detalles variables por viga. Hay 12 registros de viga con estado `EXACT` y 37 pendientes de confirmar; los registros aún **no** están vinculados a `elementTags` FE. `EXACT` indica transcripción interna, no comparación física completa ni mapeo a una barra del modelo. |
| Mallas y armadura local | 95 reglas de malla y 17 locales | 61 mallas y 15 reglas locales tienen zona resuelta; 34 y 2, respectivamente, siguen sin correspondencia espacial exacta. La lámina 205 distingue malla inferior y superior: no se deben fusionar. |
| Capacidad P–M | Curvas para columna 113022 y muro M001 | La curva de columna usa disposición simétrica y recubrimiento de 4 cm asumidos en el cálculo; la de muro también contiene hipótesis de armadura. **No** deben presentarse como capacidad verificada contra el despiece de enfierradura hasta confirmar esos detalles. |

El validador del dataset devolvió `errors=[]` y `warnings=[]` para las reglas; eso comprueba consistencia informática, no lectura exhaustiva de las láminas. El total es 283 reglas, de las cuales 64 llevan estado `EXACT`; los estados restantes incluyen 164 registros de muro con valores por confirmar y 45 reglas sin mapeo exacto de zona. La etiqueta `RESOLVED_METADATA` de muros no significa armadura resuelta en el modelo estructural.

## Continuación de la geometría

El núcleo LT1 ya tiene seis paneles continuos en cinco tramos de altura. Queda pendiente contrastar y, en su caso, incorporar otros muros del perímetro y validar ubicación/sección de todas las vigas y columnas contra sus plantas y elevaciones. No se agregó geometría ni enfierradura nueva durante esta auditoría: la correspondencia de ejes, cotas y detalles de barras todavía no es inequívoca. Hacerlo por alineación visual o repetir una regla típica contravendría las reglas del proyecto.

## Cambio del visor

El material base de las columnas del visor Unity pasó de naranja a verde. El resaltado amarillo al seleccionar un elemento se mantiene y, al deseleccionarlo, vuelve a verde. No se alteraron sección, material estructural, cargas ni resultados OpenSees.

## Para cerrar la verificación

1. Leer y registrar de forma verificable las marcas numéricas, recubrimientos, estribos y disposición de barras de las láminas de columnas y muros pertinentes; identificar la lámina exacta que sustenta `16 B22`.
2. Establecer una tabla explícita `lámina/eje/nivel/beam_id ↔ elementTag` con cotas comprobadas, antes de asignar armadura de muros y vigas o recalcular su capacidad.
3. Revisar en Unity el color verde con el proyecto abierto; la prueba automatizada disponible es estática y no sustituye la comprobación visual en el Editor.
