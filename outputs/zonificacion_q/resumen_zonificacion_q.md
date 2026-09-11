# Zonificación de SC (Q) LT1 — plan 700

- Solo preparación de datos. **No se modifica la Parte A ni la Parte B.**
- Geometría tributaria idéntica a G: bisectrices de `data/tributacion.py`, verificada 1:1 contra `area_tributaria_m2` del JSON (108 vigas). No se recalcula geometría.

| nivel | A_losa (m²) | A con SC área (m²) | Q_zon área (kN) | Q_zon vigas (kN) | err rel | vigas | vigas con Q |
|---|---|---|---|---|---|---|---|
| PISO_1 | 686.375 | 686.375 | 2633.024 | 2633.024 | 1.73e-16 | 27 | 27 |
| PISO_2 | 686.375 | 686.375 | 2348.631 | 2348.631 | 3.87e-16 | 27 | 27 |
| PISO_3 | 686.375 | 686.375 | 1923.942 | 1923.942 | 0.00e+00 | 27 | 27 |
| PISO_4 | 686.375 | 686.375 | 1705.683 | 1705.683 | 1.33e-16 | 27 | 25 |

**Q_zon total (área) LT1 = 8611.281 kN**  
Referencia uniforme 2.0 kPa (repositorio) = 5491.000 kN

## Cargas lineales de SC (NO asignadas a viga)

- PISO_4 — col3 row1 (bahía I-I', Y=1-2): **800 kgf/m = 7.8453 kN/m** (PENDIENTE_CONFIRMACION). Viga objetivo y longitud: INPUT_REQUIRED.

## Pendientes / INPUT_REQUIRED

- N/d.
