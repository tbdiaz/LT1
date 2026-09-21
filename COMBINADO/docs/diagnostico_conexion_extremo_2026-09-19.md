# Diagnóstico de vigas y muros en el extremo del modelo combinado

> **Actualización:** los diez `elementTags` facilitados después por el usuario
> permitieron identificar y completar las vigas V30x80. La sección histórica
> «Decisión y dato necesario» describe el estado anterior a recibirlos.

## Qué muestra el modelo actual

La imagen del visor no incluye un `elementTag` seleccionado, por lo que no permite identificar inequívocamente **cuáles** vigas señala. Se revisaron las plantas estructurales LT1 [102](../../planos/2017_67-102-Model.pdf) y LT2 [101](../../LT2/2024_22-101-Model.pdf) y [102](../../LT2/2024_22-102-Model.pdf), y la conectividad del JSON combinado que utiliza Unity.

- La cadena de borde del extremo LT2 en `x=0.400 m` **ya está conectada** al muro de eje `x=0.100 m` por diez elementos cortos `conector_v40_muro` (tags 9001–9010): dos en cada nivel L1, L2, L3, L4 y ROOF. La separación centroide–cara es 0.300 m, no un extremo libre.
- En cambio, las diez verticales de `vertical_caja` (50 elementos entre B1 y ROOF) tienen nodos intermedios L1–L4 unidos solo a las verticales de arriba y abajo. Sus topes ROOF coinciden con nodos de las vigas de cubierta; sus nodos de pisos inferiores **no** comparten nodo con las vigas cercanas ni pertenecen a los diafragmas. Por ejemplo, en L2 el nodo 700003 de la caja oeste está en `(0.998, 2.900, -0.050) m` y el extremo de viga más cercano está a aproximadamente 1.23 m. No hay una viga de esa longitud documentada en los datos del modelo.
- Los seis paños de muro equivalentes LT1 usan nodos en el centroide de cada paño y enlaces cinemáticos al diafragma. Por ello, una separación visual entre el sólido del muro y una viga de la retícula no basta para decidir que hay que prolongar esa viga hasta el centroide.

## Ensayo descartado

Se probó temporalmente vincular los 40 nodos de cajas en L1–L4 a los masters de diafragma. El análisis convergió y conservó equilibrio global, pero la demanda del muro M001 bajo `EY` cambió de fuera de capacidad a dentro de capacidad con la misma curva P–M. La prueba de regresión `test_muro_ey_fuera_en_eje_fuerte` detectó la alteración. **Se retiró por completo esa hipótesis** y se regeneraron el modelo y resultados originales: 24 `constraint_links`, cinco casos de análisis y 159 pruebas aprobadas. Ese ensayo no constituye una solución validada.

## Decisión y dato necesario

No se añadió ninguna viga, enlace rígido o dimensión inferida solo de la captura. Para corregir el elemento correcto sin fabricar geometría ni cambiar inadvertidamente la demanda–capacidad, se necesita el `elementTag` de una de las vigas señaladas (se obtiene al seleccionarla en Unity), o una captura con el panel de propiedades visible. Con ese tag se puede trazar el par de nodos, nivel y lámina, y aplicar la misma corrección verificada a los pisos equivalentes.

## Corrección tras identificar los diez tags

Los tags 2081/2083, 2085/2087, 2089/2091, 2093/2095 y 2205/2207 son dos
vigas `V30x80` por nivel L1, L2, L3, L4 y ROOF. Sus extremos libres estaban en
`(1.900, 4.265)` y `(1.900, 11.885)` m. Las plantas LT2 101 (L1-L4) y 102
(ROOF) muestran continuidad horizontal hasta la cadena `V40` en `x=0.400 m`.

La [tabla de geometría](../data/conexiones_v30_lt2.csv) registra los diez
tramos faltantes, de 1.50 m y sección `V30x80`, con nuevos tags 9011-9020.
Cada tramo comparte un nodo con la viga original y otro con una viga de la
cadena V40 del mismo nivel. No se movieron nodos, muros ni tags nativos LT2.
Estos elementos se agregan **solo al modelo COMBINADO** para conservar la
trazabilidad del módulo LT2 original.

Los nuevos tramos no tienen carga tributaria propia en el dataset LT2; se
mantuvieron las cargas puntuales originales, sin inventar áreas de losa.
El análisis y los diagramas se regeneraron para los cinco casos. La
[auditoría tributaria posterior](auditoria_tributarias_v30_2026-09-20.md)
cuantifica la redistribución local que aún **no está aplicada** al modelo,
pendiente de confirmar los paños de losa señalados en ese informe.
