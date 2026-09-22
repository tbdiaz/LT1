using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

// SQ4: usuario movil sobre las regiones tributarias exportadas. El punto se
// mueve con WASD/flechas o botones del HUD; la region bajo el usuario define
// las vigas receptoras. Es un prototipo de asignacion, no un reanalisis.
public class UserMovingLoadController : MonoBehaviour
{
    class Region
    {
        public string id;
        public string panel;
        public string source;
        public int floor;
        public int beamTag;
        public string receiver;
        public float baseLoad;
        public float elevation;
        public List<Vector2> polygon;
    }

    ModelLoader loader;
    readonly List<Region> regions = new List<Region>();
    readonly List<int> receiverTags = new List<int>();
    GameObject visualRoot;
    Material userMaterial;
    Material receiverMaterial;
    Vector2 position;
    int floor = 1;
    bool active;
    float magnitudeKn = 1f;
    string magnitudeText = "1.0";
    string regionLabel = "Fuera de una region tributaria.";
    string assignmentLabel = "Sin vigas receptoras.";

    public bool Active => active;
    public int Floor => floor;
    public float MagnitudeKn => magnitudeKn;
    public string MagnitudeText { get => magnitudeText; set => magnitudeText = value; }
    public string RegionLabel => regionLabel;
    public string AssignmentLabel => assignmentLabel;
    public string PositionLabel => $"X={position.x:F2} m · Y={-position.y:F2} m";
    public int ReceiverCount => receiverTags.Count;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        userMaterial = MakeMaterial(new Color(1f, 0.78f, 0.05f));
        receiverMaterial = MakeMaterial(new Color(1f, 0.20f, 0.05f));
        BuildRegions();
        MoveToFirstRegion();
    }

    void Update()
    {
        if (!active) return;
        Vector2 direction = new Vector2(Input.GetAxisRaw("Horizontal"),
                                        Input.GetAxisRaw("Vertical"));
        if (direction.sqrMagnitude <= 1e-6f) return;
        direction.Normalize();
        position += new Vector2(direction.x, -direction.y) * 3f * Time.deltaTime;
        EvaluateAndDraw();
    }

    public void Toggle()
    {
        active = !active;
        if (active)
        {
            if (regions.Count == 0) BuildRegions();
            EvaluateAndDraw();
        }
        else ClearVisuals();
    }

    public void ApplyMagnitude()
    {
        string input = (magnitudeText ?? "").Trim().Replace(',', '.');
        if (!float.TryParse(input, NumberStyles.Float, CultureInfo.InvariantCulture,
                            out float value) || value < 0f)
        {
            assignmentLabel = "P debe ser mayor o igual que cero [kN].";
            return;
        }
        magnitudeKn = value;
        magnitudeText = value.ToString("0.###", CultureInfo.InvariantCulture);
        if (active) EvaluateAndDraw();
    }

    public void MoveBy(float dx, float dy)
    {
        position += new Vector2(dx, -dy);
        if (active) EvaluateAndDraw();
    }

    public void ChangeFloor(int delta)
    {
        floor = Mathf.Clamp(floor + delta, 1, 4);
        MoveToFirstRegion();
        if (active) EvaluateAndDraw();
    }

    void MoveToFirstRegion()
    {
        foreach (Region region in regions)
        {
            if (region.floor != floor || region.polygon == null ||
                region.polygon.Count == 0) continue;
            Vector2 center = Vector2.zero;
            foreach (Vector2 p in region.polygon) center += p;
            position = center / region.polygon.Count;
            return;
        }
    }

    void BuildRegions()
    {
        regions.Clear();
        if (loader == null || loader.combinedRoot == null ||
            loader.combinedRoot.tributary_areas == null) return;
        CombinedTributary all = loader.combinedRoot.tributary_areas;
        if (all.LT2 != null && all.LT2.filas != null)
            foreach (CombinedTribRow row in all.LT2.filas) AddLt2(row);
        if (all.LT1 != null && all.LT1.filas != null)
            foreach (CombinedTribRow row in all.LT1.filas) AddLt1(row);
    }

    void AddLt2(CombinedTribRow row)
    {
        if (row == null || row.receiver_type != "BEAM" || row.element_tag <= 0 ||
            string.IsNullOrEmpty(row.polygon) ||
            !loader.beamObjects.TryGetValue(row.element_tag, out GameObject beam) ||
            beam == null) return;
        List<Vector2> polygon = ParsePolygon(row.polygon);
        if (polygon.Count < 3) return;
        regions.Add(new Region {
            id = row.tributary_id, panel = row.panel_id, source = "LT2",
            floor = FloorNumber(row.level), beamTag = row.element_tag,
            receiver = row.receiver_id, baseLoad = row.load_kN,
            elevation = beam.transform.position.y, polygon = polygon });
    }

    void AddLt1(CombinedTribRow row)
    {
        if (row == null || row.element_tag <= 0 || row.A_tributaria_m2 <= 0f ||
            !loader.elementRefs.TryGetValue(row.element_tag, out ElementRef er) ||
            er == null || !loader.nodeObjects.TryGetValue(er.nodeI, out GameObject ni) ||
            !loader.nodeObjects.TryGetValue(er.nodeJ, out GameObject nj)) return;
        Vector3 a = ni.transform.position, b = nj.transform.position;
        Vector2 av = new Vector2(a.x, a.z), bv = new Vector2(b.x, b.z);
        Vector2 d = bv - av;
        float len = d.magnitude;
        if (len < 1e-6f) return;
        Vector2 normal = new Vector2(-d.y, d.x).normalized;
        float halfWidth = row.A_tributaria_m2 / len * 0.5f;
        var polygon = new List<Vector2> {
            av + normal * halfWidth, bv + normal * halfWidth,
            bv - normal * halfWidth, av - normal * halfWidth };
        regions.Add(new Region {
            id = row.origen, panel = row.origen, source = "LT1 equivalente",
            floor = FloorNumber(row.nivel), beamTag = row.element_tag,
            receiver = row.element_tag.ToString(), baseLoad = row.P_losa_kN,
            elevation = (a.y + b.y) * 0.5f, polygon = polygon });
    }

    void EvaluateAndDraw()
    {
        ClearVisuals();
        receiverTags.Clear();
        var hits = new List<Region>();
        foreach (Region region in regions)
            if (region.floor == floor && PointInPolygon(position, region.polygon))
            {
                hits.Add(region);
                if (!receiverTags.Contains(region.beamTag)) receiverTags.Add(region.beamTag);
            }

        float elevation = FloorElevation();
        visualRoot = new GameObject("SQ4_UserMovingLoad");
        DrawUser(elevation);
        foreach (int tag in receiverTags) DrawReceiver(tag);

        if (hits.Count == 0)
        {
            regionLabel = "Fuera de una region tributaria en nivel " + floor + ".";
            assignmentLabel = "Sin vigas receptoras; P no asignada.";
            return;
        }

        var regionNames = new List<string>();
        float baseLoad = 0f;
        foreach (Region hit in hits)
        {
            string label = hit.source + " · " + (string.IsNullOrEmpty(hit.panel) ? hit.id : hit.panel);
            if (!regionNames.Contains(label)) regionNames.Add(label);
            baseLoad += hit.baseLoad;
        }
        regionLabel = string.Join(" | ", regionNames.ToArray());
        float assigned = receiverTags.Count > 0 ? magnitudeKn / receiverTags.Count : 0f;
        assignmentLabel = $"P usuario={magnitudeKn:F2} kN · {receiverTags.Count} viga(s) · " +
                          $"{assigned:F2} kN/viga · carga base regiones={baseLoad:F2} kN";
    }

    float FloorElevation()
    {
        foreach (Region region in regions) if (region.floor == floor) return region.elevation + 0.35f;
        return loader != null ? loader.modelCenter.y : 0f;
    }

    void DrawUser(float elevation)
    {
        Vector3 p = new Vector3(position.x, elevation, position.y);
        GameObject person = new GameObject("SQ4_Usuario_Persona");
        person.transform.SetParent(visualRoot.transform);

        // Figura humana esquematica de 1.70 m aprox.; solo es un marcador
        // grafico y no representa geometria ni masa estructural.
        CreatePersonPart("Cabeza", PrimitiveType.Sphere, person.transform,
                         p + Vector3.up * 1.52f, new Vector3(0.34f, 0.34f, 0.34f));
        CreatePersonPart("Torso", PrimitiveType.Capsule, person.transform,
                         p + Vector3.up * 0.98f, new Vector3(0.34f, 0.45f, 0.24f));
        DrawLine("Brazo_I", p + new Vector3(-0.20f, 1.20f, 0f),
                 p + new Vector3(-0.48f, 0.72f, 0f), userMaterial, 0.11f);
        DrawLine("Brazo_D", p + new Vector3(0.20f, 1.20f, 0f),
                 p + new Vector3(0.48f, 0.72f, 0f), userMaterial, 0.11f);
        DrawLine("Pierna_I", p + new Vector3(-0.12f, 0.62f, 0f),
                 p + new Vector3(-0.16f, 0.02f, 0f), userMaterial, 0.13f);
        DrawLine("Pierna_D", p + new Vector3(0.12f, 0.62f, 0f),
                 p + new Vector3(0.16f, 0.02f, 0f), userMaterial, 0.13f);

        // Flecha separada de la silueta para conservar la lectura de carga.
        Vector3 arrowTop = p + new Vector3(0.68f, 1.70f, 0f);
        Vector3 arrowTip = p + new Vector3(0.68f, 0.20f, 0f);
        DrawLine("SQ4_Carga", arrowTop, arrowTip, receiverMaterial, 0.11f);
        DrawLine("SQ4_Carga_Punta_I", arrowTip,
                 arrowTip + new Vector3(-0.16f, 0.24f, 0f), receiverMaterial, 0.09f);
        DrawLine("SQ4_Carga_Punta_D", arrowTip,
                 arrowTip + new Vector3(0.16f, 0.24f, 0f), receiverMaterial, 0.09f);
    }

    void CreatePersonPart(string name, PrimitiveType primitive, Transform parent,
                          Vector3 worldPosition, Vector3 scale)
    {
        GameObject part = GameObject.CreatePrimitive(primitive);
        part.name = name;
        part.transform.SetParent(parent);
        part.transform.position = worldPosition;
        part.transform.localScale = scale;
        part.GetComponent<Renderer>().material = userMaterial;
        Collider collider = part.GetComponent<Collider>();
        if (collider != null) Destroy(collider);
    }

    void DrawReceiver(int tag)
    {
        if (!loader.elementRefs.TryGetValue(tag, out ElementRef er) || er == null ||
            !loader.nodeObjects.TryGetValue(er.nodeI, out GameObject ni) ||
            !loader.nodeObjects.TryGetValue(er.nodeJ, out GameObject nj)) return;
        DrawLine("SQ4_Receptora_" + tag,
                 ni.transform.position + Vector3.up * 0.20f,
                 nj.transform.position + Vector3.up * 0.20f,
                 receiverMaterial, 0.28f);
    }

    void DrawLine(string name, Vector3 a, Vector3 b, Material mat, float width)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(visualRoot.transform);
        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = mat; lr.startColor = mat.color; lr.endColor = mat.color;
        lr.startWidth = width; lr.endWidth = width; lr.positionCount = 2;
        lr.useWorldSpace = true; lr.SetPosition(0, a); lr.SetPosition(1, b);
    }

    static List<Vector2> ParsePolygon(string text)
    {
        var result = new List<Vector2>();
        foreach (string token in text.Split(';'))
        {
            string[] xy = token.Split(',');
            if (xy.Length != 2) continue;
            if (float.TryParse(xy[0], NumberStyles.Float, CultureInfo.InvariantCulture, out float x) &&
                float.TryParse(xy[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float y))
                result.Add(new Vector2(x, -y));
        }
        return result;
    }

    static bool PointInPolygon(Vector2 p, List<Vector2> polygon)
    {
        bool inside = false;
        for (int i = 0, j = polygon.Count - 1; i < polygon.Count; j = i++)
        {
            Vector2 a = polygon[j], b = polygon[i];
            float cross = (p.x-a.x)*(b.y-a.y) - (p.y-a.y)*(b.x-a.x);
            if (Mathf.Abs(cross) < 1e-4f && p.x >= Mathf.Min(a.x,b.x)-1e-4f &&
                p.x <= Mathf.Max(a.x,b.x)+1e-4f && p.y >= Mathf.Min(a.y,b.y)-1e-4f &&
                p.y <= Mathf.Max(a.y,b.y)+1e-4f) return true;
            if (((b.y > p.y) != (a.y > p.y)) &&
                p.x < (a.x-b.x)*(p.y-b.y)/(a.y-b.y) + b.x) inside = !inside;
        }
        return inside;
    }

    static int FloorNumber(string level)
    {
        if (string.IsNullOrEmpty(level)) return 1;
        for (int i = level.Length - 1; i >= 0; i--)
            if (char.IsDigit(level[i])) return Mathf.Clamp(level[i] - '0', 1, 4);
        return 1;
    }

    Material MakeMaterial(Color color)
    {
        Material material = new Material(Shader.Find("Sprites/Default"));
        material.color = color;
        return material;
    }

    void ClearVisuals() { if (visualRoot != null) Destroy(visualRoot); visualRoot = null; }
    void OnDestroy()
    {
        ClearVisuals();
        if (userMaterial != null) Destroy(userMaterial);
        if (receiverMaterial != null) Destroy(receiverMaterial);
    }
}
