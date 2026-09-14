// CombinedModelData.cs
//
// Clases [Serializable] que reflejan EXACTAMENTE el esquema de
// modelo_combinado.json (ETAPA P1L4). Se usa JsonUtility.FromJson
// (sin dependencias externas) para deserializar la fuente única del
// visor combinado LT1+LT2.
//
// Reglas:
//  - Los nombres de campo deben coincidir con las claves del JSON.
//  - No se pueden declarar Dictionary aqui: 'results.forces /
//    displacements / reactions / equilibrio' se parsean por caso desde
//    el JSON crudo (ver ModelLoader.ParseCaseResults).
//  - Las restricciones de la etapa (no tocar geometria/cargas/modelo
//    estructural) aplican: esta capa SOLO lee la fuente.

using System;

[Serializable]
public class ModeloCombinado
{
    public CombinedMetadata metadata;
    public CombinedNode[] nodes;
    public CombinedElement[] elements;
    public CombinedSupport[] supports;
    public CombinedMaster[] masters;
    public CombinedDiaphragm[] diaphragms;
    public CombinedLink[] constraint_links;
    public CombinedLoads loads;
    public CombinedTributary tributary_areas;
    public CombinedResults results;
}

[Serializable]
public class CombinedMetadata
{
    public string modelo;
    public string etapa;
    public string generado_por;
    public string fecha_generacion;
    public string origen_fuente;
    public CombinedUnits unidades;
    public CombinedMaterials materiales;
    public CombinedCaseSet casos;
    public CombinedLevel[] niveles;
    public string transformacion_lt1;
    public CombinedInterfaz interfaz_lt1_lt2;
    public CombinedVecConv convencion_ejes_locales;
    public string convencion_fuerzas_locales;
    public string convencion_seccion_opensees;
    public string[] notas_modelo;
}

[Serializable]
public class CombinedUnits
{
    public string longitud;
    public string fuerza;
    public string presion;
    public string modulo;
}

[Serializable]
public class CombinedMaterials
{
    public CombinedConcreto concreto;
    public CombinedAcero acero;
    public CombinedConectorV40 conector_v40_muro;
}

[Serializable]
public class CombinedConcreto
{
    public float fc_MPa;
    public float E_MPa;
    public float G_MPa;
    public float nu;
    public float densidad_kg_m3;
    public string fuente;
}

[Serializable]
public class CombinedAcero
{
    public float fy_MPa;
    public float E_MPa;
    public float densidad_kg_m3;
    public string fuente;
}

[Serializable]
public class CombinedConectorV40
{
    public float E_kPa;
    public float G_kPa;
    public float A_m2;
    public float Iy_m4;
    public float Iz_m4;
    public float J_m4;
    public string nota;
}

[Serializable]
public class CombinedCaseSet
{
    public CombinedCaseInfo G;
    public CombinedCaseInfo Q;
    public CombinedCaseInfo EX;
    public CombinedCaseInfo EY;
    public CombinedCaseInfo COMBO_R;
}

[Serializable]
public class CombinedCaseInfo
{
    public int[] patrones;
    public string descripcion;
    public float qG_LT2_losa_kPa;
    public float q_Q_kPa;
    public CombinedCoef coef;
}

[Serializable]
public class CombinedCoef
{
    public float G;
    public float Q;
    public float EX;
    public float EY;
}

[Serializable]
public class CombinedLevel
{
    public string name;
    public float z_m;
}

[Serializable]
public class CombinedInterfaz
{
    public int total_pares;
    public string regla;
}

[Serializable]
public class CombinedVecConv
{
    public string x;
    public string vecxz;
    public string y;
    public string z;
}

[Serializable]
public class CombinedNode
{
    public int nodeTag;
    public float x;
    public float y;
    public float z;
    public string origen;
    public string nivel;
}

[Serializable]
public class CombinedElement
{
    public int elementTag;
    public string tipo;
    public string origen;
    public int nodeI;
    public int nodeJ;
    public float longitud_m;
    public CombinedSection seccion;
    public float[] vecxz;
    public CombinedAxes ejes_locales;

    // meta (campos opcionales presentes segun el tipo de elemento)
    public string nivel;
    public string nivel_bajo;
    public string nivel_alto;
    public string nivel_inferior;
    public string nivel_superior;
    public string nivel_lt1;
    public string beam_id;
    public string columna_id;
    public string muro_id;
    public string clave;
    public string corner;
    public string familia;
    public string tipo_v;
    public string muro;
    public int nodo_muro;
    public int tag_original;
    public int transf_tag;
    public string seccion_id;
    public string estado_geometria;
    public string fuente;
    public string orientacion;
    public string constraint;
}

[Serializable]
public class CombinedSection
{
    public string label;
    public float b_m;
    public float h_m;
    public float A_m2;
    public float Iy_m4;
    public float Iz_m4;
    public float J_m4;
    public float E_kPa;
    public float G_kPa;
    public float espesor_m;
    public string nota;
}

[Serializable]
public class CombinedAxes
{
    public float[] x;
    public float[] y;
    public float[] z;
}

[Serializable]
public class CombinedSupport
{
    public int nodeTag;
    public string origen;
    public int[] restricciones;
    public string nivel;
}

[Serializable]
public class CombinedMaster
{
    public int nodeTag;
    public string nivel;
    public float x_m;
    public float y_m;
    public float z_m;
    public int[] restricciones;
    public string metodo;
}

[Serializable]
public class CombinedDiaphragm
{
    public string nivel;
    public int master;
    public int[] slaves;
    public float z_m;
    public string dof_compatibilizados;
}

[Serializable]
public class CombinedLink
{
    public string nivel;
    public int master;
    public int nodo_muro;
    public int tag_original;
}

[Serializable]
public class CombinedLoads
{
    public CombinedBeamLoad[] G;
    public CombinedBeamLoad[] Q;
    public CombinedLateralLoad[] EX;
    public CombinedLateralLoad[] EY;
    public CombinedCaseInfo COMBO_R;
}

[Serializable]
public class CombinedBeamLoad
{
    public int patron;
    public string origen;
    public string tipo;
    public int element_tag;
    public string level;
    public string beam_id;
    public float L_m;
    public float xloc;
    public float q_kN;
    public float area_m2;
    public string nivel;
    public float w_kN_m;
    public int tag_original;
}

[Serializable]
public class CombinedLateralLoad
{
    public int patron_tag;
    public string piso;
    public int node_tag;
    public float W_sismico_kN;
    public float fx_kN;
    public float fy_kN;
}

[Serializable]
public class CombinedTributary
{
    public CombinedTribDict LT2;
    public CombinedTribDict LT1;
}

[Serializable]
public class CombinedTribDict
{
    public string fuente;
    public CombinedTribRow[] filas;
}

[Serializable]
public class CombinedTribRow
{
    // LT2
    public string tributary_id;
    public string level;
    public string panel_id;
    public string receiver_type;
    public string receiver_id;
    public string beam_id;
    public string status;
    public int n_puntos_poligono;
    // LT1 (y comun)
    public int element_tag;
    public string nivel;
    public float A_tributaria_m2;
    public float P_losa_kN;
    public float w_kN_m;
    public float q_G_kPa;
    public float qG_kN_m2;
    public float area_m2;
    public float load_kN;
    public float longitud_m;
    public string orientacion;
    public string origen;
}

[Serializable]
public class CombinedResults
{
    // 'cases' es lo unico declarable con JsonUtility; forces /
    // displacements / reactions / equilibrio se parsean por caso
    // desde el JSON crudo (ModelLoader.ParseCaseResults).
    public string[] cases;
}