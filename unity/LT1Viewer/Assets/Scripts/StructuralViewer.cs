using UnityEngine;

public class StructuralViewer : MonoBehaviour
{
    private ModelLoader loader;
    private bool modelLoaded;
    private string loadError;

    void Start()
    {
        loader = GetComponent<ModelLoader>();
        if (loader == null)
            loader = gameObject.AddComponent<ModelLoader>();

        if (!loader.LoadModel())
        {
            loadError = "No se pudo cargar modelo_combinado.json";
            Debug.LogError($"[LT1Viewer] {loadError}");
            return;
        }

        loader.BuildScene();
        EnsureRuntimeControllers();
        modelLoaded = true;

        ConfigureCamera();
        LogSummary();
    }

    void EnsureRuntimeControllers()
    {
        // Mantiene compatibles las escenas ya generadas: al abrir una escena
        // antigua, los nuevos controladores se agregan automaticamente.
        if (GetComponent<LoadVisualizationController>() == null)
            gameObject.AddComponent<LoadVisualizationController>();
        if (GetComponent<TributaryAreaVisualizationController>() == null)
            gameObject.AddComponent<TributaryAreaVisualizationController>();
        if (GetComponent<ViewerHUD>() == null)
            gameObject.AddComponent<ViewerHUD>();
        if (GetComponent<DeformedShapeController>() == null)
            gameObject.AddComponent<DeformedShapeController>();
        if (GetComponent<ForceDiagramController>() == null)
            gameObject.AddComponent<ForceDiagramController>();
        if (GetComponent<MovingLoadController>() == null)
            gameObject.AddComponent<MovingLoadController>();
    }

    void ConfigureCamera()
    {
        Camera cam = Camera.main;
        if (cam == null) return;

        if (cam.GetComponent<OrbitCamera>() == null)
            cam.gameObject.AddComponent<OrbitCamera>();

        OrbitCamera orbit = cam.GetComponent<OrbitCamera>();
        orbit.SetTarget(loader.modelCenter);

        float maxExtent = 0f;
        foreach (var node in loader.modelData.nodes)
        {
            Vector3 pos = ModelLoader.StructToUnity(node.x, node.y, node.z);
            float dist = Vector3.Distance(pos, loader.modelCenter);
            if (dist > maxExtent) maxExtent = dist;
        }

        orbit.distance = Mathf.Max(maxExtent * 1.5f, 5f);
        orbit.minDistance = Mathf.Max(maxExtent * 0.05f, 0.1f);
        orbit.maxDistance = Mathf.Max(maxExtent * 5f, 50f);
    }

    void LogSummary()
    {
        if (loader.modelData == null) return;

        int totalElements = loader.modelData.beams.Length + loader.modelData.columns.Length
                            + loader.modelData.walls.Length;

        string summary = $"COMBINADO Viewer - {loader.modelData.nodes.Length} nodes, " +
                         $"{totalElements} elements, " +
                         $"{loader.modelData.constraint_links.Length} constraintLinks, " +
                         $"{loader.modelData.supports.Length} supports, " +
                         $"{loader.modelData.diaphragms.Length} diaphragms";

        if (loader.combinedRoot != null && loader.combinedRoot.metadata != null)
        {
            var md = loader.combinedRoot.metadata;
            summary += $"\nFuente: {md.modelo} | {md.etapa} | {md.origen_fuente}";
            if (md.unidades != null)
                summary += $"\nUnits: {md.unidades.longitud}"
                           + $"/{md.unidades.fuerza}/{md.unidades.presion}";
            if (md.casos != null)
                summary += $"\nCasos: G, Q, EX, EY, COMBO_R";
        }

        if (loader.modelData.metadata != null)
        {
            var m = loader.modelData.metadata;
            if (m.material != null)
                summary += $"\nMaterial: E={m.material.E_kPa} kPa, nu={m.material.nu}, G={m.material.G_kPa} kPa";
        }

        if (loader.modelData.analysis != null)
        {
            var a = loader.modelData.analysis;
            summary += $"\nAnalisis: {a.estado}, P={a.P_aplicada_kN} kN (caso {a.caso})";
            if (a.reacciones != null)
                summary += $", R_sum={a.suma_Rz_kN} kN";
        }

        Debug.Log(summary);
    }

    void OnGUI()
    {
        DrawInfoPanel();
        DrawStatusBar();
    }

    void DrawInfoPanel()
    {
        return; // resumen incorporado al HUD principal
#pragma warning disable CS0162
        float pw = 340f;
        float ph = modelLoaded ? 210f : 60f;
        float x = 10f;
        float y = 260f;

        GUI.Box(new Rect(x, y, pw, ph), "COMBINADO Viewer");

        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 30));

        if (!modelLoaded)
        {
            if (!string.IsNullOrEmpty(loadError))
            {
                GUIStyle rich = new GUIStyle(GUI.skin.label) { richText = true };
                GUILayout.Label($"<color=red>{loadError}</color>", rich);
            }
            else
                GUILayout.Label("Cargando modelo...");
        }
        else
        {
            int totalElements = loader.modelData.beams.Length + loader.modelData.columns.Length
                                + loader.modelData.walls.Length;
            GUILayout.Label($"Nodos: {loader.modelData.nodes.Length}  |  " +
                           $"Elementos: {totalElements}  |  " +
                           $"Apoyos: {loader.modelData.supports.Length}  |  " +
                           $"Diafragmas: {loader.modelData.diaphragms.Length}");
            GUILayout.Label($"Reacciones: {loader.modelData.constraint_links.Length} rigid  |  " +
                           $"Masters: {(loader.combinedRoot != null && loader.combinedRoot.masters != null ? loader.combinedRoot.masters.Length : 0)}  |  " +
                           $"Notas: {(loader.combinedRoot != null && loader.combinedRoot.metadata != null && loader.combinedRoot.metadata.notas_modelo != null ? loader.combinedRoot.metadata.notas_modelo.Length : 0)}");

            if (loader.modelData.metadata != null && loader.modelData.metadata.material != null)
            {
                var mat = loader.modelData.metadata.material;
                GUILayout.Label($"Material: E={FormatKpa(mat.E_kPa)}  nu={mat.nu}  G={FormatKpa(mat.G_kPa)}");
            }

            if (loader.modelData.analysis != null)
            {
                var a = loader.modelData.analysis;
                GUILayout.Label($"Analisis: {a.estado}  |  P={a.P_aplicada_kN:F1} kN  |  err={a.err_rel:E2}");
                if (!string.IsNullOrEmpty(a.caso))
                    GUILayout.Label($"Caso: {a.caso}  |  fuerzas: "
                        + (a.fuerzas_elementos != null ? a.fuerzas_elementos.Length : 0)
                        + " elementos");
            }

            if (loader.combinedRoot != null && loader.combinedRoot.metadata != null
                && loader.combinedRoot.metadata.notas_modelo != null
                && loader.combinedRoot.metadata.notas_modelo.Length > 0)
            {
                GUIStyle tiny = new GUIStyle(GUI.skin.label) { fontSize = 9 };
                // solo la primera nota para no invadir; el resto en tecla 8
                string n0 = loader.combinedRoot.metadata.notas_modelo[0];
                if (n0.Length > 90) n0 = n0.Substring(0, 90) + "...";
                GUILayout.Label($"Nota: {n0}", tiny);
            }
        }

        GUILayout.EndArea();
#pragma warning restore CS0162
    }

    void DrawStatusBar()
    {
        float h = 25f;
        GUI.Box(new Rect(0, Screen.height - h, Screen.width, h), "");
        GUIStyle centered = new GUIStyle(GUI.skin.label)
        {
            alignment = TextAnchor.MiddleCenter,
            fontSize = 12
        };
        GUI.Label(new Rect(0, Screen.height - h, Screen.width, h),
                  "RMB orbitar | Rueda zoom | MMB pan | LMB seleccionar | R reset | Controles principales en botones",
                  centered);
    }

    string FormatKpa(float kpa)
    {
        if (kpa >= 1e6f) return $"{kpa / 1e6f:F1} GPa";
        if (kpa >= 1e3f) return $"{kpa / 1e3f:F0} MPa";
        return $"{kpa:F0} kPa";
    }
}
