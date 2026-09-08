using System.Collections.Generic;
using UnityEngine;

public class TributaryAreaInspector : MonoBehaviour
{
    private SelectionController selection;
    private Dictionary<int, TributaryAreaData> tributaryLookup;
    private bool lookupBuilt;

    void Start()
    {
        selection = FindObjectOfType<SelectionController>();
    }

    void BuildLookup()
    {
        tributaryLookup = new Dictionary<int, TributaryAreaData>();
        ModelLoader loader = FindObjectOfType<ModelLoader>();
        if (loader == null || loader.modelData == null || loader.modelData.tributary_areas == null)
        {
            lookupBuilt = true;
            return;
        }

        foreach (var ta in loader.modelData.tributary_areas)
            tributaryLookup[ta.elementTag] = ta;

        lookupBuilt = true;
    }

    void OnGUI()
    {
        if (selection == null) return;
        if (selection.SelectedTag < 0 || selection.SelectedType != "Viga") return;

        if (!lookupBuilt) BuildLookup();
        if (tributaryLookup == null) return;

        if (!tributaryLookup.ContainsKey(selection.SelectedTag)) return;

        TributaryAreaData ta = tributaryLookup[selection.SelectedTag];

        float pw = 310f;
        float ph = 250f;
        float x = Screen.width - pw - 10f;
        float y = 100f;

        GUI.Box(new Rect(x, y, pw, ph), "Inspector Area Tributaria");

        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 35));

        GUILayout.Label($"Elemento:    {ta.elementTag}");
        GUILayout.Label($"Nivel:       {ta.nivel}");
        GUILayout.Label($"Longitud:    {ta.longitud_m:F3} m");
        GUILayout.Space(5);
        GUILayout.Label($"A_tributaria: {ta.A_tributaria_m2:F4} m2");
        if (ta.q_G_kPa != null && ta.q_G_kPa.Length > 0)
            GUILayout.Label($"q_G:         {string.Join(" / ", System.Array.ConvertAll(ta.q_G_kPa, x => x.ToString("F3")))} kPa");
        else
            GUILayout.Label($"q_G:         N/D");
        GUILayout.Label($"P_losa:      {ta.P_losa_kN:F2} kN");
        GUILayout.Label($"w (lineal):  {ta.w_kN_m:F2} kN/m");
        GUILayout.Space(5);
        GUILayout.Label($"Orientacion: {ta.orientacion}");

        if (ta.origen != null && ta.origen.Length > 0)
        {
            GUILayout.Label($"Origen: {string.Join(", ", ta.origen)}");
        }

        GUILayout.EndArea();
    }
}
