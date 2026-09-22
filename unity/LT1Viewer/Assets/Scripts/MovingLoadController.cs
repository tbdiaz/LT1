using System.Globalization;
using UnityEngine;

// Sidequest Semana 5: carga puntual movil sobre la viga seleccionada.
// Regla de reparto lineal equivalente entre los nodos extremos:
//   Pi=P(1-xi), Pj=P*xi, 0<=xi<=1.
// Conserva fuerza (Pi+Pj=P) y primer momento (Pj*L=P*xi*L).
// Conserva equilibrio estatico, pero no representa reacciones del marco.
// Es una herramienta visual: no modifica el JSON ni reanaliza OpenSees.
public class MovingLoadController : MonoBehaviour
{
    ModelLoader loader;
    SelectionController selection;
    GameObject root;
    Material material;
    bool active;
    float magnitudeKn;
    float xi = 0.5f;
    int lastTag = -1;
    string magnitudeText = "0";
    string status = "Seleccione una viga e ingrese P.";

    public bool Active => active;
    public float MagnitudeKn => magnitudeKn;
    public float Xi => xi;
    public float LoadI => magnitudeKn * (1f - xi);
    public float LoadJ => magnitudeKn * xi;
    public string MagnitudeText { get => magnitudeText; set => magnitudeText = value; }
    public string Status => status;
    public int BeamTag => lastTag;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        selection = FindObjectOfType<SelectionController>();
        material = new Material(Shader.Find("Sprites/Default"));
        material.color = new Color(1f, 0.18f, 0.05f, 1f);
    }

    void Update()
    {
        if (!active || selection == null) return;
        if (selection.SelectedTag != lastTag) Rebuild();
    }

    public void Toggle()
    {
        active = !active;
        if (active) ApplyInput(); else Clear();
    }

    public void ApplyInput()
    {
        string normalized = (magnitudeText ?? "").Trim().Replace(',', '.');
        if (!float.TryParse(normalized, NumberStyles.Float,
                            CultureInfo.InvariantCulture, out float value)
            || value < 0f)
        {
            status = "P debe ser un numero mayor o igual a cero [kN].";
            return;
        }
        magnitudeKn = value;
        Rebuild();
    }

    public void SetPosition(float value)
    {
        xi = Mathf.Clamp01(value);
        if (active) Rebuild();
    }

    void Rebuild()
    {
        Clear();
        lastTag = selection != null ? selection.SelectedTag : -1;
        if (!active || loader == null || selection == null ||
            selection.SelectedType != "Viga")
        {
            status = "Seleccione una viga para aplicar la carga movil.";
            return;
        }
        ElementRef er = selection.GetElementRef();
        if (er == null || !loader.nodeObjects.TryGetValue(er.nodeI, out var ni)
            || !loader.nodeObjects.TryGetValue(er.nodeJ, out var nj))
        {
            status = "La viga seleccionada no tiene nodos trazables.";
            return;
        }
        Vector3 point = Vector3.Lerp(ni.transform.position,
                                     nj.transform.position, xi);
        root = new GameObject("CARGA_MOVIL_" + er.elementTag);
        DrawLine("fuste", point + Vector3.up * 2.2f, point, 0.16f);
        DrawLine("punta_a", point, point + new Vector3(-0.38f, 0.55f, 0f), 0.12f);
        DrawLine("punta_b", point, point + new Vector3(0.38f, 0.55f, 0f), 0.12f);
        float forceError = Mathf.Abs((LoadI + LoadJ) - magnitudeKn);
        float momentError = Mathf.Abs(LoadJ * er.longitud_m
                                      - magnitudeKn * xi * er.longitud_m);
        status = $"tag {er.elementTag} · Pi={LoadI:F2} kN · " +
                 $"Pj={LoadJ:F2} kN · errF={forceError:E1} · " +
                 $"errM={momentError:E1}";
    }

    void DrawLine(string name, Vector3 a, Vector3 b, float width)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(root.transform);
        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = material;
        lr.startColor = material.color;
        lr.endColor = material.color;
        lr.startWidth = width;
        lr.endWidth = width;
        lr.positionCount = 2;
        lr.useWorldSpace = true;
        lr.SetPosition(0, a);
        lr.SetPosition(1, b);
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
