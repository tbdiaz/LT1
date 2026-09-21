using System.Collections.Generic;
using System.Text;
using UnityEngine;

// Inspector de cargas y areas tributarias (requisito P1L4).
// Muestra SOLO lo que existe en modelo_combinado.json:
//   * resumen del caso activo (patrones, equilibrio vertical y lateral),
//   * cargas aplicadas del caso (beamPoint/beamUniform LT2+LT1, o sismo en
//     masters para EX/EY; COMBO_R = G+Q+EX con los coeficientes exportados),
//   * apoyos, masters, diafragmas, constraint_links,
//   * areas tributarias LT1 (108) y LT2 (320) con su fuente.
// Ningun dato se recalcula: las filas tributarias y las cargas se leen tal
// cual fueron exportadas.
public class LoadInspector : MonoBehaviour
{
    private ModelLoader loader;
    private bool show = false;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.L)) show = !show;
    }

    void OnGUI()
    {
        return; // la capa grafica y su estado se controlan desde ViewerHUD
#pragma warning disable CS0162
        if (!show) return;
        if (loader == null || loader.combinedRoot == null) return;
        if (loader.combinedRoot.loads == null) return;

        float pw = 430f;
        float ph = 300f;
        float x = Screen.width - pw - 10f;
        float y = 432f;

        GUI.Box(new Rect(x, y, pw, ph), "Cargas y Areas Tributarias");

        GUILayout.BeginArea(new Rect(x + 10, y + 24, pw - 20, ph - 34));

        GUILayout.Label($"<b>Caso activo: {loader.activeCase}</b>");
        var info = loader.GetCaseInfo(loader.activeCase);
        if (info != null && info.patrones != null && info.patrones.Length > 0)
        {
            var pats = new List<string>();
            foreach (var p in info.patrones) pats.Add(p.ToString());
            GUILayout.Label($"  patrones: {string.Join(" + ", pats.ToArray())}");
        }
        else if (loader.activeCase == "COMBO_R")
        {
            GUILayout.Label("  patrones: 1,2,3,4,5 (G + Q + EX, coef EY=0)");
        }

        DrawLoads();

        GUILayout.Space(6);
        GUILayout.Label("<b>Equilibrio (exportado):</b>");
        var eq = loader.Eq;
        GUILayout.Label($"  P_aplicada = {eq.P_aplicada_kN:F3} kN | "
            + $"sumRz = {eq.sum_Rz_kN:F3} kN | err_rel(v) = {eq.err_rel_vertical:E2}");
        if (eq.lat_axis.Length > 0)
            GUILayout.Label($"  {eq.lat_axis}: corte_basal = {eq.corte_basal_kN:F3} kN "
                + $"| err_rel(lat) = {eq.err_rel_lateral:E2} | rc = {eq.rc}");

        GUILayout.Space(6);
        int tribLt1 = loader.combinedRoot.tributary_areas != null
            && loader.combinedRoot.tributary_areas.LT1 != null
            ? (loader.combinedRoot.tributary_areas.LT1.filas != null
               ? loader.combinedRoot.tributary_areas.LT1.filas.Length : 0) : 0;
        int tribLt2 = loader.combinedRoot.tributary_areas != null
            && loader.combinedRoot.tributary_areas.LT2 != null
            ? (loader.combinedRoot.tributary_areas.LT2.filas != null
               ? loader.combinedRoot.tributary_areas.LT2.filas.Length : 0) : 0;
        GUILayout.Label("<b>Inventario del modelo:</b>");
        GUILayout.Label($"  Nodos: {loader.modelData.nodes.Length} | "
            + $"Apoyos: {loader.modelData.supports.Length} (B1 fijos 6 GDL) | "
            + $"Masters: {loader.combinedRoot.masters.Length} | "
            + $"Diafragmas: {loader.modelData.diaphragms.Length}");
        GUILayout.Label($"  ConstraintLinks(rigid): {loader.modelData.constraint_links.Length} | "
            + $"Elementos: {loader.modelData.beams.Length + loader.modelData.columns.Length + loader.modelData.walls.Length}");
        GUILayout.Label($"  Area tributaria LT1: {tribLt1} filas | LT2: {tribLt2} filas");

        GUILayout.EndArea();
#pragma warning restore CS0162
    }

    void DrawLoads()
    {
        string c = loader.activeCase;
        if (c == "EX" || c == "EY")
        {
            DrawLateral(c);
            return;
        }

        var g = loader.combinedRoot.loads.G;
        var q = loader.combinedRoot.loads.Q;
        var ex = loader.combinedRoot.loads.EX;

        if (c == "G")
            DrawBeamLoads("G (patrones 1/2)", g);
        else if (c == "Q")
            DrawBeamLoads("Q (patrones 3/4)", q);
        else if (c == "COMBO_R")
        {
            GUILayout.Label($"  coef: G={1f:0.#} Q={1f:0.#} EX={1f:0.#} EY={0f:0.#} "
                + "(R = G + Q + EX)");
            DrawBeamLoads("G (patron 1/2)", g);
            DrawBeamLoads("Q (patron 3/4)", q);
            if (ex != null) GUILayout.Label($"  EX (patron 5): {ex.Length} fuerzas sísmicas en masters");
        }
    }

    void DrawBeamLoads(string title, CombinedBeamLoad[] loads)
    {
        if (loads == null || loads.Length == 0)
        {
            GUILayout.Label($"  {title}: 0 registros");
            return;
        }

        int lt2 = 0, lt1 = 0, comb = 0, point = 0, uniform = 0;
        foreach (var l in loads)
        {
            if (l.origen == "LT2") lt2++;
            else if (l.origen == "LT1") lt1++;
            else comb++;
            if (l.tipo != null && l.tipo.StartsWith("beamPoint")) point++;
            else uniform++;
        }
        GUILayout.Label($"  {title}: {loads.Length} registros "
            + $"(LT2 {lt2} / LT1 {lt1} / COMBINADO {comb}); "
            + $"beamPoint {point} / beamUniform {uniform}");
    }

    void DrawLateral(string caseKey)
    {
        var lat = caseKey == "EX" ? loader.combinedRoot.loads.EX
                                  : loader.combinedRoot.loads.EY;
        if (lat == null || lat.Length == 0)
        {
            GUILayout.Label($"  {caseKey}: sin fuerzas sísmicas");
            return;
        }

        GUILayout.Label($"  {caseKey} (patron {lat[0].patron_tag}): fuerzas de piso "
            + $"aplicadas en los masters 1001..1005");
        foreach (var f in lat)
        {
            GUILayout.Label($"    piso {f.piso}: master {f.node_tag} | "
                + $"W = {f.W_sismico_kN:F2} kN | fx = {f.fx_kN:F2} kN | "
                + $"fy = {f.fy_kN:F2} kN");
        }
    }
}
