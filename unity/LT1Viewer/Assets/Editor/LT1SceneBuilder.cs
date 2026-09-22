using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class LT1SceneBuilder
{
    const string ScenePath = "Assets/Scenes/LT1Viewer.unity";

    [MenuItem("LT1/Build LT1Viewer Scene")]
    public static void Build()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,
                                                NewSceneMode.Single);

        // --- Cámara principal ---
        GameObject camGO = new GameObject("Main Camera");
        camGO.tag = "MainCamera";
        Camera cam = camGO.AddComponent<Camera>();
        camGO.AddComponent<AudioListener>();
        cam.fieldOfView = 60f;
        cam.nearClipPlane = 0.05f;
        cam.farClipPlane = 2000f;
        camGO.transform.position = new Vector3(0f, 30f, -45f);
        camGO.transform.rotation = Quaternion.Euler(30f, 0f, 0f);
        camGO.AddComponent<OrbitCamera>();

        // --- Iluminación ---
        GameObject lightGO = new GameObject("Directional Light");
        Light light = lightGO.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.1f;
        lightGO.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        // --- LT1Viewer (loader + controladores) ---
        GameObject viewer = new GameObject("LT1Viewer");
        viewer.AddComponent<StructuralViewer>();
        viewer.AddComponent<VisibilityController>();
        viewer.AddComponent<SelectionController>();
        viewer.AddComponent<TributaryAreaInspector>();
        viewer.AddComponent<IdLabelController>();
        viewer.AddComponent<LocalAxesController>();
        viewer.AddComponent<StructuralResultsController>();
        viewer.AddComponent<DeformedShapeController>();
        viewer.AddComponent<ForceDiagramController>();
        viewer.AddComponent<CaseSelector>();
        viewer.AddComponent<LoadInspector>();
        viewer.AddComponent<PmPanelController>();
        viewer.AddComponent<LoadVisualizationController>();
        viewer.AddComponent<TributaryAreaVisualizationController>();
        viewer.AddComponent<MovingLoadController>();
        viewer.AddComponent<ScenarioModificationController>();
        viewer.AddComponent<SuperpositionController>();
        viewer.AddComponent<UserMovingLoadController>();
        viewer.AddComponent<ViewerHUD>();

        // --- Registrar escena en Build Settings ---
        var buildSettings = EditorBuildSettings.scenes;
        bool found = false;
        foreach (var s in buildSettings)
        {
            string p = AssetDatabase.AssetPathToGUID(s.path);
            string p2 = AssetDatabase.AssetPathToGUID(ScenePath);
            if (!string.IsNullOrEmpty(p) && p == p2) { found = true; break; }
            if (s.path == ScenePath) { found = true; break; }
        }
        System.Collections.Generic.List<EditorBuildSettingsScene> scenes =
            new System.Collections.Generic.List<EditorBuildSettingsScene>(buildSettings);
        if (!found)
        {
            scenes.Add(new EditorBuildSettingsScene(ScenePath, true));
            EditorBuildSettings.scenes = scenes.ToArray();
        }

        // --- Guardar ---
        System.IO.Directory.CreateDirectory("Assets/Scenes");
        bool saved = EditorSceneManager.SaveScene(
            scene, ScenePath, false);
        if (saved)
        {
            Debug.Log("[LT1SceneBuilder] Escena guardada: " + ScenePath);
        }
        else
        {
            Debug.LogError("[LT1SceneBuilder] No se pudo guardar la escena: " + ScenePath);
        }
    }
}
