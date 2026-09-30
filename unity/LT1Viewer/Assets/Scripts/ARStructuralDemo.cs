using System;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

/// <summary>
/// Semana 6: registra un elemento OpenSees sobre una imagen detectada.
///
/// Cadena de coordenadas (las coordenadas OpenSees estan en metros):
///   1) OpenSees -> Unity: u = (X, Z, -Y).
///   2) Unity local -> AR: pAR = TImagen * (traslacion + R * escala * (u-uOrigen)).
///
/// TImagen es la pose que ARKit entrega para ARTrackedImage. El propio
/// ARTrackedImage es un trackable espacial persistente y se utiliza como el
/// anchor asociado a la imagen: ARContent se hace hijo de su Transform.
/// La geometria y el resultado se leen, sin modificarlos, del JSON combinado.
/// </summary>
[DisallowMultipleComponent]
public sealed class ARStructuralDemo : MonoBehaviour
{
    [Header("AR")]
    public ARTrackedImageManager trackedImageManager;
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
    TextMesh worldLabel;
    Vector3 unityI;
    Vector3 unityJ;
    float resultValue;
    string elementType;
    string elementOrigin;
    string status = "Iniciando sesion AR...";
    bool dataReady;

    void Awake()
    {
        if (trackedImageManager == null)
            trackedImageManager = FindFirstObjectByType<ARTrackedImageManager>();
        if (arCamera == null)
            arCamera = Camera.main;

        dataReady = TryLoadElementAndResult(out string error);
        if (!dataReady)
        {
            status = error;
            Debug.LogError("[Semana6 AR] " + error);
        }
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
            SetContentVisible(false);
            status = "Apunte la camara a la imagen de referencia.";
            return;
        }

        bool tracking = selected.trackingState == TrackingState.Tracking;
        if (contentRoot == null)
            BuildContent(selected.transform);
        else if (contentRoot.transform.parent != selected.transform)
            contentRoot.transform.SetParent(selected.transform, false);

        ApplyRegistrationTransform();
        SetContentVisible(tracking);
        status = tracking
            ? "Imagen detectada | pose y anchor activos"
            : "Imagen detectada | tracking limitado";

        if (worldLabel != null && arCamera != null && tracking)
        {
            Vector3 towardCamera = worldLabel.transform.position - arCamera.transform.position;
            if (towardCamera.sqrMagnitude > 0.000001f)
                worldLabel.transform.rotation = Quaternion.LookRotation(towardCamera.normalized, Vector3.up);
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

    bool TryLoadElementAndResult(out string error)
    {
        error = "";
        string path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        if (!File.Exists(path))
        {
            error = "No se encontro " + path;
            return false;
        }

        string json = File.ReadAllText(path);
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
        // en Game View de escritorio y en pantallas de iPhone.
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
