using System.Collections.Generic;
using UnityEngine;

public class SelectionController : MonoBehaviour
{
    [HideInInspector] public int SelectedTag = -1;
    [HideInInspector] public string SelectedType = "";
    [HideInInspector] public GameObject SelectedObject;

    private Material highlightMaterial;
    private Material originalMaterial;
    private Dictionary<int, TributaryAreaData> tributaryLookup;

    void Start()
    {
        highlightMaterial = new Material(Shader.Find("Standard"));
        highlightMaterial.color = Color.yellow;
    }

    void Update()
    {
        if (Input.GetMouseButtonDown(0) && !Input.GetKey(KeyCode.LeftAlt))
        {
            HandleClick();
        }
    }

    void HandleClick()
    {
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);

        if (!Physics.Raycast(ray, out RaycastHit hit))
        {
            Deselect();
            return;
        }

        string objName = hit.collider.gameObject.name;

        if (objName.StartsWith("Beam_") || objName.StartsWith("Column_") ||
            objName.StartsWith("Wall_"))
        {
            SelectElement(hit.collider.gameObject, objName);
        }
        else
        {
            Deselect();
        }
    }

    void SelectElement(GameObject go, string objName)
    {
        Deselect();

        SelectedObject = go;
        originalMaterial = go.GetComponent<Renderer>().material;
        go.GetComponent<Renderer>().material = highlightMaterial;

        SelectedTag = ParseTag(objName);
        if (objName.StartsWith("Beam_")) SelectedType = "Viga";
        else if (objName.StartsWith("Column_")) SelectedType = "Columna";
        else if (objName.StartsWith("Wall_")) SelectedType = "Muro";
    }

    public void Deselect()
    {
        if (SelectedObject != null && originalMaterial != null)
        {
            SelectedObject.GetComponent<Renderer>().material = originalMaterial;
        }
        SelectedObject = null;
        originalMaterial = null;
        SelectedTag = -1;
        SelectedType = "";
    }

    int ParseTag(string name)
    {
        int idx = name.LastIndexOf('_');
        if (idx >= 0 && int.TryParse(name.Substring(idx + 1), out int tag))
            return tag;
        return -1;
    }

    public BeamData GetSelectedBeam()
    {
        if (SelectedTag < 0 || SelectedType != "Viga") return null;
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null || loader.modelData.beams == null) return null;

        foreach (var b in loader.modelData.beams)
            if (b.elementTag == SelectedTag) return b;
        return null;
    }

    public ColumnData GetSelectedColumn()
    {
        if (SelectedTag < 0 || SelectedType != "Columna") return null;
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null || loader.modelData.columns == null) return null;

        foreach (var c in loader.modelData.columns)
            if (c.elementTag == SelectedTag) return c;
        return null;
    }

    public WallData GetSelectedWall()
    {
        if (SelectedTag < 0 || SelectedType != "Muro") return null;
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null || loader.modelData.walls == null) return null;

        foreach (var w in loader.modelData.walls)
            if (w.elementTag == SelectedTag) return w;
        return null;
    }

    void OnGUI()
    {
        if (SelectedTag < 0) return;

        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null) return;

        string info = "";

        if (SelectedType == "Viga")
        {
            var b = GetSelectedBeam();
            if (b != null)
            {
                info = $"Tipo: Viga\n" +
                       $"Tag: {b.elementTag}\n" +
                       $"Nodo i: {b.node_i}\n" +
                       $"Nodo j: {b.node_j}\n" +
                       $"Seccion: {b.seccion}\n" +
                       $"Longitud: {b.longitud_m:F3} m\n" +
                       $"Nivel: {b.nivel}";
            }
        }
        else if (SelectedType == "Columna")
        {
            var c = GetSelectedColumn();
            if (c != null)
            {
                info = $"Tipo: Columna\n" +
                       $"Tag: {c.elementTag}\n" +
                       $"Nodo i: {c.node_i}\n" +
                       $"Nodo j: {c.node_j}\n" +
                       $"Seccion: {c.seccion}\n" +
                       $"Longitud: {c.longitud_m:F3} m\n" +
                       $"Nivel: {c.nivel_inferior} -> {c.nivel_superior}";
            }
        }
        else if (SelectedType == "Muro")
        {
            var w = GetSelectedWall();
            if (w != null)
            {
                info = $"Tipo: Muro equivalente (lineal)\n" +
                       $"ID: {w.clave}\n" +
                       $"Tag: {w.elementTag}\n" +
                       $"Nodo i: {w.node_i}\n" +
                       $"Nodo j: {w.node_j}\n" +
                       $"Seccion equiv: {w.seccion}\n" +
                       $"Espesor: {w.espesor_m:F2} m\n" +
                       $"L_planta: {w.longitud_planta_m:F3} m\n" +
                       $"Orientacion: {w.orientacion}\n" +
                       $"Tramo: {w.nivel_inferior} -> {w.nivel_superior}";
            }
        }

        if (string.IsNullOrEmpty(info)) return;

        float pw = 320f;
        float ph = SelectedType == "Muro" ? 250f : 180f;
        float x = Screen.width - pw - 10f;
        float y = Screen.height - ph - 40f;

        GUI.Box(new Rect(x, y, pw, ph), "Info Elemento");

        GUIStyle style = new GUIStyle(GUI.skin.label) { richText = false };
        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 35));
        GUILayout.Label(info, style);

        if (SelectedType == "Muro")
        {
            GUILayout.Space(5);
            GUIStyle grey = new GUIStyle(GUI.skin.label) { richText = true, fontSize = 10 };
            GUILayout.Label("<color=grey>Elemento resistente OpenSees: elasticBeamColumn</color>", grey);
        }

        GUILayout.EndArea();
    }
}