using UnityEngine;

// Diagramas con signo del elemento seleccionado. La fuerza de seccion se
// obtiene de las fuerzas resistentes de extremo de OpenSees mediante
// q_i=-F_i y q_j=+F_j. No se mezclan kN con kN-m ni se elimina el signo.
public class ForceDiagramController : MonoBehaviour
{
    public enum DiagramMode { Mz, My, N, Vy, Vz, T }

    private ModelLoader loader;
    private SelectionController selection;
    private GameObject diagramsRoot;
    private Material lineMaterial;
    private Material baseMaterial;
    private bool active;
    private int drawnTag = -1;
    private string drawnCase = "";
    private DiagramMode mode = DiagramMode.Mz;
    private Texture2D chartTexture;
    private float chartValueI;
    private float chartValueJ;
    private string status = "Diagrama apagado";

    public bool Active => active;
    public DiagramMode Mode => mode;
    public string ModeLabel => mode.ToString();
    public Texture2D ChartTexture => chartTexture;
    public float ChartValueI => chartValueI;
    public float ChartValueJ => chartValueJ;
    public int DrawnTag => drawnTag;
    public string DrawnCase => drawnCase;
    public string CurrentUnits => Units(mode);
    public string Status => status;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        selection = FindObjectOfType<SelectionController>();
        lineMaterial = new Material(Shader.Find("Sprites/Default"));
        baseMaterial = new Material(Shader.Find("Sprites/Default"));
        baseMaterial.color = new Color(0.75f, 0.75f, 0.75f, 0.8f);
        ApplyModeColor();
    }

    void OnEnable() { ModelLoader.CaseChanged += HandleCaseChanged; }
    void OnDisable() { ModelLoader.CaseChanged -= HandleCaseChanged; }
    void HandleCaseChanged(string caseKey) { drawnCase = ""; if (active) Refresh(); }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.M)) Toggle();
        if (!active || selection == null) return;
        string c = loader != null ? loader.activeCase : "";
        if (selection.SelectedTag != drawnTag || c != drawnCase) Refresh();
    }

    public void Toggle()
    {
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        if (selection == null) selection = FindObjectOfType<SelectionController>();
        active = !active;
        if (active) Refresh();
        else { Clear(); status = "Diagrama apagado"; }
    }

    public void SetMode(DiagramMode next)
    {
        mode = next;
        ApplyModeColor();
        if (active) Refresh();
    }

    public void CycleMode() { SetMode((DiagramMode)(((int)mode + 1) % 6)); }

    void ApplyModeColor()
    {
        if (lineMaterial == null) return;
        switch (mode)
        {
            case DiagramMode.Mz: lineMaterial.color = new Color(1f, 0.15f, 0.85f); break;
            case DiagramMode.My: lineMaterial.color = new Color(0.65f, 0.25f, 1f); break;
            case DiagramMode.N:  lineMaterial.color = new Color(0.15f, 1f, 0.35f); break;
            case DiagramMode.Vy: lineMaterial.color = new Color(1f, 0.58f, 0.08f); break;
            case DiagramMode.Vz: lineMaterial.color = new Color(1f, 0.85f, 0.05f); break;
            default:             lineMaterial.color = new Color(0.1f, 0.95f, 1f); break;
        }
    }

    public void Refresh()
    {
        Clear();
        if (!active) { status = "Diagrama apagado"; return; }
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        if (selection == null) selection = FindObjectOfType<SelectionController>();
        if (loader == null || selection == null)
        { status = "Controlador del modelo o seleccion no disponible"; return; }
        int tag = selection.SelectedTag;
        if (tag < 0) { status = "Selecciona una viga, columna o muro"; return; }
        if (!loader.elementForceI.TryGetValue(tag, out var fi) ||
            !loader.elementForceJ.TryGetValue(tag, out var fj) ||
            fi == null || fj == null || fi.Length < 6 || fj.Length < 6)
        { status = "Sin fuerzas de extremo para tag " + tag; return; }
        if (!TryGetEnds(tag, out var a, out var b))
        { status = "No se encontraron los nodos del tag " + tag; return; }

        int idx = ComponentIndex(mode);
        float valueI = -fi[idx];
        float valueJ = fj[idx];
        float maxAbs = Mathf.Max(Mathf.Abs(valueI), Mathf.Abs(valueJ));
        Vector3 dir = b - a;
        float len = dir.magnitude;
        if (len < 0.001f) { status = "Elemento de longitud nula"; return; }
        dir /= len;
        GetLocalFrame(tag, dir, out var localY, out var localZ);
        Vector3 normal = DiagramNormal(mode, localY, localZ);
        float peak = Mathf.Clamp(len * 0.38f, 0.9f, 5.0f);
        float scale = maxAbs > 1e-7f ? peak / maxAbs : 0f;

        diagramsRoot = new GameObject("Diagram_" + mode + "_" + tag);
        DrawLine("Base", new[] { a, b }, baseMaterial, 0.025f);
        const int samples = 21;
        var curve = new Vector3[samples];
        for (int i = 0; i < samples; i++)
        {
            float t = i / (samples - 1f);
            float value = Mathf.Lerp(valueI, valueJ, t);
            curve[i] = Vector3.Lerp(a, b, t) + normal * value * scale;
        }
        DrawLine(mode.ToString(), curve, lineMaterial, 0.16f);
        for (int i = 0; i < samples; i += 2)
            DrawLine("Ordinate_" + i,
                     new[] { Vector3.Lerp(a, b, i / (samples - 1f)), curve[i] },
                     lineMaterial, 0.035f);
        AddLabel($"{mode}: {valueI:F1} -> {valueJ:F1} {Units(mode)}",
                 curve[samples / 2] + Vector3.up * 0.22f);
        drawnTag = tag;
        drawnCase = loader.activeCase;
        chartValueI = valueI;
        chartValueJ = valueJ;
        BuildChart(valueI, valueJ);
        status = "OK";
    }

    int ComponentIndex(DiagramMode m)
    {
        switch (m)
        {
            case DiagramMode.N: return 0;
            case DiagramMode.Vy: return 1;
            case DiagramMode.Vz: return 2;
            case DiagramMode.T: return 3;
            case DiagramMode.My: return 4;
            default: return 5;
        }
    }

    string Units(DiagramMode m) =>
        (m == DiagramMode.N || m == DiagramMode.Vy || m == DiagramMode.Vz) ? "kN" : "kN-m";

    Vector3 DiagramNormal(DiagramMode m, Vector3 y, Vector3 z) =>
        (m == DiagramMode.Mz || m == DiagramMode.Vy) ? y : z;

    void DrawLine(string name, Vector3[] points, Material mat, float width)
    {
        var go = new GameObject(name);
        go.transform.SetParent(diagramsRoot.transform);
        var lr = go.AddComponent<LineRenderer>();
        lr.material = mat;
        lr.startColor = mat.color;
        lr.endColor = mat.color;
        lr.startWidth = width;
        lr.endWidth = width;
        lr.useWorldSpace = true;
        lr.positionCount = points.Length;
        lr.SetPositions(points);
    }

    void AddLabel(string text, Vector3 pos)
    {
        var go = new GameObject("DiagramLabel");
        go.transform.SetParent(diagramsRoot.transform);
        go.transform.position = pos;
        var tm = go.AddComponent<TextMesh>();
        tm.text = text;
        tm.characterSize = 0.22f;
        tm.fontSize = 48;
        tm.anchor = TextAnchor.MiddleCenter;
        tm.color = Color.white;
    }

    void GetLocalFrame(int tag, Vector3 dir, out Vector3 localY, out Vector3 localZ)
    {
        if (loader.elementRefs.TryGetValue(tag, out var r) && r.ejes_locales != null &&
            r.ejes_locales.x != null && r.ejes_locales.x.Length >= 3 &&
            r.ejes_locales.y != null && r.ejes_locales.y.Length >= 3 &&
            r.ejes_locales.z != null && r.ejes_locales.z.Length >= 3)
        {
            Vector3 x = ModelLoader.StructToUnity(r.ejes_locales.x[0], r.ejes_locales.x[1], r.ejes_locales.x[2]).normalized;
            localY = ModelLoader.StructToUnity(r.ejes_locales.y[0], r.ejes_locales.y[1], r.ejes_locales.y[2]).normalized;
            localZ = ModelLoader.StructToUnity(r.ejes_locales.z[0], r.ejes_locales.z[1], r.ejes_locales.z[2]).normalized;
            if (Vector3.Dot(x, dir) < 0f) { localY = -localY; localZ = -localZ; }
        }
        else
        {
            localZ = Vector3.Cross(Vector3.up, dir);
            if (localZ.sqrMagnitude < 0.001f) localZ = Vector3.Cross(Vector3.forward, dir);
            localZ.Normalize();
            localY = Vector3.Cross(localZ, dir).normalized;
        }
    }

    bool TryGetEnds(int tag, out Vector3 a, out Vector3 b)
    {
        a = b = Vector3.zero;
        if (!loader.elementRefs.TryGetValue(tag, out var r)) return false;
        if (!loader.nodeObjects.TryGetValue(r.nodeI, out var ni) ||
            !loader.nodeObjects.TryGetValue(r.nodeJ, out var nj)) return false;
        a = ni.transform.position;
        b = nj.transform.position;
        return true;
    }

    void Clear()
    {
        if (diagramsRoot != null) Destroy(diagramsRoot);
        if (chartTexture != null) Destroy(chartTexture);
        diagramsRoot = null;
        chartTexture = null;
        drawnTag = -1;
    }

    void BuildChart(float valueI, float valueJ)
    {
        const int w = 500, h = 150;
        const int left = 42, right = 486, top = 12, bottom = 126;
        Color32 bg = new Color32(19, 24, 34, 245);
        Color32 grid = new Color32(63, 72, 89, 255);
        Color32 axis = new Color32(220, 226, 236, 255);
        Color32 curve = (Color32)lineMaterial.color;
        Color32[] px = new Color32[w * h];
        for (int i = 0; i < px.Length; i++) px[i] = bg;
        for (int i = 0; i <= 4; i++)
        {
            int x = left + Mathf.RoundToInt(i / 4f * (right - left));
            ChartLine(px, w, h, x, top, x, bottom, grid, 1);
            int y = top + Mathf.RoundToInt(i / 4f * (bottom - top));
            ChartLine(px, w, h, left, y, right, y, grid, 1);
        }
        float min = Mathf.Min(0f, valueI, valueJ);
        float max = Mathf.Max(0f, valueI, valueJ);
        float pad = Mathf.Max((max - min) * 0.15f, 1e-3f);
        min -= pad; max += pad;
        int zeroY = Mathf.RoundToInt(bottom - (0f - min) / (max - min) * (bottom - top));
        ChartLine(px, w, h, left, zeroY, right, zeroY, axis, 2);
        ChartLine(px, w, h, left, top, left, bottom, axis, 2);
        int lastX = left;
        int lastY = Mathf.RoundToInt(bottom - (valueI - min) / (max - min) * (bottom - top));
        for (int i = 1; i <= 40; i++)
        {
            float t = i / 40f;
            float value = Mathf.Lerp(valueI, valueJ, t);
            int x = Mathf.RoundToInt(Mathf.Lerp(left, right, t));
            int y = Mathf.RoundToInt(bottom - (value - min) / (max - min) * (bottom - top));
            ChartLine(px, w, h, lastX, lastY, x, y, curve, 3);
            lastX = x; lastY = y;
        }
        chartTexture = new Texture2D(w, h, TextureFormat.RGBA32, false);
        chartTexture.SetPixels32(px);
        chartTexture.Apply();
    }

    static void ChartLine(Color32[] px, int w, int h, int x0, int y0,
                          int x1, int y1, Color32 color, int thickness)
    {
        int dx = Mathf.Abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
        int dy = -Mathf.Abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
        int err = dx + dy;
        while (true)
        {
            for (int oy = -thickness / 2; oy <= thickness / 2; oy++)
                for (int ox = -thickness / 2; ox <= thickness / 2; ox++)
                {
                    int x = x0 + ox, y = y0 + oy;
                    if (x >= 0 && x < w && y >= 0 && y < h) px[y * w + x] = color;
                }
            if (x0 == x1 && y0 == y1) break;
            int e2 = 2 * err;
            if (e2 >= dy) { err += dy; x0 += sx; }
            if (e2 <= dx) { err += dx; y0 += sy; }
        }
    }

    void OnGUI()
    {
        // La grafica 2D se dibuja dentro del inspector derecho de ViewerHUD.
    }

    void OnDestroy() { Clear(); }
}
