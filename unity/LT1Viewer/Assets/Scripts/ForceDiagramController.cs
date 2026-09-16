using System.Collections.Generic;
using UnityEngine;

// P1L4: diagramas de esfuerzos del elemento seleccionado.
// - Tecla M o boton "M Diagramas": activa/desactiva.
// - Botones MOMENTO / AXIAL / CORTE: elige que diagrama(s) se dibujan.
// Dibuja hasta 3 diagramas como polilineas en 3D sobre el elemento:
//   * Momento (magenta): perfil lineal de M_resultante = hypot(My, Mz).
//   * Axial (verde): perfil lineal de N interno (compresion<0, traccion>0).
//   * Corte (naranja): perfil lineal de V_resultante = hypot(Vy, Vz).
// El perfil es LINEAL entre extremos (valores de analysis.fuerzas_elementos
// desde results.forces del caso activo): exacto para columnas/muros sin carga
// en el claro y aproximado para vigas con q_G (documentado en README).
// Escala grafica RELATIVA a la longitud del elemento (pico ~25% de la
// longitud, minimo 1.0 m) para que el diagrama sea claramente visible en la
// escala del modelo. Las direcciones de desplazamiento usan los EJES LOCALES
// exportados del JSON (ejes_locales.x/y/z), igual que LocalAxesController.
public class ForceDiagramController : MonoBehaviour
{
    private ModelLoader loader;
    private SelectionController selection;
    private bool active;
    private bool showMoment = true;
    private bool showAxial = true;
    private bool showShear = true;
    private int drawnTag = -1;
    private GameObject diagramsRoot;

    private Material magenta;
    private Material green;
    private Material orange;
    private Material grey;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        selection = FindObjectOfType<SelectionController>();
        CreateMaterials();
    }

    void OnEnable()
    {
        ModelLoader.CaseChanged += HandleCaseChanged;
    }

    void OnDisable()
    {
        ModelLoader.CaseChanged -= HandleCaseChanged;
    }

    // P1L4: al cambiar el caso activo se redibujan los diagramas con las
    // fuerzas del nuevo caso (analysis.fuerzas_elementos es reconstruido).
    void HandleCaseChanged(string caseKey)
    {
        if (active) Refresh();
    }

    void CreateMaterials()
    {
        magenta = new Material(Shader.Find("Sprites/Default"));
        magenta.color = new Color(1f, 0.2f, 1f);
        green = new Material(Shader.Find("Sprites/Default"));
        green.color = new Color(0.2f, 0.9f, 0.35f);
        orange = new Material(Shader.Find("Sprites/Default"));
        orange.color = new Color(1f, 0.6f, 0.1f);
        grey = new Material(Shader.Find("Sprites/Default"));
        grey.color = new Color(0.6f, 0.6f, 0.6f);
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.M)) Toggle();
        if (active && selection != null &&
            (selection.SelectedTag != drawnTag || selection.SelectedTag < 0))
            Refresh();
    }

    void Toggle()
    {
        active = !active;
        if (!active)
            Clear();
        else
            Refresh();
    }

    void Refresh()
    {
        Clear();
        if (!active || selection == null || selection.SelectedTag < 0) return;
        if (loader == null || loader.modelData == null) return;

        int tag = selection.SelectedTag;
        ElementInternalForceData f = null;
        if (loader.modelData.analysis != null &&
            loader.modelData.analysis.fuerzas_elementos != null)
        {
            foreach (var e in loader.modelData.analysis.fuerzas_elementos)
                if (e.elementTag == tag) { f = e; break; }
        }
        if (f == null || f.F_i == null || f.F_j == null || f.F_i.Length < 6) return;

        Vector3 posI, posJ;
        if (!TryGetEnds(tag, out posI, out posJ)) return;

        diagramsRoot = new GameObject("Diagrams_" + tag);

        Vector3 dir = (posJ - posI);
        float len = dir.magnitude;
        if (len < 0.001f) return;
        dir /= len;

        // P1L4: direcciones de desplazamiento = EJES LOCALES exportados del
        // elemento (ejes_locales.x/y/z), misma logica que LocalAxesController.
        Vector3 localY, localZ;
        GetLocalFrame(tag, dir, out localY, out localZ);

        // vectores de fuerza por extremo
        float mI = Mathf.Sqrt(f.F_i[4] * f.F_i[4] + f.F_i[5] * f.F_i[5]);
        float mJ = Mathf.Sqrt(f.F_j[4] * f.F_j[4] + f.F_j[5] * f.F_j[5]);
        float nI = -f.F_i[0];           // interno
        float nJ = f.F_j[0];            // interno (traccion+, compresion-)
        float vI = Mathf.Sqrt(f.F_i[1] * f.F_i[1] + f.F_i[2] * f.F_i[2]);
        float vJ = Mathf.Sqrt(f.F_j[1] * f.F_j[1] + f.F_j[2] * f.F_j[2]);

        float maxMag = Mathf.Max(Mathf.Max(mI, mJ), Mathf.Max(Mathf.Max(Mathf.Abs(nI), Mathf.Abs(nJ)), Mathf.Max(vI, vJ)));
        // Escala grafica RELATIVA a la longitud del elemento: el pico del
        // diagrama se desplaza ~25% de la longitud (minimo 1.0 m). Si el valor
        // maximo es ~nulo (maxMag < 1e-3) se deja k=0 (sin desplegar perfiles).
        float peak = Mathf.Max(0.25f * len, 1.0f);
        float k = maxMag > 1e-3f ? peak / maxMag : 0f;

        // linea base
        DrawBaseLine(posI, posJ);

        // momento (magnitud resultante, sin signo) -> eje local Z
        if (showMoment && k > 0f)
            DrawProfile("M (resultante My,Mz)", posI, posJ, localZ,
                        mI * k, mJ * k, magenta, new Vector2(mI, mJ));

        // axial (interno) -> -eje local Z
        if (showAxial && k > 0f)
            DrawProfile("N (interno)", posI, posJ, -localZ,
                        nI * k, nJ * k, green, new Vector2(nI, nJ));

        // corte (resultante Vy,Vz) -> eje local Y
        if (showShear && k > 0f)
            DrawProfile("V (resultante Vy,Vz)", posI, posJ, localY,
                        vI * k, vJ * k, orange, new Vector2(vI, vJ));

        drawnTag = tag;
    }

    void GetLocalFrame(int tag, Vector3 dir, out Vector3 localY, out Vector3 localZ)
    {
        ElementRef r = null;
        if (loader.elementRefs != null && loader.elementRefs.TryGetValue(tag, out r)
            && r.ejes_locales != null
            && r.ejes_locales.x != null && r.ejes_locales.x.Length >= 3
            && r.ejes_locales.y != null && r.ejes_locales.y.Length >= 3
            && r.ejes_locales.z != null && r.ejes_locales.z.Length >= 3)
        {
            Vector3 x = ModelLoader.StructToUnity(
                r.ejes_locales.x[0], r.ejes_locales.x[1], r.ejes_locales.x[2]).normalized;
            localY = ModelLoader.StructToUnity(
                r.ejes_locales.y[0], r.ejes_locales.y[1], r.ejes_locales.y[2]).normalized;
            localZ = ModelLoader.StructToUnity(
                r.ejes_locales.z[0], r.ejes_locales.z[1], r.ejes_locales.z[2]).normalized;
            if (Vector3.Dot(x, dir) < 0f)
            {
                localY = -localY;
                localZ = -localZ;
            }
        }
        else
        {
            Vector3 perp = Vector3.Cross(Vector3.up, dir);
            if (perp.sqrMagnitude < 0.001f)
                perp = Vector3.Cross(Vector3.forward, dir);
            localZ = perp.normalized;
            localY = Vector3.Cross(localZ, dir).normalized;
        }
    }

    bool TryGetEnds(int tag, out Vector3 posI, out Vector3 posJ)
    {
        int nodeI = -1, nodeJ = -1;
        if (loader.modelData.beams != null)
            foreach (var b in loader.modelData.beams)
                if (b.elementTag == tag) { nodeI = b.node_i; nodeJ = b.node_j; break; }
        if (nodeI < 0 && loader.modelData.columns != null)
            foreach (var c in loader.modelData.columns)
                if (c.elementTag == tag) { nodeI = c.node_i; nodeJ = c.node_j; break; }
        if (nodeI < 0 && loader.modelData.walls != null)
            foreach (var w in loader.modelData.walls)
                if (w.elementTag == tag) { nodeI = w.node_i; nodeJ = w.node_j; break; }

        posI = posJ = Vector3.zero;
        if (nodeI < 0) return false;
        if (!loader.nodeObjects.ContainsKey(nodeI) || !loader.nodeObjects.ContainsKey(nodeJ))
            return false;
        posI = loader.nodeObjects[nodeI].transform.position;
        posJ = loader.nodeObjects[nodeJ].transform.position;
        return true;
    }

    void DrawBaseLine(Vector3 a, Vector3 b)
    {
        GameObject go = new GameObject("baseline");
        go.transform.SetParent(diagramsRoot.transform);
        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = grey;
        lr.startColor = new Color(0.6f, 0.6f, 0.6f, 0.7f);
        lr.endColor = lr.startColor;
        lr.startWidth = 0.015f;
        lr.endWidth = 0.015f;
        lr.useWorldSpace = true;
        lr.positionCount = 2;
        lr.SetPosition(0, a);
        lr.SetPosition(1, b);
    }

    void DrawProfile(string name, Vector3 a, Vector3 b, Vector3 normal,
                     float valI, float valJ, Material mat, Vector2 vals)
    {
        GameObject go = new GameObject("diag_" + name);
        go.transform.SetParent(diagramsRoot.transform);
        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = mat;
        lr.startColor = mat.color;
        lr.endColor = mat.color;
        lr.startWidth = 0.07f;
        lr.endWidth = 0.07f;
        lr.useWorldSpace = true;
        lr.positionCount = 2;
        lr.SetPosition(0, a + normal * valI);
        lr.SetPosition(1, b + normal * valJ);

        AddLabel(name, (a + b) * 0.5f + normal * (valI + valJ) * 0.5f
                 + normal * 0.15f);
        AddLabel($"{vals.x:F1} @ i  /  {vals.y:F1} @ j",
                 (a + b + (normal * (valI + valJ)) * 2f) * 0.5f + normal * 0.25f);
    }

    void AddLabel(string text, Vector3 pos)
    {
        GameObject go = new GameObject("lbl_" + text.Replace(' ', '_'));
        go.transform.SetParent(diagramsRoot.transform);
        go.transform.position = pos;
        TextMesh tm = go.AddComponent<TextMesh>();
        tm.text = text;
        tm.characterSize = 0.3f;
        tm.fontSize = 40;
        tm.anchor = TextAnchor.LowerLeft;
        tm.alignment = TextAlignment.Left;
        tm.color = Color.white;
    }

    void Clear()
    {
        if (diagramsRoot != null) Destroy(diagramsRoot);
        diagramsRoot = null;
        drawnTag = -1;
    }

    void OnDestroy()
    {
        Clear();
    }

    void OnGUI()
    {
        GUILayout.BeginArea(new Rect(Screen.width - 250, 150, 240, 130));
        GUILayout.BeginVertical("box");
        if (GUILayout.Button($"M Diagramas         [{(active ? "ON" : "OFF")}]"))
            Toggle();
        if (active)
        {
            GUILayout.BeginHorizontal();
            bool m = GUILayout.Toggle(showMoment, "MOMENTO");
            bool n = GUILayout.Toggle(showAxial, "AXIAL");
            bool v = GUILayout.Toggle(showShear, "CORTE");
            GUILayout.EndHorizontal();
            if (m != showMoment || n != showAxial || v != showShear)
            {
                showMoment = m;
                showAxial = n;
                showShear = v;
                Refresh();
            }
            GUILayout.Label("Magenta=M | Verde=N | Naranja=V");
        }
        GUILayout.EndVertical();
        GUILayout.EndArea();
    }
}