# Reglas del proyecto LT1

- Este proyecto corresponde exclusivamente al modelo estructural LT1.
- No inventar geometría, dimensiones, niveles, secciones, materiales, cargas ni condiciones de apoyo.
- Toda la información estructural debe provenir de los planos y datos que se entreguen explícitamente.
- OpenSeesPy será utilizado para construir y analizar el modelo estructural 3D.
- Los datos de geometría deben mantenerse separados de la lógica del modelo.
- Utilizar como unidades base: metros (m), kilonewtons (kN) y kilopascales (kPa).
- Cada etapa del modelo debe poder verificarse antes de avanzar a la siguiente.
- No asumir que elementos visualmente alineados en un plano tienen la misma coordenada sin verificar sus cotas.
- No modificar ni eliminar información existente sin explicar previamente el motivo.
- No avanzar automáticamente a otras etapas del modelo sin que se solicite.