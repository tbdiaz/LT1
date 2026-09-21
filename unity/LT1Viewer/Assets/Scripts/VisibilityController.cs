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
        "Muros equivalentes (elasticBeamColumn)\n" +
        "se muestran segun su tipo real del JSON\n" +
        "(muro / muro_corner / conector V40-muro)";

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

    public bool ShowNodes => showNodes;
    public bool ShowBeams => showBeams;
    public bool ShowColumns => showColumns;
    public bool ShowWalls => showWalls;
    public bool ShowSupports => showSupports;
    public bool ShowDiaphragms => showDiaphragms;
    public bool ShowConstraintLinks => showConstraintLinks;

    void OnGUI()
    {
        // La interfaz principal se dibuja en ViewerHUD para evitar paneles
        // superpuestos. Las teclas 1..8 siguen disponibles.
        return;
#pragma warning disable CS0162
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
        if (GUILayout.Button($"8 Notas modelo     [{BoolStr(showPendingInfo)}]")) TogglePendingInfo();

        if (showWalls)
        {
            GUILayout.Space(5);
            GUILayout.Label(WallsMessageComputed());
        }

        GUILayout.EndVertical();
        GUILayout.EndArea();

        if (showPendingInfo)
            DrawPendingPanel();
#pragma warning restore CS0162
    }

    void DrawPendingPanel()
    {
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.combinedRoot == null) return;

        float pw = 460f;
        float ph = 240f;
        float x = 10f;
        float y = Screen.height - ph - 40f;

        GUI.Box(new Rect(x, y, pw, ph), "Notas del modelo (fuente: JSON)");
        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 60));

        if (loader.combinedRoot.metadata != null
            && loader.combinedRoot.metadata.notas_modelo != null
            && loader.combinedRoot.metadata.notas_modelo.Length > 0)
        {
            foreach (var n in loader.combinedRoot.metadata.notas_modelo)
                GUILayout.Label("- " + n);
        }
        else
        {
            GUILayout.Label("- (sin notas en el JSON)");
        }

        GUIStyle gap = new GUIStyle();
        GUILayout.Space(6);

        GUILayout.EndArea();

        GUILayout.BeginArea(new Rect(x + 10, y + ph - 50, pw - 20, 40));
        GUIStyle orange = new GUIStyle(GUI.skin.label) { richText = true, fontSize = 10 };
        GUILayout.Label("<color=orange>Sin valores inventados; solo lo documentado "
            + "en modelo_combinado.json (incluye flags SUPUESTO).</color>", orange);
        GUILayout.EndArea();
    }

    string WallsMessageComputed()
    {
        var loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.combinedRoot == null) return wallsMessage;

        int muro = 0, muroCorner = 0, conector = 0;
        foreach (var e in loader.combinedRoot.elements)
        {
            if (e.tipo == "muro") muro++;
            else if (e.tipo == "muro_corner") muroCorner++;
            else if (e.tipo == "conector_v40_muro") conector++;
        }

        return "Muros equivalentes (elasticBeamColumn):\n" +
               $"  muro LT1: {muro}\n" +
               $"  muro_corner LT2: {muroCorner}\n" +
               $"  conector V40-muro (COMBINADO): {conector}\n" +
               $"RigidLinks al master del diafragma: "
               + (loader.modelData != null ? loader.modelData.constraint_links.Length.ToString() : "?");
    }

    string BoolStr(bool val) { return val ? "ON" : "OFF"; }

    public void ToggleNodes()          { showNodes = !showNodes;           SetGroup(nodesGroup, showNodes); }
    public void ToggleBeams()          { showBeams = !showBeams;           SetGroup(beamsGroup, showBeams); }
    public void ToggleColumns()        { showColumns = !showColumns;       SetGroup(columnsGroup, showColumns); }
    public void ToggleWalls()          { showWalls = !showWalls;           SetGroup(wallsGroup, showWalls); }
    public void ToggleConstraintLinks(){ showConstraintLinks = !showConstraintLinks; SetGroup(constraintLinksGroup, showConstraintLinks); }
    public void ToggleSupports()       { showSupports = !showSupports;     SetGroup(supportsGroup, showSupports); }
    public void ToggleDiaphragms()     { showDiaphragms = !showDiaphragms; SetGroup(diaphragmsGroup, showDiaphragms); }
    public void TogglePendingInfo()    { showPendingInfo = !showPendingInfo; }

    void SetGroup(GameObject go, bool active)
    {
        if (go != null) go.SetActive(active);
    }
}
