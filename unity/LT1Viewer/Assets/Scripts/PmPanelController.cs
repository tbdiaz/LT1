using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

// P1L4 - FASE B: panel de capacidad P-M (curva + punto de demanda +
// DENTRO/FUERA + caso activo + trazabilidad) del visor COMBINADO.
//
// Lee results.pm de modelo_combinado.json (a traves de loader.rawJson,
// igual que forces/displacements/reactions/equilibrio): NINGUN valor se
// inventa, todo proviene del JSON exportado por p1l4_pm.py / 
// integrar_p1l4_unity.py.
//
//   * columna_113022  -> curva P-M (P 70x70, 16 barras de 22 mm).
//   * muro_M001       -> los objetos Unity 4001 y 4002 (muro_corner, media
//     seccion cada uno) se agrupan como UN solo muro fisico: curva de eje
//     FUERTE (en el plano de la pared) y DEBIL (fuera de plano), cada una
//     con su punto de demanda.
//
// Al seleccionar el elemento, el panel muestra la curva, el punto de
// demanda del caso activo, el DENTRO/FUERA de cada eje y la trazabilidad
// JSON. El caso activo se cambia con el selector 'Caso activo'
// (CaseSelector) y el panel se refresca solo (escucha el caso vigente).
public class PmPanelController : MonoBehaviour
{
    // margenes del grafico (mismas constantes para dibujar y rotular)
    const int ML = 54;
    const int MR = 12;
    const int MT = 12;
    const int MB = 36;

    private ModelLoader loader;
    private SelectionController selection;
    private PmData pm;
    private Texture2D chart;
    private string chartKey = "";

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        selection = FindObjectOfType<SelectionController>();
    }

    void LateUpdate()
    {
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        if (selection == null) selection = FindObjectOfType<SelectionController>();

        if (pm == null && loader != null && !string.IsNullOrEmpty(loader.rawJson))
        {
            pm = PmData.Parse(loader.rawJson);
            if (pm == null)
                Debug.LogWarning("[PmPanel] results.pm no encontrado o ilegible "
                                 + "en modelo_combinado.json");
        }
        if (pm == null || selection == null) return;

        int tag = selection.SelectedTag;
        if (tag < 0)
        {
            chart = null;
            chartKey = "";
            return;
        }

        string caso = loader != null && !string.IsNullOrEmpty(loader.activeCase)
            ? loader.activeCase : pm.casoActivo;

        PmBloque blk = pm.BloquePara(tag);
        if (blk == null)
        {
            chart = null;
            chartKey = "";
            return;
        }

        string key = blk.clave + "|" + caso;
        if (key != chartKey)
        {
            chartKey = key;
            chart = BuildChart(blk, caso, 560, 400);
        }
    }

    void OnGUI()
    {
        if (pm == null || selection == null || chart == null) return;

        int tag = selection.SelectedTag;
        if (tag < 0) return;

        PmBloque blk = pm.BloquePara(tag);
        if (blk == null) return;

        string caso = loader != null && !string.IsNullOrEmpty(loader.activeCase)
            ? loader.activeCase : pm.casoActivo;
        PmDemanda d = blk.Demanda(caso);

        GUIStyle rich = new GUIStyle(GUI.skin.label)
        { richText = true, wordWrap = true, fontSize = 12 };
        GUIStyle small = new GUIStyle(GUI.skin.label)
        { richText = true, wordWrap = true, fontSize = 10 };

        float pw = 800f;
        float px = Mathf.Max(4f, (Screen.width - pw) / 2f);
        float py = 60f;
        float headerH = 78f;

        // --- cabecera ------------------------------------------------------
        GUI.Box(new Rect(px, py, pw, headerH), "Capacidad P-M (FASE B)");
        GUILayout.BeginArea(new Rect(px + 8, py + 20, pw - 16, headerH - 26));
        if (blk.esMuro)
        {
            GUILayout.Label("<b>Muro M001</b> (LT2, eje A')  |  "
                + "<color=grey>objetos Unity 4001 + 4002 agrupados como UN "
                + "solo muro fisico (media seccion cada uno)</color>", rich);
        }
        else
        {
            GUILayout.Label("<b>Columna 113022</b> (LT1)  |  "
                + "<color=grey>P 70x70, 16 barras de 22 mm</color>", rich);
        }
        GUILayout.Label("Caso activo: <b>" + caso + "</b>  |  curvas desde "
            + "results.pm(" + blk.clave + ")  |  unidades kN / kN·m", rich);
        GUILayout.EndArea();

        // --- grafico -------------------------------------------------------
        float chartY = py + headerH + 4f;
        GUI.DrawTexture(new Rect(px, chartY, chart.width, chart.height), chart);

        float pMin, pMax, mMax;
        Ranges(blk, caso, out pMin, out pMax, out mMax);
        float plotL = px + ML;
        float plotT = chartY + MT;
        float plotR = plotL + (chart.width - ML - MR);
        float plotB = plotT + (chart.height - MT - MB);

        GUI.Label(new Rect(px + 4, chartY + 2, 130f, 18f), "M (kN·m)", small);
        GUI.Label(new Rect(px + 6, plotT - 2f, 90f, 18f), FormatV(mMax), small);
        GUI.Label(new Rect(plotL, plotB - 16f, 70f, 18f), "0", small);
        GUI.Label(new Rect(plotR - 150f, plotB - 16f, 160f, 18f),
                  FormatV(pMax) + "  (P0 compresion)", small);
        GUI.Label(new Rect(px + 4, plotB + 2f, 260f, 18f),
                  "P (kN, compresion positiva) ->", small);

        // --- pie (demanda vs capacidad) -------------------------------------
        float footY = chartY + chart.height + 4f;
        float footH = blk.esMuro ? 228f : 120f;
        GUI.Box(new Rect(px, footY, pw, footH),
                "Demanda vs capacidad - caso activo");
        GUILayout.BeginArea(new Rect(px + 8, footY + 20, pw - 16, footH - 28));

        if (d == null)
        {
            GUILayout.Label("Sin demanda exportada para el caso " + caso, rich);
        }
        else if (blk.esMuro)
        {
            GUILayout.Label("<b>EJE FUERTE</b> (en plano; vuelco sobre X "
                + "global):");
            GUILayout.Label("  N = " + d.N.ToString("F1") + " kN | M_muro = "
                + d.MDem.ToString("F1") + " kN·m | M_cap(N) = "
                + d.MCap.ToString("F1") + " kN·m  ->  " + Estado(d.dentro), rich);
            GUILayout.Label("<b>EJE DEBIL</b> (fuera de plano):");
            GUILayout.Label("  My = " + d.MyDem.ToString("F1") + " kN·m | "
                + "M_cap_debil(N) = " + d.MyCap.ToString("F1")
                + " kN·m  ->  " + Estado(d.dentroDebil), rich);
        }
        else
        {
            GUILayout.Label("  N = " + d.N.ToString("F1") + " kN (compresion+)"
                + " |  M = " + d.MDem.ToString("F1") + " kN·m |  M_cap(N) = "
                + d.MCap.ToString("F1") + " kN·m  ->  "
                + Estado(d.dentro), rich);
        }

        if (blk.esMuro && caso == "EY" && d != null && !d.dentro)
        {
            GUILayout.Label("<color=#d02000>EVALUADO: el caso EY deja el eje "
                + "fuerte FUERA (D/C ~ 1.78); la demanda es la reaccion Mx "
                + "real de la base del modelo (auditoria_ey_m001.md).</color>",
                small);
        }

        string traz = "Trazabilidad: elementTag -> results.pm." + blk.clave
            + " -> demanda_por_caso." + caso + ";  capacidad: pico M de la "
            + "fiber section a la N de demanda (estado limite eps_cu=0.003; "
            + "FASE A verificada por reacciones).  P0 = "
            + Mathf.Abs(blk.P0).ToString("F0") + " kN";
        if (blk.esMuro)
            traz += "  |  P0 debil = " + Mathf.Abs(blk.P0Debil).ToString("F0")
                + " kN";
        traz += ".";
        GUILayout.Label("<color=grey>" + traz + "</color>", small);

        GUILayout.EndArea();
    }

    // -----------------------------------------------------------------------
    //  Grafico
    // -----------------------------------------------------------------------
    void Ranges(PmBloque blk, string caso, out float pMin, out float pMax,
                out float mMax)
    {
        pMin = 0f;
        pMax = 0f;
        mMax = 0f;
        float p0 = 0f;
        for (int i = 0; i < blk.curva.Count; i++)
        {
            p0 = Mathf.Max(p0, Mathf.Abs(blk.curva[i].P));
            mMax = Mathf.Max(mMax, blk.curva[i].M);
        }
        for (int i = 0; i < blk.curvaDebil.Count; i++)
        {
            p0 = Mathf.Max(p0, Mathf.Abs(blk.curvaDebil[i].P));
            mMax = Mathf.Max(mMax, blk.curvaDebil[i].M);
        }
        PmDemanda d = blk.Demanda(caso);
        if (d != null)
        {
            p0 = Mathf.Max(p0, Mathf.Abs(d.N));
            mMax = Mathf.Max(mMax, d.MDem);
            if (blk.esMuro) mMax = Mathf.Max(mMax, d.MyDem);
            // traccion (N compresion negativo) -> pequeno margen a traccion
            if (d.N < 0f) pMin = d.N * 1.3f;
        }
        pMax = p0 * 1.06f + 1f;
        mMax = mMax * 1.06f + 1f;
    }

    Texture2D BuildChart(PmBloque blk, string caso, int w, int h)
    {
        Color32 bg = new Color32(250, 250, 250, 255);
        Color32 grid = new Color32(214, 214, 214, 255);
        Color32 axis = new Color32(130, 130, 130, 255);
        Color32 colC = new Color32(0, 77, 204, 255);
        Color32 fuC = new Color32(200, 40, 40, 255);
        Color32 deC = new Color32(230, 140, 0, 255);
        Color32 okCore = new Color32(10, 154, 10, 255);
        Color32 okRing = new Color32(0, 92, 0, 255);
        Color32 koCore = new Color32(208, 0, 0, 255);
        Color32 koRing = new Color32(140, 0, 0, 255);

        Color32[] px = new Color32[w * h];
        for (int i = 0; i < px.Length; i++) px[i] = bg;

        float pMin, pMax, mMax;
        Ranges(blk, caso, out pMin, out pMax, out mMax);

        int leftX = ML, rightX = w - MR, topY = MT, botY = h - MB;
        float span = Mathf.Max(pMax - pMin, 1e-3f);
        float mSpan = Mathf.Max(mMax, 1e-3f);

        for (int i = 1; i <= 4; i++)
        {
            int gx = leftX + (int)Mathf.Round(i / 5f * (rightX - leftX));
            Line(px, w, h, gx, topY, gx, botY, grid);
            int gy = topY + (int)Mathf.Round(i / 5f * (botY - topY));
            Line(px, w, h, leftX, gy, rightX, gy, grid);
        }

        int zx = Mathf.Clamp(
            Mathf.RoundToInt(leftX + (0f - pMin) / span * (rightX - leftX)),
            leftX, rightX);
        Line(px, w, h, zx, topY, zx, botY, axis);
        Line(px, w, h, leftX, botY, rightX, botY, axis);

        if (blk.esMuro)
        {
            Polyline(px, w, h, blk.curva, fuC, false, pMin, span, mSpan,
                     leftX, rightX, topY, botY);
            Polyline(px, w, h, blk.curvaDebil, deC, true, pMin, span, mSpan,
                     leftX, rightX, topY, botY);
        }
        else
        {
            Polyline(px, w, h, blk.curva, colC, false, pMin, span, mSpan,
                     leftX, rightX, topY, botY);
        }

        PmDemanda d = blk.Demanda(caso);
        if (d != null)
        {
            int dx = Mathf.Clamp(
                Mathf.RoundToInt(leftX + (d.N - pMin) / span * (rightX - leftX)),
                leftX, rightX);
            int dy = Mathf.Clamp(
                Mathf.RoundToInt(botY - d.MDem / mSpan * (botY - topY)),
                topY, botY);
            DrawMarker(px, w, h, dx, dy,
                       d.dentro ? okCore : koCore,
                       d.dentro ? okRing : koRing);
            if (blk.esMuro)
            {
                int wy = Mathf.Clamp(
                    Mathf.RoundToInt(botY - d.MyDem / mSpan * (botY - topY)),
                    topY, botY);
                DrawMarker(px, w, h, dx, wy,
                           d.dentroDebil ? okCore : koCore,
                           d.dentroDebil ? okRing : koRing);
            }
        }

        Texture2D tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
        tex.SetPixels32(px);
        tex.Apply();
        return tex;
    }

    static void Polyline(Color32[] px, int w, int h, List<PmPoint> pts,
                         Color32 c, bool dash, float pMin, float span,
                         float mSpan, int leftX, int rightX, int topY, int botY)
    {
        if (pts == null || pts.Count < 2) return;
        for (int i = 1; i < pts.Count; i++)
        {
            int x0 = Mathf.Clamp(
                Mathf.RoundToInt(leftX + (pts[i - 1].P - pMin) / span
                                 * (rightX - leftX)), leftX, rightX);
            int y0 = Mathf.Clamp(
                Mathf.RoundToInt(botY - pts[i - 1].M / mSpan * (botY - topY)),
                topY, botY);
            int x1 = Mathf.Clamp(
                Mathf.RoundToInt(leftX + (pts[i].P - pMin) / span
                                 * (rightX - leftX)), leftX, rightX);
            int y1 = Mathf.Clamp(
                Mathf.RoundToInt(botY - pts[i].M / mSpan * (botY - topY)),
                topY, botY);
            if (dash) DashedLine(px, w, h, x0, y0, x1, y1, c, 5);
            else Line(px, w, h, x0, y0, x1, y1, c);
        }
    }

    static void Line(Color32[] px, int w, int h, int x0, int y0, int x1, int y1,
                     Color32 c)
    {
        int dx = Mathf.Abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
        int dy = -Mathf.Abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
        int err = dx + dy;
        int x = x0, y = y0;
        for (;;)
        {
            SetPixel(px, w, h, x, y, c);
            if (x == x1 && y == y1) break;
            int e2 = 2 * err;
            if (e2 >= dy) { err += dy; x += sx; }
            if (e2 <= dx) { err += dx; y += sy; }
        }
    }

    static void DashedLine(Color32[] px, int w, int h, int x0, int y0, int x1,
                           int y1, Color32 c, int seg)
    {
        float len = Mathf.Sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0));
        if (len < 1f)
        {
            SetPixel(px, w, h, x0, y0, c);
            return;
        }
        float dx = (x1 - x0) / len, dy = (y1 - y0) / len;
        float t = 0f;
        while (t < len)
        {
            float e = Mathf.Min(t + seg, len);
            Line(px, w, h,
                 x0 + Mathf.RoundToInt(dx * t), y0 + Mathf.RoundToInt(dy * t),
                 x0 + Mathf.RoundToInt(dx * e), y0 + Mathf.RoundToInt(dy * e),
                 c);
            t = e + seg;
        }
    }

    static void FillRect(Color32[] px, int w, int h, int x0, int y0, int x1,
                         int y1, Color32 c)
    {
        int xa = Mathf.Clamp(Mathf.Min(x0, x1), 0, w - 1);
        int xb = Mathf.Clamp(Mathf.Max(x0, x1), 0, w - 1);
        int ya = Mathf.Clamp(Mathf.Min(y0, y1), 0, h - 1);
        int yb = Mathf.Clamp(Mathf.Max(y0, y1), 0, h - 1);
        for (int y = ya; y <= yb; y++)
            for (int x = xa; x <= xb; x++)
                px[y * w + x] = c;
    }

    static void DrawMarker(Color32[] px, int w, int h, int cx, int cy,
                           Color32 core, Color32 ring)
    {
        FillRect(px, w, h, cx - 2, cy - 2, cx + 2, cy + 2, core);
        Line(px, w, h, cx - 4, cy - 4, cx + 4, cy - 4, ring);
        Line(px, w, h, cx + 4, cy - 4, cx + 4, cy + 4, ring);
        Line(px, w, h, cx + 4, cy + 4, cx - 4, cy + 4, ring);
        Line(px, w, h, cx - 4, cy + 4, cx - 4, cy - 4, ring);
    }

    static void SetPixel(Color32[] px, int w, int h, int x, int y, Color32 c)
    {
        if (x >= 0 && x < w && y >= 0 && y < h) px[y * w + x] = c;
    }

    static string FormatV(float v)
    {
        if (v >= 10000f) return (v / 1000f).ToString("0") + "k";
        if (v >= 1000f) return (v / 1000f).ToString("0.0") + "k";
        return v.ToString("0");
    }

    static string Estado(bool dentro)
    {
        return dentro ? "<color=#0a8a0a>DENTRO</color>"
                      : "<color=#d02000>FUERA</color>";
    }
}

// ---------------------------------------------------------------------------
//  Datos de results.pm (parseados del JSON crudo, como force/results)
// ---------------------------------------------------------------------------
public class PmData
{
    public string casoActivo = "";
    public string[] casosAutorizados = new string[0];
    public PmBloque muro;
    public PmBloque columna;

    public PmBloque BloquePara(int tag)
    {
        if (muro != null && muro.Contiene(tag)) return muro;
        if (columna != null && columna.Contiene(tag)) return columna;
        return null;
    }

    public static PmData Parse(string rawJson)
    {
        if (string.IsNullOrEmpty(rawJson)) return null;
        string pmJson = ExtractValue(rawJson, "pm");
        if (string.IsNullOrEmpty(pmJson)) return null;

        object root;
        if (!PmJsonParser.TryParse(pmJson, out root)) return null;
        Dictionary<string, object> pm = root as Dictionary<string, object>;
        if (pm == null) return null;

        PmData d = new PmData();
        d.casoActivo = PmBloque.Str(pm, "caso_activo");
        List<object> ca = pm.ContainsKey("casos_autorizados")
            ? pm["casos_autorizados"] as List<object> : null;
        if (ca != null)
        {
            d.casosAutorizados = new string[ca.Count];
            for (int i = 0; i < ca.Count; i++)
                d.casosAutorizados[i] = ca[i] as string ?? "";
        }
        d.muro = PmBloque.Muro(PmBloque.Obj(pm, "muro_M001"));
        d.columna = PmBloque.Columna(PmBloque.Obj(pm, "columna_113022"));
        if (d.muro == null || d.columna == null
            || d.muro.curva == null || d.muro.curva.Count == 0
            || d.columna.curva == null || d.columna.curva.Count == 0)
            return null;
        return d;
    }

    // Copia del patron de ModelLoader (ExtractValue era privado): devuelve el
    // substring JSON que corresponde a una clave de primer nivel ("pm").
    static string ExtractValue(string json, string keyName)
    {
        int idx = -1;
        for (int i = 0; i + keyName.Length <= json.Length; i++)
        {
            if (i > 0 && (json[i - 1] == ' ' || json[i - 1] == '{' || json[i - 1] == ','))
                if (json[i] == '"')
                {
                    int j = i + 1;
                    int k = 0;
                    bool scpe = false;
                    while (j < json.Length && k < keyName.Length)
                    {
                        if (json[j] == keyName[k] && !scpe) { j++; k++; }
                        else break;
                    }
                    // se exige tamano exacto mayor que keyName (coma, llave, espacio)
                    if (k == keyName.Length && j < json.Length && json[j] == '"')
                    {
                        // debe terminar con : (coma, espacioss...)
                        int p = j + 1;
                        while (p < json.Length && char.IsWhiteSpace(json[p])) p++;
                        if (p < json.Length && json[p] == ':') { idx = p; break; }
                    }
                }
        }
        if (idx < 0) return null;

        int i0 = idx + 1;
        while (i0 < json.Length && char.IsWhiteSpace(json[i0])) i0++;
        if (i0 >= json.Length) return null;

        char c = json[i0];
        if (c != '{' && c != '[') return null;
        char open = c;
        char close = c == '{' ? '}' : ']';
        int depth = 1;
        int i1 = i0 + 1;
        bool inStr = false, esc = false;
        while (i1 < json.Length && depth > 0)
        {
            char ch = json[i1];
            if (inStr)
            {
                if (esc) esc = false;
                else if (ch == '\\') esc = true;
                else if (ch == '"') inStr = false;
            }
            else
            {
                if (ch == '"') inStr = true;
                else if (ch == open) depth++;
                else if (ch == close) depth--;
            }
            i1++;
        }
        if (depth != 0) return null;
        return json.Substring(i0, i1 - i0);
    }
}

public class PmBloque
{
    public string clave = "";
    public string etiqueta = "";
    public int[] elementTags = new int[0];
    public bool esMuro;
    public List<PmPoint> curva = new List<PmPoint>();
    public List<PmPoint> curvaDebil = new List<PmPoint>();
    public float P0;
    public float P0Debil;
    public Dictionary<string, PmDemanda> demandas =
        new Dictionary<string, PmDemanda>();

    public bool Contiene(int tag)
    {
        for (int i = 0; i < elementTags.Length; i++)
            if (elementTags[i] == tag) return true;
        return false;
    }

    public PmDemanda Demanda(string caso)
    {
        PmDemanda d;
        if (demandas != null && demandas.TryGetValue(caso, out d)) return d;
        return null;
    }

    public static PmBloque Muro(Dictionary<string, object> obj)
    {
        if (obj == null) return null;
        PmBloque b = new PmBloque();
        b.clave = "muro_M001";
        b.etiqueta = "Muro M001";
        b.esMuro = true;
        b.elementTags = Tags(obj);
        Dictionary<string, object> cap = Obj(obj, "capacidad");
        if (cap == null) return null;
        b.curva = Puntos(Leaf(cap, "curva_fuerte"));
        b.curvaDebil = Puntos(Leaf(cap, "curva_debil"));
        b.P0 = (float)Num(cap, "P0_kN_compresion", 0f);
        b.P0Debil = (float)Num(cap, "P0_kN_debil", 0f);
        b.demandas = Demandas(Obj(obj, "demanda_por_caso"), true);
        if (b.curva == null || b.curva.Count == 0) return null;
        return b;
    }

    public static PmBloque Columna(Dictionary<string, object> obj)
    {
        if (obj == null) return null;
        PmBloque b = new PmBloque();
        b.clave = "columna_113022";
        b.etiqueta = "Columna 113022";
        b.esMuro = false;
        b.elementTags = Tags(obj);
        Dictionary<string, object> cap = Obj(obj, "capacidad");
        if (cap == null) return null;
        b.curva = Puntos(Leaf(cap, "curva"));
        b.curvaDebil = new List<PmPoint>();
        b.P0 = (float)Num(cap, "P0_kN_compresion", 0f);
        b.demandas = Demandas(Obj(obj, "demanda_por_caso"), false);
        if (b.curva == null || b.curva.Count == 0) return null;
        return b;
    }

    public static List<PmPoint> Puntos(object leaf)
    {
        List<PmPoint> r = new List<PmPoint>();
        List<object> arr = leaf as List<object>;
        if (arr == null) return r;
        for (int i = 0; i < arr.Count; i++)
        {
            List<object> pt = arr[i] as List<object>;
            if (pt == null || pt.Count < 2) continue;
            double p = ToD(pt[0]);
            double m = ToD(pt[1]);
            // el JSON usa signo de carga (negativo = compresion); el panel
            // grafica compresion POSITIVA, igual que los N de la demanda.
            r.Add(new PmPoint { P = (float)-p, M = (float)m });
        }
        return r;
    }

    public static Dictionary<string, PmDemanda> Demandas(
        Dictionary<string, object> obj, bool esMuro)
    {
        Dictionary<string, PmDemanda> r = new Dictionary<string, PmDemanda>();
        if (obj == null) return r;
        foreach (KeyValuePair<string, object> kv in obj)
        {
            Dictionary<string, object> v = kv.Value as Dictionary<string, object>;
            if (v == null) continue;
            PmDemanda d = new PmDemanda();
            d.caso = kv.Key;
            d.N = (float)Num(v, "N_kN_compresion", 0f);
            if (esMuro)
            {
                d.MDem = (float)Num(v, "M_fuerte_demanda_kN_m", 0f);
                d.MCap = (float)Num(v, "M_fuerte_capacidad_kN_m", 0f);
                d.dentro = B(v, "dentro_fuerte", false);
                d.MyDem = (float)Num(v, "My_debil_demanda_kN_m", 0f);
                d.MyCap = (float)Num(v, "M_debil_capacidad_kN_m", 0f);
                d.dentroDebil = B(v, "dentro_debil", false);
            }
            else
            {
                d.MDem = (float)Num(v, "M_demanda_kN_m", 0f);
                d.MCap = (float)Num(v, "M_capacidad_kN_m", 0f);
                d.dentro = B(v, "dentro", false);
            }
            r[kv.Key] = d;
        }
        return r;
    }

    public static Dictionary<string, object> Obj(
        Dictionary<string, object> parent, string key)
    {
        if (parent == null || !parent.ContainsKey(key)) return null;
        return parent[key] as Dictionary<string, object>;
    }

    public static object Leaf(Dictionary<string, object> parent, string key)
    {
        if (parent == null || !parent.ContainsKey(key)) return null;
        return parent[key];
    }

    public static int[] Tags(Dictionary<string, object> obj)
    {
        List<object> arr = Leaf(obj, "elementTags") as List<object>;
        if (arr == null) return new int[0];
        int[] t = new int[arr.Count];
        for (int i = 0; i < arr.Count; i++)
        {
            object it = arr[i];
            t[i] = it is double ? (int)(double)it : 0;
        }
        return t;
    }

    public static string Str(Dictionary<string, object> obj, string key)
    {
        object v = Leaf(obj, key);
        return v as string ?? "";
    }

    public static bool B(Dictionary<string, object> obj, string key, bool def)
    {
        object v = Leaf(obj, key);
        if (v is bool) return (bool)v;
        return def;
    }

    public static double Num(Dictionary<string, object> obj, string key,
                             double def)
    {
        object v = Leaf(obj, key);
        if (v is double) return (double)v;
        return def;
    }

    public static double ToD(object v)
    {
        if (v is double) return (double)v;
        return 0.0;
    }
}

public class PmPoint
{
    public float P;   // compresion positiva (kN)
    public float M;   // kN*m
}

public class PmDemanda
{
    public string caso = "";
    public float N;      // compresion positiva (kN)
    public float MDem;   // kN*m
    public float MCap;   // kN*m, capacidad a la N de demanda
    public bool dentro;
    public float MyDem;  // muro: fuera de plano (kN*m)
    public float MyCap;  // muro: capacidad eje debil a la N de demanda
    public bool dentroDebil;
}

// ---------------------------------------------------------------------------
//  Parser JSON minimo (solo para results.pm; JsonUtility no soporta
//  diccionarios ni matrices anidadas de este bloque).
// ---------------------------------------------------------------------------
public static class PmJsonParser
{
    public static bool TryParse(string text, out object value)
    {
        value = null;
        if (string.IsNullOrEmpty(text)) return false;
        int i = 0;
        if (!ParseValue(text, ref i, out value)) return false;
        SkipWs(text, ref i);
        return i == text.Length;
    }

    static void SkipWs(string s, ref int i)
    {
        while (i < s.Length
               && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r'))
            i++;
    }

    static bool ParseValue(string s, ref int i, out object v)
    {
        SkipWs(s, ref i);
        v = null;
        if (i >= s.Length) return false;
        char c = s[i];
        if (c == '{') return ParseObject(s, ref i, out v);
        if (c == '[') return ParseArray(s, ref i, out v);
        if (c == '"') return ParseString(s, ref i, out v);
        if (c == 't' && Match(s, i, "true")) { v = true; i += 4; return true; }
        if (c == 'f' && Match(s, i, "false")) { v = false; i += 5; return true; }
        if (c == 'n' && Match(s, i, "null")) { i += 4; return true; }
        return ParseNumber(s, ref i, out v);
    }

    static bool ParseObject(string s, ref int i, out object v)
    {
        Dictionary<string, object> d = new Dictionary<string, object>();
        v = d;
        i++;
        SkipWs(s, ref i);
        if (i < s.Length && s[i] == '}') { i++; return true; }
        while (i < s.Length)
        {
            SkipWs(s, ref i);
            if (i >= s.Length || s[i] != '"') return false;
            object key;
            if (!ParseString(s, ref i, out key)) return false;
            string k = (string)key;
            SkipWs(s, ref i);
            if (i >= s.Length || s[i] != ':') return false;
            i++;
            object val;
            if (!ParseValue(s, ref i, out val)) return false;
            d[k] = val;
            SkipWs(s, ref i);
            if (i >= s.Length) return false;
            if (s[i] == ',') { i++; continue; }
            if (s[i] == '}') { i++; return true; }
            return false;
        }
        return false;
    }

    static bool ParseArray(string s, ref int i, out object v)
    {
        List<object> l = new List<object>();
        v = l;
        i++;
        SkipWs(s, ref i);
        if (i < s.Length && s[i] == ']') { i++; return true; }
        while (i < s.Length)
        {
            SkipWs(s, ref i);
            object val;
            if (!ParseValue(s, ref i, out val)) return false;
            l.Add(val);
            SkipWs(s, ref i);
            if (i >= s.Length) return false;
            if (s[i] == ',') { i++; continue; }
            if (s[i] == ']') { i++; return true; }
            return false;
        }
        return false;
    }

    static bool ParseString(string s, ref int i, out object v)
    {
        StringBuilder sb = new StringBuilder();
        v = "";
        i++; // comilla de apertura
        while (i < s.Length)
        {
            char c = s[i];
            if (c == '"') { i++; v = sb.ToString(); return true; }
            if (c == '\\')
            {
                i++;
                if (i >= s.Length) return false;
                char e = s[i];
                switch (e)
                {
                    case '"': sb.Append('"'); break;
                    case '\\': sb.Append('\\'); break;
                    case '/': sb.Append('/'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    case 't': sb.Append('\t'); break;
                    case 'u':
                        if (i + 4 >= s.Length) return false;
                        string hex = s.Substring(i + 1, 4);
                        sb.Append((char)System.Convert.ToInt32(hex, 16));
                        i += 4;
                        break;
                    default:
                        return false;
                }
                i++;
                continue;
            }
            sb.Append(c);
            i++;
        }
        return false;
    }

    static bool ParseNumber(string s, ref int i, out object v)
    {
        v = 0.0;
        int start = i;
        if (i < s.Length && s[i] == '-') i++;
        while (i < s.Length && ((s[i] >= '0' && s[i] <= '9') || s[i] == '.'))
            i++;
        if (i < s.Length && (s[i] == 'e' || s[i] == 'E'))
        {
            i++;
            if (i < s.Length && (s[i] == '+' || s[i] == '-')) i++;
            while (i < s.Length && (s[i] >= '0' && s[i] <= '9')) i++;
        }
        string num = s.Substring(start, i - start);
        double d;
        if (!double.TryParse(num, NumberStyles.Float,
                             CultureInfo.InvariantCulture, out d))
            return false;
        v = d;
        return true;
    }

    static bool Match(string s, int i, string token)
    {
        if (i + token.Length > s.Length) return false;
        for (int k = 0; k < token.Length; k++)
            if (s[i + k] != token[k]) return false;
        return true;
    }
}