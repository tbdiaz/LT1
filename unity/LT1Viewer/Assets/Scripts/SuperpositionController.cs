using UnityEngine;

// Combina linealmente respuestas ya analizadas. Es valido mientras el modelo
// permanezca lineal y no equivale al reanalisis de un modelo modificado.
public class SuperpositionController : MonoBehaviour
{
    ModelLoader loader;

    public float G { get; private set; } = 1f;
    public float Q { get; private set; } = 1f;
    public float EX { get; private set; } = 1f;
    public float EY { get; private set; } = 0f;
    public bool Active => loader != null && loader.IsLinearSuperposition;

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
        LoadComboR(false);
    }

    public float Get(string caseKey)
    {
        switch (caseKey)
        {
            case "G": return G;
            case "Q": return Q;
            case "EX": return EX;
            case "EY": return EY;
            default: return 0f;
        }
    }

    public void Set(string caseKey, float value)
    {
        value = Mathf.Clamp(value, -2f, 2f);
        switch (caseKey)
        {
            case "G": G = value; break;
            case "Q": Q = value; break;
            case "EX": EX = value; break;
            case "EY": EY = value; break;
            default: return;
        }
        Apply();
    }

    public void LoadComboR(bool apply = true)
    {
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        CombinedCaseInfo info = loader != null ? loader.GetCaseInfo("COMBO_R") : null;
        if (info != null && info.coef != null)
        {
            G = info.coef.G;
            Q = info.coef.Q;
            EX = info.coef.EX;
            EY = info.coef.EY;
        }
        if (apply) Apply();
    }

    public void Zero()
    {
        G = Q = EX = EY = 0f;
        Apply();
    }

    void Apply()
    {
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        if (loader != null) loader.ApplyLinearSuperposition(G, Q, EX, EY);
    }
}
