using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;

// ModelLoader para el VISOR COMBINADO LT1+LT2 (etapa P1L4).
//
// Fuente unica: `modelo_combinado.json` (StreamingAssets). El JSON se
// deserializa en `combinedRoot` (clases CombinedModelData, espejo exacto del
// esquema exportado) y, ademas, se construyen los agregados legacy del visor
// (modelData.beams/columns/walls/.../analysis/tributary_areas) para que los
// controladores preexistentes sigan funcionando sin cambios de contrato.
//
// Los resultados (forces/displacements/reactions/equilibrio) son un mapa
// {caso: {tag: valor}} que JsonUtility no puede deserializar: se parsean por
// caso activo desde el JSON crudo (SetActiveCase). No se inventa ningun valor:
// todo proviene del JSON exportado.
//
// La capacidad P-M queda PREPARADA (modelData.capacidades == vacio): los
// datos resistentes no estan documentados, asi que no se dibuja ninguna curva.
public class ModelLoader : MonoBehaviour
{
    public string jsonFileName = "modelo_combinado.json";

    // --- modelo legacy (agregados que consumen los controladores) ----------
    [HideInInspector] public ModelRoot modelData;

    // --- modelo combinado (fuente verdadera) --------------------------------
    [HideInInspector] public ModeloCombinado combinedRoot;
    [HideInInspector] public string rawJson;
    [HideInInspector] public string activeCase = "";
    [HideInInspector] public ActiveEquilibrium Eq = new ActiveEquilibrium();
    [HideInInspector] public bool IsLinearSuperposition;
    [HideInInspector] public float[] SuperpositionCoefficients = { 1f, 1f, 1f, 0f };
    [HideInInspector] public int ResultRevision;

    [HideInInspector] public Dictionary<int, GameObject> nodeObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> beamObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> columnObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> wallObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> constraintLinkObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> supportObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public Dictionary<int, GameObject> masterNodeObjects = new Dictionary<int, GameObject>();
    [HideInInspector] public List<GameObject> aestheticSlabObjects = new List<GameObject>();
    [HideInInspector] public Vector3 modelCenter;

    [Header("Losas esteticas LT1 + LT2 (no estructurales)")]
    public string aestheticSlabJsonFileName = "modelo_lt1.json";
    public string aestheticSlabLt2JsonFileName = "edificio_lt2.json";
    [Min(0.01f)] public float aestheticSlabThickness = 0.10f;
    public Color aestheticSlabColor = new Color(0.32f, 0.35f, 0.39f);
    [Tooltip("Desfase grafico del cielo subterraneo para evitar que se pierda por z-fighting. No modifica la cota estructural.")]
    [Min(0f)] public float basementSlabVisibilityOffset = 0.03f;
    [Tooltip("Agrega el cielo estetico del 1er subterraneo LT1 en PISO_1S (-4.01 m), usando la reticula documentada. No altera el modelo estructural.")]
    public bool fillLt1BasementRoofForDesign = true;
    [Tooltip("Completa visualmente la cubierta LT2 con los contornos exteriores documentados. No altera el modelo estructural.")]
    public bool fillLt2RoofForDesign = true;

    // --- trazabilidad elementTag <-> JSON <-> GameObject ---------------------
    [HideInInspector] public Dictionary<int, ElementRef> elementRefs = new Dictionary<int, ElementRef>();
    // restricciones de borde por nodo (apoyos + masters), para el panel de seleccion
    [HideInInspector] public Dictionary<int, int[]> boundaryRestricciones = new Dictionary<int, int[]>();
    [HideInInspector] public Dictionary<int, string> boundaryOrigen = new Dictionary<int, string>();

    // Fuerzas locales [N,Vy,Vz,T,My,Mz] x extremo del caso activo
    [HideInInspector] public Dictionary<int, float[]> elementForceI = new Dictionary<int, float[]>();
    [HideInInspector] public Dictionary<int, float[]> elementForceJ = new Dictionary<int, float[]>();

    public static event Action<string> CaseChanged;

    private Material beamMaterial;
    private Material columnMaterial;
    private Material supportMaterial;
    private Material nodeMaterial;
    private Material masterMaterial;
    private Material diaphragmMaterial;
    private Material wallMaterial;
    private Material constraintLinkMaterial;
    private Material aestheticSlabMaterial;

    private Dictionary<int, int> elementJsonIndex = new Dictionary<int, int>();
    private Dictionary<int, int[]> elementNodePair = new Dictionary<int, int[]>();
    private Dictionary<string, Dictionary<int, float[]>> forceCaseCache =
        new Dictionary<string, Dictionary<int, float[]>>();
    private Dictionary<string, Dictionary<int, float[]>> displacementCaseCache =
        new Dictionary<string, Dictionary<int, float[]>>();
    private Dictionary<string, Dictionary<int, float[]>> reactionCaseCache =
        new Dictionary<string, Dictionary<int, float[]>>();
    private Dictionary<string, ActiveEquilibrium> equilibriumCaseCache =
        new Dictionary<string, ActiveEquilibrium>();
    private int[] emptyInt6 = { 0, 0, 0, 0, 0, 0 };

    public string[] CaseList
    {
        get
        {
            if (combinedRoot == null || combinedRoot.results == null ||
                combinedRoot.results.cases == null) return new string[0];
            return combinedRoot.results.cases;
        }
    }

    public CombinedCaseInfo GetCaseInfo(string caseKey)
    {
        if (combinedRoot == null || combinedRoot.metadata == null) return null;
        var cc = combinedRoot.metadata.casos;
        if (cc == null) return null;
        switch (caseKey)
        {
            case "G": return cc.G;
            case "Q": return cc.Q;
            case "EX": return cc.EX;
            case "EY": return cc.EY;
            case "COMBO_R": return cc.COMBO_R;
            default: return null;
        }
    }

    public bool IsLateralCase(string caseKey)
    {
        return caseKey == "EX" || caseKey == "EY";
    }

    public static Vector3 StructToUnity(float x, float y, float z)
    {
        return new Vector3(x, z, -y);
    }

    void Awake()
    {
        CreateMaterials();
    }

    void CreateMaterials()
    {
        // Paleta de alto contraste para lectura tipo videojuego/visor BIM.
        beamMaterial = CreateMaterial(new Color(1.00f, 0.45f, 0.05f));
        columnMaterial = CreateMaterial(new Color(0.55f, 0.55f, 0.55f));
        supportMaterial = CreateMaterial(new Color(0.95f, 0.12f, 0.18f));
        nodeMaterial = CreateMaterial(new Color(0.20f, 0.85f, 1.00f));
        masterMaterial = CreateMaterial(new Color(1.0f, 0.84f, 0.0f));
        diaphragmMaterial = CreateTransparentMaterial(new Color(0.5f, 0.8f, 0.5f, 0.25f));
        wallMaterial = CreateMaterial(new Color(0.88f, 0.10f, 0.12f));
        aestheticSlabMaterial = CreateMaterial(aestheticSlabColor);
        constraintLinkMaterial = new Material(Shader.Find("Sprites/Default"));
        constraintLinkMaterial.color = new Color(0.0f, 0.85f, 0.90f);
    }

    Material CreateMaterial(Color color)
    {
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = color;
        return mat;
    }

    Material CreateTransparentMaterial(Color color)
    {
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = color;
        mat.SetFloat("_Mode", 3f);
        mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        mat.SetInt("_ZWrite", 0);
        mat.DisableKeyword("_ALPHATEST_ON");
        mat.EnableKeyword("_ALPHABLEND_ON");
        mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        mat.renderQueue = 3000;
        return mat;
    }

    // =======================================================================
    //  Carga
    // =======================================================================
    public bool LoadModel()
    {
        string jsonPath = FindJsonPath();
        if (string.IsNullOrEmpty(jsonPath))
        {
            Debug.LogError($"[LT1Viewer] JSON file not found: {jsonFileName}");
            return false;
        }

        Debug.Log($"[LT1Viewer] Loading model from: {jsonPath}");
        rawJson = File.ReadAllText(jsonPath);

        combinedRoot = JsonUtility.FromJson<ModeloCombinado>(rawJson);
        if (combinedRoot == null || combinedRoot.elements == null)
        {
            Debug.LogError("[LT1Viewer] Failed to parse modelo_combinado.json");
            return false;
        }

        BuildAggregates();
        PrepareResultCaches();

        if (!SetActiveCase(CaseList.Length > 0 ? CaseList[0] : "G"))
        {
            Debug.LogError("[LT1Viewer] No se pudo preparar el caso inicial");
            return false;
        }

        Debug.Log($"[LT1Viewer] Model parsed: {modelData.nodes.Length} nodes, " +
                  $"{modelData.beams.Length} beams, {modelData.columns.Length} columns, " +
                  $"{modelData.walls.Length} walls, " +
                  $"{modelData.constraint_links.Length} constraintLinks, " +
                  $"{modelData.supports.Length} supports, {modelData.diaphragms.Length} diaphragms | " +
                  $"casos: {string.Join(",", CaseList)}");

        return true;
    }

    // =======================================================================
    //  Agregados legacy desde el JSON combinado
    // =======================================================================
    void BuildAggregates()
    {
        var m = new ModelRoot();
        m.metadata = BuildMetadata();
        m.nodes = BuildNodesAggregate();
        BuildElementsAggregate(out m.beams, out m.columns, out m.walls);
        m.supports = BuildSupportsAggregate();
        m.diaphragms = BuildDiaphragmsAggregate();
        m.constraint_links = BuildLinksAggregate();
        m.analysis = NewAnalysis();
        m.capacidades = new CapacidadPmData[0];
        m.tributary_areas = BuildTributaryAggregate();
        m.panos = new PanosData[0];
        m.pending_geometry = new PendingGeometryData[0];
        modelData = m;
        BuildBoundaryLookups();
    }

    Metadata BuildMetadata()
    {
        var md = combinedRoot.metadata;
        var concreto = md != null && md.materiales != null ? md.materiales.concreto : null;
        var unidades = md != null ? md.unidades : null;

        return new Metadata
        {
            unidades = new Units
            {
                longitud = unidades != null ? unidades.longitud : "m",
                fuerza = unidades != null ? unidades.fuerza : "kN",
                tension = unidades != null ? unidades.presion : "kPa"
            },
            sistema_coordenadas = "X=Este, Y=Norte, Z=vertical",
            fecha_generacion = md != null ? md.fecha_generacion : "",
            estado_modelo = md != null
                ? $"{md.modelo} | {md.etapa}"
                : "",
            analisis_disponible = true,
            material = concreto != null
                ? new MaterialProps
                {
                    E_kPa = concreto.E_MPa * 1000f,
                    nu = concreto.nu,
                    G_kPa = concreto.G_MPa * 1000f,
                    fuente = concreto.fuente
                }
                : new MaterialProps { E_kPa = 0f, nu = 0f, G_kPa = 0f, fuente = "" },
            conteos = new ModelCounts
            {
                nodos_totales = combinedRoot.nodes.Length,
                nodos_master = combinedRoot.masters != null ? combinedRoot.masters.Length : 0,
                apoyos = combinedRoot.supports.Length,
                diafragmas = combinedRoot.diaphragms.Length,
                elasticBeamColumn = combinedRoot.elements.Length
            },
            analisis = new AnalysisInfo
            {
                estado = "DISPONIBLE",
                analyze_retorno = 0,
                P_gravedad_kN = 0f,
                suma_Rz_kN = 0f,
                error_rel_equilibrio = 0f,
                max_desplazamiento_m = 0f
            },
            pendientes = new PendingGeometryData[0],
            limitaciones = md != null && md.notas_modelo != null
                ? md.notas_modelo : new string[0]
        };
    }

    NodeData[] BuildNodesAggregate()
    {
        var list = new List<NodeData>();
        foreach (var n in combinedRoot.nodes)
        {
            list.Add(new NodeData
            {
                tag = n.nodeTag,
                x = n.x,
                y = n.y,
                z = n.z,
                tipo = n.origen == "LT2_master" ? "master" : "estructural",
                nivel = n.nivel,
                eje_x = "",
                eje_y = ""
            });
        }
        return list.ToArray();
    }

    void BuildElementsAggregate(out BeamData[] beams, out ColumnData[] columns,
                                out WallData[] walls)
    {
        var beamList = new List<BeamData>();
        var colList = new List<ColumnData>();
        var wallList = new List<WallData>();

        for (int i = 0; i < combinedRoot.elements.Length; i++)
        {
            var e = combinedRoot.elements[i];
            elementJsonIndex[e.elementTag] = i;
            elementNodePair[e.elementTag] = new[] { e.nodeI, e.nodeJ };
            elementRefs.Remove(e.elementTag);

            if (e.tipo == "viga" || e.tipo == "viga_saliente" || e.tipo == "segmento_fachada")
            {
                beamList.Add(new BeamData
                {
                    elementTag = e.elementTag,
                    node_i = e.nodeI,
                    node_j = e.nodeJ,
                    seccion = e.seccion != null ? e.seccion.label : "",
                    longitud_m = e.longitud_m,
                    nivel = string.IsNullOrEmpty(e.nivel) ? e.nivel_lt1 : e.nivel,
                    local_axis_xz = e.vecxz,
                    A_m2 = e.seccion != null ? e.seccion.A_m2 : 0f,
                    Iy_m4 = e.seccion != null ? e.seccion.Iy_m4 : 0f,
                    Iz_m4 = e.seccion != null ? e.seccion.Iz_m4 : 0f,
                    J_m4 = e.seccion != null ? e.seccion.J_m4 : 0f
                });
            }
            else if (e.tipo == "columna" || e.tipo == "vertical_caja")
            {
                colList.Add(new ColumnData
                {
                    elementTag = e.elementTag,
                    node_i = e.nodeI,
                    node_j = e.nodeJ,
                    seccion = e.seccion != null ? e.seccion.label : "",
                    longitud_m = e.longitud_m,
                    nivel_inferior = Fallback(e.nivel_bajo, e.nivel_inferior, e.nivel),
                    nivel_superior = Fallback(e.nivel_alto, e.nivel_superior, e.nivel),
                    local_axis_xz = e.vecxz,
                    A_m2 = e.seccion != null ? e.seccion.A_m2 : 0f,
                    Iy_m4 = e.seccion != null ? e.seccion.Iy_m4 : 0f,
                    Iz_m4 = e.seccion != null ? e.seccion.Iz_m4 : 0f,
                    J_m4 = e.seccion != null ? e.seccion.J_m4 : 0f
                });
            }
            else if (e.tipo == "muro" || e.tipo == "muro_corner" || e.tipo == "conector_v40_muro")
            {
                var s = e.seccion;
                float espesor = (s != null && s.espesor_m > 1e-6f) ? s.espesor_m
                    : (s != null && s.b_m > 1e-6f ? s.b_m : 0f);
                wallList.Add(new WallData
                {
                    elementTag = e.elementTag,
                    node_i = e.nodeI,
                    node_j = e.nodeJ,
                    clave = e.clave,
                    seccion = s != null ? s.label : "",
                    espesor_m = espesor,
                    longitud_planta_m = (e.tipo == "muro_corner" && s != null && s.h_m > 1e-6f)
                        ? s.h_m : 0f,
                    orientacion = e.orientacion,
                    en_plano_direccion = "",
                    nivel_inferior = Fallback(e.nivel_bajo, e.nivel_inferior, e.nivel),
                    nivel_superior = Fallback(e.nivel_alto, e.nivel_superior, e.nivel),
                    longitud_vertical_m = e.longitud_m,
                    local_axis_xz = e.vecxz,
                    A_m2 = s != null ? s.A_m2 : 0f,
                    Iy_m4 = s != null ? s.Iy_m4 : 0f,
                    Iz_m4 = s != null ? s.Iz_m4 : 0f,
                    J_m4 = s != null ? s.J_m4 : 0f,
                    estado_geometria = e.estado_geometria,
                    fuente = e.fuente,
                    constraint = e.constraint
                });
            }
        }

        beams = beamList.ToArray();
        columns = colList.ToArray();
        walls = wallList.ToArray();
    }

    SupportData[] BuildSupportsAggregate()
    {
        var list = new List<SupportData>();
        foreach (var sp in combinedRoot.supports)
        {
            list.Add(new SupportData
            {
                nodeTag = sp.nodeTag,
                restricciones = sp.restricciones,
                tipo = "fijo",
                nivel = sp.nivel
            });
        }
        return list.ToArray();
    }

    DiaphragmData[] BuildDiaphragmsAggregate()
    {
        var list = new List<DiaphragmData>();
        foreach (var d in combinedRoot.diaphragms)
        {
            list.Add(new DiaphragmData
            {
                nivel = d.nivel,
                master = d.master,
                slaves = d.slaves,
                z = d.z_m,
                DOF_compatibilizados = d.dof_compatibilizados
            });
        }
        return list.ToArray();
    }

    ConstraintLinkData[] BuildLinksAggregate()
    {
        var list = new List<ConstraintLinkData>();
        foreach (var l in combinedRoot.constraint_links)
        {
            list.Add(new ConstraintLinkData
            {
                rectype = "rigidLink",
                nivel = l.nivel,
                nodo_maestro_retained = l.master,
                nodo_muro = l.nodo_muro,
                muro_clave = "",
                elimina_gdl = false
            });
        }
        return list.ToArray();
    }

    TributaryAreaData[] BuildTributaryAggregate()
    {
        var list = new List<TributaryAreaData>();
        if (combinedRoot.tributary_areas == null) return list.ToArray();

        // LT1: registros 1:1 con el esquema legacy del visor.
        if (combinedRoot.tributary_areas.LT1 != null &&
            combinedRoot.tributary_areas.LT1.filas != null)
        {
            foreach (var r in combinedRoot.tributary_areas.LT1.filas)
            {
                list.Add(new TributaryAreaData
                {
                    elementTag = r.element_tag,
                    nivel = r.nivel,
                    A_tributaria_m2 = r.A_tributaria_m2,
                    P_losa_kN = r.P_losa_kN,
                    w_kN_m = r.w_kN_m,
                    q_G_kPa = new[] { r.q_G_kPa },
                    longitud_m = r.longitud_m,
                    orientacion = r.orientacion,
                    origen = string.IsNullOrEmpty(r.origen)
                        ? new string[0] : new[] { r.origen }
                });
            }
        }

        // LT2: el dato existe (area/load/status); se conserva tal cual, sin
        // recalcular nada. Solo se agregan las filas cuyo receiver es BEAM.
        if (combinedRoot.tributary_areas.LT2 != null &&
            combinedRoot.tributary_areas.LT2.filas != null)
        {
            foreach (var r in combinedRoot.tributary_areas.LT2.filas)
            {
                if (r.receiver_type != "BEAM" || r.element_tag <= 0) continue;
                list.Add(new TributaryAreaData
                {
                    elementTag = r.element_tag,
                    nivel = r.level,
                    A_tributaria_m2 = r.area_m2,
                    P_losa_kN = r.load_kN,
                    w_kN_m = 0f,
                    q_G_kPa = new[] { r.qG_kN_m2 },
                    longitud_m = 0f,
                    orientacion = "",
                    origen = new[] { "LT2" }
                });
            }
        }

        return list.ToArray();
    }

    void BuildBoundaryLookups()
    {
        boundaryRestricciones.Clear();
        boundaryOrigen.Clear();

        if (combinedRoot.supports != null)
            foreach (var sp in combinedRoot.supports)
            {
                boundaryRestricciones[sp.nodeTag] = sp.restricciones ?? emptyInt6;
                boundaryOrigen[sp.nodeTag] = sp.origen;
            }

        if (combinedRoot.masters != null)
            foreach (var mst in combinedRoot.masters)
            {
                if (!boundaryRestricciones.ContainsKey(mst.nodeTag))
                {
                    boundaryRestricciones[mst.nodeTag] = mst.restricciones ?? emptyInt6;
                    boundaryOrigen[mst.nodeTag] = "LT2_master";
                }
            }
    }

    // =======================================================================
    //  Caso activo
    // =======================================================================
    void PrepareResultCaches()
    {
        forceCaseCache.Clear();
        displacementCaseCache.Clear();
        reactionCaseCache.Clear();
        equilibriumCaseCache.Clear();
        string forcesObj = ExtractValue(rawJson, "forces");
        string dispObj = ExtractValue(rawJson, "displacements");
        string reacObj = ExtractValue(rawJson, "reactions");
        string eqObj = ExtractValue(rawJson, "equilibrio");
        foreach (string c in CaseList)
        {
            forceCaseCache[c] = ParseForceCase(forcesObj, c);
            displacementCaseCache[c] = ParseValueDict(dispObj, c);
            reactionCaseCache[c] = ParseValueDict(reacObj, c);
            equilibriumCaseCache[c] = ParseEquilibrio(eqObj, c) ?? new ActiveEquilibrium();
        }
    }

    public bool SetActiveCase(string caseKey)
    {
        if (combinedRoot == null || combinedRoot.results == null ||
            combinedRoot.results.cases == null) return false;

        bool found = false;
        foreach (var c in combinedRoot.results.cases)
            if (c == caseKey) { found = true; break; }
        if (!found) return false;

        IsLinearSuperposition = false;
        return ApplyResults(caseKey, forceCaseCache[caseKey],
            displacementCaseCache[caseKey], reactionCaseCache[caseKey],
            equilibriumCaseCache[caseKey]);
    }

    public bool ApplyLinearSuperposition(float g, float q, float ex, float ey)
    {
        string[] cases = { "G", "Q", "EX", "EY" };
        float[] coef = { g, q, ex, ey };
        var forces = new Dictionary<int, float[]>();
        var displacements = new Dictionary<int, float[]>();
        var reactions = new Dictionary<int, float[]>();
        var eq = new ActiveEquilibrium { rc = 0, lat_axis = "XY" };

        for (int k = 0; k < cases.Length; k++)
        {
            if (!forceCaseCache.ContainsKey(cases[k])) return false;
            AccumulateCase(forces, forceCaseCache[cases[k]], coef[k]);
            AccumulateCase(displacements, displacementCaseCache[cases[k]], coef[k]);
            AccumulateCase(reactions, reactionCaseCache[cases[k]], coef[k]);
            AccumulateEquilibrium(eq, equilibriumCaseCache[cases[k]], coef[k]);
        }

        SuperpositionCoefficients = coef;
        IsLinearSuperposition = true;
        return ApplyResults("SUPERPOSICION", forces, displacements, reactions, eq);
    }

    static void AccumulateCase(Dictionary<int, float[]> target,
                               Dictionary<int, float[]> source, float factor)
    {
        if (source == null || Mathf.Abs(factor) <= 1e-8f) return;
        foreach (var kv in source)
        {
            if (!target.TryGetValue(kv.Key, out float[] sum))
            {
                sum = new float[kv.Value.Length];
                target[kv.Key] = sum;
            }
            int n = Mathf.Min(sum.Length, kv.Value.Length);
            for (int i = 0; i < n; i++) sum[i] += factor * kv.Value[i];
        }
    }

    static void AccumulateEquilibrium(ActiveEquilibrium sum,
                                      ActiveEquilibrium value, float factor)
    {
        if (value == null || Mathf.Abs(factor) <= 1e-8f) return;
        if (value.rc != 0) sum.rc = value.rc;
        sum.P_aplicada_kN += factor * value.P_aplicada_kN;
        sum.sum_Rx_kN += factor * value.sum_Rx_kN;
        sum.sum_Ry_kN += factor * value.sum_Ry_kN;
        sum.sum_Rz_kN += factor * value.sum_Rz_kN;
        sum.vert_ref_kN += factor * value.vert_ref_kN;
        sum.lat_ref_kN += factor * value.lat_ref_kN;
        sum.corte_basal_kN += factor * value.corte_basal_kN;
        sum.err_abs_vertical_kN += factor * value.err_abs_vertical_kN;
        sum.err_abs_lateral_kN += factor * value.err_abs_lateral_kN;
    }

    bool ApplyResults(string caseKey, Dictionary<int, float[]> forces,
                      Dictionary<int, float[]> displacements,
                      Dictionary<int, float[]> reactions, ActiveEquilibrium eq)
    {
        activeCase = caseKey;
        ResultRevision++;
        if (modelData.analysis == null) modelData.analysis = NewAnalysis();
        Eq = eq ?? new ActiveEquilibrium();

        elementForceI.Clear();
        elementForceJ.Clear();
        var fuerzas = new List<ElementInternalForceData>();
        foreach (var kv in forces)
        {
            if (kv.Value.Length < 12) continue;
            int[] pair;
            int ni = -1, nj = -1;
            if (elementNodePair.TryGetValue(kv.Key, out pair))
            {
                ni = pair[0];
                nj = pair[1];
            }
            var fI = new float[6];
            var fJ = new float[6];
            Array.Copy(kv.Value, 0, fI, 0, 6);
            Array.Copy(kv.Value, 6, fJ, 0, 6);
            elementForceI[kv.Key] = fI;
            elementForceJ[kv.Key] = fJ;
            fuerzas.Add(new ElementInternalForceData
            {
                elementTag = kv.Key,
                node_i = ni,
                node_j = nj,
                estado = "OK",
                F_i = fI,
                F_j = fJ
            });
        }

        var a = modelData.analysis;
        a.caso = caseKey;
        var info = GetCaseInfo(caseKey);
        a.caso_descripcion = IsLinearSuperposition
            ? "Combinacion lineal interactiva de G, Q, EX y EY"
            : info != null ? info.descripcion : "";
        a.convencion_fuerzas = combinedRoot.metadata != null
            ? combinedRoot.metadata.convencion_fuerzas_locales : "";
        a.estado = Eq.rc == 0
            ? (IsLinearSuperposition ? "SUPERPOSICION LINEAL" : "OK")
            : $"RC={Eq.rc}";
        a.P_aplicada_kN = Eq.P_aplicada_kN;
        a.suma_Rz_kN = Eq.sum_Rz_kN;
        a.err_abs_kN = Eq.err_abs_vertical_kN;
        a.err_rel = Eq.err_rel_vertical;
        a.max_desplazamiento_m = 0f;
        a.nodo_max_desplazamiento = -1;
        a.max_Uz_m = 0f;
        a.nan_inf = false;
        a.diafragmas_compatibles = Eq.rc == 0;
        a.reacciones = reactions;
        a.desplazamientos = displacements;
        a.fuerzas_elementos = fuerzas.ToArray();

        float maxMag = 0f;
        float maxUz = 0f;
        int nodeMax = -1;
        foreach (var kv in displacements)
        {
            var v = kv.Value;
            if (v == null || v.Length < 3) continue;
            Vector3 off = StructToUnity(v[0], v[1], v[2]);
            float mag = off.magnitude;
            if (mag > maxMag)
            {
                maxMag = mag;
                nodeMax = kv.Key;
            }
            if (Mathf.Abs(v[2]) > maxUz) maxUz = Mathf.Abs(v[2]);
        }
        a.max_desplazamiento_m = maxMag;
        a.nodo_max_desplazamiento = nodeMax;
        a.max_Uz_m = maxUz;

        if (modelData.metadata != null && modelData.metadata.analisis != null)
        {
            modelData.metadata.analisis.estado = a.estado;
            modelData.metadata.analisis.analyze_retorno = Eq.rc;
            modelData.metadata.analisis.P_gravedad_kN = Eq.P_aplicada_kN;
            modelData.metadata.analisis.suma_Rz_kN = Eq.sum_Rz_kN;
            modelData.metadata.analisis.error_rel_equilibrio = Eq.err_rel_vertical;
            modelData.metadata.analisis.max_desplazamiento_m = maxMag;
        }

        if (CaseChanged != null) CaseChanged(caseKey);
        return true;
    }

    AnalysisData NewAnalysis()
    {
        return new AnalysisData
        {
            estado = "",
            P_aplicada_kN = 0f,
            suma_Rz_kN = 0f,
            err_abs_kN = 0f,
            err_rel = 0f,
            max_desplazamiento_m = 0f,
            nodo_max_desplazamiento = -1,
            max_Uz_m = 0f,
            nan_inf = false,
            diafragmas_compatibles = true,
            reacciones = new Dictionary<int, float[]>(),
            desplazamientos = new Dictionary<int, float[]>(),
            caso = "",
            caso_descripcion = "",
            convencion_fuerzas = "",
            fuerzas_elementos = new ElementInternalForceData[0]
        };
    }

    // =======================================================================
    //  Construccion de la escena
    // =======================================================================
    public void BuildScene()
    {
        if (modelData == null) return;

        GameObject structure = new GameObject("Structure");
        GameObject nodesParent = new GameObject("Nodes");
        GameObject beamsParent = new GameObject("Beams");
        GameObject columnsParent = new GameObject("Columns");
        GameObject wallsParent = new GameObject("Walls");
        GameObject constraintLinksParent = new GameObject("ConstraintLinks");
        GameObject supportsParent = new GameObject("Supports");
        GameObject diaphragmsParent = new GameObject("Diaphragms");
        GameObject aestheticSlabsParent = new GameObject("AestheticSlabs");

        nodesParent.transform.SetParent(structure.transform);
        beamsParent.transform.SetParent(structure.transform);
        columnsParent.transform.SetParent(structure.transform);
        wallsParent.transform.SetParent(structure.transform);
        constraintLinksParent.transform.SetParent(structure.transform);
        supportsParent.transform.SetParent(structure.transform);
        diaphragmsParent.transform.SetParent(structure.transform);
        aestheticSlabsParent.transform.SetParent(structure.transform);

        BuildNodes(nodesParent.transform);
        BuildBeams(beamsParent.transform);
        BuildLt1PendingVisualBeams(beamsParent.transform);
        BuildLt2VisualBeamClosures(beamsParent.transform);
        BuildColumns(columnsParent.transform);
        BuildWalls(wallsParent.transform);
        BuildConstraintLinks(constraintLinksParent.transform);
        BuildSupports(supportsParent.transform);
        BuildDiaphragms(diaphragmsParent.transform);
        BuildAestheticSlabs(aestheticSlabsParent.transform);
        ComputeModelCenter();
    }

    void BuildAestheticSlabs(Transform parent)
    {
        string sourcePath = Path.Combine(Application.streamingAssetsPath, aestheticSlabJsonFileName);
        if (!File.Exists(sourcePath))
        {
            Debug.LogWarning($"[LT1Viewer] No se encontro la fuente de losas esteticas: {sourcePath}");
            return;
        }

        string sourceJson = File.ReadAllText(sourcePath);
        ModelRoot source = JsonUtility.FromJson<ModelRoot>(sourceJson);
        Lt1VisualSupplementRoot supplement = JsonUtility.FromJson<Lt1VisualSupplementRoot>(sourceJson);
        if (source == null || source.nodes == null || source.panos == null || source.diaphragms == null)
        {
            Debug.LogWarning("[LT1Viewer] Fuente LT1 incompleta; no se generan losas esteticas");
            return;
        }

        float offsetX;
        bool invertY;
        if (!TryGetDocumentedLt1Transform(out offsetX, out invertY))
        {
            Debug.LogWarning("[LT1Viewer] Transformacion LT1 no verificable; no se generan losas esteticas");
            return;
        }

        Dictionary<string, float> axisX = BuildAxisCoordinateMap(source.nodes, true);
        Dictionary<string, float> axisY = BuildAxisCoordinateMap(source.nodes, false);
        ApplyDocumentedAxisCorrection(axisX);

        Dictionary<string, float> levelZ = new Dictionary<string, float>();
        foreach (var diaphragm in source.diaphragms)
        {
            if (diaphragm != null && !string.IsNullOrEmpty(diaphragm.nivel))
                levelZ[diaphragm.nivel] = diaphragm.z;
        }

        aestheticSlabObjects.Clear();
        int regularPanelsBuilt = 0;
        foreach (var pano in source.panos)
        {
            float z;
            if (!levelZ.TryGetValue(pano.nivel, out z))
            {
                Debug.LogWarning($"[LT1Viewer] Losa estetica {pano.id}: falta cota de nivel verificada; se omite");
                continue;
            }

            if (CreateLt1AestheticSlab(parent, pano, pano.id, z, offsetX, invertY, axisX, axisY))
                regularPanelsBuilt++;
        }

        int basementRoofPanelsBuilt = 0;
        if (fillLt1BasementRoofForDesign && supplement != null &&
            supplement.basement_slabs != null)
        {
            // Contorno exterior digitalizado de la planta de cielo del primer
            // subterraneo. No se reutiliza la planta superior ni se cierran
            // huecos interiores cuyas cotas no estan verificadas.
            foreach (var slabData in supplement.basement_slabs)
            {
                if (slabData == null || slabData.nivel != "PISO_1S") continue;
                if (CreateLt1AestheticSlabRectangle(parent, slabData, offsetX, invertY))
                    basementRoofPanelsBuilt++;
            }
        }
        else if (fillLt1BasementRoofForDesign)
        {
            Debug.LogWarning("[LT1Viewer] Contorno PISO_1S no disponible; no se genera su techo estetico");
        }

        Debug.Log($"[LT1Viewer] Losas esteticas LT1: {regularPanelsBuilt} panos regulares + " +
                  $"{basementRoofPanelsBuilt} panos techo PISO_1S, " +
                  $"espesor grafico={aestheticSlabThickness:F2} m (sin funcion estructural)");

        BuildAestheticSlabsLt2(parent);
    }

    bool CreateLt1AestheticSlab(Transform parent, PanosData pano, string visualId,
                                float z, float offsetX, bool invertY,
                                Dictionary<string, float> axisX,
                                Dictionary<string, float> axisY)
    {
        float x0, x1, y0, y1;
        if (!axisX.TryGetValue(pano.eje_x0, out x0) ||
            !axisX.TryGetValue(pano.eje_x1, out x1) ||
            !axisY.TryGetValue(pano.eje_y0, out y0) ||
            !axisY.TryGetValue(pano.eje_y1, out y1))
        {
            Debug.LogWarning($"[LT1Viewer] Losa estetica {visualId}: faltan coordenadas verificadas; se omite");
            return false;
        }

        float combinedX0 = x0 + offsetX;
        float combinedX1 = x1 + offsetX;
        float combinedY0 = invertY ? -y0 : y0;
        float combinedY1 = invertY ? -y1 : y1;
        float sizeX = Mathf.Abs(combinedX1 - combinedX0);
        float sizeY = Mathf.Abs(combinedY1 - combinedY0);
        if (sizeX < 0.001f || sizeY < 0.001f) return false;

        GameObject slab = GameObject.CreatePrimitive(PrimitiveType.Cube);
        slab.name = $"AestheticSlab_LT1_{visualId}";
        slab.transform.position = StructToUnity(
            (combinedX0 + combinedX1) * 0.5f,
            (combinedY0 + combinedY1) * 0.5f,
            z - aestheticSlabThickness * 0.5f
        );
        slab.transform.localScale = new Vector3(sizeX, aestheticSlabThickness, sizeY);
        slab.GetComponent<Renderer>().material = aestheticSlabMaterial;

        Collider collider = slab.GetComponent<Collider>();
        if (collider != null) Destroy(collider);

        slab.transform.SetParent(parent);
        aestheticSlabObjects.Add(slab);
        return true;
    }

    bool CreateLt1AestheticSlabRectangle(Transform parent, Lt1BasementSlabData data,
                                         float offsetX, bool invertY)
    {
        float combinedX0 = data.x0 + offsetX;
        float combinedX1 = data.x1 + offsetX;
        float combinedY0 = invertY ? -data.y0 : data.y0;
        float combinedY1 = invertY ? -data.y1 : data.y1;
        float sizeX = Mathf.Abs(combinedX1 - combinedX0);
        float sizeY = Mathf.Abs(combinedY1 - combinedY0);
        if (sizeX < 0.001f || sizeY < 0.001f) return false;

        GameObject slab = GameObject.CreatePrimitive(PrimitiveType.Cube);
        slab.name = $"AestheticSlab_LT1_{data.id}";
        slab.transform.position = StructToUnity(
            (combinedX0 + combinedX1) * 0.5f,
            (combinedY0 + combinedY1) * 0.5f,
            data.z - aestheticSlabThickness * 0.5f + basementSlabVisibilityOffset
        );
        slab.transform.localScale = new Vector3(sizeX, aestheticSlabThickness, sizeY);
        slab.GetComponent<Renderer>().material = aestheticSlabMaterial;

        Collider collider = slab.GetComponent<Collider>();
        if (collider != null) Destroy(collider);

        slab.transform.SetParent(parent);
        aestheticSlabObjects.Add(slab);
        return true;
    }

    bool TryGetDocumentedLevelZ(NodeData[] nodes, string level, out float z)
    {
        z = 0f;
        bool found = false;
        foreach (var node in nodes)
        {
            if (node == null || node.nivel != level) continue;
            if (!found)
            {
                z = node.z;
                found = true;
            }
            else if (!Mathf.Approximately(z, node.z))
            {
                Debug.LogWarning($"[LT1Viewer] Nivel {level}: cotas inconsistentes");
                return false;
            }
        }
        return found;
    }

    void BuildAestheticSlabsLt2(Transform parent)
    {
        string sourcePath = Path.Combine(Application.streamingAssetsPath, aestheticSlabLt2JsonFileName);
        if (!File.Exists(sourcePath))
        {
            Debug.LogWarning($"[LT1Viewer] No se encontro la fuente de losas LT2: {sourcePath}");
            return;
        }

        Lt2VisualRoot source = JsonUtility.FromJson<Lt2VisualRoot>(File.ReadAllText(sourcePath));
        if (source == null || source.slabs == null)
        {
            Debug.LogWarning("[LT1Viewer] Fuente LT2 incompleta; no se generan sus losas esteticas");
            return;
        }

        int panelsBuilt = 0;
        int piecesBuilt = 0;
        foreach (var panel in source.slabs)
        {
            Rect outer;
            if (panel == null || !TryParseDocumentedRectangle(panel.polygon, out outer))
            {
                Debug.LogWarning($"[LT1Viewer] Pano LT2 {panel?.panel_id}: poligono no verificable; se omite");
                continue;
            }

            List<Rect> pieces = new List<Rect> { outer };
            // En L1-L4 se conservan los huecos documentados. En ROOF, la vista
            // de diseno solicitada completa la cubierta usando exclusivamente
            // el contorno exterior ya registrado de cada pano. Es estetico:
            // no modifica masa, rigidez, cargas ni la geometria de OpenSees.
            bool fillRoof = fillLt2RoofForDesign && panel.level == "ROOF";
            if (!fillRoof && panel.holes != null)
            {
                foreach (string holePolygon in panel.holes)
                {
                    Rect hole;
                    if (!TryParseDocumentedRectangle(holePolygon, out hole))
                    {
                        Debug.LogWarning($"[LT1Viewer] Pano LT2 {panel.panel_id}: hueco no verificable; se omite el pano");
                        pieces.Clear();
                        break;
                    }
                    pieces = SubtractRectangle(pieces, hole);
                }
            }

            int panelPieces = 0;
            foreach (Rect piece in pieces)
            {
                if (piece.width < 0.001f || piece.height < 0.001f) continue;

                GameObject slab = GameObject.CreatePrimitive(PrimitiveType.Cube);
                slab.name = $"AestheticSlab_LT2_{panel.panel_id}_S{panelPieces + 1}";
                slab.transform.position = StructToUnity(
                    piece.center.x,
                    piece.center.y,
                    panel.z - aestheticSlabThickness * 0.5f
                );
                slab.transform.localScale = new Vector3(
                    piece.width,
                    aestheticSlabThickness,
                    piece.height
                );
                slab.GetComponent<Renderer>().material = aestheticSlabMaterial;

                Collider collider = slab.GetComponent<Collider>();
                if (collider != null) Destroy(collider);

                slab.transform.SetParent(parent);
                aestheticSlabObjects.Add(slab);
                panelPieces++;
                piecesBuilt++;
            }

            if (panelPieces > 0) panelsBuilt++;
        }

        Debug.Log($"[LT1Viewer] Losas esteticas LT2: {panelsBuilt} panos / {piecesBuilt} piezas, " +
                  $"cubierta visual completa={(fillLt2RoofForDesign ? "SI" : "NO")}, " +
                  $"espesor grafico={aestheticSlabThickness:F2} m (sin funcion estructural)");
    }

    bool TryParseDocumentedRectangle(string polygon, out Rect rectangle)
    {
        rectangle = new Rect();
        if (string.IsNullOrEmpty(polygon)) return false;

        string[] pointTexts = polygon.Split(';');
        if (pointTexts.Length != 4) return false;

        float minX = float.MaxValue;
        float maxX = float.MinValue;
        float minY = float.MaxValue;
        float maxY = float.MinValue;
        var points = new List<Vector2>();

        foreach (string pointText in pointTexts)
        {
            string[] coordinates = pointText.Split(',');
            float x, y;
            if (coordinates.Length != 2 ||
                !TryInvariantFloat(coordinates[0].Trim(), out x) ||
                !TryInvariantFloat(coordinates[1].Trim(), out y))
                return false;

            points.Add(new Vector2(x, y));
            minX = Mathf.Min(minX, x);
            maxX = Mathf.Max(maxX, x);
            minY = Mathf.Min(minY, y);
            maxY = Mathf.Max(maxY, y);
        }

        foreach (Vector2 point in points)
        {
            bool onX = Mathf.Approximately(point.x, minX) || Mathf.Approximately(point.x, maxX);
            bool onY = Mathf.Approximately(point.y, minY) || Mathf.Approximately(point.y, maxY);
            if (!onX || !onY) return false;
        }

        rectangle = Rect.MinMaxRect(minX, minY, maxX, maxY);
        return rectangle.width > 0.001f && rectangle.height > 0.001f;
    }

    List<Rect> SubtractRectangle(List<Rect> source, Rect hole)
    {
        var result = new List<Rect>();
        foreach (Rect piece in source)
        {
            float ix0 = Mathf.Max(piece.xMin, hole.xMin);
            float ix1 = Mathf.Min(piece.xMax, hole.xMax);
            float iy0 = Mathf.Max(piece.yMin, hole.yMin);
            float iy1 = Mathf.Min(piece.yMax, hole.yMax);

            if (ix1 <= ix0 || iy1 <= iy0)
            {
                result.Add(piece);
                continue;
            }

            AddRectangleIfVisible(result, piece.xMin, piece.yMin, ix0, piece.yMax);
            AddRectangleIfVisible(result, ix1, piece.yMin, piece.xMax, piece.yMax);
            AddRectangleIfVisible(result, ix0, piece.yMin, ix1, iy0);
            AddRectangleIfVisible(result, ix0, iy1, ix1, piece.yMax);
        }
        return result;
    }

    void AddRectangleIfVisible(List<Rect> rectangles, float x0, float y0, float x1, float y1)
    {
        if (x1 - x0 > 0.001f && y1 - y0 > 0.001f)
            rectangles.Add(Rect.MinMaxRect(x0, y0, x1, y1));
    }

    bool TryGetDocumentedLt1Transform(out float offsetX, out bool invertY)
    {
        offsetX = 0f;
        invertY = false;
        string transform = combinedRoot != null && combinedRoot.metadata != null
            ? combinedRoot.metadata.transformacion_lt1 : "";
        if (string.IsNullOrEmpty(transform)) return false;

        Match xMatch = Regex.Match(transform,
            @"X'\s*=\s*X\s*([+-])\s*(\d+(?:\.\d+)?)",
            RegexOptions.IgnoreCase);
        if (!xMatch.Success || !TryInvariantFloat(xMatch.Groups[2].Value, out offsetX))
            return false;

        if (xMatch.Groups[1].Value == "-") offsetX = -offsetX;
        invertY = Regex.IsMatch(transform, @"Y'\s*=\s*-\s*Y", RegexOptions.IgnoreCase);
        bool preserveZ = Regex.IsMatch(transform, @"Z'\s*=\s*Z", RegexOptions.IgnoreCase);
        return invertY && preserveZ;
    }

    void ApplyDocumentedAxisCorrection(Dictionary<string, float> axisX)
    {
        string transform = combinedRoot != null && combinedRoot.metadata != null
            ? combinedRoot.metadata.transformacion_lt1 : "";
        Match correction = Regex.Match(transform,
            @"eje\s+(.+?)\s+corregido\s+(-?\d+(?:\.\d+)?)\s*->\s*(-?\d+(?:\.\d+)?)",
            RegexOptions.IgnoreCase);
        float corrected;
        if (correction.Success &&
            TryInvariantFloat(correction.Groups[3].Value, out corrected))
        {
            axisX[correction.Groups[1].Value.Trim()] = corrected;
        }
    }

    Dictionary<string, float> BuildAxisCoordinateMap(NodeData[] nodes, bool xAxis)
    {
        Dictionary<string, float> coordinates = new Dictionary<string, float>();
        HashSet<string> inconsistentAxes = new HashSet<string>();

        foreach (var node in nodes)
        {
            string axis = xAxis ? node.eje_x : node.eje_y;
            if (string.IsNullOrEmpty(axis) || inconsistentAxes.Contains(axis)) continue;

            float coordinate = xAxis ? node.x : node.y;
            float existing;
            if (coordinates.TryGetValue(axis, out existing) && !Mathf.Approximately(existing, coordinate))
            {
                coordinates.Remove(axis);
                inconsistentAxes.Add(axis);
                Debug.LogWarning($"[LT1Viewer] Eje {axis}: coordenada inconsistente; se omiten sus losas");
            }
            else
            {
                coordinates[axis] = coordinate;
            }
        }

        return coordinates;
    }

    void BuildNodes(Transform parent)
    {
        if (modelData.nodes == null) return;

        foreach (var node in modelData.nodes)
        {
            Vector3 pos = StructToUnity(node.x, node.y, node.z);
            bool isMaster = node.tipo == "master";

            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = $"Node_{node.tag}";
            go.transform.position = pos;

            float radius = isMaster ? 0.15f : 0.08f;
            go.transform.localScale = Vector3.one * radius * 2f;

            go.GetComponent<Renderer>().material = isMaster ? masterMaterial : nodeMaterial;
            go.transform.SetParent(parent);

            nodeObjects[node.tag] = go;
            if (isMaster)
                masterNodeObjects[node.tag] = go;
        }
    }

    void BuildBeams(Transform parent)
    {
        if (modelData.beams == null) return;

        foreach (var beam in modelData.beams)
        {
            GameObject go = CreateElementGO(
                beam.elementTag, beam.node_i, beam.node_j,
                // Grosor de representacion; no modifica la seccion ni rigidez OpenSees.
                beam.longitud_m, 0.55f, beamMaterial, "Beam"
            );
            if (go != null)
            {
                go.transform.SetParent(parent);
                beamObjects[beam.elementTag] = go;
                AttachRef(go, beam.elementTag);
            }
        }
    }

    // Vigas del cielo del primer subterraneo cuya posicion y rotulo se leen
    // en el plano, pero cuyo canto variable o encuentro vertical aun no esta
    // completamente acotado. Se dibujan para revisar la digitalizacion y no
    // reciben elementTag, rigidez, masa, cargas ni resultados analiticos.
    void BuildLt1PendingVisualBeams(Transform parent)
    {
        string sourcePath = Path.Combine(Application.streamingAssetsPath, aestheticSlabJsonFileName);
        if (!File.Exists(sourcePath)) return;

        string sourceJson = File.ReadAllText(sourcePath);
        ModelRoot modelSource = JsonUtility.FromJson<ModelRoot>(sourceJson);
        Lt1VisualSupplementRoot source =
            JsonUtility.FromJson<Lt1VisualSupplementRoot>(sourceJson);

        float offsetX;
        bool invertY;
        if (!TryGetDocumentedLt1Transform(out offsetX, out invertY)) return;

        int analyticalCreated = 0;
        if (modelSource != null && modelSource.nodes != null && modelSource.beams != null)
        {
            var sourceNodes = new Dictionary<int, NodeData>();
            foreach (var node in modelSource.nodes)
                if (node != null) sourceNodes[node.tag] = node;

            foreach (var beam in modelSource.beams)
            {
                if (beam == null || beam.nivel != "PISO_1S" ||
                    beamObjects.ContainsKey(beam.elementTag) ||
                    !sourceNodes.ContainsKey(beam.node_i) ||
                    !sourceNodes.ContainsKey(beam.node_j)) continue;

                NodeData ni = sourceNodes[beam.node_i];
                NodeData nj = sourceNodes[beam.node_j];
                Vector3 a = StructToUnity(ni.x + offsetX, invertY ? -ni.y : ni.y, ni.z);
                Vector3 b = StructToUnity(nj.x + offsetX, invertY ? -nj.y : nj.y, nj.z);
                if (CreateLt1SourceBeamVisual(parent, $"Analytical_{beam.elementTag}", a, b))
                    analyticalCreated++;
            }
        }

        int pendingCreated = 0;
        if (source != null && source.visual_beams != null)
        {
            foreach (var beam in source.visual_beams)
            {
                if (beam == null || beam.nivel != "PISO_1S") continue;
                float x1 = beam.x1 + offsetX;
                float x2 = beam.x2 + offsetX;
                float y1 = invertY ? -beam.y1 : beam.y1;
                float y2 = invertY ? -beam.y2 : beam.y2;
                Vector3 a = StructToUnity(x1, y1, beam.z1);
                Vector3 b = StructToUnity(x2, y2, beam.z2);
                if (CreateLt1SourceBeamVisual(parent, $"Pending_{beam.id}", a, b))
                    pendingCreated++;
            }
        }

        Debug.Log($"[LT1Viewer] Vigas subterraneo LT1: {analyticalCreated} analiticas incorporadas " +
                  $"desde modelo_lt1 + {pendingCreated} pendientes visuales");

        int supportWallsCreated = 0;
        if (source != null && source.visual_support_walls != null)
        {
            foreach (var wall in source.visual_support_walls)
            {
                if (wall == null || wall.nivel != "PISO_1S") continue;
                float x1 = wall.x1 + offsetX;
                float x2 = wall.x2 + offsetX;
                float y1 = invertY ? -wall.y1 : wall.y1;
                float y2 = invertY ? -wall.y2 : wall.y2;
                if (CreateLt1VisualSupportWall(parent, wall, x1, y1, x2, y2))
                    supportWallsCreated++;
            }
        }
        Debug.Log($"[LT1Viewer] Apoyos visuales subterraneo LT1: {supportWallsCreated} muros del plano 101");
    }

    bool CreateLt1SourceBeamVisual(Transform parent, string id, Vector3 a, Vector3 b)
    {
        Vector3 direction = b - a;
        float length = direction.magnitude;
        if (length < 0.001f) return false;

        GameObject visual = GameObject.CreatePrimitive(PrimitiveType.Cube);
        visual.name = $"BeamVisual_LT1_{id}";
        visual.transform.position = (a + b) * 0.5f;
        visual.transform.localScale = new Vector3(0.55f, 0.55f, length);
        visual.transform.rotation = Quaternion.FromToRotation(Vector3.forward, direction);
        visual.GetComponent<Renderer>().material = beamMaterial;
        Collider collider = visual.GetComponent<Collider>();
        if (collider != null) Destroy(collider);
        visual.transform.SetParent(parent);
        return true;
    }

    bool CreateLt1VisualSupportWall(Transform parent, Lt1VisualSupportWallData data,
                                    float x1, float y1, float x2, float y2)
    {
        float dx = x2 - x1;
        float dy = y2 - y1;
        float length = Mathf.Sqrt(dx * dx + dy * dy);
        float height = data.z_superior - data.z_inferior;
        if (length < 0.001f || height < 0.001f || data.espesor_m <= 0f) return false;

        GameObject wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
        wall.name = $"WallVisual_LT1_{data.id}";
        wall.transform.position = StructToUnity(
            (x1 + x2) * 0.5f,
            (y1 + y2) * 0.5f,
            (data.z_inferior + data.z_superior) * 0.5f
        );
        wall.transform.localScale = new Vector3(data.espesor_m, height, length);
        wall.transform.rotation = Quaternion.Euler(
            0f, Mathf.Atan2(dx, -dy) * Mathf.Rad2Deg, 0f);
        wall.GetComponent<Renderer>().material = wallMaterial;
        Collider collider = wall.GetComponent<Collider>();
        if (collider != null) Destroy(collider);
        wall.transform.SetParent(parent);
        return true;
    }

    // Cierres exclusivamente graficos para tres vigas LT2 cuya conectividad
    // analitica termina en apoyos verticales, pero que en la vista quedan con
    // una separacion respecto de la viga vecina. No se modifican nodos,
    // elementos, rigidez, cargas ni resultados del modelo OpenSees.
    void BuildLt2VisualBeamClosures(Transform parent)
    {
        int created = 0;

        // VI-02 y VI-04: cerrar el claro visual hacia sus tramos occidentales.
        if (CreateVisualBridgeBetweenBeamEnds(parent, 2232, true, 2231, false)) created++;
        if (CreateVisualBridgeBetweenBeamEnds(parent, 2234, true, 2233, false)) created++;

        // VI-07: cerrar ambos extremos; al oeste hacia VI-06 y al este hacia
        // la viga de borde existente.
        if (CreateVisualBridgeBetweenBeamEnds(parent, 2237, true, 2236, false)) created++;
        if (CreateVisualBridgeToBeam(parent, 2237, false, 2227)) created++;

        Debug.Log($"[LT1Viewer] Cierres visuales LT2: {created}/4 (tags 2232, 2234 y 2237; sin efecto estructural)");
    }

    bool CreateVisualBridgeBetweenBeamEnds(Transform parent, int sourceTag,
                                           bool sourceUseI, int targetTag,
                                           bool targetUseI)
    {
        Vector3 sourceI, sourceJ, targetI, targetJ;
        if (!TryGetElementPositions(sourceTag, out sourceI, out sourceJ) ||
            !TryGetElementPositions(targetTag, out targetI, out targetJ))
            return false;

        Vector3 a = sourceUseI ? sourceI : sourceJ;
        Vector3 b = targetUseI ? targetI : targetJ;
        return CreateVisualBeamBridge(parent, sourceTag, a, b);
    }

    bool CreateVisualBridgeToBeam(Transform parent, int sourceTag,
                                  bool sourceUseI, int targetTag)
    {
        Vector3 sourceI, sourceJ, targetI, targetJ;
        if (!TryGetElementPositions(sourceTag, out sourceI, out sourceJ) ||
            !TryGetElementPositions(targetTag, out targetI, out targetJ))
            return false;

        Vector3 a = sourceUseI ? sourceI : sourceJ;
        Vector3 targetDirection = targetJ - targetI;
        float denominator = Vector3.Dot(targetDirection, targetDirection);
        if (denominator < 0.000001f) return false;

        float t = Mathf.Clamp01(Vector3.Dot(a - targetI, targetDirection) / denominator);
        Vector3 b = targetI + targetDirection * t;
        return CreateVisualBeamBridge(parent, sourceTag, a, b);
    }

    bool TryGetElementPositions(int elementTag, out Vector3 posI, out Vector3 posJ)
    {
        posI = Vector3.zero;
        posJ = Vector3.zero;

        int[] pair;
        if (!elementNodePair.TryGetValue(elementTag, out pair) || pair.Length < 2 ||
            !nodeObjects.ContainsKey(pair[0]) || !nodeObjects.ContainsKey(pair[1]))
        {
            Debug.LogWarning($"[LT1Viewer] No se pudo crear el cierre visual de la viga {elementTag}");
            return false;
        }

        posI = nodeObjects[pair[0]].transform.position;
        posJ = nodeObjects[pair[1]].transform.position;
        return true;
    }

    bool CreateVisualBeamBridge(Transform parent, int sourceTag, Vector3 a, Vector3 b)
    {
        Vector3 direction = b - a;
        float length = direction.magnitude;
        if (length < 0.001f) return false;

        GameObject bridge = GameObject.CreatePrimitive(PrimitiveType.Cube);
        bridge.name = $"BeamVisualClosure_{sourceTag}";
        bridge.transform.position = (a + b) * 0.5f;
        bridge.transform.localScale = new Vector3(0.55f, 0.55f, length);
        bridge.transform.rotation = Quaternion.FromToRotation(Vector3.forward, direction);
        bridge.GetComponent<Renderer>().material = beamMaterial;

        Collider collider = bridge.GetComponent<Collider>();
        if (collider != null) Destroy(collider);

        bridge.transform.SetParent(parent);
        return true;
    }

    void BuildColumns(Transform parent)
    {
        if (modelData.columns == null) return;

        foreach (var col in modelData.columns)
        {
            GameObject go = CreateElementGO(
                col.elementTag, col.node_i, col.node_j,
                // Mantener una diferencia visual clara respecto de las vigas.
                col.longitud_m, 0.70f, columnMaterial, "Column"
            );
            if (go != null)
            {
                go.transform.SetParent(parent);
                columnObjects[col.elementTag] = go;
                AttachRef(go, col.elementTag);
            }
        }
    }

    void BuildWalls(Transform parent)
    {
        if (modelData.walls == null || modelData.walls.Length == 0)
        {
            Debug.Log("[LT1Viewer] no walls in model data");
            return;
        }

        foreach (var wall in modelData.walls)
        {
            // El muro equivalente (y el conector V40-muro) es un
            // elasticBeamColumn LINEAL en OpenSees. Se representa como barra
            // vertical diferenciada (color/grosor) SOLO como visualizacion.
            GameObject go = CreateElementGO(
                wall.elementTag, wall.node_i, wall.node_j,
                wall.longitud_vertical_m, 0.72f, wallMaterial, "Wall"
            );
            if (go != null)
            {
                go.transform.SetParent(parent);
                wallObjects[wall.elementTag] = go;
                AttachRef(go, wall.elementTag);
            }
        }
    }

    void AttachRef(GameObject go, int tag)
    {
        int idx;
        if (!elementJsonIndex.TryGetValue(tag, out idx)) return;
        var e = combinedRoot.elements[idx];

        ElementRef r = go.AddComponent<ElementRef>();
        r.elementTag = e.elementTag;
        r.jsonIndex = idx;
        r.tipo = e.tipo;
        r.origen = e.origen;
        r.categoria = go.name.Split('_')[0];
        r.nodeI = e.nodeI;
        r.nodeJ = e.nodeJ;
        r.longitud_m = e.longitud_m;
        r.seccion = e.seccion;
        r.vecxz = e.vecxz;
        r.ejes_locales = e.ejes_locales;
        r.nivel = e.nivel;
        r.nivel_bajo = e.nivel_bajo;
        r.nivel_alto = e.nivel_alto;
        r.nivel_inferior = e.nivel_inferior;
        r.nivel_superior = e.nivel_superior;
        r.nivel_lt1 = e.nivel_lt1;
        r.beam_id = e.beam_id;
        r.columna_id = e.columna_id;
        r.muro_id = e.muro_id;
        r.clave = e.clave;
        r.corner = e.corner;
        r.familia = e.familia;
        r.tipo_v = e.tipo_v;
        r.muro = e.muro;
        r.nodo_muro = e.nodo_muro;
        r.tag_original = e.tag_original;
        r.transf_tag = e.transf_tag;
        r.estado_geometria = e.estado_geometria;
        r.fuente = e.fuente;
        r.orientacion = e.orientacion;
        r.constraint = e.constraint;

        elementRefs[tag] = r;
    }

    void BuildConstraintLinks(Transform parent)
    {
        if (modelData.constraint_links == null || modelData.constraint_links.Length == 0)
        {
            Debug.Log("[LT1Viewer] no constraint links in model data");
            return;
        }

        foreach (var cl in modelData.constraint_links)
        {
            if (!nodeObjects.ContainsKey(cl.nodo_maestro_retained) ||
                !nodeObjects.ContainsKey(cl.nodo_muro))
                continue;

            Vector3 posA = nodeObjects[cl.nodo_maestro_retained].transform.position;
            Vector3 posB = nodeObjects[cl.nodo_muro].transform.position;

            GameObject go = CreateDashedLink(parent, "ConstraintLink_" + cl.nodo_muro, posA, posB);
            constraintLinkObjects[cl.nodo_muro] = go;
        }
    }

    GameObject CreateDashedLink(Transform parent, string name, Vector3 a, Vector3 b)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(parent);

        Vector3 dir = b - a;
        float length = dir.magnitude;
        if (length < 0.001f) return go;

        int segments = Mathf.Max(8, Mathf.RoundToInt(length / 0.5f));
        float dashLen = Mathf.Max(length / segments * 0.6f, 0.05f);
        float gapLen = Mathf.Max(length / segments * 0.4f, 0.04f);

        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = constraintLinkMaterial;
        lr.startColor = Color.cyan;
        lr.endColor = Color.cyan;
        lr.startWidth = 0.08f;
        lr.endWidth = 0.08f;
        lr.useWorldSpace = true;

        var points = new List<Vector3>();
        int pos = 0;
        Vector3 dirNorm = dir / length;
        float covered = 0f;
        while (covered < length && points.Count < 512)
        {
            float d0 = Mathf.Min(covered, length);
            float d1 = Mathf.Min(covered + dashLen, length);
            points.Add(a + dirNorm * d0);
            if (d1 > d0) points.Add(a + dirNorm * d1);
            covered = d1 + gapLen;
            pos++;
        }

        lr.positionCount = points.Count;
        for (int i = 0; i < points.Count; i++) lr.SetPosition(i, points[i]);

        return go;
    }

    GameObject CreateElementGO(int tag, int nodeI, int nodeJ, float longitud,
                               float thickness, Material material, string prefix)
    {
        if (!nodeObjects.ContainsKey(nodeI) || !nodeObjects.ContainsKey(nodeJ))
        {
            Debug.LogWarning($"[LT1Viewer] {prefix} {tag}: missing node reference ({nodeI} or {nodeJ})");
            return null;
        }

        Vector3 posI = nodeObjects[nodeI].transform.position;
        Vector3 posJ = nodeObjects[nodeJ].transform.position;
        Vector3 direction = posJ - posI;
        float length = direction.magnitude;

        if (length < 0.001f)
        {
            Debug.LogWarning($"[LT1Viewer] {prefix} {tag}: zero-length element");
            return null;
        }

        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = $"{prefix}_{tag}";
        go.transform.position = (posI + posJ) * 0.5f;
        go.transform.localScale = new Vector3(thickness, thickness, length);
        go.transform.rotation = Quaternion.FromToRotation(Vector3.forward, direction);
        go.GetComponent<Renderer>().material = material;

        return go;
    }

    void BuildSupports(Transform parent)
    {
        if (modelData.supports == null) return;

        foreach (var support in modelData.supports)
        {
            if (!nodeObjects.ContainsKey(support.nodeTag)) continue;

            Vector3 pos = nodeObjects[support.nodeTag].transform.position;

            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = $"Support_{support.nodeTag}";
            go.transform.position = pos + Vector3.down * 0.25f;
            go.transform.localScale = new Vector3(0.4f, 0.4f, 0.4f);
            go.GetComponent<Renderer>().material = supportMaterial;
            go.transform.SetParent(parent);

            supportObjects[support.nodeTag] = go;
        }
    }

    void BuildDiaphragms(Transform parent)
    {
        if (modelData.diaphragms == null) return;

        foreach (var diaphragm in modelData.diaphragms)
        {
            GameObject go = CreateDiaphragmGO(diaphragm);
            if (go != null)
                go.transform.SetParent(parent);
        }
    }

    GameObject CreateDiaphragmGO(DiaphragmData diaphragm)
    {
        GameObject go = new GameObject($"Diaphragm_nivel{diaphragm.nivel}");

        float unityY = diaphragm.z;

        Vector3 minBound = new Vector3(float.MaxValue, 0f, float.MaxValue);
        Vector3 maxBound = new Vector3(float.MinValue, 0f, float.MinValue);

        if (nodeObjects.ContainsKey(diaphragm.master))
        {
            Vector3 mp = nodeObjects[diaphragm.master].transform.position;
            minBound.x = mp.x; minBound.z = mp.z;
            maxBound.x = mp.x; maxBound.z = mp.z;
        }

        if (diaphragm.slaves != null)
        {
            foreach (int slaveTag in diaphragm.slaves)
            {
                if (!nodeObjects.ContainsKey(slaveTag)) continue;
                Vector3 sp = nodeObjects[slaveTag].transform.position;
                minBound.x = Mathf.Min(minBound.x, sp.x);
                minBound.z = Mathf.Min(minBound.z, sp.z);
                maxBound.x = Mathf.Max(maxBound.x, sp.x);
                maxBound.z = Mathf.Max(maxBound.z, sp.z);
            }
        }

        float sizeX = Mathf.Max(maxBound.x - minBound.x, 0.5f);
        float sizeZ = Mathf.Max(maxBound.z - minBound.z, 0.5f);
        Vector3 center = new Vector3(
            (minBound.x + maxBound.x) * 0.5f,
            unityY,
            (minBound.z + maxBound.z) * 0.5f
        );

        GameObject plane = GameObject.CreatePrimitive(PrimitiveType.Quad);
        plane.transform.SetParent(go.transform);
        plane.transform.position = center;
        plane.transform.localScale = new Vector3(sizeX, sizeZ, 1f);
        plane.transform.rotation = Quaternion.Euler(-90f, 0f, 0f);

        plane.GetComponent<Renderer>().material = diaphragmMaterial;

        Collider col = plane.GetComponent<Collider>();
        if (col != null) Destroy(col);

        return go;
    }

    void ComputeModelCenter()
    {
        if (modelData.nodes == null || modelData.nodes.Length == 0)
        {
            modelCenter = Vector3.zero;
            return;
        }

        Vector3 sum = Vector3.zero;
        foreach (var node in modelData.nodes)
            sum += StructToUnity(node.x, node.y, node.z);

        modelCenter = sum / modelData.nodes.Length;
    }

    string FindJsonPath()
    {
        string path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        if (File.Exists(path)) return path;

        path = Path.Combine(Application.dataPath, jsonFileName);
        if (File.Exists(path)) return path;

        path = Path.Combine(Application.persistentDataPath, jsonFileName);
        if (File.Exists(path)) return path;

        return null;
    }

    // =======================================================================
    //  Parseo de resultados por caso (JsonUtility no soporta Dictionary)
    // =======================================================================
    static string Fallback(string a, string b, string c)
    {
        if (!string.IsNullOrEmpty(a)) return a;
        if (!string.IsNullOrEmpty(b)) return b;
        return c ?? "";
    }

    static string ExtractValue(string json, string keyName)
    {
        if (string.IsNullOrEmpty(json)) return null;
        var m = Regex.Match(json, "\\\"" + Regex.Escape(keyName) + "\\\"\\s*:");
        if (!m.Success) return null;

        int i = m.Index + m.Length;
        while (i < json.Length && char.IsWhiteSpace(json[i])) i++;
        if (i >= json.Length) return null;

        char c = json[i];
        if (c == '{' || c == '[')
        {
            char open = c;
            char close = c == '{' ? '}' : ']';
            int depth = 1;
            int j = i + 1;
            bool inStr = false, esc = false;
            while (j < json.Length && depth > 0)
            {
                char ch = json[j];
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
                j++;
            }
            return json.Substring(i, j - i);
        }

        int k = i;
        bool q = false, e2 = false;
        while (k < json.Length)
        {
            char ch = json[k];
            if (q)
            {
                if (e2) e2 = false;
                else if (ch == '\\') e2 = true;
                else if (ch == '"') q = false;
            }
            else
            {
                if (ch == '"') q = true;
                else if (ch == ',' || ch == '}' || ch == ']') break;
            }
            k++;
        }
        return json.Substring(i, k - i).Trim();
    }

    static bool TryInvariantFloat(string text, out float value)
    {
        return float.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture,
                              out value);
    }

    static int ForceFieldIndex(string field)
    {
        switch (field)
        {
            case "N1": return 0;
            case "Vy1": return 1;
            case "Vz1": return 2;
            case "T1": return 3;
            case "My1": return 4;
            case "Mz1": return 5;
            case "N2": return 6;
            case "Vy2": return 7;
            case "Vz2": return 8;
            case "T2": return 9;
            case "My2": return 10;
            case "Mz2": return 11;
            default: return -1;
        }
    }

    Dictionary<int, float[]> ParseForceCase(string forcesObj, string caseKey)
    {
        var dict = new Dictionary<int, float[]>();
        if (string.IsNullOrEmpty(forcesObj)) return dict;

        string caseObj = ExtractValue(forcesObj, caseKey);
        if (string.IsNullOrEmpty(caseObj)) return dict;

        var entry = new Regex("\"(-?\\d+)\"\\s*:\\s*\\{([^}]*)\\}");
        var field = new Regex("\"([A-Za-z0-9_]+)\"\\s*:\\s*(-?\\d+\\.?\\d*(?:[eE][+\\-]?\\d+)?)");
        foreach (Match e in entry.Matches(caseObj))
        {
            if (!int.TryParse(e.Groups[1].Value, out int tag)) continue;
            float[] v = new float[12];
            foreach (Match f in field.Matches(e.Groups[2].Value))
            {
                int idx = ForceFieldIndex(f.Groups[1].Value);
                if (idx < 0) continue;
                if (TryInvariantFloat(f.Groups[2].Value, out float val)) v[idx] = val;
            }
            dict[tag] = v;
        }
        return dict;
    }

    Dictionary<int, float[]> ParseValueDict(string objStr, string caseKey)
    {
        var dict = new Dictionary<int, float[]>();
        if (string.IsNullOrEmpty(objStr)) return dict;

        string caseObj = ExtractValue(objStr, caseKey);
        if (string.IsNullOrEmpty(caseObj)) return dict;

        var entry = new Regex("\"(-?\\d+)\"\\s*:\\s*\\[([^\\]]*)\\]");
        foreach (Match e in entry.Matches(caseObj))
        {
            if (!int.TryParse(e.Groups[1].Value, out int tag)) continue;
            string[] parts = e.Groups[2].Value.Split(',');
            float[] values = new float[parts.Length];
            for (int j = 0; j < parts.Length; j++)
                TryInvariantFloat(parts[j].Trim(), out values[j]);
            dict[tag] = values;
        }
        return dict;
    }

    ActiveEquilibrium ParseEquilibrio(string eqObjStr, string caseKey)
    {
        if (string.IsNullOrEmpty(eqObjStr)) return null;

        string caseObj = ExtractValue(eqObjStr, caseKey);
        if (string.IsNullOrEmpty(caseObj)) return null;

        var eq = new ActiveEquilibrium();
        var field = new Regex("\"([A-Za-z0-9_]+)\"\\s*:\\s*(-?\\d+\\.?\\d*(?:[eE][+\\-]?\\d+)?)");
        foreach (Match f in field.Matches(caseObj))
        {
            float v;
            if (!TryInvariantFloat(f.Groups[2].Value, out v)) continue;
            switch (f.Groups[1].Value)
            {
                case "rc": eq.rc = (int)v; break;
                case "P_aplicada_kN": eq.P_aplicada_kN = v; break;
                case "sum_Rx_kN": eq.sum_Rx_kN = v; break;
                case "sum_Ry_kN": eq.sum_Ry_kN = v; break;
                case "sum_Rz_kN": eq.sum_Rz_kN = v; break;
                case "vert_ref_kN": eq.vert_ref_kN = v; break;
                case "lat_ref_kN": eq.lat_ref_kN = v; break;
                case "corte_basal_kN": eq.corte_basal_kN = v; break;
                case "err_abs_vertical_kN": eq.err_abs_vertical_kN = v; break;
                case "err_rel_vertical": eq.err_rel_vertical = v; break;
                case "err_abs_lateral_kN": eq.err_abs_lateral_kN = v; break;
                case "err_rel_lateral": eq.err_rel_lateral = v; break;
            }
        }
        var lm = Regex.Match(caseObj, "\"lat_axis\"\\s*:\\s*\"([^\"]*)\"");
        eq.lat_axis = lm.Success ? lm.Groups[1].Value : "";
        return eq;
    }
}

[Serializable]
public class ActiveEquilibrium
{
    public int rc;
    public float P_aplicada_kN;
    public float sum_Rx_kN;
    public float sum_Ry_kN;
    public float sum_Rz_kN;
    public float vert_ref_kN;
    public string lat_axis;
    public float lat_ref_kN;
    public float corte_basal_kN;
    public float err_abs_vertical_kN;
    public float err_rel_vertical;
    public float err_abs_lateral_kN;
    public float err_rel_lateral;
}

[Serializable]
public class Lt2VisualRoot
{
    public Lt2VisualSlab[] slabs;
}

[Serializable]
public class Lt1VisualSupplementRoot
{
    public Lt1VisualBeamData[] visual_beams;
    public Lt1VisualSupportWallData[] visual_support_walls;
    public Lt1BasementSlabData[] basement_slabs;
}

[Serializable]
public class Lt1VisualBeamData
{
    public string id;
    public string nivel;
    public string seccion;
    public string estado;
    public float x1;
    public float y1;
    public float x2;
    public float y2;
    public float z1;
    public float z2;
}

[Serializable]
public class Lt1BasementSlabData
{
    public string id;
    public string nivel;
    public string estado;
    public float x0;
    public float x1;
    public float y0;
    public float y1;
    public float z;
}

[Serializable]
public class Lt1VisualSupportWallData
{
    public string id;
    public string nivel;
    public string seccion;
    public string estado;
    public float espesor_m;
    public float x1;
    public float y1;
    public float x2;
    public float y2;
    public float z_inferior;
    public float z_superior;
}

[Serializable]
public class Lt2VisualSlab
{
    public string panel_id;
    public string level;
    public float z;
    public string polygon;
    public string[] holes;
    public string status;
    public string hole_status;
}
