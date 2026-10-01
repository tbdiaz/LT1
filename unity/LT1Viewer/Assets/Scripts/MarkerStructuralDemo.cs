using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.Rendering;

/// <summary>
/// Semana 6 para Android sin ARCore. Detecta una forma rectangular horizontal
/// tipo viga en WebCamTexture y usa su centro, escala y rotacion como referencia
/// visual para el elemento OpenSees 800205.
/// </summary>
[DisallowMultipleComponent]
public sealed class MarkerStructuralDemo : MonoBehaviour
{
    [Header("Camara y deteccion de viga")]
    public Camera displayCamera;
    [Range(1, 8)] public int pixelStep = 4;
    [Range(1, 10)] public int processEveryNFrames = 1;
    [Range(0.05f, 2f)] public float lostTimeoutSeconds = 1.00f;
    [Range(0.01f, 1f)] public float poseSmoothing = 0.18f;
    [Range(2, 20)] public int stableFramesRequired = 6;
    [Range(0.01f, 0.25f)] public float maximumStableCenterDelta = 0.055f;
    [Range(1f, 30f)] public float maximumStableAngleDeltaDegrees = 8f;
    [Range(0.02f, 0.50f)] public float maximumStableRelativeWidthDelta = 0.18f;
    [Range(10f, 80f)] public float luminanceContrast = 20f;
    [Range(2f, 12f)] public float minimumBeamAspect = 2.8f;
    [Range(5f, 25f)] public float maximumBeamAspect = 12f;
    [Range(5f, 35f)] public float maximumScreenTiltDegrees = 22f;
    [Range(0.1f, 0.8f)] public float minimumBeamScreenLength = 0.28f;
    [Range(0.02f, 0.3f)] public float minimumBeamScreenThickness = 0.045f;
    [Range(0.005f, 0.2f)] public float minimumBeamScreenArea = 0.020f;
    [Range(2f, 40f)] public float minimumLongitudinalEdgeContrast = 8f;
    [Range(0.2f, 0.9f)] public float minimumLongitudinalEdgeSupport = 0.45f;
    [Range(0.1f, 0.8f)] public float maximumThicknessVariation = 0.38f;
    [Min(0.25f)] public float visualAnchorDepthMetres = 1.20f;

    [Header("Fuente OpenSees")]
    public string jsonFileName = "semana06_element_800205.json";
    public int elementTag = 800205;
    public string loadCase = "COMBO_R";
    public string resultComponent = "My1";
    public string displayResultName = "M";
    public string resultUnits = "kN·m";

    [Header("Modelo local -> marcador")]
    [Min(0.0001f)] public float modelScale = 0.035f;
    public Vector3 modelEulerDegrees = Vector3.zero;
    public Vector3 modelTranslationMetres = new Vector3(0f, 0f, 0.015f);
    [Min(0.001f)] public float visualThicknessMetres = 0.025f;

    WebCamTexture webcam;
    Color32[] pixels;
    bool[] blobMask;
    int[] blobQueue;
    GameObject backgroundObject;
    Mesh backgroundMesh;
    Material backgroundMaterial;
    GameObject markerAnchor;
    GameObject contentRoot;
    TextMesh worldLabel;
    Vector3 unityI;
    Vector3 unityJ;
    float resultValue;
    string elementType;
    string elementOrigin;
    Semana06BeamData structuralData;
    string status = "Inicializando camara...";
    string cameraDiagnostic = "WebCamTexture: aun no creada";
    bool dataReady;
    bool cameraReady;
    bool cameraPermissionGranted;
    bool cameraHasValidFrame;
    bool poseInitialized;
    int cameraOpenAttempt;
    int cameraFramesReceived;
    int processedFrameCount;
    int lastCandidateCount;
    bool beamDetectedInLastProcessedFrame;
    bool beamConfirmed;
    int stableCandidateFrames;
    Vector2 trackedCenter;
    Vector2 trackedAxis = Vector2.right;
    float trackedWidth;
    Vector2[] lastDetectedCorners;
    float lastCameraFrameTime = -1f;
    float lastMarkerTime = -100f;
    Vector2 resultsScroll;
    int lastScreenWidth;
    int lastScreenHeight;
    int lastVideoAngle = -1;
    bool lastVideoMirror;
    int lastVideoWidth;
    int lastVideoHeight;
    Vector2 cameraCropMin;
    Vector2 cameraCropSize = Vector2.one;
    readonly string[] dataLoadSteps = new string[6];
    bool dataDiagnosticsVisible;

    IEnumerator Start()
    {
        if (displayCamera == null) displayCamera = Camera.main;
        if (displayCamera == null)
        {
            SetError("La escena no contiene una camara principal.");
            yield break;
        }

        status = "Verificando permiso de camara...";
        yield return EnsureCameraPermission();
        if (!cameraPermissionGranted) yield break;

        // En algunos Samsung la lista se publica uno o dos cuadros despues de
        // validar el permiso. Consultarla una sola vez puede devolver cero.
        status = "Buscando camara trasera...";
        float devicesDeadline = Time.realtimeSinceStartup + 10f;
        WebCamDevice[] devices = WebCamTexture.devices;
        while (devices.Length == 0 && Time.realtimeSinceStartup < devicesDeadline)
        {
            yield return null;
            devices = WebCamTexture.devices;
        }

        if (devices.Length == 0)
        {
            SetError("No se encontro una camara disponible.");
            yield break;
        }

        yield return OpenRearCamera(devices);
        if (!cameraHasValidFrame) yield break;

        // La camara se abre antes de leer el JSON combinado (aprox. 16 MB),
        // para que un telefono de entrada no parezca detenido en el permiso.
        CreateCameraBackground();
        status = "Camara activa | cargando paquete liviano del elemento 800205...";
        yield return null;
        yield return LoadStructuralData();
        if (!dataReady)
        {
            webcam.Stop();
            yield break;
        }

        CreateBeamAnchorAndContent();
        cameraReady = true;
        status = "Buscando viga...";
    }

    IEnumerator OpenRearCamera(WebCamDevice[] devices)
    {
        var rearDevices = new List<WebCamDevice>();
        for (int i = 0; i < devices.Length; i++)
        {
            WebCamDevice device = devices[i];
            int resolutionCount = device.availableResolutions == null
                ? 0 : device.availableResolutions.Length;
            Debug.Log($"[CameraDiag] device[{i}] name='{device.name}', " +
                      $"front={device.isFrontFacing}, kind={device.kind}, " +
                      $"resolutions={resolutionCount}");
            if (!device.isFrontFacing && device.kind != WebCamKind.ColorAndDepth)
                rearDevices.Add(device);
        }

        rearDevices.Sort((a, b) => CameraPriority(a.kind).CompareTo(CameraPriority(b.kind)));
        if (rearDevices.Count == 0)
        {
            SetError("El telefono no informo una camara trasera de color disponible.");
            yield break;
        }

        // Primer pase: sin imponer resolucion ni FPS. En algunos Samsung pedir
        // 640x480@30 impide que Camera2 entregue el primer frame aunque Play()
        // no lance una excepcion.
        foreach (WebCamDevice device in rearDevices)
        {
            yield return TryOpenCamera(device, 0, 0);
            if (cameraHasValidFrame) yield break;
        }

        // Segundo pase: solicita una resolucion anunciada por el propio equipo.
        foreach (WebCamDevice device in rearDevices)
        {
            if (!TryChooseCameraResolution(device, out int width, out int height))
                continue;
            yield return TryOpenCamera(device, width, height);
            if (cameraHasValidFrame) yield break;
        }

        SetError("Ninguna camara trasera entrego frames. " + cameraDiagnostic);
    }

    IEnumerator TryOpenCamera(WebCamDevice device, int requestedWidth, int requestedHeight)
    {
        cameraOpenAttempt++;
        cameraHasValidFrame = false;
        cameraFramesReceived = 0;
        lastCameraFrameTime = -1f;

        if (webcam != null)
        {
            if (webcam.isPlaying) webcam.Stop();
            Destroy(webcam);
            webcam = null;
            yield return null;
        }

        string mode = requestedWidth > 0
            ? $"{requestedWidth}x{requestedHeight}"
            : "resolucion nativa";
        status = $"Abriendo camara trasera (intento {cameraOpenAttempt}): " +
                 $"{device.name} | {mode}";

        try
        {
            // El constructor sin restricciones es el camino mas compatible en
            // Android; el segundo pase usa solo resoluciones declaradas.
            webcam = requestedWidth > 0
                ? new WebCamTexture(device.name, requestedWidth, requestedHeight)
                : new WebCamTexture(device.name);
            webcam.Play();
            cameraDiagnostic = "Play()=llamado";
        }
        catch (Exception exception)
        {
            cameraDiagnostic = "Play()=EXCEPCION | " + exception.GetType().Name +
                               ": " + exception.Message;
            Debug.LogError("[CameraDiag] " + cameraDiagnostic);
            yield break;
        }

        float startedAt = Time.realtimeSinceStartup;
        float deadline = startedAt + 8f;
        bool replayed = false;
        while (Time.realtimeSinceStartup < deadline)
        {
            bool updated = webcam.didUpdateThisFrame;
            if (updated)
            {
                cameraFramesReceived++;
                lastCameraFrameTime = Time.realtimeSinceStartup;
            }

            cameraDiagnostic = CameraStateText(updated);
            if (webcam.isPlaying && updated && webcam.width > 16 && webcam.height > 16)
            {
                cameraHasValidFrame = true;
                Debug.Log("[CameraDiag] camara abierta: " + cameraDiagnostic);
                yield break;
            }

            // Algunos controladores aceptan Play() antes de completar la sesion
            // Camera2. Un segundo Play, una sola vez, reactiva esa sesion.
            if (!replayed && !webcam.isPlaying &&
                Time.realtimeSinceStartup - startedAt > 1.5f)
            {
                replayed = true;
                try
                {
                    webcam.Play();
                    cameraDiagnostic += " | Play() reintentado";
                }
                catch (Exception exception)
                {
                    cameraDiagnostic += " | reintento=" + exception.GetType().Name;
                }
            }
            yield return null;
        }

        cameraDiagnostic = "TIMEOUT | " + CameraStateText(webcam.didUpdateThisFrame);
        Debug.LogWarning("[CameraDiag] " + device.name + " fallo: " + cameraDiagnostic);
        if (webcam.isPlaying) webcam.Stop();
    }

    string CameraStateText(bool updated) =>
        $"Play()=llamado | isPlaying={webcam != null && webcam.isPlaying} | " +
        $"didUpdateThisFrame={updated} | " +
        $"size={(webcam == null ? 0 : webcam.width)}x{(webcam == null ? 0 : webcam.height)} | " +
        $"frames={cameraFramesReceived} | device='{(webcam == null ? "" : webcam.deviceName)}'";

    static int CameraPriority(WebCamKind kind)
    {
        if (kind == WebCamKind.WideAngle) return 0;
        if (kind == WebCamKind.Unknown) return 1;
        if (kind == WebCamKind.UltraWideAngle) return 2;
        if (kind == WebCamKind.Telephoto) return 3;
        return 4;
    }

    static bool TryChooseCameraResolution(WebCamDevice device, out int width, out int height)
    {
        width = 0;
        height = 0;
        Resolution[] resolutions = device.availableResolutions;
        if (resolutions == null || resolutions.Length == 0) return false;

        int targetArea = 640 * 480;
        long bestScore = long.MaxValue;
        foreach (Resolution resolution in resolutions)
        {
            if (resolution.width <= 16 || resolution.height <= 16) continue;
            long area = (long)resolution.width * resolution.height;
            long score = Math.Abs(area - targetArea);
            if (score < bestScore)
            {
                bestScore = score;
                width = resolution.width;
                height = resolution.height;
            }
        }
        return width > 0 && height > 0;
    }

    IEnumerator EnsureCameraPermission()
    {
#if UNITY_ANDROID && !UNITY_EDITOR
        // Application.RequestUserAuthorization puede quedar esperando en
        // ciertos Samsung aunque CAMERA ya figure como concedido. La API
        // Android de Unity permite resolver primero ese caso sin abrir dialogo.
        if (UnityEngine.Android.Permission.HasUserAuthorizedPermission(
                UnityEngine.Android.Permission.Camera))
        {
            cameraPermissionGranted = true;
            yield break;
        }

        bool permissionResolved = false;
        bool permissionGranted = false;
        var callbacks = new UnityEngine.Android.PermissionCallbacks();
        callbacks.PermissionGranted += _ =>
        {
            permissionGranted = true;
            permissionResolved = true;
        };
        callbacks.PermissionDenied += _ => permissionResolved = true;
        callbacks.PermissionDeniedAndDontAskAgain += _ => permissionResolved = true;

        UnityEngine.Android.Permission.RequestUserPermission(
            UnityEngine.Android.Permission.Camera, callbacks);

        float permissionDeadline = Time.realtimeSinceStartup + 20f;
        while (!permissionResolved && Time.realtimeSinceStartup < permissionDeadline)
            yield return null;

        cameraPermissionGranted = permissionGranted ||
            UnityEngine.Android.Permission.HasUserAuthorizedPermission(
                UnityEngine.Android.Permission.Camera);
#else
        yield return Application.RequestUserAuthorization(UserAuthorization.WebCam);
        cameraPermissionGranted =
            Application.HasUserAuthorization(UserAuthorization.WebCam);
#endif

        if (!cameraPermissionGranted)
            SetError("Se requiere permiso de camara para detectar el marcador.");
    }

    IEnumerator LoadStructuralData()
    {
        string path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        string json = null;
        status = "Abriendo paquete liviano " + jsonFileName + "...";
        yield return null;

        if (path.Contains("://"))
        {
            UnityWebRequest request = null;
            UnityWebRequestAsyncOperation operation = null;
            try
            {
                request = UnityWebRequest.Get(path);
                request.timeout = 10;
                operation = request.SendWebRequest();
            }
            catch (Exception exception)
            {
                request?.Dispose();
                SetError("ERROR paquete 800205: no se pudo abrir: " +
                         exception.GetType().Name + " - " + exception.Message);
                yield break;
            }

            status = "Leyendo paquete liviano 800205...";
            float readDeadline = Time.realtimeSinceStartup + 10f;
            while (!operation.isDone && Time.realtimeSinceStartup < readDeadline)
                yield return null;

            if (!operation.isDone)
            {
                request.Abort();
                request.Dispose();
                SetError("ERROR paquete 800205: timeout de lectura tras 10 s.");
                yield break;
            }
            if (request.result != UnityWebRequest.Result.Success)
            {
                string requestError = request.error;
                request.Dispose();
                SetError("ERROR paquete 800205: lectura Android: " + requestError);
                yield break;
            }
            try
            {
                byte[] bytes = request.downloadHandler.data;
                json = bytes == null ? null : Encoding.UTF8.GetString(bytes);
            }
            catch (Exception exception)
            {
                request.Dispose();
                SetError("ERROR paquete 800205: no se pudo decodificar: " +
                         exception.GetType().Name + " - " + exception.Message);
                yield break;
            }
            request.Dispose();
        }
        else
        {
            if (!File.Exists(path))
            {
                SetError("ERROR paquete 800205: archivo inexistente: " + path);
                yield break;
            }
            status = "Leyendo paquete liviano 800205...";
            yield return null;
            try
            {
                json = File.ReadAllText(path);
            }
            catch (Exception exception)
            {
                SetError("ERROR paquete 800205: lectura local: " +
                         exception.GetType().Name + " - " + exception.Message);
                yield break;
            }
        }

        if (string.IsNullOrEmpty(json))
        {
            SetError("ERROR paquete 800205: archivo vacio.");
            yield break;
        }

        status = "Validando geometria y resultados reales de 800205...";
        yield return null;
        try
        {
            structuralData = JsonUtility.FromJson<Semana06BeamData>(json);
        }
        catch (Exception exception)
        {
            SetError("ERROR paquete 800205: JSON invalido: " + exception.Message);
            yield break;
        }
        if (structuralData == null || structuralData.element == null ||
            structuralData.elementTag != elementTag || structuralData.nodes == null ||
            structuralData.nodes.Length != 2 || structuralData.forceCases == null ||
            structuralData.forceCases.Length == 0)
        {
            SetError("ERROR paquete 800205: faltan elemento, nodos o resultados.");
            yield break;
        }

        Semana06Node nodeI = structuralData.nodes[0];
        Semana06Node nodeJ = structuralData.nodes[1];
        Vector3 rawI = OpenSeesToUnity(nodeI.x, nodeI.y, nodeI.z);
        Vector3 rawJ = OpenSeesToUnity(nodeJ.x, nodeJ.y, nodeJ.z);
        Vector3 midpoint = (rawI + rawJ) * 0.5f;
        unityI = rawI - midpoint;
        unityJ = rawJ - midpoint;
        elementType = structuralData.element.type;
        elementOrigin = structuralData.element.origin;
        Semana06ForceCase combo = Array.Find(structuralData.forceCases,
            item => item.caseName == loadCase);
        if (combo == null)
        {
            SetError("ERROR paquete 800205: no existe COMBO_R.");
            yield break;
        }
        resultValue = combo.My1;
        dataReady = true;
        status = "Buscando viga...";
    }

    void Update()
    {
        if (webcam == null || !webcam.isPlaying) return;

        UpdateCameraBackground();
        bool updated = webcam.didUpdateThisFrame;
        if (updated)
        {
            cameraFramesReceived++;
            lastCameraFrameTime = Time.realtimeSinceStartup;
        }
        cameraDiagnostic = CameraStateText(updated) +
            $" | ultimoFrameHace={(lastCameraFrameTime < 0f ? -1f : Time.realtimeSinceStartup - lastCameraFrameTime):F2}s";

        // En ciertos controladores Camera2 (incluido el Galaxy A05),
        // didUpdateThisFrame puede llegar en un momento distinto del Update de
        // Unity aunque la textura se actualice y se renderice correctamente.
        // El detector lee directamente y de forma continua la MISMA instancia
        // WebCamTexture asignada al material de fondo. GetPixels32 devuelve el
        // frame mas reciente disponible sin abrir una segunda camara.
        bool detectorCanRead = cameraHasValidFrame && dataReady &&
            markerAnchor != null && webcam.width > 16 && webcam.height > 16;
        if (detectorCanRead && Time.frameCount % processEveryNFrames == 0)
            ProcessCameraFrame();

        bool showConfirmedContent = HasConfirmedBeam();
        if (contentRoot != null) contentRoot.SetActive(showConfirmedContent);
        if (beamConfirmed && !showConfirmedContent)
        {
            beamConfirmed = false;
            beamDetectedInLastProcessedFrame = false;
            stableCandidateFrames = 0;
            poseInitialized = false;
            lastDetectedCorners = null;
            status = "Buscando viga...";
        }

        FaceLabelToCamera(showConfirmedContent);
    }

    void ProcessCameraFrame()
    {
        int width = webcam.width;
        int height = webcam.height;
        if (width <= 16 || height <= 16) return;
        pixels = webcam.GetPixels32(pixels);
        processedFrameCount++;

        if (!TryFindHorizontalBeam(width, height, out Vector2[] corners,
                out Vector2 displayCenter, out Vector2 displayAxis, out float displayWidth,
                out lastCandidateCount))
        {
            beamDetectedInLastProcessedFrame = false;
            if (!beamConfirmed)
            {
                stableCandidateFrames = 0;
                status = "Buscando viga...";
            }
            return;
        }

        if (!beamConfirmed)
        {
            if (stableCandidateFrames == 0 ||
                !IsCompatibleCandidate(displayCenter, displayAxis, displayWidth))
            {
                trackedCenter = displayCenter;
                trackedAxis = displayAxis;
                trackedWidth = displayWidth;
                stableCandidateFrames = 1;
            }
            else
            {
                SmoothTrackedCandidate(displayCenter, displayAxis, displayWidth, 0.25f);
                stableCandidateFrames++;
            }

            beamDetectedInLastProcessedFrame = false;
            status = "Buscando viga...";
            if (stableCandidateFrames < stableFramesRequired) return;

            beamConfirmed = true;
            poseInitialized = false;
            lastDetectedCorners = (Vector2[])corners.Clone();
        }
        else
        {
            // Una forma distinta o un salto grande no mueve inmediatamente el
            // contenido: se conserva el ultimo anchor durante el timeout corto.
            if (!IsCompatibleCandidate(displayCenter, displayAxis, displayWidth))
            {
                beamDetectedInLastProcessedFrame = false;
                return;
            }
            SmoothTrackedCandidate(displayCenter, displayAxis, displayWidth, poseSmoothing);
            SmoothDetectedCorners(corners);
        }

        Vector3 centerAtDepth = displayCamera.ViewportToWorldPoint(
            new Vector3(trackedCenter.x, trackedCenter.y, visualAnchorDepthMetres));
        Vector2 rightUv = trackedCenter + trackedAxis * trackedWidth * 0.5f;
        Vector2 leftUv = trackedCenter - trackedAxis * trackedWidth * 0.5f;
        Vector3 rightAtDepth = displayCamera.ViewportToWorldPoint(
            new Vector3(rightUv.x, rightUv.y, visualAnchorDepthMetres));
        Vector3 leftAtDepth = displayCamera.ViewportToWorldPoint(
            new Vector3(leftUv.x, leftUv.y, visualAnchorDepthMetres));
        Vector3 position = displayCamera.transform.InverseTransformPoint(centerAtDepth);
        Vector3 widthDirection = displayCamera.transform.InverseTransformDirection(
            rightAtDepth - leftAtDepth);
        if (widthDirection.sqrMagnitude < 0.000001f) return;
        Quaternion rotation = Quaternion.FromToRotation(Vector3.right, widthDirection.normalized);
        float detectedWorldWidth = Vector3.Distance(leftAtDepth, rightAtDepth);
        float dynamicScale = detectedWorldWidth / Mathf.Max(structuralData.element.length_m, 0.001f);

        bool hadPose = poseInitialized;
        if (!hadPose)
        {
            markerAnchor.transform.localPosition = position;
            markerAnchor.transform.localRotation = rotation;
            poseInitialized = true;
        }
        else
        {
            markerAnchor.transform.localPosition = Vector3.Lerp(
                markerAnchor.transform.localPosition, position, poseSmoothing);
            markerAnchor.transform.localRotation = Quaternion.Slerp(
                markerAnchor.transform.localRotation, rotation, poseSmoothing);
        }
        contentRoot.transform.localScale = Vector3.Lerp(
            contentRoot.transform.localScale, Vector3.one * dynamicScale,
            hadPose ? poseSmoothing : 1f);

        beamDetectedInLastProcessedFrame = true;
        lastMarkerTime = Time.time;
        status = "VIGA DETECTADA";
    }

    bool HasConfirmedBeam() =>
        beamConfirmed && Time.time - lastMarkerTime <= lostTimeoutSeconds;

    bool IsCompatibleCandidate(Vector2 center, Vector2 axis, float width)
    {
        if (trackedWidth <= 0.0001f) return true;
        float centerDelta = Vector2.Distance(center, trackedCenter);
        float dot = Mathf.Clamp(Mathf.Abs(Vector2.Dot(axis.normalized,
                                                       trackedAxis.normalized)), 0f, 1f);
        float angleDelta = Mathf.Acos(dot) * Mathf.Rad2Deg;
        float relativeWidthDelta = Mathf.Abs(width - trackedWidth) /
                                   Mathf.Max(trackedWidth, 0.0001f);
        return centerDelta <= maximumStableCenterDelta &&
               angleDelta <= maximumStableAngleDeltaDegrees &&
               relativeWidthDelta <= maximumStableRelativeWidthDelta;
    }

    void SmoothTrackedCandidate(Vector2 center, Vector2 axis, float width, float amount)
    {
        trackedCenter = Vector2.Lerp(trackedCenter, center, amount);
        Vector2 alignedAxis = Vector2.Dot(axis, trackedAxis) < 0f ? -axis : axis;
        trackedAxis = Vector2.Lerp(trackedAxis, alignedAxis, amount).normalized;
        trackedWidth = Mathf.Lerp(trackedWidth, width, amount);
    }

    void SmoothDetectedCorners(Vector2[] corners)
    {
        if (lastDetectedCorners == null || lastDetectedCorners.Length != 4)
        {
            lastDetectedCorners = (Vector2[])corners.Clone();
            return;
        }
        for (int i = 0; i < 4; i++)
            lastDetectedCorners[i] = Vector2.Lerp(lastDetectedCorners[i], corners[i],
                                                  poseSmoothing);
    }

    bool TryFindHorizontalBeam(int width, int height, out Vector2[] corners,
                               out Vector2 center, out Vector2 axis, out float beamWidth,
                               out int candidatesFound)
    {
        corners = null;
        center = Vector2.zero;
        axis = Vector2.right;
        beamWidth = 0f;
        candidatesFound = 0;

        bool darkFound = TryFindHorizontalBeamCandidate(width, height, false,
            out Vector2[] darkCorners, out Vector2 darkCenter, out Vector2 darkAxis,
            out float darkWidth, out float darkScore, out int darkCandidates);
        bool brightFound = TryFindHorizontalBeamCandidate(width, height, true,
            out Vector2[] brightCorners, out Vector2 brightCenter, out Vector2 brightAxis,
            out float brightWidth, out float brightScore, out int brightCandidates);
        candidatesFound = darkCandidates + brightCandidates;

        if (!darkFound && !brightFound) return false;
        if (brightFound && (!darkFound || brightScore > darkScore))
        {
            corners = brightCorners;
            center = brightCenter;
            axis = brightAxis;
            beamWidth = brightWidth;
        }
        else
        {
            corners = darkCorners;
            center = darkCenter;
            axis = darkAxis;
            beamWidth = darkWidth;
        }
        return true;
    }

    bool TryFindHorizontalBeamCandidate(int width, int height, bool bright,
                                        out Vector2[] bestCorners, out Vector2 bestCenter,
                                        out Vector2 bestAxis, out float bestWidth,
                                        out float bestScore, out int candidatesFound)
    {
        bestCorners = null;
        bestCenter = Vector2.zero;
        bestAxis = Vector2.right;
        bestWidth = 0f;
        bestScore = 0f;
        candidatesFound = 0;
        int step = Mathf.Max(1, pixelStep);
        int gridWidth = (width + step - 1) / step;
        int gridHeight = (height + step - 1) / step;
        int cells = gridWidth * gridHeight;
        if (blobMask == null || blobMask.Length != cells) blobMask = new bool[cells];
        if (blobQueue == null || blobQueue.Length != cells) blobQueue = new int[cells];

        double luminanceSum = 0.0;
        for (int gy = 0; gy < gridHeight; gy++)
        {
            int py = Mathf.Min(gy * step, height - 1);
            for (int gx = 0; gx < gridWidth; gx++)
            {
                int px = Mathf.Min(gx * step, width - 1);
                Color32 color = pixels[py * width + px];
                luminanceSum += 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b;
            }
        }
        float mean = (float)(luminanceSum / Math.Max(cells, 1));
        for (int gy = 0; gy < gridHeight; gy++)
        {
            int py = Mathf.Min(gy * step, height - 1);
            for (int gx = 0; gx < gridWidth; gx++)
            {
                int px = Mathf.Min(gx * step, width - 1);
                Color32 color = pixels[py * width + px];
                float luminance = 0.2126f * color.r + 0.7152f * color.g + 0.0722f * color.b;
                blobMask[gy * gridWidth + gx] = bright
                    ? luminance > mean + luminanceContrast
                    : luminance < mean - luminanceContrast;
            }
        }

        int minimumCells = Mathf.Max(24, cells / 350);
        for (int start = 0; start < cells; start++)
        {
            if (!blobMask[start]) continue;
            int head = 0;
            int tail = 0;
            blobQueue[tail++] = start;
            blobMask[start] = false;
            int count = 0;
            double sumX = 0.0, sumY = 0.0, sumXX = 0.0, sumYY = 0.0, sumXY = 0.0;

            while (head < tail)
            {
                int current = blobQueue[head++];
                int x = current % gridWidth;
                int y = current / gridWidth;
                float px = Mathf.Min(x * step, width - 1);
                float py = Mathf.Min(y * step, height - 1);
                count++;
                sumX += px; sumY += py;
                sumXX += px * px; sumYY += py * py; sumXY += px * py;
                Visit(x - 1, y, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x + 1, y, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x, y - 1, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x, y + 1, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x - 1, y - 1, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x + 1, y - 1, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x - 1, y + 1, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x + 1, y + 1, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                // Puentea una interrupcion de un solo pixel de muestreo. Esto
                // conserva una viga parcialmente tapada por cables delgados.
                Visit(x - 2, y, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x + 2, y, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x, y - 2, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
                Visit(x, y + 2, gridWidth, gridHeight, blobMask, blobQueue, ref tail);
            }
            if (count < minimumCells) continue;

            float cx = (float)(sumX / count);
            float cy = (float)(sumY / count);
            float covXX = (float)(sumXX / count - cx * cx);
            float covYY = (float)(sumYY / count - cy * cy);
            float covXY = (float)(sumXY / count - cx * cy);
            float trace = covXX + covYY;
            float root = Mathf.Sqrt(Mathf.Max(0f,
                (covXX - covYY) * (covXX - covYY) + 4f * covXY * covXY));
            float lambdaLong = Mathf.Max((trace + root) * 0.5f, 0.001f);
            float lambdaShort = Mathf.Max((trace - root) * 0.5f, 0.001f);
            float aspect = Mathf.Sqrt(lambdaLong / lambdaShort);
            if (aspect < minimumBeamAspect || aspect > maximumBeamAspect) continue;

            float angle = 0.5f * Mathf.Atan2(2f * covXY, covXX - covYY);
            Vector2 rawAxis = new Vector2(Mathf.Cos(angle), Mathf.Sin(angle));
            float halfLong = Mathf.Sqrt(3f * lambdaLong);
            float halfShort = Mathf.Sqrt(3f * lambdaShort);
            float estimatedArea = 12f * Mathf.Sqrt(lambdaLong * lambdaShort);
            float fill = count * step * step / Mathf.Max(estimatedArea, 1f);
            if (fill < 0.32f) continue;

            Vector2 rawCenter = new Vector2(cx / (width - 1f), cy / (height - 1f));
            Vector2 rawAxisUv = new Vector2(rawAxis.x * halfLong / (width - 1f),
                                            rawAxis.y * halfLong / (height - 1f));
            Vector2 rawPerpUv = new Vector2(-rawAxis.y * halfShort / (width - 1f),
                                             rawAxis.x * halfShort / (height - 1f));
            Vector2 displayCenter = RawToDisplayUv(rawCenter);
            Vector2 longEndA = RawToDisplayUv(rawCenter - rawAxisUv);
            Vector2 longEndB = RawToDisplayUv(rawCenter + rawAxisUv);
            Vector2 shortEndA = RawToDisplayUv(rawCenter - rawPerpUv);
            Vector2 shortEndB = RawToDisplayUv(rawCenter + rawPerpUv);
            Vector2 displayAxis = (longEndB - longEndA).normalized;
            if (displayAxis.x < 0f) displayAxis = -displayAxis;
            float tilt = Mathf.Abs(Mathf.Atan2(displayAxis.y, displayAxis.x) * Mathf.Rad2Deg);
            float displayLong = Vector2.Distance(longEndA, longEndB);
            float displayShort = Vector2.Distance(shortEndA, shortEndB);
            float screenArea = displayLong * displayShort;
            if (tilt > maximumScreenTiltDegrees ||
                displayLong < minimumBeamScreenLength ||
                displayShort < minimumBeamScreenThickness ||
                screenArea < minimumBeamScreenArea || screenArea > 0.55f)
                continue;

            // El mismo crop usado para dibujar la camara puede dejar partes del
            // sensor fuera de pantalla. Solo se aceptan vigas visibles completas.
            if (displayCenter.x < 0f || displayCenter.x > 1f ||
                displayCenter.y < 0f || displayCenter.y > 1f)
                continue;

            Vector2 up = new Vector2(-displayAxis.y, displayAxis.x);
            if (up.y < 0f) up = -up;
            if (!ValidateStructuralBeamBand(width, height, displayCenter, displayAxis,
                    up, displayLong, displayShort, out Vector2 refinedCenter,
                    out float refinedThickness, out float structuralQuality))
                continue;
            displayCenter = refinedCenter;
            displayShort = refinedThickness;
            Vector2[] candidate = {
                displayCenter - displayAxis * displayLong * 0.5f + up * displayShort * 0.5f,
                displayCenter + displayAxis * displayLong * 0.5f + up * displayShort * 0.5f,
                displayCenter + displayAxis * displayLong * 0.5f - up * displayShort * 0.5f,
                displayCenter - displayAxis * displayLong * 0.5f - up * displayShort * 0.5f
            };
            bool entirelyVisible = true;
            foreach (Vector2 corner in candidate)
                entirelyVisible &= corner.x >= 0f && corner.x <= 1f &&
                                   corner.y >= 0f && corner.y <= 1f;
            if (!entirelyVisible) continue;
            candidatesFound++;
            float score = displayLong * displayShort * Mathf.Clamp01(fill) *
                          structuralQuality;
            if (score <= bestScore) continue;
            bestScore = score;
            bestCorners = candidate;
            bestCenter = displayCenter;
            bestAxis = displayAxis;
            bestWidth = displayLong;
        }
        return bestCorners != null;
    }

    bool ValidateStructuralBeamBand(int width, int height, Vector2 center,
                                    Vector2 axis, Vector2 normal, float length,
                                    float estimatedThickness,
                                    out Vector2 refinedCenter,
                                    out float refinedThickness,
                                    out float quality)
    {
        refinedCenter = center;
        refinedThickness = estimatedThickness;
        quality = 0f;
        const int stations = 18;
        int topEdgeStations = 0;
        int bottomEdgeStations = 0;
        int pairedEdgeStations = 0;
        int continuousInteriorStations = 0;
        float thicknessSum = 0f;
        float thicknessSquaredSum = 0f;
        float centerOffsetSum = 0f;
        float edgeStrengthSum = 0f;

        float expectedHalf = estimatedThickness * 0.5f;
        float searchRadius = Mathf.Max(expectedHalf * 0.42f, 0.008f);
        float edgeProbe = Mathf.Clamp(estimatedThickness * 0.09f, 0.004f, 0.018f);

        for (int station = 0; station < stations; station++)
        {
            float along = Mathf.Lerp(-0.46f, 0.46f, station / (stations - 1f));
            Vector2 stationCenter = center + axis * (length * along);
            bool topFound = TryFindLongitudinalEdge(width, height, stationCenter,
                normal, expectedHalf, searchRadius, edgeProbe,
                out float topOffset, out float topStrength);
            bool bottomFound = TryFindLongitudinalEdge(width, height, stationCenter,
                normal, -expectedHalf, searchRadius, edgeProbe,
                out float bottomOffset, out float bottomStrength);

            if (topFound) topEdgeStations++;
            if (bottomFound) bottomEdgeStations++;
            if (topFound && bottomFound && topOffset > bottomOffset)
            {
                float measuredThickness = topOffset - bottomOffset;
                // Rechaza pares pertenecientes a objetos distintos o a cables.
                if (measuredThickness >= minimumBeamScreenThickness * 0.75f &&
                    measuredThickness <= estimatedThickness * 1.75f)
                {
                    pairedEdgeStations++;
                    thicknessSum += measuredThickness;
                    thicknessSquaredSum += measuredThickness * measuredThickness;
                    centerOffsetSum += (topOffset + bottomOffset) * 0.5f;
                    edgeStrengthSum += (topStrength + bottomStrength) * 0.5f;
                }
            }

            // La superficie entre bordes debe ser una banda razonablemente
            // continua. Se permiten estaciones fallidas por instalaciones.
            if (TrySampleLuminance(width, height,
                    stationCenter - normal * expectedHalf * 0.45f, out float innerA) &&
                TrySampleLuminance(width, height, stationCenter, out float innerB) &&
                TrySampleLuminance(width, height,
                    stationCenter + normal * expectedHalf * 0.45f, out float innerC))
            {
                float range = Mathf.Max(innerA, Mathf.Max(innerB, innerC)) -
                              Mathf.Min(innerA, Mathf.Min(innerB, innerC));
                if (range <= 70f) continuousInteriorStations++;
            }
        }

        float topSupport = topEdgeStations / (float)stations;
        float bottomSupport = bottomEdgeStations / (float)stations;
        float pairedSupport = pairedEdgeStations / (float)stations;
        float interiorSupport = continuousInteriorStations / (float)stations;
        if (topSupport < minimumLongitudinalEdgeSupport ||
            bottomSupport < minimumLongitudinalEdgeSupport ||
            pairedSupport < minimumLongitudinalEdgeSupport * 0.72f ||
            interiorSupport < 0.50f || pairedEdgeStations < 6)
            return false;

        float meanThickness = thicknessSum / pairedEdgeStations;
        float variance = Mathf.Max(0f,
            thicknessSquaredSum / pairedEdgeStations - meanThickness * meanThickness);
        float coefficientOfVariation = Mathf.Sqrt(variance) /
                                       Mathf.Max(meanThickness, 0.0001f);
        if (coefficientOfVariation > maximumThicknessVariation) return false;

        float meanCenterOffset = centerOffsetSum / pairedEdgeStations;
        refinedCenter = center + normal * meanCenterOffset;
        refinedThickness = meanThickness;
        float edgeQuality = Mathf.Clamp01(
            edgeStrengthSum / pairedEdgeStations /
            Mathf.Max(minimumLongitudinalEdgeContrast * 2f, 1f));
        float constantThicknessQuality = 1f -
            Mathf.Clamp01(coefficientOfVariation /
                          Mathf.Max(maximumThicknessVariation, 0.001f));
        quality = Mathf.Clamp01(0.35f * pairedSupport +
                                0.25f * interiorSupport +
                                0.20f * edgeQuality +
                                0.20f * constantThicknessQuality);
        return quality >= 0.42f;
    }

    bool TryFindLongitudinalEdge(int width, int height, Vector2 stationCenter,
                                 Vector2 normal, float expectedOffset,
                                 float searchRadius, float probe,
                                 out float bestOffset, out float bestStrength)
    {
        bestOffset = expectedOffset;
        bestStrength = 0f;
        const int searchSteps = 8;
        for (int step = 0; step <= searchSteps; step++)
        {
            float offset = expectedOffset +
                Mathf.Lerp(-searchRadius, searchRadius, step / (float)searchSteps);
            if (!TrySampleLuminance(width, height,
                    stationCenter + normal * (offset - probe), out float before) ||
                !TrySampleLuminance(width, height,
                    stationCenter + normal * (offset + probe), out float after))
                continue;
            float strength = Mathf.Abs(after - before);
            if (strength > bestStrength)
            {
                bestStrength = strength;
                bestOffset = offset;
            }
        }
        return bestStrength >= minimumLongitudinalEdgeContrast;
    }

    bool TrySampleLuminance(int width, int height, Vector2 displayUv,
                            out float luminance)
    {
        luminance = 0f;
        if (displayUv.x < 0f || displayUv.x > 1f ||
            displayUv.y < 0f || displayUv.y > 1f)
            return false;
        Vector2 rawUv = DisplayToRawUv(displayUv);
        int x = Mathf.Clamp(Mathf.RoundToInt(rawUv.x * (width - 1)), 0, width - 1);
        int y = Mathf.Clamp(Mathf.RoundToInt(rawUv.y * (height - 1)), 0, height - 1);
        Color32 color = pixels[y * width + x];
        luminance = 0.2126f * color.r + 0.7152f * color.g + 0.0722f * color.b;
        return true;
    }

    static void Visit(int x, int y, int width, int height, bool[] mask,
                      int[] queue, ref int tail)
    {
        if (x < 0 || x >= width || y < 0 || y >= height) return;
        int index = y * width + x;
        if (!mask[index]) return;
        mask[index] = false;
        queue[tail++] = index;
    }

    Vector2 RawToDisplayUv(Vector2 uv)
    {
        Vector2 rotated;
        switch ((webcam.videoRotationAngle % 360 + 360) % 360)
        {
            case 90: rotated = new Vector2(uv.y, 1f - uv.x); break;
            case 180: rotated = new Vector2(1f - uv.x, 1f - uv.y); break;
            case 270: rotated = new Vector2(1f - uv.y, uv.x); break;
            default: rotated = uv; break;
        }
        if (webcam.videoVerticallyMirrored) rotated.y = 1f - rotated.y;
        return new Vector2(
            (rotated.x - cameraCropMin.x) / Mathf.Max(cameraCropSize.x, 0.0001f),
            (rotated.y - cameraCropMin.y) / Mathf.Max(cameraCropSize.y, 0.0001f));
    }

    Vector2 DisplayToRawUv(Vector2 uv)
    {
        uv = new Vector2(
            cameraCropMin.x + uv.x * cameraCropSize.x,
            cameraCropMin.y + uv.y * cameraCropSize.y);
        if (webcam.videoVerticallyMirrored) uv.y = 1f - uv.y;
        switch ((webcam.videoRotationAngle % 360 + 360) % 360)
        {
            case 90: return new Vector2(1f - uv.y, uv.x);
            case 180: return new Vector2(1f - uv.x, 1f - uv.y);
            case 270: return new Vector2(uv.y, 1f - uv.x);
            default: return uv;
        }
    }

    void CreateCameraBackground()
    {
        backgroundObject = new GameObject("CameraBackground_NoARCore");
        backgroundObject.transform.SetParent(displayCamera.transform, false);
        backgroundObject.transform.localPosition = new Vector3(0f, 0f, 10f);
        backgroundObject.transform.localRotation = Quaternion.identity;
        backgroundMesh = new Mesh { name = "CameraBackgroundMesh" };
        backgroundObject.AddComponent<MeshFilter>().sharedMesh = backgroundMesh;
        MeshRenderer renderer = backgroundObject.AddComponent<MeshRenderer>();
        renderer.shadowCastingMode = ShadowCastingMode.Off;
        renderer.receiveShadows = false;
        // Resources.Load garantiza que el shader del fondo sea incluido en el
        // APK. Shader.Find("Unlit/Texture") podia ser eliminado durante el
        // stripping de Android y dejar la pantalla negra aunque WebCamTexture
        // estuviera recibiendo frames correctamente.
        Shader shader = Resources.Load<Shader>("WebCamBackground");
        if (shader == null)
        {
            SetError("No se pudo cargar el shader del fondo de camara.");
            return;
        }
        backgroundMaterial = new Material(shader)
        {
            name = "WebCamBackgroundMaterial_Runtime",
            mainTexture = webcam,
            renderQueue = (int)RenderQueue.Background
        };
        renderer.sharedMaterial = backgroundMaterial;
        UpdateCameraBackground(true);
        cameraDiagnostic += " | fondo=activo";
    }

    void UpdateCameraBackground(bool force = false)
    {
        if (backgroundMesh == null || webcam == null) return;
        int angle = webcam.videoRotationAngle;
        bool mirror = webcam.videoVerticallyMirrored;
        if (!force && lastScreenWidth == Screen.width && lastScreenHeight == Screen.height &&
            lastVideoAngle == angle && lastVideoMirror == mirror &&
            lastVideoWidth == webcam.width && lastVideoHeight == webcam.height) return;

        lastScreenWidth = Screen.width;
        lastScreenHeight = Screen.height;
        lastVideoAngle = angle;
        lastVideoMirror = mirror;
        lastVideoWidth = webcam.width;
        lastVideoHeight = webcam.height;

        int normalizedAngle = (angle % 360 + 360) % 360;
        bool dimensionsSwap = normalizedAngle == 90 || normalizedAngle == 270;
        float orientedWidth = dimensionsSwap ? webcam.height : webcam.width;
        float orientedHeight = dimensionsSwap ? webcam.width : webcam.height;
        float cameraAspect = orientedWidth / Mathf.Max(orientedHeight, 1f);
        float screenAspect = Screen.width / Mathf.Max((float)Screen.height, 1f);

        // Aspect-fill: llena la pantalla vertical recortando solo el excedente,
        // sin deformar los pixeles de la camara. El detector usa este mismo crop.
        cameraCropMin = Vector2.zero;
        cameraCropSize = Vector2.one;
        if (cameraAspect > screenAspect)
        {
            cameraCropSize.x = screenAspect / cameraAspect;
            cameraCropMin.x = (1f - cameraCropSize.x) * 0.5f;
        }
        else if (cameraAspect < screenAspect)
        {
            cameraCropSize.y = cameraAspect / screenAspect;
            cameraCropMin.y = (1f - cameraCropSize.y) * 0.5f;
        }

        float z = 10f;
        float halfHeight = z * Mathf.Tan(displayCamera.fieldOfView * Mathf.Deg2Rad * 0.5f);
        float halfWidth = halfHeight * displayCamera.aspect;
        backgroundMesh.Clear();
        backgroundMesh.vertices = new[] {
            new Vector3(-halfWidth, -halfHeight, 0f),
            new Vector3(halfWidth, -halfHeight, 0f),
            new Vector3(halfWidth, halfHeight, 0f),
            new Vector3(-halfWidth, halfHeight, 0f)
        };
        backgroundMesh.uv = new[] {
            DisplayToRawUv(new Vector2(0f, 0f)),
            DisplayToRawUv(new Vector2(1f, 0f)),
            DisplayToRawUv(new Vector2(1f, 1f)),
            DisplayToRawUv(new Vector2(0f, 1f))
        };
        backgroundMesh.triangles = new[] { 0, 2, 1, 0, 3, 2 };
        backgroundMesh.RecalculateBounds();
    }

    void CreateBeamAnchorAndContent()
    {
        markerAnchor = new GameObject("DetectedBeamAnchor_ElementTag_" + elementTag);
        markerAnchor.transform.SetParent(displayCamera.transform, false);
        contentRoot = new GameObject("BeamRegisteredContent_ElementTag_" + elementTag);
        contentRoot.transform.SetParent(markerAnchor.transform, false);
        contentRoot.transform.localPosition = modelTranslationMetres;
        contentRoot.transform.localRotation = Quaternion.Euler(modelEulerDegrees);
        contentRoot.transform.localScale = Vector3.one;

        GameObject element = GameObject.CreatePrimitive(PrimitiveType.Cube);
        element.name = "OpenSees_Element_" + elementTag;
        element.transform.SetParent(contentRoot.transform, false);
        Vector3 direction = unityJ - unityI;
        element.transform.localPosition = (unityI + unityJ) * 0.5f;
        element.transform.localRotation = Quaternion.FromToRotation(Vector3.forward, direction.normalized);
        float thickness = visualThicknessMetres / Mathf.Max(modelScale, 0.0001f);
        element.transform.localScale = new Vector3(thickness, thickness, direction.magnitude);
        Destroy(element.GetComponent<Collider>());
        Shader shader = Shader.Find("Unlit/Color") ?? Shader.Find("Standard");
        Material material = new Material(shader);
        material.color = new Color(1f, 0.42f, 0.03f, 1f);
        element.GetComponent<Renderer>().material = material;

        CreateResultVisuals();

        GameObject labelObject = new GameObject("TraceabilityLabel_" + elementTag);
        labelObject.transform.SetParent(contentRoot.transform, false);
        labelObject.transform.localPosition = (unityI + unityJ) * 0.5f + Vector3.up * 0.35f;
        worldLabel = labelObject.AddComponent<TextMesh>();
        worldLabel.text = LabelText();
        worldLabel.anchor = TextAnchor.LowerCenter;
        worldLabel.alignment = TextAlignment.Center;
        worldLabel.fontSize = 54;
        worldLabel.characterSize = 0.006f / modelScale;
        worldLabel.color = Color.white;
        contentRoot.SetActive(false);
    }

    void CreateResultVisuals()
    {
        Semana06ForceCase combo = Array.Find(structuralData.forceCases,
            item => item.caseName == "COMBO_R");
        if (combo != null)
        {
            float normalizer = Mathf.Max(Mathf.Abs(combo.My1), Mathf.Abs(combo.My2), 0.001f);
            Vector3 up = Vector3.up;
            CreateResultLine("COMBO_R_My_Extremos", new[] {
                unityI + up * (combo.My1 / normalizer) * 0.75f,
                unityJ + up * (combo.My2 / normalizer) * 0.75f
            }, new Color(0.1f, 0.9f, 1f, 1f), 0.035f);
        }

        Semana06DisplacementCase deformation = Array.Find(structuralData.displacementCases,
            item => item.caseName == "COMBO_R");
        if (deformation != null && deformation.nodeI != null && deformation.nodeI.Length >= 3 &&
            deformation.nodeJ != null && deformation.nodeJ.Length >= 3)
        {
            const float amplification = 100f;
            Vector3 dI = OpenSeesToUnity(deformation.nodeI[0], deformation.nodeI[1],
                                         deformation.nodeI[2]) * amplification;
            Vector3 dJ = OpenSeesToUnity(deformation.nodeJ[0], deformation.nodeJ[1],
                                         deformation.nodeJ[2]) * amplification;
            var points = new Vector3[17];
            for (int i = 0; i < points.Length; i++)
            {
                float t = i / (points.Length - 1f);
                points[i] = Vector3.Lerp(unityI + dI, unityJ + dJ, t);
            }
            CreateResultLine("COMBO_R_DeformadaNodal_x100", points,
                new Color(1f, 0.15f, 0.85f, 1f), 0.045f);
        }
    }

    void CreateResultLine(string lineName, Vector3[] positions, Color color, float width)
    {
        GameObject lineObject = new GameObject(lineName);
        lineObject.transform.SetParent(contentRoot.transform, false);
        LineRenderer line = lineObject.AddComponent<LineRenderer>();
        line.useWorldSpace = false;
        line.positionCount = positions.Length;
        line.SetPositions(positions);
        line.startWidth = width;
        line.endWidth = width;
        line.numCapVertices = 4;
        Shader shader = Shader.Find("Unlit/Color") ?? Shader.Find("Sprites/Default");
        line.material = new Material(shader) { color = color };
        line.startColor = color;
        line.endColor = color;
    }

    void FaceLabelToCamera(bool visible)
    {
        if (!visible || worldLabel == null || displayCamera == null) return;
        Vector3 direction = worldLabel.transform.position - displayCamera.transform.position;
        if (direction.sqrMagnitude > 0.000001f)
            worldLabel.transform.rotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
    }

    IEnumerator ParseStructuralDataStaged(string json)
    {
        SetDataStep(2, "EN CURSO", "buscando tag " + elementTag);
        status = "Datos 3/6 | buscando elementTag " + elementTag + "...";
        yield return null;

        int elementsStart;
        int elementsEnd;
        int elementStart;
        int elementEnd;
        int nodeITag = 0;
        int nodeJTag = 0;
        string stageError = null;
        try
        {
            if (!TryFindArrayScope(json, "elements", out elementsStart, out elementsEnd) ||
                !TryFindObjectByIntegerProperty(json, elementsStart, elementsEnd,
                    "elementTag", elementTag, out elementStart, out elementEnd))
            {
                stageError = "no se encontro elementTag " + elementTag;
            }
            else if (!TryReadIntProperty(json, elementStart, elementEnd, "nodeI", out nodeITag) ||
                !TryReadIntProperty(json, elementStart, elementEnd, "nodeJ", out nodeJTag))
            {
                stageError = "elementTag sin nodeI/nodeJ validos";
            }
            else
            {
                if (!TryReadStringProperty(json, elementStart, elementEnd, "tipo", out elementType))
                    elementType = "elemento estructural";
                if (!TryReadStringProperty(json, elementStart, elementEnd, "origen", out elementOrigin))
                    elementOrigin = "modelo combinado";
            }
        }
        catch (Exception exception)
        {
            stageError = exception.GetType().Name + " - " + exception.Message;
        }
        if (stageError != null)
        {
            FailDataLoad(2, stageError);
            yield break;
        }
        SetDataStep(2, "OK", elementType + " | nodos " + nodeITag + "-" + nodeJTag);
        yield return null;

        SetDataStep(3, "EN CURSO", "buscando " + nodeITag + " y " + nodeJTag);
        status = "Datos 4/6 | buscando nodos de elementTag " + elementTag + "...";
        yield return null;

        Vector3 nodeI = Vector3.zero;
        Vector3 nodeJ = Vector3.zero;
        stageError = null;
        try
        {
            if (!TryFindArrayScope(json, "nodes", out int nodesStart, out int nodesEnd) ||
                !TryFindObjectByIntegerProperty(json, nodesStart, nodesEnd,
                    "nodeTag", nodeITag, out int nodeIStart, out int nodeIEnd) ||
                !TryFindObjectByIntegerProperty(json, nodesStart, nodesEnd,
                    "nodeTag", nodeJTag, out int nodeJStart, out int nodeJEnd) ||
                !TryReadNodeCoordinates(json, nodeIStart, nodeIEnd, out nodeI) ||
                !TryReadNodeCoordinates(json, nodeJStart, nodeJEnd, out nodeJ))
            {
                stageError = "no se encontraron ambos nodos con x/y/z";
            }
        }
        catch (Exception exception)
        {
            stageError = exception.GetType().Name + " - " + exception.Message;
        }
        if (stageError != null)
        {
            FailDataLoad(3, stageError);
            yield break;
        }
        SetDataStep(3, "OK", nodeITag + " y " + nodeJTag);

        Vector3 uI = OpenSeesToUnity(nodeI.x, nodeI.y, nodeI.z);
        Vector3 uJ = OpenSeesToUnity(nodeJ.x, nodeJ.y, nodeJ.z);
        unityI = Vector3.zero;
        unityJ = uJ - uI;
        yield return null;

        SetDataStep(4, "EN CURSO", loadCase + "/" + resultComponent);
        status = "Datos 5/6 | buscando " + loadCase + "/" + resultComponent + "...";
        yield return null;
        stageError = null;
        try
        {
            if (!TryReadForce(json, loadCase, elementTag, resultComponent, out resultValue))
            {
                stageError = "no existe results.forces/" + loadCase + "/" +
                             elementTag + "/" + resultComponent;
            }
        }
        catch (Exception exception)
        {
            stageError = exception.GetType().Name + " - " + exception.Message;
        }
        if (stageError != null)
        {
            FailDataLoad(4, stageError);
            yield break;
        }
        SetDataStep(4, "OK", resultValue.ToString("F3", CultureInfo.InvariantCulture) +
                    " " + resultUnits);
        yield return null;

        SetDataStep(5, "EN CURSO", "validando datos");
        status = "Datos 6/6 | finalizando carga...";
        yield return null;
        dataReady = true;
        SetDataStep(5, "OK", "carga estructural finalizada");
        status = "Datos estructurales OK | preparando tracking...";
        Debug.Log($"[Semana6 Marker] tag {elementTag}: " +
                  $"I=({nodeI.x},{nodeI.y},{nodeI.z}), " +
                  $"J=({nodeJ.x},{nodeJ.y},{nodeJ.z}) m; " +
                  $"{displayResultName}={resultValue} {resultUnits}.");
    }

    void InitializeDataLoadSteps()
    {
        dataDiagnosticsVisible = true;
        for (int i = 0; i < dataLoadSteps.Length; i++)
            dataLoadSteps[i] = (i + 1) + ". " + DataStepName(i) + ": PENDIENTE";
    }

    void SetDataStep(int index, string state, string detail)
    {
        dataDiagnosticsVisible = true;
        dataLoadSteps[index] = (index + 1) + ". " + DataStepName(index) + ": " +
                               state + (string.IsNullOrEmpty(detail) ? "" : " | " + detail);
    }

    void FailDataLoad(int index, string detail)
    {
        dataReady = false;
        SetDataStep(index, "ERROR", detail);
        for (int i = index + 1; i < dataLoadSteps.Length; i++)
            SetDataStep(i, "ERROR", "no ejecutado por fallo anterior");
        SetError("ERROR datos " + (index + 1) + "/6: " + detail);
    }

    static string DataStepName(int index)
    {
        switch (index)
        {
            case 0: return "Abrir archivo";
            case 1: return "Leer archivo";
            case 2: return "Encontrar elementTag 800205";
            case 3: return "Encontrar nodos";
            case 4: return "Encontrar COMBO_R/My1";
            case 5: return "Finalizar carga";
            default: return "Paso";
        }
    }

    public static Vector3 OpenSeesToUnity(float x, float y, float z) =>
        new Vector3(x, z, -y);

    static bool TryReadForce(string json, string caseName, int tag,
                             string component, out float value)
    {
        value = 0f;
        if (!TryFindNamedObject(json, 0, json.Length, "results",
                out int resultsStart, out int resultsEnd) ||
            !TryFindNamedObject(json, resultsStart, resultsEnd, "forces",
                out int forcesStart, out int forcesEnd) ||
            !TryFindNamedObject(json, forcesStart, forcesEnd, caseName,
                out int caseStart, out int caseEnd) ||
            !TryFindNamedObject(json, caseStart, caseEnd, tag.ToString(CultureInfo.InvariantCulture),
                out int tagStart, out int tagEnd))
            return false;

        return TryReadFloatProperty(json, tagStart, tagEnd, component, out value);
    }

    static bool TryReadNodeCoordinates(string json, int start, int end, out Vector3 node)
    {
        node = Vector3.zero;
        if (!TryReadFloatProperty(json, start, end, "x", out float x) ||
            !TryReadFloatProperty(json, start, end, "y", out float y) ||
            !TryReadFloatProperty(json, start, end, "z", out float z))
            return false;
        node = new Vector3(x, y, z);
        return true;
    }

    static bool TryFindArrayScope(string json, string name, out int start, out int end)
    {
        start = end = -1;
        if (!TryFindPropertyValueStart(json, 0, json.Length, name, out int valueStart) ||
            valueStart >= json.Length || json[valueStart] != '[')
            return false;
        int close = FindJsonContainerEnd(json, valueStart, '[', ']', json.Length);
        if (close < 0) return false;
        start = valueStart + 1;
        end = close;
        return true;
    }

    static bool TryFindNamedObject(string json, int scopeStart, int scopeEnd,
                                   string name, out int start, out int end)
    {
        start = end = -1;
        if (!TryFindPropertyValueStart(json, scopeStart, scopeEnd, name, out int valueStart) ||
            valueStart >= scopeEnd || json[valueStart] != '{')
            return false;
        int close = FindJsonContainerEnd(json, valueStart, '{', '}', scopeEnd);
        if (close < 0) return false;
        start = valueStart + 1;
        end = close;
        return true;
    }

    static bool TryFindObjectByIntegerProperty(string json, int scopeStart, int scopeEnd,
                                                string property, int expected,
                                                out int objectStart, out int objectEnd)
    {
        objectStart = objectEnd = -1;
        string needle = "\"" + property + "\"";
        int search = scopeStart;
        while (search < scopeEnd)
        {
            int propertyAt = json.IndexOf(needle, search, StringComparison.Ordinal);
            if (propertyAt < 0 || propertyAt >= scopeEnd) return false;
            if (TryFindPropertyValueStart(json, propertyAt, scopeEnd, property,
                    out int valueStart) && TryParseJsonInt(json, valueStart, scopeEnd,
                    out int found, out _) && found == expected)
            {
                int open = json.LastIndexOf('{', propertyAt);
                if (open < scopeStart) return false;
                int close = FindJsonContainerEnd(json, open, '{', '}', scopeEnd);
                if (close < 0) return false;
                objectStart = open + 1;
                objectEnd = close;
                return true;
            }
            search = propertyAt + needle.Length;
        }
        return false;
    }

    static bool TryReadIntProperty(string json, int scopeStart, int scopeEnd,
                                   string name, out int value)
    {
        value = 0;
        return TryFindPropertyValueStart(json, scopeStart, scopeEnd, name, out int start) &&
               TryParseJsonInt(json, start, scopeEnd, out value, out _);
    }

    static bool TryReadFloatProperty(string json, int scopeStart, int scopeEnd,
                                     string name, out float value)
    {
        value = 0f;
        if (!TryFindPropertyValueStart(json, scopeStart, scopeEnd, name, out int start))
            return false;
        int finish = start;
        while (finish < scopeEnd &&
               (char.IsDigit(json[finish]) || json[finish] == '-' || json[finish] == '+' ||
                json[finish] == '.' || json[finish] == 'e' || json[finish] == 'E'))
            finish++;
        return finish > start && float.TryParse(json.Substring(start, finish - start),
            NumberStyles.Float, CultureInfo.InvariantCulture, out value);
    }

    static bool TryReadStringProperty(string json, int scopeStart, int scopeEnd,
                                      string name, out string value)
    {
        value = "";
        if (!TryFindPropertyValueStart(json, scopeStart, scopeEnd, name, out int start) ||
            start >= scopeEnd || json[start] != '"')
            return false;
        int finish = start + 1;
        bool escaped = false;
        while (finish < scopeEnd)
        {
            char c = json[finish];
            if (c == '"' && !escaped)
            {
                value = json.Substring(start + 1, finish - start - 1)
                    .Replace("\\\"", "\"").Replace("\\\\", "\\");
                return true;
            }
            escaped = c == '\\' && !escaped;
            if (c != '\\') escaped = false;
            finish++;
        }
        return false;
    }

    static bool TryFindPropertyValueStart(string json, int scopeStart, int scopeEnd,
                                          string name, out int valueStart)
    {
        valueStart = -1;
        string needle = "\"" + name + "\"";
        int propertyAt = json.IndexOf(needle, scopeStart, StringComparison.Ordinal);
        if (propertyAt < 0 || propertyAt >= scopeEnd) return false;
        int cursor = propertyAt + needle.Length;
        while (cursor < scopeEnd && char.IsWhiteSpace(json[cursor])) cursor++;
        if (cursor >= scopeEnd || json[cursor] != ':') return false;
        cursor++;
        while (cursor < scopeEnd && char.IsWhiteSpace(json[cursor])) cursor++;
        if (cursor >= scopeEnd) return false;
        valueStart = cursor;
        return true;
    }

    static bool TryParseJsonInt(string json, int start, int end,
                                out int value, out int finish)
    {
        value = 0;
        finish = start;
        if (finish < end && (json[finish] == '-' || json[finish] == '+')) finish++;
        int digitsStart = finish;
        while (finish < end && char.IsDigit(json[finish])) finish++;
        return finish > digitsStart && int.TryParse(json.Substring(start, finish - start),
            NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
    }

    static int FindJsonContainerEnd(string json, int openAt, char open, char close, int limit)
    {
        int depth = 0;
        bool inString = false;
        bool escaped = false;
        for (int i = openAt; i < limit; i++)
        {
            char c = json[i];
            if (inString)
            {
                if (c == '"' && !escaped) inString = false;
                escaped = c == '\\' && !escaped;
                if (c != '\\') escaped = false;
                continue;
            }
            if (c == '"')
            {
                inString = true;
                escaped = false;
            }
            else if (c == open) depth++;
            else if (c == close && --depth == 0) return i;
        }
        return -1;
    }

    string LabelText()
    {
        Semana06ForceCase combo = structuralData == null ? null :
            Array.Find(structuralData.forceCases, item => item.caseName == "COMBO_R");
        string moments = combo == null ? "" :
            $"\nCOMBO_R My: I={combo.My1:F2}, J={combo.My2:F2} kN.m";
        return $"OpenSees elementTag {elementTag}\n{elementType} | {elementOrigin}" + moments +
               "\nCian: My extremos | Magenta: deformada nodal x100";
    }

    void DrawCleanResultsPanel()
    {
        Semana06ForceCase combo = Array.Find(structuralData.forceCases,
            item => item.caseName == "COMBO_R");
        Semana06DisplacementCase displacement = Array.Find(structuralData.displacementCases,
            item => item.caseName == "COMBO_R");
        Semana06Load deadLoad = Array.Find(structuralData.loads,
            item => item.caseName == "G");
        Semana06Load liveLoad = Array.Find(structuralData.loads,
            item => item.caseName == "Q");
        if (combo == null || displacement == null || displacement.nodeI == null ||
            displacement.nodeI.Length < 3 || deadLoad == null || liveLoad == null)
            return;

        var subtitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = Mathf.Clamp(Screen.width / 38, 22, 38),
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleLeft
        };
        var valueStyle = new GUIStyle(subtitleStyle)
        {
            alignment = TextAnchor.MiddleRight
        };
        var unitStyle = new GUIStyle(subtitleStyle)
        {
            fontStyle = FontStyle.Normal,
            alignment = TextAnchor.MiddleLeft
        };

        float axial = Mathf.Abs(combo.N1) < 0.0005f ? 0f : combo.N1;
        DrawResultRow("Fuerza axial", axial.ToString("F3", CultureInfo.InvariantCulture),
                      "kN", subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Fuerza de corte", combo.Vz1.ToString("F3", CultureInfo.InvariantCulture),
                      "kN", subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Momento flector", combo.My1.ToString("F3", CultureInfo.InvariantCulture),
                      "kN·m", subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Ux", FormatSigned(displacement.nodeI[0] * 1000f), "mm",
                      subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Uy", FormatSigned(displacement.nodeI[1] * 1000f), "mm",
                      subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Uz", FormatSigned(displacement.nodeI[2] * 1000f), "mm",
                      subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Área tributaria",
                      liveLoad.tributaryArea_m2.ToString("F3", CultureInfo.InvariantCulture),
                      "m²", subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("G", deadLoad.w_kN_m.ToString("F3", CultureInfo.InvariantCulture),
                      "kN/m", subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Q", liveLoad.w_kN_m.ToString("F3", CultureInfo.InvariantCulture),
                      "kN/m", subtitleStyle, valueStyle, unitStyle);
        DrawResultRow("Demanda / Capacidad", "PENDIENTE", "",
                      subtitleStyle, valueStyle, unitStyle);
    }

    static string FormatSigned(float value)
    {
        if (Mathf.Abs(value) < 0.0005f) value = 0f;
        return value > 0f
            ? "+" + value.ToString("F3", CultureInfo.InvariantCulture)
            : value.ToString("F3", CultureInfo.InvariantCulture);
    }

    static void DrawResultRow(string subtitle, string value, string unit,
                              GUIStyle subtitleStyle, GUIStyle valueStyle,
                              GUIStyle unitStyle)
    {
        GUILayout.BeginHorizontal(GUILayout.Height(Mathf.Clamp(Screen.height / 24f, 42f, 64f)));
        GUILayout.Label(subtitle, subtitleStyle, GUILayout.Width(Screen.width * 0.48f));
        GUILayout.Label(value, valueStyle, GUILayout.Width(Screen.width * 0.25f));
        GUILayout.Label(unit, unitStyle, GUILayout.ExpandWidth(true));
        GUILayout.EndHorizontal();
    }

    void SetError(string error)
    {
        status = error;
        Debug.LogError("[Semana6 Marker] " + error);
    }

    void DrawDetectionOverlay()
    {
        if (lastDetectedCorners == null || lastDetectedCorners.Length != 4 ||
            !HasConfirmedBeam())
            return;

        Color outline = new Color(0.15f, 1f, 0.25f, 1f);
        for (int i = 0; i < 4; i++)
            DrawViewportLine(lastDetectedCorners[i], lastDetectedCorners[(i + 1) % 4],
                             outline, Mathf.Max(4f, Screen.width / 180f));

        float minX = 1f;
        float maxY = 0f;
        foreach (Vector2 corner in lastDetectedCorners)
        {
            minX = Mathf.Min(minX, corner.x);
            maxY = Mathf.Max(maxY, corner.y);
        }
        var labelStyle = new GUIStyle(GUI.skin.box)
        {
            alignment = TextAnchor.MiddleCenter,
            fontSize = Mathf.Clamp(Screen.width / 32, 20, 38)
        };
        labelStyle.normal.textColor = outline;
        float labelWidth = Mathf.Min(320f, Screen.width * 0.62f);
        float x = Mathf.Clamp(minX * Screen.width, 4f, Screen.width - labelWidth - 4f);
        float y = Mathf.Clamp((1f - maxY) * Screen.height - 52f, 4f, Screen.height - 48f);
        GUI.Box(new Rect(x, y, labelWidth, 46f), "VIGA DETECTADA", labelStyle);
    }

    static void DrawViewportLine(Vector2 startUv, Vector2 endUv, Color color,
                                 float thickness)
    {
        Vector2 start = new Vector2(startUv.x * Screen.width,
                                    (1f - startUv.y) * Screen.height);
        Vector2 end = new Vector2(endUv.x * Screen.width,
                                  (1f - endUv.y) * Screen.height);
        Vector2 delta = end - start;
        float length = delta.magnitude;
        if (length < 1f) return;

        Matrix4x4 previousMatrix = GUI.matrix;
        Color previousColor = GUI.color;
        GUI.color = color;
        GUIUtility.RotateAroundPivot(Mathf.Atan2(delta.y, delta.x) * Mathf.Rad2Deg, start);
        GUI.DrawTexture(new Rect(start.x, start.y - thickness * 0.5f, length, thickness),
                        Texture2D.whiteTexture);
        GUI.matrix = previousMatrix;
        GUI.color = previousColor;
    }

    void OnGUI()
    {
        bool showConfirmedContent = HasConfirmedBeam();
        GUI.skin.label.fontSize = Mathf.Clamp(Screen.width / 60, 16, 28);
        GUI.skin.box.fontSize = Mathf.Clamp(Screen.width / 65, 15, 26);
        GUILayout.BeginArea(new Rect(18, 18, Screen.width - 36,
            Mathf.Min(900, Screen.height * 0.88f)), GUI.skin.box);
        GUILayout.Label("SEMANA 6 | VIGA HORIZONTAL SIN ARCORE");
        GUILayout.Label(status);
        GUILayout.Label("DIAGNOSTICO: " + cameraDiagnostic);
        GUILayout.Label($"frames procesados: {processedFrameCount} | " +
                        $"candidatos encontrados: {lastCandidateCount} | " +
                        $"viga detectada: {(showConfirmedContent ? "sí" : "no")}");
        if (showConfirmedContent)
        {
            resultsScroll = GUILayout.BeginScrollView(resultsScroll);
            DrawCleanResultsPanel();
            GUILayout.EndScrollView();
        }
        GUILayout.EndArea();
        DrawDetectionOverlay();
    }

    void OnDestroy()
    {
        if (webcam != null && webcam.isPlaying) webcam.Stop();
        if (backgroundMaterial != null) Destroy(backgroundMaterial);
        if (backgroundMesh != null) Destroy(backgroundMesh);
    }
}
