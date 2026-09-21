using System.Collections.Generic;
using UnityEngine;

public class IdLabelController : MonoBehaviour
{
    private bool showNodeIds;
    private bool showElementIds;
    private bool initialized;
    private float labelCharHeight = 0.3f;

    private List<GameObject> nodeLabels = new List<GameObject>();
    private List<GameObject> elementLabels = new List<GameObject>();
    public bool ShowNodeIds => showNodeIds;
    public bool ShowElementIds => showElementIds;

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.N)) ToggleNodeIds();
        if (Input.GetKeyDown(KeyCode.E)) ToggleElementIds();
    }

    void OnGUI()
    {
        return; // controles centralizados en ViewerHUD
#pragma warning disable CS0162
        GUILayout.BeginArea(new Rect(Screen.width - 220, 10, 210, 80));
        GUILayout.BeginVertical("box");
        GUILayout.Label("<b>Etiquetas</b>");
        if (GUILayout.Button($"N IDs Nodos    [{BoolStr(showNodeIds)}]"))    ToggleNodeIds();
        if (GUILayout.Button($"E IDs Elementos [{BoolStr(showElementIds)}]")) ToggleElementIds();
        GUILayout.EndVertical();
        GUILayout.EndArea();
#pragma warning restore CS0162
    }

    string BoolStr(bool v) { return v ? "ON" : "OFF"; }

    public void ToggleNodeIds()
    {
        showNodeIds = !showNodeIds;
        EnsureInitialized();
        foreach (var go in nodeLabels)
            if (go != null) go.SetActive(showNodeIds);
    }

    public void ToggleElementIds()
    {
        showElementIds = !showElementIds;
        EnsureInitialized();
        foreach (var go in elementLabels)
            if (go != null) go.SetActive(showElementIds);
    }

    void EnsureInitialized()
    {
        if (initialized) return;
        InitializeLabels();
        initialized = true;
    }

    void InitializeLabels()
    {
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null) return;

        GameObject labelsRoot = new GameObject("Labels");

        CreateNodeLabels(loader, labelsRoot.transform);
        CreateElementLabels(loader, labelsRoot.transform, loader.modelData.beams, "Beam");
        CreateElementLabels(loader, labelsRoot.transform, loader.modelData.columns, "Col");
        CreateElementLabels(loader, labelsRoot.transform, loader.modelData.walls, "Wall");
    }

    void CreateNodeLabels(ModelLoader loader, Transform parent)
    {
        if (loader.modelData.nodes == null) return;

        foreach (var node in loader.modelData.nodes)
        {
            if (!loader.nodeObjects.ContainsKey(node.tag)) continue;

            Vector3 pos = loader.nodeObjects[node.tag].transform.position;
            pos.y += labelCharHeight;

            GameObject go = CreateLabelObject($"Lbl_node_{node.tag}", pos, parent);
            TextMesh tm = go.GetComponent<TextMesh>();
            tm.text = node.tag.ToString();
            tm.color = new Color(0.1f, 0.1f, 0.1f);

            CreateShadow(go.transform, tm.text, labelCharHeight);

            nodeLabels.Add(go);
            go.SetActive(showNodeIds);
        }
    }

    void CreateElementLabels(ModelLoader loader, Transform parent,
                             object[] elements, string prefix)
    {
        Dictionary<int, GameObject> objectMap;
        List<int> tags = new List<int>();

        if (prefix == "Beam" && loader.modelData.beams != null)
        {
            objectMap = loader.beamObjects;
            foreach (var b in loader.modelData.beams) tags.Add(b.elementTag);
        }
        else if (prefix == "Col" && loader.modelData.columns != null)
        {
            objectMap = loader.columnObjects;
            foreach (var c in loader.modelData.columns) tags.Add(c.elementTag);
        }
        else if (prefix == "Wall" && loader.modelData.walls != null)
        {
            objectMap = loader.wallObjects;
            foreach (var w in loader.modelData.walls) tags.Add(w.elementTag);
        }
        else return;

        foreach (int tag in tags)
        {
            if (!objectMap.ContainsKey(tag) || objectMap[tag] == null) continue;

            Vector3 pos = objectMap[tag].transform.position;
            pos.y += labelCharHeight;

            GameObject go = CreateLabelObject($"Lbl_{prefix}_{tag}", pos, parent);
            TextMesh tm = go.GetComponent<TextMesh>();
            tm.text = tag.ToString();
            tm.color = new Color(0.15f, 0.15f, 0.45f);

            elementLabels.Add(go);
            go.SetActive(showElementIds);
        }
    }

    GameObject CreateLabelObject(string name, Vector3 position, Transform parent)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(parent);
        go.transform.position = position;

        TextMesh tm = go.AddComponent<TextMesh>();
        tm.characterSize = labelCharHeight;
        tm.fontSize = 48;
        tm.anchor = TextAnchor.MiddleCenter;
        tm.alignment = TextAlignment.Center;

        return go;
    }

    void CreateShadow(Transform parent, string text, float size)
    {
        GameObject shadow = new GameObject("Shadow");
        shadow.transform.SetParent(parent);
        shadow.transform.localPosition = new Vector3(0.01f, -0.01f, 0.01f);

        TextMesh tm = shadow.AddComponent<TextMesh>();
        tm.text = text;
        tm.characterSize = size;
        tm.fontSize = 48;
        tm.anchor = TextAnchor.MiddleCenter;
        tm.alignment = TextAlignment.Center;
        tm.color = new Color(0.85f, 0.85f, 0.85f, 0.5f);
    }
}
