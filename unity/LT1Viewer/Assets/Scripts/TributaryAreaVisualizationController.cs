using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

// LT2: contornos exactos exportados desde tributary_areas_LT2.csv.
// LT1: franja equivalente centrada en la viga, con area exacta A_trib=A/L;
// no se presenta como poligono original porque esa geometria no fue exportada.
public class TributaryAreaVisualizationController : MonoBehaviour
{
    private ModelLoader loader;
    private GameObject root;
    private bool active;
    public bool Active => active;

    void Start() { loader = FindObjectOfType<ModelLoader>(); }

    public void Toggle()
    {
        active = !active;
        if (active) Build(); else Clear();
    }

    public void Build()
    {
        Clear();
        if (!active || loader == null || loader.combinedRoot == null ||
            loader.combinedRoot.tributary_areas == null) return;
        root = new GameObject("TributaryAreas");
        Material lt2 = MakeMaterial(new Color(0.05f, 1f, 0.85f, 0.75f));
        Material lt1 = MakeMaterial(new Color(0.55f, 1f, 0.15f, 0.72f));
        Material v30 = MakeMaterial(new Color(1f, 0.55f, 0.08f, 0.90f));
        var t = loader.combinedRoot.tributary_areas;
        if (t.LT2 != null && t.LT2.filas != null)
            foreach (var row in t.LT2.filas)
            {
                if (row.status == "REDISTRIBUIDO_COMBINADO")
                {
                    // Solo la parte positiva representa el area trasladada a
                    // las V30 nuevas; las filas negativas corrigen las V40.
                    if (row.area_m2 > 0f) DrawEquivalent(
                        row, v30, "LT2_V30_redist_");
                }
                else DrawLt2(row, lt2);
            }
        if (t.LT1 != null && t.LT1.filas != null)
            foreach (var row in t.LT1.filas) DrawEquivalent(
                row, lt1, "LT1_equiv_");
    }

    void DrawLt2(CombinedTribRow row, Material mat)
    {
        if (row.receiver_type != "BEAM" || row.element_tag <= 0 ||
            string.IsNullOrEmpty(row.polygon)) return;
        if (!loader.beamObjects.TryGetValue(row.element_tag, out var beam) || beam == null) return;
        var pts = new List<Vector3>();
        foreach (string token in row.polygon.Split(';'))
        {
            string[] xy = token.Split(',');
            if (xy.Length != 2) continue;
            if (!float.TryParse(xy[0], NumberStyles.Float, CultureInfo.InvariantCulture, out float x) ||
                !float.TryParse(xy[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float y)) continue;
            pts.Add(new Vector3(x, beam.transform.position.y + 0.08f, -y));
        }
        if (pts.Count < 3) return;
        if ((pts[0] - pts[pts.Count - 1]).sqrMagnitude > 1e-6f) pts.Add(pts[0]);
        DrawOutline("LT2_" + row.tributary_id, pts, mat);
    }

    void DrawEquivalent(CombinedTribRow row, Material mat, string prefix)
    {
        float area = row.A_tributaria_m2 > 0f
            ? row.A_tributaria_m2 : row.area_m2;
        if (row.element_tag <= 0 || area <= 0f) return;
        if (!loader.elementRefs.TryGetValue(row.element_tag, out var er)) return;
        if (!loader.nodeObjects.TryGetValue(er.nodeI, out var ni) ||
            !loader.nodeObjects.TryGetValue(er.nodeJ, out var nj)) return;
        Vector3 a = ni.transform.position;
        Vector3 b = nj.transform.position;
        Vector3 d = b - a;
        d.y = 0f;
        float len = d.magnitude;
        if (len < 1e-5f) return;
        Vector3 p = new Vector3(-d.z, 0f, d.x).normalized;
        float halfWidth = area / len * 0.5f;
        Vector3 up = Vector3.up * 0.10f;
        DrawOutline(prefix + row.element_tag,
            new List<Vector3> { a+p*halfWidth+up, b+p*halfWidth+up,
                                b-p*halfWidth+up, a-p*halfWidth+up,
                                a+p*halfWidth+up }, mat);
    }

    void DrawOutline(string name, List<Vector3> pts, Material mat)
    {
        var go = new GameObject(name);
        go.transform.SetParent(root.transform);
        var lr = go.AddComponent<LineRenderer>();
        lr.material = mat;
        lr.startColor = mat.color;
        lr.endColor = mat.color;
        lr.startWidth = 0.075f;
        lr.endWidth = 0.075f;
        lr.useWorldSpace = true;
        lr.positionCount = pts.Count;
        lr.SetPositions(pts.ToArray());
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
