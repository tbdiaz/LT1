using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>Crea la demostracion de deteccion visual de viga sin ARCore.</summary>
public static class MarkerStructuralDemoBuilder
{
    public const string ScenePath = "Assets/Scenes/MarkerStructuralDemo.unity";

    [MenuItem("LT1/Semana 6 A05/Crear escena viga horizontal")]
    public static void Build()
    {
        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        GameObject cameraObject = new GameObject("Marker Camera");
        cameraObject.tag = "MainCamera";
        Camera camera = cameraObject.AddComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = Color.black;
        camera.nearClipPlane = 0.01f;
        camera.farClipPlane = 50f;
        camera.fieldOfView = 60f;
        cameraObject.AddComponent<AudioListener>();

        GameObject demoObject = new GameObject("Semana6_A05_ImageTracking");
        MarkerStructuralDemo demo = demoObject.AddComponent<MarkerStructuralDemo>();
        demo.displayCamera = camera;
        demo.processEveryNFrames = 1;
        demo.lostTimeoutSeconds = 1.0f;
        demo.poseSmoothing = 0.18f;
        demo.stableFramesRequired = 6;
        demo.maximumStableCenterDelta = 0.055f;
        demo.maximumStableAngleDeltaDegrees = 8f;
        demo.maximumStableRelativeWidthDelta = 0.18f;
        demo.luminanceContrast = 20f;
        demo.minimumBeamAspect = 2.8f;
        demo.maximumBeamAspect = 12f;
        demo.maximumScreenTiltDegrees = 22f;
        demo.minimumBeamScreenLength = 0.28f;
        demo.minimumBeamScreenThickness = 0.045f;
        demo.minimumBeamScreenArea = 0.020f;
        demo.minimumLongitudinalEdgeContrast = 8f;
        demo.minimumLongitudinalEdgeSupport = 0.45f;
        demo.maximumThicknessVariation = 0.38f;
        demo.visualAnchorDepthMetres = 1.20f;
        demo.elementTag = 800205;
        demo.loadCase = "COMBO_R";
        demo.resultComponent = "My1";
        demo.displayResultName = "M";
        demo.resultUnits = "kN·m";
        demo.modelScale = 0.035f;
        demo.modelEulerDegrees = Vector3.zero;
        demo.modelTranslationMetres = new Vector3(0f, 0f, 0.015f);

        EditorSceneManager.SaveScene(scene, ScenePath);
        AddSceneToBuildSettings();
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Selection.activeGameObject = demoObject;
        Debug.Log("[Semana6 A05] Escena sin ARCore creada: " + ScenePath);
    }

    static void AddSceneToBuildSettings()
    {
        var scenes = new List<EditorBuildSettingsScene>
        {
            new EditorBuildSettingsScene(ScenePath, true)
        };
        foreach (EditorBuildSettingsScene old in EditorBuildSettings.scenes)
            if (old.path != ScenePath) scenes.Add(old);
        EditorBuildSettings.scenes = scenes.ToArray();
    }
}
