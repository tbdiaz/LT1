using System.Collections.Generic;
using UnityEngine;

// HUD unico, de alto contraste y operable con mouse. Sustituye los paneles
// IMGUI dispersos que se superponian y ocultaban resultados.
public class ViewerHUD : MonoBehaviour
{
    static float LeftW => Application.isMobilePlatform ? 290f : 255f;
    static float RightW => Application.isMobilePlatform ? 500f : 440f;
    static float TopH => Application.isMobilePlatform ? 245f : 215f;
    static float ButtonH => Application.isMobilePlatform ? 44f : 29f;

    ModelLoader loader;
    VisibilityController visibility;
    SelectionController selection;
    IdLabelController ids;
    LocalAxesController axes;
    DeformedShapeController deformed;
    ForceDiagramController diagrams;
    LoadVisualizationController loads;
    TributaryAreaVisualizationController tributary;
    MovingLoadController movingLoad;
    Vector2 selectionScroll;

    public static bool PointerOverHud(Vector3 mouse)
    {
        float y = Screen.height - mouse.y;
        float leftH = Application.isMobilePlatform ? Screen.height - 8f : 455f;
        return (mouse.x <= LeftW + 8f && y <= leftH) ||
               mouse.x >= Screen.width - RightW - 8f ||
               (y <= TopH + 8f && mouse.x > LeftW && mouse.x < Screen.width - RightW);
    }

    void Start() { FindControllers(); }

    void FindControllers()
    {
        loader = FindObjectOfType<ModelLoader>();
        visibility = FindObjectOfType<VisibilityController>();
        selection = FindObjectOfType<SelectionController>();
        ids = FindObjectOfType<IdLabelController>();
        axes = FindObjectOfType<LocalAxesController>();
        deformed = FindObjectOfType<DeformedShapeController>();
        diagrams = FindObjectOfType<ForceDiagramController>();
        loads = FindObjectOfType<LoadVisualizationController>();
        tributary = FindObjectOfType<TributaryAreaVisualizationController>();
        movingLoad = FindObjectOfType<MovingLoadController>();
    }

    void OnGUI()
    {
        GUI.depth = -50;
        if (loader == null) FindControllers();
        DrawLeftPanel();
        DrawTopToolbar();
        DrawSelectionPanel();
    }

    GUIStyle Header(int size = 15)
    {
        return new GUIStyle(GUI.skin.label)
        { fontSize = size, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter,
          normal = { textColor = Color.white } };
    }

    GUIStyle TextStyle(int size = 12)
    {
        return new GUIStyle(GUI.skin.label)
        { fontSize = size, richText = true, wordWrap = true,
          normal = { textColor = new Color(0.92f, 0.95f, 1f) } };
    }

    bool ToggleButton(string label, bool on, System.Action action)
    {
        Color old = GUI.backgroundColor;
        GUI.backgroundColor = on ? new Color(0.12f, 0.72f, 0.42f) : new Color(0.28f, 0.32f, 0.40f);
        bool pressed = GUILayout.Button(label + (on ? "  ON" : "  OFF"), GUILayout.Height(ButtonH));
        GUI.backgroundColor = old;
        if (pressed && action != null) action();
        return pressed;
    }

    void DrawLeftPanel()
    {
        float panelH = Application.isMobilePlatform ? Screen.height - 16f : 444f;
        GUI.Box(new Rect(8, 8, LeftW, panelH), "");
        GUILayout.BeginArea(new Rect(16, 13, LeftW - 16, panelH - 12f));
        GUILayout.Label("LT1 + LT2  |  CAPAS", Header(16));
        GUILayout.Label("Colores: vigas azul · columnas verde · muros violeta", TextStyle(10));
        GUILayout.Space(5);
        if (visibility != null)
        {
            ToggleButton("NODOS", visibility.ShowNodes, visibility.ToggleNodes);
            ToggleButton("VIGAS", visibility.ShowBeams, visibility.ToggleBeams);
            ToggleButton("COLUMNAS", visibility.ShowColumns, visibility.ToggleColumns);
            ToggleButton("MUROS", visibility.ShowWalls, visibility.ToggleWalls);
            ToggleButton("APOYOS", visibility.ShowSupports, visibility.ToggleSupports);
            ToggleButton("DIAFRAGMAS", visibility.ShowDiaphragms, visibility.ToggleDiaphragms);
            ToggleButton("RIGID LINKS", visibility.ShowConstraintLinks, visibility.ToggleConstraintLinks);
        }
        GUILayout.BeginHorizontal();
        if (ids != null)
        {
            ToggleButton("ID NODO", ids.ShowNodeIds, ids.ToggleNodeIds);
            ToggleButton("ID ELEM", ids.ShowElementIds, ids.ToggleElementIds);
        }
        GUILayout.EndHorizontal();
        if (axes != null) ToggleButton("EJES LOCALES", axes.ShowAxes, axes.ToggleAxes);
        GUILayout.EndArea();
    }

    void DrawTopToolbar()
    {
        float x = LeftW + 18f;
        float w = Mathf.Max(420f, Screen.width - LeftW - RightW - 36f);
        GUI.Box(new Rect(x, 8, w, TopH), "");
        GUILayout.BeginArea(new Rect(x + 8, 12, w - 16, TopH - 8));
        GUILayout.BeginHorizontal();
        GUILayout.Label("CASO", Header(13), GUILayout.Width(50));
        if (loader != null)
        {
            foreach (string c in loader.CaseList)
            {
                Color old = GUI.backgroundColor;
                GUI.backgroundColor = c == loader.activeCase ? new Color(0.10f, 0.62f, 0.95f) : new Color(0.30f, 0.34f, 0.42f);
                if (GUILayout.Button(c, GUILayout.Height(28))) loader.SetActiveCase(c);
                GUI.backgroundColor = old;
            }
        }
        GUILayout.EndHorizontal();
        GUILayout.Space(4);
        GUILayout.BeginHorizontal();
        if (deformed != null)
        {
            ToggleButton("DEFORMADA", deformed.Active, deformed.Toggle);
            if (GUILayout.Button("−", GUILayout.Width(28), GUILayout.Height(29))) deformed.ScaleDown();
            GUILayout.Label("x" + deformed.ScaleFactor.ToString("F0"), Header(11), GUILayout.Width(42));
            if (GUILayout.Button("+", GUILayout.Width(28), GUILayout.Height(29))) deformed.ScaleUp();
        }
        if (loads != null) ToggleButton("CARGAS", loads.Active, loads.Toggle);
        if (tributary != null) ToggleButton("AREAS", tributary.Active, tributary.Toggle);
        GUILayout.EndHorizontal();
        GUILayout.Space(3);
        GUILayout.BeginHorizontal();
        if (diagrams != null)
        {
            ToggleButton("DIAGRAMA " + diagrams.ModeLabel, diagrams.Active, diagrams.Toggle);
            foreach (ForceDiagramController.DiagramMode m in
                     System.Enum.GetValues(typeof(ForceDiagramController.DiagramMode)))
            {
                Color old = GUI.backgroundColor;
                GUI.backgroundColor = diagrams.Mode == m
                    ? new Color(0.82f, 0.24f, 0.72f)
                    : new Color(0.30f, 0.34f, 0.42f);
                if (GUILayout.Button(m.ToString(), GUILayout.Width(39), GUILayout.Height(29)))
                    diagrams.SetMode(m);
                GUI.backgroundColor = old;
            }
        }
        GUILayout.EndHorizontal();
        GUILayout.Space(3);
        DrawMovingLoadControls();
        GUILayout.Label(Application.isMobilePlatform
            ? "1 dedo orbitar/seleccionar · 2 dedos pan/zoom"
            : "RMB orbitar · rueda zoom · MMB pan · LMB seleccionar elemento",
            TextStyle(10));
        GUILayout.EndArea();
    }

    void DrawMovingLoadControls()
    {
        if (movingLoad == null) return;
        GUILayout.BeginHorizontal();
        ToggleButton("CARGA MOVIL", movingLoad.Active, movingLoad.Toggle);
        if (movingLoad.Active)
        {
            GUILayout.Label("P [kN]", TextStyle(11), GUILayout.Width(48));
            movingLoad.MagnitudeText = GUILayout.TextField(
                movingLoad.MagnitudeText, GUILayout.Width(68),
                GUILayout.Height(ButtonH));
            if (GUILayout.Button("APLICAR", GUILayout.Width(68),
                                 GUILayout.Height(ButtonH)))
                movingLoad.ApplyInput();
            float next = GUILayout.HorizontalSlider(
                movingLoad.Xi, 0f, 1f, GUILayout.Width(150));
            if (Mathf.Abs(next - movingLoad.Xi) > 1e-5f)
                movingLoad.SetPosition(next);
            GUILayout.Label($"x/L={movingLoad.Xi:F2}", TextStyle(11),
                            GUILayout.Width(66));
        }
        GUILayout.EndHorizontal();
        if (movingLoad.Active)
            GUILayout.Label(movingLoad.Status +
                " · reparto Pi=P(1-x/L), Pj=P(x/L) · visual, sin reanalisis",
                TextStyle(10));
    }

    void DrawSelectionPanel()
    {
        float x = Screen.width - RightW - 8f;
        float h = Screen.height - 42f;
        GUI.Box(new Rect(x, 8, RightW, h), "");
        GUILayout.BeginArea(new Rect(x + 10, 13, RightW - 20, h - 12));
        GUILayout.Label("ELEMENTO SELECCIONADO", Header(16));
        if (selection == null || selection.SelectedTag < 0)
        {
            GUILayout.Space(15);
            GUILayout.Label("Haz click sobre una viga, columna o muro. Aqui apareceran ID, nodos, seccion, material, restricciones y N/V/T/M del caso activo.", TextStyle(13));
            GUILayout.EndArea();
            return;
        }
        ElementRef r = selection.GetElementRef();
        if (r == null) { GUILayout.Label("Elemento sin referencia.", TextStyle()); GUILayout.EndArea(); return; }
        selectionScroll = GUILayout.BeginScrollView(selectionScroll);
        GUILayout.Label($"<color=#58D8FF><b>{r.TipoEtiqueta()}  ·  tag {r.elementTag}</b></color>", TextStyle(15));
        GUILayout.Label($"Origen {r.origen}  |  JSON index {r.jsonIndex}\nNodos I={r.nodeI}  J={r.nodeJ}\nLongitud {r.longitud_m:F3} m", TextStyle());
        if (r.seccion != null)
        {
            GUILayout.Label("<b>SECCION Y MATERIAL</b>", TextStyle(13));
            GUILayout.Label($"{r.seccion.label}\nA={r.seccion.A_m2:E3} m²  Iy={r.seccion.Iy_m4:E3} m⁴  Iz={r.seccion.Iz_m4:E3} m⁴\nE={r.seccion.E_kPa/1000f:F0} MPa  G={r.seccion.G_kPa/1000f:F0} MPa", TextStyle());
        }
        GUILayout.Label("<b>RESTRICCIONES / CONDICIONES</b>", TextStyle(13));
        GUILayout.Label(BoundaryText(r), TextStyle(11));
        if (!string.IsNullOrEmpty(r.constraint))
            GUILayout.Label("<color=#FFD15C>" + r.constraint + "</color>", TextStyle(10));
        GUILayout.Label("<b>EJES LOCALES</b>", TextStyle(13));
        if (r.ejes_locales != null && r.ejes_locales.x != null)
            GUILayout.Label("x=" + Vec(r.ejes_locales.x) + "\ny=" + Vec(r.ejes_locales.y) + "\nz=" + Vec(r.ejes_locales.z), TextStyle(11));
        DrawForces(r.elementTag);
        DrawElementDiagram(r.elementTag);
        DrawTributaryData(r.elementTag);
        if (r.IsSupuesta()) GUILayout.Label("<color=#FF9B45><b>SUPUESTO:</b> " + r.estado_geometria + "</color>", TextStyle(11));
        GUILayout.EndScrollView();
        if (GUILayout.Button("DESELECCIONAR", GUILayout.Height(30))) selection.Deselect();
        GUILayout.EndArea();
    }

    void DrawForces(int tag)
    {
        GUILayout.Label("<b>RESULTADOS · " + (loader != null ? loader.activeCase : "") + "</b>", TextStyle(14));
        if (loader == null || !loader.elementForceI.TryGetValue(tag, out var fi) ||
            !loader.elementForceJ.TryGetValue(tag, out var fj) || fi.Length < 6 || fj.Length < 6)
        { GUILayout.Label("Sin resultados para este caso.", TextStyle()); return; }
        string[] names = { "N", "Vy", "Vz", "T", "My", "Mz" };
        string[] units = { "kN", "kN", "kN", "kN-m", "kN-m", "kN-m" };
        GUILayout.Label("Convencion de seccion: i = -F_i, j = +F_j", TextStyle(10));
        for (int k = 0; k < 6; k++)
        {
            string color = k == 0 ? "#5CFF83" : k >= 4 ? "#FF62DB" : k == 3 ? "#55EEFF" : "#FFB347";
            GUILayout.Label($"<color={color}><b>{names[k]}</b></color>   i={-fi[k]:F2}   j={fj[k]:F2}  {units[k]}", TextStyle(12));
        }
    }

    void DrawTributaryData(int tag)
    {
        if (loader == null || loader.modelData == null ||
            loader.modelData.tributary_areas == null) return;
        float area = 0f, load = 0f;
        int rows = 0;
        string level = "";
        foreach (var ta in loader.modelData.tributary_areas)
        {
            if (ta == null || ta.elementTag != tag) continue;
            area += ta.A_tributaria_m2;
            load += ta.P_losa_kN;
            if (string.IsNullOrEmpty(level)) level = ta.nivel;
            rows++;
        }
        if (rows == 0) return;
        GUILayout.Label("<b>AREA TRIBUTARIA / CARGA</b>", TextStyle(13));
        GUILayout.Label($"Nivel {level} · {rows} zona(s)\nA={area:F3} m² · P_losa={load:F2} kN", TextStyle(11));
    }

    void DrawElementDiagram(int tag)
    {
        GUILayout.Label("<b>DIAGRAMA DEL ELEMENTO</b>", TextStyle(13));
        if (diagrams == null)
        {
            GUILayout.Label("Controlador de diagramas no disponible.", TextStyle(11));
            return;
        }
        if (!diagrams.Active)
        {
            GUILayout.Label("Activa DIAGRAMA en la barra superior y elige Mz, My, N, Vy, Vz o T.", TextStyle(11));
            return;
        }
        if (diagrams.DrawnTag != tag || diagrams.ChartTexture == null)
        {
            GUILayout.Label("<color=#FFB347>" + diagrams.Status + "</color>", TextStyle(11));
            if (GUILayout.Button("REINTENTAR DIAGRAMA", GUILayout.Height(27))) diagrams.Refresh();
            return;
        }

        GUILayout.Label("<color=#FF62DB><b>" + diagrams.ModeLabel +
                        "</b></color> · caso " + diagrams.DrawnCase,
                        TextStyle(12));
        Rect chartRect = GUILayoutUtility.GetRect(380f, 114f,
                                                  GUILayout.ExpandWidth(true));
        GUI.DrawTexture(chartRect, diagrams.ChartTexture,
                        ScaleMode.StretchToFill, false);
        GUILayout.Label("i = " + diagrams.ChartValueI.ToString("F2") +
                        "   →   j = " + diagrams.ChartValueJ.ToString("F2") +
                        " " + diagrams.CurrentUnits +
                        "\nEje horizontal: longitud i → j", TextStyle(11));
    }

    string BoundaryText(ElementRef r)
    {
        var parts = new List<string>();
        AddBoundary(parts, r.nodeI);
        AddBoundary(parts, r.nodeJ);
        return parts.Count > 0 ? string.Join("\n", parts.ToArray()) : "Extremos sin apoyo directo; revisar diafragma/links del nivel.";
    }

    void AddBoundary(List<string> parts, int tag)
    {
        if (loader == null || !loader.boundaryRestricciones.TryGetValue(tag, out var v)) return;
        string origin = loader.boundaryOrigen.ContainsKey(tag) ? loader.boundaryOrigen[tag] : "";
        parts.Add("Nodo " + tag + " · " + origin + " · [" + string.Join(",", v) + "]");
    }

    string Vec(float[] v) => v != null && v.Length >= 3 ? $"({v[0]:F3}, {v[1]:F3}, {v[2]:F3})" : "N/D";
}
