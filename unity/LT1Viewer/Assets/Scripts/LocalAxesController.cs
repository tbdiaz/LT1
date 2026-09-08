using System.Collections.Generic;
using UnityEngine;

public class LocalAxesController : MonoBehaviour
{
    private bool showAxes;
    private bool initialized;
    private readonly List<GameObject> axisObjects = new List<GameObject>();

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.A)) ToggleAxes();
    }

    void OnGUI()
    {
        GUILayout.BeginArea(new Rect(10, Screen.height - 50, 220, 40));
        GUILayout.BeginVertical("box");
        if (GUILayout.Button($"A Ejes Locales [{(showAxes ? "ON" : "OFF")}]"))
            ToggleAxes();
        GUILayout.EndVertical();
        GUILayout.EndArea();
    }

    void ToggleAxes()
    {
        showAxes = !showAxes;
        EnsureInitialized();
        foreach (var go in axisObjects)
            if (go != null) go.SetActive(showAxes);
    }

    void EnsureInitialized()
    {
        if (initialized) return;
        BuildAxes();
        initialized = true;
    }

    void BuildAxes()
    {
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null) return;

        GameObject axesRoot = new GameObject("LocalAxes");

        if (loader.modelData.beams != null)
        {
            foreach (var beam in loader.modelData.beams)
                BuildElementAxes(axesRoot.transform, loader, beam.elementTag,
                                 beam.node_i, beam.node_j, beam.local_axis_xz,
                                 loader.beamObjects);
        }

        if (loader.modelData.columns != null)
        {
            foreach (var col in loader.modelData.columns)
                BuildElementAxes(axesRoot.transform, loader, col.elementTag,
                                 col.node_i, col.node_j, col.local_axis_xz,
                                 loader.columnObjects);
        }

        if (loader.modelData.walls != null)
        {
            foreach (var wall in loader.modelData.walls)
                BuildElementAxes(axesRoot.transform, loader, wall.elementTag,
                                 wall.node_i, wall.node_j, wall.local_axis_xz,
                                 loader.wallObjects);
        }
    }

    void BuildElementAxes(Transform parent, ModelLoader loader, int tag,
                          int nodeI, int nodeJ, float[] localAxisXZ,
                          Dictionary<int, GameObject> objectMap)
    {
        if (!objectMap.ContainsKey(tag) || objectMap[tag] == null) return;
        if (!loader.nodeObjects.ContainsKey(nodeI) || !loader.nodeObjects.ContainsKey(nodeJ)) return;

        Vector3 posI = loader.nodeObjects[nodeI].transform.position;
        Vector3 posJ = loader.nodeObjects[nodeJ].transform.position;
        Vector3 elementDir = posJ - posI;
        float length = elementDir.magnitude;

        if (length < 0.001f) return;

        float axisLength = Mathf.Max(0.2f * length, 0.5f);
        Vector3 center = (posI + posJ) * 0.5f;
        Vector3 localX = elementDir / length;

        Vector3 localZ;
        if (localAxisXZ != null && localAxisXZ.Length >= 3)
        {
            localZ = new Vector3(localAxisXZ[0], localAxisXZ[2], -localAxisXZ[1]).normalized;
            if (Vector3.Dot(localZ, localX) > 0.99f)
                localZ = GetFallbackPerpendicular(localX);
        }
        else
        {
            localZ = GetFallbackPerpendicular(localX);
        }

        Vector3 localY = Vector3.Cross(localZ, localX).normalized;

        DrawAxisLine(parent, center, localX, axisLength, Color.red);
        DrawAxisLine(parent, center, localY, axisLength, Color.green);
        DrawAxisLine(parent, center, localZ, axisLength, Color.blue);
    }

    Vector3 GetFallbackPerpendicular(Vector3 dir)
    {
        Vector3 up = Vector3.up;
        Vector3 perp = Vector3.Cross(up, dir);
        if (perp.sqrMagnitude < 0.001f)
            perp = Vector3.Cross(Vector3.forward, dir);
        return perp.normalized;
    }

    void DrawAxisLine(Transform parent, Vector3 start, Vector3 direction, float length, Color color)
    {
        GameObject lineGo = new GameObject("Axis_" + ColorName(color));
        lineGo.transform.SetParent(parent);

        LineRenderer lr = lineGo.AddComponent<LineRenderer>();
        lr.positionCount = 2;
        lr.SetPosition(0, start);
        lr.SetPosition(1, start + direction * length);
        lr.startWidth = 0.025f;
        lr.endWidth = 0.025f;
        lr.useWorldSpace = true;

        lr.material = new Material(Shader.Find("Sprites/Default"));
        lr.startColor = color;
        lr.endColor = color;

        axisObjects.Add(lineGo);
    }

    string ColorName(Color c)
    {
        if (c == Color.red) return "X";
        if (c == Color.green) return "Y";
        return "Z";
    }
}
