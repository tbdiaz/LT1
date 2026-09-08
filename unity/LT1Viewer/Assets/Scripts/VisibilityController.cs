using UnityEngine;

public class VisibilityController : MonoBehaviour
{
    private GameObject nodesGroup;
    private GameObject beamsGroup;
    private GameObject columnsGroup;
    private GameObject wallsGroup;
    private GameObject constraintLinksGroup;
    private GameObject supportsGroup;
    private GameObject diaphragmsGroup;

    private bool showNodes = true;
    private bool showBeams = true;
    private bool showColumns = true;
    private bool showWalls = true;
    private bool showConstraintLinks = false;
    private bool showSupports = true;
    private bool showDiaphragms = true;
    private bool showPendingInfo;

    private bool initialized;
    private string wallsMessage =
        "6 muros equivalentes (nucleo PISO_2, v2)\n" +
        "elemento resistente lineal (elasticBeamColumn)\n" +
        "12 rigidLink al master del diafragma\n" +
        "PISO_1 -> PISO_2";

    void Start()
    {
        InitializeGroups();
    }

    void InitializeGroups()
    {
        if (initialized) return;

        GameObject structure = GameObject.Find("Structure");
        if (structure == null) return;

        nodesGroup = FindChild(structure, "Nodes");
        beamsGroup = FindChild(structure, "Beams");
        columnsGroup = FindChild(structure, "Columns");
        wallsGroup = FindChild(structure, "Walls");
        constraintLinksGroup = FindChild(structure, "ConstraintLinks");
        supportsGroup = FindChild(structure, "Supports");
        diaphragmsGroup = FindChild(structure, "Diaphragms");

        if (wallsGroup == null)
        {
            wallsGroup = new GameObject("Walls");
            wallsGroup.transform.SetParent(structure.transform);
        }

        initialized = true;
    }

    GameObject FindChild(GameObject parent, string name)
    {
        Transform t = parent.transform.Find(name);
        return t != null ? t.gameObject : null;
    }

    void Update()
    {
        if (!initialized) InitializeGroups();

        if (Input.GetKeyDown(KeyCode.Alpha1)) ToggleNodes();
        if (Input.GetKeyDown(KeyCode.Alpha2)) ToggleBeams();
        if (Input.GetKeyDown(KeyCode.Alpha3)) ToggleColumns();
        if (Input.GetKeyDown(KeyCode.Alpha4)) ToggleWalls();
        if (Input.GetKeyDown(KeyCode.Alpha5)) ToggleSupports();
        if (Input.GetKeyDown(KeyCode.Alpha6)) ToggleDiaphragms();
        if (Input.GetKeyDown(KeyCode.Alpha7)) ToggleConstraintLinks();
        if (Input.GetKeyDown(KeyCode.Alpha8)) TogglePendingInfo();
        if (Input.GetKeyDown(KeyCode.P)) TogglePendingInfo();
    }

    void OnGUI()
    {
        GUILayout.BeginArea(new Rect(10, 10, 240, 250));
        GUILayout.BeginVertical("box");
        GUILayout.Label("<b>Visibilidad</b>");

        if (GUILayout.Button($"1 Nodos          [{BoolStr(showNodes)}]"))  ToggleNodes();
        if (GUILayout.Button($"2 Vigas          [{BoolStr(showBeams)}]"))  ToggleBeams();
        if (GUILayout.Button($"3 Columnas       [{BoolStr(showColumns)}]")) ToggleColumns();
        if (GUILayout.Button($"4 Muros          [{BoolStr(showWalls)}]"))  ToggleWalls();
        if (GUILayout.Button($"5 Apoyos         [{BoolStr(showSupports)}]")) ToggleSupports();
        if (GUILayout.Button($"6 Diafragmas     [{BoolStr(showDiaphragms)}]")) ToggleDiaphragms();
        if (GUILayout.Button($"7 Constraint Links [{BoolStr(showConstraintLinks)}]")) ToggleConstraintLinks();
        if (GUILayout.Button($"8 Pendientes info  [{BoolStr(showPendingInfo)}]")) TogglePendingInfo();

        if (showWalls)
        {
            GUILayout.Space(5);
            GUILayout.Label(wallsMessage);
        }

        GUILayout.EndVertical();
        GUILayout.EndArea();

        if (showPendingInfo)
            DrawPendingPanel();
    }

    void DrawPendingPanel()
    {
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null) return;

        float pw = 400f;
        float ph = 210f;
        float x = 10f;
        float y = Screen.height - ph - 40f;

        GUI.Box(new Rect(x, y, pw, ph), "Geometria pendiente (no modelada)");
        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 35));

        if (loader.modelData.pending_geometry != null && loader.modelData.pending_geometry.Length > 0)
        {
            foreach (var p in loader.modelData.pending_geometry)
                GUILayout.Label("- " + p.descripcion);
        }
        else
        {
            GUILayout.Label("- Nucleo PISO_4 (plan 103): extremos sin cerrar");
            GUILayout.Label("- Muros subterraneo (plan 101)");
            GUILayout.Label("- V.30/45 · V.60/VAR · V.60-30/80-40");
            GUILayout.Label("- P.M. 300x300x20 · V.M.");
            GUILayout.Label("- Carga de salientes (PISO_2)");
        }

        GUILayout.Space(5);
        GUIStyle orange = new GUIStyle(GUI.skin.label) { richText = true, fontSize = 10 };
        GUILayout.Label("<color=orange>No se inventa geometria para representarlos.</color>", orange);

        GUILayout.EndArea();
    }

    string BoolStr(bool val) { return val ? "ON" : "OFF"; }

    void ToggleNodes()          { showNodes = !showNodes;           SetGroup(nodesGroup, showNodes); }
    void ToggleBeams()          { showBeams = !showBeams;           SetGroup(beamsGroup, showBeams); }
    void ToggleColumns()        { showColumns = !showColumns;       SetGroup(columnsGroup, showColumns); }
    void ToggleWalls()          { showWalls = !showWalls;           SetGroup(wallsGroup, showWalls); }
    void ToggleConstraintLinks(){ showConstraintLinks = !showConstraintLinks; SetGroup(constraintLinksGroup, showConstraintLinks); }
    void ToggleSupports()       { showSupports = !showSupports;     SetGroup(supportsGroup, showSupports); }
    void ToggleDiaphragms()     { showDiaphragms = !showDiaphragms; SetGroup(diaphragmsGroup, showDiaphragms); }
    void TogglePendingInfo()    { showPendingInfo = !showPendingInfo; }

    void SetGroup(GameObject go, bool active)
    {
        if (go != null) go.SetActive(active);
    }
}