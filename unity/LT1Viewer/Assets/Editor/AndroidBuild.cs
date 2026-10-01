using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

// Configuracion y APK reproducibles de Semana 6 para Galaxy A05, sin ARCore.
public static class AndroidBuild
{
    const string ScenePath = "Assets/Scenes/MarkerStructuralDemo.unity";
    const string ApkPath = "Builds/Android/LT1-Semana06-A05.apk";
    internal static bool IsSemana06BuildActive { get; private set; }

    [MenuItem("LT1/Semana 6 A05/Configurar Android sin ARCore")]
    public static void ConfigureForGalaxyA05()
    {
        PlayerSettings.SetApplicationIdentifier(
            NamedBuildTarget.Android, "cl.p0mcoc.lt1.semana06a05");
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.Portrait;
        EditorUserBuildSettings.buildAppBundle = false;
        AssetDatabase.SaveAssets();
        Debug.Log("[Semana6 A05] Android ARM64 configurado sin XR/ARCore.");
    }

    [MenuItem("LT1/Semana 6 A05/Compilar APK")]
    public static void BuildApk()
    {
        if (!BuildPipeline.IsBuildTargetSupported(
                BuildTargetGroup.Android, BuildTarget.Android))
            throw new InvalidOperationException(
                "Falta Android Build Support para esta version de Unity.");
        if (!File.Exists(ScenePath))
            throw new FileNotFoundException(
                "Primero ejecute LT1 > Semana 6 A05 > Crear escena sin ARCore.", ScenePath);

        ConfigureForGalaxyA05();
        Directory.CreateDirectory(Path.GetDirectoryName(ApkPath));

        BuildPlayerOptions options = new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = ApkPath,
            target = BuildTarget.Android,
            options = BuildOptions.None
        };
        BuildReport report;
        IsSemana06BuildActive = true;
        try
        {
            report = BuildPipeline.BuildPlayer(options);
        }
        finally
        {
            IsSemana06BuildActive = false;
        }
        if (report.summary.result != BuildResult.Succeeded)
            throw new Exception("Build Android fallo: " + report.summary.result);
        Debug.Log($"[Semana6 A05] APK creado: {ApkPath} ({report.summary.totalSize} bytes)");
    }

    public static void BuildFromCommandLine() => BuildApk();
}

// El proyecto principal conserva sus JSON completos. Solo la compilacion de esta
// demo elimina sus copias del proyecto Gradle y empaqueta el extracto de 7 KB.
public sealed class Semana06StreamingAssetsFilter :
    UnityEditor.Android.IPostGenerateGradleAndroidProject
{
    static readonly string[] ExcludedAssets =
    {
        "modelo_combinado.json",
        "modelo_lt1.json",
        "pm_column_113022.png",
        "pm_wall_M001.png"
    };

    public int callbackOrder => 1000;

    public void OnPostGenerateGradleAndroidProject(string path)
    {
        if (!AndroidBuild.IsSemana06BuildActive) return;
        string assetsPath = Path.Combine(path, "src", "main", "assets");
        foreach (string fileName in ExcludedAssets)
        {
            string generatedCopy = Path.Combine(assetsPath, fileName);
            if (File.Exists(generatedCopy)) File.Delete(generatedCopy);
        }
        Debug.Log("[Semana6 A05] Gradle contiene solo el paquete liviano de 800205.");
    }
}
