using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

/// <summary>
/// Semana 6: registra un elemento OpenSees sobre una imagen detectada.
///
/// Cadena de coordenadas (las coordenadas OpenSees estan en metros):
///   1) OpenSees -> Unity: u = (X, Z, -Y).
///   2) Unity local -> AR: pAR = TImagen * (traslacion + R * escala * (u-uOrigen)).
///
/// TImagen es la pose que ARCore/ARKit entrega para ARTrackedImage. Al detectar
/// la imagen se crea un ARAnchor en esa pose y ARContent se hace hijo suyo.
/// Si el proveedor no permite crearlo, el ARTrackedImage se usa como respaldo.
/// La geometria y el resultado se leen, sin modificarlos, del JSON combinado.
/// </summary>
[DisallowMultipleComponent]
public sealed class ARStructuralDemo : MonoBehaviour
{
    [Header("AR")]
    public ARTrackedImageManager trackedImageManager;
    public ARAnchorManager anchorManager;
    public Camera arCamera;
    public string referenceImageName = "LT1_AR_REFERENCE";

    [Header("Fuente OpenSees")]
    public string jsonFileName = "modelo_combinado.json";
    public int elementTag = 800205;
    public string loadCase = "COMBO_R";
    [Tooltip("Componente exportada por OpenSees: N1, Vy1, Vz1, T1, My1 o Mz1.")]
    public string resultComponent = "My1";
    public string displayResultName = "M";
    public string resultUnits = "kN·m";

    [Header("Unity local -> AR (respecto de la imagen)")]
    [Min(0.0001f)] public float arScale = 0.035f;
    public Vector3 arEulerDegrees = Vector3.zero;
    public Vector3 arTranslationMetres = new Vector3(0f, 0.015f, 0f);
    [Min(0.001f)] public float visualThicknessMetres = 0.025f;

    GameObject contentRoot;
    GameObject elementObject;
    ARAnchor spatialAnchor;
    TextMesh worldLabel;
    Vector3 unityI;
    Vector3 unityJ;
    float resultValue;
    string elementType;
    string elementOrigin;
    string status = "Iniciando sesion AR...";
    bool dataReady;
    bool anchorRequestPending;

    void Awake()
    {
        if (trackedImageManager == null)
            trackedImageManager = FindFirstObjectByType<ARTrackedImageManager>();
        if (anchorManager == null)
            anchorManager = FindFirstObjectByType<ARAnchorManager>();
        if (arCamera == null)
            arCamera = Camera.main;
    }

    IEnumerator Start()
    {
        string path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        string json;

        // En Android StreamingAssets vive dentro del APK (jar:file://...) y no
        // puede leerse con File.ReadAllText. UnityWebRequest funciona tanto ahi
        // como en una URL; en Editor/iOS se conserva la lectura directa.
        if (path.Contains("://"))
        {
            using UnityWebRequest request = UnityWebRequest.Get(path);
            yield return request.SendWebRequest();
            if (request.result != UnityWebRequest.Result.Success)
            {
                SetDataError("No se pudo leer " + jsonFileName + ": " + request.error);
                yield break;
            }
            json = request.downloadHandler.text;
        }
        else
        {
            if (!File.Exists(path))
            {
                SetDataError("No se encontro " + path);
                yield break;
            }
            json = File.ReadAllText(path);
        }

        dataReady = TryLoadElementAndResult(json, out string error);
        if (!dataReady)
            SetDataError(error);
        else
            status = "Sesion AR iniciada | apunte a la imagen de referencia.";
    }

    void SetDataError(string error)
    {
        dataReady = false;
        status = error;
        Debug.LogError("[Semana6 AR] " + error);
    }

    void Update()
    {
        if (!dataReady || trackedImageManager == null)
            return;

        ARTrackedImage selected = null;
        foreach (ARTrackedImage image in trackedImageManager.trackables)
        {
            if (image.referenceImage.name == referenceImageName)
            {
                selected = image;
                break;
            }
        }

        if (selected == null)
        {
            bool anchorTracking = spatialAnchor != null &&
                                  spatialAnchor.trackingState == TrackingState.Tracking;
            SetContentVisible(anchorTracking);
            status = anchorTracking
                ? "Imagen fuera de cuadro | anchor AR activo"
                : "Apunte la camara a la imagen de referencia.";
            FaceLabelToCamera(anchorTracking);
            return;
        }

        bool tracking = selected.trackingState == TrackingState.Tracking;
        if (contentRoot == null && spatialAnchor == null && !anchorRequestPending)
            CreateAnchorAtImagePose(selected);

        ApplyRegistrationTransform();
        bool contentTracking = spatialAnchor != null
            ? spatialAnchor.trackingState == TrackingState.Tracking
            : tracking;
        SetContentVisible(contentTracking);
        status = spatialAnchor != null && contentTracking
            ? "Imagen detectada | pose y ARAnchor activos"
            : tracking
                ? "Imagen detectada | creando anchor..."
                : "Imagen detectada | tracking limitado";

        FaceLabelToCamera(contentTracking);
    }

    void FaceLabelToCamera(bool tracking)
    {
        if (worldLabel != null && arCamera != null && tracking)
        {
            Vector3 towardCamera = worldLabel.transform.position - arCamera.transform.position;
            if (towardCamera.sqrMagnitude > 0.000001f)
                worldLabel.transform.rotation = Quaternion.LookRotation(towardCamera.normalized, Vector3.up);
        }
    }

    async void CreateAnchorAtImagePose(ARTrackedImage image)
    {
        anchorRequestPending = true;
        status = "Imagen detectada | creando anchor...";

        if (anchorManager != null && anchorManager.enabled)
        {
            var result = await anchorManager.TryAddAnchorAsync(
                new Pose(image.transform.position, image.transform.rotation));
            spatialAnchor = result.value;
        }

        if (this == null) return;
        anchorRequestPending = false;

        if (spatialAnchor != null)
        {
            spatialAnchor.gameObject.name = "ARAnchor_ElementTag_" + elementTag;
            BuildContent(spatialAnchor.transform);
            Debug.Log("[Semana6 AR] ARAnchor creado para elementTag " + elementTag + ".");
        }
        else if (image != null)
        {
            // Un tracked image tambien entrega una pose rastreada estable. Este
            // respaldo permite continuar y deja la condicion visible en Console.
            BuildContent(image.transform);
            Debug.LogWarning("[Semana6 AR] No se pudo crear ARAnchor; se usa ARTrackedImage como anchor de respaldo.");
        }
    }

    void BuildContent(Transform imageAnchor)
    {
        contentRoot = new GameObject("ARContent_ElementTag_" + elementTag);
        // El ARTrackedImage aporta pose (posicion + rotacion) y actua como anchor.
        contentRoot.transform.SetParent(imageAnchor, false);

        elementObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
        elementObject.name = "OpenSees_Element_" + elementTag;
        elementObject.transform.SetParent(contentRoot.transform, false);

        Vector3 localI = unityI;
        Vector3 localJ = unityJ;
        Vector3 direction = localJ - localI;
        float length = direction.magnitude;
        elementObject.transform.localPosition = (localI + localJ) * 0.5f;
        elementObject.transform.localRotation = Quaternion.FromToRotation(Vector3.forward, direction.normalized);

        // El espesor es grafico; no representa ni modifica la seccion estructural.
        float unscaledThickness = visualThicknessMetres / Mathf.Max(arScale, 0.0001f);
        elementObject.transform.localScale = new Vector3(unscaledThickness, unscaledThickness, length);
        var material = new Material(Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard"));
        material.color = new Color(1f, 0.48f, 0.05f, 1f);
        elementObject.GetComponent<Renderer>().material = material;

        GameObject labelObject = new GameObject("TraceabilityLabel_" + elementTag);
        labelObject.transform.SetParent(contentRoot.transform, false);
        labelObject.transform.localPosition = (localI + localJ) * 0.5f + Vector3.up * (0.12f / arScale);
        worldLabel = labelObject.AddComponent<TextMesh>();
        worldLabel.text = LabelText();
        worldLabel.anchor = TextAnchor.LowerCenter;
        worldLabel.alignment = TextAlignment.Center;
        worldLabel.fontSize = 48;
        worldLabel.characterSize = 0.005f / arScale;
        worldLabel.color = Color.white;

        ApplyRegistrationTransform();
    }

    void ApplyRegistrationTransform()
    {
        if (contentRoot == null) return;
        contentRoot.transform.localPosition = arTranslationMetres;
        contentRoot.transform.localRotation = Quaternion.Euler(arEulerDegrees);
        contentRoot.transform.localScale = Vector3.one * arScale;
    }

    void SetContentVisible(bool visible)
    {
        if (contentRoot != null && contentRoot.activeSelf != visible)
            contentRoot.SetActive(visible);
    }

    bool TryLoadElementAndResult(string json, out string error)
    {
        error = "";
        ModeloCombinado root = JsonUtility.FromJson<ModeloCombinado>(json);
        if (root == null || root.nodes == null || root.elements == null)
        {
            error = "El JSON combinado no contiene nodes/elements.";
            return false;
        }

        CombinedElement element = Array.Find(root.elements, e => e.elementTag == elementTag);
        if (element == null)
        {
            error = "elementTag " + elementTag + " no existe en el modelo combinado.";
            return false;
        }

        CombinedNode nodeI = Array.Find(root.nodes, n => n.nodeTag == element.nodeI);
        CombinedNode nodeJ = Array.Find(root.nodes, n => n.nodeTag == element.nodeJ);
        if (nodeI == null || nodeJ == null)
        {
            error = "El elemento no tiene ambos nodos en el JSON.";
            return false;
        }

        // OpenSees -> Unity. Se resta el nodo I para tener un origen local
        // explicable y evitar trasladar coordenadas globales grandes al marker.
        Vector3 uI = OpenSeesToUnity(nodeI.x, nodeI.y, nodeI.z);
        Vector3 uJ = OpenSeesToUnity(nodeJ.x, nodeJ.y, nodeJ.z);
        unityI = Vector3.zero;
        unityJ = uJ - uI;
        elementType = element.tipo;
        elementOrigin = element.origen;

        if (!TryReadForce(json, loadCase, elementTag, resultComponent, out resultValue))
        {
            error = $"No existe results.forces/{loadCase}/{elementTag}/{resultComponent}.";
            return false;
        }

        Debug.Log($"[Semana6 AR] OpenSees tag {elementTag}: " +
                  $"I=({nodeI.x},{nodeI.y},{nodeI.z}), J=({nodeJ.x},{nodeJ.y},{nodeJ.z}) m; " +
                  $"Unity local I={unityI}, J={unityJ}; {displayResultName}={resultValue} {resultUnits}.");
        return true;
    }

    public static Vector3 OpenSeesToUnity(float x, float y, float z)
    {
        return new Vector3(x, z, -y);
    }

    static bool TryReadForce(string json, string caseName, int tag, string component, out float value)
    {
        value = 0f;
        string pattern = "\\\"forces\\\"\\s*:\\s*\\{[\\s\\S]*?\\\"" + Regex.Escape(caseName) +
                         "\\\"\\s*:\\s*\\{[\\s\\S]*?\\\"" + tag +
                         "\\\"\\s*:\\s*\\{([^}]*)\\}";
        Match block = Regex.Match(json, pattern);
        if (!block.Success) return false;
        Match field = Regex.Match(block.Groups[1].Value,
            "\\\"" + Regex.Escape(component) + "\\\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?(?:[eE][+\\-]?\\d+)?)");
        return field.Success && float.TryParse(field.Groups[1].Value, NumberStyles.Float,
            CultureInfo.InvariantCulture, out value);
    }

    string LabelText()
    {
        return $"OpenSees elementTag {elementTag}\n{elementType} | {elementOrigin}\n" +
               $"Caso {loadCase} | {displayResultName} ({resultComponent}) = " +
               $"{resultValue.ToString("F2", CultureInfo.InvariantCulture)} {resultUnits}";
    }

    void OnGUI()
    {
        // Limitar el tamano evita que la linea caso/resultado quede recortada
        // en Game View de escritorio y en pantallas de telefono.
        GUI.skin.label.fontSize = Mathf.Clamp(Screen.width / 55, 20, 34);
        GUI.skin.box.fontSize = Mathf.Clamp(Screen.width / 65, 16, 28);
        var rect = new Rect(20, 20, Screen.width - 40, Mathf.Min(320, Screen.height * 0.38f));
        GUILayout.BeginArea(rect, GUI.skin.box);
        GUILayout.Label("SEMANA 6 | AR + OpenSees");
        GUILayout.Label(status);
        if (dataReady) GUILayout.Label(LabelText());
        GUILayout.EndArea();
    }
}
