using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

// Build reproducible de Semana 5. Requiere Android Build Support instalado
// para la misma version de Unity indicada por ProjectVersion.txt.
public static class AndroidBuild
{
    const string ScenePath = "Assets/Scenes/LT1Viewer.unity";
    const string ApkPath = "Builds/Android/LT1Viewer-semana05.apk";

    [MenuItem("LT1/Build Android APK")]
    public static void BuildApk()
    {
        if (!BuildPipeline.IsBuildTargetSupported(
                BuildTargetGroup.Android, BuildTarget.Android))
            throw new InvalidOperationException(
                "Falta Android Build Support para esta version de Unity.");

        Directory.CreateDirectory(Path.GetDirectoryName(ApkPath));
        PlayerSettings.SetApplicationIdentifier(
            NamedBuildTarget.Android, "cl.p0mcoc.lt1viewer");
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
        EditorUserBuildSettings.buildAppBundle = false;

        BuildPlayerOptions options = new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = ApkPath,
            target = BuildTarget.Android,
            options = BuildOptions.None
        };
        BuildReport report = BuildPipeline.BuildPlayer(options);
        if (report.summary.result != BuildResult.Succeeded)
            throw new Exception("Build Android fallo: " + report.summary.result);
        Debug.Log($"APK creado: {ApkPath} ({report.summary.totalSize} bytes)");
    }

    public static void BuildFromCommandLine() => BuildApk();
}
