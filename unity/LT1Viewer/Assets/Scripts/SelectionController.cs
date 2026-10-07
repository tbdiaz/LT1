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
    private Renderer[] selectedRenderers = new Renderer[0];
    private Material[] originalMaterials = new Material[0];
    private Vector2 touchStart;
    private float touchStartTime;
    private int trackedFinger = -1;

    void Start()
    {
        highlightMaterial = new Material(Shader.Find("Standard"));
        highlightMaterial.color = Color.yellow;
    }

    void Update()
    {
        if (Input.touchCount > 0)
        {
            HandleTouchSelection();
            return;
        }
        if (Input.GetMouseButtonDown(0) && !Input.GetKey(KeyCode.LeftAlt))
        {
            if (ViewerHUD.PointerOverHud(Input.mousePosition)) return;
            HandleClick(Input.mousePosition);
        }
    }

    void HandleTouchSelection()
    {
        if (Input.touchCount != 1) return;
        Touch touch = Input.GetTouch(0);
        if (touch.phase == TouchPhase.Began)
        {
            trackedFinger = touch.fingerId;
            touchStart = touch.position;
            touchStartTime = Time.unscaledTime;
        }
        else if ((touch.phase == TouchPhase.Ended ||
                  touch.phase == TouchPhase.Canceled) &&
                 touch.fingerId == trackedFinger)
        {
            float movement = Vector2.Distance(touchStart, touch.position);
            float duration = Time.unscaledTime - touchStartTime;
            trackedFinger = -1;
            float tapTolerance = Mathf.Max(22f, Screen.dpi > 0f
                ? Screen.dpi * 0.10f : 22f);
            if (touch.phase == TouchPhase.Ended && movement <= tapTolerance &&
                duration <= 0.80f && !ViewerHUD.PointerOverHud(touch.position))
                HandleClick(touch.position);
        }
    }

    void HandleClick(Vector3 screenPoint)
    {
        Camera selectionCamera = ResolveSelectionCamera();
        if (selectionCamera == null) return;
        Ray ray = selectionCamera.ScreenPointToRay(screenPoint);

        // Un nodo o apoyo puede estar delante de la barra. Raycast() devolvia
        // solo ese primer collider y cancelaba la seleccion. Se recorren todos
        // los impactos ordenados y se toma el primero con trazabilidad real.
        RaycastHit[] hits = Physics.RaycastAll(
            ray, Mathf.Infinity, ~0, QueryTriggerInteraction.Ignore);
        System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (RaycastHit hit in hits)
        {
            ElementRef element = hit.collider.GetComponent<ElementRef>();
            if (element == null)
                element = hit.collider.GetComponentInParent<ElementRef>();
            if (element == null) continue;
            SelectElement(element);
            return;
        }
        Deselect();
    }

    static Camera ResolveSelectionCamera()
    {
        Camera[] cameras = FindObjectsOfType<Camera>();
        Camera best = null;
        foreach (Camera candidate in cameras)
        {
            if (candidate == null || !candidate.enabled
                || !candidate.gameObject.activeInHierarchy) continue;
            bool candidateOrbits = candidate.GetComponent<OrbitCamera>() != null;
            bool bestOrbits = best != null
                && best.GetComponent<OrbitCamera>() != null;
            if (best == null || (candidateOrbits && !bestOrbits)
                || (candidateOrbits == bestOrbits && candidate.depth > best.depth))
                best = candidate;
        }
        return best != null ? best : Camera.main;
    }

    void SelectElement(ElementRef element)
    {
        Deselect();

        SelectedObject = element.gameObject;
        SelectedTag = element.elementTag;
        if (element.tipo == "columna") SelectedType = "Columna";
        else if (element.tipo == "muro" || element.tipo == "muro_corner"
                 || element.tipo == "vertical_caja"
                 || element.tipo == "conector_v40_muro")
            SelectedType = "Muro";
        else SelectedType = "Viga";

        selectedRenderers = SelectedObject.GetComponentsInChildren<Renderer>();
        originalMaterials = new Material[selectedRenderers.Length];
        for (int i = 0; i < selectedRenderers.Length; i++)
        {
            originalMaterials[i] = selectedRenderers[i].material;
            selectedRenderers[i].material = highlightMaterial;
        }
    }

    public void Deselect()
    {
        int count = Mathf.Min(selectedRenderers.Length, originalMaterials.Length);
        for (int i = 0; i < count; i++)
        {
            if (selectedRenderers[i] != null && originalMaterials[i] != null)
                selectedRenderers[i].material = originalMaterials[i];
        }
        SelectedObject = null;
        selectedRenderers = new Renderer[0];
        originalMaterials = new Material[0];
        SelectedTag = -1;
        SelectedType = "";
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
