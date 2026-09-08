using System;
using System.Collections.Generic;

[Serializable]
public class ModelRoot
{
    public Metadata metadata;
    public NodeData[] nodes;
    public BeamData[] beams;
    public ColumnData[] columns;
    public SupportData[] supports;
    public DiaphragmData[] diaphragms;
    public WallData[] walls;
    public ConstraintLinkData[] constraint_links;
    public AnalysisData analysis;
    public TributaryAreaData[] tributary_areas;
    public PanosData[] panos;
    public PendingGeometryData[] pending_geometry;
}

[Serializable]
public class Metadata
{
    public Units unidades;
    public string sistema_coordenadas;
    public string fecha_generacion;
    public string estado_modelo;
    public bool analisis_disponible;
    public MaterialProps material;
    public ModelCounts conteos;
    public AnalysisInfo analisis;
    public PendingGeometryData[] pendientes;
    public string[] limitaciones;
}

[Serializable]
public class ModelCounts
{
    public int nodos_totales;
    public int nodos_estructurales;
    public int nodos_master;
    public int elasticBeamColumn;
    public int columnas;
    public int vigas;
    public int muros_equivalentes;
    public int rigidLink_constraint_muros;
    public int apoyos;
    public int diafragmas;
}

[Serializable]
public class AnalysisInfo
{
    public string estado;
    public int analyze_retorno;
    public float P_gravedad_kN;
    public float suma_Rz_kN;
    public float error_rel_equilibrio;
    public float max_desplazamiento_m;
}

[Serializable]
public class Units
{
    public string longitud;
    public string fuerza;
    public string tension;
}

[Serializable]
public class MaterialProps
{
    public float E_kPa;
    public float nu;
    public float G_kPa;
    public string fuente;
}

[Serializable]
public class NodeData
{
    public int tag;
    public float x;
    public float y;
    public float z;
    public string tipo;
    public string nivel;
    public string eje_x;
    public string eje_y;
}

[Serializable]
public class BeamData
{
    public int elementTag;
    public int node_i;
    public int node_j;
    public string seccion;
    public float longitud_m;
    public string nivel;
    public float[] local_axis_xz;
    public float A_m2;
    public float Iy_m4;
    public float Iz_m4;
    public float J_m4;
    public float carga_lineal_qG_kN_m;
    public float area_tributaria_m2;
    public float carga_total_tributaria_kN;
    public string orientacion;
}

[Serializable]
public class ColumnData
{
    public int elementTag;
    public int node_i;
    public int node_j;
    public string seccion;
    public float longitud_m;
    public string nivel_inferior;
    public string nivel_superior;
    public float[] local_axis_xz;
    public float A_m2;
    public float Iy_m4;
    public float Iz_m4;
    public float J_m4;
}

[Serializable]
public class SupportData
{
    public int nodeTag;
    public int[] restricciones;
    public string tipo;
    public string nivel;
}

[Serializable]
public class DiaphragmData
{
    public string nivel;
    public int master;
    public int[] slaves;
    public float z;
    public string DOF_compatibilizados;
}

[Serializable]
public class WallData
{
    public int elementTag;
    public int node_i;
    public int node_j;
    public string clave;
    public string seccion;
    public float espesor_m;
    public float longitud_planta_m;
    public string orientacion;
    public string en_plano_direccion;
    public string nivel_inferior;
    public string nivel_superior;
    public float longitud_vertical_m;
    public float[] local_axis_xz;
    public float A_m2;
    public float Iy_m4;
    public float Iz_m4;
    public float J_m4;
    public string estado_geometria;
    public string fuente;
    public string constraint;
}

[Serializable]
public class ConstraintLinkData
{
    public string rectype;
    public string beamType;
    public string config;
    public int nodo_maestro_retained;
    public int nodo_muro;
    public string nivel;
    public string muro_clave;
    public string lado;
    public string movimiento_heredado;
    public bool elimina_gdl;
}

[Serializable]
public class PendingGeometryData
{
    public string id;
    public string descripcion;
    public string tipo;
    public string estado;
}

[Serializable]
public class AnalysisData
{
    public string estado;
    public float P_aplicada_kN;
    public float suma_Rz_kN;
    public float err_abs_kN;
    public float err_rel;
    public float max_desplazamiento_m;
    public int nodo_max_desplazamiento;
    public float max_Uz_m;
    public bool nan_inf;
    public bool diafragmas_compatibles;
    [NonSerialized] public Dictionary<int, float[]> reacciones;
    [NonSerialized] public Dictionary<int, float[]> desplazamientos;
}

[Serializable]
public class TributaryAreaData
{
    public int elementTag;
    public string nivel;
    public float A_tributaria_m2;
    public float P_losa_kN;
    public float w_kN_m;
    public float[] q_G_kPa;
    public float longitud_m;
    public string orientacion;
    public string[] origen;
}

[Serializable]
public class PanosData
{
    public string id;
    public string nivel;
    public string eje_x0;
    public string eje_x1;
    public string eje_y0;
    public string eje_y1;
    public float Lx;
    public float Ly;
    public float area_m2;
    public float q_G_kPa;
}
