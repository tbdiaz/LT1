using System.Collections.Generic;
using UnityEngine;

// Superposicion de la deformada sobre el modelo sin deformar. Los valores
// provienen exclusivamente de results.displacements[caso]; scale es solo un
// factor grafico. Mantener ambas formas visibles hace inequívoco el cambio.
public class DeformedShapeController : MonoBehaviour
{
    const float MinScale = 10f;
    const float MaxScale = 2000f;

    ModelLoader loader;
    GameObject root;
    Material material;
    bool active;
    float scale = 100f;

    public bool Active => active;
    public float ScaleFactor => scale;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        material = new Material(Shader.Find("Sprites/Default"));
        material.color = new Color(1f, 0.15f, 0.05f, 1f);
    }

    void OnEnable() { ModelLoader.CaseChanged += HandleCaseChanged; }
    void OnDisable() { ModelLoader.CaseChanged -= HandleCaseChanged; }

    void HandleCaseChanged(string caseKey)
    {
        if (active) Rebuild();
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.D)) Toggle();
        if (!active) return;
        if (Input.GetKeyDown(KeyCode.Plus) || Input.GetKeyDown(KeyCode.KeypadPlus))
            ScaleUp();
        if (Input.GetKeyDown(KeyCode.Minus) || Input.GetKeyDown(KeyCode.KeypadMinus))
            ScaleDown();
    }

    public void Toggle()
    {
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null) return;
        active = !active;
        if (active) Rebuild(); else Clear();
    }

    public void ScaleUp() { AdjustScale(1.35f); }
    public void ScaleDown() { AdjustScale(1f / 1.35f); }

    void AdjustScale(float factor)
    {
        scale = Mathf.Clamp(scale * factor, MinScale, MaxScale);
        if (active) Rebuild();
    }

    void Rebuild()
    {
        Clear();
        if (loader == null || loader.modelData == null ||
            loader.modelData.analysis == null ||
            loader.modelData.analysis.desplazamientos == null) return;

        root = new GameObject("DEFORMADA_" + loader.activeCase + "_x" + scale.ToString("F0"));

        foreach (var b in loader.modelData.beams)
            AddElement("Def_B_" + b.elementTag, b.node_i, b.node_j);
        foreach (var c in loader.modelData.columns)
            AddElement("Def_C_" + c.elementTag, c.node_i, c.node_j);
        foreach (var w in loader.modelData.walls)
            AddElement("Def_W_" + w.elementTag, w.node_i, w.node_j);
    }

    void AddElement(string name, int nodeI, int nodeJ)
    {
        if (!TryDeformedPosition(nodeI, out var a) ||
            !TryDeformedPosition(nodeJ, out var b)) return;

        GameObject go = new GameObject(name);
        go.transform.SetParent(root.transform);
        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = material;
        lr.startColor = material.color;
        lr.endColor = new Color(1f, 0.85f, 0.05f, 1f);
        lr.startWidth = 0.14f;
        lr.endWidth = 0.14f;
        lr.numCapVertices = 4;
        lr.positionCount = 2;
        lr.useWorldSpace = true;
        lr.SetPosition(0, a);
        lr.SetPosition(1, b);
    }

    bool TryDeformedPosition(int tag, out Vector3 position)
    {
        position = Vector3.zero;
        GameObject node;
        if (!loader.nodeObjects.TryGetValue(tag, out node) &&
            !loader.masterNodeObjects.TryGetValue(tag, out node)) return false;
        if (node == null) return false;

        // Los objetos del modelo permanecen en la posicion no deformada.
        position = node.transform.position;
        if (!loader.modelData.analysis.desplazamientos.TryGetValue(tag, out var u) ||
            u == null || u.Length < 3) return true;
        position += ModelLoader.StructToUnity(u[0], u[1], u[2]) * scale;
        return true;
    }

    void Clear()
    {
        if (root != null) Destroy(root);
        root = null;
    }

    void OnDestroy()
    {
        Clear();
        if (material != null) Destroy(material);
    }
}
