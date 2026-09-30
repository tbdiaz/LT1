using UnityEditor;
using UnityEditor.Build;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.XR.Management;

/// <summary>Configuracion iOS/ARKit repetible. No altera el modelo estructural.</summary>
public static class IOSARBuild
{
    [MenuItem("LT1/Semana 6/Configurar proyecto para iPhone")]
    public static void Configure()
    {
        PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.iOS, "cl.p0mcoc.lt1.ar");
        PlayerSettings.iOS.cameraUsageDescription =
            "La camara se usa para detectar la imagen de referencia y registrar el modelo estructural en realidad aumentada.";
        PlayerSettings.iOS.targetOSVersionString = "13.0";
        PlayerSettings.iOS.targetDevice = iOSTargetDevice.iPhoneAndiPad;
        PlayerSettings.SetArchitecture(NamedBuildTarget.iOS, 1); // ARM64
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;

        var targetSettings = XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.iOS);
        bool arkitAssigned = targetSettings != null && targetSettings.AssignedSettings != null &&
            XRPackageMetadataStore.AssignLoader(
                targetSettings.AssignedSettings,
                "UnityEngine.XR.ARKit.ARKitLoader",
                BuildTargetGroup.iOS);
        AssetDatabase.SaveAssets();
        Debug.Log(arkitAssigned
            ? "[Semana6 AR] iOS ARM64 y ARKit Loader configurados."
            : "[Semana6 AR] iOS configurado; verifique ARKit en XR Plug-in Management > iOS.");
    }
}
