using System;
using UnityEngine;

// P1L4: al seleccionar viga/columna/muro muestra los resultados locales
// N, Vy, Vz, T, My, Mz (extremos i y j), el caso activo y el vínculo con
// elementTag. Ademas, si el elemento tiene registro en 'capacidades' del JSON,
// muestra la demanda P-M del modelo (caso G_gravedad) y el estado de la
// capacidad. Hoy ambas piezas (columna 111000 y muro 400001) estan
// NO_DISPONIBLE: no hay curva P-M exportada porque los datos resistentes
// (f'c, fy, recubrimiento; armadura de muros) NO estan documentados en el
// proyecto. No se dibuja curva inventada: se listan los datos faltantes.
public class StructuralResultsController : MonoBehaviour
{
    private SelectionController selection;
    private ModelLoader loader;

    void Start()
    {
        selection = FindObjectOfType<SelectionController>();
        loader = FindObjectOfType<ModelLoader>();
    }

    ElementInternalForceData GetForces(int tag)
    {
        if (loader == null || loader.modelData == null ||
            loader.modelData.analysis == null)
            return null;
        var list = loader.modelData.analysis.fuerzas_elementos;
        if (list == null) return null;
        foreach (var e in list)
            if (e.elementTag == tag) return e;
        return null;
    }

    CapacidadPmData GetCapacidad(int tag, string tipo)
    {
        if (loader == null || loader.modelData == null) return null;
        var list = loader.modelData.capacidades;
        if (list == null) return null;
        string target = tipo == "Viga" ? "viga"
            : tipo == "Columna" ? "columna" : "muro";
        foreach (var c in list)
            if (c.elementTag == tag && c.elemento_tipo == target) return c;
        return null;
    }

    void OnGUI()
    {
        // ViewerHUD presenta estos resultados con una convencion de seccion
        // unica (-F_i, +F_j) y evita superponer dos fichas del mismo elemento.
        return;
#pragma warning disable CS0162
        if (selection == null || loader == null) return;
        if (selection.SelectedTag < 0) return;

        ElementInternalForceData f = GetForces(selection.SelectedTag);
        CapacidadPmData cap = GetCapacidad(selection.SelectedTag, selection.SelectedType);

        float pw = 360f;
        float ph = f != null ? 210f : 50f;
        float x = Screen.width - pw - 10f;
        float y = Screen.height - ph - 260f;

        GUI.Box(new Rect(x, y, pw, ph), "Resultados estructurales (P1L4)");
        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 35));

        if (loader.modelData != null && loader.modelData.analysis != null)
            GUILayout.Label($"Caso activo: {loader.modelData.analysis.caso}");

        if (f != null)
        {
            GUILayout.Label($"elementTag {f.elementTag} -> nodos {f.node_i} | {f.node_j}");
            GUILayout.Space(4);
            GUILayout.Label("Local [N, Vy, Vz, T, My, Mz]  (kN y kN-m)");
            GUILayout.Label($"Extremo i (nodo {f.node_i}):");
            GUILayout.Label($"  N={Neg(f.F_i)}  Vy={F(f.F_i,1)}  Vz={F(f.F_i,2)}");
            GUILayout.Label($"  T={F(f.F_i,3)}  My={F(f.F_i,4)}  Mz={F(f.F_i,5)}");
            GUILayout.Label($"Extremo j (nodo {f.node_j}):");
            GUILayout.Label($"  N={F(f.F_j,0)}  Vy={F(f.F_j,1)}  Vz={F(f.F_j,2)}");
            GUILayout.Label($"  T={F(f.F_j,3)}  My={F(f.F_j,4)}  Mz={F(f.F_j,5)}");
            GUILayout.Space(3);
            GUIStyle grey = new GUIStyle(GUI.skin.label)
            { richText = true, fontSize = 9 };
            GUILayout.Label("<color=grey>N (compresion<0, traccion>0) | F_i[0]=-N, "
                + "F_j[0]=+N segun convencion del JSON</color>", grey);
        }
        else
        {
            GUILayout.Label("Sin resultados locales para este elemento.");
        }

        GUILayout.EndArea();

        if (cap != null)
            DrawCapacidadPanel(cap);
#pragma warning restore CS0162
    }

    string Neg(float[] v) { return v != null && v.Length > 0 ? v[0].ToString("F1") : "-"; }
    string F(float[] v, int idx)
    {
        return v != null && v.Length > idx ? v[idx].ToString("F2") : "-";
    }

    void DrawCapacidadPanel(CapacidadPmData cap)
    {
        float pw = 300f;
        float ph = 270f;
        float x = Screen.width - pw - 10f;
        float y = 10f;

        GUI.Box(new Rect(x, y, pw, ph),
            $"Demanda-Capacidad P-M | {cap.seccion} [tag {cap.elementTag}]");
        GUILayout.BeginArea(new Rect(x + 10, y + 25, pw - 20, ph - 35));

        GUILayout.Label($"Estado: {cap.estado}");
        GUIStyle org = new GUIStyle(GUI.skin.label)
        { richText = true, wordWrap = true };

        if (cap.demanda != null)
        {
            GUILayout.Space(3);
            GUILayout.Label($"Demanda del modelo ({cap.demanda.caso}):");
            GUILayout.Label($"  N = {cap.demanda.N_kN:F1} kN (compresion<0)");
            GUILayout.Label($"  M = {cap.demanda.M_kN_m:F1} kN-m (extremo "
                + $"{cap.demanda.extremo})");
            GUILayout.Label("<color=grey>Resultado real del modelo alcanzado "
                + "desde elementTag (SIN curva de capacidad).</color>", org);
        }

        GUILayout.Space(3);
        GUILayout.Label("<color=orange>Capacidad P-M NO DISPONIBLE: los datos "
            + "resistentes (f'c, fy, recubrimiento y, para muros, la armadura "
            + "longitudinal) no estan documentados en el proyecto. No se "
            + "dibuja curva inventada.</color>", org);

        if (cap.faltantes != null && cap.faltantes.Length > 0)
        {
            GUILayout.Space(3);
            GUILayout.Label("Datos faltantes:");
            foreach (var m in cap.faltantes)
                GUILayout.Label($"- {m}");
        }

        GUILayout.EndArea();
    }
}
