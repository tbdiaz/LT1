using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;

public class ModelLoader : MonoBehaviour
{
    public string jsonFileName = "modelo_lt1.json";

    [HideInInspector] public ModelRoot modelData;
    [HideInInspector] public Dictionary<int, GameObject> nodeObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> beamObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> columnObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> wallObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> constraintLinkObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> supportObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> masterNodeObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Vector3 modelCenter;

    private Material beamMaterial;
    private Material columnMaterial;
    private Material supportMaterial;
    private Material nodeMaterial;
    private Material masterMaterial;
    private Material diaphragmMaterial;
    private Material wallMaterial;
    private Material constraintLinkMaterial;

    public static Vector3 StructToUnity(float x, float y, float z)
    {
        return new Vector3(x, z, -y);
    }

    void Awake()
    {
        CreateMaterials();
    }

    void CreateMaterials()
    {
        beamMaterial = CreateMaterial(new Color(0.44f, 0.56f, 0.69f));
        columnMaterial = CreateMaterial(new Color(0.56f, 0.56f, 0.56f));
        supportMaterial = CreateMaterial(new Color(0.80f, 0.20f, 0.20f));
        nodeMaterial = CreateMaterial(new Color(0.17f, 0.42f, 0.69f));
        masterMaterial = CreateMaterial(new Color(1.0f, 0.84f, 0.0f));
        diaphragmMaterial = CreateTransparentMaterial(new Color(0.5f, 0.8f, 0.5f, 0.25f));
        wallMaterial = CreateMaterial(new Color(0.61f, 0.11f, 0.13f));
        constraintLinkMaterial = new Material(Shader.Find("Sprites/Default"));
        constraintLinkMaterial.color = new Color(0.0f, 0.85f, 0.90f);
    }

    Material CreateMaterial(Color color)
    {
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = color;
        return mat;
    }

    Material CreateTransparentMaterial(Color color)
    {
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = color;
        mat.SetFloat("_Mode", 3f);
        mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        mat.SetInt("_ZWrite", 0);
        mat.DisableKeyword("_ALPHATEST_ON");
        mat.EnableKeyword("_ALPHABLEND_ON");
        mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        mat.renderQueue = 3000;
        return mat;
    }

    public bool LoadModel()
    {
        string jsonPath = FindJsonPath();
        if (string.IsNullOrEmpty(jsonPath))
        {
            Debug.LogError($"[LT1Viewer] JSON file not found: {jsonFileName}");
            return false;
        }

        Debug.Log($"[LT1Viewer] Loading model from: {jsonPath}");
        string json = File.ReadAllText(jsonPath);

        modelData = JsonUtility.FromJson<ModelRoot>(json);
        if (modelData == null)
        {
            Debug.LogError("[LT1Viewer] Failed to parse JSON model data");
            return false;
        }

        ParseAnalysisDictionaries(json);

        Debug.Log($"[LT1Viewer] Model parsed: {modelData.nodes.Length} nodes, " +
                  $"{modelData.beams.Length} beams, {modelData.columns.Length} columns, " +
                  $"{modelData.walls.Length} walls, " +
                  $"{modelData.constraint_links.Length} constraintLinks, " +
                  $"{modelData.supports.Length} supports, {modelData.diaphragms.Length} diaphragms");

        return true;
    }

    public void BuildScene()
    {
        if (modelData == null) return;

        GameObject structure = new GameObject("Structure");
        GameObject nodesParent = new GameObject("Nodes");
        GameObject beamsParent = new GameObject("Beams");
        GameObject columnsParent = new GameObject("Columns");
        GameObject wallsParent = new GameObject("Walls");
        GameObject constraintLinksParent = new GameObject("ConstraintLinks");
        GameObject supportsParent = new GameObject("Supports");
        GameObject diaphragmsParent = new GameObject("Diaphragms");

        nodesParent.transform.SetParent(structure.transform);
        beamsParent.transform.SetParent(structure.transform);
        columnsParent.transform.SetParent(structure.transform);
        wallsParent.transform.SetParent(structure.transform);
        constraintLinksParent.transform.SetParent(structure.transform);
        supportsParent.transform.SetParent(structure.transform);
        diaphragmsParent.transform.SetParent(structure.transform);

        BuildNodes(nodesParent.transform);
        BuildBeams(beamsParent.transform);
        BuildColumns(columnsParent.transform);
        BuildWalls(wallsParent.transform);
        BuildConstraintLinks(constraintLinksParent.transform);
        BuildSupports(supportsParent.transform);
        BuildDiaphragms(diaphragmsParent.transform);
        ComputeModelCenter();
    }

    void BuildNodes(Transform parent)
    {
        if (modelData.nodes == null) return;

        foreach (var node in modelData.nodes)
        {
            Vector3 pos = StructToUnity(node.x, node.y, node.z);
            bool isMaster = node.tipo == "master";

            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = $"Node_{node.tag}";
            go.transform.position = pos;

            float radius = isMaster ? 0.15f : 0.08f;
            go.transform.localScale = Vector3.one * radius * 2f;

            go.GetComponent<Renderer>().material = isMaster ? masterMaterial : nodeMaterial;
            go.transform.SetParent(parent);

            nodeObjects[node.tag] = go;
            if (isMaster)
                masterNodeObjects[node.tag] = go;
        }
    }

    void BuildBeams(Transform parent)
    {
        if (modelData.beams == null) return;

        foreach (var beam in modelData.beams)
        {
            GameObject go = CreateElementGO(
                beam.elementTag, beam.node_i, beam.node_j,
                beam.longitud_m, 0.12f, beamMaterial, "Beam"
            );
            if (go != null)
            {
                go.transform.SetParent(parent);
                beamObjects[beam.elementTag] = go;
            }
        }
    }

    void BuildColumns(Transform parent)
    {
        if (modelData.columns == null) return;

        foreach (var col in modelData.columns)
        {
            GameObject go = CreateElementGO(
                col.elementTag, col.node_i, col.node_j,
                col.longitud_m, 0.16f, columnMaterial, "Column"
            );
            if (go != null)
            {
                go.transform.SetParent(parent);
                columnObjects[col.elementTag] = go;
            }
        }
    }

    void BuildWalls(Transform parent)
    {
        if (modelData.walls == null || modelData.walls.Length == 0)
        {
            Debug.Log("[LT1Viewer] no walls in model data");
            return;
        }

        foreach (var wall in modelData.walls)
        {
            // El muro equivalente es un elasticBeamColumn LINEAL en OpenSees.
            // Se representa como barra vertical diferenciada (color propio y
            // grosor mayor) SOLO como visualización; no es un FE de superficie.
            GameObject go = CreateElementGO(
                wall.elementTag, wall.node_i, wall.node_j,
                wall.longitud_vertical_m, 0.55f, wallMaterial, "Wall"
            );
            if (go != null)
            {
                go.transform.SetParent(parent);
                wallObjects[wall.elementTag] = go;
            }
        }
    }

    void BuildConstraintLinks(Transform parent)
    {
        if (modelData.constraint_links == null || modelData.constraint_links.Length == 0)
        {
            Debug.Log("[LT1Viewer] no constraint links in model data");
            return;
        }

        foreach (var cl in modelData.constraint_links)
        {
            if (!nodeObjects.ContainsKey(cl.nodo_maestro_retained) ||
                !nodeObjects.ContainsKey(cl.nodo_muro))
                continue;

            Vector3 posA = nodeObjects[cl.nodo_maestro_retained].transform.position;
            Vector3 posB = nodeObjects[cl.nodo_muro].transform.position;

            // Línea auxiliar discontinua (dashed) para no confundirla con una
            // viga real: el rigidLink es una restricción cinemática, no elemento.
            GameObject go = CreateDashedLink(parent, "ConstraintLink_" + cl.nodo_muro, posA, posB);
            constraintLinkObjects[cl.nodo_muro] = go;
        }
    }

    GameObject CreateDashedLink(Transform parent, string name, Vector3 a, Vector3 b)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(parent);

        Vector3 dir = b - a;
        float length = dir.magnitude;
        if (length < 0.001f) return go;

        int segments = Mathf.Max(8, Mathf.RoundToInt(length / 0.5f));
        float dashLen = Mathf.Max(length / segments * 0.6f, 0.05f);
        float gapLen = Mathf.Max(length / segments * 0.4f, 0.04f);

        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = constraintLinkMaterial;
        lr.startColor = Color.cyan;
        lr.endColor = Color.cyan;
        lr.startWidth = 0.08f;
        lr.endWidth = 0.08f;
        lr.useWorldSpace = true;

        var points = new List<Vector3>();
        int pos = 0;
        Vector3 dirNorm = dir / length;
        float covered = 0f;
        while (covered < length && points.Count < 512)
        {
            float d0 = Mathf.Min(covered, length);
            float d1 = Mathf.Min(covered + dashLen, length);
            points.Add(a + dirNorm * d0);
            if (d1 > d0) points.Add(a + dirNorm * d1);
            covered = d1 + gapLen;
            pos++;
        }

        lr.positionCount = points.Count;
        for (int i = 0; i < points.Count; i++) lr.SetPosition(i, points[i]);

        return go;
    }

    GameObject CreateElementGO(int tag, int nodeI, int nodeJ, float longitud,
                               float thickness, Material material, string prefix)
    {
        if (!nodeObjects.ContainsKey(nodeI) || !nodeObjects.ContainsKey(nodeJ))
        {
            Debug.LogWarning($"[LT1Viewer] {prefix} {tag}: missing node reference ({nodeI} or {nodeJ})");
            return null;
        }

        Vector3 posI = nodeObjects[nodeI].transform.position;
        Vector3 posJ = nodeObjects[nodeJ].transform.position;
        Vector3 direction = posJ - posI;
        float length = direction.magnitude;

        if (length < 0.001f)
        {
            Debug.LogWarning($"[LT1Viewer] {prefix} {tag}: zero-length element");
            return null;
        }

        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = $"{prefix}_{tag}";
        go.transform.position = (posI + posJ) * 0.5f;
        go.transform.localScale = new Vector3(thickness, thickness, length);
        go.transform.rotation = Quaternion.FromToRotation(Vector3.forward, direction);
        go.GetComponent<Renderer>().material = material;

        return go;
    }

    void BuildSupports(Transform parent)
    {
        if (modelData.supports == null) return;

        foreach (var support in modelData.supports)
        {
            if (!nodeObjects.ContainsKey(support.nodeTag)) continue;

            Vector3 pos = nodeObjects[support.nodeTag].transform.position;

            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = $"Support_{support.nodeTag}";
            go.transform.position = pos + Vector3.down * 0.25f;
            go.transform.localScale = new Vector3(0.4f, 0.4f, 0.4f);
            go.GetComponent<Renderer>().material = supportMaterial;
            go.transform.SetParent(parent);

            supportObjects[support.nodeTag] = go;
        }
    }

    void BuildDiaphragms(Transform parent)
    {
        if (modelData.diaphragms == null) return;

        foreach (var diaphragm in modelData.diaphragms)
        {
            GameObject go = CreateDiaphragmGO(diaphragm);
            if (go != null)
                go.transform.SetParent(parent);
        }
    }

    GameObject CreateDiaphragmGO(DiaphragmData diaphragm)
    {
        GameObject go = new GameObject($"Diaphragm_nivel{diaphragm.nivel}");

        float unityY = diaphragm.z;

        Vector3 minBound = new Vector3(float.MaxValue, 0f, float.MaxValue);
        Vector3 maxBound = new Vector3(float.MinValue, 0f, float.MinValue);

        if (nodeObjects.ContainsKey(diaphragm.master))
        {
            Vector3 mp = nodeObjects[diaphragm.master].transform.position;
            minBound.x = mp.x; minBound.z = mp.z;
            maxBound.x = mp.x; maxBound.z = mp.z;
        }

        if (diaphragm.slaves != null)
        {
            foreach (int slaveTag in diaphragm.slaves)
            {
                if (!nodeObjects.ContainsKey(slaveTag)) continue;
                Vector3 sp = nodeObjects[slaveTag].transform.position;
                minBound.x = Mathf.Min(minBound.x, sp.x);
                minBound.z = Mathf.Min(minBound.z, sp.z);
                maxBound.x = Mathf.Max(maxBound.x, sp.x);
                maxBound.z = Mathf.Max(maxBound.z, sp.z);
            }
        }

        float sizeX = Mathf.Max(maxBound.x - minBound.x, 0.5f);
        float sizeZ = Mathf.Max(maxBound.z - minBound.z, 0.5f);
        Vector3 center = new Vector3(
            (minBound.x + maxBound.x) * 0.5f,
            unityY,
            (minBound.z + maxBound.z) * 0.5f
        );

        GameObject plane = GameObject.CreatePrimitive(PrimitiveType.Quad);
        plane.transform.SetParent(go.transform);
        plane.transform.position = center;
        plane.transform.localScale = new Vector3(sizeX, sizeZ, 1f);
        plane.transform.rotation = Quaternion.Euler(-90f, 0f, 0f);

        plane.GetComponent<Renderer>().material = diaphragmMaterial;

        Collider col = plane.GetComponent<Collider>();
        if (col != null) Destroy(col);

        return go;
    }

    void ComputeModelCenter()
    {
        if (modelData.nodes == null || modelData.nodes.Length == 0)
        {
            modelCenter = Vector3.zero;
            return;
        }

        Vector3 sum = Vector3.zero;
        foreach (var node in modelData.nodes)
            sum += StructToUnity(node.x, node.y, node.z);

        modelCenter = sum / modelData.nodes.Length;
    }

    string FindJsonPath()
    {
        string path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        if (File.Exists(path)) return path;

        path = Path.Combine(Application.dataPath, jsonFileName);
        if (File.Exists(path)) return path;

        path = Path.Combine(Application.persistentDataPath, jsonFileName);
        if (File.Exists(path)) return path;

        return null;
    }

    void ParseAnalysisDictionaries(string json)
    {
        if (modelData.analysis == null)
        {
            modelData.analysis = new AnalysisData
            {
                reacciones = new Dictionary<int, float[]>(),
                desplazamientos = new Dictionary<int, float[]>()
            };
            return;
        }

        modelData.analysis.reacciones = ParseFloatDict(json, "reacciones");
        modelData.analysis.desplazamientos = ParseFloatDict(json, "desplazamientos");
    }

    Dictionary<int, float[]> ParseFloatDict(string json, string key)
    {
        var dict = new Dictionary<int, float[]>();

        string pattern = "\"" + key + "\"\\s*:\\s*\\{";
        Match match = Regex.Match(json, pattern);
        if (!match.Success) return dict;

        int startIdx = match.Index + match.Length;
        int braceCount = 1;
        int i = startIdx;

        while (i < json.Length && braceCount > 0)
        {
            if (json[i] == '{') braceCount++;
            else if (json[i] == '}') braceCount--;
            i++;
        }

        string dictContent = json.Substring(startIdx, i - startIdx - 1);

        var entryRegex = new Regex(@"""(-?\d+)""\s*:\s*\[([^\]]+)\]");
        foreach (Match entry in entryRegex.Matches(dictContent))
        {
            if (!int.TryParse(entry.Groups[1].Value, out int tag)) continue;
            string[] parts = entry.Groups[2].Value.Split(',');
            float[] values = new float[parts.Length];
            for (int j = 0; j < parts.Length; j++)
                float.TryParse(parts[j].Trim(), out values[j]);
            dict[tag] = values;
        }

        return dict;
    }
}
