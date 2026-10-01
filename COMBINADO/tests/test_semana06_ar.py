import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNITY = ROOT / "unity" / "LT1Viewer"
FULL_JSON = UNITY / "Assets" / "StreamingAssets" / "modelo_combinado.json"
LIGHT_JSON = UNITY / "Assets" / "StreamingAssets" / "semana06_element_800205.json"


def test_light_package_is_small_and_traceable_to_the_real_model():
    full = json.loads(FULL_JSON.read_text(encoding="utf-8"))
    light = json.loads(LIGHT_JSON.read_text(encoding="utf-8"))
    original = next(item for item in full["elements"] if item["elementTag"] == 800205)

    assert LIGHT_JSON.stat().st_size < 50_000
    assert light["sourceFile"] == "modelo_combinado.json"
    assert light["elementTag"] == 800205
    assert light["element"]["nodeI"] == original["nodeI"]
    assert light["element"]["nodeJ"] == original["nodeJ"]
    assert light["element"]["length_m"] == original["longitud_m"]
    assert light["element"]["section"]["label"] == original["seccion"]["label"]

    expected_forces = full["results"]["forces"]
    for case in light["forceCases"]:
        actual = {key: value for key, value in case.items() if key != "caseName"}
        assert actual == expected_forces[case["caseName"]]["800205"]

    expected_displacements = full["results"]["displacements"]
    for case in light["displacementCases"]:
        assert case["nodeI"] == expected_displacements[case["caseName"]][str(original["nodeI"])]
        assert case["nodeJ"] == expected_displacements[case["caseName"]][str(original["nodeJ"])]

    assert light["diagramAvailability"]["endForcesAvailable"] is True
    assert light["diagramAvailability"]["internalStationResultsAvailable"] is False
    assert light["demandCapacity"]["available"] is False


def test_ar_coordinate_chain_and_traceability_are_explicit():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")
    scene = (UNITY / "Assets" / "Scenes" / "MarkerStructuralDemo.unity").read_text(encoding="utf-8")

    assert "new Vector3(x, z, -y)" in source
    assert "contentRoot.transform.SetParent(markerAnchor.transform, false);" in source
    assert "contentRoot.transform.localPosition = modelTranslationMetres;" in source
    assert "Quaternion.Euler(modelEulerDegrees)" in source
    assert "detectedWorldWidth / Mathf.Max(structuralData.element.length_m" in source
    assert "Quaternion.FromToRotation(Vector3.right, widthDirection.normalized)" in source
    assert "elementTag" in source and "loadCase" in source and "resultUnits" in source
    assert "public int elementTag = 800205;" in source
    assert 'public string resultComponent = "My1";' in source
    assert "elementTag: 800205" in scene
    assert "jsonFileName: semana06_element_800205.json" in scene


def test_a05_build_does_not_require_arcore():
    manifest = json.loads((UNITY / "Packages" / "manifest.json").read_text(encoding="utf-8"))
    deps = manifest["dependencies"]

    assert "com.unity.xr.arcore" not in deps
    assert (UNITY / "Assets" / "Editor" / "MarkerStructuralDemoBuilder.cs").is_file()
    android_builder = (UNITY / "Assets" / "Editor" / "AndroidBuild.cs").read_text(encoding="utf-8")
    assert "ARCoreLoader" not in android_builder
    assert 'const string ScenePath = "Assets/Scenes/MarkerStructuralDemo.unity";' in android_builder
    assert "LT1-Semana06-A05.apk" in android_builder
    assert "Semana06StreamingAssetsFilter" in android_builder
    assert '"modelo_combinado.json"' in android_builder


def test_runtime_detects_a_horizontal_beam_without_svg_marker():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")

    assert "WebCamTexture" in source
    assert "TryFindHorizontalBeamCandidate" in source
    assert "minimumBeamAspect" in source
    assert "maximumScreenTiltDegrees" in source
    assert 'new GameObject("DetectedBeamAnchor_ElementTag_" + elementTag)' in source
    assert "ViewportToWorldPoint" in source
    assert "FindLargestBlob" not in source
    assert "SolveHomography" not in source
    assert "FiducialColor" not in source


def test_android_camera_initialization_keeps_working_rear_camera_path():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")

    assert "UnityEngine.Android.Permission.HasUserAuthorizedPermission" in source
    assert "UnityEngine.Android.Permission.RequestUserPermission" in source
    assert "while (devices.Length == 0" in source
    assert "!device.isFrontFacing" in source
    assert "webcam.didUpdateThisFrame" in source
    assert "new WebCamTexture(device.name)" in source
    assert "device.availableResolutions" in source
    assert "CameraPriority" in source
    assert '"Play()=llamado | isPlaying=' in source
    assert '"didUpdateThisFrame=' in source


def test_camera_frames_use_the_existing_fullscreen_background_shader():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")
    shader = (UNITY / "Assets" / "Resources" / "WebCamBackground.shader").read_text(encoding="utf-8")

    assert 'Resources.Load<Shader>("WebCamBackground")' in source
    assert "mainTexture = webcam" in source
    assert "RenderQueue.Background" in source
    assert "Cull Off" in shader
    assert "ZWrite Off" in shader
    assert "ZTest Always" in shader
    assert "tex2D(_MainTex, input.uv)" in shader


def test_camera_aspect_crop_and_detector_overlay_share_coordinates():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")
    scene = (UNITY / "Assets" / "Scenes" / "MarkerStructuralDemo.unity").read_text(encoding="utf-8")

    assert "cameraCropMin" in source and "cameraCropSize" in source
    assert "cameraAspect > screenAspect" in source
    assert "DisplayToRawUv(new Vector2(0f, 0f))" in source
    assert "RawToDisplayUv(rawCenter)" in source
    assert "processedFrameCount++" in source
    assert "candidatesFound++" in source
    assert '"VIGA DETECTADA"' in source
    assert "DrawDetectionOverlay" in source
    assert "frames procesados:" in source
    assert "candidatos encontrados:" in source
    assert "viga detectada:" in source
    assert "processEveryNFrames: 1" in scene


def test_detector_reads_the_active_rendered_webcam_continuously():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")

    assert "backgroundMaterial" in source and "mainTexture = webcam" in source
    assert "pixels = webcam.GetPixels32(pixels);" in source
    assert "if (webcam == null || !webcam.isPlaying) return;" in source
    assert "bool detectorCanRead = cameraHasValidFrame && dataReady" in source
    assert "if (detectorCanRead && Time.frameCount % processEveryNFrames == 0)" in source
    assert "if (updated && Time.frameCount % processEveryNFrames == 0)" not in source


def test_results_wait_for_a_stable_beam_and_anchor_survives_short_loss():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")
    scene = (UNITY / "Assets" / "Scenes" / "MarkerStructuralDemo.unity").read_text(encoding="utf-8")

    assert 'status = "Buscando viga...";' in source
    assert "stableCandidateFrames < stableFramesRequired" in source
    assert "IsCompatibleCandidate" in source
    assert "SmoothTrackedCandidate" in source
    assert "SmoothDetectedCorners" in source
    assert "bool showConfirmedContent = HasConfirmedBeam();" in source
    assert "if (showConfirmedContent)" in source
    assert "contentRoot.SetActive(showConfirmedContent)" in source
    assert 'status = "VIGA DETECTADA";' in source
    assert "stableFramesRequired: 6" in scene
    assert "lostTimeoutSeconds: 1" in scene


def test_detector_requires_a_structural_concrete_beam_band():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")
    scene = (UNITY / "Assets" / "Scenes" / "MarkerStructuralDemo.unity").read_text(encoding="utf-8")

    assert "ValidateStructuralBeamBand" in source
    assert "TryFindLongitudinalEdge" in source
    assert "topSupport < minimumLongitudinalEdgeSupport" in source
    assert "bottomSupport < minimumLongitudinalEdgeSupport" in source
    assert "coefficientOfVariation > maximumThicknessVariation" in source
    assert "interiorSupport < 0.50f" in source
    assert "displayLong < minimumBeamScreenLength" in source
    assert "displayShort < minimumBeamScreenThickness" in source
    assert "screenArea < minimumBeamScreenArea" in source
    assert "refinedCenter" in source and "refinedThickness" in source
    assert "stableFramesRequired: 6" in scene
    assert "minimumBeamScreenLength: 0.28" in scene
    assert "minimumBeamScreenThickness: 0.045" in scene


def test_android_loads_only_the_light_package_and_exposes_real_availability():
    source = (UNITY / "Assets" / "Scripts" / "MarkerStructuralDemo.cs").read_text(encoding="utf-8")
    scene = (UNITY / "Assets" / "Scenes" / "MarkerStructuralDemo.unity").read_text(encoding="utf-8")

    assert 'public string jsonFileName = "semana06_element_800205.json";' in source
    assert "JsonUtility.FromJson<Semana06BeamData>(json)" in source
    assert "CreateResultVisuals();" in source
    assert 'DrawResultRow("Fuerza axial"' in source
    assert 'DrawResultRow("Fuerza de corte"' in source
    assert 'DrawResultRow("Momento flector"' in source
    assert 'DrawResultRow("Ux"' in source
    assert 'DrawResultRow("Uy"' in source
    assert 'DrawResultRow("Uz"' in source
    assert 'DrawResultRow("Área tributaria"' in source
    assert 'DrawResultRow("G"' in source
    assert 'DrawResultRow("Q"' in source
    assert 'DrawResultRow("Demanda / Capacidad", "PENDIENTE"' in source
    assert "modelo_combinado.json" not in scene
