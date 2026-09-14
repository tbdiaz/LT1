using UnityEngine;

// Referencia de trazabilidad elemento <-> JSON <-> GameObject.
//
// Cada primitiva del visor que representa un elemento del modelo lleva un
// ElementRef con la informacion COMPLETA del elemento tal como fue exportada
// en modelo_combinado.json (sin reinventar nada). Junto con
// ModelLoader.elementRefs[elementTag], esto permite:
//   GameObject -> elementTag -> indice en combinedRoot.elements -> campos JSON.
// Los resultados del caso activo se consultan por elementTag en
// ModelLoader.analysis.fuerzas_elementos (N/Vy/Vz/T/My/Mz x extremo).
public class ElementRef : MonoBehaviour
{
    public int elementTag;
    public int jsonIndex;      // indice en combinedRoot.elements
    public string tipo;        // viga | columna | muro | viga_saliente | ...
    public string origen;      // LT2 | LT1 | COMBINADO | ... (del JSON)
    public string categoria;   // "Beam" | "Column" | "Wall" (prefijo del GO)

    public int nodeI;
    public int nodeJ;
    public float longitud_m;

    public CombinedSection seccion;   // label/b/h/A/Iy/Iz/J/E/G/nota
    public float[] vecxz;             // vector de referencia de la geomTransf
    public CombinedAxes ejes_locales; // ejes locales exportados (x,y,z)

    // meta segun tipo de elemento (origen del JSON)
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

    public string TipoEtiqueta()
    {
        switch (tipo)
        {
            case "viga": return "Viga";
            case "viga_saliente": return "Viga saliente";
            case "segmento_fachada": return "Segmento de fachada";
            case "columna": return "Columna";
            case "vertical_caja": return "Vertical (caja/pilastra)";
            case "muro": return "Muro equivalente";
            case "muro_corner": return "Muro (corner)";
            case "conector_v40_muro": return "Conector V40-muro";
            default: return tipo;
        }
    }

    public bool IsSupuesta()
    {
        return !string.IsNullOrEmpty(estado_geometria) &&
               (estado_geometria.ToUpperInvariant().Contains("ASUM")
                || estado_geometria.ToUpperInvariant().Contains("SUPUESTO")
                || estado_geometria.ToUpperInvariant().Contains("PENDING"));
    }
}