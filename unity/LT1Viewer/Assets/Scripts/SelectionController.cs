using System.Collections.Generic;
using UnityEngine;

// Seleccion de elementos del VISOR COMBINADO LT1+LT2 (P1L4).
// Alcance por requisito: al seleccionar un elemento se muestra elementTag,
// tipo (tipo real del JSON), nodeI, nodeJ, seccion, material, origen,
// ejes locales (los exportados en 'ejes_locales'), restricciones de borde,
// caso activo y los flags de SUPUESTO. Los esfuerzos locales del caso activo
// (N/Vy/Vz/T/My/Mz por extremo) se muestran en el panel
// 'Resultados estructurales' (StructuralResultsController), que lee el mismo
// analysis.fuerzas_elementos por elementTag -> trazabilidad JSON<->resultado.
// No se inventa ningun valor: los campos ausentes se muestran como N/D.
public class SelectionController : MonoBehaviour
{
    [HideInInspector] public int SelectedTag = -1;
    [HideInInspector] public string SelectedType = "";
    [HideInInspector] public GameObject SelectedObject;

    private Material highlightMaterial;
    private Material originalMaterial;

    void Start()
    {
        highlightMaterial = new Material(Shader.Find("Standard"));
        highlightMaterial.color = Color.yellow;
    }

    void Update()
    {
        if (Input.GetMouseButtonDown(0) && !Input.GetKey(KeyCode.LeftAlt))
        {
            if (ViewerHUD.PointerOverHud(Input.mousePosition)) return;
            HandleClick();
        }
    }

    void HandleClick()
    {
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);

        if (!Physics.Raycast(ray, out RaycastHit hit))
        {
            Deselect();
            return;
        }

        string objName = hit.collider.gameObject.name;

        if (objName.StartsWith("Beam_") || objName.StartsWith("Column_") ||
            objName.StartsWith("Wall_"))
        {
            SelectElement(hit.collider.gameObject, objName);
        }
        else
        {
            Deselect();
        }
    }

    void SelectElement(GameObject go, string objName)
    {
        Deselect();

        SelectedObject = go;
        originalMaterial = go.GetComponent<Renderer>().material;
        go.GetComponent<Renderer>().material = highlightMaterial;

        SelectedTag = ParseTag(objName);
        if (objName.StartsWith("Beam_")) SelectedType = "Viga";
        else if (objName.StartsWith("Column_")) SelectedType = "Columna";
        else if (objName.StartsWith("Wall_")) SelectedType = "Muro";
    }

    public void Deselect()
    {
        if (SelectedObject != null && originalMaterial != null)
        {
            SelectedObject.GetComponent<Renderer>().material = originalMaterial;
        }
        SelectedObject = null;
        originalMaterial = null;
        SelectedTag = -1;
        SelectedType = "";
    }

    int ParseTag(string name)
    {
        int idx = name.LastIndexOf('_');
        if (idx >= 0 && int.TryParse(name.Substring(idx + 1), out int tag))
            return tag;
        return -1;
    }

    public ElementRef GetElementRef()
    {
        if (SelectedTag < 0) return null;
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null) return null;

        if (SelectedObject != null)
        {
            ElementRef r = SelectedObject.GetComponent<ElementRef>();
            if (r != null && r.elementTag == SelectedTag) return r;
        }

        ElementRef found = null;
        if (loader.elementRefs != null && loader.elementRefs.TryGetValue(SelectedTag, out found))
            return found;
        return null;
    }

    // Se conservan los getters legacy (los controladores existentes pueden
    // consultar el agregado por elementTag).
    public BeamData GetSelectedBeam()
    {
        if (SelectedTag < 0 || SelectedType != "Viga") return null;
        var loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null || loader.modelData.beams == null) return null;
        foreach (var b in loader.modelData.beams)
            if (b.elementTag == SelectedTag) return b;
        return null;
    }

    public ColumnData GetSelectedColumn()
    {
        if (SelectedTag < 0 || SelectedType != "Columna") return null;
        var loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null || loader.modelData.columns == null) return null;
        foreach (var c in loader.modelData.columns)
            if (c.elementTag == SelectedTag) return c;
        return null;
    }

    public WallData GetSelectedWall()
    {
        if (SelectedTag < 0 || SelectedType != "Muro") return null;
        var loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null || loader.modelData.walls == null) return null;
        foreach (var w in loader.modelData.walls)
            if (w.elementTag == SelectedTag) return w;
        return null;
    }

    void OnGUI()
    {
        return; // ficha unificada (propiedades + esfuerzos) en ViewerHUD
#pragma warning disable CS0162
        if (SelectedTag < 0) return;

        var loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null) return;

        ElementRef r = GetElementRef();
        if (r == null) return;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Tipo: {r.TipoEtiqueta()}  [{r.origen}]");
        sb.AppendLine($"elementTag: {r.elementTag}  (json idx {r.jsonIndex})");
        sb.AppendLine($"Nodos: I={r.nodeI}  J={r.nodeJ}");
        sb.AppendLine(r.nivel.Length > 0 ? $"Nivel: {r.nivel}"
            : TryRange(r, out string rng) ? $"Nivel: {rng}" : "Nivel: N/D");
        sb.AppendLine($"Longitud: {r.longitud_m:F3} m");

        if (r.seccion != null)
        {
            var s = r.seccion;
            sb.AppendLine($"Seccion: {s.label}");
            if (s.b_m > 1e-6f && s.h_m > 1e-6f)
                sb.AppendLine($"  b x h: {s.b_m:F3} x {s.h_m:F3} m");
            if (s.A_m2 > 0f) sb.AppendLine($"  A={s.A_m2:E3} m2  Iy={s.Iy_m4:E3}  Iz={s.Iz_m4:E3}  J={s.J_m4:E3} m4");
            sb.AppendLine($"Material: E={FormatKpa(s.E_kPa)}  G={FormatKpa(s.G_kPa)}");
        }

        if (r.vecxz != null && r.vecxz.Length >= 3)
            sb.AppendLine($"vecxz: {VecStr(r.vecxz)}");

        if (r.ejes_locales != null &&
            r.ejes_locales.x != null && r.ejes_locales.x.Length >= 3 &&
            r.ejes_locales.y != null && r.ejes_locales.y.Length >= 3 &&
            r.ejes_locales.z != null && r.ejes_locales.z.Length >= 3)
        {
            sb.AppendLine($"Ejes locales (exportados):");
            sb.AppendLine($"  x={VecStr(r.ejes_locales.x)}");
            sb.AppendLine($"  y={VecStr(r.ejes_locales.y)}");
            sb.AppendLine($"  z={VecStr(r.ejes_locales.z)}");
        }

        sb.AppendLine(DescribeBoundaries(loader, r));

        sb.AppendLine($"Caso activo: {loader.activeCase}");
        sb.AppendLine("<color=grey>Esfuerzos N/Vy/Vz/T/My/Mz en el panel "
            + "'Resultados estructurales'.</color>");

        if (r.IsSupuesta())
            sb.AppendLine($"<color=orange>FLAG SUPUESTO: {r.estado_geometria}"
                + "</color>");
        else if (!string.IsNullOrEmpty(r.estado_geometria))
            sb.AppendLine($"Estado geometria: {r.estado_geometria}");

        if (!string.IsNullOrEmpty(r.clave)) sb.AppendLine($"Clave: {r.clave}");
        if (!string.IsNullOrEmpty(r.beam_id)) sb.AppendLine($"beam_id: {r.beam_id}");
        if (!string.IsNullOrEmpty(r.columna_id)) sb.AppendLine($"columna_id: {r.columna_id}");
        if (!string.IsNullOrEmpty(r.muro_id)) sb.AppendLine($"muro_id: {r.muro_id}");
        if (r.tag_original > 0) sb.AppendLine($"tag_original: {r.tag_original}");
        if (!string.IsNullOrEmpty(r.fuente)) sb.AppendLine($"Fuente: {r.fuente}");

        string info = sb.ToString();
        int lines = CountLines(info);

        float pw = 380f;
        float ph = 28 + lines * 16f + 24f;
        float x = 10f;
        float y = Screen.height - ph - 40f;

        GUI.Box(new Rect(x, y, pw, ph), "Info Elemento (P1L4)");

        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 35));
        GUIStyle style = new GUIStyle(GUI.skin.label) { richText = true, fontSize = 12, wordWrap = true };
        GUILayout.Label(info, style);
        GUILayout.EndArea();
#pragma warning restore CS0162
    }

    bool TryRange(ElementRef r, out string range)
    {
        range = "";
        string a = FirstNonEmpty(r.nivel_bajo, r.nivel_inferior, r.nivel);
        string b = FirstNonEmpty(r.nivel_alto, r.nivel_superior, r.nivel);
        if (a.Length == 0 && b.Length == 0) return false;
        if (a == b) range = a;
        else range = $"{a} -> {b}";
        return true;
    }

    string FirstNonEmpty(params string[] vals)
    {
        foreach (var v in vals)
            if (!string.IsNullOrEmpty(v)) return v;
        return "";
    }

    string DescribeBoundaries(ModelLoader loader, ElementRef r)
    {
        string res = "Restricciones (borde): ";
        bool any = false;
        if (loader.boundaryRestricciones != null)
        {
            if (loader.boundaryRestricciones.ContainsKey(r.nodeI))
            {
                res += $"nodo {r.nodeI} (apoyo {loader.boundaryOrigen[r.nodeI]}) "
                    + "[" + JoinInts(loader.boundaryRestricciones[r.nodeI]) + "]  ";
                any = true;
            }
            if (loader.boundaryRestricciones.ContainsKey(r.nodeJ))
            {
                res += $"nodo {r.nodeJ} (apoyo {loader.boundaryOrigen[r.nodeJ]}) "
                    + "[" + JoinInts(loader.boundaryRestricciones[r.nodeJ]) + "]";
                any = true;
            }
        }
        if (!any) res += "nodos libres (sin apoyo)";
        return res;
    }

    string JoinInts(int[] v)
    {
        if (v == null) return "";
        var parts = new List<string>();
        foreach (var i in v) parts.Add(i.ToString());
        return string.Join(",", parts.ToArray());
    }

    static string VecStr(float[] v)
    {
        return $"({v[0]:F4}, {v[1]:F4}, {v[2]:F4})";
    }

    static string FormatKpa(float kpa)
    {
        if (kpa >= 1e9f) return $"{kpa / 1e9f:F2} GPa";
        if (kpa >= 1e6f) return $"{kpa / 1e6f:F1} MPa";
        return $"{kpa:F0} kPa";
    }

    static int CountLines(string s)
    {
        int n = 1;
        foreach (char c in s) if (c == '\n') n++;
        return n;
    }
}
