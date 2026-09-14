using System.Collections.Generic;
using UnityEngine;

// P1L4: visualiza la deformada usando analysis.desplazamientos del JSON.
// - Tecla D: activa/desactiva.
// - Teclas + / -: ajustar factor de escala.
// Mueve nodos y elementos (vigas/columnas/muros) y reconstruye los
// constraintLinks (dashed) con las posiciones deformadas. Los diafragmas se
// mantienen en su plano (rigidez de plano) mientras la deformada esta activa
// (limitacion documentada en README).
public class DeformedShapeController : MonoBehaviour
{
    private const float MinScale = 10f;
    private const float MaxScale = 1000f;

    private ModelLoader loader;
    private bool active;
    private bool built;
    private float scale = 100f;

    private Dictionary<int, Vector3> baseNodePos = new Dictionary<int, Vector3>();
    private Dictionary<int, Vector3> nodeDisp = new Dictionary<int, Vector3>();
    private List<DeformElem> elements = new List<DeformElem>();
    private List<LinkRef> links = new List<LinkRef>();

    class DeformElem
    {
        public GameObject go;
        public int nodeI;
        public int nodeJ;
        public float baseLength;
        public float baseThickness;
    }

    class LinkRef
    {
        public int nodoMuro;
        public int nodoMaestro;
        public Vector3 baseA;
        public Vector3 baseB;
    }

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
    }

    void OnEnable()
    {
        ModelLoader.CaseChanged += HandleCaseChanged;
    }

    void OnDisable()
    {
        ModelLoader.CaseChanged -= HandleCaseChanged;
    }

    // P1L4: al cambiar el caso activo se recapturan los DESPLAZAMIENTOS del
    // caso (analysis.desplazamientos es reconstruido por SetActiveCase). Las
    // posiciones base (sin deformar) NO se recapturan, de modo que el factor
    // de escala nunca se acumula sobre una deformada previa.
    void HandleCaseChanged(string caseKey)
    {
        if (!built) return;
        nodeDisp.Clear();
        CaptureDisplacements();
        if (active) Apply();
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.D)) Toggle();
        if (active)
        {
            if (Input.GetKeyDown(KeyCode.Plus) || Input.GetKeyDown(KeyCode.KeypadPlus))
                AdjustScale(1.2f);
            if (Input.GetKeyDown(KeyCode.Minus) || Input.GetKeyDown(KeyCode.KeypadMinus))
                AdjustScale(1f / 1.2f);
        }
    }

    void Toggle()
    {
        if (loader == null || loader.modelData == null) return;
        active = !active;
        if (active) EnsureBuilt();
        Apply();
    }

    void AdjustScale(float factor)
    {
        scale = Mathf.Clamp(scale * factor, MinScale, MaxScale);
        if (active) Apply();
    }

    void EnsureBuilt()
    {
        if (built || loader.modelData == null) return;
        CaptureBase();
        CaptureDisplacements();
        CaptureElements();
        CaptureLinks();
        built = true;
    }

    void CaptureBase()
    {
        foreach (var kv in loader.nodeObjects)
            if (kv.Value != null) baseNodePos[kv.Key] = kv.Value.transform.position;
        foreach (var kv in loader.masterNodeObjects)
            if (kv.Value != null) baseNodePos[kv.Key] = kv.Value.transform.position;
    }

    void CaptureDisplacements()
    {
        nodeDisp.Clear();
        var dis = loader.modelData.analysis != null
            ? loader.modelData.analysis.desplazamientos : null;
        if (dis == null) return;
        foreach (var kv in dis)
        {
            if (kv.Value == null || kv.Value.Length < 3) continue;
            // StructToUnity(x,y,z) = (x, z, -y); aplicado al desplazamiento.
            Vector3 off = ModelLoader.StructToUnity(kv.Value[0], kv.Value[1], kv.Value[2]);
            nodeDisp[kv.Key] = off;
        }
    }

    void CaptureElements()
    {
        if (loader.modelData.beams != null)
            foreach (var b in loader.modelData.beams)
                AddElem(loader.beamObjects, b.elementTag, b.node_i, b.node_j);
        if (loader.modelData.columns != null)
            foreach (var c in loader.modelData.columns)
                AddElem(loader.columnObjects, c.elementTag, c.node_i, c.node_j);
        if (loader.modelData.walls != null)
            foreach (var w in loader.modelData.walls)
                AddElem(loader.wallObjects, w.elementTag, w.node_i, w.node_j);
    }

    void AddElem(Dictionary<int, GameObject> map, int tag, int nodeI, int nodeJ)
    {
        if (!map.ContainsKey(tag) || map[tag] == null) return;
        if (!baseNodePos.ContainsKey(nodeI) || !baseNodePos.ContainsKey(nodeJ)) return;
        Vector3 a = baseNodePos[nodeI];
        Vector3 b = baseNodePos[nodeJ];
        elements.Add(new DeformElem
        {
            go = map[tag], nodeI = nodeI, nodeJ = nodeJ,
            baseLength = (b - a).magnitude,
            baseThickness = map[tag].transform.localScale.x,
        });
    }

    void CaptureLinks()
    {
        if (loader.modelData.constraint_links == null) return;
        foreach (var l in loader.modelData.constraint_links)
        {
            if (baseNodePos.TryGetValue(l.nodo_maestro_retained, out var a)
                && baseNodePos.TryGetValue(l.nodo_muro, out var b))
            {
                links.Add(new LinkRef
                {
                    nodoMuro = l.nodo_muro,
                    nodoMaestro = l.nodo_maestro_retained,
                    baseA = a, baseB = b,
                });
            }
        }
    }

    Vector3 NodePos(int tag)
    {
        Vector3 basePos = baseNodePos.ContainsKey(tag) ? baseNodePos[tag] : Vector3.zero;
        if (!active) return basePos;
        Vector3 off = nodeDisp.ContainsKey(tag) ? nodeDisp[tag] : Vector3.zero;
        return basePos + off * scale;
    }

    void Apply()
    {
        if (!built) return;

        // nodos (estructurales y masters)
        foreach (var kv in baseNodePos)
        {
            GameObject go = null;
            if (loader.nodeObjects.ContainsKey(kv.Key)) go = loader.nodeObjects[kv.Key];
            else if (loader.masterNodeObjects.ContainsKey(kv.Key)) go = loader.masterNodeObjects[kv.Key];
            if (go != null) go.transform.position = NodePos(kv.Key);
        }

        // elementos
        foreach (var e in elements)
        {
            if (e.go == null) continue;
            Vector3 posI = NodePos(e.nodeI);
            Vector3 posJ = NodePos(e.nodeJ);
            Vector3 dir = posJ - posI;
            e.go.transform.position = (posI + posJ) * 0.5f;
            e.go.transform.localScale = new Vector3(e.baseThickness, e.baseThickness,
                                                    active && dir.sqrMagnitude > 1e-12f
                                                        ? dir.magnitude : e.baseLength);
            if (dir.sqrMagnitude > 1e-8f)
                e.go.transform.rotation = Quaternion.FromToRotation(Vector3.forward, dir);
        }

        // constraintLinks (rigidLink de muros): reconstruir linea punteada
        if (loader.modelData.constraint_links != null && links.Count > 0)
        {
            foreach (var rl in links)
            {
                if (!loader.constraintLinkObjects.ContainsKey(rl.nodoMuro)) continue;
                GameObject go = loader.constraintLinkObjects[rl.nodoMuro];
                if (go == null) continue;
                LineRenderer lr = go.GetComponent<LineRenderer>();
                if (lr != null) DashLine(lr, NodePos(rl.nodoMaestro), NodePos(rl.nodoMuro));
            }
        }
    }

    void DashLine(LineRenderer lr, Vector3 a, Vector3 b)
    {
        Vector3 dir = b - a;
        float length = dir.magnitude;
        if (length < 0.001f) { lr.positionCount = 0; return; }
        int segments = Mathf.Max(8, Mathf.RoundToInt(length / 0.5f));
        float dashLen = Mathf.Max(length / segments * 0.6f, 0.05f);
        float gapLen = Mathf.Max(length / segments * 0.4f, 0.04f);
        var pts = new List<Vector3>();
        float covered = 0f;
        int guard = 0;
        while (covered < length && guard < 512)
        {
            float d0 = Mathf.Min(covered, length);
            float d1 = Mathf.Min(covered + dashLen, length);
            if (d1 > d0){ pts.Add(a + dir * (d0 / length)); pts.Add(a + dir * (d1 / length)); }
            covered = d1 + gapLen;
            guard++;
        }
        lr.positionCount = pts.Count;
        for (int i = 0; i < pts.Count; i++) lr.SetPosition(i, pts[i]);
    }

    void OnGUI()
    {
        GUILayout.BeginArea(new Rect(Screen.width - 220, 100, 210, 64));
        GUILayout.BeginVertical("box");
        GUILayout.Label($"D Deformada          [{active ? "ON" : "OFF"}]");
        if (active) GUILayout.Label($"Escala: x{scale:F0}  (+ / - ajustar)");
        GUILayout.EndVertical();
        GUILayout.EndArea();
    }
}