using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.XR.ARSubsystems;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;
using UnityEngine.SceneManagement;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using Unity.XR.CoreUtils;

/// <summary>Crea de forma reproducible la escena y biblioteca de Semana 6.</summary>
public static class ARStructuralDemoBuilder
{
    const string ScenePath = "Assets/Scenes/ARStructuralDemo.unity";
    const string LibraryPath = "Assets/AR/LT1ARReferenceLibrary.asset";
    // StreamingAssets conserva la fuente usada por el visor, pero Unity la
    // importa con DefaultImporter. La copia dentro de Assets/AR se importa
    // como Texture2D, que es lo que XRReferenceImageLibrary requiere.
    const string MarkerSourcePath = "Assets/StreamingAssets/pm_column_113022.png";
    const string MarkerPath = "Assets/AR/ReferenceImages/pm_column_113022.png";

    [MenuItem("LT1/Semana 6/Crear o actualizar escena AR")]
    public static void Build()
    {
        EnsureFolder("Assets/AR");
        EnsureFolder("Assets/AR/ReferenceImages");
        EnsureMarkerTexture();
        XRReferenceImageLibrary library = BuildReferenceLibrary();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        GameObject sessionObject = new GameObject("AR Session");
        sessionObject.AddComponent<ARSession>();
        sessionObject.AddComponent<ARInputManager>();

        GameObject originObject = new GameObject("XR Origin (AR)");
        XROrigin origin = originObject.AddComponent<XROrigin>();
        ARTrackedImageManager imageManager = originObject.AddComponent<ARTrackedImageManager>();
        ARAnchorManager anchorManager = originObject.AddComponent<ARAnchorManager>();
        imageManager.referenceLibrary = library;
        imageManager.requestedMaxNumberOfMovingImages = 1;

        GameObject cameraOffset = new GameObject("Camera Offset");
        cameraOffset.transform.SetParent(originObject.transform, false);
        origin.CameraFloorOffsetObject = cameraOffset;

        GameObject cameraObject = new GameObject("AR Camera");
        cameraObject.tag = "MainCamera";
        cameraObject.transform.SetParent(cameraOffset.transform, false);
        Camera camera = cameraObject.AddComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = Color.black;
        camera.nearClipPlane = 0.01f;
        camera.farClipPlane = 100f;
        cameraObject.AddComponent<AudioListener>();
        cameraObject.AddComponent<ARCameraManager>();
        cameraObject.AddComponent<ARCameraBackground>();
        TrackedPoseDriver poseDriver = cameraObject.AddComponent<TrackedPoseDriver>();
        poseDriver.positionInput = new InputActionProperty(new InputAction(
            "AR device position", InputActionType.PassThrough, "<HandheldARInputDevice>/devicePosition"));
        poseDriver.rotationInput = new InputActionProperty(new InputAction(
            "AR device rotation", InputActionType.PassThrough, "<HandheldARInputDevice>/deviceRotation"));
        origin.Camera = camera;

        GameObject demoObject = new GameObject("Semana6_AR_OpenSees");
        ARStructuralDemo demo = demoObject.AddComponent<ARStructuralDemo>();
        demo.trackedImageManager = imageManager;
        demo.anchorManager = anchorManager;
        demo.arCamera = camera;
        demo.referenceImageName = "LT1_AR_REFERENCE";
        demo.elementTag = 800205;
        demo.loadCase = "COMBO_R";
        demo.resultComponent = "My1";
        demo.displayResultName = "M";
        demo.resultUnits = "kN·m";
        demo.arScale = 0.035f;
        demo.arEulerDegrees = Vector3.zero;
        demo.arTranslationMetres = new Vector3(0f, 0.015f, 0f);

        EditorSceneManager.SaveScene(scene, ScenePath);
        AddSceneToBuildSettings();
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Selection.activeGameObject = demoObject;
        Debug.Log("[Semana6 AR] Escena creada: " + ScenePath);
    }

    static XRReferenceImageLibrary BuildReferenceLibrary()
    {
        XRReferenceImageLibrary library = AssetDatabase.LoadAssetAtPath<XRReferenceImageLibrary>(LibraryPath);
        if (library == null)
        {
            library = ScriptableObject.CreateInstance<XRReferenceImageLibrary>();
            AssetDatabase.CreateAsset(library, LibraryPath);
        }

        while (library.count > 0)
            library.RemoveAt(library.count - 1);

        Texture2D marker = AssetDatabase.LoadAssetAtPath<Texture2D>(MarkerPath);
        if (marker == null)
            throw new System.IO.InvalidDataException(
                "La imagen existe pero Unity no pudo importarla como Texture2D: " + MarkerPath);

        library.Add();
        int index = library.count - 1;
        library.SetName(index, "LT1_AR_REFERENCE");
        library.SetTexture(index, marker, true);
        library.SetSpecifySize(index, true);
        const float widthMetres = 0.20f;
        float heightMetres = widthMetres * marker.height / marker.width;
        library.SetSize(index, new Vector2(widthMetres, heightMetres));
        EditorUtility.SetDirty(library);
        return library;
    }

    static void EnsureMarkerTexture()
    {
        string source = System.IO.Path.GetFullPath(MarkerSourcePath);
        string destination = System.IO.Path.GetFullPath(MarkerPath);
        if (!System.IO.File.Exists(source))
            throw new System.IO.FileNotFoundException(
                "No se encontro la imagen fuente de referencia", MarkerSourcePath);

        bool copyRequired = !System.IO.File.Exists(destination) ||
            new System.IO.FileInfo(source).Length != new System.IO.FileInfo(destination).Length;
        if (copyRequired)
            System.IO.File.Copy(source, destination, true);

        AssetDatabase.ImportAsset(MarkerPath, ImportAssetOptions.ForceSynchronousImport |
                                               ImportAssetOptions.ForceUpdate);
    }

    static void AddSceneToBuildSettings()
    {
        var old = EditorBuildSettings.scenes;
        var list = new System.Collections.Generic.List<EditorBuildSettingsScene>();
        list.Add(new EditorBuildSettingsScene(ScenePath, true));
        foreach (var scene in old)
            if (scene.path != ScenePath) list.Add(scene);
        EditorBuildSettings.scenes = list.ToArray();
    }

    static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path)) return;
        string parent = System.IO.Path.GetDirectoryName(path).Replace('\\', '/');
        string name = System.IO.Path.GetFileName(path);
        AssetDatabase.CreateFolder(parent, name);
    }
}
