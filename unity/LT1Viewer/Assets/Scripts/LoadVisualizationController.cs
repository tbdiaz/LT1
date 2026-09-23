using System.Collections.Generic;
using UnityEngine;

// Capa grafica de cargas del caso activo. Para G/Q se agrega la carga por
// elementTag y se dibuja una flecha vertical representativa por viga; EX/EY
// se dibujan en los nodos master con su direccion global real.
public class LoadVisualizationController : MonoBehaviour
{
    private ModelLoader loader;
    private ScenarioModificationController scenario;
    private GameObject root;
    private bool active;
    public bool Active => active;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        scenario = FindObjectOfType<ScenarioModificationController>();
    }
    void OnEnable() { ModelLoader.CaseChanged += OnCaseChanged; }
    void OnDisable() { ModelLoader.CaseChanged -= OnCaseChanged; }
    void OnCaseChanged(string c) { if (active) Rebuild(); }

    public void Toggle()
    {
        active = !active;
        if (active) Rebuild(); else Clear();
    }

    public void Show()
    {
        active = true;
        Rebuild();
    }

    public void Rebuild()
    {
        Clear();
        // En escenas antiguas los controladores se agregan en runtime y su
        // orden de Start no esta garantizado. Recuperar referencias aqui
        // asegura que el factor aplicado se use inmediatamente.
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        if (scenario == null) scenario = FindObjectOfType<ScenarioModificationController>();
        if (!active || loader == null || loader.combinedRoot == null ||
            loader.combinedRoot.loads == null) return;
        root = new GameObject("AppliedLoads_" + loader.activeCase);
        if (loader.activeCase == "EX" || loader.activeCase == "EY")
        {
            DrawLateral(loader.activeCase == "EX" ? loader.combinedRoot.loads.EX
                                                   : loader.combinedRoot.loads.EY);
            return;
        }
        if (loader.activeCase == "G") DrawBeamLoads(loader.combinedRoot.loads.G, null);
        else if (loader.activeCase == "Q") DrawBeamLoads(loader.combinedRoot.loads.Q, null);
        else if (loader.activeCase == "COMBO_R")
            DrawBeamLoads(loader.combinedRoot.loads.G, loader.combinedRoot.loads.Q);
    }

    void DrawBeamLoads(CombinedBeamLoad[] first, CombinedBeamLoad[] second)
    {
        var totals = new Dictionary<int, float>();
        Accumulate(first, totals);
        Accumulate(second, totals);
        float max = 0f;
        foreach (var v in totals.Values) max = Mathf.Max(max, v);
        Material mat = MakeMaterial(loader.activeCase == "Q"
            ? new Color(0.2f, 1f, 0.35f) : new Color(0.1f, 0.85f, 1f));
        float factor = scenario != null ? scenario.CurrentLoadFactor : 1f;
        float visualFactor = Mathf.Clamp(factor, 0f, 4f);
        foreach (var kv in totals)
        {
            if (!loader.beamObjects.TryGetValue(kv.Key, out var beam) || beam == null) continue;
            float length = (max > 0f ? Mathf.Lerp(0.55f, 2.6f, Mathf.Sqrt(kv.Value / max)) : 0.8f)
                           * visualFactor;
            Vector3 tip = beam.transform.position + Vector3.up * 0.18f;
            DrawArrow(tip + Vector3.up * length, tip, mat, 0.055f);
        }
    }

    void Accumulate(CombinedBeamLoad[] loads, Dictionary<int, float> totals)
    {
        if (loads == null) return;
        foreach (var l in loads)
        {
            float value;
            if (!string.IsNullOrEmpty(l.tipo) && l.tipo.ToLowerInvariant().Contains("uniform"))
                value = Mathf.Abs(l.w_kN_m) * Mathf.Max(l.L_m, 1f);
            else value = Mathf.Abs(l.q_kN);
            if (!totals.ContainsKey(l.element_tag)) totals[l.element_tag] = 0f;
            totals[l.element_tag] += value;
        }
    }

    void DrawLateral(CombinedLateralLoad[] loads)
    {
        if (loads == null) return;
        float max = 0f;
        foreach (var l in loads) max = Mathf.Max(max, Mathf.Sqrt(l.fx_kN*l.fx_kN + l.fy_kN*l.fy_kN));
        Material mat = MakeMaterial(new Color(1f, 0.18f, 0.12f));
        float factor = scenario != null ? scenario.CurrentLoadFactor : 1f;
        float visualFactor = Mathf.Clamp(factor, 0f, 4f);
        foreach (var l in loads)
        {
            if (!loader.nodeObjects.TryGetValue(l.node_tag, out var node) || node == null) continue;
            Vector3 d = ModelLoader.StructToUnity(l.fx_kN, l.fy_kN, 0f);
            float mag = d.magnitude;
            if (mag < 1e-8f) continue;
            float length = (max > 0f ? Mathf.Lerp(1.2f, 4.0f, mag / max) : 1.2f)
                           * visualFactor;
            DrawArrow(node.transform.position, node.transform.position + d.normalized * length, mat, 0.11f);
        }
    }

    void DrawArrow(Vector3 start, Vector3 tip, Material mat, float width)
    {
        Vector3 d = tip - start;
        if (d.sqrMagnitude < 1e-8f) return;
        Vector3 side = Vector3.Cross(d.normalized, Vector3.up);
        if (side.sqrMagnitude < 0.01f) side = Vector3.right;
        side.Normalize();
        Vector3 back = tip - d.normalized * Mathf.Min(0.35f, d.magnitude * 0.25f);
        var go = new GameObject("LoadArrow");
        go.transform.SetParent(root.transform);
        var lr = go.AddComponent<LineRenderer>();
        lr.material = mat;
        lr.startColor = mat.color;
        lr.endColor = mat.color;
        lr.startWidth = width;
        lr.endWidth = width;
        lr.useWorldSpace = true;
        lr.positionCount = 5;
        lr.SetPositions(new[] { start, tip, back + side * 0.18f, tip, back - side * 0.18f });
    }

    Material MakeMaterial(Color c)
    {
        var m = new Material(Shader.Find("Sprites/Default"));
        m.color = c;
        return m;
    }

    void Clear() { if (root != null) Destroy(root); root = null; }
    void OnDestroy() { Clear(); }
}
